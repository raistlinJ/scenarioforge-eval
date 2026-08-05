#!/usr/bin/env python3
"""Expand the dataset suite into fixed, one-iteration specification files.

Each file gets a stable seed derived from its source file and iteration number.
That fixes all evaluator-resolved ranges and makes catalog selections
reproducible while the installed ScenarioForge catalog remains unchanged.
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path

import yaml

from scenarioforge_eval.parser import SpecParser


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPOSITORY_ROOT / "datasets"
OUTPUT_DIR = REPOSITORY_ROOT / "dataset-resolved"


def _seed_for(source: Path, iteration: int) -> int:
    digest = hashlib.sha256(f"{source.name}:{iteration}".encode("utf-8")).digest()
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
    return {
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


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    generated = 0
    for source in sorted(SOURCE_DIR.glob("*.spec.yaml")):
        parser = SpecParser(str(source))
        iterations = max(0, int(parser.spec.get("iterations", 1)))
        for iteration in range(1, iterations + 1):
            source_name = source.name.removesuffix(".spec.yaml")
            destination = OUTPUT_DIR / f"{source_name}-run{iteration:02d}.spec.yaml"
            legacy_destination = OUTPUT_DIR / f"{source.stem}-run{iteration:02d}.spec.yaml"
            if legacy_destination != destination and legacy_destination.exists():
                legacy_destination.unlink()
            payload = _resolved_spec(source, iteration)
            destination.write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
            generated += 1
    print(f"Generated {generated} fixed specs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
