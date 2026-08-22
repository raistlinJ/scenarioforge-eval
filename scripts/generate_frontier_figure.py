#!/usr/bin/env python3
"""Render the authoring-comparison figure as standalone SVG.

Hand-written SVG to match datasets/generate_ground_truth_figures.py: the repo
ships vector figures with no plotting dependency, which is also what a paper
wants. Static rather than interactive because the target medium is print.

Colors are the validated categorical slots 1-3 (blue/orange/aqua), which clear
every all-pairs gate. The status palette was rejected for the outcome bars: its
good/critical pair separates by only ΔE 4.1 under deuteranopia, and "built"
versus "rejected" is precisely the distinction a reader must not lose.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / 'frontier-experimentation' / 'metrics'
OUT = ROOT / 'frontier-experimentation' / 'authoring-comparison.svg'

BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
INK, MUTED, GRID, SURFACE = '#1f2937', '#6b7280', '#e5e7eb', '#fcfcfb'

RUNG_LABELS = {
    '1': 'bare', '2': '+structure', '3': '+node vocab',
    '4': '+segmentation', '5': '+images',
}


def load() -> tuple[dict, list[dict]]:
    summary = json.loads((METRICS / 'summary.json').read_text(encoding='utf-8'))
    rows = list(csv.DictReader((METRICS / 'per_case.csv').open(encoding='utf-8')))
    return summary['groups'], rows


def _axis(x0: int, y0: int, w: int, h: int, title: str, ylab: str) -> list[str]:
    out = [f'<text x="{x0}" y="{y0 - 34}" class="panel-title">{escape(title)}</text>',
           f'<text x="{x0}" y="{y0 - 14}" class="axis-label">{escape(ylab)}</text>']
    for pct in range(0, 101, 25):
        y = y0 + h - (pct / 100) * h
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + w}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x0 - 10}" y="{y + 4:.1f}" class="tick" text-anchor="end">{pct}%</text>')
    return out


def build(groups: dict, rows: list[dict]) -> str:
    rungs = [r for r in '12345' if f'B{r}' in groups]
    W, H = 1180, 905
    s: list[str] = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
    s.append('<title id="t">Scenario authoring: tool-scaffolded versus free-text frontier model</title>')
    s.append('<desc id="d">Buildability on CORE, outcome composition, and intent accuracy across '
             'five levels of prompt scaffolding, against a ScenarioForge reference.</desc>')
    s.append('<style>'
             f'text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:{INK}}}'
             '.title{font-size:26px;font-weight:700}'
             f'.subtitle{{font-size:13px;fill:{MUTED}}}'
             '.panel-title{font-size:17px;font-weight:700}'
             f'.axis-label{{font-size:11px;fill:{MUTED}}}'
             f'.tick{{font-size:11px;fill:{MUTED}}}'
             '.val{font-size:12px;font-weight:700}'
             '.lgd{font-size:12px}'
             f'.note{{font-size:11px;fill:{MUTED}}}'
             '</style>')
    s.append(f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>')
    s.append('<text x="48" y="46" class="title">Producing a runnable CORE scenario</text>')
    s.append('<text x="48" y="70" class="subtitle">'
             'ScenarioForge + Qwen3-27B versus gpt-5.6-sol given progressively more scaffolding · '
             f'n={groups["A"].get("full_n", "?")} cases per group</text>')

    # ---------- Panel 1: buildability ----------
    x0, y0, w, h = 90, 150, 470, 260
    s += _axis(x0, y0, w, h, '1 · Scenario builds on CORE', 'share of cases CORE instantiates')
    step = w / max(1, len(rungs) - 1)
    pts = []
    for i, r in enumerate(rungs):
        g = groups[f'B{r}']
        rate = g.get('full_buildable_rate') or 0
        x = x0 + i * step
        y = y0 + h - rate * h
        pts.append((x, y, rate, g))
    # Arm A reference: dashed, so the arms differ by line style as well as hue.
    ay = y0 + h - (groups['A']['full_buildable_rate']) * h
    s.append(f'<line x1="{x0}" y1="{ay:.1f}" x2="{x0 + w}" y2="{ay:.1f}" stroke="{ORANGE}" '
             f'stroke-width="2" stroke-dasharray="7 4"/>')
    s.append(f'<text x="{x0 + w}" y="{ay - 9:.1f}" class="val" fill="{ORANGE}" '
             f'text-anchor="end">ScenarioForge  100%</text>')
    s.append('<polyline fill="none" stroke="' + BLUE + '" stroke-width="2" points="'
             + ' '.join(f'{x:.1f},{y:.1f}' for x, y, _, _ in pts) + '"/>')
    for i, (x, y, rate, g) in enumerate(pts):
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{BLUE}" stroke="{SURFACE}" stroke-width="2"/>')
        s.append(f'<text x="{x:.1f}" y="{y - 13:.1f}" class="val" fill="{BLUE}" '
                 f'text-anchor="middle">{rate * 100:.0f}%</text>')
        s.append(f'<text x="{x:.1f}" y="{y0 + h + 20:.1f}" class="tick" text-anchor="middle">'
                 f'rung {rungs[i]}</text>')
        s.append(f'<text x="{x:.1f}" y="{y0 + h + 35:.1f}" class="tick" text-anchor="middle">'
                 f'{escape(RUNG_LABELS[rungs[i]])}</text>')

    # ---------- Panel 2: outcome composition ----------
    x2, y2, w2, h2 = 660, 150, 440, 260
    s += _axis(x2, y2, w2, h2, '2 · What CORE did with the file', 'share of cases')
    order = [('built', BLUE, 'built'), ('loaded-empty', AQUA, 'loaded, no nodes'),
             ('rejected', ORANGE, 'rejected')]
    bw = w2 / len(rungs) * 0.56
    gap = w2 / len(rungs)
    for i, r in enumerate(rungs):
        outcomes = json.loads(groups[f'B{r}'].get('load_outcomes') or '{}')
        total = sum(v for k, v in outcomes.items() if k != 'not-tested') or 1
        cx = x2 + i * gap + gap / 2
        cursor = y2 + h2
        for key, color, _ in order:
            n = outcomes.get(key, 0)
            if not n:
                continue
            seg = (n / total) * h2
            # 2px surface gap keeps adjacent segments from reading as one mass.
            s.append(f'<rect x="{cx - bw / 2:.1f}" y="{cursor - seg + 1:.1f}" width="{bw:.1f}" '
                     f'height="{max(0, seg - 2):.1f}" rx="3" fill="{color}"/>')
            if seg > 22:
                s.append(f'<text x="{cx:.1f}" y="{cursor - seg / 2 + 4:.1f}" class="val" '
                         f'fill="#ffffff" text-anchor="middle">{n}</text>')
            cursor -= seg
        s.append(f'<text x="{cx:.1f}" y="{y2 + h2 + 20:.1f}" class="tick" text-anchor="middle">rung {r}</text>')
    lx = x2
    for j, (_, color, label) in enumerate(order):
        s.append(f'<rect x="{lx}" y="{y2 + h2 + 40}" width="11" height="11" rx="2" fill="{color}"/>')
        s.append(f'<text x="{lx + 17}" y="{y2 + h2 + 50}" class="lgd">{escape(label)}</text>')
        lx += 30 + len(label) * 7

    # ---------- Panel 3: intent accuracy ----------
    x3, y3, w3, h3 = 90, 530, 470, 240
    s += _axis(x3, y3, w3, h3, '3 · Scenario matches the prompt', 'field accuracy, hitl excluded')
    pts3 = []
    for i, r in enumerate(rungs):
        acc = groups[f'B{r}'].get('sym_field_accuracy') or 0
        x = x3 + i * (w3 / max(1, len(rungs) - 1))
        pts3.append((x, y3 + h3 - acc * h3, acc))
    ay3 = y3 + h3 - (groups['A']['sym_field_accuracy']) * h3
    s.append(f'<line x1="{x3}" y1="{ay3:.1f}" x2="{x3 + w3}" y2="{ay3:.1f}" stroke="{ORANGE}" '
             f'stroke-width="2" stroke-dasharray="7 4"/>')
    s.append(f'<text x="{x3 + 6}" y="{ay3 + 18:.1f}" class="val" fill="{ORANGE}" text-anchor="start">'
             f'ScenarioForge  {groups["A"]["sym_field_accuracy"] * 100:.0f}%</text>')
    s.append('<polyline fill="none" stroke="' + BLUE + '" stroke-width="2" points="'
             + ' '.join(f'{x:.1f},{y:.1f}' for x, y, _ in pts3) + '"/>')
    for i, (x, y, acc) in enumerate(pts3):
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{BLUE}" stroke="{SURFACE}" stroke-width="2"/>')
        s.append(f'<text x="{x:.1f}" y="{y - 13:.1f}" class="val" fill="{BLUE}" text-anchor="middle">'
                 f'{acc * 100:.0f}%</text>')
        s.append(f'<text x="{x:.1f}" y="{y3 + h3 + 20:.1f}" class="tick" text-anchor="middle">rung {rungs[i]}</text>')

    # ---------- Panel 4: cost of scaffolding ----------
    x4, y4, w4, h4 = 660, 530, 440, 240
    s.append(f'<text x="{x4}" y="{y4 - 34}" class="panel-title">4 · Cost of scaffolding</text>')
    s.append(f'<text x="{x4}" y="{y4 - 14}" class="axis-label">mean tokens per scenario (total labelled)</text>')
    peak = max(int(groups[f'B{r}'].get('full_completion_tokens_mean') or 0)
               + int(groups[f'B{r}'].get('full_prompt_tokens_mean') or 0) for r in rungs) or 1
    maxc = peak * 1.22  # headroom so the tallest value label clears the caption
    bw4 = w4 / len(rungs) * 0.5
    for i, r in enumerate(rungs):
        g = groups[f'B{r}']
        comp = int(g.get('full_completion_tokens_mean') or 0)
        prom = int(g.get('full_prompt_tokens_mean') or 0)
        cx = x4 + i * (w4 / len(rungs)) + (w4 / len(rungs)) / 2
        ch = (comp / maxc) * h4
        ph = (prom / maxc) * h4
        s.append(f'<rect x="{cx - bw4 / 2:.1f}" y="{y4 + h4 - ch:.1f}" width="{bw4:.1f}" '
                 f'height="{ch:.1f}" rx="4" fill="{BLUE}"/>')
        s.append(f'<rect x="{cx - bw4 / 2:.1f}" y="{y4 + h4 - ch - ph - 2:.1f}" width="{bw4:.1f}" '
                 f'height="{max(2, ph):.1f}" rx="3" fill="{AQUA}"/>')
        s.append(f'<text x="{cx:.1f}" y="{y4 + h4 - ch - ph - 10:.1f}" class="val" '
                 f'text-anchor="middle">{comp + prom}</text>')
        s.append(f'<text x="{cx:.1f}" y="{y4 + h4 + 20:.1f}" class="tick" text-anchor="middle">rung {r}</text>')
        med = g.get('full_gen_median_s')
        s.append(f'<text x="{cx:.1f}" y="{y4 + h4 + 35:.1f}" class="tick" text-anchor="middle">{med}s</text>')
    s.append(f'<line x1="{x4}" y1="{y4 + h4}" x2="{x4 + w4}" y2="{y4 + h4}" stroke="{GRID}" stroke-width="1"/>')
    for j, (color, label) in enumerate(((BLUE, 'completion tokens'), (AQUA, 'prompt tokens (scaffold)'))):
        lxx = x4 + j * 190
        s.append(f'<rect x="{lxx}" y="{y4 + h4 + 46}" width="11" height="11" rx="2" fill="{color}"/>')
        s.append(f'<text x="{lxx + 17}" y="{y4 + h4 + 56}" class="lgd">{escape(label)}</text>')
    s.append(f'<text x="{x4}" y="{y4 + h4 + 78}" class="note">bottom row: median generation seconds</text>')

    s.append(f'<text x="48" y="{H - 26}" class="note">'
             'Built = CORE constructed the session definition via open_xml(start=False); not a runtime measure. '
             'hitl excluded from panel 3: only the frontier arm was instructed to include one.</text>')
    s.append('</svg>')
    return '\n'.join(s)


def main() -> int:
    groups, rows = load()
    OUT.write_text(build(groups, rows), encoding='utf-8')
    print(f'wrote {OUT} ({OUT.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
