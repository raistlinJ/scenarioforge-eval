#!/usr/bin/env python3
"""Arm B: ask a frontier model for a CORE scenario with no scaffolding.

The experiment this belongs to compares two ways of authoring a CORE scenario:

  Arm A  ScenarioForge's `ai` phase -- tool-driven authoring over the MCP
         bridge, with a scenario schema, catalog search, validation and repair.
  Arm B  this script -- a frontier model told, in plain words, to produce a
         scenario that runs on CORE with a HITL interface, and nothing else.

Arm B deliberately does not go through ScenarioForge. Even `--ai-skip-bridge`
applies ScenarioForge's system prompt, scenario JSON schema and repair pass,
which is the scaffolding under test; routing Arm B through it would measure the
tool against itself.

The API key is read from OPENAI_API_KEY and is never logged or written to disk.
Nothing here belongs in the product: it is experiment tooling.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scenarioforge_eval.accuracy import (  # noqa: E402
    aggregate, score_facts, score_scenario, unreadable,
)
from scenarioforge_eval.armb_rungs import RUNG_LABELS, rung_prompt  # noqa: E402
from scenarioforge_eval.core_script_facts import observe_core_script  # noqa: E402
from scenarioforge_eval.core_xml_facts import observe_core_xml  # noqa: E402
from scenarioforge_eval.core_script_facts import extract_python as extract_python_source  # noqa: E402


SF_XML_BLOCK = re.compile(r'<\s*(Scenarios|ScenarioEditor)\b.*?</\s*\1\s*>', re.S)
CORE_XML_BLOCK = re.compile(r'<\s*(scenario|session)\b.*?</\s*\1\s*>', re.S)
XML_BLOCK = SF_XML_BLOCK
FENCED = re.compile(r'```(?:xml|yaml|json|python|ini)?\s*(.*?)```', re.S)


def classify(text: str) -> str:
    """What kind of artifact did the model actually return?"""
    body = text or ''
    if SF_XML_BLOCK.search(body):
        return 'scenarioforge-xml'
    if CORE_XML_BLOCK.search(body):
        return 'core-xml'
    if re.search(r'<\?xml|<\s*network\b', body, re.I):
        return 'other-xml'
    if re.search(r'^\s*(node|link)\b[^\n{]*\{', body, re.M):
        return 'core-imn'
    if re.search(r'from\s+core\b|import\s+core\b|core\.api', body):
        return 'core-python-api'
    if re.search(r'^\s*[{\[]', body.strip()):
        return 'json'
    if re.search(r'^\s*\w+:\s', body, re.M) and '---' in body:
        return 'yaml'
    return 'prose'


def extract_xml(text: str, pattern: re.Pattern) -> str | None:
    for candidate in [text] + FENCED.findall(text or ''):
        match = pattern.search(candidate or '')
        if not match:
            continue
        blob = match.group(0)
        try:
            ET.fromstring(blob)
        except ET.ParseError:
            continue
        return blob
    return None


def extract_scenario_xml(text: str) -> str | None:
    for candidate in [text] + FENCED.findall(text or ''):
        match = XML_BLOCK.search(candidate or '')
        if not match:
            continue
        blob = match.group(0)
        try:
            ET.fromstring(blob)
        except ET.ParseError:
            continue
        return blob
    return None


def call_openai(*, base_url: str, model: str, api_key: str, prompt: str,
                temperature: float | None, timeout: float) -> tuple[str, dict]:
    payload: dict = {'model': model, 'messages': [{'role': 'user', 'content': prompt}]}
    # Only sent when explicitly requested: some model families reject an
    # explicit temperature, and a 400 on every call would read as an arm
    # failure rather than a client mistake.
    if temperature is not None:
        payload['temperature'] = temperature
    response = requests.post(
        f'{base_url.rstrip("/")}/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json=payload,
        timeout=timeout,
    )
    if response.status_code >= 400:
        # Surface the provider's own message; never echo the request headers.
        detail = ''
        try:
            detail = str((response.json() or {}).get('error', {}).get('message') or '')
        except Exception:
            detail = response.text[:300]
        raise RuntimeError(f'HTTP {response.status_code}: {detail}')
    data = response.json()
    text = ((data.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
    return text, (data.get('usage') or {})


def load_specs(spec_dir: Path) -> list[dict]:
    specs = []
    for path in sorted(spec_dir.glob('*.spec.yaml')):
        doc = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        prompt = ((doc.get('ai') or {}).get('prompt') or doc.get('prompt') or '').strip()
        if not prompt:
            continue
        specs.append({
            'file': path.name,
            'name': doc.get('name') or path.stem,
            'description': prompt,
            'expected': doc.get('expected') or {},
        })
    return specs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--specs', type=Path, default=REPO_ROOT / 'ai-gen-dataset-resolved')
    ap.add_argument('--out', type=Path, default=None,
                    help='directory for per-spec results (required for a real run)')
    ap.add_argument('--model', default='',
                    help='exact API model id; use --list-models to find it')
    ap.add_argument('--base-url', default='https://api.openai.com/v1',
                    help='OpenAI-compatible base URL')
    ap.add_argument('--rung', type=int, default=0,
                    help='scaffolding level 0-5; see armb_rungs.RUNG_LABELS')
    ap.add_argument('--temperature', type=float, default=None,
                    help='only sent when given; omit for models that reject it')
    ap.add_argument('--timeout', type=float, default=180.0)
    ap.add_argument('--limit', type=int, default=0, help='only run the first N specs')
    ap.add_argument('--only', default='', help='substring filter on spec name')
    ap.add_argument('--skip-existing', action='store_true',
                    help='skip cases that already have a result.json in --out')
    ap.add_argument('--list-models', action='store_true',
                    help='print model ids this key can reach, then exit')
    ap.add_argument('--dry-run', action='store_true',
                    help='print the exact instruction per spec and exit without calling')
    args = ap.parse_args()

    if args.list_models:
        key = os.environ.get('OPENAI_API_KEY', '').strip()
        if not key:
            print('OPENAI_API_KEY is not set.', file=sys.stderr)
            return 2
        reply = requests.get(
            f'{args.base_url.rstrip("/")}/models',
            headers={'Authorization': f'Bearer {key}'},
            timeout=args.timeout,
        )
        if reply.status_code >= 400:
            print(f'HTTP {reply.status_code}: {reply.text[:300]}', file=sys.stderr)
            return 1
        for entry in sorted((reply.json() or {}).get('data') or [], key=lambda e: str(e.get('id'))):
            print(entry.get('id'))
        return 0

    if not args.model and not args.dry_run:
        print('--model is required. Run with --list-models to see the ids this '
              'key can reach.', file=sys.stderr)
        return 2
    if args.out is None and not args.dry_run:
        print('--out is required for a real run.', file=sys.stderr)
        return 2

    specs = load_specs(args.specs)
    if args.only:
        specs = [s for s in specs if args.only in s['name']]
    if args.limit:
        specs = specs[:args.limit]
    if args.skip_existing and args.out is not None:
        # Re-asking a case already answered costs tokens and buys nothing.
        before = len(specs)
        specs = [s for s in specs if not (args.out / s['name'] / 'result.json').is_file()]
        if before != len(specs):
            print(f'skipping {before - len(specs)} case(s) already present in {args.out}')
    if not specs:
        print(f'No specs with prompts found in {args.specs}', file=sys.stderr)
        return 1

    if args.dry_run:
        for spec in specs:
            print('=' * 70)
            print(f"# {spec['name']}  ({spec['file']})")
            print(rung_prompt(args.rung, spec['description']))
        print('=' * 70)
        print(f'{len(specs)} spec(s); no API calls made.')
        return 0

    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not api_key:
        print('OPENAI_API_KEY is not set. Export it in this shell; it is never '
              'read from a file or written to the run output.', file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    results, scores = [], []

    for index, spec in enumerate(specs, start=1):
        prompt = rung_prompt(args.rung, spec['description'])
        print(f"[{index}/{len(specs)}] {spec['name']} ... ", end='', flush=True)
        started = time.time()
        record: dict = {
            'name': spec['name'], 'file': spec['file'],
            'description': spec['description'], 'instruction': prompt,
            'model': args.model, 'expected': spec['expected'],
            'rung': args.rung, 'rung_label': RUNG_LABELS.get(args.rung, ''),
        }
        try:
            text, usage = call_openai(
                base_url=args.base_url, model=args.model, api_key=api_key,
                prompt=prompt, temperature=args.temperature, timeout=args.timeout,
            )
            record.update(ok=True, usage=usage, response=text)
        except Exception as exc:
            record.update(ok=False, error=str(exc), response='')
            print(f'FAILED ({exc})')
            results.append(record)
            continue
        record['duration_s'] = round(time.time() - started, 2)

        run_dir = args.out / spec['name']
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / 'response.txt').write_text(text, encoding='utf-8')

        record['format'] = classify(text)

        if record['format'] == 'core-xml':
            # CORE's own session format: graded from the file CORE itself reads.
            blob = extract_xml(text, CORE_XML_BLOCK)
            record['scenario_xml_found'] = bool(blob)
            if blob:
                xml_path = run_dir / 'scenario.core.xml'
                xml_path.write_text(blob, encoding='utf-8')
                facts = observe_core_xml(str(xml_path))
                score = (score_facts(spec['expected'], facts) if facts.get('parsed')
                         else unreadable(spec['expected'], 'core xml did not parse'))
                score['name'] = spec['name']
                scores.append(score)
                record['score'] = {k: v for k, v in score.items() if k != 'checks'}
                record['checks'] = score.get('checks')
                record['observed'] = facts
                print(f"{record['format']}  accuracy={score['accuracy']*100:.0f}%")
            else:
                scores.append(dict(unreadable(spec['expected'], 'core xml not extractable'),
                                   name=spec['name']))
                print(f"{record['format']}  (xml present but unparseable)")
            (run_dir / 'result.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
            results.append(record)
            continue

        xml_blob = extract_scenario_xml(text)
        record['scenario_xml_found'] = bool(xml_blob)

        if xml_blob:
            xml_path = run_dir / 'scenario.xml'
            xml_path.write_text(xml_blob, encoding='utf-8')
            score = score_scenario(spec['expected'], str(xml_path))
            score['name'] = spec['name']
            scores.append(score)
            record['score'] = {k: v for k, v in score.items() if k != 'checks'}
            record['checks'] = score.get('checks')
            print(f"{record['format']}  accuracy={score['accuracy']*100:.0f}%")
        elif record['format'] == 'core-python-api':
            # A CORE Python script is a legitimate answer to "a scenario that
            # runs on CORE"; refusing to read it would grade the grader.
            facts = observe_core_script(text)
            (run_dir / 'scenario.py').write_text(extract_python_source(text), encoding='utf-8')
            if facts.get('parsed'):
                score = score_facts(spec['expected'], facts)
            else:
                score = unreadable(spec['expected'], 'python did not parse')
            score['name'] = spec['name']
            scores.append(score)
            record['score'] = {k: v for k, v in score.items() if k != 'checks'}
            record['checks'] = score.get('checks')
            record['observed'] = facts
            print(f"{record['format']}  accuracy={score['accuracy']*100:.0f}%")
        else:
            # Still counted as a scenario that could not be graded, which is a
            # result about the arm, not a gap in the measurement.
            scores.append(dict(unreadable(spec['expected'], f"format={record['format']}"),
                               name=spec['name']))
            print(f"{record['format']}  (no gradeable scenario)")

        (run_dir / 'result.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
        results.append(record)

    summary = {
        'arm': 'B-freetext-frontier',
        'rung': args.rung,
        'rung_label': RUNG_LABELS.get(args.rung, ''),
        'model': args.model,
        'base_url': args.base_url,
        'specs': len(specs),
        'api_ok': sum(1 for r in results if r.get('ok')),
        'formats': {f: sum(1 for r in results if r.get('format') == f)
                    for f in sorted({r.get('format') for r in results if r.get('format')})},
        'scenario_xml_found': sum(1 for r in results if r.get('scenario_xml_found')),
        'accuracy': aggregate(scores),
    }
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print()
    print(json.dumps({k: v for k, v in summary.items() if k != 'accuracy'}, indent=2))
    acc = summary['accuracy']
    print(f"loadable={acc['loadable']}/{acc['scenarios']} "
          f"exact={acc['exact_match']} field_accuracy={acc['field_accuracy']*100:.1f}%")
    print(f'\nWrote {args.out}/summary.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
