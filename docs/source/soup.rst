Soup
===================================

Making a Soup
-----------------------------------

To parse a :math:`\LaTeX` document, pass an open filehandle or a string into the
:code:`TexSoup` constructor::

    >>> from TexSoup import TexSoup
    >>> with open("main.tex") as f:
    ...     soup = TexSoup(f)
    >>> soup2 = TexSoup(r'\begin{document}Hello world!\end{document}')

Alternatively, compute the data structure only::

    >>> from TexSoup import read
    >>> soup3, _ = read(r'\begin{document}Hello world!\end{document}')
    >>> soup3
    [TexNamedEnv('document', ['Hello world!'], [])]

You can also ask TexSoup to tolerate :math:`\LaTeX` errors. In which case,
TexSoup will make a best-effort guess::

    >>> soup4 = TexSoup(r'\begin{itemize}\item hullo\end{enumerate}', tolerance=1)
    \begin{itemize}\item hullo\end{itemize}\end{enumerate}


Kinds of Objects
------------------------------------

TexSoup translates a :math:`\LaTeX` document into a tree of Python objects.
There are only three *kinds* of objects: commands, environments, and
text.

Command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A :code:`TexCmd` corresponds to a command in the original document::

    >>> soup = TexSoup(r'I am \textbf{\large Large and bold}')
    >>> cmd = soup.textbf
    >>> cmd
    \textbf{\large Large and bold}

You can access the underlying data structures using :code:`.expr`.

    >>> cmd.expr
    TexCmd('textbf', [BraceGroup(TexCmd('large'), ' Large and bold')])

Every command has a name::

    >>> cmd.name
    'textbf'

You can change the command's name too. This change will be reflected when you
convert the TexSoup back to :math:`\LaTeX`::

    >>> cmd.name = 'textit'
    >>> cmd
    \textit{\large Large and bold}
    >>> soup
    I am \textit{\large Large and bold}

Commands may have any number of arguments, stored in :code:`.args` as a list.
Our command has just one argument::

    >>> len(cmd.args)
    1
    >>> str(cmd.args[0])
    '{\\large Large and bold}'

You can add, remove, and modify arguments, treating :code:`.args` as a list::

    >>> cmd.args.append('{moar}')  # add arguments
    >>> str(cmd.args)
    '{\\large Large and bold}{moar}'
    >>> cmd.args.remove('{\large Large and bold}')  # remove arguments
    >>> str(cmd.args)
    '{moar}'
    >>> cmd.args[0].string = 'floating'  # modify arguments
    >>> str(cmd.args)
    '{floating}'

All arguments are represented using TexSoup's underlying data structures::

    >>> cmd.args
    [BraceGroup('floating')]

The above commands all apply to optional arguments as well. Note
that all changes are reflected when we convert the soup back to :math:`\LaTeX`::

    >>> cmd.args.append('[optional]')  # add optional arg
    >>> str(cmd.args)
    '{floating}[optional]'
    >>> cmd.args.remove('[optional]')  # remove optional arg
    >>> str(cmd.args)
    '{floating}'
    >>> soup
    I am \textit{floating}

Text
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note: If you've just started reading from this portion of the guide, start
         by defining :code:`soup = TexSoup(r'I am \textit{floating}')`.

A :code:`TexText` represents floating bits of text::

    >>> soup
    I am \textit{floating}
    >>> text = next(soup.contents)
    >>> text
    'I am '
    >>> type(text)
    <class 'TexSoup.data.TexText'>

You can set the :code:`.text` attribute. As before, this will be reflected
when you convert the data structure back into :math:`\LaTeX`.

    >>> text.text = 'I am not '
    >>> soup
    I am not \textit{floating}

Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Environments, or :code:`TexEnv`, are split into three types:

1. :code:`TexNamedEnv`: The typical environments you think of, with a begin
   and an end, such as :code:`\begin{itemize}...\end{itemize}`.
2. :code:`TexUnNamedEnv`: Special environments such as math :code:`\(...\)`.
   All math environments fall in this category.
3. :code:`TexGroup`: Unnamed environments with single-character delimiters,
   like :code:`{...}`.

You can access environments by name::

    >>> soup = TexSoup(r'Haha \begin{itemize}[label=\alph]\item Huehue\end{itemize}')
    >>> env = soup.itemize
    >>> env
    \begin{itemize}[label=\alph]\item Huehue\end{itemize}

Every environment's name can be accessed and modified using :code:`.name`::

    >>> env.name
    'itemize'
    >>> env.name = 'enumerate'
    >>> env
    \begin{enumerate}[label=\alph]\item Huehue\end{enumerate}
    >>> soup
    Haha \begin{enumerate}[label=\alph]\item Huehue\end{enumerate}

As with commands, environments store arguments in a list :code:`.args`::

    >>> str(env.args)
    '[label=\\alph]'

Each environment will contain variable amounts of content, accessible via
:code:`.contents`::

    >>> list(env.contents)
    [\item Huehue]
