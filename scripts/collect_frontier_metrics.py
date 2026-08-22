#!/usr/bin/env python3
"""Assemble every measurement from the scenario-authoring comparison.

Writes machine-readable tables under frontier-experimentation/ so figures and
paper text are generated from one audited source rather than from numbers
copied out of terminal scrollback.

Two asymmetries are recorded rather than smoothed over, because both would
otherwise silently favour one arm:

* HITL. Arm B is told to include a hardware-in-the-loop interface in its
  instruction; Arm A receives only the scenario description, because
  ScenarioForge takes HITL from spec configuration rather than the prompt.
  Scoring `hitl` therefore measures a requirement only one arm was given, so
  every accuracy figure is emitted twice -- with and without that field.

* Vocabulary gating. `vulnerabilities` and `segmentation` have no expression in
  a bare CORE XML until rungs 4 and 5 supply the terms, so low scores there at
  low rungs are a property of the instruction, not of the model.

Re-runnable at any time; partial sweeps are reported as far as they got.
"""

from __future__ import annotations

import csv
import json
import re
import statistics as st
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

from scenarioforge_eval.accuracy import score_facts, unreadable  # noqa: E402
from scenarioforge_eval.accuracy import observe_scenario  # noqa: E402
from scenarioforge_eval.core_script_facts import observe_core_script  # noqa: E402
from scenarioforge_eval.core_xml_facts import observe_core_xml  # noqa: E402
from scripts.armb_freetext_openai import CORE_XML_BLOCK, classify, extract_xml  # noqa: E402

OUT = REPO_ROOT / 'frontier-experimentation'
METRICS = OUT / 'metrics'
SPECS = REPO_ROOT / 'comparison-dataset-resolved'
ARM_A = REPO_ROOT / 'comparison-out' / 'arm-a'
ARM_A_RETRY = REPO_ROOT / 'comparison-out' / 'arm-a-retry'
ARM_B = REPO_ROOT / 'armb-out'
SCRATCH = Path('/private/tmp/claude-501/-Users-jcacosta-Documents-GitHub-scenarioforge-eval/'
               '29ef6767-4dc8-4804-a3d9-2eb4b0b02da5/scratchpad')

BUILT_RE = re.compile(r'Topology built \(routers=(\d+) hosts=(\d+)\)')
# Fields only one arm was asked for; excluded from the symmetric headline.
ASYMMETRIC_FIELDS = ('hitl',)


def load_cases() -> dict[str, dict]:
    cases = {}
    for path in sorted(SPECS.glob('*.spec.yaml')):
        doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        if doc.get('name'):
            cases[doc['name']] = {'expected': doc.get('expected') or {},
                                  'tier': doc.get('tier'),
                                  'prompt': (doc.get('ai') or {}).get('prompt', '')}
    return cases


def _symmetric(expected: dict) -> dict:
    return {k: v for k, v in expected.items() if k not in ASYMMETRIC_FIELDS}


def _row_from_score(score: dict) -> dict:
    return {
        'matched': score.get('matched', 0),
        'total': score.get('total', 0),
        'accuracy': round(score.get('accuracy', 0.0), 4),
        'exact': bool(score.get('exact')),
    }


def collect_arm_a(cases: dict) -> list[dict]:
    rows = []
    for name, case in cases.items():
        for base in (ARM_A_RETRY, ARM_A):          # retry wins when present
            result_path = base / f'{name}_result.json'
            if result_path.is_file():
                break
        else:
            continue
        result = json.loads(result_path.read_text(encoding='utf-8'))
        run_dir = base / name
        xml = run_dir / 'scenario.xml'

        facts = observe_scenario(str(xml)) if xml.is_file() else None
        full = score_facts(case['expected'], facts) if facts else unreadable(case['expected'], 'no xml')
        sym = score_facts(_symmetric(case['expected']), facts) if facts else unreadable(_symmetric(case['expected']), 'no xml')

        built_r = built_h = None
        topo_log = run_dir / 'topo.log'
        if topo_log.is_file():
            found = BUILT_RE.findall(topo_log.read_text(encoding='utf-8', errors='ignore'))
            if found:
                built_r, built_h = int(found[-1][0]), int(found[-1][1])

        phases = ((result.get('metrics') or {}).get('phases') or {})
        ai_phase = phases.get('ai') or {}
        topo_phase = phases.get('topo') or {}
        ai_meta = (result.get('metadata') or {}).get('ai_generation') or {}
        resources = ai_phase.get('resources') or {}
        rows.append({
            'arm': 'A', 'rung': '', 'case': name, 'tier': case['tier'],
            'format': 'scenarioforge-xml',
            **{f'full_{k}': v for k, v in _row_from_score(full).items()},
            **{f'sym_{k}': v for k, v in _row_from_score(sym).items()},
            'built': bool(result.get('stages', {}).get('topology') == 'PASS'),
            'built_nodes': (built_r + built_h) if built_r is not None else '',
            'built_routers': built_r if built_r is not None else '',
            'built_hosts': built_h if built_h is not None else '',
            'gen_seconds': round(float(ai_phase.get('duration_s') or 0), 2),
            'build_seconds': round(float(topo_phase.get('duration_s') or 0), 2),
            'total_seconds': round(float((result.get('metrics', {}).get('run') or {}).get('duration_s') or 0), 2),
            'started_at': ai_phase.get('started_at', ''),
            'ended_at': ai_phase.get('ended_at', ''),
            'client_cpu_s': round(float(resources.get('cpu_user_s') or 0)
                                  + float(resources.get('cpu_system_s') or 0), 2),
            'client_max_rss_bytes': resources.get('max_rss_bytes', ''),
            'attempts': ai_meta.get('attempts', ''),
            'tokens_source': 'unavailable (provider usage not surfaced by the ai phase)',
            'prompt_tokens': '', 'completion_tokens': '', 'reasoning_tokens': '',
            'checks': json.dumps({f: c['ok'] for f, c in (full.get('checks') or {}).items()}),
        })
    return rows


