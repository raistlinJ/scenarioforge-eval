#!/usr/bin/env python3
"""Side-by-side report for the scenario-authoring comparison.

Reads the two arms' outputs and grades both with the same instrument:

  Arm A  an evaluator run directory (ai-gen-dataset-out style), one
         subdirectory per spec containing the generated scenario.xml
  Arm B  the output of scripts/armb_freetext_openai.py

Both are scored against the `expected` block of the spec that produced them, so
neither arm is graded on a rubric derived from its own output. A case an arm
could not answer stays in that arm's denominator -- dropping it would flatter
whichever arm failed to produce anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scenarioforge_eval.accuracy import aggregate, score_scenario  # noqa: E402


def load_cases(spec_dir: Path) -> dict[str, dict]:
    cases = {}
    for path in sorted(spec_dir.glob('*.spec.yaml')):
        doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        name = doc.get('name')
        if name:
            cases[name] = {'expected': doc.get('expected') or {}, 'tier': doc.get('tier')}
    return cases


def collect(run_dir: Path, cases: dict[str, dict]) -> dict[str, dict]:
    """Score whatever each arm produced for each case."""
    scored: dict[str, dict] = {}
    for name, case in cases.items():
        xml = run_dir / name / 'scenario.xml'
        if not xml.is_file():
            # Absent output is a result, not a missing measurement.
            scored[name] = {'loadable': False, 'checks': {}, 'matched': 0,
                            'total': len(case['expected']), 'accuracy': 0.0,
                            'produced': False, 'name': name}
            continue
        score = score_scenario(case['expected'], str(xml))
        score.update(produced=True, name=name)
        scored[name] = score
    return scored


def _pct(value: float) -> str:
    return f'{value * 100:.0f}%'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--specs', type=Path, default=REPO_ROOT / 'comparison-dataset-resolved')
    ap.add_argument('--arm-a', type=Path, required=True, help='evaluator run output directory')
    ap.add_argument('--arm-b', type=Path, required=True, help='armb_freetext_openai output directory')
    ap.add_argument('--json-out', type=Path, default=None)
    args = ap.parse_args()

    cases = load_cases(args.specs)
    if not cases:
        print(f'No cases found in {args.specs}', file=sys.stderr)
        return 1

    a = collect(args.arm_a, cases)
    b = collect(args.arm_b, cases)

    width = max(len(n) for n in cases)
    print(f"{'case':<{width}}  {'tier':>4}  {'A':>6}  {'B':>6}   notes")
    for name, case in cases.items():
        sa, sb = a[name], b[name]
        notes = []
        if not sb['produced']:
            notes.append('B: no scenario')
        if not sa['produced']:
            notes.append('A: no scenario')
        print(f"{name:<{width}}  {str(case['tier'] or '-'):>4}  "
              f"{_pct(sa['accuracy']):>6}  {_pct(sb['accuracy']):>6}   {'; '.join(notes)}")

    agg_a, agg_b = aggregate(list(a.values())), aggregate(list(b.values()))
    print()
    print(f"{'metric':<24} {'Arm A':>10} {'Arm B':>10}")
    for label, key in (('scenarios', 'scenarios'), ('produced a scenario', 'loadable'),
                       ('exact match', 'exact_match'), ('checks matched', 'checks_matched'),
                       ('checks total', 'checks_total')):
        print(f'{label:<24} {agg_a[key]:>10} {agg_b[key]:>10}')
    print(f"{'field accuracy':<24} {_pct(agg_a['field_accuracy']):>10} {_pct(agg_b['field_accuracy']):>10}")

    print()
    print('by tier:')
    tiers = sorted({c['tier'] for c in cases.values() if c['tier'] is not None})
    for tier in tiers:
        names = [n for n, c in cases.items() if c['tier'] == tier]
        ta = aggregate([a[n] for n in names])
        tb = aggregate([b[n] for n in names])
        print(f"   tier {tier} (n={len(names)}):  A {_pct(ta['field_accuracy']):>5}"
              f"   B {_pct(tb['field_accuracy']):>5}")

    print()
    print('by field:')
    fields = sorted(set(agg_a['per_field']) | set(agg_b['per_field']))
    for field in fields:
        fa = agg_a['per_field'].get(field, {})
        fb = agg_b['per_field'].get(field, {})
        print(f"   {field:<22} A {fa.get('matched', 0)}/{fa.get('total', 0):<4}"
              f"  B {fb.get('matched', 0)}/{fb.get('total', 0)}")

    if args.json_out:
        args.json_out.write_text(json.dumps({
            'arm_a': {'run_dir': str(args.arm_a), 'aggregate': agg_a,
                      'per_case': {n: {k: v for k, v in s.items() if k != 'checks'} for n, s in a.items()}},
            'arm_b': {'run_dir': str(args.arm_b), 'aggregate': agg_b,
                      'per_case': {n: {k: v for k, v in s.items() if k != 'checks'} for n, s in b.items()}},
        }, indent=2), encoding='utf-8')
        print(f'\nWrote {args.json_out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
