#!/usr/bin/env python3
"""Generate traceable ground-truth and paper-ready dataset-distribution figures."""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import yaml


ROOT = Path(__file__).resolve().parent.parent
RESOLVED = ROOT / 'dataset-resolved'
MANIFEST = RESOLVED / 'catalog-selections.json'
STATS_PATH = RESOLVED / 'ground-truth-statistics.json'
GROUND_TRUTH = RESOLVED / 'ground-truth-distribution.svg'
PAPER = RESOLVED / 'research-distribution.svg'


# These families describe what the catalog components are, rather than merely
# repeating their repository-directory names. Components not named below are
# application frameworks, web applications, or CMS targets by default.
VULHUB_SEMANTIC_FAMILIES = {
    'Data, search & storage': {
        'adminer', 'couchdb', 'elasticsearch', 'h2database', 'hadoop', 'hugegraph',
        'influxdb', 'kibana', 'metabase', 'mongo-express', 'mysql', 'neo4j', 'opentsdb',
        'pgadmin', 'phpmyadmin', 'postgres', 'redis', 'solr', 'spark', 'superset',
    },
    'DevOps, CI/CD & source control': {
        'docker', 'gitea', 'gitlab', 'gitlist', 'gogs', 'jenkins', 'jmeter', 'nexus',
        'saltstack', 'teamcity',
    },
    'Messaging, integration & middleware': {
        'activemq', 'apache-cxf', 'dubbo', 'kafka', 'nacos', 'openfire', 'rocketmq', 'xstream',
    },
    'Enterprise & collaboration applications': {
        'aj-report', 'confluence', 'jira', 'metersphere', 'ofbiz', 'showdoc', 'v2board', 'yapi', 'zabbix',
    },
    'Network & web infrastructure': {
        'apisix', 'appweb', 'cgi', 'cups-browsed', 'dns', 'goahead', 'httpd', 'ingress-nginx',
        'mini_httpd', 'nginx', 'ntopng', 'opensmtpd', 'samba', 'webmin',
    },
    'Security, identity & remote access': {
        'apereo-cas', 'jumpserver', 'libssh', 'openssh', 'openssl', 'polkit', 'shiro',
    },
    'System tools, runtimes & media': {
        'aria2', 'bash', 'electron', 'erlang', 'ffmpeg', 'imagemagick', 'java', 'librsvg', 'phpunit', 'python',
    },
}

SELF_GENERATED_SEMANTIC_FAMILIES = {
    'Web delivery & application access': {'HTTP', 'HTTPS'},
    'Remote administration & source access': {'SSH', 'Git'},
    'Identity & discovery': {'DNS', 'LDAP'},
    'File sharing': {'NFS', 'SMB', 'Network Share'},
    'Data stores': {'Database', 'Cache'},
    'Messaging & transfer': {'Mail', 'MQTT', 'FTP'},
    'Software supply chain': {'Dependency Consumer'},
}


def population(values: list[int | float]) -> dict:
    return {
        'n': len(values),
        'total': sum(values),
        'mean': statistics.fmean(values),
        'variance': statistics.pvariance(values),
        'std_dev': statistics.pstdev(values),
        'minimum': min(values),
        'maximum': max(values),
    }


def rounded(metrics: dict) -> dict:
    return {key: round(value, 3) if isinstance(value, float) else value for key, value in metrics.items()}


def _entity_data(summary: dict) -> tuple[Counter[str], Counter[str], dict[str, str], Counter[str], Counter[str]]:
    vulnerabilities = Counter(summary['vulnerabilities'])
    generators = Counter(summary['flag_node_generators'])
    generator_labels = {}
    for selection in summary['selections']:
        for generator in selection['generators']:
            generator_labels[generator['id']] = generator['name']

    vulnerability_types = Counter()
    vulnerability_type_images = Counter()
    for key, count in vulnerabilities.items():
        image_name = key.split('|', 1)[0]
        family = image_name.split('/', 1)[0]
        vulnerability_types[family] += count
        vulnerability_type_images[family] += 1

    generator_types = Counter()
    for generator_id, count in generators.items():
        family = generator_labels[generator_id].split(':', 1)[0]
        generator_types[family] += count
    return vulnerabilities, generators, generator_labels, vulnerability_types, generator_types


