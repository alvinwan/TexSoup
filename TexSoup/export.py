"""Export TexSoup trees to serialized formats."""

import json
import re
from html import escape
from xml.etree.ElementTree import Element, tostring

from TexSoup.data import (TexCmd, TexDisplayMathEnv, TexDisplayMathModeEnv,
                          TexEnv, TexExpr, TexGroup, TexMathEnv,
                          TexMathModeEnv, TexNamedEnv, TexNode, TexText)

__all__ = ['dump', 'dumps']

SECTION_LEVELS = {
    'section': 2,
    'subsection': 3,
    'subsubsection': 4,
    'paragraph': 5,
    'subparagraph': 6,
}
INLINE_COMMANDS = {
    'emph': 'em',
    'textbf': 'strong',
    'textit': 'em',
    'textsc': 'span class="tex-smallcaps"',
    'texttt': 'code',
    'underline': 'u',
}
TRANSPARENT_COMMANDS = {
    'mathbf',
    'mathrm',
    'mathit',
    'mbox',
    'texrm',
    'textnormal',
    'textrm',
}
TRANSPARENT_ZERO_ARG_COMMANDS = {'centering', 'small', 'tt'}
REFERENCE_COMMANDS = {
    'autoref',
    'cite',
    'citep',
    'citet',
    'eqref',
    'pageref',
    'ref',
}
DISPLAY_MATH_ENVS = {
    'align',
    'align*',
    'displaymath',
    'equation',
    'equation*',
    'gather',
    'gather*',
    'multline',
    'multline*',
}
LIST_ENVS = {
    'description': 'ul',
    'enumerate': 'ol',
    'itemize': 'ul',
}
RAW_BLOCK_ENVS = {
    'array',
    'lstlisting',
    'tabular',
    'tabular*',
    'verbatim',
}
SKIPPED_BODY_COMMANDS = {'author', 'date', 'maketitle', 'title'}
PARAGRAPH_BREAK = object()


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
    if format == 'json':
        tree = _to_export_tree(tex)
        return json.dumps(tree, indent='  ')
    if format == 'xml':
        tree = _to_export_tree(tex)
        return _to_xml_string(tree)
    if format == 'html':
        return _to_html_string(_get_expr(tex))
    if format == 'html_tree':
        tree = _to_export_tree(tex)
        return _to_html_tree_string(tree)
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


