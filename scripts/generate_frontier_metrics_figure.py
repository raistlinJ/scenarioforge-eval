#!/usr/bin/env python3
"""Second figure: where the gap comes from, rather than how big it is.

Four views the headline figure cannot carry: which requested elements each arm
actually produces, how buildability varies with task difficulty and with
scenario size, and how the two arms' latency distributions differ in shape.

Sequential blue for the accuracy matrix (magnitude), validated categorical
slots for the categorical panels. Every cell and bar is labelled, which is also
the relief required for the lighter steps.
"""

from __future__ import annotations

import collections
import csv
import glob
import statistics as st
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / 'frontier-experimentation' / 'metrics'
OUT = ROOT / 'frontier-experimentation' / 'metrics-detail.svg'

BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
INK, MUTED, GRID, SURFACE = '#1f2937', '#6b7280', '#e5e7eb', '#fcfcfb'
# blue ramp, light -> dark (sequential = one hue)
RAMP = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#2a78d6', '#1c5cab', '#104281']
GROUPS = ['A', 'B1', 'B2', 'B3', 'B4', 'B5']
FIELD_ORDER = ['routers', 'hosts', 'services', 'segmentation', 'vulnerabilities', 'traffic', 'hitl']


def ramp_for(v: float) -> str:
    return RAMP[min(len(RAMP) - 1, int(v * len(RAMP)))]


def load():
    rows = list(csv.DictReader((METRICS / 'per_case.csv').open(encoding='utf-8')))
    fields = list(csv.DictReader((METRICS / 'per_field.csv').open(encoding='utf-8')))
    specs = {}
    for p in glob.glob(str(ROOT / 'comparison-dataset-resolved' / '*.spec.yaml')):
        d = yaml.safe_load(open(p, encoding='utf-8'))
        specs[d['name']] = d.get('expected') or {}
    size = {n: (e.get('routers', 0) + e.get('hosts', 0)) for n, e in specs.items()}
    return rows, fields, size


