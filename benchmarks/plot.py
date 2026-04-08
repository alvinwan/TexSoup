#!/usr/bin/env python3
"""Generate a 50-paper robustness/speed chart for the benchmarks README.

This emits a plain SVG so the chart can be regenerated without adding plotting
dependencies to the repository.

Usage:
    python3 benchmarks/plot.py
    python3 benchmarks/plot.py --output benchmarks/summary.svg
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from xml.sax.saxutils import escape

BACKENDS = (
    {
        'name': 'TexSoup',
        'successes': 50,
        'timeouts': 0,
        'other_failures': 0,
        'total': 50,
        'mean_ms': 668,
        'label': '668 ms',
        'color': '#1f7a5a',
    },
    {
        'name': 'plasTeX',
        'successes': 11,
        'timeouts': 9,
        'other_failures': 30,
        'total': 50,
        'mean_ms': 829,
        'label': '829 ms',
        'color': '#6e7c91',
    },
    {
        'name': 'LaTeXML',
        'successes': 29,
        'timeouts': 14,
        'other_failures': 7,
        'total': 50,
        'mean_ms': 5231,
        'label': '5,231 ms',
        'color': '#c06b3e',
    },
)

WIDTH = 980
HEIGHT = 360
X_PADDING = 0
Y_PADDING = 12
PANEL_GAP = 16
PANEL_TOP = 12
PANEL_HEIGHT = HEIGHT - PANEL_TOP - Y_PADDING
PANEL_WIDTH = (WIDTH - X_PADDING * 2 - PANEL_GAP) / 2
BAR_WIDTH = 74
BAR_GAP = 42
ROUND = 10
FONT = 'ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'

BG = 'var(--bg)'
PANEL = 'var(--panel)'
PANEL_STROKE = 'var(--panel-stroke)'
GRID = 'var(--grid)'
AXIS = 'var(--axis)'
TEXT = 'var(--text)'
MUTED = 'var(--muted)'
LEGEND_SUCCESS = 'var(--legend-success)'
LEGEND_TIMEOUT_FILL = 'var(--legend-timeout-fill)'
LEGEND_TIMEOUT_STROKE = 'var(--legend-timeout-stroke)'
LEGEND_OTHER_FILL = 'var(--legend-other-fill)'
LEGEND_OTHER_STROKE = 'var(--legend-other-stroke)'
SEGMENT_TIMEOUT_FILL = 'var(--segment-timeout-fill)'
SEGMENT_OTHER_FILL = 'var(--segment-other-fill)'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('benchmarks/summary.svg'),
        help='Where to write the SVG chart.',
    )
    return parser.parse_args()


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip('#')
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return '#' + ''.join(f'{max(0, min(255, round(channel))):02x}' for channel in rgb)


def mix(color: str, amount: float) -> str:
    r, g, b = hex_to_rgb(color)
    return rgb_to_hex((
        r + (255 - r) * amount,
        g + (255 - g) * amount,
        b + (255 - b) * amount,
    ))


def svg_text(x, y, text, size=14, weight='400', anchor='start', fill=TEXT):
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="{FONT}" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">'
        f'{escape(text)}</text>'
    )


def svg_rect(x, y, width, height, fill, rx=8, stroke='none', stroke_width=1, dash=None, clip_path=None):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
    clip_attr = f' clip-path="url(#{clip_path})"' if clip_path else ''
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"'
        f'{dash_attr}{clip_attr} />'
    )


def panel_origin(index):
    return X_PADDING + index * (PANEL_WIDTH + PANEL_GAP), PANEL_TOP


def draw_panel_frame(elements, x, y, title, subtitle):
    elements.append(svg_rect(x, y, PANEL_WIDTH, PANEL_HEIGHT, PANEL, rx=14, stroke=PANEL_STROKE))
    elements.append(svg_text(x + 18, y + 28, title, size=16, weight='600'))
    elements.append(svg_text(x + 18, y + 48, subtitle, size=12, fill=MUTED))


def draw_legend(elements, x, y):
    items = (
        ('Success', 'success'),
        ('Timed out', 'timeout'),
        ('Other failure', 'other'),
    )
    cursor = x
    for label, kind in items:
        if kind == 'success':
            elements.append(svg_rect(cursor, y - 10, 12, 12, LEGEND_SUCCESS, rx=3, stroke=LEGEND_SUCCESS))
        elif kind == 'timeout':
            elements.append(svg_rect(cursor, y - 10, 12, 12, LEGEND_TIMEOUT_FILL, rx=3,
                                     stroke=LEGEND_TIMEOUT_STROKE, dash='4 3'))
            elements.append(svg_rect(cursor, y - 10, 12, 12, 'url(#legend-timeout-pattern)', rx=3))
        else:
            elements.append(svg_rect(cursor, y - 10, 12, 12, LEGEND_OTHER_FILL, rx=3,
                                     stroke=LEGEND_OTHER_STROKE, dash='4 3'))
        elements.append(svg_text(cursor + 18, y, label, size=11, fill=MUTED))
        cursor += 18 + len(label) * 6.6 + 20


def draw_count_label(elements, x, y, value, fill=TEXT):
    elements.append(svg_text(x, y, str(value), size=11, weight='600', anchor='middle', fill=fill))


def draw_correctness_panel(elements):
    x, y = panel_origin(0)
    draw_panel_frame(elements, x, y, 'Robustness', 'Stacked outcomes on 50 AI/ML arXiv papers')
    draw_legend(elements, x + 18, y + 68)

    axis_left = x + 54
    axis_right = x + PANEL_WIDTH - 16
    axis_top = y + 102
    axis_bottom = y + PANEL_HEIGHT - 52
    axis_height = axis_bottom - axis_top

    for tick in range(0, 51, 10):
        tick_y = axis_bottom - axis_height * (tick / 50)
        elements.append(f'<line x1="{axis_left}" y1="{tick_y}" x2="{axis_right}" y2="{tick_y}" stroke="{GRID}" />')
        elements.append(svg_text(axis_left - 10, tick_y + 4, str(tick), size=11, anchor='end', fill=MUTED))

    elements.append(f'<line x1="{axis_left}" y1="{axis_top}" x2="{axis_left}" y2="{axis_bottom}" stroke="{AXIS}" />')
    elements.append(f'<line x1="{axis_left}" y1="{axis_bottom}" x2="{axis_right}" y2="{axis_bottom}" stroke="{AXIS}" />')

    total_width = len(BACKENDS) * BAR_WIDTH + (len(BACKENDS) - 1) * BAR_GAP
    start_x = axis_left + (axis_right - axis_left - total_width) / 2

    for index, backend in enumerate(BACKENDS):
        bar_x = start_x + index * (BAR_WIDTH + BAR_GAP)
        clip_id = f'clip-{backend["name"]}'
        elements.append(
            f'<clipPath id="{clip_id}"><rect x="{bar_x}" y="{axis_top}" width="{BAR_WIDTH}" '
            f'height="{axis_height}" rx="{ROUND}" /></clipPath>'
        )

        centers = {}
        current_top = axis_top
        segments = (
            ('other', backend['other_failures']),
            ('timeout', backend['timeouts']),
            ('success', backend['successes']),
        )
        for kind, value in segments:
            if value <= 0:
                continue
            height = axis_height * (value / backend['total'])
            y0 = current_top
            centers[kind] = y0 + height / 2
            if kind == 'success':
                elements.append(svg_rect(bar_x, y0, BAR_WIDTH, height, backend['color'], rx=0, clip_path=clip_id))
                draw_count_label(elements, bar_x + BAR_WIDTH / 2, centers[kind] + 4, value, fill='#ffffff')
            elif kind == 'timeout':
                timeout_stroke = mix(backend['color'], 0.45)
                elements.append(svg_rect(bar_x, y0, BAR_WIDTH, height, SEGMENT_TIMEOUT_FILL, rx=0, clip_path=clip_id))
                elements.append(svg_rect(bar_x, y0, BAR_WIDTH, height, f'url(#timeout-pattern-{backend["name"]})',
                                         rx=0, clip_path=clip_id))
                elements.append(svg_rect(bar_x, y0, BAR_WIDTH, height, 'none', rx=0,
                                         stroke=timeout_stroke, stroke_width=1.5, dash='6 4', clip_path=clip_id))
                draw_count_label(elements, bar_x + BAR_WIDTH / 2, centers[kind] + 4, value)
            else:
                other_stroke = mix(backend['color'], 0.68)
                elements.append(svg_rect(bar_x, y0, BAR_WIDTH, height, SEGMENT_OTHER_FILL, rx=0, clip_path=clip_id))
                elements.append(svg_rect(bar_x, y0, BAR_WIDTH, height, 'none', rx=0,
                                         stroke=other_stroke, stroke_width=1.5, dash='6 4', clip_path=clip_id))
                draw_count_label(elements, bar_x + BAR_WIDTH / 2, centers[kind] + 4, value)
            current_top += height

        elements.append(svg_rect(bar_x, axis_top, BAR_WIDTH, axis_height, 'none', rx=ROUND,
                                 stroke=backend['color'], stroke_width=1.5))
        elements.append(svg_text(bar_x + BAR_WIDTH / 2, axis_bottom + 20, backend['name'],
                                 size=11, anchor='middle', fill=MUTED))


def draw_speed_panel(elements):
    x, y = panel_origin(1)
    draw_panel_frame(elements, x, y, 'Speed', 'Mean runtime on successful papers only (linear scale)')

    axis_left = x + 54
    axis_right = x + PANEL_WIDTH - 16
    axis_top = y + 82
    axis_bottom = y + PANEL_HEIGHT - 52
    axis_height = axis_bottom - axis_top
    max_ms = max(backend['mean_ms'] for backend in BACKENDS)
    axis_max = math.ceil(max_ms / 1000) * 1000
    tick_step = max(1000, axis_max // 3)

    for tick in range(0, axis_max + 1, tick_step):
        fraction = tick / axis_max if axis_max else 0
        tick_y = axis_bottom - axis_height * fraction
        elements.append(f'<line x1="{axis_left}" y1="{tick_y}" x2="{axis_right}" y2="{tick_y}" stroke="{GRID}" />')
        if tick == 0:
            label = '0'
        elif tick >= 1000 and tick % 1000 == 0:
            label = f'{tick // 1000}k ms'
        elif tick >= 1000:
            label = f'{tick / 1000:.1f}k ms'
        else:
            label = f'{tick} ms'
        elements.append(svg_text(axis_left - 10, tick_y + 4, label, size=11, anchor='end', fill=MUTED))

    elements.append(f'<line x1="{axis_left}" y1="{axis_top}" x2="{axis_left}" y2="{axis_bottom}" stroke="{AXIS}" />')
    elements.append(f'<line x1="{axis_left}" y1="{axis_bottom}" x2="{axis_right}" y2="{axis_bottom}" stroke="{AXIS}" />')

    total_width = len(BACKENDS) * BAR_WIDTH + (len(BACKENDS) - 1) * BAR_GAP
    start_x = axis_left + (axis_right - axis_left - total_width) / 2
    for index, backend in enumerate(BACKENDS):
        bar_x = start_x + index * (BAR_WIDTH + BAR_GAP)
        fraction = backend['mean_ms'] / axis_max if axis_max else 0
        bar_height = max(axis_height * fraction, 4)
        bar_y = axis_bottom - bar_height
        elements.append(svg_rect(bar_x, bar_y, BAR_WIDTH, bar_height, backend['color'], rx=10))
        elements.append(svg_text(bar_x + BAR_WIDTH / 2, bar_y - 10, backend['label'],
                                 size=11, weight='600', anchor='middle'))
        elements.append(svg_text(bar_x + BAR_WIDTH / 2, axis_bottom + 20, backend['name'],
                                 size=11, anchor='middle', fill=MUTED))


def style_block():
    return """
