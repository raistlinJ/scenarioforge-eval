#!/usr/bin/env python3
"""Regenerate ``distribution.svg`` from the dataset YAML specifications.

The chart intentionally reports configured *filter* coverage.  Actual catalog
entries are selected at evaluator runtime, so their names and frequencies are
not stable until a particular batch has completed.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import yaml


DATASETS_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = DATASETS_DIR / "distribution.svg"
VULNERABILITY_LABELS = {"php": "PHP"}


def _enabled(section: object) -> bool:
    if not isinstance(section, dict):
        return False
    if "enabled" in section:
        return bool(section["enabled"])
    if "randomize" in section:
        return bool(section["randomize"])
    return bool(section.get("count") or section.get("include") or section.get("exclude"))


def _values(section: dict, *, generator: bool = False) -> set[str]:
    values = section.get("include") or []
    if isinstance(values, str):
        values = [values]
    normalized = set()
    for value in values:
        name = str(value).strip()
        if not name:
            continue
        if generator:
            name = name.split(":", 1)[0].strip()
        normalized.add(name)
    return normalized


def collect() -> dict:
    vulnerability_types: Counter[str] = Counter()
    generator_types: Counter[str] = Counter()
    payload_rows: Counter[str] = Counter()
    payload_pairs: Counter[str] = Counter()
    composition: Counter[str] = Counter()
    feature_coverage: Counter[str] = Counter()
    chain_lengths: Counter[int] = Counter()
    segmentation_types: Counter[str] = Counter()
    spec_count = 0
    executions = 0

    for path in sorted(DATASETS_DIR.glob("*.spec.yaml")):
        with path.open(encoding="utf-8") as handle:
            spec = yaml.safe_load(handle) or {}
        iterations = max(0, int(spec.get("iterations", 1)))
        spec_count += 1
        executions += iterations

        vulns = spec.get("vulns") or {}
        generators = spec.get("flag_node_generators") or {}
        has_vulns = _enabled(vulns)
        has_generators = _enabled(generators)
        flows = spec.get("flows") or {}
        segmentation = spec.get("segmentation") or {}
        has_flows = _enabled(flows)
        has_segmentation = _enabled(segmentation)
        has_pivot = bool(
            segmentation.get("accessible_by_pivot")
            or any(item.get("pivot_enabled") for item in segmentation.get("items") or [])
        )
        if has_generators:
            feature_coverage["Flag-node generators"] += iterations
        if has_flows:
            feature_coverage["Chained challenges"] += iterations
            chain_lengths[int(flows["chain_length"])] += iterations
        if has_segmentation:
            feature_coverage["Segmentation"] += iterations
            for item in segmentation.get("items") or []:
                segmentation_types[str(item["type"]).title()] += iterations
        if has_pivot:
            feature_coverage["Pivot paths"] += iterations
        if has_vulns and has_generators:
            composition["Mixed"] += iterations
        elif has_vulns:
            composition["Vulnerability only"] += iterations
        elif has_generators:
            composition["Flag-node-generator only"] += iterations

        if has_vulns:
            for value in _values(vulns):
                label = VULNERABILITY_LABELS.get(value.lower(), value.title())
                vulnerability_types[label] += iterations
        if has_generators:
            for value in _values(generators, generator=True):
                generator_types[value] += iterations

        traffic = spec.get("traffic") or {}
        payload_types = traffic.get("payload_types") or []
        if isinstance(payload_types, str):
            payload_types = [payload_types]
        profile_rows = {"light": [1], "medium": [1, 1], "heavy": [2, 2]}
        rows = profile_rows.get(str(traffic.get("profile", "")).lower(), [])
        for index, pairs in enumerate(rows):
            if index >= len(payload_types):
                continue
            payload = str(payload_types[index]).strip().title()
            payload_rows[payload] += 1
            payload_pairs[payload] += pairs

    return {
        "spec_count": spec_count,
        "executions": executions,
        "composition": composition,
        "feature_coverage": feature_coverage,
        "chain_lengths": chain_lengths,
        "segmentation_types": segmentation_types,
        "vulnerability_types": vulnerability_types,
        "generator_types": generator_types,
        "payload_rows": payload_rows,
        "payload_pairs": payload_pairs,
    }


def _bar_rows(
    items: list[tuple[str, int, str]], *, x: int, y: int, columns: int
) -> list[str]:
    """Render non-exclusive type-coverage bars in balanced columns."""
    parts: list[str] = []
    rows = (len(items) + columns - 1) // columns
    max_value = max(value for _, value, _ in items) if items else 1
    column_width = 410 if columns == 3 else 290
    for index, (label, value, color) in enumerate(items):
        column = index // rows
        row = index % rows
        item_x = x + column * column_width
        item_y = y + row * 53
        bar_width = round(155 * value / max_value)
        parts.extend(
            [
                f'<text x="{item_x}" y="{item_y}" class="label">{escape(label)}</text>',
                f'<rect x="{item_x}" y="{item_y + 8}" width="{bar_width}" height="16" rx="3" fill="{color}"/>',
                f'<text x="{item_x + bar_width + 8}" y="{item_y + 21}" class="value">{value}</text>',
            ]
        )
    return parts


def render(summary: dict) -> str:
    executions = summary["executions"]
    specs = summary["spec_count"]
    vulnerability_types = sorted(
        summary["vulnerability_types"].items(), key=lambda item: (-item[1], item[0])
    )
    generator_types = sorted(
        summary["generator_types"].items(), key=lambda item: (-item[1], item[0])
    )
    payloads = [(name, summary["payload_rows"][name], summary["payload_pairs"][name]) for name in ("Text", "Photo", "Audio", "Video", "Gibberish")]
    composition = summary["composition"]
    features = summary["feature_coverage"]
    chain_lengths = summary["chain_lengths"]
    segmentation_types = summary["segmentation_types"]
    service_types = [
        *[(name, count, "#dc2626") for name, count in vulnerability_types],
        *[(name, count, "#0f766e") for name, count in generator_types],
    ]
    service_types.sort(key=lambda item: (-item[1], item[0]))

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1370" viewBox="0 0 1400 1370" role="img" aria-labelledby="title desc">',
        '  <title id="title">ScenarioForge-Eval dataset type distribution</title>',
        '  <desc id="desc">Combined configured service coverage, execution composition, and traffic payload configuration across the dataset YAML suite. Red bars represent Vulhub images and teal bars represent self-generated services.</desc>',
        '  <style>',
        '    text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #1f2937; }',
        '    .title { font-size: 28px; font-weight: 700; }',
        '    .subtitle { font-size: 14px; fill: #4b5563; }',
        '    .panel { fill: #ffffff; stroke: #d1d5db; stroke-width: 1; }',
        '    .panel-title { font-size: 18px; font-weight: 700; }',
        '    .label { font-size: 13px; }',
        '    .value { font-size: 13px; font-weight: 700; }',
        '    .note { font-size: 12px; fill: #6b7280; }',
        '    .big { font-size: 30px; font-weight: 700; }',
        '  </style>',
        '  <rect width="1400" height="1370" fill="#f8fafc"/>',
        '  <text x="50" y="53" class="title">ScenarioForge-Eval dataset distribution</text>',
        f'  <text x="50" y="78" class="subtitle">{specs} specifications × their declared iterations = {executions} resolved scenarios</text>',
        '  <rect x="40" y="105" width="640" height="142" rx="12" class="panel"/>',
        '  <text x="64" y="140" class="panel-title">Resolved scenario composition</text>',
        '  <text x="64" y="163" class="note">Mutually exclusive execution counts</text>',
        f'  <text x="64" y="210" class="big">{composition["Vulnerability only"]}</text><text x="64" y="230" class="note">vulnerability only</text>',
        f'  <text x="274" y="210" class="big">{composition["Flag-node-generator only"]}</text><text x="274" y="230" class="note">flag-node-generator only</text>',
        f'  <text x="536" y="210" class="big">{composition["Mixed"]}</text><text x="536" y="230" class="note">mixed</text>',
        '  <rect x="705" y="105" width="655" height="142" rx="12" class="panel"/>',
        '  <text x="729" y="140" class="panel-title">How to read the type charts</text>',
        '  <text x="729" y="166" class="note">A bar is the number of declared iterations whose YAML includes that service type.</text>',
        '  <text x="729" y="187" class="note">Service bars are non-exclusive and do not sum to 150. Runtime catalog selections can vary per batch.</text>',
        '  <text x="729" y="220" class="note">Vulhub-image and self-generated counts add topology nodes; they do not create additional scenarios.</text>',
        '  <rect x="40" y="275" width="1320" height="180" rx="12" class="panel"/>',
        '  <text x="64" y="312" class="panel-title">Chained challenge and network-feature balance</text>',
        f'  <text x="64" y="355" class="big">{features["Chained challenges"]}</text><text x="64" y="377" class="note">chained scenarios</text>',
        f'  <text x="242" y="355" class="big">{features["Flag-node generators"]}</text><text x="242" y="377" class="note">flag-node-generator scenarios</text>',
        f'  <text x="500" y="355" class="big">{features["Segmentation"]}</text><text x="500" y="377" class="note">segmented scenarios</text>',
        f'  <text x="700" y="355" class="big">{features["Pivot paths"]}</text><text x="700" y="377" class="note">pivot-path scenarios</text>',
        f'  <text x="64" y="425" class="note">Fixed chain lengths: {" · ".join(f"{length} hops × {chain_lengths[length]}" for length in sorted(chain_lengths))}</text>',
        f'  <text x="700" y="425" class="note">Explicit boundary coverage: Firewall × {segmentation_types["Firewall"]} · NAT × {segmentation_types["Nat"]}</text>',
        '  <rect x="40" y="485" width="1320" height="610" rx="12" class="panel"/>',
        '  <text x="64" y="522" class="panel-title">Services</text>',
        f'  <text x="64" y="545" class="note">{len(service_types)} configured types · executions with service included</text>',
        '  <rect x="405" y="531" width="14" height="14" rx="3" fill="#dc2626"/><text x="427" y="543" class="note">Vulhub images (vulnerabilities)</text>',
        '  <rect x="625" y="531" width="14" height="14" rx="3" fill="#0f766e"/><text x="647" y="543" class="note">Self-generated services</text>',
        *[f'  {line}' for line in _bar_rows(service_types, x=64, y=584, columns=3)],
        '  <rect x="40" y="1125" width="1320" height="200" rx="12" class="panel"/>',
        '  <text x="64" y="1162" class="panel-title">Traffic payload configuration</text>',
        '  <text x="64" y="1185" class="note">Every resolved scenario enables traffic.</text>',
    ]
    colors = {"Text": "#2563eb", "Photo": "#db2777", "Audio": "#0891b2", "Video": "#7c3aed", "Gibberish": "#475569"}
    for index, (name, rows, pairs) in enumerate(payloads):
        x = 64 + index * 250
        svg.extend(
            [
                f'  <text x="{x}" y="1230" class="label">{name}</text>',
                f'  <rect x="{x}" y="1242" width="{rows * 14}" height="20" rx="4" fill="{colors[name]}"/>',
                f'  <text x="{x}" y="1286" class="value">{rows} rows · {pairs} pairs</text>',
            ]
        )
    svg.extend(
        [
            '  <text x="64" y="1310" class="note">Source: static YAML filters and declared iterations. Regenerate with: uv run python datasets/generate_distribution.py</text>',
            '</svg>',
            '',
        ]
    )
    return "\n".join(svg)


def main() -> None:
    OUTPUT_PATH.write_text(render(collect()), encoding="utf-8")


if __name__ == "__main__":
    main()
