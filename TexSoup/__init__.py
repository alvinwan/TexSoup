"""
TexSoup
---

Main file, containing most commonly used elements of TexSoup

@author: Alvin Wan
@site: alvinwan.com
"""

from TexSoup.tex import *


def TexSoup(tex):
    r"""
    At a high-level, parses provided Tex into a navigable, searchable structure.
    This is accomplished in two steps:
    1. Tex is parsed, cleaned, and packaged.
    2. Structure fed to TexNodes for a searchable, coder-friendly interface.

    :param (iterable, string) tex: the Tex source
    :return TexNode: object representing tex document

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
    ... red lemon & uncommon \\
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
    red lemon & uncommon \\
    life & common
    \end{tabular}
    >>> soup.tabular.args[0]
    'c c'
    >>> soup.item
    \item red lemon
    >>> list(soup.find_all('item'))
    [\item red lemon, \item life]
    >>> soup = TexSoup(r'''\textbf{'Hello'}\textit{'Y'}O\textit{'U'}''')
    >>> soup.textbf.delete()
    >>> 'Hello' not in repr(soup)
    True
    >>> soup.textit.replace('S')
    >>> soup.textit.replace('U', 'P')
    >>> ''.join(str(soup).splitlines())
    'SOUP'
    """
    parsed, src = read(tex)
    return TexNode(parsed, src=src)
