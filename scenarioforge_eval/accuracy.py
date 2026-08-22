"""Score a generated scenario against the intent its prompt declared.

The evaluator already reports whether a scenario *ran*. That is necessary but
not sufficient for comparing scenario authoring methods: a generator can emit a
scenario that builds perfectly and is not the scenario that was asked for. This
module supplies the missing axis by comparing an `expected` block, written
alongside the prompt, against facts read back out of the generated XML.

Expectations are machine-readable on purpose. Re-parsing the English prompt at
scoring time would make the grader agree with whatever the generator did to the
same words, which is precisely the failure mode a grader exists to catch.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


HOST_ROLES = ('Docker', 'PC', 'Workstation', 'Server', 'Host')

# Fields an `expected` block may declare. Anything absent is simply not scored,
# so a prompt that says nothing about traffic is not penalised for its absence.
SCORED_FIELDS = (
    'routers',
    'hosts',
    'services',
    'vulnerabilities',
    'vulnerability_names',
    'flag_node_generators',
    'generator_names',
    'segmentation',
    'traffic',
    'hitl',
)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _sections(root: ET.Element) -> dict[str, list[ET.Element]]:
    found: dict[str, list[ET.Element]] = {}
    for section in root.iter('section'):
        found.setdefault(str(section.get('name') or ''), []).extend(list(section))
    return found


def observe_scenario(xml_path: str) -> dict[str, Any]:
    """Read the gradeable facts out of a generated scenario XML."""
    root = ET.parse(xml_path).getroot()
    sections = _sections(root)

    routers = sum(_int(i.get('v_count')) for i in sections.get('Routing', []))
    ordinary_hosts = sum(
        _int(i.get('v_count'))
        for i in sections.get('Node Information', [])
        if str(i.get('selected')) in HOST_ROLES
    )

    generators = sections.get('Flag Node Generators', [])
    vulnerabilities = sections.get('Vulnerabilities', [])
    vulnerability_hosts = sum(max(1, _int(i.get('v_count'), 1)) for i in vulnerabilities)
    generator_hosts = sum(max(1, _int(i.get('v_count'), 1)) for i in generators)
    hitl = root.find('.//HardwareInLoop')

    return {
        'routers': routers,
        # Vulnerabilities and flag-node generators each materialize a host in
        # CORE.  Count them here as the direct arm's CORE-XML reader does;
        # otherwise a request such as "four hosts, one of them vulnerable"
        # is incorrectly scored as only three hosts in the ScenarioForge arm.
        'hosts': ordinary_hosts + vulnerability_hosts + generator_hosts,
        # A row without an explicit count still contributes one node.
        'services': sorted({str(i.get('selected')) for i in sections.get('Services', []) if i.get('selected')}),
        'vulnerabilities': vulnerability_hosts,
        'vulnerability_names': sorted({
            str(i.get('v_name') or i.get('name') or '') for i in vulnerabilities
        } - {''}),
        'flag_node_generators': generator_hosts,
        'generator_names': sorted({str(i.get('g_name') or '') for i in generators} - {''}),
        'generator_ids': sorted({str(i.get('g_id') or '') for i in generators} - {''}),
        'segmentation': sorted({str(i.get('selected')) for i in sections.get('Segmentation', []) if i.get('selected')}),
        'traffic': bool(sections.get('Traffic')),
        'hitl': bool(hitl is not None and str(hitl.get('enabled') or '').lower() == 'true'),
    }


def _compare(field: str, expected: Any, observed: Any) -> tuple[bool, str]:
    if field in ('services', 'segmentation'):
        want = {str(v).strip().upper() for v in (expected or [])}
        got = {str(v).strip().upper() for v in (observed or [])}
        missing = sorted(want - got)
        return (not missing), (f'missing {missing}' if missing else 'ok')
    if field in ('vulnerability_names', 'generator_names'):
        want = {str(v).strip().lower() for v in (expected or [])}
        got = {str(v).strip().lower() for v in (observed or [])}
        missing = sorted(want - got)
        return (not missing), (f'missing {missing}' if missing else 'ok')
    if field in ('traffic', 'hitl'):
        return bool(expected) == bool(observed), f'expected {bool(expected)}, got {bool(observed)}'
    want_n, got_n = _int(expected), _int(observed)
    return want_n == got_n, f'expected {want_n}, got {got_n}'


def score_facts(expected: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    """Grade already-extracted facts, whatever format they were read from.

    Both arms are scored through here so neither is graded on a rubric shaped
    by its own output format.
    """
    checks: dict[str, Any] = {}
    for field in _declared(expected):
        ok, detail = _compare(field, expected.get(field), observed.get(field))
        checks[field] = {'ok': ok, 'expected': expected.get(field),
                         'observed': observed.get(field), 'detail': detail}
    matched = sum(1 for c in checks.values() if c['ok'])
    total = len(checks)
    return {
        'loadable': True,
        'observed': observed,
        'checks': checks,
        'matched': matched,
        'total': total,
        'accuracy': (matched / total) if total else 0.0,
        'exact': matched == total and total > 0,
    }


def unreadable(expected: dict[str, Any], error: str) -> dict[str, Any]:
    """Score for output that could not be read at all.

    Kept in the denominator: dropping it would flatter whichever arm failed to
    produce anything usable.
    """
    return {'loadable': False, 'error': error, 'checks': {}, 'matched': 0,
            'total': len(_declared(expected)), 'accuracy': 0.0, 'exact': False}


def score_scenario(expected: dict[str, Any], xml_path: str) -> dict[str, Any]:
    """Grade one generated ScenarioForge XML against its declared intent."""
    try:
        observed = observe_scenario(xml_path)
    except (OSError, ET.ParseError) as exc:
        return unreadable(expected, f'{type(exc).__name__}: {exc}')

    checks: dict[str, Any] = {}
    for field in _declared(expected):
        ok, detail = _compare(field, expected.get(field), observed.get(field))
        checks[field] = {'ok': ok, 'expected': expected.get(field), 'observed': observed.get(field), 'detail': detail}

    matched = sum(1 for c in checks.values() if c['ok'])
    total = len(checks)
    return {
        'loadable': True,
        'observed': observed,
        'checks': checks,
        'matched': matched,
        'total': total,
        'accuracy': (matched / total) if total else 0.0,
        'exact': matched == total and total > 0,
    }


def _declared(expected: dict[str, Any]) -> list[str]:
    return [f for f in SCORED_FIELDS if isinstance(expected, dict) and f in expected]


def aggregate(scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll per-scenario scores into the numbers an experiment arm reports."""
    total_checks = sum(s.get('total', 0) for s in scores)
    matched = sum(s.get('matched', 0) for s in scores)
    field_totals: dict[str, list[int]] = {}
    for s in scores:
        for field, check in (s.get('checks') or {}).items():
            bucket = field_totals.setdefault(field, [0, 0])
            bucket[1] += 1
            if check.get('ok'):
                bucket[0] += 1
    return {
        'scenarios': len(scores),
        'loadable': sum(1 for s in scores if s.get('loadable')),
        'exact_match': sum(1 for s in scores if s.get('exact')),
        'checks_matched': matched,
        'checks_total': total_checks,
        'field_accuracy': (matched / total_checks) if total_checks else 0.0,
        'per_field': {
            field: {'matched': hit, 'total': n, 'accuracy': (hit / n) if n else 0.0}
            for field, (hit, n) in sorted(field_totals.items())
        },
    }
