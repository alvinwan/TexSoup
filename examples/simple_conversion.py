"""
Export to JSON, XML, and HTML
---

This script converts a given LaTeX document into a normalized tree and exports
that tree as JSON, XML, or HTML.

To use it, run

    python simple_conversion.py

after installing TexSoup.

For JSON exports, this script also verifies that the normalized tree can be
converted back into the original LaTeX source.

@author: Simon Maenaut, Alvin Wan
"""

import json
from html import escape
from pathlib import Path
from xml.etree.ElementTree import Element, indent, tostring

import TexSoup
from TexSoup.data import TexCmd, TexEnv, TexGroup, TexText


def to_structure(tex_tree):
    r"""Convert a TexSoup tree into a normalized export structure.

    >>> tree = to_structure(TexSoup.TexSoup(r'\section{Hello}').expr.all)
    >>> tree['type']
    'latex'
    >>> tree['contents'][0]['type']
    'cmd'
    >>> tree['contents'][0]['name']
    'section'
    """
    return {
        "type": "latex",
        "contents": [to_node(node) for node in tex_tree],
    }


def to_node(node):
    """Convert a single TexSoup node into an export node."""
    if isinstance(node, TexGroup):
        return {
            "type": "group",
            "kind": type(node).__name__,
            "begin": node.begin,
            "end": node.end,
            "contents": [to_node(content) for content in node.all],
        }
    if isinstance(node, TexEnv):
        return {
            "type": "env",
            "name": node.name,
            "begin": node.begin + str(node.args),
            "end": node.end,
            "contents": [to_node(content) for content in node.all],
        }
    if isinstance(node, TexCmd):
        return {
            "type": "cmd",
            "name": node.name,
            "source": "\\" + node.name + str(node.args),
        }
    if isinstance(node, TexText):
        return {
            "type": "text",
            "value": str(node),
        }
    return {
        "type": "token",
        "value": str(node),
    }


def to_latex(node):
    r"""Convert a normalized export structure back into LaTeX.

    >>> tree = to_structure(TexSoup.TexSoup(r'\section{Hello}').expr.all)
    >>> to_latex(tree)
    '\\section{Hello}'
    """
    node_type = node["type"]

    if node_type == "latex":
        return "".join(to_latex(content) for content in node["contents"])
    if node_type == "env":
        return node["begin"] + "".join(
            to_latex(content) for content in node["contents"]) + node["end"]
    if node_type == "group":
        return node["begin"] + "".join(
            to_latex(content) for content in node["contents"]) + node["end"]
    if node_type == "cmd":
        return node["source"]
    return node["value"]


def to_json_string(tree):
    """Serialize the normalized tree to pretty JSON."""
    return json.dumps(tree, indent="  ")


def to_xml_string(tree):
    r"""Serialize the normalized tree to pretty XML.

    >>> xml = to_xml_string(to_structure(TexSoup.TexSoup(r'\section{Hello}').expr.all))
    >>> xml.startswith('<?xml version="1.0" encoding="utf-8"?>')
    True
    >>> '<cmd name="section"' in xml
    True
    """
    root = to_xml_node(tree)
    indent(root, space="  ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + tostring(
        root, encoding="unicode")


def to_xml_node(node):
    """Convert a normalized node into an XML element."""
    node_type = node["type"]
    if node_type == "latex":
        element = Element("latex")
        append_xml_children(element, node["contents"])
        return element

    element = Element(node_type)
    for key in ("name", "kind", "begin", "end", "source"):
        if key in node:
            element.set(key, node[key])

    if node_type in ("text", "token"):
        element.text = node["value"]
    else:
        append_xml_children(element, node.get("contents", ()))
    return element


def append_xml_children(parent, children):
    """Append child XML nodes."""
    for child in children:
        parent.append(to_xml_node(child))