<style>
  svg {
    color-scheme: light dark;
    --bg: #ffffff;
    --panel: #fafbfc;
    --panel-stroke: #e4e7ec;
    --grid: #eceef2;
    --axis: #d5d8df;
    --text: #1c1f24;
    --muted: #5d6674;
      --legend-success: #6b7280;
      --legend-timeout-fill: rgba(0, 0, 0, 0.08);
      --legend-timeout-stroke: #7b8797;
      --legend-other-fill: rgba(0, 0, 0, 0.04);
      --legend-other-stroke: #9ca3af;
      --segment-timeout-fill: rgba(0, 0, 0, 0.08);
      --segment-other-fill: rgba(0, 0, 0, 0.04);
    }

  @media (prefers-color-scheme: dark) {
    svg {
      --bg: #0e1117;
      --panel: #151a23;
      --panel-stroke: #2f3847;
      --grid: #2a3140;
      --axis: #3a4456;
      --text: #f3f5f8;
      --muted: #b7bfcb;
      --legend-success: #cbd5e1;
      --legend-timeout-fill: rgba(255, 255, 255, 0.08);
      --legend-timeout-stroke: #aab6c8;
      --legend-other-fill: rgba(255, 255, 255, 0.04);
      --legend-other-stroke: #8f9bad;
      --segment-timeout-fill: rgba(255, 255, 255, 0.08);
      --segment-other-fill: rgba(255, 255, 255, 0.04);
    }
  }
</style>""".strip()


def pattern_defs():
    defs = [
        '<pattern id="legend-timeout-pattern" patternUnits="userSpaceOnUse" width="8" height="8" '
        'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" '
        'stroke="#7b8797" stroke-width="1.7" /></pattern>'
    ]
    for backend in BACKENDS:
        stroke = mix(backend['color'], 0.45)
        defs.append(
            f'<pattern id="timeout-pattern-{backend["name"]}" patternUnits="userSpaceOnUse" '
            f'width="8" height="8" patternTransform="rotate(45)">'
            f'<line x1="0" y1="0" x2="0" y2="8" stroke="{stroke}" stroke-width="1.7" /></pattern>'
        )
    return defs


def build_svg():
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" fill="none">',
        style_block(),
        '<defs>',
        *pattern_defs(),
        '</defs>',
        svg_rect(0, 0, WIDTH, HEIGHT, BG, rx=0),
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
