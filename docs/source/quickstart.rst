Quick Start
===================================

The below illustrates major categories of features that TexSoup supports--how it
works, when it works, and how to leverage its utilities.

.. note:: Full disclaimer: I follow the same structure that the well-written
          BeautifulSoup docs do. So, if the guides look well-organized, thank
          BeautifulSoup. With that said, these are very much a work in progress.

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

Pass this document to ``TexSoup`` to obtain a fully-fledged parse tree::

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

Here are some simple ways to navigate this parse tree::

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

One possible task is retrieving the number of references to a figure::

  >>> soup.count(r'\ref{table:synonyms}')
  1

Another possible task is extracting all text from the page::

  >>> list(soup.text)
  ['Hello ', 'world', '.', 'Watermelon', '\n\n(n.) A sacred fruit. Also known as:\n\n', 'red lemon\n', 'life\n', '\n\nHere is the prevalence of each synonym.\n\n', '\nred lemon & uncommon \\\\ ', '\nlife & common\n']


How to Install
-----------------------------------

TexSoup is published via PyPi, so you can install it via ``pip``. The package
name is ``TexSoup``::

  pip install TexSoup

Alternatively, you can install the package from source::

  git clone https://github.com/alvinwan/TexSoup.git
  cd TexSoup
  python setup.py install
