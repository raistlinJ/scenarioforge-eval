#!/usr/bin/env python3
"""Re-score saved Arm B responses without calling the provider again.

Grading a new output format means changing the grader, and the grader must
never be the reason to re-bill a run. Every response is kept verbatim, so
scores are recomputed from disk.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

from scenarioforge_eval.accuracy import aggregate, score_facts, unreadable  # noqa: E402
from scenarioforge_eval.core_script_facts import observe_core_script  # noqa: E402
from scenarioforge_eval.core_xml_facts import observe_core_xml  # noqa: E402
from scripts.armb_freetext_openai import CORE_XML_BLOCK, classify, extract_xml  # noqa: E402


def regrade(run_dir: Path, cases: dict[str, dict]) -> list[dict]:
    scored = []
    for case_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        response = case_dir / 'response.txt'
        if not response.is_file():
            continue
        name = case_dir.name
        expected = (cases.get(name) or {}).get('expected') or {}
        text = response.read_text(encoding='utf-8')
        fmt = classify(text)

        if fmt in ('core-xml', 'other-xml'):
            blob = extract_xml(text, CORE_XML_BLOCK)
            if blob:
                xml_path = case_dir / 'scenario.core.xml'
                xml_path.write_text(blob, encoding='utf-8')
                facts = observe_core_xml(str(xml_path))
                score = (score_facts(expected, facts) if facts.get('parsed')
                         else unreadable(expected, 'core xml did not parse'))
            else:
                score = unreadable(expected, f'{fmt}: no extractable scenario')
        elif fmt == 'core-python-api':
            facts = observe_core_script(text)
            score = (score_facts(expected, facts) if facts.get('parsed')
                     else unreadable(expected, 'python did not parse'))
        else:
            score = unreadable(expected, f'format={fmt}')

        score.update(name=name, format=fmt, tier=(cases.get(name) or {}).get('tier'))
        scored.append(score)
    return scored


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('run_dirs', nargs='+', type=Path)
    ap.add_argument('--specs', type=Path, default=REPO_ROOT / 'comparison-dataset-resolved')
    ap.add_argument('--json-out', type=Path, default=None)
    args = ap.parse_args()

    cases = {}
    for path in sorted(args.specs.glob('*.spec.yaml')):
        doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        if doc.get('name'):
            cases[doc['name']] = {'expected': doc.get('expected') or {}, 'tier': doc.get('tier')}

    everything = {}
    for run_dir in args.run_dirs:
        if not run_dir.is_dir():
            continue
        scored = regrade(run_dir, cases)
        agg = aggregate(scored)
        formats = {}
        for s in scored:
            formats[s['format']] = formats.get(s['format'], 0) + 1
        print(f'--- {run_dir}  (n={agg["scenarios"]})')
        for s in scored:
            misses = [f for f, c in (s.get('checks') or {}).items() if not c.get('ok')]
            print(f"   {s['name']:<30} {s['format']:<16} {s['accuracy']*100:>4.0f}%"
                  f"  {'miss: ' + ','.join(misses) if misses else ''}")
        print(f"   formats: {formats}")
        print(f"   exact={agg['exact_match']}/{agg['scenarios']}  "
              f"field_accuracy={agg['field_accuracy']*100:.1f}%")
        everything[str(run_dir)] = {'aggregate': agg, 'formats': formats,
                                    'cases': [{k: v for k, v in s.items() if k != 'checks'} for s in scored]}
    if args.json_out:
        args.json_out.write_text(json.dumps(everything, indent=2), encoding='utf-8')
        print(f'wrote {args.json_out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
