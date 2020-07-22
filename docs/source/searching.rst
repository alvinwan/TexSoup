.. _page-search:

Search
===================================

TexSoup supports a few search utilities, namely :code:`.find` and
:code:`.find_all`. The interface for both is identical. Here's the
:math:`\LaTeX` document from the quickstart guide::

    >>> tex_doc = """
    ... \begin{document}
    ... \section{Hello \textit{world}.}
    ... \subsection{Watermelon}
    ... (n.) A sacred fruit. Also known as:
    ... \begin{itemize}
    ...   \item red lemon
    ...   \item life
    ... \end{itemize}
    ... Here is the prevalence of each synonym, in Table \ref{table:synonyms}.
    ... \begin{tabular}{c c}\label{table:synonyms}
    ...   red lemon & uncommon \\ \n
    ...   life & common
    ... \end{tabular}
    ... \end{document}
    ... """
    >>> from TexSoup import TexSoup
    >>> soup = TexSoup(tex_doc)

Kinds of Filters
-----------------------------------

The simplest way to search is using a string filter::

    >>> soup.find_all('item')
    [\item red lemon
      , \item life
    ]

If you pass in a list, TexSoup will return results that match *any* item in
that list.

    >>> soup.find_all('item', 'textit')
    [\textit{world}, \item red lemon
      , \item life
    ]

You can also use regex compiled objects or regex strings with
:code:`.search_regex`.
