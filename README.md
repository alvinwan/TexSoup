# TexSoup

Parses valid LaTeX and provides a variety of BeautifulSoup-esque methods and Pythonic idioms for iterating and searching the parse tree. Unlike BeautifulSoup
however, TexSoup is modeled after an interpreter, providing a set of Pythonic
structures for processing environments, commands, and arguments in anticipation
of integration with a CAS.

# Soup

There is one main utility, `TexSoup`, which translates any LaTeX string or
iterator into a soupified object.

## Starting with TexSoup

You have two options. Either give (1) a file buffer (`open('file.tex')`) or (2) a string.

```
from TexSoup import TexSoup
soup = TexSoup("""
\begin{document}

\section{Hello \textit{world}.}

\subsection{Watermelon}

(n.) A sacred fruit. Also known as:

\begin{itemize}
\item red lemon
\item life
\end{itemize}

Here is the prevalence of each synonym.

\begin{tabular}{c c}
red lemon & uncommon \\
life & common
\end{tabular}

\end{document}
""")
```

With the soupified LaTeX, you can now search and traverse the document tree.
The below is a demonstration of basic functions that TexSoup provides.

```
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
['\item red lemon', '\item life']
```

# Parser

There is one main utility, `read`, which translates any LaTeX string or iterator
into a Python abstraction.

## Starting with the Parser

```
>>> from TexSoup import read
>>> expr = read('\section{textbf}')
>>> expr
TexCmd('section', [RArg('textbf')])
>>> print(expr)
\section{textbf}
```
