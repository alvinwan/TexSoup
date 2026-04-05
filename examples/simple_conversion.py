"""
Export to JSON and XML
---

This script uses TexSoup's built-in export helpers to serialize a LaTeX
document as JSON or XML.

For the richer paper-style HTML renderer, see `examples/render_arxiv_paper.py`.

To use it, run

    python simple_conversion.py

after installing TexSoup.
"""

from pathlib import Path

from TexSoup import TexSoup, dumps


if __name__ == '__main__':
    tex_path = Path(input('LaTeX file:').strip())
    export_format = input('Export format (json/xml): ').strip().lower()

    output_path = tex_path.with_name(tex_path.stem + '__tmp.' + export_format)
    output_path.write_text(dumps(TexSoup(tex_path.read_text()), format=export_format))
    print(output_path.read_text())
