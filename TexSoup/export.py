"""Export TexSoup trees to serialized formats."""

import json
from html import escape
from xml.etree.ElementTree import Element, tostring

from TexSoup.data import TexCmd, TexEnv, TexExpr, TexGroup, TexNode, TexText

__all__ = ['dump', 'dumps']


def dumps(tex, format='json'):
    r"""Serialize a TexSoup node to the requested format.

    :param TexNode tex: TexSoup node to serialize
    :param str format: one of ``json``, ``xml``, or ``html``
    :return: serialized output
    :rtype: str

    >>> from TexSoup import TexSoup
    >>> soup = TexSoup(r'\section{Hello}')
    >>> '"type": "latex"' in dumps(soup)
    True
    >>> dumps(soup, format='xml').startswith('<?xml version="1.0" encoding="utf-8"?>')
    True
    >>> dumps(soup, format='html').startswith('<!DOCTYPE html>')
    True
    """
    tree = _to_export_tree(tex)
    if format == 'json':
        return json.dumps(tree, indent='  ')
    if format == 'xml':
        return _to_xml_string(tree)
    if format == 'html':
        return _to_html_string(tree)
    raise ValueError('Unsupported export format: %s' % format)


def dump(tex, fp, format='json'):
    r"""Serialize a TexSoup node into a writable file object.

    :param TexNode tex: TexSoup node to serialize
    :param file fp: writable file-like object
    :param str format: one of ``json``, ``xml``, or ``html``

    >>> from io import StringIO
    >>> from TexSoup import TexSoup
    >>> buffer = StringIO()
    >>> dump(TexSoup(r'\section{Hello}'), buffer, format='xml')
    >>> buffer.getvalue().startswith('<?xml version="1.0" encoding="utf-8"?>')
    True
    """
    fp.write(dumps(tex, format=format))


def _to_export_tree(tex):
    """Convert a TexSoup node into a normalized export structure."""
    expr = _get_expr(tex)
    if expr.name == '[tex]':
        return {
            'type': 'latex',
            'contents': [_to_node(child) for child in expr.all],
        }
    return _to_node(expr)


def _get_expr(tex):
    """Normalize export input to a TexExpr."""
    if isinstance(tex, TexNode):
        return tex.expr
    if isinstance(tex, TexExpr):
        return tex
    raise TypeError('Expected TexNode or TexExpr, got %s' % type(tex).__name__)


def _to_node(node):
    """Convert a single TexSoup node into an export node."""
    if isinstance(node, TexGroup):
        return {
            'type': 'group',
            'kind': type(node).__name__,
            'begin': node.begin,
            'end': node.end,
            'contents': [_to_node(content) for content in node.all],
        }
    if isinstance(node, TexEnv):
        return {
            'type': 'env',
            'name': node.name,
            'begin': node.begin + str(node.args),
            'end': node.end,
            'contents': [_to_node(content) for content in node.all],
        }
    if isinstance(node, TexCmd):
        return {
            'type': 'cmd',
            'name': node.name,
            'source': '\\' + node.name + str(node.args),
        }
    if isinstance(node, TexText):
        return {
            'type': 'text',
            'value': str(node),
        }
    return {
        'type': 'token',
        'value': str(node),
    }


def _to_xml_string(tree):
    """Serialize the normalized tree to pretty XML."""
    root = _to_xml_node(tree)
    _indent(root)
    return '<?xml version="1.0" encoding="utf-8"?>\n' + tostring(
        root, encoding='unicode')


def _to_xml_node(node):
    """Convert a normalized node into an XML element."""
    node_type = node['type']
    if node_type == 'latex':
        element = Element('latex')
        for child in node['contents']:
            element.append(_to_xml_node(child))
        return element

    element = Element(node_type)
    for key in ('name', 'kind', 'begin', 'end', 'source'):
        if key in node:
            element.set(key, node[key])

    if node_type in ('text', 'token'):
        element.text = node['value']
    else:
        for child in node.get('contents', ()):
            element.append(_to_xml_node(child))
    return element


def _to_html_string(tree):
    """Serialize the normalized tree to a standalone HTML document."""
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
</html>""".format(body=_to_html_node(tree))


def _to_html_node(node):
    """Convert a normalized node into HTML markup."""
    node_type = node['type']

    if node_type == 'latex':
        return '<div class="tex-root">{}</div>'.format(
            ''.join(_to_html_node(content) for content in node['contents']))

    if node_type == 'env':
        contents = ''.join(_to_html_node(content) for content in node['contents'])
        meta = '<div class="tex-meta">{begin} ... {end}</div>'.format(
            begin=escape(node['begin']), end=escape(node['end']))
        return (
            '<div class="tex-env" data-name="{name}">{meta}'
            '<div class="tex-contents">{contents}</div></div>'
        ).format(name=escape(node['name']), meta=meta, contents=contents)

    if node_type == 'group':
        contents = ''.join(_to_html_node(content) for content in node['contents'])
        return (
            '<div class="tex-group" data-kind="{kind}">'
            '<span class="tex-delim">{begin}</span>'
            '<div class="tex-contents">{contents}</div>'
            '<span class="tex-delim">{end}</span>'
            '</div>'
        ).format(
            kind=escape(node['kind']),
            begin=escape(node['begin']),
            end=escape(node['end']),
            contents=contents,
        )

    if node_type == 'cmd':
        return '<code class="tex-cmd" data-name="{name}">{source}</code>'.format(
            name=escape(node['name']), source=escape(node['source']))

    return '<span class="tex-{type}">{value}</span>'.format(
        type=node_type, value=escape(node['value']))


def _indent(element, level=0):
    """Indent XML elements in-place for pretty output."""
    padding = '\n' + '  ' * level
    if len(element):
        if not element.text or not element.text.strip():
            element.text = padding + '  '
        for child in element:
            _indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = padding + '  '
        if not element[-1].tail or not element[-1].tail.strip():
            element[-1].tail = padding
