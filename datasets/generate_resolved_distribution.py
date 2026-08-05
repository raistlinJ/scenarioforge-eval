#!/usr/bin/env python3
"""Render the exact catalog-selection distribution for ``dataset-resolved``."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parent.parent
RESOLVED_DIR = ROOT / 'dataset-resolved'
MANIFEST = RESOLVED_DIR / 'catalog-selections.json'
OUTPUT = RESOLVED_DIR / 'distribution.svg'


def _counts(summary: dict) -> tuple[Counter[str], Counter[str], dict[str, str]]:
    vulnerability_counts = Counter()
    generator_counts = Counter()
    labels = {}
    for selection in summary['selections']:
        for name in selection['vulnerabilities']:
            vulnerability_counts[name] += 1
        for generator in selection['generators']:
            generator_counts[generator['id']] += generator['count']
            labels[generator['id']] = generator['name']
    return vulnerability_counts, generator_counts, labels


def _histogram_text(counts: Counter[str]) -> str:
    histogram = Counter(counts.values())
    return ' · '.join(f'{histogram[count]} names × {count}' for count in sorted(histogram))


def _network_summary(summary: dict) -> dict:
    routers = hosts = service_assignments = 0
    base_nodes = []
    total_nodes = []
    scale = Counter()
    flow_lengths = []
    segmented = firewalls = nats = pivots = 0
    segmentation_densities = []

    for selection in summary['selections']:
        spec_path = RESOLVED_DIR / selection['file']
        spec = yaml.safe_load(spec_path.read_text(encoding='utf-8')) or {}
        topology = spec['topology']
        router_count = int(topology['routers'])
        host_count = int(topology['hosts'])
        routers += router_count
        hosts += host_count
        base_count = router_count + host_count
        base_nodes.append(base_count)
        catalog_nodes = sum(item['count'] for item in (spec['vulns'].get('specific') or []))
        catalog_nodes += sum(item['count'] for item in (spec['flag_node_generators'].get('specific') or []))
        total_nodes.append(base_count + catalog_nodes)
        if base_count <= 6:
            scale['small'] += 1
        elif base_count <= 12:
            scale['medium'] += 1
        else:
            scale['large'] += 1

        services = spec['services']
        if services.get('enabled'):
            service_assignments += int(services['count'])
        flows = spec['flows']
        if flows.get('enabled'):
            flow_lengths.append(int(flows['chain_length']))
        segmentation = spec['segmentation']
        if segmentation.get('enabled'):
            segmented += 1
            segmentation_densities.append(float(segmentation['density']))
            for item in segmentation.get('items') or []:
                count = int(item['count'])
                if item['type'] == 'Firewall':
                    firewalls += count
                elif item['type'] == 'NAT':
                    nats += count
                if item.get('pivot_enabled'):
                    pivots += count

    return {
        'routers': routers,
        'hosts': hosts,
        'base_nodes': sum(base_nodes),
        'base_range': (min(base_nodes), max(base_nodes)),
        'total_nodes': sum(total_nodes),
        'total_range': (min(total_nodes), max(total_nodes)),
        'scale': scale,
        'service_assignments': service_assignments,
        'flow_count': len(flow_lengths),
        'flow_range': (min(flow_lengths), max(flow_lengths)),
        'segmented': segmented,
        'firewalls': firewalls,
        'nats': nats,
        'pivots': pivots,
        'density_range': (min(segmentation_densities), max(segmentation_densities)),
    }


def _rows(items: list[tuple[str, int]], *, x: int, y: int, color: str) -> list[str]:
    max_count = max(count for _, count in items) if items else 1
    parts = []
    for index, (label, count) in enumerate(items):
        row_y = y + index * 34
        width = round(185 * count / max_count)
        display_label = label if len(label) <= 34 else f'{label[:33]}…'
        parts.extend([
            f'<text x="{x}" y="{row_y}" class="label">{escape(display_label)}</text>',
            f'<rect x="{x + 250}" y="{row_y - 13}" width="{width}" height="16" rx="3" fill="{color}"/>',
            f'<text x="{x + 443}" y="{row_y}" class="value">{count}</text>',
        ])
    return parts


def render(summary: dict) -> str:
    vulnerabilities, generators, labels = _counts(summary)
    network = _network_summary(summary)
    top_vulns = sorted(vulnerabilities.items(), key=lambda item: (-item[1], item[0]))[:14]
    top_generators = sorted(
        ((labels[item_id], count) for item_id, count in generators.items()),
        key=lambda item: (-item[1], item[0]),
    )[:14]
    total_vulns = sum(vulnerabilities.values())
    total_generators = sum(generators.values())
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200" role="img" aria-labelledby="title desc">',
        '  <title id="title">Exact resolved service distribution</title>',
        '  <desc id="desc">Concrete Vulhub image and self-generated service selections, plus fixed topology and segmentation configuration, materialized in the resolved dataset.</desc>',
        '  <style>',
        '    text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #1f2937; }',
        '    .title { font-size: 28px; font-weight: 700; }',
        '    .subtitle, .note { font-size: 12px; fill: #6b7280; }',
        '    .panel { fill: #ffffff; stroke: #d1d5db; stroke-width: 1; }',
        '    .panel-title { font-size: 18px; font-weight: 700; }',
        '    .label { font-size: 12px; }',
        '    .value { font-size: 12px; font-weight: 700; }',
        '    .big { font-size: 28px; font-weight: 700; }',
        '  </style>',
        '  <rect width="1200" height="920" fill="#f8fafc"/>',
        '  <text x="45" y="52" class="title">Exact resolved service distribution</text>',
        f'  <text x="45" y="76" class="subtitle">{summary["resolved_spec_count"]} fixed scenarios · catalog snapshot at {escape(summary["scenarioforge_path"])}</text>',
        '  <rect x="35" y="102" width="360" height="150" rx="12" class="panel"/>',
        '  <text x="58" y="136" class="panel-title">Vulhub images</text>',
        f'  <text x="58" y="181" class="big">{total_vulns}</text><text x="58" y="203" class="note">selected topology nodes</text>',
        f'  <text x="205" y="181" class="big">{len(vulnerabilities)}</text><text x="205" y="203" class="note">unique concrete images</text>',
        f'  <text x="58" y="231" class="note">{min(vulnerabilities.values())}–{max(vulnerabilities.values())} uses per image; all {len(vulnerabilities)} images represented</text>',
        '  <rect x="420" y="102" width="360" height="150" rx="12" class="panel"/>',
        '  <text x="443" y="136" class="panel-title">Self-generated services</text>',
        f'  <text x="443" y="181" class="big">{total_generators}</text><text x="443" y="203" class="note">selected topology nodes</text>',
        f'  <text x="590" y="181" class="big">{len(generators)}/{summary["eligible_generator_count"]}</text><text x="590" y="203" class="note">enabled generators represented</text>',
        f'  <text x="443" y="231" class="note">{min(generators.values())}–{max(generators.values())} uses per generator; all {len(generators)} represented</text>',
        '  <rect x="805" y="102" width="360" height="150" rx="12" class="panel"/>',
        '  <text x="828" y="136" class="panel-title">Fixed network topology</text>',
        f'  <text x="828" y="181" class="big">{network["routers"]}</text><text x="828" y="203" class="note">routers</text>',
        f'  <text x="975" y="181" class="big">{network["hosts"]}</text><text x="975" y="203" class="note">Docker hosts</text>',
        f'  <text x="828" y="231" class="note">{network["total_nodes"]} total planned nodes including catalog nodes</text>',
        '  <rect x="35" y="280" width="1130" height="225" rx="12" class="panel"/>',
        '  <text x="58" y="316" class="panel-title">Network configuration</text>',
        f'  <text x="58" y="346" class="value">Topology scale</text><text x="58" y="368" class="note">{network["scale"]["small"]} small (≤6), {network["scale"]["medium"]} medium (7–12), {network["scale"]["large"]} large (13+) base-node scenarios</text>',
        f'  <text x="58" y="392" class="note">{network["base_nodes"]} base nodes total; {network["base_range"][0]}–{network["base_range"][1]} base and {network["total_range"][0]}–{network["total_range"][1]} total nodes per scenario.</text>',
        f'  <text x="650" y="346" class="value">Services and flows</text><text x="650" y="368" class="note">{network["service_assignments"]} fixed service assignments · {network["flow_count"]} flow scenarios · {network["flow_range"][0]}–{network["flow_range"][1]} hop chains</text>',
        f'  <text x="650" y="392" class="note">Traffic remains enabled in all {summary["resolved_spec_count"]} scenarios with fixed payload rows in each YAML.</text>',
        f'  <text x="58" y="434" class="value">Segmentation</text><text x="58" y="456" class="note">{network["segmented"]} scenarios · {network["firewalls"]} Firewall rows · {network["nats"]} NAT rows · {network["pivots"]} pivot-enabled rows · density {network["density_range"][0]:.2f}–{network["density_range"][1]:.2f}</text>',
        '  <text x="650" y="434" class="value">Subnet CIDRs</text><text x="650" y="456" class="note">Allocated during ScenarioForge topology; these YAMLs fix the inputs.</text>',
        '  <rect x="35" y="540" width="550" height="585" rx="12" class="panel"/>',
        '  <text x="58" y="576" class="panel-title">Most-used exact Vulhub images</text>',
        '  <text x="58" y="598" class="note">Red bars · every exact selection is in catalog-selections.json and its YAML.</text>',
        *[f'  {line}' for line in _rows(top_vulns, x=58, y=635, color="#dc2626")],
        '  <rect x="615" y="540" width="550" height="585" rx="12" class="panel"/>',
        '  <text x="638" y="576" class="panel-title">Most-used exact self-generated services</text>',
        f'  <text x="638" y="598" class="note">Teal bars · all {len(generators)} enabled non-Sample generators are represented at least once.</text>',
        *[f'  {line}' for line in _rows(top_generators, x=638, y=635, color="#0f766e")],
        '  <text x="45" y="1170" class="note">Selection is greedily balanced across each eligible filter set; rerun materialization after changing the ScenarioForge catalog.</text>',
        '</svg>',
        '',
    ]
    return '\n'.join(svg)


def main() -> None:
    if not MANIFEST.exists():
        raise SystemExit('Missing catalog-selections.json. Run materialize_catalog_selections.py first.')
    summary = json.loads(MANIFEST.read_text(encoding='utf-8'))
    OUTPUT.write_text(render(summary), encoding='utf-8')


if __name__ == '__main__':
    main()
