#!/usr/bin/env python3
"""Rejoin comma-split facts in installed generator manifests.

A fact name can contain a comma -- ``Credential(user, password)``,
``PortForward(host, port)``, ``Directory(host, path)``. In the packs installed
on this machine, 32 of 87 manifests store each of those as *two* list entries:

    artifacts:
      requires:
      - Knowledge(ip)
      - Credential(user      # <- one fact, split on its comma
      - password)

Both ``artifacts.requires``/``produces`` and the ``inputs[].name`` fields are
affected. Nothing in the current code does this -- ``_split_artifact_list``
preserves commas correctly on every input shape -- so it is damage carried in
the packs themselves, from an older importer or the upstream export.

Why it matters: a fragment never matches a real producer, so dependency
analysis sees requirements that can never be satisfied and produces that
nobody consumes. ``_normalize_fact_names`` does not rejoin them either, so the
fragments flow into chain validation as distinct facts.

The repair is unambiguous: a fragment is any entry whose parentheses are
unbalanced, and it is closed by appending following entries -- with ``, `` --
until they balance. Nothing else is touched.

Idempotent, and backs up each file it changes as ``manifest.yaml.prefacts``
(skipped when that backup already exists, so re-running cannot lose the
original).

Usage:
    python3 scripts/repair_generator_manifest_facts.py --sf-path ../scenarioforge
    python3 scripts/repair_generator_manifest_facts.py --sf-path ../scenarioforge --apply

Without ``--apply`` it only reports. ``outputs/`` is gitignored, so these
edits are machine-local and must be reapplied after reinstalling a pack --
see catalog-fixes.md.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml


def rejoin(values: list) -> tuple[list[str], int]:
    """Rejoin fragments split on a fact's internal comma.

    Returns the repaired list and how many joins were performed.
    """
    out: list[str] = []
    joins = 0
    buffer = ""
    for raw in values:
        text = str(raw or "").strip()
        if not text:
            continue
        if buffer:
            buffer = f"{buffer}, {text}"
            joins += 1
        else:
            buffer = text
        if buffer.count("(") <= buffer.count(")"):
            out.append(buffer)
            buffer = ""
    if buffer:
        # Unbalanced to the end: keep it rather than silently dropping data.
        out.append(buffer)
    return out, joins


def repair_manifest(data: dict) -> int:
    """Repair a loaded manifest in place. Returns the number of joins made."""
    joins = 0
    artifacts = data.get("artifacts")
    if isinstance(artifacts, dict):
        for key in ("requires", "produces", "optional_requires"):
            values = artifacts.get(key)
            if isinstance(values, list):
                fixed, count = rejoin(values)
                if count:
                    artifacts[key] = fixed
                    joins += count
    inputs = data.get("inputs")
    if isinstance(inputs, list):
        # Second corruption shape: the split turned the tail into a stray
        # mapping key instead of a list entry, so the dict reads
        # {'name': 'Credential(user', 'password)': None, 'type': ...}.
        for item in inputs:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name or name.count("(") <= name.count(")"):
                continue
            for key in [k for k in item if isinstance(k, str)]:
                if key == "name" or item.get(key) is not None:
                    continue
                if key.count(")") > key.count("("):
                    item["name"] = f"{name}, {key.strip()}"
                    del item[key]
                    joins += 1
                    break
        names = [item.get("name") if isinstance(item, dict) else item for item in inputs]
        if any(str(n or "").count("(") != str(n or "").count(")") for n in names):
            rebuilt: list = []
            pending: dict | None = None
            for item in inputs:
                if not isinstance(item, dict):
                    rebuilt.append(item)
                    continue
                name = str(item.get("name") or "").strip()
                if pending is not None:
                    pending["name"] = f"{pending['name']}, {name}"
                    joins += 1
                    if pending["name"].count("(") <= pending["name"].count(")"):
                        rebuilt.append(pending)
                        pending = None
                    continue
                if name.count("(") > name.count(")"):
                    pending = dict(item)
                    pending["name"] = name
                    continue
                rebuilt.append(item)
            if pending is not None:
                rebuilt.append(pending)
            data["inputs"] = rebuilt
    return joins


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf-path", default="../scenarioforge", help="ScenarioForge checkout")
    parser.add_argument("--apply", action="store_true", help="write changes (default: report only)")
    args = parser.parse_args()

    root = Path(args.sf_path).expanduser().resolve() / "outputs" / "installed_generators"
    if not root.is_dir():
        print(f"FAIL: {root} does not exist", file=sys.stderr)
        return 1

    changed = 0
    total_joins = 0
    scanned = 0
    for manifest_path in sorted(root.glob("*/*/manifest.yaml")):
        scanned += 1
        try:
            data = yaml.safe_load(manifest_path.read_text(encoding="utf-8", errors="ignore")) or {}
        except Exception as exc:
            print(f"  skip (unparseable): {manifest_path} ({exc})")
            continue
        if not isinstance(data, dict):
            continue
        joins = repair_manifest(data)
        if not joins:
            continue
        changed += 1
        total_joins += joins
        print(f"  {manifest_path.parent.name}: {joins} join(s)  id={data.get('id')}")
        if args.apply:
            backup = manifest_path.with_suffix(manifest_path.suffix + ".prefacts")
            if not backup.exists():
                shutil.copy2(manifest_path, backup)
            manifest_path.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )

    print(f"\nscanned {scanned} manifest(s); {changed} need repair ({total_joins} joins)")
    if changed and not args.apply:
        print("re-run with --apply to write the changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
