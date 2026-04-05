"""
Group Text Blocks
---

This script groups adjacent text that belongs together even when inline LaTeX
commands split it across multiple descendant nodes. Structural nodes such as
sectioning commands, environments, and ``\\item`` start new blocks.

To use it, run

    python text_blocks.py

after installing TexSoup.
"""

from textwrap import dedent

from TexSoup import TexSoup
from TexSoup.data import TexCmd, TexEnv, TexText
from TexSoup.utils import Token


SECTIONING_COMMANDS = (
    'part',
    'chapter',
    'section',
    'subsection',
    'subsubsection',
    'paragraph',
    'subparagraph',
)
TEXT_BLOCK_COMMANDS = frozenset(SECTIONING_COMMANDS + ('item',))


def starts_text_block(node):
    """Whether a node should start a new grouped text block."""
    expr = getattr(node, 'expr', node)
    if isinstance(expr, TexEnv):
        return True
    if isinstance(expr, TexCmd):
        return expr.name.rstrip('*') in TEXT_BLOCK_COMMANDS
    return False


def text_blocks(node):
    r"""Return grouped text blocks for the given TexSoup node.

    >>> soup = TexSoup(dedent(r'''
    ... \begin{document}
    ...
    ... \section{Hello \textit{world}.}
    ...
    ... \subsection{Watermelon}
    ...
    ... (n.) A sacred fruit. Also known as:
    ...
    ... \begin{itemize}
    ... \item red lemon
    ... \item life
    ... \end{itemize}
    ...
    ... Here is the prevalence of each synonym.
    ...
    ... \begin{tabular}{c c}
    ... red lemon & uncommon \\
    ... life & common
    ... \end{tabular}
    ...
    ... \end{document}
    ... ''').strip())
    >>> text_blocks(soup.document)[:6] == [
    ...     'Hello world.',
    ...     'Watermelon',
    ...     '(n.) A sacred fruit. Also known as:\n\n',
    ...     ' red lemon\n',
    ...     ' life\n',
    ...     '\nHere is the prevalence of each synonym.\n\n',
    ... ]
    True
    >>> text_blocks(soup.document)[6] == 'c c\nred lemon & uncommon \\\\\nlife & common\n'
    True
    >>> text_blocks(soup.section) == ['Hello world.']
    True
    >>> text_blocks(soup.itemize) == [' red lemon\n', ' life\n']
    True
    """
    block = []
    grouped = []

    def flush():
        if block:
            grouped.append(''.join(block))
            del block[:]

    for content in node.contents:
        if isinstance(content, (TexText, Token, str)):
            block.append(str(content))
            continue

        nested_blocks = text_blocks(content)
        if not nested_blocks:
            continue

        if starts_text_block(content):
            flush()
            grouped.extend(nested for nested in nested_blocks if nested)
            continue

        block.append(''.join(map(str, nested_blocks)))

    flush()
    return grouped


if __name__ == '__main__':
    soup = TexSoup(dedent(r"""
    \begin{document}

    \section{Hello \textit{world}.}

    \subsection{Watermelon}

    (n.) A sacred fruit. Also known as:

    \begin{itemize}
    \item red lemon
    \item life
    \end{itemize}
    \end{document}
    """).strip())
    print(text_blocks(soup.document))
