# TexSoup

[![Build Status](https://travis-ci.org/alvinwan/TexSoup.svg?branch=master)](https://travis-ci.org/alvinwan/TexSoup)
[![Coverage Status](https://coveralls.io/repos/github/alvinwan/TexSoup/badge.svg?branch=master)](https://coveralls.io/github/alvinwan/TexSoup?branch=master)

> This is a Python3 application that does not support Python2.

Parses valid LaTeX and provides a variety of BeautifulSoup-esque methods and Pythonic idioms for iterating and searching the parse tree. Unlike BeautifulSoup
however, TexSoup is modeled after an interpreter, providing a set of Pythonic
structures for processing environments, commands, and arguments.

created by [Alvin Wan](http://alvinwan.com)

# Installation

Just install via pip.

```
pip install texsoup
```

# Soup

There is one main utility, `TexSoup`, which translates any LaTeX string or
iterator into a soupified object.

## Basic Usage

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
[\item red lemon, \item life]
```

## Search

For (slightly) more advanced searches, include arguments. For example, to
search for all references to a particular label, search for `ref{<label>}`. This
way you can count the number of times a particular label is referenced.

```
>>> soup = TexSoup("""
... \section{Heading}\label{Section:Heading}
...
... Some text about the \ref{Section:Heading} heading goes here. Yet another
... sentence about the \ref{Section:Heading} heading.
... """)
>>> soup.count('\ref{Section:Heading}')
2
```

## Modification

Additionally, modify the TeX parse tree in place, to generate new LaTeX.

```
>>> soup = TexSoup("""\textbf{'Hello'}\textit{'Y'}O\textit{'U'}""")
>>> soup.textbf.delete()
>>> 'Hello' not in repr(soup)
True
>>> soup.textit.replace('S')
>>> soup.textit.replace('U', 'P')
>>> str(soup)
SOUP
```

# Parser

There is one main utility, `read`, which translates any LaTeX string or iterator
into a Python abstraction.

## Basic Usage

```
>>> from TexSoup import read
>>> expr = read('\section{textbf}')
>>> expr
TexCmd('section', [RArg('textbf')])
>>> print(expr)
\section{textbf}
```

# TexSoup in the Wild

TexSoup has a variety of practical applications, whether it be minor conveniences or more powerful LaTeX extensions. The below exhibits a few of these use cases, from simple reference counts to integration with computer algebra systems (coming soon).

## Examples

See the `examples/` folder for example scripts and usages for TexSoup.

- [Count References](https://github.com/alvinwan/TexSoup/blob/master/examples/count_references.py)
- [Solution Length](https://github.com/alvinwan/TexSoup/blob/master/examples/solution_length.py)
- [Resolve Imports](https://github.com/alvinwan/TexSoup/blob/master/examples/resolve_imports.py)

## Uses

See slightly more complex uses for TexSoup.

- [LaTex2Python](https://github.com/alvinwan/tex2py) converts LaTeX into a document tree, organizing content by either a default or custom hierarchy.
- [Tex2Ipy](https://github.com/prabhuramachandran/tex2ipy) by Prabhu Ramachandran, converts LaTeX beamer files to Jupyter notebooks