def build(rows, fieldrows, size) -> str:
    W, H = 1180, 750
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         'role="img" aria-labelledby="t d">',
         '<title id="t">Where the authoring gap comes from</title>',
         '<desc id="d">Per-element accuracy, buildability by difficulty tier and by scenario size, '
         'and generation latency distributions.</desc>',
         '<style>'
         f'text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:{INK}}}'
         '.title{font-size:26px;font-weight:700}'
         f'.subtitle{{font-size:13px;fill:{MUTED}}}'
         '.panel-title{font-size:17px;font-weight:700}'
         f'.axis-label{{font-size:11px;fill:{MUTED}}}'
         f'.tick{{font-size:11px;fill:{MUTED}}}'
         '.val{font-size:11px;font-weight:700}'
         '.cell{font-size:11px;font-weight:700}'
         '.lgd{font-size:12px}'
         f'.note{{font-size:11px;fill:{MUTED}}}'
         '</style>',
         f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>',
         '<text x="48" y="46" class="title">Where the authoring gap comes from</text>',
         '<text x="48" y="70" class="subtitle">n=50 cases per group · '
         'A = ScenarioForge + Qwen3-27B, B1-B5 = gpt-5.6-sol by scaffolding rung</text>']

    # ---- Panel 1: per-element accuracy matrix ----
    x0, y0 = 190, 150
    cw, ch = 82, 34
    s.append(f'<text x="48" y="{y0 - 34}" class="panel-title">1 · Which requested elements appear</text>')
    s.append(f'<text x="48" y="{y0 - 14}" class="axis-label">field accuracy; darker is higher</text>')
    acc = collections.defaultdict(dict)
    for r in fieldrows:
        acc[r['field']][r['group']] = float(r['accuracy'])
    for j, g in enumerate(GROUPS):
        s.append(f'<text x="{x0 + j * cw + cw / 2:.0f}" y="{y0 - 6}" class="tick" '
                 f'text-anchor="middle">{g}</text>')
    for i, f in enumerate(FIELD_ORDER):
        yy = y0 + i * ch
        s.append(f'<text x="{x0 - 12}" y="{yy + ch / 2 + 4:.0f}" class="tick" text-anchor="end">{escape(f)}</text>')
        for j, g in enumerate(GROUPS):
            if g not in acc.get(f, {}):
                continue
            v = acc[f][g]
            xx = x0 + j * cw
            s.append(f'<rect x="{xx + 1}" y="{yy + 1}" width="{cw - 3}" height="{ch - 3}" rx="3" '
                     f'fill="{ramp_for(v)}"/>')
            s.append(f'<text x="{xx + cw / 2:.0f}" y="{yy + ch / 2 + 4:.0f}" class="cell" '
                     f'text-anchor="middle" fill="{"#ffffff" if v >= 0.57 else INK}">{v * 100:.0f}</text>')
    note_y = y0 + len(FIELD_ORDER) * ch + 22
    s.append(f'<text x="48" y="{note_y}" class="note">'
             'traffic and hitl were never in any rung’s vocabulary; vulnerabilities and segmentation '
             'climb exactly where rungs 4-5 introduce their terms.</text>')

    # ---- Panel 2: buildability by tier ----
    x2, y2, w2, h2 = 740, 150, 360, 200
    s.append(f'<text x="{x2}" y="{y2 - 34}" class="panel-title">2 · Buildability by difficulty tier</text>')
    s.append(f'<text x="{x2}" y="{y2 - 14}" class="axis-label">share of cases CORE instantiates</text>')
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        if r.get('load_outcome') == 'not-tested':
            continue
        by[r['arm'] + r['rung']][r['tier']].append(r['built'] == 'True')
    tiers = sorted({r['tier'] for r in rows if r['tier']})
    series = [('A', ORANGE, 'ScenarioForge'), ('B5', BLUE, 'frontier, rung 5'), ('B1', AQUA, 'frontier, rung 1')]
    gapw = w2 / len(tiers)
    bw = gapw / (len(series) + 2.2)
    for pct in (0, 50, 100):
        yy = y2 + h2 - pct / 100 * h2
        s.append(f'<line x1="{x2}" y1="{yy}" x2="{x2 + w2}" y2="{yy}" stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{x2 - 8}" y="{yy + 4}" class="tick" text-anchor="end">{pct}%</text>')
    for ti, t in enumerate(tiers):
        for si, (g, color, _) in enumerate(series):
            vals = by[g].get(t) or []
            if not vals:
                continue
            rate = sum(vals) / len(vals)
            xx = x2 + ti * gapw + 6 + si * (bw + 2)
            bh = rate * h2
            s.append(f'<rect x="{xx:.1f}" y="{y2 + h2 - bh:.1f}" width="{bw:.1f}" '
                     f'height="{max(1, bh):.1f}" rx="3" fill="{color}"/>')
            if rate > 0:
                s.append(f'<text x="{xx + bw / 2:.1f}" y="{y2 + h2 - bh - 5:.1f}" class="val" '
                         f'text-anchor="middle">{rate * 100:.0f}</text>')
        s.append(f'<text x="{x2 + ti * gapw + gapw / 2:.0f}" y="{y2 + h2 + 18}" class="tick" '
                 f'text-anchor="middle">T{t}</text>')
    lx = x2
    for _, color, label in series:
        s.append(f'<rect x="{lx}" y="{y2 + h2 + 32}" width="11" height="11" rx="2" fill="{color}"/>')
        s.append(f'<text x="{lx + 16}" y="{y2 + h2 + 42}" class="lgd">{escape(label)}</text>')
        lx += 34 + len(label) * 6.6

    # ---- Panel 3: buildability by scenario size ----
    x3, y3, w3, h3 = 740, 470, 360, 180
    s.append(f'<text x="{x3}" y="{y3 - 34}" class="panel-title">4 · Buildability by scenario size</text>')
    s.append(f'<text x="{x3}" y="{y3 - 14}" class="axis-label">requested routers + hosts</text>')

    def band(n):
        return '3-8' if n <= 8 else ('9-14' if n <= 14 else '15-20')
    bands = ['3-8', '9-14', '15-20']
    bs = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        if r.get('load_outcome') == 'not-tested':
            continue
        bs[r['arm'] + r['rung']][band(size.get(r['case'], 0))].append(r['built'] == 'True')
    gapw3 = w3 / len(bands)
    bw3 = gapw3 / (len(series) + 2.2)
    for pct in (0, 50, 100):
        yy = y3 + h3 - pct / 100 * h3
        s.append(f'<line x1="{x3}" y1="{yy}" x2="{x3 + w3}" y2="{yy}" stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{x3 - 8}" y="{yy + 4}" class="tick" text-anchor="end">{pct}%</text>')
    for bi, b in enumerate(bands):
        for si, (g, color, _) in enumerate(series):
            vals = bs[g].get(b) or []
            if not vals:
                continue
            rate = sum(vals) / len(vals)
            xx = x3 + bi * gapw3 + 6 + si * (bw3 + 2)
            bh = rate * h3
            s.append(f'<rect x="{xx:.1f}" y="{y3 + h3 - bh:.1f}" width="{bw3:.1f}" '
                     f'height="{max(1, bh):.1f}" rx="3" fill="{color}"/>')
            if rate > 0:
                s.append(f'<text x="{xx + bw3 / 2:.1f}" y="{y3 + h3 - bh - 5:.1f}" class="val" '
                         f'text-anchor="middle">{rate * 100:.0f}</text>')
        n = len(bs['A'].get(b) or [])
        s.append(f'<text x="{x3 + bi * gapw3 + gapw3 / 2:.0f}" y="{y3 + h3 + 18}" class="tick" '
                 f'text-anchor="middle">{b} nodes (n={n})</text>')

    # ---- Panel 4: latency distribution ----
    x4, y4, w4, h4 = 190, 470, 410, 180
    s.append(f'<text x="48" y="{y4 - 34}" class="panel-title">3 · Generation latency</text>')
    s.append(f'<text x="48" y="{y4 - 14}" class="axis-label">seconds per scenario · box = p25-p75, line = median</text>')
    lat = {}
    for g, color, label in series:
        v = sorted(float(r['gen_seconds']) for r in rows
                   if r['arm'] + r['rung'] == g and str(r.get('gen_seconds') or '') not in ('', '0', '0.0'))
        if v:
            lat[g] = (v, color, label)
    hi = max(v[-1] for v, _, _ in lat.values())
    for secs in (0, 200, 400, 600, 800):
        if secs > hi * 1.05:
            continue
        xx = x4 + (secs / (hi * 1.05)) * w4
        s.append(f'<line x1="{xx:.0f}" y1="{y4}" x2="{xx:.0f}" y2="{y4 + h4 - 26}" stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{xx:.0f}" y="{y4 + h4 - 8}" class="tick" text-anchor="middle">{secs}s</text>')
    rowh = (h4 - 40) / max(1, len(lat))
    for i, (g, (v, color, label)) in enumerate(lat.items()):
        yy = y4 + 14 + i * rowh
        def px(val):
            return x4 + (val / (hi * 1.05)) * w4
        p25, med, p75 = v[len(v) // 4], st.median(v), v[3 * len(v) // 4]
        s.append(f'<line x1="{px(v[0]):.1f}" y1="{yy + rowh / 2:.1f}" x2="{px(v[-1]):.1f}" '
                 f'y2="{yy + rowh / 2:.1f}" stroke="{color}" stroke-width="2"/>')
        s.append(f'<rect x="{px(p25):.1f}" y="{yy + rowh / 2 - 9:.1f}" width="{max(2, px(p75) - px(p25)):.1f}" '
                 f'height="18" rx="3" fill="{color}" opacity="0.35"/>')
        s.append(f'<line x1="{px(med):.1f}" y1="{yy + rowh / 2 - 10:.1f}" x2="{px(med):.1f}" '
                 f'y2="{yy + rowh / 2 + 10:.1f}" stroke="{color}" stroke-width="3"/>')
        s.append(f'<text x="{x4 - 8}" y="{yy + rowh / 2 + 4:.1f}" class="tick" text-anchor="end">{escape(label)}</text>')
        s.append(f'<text x="{px(v[-1]) + 6:.1f}" y="{yy + rowh / 2 + 4:.1f}" class="val" '
                 f'fill="{color}">{med:.0f}s med · {v[-1]:.0f}s max</text>')

    s.append(f'<text x="48" y="{H - 24}" class="note">'
             'Built = CORE constructed the session definition via open_xml(start=False). '
             'Arm A latency is the ai phase only, excluding the CORE build.</text>')
    s.append('</svg>')
    return '\n'.join(s)


def main() -> int:
    rows, fieldrows, size = load()
    OUT.write_text(build(rows, fieldrows, size), encoding='utf-8')
    print(f'wrote {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
