#!/usr/bin/env python3
"""Persist balanced, concrete catalog selections in ``dataset-resolved``.

Run ``generate_resolved_specs.py`` first to restore filter-based resolved
specifications, then run this script against the intended ScenarioForge
checkout.  The selected catalog snapshot is stored directly in each YAML file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, OrderedDict
from pathlib import Path

import yaml

from scenarioforge_eval.executor import Executor


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPOSITORY_ROOT / "dataset-resolved"
COVERAGE_PREFIX = '90-catalog-coverage-'


def _tie_break(seed: int, namespace: str, key: str) -> str:
    return hashlib.sha256(f"{seed}:{namespace}:{key}".encode()).hexdigest()


def _choose_balanced(
    candidates: list[dict],
    count: int,
    *,
    usage: Counter[str],
    key,
    seed: int,
    namespace: str,
    unique: bool,
) -> list[dict]:
    if count > len(candidates) and unique:
        raise ValueError(f"requested {count} unique entries from only {len(candidates)} eligible entries")
    selected = []
    available = list(candidates)
    for index in range(count):
        pool = available if unique else candidates
        choice = min(
            pool,
            key=lambda entry: (
                usage[key(entry)],
                _tie_break(seed, f"{namespace}:{index}", key(entry)),
            ),
        )
        selected.append(choice)
        usage[key(choice)] += 1
        if unique:
            available.remove(choice)
    return selected


def _write_yaml(path: Path, value: dict) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _is_sample_generator(entry: dict) -> bool:
    return 'sample' in str(entry.get('id') or '').lower() or 'sample' in str(entry.get('name') or '').lower()


def _coverage_spec(index: int, vulnerabilities: list[dict], generator: dict) -> dict:
    """Build a fixed, network-varied scenario that closes catalog coverage gaps."""
    seed = int.from_bytes(hashlib.sha256(f'catalog-coverage:{index}'.encode()).digest()[:4], 'big') & 0x7FFFFFFF
    traffic_profiles = (
        (0.35, [{'type': 'TCP', 'count': 1, 'factor': 1.0, 'pattern': 'periodic', 'rate_kbps': 32.0, 'period_s': 5.0, 'jitter_pct': 10.0, 'content_type': 'text'}]),
        (0.60, [
            {'type': 'TCP', 'count': 1, 'factor': 1.0, 'pattern': 'continuous', 'rate_kbps': 128.0, 'period_s': 2.0, 'jitter_pct': 15.0, 'content_type': 'photo'},
            {'type': 'UDP', 'count': 1, 'factor': 1.0, 'pattern': 'periodic', 'rate_kbps': 64.0, 'period_s': 5.0, 'jitter_pct': 25.0, 'content_type': 'audio'},
        ]),
        (0.85, [
            {'type': 'TCP', 'count': 2, 'factor': 1.0, 'pattern': 'continuous', 'rate_kbps': 512.0, 'period_s': 1.0, 'jitter_pct': 10.0, 'content_type': 'video'},
            {'type': 'UDP', 'count': 2, 'factor': 1.0, 'pattern': 'burst', 'rate_kbps': 256.0, 'period_s': 2.0, 'jitter_pct': 20.0, 'content_type': 'gibberish'},
        ]),
    )
    density, traffic_items = traffic_profiles[index % len(traffic_profiles)]
    segmentation_items = []
    if index % 2 == 0:
        segmentation_items = [
            {'type': 'Firewall', 'count': 1, 'factor': 1.0, 'pivot_enabled': index % 6 == 0},
            {'type': 'NAT', 'count': 1, 'factor': 1.0, 'pivot_enabled': index % 9 == 0},
        ]
    return {
        'name': f'dataset-catalog-coverage-{index:03d}',
        'iterations': 1,
        'seed': seed,
        'topology': {'routers': 1 + index % 3, 'hosts': 4 + index % 7},
        'services': {'enabled': True, 'count': 2 + index % 4, 'density': 1.0, 'include': ['SSH', 'HTTP'], 'exclude': []},
        'traffic': {'enabled': True, 'density': density, 'items': traffic_items},
        'vulns': {
            'enabled': True,
            'count': len(vulnerabilities),
            'specific': [{'name': item['name'], 'count': 1} for item in vulnerabilities],
        },
        'flag_node_generators': {
            'enabled': True,
            'count': 1,
            'specific': [{'id': generator['id'], 'name': generator['name'], 'count': 1}],
        },
        'flows': {'enabled': True, 'chain_length': 2 + index % 4, 'allow_duplicates': False, 'include_all_topology_pivots': bool(index % 6 == 0)},
        'segmentation': {'enabled': bool(segmentation_items), 'density': 0.35 + (index % 3) * 0.10, 'items': segmentation_items},
        'hitl': {'use_env': False},
        'validation': {'policy': 'strict'},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize exact balanced catalog selections")
    parser.add_argument("--sf-path", default="../scenarioforge", help="ScenarioForge checkout containing enabled catalogs")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Resolved spec directory")
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()
    for path in output_dir.glob(f'{COVERAGE_PREFIX}*.spec.yaml'):
        path.unlink()
    paths = sorted(path for path in output_dir.glob("*.spec.yaml") if not path.name.startswith(COVERAGE_PREFIX))
    if not paths:
        raise SystemExit(f"No resolved specs found in {output_dir}. Run generate_resolved_specs.py first.")

    catalog_executor = Executor({'name': 'catalog-materialization', 'seed': 0}, str(output_dir), args.sf_path)
    vulnerabilities = catalog_executor._load_eligible_vulnerability_catalog() or []
    generators = catalog_executor._load_eligible_flag_node_generator_catalog()
    active_generators = [entry for entry in generators if not _is_sample_generator(entry)]
    if not vulnerabilities or not active_generators:
        raise SystemExit("The configured ScenarioForge checkout has no eligible vulnerability or generator catalog.")

    vulnerability_usage: Counter[str] = Counter()
    generator_usage: Counter[str] = Counter()
    manifest = []

    for path in paths:
        spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        seed = int(spec['seed'])
        entry = {'file': path.name, 'name': spec['name'], 'vulnerabilities': [], 'generators': []}

        vuln_spec = spec.get('vulns') or {}
        if vuln_spec.get('enabled') and not vuln_spec.get('specific'):
            filters = vuln_spec.get('include') or []
            excluded = vuln_spec.get('exclude') or []
            eligible = [
                item for item in vulnerabilities
                if (not filters or catalog_executor._vulnerability_matches_filter(item, filters))
                and not catalog_executor._vulnerability_matches_filter(item, excluded)
            ]
            selected = _choose_balanced(
                eligible,
                int(vuln_spec['count']),
                usage=vulnerability_usage,
                key=lambda item: f"{item['name']}|{item['path']}",
                seed=seed,
                namespace='vulnerabilities',
                unique=True,
            )
            vuln_spec['specific'] = [
                {'name': item['name'], 'count': 1}
                for item in selected
            ]
            vuln_spec['count'] = len(selected)
            vuln_spec.pop('include', None)
            vuln_spec.pop('exclude', None)
            spec['vulns'] = vuln_spec
            entry['vulnerabilities'] = [item['name'] for item in selected]

        generator_spec = spec.get('flag_node_generators') or {}
        if generator_spec.get('enabled') and not generator_spec.get('specific'):
            filters = generator_spec.get('include') or []
            excluded = generator_spec.get('exclude') or []
            eligible = [
                item for item in active_generators
                if (not filters or catalog_executor._flag_node_generator_matches_filter(item, filters))
                and not catalog_executor._flag_node_generator_matches_filter(item, excluded)
            ]
            selected = _choose_balanced(
                eligible,
                int(generator_spec['count']),
                usage=generator_usage,
                key=lambda item: item['id'],
                seed=seed,
                namespace='flag-node-generators',
                unique=False,
            )
            selected_counts: OrderedDict[str, dict] = OrderedDict()
            for item in selected:
                selected_counts.setdefault(item['id'], {'id': item['id'], 'name': item['name'], 'count': 0})
                selected_counts[item['id']]['count'] += 1
            generator_spec['specific'] = list(selected_counts.values())
            generator_spec['count'] = len(selected)
            generator_spec.pop('include', None)
            generator_spec.pop('exclude', None)
            spec['flag_node_generators'] = generator_spec
            entry['generators'] = list(generator_spec['specific'])

        _write_yaml(path, spec)
        manifest.append(entry)

    selected_vulnerability_keys = set(vulnerability_usage)
    missing_vulnerabilities = [
        entry for entry in vulnerabilities
        if f"{entry['name']}|{entry['path']}" not in selected_vulnerability_keys
    ]
    for coverage_index, start in enumerate(range(0, len(missing_vulnerabilities), 3), start=1):
        chunk = missing_vulnerabilities[start:start + 3]
        generator = _choose_balanced(
            active_generators,
            1,
            usage=generator_usage,
            key=lambda item: item['id'],
            seed=coverage_index,
            namespace='coverage-generators',
            unique=False,
        )[0]
        coverage = _coverage_spec(coverage_index, chunk, generator)
        destination = output_dir / f'{COVERAGE_PREFIX}{coverage_index:03d}.spec.yaml'
        _write_yaml(destination, coverage)
        for vulnerability in chunk:
            vulnerability_usage[f"{vulnerability['name']}|{vulnerability['path']}"] += 1
        manifest.append({
            'file': destination.name,
            'name': coverage['name'],
            'vulnerabilities': [entry['name'] for entry in chunk],
            'generators': coverage['flag_node_generators']['specific'],
            'coverage_fixture': True,
        })

    summary = {
        'scenarioforge_path': str(Path(args.sf_path).resolve()),
        'base_resolved_spec_count': len(paths),
        'resolved_spec_count': len(manifest),
        'coverage_fixture_count': sum(bool(entry.get('coverage_fixture')) for entry in manifest),
        'eligible_vulnerability_count': len(vulnerabilities),
        'eligible_generator_count': len(active_generators),
        'vulnerabilities': dict(sorted(vulnerability_usage.items())),
        'flag_node_generators': dict(sorted(generator_usage.items())),
        'selections': manifest,
    }
    (output_dir / 'catalog-selections.json').write_text(
        json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    print(
        f"Materialized {sum(vulnerability_usage.values())} Vulhub and "
        f"{sum(generator_usage.values())} self-generated nodes across {len(manifest)} specs "
        f"({len(missing_vulnerabilities) // 3 + bool(len(missing_vulnerabilities) % 3)} coverage fixtures added)."
    )


if __name__ == '__main__':
    main()
