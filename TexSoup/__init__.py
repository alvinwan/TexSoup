"""TexSoup's main utility is the ``TexSoup`` function.

Invoke this function on a LaTeX string or file handler to obtain a parse
tree with navigation, search, and modification utilities.
"""

from TexSoup.tex import read
from TexSoup.data import TexNode

__version__ = '0.3.0'


# noinspection PyPep8Naming
def TexSoup(tex_code, skip_envs=(), tolerance=0):
    r"""
    At a high-level, parses provided Tex into a navigable, searchable
    structure. This is accomplished in two steps:

    1. Tex is parsed, cleaned, and packaged.
    2. Structure fed to TexNodes for a searchable, coder-friendly interface.

    :param Union[str,iterable] tex_code: the Tex source
    :param Union[str] skip_envs: names of environments to skip parsing
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :return: :class:`TexSoup.data.TexNode` object representing tex document

    >>> from TexSoup import TexSoup
    >>> soup = TexSoup(r'''
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
    ... red lemon & uncommon \\ \n
    ... life & common
    ... \end{tabular}
    ...
    ... \end{document}
    ... ''')
    >>> soup.section
    \section{Hello \textit{world}.}
    >>> soup.section.name
    'section'
    >>> soup.section.string
    'Hello \\textit{world}.'
    >>> soup.section.parent.name
    'document'
    >>> soup.tabular
    \begin{tabular}{c c}
    red lemon & uncommon \\ \n
    life & common
    \end{tabular}
    >>> soup.tabular.args[0].string
    'c c'
    >>> soup.itemize
    \begin{itemize}
    \item red lemon
    \item life
    \end{itemize}
    >>> soup.item
    \item red lemon
    <BLANKLINE>
    >>> list(soup.find_all('item'))
    [\item red lemon
    , \item life
    ]
    >>> soup = TexSoup(r'''\textbf{'Hello'}\textit{'Y'}O\textit{'U'}''')
    >>> soup.textbf.delete()
    >>> 'Hello' not in repr(soup)
    True
    >>> soup.textit.replace_with('S')
    >>> soup.textit.replace_with('U', 'P')
    >>> soup
    SOUP
    """
    parsed, src = read(tex_code, skip_envs=skip_envs, tolerance=tolerance)
    return TexNode(parsed, src=src)