def _to_html_string(expr):
    """Render a TexSoup tree as a paper-like HTML document."""
    metadata, body_nodes = _extract_document(expr)
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --paper: #fffdf8;
      --page: #efe5d2;
      --page-top: #f8f3ea;
      --ink: #201912;
      --muted: #6d5f52;
      --line: #dac8af;
      --accent: #8a4b17;
      --accent-soft: rgba(138, 75, 23, 0.1);
      --link: #0d5c63;
      --shadow: rgba(47, 32, 20, 0.08);
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top, rgba(255, 255, 255, 0.88), transparent 38%),
        linear-gradient(180deg, var(--page-top) 0%, var(--page) 100%);
      color: var(--ink);
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua",
          Georgia, serif;
    }}
    .tex-shell {{
      max-width: 920px;
      margin: 0 auto;
      padding: 3rem 1.25rem 4rem;
    }}
    .tex-paper {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: 0 28px 64px var(--shadow);
      padding: 4rem 4.5rem;
    }}
    .tex-frontmatter {{
      margin-bottom: 2.25rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid rgba(218, 200, 175, 0.9);
      text-align: center;
    }}
    .tex-paper-title {{
      margin: 0;
      font-size: 2.6rem;
      line-height: 1.05;
      letter-spacing: -0.03em;
    }}
    .tex-paper-authors,
    .tex-paper-date {{
      margin: 0.7rem 0 0;
      color: var(--muted);
      font-size: 1rem;
    }}
    .tex-abstract {{
      margin: 0 0 2rem;
      padding: 1.2rem 1.35rem;
      border: 1px solid rgba(218, 200, 175, 0.95);
      border-left: 4px solid var(--accent);
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(248, 242, 233, 0.95), rgba(255, 252, 245, 0.95));
    }}
    .tex-abstract h2 {{
      margin: 0 0 0.75rem;
      color: var(--accent);
      font: 700 0.86rem/1.2 ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .tex-body {{
      font-size: 1rem;
      line-height: 1.72;
    }}
    .tex-body h2,
    .tex-body h3,
    .tex-body h4,
    .tex-body h5,
    .tex-body h6 {{
      margin: 2rem 0 0.8rem;
      line-height: 1.2;
      font-weight: 700;
    }}
    .tex-body h2 {{
      font-size: 1.65rem;
      border-bottom: 1px solid rgba(218, 200, 175, 0.7);
      padding-bottom: 0.3rem;
    }}
    .tex-body h3 {{
      font-size: 1.28rem;
    }}
    .tex-body h4 {{
      font-size: 1.1rem;
    }}
    .tex-body h5,
    .tex-body h6 {{
      font-size: 1rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .tex-body p {{
      margin: 0 0 1.15rem;
      text-align: justify;
    }}
    .tex-body ul,
    .tex-body ol {{
      margin: 0 0 1.2rem 1.15rem;
      padding-left: 1.1rem;
    }}
    .tex-body li {{
      margin: 0.35rem 0;
    }}
    .tex-body li > p:first-child {{
      margin-top: 0;
    }}
    .tex-link {{
      color: var(--link);
      text-decoration: none;
      border-bottom: 1px solid rgba(13, 92, 99, 0.25);
    }}
    .tex-reference {{
      color: var(--accent);
      font-weight: 600;
    }}
    .tex-smallcaps {{
      font-variant: small-caps;
      letter-spacing: 0.04em;
    }}
    .tex-inline-raw,
    .tex-source {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
    }}
    .tex-inline-raw {{
      padding: 0.08rem 0.3rem;
      border-radius: 0.4rem;
      background: rgba(138, 75, 23, 0.08);
      color: var(--accent);
      font-size: 0.92em;
    }}
    .tex-footnote {{
      color: var(--muted);
      font-size: 0.92em;
    }}
    .tex-figure,
    .tex-table-block,
    .tex-raw-block,
    .tex-math-block,
    .tex-generic-block,
    blockquote {{
      margin: 1.5rem 0;
      padding: 1rem 1.15rem;
      border: 1px solid rgba(218, 200, 175, 0.95);
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(250, 245, 238, 0.96), rgba(255, 252, 246, 0.96));
    }}
    .tex-math-block {{
      overflow-x: auto;
      text-align: center;
    }}
    .tex-source {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.92rem;
      line-height: 1.6;
    }}
    .tex-graphic-placeholder {{
      display: grid;
      place-items: center;
      gap: 0.5rem;
      min-height: 8rem;
      padding: 1rem;
      border: 1px dashed rgba(138, 75, 23, 0.35);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.55);
      color: var(--muted);
      text-align: center;
    }}
    .tex-figure figcaption,
    .tex-table-block figcaption,
    .tex-caption {{
      margin-top: 0.85rem;
      color: var(--muted);
      font-size: 0.95rem;
      text-align: center;
    }}
    .tex-env-label {{
      color: var(--muted);
      font: 600 0.76rem/1.4 ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    @media (max-width: 860px) {{
      .tex-shell {{
        padding: 1.1rem 0.7rem 2rem;
      }}
      .tex-paper {{
        padding: 1.8rem 1.3rem 2rem;
        border-radius: 18px;
      }}
      .tex-paper-title {{
        font-size: 2rem;
      }}
      .tex-body p {{
        text-align: left;
      }}
    }}
  </style>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
        packages: {{'[+]': ['ams']}},
        macros: {macros}
      }},
      svg: {{
        fontCache: 'global'
      }}
    }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
</head>
<body>
  <main class="tex-shell">
    <article class="tex-paper">
      {frontmatter}
      <div class="tex-body">{body}</div>
    </article>
  </main>
