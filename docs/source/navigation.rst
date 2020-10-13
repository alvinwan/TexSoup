Navigation
===================================

Here's the :math:`\LaTeX` document from the quickstart guide::

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

Going Down
-----------------------------------

Some expressions contain content. For example, environments may contain items.
TexSoup provides attributes for navigating an environment's children.

Naviate by naming the expression you want. For example, to access italicized
text, use :code:`soup.textit`::

    >>> soup.textit
    \textit{world}

You can use this to select expressions from a specific part of the document.
For example, this retrieves the an item from an itemize environment::

    >>> soup.itemize.item
    \item red lemon



Note accessing by name only returns the first result.

    >>> soup.item
    \item red lemon


To access *all* items, use one of the utilities from :ref:`page-search`, such
as :code:`find_all`::

    >>> soup.find_all('item')
    [\item red lemon
      , \item life
    ]

An environment's contents are accessible via a list called :code:`contents`.
Note that changing this list in-place will not affect the environment::

    >>> soup.itemize.contents
    [\item red lemon
      , \item life
    ]

There are several views into an environment's content:

- :code:`.children`: Nested Tex expressions. Does not include floating text.
- :code:`.contents`: Nested Tex expressions and text. Does not contain whitespace-only text.
- :code:`.expr.all`: Nested Tex expressions and text, regardless of whitespace or not. All information needed to reconstruct the original source.
- :code:`.descendants`: Tex expressions nested inside of Tex expressions.
- :code:`.text`: Used to "detex" a source file. Returns text from all descendants, without Tex expressions.

If a command has only one required argument, or an environment has only one
child, these values are made available as a :code:`.string`.

    >>> soup.textit.string
    'world'

Going Up
-----------------------------------

You can access an experssion's parent with the :code:`.parent` attribute::

    >>> soup.textit.parent
    \section{Hello \textit{world}.}
