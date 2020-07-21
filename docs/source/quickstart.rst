Quick Start
===================================

The below illustrates some basic TexSoup functions.

How to Use
-----------------------------------

Here is a :math:`\LaTeX` document::

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

Call :code:`TexSoup` on this string to re-represent this document as a
nested data structure::

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

Here are a few ways to navigate the TexSoup data structure::

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

  >>> list(soup.find_all('item'))
  [\item red lemon
    , \item life
  ]

One task may be to find all references. To do this, simply search for
``\ref{<label>}``. You can even report each reference's line number::

  >>> soup.count(r'\ref{table:synonyms}')
  1
  >>> for cmd in soup.find_all(r'\ref{table:synonyms}'):
  ...   soup.char_pos_to_line(cmd.position)
  (8, 49)

Another task may be to extract all text from the page::

  >>> list(soup.text)
  ['Hello ', 'world', '.', 'Watermelon', '\n\n(n.) A sacred fruit. Also known as:\n\n', 'red lemon\n', 'life\n', '\n\nHere is the prevalence of each synonym.\n\n', '\nred lemon & uncommon \\\\ ', '\nlife & common\n']

Does this look promising? If so,
`try TexSoup online <https://repl.it/@ALVINWAN1/texsoup>`_ or read on to
install.

How to Install
-----------------------------------

TexSoup is published via PyPi, so you can install it via ``pip``. The package
name is ``TexSoup``::

  pip install TexSoup

Alternatively, you can install the package from source::

  git clone https://github.com/alvinwan/TexSoup.git
  cd TexSoup
  python setup.py install
