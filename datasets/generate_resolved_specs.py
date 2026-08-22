#!/usr/bin/env python3
"""Expand the dataset suite into fixed, one-iteration specification files.

Each file gets a stable seed derived from its source file and iteration number.
That fixes all evaluator-resolved ranges and makes catalog selections
reproducible while the installed ScenarioForge catalog remains unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import random
from pathlib import Path

import yaml

from scenarioforge_eval.parser import SpecParser


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPOSITORY_ROOT / "datasets"
OUTPUT_DIR = REPOSITORY_ROOT / "dataset-resolved"

# (source stem, iteration) -> retry suffix, for iterations whose default seed
# resolved a vulnerability/flag-node-generator combination the flag-sequencing
# solver cannot find a distinct compatible generator assignment for (chain
# nodes are all mandatory in this suite -- see the flow-length comment in
# generate_ground_truth_figures.py -- so an incompatible combination cannot
# fall back to a shorter chain; it just fails). Bumping to a fresh seed keeps
# the dataset's declared config unchanged while giving the solver a different
# random selection to work with. Confirmed against real flag-sequencing
# failures: eligible_flag_generators=59, eligible_flag_node_generators=87 in
# every case, so the pool was never the constraint.
_RETRY_SEED_OVERRIDES: dict[tuple[str, int], str] = {
    ("24-artifact-data-stores", 3): "retry1",
    ("35-mixed-perimeter-identity", 2): "retry1",
    ("54-segmented-enterprise-pivots", 2): "retry1",
    ("52-segmented-mixed-perimeter", 2): "retry1",
    # Iterations 1 and 4 land a "dependency consumer" generator
    # (dep_ssh_key_bastion, dep_api_key_admin_endpoint) on a pivot target, and
    # the two constraints that puts on the step cannot both hold. The consumer
    # needs an artifact -- SSHPrivateKey(path), APIKey(service) -- that nothing
    # in the chain produces, so Flow can only hand it over at a chain start;
    # being a pivot target simultaneously pins the step after its provider.
    # First position or after the provider: no ordering is both. The solver
    # picks the pair anyway because a pivot requirement is attached during
    # assignment enrichment, after selection has already committed, so the
    # constraint is invisible where the choice is made. Teaching selection
    # about pivots was tried and reverted: pivot requirements are pervasive
    # here (7 of 8 steps in run01 want one), so every version of that rule
    # starved the solver into producing no chain at all rather than a
    # different one. Re-seeding avoids the pairing outright and leaves the
    # declared config untouched; a real fix means solving selection and
    # ordering together instead of in sequence.
    # Iteration 4 needed a second bump: `retry1` still landed a consumer on a
    # pivot target (`Pivot(docker-11)` required at position 0). `retry2`
    # resolves cleanly. Both were checked by running flag-sequencing against
    # the regenerated spec, not by inspection.
    ("54-segmented-enterprise-pivots", 1): "retry1",
    ("54-segmented-enterprise-pivots", 4): "retry2",
}


def _seed_for(source: Path, iteration: int) -> int:
    key = f"{source.name}:{iteration}"
    # `.stem` only strips one suffix, leaving ".spec" on a ".spec.yaml" name.
    stem = source.name.removesuffix(".spec.yaml")
    retry = _RETRY_SEED_OVERRIDES.get((stem, iteration))
    if retry:
        key = f"{key}:{retry}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _yaml_traffic(parser: SpecParser, rng: random.Random) -> dict:
    """Convert parser-normalized traffic rows back to public schema fields."""
    traffic = parser.get_traffic_spec(rng=rng)
    items = []
    for item in traffic.pop("items"):
        items.append(
            {
                "type": item["selected"],
                "count": item["v_count"],
                "factor": item["factor"],
                "pattern": item["pattern"],
                "rate_kbps": item["rate_kbps"],
                "period_s": item["period_s"],
                "jitter_pct": item["jitter_pct"],
                "content_type": item["content_type"],
            }
        )
    # The explicit rows above replace the named profile in a fully resolved spec.
    traffic.pop("profile", None)
    traffic.pop("payload_types", None)
    traffic["items"] = items
    return traffic


def _yaml_segmentation(parser: SpecParser, rng: random.Random) -> dict:
    """Convert parser-normalized segmentation rows back to public schema fields."""
    segmentation = parser.get_segmentation_spec(rng=rng)
    items = []
    for item in segmentation.pop("items"):
        converted = {
            key: value
            for key, value in item.items()
            if key not in {"selected", "v_metric", "v_count"}
        }
        converted["type"] = item["selected"]
        converted["count"] = item["v_count"]
        items.append(converted)
    segmentation["items"] = items
    return segmentation


def _resolved_spec(source: Path, iteration: int) -> dict:
    parser = SpecParser(str(source))
    seed = _seed_for(source, iteration)
    rng = random.Random(seed)
    name = f"{parser.get_name()}_run{iteration:02d}"
    resolved = {
        "name": name,
        "iterations": 1,
        "seed": seed,
        "topology": parser.get_topology_spec(rng=rng),
        "services": parser.get_services_spec(rng=rng),
        "traffic": _yaml_traffic(parser, rng),
        "vulns": parser.get_vulns_spec(rng=rng),
        "flag_node_generators": parser.get_flag_node_generators_spec(rng=rng),
        "flows": parser.get_flows_spec(rng=rng),
        "segmentation": _yaml_segmentation(parser, rng),
        "hitl": parser.get_hitl_spec(),
        "validation": parser.get_validation_spec(),
    }
    # Ground truth for accuracy scoring travels with the resolved spec: a run is
    # graded from the file it was launched with, not from its source.
    if isinstance(parser.spec.get("expected"), dict):
        resolved["expected"] = parser.spec["expected"]
    # Difficulty band travels too, so results can be broken down by tier.
    if parser.spec.get("tier") is not None:
        resolved["tier"] = parser.spec["tier"]
    # A prompt is not resolvable to fixed values the way a range is: the model
    # decides the topology at run time. Carry the request so a resolved spec
    # still reproduces the same *request*, and leave it out entirely for the
    # deterministic suite so those files are unchanged.
    ai = parser.get_ai_spec(rng=rng)
    if not ai.get("enabled"):
        return resolved

    resolved["ai"] = ai
    # Sections the prompt replaces are dropped unless the author wrote them:
    # on the AI path `_generate_xml` never reads them, so resolving them from
    # defaults only invites a reader to believe a scenario has 3 routers and 9
    # hosts when its prompt asked for 2 and 3.
    #
    # `flows` is deliberately NOT in this list even though no prompt spec
    # declares it. main.py rebuilds every section through the SpecParser
    # getters on each run, so an omitted `flows` does not disable
    # flag-sequencing -- it re-randomizes chain_length (3-5) per run, which is
    # the one section that reaches the AI path at runtime and the opposite of
    # what a "resolved" spec is for. Writing it out pins it.
    for section in (
        "topology",
        "services",
        "traffic",
        "vulns",
        "flag_node_generators",
        "segmentation",
    ):
        if section not in parser.spec:
            resolved.pop(section, None)
    return resolved


def generate(source_dir: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    for source in sorted(source_dir.glob("*.spec.yaml")):
        parser = SpecParser(str(source))
        iterations = max(0, int(parser.spec.get("iterations", 1)))
        for iteration in range(1, iterations + 1):
            source_name = source.name.removesuffix(".spec.yaml")
            destination = output_dir / f"{source_name}-run{iteration:02d}.spec.yaml"
            legacy_destination = output_dir / f"{source.stem}-run{iteration:02d}.spec.yaml"
            if legacy_destination != destination and legacy_destination.exists():
                legacy_destination.unlink()
            payload = _resolved_spec(source, iteration)
            destination.write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
            generated += 1
    print(f"Generated {generated} fixed specs in {output_dir}")
    return generated


def main() -> None:
    # The prompt-driven suite resolves through exactly the same seeding and
    # section normalization, so it gets directory arguments rather than a
    # second copy of this script.
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = ap.parse_args()
    generate(args.source_dir, args.output_dir)


if __name__ == "__main__":
    main()
