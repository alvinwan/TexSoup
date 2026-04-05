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
    'em': 'em',
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
TRANSPARENT_ZERO_ARG_COMMANDS = {
    'centering',
    'footnotesize',
    'small',
    'tt',
}
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
    'verbatim',
}
SKIPPED_BODY_COMMANDS = {'author', 'date', 'maketitle', 'title'}
INVISIBLE_COMMANDS = {
    'bigskip',
    'bibliographystyle',
    'label',
    'medskip',
    'newpage',
    'newblock',
    'noindent',
    'pagebreak',
    'smallskip',
    'vspace',
    'vspace*',
}
TABULAR_ENVS = {'tabular', 'tabular*'}
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
    context = _collect_render_context(body_nodes)
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
    .tex-anchor {{
      display: block;
      position: relative;
      top: -1rem;
      visibility: hidden;
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
    .tex-bibliography ol {{
      margin: 0;
      padding-left: 1.4rem;
    }}
    .tex-bibliography li {{
      margin: 0 0 0.95rem;
    }}
    .tex-bibliography li p:last-child {{
      margin-bottom: 0;
    }}
    .tex-table-wrap {{
      overflow-x: auto;
    }}
    .tex-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
      background: rgba(255, 255, 255, 0.72);
    }}
    .tex-table th,
    .tex-table td {{
      padding: 0.55rem 0.7rem;
      border: 1px solid rgba(218, 200, 175, 0.9);
      vertical-align: top;
    }}
    .tex-table th {{
      background: rgba(138, 75, 23, 0.08);
      text-align: left;
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
        frontmatter=_render_frontmatter(metadata, context),
        body=_render_blocks(body_nodes, context),
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
        'title_nodes': (),
        'title_text': '',
        'author_nodes': (),
        'date_nodes': (),
        'abstract_nodes': (),
        'mathjax_macros': _collect_mathjax_macros(preamble_nodes),
    }

    for node in preamble_nodes + body_nodes:
        if isinstance(node, TexCmd) and node.name in ('title', 'author', 'date') and node.args:
            text = str(node.args[0].string).strip()
            metadata['%s_nodes' % node.name] = list(node.args[0].contents)
            metadata['%s_text' % node.name] = text
        if isinstance(node, TexNamedEnv) and node.name == 'abstract' and not metadata['abstract_nodes']:
            metadata['abstract_nodes'] = list(_body_contents(node))

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


def _render_frontmatter(metadata, context):
    """Render document frontmatter."""
    parts = []
    title_html = _render_inline_nodes(metadata['title_nodes'], context)
    author_html = _render_inline_nodes(metadata['author_nodes'], context)
    date_html = _render_inline_nodes(metadata['date_nodes'], context)
    abstract_html = _render_blocks(metadata['abstract_nodes'], context) if metadata['abstract_nodes'] else ''
    if title_html or author_html or date_html:
        parts.append('<header class="tex-frontmatter">')
        if title_html:
            parts.append('<h1 class="tex-paper-title">{}</h1>'.format(title_html))
        if author_html:
            parts.append('<p class="tex-paper-authors">{}</p>'.format(author_html))
        if date_html:
            parts.append('<p class="tex-paper-date">{}</p>'.format(date_html))
        parts.append('</header>')
    if abstract_html:
        parts.append(
            '<section class="tex-abstract"><h2>Abstract</h2>{}</section>'.format(
                abstract_html)
        )
    return ''.join(parts)


def _collect_render_context(nodes):
    """Collect anchors and bibliography metadata for rendered links."""
    context = {
        'labels': {},
        'bibitems': {},
    }
    bibliography_index = 1

    def visit(current_nodes):
        nonlocal bibliography_index
        for node in current_nodes:
            if isinstance(node, TexCmd) and node.name == 'label' and node.args:
                label = str(node.args[0].string)
                context['labels'][label] = _anchor_id('label', label)
            if isinstance(node, TexNamedEnv) and node.name == 'thebibliography':
                for child in _body_contents(node):
                    if isinstance(child, TexCmd) and child.name == 'bibitem':
                        key = _bibitem_key(child)
                        if key not in context['bibitems']:
                            context['bibitems'][key] = {
                                'id': _anchor_id('bib', key),
                                'display': str(bibliography_index),
                            }
                            bibliography_index += 1
            if isinstance(node, TexNamedEnv):
                visit(_body_contents(node))
            elif isinstance(node, TexGroup):
                visit(list(node.contents))
            elif isinstance(node, TexCmd) and getattr(node, '_contents', None):
                visit(node._contents)

    visit(nodes)
    return context


def _body_contents(node):
    """Return rendered body contents, excluding environment args."""
    return list(getattr(node, '_contents', ()))


def _anchor_id(prefix, value):
    """Create a stable anchor id for a LaTeX label."""
    slug = re.sub(r'[^A-Za-z0-9._-]+', '-', value).strip('-').lower()
    return '%s-%s' % (prefix, slug or 'item')


def _link_target(label, context):
    """Resolve a label or bibliography key to an anchor link."""
    if label in context['labels']:
        return '#%s' % context['labels'][label]
    if label in context['bibitems']:
        return '#%s' % context['bibitems'][label]['id']
    return '#%s' % _anchor_id('label', label)


def _resolve_href(target, context):
    """Resolve an internal label or preserve an external URL target."""
    if re.match(r'^(?:https?|mailto):', target):
        return target
    if target.startswith('#'):
        return target
    return _link_target(target, context)


def _reference_text(command_name, target):
    """Return fallback display text for a reference command."""
    if command_name == 'eqref':
        return '(%s)' % target
    return target


def _first_label(node):
    """Return the first top-level label attached to a parsed node."""
    for child in _body_contents(node):
        if isinstance(child, TexCmd) and child.name == 'label' and child.args:
            return str(child.args[0].string)
    return None


def _strip_math_labels(source):
    """Remove label commands from rendered display math source."""
    return re.sub(r'\\label\{[^{}]+\}', '', source)


def _color_to_css(model, value):
    """Convert a LaTeX color declaration to a CSS color string."""
    value = value.strip()
    if not model:
        return value

    model = model.strip().lower()
    if model == 'html':
        return '#%s' % value.lstrip('#')

    components = [part.strip() for part in value.split(',') if part.strip()]
    if model in ('rgb', 'rgb*') and len(components) == 3:
        floats = [float(component) for component in components]
        if all(component <= 1 for component in floats):
            floats = [round(component * 255) for component in floats]
        return 'rgb({})'.format(', '.join(str(int(component)) for component in floats))
    if model == 'gray' and len(components) == 1:
        component = float(components[0])
        if component <= 1:
            component *= 255
        component = int(round(component))
        return 'rgb({0}, {0}, {0})'.format(component)
    return value


def _render_color_command(node, context):
    """Render \\color or \\textcolor as a styled inline span."""
    if not node.args:
        return ''

    model = None
    value_index = 0
    body_index = 1
    if str(node.args[0]).startswith('['):
        model = node.args[0].string
        value_index = 1
        body_index = 2
    if len(node.args) <= body_index:
        return ''

    css = _color_to_css(model, node.args[value_index].string)
    body = _render_inline_nodes(list(node.args[body_index].contents), context)
    if not body:
        body = escape(str(node.args[body_index].string))
    return '<span style="color: {color}">{body}</span>'.format(
        color=escape(css), body=body)


def _render_citation(node, context):
    """Render a citation command as linked bibliography references."""
    keys = []
    for arg in node.args:
        keys.extend(key.strip() for key in arg.string.split(',') if key.strip())

    rendered = []
    for key in keys:
        entry = context['bibitems'].get(key)
        label = entry['display'] if entry else key
        href = '#%s' % entry['id'] if entry else _link_target(key, context)
        rendered.append('<a class="tex-reference" href="{href}">{label}</a>'.format(
            href=escape(href), label=escape(label)))
    return '[{}]'.format(', '.join(rendered))


def _bibitem_key(node):
    """Return the bibliography key for a \\bibitem command."""
    if not node.args:
        return str(node)
    return str(node.args[-1].string)


def _render_blocks(nodes, context):
    """Render a sequence of parsed nodes as block HTML."""
    blocks = []
    inline = []
    for node in nodes:
        if _skip_body_node(node):
            continue
        if _is_block_node(node):
            _flush_paragraph(blocks, inline)
            rendered = _render_block_node(node, context)
            if rendered:
                blocks.append(rendered)
            continue

        for fragment in _render_inline_segments(node, context):
            if fragment is PARAGRAPH_BREAK:
                _flush_paragraph(blocks, inline)
            elif fragment:
                inline.append(fragment)
    _flush_paragraph(blocks, inline)
    return ''.join(blocks)


def _render_inline_nodes(nodes, context):
    """Render parsed nodes as inline HTML."""
    fragments = []
    for node in nodes:
        if _skip_body_node(node):
            continue
        if _is_block_node(node):
            rendered = _render_block_node(node, context)
            if rendered:
                fragments.append(rendered)
            continue
        for fragment in _render_inline_segments(node, context):
            if fragment is not PARAGRAPH_BREAK and fragment:
                fragments.append(fragment)
    return ''.join(fragments).strip()


def _render_inline_segments(node, context):
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
    rendered = _render_inline_node(node, context)
    return [rendered] if rendered else []


def _render_inline_node(node, context):
    """Render a single node as inline HTML."""
    if isinstance(node, TexGroup):
        return _render_inline_nodes(list(node.contents), context)
    if isinstance(node, (TexMathEnv, TexMathModeEnv)):
        return '<span class="tex-math">{}</span>'.format(escape(str(node)))
    if not isinstance(node, TexCmd):
        return '<span class="tex-inline-raw">{}</span>'.format(escape(str(node)))
    if node.name in SKIPPED_BODY_COMMANDS or node.name in ('caption', 'maketitle'):
        return ''
    if node.name in INVISIBLE_COMMANDS:
        if node.name == 'label' and node.args:
            label = str(node.args[0].string)
            anchor_id = context['labels'].get(label, _anchor_id('label', label))
            return '<a class="tex-anchor" id="{anchor}"></a>'.format(anchor=escape(anchor_id))
        return ''
    if node.name in INLINE_COMMANDS and node.args:
        return _wrap_inline(INLINE_COMMANDS[node.name], _render_inline_nodes(list(node.args[0].contents), context))
    if node.name in TRANSPARENT_COMMANDS and node.args:
        return _render_inline_nodes(list(node.args[0].contents), context)
    if node.name in TRANSPARENT_ZERO_ARG_COMMANDS:
        return ''
    if node.name in ('color', 'textcolor'):
        return _render_color_command(node, context)
    if node.name == 'url' and node.args:
        href = escape(str(node.args[-1].string))
        return '<a class="tex-link" href="{href}">{href}</a>'.format(href=href)
    if node.name == 'href' and len(node.args) >= 2:
        href = escape(str(node.args[0].string))
        label = _render_inline_nodes(list(node.args[1].contents), context)
        return '<a class="tex-link" href="{href}">{label}</a>'.format(href=href, label=label)
    if node.name == 'hyperref' and len(node.args) >= 2:
        href = escape(_resolve_href(str(node.args[0].string), context))
        label = _render_inline_nodes(list(node.args[1].contents), context)
        return '<a class="tex-link" href="{href}">{label}</a>'.format(href=href, label=label)
    if node.name == 'hyperlink' and len(node.args) >= 2:
        href = escape(_resolve_href(str(node.args[0].string), context))
        label = _render_inline_nodes(list(node.args[1].contents), context)
        return '<a class="tex-link" href="{href}">{label}</a>'.format(href=href, label=label)
    if node.name == 'hypertarget' and len(node.args) >= 2:
        anchor = _anchor_id('label', str(node.args[0].string))
        label = _render_inline_nodes(list(node.args[1].contents), context)
        return '<a class="tex-anchor" id="{anchor}"></a>{label}'.format(
            anchor=escape(anchor), label=label)
    if node.name in REFERENCE_COMMANDS and node.args:
        if node.name.startswith('cite'):
            return _render_citation(node, context)
        target = str(node.args[0].string)
        return '<a class="tex-reference" href="{href}">{label}</a>'.format(
            href=escape(_link_target(target, context)),
            label=escape(_reference_text(node.name, target)))
    if node.name == 'thanks' and node.args:
        return '<span class="tex-footnote">({})</span>'.format(
            _render_inline_nodes(list(node.args[0].contents), context))
    if node.name == 'footnote' and node.args:
        return '<span class="tex-footnote">({})</span>'.format(
            _render_inline_nodes(list(node.args[0].contents), context))
    if node.name == 'checkmark':
        return '&#10003;'
    if node.name == 'multicolumn' and node.args:
        return _render_inline_nodes(list(node.args[-1].contents), context)
    if node.name in ('\\', 'newline'):
        return '<br />'
    return '<span class="tex-inline-raw">{}</span>'.format(escape(str(node)))


def _render_block_node(node, context):
    """Render a single node as block HTML."""
    if isinstance(node, TexGroup):
        return _render_blocks(list(node.contents), context)
    if isinstance(node, (TexDisplayMathEnv, TexDisplayMathModeEnv)):
        return _render_math_block(str(node))
    if isinstance(node, TexNamedEnv):
        if node.name == 'document':
            return _render_blocks(_body_contents(node), context)
        if node.name == 'abstract':
            return ''
        if node.name == 'thebibliography':
            return _render_bibliography(node, context)
        if node.name in LIST_ENVS:
            return _render_list(node, context)
        if node.name in ('figure', 'figure*'):
            return _render_figure(node, class_name='tex-figure', context=context)
        if node.name in ('table', 'table*'):
            return _render_figure(node, class_name='tex-table-block', context=context)
        if node.name in DISPLAY_MATH_ENVS:
            label = _first_label(node)
            anchor_id = context['labels'].get(label) if label else None
            return _render_math_block(_strip_math_labels(str(node)), anchor_id=anchor_id)
        if node.name in TABULAR_ENVS:
            return _render_tabular(node, context)
        if node.name in RAW_BLOCK_ENVS:
            return _render_raw_block(node, class_name='tex-raw-block')
        if node.name in ('quote', 'quotation'):
            return '<blockquote>{}</blockquote>'.format(_render_blocks(_body_contents(node), context))
        if node.name == 'center':
            return '<div class="tex-generic-block" style="text-align:center">{}</div>'.format(
                _render_blocks(_body_contents(node), context))
        return (
            '<section class="tex-generic-block">'
            '<div class="tex-env-label">\\begin{{{name}}}</div>'
            '{contents}'
            '<div class="tex-env-label">\\end{{{name}}}</div>'
            '</section>'
        ).format(name=escape(node.name), contents=_render_blocks(_body_contents(node), context))
    if isinstance(node, TexCmd):
        if node.name in SECTION_LEVELS:
            return _render_heading(node, context)
        if node.name == 'includegraphics':
            return _render_includegraphics(node)
        if node.name == 'caption' and node.args:
            return '<div class="tex-caption">{}</div>'.format(
                _render_inline_nodes(list(node.args[0].contents), context))
        if node.name == 'item':
            return _render_list_item(node, context)
        return ''
    return '<div class="tex-raw-block"><pre class="tex-source">{}</pre></div>'.format(
        escape(str(node)))


def _render_heading(node, context):
    """Render a sectioning command as a heading."""
    level = SECTION_LEVELS[node.name]
    title = _render_inline_nodes(list(node.args[0].contents), context) if node.args else escape(node.name)
    return '<h{level}>{title}</h{level}>'.format(level=level, title=title)


def _render_list(env, context):
    """Render itemize/enumerate/description environments."""
    items = [
        _render_list_item(child, context)
        for child in _body_contents(env)
        if isinstance(child, TexCmd) and child.name == 'item'
    ]
    if not items:
        return _render_raw_block(env, class_name='tex-raw-block')
    tag = LIST_ENVS[env.name]
    return '<{tag}>{items}</{tag}>'.format(tag=tag, items=''.join(items))


def _render_list_item(item, context):
    """Render a list item."""
    body = _render_blocks(list(item.contents), context).strip()
    if not body:
        body = _render_inline_nodes(list(item.contents), context)
    return '<li>{}</li>'.format(body)


def _render_figure(env, class_name, context):
    """Render figure-like environments."""
    caption = ''
    parts = []
    for child in _body_contents(env):
        if isinstance(child, TexCmd) and child.name == 'caption' and child.args:
            caption = _render_inline_nodes(list(child.args[0].contents), context)
            continue
        if _is_block_node(child):
            rendered = _render_block_node(child, context)
        else:
            rendered = _render_inline_nodes([child], context)
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


def _render_bibliography(env, context):
    """Render thebibliography as a linked references section."""
    entries = []
    current = None
    for child in _body_contents(env):
        if isinstance(child, TexCmd) and child.name == 'bibitem':
            if current is not None:
                entries.append(current)
            key = _bibitem_key(child)
            current = {'key': key, 'nodes': []}
            continue
        if current is not None:
            current['nodes'].append(child)
    if current is not None:
        entries.append(current)

    items = []
    for entry in entries:
        meta = context['bibitems'].get(entry['key'], {
            'id': _anchor_id('bib', entry['key']),
            'display': entry['key'],
        })
        items.append(
            '<li id="{anchor}">{body}</li>'.format(
                anchor=escape(meta['id']),
                body=_render_blocks(entry['nodes'], context),
            )
        )
    return '<section class="tex-bibliography"><h2>References</h2><ol>{}</ol></section>'.format(
        ''.join(items))


def _render_tabular(env, context):
    """Render a basic tabular environment as an HTML table."""
    body_contents = list(_body_contents(env))
    if body_contents and str(body_contents[0]).strip().startswith('{'):
        body_contents = body_contents[1:]
    text = ''.join(map(str, body_contents))
    rows = []
    for raw_row in re.split(r'\\\\|\\tabularnewline', text):
        row = raw_row.strip()
        if not row:
            continue
        row = re.sub(r'\\(toprule|midrule|bottomrule|hline)\b', '', row)
        row = re.sub(r'\\(c|x)?midrule(?:\[[^\]]*\])?\{[^{}]*\}', '', row)
        row = re.sub(r'\\cline\{[^{}]*\}', '', row).strip()
        if not row:
            continue
        cells = [cell.strip() for cell in row.split('&')]
        rows.append(cells)
    if not rows:
        return _render_raw_block(env, class_name='tex-raw-block')

    rendered_rows = []
    for index, row in enumerate(rows):
        tag = 'th' if index == 0 else 'td'
        rendered_cells = ''.join(
            '<{tag}>{cell}</{tag}>'.format(
                tag=tag,
                cell=_render_inline_tex(cell, context),
            )
            for cell in row
        )
        rendered_rows.append('<tr>{}</tr>'.format(rendered_cells))
    return '<div class="tex-table-wrap"><table class="tex-table">{}</table></div>'.format(
        ''.join(rendered_rows))


def _render_inline_tex(source, context):
    """Render a small LaTeX fragment inline."""
    try:
        from TexSoup import TexSoup
        parsed = TexSoup(source, tolerance=1)
    except Exception:
        return escape(_normalize_inline_text(source))
    return _render_inline_nodes(list(parsed.expr.contents), context) or escape(
        _normalize_inline_text(source))


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


def _render_math_block(source, anchor_id=None):
    """Render display math using MathJax delimiters."""
    attrs = ' class="tex-math-block"'
    if anchor_id:
        attrs += ' id="%s"' % escape(anchor_id)
    return '<div{attrs}>{source}</div>'.format(
        attrs=attrs,
        source=escape(source),
    )


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
        return any(_is_block_node(child) for child in node.contents)
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