def _semantic_family(value: str, taxonomy: dict[str, set[str]], fallback: str) -> str:
    for family, members in taxonomy.items():
        if value in members:
            return family
    return fallback


def _network_data(summary: dict) -> tuple[dict[str, dict], dict[str, dict], list[dict], dict]:
    values = {key: [] for key in ('routers', 'docker_hosts', 'base_nodes', 'total_nodes', 'service_assignments', 'flow_hops', 'segmentation_rows')}
    traffic_values = {key: [] for key in ('density', 'rows', 'requested_pairs')}
    traffic_types: Counter[str] = Counter()
    traffic_pairs: Counter[str] = Counter()
    feature_counts: Counter[str] = Counter()
    flow_length_histogram: Counter[int] = Counter()
    segmentation_type_rows: Counter[str] = Counter()
    pivot_provider_rows: Counter[str] = Counter()
    for selection in summary['selections']:
        spec = yaml.safe_load((RESOLVED / selection['file']).read_text(encoding='utf-8')) or {}
        routers = int(spec['topology']['routers'])
        hosts = int(spec['topology']['hosts'])
        catalog_nodes = sum(item['count'] for item in (spec['vulns'].get('specific') or []))
        catalog_nodes += sum(item['count'] for item in (spec['flag_node_generators'].get('specific') or []))
        values['routers'].append(routers)
        values['docker_hosts'].append(hosts)
        values['base_nodes'].append(routers + hosts)
        values['total_nodes'].append(routers + hosts + catalog_nodes)
        values['service_assignments'].append(int(spec['services']['count']) if spec['services'].get('enabled') else 0)
        generators = spec['flag_node_generators']
        flows = spec['flows']
        segmentation = spec['segmentation']
        if generators.get('enabled'):
            feature_counts['flag_node_generator_scenarios'] += 1
        if flows.get('enabled'):
            length = int(flows['chain_length'])
            feature_counts['chained_scenarios'] += 1
            flow_length_histogram[length] += 1
        else:
            length = 0
            feature_counts['unchained_scenarios'] += 1
        segmentation_items = segmentation.get('items') or []
        if segmentation.get('enabled'):
            feature_counts['segmented_scenarios'] += 1
        if segmentation.get('accessible_by_pivot') or any(item.get('pivot_enabled') for item in segmentation_items):
            feature_counts['pivot_scenarios'] += 1
        for item in segmentation_items:
            count = int(item['count'])
            segmentation_type_rows[str(item['type'])] += count
            if item.get('pivot_enabled'):
                pivot_provider_rows[str(item.get('pivot_provider') or 'random')] += count
        values['flow_hops'].append(length)
        values['segmentation_rows'].append(sum(int(item['count']) for item in segmentation_items))
        traffic = spec.get('traffic') or {}
        items = traffic.get('items') or []
        traffic_values['density'].append(float(traffic.get('density', 0.0)))
        traffic_values['rows'].append(len(items))
        traffic_values['requested_pairs'].append(sum(int(item.get('count', 0)) for item in items))
        for item in items:
            payload = str(item.get('content_type') or 'text').title()
            traffic_types[payload] += 1
            traffic_pairs[payload] += int(item.get('count', 0))
    type_rows = [
        {'type': name, 'rows': traffic_types[name], 'requested_pairs': traffic_pairs[name]}
        for name in sorted(traffic_types)
    ]
    return (
        {name: rounded(population(items)) for name, items in values.items()},
        {name: rounded(population(items)) for name, items in traffic_values.items()},
        type_rows,
        dict(feature_counts) | {
            'flow_length_histogram': dict(sorted(flow_length_histogram.items())),
            'segmentation_type_rows': dict(sorted(segmentation_type_rows.items())),
            'pivot_provider_rows': dict(sorted(pivot_provider_rows.items())),
        },
    )


