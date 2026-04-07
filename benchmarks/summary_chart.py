#!/usr/bin/env python3
"""Generate a benchmark summary chart for the README snapshot.

This intentionally emits a plain SVG so the repo does not need a plotting
dependency just to keep a summary figure up to date.

Usage:
    python3 benchmarks/summary_chart.py
    python3 benchmarks/summary_chart.py --output benchmarks/summary.svg
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from xml.sax.saxutils import escape

BACKENDS = (
    {
        'name': 'TexSoup',
        'successes': 10,
        'total': 10,
        'mean_ms': 937,
        'label': '937 ms',
        'color': '#1f7a5a',
    },
    {
        'name': 'plasTeX',
        'successes': 3,
        'total': 10,
        'mean_ms': 1661,
        'label': '1,661 ms',
        'color': '#6e7c91',
    },
    {
        'name': 'LaTeXML',
        'successes': 9,
        'total': 10,
        'mean_ms': 151521,
        'label': '151,521 ms',
        'color': '#c06b3e',
    },
)

WIDTH = 980
HEIGHT = 420
PADDING = 36
TITLE_Y = 32
SUBTITLE_Y = 54
PANEL_GAP = 28
PANEL_TOP = 90
PANEL_HEIGHT = 270
PANEL_WIDTH = (WIDTH - PADDING * 2 - PANEL_GAP) / 2
BAR_WIDTH = 74
BAR_GAP = 42
AXIS_COLOR = '#d5d8df'
GRID_COLOR = '#eceef2'
TEXT_COLOR = '#1c1f24'
MUTED = '#5d6674'
FONT = 'ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('benchmarks/summary.svg'),
        help='Where to write the SVG chart.',
    )
    return parser.parse_args()


def svg_text(x, y, text, size=14, weight='400', anchor='start', fill=TEXT_COLOR):
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="{FONT}" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">'
        f'{escape(text)}</text>'
    )


def svg_rect(x, y, width, height, fill, rx=8, stroke='none', dash=None):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}"{dash_attr} />'
    )


def panel_origin(index):
    return PADDING + index * (PANEL_WIDTH + PANEL_GAP), PANEL_TOP


def draw_panel_frame(elements, x, y, title, subtitle):
    elements.append(svg_rect(x, y, PANEL_WIDTH, PANEL_HEIGHT, '#fafbfc', rx=14, stroke='#e4e7ec'))
    elements.append(svg_text(x + 18, y + 28, title, size=16, weight='600'))
    elements.append(svg_text(x + 18, y + 48, subtitle, size=12, fill=MUTED))


def draw_correctness_panel(elements):
    x, y = panel_origin(0)
    draw_panel_frame(elements, x, y, 'Correctness', 'Success rate on the 10-paper arXiv set; higher is better')
    axis_left = x + 54
    axis_right = x + PANEL_WIDTH - 16
    axis_top = y + 82
    axis_bottom = y + PANEL_HEIGHT - 52
    axis_height = axis_bottom - axis_top
    max_success = 10

    for tick in range(0, max_success + 1, 2):
        tick_y = axis_bottom - axis_height * (tick / max_success)
        elements.append(f'<line x1="{axis_left}" y1="{tick_y}" x2="{axis_right}" y2="{tick_y}" stroke="{GRID_COLOR}" />')
        elements.append(svg_text(axis_left - 10, tick_y + 4, str(tick), size=11, anchor='end', fill=MUTED))

    elements.append(f'<line x1="{axis_left}" y1="{axis_top}" x2="{axis_left}" y2="{axis_bottom}" stroke="{AXIS_COLOR}" />')
    elements.append(f'<line x1="{axis_left}" y1="{axis_bottom}" x2="{axis_right}" y2="{axis_bottom}" stroke="{AXIS_COLOR}" />')

    total_width = len(BACKENDS) * BAR_WIDTH + (len(BACKENDS) - 1) * BAR_GAP
    start_x = axis_left + (axis_right - axis_left - total_width) / 2
    for index, backend in enumerate(BACKENDS):
        bar_x = start_x + index * (BAR_WIDTH + BAR_GAP)
        bar_height = axis_height * (backend['successes'] / backend['total'])
        bar_y = axis_bottom - bar_height
        elements.append(svg_rect(bar_x, bar_y, BAR_WIDTH, bar_height, backend['color'], rx=10))
        elements.append(svg_text(bar_x + BAR_WIDTH / 2, bar_y - 10, f"{backend['successes']}/{backend['total']}",
                                 size=12, weight='600', anchor='middle'))
        elements.append(svg_text(bar_x + BAR_WIDTH / 2, axis_bottom + 20, backend['name'],
                                 size=11, anchor='middle', fill=MUTED))


def draw_speed_panel(elements):
    x, y = panel_origin(1)
    draw_panel_frame(elements, x, y, 'Speed', 'Mean runtime on the same 10-paper set; lower is better (log scale)')
    axis_left = x + 54
    axis_right = x + PANEL_WIDTH - 16
    axis_top = y + 82
    axis_bottom = y + PANEL_HEIGHT - 52
    axis_height = axis_bottom - axis_top
    log_min = math.log10(100)
    log_max = math.log10(1_000_000)

    ticks = (100, 1_000, 10_000, 100_000, 1_000_000)
    for tick in ticks:
        fraction = (math.log10(tick) - log_min) / (log_max - log_min)
        tick_y = axis_bottom - axis_height * fraction
        elements.append(f'<line x1="{axis_left}" y1="{tick_y}" x2="{axis_right}" y2="{tick_y}" stroke="{GRID_COLOR}" />')
        label = '1M ms' if tick == 1_000_000 else (f'{tick // 1000}k ms' if tick >= 1000 else f'{tick} ms')
        elements.append(svg_text(axis_left - 10, tick_y + 4, label, size=11, anchor='end', fill=MUTED))

    elements.append(f'<line x1="{axis_left}" y1="{axis_top}" x2="{axis_left}" y2="{axis_bottom}" stroke="{AXIS_COLOR}" />')
    elements.append(f'<line x1="{axis_left}" y1="{axis_bottom}" x2="{axis_right}" y2="{axis_bottom}" stroke="{AXIS_COLOR}" />')

    total_width = len(BACKENDS) * BAR_WIDTH + (len(BACKENDS) - 1) * BAR_GAP
    start_x = axis_left + (axis_right - axis_left - total_width) / 2
    for index, backend in enumerate(BACKENDS):
        bar_x = start_x + index * (BAR_WIDTH + BAR_GAP)
        fraction = (math.log10(backend['mean_ms']) - log_min) / (log_max - log_min)
        bar_height = max(axis_height * fraction, 4)
        bar_y = axis_bottom - bar_height
        elements.append(svg_rect(bar_x, bar_y, BAR_WIDTH, bar_height, backend['color'], rx=10))
        elements.append(svg_text(bar_x + BAR_WIDTH / 2, bar_y - 10, backend['label'],
                                 size=11, weight='600', anchor='middle'))
        elements.append(svg_text(bar_x + BAR_WIDTH / 2, axis_bottom + 20, backend['name'],
                                 size=11, anchor='middle', fill=MUTED))


def build_svg():
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" fill="none">',
        svg_rect(0, 0, WIDTH, HEIGHT, '#ffffff', rx=0),
        svg_text(PADDING, TITLE_Y, 'TexSoup Benchmark Snapshot', size=24, weight='700'),
        svg_text(PADDING, SUBTITLE_Y,
                 'AI/ML arXiv set from benchmarks/README.md, measured locally on April 5, 2026',
                 size=13, fill=MUTED),
    ]
    draw_correctness_panel(elements)
    draw_speed_panel(elements)
    elements.append('</svg>')
    return '\n'.join(elements)


def main():
    args = parse_args()
    args.output.write_text(build_svg())
    print(args.output)


if __name__ == '__main__':
    main()
