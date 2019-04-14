<a href="https://texsoup.alvinwan.com"><img src="https://user-images.githubusercontent.com/2068077/55692228-b7f92d00-595a-11e9-93a2-90090a361d12.png" width="80px"></a>

# [TexSoup](https://texsoup.alvinwan.com)

[![Build Status](https://travis-ci.org/alvinwan/TexSoup.svg?branch=master)](https://travis-ci.org/alvinwan/TexSoup)
[![Coverage Status](https://coveralls.io/repos/github/alvinwan/TexSoup/badge.svg?branch=master)](https://coveralls.io/github/alvinwan/TexSoup?branch=master)

TexSoup is a Python3 package for searching, navigating, and modifying LaTeX documents.

- [Installation](https://github.com/alvinwan/TexSoup#Installation)
- [Getting Started](https://github.com/alvinwan/TexSoup#Getting-Started)

Created by [Alvin Wan](http://alvinwan.com).

# Installation

## Pip

TexSoup is published via PyPi, so you can install it via `pip`. The package
name is `TexSoup`:

```bash
$ pip install texsoup
```

## From source

Alternatively, you can install the package from source:

```bash
$ git clone https://github.com/alvinwan/TexSoup.git
$ cd TexSoup
$ pip install .
```

# Getting Started

- [Quickstart Guide: how and when to use TexSoup](http://texsoup.alvinwan.com/docs/quickstart.html)
- [API Reference](http://texsoup.alvinwan.com/docs/data.html)
- [Example Use Cases: counting references, resolving imports, and more](https://github.com/alvinwan/TexSoup/tree/master/examples)

There is one main utility, `TexSoup`, which translates any $\LaTeX$ string or
iterator into a soupified object.

## Basic Usage

There are two ways to input $\LaTeX$ into TexSoup. Either pass in (1) a file
buffer (`open('file.tex')`) or (2) a string.

``` python
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

With the soupified $\LaTeX$, you can now search and traverse the document tree.
The code below demonstrates the basic functions that TexSoup provides.

```python
>>> soup.section  # grabs the first `section`
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

[See more in the Quickstart Guide &rarr;](https://texsoup.alvinwan.com/docs/quickstart.html)