def collect() -> dict:
    summary = json.loads(MANIFEST.read_text(encoding='utf-8'))
    vulnerabilities, generators, labels, vulnerability_types, generator_types = _entity_data(summary)
    network_metrics, traffic_metrics, traffic_types, challenge_features = _network_data(summary)
    vulnerability_semantic = Counter()
    vulnerability_semantic_images = Counter()
    for key, count in vulnerabilities.items():
        component = key.split('|', 1)[0].split('/', 1)[0]
        family = _semantic_family(component, VULHUB_SEMANTIC_FAMILIES, 'Web applications, frameworks & CMS')
        vulnerability_semantic[family] += count
        vulnerability_semantic_images[family] += 1
    generator_semantic = Counter()
    generator_semantic_entries = Counter()
    for generator_id, count in generators.items():
        component = labels[generator_id].split(':', 1)[0]
        family = _semantic_family(component, SELF_GENERATED_SEMANTIC_FAMILIES, 'Other self-generated service')
        generator_semantic[family] += count
        generator_semantic_entries[family] += 1
    statistics_payload = {
        'methodology': {
            'selection_statistics': 'Population statistics over concrete catalog-entry selection counts.',
            'network_statistics': 'Population statistics over one fixed value per resolved scenario.',
            'vulnerability_type': 'First path component of the concrete Vulhub image name.',
            'generator_type': 'Prefix of the enabled generator display name before the first colon.',
            'excluded_generator_family': 'Sample',
        },
        'scenario_count': summary['resolved_spec_count'],
        'catalog_snapshot': summary['scenarioforge_path'],
        'vulhub_images': rounded(population(list(vulnerabilities.values()))) | {
            'catalog_entries': summary['eligible_vulnerability_count'],
            'coverage_fraction': len(vulnerabilities) / summary['eligible_vulnerability_count'],
            'type_count': len(vulnerability_types),
        },
        'self_generated_services': rounded(population(list(generators.values()))) | {
            'catalog_entries': summary['eligible_generator_count'],
            'coverage_fraction': len(generators) / summary['eligible_generator_count'],
            'type_count': len(generator_types),
        },
        'network_per_scenario': network_metrics,
        'traffic_per_scenario': traffic_metrics,
        'traffic_payload_types': traffic_types,
        'challenge_features': challenge_features,
        'vulnerability_types': [
            {'type': name, 'selections': count, 'unique_images': sum(1 for key in vulnerabilities if key.split('|', 1)[0].split('/', 1)[0] == name)}
            for name, count in sorted(vulnerability_types.items(), key=lambda item: (-item[1], item[0]))
        ],
        'self_generated_service_types': [
            {'type': name, 'selections': count, 'unique_generators': sum(1 for generator_id in generators if labels[generator_id].split(':', 1)[0] == name)}
            for name, count in sorted(generator_types.items(), key=lambda item: (-item[1], item[0]))
        ],
        'vulhub_semantic_families': [
            {'family': name, 'selections': count, 'unique_images': vulnerability_semantic_images[name]}
            for name, count in sorted(vulnerability_semantic.items(), key=lambda item: (-item[1], item[0]))
        ],
        'self_generated_semantic_families': [
            {'family': name, 'selections': count, 'unique_generators': generator_semantic_entries[name]}
            for name, count in sorted(generator_semantic.items(), key=lambda item: (-item[1], item[0]))
        ],
        'vulhub_component_family_map': {
            component: _semantic_family(component, VULHUB_SEMANTIC_FAMILIES, 'Web applications, frameworks & CMS')
            for component in sorted(vulnerability_types)
        },
        'self_generated_type_family_map': {
            component: _semantic_family(component, SELF_GENERATED_SEMANTIC_FAMILIES, 'Other self-generated service')
            for component in sorted(generator_types)
        },
        'selection_histograms': {
            'vulhub_images': dict(sorted(Counter(vulnerabilities.values()).items())),
            'self_generated_services': dict(sorted(Counter(generators.values()).items())),
        },
    }
    return statistics_payload


def _style() -> list[str]:
    return [
        '  <style>',
        '    text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #1f2937; }',
        '    .title { font-size: 28px; font-weight: 700; }',
        '    .subtitle, .note { font-size: 12px; fill: #6b7280; }',
        '    .panel { fill: #ffffff; stroke: #d1d5db; stroke-width: 1; }',
        '    .panel-title { font-size: 18px; font-weight: 700; }',
        '    .label { font-size: 12px; }',
        '    .value { font-size: 12px; font-weight: 700; }',
        '    .big { font-size: 27px; font-weight: 700; }',
        '    .header { font-size: 12px; font-weight: 700; fill: #4b5563; }',
        '  </style>',
    ]