def to_html_string(tree):
    r"""Serialize the normalized tree to a standalone HTML document.

    >>> html = to_html_string(to_structure(TexSoup.TexSoup(r'\section{Hello}').expr.all))
    >>> html.startswith('<!DOCTYPE html>')
    True
    >>> 'class="tex-cmd"' in html
    True
    """
    body = to_html_node(tree)
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TexSoup Export</title>
  <style>
    body {{
      font-family: Menlo, Monaco, monospace;
      margin: 2rem;
      line-height: 1.5;
      background: #fffaf3;
      color: #2d2418;
    }}
    .tex-root, .tex-env, .tex-group {{
      border: 1px solid #d9c7aa;
      border-radius: 8px;
      margin: 0.75rem 0;
      padding: 0.75rem;
      background: #fff;
    }}
    .tex-meta {{
      color: #8a5b2c;
      margin-bottom: 0.5rem;
    }}
    .tex-contents {{
      margin-left: 1rem;
    }}
    .tex-cmd, .tex-text, .tex-token {{
      display: inline-block;
      margin: 0.1rem 0.2rem 0.1rem 0;
      white-space: pre-wrap;
    }}
    .tex-cmd {{
      color: #0d5c63;
      font-weight: 600;
    }}
    .tex-delim {{
      color: #8a5b2c;
      font-weight: 700;
    }}
  </style>
</head>
<body>
{body}
</body>
</html>""".format(body=body)


def to_html_node(node):
    """Convert a normalized node into HTML markup."""
    node_type = node["type"]

    if node_type == "latex":
        contents = "".join(to_html_node(content) for content in node["contents"])
        return '<div class="tex-root">{}</div>'.format(contents)

    if node_type == "env":
        contents = "".join(to_html_node(content) for content in node["contents"])
        meta = '<div class="tex-meta">{begin} ... {end}</div>'.format(
            begin=escape(node["begin"]), end=escape(node["end"]))
        return (
            '<div class="tex-env" data-name="{name}">{meta}'
            '<div class="tex-contents">{contents}</div></div>'
        ).format(name=escape(node["name"]), meta=meta, contents=contents)

    if node_type == "group":
        contents = "".join(to_html_node(content) for content in node["contents"])
        return (
            '<div class="tex-group" data-kind="{kind}">'
            '<span class="tex-delim">{begin}</span>'
            '<div class="tex-contents">{contents}</div>'
            '<span class="tex-delim">{end}</span>'
            '</div>'
        ).format(
            kind=escape(node["kind"]),
            begin=escape(node["begin"]),
            end=escape(node["end"]),
            contents=contents,
        )

    if node_type == "cmd":
        return '<code class="tex-cmd" data-name="{name}">{source}</code>'.format(
            name=escape(node["name"]), source=escape(node["source"]))

    return '<span class="tex-{type}">{value}</span>'.format(
        type=node_type, value=escape(node["value"]))


def export_string(tree, export_format):
    """Serialize the normalized tree to the requested format."""
    if export_format == "json":
        return to_json_string(tree)
    if export_format == "xml":
        return to_xml_string(tree)
    if export_format == "html":
        return to_html_string(tree)
    raise ValueError("Unsupported export format: %s" % export_format)


if __name__ == '__main__':
    tex_path = Path(input('LaTeX file:').strip())
    export_format = input('Export format (json/xml/html): ').strip().lower()

    tex_text = tex_path.read_text()
    export_tree = to_structure(TexSoup.TexSoup(tex_text).expr.all)

    suffix = {
        "json": ".json",
        "xml": ".xml",
        "html": ".html",
    }.get(export_format)
    if suffix is None:
        raise ValueError("Unsupported export format: %s" % export_format)

    output_path = tex_path.with_name(tex_path.stem + "__tmp" + suffix)
    output_path.write_text(export_string(export_tree, export_format))
    print(output_path.read_text())

    if export_format == "json":
        exported = json.loads(output_path.read_text())
        print("\nRound-trip:", tex_text == to_latex(exported))