</body>
</html>""".format(
        title=escape(metadata['title_text'] or 'TexSoup HTML Export'),
        frontmatter=_render_frontmatter(metadata),
        body=_render_blocks(body_nodes),
        macros=json.dumps(metadata['mathjax_macros'], sort_keys=True),
    )


def _extract_document(expr):
    """Extract document metadata and renderable body nodes."""
    if expr.name == '[tex]':
        root_nodes = list(expr.contents)
        document = next(
            (node for node in root_nodes
             if isinstance(node, TexNamedEnv) and node.name == 'document'),
            None,
        )
        body_nodes = list(document.contents) if document is not None else root_nodes
        preamble_nodes = root_nodes[:root_nodes.index(document)] if document is not None else root_nodes
    else:
        preamble_nodes = []
        body_nodes = [expr]

    metadata = {
        'title_html': '',
        'title_text': '',
        'author_html': '',
        'date_html': '',
        'abstract_html': '',
        'mathjax_macros': _collect_mathjax_macros(preamble_nodes),
    }

    for node in preamble_nodes + body_nodes:
        if isinstance(node, TexCmd) and node.name in ('title', 'author', 'date') and node.args:
            rendered = _render_inline_nodes(list(node.args[0].contents))
            text = str(node.args[0].string).strip()
            metadata['%s_html' % node.name] = rendered
            metadata['%s_text' % node.name] = text
        if isinstance(node, TexNamedEnv) and node.name == 'abstract' and not metadata['abstract_html']:
            metadata['abstract_html'] = _render_blocks(list(node.contents))

    return metadata, body_nodes


def _collect_mathjax_macros(nodes):
    """Collect simple macro definitions for MathJax."""
    macros = {}
    for node in nodes:
        if not isinstance(node, TexCmd):
            continue
        if node.name not in ('newcommand', 'renewcommand', 'providecommand'):
            continue
        if len(node.args) < 2:
            continue

        raw_name = getattr(node.args[0], 'string', str(node.args[0]))
        if not raw_name.startswith('\\'):
            continue

        body_index = 1
        arg_count = None
        if len(node.args) > 2 and str(node.args[1]).startswith('[') and node.args[1].string.isdigit():
            arg_count = int(node.args[1].string)
            body_index = 2
        if len(node.args) > body_index + 1 and str(node.args[body_index]).startswith('['):
            continue
        if body_index >= len(node.args):
            continue

        replacement = node.args[body_index].string
        macro_name = raw_name.lstrip('\\')
        macros[macro_name] = [replacement, arg_count] if arg_count else replacement
    return macros


def _render_frontmatter(metadata):
    """Render document frontmatter."""
    parts = []
    if metadata['title_html'] or metadata['author_html'] or metadata['date_html']:
        parts.append('<header class="tex-frontmatter">')
        if metadata['title_html']:
            parts.append('<h1 class="tex-paper-title">{}</h1>'.format(metadata['title_html']))
        if metadata['author_html']:
            parts.append('<p class="tex-paper-authors">{}</p>'.format(metadata['author_html']))
        if metadata['date_html']:
            parts.append('<p class="tex-paper-date">{}</p>'.format(metadata['date_html']))
        parts.append('</header>')
    if metadata['abstract_html']:
        parts.append(
            '<section class="tex-abstract"><h2>Abstract</h2>{}</section>'.format(
                metadata['abstract_html'])
        )
    return ''.join(parts)


def _render_blocks(nodes):
    """Render a sequence of parsed nodes as block HTML."""
    blocks = []
    inline = []
    for node in nodes:
        if _skip_body_node(node):
            continue
        if _is_block_node(node):
            _flush_paragraph(blocks, inline)
            rendered = _render_block_node(node)
            if rendered:
                blocks.append(rendered)
            continue

        for fragment in _render_inline_segments(node):
            if fragment is PARAGRAPH_BREAK:
                _flush_paragraph(blocks, inline)
            elif fragment:
                inline.append(fragment)
    _flush_paragraph(blocks, inline)
    return ''.join(blocks)


def _render_inline_nodes(nodes):
    """Render parsed nodes as inline HTML."""
    fragments = []
    for node in nodes:
        if _skip_body_node(node):
            continue
        if _is_block_node(node):
            rendered = _render_block_node(node)
            if rendered:
                fragments.append(rendered)
            continue
        for fragment in _render_inline_segments(node):
            if fragment is not PARAGRAPH_BREAK and fragment:
                fragments.append(fragment)
    return ''.join(fragments).strip()


def _render_inline_segments(node):
    """Render a node to inline fragments, preserving paragraph breaks."""
    if isinstance(node, TexText):
        stripped = _strip_comment_lines(str(node))
        parts = re.split(r'\n\s*\n+', stripped)
        fragments = []
        for index, part in enumerate(parts):
            lines = part.split(r'\\')
            for line_index, line in enumerate(lines):
                normalized = _normalize_inline_text(line)
                if normalized:
                    fragments.append(escape(normalized))
                if line_index < len(lines) - 1:
                    fragments.append('<br />')
            if index < len(parts) - 1:
                fragments.append(PARAGRAPH_BREAK)
        return fragments
    rendered = _render_inline_node(node)
    return [rendered] if rendered else []


def _render_inline_node(node):
    """Render a single node as inline HTML."""
    if isinstance(node, TexGroup):
        return _render_inline_nodes(list(node.contents))
    if isinstance(node, (TexMathEnv, TexMathModeEnv)):
        return '<span class="tex-math">{}</span>'.format(escape(str(node)))
    if not isinstance(node, TexCmd):
        return '<span class="tex-inline-raw">{}</span>'.format(escape(str(node)))
    if node.name in SKIPPED_BODY_COMMANDS or node.name in ('caption', 'maketitle'):
        return ''
    if node.name in INLINE_COMMANDS and node.args:
        return _wrap_inline(INLINE_COMMANDS[node.name], _render_inline_nodes(list(node.args[0].contents)))
    if node.name in TRANSPARENT_COMMANDS and node.args:
        return _render_inline_nodes(list(node.args[0].contents))
    if node.name in TRANSPARENT_ZERO_ARG_COMMANDS:
        return ''
    if node.name == 'url' and node.args:
        href = escape(node.args[-1].string)
        return '<a class="tex-link" href="{href}">{href}</a>'.format(href=href)
    if node.name == 'href' and len(node.args) >= 2:
        href = escape(node.args[0].string)
        label = _render_inline_nodes(list(node.args[1].contents))
        return '<a class="tex-link" href="{href}">{label}</a>'.format(href=href, label=label)
    if node.name in REFERENCE_COMMANDS and node.args:
        label = ', '.join(arg.string for arg in node.args if getattr(arg, 'string', ''))
        return '<span class="tex-reference">{}</span>'.format(escape(label or str(node)))
    if node.name == 'thanks' and node.args:
        return '<span class="tex-footnote">({})</span>'.format(
            _render_inline_nodes(list(node.args[0].contents)))
    if node.name == 'footnote' and node.args:
        return '<span class="tex-footnote">({})</span>'.format(
            _render_inline_nodes(list(node.args[0].contents)))
    if node.name in ('\\', 'newline'):
        return '<br />'
    return '<span class="tex-inline-raw">{}</span>'.format(escape(str(node)))


def _render_block_node(node):
    """Render a single node as block HTML."""
    if isinstance(node, (TexDisplayMathEnv, TexDisplayMathModeEnv)):
        return _render_math_block(str(node))
    if isinstance(node, TexNamedEnv):
        if node.name == 'document':
            return _render_blocks(list(node.contents))
        if node.name == 'abstract':
            return ''
        if node.name in LIST_ENVS:
            return _render_list(node)
        if node.name in ('figure', 'figure*'):
            return _render_figure(node, class_name='tex-figure')
        if node.name in ('table', 'table*'):
            return _render_figure(node, class_name='tex-table-block')
        if node.name in DISPLAY_MATH_ENVS:
            return _render_math_block(str(node))
        if node.name in RAW_BLOCK_ENVS:
            return _render_raw_block(node, class_name='tex-raw-block')
        if node.name in ('quote', 'quotation'):
            return '<blockquote>{}</blockquote>'.format(_render_blocks(list(node.contents)))
        if node.name == 'center':
            return '<div class="tex-generic-block" style="text-align:center">{}</div>'.format(
                _render_blocks(list(node.contents)))
        return (
            '<section class="tex-generic-block">'
            '<div class="tex-env-label">\\begin{{{name}}}</div>'
            '{contents}'
            '<div class="tex-env-label">\\end{{{name}}}</div>'
            '</section>'
        ).format(name=escape(node.name), contents=_render_blocks(list(node.contents)))
    if isinstance(node, TexCmd):
        if node.name in SECTION_LEVELS:
            return _render_heading(node)
        if node.name == 'includegraphics':
            return _render_includegraphics(node)
        if node.name == 'caption' and node.args:
            return '<div class="tex-caption">{}</div>'.format(
                _render_inline_nodes(list(node.args[0].contents)))
        if node.name == 'item':
            return _render_list_item(node)
        return ''
    return '<div class="tex-raw-block"><pre class="tex-source">{}</pre></div>'.format(
        escape(str(node)))


def _render_heading(node):
    """Render a sectioning command as a heading."""
    level = SECTION_LEVELS[node.name]
    title = _render_inline_nodes(list(node.args[0].contents)) if node.args else escape(node.name)
    return '<h{level}>{title}</h{level}>'.format(level=level, title=title)


def _render_list(env):
    """Render itemize/enumerate/description environments."""
    items = [
        _render_list_item(child)
        for child in env.children
        if isinstance(child, TexCmd) and child.name == 'item'
    ]
    if not items:
        return _render_raw_block(env, class_name='tex-raw-block')
    tag = LIST_ENVS[env.name]
    return '<{tag}>{items}</{tag}>'.format(tag=tag, items=''.join(items))


def _render_list_item(item):
    """Render a list item."""
    body = _render_blocks(list(item.contents)).strip()
    if not body:
        body = _render_inline_nodes(list(item.contents))
    return '<li>{}</li>'.format(body)


def _render_figure(env, class_name):
    """Render figure-like environments."""
    caption = ''
    parts = []
    for child in env.contents:
        if isinstance(child, TexCmd) and child.name == 'caption' and child.args:
            caption = _render_inline_nodes(list(child.args[0].contents))
            continue
        if _is_block_node(child):
            rendered = _render_block_node(child)
        else:
            rendered = _render_inline_nodes([child])
        if rendered:
            parts.append(rendered)

    body = ''.join(parts) or _render_raw_block(env, class_name='tex-raw-block')
    return (
        '<figure class="{class_name}">{body}{caption}</figure>'
    ).format(
        class_name=class_name,
        body=body,
        caption='<figcaption>{}</figcaption>'.format(caption) if caption else '',
    )


def _render_includegraphics(cmd):
    """Render an image inclusion as a placeholder figure."""
    target = cmd.args[-1].string if cmd.args else str(cmd)
    return (
        '<figure class="tex-figure">'
        '<div class="tex-graphic-placeholder">'
        '<strong>Figure asset</strong>'
        '<code class="tex-source">{target}</code>'
        '</div>'
        '</figure>'
    ).format(target=escape(target))


def _render_math_block(source):
    """Render display math using MathJax delimiters."""
    return '<div class="tex-math-block">{}</div>'.format(escape(source))


def _render_raw_block(node, class_name):
    """Render a raw LaTeX block."""
    return '<div class="{class_name}"><pre class="tex-source">{source}</pre></div>'.format(
        class_name=class_name,
        source=escape(str(node)),
    )


def _skip_body_node(node):
    """Return whether this node should be omitted from the rendered body."""
    return (
        isinstance(node, TexCmd) and node.name in SKIPPED_BODY_COMMANDS | {'maketitle'}
    ) or (
        isinstance(node, TexNamedEnv) and node.name == 'abstract'
    )


def _is_block_node(node):
    """Return whether a parsed node should be rendered as a block."""
    if isinstance(node, TexText):
        return False
    if isinstance(node, TexGroup):
        return False
    if isinstance(node, (TexMathEnv, TexMathModeEnv)):
        return False
    if isinstance(node, (TexDisplayMathEnv, TexDisplayMathModeEnv, TexNamedEnv)):
        return True
    return isinstance(node, TexCmd) and node.name in (
        set(SECTION_LEVELS) | {'caption', 'includegraphics', 'item'}
    )


def _strip_comment_lines(text):
    """Remove standalone LaTeX comment lines from text nodes."""
    return ''.join(
        line for line in text.splitlines(True)
        if not line.lstrip().startswith('%')
    )


def _normalize_inline_text(text):
    """Collapse inline whitespace while preserving word boundaries."""
    if not text:
        return ''
    leading = ' ' if text[:1].isspace() else ''
    trailing = ' ' if text[-1:].isspace() else ''
    core = ' '.join(text.split())
    if not core:
        return ''
    core = (core.replace(r'\{', '{')
                .replace(r'\}', '}')
                .replace(r'\%', '%')
                .replace(r'\&', '&')
                .replace(r'\_', '_')
                .replace('~', ' '))
    return leading + core + trailing


def _flush_paragraph(blocks, inline):
    """Flush accumulated inline fragments into a paragraph block."""
    html = ''.join(inline).strip()
    if html:
        blocks.append('<p>{}</p>'.format(html))
    del inline[:]


def _wrap_inline(tag, content):
    """Wrap inline content in an HTML tag specification."""
    if ' ' in tag:
        name, attrs = tag.split(' ', 1)
        return '<{name} {attrs}>{content}</{name}>'.format(
            name=name, attrs=attrs, content=content)
    return '<{tag}>{content}</{tag}>'.format(tag=tag, content=content)


def _to_html_tree_string(tree):
    """Serialize the normalized tree to a standalone HTML document."""
    counts = _count_nodes(tree)
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TexSoup Export</title>
  <style>
    :root {{
      color-scheme: light;
      --paper: #f3eadc;
      --panel: rgba(255, 253, 248, 0.92);
      --panel-strong: rgba(255, 255, 255, 0.96);
      --ink: #241d16;
      --muted: #736150;
      --line: #dbc9b3;
      --cmd: #0d5c63;
      --env: #8a4b17;
      --group: #5b4b87;
      --leaf: #2c6e49;
      --shadow: rgba(44, 29, 17, 0.08);
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      line-height: 1.5;
      background:
        radial-gradient(circle at top, rgba(255, 255, 255, 0.92), transparent 42%),
        linear-gradient(180deg, #f8f4ec 0%, var(--paper) 100%);
      color: var(--ink);
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua",
          Georgia, serif;
    }}
    .tex-page {{
      max-width: 1220px;
      margin: 0 auto;
      padding: 2.25rem 1.5rem 3rem;
    }}
    .tex-hero {{
      margin-bottom: 1.25rem;
      padding: 1.4rem 1.6rem;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: linear-gradient(135deg, var(--panel-strong), rgba(250, 243, 229, 0.96));
      box-shadow: 0 20px 40px var(--shadow);
    }}
    .tex-kicker {{
      margin: 0 0 0.35rem;
      color: var(--env);
      font: 700 0.76rem/1.2 ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .tex-title {{
      margin: 0;
      font-size: 2rem;
      font-weight: 700;
      line-height: 1.05;
    }}
    .tex-subtitle {{
      max-width: 52rem;
      margin: 0.55rem 0 1rem;
      color: var(--muted);
      font-size: 1rem;
    }}
    .tex-stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.55rem;
    }}
    .tex-stat {{
      padding: 0.35rem 0.7rem;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid var(--line);
      color: var(--muted);
      font: 600 0.78rem/1.2 ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
    }}
    .tex-root {{
      display: grid;
      gap: 0.8rem;
    }}
    .tex-node {{
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel);
      box-shadow: 0 14px 28px rgba(57, 40, 20, 0.05);
      overflow: hidden;
    }}
    .tex-node summary,
    .tex-leaf {{
      padding: 0.9rem 1rem;
    }}
    .tex-node summary {{
      display: flex;
      align-items: center;
      gap: 0.7rem;
      cursor: pointer;
      list-style: none;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 241, 229, 0.9));
    }}
    .tex-node summary::-webkit-details-marker {{
      display: none;
    }}
    .tex-tag {{
      flex: none;
      padding: 0.28rem 0.55rem;
      border-radius: 999px;
      font: 700 0.68rem/1.1 ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      background: rgba(115, 97, 80, 0.12);
      color: var(--muted);
    }}
    .tex-tag-cmd {{
      background: rgba(13, 92, 99, 0.12);
      color: var(--cmd);
    }}
    .tex-tag-env {{
      background: rgba(138, 75, 23, 0.12);
      color: var(--env);
    }}
    .tex-tag-group {{
      background: rgba(91, 75, 135, 0.12);
      color: var(--group);
    }}
    .tex-tag-text,
    .tex-tag-token {{
      background: rgba(44, 110, 73, 0.12);
      color: var(--leaf);
    }}
    .tex-tag-comment,
    .tex-tag-whitespace {{
      background: rgba(115, 97, 80, 0.12);
      color: var(--muted);
    }}
    .tex-name {{
      font: 600 0.96rem/1.35 ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
      color: var(--ink);
      overflow-wrap: anywhere;
    }}
    .tex-note {{
      color: var(--muted);
      font: 0.82rem/1.35 ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
      margin-left: auto;
      padding-left: 0.8rem;
    }}
    .tex-meta {{
      display: grid;
      gap: 0.4rem;
      padding: 0 1rem 0.9rem;
      color: var(--muted);
      border-top: 1px solid rgba(219, 201, 179, 0.7);
      background: rgba(249, 244, 236, 0.72);
    }}
    .tex-meta code {{
      display: inline-block;
      overflow-wrap: anywhere;
      font: 0.78rem/1.45 ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
    }}
    .tex-children {{
      display: grid;
      gap: 0.75rem;
      padding: 0.95rem 1rem 1rem 1.4rem;
      background: linear-gradient(180deg, rgba(250, 246, 239, 0.84), rgba(255, 255, 255, 0.7));
    }}
    .tex-children > * {{
      position: relative;
    }}
    .tex-children > *::before {{
      content: "";
      position: absolute;
      left: -0.75rem;
      top: 0.25rem;
      bottom: 0.25rem;
      width: 2px;
      border-radius: 2px;
      background: linear-gradient(180deg, rgba(219, 201, 179, 0.15), rgba(219, 201, 179, 0.92));
    }}
    .tex-leaf {{
      display: grid;
      gap: 0.6rem;
    }}
    .tex-source {{
      margin: 0;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font: 0.88rem/1.6 ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
      color: var(--ink);
    }}
    .tex-comment .tex-source {{
      color: #6a6357;
      font-style: italic;
    }}
    .tex-whitespace .tex-source {{
      color: #9a856f;
    }}
    .tex-root-node > .tex-children {{
      padding-left: 1rem;
    }}
    .tex-root-node > .tex-children > *::before {{
      display: none;
    }}
    @media (max-width: 720px) {{
      .tex-page {{
        padding: 1.25rem 0.9rem 2rem;
      }}
      .tex-node summary,
      .tex-leaf {{
        padding: 0.8rem 0.85rem;
      }}
      .tex-note {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
<main class="tex-page">
  <header class="tex-hero">
    <p class="tex-kicker">TexSoup</p>
    <h1 class="tex-title">HTML Export</h1>
    <p class="tex-subtitle">
      Structural view of a LaTeX parse tree, organized as commands,
      environments, groups, and text nodes.
    </p>
    <div class="tex-stats">
      <span class="tex-stat">{cmds} commands</span>
      <span class="tex-stat">{envs} environments</span>
      <span class="tex-stat">{groups} groups</span>
      <span class="tex-stat">{texts} text nodes</span>
      <span class="tex-stat">{tokens} tokens</span>
    </div>
  </header>
  {body}
</main>
</body>
</html>""".format(
        body=_to_html_node(tree),
        cmds=counts['cmd'],
        envs=counts['env'],
        groups=counts['group'],
        texts=counts['text'],
        tokens=counts['token'],
    )