def collect_arm_b(cases: dict) -> list[dict]:
    rows = []
    for rung_dir in sorted(ARM_B.glob('rung*')):
        rung = rung_dir.name.replace('rung', '')
        load_path = SCRATCH / f'rung{rung}-load.json'
        load = {}
        if load_path.is_file():
            load = {r['case']: r for r in json.loads(load_path.read_text(encoding='utf-8'))}
        for case_dir in sorted(p for p in rung_dir.iterdir() if p.is_dir()):
            name = case_dir.name
            case = cases.get(name)
            if not case:
                continue
            result_path = case_dir / 'result.json'
            result = json.loads(result_path.read_text(encoding='utf-8')) if result_path.is_file() else {}
            response = case_dir / 'response.txt'
            text = response.read_text(encoding='utf-8') if response.is_file() else ''
            fmt = classify(text) if text else 'none'

            if fmt in ('core-xml', 'other-xml'):
                blob = extract_xml(text, CORE_XML_BLOCK)
                if blob:
                    xml_path = case_dir / 'scenario.core.xml'
                    xml_path.write_text(blob, encoding='utf-8')
                    facts = observe_core_xml(str(xml_path))
                else:
                    facts = None
            elif fmt == 'core-python-api':
                facts = observe_core_script(text)
            else:
                facts = None
            usable = bool(facts and facts.get('parsed'))

            full = score_facts(case['expected'], facts) if usable else unreadable(case['expected'], fmt)
            sym = score_facts(_symmetric(case['expected']), facts) if usable else unreadable(_symmetric(case['expected']), fmt)

            entry = load.get(name, {})
            nodes = entry.get('nodes_created')
            if not entry:
                outcome = 'not-tested'
            elif entry.get('loaded') and (nodes or 0) > 0:
                outcome = 'built'
            elif entry.get('loaded'):
                outcome = 'loaded-empty'
            else:
                outcome = 'rejected'

            usage = result.get('usage') or {}
            details = usage.get('completion_tokens_details') or {}
            rows.append({
                'arm': 'B', 'rung': rung, 'case': name, 'tier': case['tier'], 'format': fmt,
                **{f'full_{k}': v for k, v in _row_from_score(full).items()},
                **{f'sym_{k}': v for k, v in _row_from_score(sym).items()},
                'built': outcome == 'built',
                'built_nodes': nodes if nodes is not None else '',
                'built_routers': '', 'built_hosts': '',
                'load_outcome': outcome,
                'gen_seconds': result.get('duration_s', ''),
                'build_seconds': '',
                'total_seconds': result.get('duration_s', ''),
                'started_at': '', 'ended_at': '',
                'client_cpu_s': '', 'client_max_rss_bytes': '',
                'attempts': 1,
                'tokens_source': 'openai api usage',
                'prompt_tokens': usage.get('prompt_tokens', ''),
                'completion_tokens': usage.get('completion_tokens', ''),
                'reasoning_tokens': details.get('reasoning_tokens', ''),
                'checks': json.dumps({f: c['ok'] for f, c in (full.get('checks') or {}).items()}),
            })
    return rows


