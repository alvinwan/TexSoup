"""
Render an arXiv Paper with Linked Assets
---

This script downloads an arXiv source package, extracts it, and writes the
rendered HTML next to the paper's main `.tex` file so relative figure asset
links continue to work.

Figure assets that browsers can display directly (`.png`, `.jpg`, `.svg`,
etc.) render inline. Other assets such as `.pdf` remain clickable links.

To use it, run

    python examples/render_arxiv_paper.py 2004.05565

after installing TexSoup.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from TexSoup import TexSoup, dumps
from benchmarks.arxiv import load_paper_text, normalize_paper_id


def build_parser():
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paper_id', help='arXiv identifier such as 2004.05565')
    parser.add_argument(
        '--cache-dir',
        type=Path,
        default=Path('tmp/arxiv_benchmarks'),
        help='Where downloaded and extracted arXiv sources are stored.',
    )
    parser.add_argument(
        '--skip-expand-inputs',
        action='store_true',
        help='Do not inline \\input / \\include files before rendering.',
    )
    parser.add_argument(
        '--skip-expand-bbl',
        action='store_true',
        help='Do not inline .bbl bibliography files before rendering.',
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Optional output HTML path. Defaults to the extracted main .tex path with .html.',
    )
    return parser


def default_output_path(paper):
    """Return the default HTML path for a rendered paper."""
    return Path(paper['root']) / Path(paper['main_tex']).with_suffix('.html')


def main():
    """Render an arXiv paper to HTML."""
    args = build_parser().parse_args()
    paper = load_paper_text(normalize_paper_id(args.paper_id), args)
    output_path = args.output or default_output_path(paper)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dumps(TexSoup(paper['text']), format='html'))
    print(output_path)


if __name__ == '__main__':
    main()
