"""Export TexSoup trees as basic serialized structures."""

import json
from xml.etree.ElementTree import Element, tostring

from TexSoup.data import TexCmd, TexEnv, TexExpr, TexGroup, TexNode, TexText

__all__ = ['dump', 'dumps']


def dumps(tex, format='json'):
    r"""Serialize a TexSoup node to JSON or XML.

    :param TexNode tex: TexSoup node to serialize
    :param str format: one of ``json`` or ``xml``
    :return: serialized output
    :rtype: str

    >>> from TexSoup import TexSoup
    >>> soup = TexSoup(r'\section{Hello}')
    >>> '"type": "latex"' in dumps(soup)
    True
    >>> dumps(soup, format='xml').startswith('<?xml version="1.0" encoding="utf-8"?>')
    True
    """
    tree = _to_export_tree(tex)
    if format == 'json':
        return json.dumps(tree, indent='  ')
    if format == 'xml':
        return _to_xml_string(tree)
    raise ValueError('Unsupported export format: %s' % format)


def dump(tex, fp, format='json'):
    r"""Serialize a TexSoup node into a writable file object.

    :param TexNode tex: TexSoup node to serialize
    :param file fp: writable file-like object
    :param str format: one of ``json`` or ``xml``

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


def _indent(element, level=0):
    """Indent an XML tree in place."""
    indent = '\n' + level * '  '
    child_indent = indent + '  '
    children = list(element)
    if children:
        if not element.text or not element.text.strip():
            element.text = child_indent
        for child in children:
            _indent(child, level + 1)
        if not children[-1].tail or not children[-1].tail.strip():
            children[-1].tail = indent
    elif level and (not element.tail or not element.tail.strip()):
        element.tail = indent
