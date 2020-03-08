Quick Start
===================================

The below illustrates major categories of features that TexSoup supports--how it
works, when it works, and how to leverage its utilities.

.. note:: Full disclaimer: I'm a big fan of BeautifulSoup documentation and
          modeled these guides after theirs.

How to Use
-----------------------------------

Here is a LaTeX document that we'll be using as an example throughout::

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

There are two ways to input $\LaTeX$ into TexSoup. Either pass in

1. a file buffer (`open('file.tex')`) OR
2. a string

Below, we demonstrate using the string defined above::

  >>> from TexSoup import TexSoup
  >>> soup = TexSoup(tex_doc)
  >>> soup
  \begin{document}
  \section{Hello \textit{world}.}
  \subsection{Watermelon}
  (n.) A sacred fruit. Also known as:
  \begin{itemize}
  \item red lemon
  \item life
  \end{itemize}
  Here is the prevalence of each synonym, in Table \ref{table:synonyms}.
  \begin{tabular}{c c}\label{table:synonyms}
  red lemon & uncommon \\ \n
  life & common
  \end{tabular}
  \end{document}

With the soupified :math:`\LaTeX`, you can now search and traverse the document tree.
The code below demonstrates the basic functions that TexSoup provides.::

  >>> soup.section
  \section{Hello \textit{world}.}
  >>> soup.section.name
  'section'
  >>> soup.section.string
  'Hello \\textit{world}.'
  >>> soup.section.parent.name
  'document'
  >>> soup.tabular
  \begin{tabular}{c c}\label{table:synonyms}
  red lemon & uncommon \\ \n
  life & common
  \end{tabular}
  >>> soup.tabular.args[0]
  'c c'
  >>> soup.item
  \item red lemon
  ...
  >>> list(soup.find_all('item'))
  [\item red lemon
  , \item life
  ]

One possible task is searching for references to a figure. For this (slightly)
more advanced search, include arguments. For example, to search for all
references to a particular label, search for ``ref{<label>}``. This way you can
count the number of times a particular label is referenced.::

  >>> soup.count(r'\ref{table:synonyms}')
  1

Another possible task is extracting all text from the page::

  >>> list(soup.text)
  ['Hello ', 'world', '.', 'Watermelon', '\n\n(n.) A sacred fruit. Also known as:\n\n', 'red lemon\n', 'life\n', '\n\nHere is the prevalence of each synonym.\n\n', '\nred lemon & uncommon \\\\ ', '\nlife & common\n']

If you need more flexibility and wish to build on top of the raw parse tree,
you may use the underlying data structures. For direct access to the raw data
structures, without a wrapper ``TexNode``, use the main parsing utility,
``read``, which translates any :math:`\LaTeX` string or iterator into a Python
data structure.

  >>> from TexSoup import read
  >>> expr = read('\section{textbf}')
  >>> expr
  TexCmd('section', [RArg('textbf')])
  >>> print(expr)
  \section{textbf}

Does this look promising? If so, see installation and more detailed usage
instructions below.

How to Install
-----------------------------------

TexSoup is published via PyPi, so you can install it via ``pip``. The package
name is ``TexSoup``::

  pip install TexSoup

Alternatively, you can install the package from source::

  git clone https://github.com/alvinwan/TexSoup.git
  cd TexSoup
  python setup.py install

Making a Soup
-----------------------------------

To parse a $LaTeX$ document, pass an open filehandle or a string into the
`TexSoup` constructor.
