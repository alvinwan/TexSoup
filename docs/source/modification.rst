Modification
===================================

You can also modify the document using the TexSoup tree, then export the changes
back to a :math:`\LaTeX` file.

Commands
-----------------------------------

As mentioned in :ref:`page-soup`, you can change commands and their arguments.

    >>> soup = TexSoup(r'I am \textbf{\large Large and bold}')
    >>> cmd = soup.textbf
    >>> cmd.name = 'textit'
    >>> cmd
    \textit{\large Large and bold}

You can set :code:`.string` for any single-argument command (e.g., :code:`\section`).

    >>> cmd.string = 'corgis are the best'
    >>> cmd
    \textit{corgis are the best}

You can do the same for any command in math mode.

    >>> soup2 = TexSoup(r'$$\textrm{math}\sum$$')
    >>> soup2.textrm.string = 'not math'
    >>> soup2
    $$\textrm{not math}\sum$$

You can also remove any command in-place, by calling :code:`.delete` on it.

    >>> soup2.textrm.delete()
    >>> soup2
    $$\sum$$

Arguments
-----------------------------------

You can modify arguments just as you would a list.

    >>> cmd.args.append('{moar}')
    >>> cmd
    \textit{corgis are the best}{moar}
    >>> cmd.args.remove('{moar}')
    >>> cmd
    \textit{corgis are the best}
    >>> cmd.args.extend(['[moar]', '{crazy}'])
    \textit{corgis are the best}[moar]{crazy}
    >>> cmd.args = cmd.args[:2]
    >>> cmd
    \textit{corgis are the best}[moar]

Use the argument's :code:`.string` attribute to modify the argument's contents.

    >>> cmd.args[0].string = 'no'
    >>> cmd
    \textit{no}[moar]

Environments
-----------------------------------

Use the :code:`.string` attribute to modify any environment with only text content
(i.e., a verbatim or math environment).

    >>> soup = TexSoup(r'\begin{verbatim}Huehue\end{verbatim}')
    >>> soup.verbatim.string = 'HUEHUE'
    >>> soup
    \begin{verbatim}HUEHUE\end{verbatim}
    >>> soup = TexSoup(r'$$\text{math}$$')
    >>> soup.text.string = ''

You can add to an environment's contents using list-like operations, like
:code:`.append`, :code:`.remove`, :code:`.insert`, and :code:`.extend`.

    >>> from TexSoup import TexSoup
    >>> soup = TexSoup(r'''
    ... \begin{itemize}
    ...     \item Hello
    ...     \item Bye
    ... \end{itemize}''')
    >>> tmp = soup.item
    >>> soup.itemize.remove(soup.item)
    >>> soup.itemize
    \begin{itemize}
    \item Bye
    \end{itemize}
    >>> soup.insert(1, tmp)
    >>> soup
    \begin{itemize}
    \item Hello
    \item Bye
    \end{itemize}

See :class:`TexSoup.data.TexNode` for more utilities.