def _to_html_node(node):
    """Convert a normalized node into HTML markup."""
    node_type = node['type']

    if node_type == 'latex':
        return (
            '<section class="tex-node tex-root-node">'
            '<div class="tex-children">{contents}</div>'
            '</section>'
        ).format(contents=''.join(_to_html_node(content) for content in node['contents']))

    if node_type == 'env':
        return _to_html_branch(
            tag='env',
            name='\\begin{{{}}}'.format(node['name']),
            note=_child_note(node),
            meta='<code>{}</code><code>{}</code>'.format(
                escape(node['begin']), escape(node['end'])),
            contents=''.join(_to_html_node(content) for content in node['contents']),
            open_attr=' open',
        )

    if node_type == 'group':
        return _to_html_branch(
            tag='group',
            name='{} {} {}'.format(node['kind'], node['begin'], node['end']),
            note=_child_note(node),
            meta='<code>{}</code><code>{}</code>'.format(
                escape(node['begin']), escape(node['end'])),
            contents=''.join(_to_html_node(content) for content in node['contents']),
            open_attr='',
        )

    if node_type == 'cmd':
        return _to_html_leaf(node_type, node['source'])

    return _to_html_leaf(node_type, node['value'])


def _to_html_branch(tag, name, note, meta, contents, open_attr):
    """Render a branch node such as an environment or group."""
    return (
        '<details class="tex-node tex-{tag}"{open_attr}>'
        '<summary>'
        '<span class="tex-tag tex-tag-{tag}">{tag}</span>'
        '<code class="tex-name">{name}</code>'
        '<span class="tex-note">{note}</span>'
        '</summary>'
        '<div class="tex-meta">{meta}</div>'
        '<div class="tex-children">{contents}</div>'
        '</details>'
    ).format(
        tag=tag,
        name=escape(name),
        note=escape(note),
        meta=meta,
        contents=contents,
        open_attr=open_attr,
    )


