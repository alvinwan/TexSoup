"""
Export to JSON, XML, and HTML
---

This script uses TexSoup's built-in export helpers to serialize a LaTeX
document as JSON, XML, or HTML.

To use it, run

    python simple_conversion.py

after installing TexSoup.
"""

from pathlib import Path

from TexSoup import TexSoup, dumps


if __name__ == '__main__':
    tex_path = Path(input('LaTeX file:').strip())
    export_format = input('Export format (json/xml/html): ').strip().lower()

    output_path = tex_path.with_name(tex_path.stem + '__tmp.' + export_format)
    output_path.write_text(dumps(TexSoup(tex_path.read_text()), format=export_format))
    print(output_path.read_text())
