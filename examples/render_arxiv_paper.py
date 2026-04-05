"""
Render an arXiv Paper with Linked Assets
---

This script downloads an arXiv source package, extracts it, and writes the
rendered HTML using the extracted source tree as the asset root so figure links
and browser-displayable figure assets continue to work.

Figure assets that browsers can display directly (`.png`, `.jpg`, `.svg`,
etc.) render inline. Other assets such as `.pdf` remain clickable links.

To use it, run

    python examples/render_arxiv_paper.py 2004.05565

after installing TexSoup.
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from TexSoup import TexSoup, dumps
from TexSoup.export import PDF_PREVIEW_SUFFIX
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


def preview_path(pdf_path):
    """Return the generated PNG preview path for a PDF figure."""
    return pdf_path.with_name(pdf_path.stem + PDF_PREVIEW_SUFFIX)


def ensure_pdf_preview(pdf_path):
    """Generate a PNG preview for a PDF figure when possible."""
    preview = preview_path(pdf_path)
    if preview.exists() and preview.stat().st_mtime >= pdf_path.stat().st_mtime:
        return preview

    sips = shutil.which('sips')
    if not sips:
        return None

    subprocess.run(
        [sips, '-s', 'format', 'png', str(pdf_path), '--out', str(preview)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return preview


def ensure_pdf_previews(root):
    """Generate PDF previews under the extracted paper source tree."""
    for pdf_path in root.rglob('*.pdf'):
        ensure_pdf_preview(pdf_path)


def main():
    """Render an arXiv paper to HTML."""
    args = build_parser().parse_args()
    paper = load_paper_text(normalize_paper_id(args.paper_id), args)
    ensure_pdf_previews(paper['root'])
    output_path = args.output or default_output_path(paper)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        dumps(TexSoup(paper['text']), format='html', asset_root=paper['root']))
    print(output_path)


if __name__ == '__main__':
    main()