def _to_html_leaf(node_type, value):
    """Render a leaf node such as text, token, or command."""
    if node_type == 'cmd':
        return (
            '<div class="tex-node tex-leaf tex-cmd">'
            '<span class="tex-tag tex-tag-cmd">cmd</span>'
            '<pre class="tex-source">{}</pre>'
            '</div>'
        ).format(escape(value))

    leaf_type = node_type
    display_value = value
    if node_type == 'text' and not value.strip():
        leaf_type = 'whitespace'
        display_value = value.encode('unicode_escape').decode('ascii') or "''"
    elif node_type == 'text' and value.lstrip().startswith('%'):
        leaf_type = 'comment'

    return (
        '<div class="tex-node tex-leaf tex-{type}">'
        '<span class="tex-tag tex-tag-{type}">{type}</span>'
        '<pre class="tex-source">{value}</pre>'
        '</div>'
    ).format(
        type=leaf_type,
        value=escape(display_value),
    )


def _child_note(node):
    """Return a human-readable child-count label."""
    count = len(node.get('contents', ()))
    return '{} {}'.format(count, 'child' if count == 1 else 'children')


def _count_nodes(node):
    """Count normalized export nodes by type."""
    counts = {
        'cmd': 0,
        'env': 0,
        'group': 0,
        'text': 0,
        'token': 0,
    }

    def visit(current):
        node_type = current['type']
        if node_type in counts:
            counts[node_type] += 1
        for child in current.get('contents', ()):
            visit(child)

    visit(node)
    return counts


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