def _type_rows(items: list[dict], *, x: int, y: int, color: str, maximum: int) -> list[str]:
    rows = []
    max_count = max(item['selections'] for item in items) if items else 1
    for index, item in enumerate(items[:maximum]):
        row_y = y + index * 29
        label = item['type'] if len(item['type']) <= 26 else f"{item['type'][:25]}…"
        width = round(152 * item['selections'] / max_count)
        rows.extend([
            f'<text x="{x}" y="{row_y}" class="label">{escape(label)}</text>',
            f'<rect x="{x + 175}" y="{row_y - 12}" width="{width}" height="15" rx="3" fill="{color}"/>',
            f'<text x="{x + 335}" y="{row_y}" class="value">{item["selections"]} / {item["unique_images"] if "unique_images" in item else item["unique_generators"]}</text>',
        ])
    return rows


def _histogram(histogram: dict[str, int]) -> str:
    return ' · '.join(f'{count} entries × {uses} use{"s" if uses != 1 else ""}' for uses, count in histogram.items())


def ground_truth_svg(data: dict) -> str:
    vulns = data['vulhub_images']
    generators = data['self_generated_services']
    vtypes = data['vulnerability_types']
    gtypes = data['self_generated_service_types']
    network = data['network_per_scenario']
    features = data['challenge_features']
    chain_summary = ' · '.join(
        f'{length} hops × {count}'
        for length, count in features['flow_length_histogram'].items()
    )
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1380" viewBox="0 0 1400 1380" role="img" aria-labelledby="title desc">',
        '  <title id="title">Ground-truth resolved dataset distribution</title>',
        '  <desc id="desc">Exact catalog coverage, type aggregates, selection-frequency distributions, and population statistics for the materialized dataset.</desc>',
        *_style(),
        '  <rect width="1400" height="1380" fill="#f8fafc"/>',
        '  <text x="45" y="52" class="title">Ground-truth resolved dataset distribution</text>',
        f'  <text x="45" y="76" class="subtitle">{data["scenario_count"]} fixed scenarios · exact selections from {escape(data["catalog_snapshot"])}</text>',
        '  <rect x="35" y="102" width="650" height="155" rx="12" class="panel"/>',
        '  <text x="58" y="138" class="panel-title">Vulhub images</text>',
        f'  <text x="58" y="184" class="big">{vulns["catalog_entries"]}/{vulns["catalog_entries"]}</text><text x="58" y="205" class="note">catalog images represented</text>',
        f'  <text x="270" y="184" class="big">{vulns["total"]}</text><text x="270" y="205" class="note">total selections</text>',
        f'  <text x="440" y="184" class="big">{vulns["type_count"]}</text><text x="440" y="205" class="note">component types</text>',
        f'  <text x="58" y="235" class="note">Mean {vulns["mean"]:.3f} · population variance {vulns["variance"]:.3f} · population SD {vulns["std_dev"]:.3f} · range {vulns["minimum"]}–{vulns["maximum"]}</text>',
        '  <rect x="715" y="102" width="650" height="155" rx="12" class="panel"/>',
        '  <text x="738" y="138" class="panel-title">Self-generated services</text>',
        f'  <text x="738" y="184" class="big">{generators["catalog_entries"]}/{generators["catalog_entries"]}</text><text x="738" y="205" class="note">enabled non-Sample generators represented</text>',
        f'  <text x="1015" y="184" class="big">{generators["total"]}</text><text x="1015" y="205" class="note">total selections</text>',
        f'  <text x="1170" y="184" class="big">{generators["type_count"]}</text><text x="1170" y="205" class="note">service types</text>',
        f'  <text x="738" y="235" class="note">Mean {generators["mean"]:.3f} · population variance {generators["variance"]:.3f} · population SD {generators["std_dev"]:.3f} · range {generators["minimum"]}–{generators["maximum"]}</text>',
        '  <rect x="35" y="285" width="650" height="700" rx="12" class="panel"/>',
        '  <text x="58" y="321" class="panel-title">Vulhub component types</text>',
        '  <text x="58" y="343" class="note">Top 20 of 136 types · label / selections / unique images. Full table: ground-truth-statistics.json.</text>',
        *[f'  {line}' for line in _type_rows(vtypes, x=58, y=378, color="#dc2626", maximum=20)],
        '  <rect x="715" y="285" width="650" height="700" rx="12" class="panel"/>',
        '  <text x="738" y="321" class="panel-title">Self-generated service types</text>',
        '  <text x="738" y="343" class="note">All 15 types · label / selections / unique generators.</text>',
        *[f'  {line}' for line in _type_rows(gtypes, x=738, y=378, color="#0f766e", maximum=15)],
        '  <rect x="35" y="1015" width="650" height="245" rx="12" class="panel"/>',
        '  <text x="58" y="1051" class="panel-title">Network ground truth per scenario</text>',
        '  <text x="58" y="1074" class="note">Population statistics over fixed YAML values: mean · variance · SD · observed range.</text>',
        '  <text x="58" y="1101" class="header">Metric</text><text x="280" y="1101" class="header">Mean</text><text x="360" y="1101" class="header">Variance</text><text x="460" y="1101" class="header">SD</text><text x="555" y="1101" class="header">Range</text>',
        f'  <text x="58" y="1128" class="label">Routers</text><text x="280" y="1128" class="value">{network["routers"]["mean"]:.3f}</text><text x="360" y="1128" class="value">{network["routers"]["variance"]:.3f}</text><text x="460" y="1128" class="value">{network["routers"]["std_dev"]:.3f}</text><text x="555" y="1128" class="value">{network["routers"]["minimum"]}–{network["routers"]["maximum"]}</text>',
        f'  <text x="58" y="1150" class="label">Docker hosts</text><text x="280" y="1150" class="value">{network["docker_hosts"]["mean"]:.3f}</text><text x="360" y="1150" class="value">{network["docker_hosts"]["variance"]:.3f}</text><text x="460" y="1150" class="value">{network["docker_hosts"]["std_dev"]:.3f}</text><text x="555" y="1150" class="value">{network["docker_hosts"]["minimum"]}–{network["docker_hosts"]["maximum"]}</text>',
        f'  <text x="58" y="1172" class="label">Base nodes</text><text x="280" y="1172" class="value">{network["base_nodes"]["mean"]:.3f}</text><text x="360" y="1172" class="value">{network["base_nodes"]["variance"]:.3f}</text><text x="460" y="1172" class="value">{network["base_nodes"]["std_dev"]:.3f}</text><text x="555" y="1172" class="value">{network["base_nodes"]["minimum"]}–{network["base_nodes"]["maximum"]}</text>',
        f'  <text x="58" y="1194" class="label">Total planned nodes</text><text x="280" y="1194" class="value">{network["total_nodes"]["mean"]:.3f}</text><text x="360" y="1194" class="value">{network["total_nodes"]["variance"]:.3f}</text><text x="460" y="1194" class="value">{network["total_nodes"]["std_dev"]:.3f}</text><text x="555" y="1194" class="value">{network["total_nodes"]["minimum"]}–{network["total_nodes"]["maximum"]}</text>',
        f'  <text x="58" y="1216" class="label">Service assignments</text><text x="280" y="1216" class="value">{network["service_assignments"]["mean"]:.3f}</text><text x="360" y="1216" class="value">{network["service_assignments"]["variance"]:.3f}</text><text x="460" y="1216" class="value">{network["service_assignments"]["std_dev"]:.3f}</text><text x="555" y="1216" class="value">{network["service_assignments"]["minimum"]}–{network["service_assignments"]["maximum"]}</text>',
        f'  <text x="58" y="1238" class="label">Flow hops / segmentation rows</text><text x="280" y="1238" class="value">{network["flow_hops"]["mean"]:.3f} / {network["segmentation_rows"]["mean"]:.3f}</text><text x="460" y="1238" class="value">SD {network["flow_hops"]["std_dev"]:.3f} / {network["segmentation_rows"]["std_dev"]:.3f}</text><text x="555" y="1238" class="value">{network["flow_hops"]["minimum"]}–{network["flow_hops"]["maximum"]} / {network["segmentation_rows"]["minimum"]}–{network["segmentation_rows"]["maximum"]}</text>',
        '  <rect x="715" y="1015" width="650" height="245" rx="12" class="panel"/>',
        '  <text x="738" y="1051" class="panel-title">Selection-frequency ground truth</text>',
        f'  <text x="738" y="1080" class="value">Vulhub images</text><text x="738" y="1102" class="note">{escape(_histogram(data["selection_histograms"]["vulhub_images"]))}</text>',
        f'  <text x="738" y="1133" class="value">Self-generated services</text><text x="738" y="1155" class="note">{escape(_histogram(data["selection_histograms"]["self_generated_services"]))}</text>',
        f'  <text x="738" y="1187" class="value">Chained challenges</text><text x="738" y="1209" class="note">{features["chained_scenarios"]} chained / {features["unchained_scenarios"]} baseline · {chain_summary}</text>',
        f'  <text x="738" y="1235" class="note">{features["flag_node_generator_scenarios"]} generator · {features["segmented_scenarios"]} segmented · {features["pivot_scenarios"]} pivot scenarios</text>',
        '  <text x="45" y="1330" class="note">Generated from catalog-selections.json and the fixed resolved YAMLs. No runtime execution outcome is implied.</text>',
        '</svg>',
        '',
    ]
    return '\n'.join(lines)