def _agg(rows: list[dict], prefix: str) -> dict:
    if not rows:
        return {}
    matched = sum(r[f'{prefix}_matched'] for r in rows)
    total = sum(r[f'{prefix}_total'] for r in rows)
    secs = [float(r['gen_seconds']) for r in rows if str(r.get('gen_seconds') or '') not in ('', '0', '0.0')]
    comp = [int(r['completion_tokens']) for r in rows if str(r.get('completion_tokens') or '') != '']
    reas = [int(r['reasoning_tokens']) for r in rows if str(r.get('reasoning_tokens') or '') != '']
    tested = [r for r in rows if r.get('load_outcome', 'n/a') != 'not-tested']
    built = sum(1 for r in tested if r['built'])
    out = {
        'n': len(rows),
        'exact': sum(1 for r in rows if r[f'{prefix}_exact']),
        'checks_matched': matched, 'checks_total': total,
        'field_accuracy': round(matched / total, 4) if total else 0.0,
        'build_tested': len(tested),
        'built': built,
        'buildable_rate': round(built / len(tested), 4) if tested else '',
    }
    if secs:
        out.update(gen_mean_s=round(st.mean(secs), 1), gen_median_s=round(st.median(secs), 1),
                   gen_min_s=round(min(secs), 1), gen_max_s=round(max(secs), 1))
    if comp:
        out.update(completion_tokens_mean=round(st.mean(comp)), completion_tokens_total=sum(comp))
        pairs = [(int(r['completion_tokens']), float(r['gen_seconds']))
                 for r in rows
                 if str(r.get('completion_tokens') or '') != '' and str(r.get('gen_seconds') or '') != '']
        rates = [c / s for c, s in pairs if s > 0]
        if rates:
            out['completion_tokens_per_s_mean'] = round(st.mean(rates), 1)
    prompts = [int(r['prompt_tokens']) for r in rows if str(r.get('prompt_tokens') or '') != '']
    if prompts:
        out.update(prompt_tokens_mean=round(st.mean(prompts)), prompt_tokens_total=sum(prompts))
    builds = [float(r['build_seconds']) for r in rows
              if str(r.get('build_seconds') or '') not in ('', '0', '0.0')]
    if builds:
        out.update(build_mean_s=round(st.mean(builds), 1), build_median_s=round(st.median(builds), 1))
    if reas:
        out.update(reasoning_tokens_mean=round(st.mean(reas)),
                   reasoning_fraction=round(sum(reas) / sum(comp), 3) if comp else '')
    return out


def main() -> int:
    METRICS.mkdir(parents=True, exist_ok=True)
    cases = load_cases()
    rows = collect_arm_a(cases) + collect_arm_b(cases)
    if not rows:
        print('no results found', file=sys.stderr)
        return 1

    fields = list(rows[0].keys())
    for r in rows:
        for f in fields:
            r.setdefault(f, '')
    per_case = METRICS / 'per_case.csv'
    with per_case.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(f"{r['arm']}{r['rung']}", []).append(r)

    per_rung_rows = []
    for key, group in sorted(groups.items()):
        entry = {'group': key, 'arm': group[0]['arm'], 'rung': group[0]['rung']}
        entry.update({f'full_{k}': v for k, v in _agg(group, 'full').items()})
        entry.update({f'sym_{k}': v for k, v in _agg(group, 'sym').items()})
        fmts: dict[str, int] = {}
        outcomes: dict[str, int] = {}
        for r in group:
            fmts[r['format']] = fmts.get(r['format'], 0) + 1
            if r.get('load_outcome'):
                outcomes[r['load_outcome']] = outcomes.get(r['load_outcome'], 0) + 1
        entry['formats'] = json.dumps(fmts)
        entry['load_outcomes'] = json.dumps(outcomes)
        per_rung_rows.append(entry)

    per_rung = METRICS / 'per_rung.csv'
    rung_fields = sorted({k for r in per_rung_rows for k in r})
    rung_fields = ['group', 'arm', 'rung'] + [f for f in rung_fields if f not in ('group', 'arm', 'rung')]
    with per_rung.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=rung_fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(per_rung_rows)

    # per-field accuracy, which is where vocabulary gating shows up
    field_rows = []
    for key, group in sorted(groups.items()):
        tally: dict[str, list[int]] = {}
        for r in group:
            for field, ok in json.loads(r['checks'] or '{}').items():
                bucket = tally.setdefault(field, [0, 0])
                bucket[1] += 1
                bucket[0] += 1 if ok else 0
        for field, (hit, n) in sorted(tally.items()):
            field_rows.append({'group': key, 'field': field, 'matched': hit, 'total': n,
                               'accuracy': round(hit / n, 4) if n else 0.0})
    with (METRICS / 'per_field.csv').open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['group', 'field', 'matched', 'total', 'accuracy'])
        writer.writeheader()
        writer.writerows(field_rows)

    summary = {
        'cases': len(cases),
        'asymmetric_fields_excluded_from_sym': list(ASYMMETRIC_FIELDS),
        'groups': {r['group']: r for r in per_rung_rows},
    }
    (METRICS / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print(f'{len(rows)} case-rows across {len(groups)} groups -> {METRICS}')
    print(f"{'group':<7}{'n':>4}{'exact':>7}{'acc':>8}{'exact*':>8}{'acc*':>8}"
          f"{'built':>10}{'build%':>8}{'med s':>8}")
    for r in per_rung_rows:
        rate = r.get('full_buildable_rate', '')
        rate_txt = f"{rate*100:.0f}%" if isinstance(rate, (int, float)) else 'n/t'
        print(f"{r['group']:<7}{r.get('full_n',0):>4}{r.get('full_exact',0):>7}"
              f"{r.get('full_field_accuracy',0)*100:>7.1f}%{r.get('sym_exact',0):>8}"
              f"{r.get('sym_field_accuracy',0)*100:>7.1f}%"
              f"{str(r.get('full_built',0)) + '/' + str(r.get('full_build_tested',0)):>10}"
              f"{rate_txt:>8}{r.get('full_gen_median_s','-'):>8}")
    print('\n  * = excluding `hitl`, which only Arm B was instructed to include')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