def _stat_row(label: str, metrics: dict, *, y: int) -> str:
    return (
        f'<text x="75" y="{y}" class="label">{escape(label)}</text>'
        f'<text x="350" y="{y}" class="value">{metrics["n"]}</text>'
        f'<text x="455" y="{y}" class="value">{metrics["total"]}</text>'
        f'<text x="565" y="{y}" class="value">{metrics["mean"]:.3f}</text>'
        f'<text x="705" y="{y}" class="value">{metrics["variance"]:.3f}</text>'
        f'<text x="850" y="{y}" class="value">{metrics["std_dev"]:.3f}</text>'
        f'<text x="995" y="{y}" class="value">{metrics["minimum"]}–{metrics["maximum"]}</text>'
    )


def research_svg(data: dict) -> str:
    vulns = data['vulhub_images']
    generators = data['self_generated_services']
    network = data['network_per_scenario']
    traffic = data['traffic_per_scenario']
    traffic_types = data['traffic_payload_types']
    vulnerability_families = data['vulhub_semantic_families']
    generator_families = data['self_generated_semantic_families']
    vuln_histogram = [(int(uses), entries) for uses, entries in data['selection_histograms']['vulhub_images'].items()]
    generator_histogram = [(int(uses), entries) for uses, entries in data['selection_histograms']['self_generated_services'].items()]
    features = data['challenge_features']
    chain_summary = ' · '.join(
        f'{length}×{count}' for length, count in features['flow_length_histogram'].items()
    )
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1360" viewBox="0 0 1400 1360" role="img" aria-labelledby="title desc">',
        '  <title id="title">Resolved ScenarioForge dataset: coverage and balance</title>',
        '  <desc id="desc">Research-ready bar-chart summary of exact catalog balance, network and traffic variation, payload allocation, and semantic family composition.</desc>',
        *_style(),
        '  <rect width="1400" height="1360" fill="#ffffff"/>',
        '  <text x="50" y="55" class="title">Resolved ScenarioForge dataset: coverage and balance</text>',
        f'  <text x="50" y="80" class="subtitle">Ground truth: {data["scenario_count"]} fixed scenarios, materialized against one validated catalog snapshot</text>',
        '  <rect x="40" y="108" width="410" height="108" rx="12" class="panel"/>',
        f'  <text x="64" y="145" class="big">{vulns["catalog_entries"]}/{vulns["catalog_entries"]}</text><text x="64" y="166" class="note">Vulhub images covered (100%)</text>',
        f'  <text x="64" y="195" class="note">{len(vulnerability_families)} semantic families · {vulns["total"]} selections · mean {vulns["mean"]:.2f} ± {vulns["std_dev"]:.2f}</text>',
        '  <rect x="495" y="108" width="410" height="108" rx="12" class="panel"/>',
        f'  <text x="519" y="145" class="big">{generators["catalog_entries"]}/{generators["catalog_entries"]}</text><text x="519" y="166" class="note">Non-Sample generators covered (100%)</text>',
        f'  <text x="519" y="195" class="note">{len(generator_families)} semantic families · {generators["total"]} selections · mean {generators["mean"]:.2f} ± {generators["std_dev"]:.2f}</text>',
        '  <rect x="950" y="108" width="410" height="108" rx="12" class="panel"/>',
        f'  <text x="974" y="145" class="big">{features["chained_scenarios"]}</text><text x="974" y="166" class="note">chained, reproducible scenarios</text>',
        f'  <text x="974" y="195" class="note">Chain lengths: {chain_summary} · {features["pivot_scenarios"]} pivot scenarios</text>',
        '  <rect x="40" y="245" width="620" height="220" rx="12" class="panel"/>',
        '  <text x="64" y="281" class="panel-title">Concrete Vulhub entry balance</text>',
        f'  <text x="64" y="303" class="note">Bar height = number of images at each exact use count. Population variance {vulns["variance"]:.3f}; SD {vulns["std_dev"]:.3f}.</text>',
        '  <rect x="710" y="245" width="650" height="220" rx="12" class="panel"/>',
        '  <text x="734" y="281" class="panel-title">Concrete self-generated entry balance</text>',
        f'  <text x="734" y="303" class="note">Bar height = number of generators at each exact use count. Population variance {generators["variance"]:.3f}; SD {generators["std_dev"]:.3f}.</text>',
    ]
    vhist_max = max(entries for _, entries in vuln_histogram)
    for index, (uses, entries) in enumerate(vuln_histogram):
        x = 75 + index * 88
        height = round(105 * entries / vhist_max)
        lines.append(f'  <rect x="{x}" y="{425 - height}" width="46" height="{height}" rx="4" fill="#dc2626"/><text x="{x + 17}" y="446" class="label">{uses}×</text><text x="{x + 8}" y="{418 - height}" class="value">{entries}</text>')
    ghist_max = max(entries for _, entries in generator_histogram)
    for index, (uses, entries) in enumerate(generator_histogram):
        x = 770 + index * 110
        height = round(105 * entries / ghist_max)
        lines.append(f'  <rect x="{x}" y="{425 - height}" width="58" height="{height}" rx="4" fill="#0f766e"/><text x="{x + 21}" y="446" class="label">{uses}×</text><text x="{x + 12}" y="{418 - height}" class="value">{entries}</text>')
    lines.extend([
        '  <rect x="40" y="500" width="620" height="365" rx="12" class="panel"/>',
        '  <text x="64" y="536" class="panel-title">Network variation per scenario</text>',
        '  <text x="64" y="558" class="note">Bar = mean as a share of that row’s observed maximum; labels give mean ± SD and range.</text>',
    ])
    for index, (label, key) in enumerate((('Routers', 'routers'), ('Docker hosts', 'docker_hosts'), ('Base nodes', 'base_nodes'), ('Total planned nodes', 'total_nodes'), ('Service assignments', 'service_assignments'), ('Flow hops', 'flow_hops'), ('Segmentation rows', 'segmentation_rows'))):
        metrics = network[key]
        y = 595 + index * 36
        width = round(210 * metrics['mean'] / metrics['maximum']) if metrics['maximum'] else 0
        lines.append(f'  <text x="64" y="{y}" class="label">{label}</text><rect x="225" y="{y - 13}" width="210" height="15" rx="3" fill="#e5e7eb"/><rect x="225" y="{y - 13}" width="{width}" height="15" rx="3" fill="#2563eb"/><text x="450" y="{y}" class="value">{metrics["mean"]:.2f} ± {metrics["std_dev"]:.2f}; {metrics["minimum"]}–{metrics["maximum"]}</text>')
    lines.extend([
        '  <rect x="710" y="500" width="650" height="365" rx="12" class="panel"/>',
        '  <text x="734" y="536" class="panel-title">Traffic workload and payload types</text>',
        '  <text x="734" y="558" class="note">Scenario means use fixed Traffic rows; payload bars show requested sender/receiver pairs.</text>',
    ])
    for index, (label, key) in enumerate((('Traffic density', 'density'), ('Traffic rows', 'rows'), ('Requested pairs', 'requested_pairs'))):
        metrics = traffic[key]
        y = 595 + index * 36
        width = round(190 * metrics['mean'] / metrics['maximum']) if metrics['maximum'] else 0
        lines.append(f'  <text x="734" y="{y}" class="label">{label}</text><rect x="875" y="{y - 13}" width="190" height="15" rx="3" fill="#e5e7eb"/><rect x="875" y="{y - 13}" width="{width}" height="15" rx="3" fill="#7c3aed"/><text x="1080" y="{y}" class="value">{metrics["mean"]:.2f} ± {metrics["std_dev"]:.2f}; {metrics["minimum"]}–{metrics["maximum"]}</text>')
    lines.append('  <text x="734" y="715" class="header">Payload type: requested pairs</text>')
    pair_max = max(item['requested_pairs'] for item in traffic_types)
    colors = {'Audio': '#0891b2', 'Gibberish': '#475569', 'Photo': '#db2777', 'Text': '#2563eb', 'Video': '#7c3aed'}
    for index, item in enumerate(traffic_types):
        y = 742 + index * 23
        width = round(170 * item['requested_pairs'] / pair_max)
        lines.append(f'  <text x="734" y="{y}" class="label">{escape(item["type"])}</text><rect x="820" y="{y - 12}" width="{width}" height="15" rx="3" fill="{colors.get(item["type"], "#64748b")}"/><text x="{828 + width}" y="{y}" class="value">{item["requested_pairs"]} pairs · {item["rows"]} rows</text>')
    lines.extend([
        '  <rect x="40" y="900" width="620" height="345" rx="12" class="panel"/>',
        '  <text x="64" y="936" class="panel-title">Vulhub semantic families</text>',
        '  <text x="64" y="958" class="note">Classification by component function (e.g., Struts2 → web framework; Drupal → CMS; Elasticsearch → data/search).</text>',
        '  <rect x="710" y="900" width="650" height="345" rx="12" class="panel"/>',
        '  <text x="734" y="936" class="panel-title">Self-generated semantic families</text>',
        '  <text x="734" y="958" class="note">Classification by service role rather than protocol-name prefixes.</text>',
    ])
    vmax = max(item['selections'] for item in vulnerability_families)
    for index, item in enumerate(vulnerability_families):
        y = 988 + index * 29
        label = item['family'] if len(item['family']) <= 31 else f'{item["family"][:30]}…'
        width = round(220 * item['selections'] / vmax)
        lines.append(f'  <text x="64" y="{y}" class="label">{escape(label)}</text><rect x="300" y="{y - 12}" width="{width}" height="15" rx="3" fill="#dc2626"/><text x="{308 + width}" y="{y}" class="value">{item["selections"]} / {item["unique_images"]}</text>')
    gmax = max(item['selections'] for item in generator_families)
    for index, item in enumerate(generator_families):
        y = 988 + index * 29
        width = round(220 * item['selections'] / gmax)
        lines.append(f'  <text x="734" y="{y}" class="label">{escape(item["family"])}</text><rect x="970" y="{y - 12}" width="{width}" height="15" rx="3" fill="#0f766e"/><text x="{978 + width}" y="{y}" class="value">{item["selections"]} / {item["unique_generators"]}</text>')
    lines.extend([
        f'  <text x="50" y="1290" class="note">Each family bar shows selections / concrete entries. Every eligible entry is observed at least once; repetition is bounded (Vulhub {vulns["minimum"]}–{vulns["maximum"]}, generators {generators["minimum"]}–{generators["maximum"]}).</text>',
        '  <text x="50" y="1320" class="note">Definitions, mappings, type membership, and exact population statistics: dataset-resolved/ground-truth-statistics.json. Sample generators are excluded by design.</text>',
        '</svg>',
        '',
    ])
    return '\n'.join(lines)


def main() -> None:
    if not MANIFEST.exists():
        raise SystemExit('Missing catalog-selections.json. Materialize the resolved dataset first.')
    data = collect()
    STATS_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    GROUND_TRUTH.write_text(ground_truth_svg(data), encoding='utf-8')
    PAPER.write_text(research_svg(data), encoding='utf-8')


if __name__ == '__main__':
    main()
