from TexSoup import TexSoup
import pytest


###############
# BASIC TESTS #
###############


def test_commands_only():
    """Tests that parser for commands-only string works."""
    soup = TexSoup(r"""
    \section{Chikin Tales}
    \subsection{Chikin Fly}
    """)
    children = list(soup.children)
    assert len(children) == 2
    assert str(children[0]) == '\section{Chikin Tales}'
    assert str(children[1]) == '\subsection{Chikin Fly}'


def test_commands_envs_only():
    """Tests that parser for commands-environments-only string works."""
    soup = TexSoup(r"""
    \section{Chikin Tales}
    \subsection{Chikin Fly}

    \begin{itemize}
    \item plop
    \item squat
    \end{itemize}
    """)
    children = list(soup.children)
    assert len(children) == 3
    assert str(children[0]) == '\section{Chikin Tales}'
    assert str(children[1]) == '\subsection{Chikin Fly}'
    itemize = children[2]
    assert itemize.name == 'itemize'
    items = list(itemize.children)
    assert len(items) == 2


def test_commands_envs_text():
    """Tests that parser for commands, environments, and strings work."""
    soup = TexSoup(r"""
    \begin{document}
    \section{Chikin Tales}
    \subsection{Chikin Fly}

    Here is what chickens do:

    \begin{itemize}
    \item plop
    \item squat
    \end{itemize}
    \end{document}
    """)
    assert len(list(soup.children)) == 1
    doc = next(soup.children)
    assert doc.name == 'document'
    contents, children = list(doc.contents), list(doc.children)
    assert str(children[0]) == '\section{Chikin Tales}'
    assert str(children[1]) == '\subsection{Chikin Fly}'
    assert len(children) == 3
    assert len(contents) == 4


#########
# CASES #
#########


def test_text_preserved():
    """Tests that the parser preserves regular non-expression text."""
    soup = TexSoup(r"""
    \Question \textbf{Question Title}

    Here is what chickens do:

    \sol{They fly!}
    """)
    assert 'Here is what chickens do:' in str(soup)


def test_command_name_parse():
    """Tests that the name of a command is parsed correctly.

    Arguments can be separated from a command name by at most one line break
    and any other whitespace.
    """
    with_space_not_arg = TexSoup(r"""\item (10 points)""")
    assert with_space_not_arg.item is not None
    assert with_space_not_arg.item.extra == '(10 points)'

    with_space_with_arg = TexSoup(r"""\section {hula}""")
    assert with_space_with_arg.section.string == 'hula'

    with_linebreak_with_arg = TexSoup(r"""\section
{hula}""")
    assert with_linebreak_with_arg.section.string == 'hula'


def test_commands_without_arguments():
    """Tests that commands without arguments are parsed correctly."""
    soup = TexSoup(r"""
    \Question \textbf{Question Title}

    Here is what chickens do:

    \sol{They fly!}

    \Question
    \textbf{Question 2 Title}
    """)
    assert len(list(soup.contents)) == 6
    assert soup[0].name.strip() == 'Question'
    assert len(list(soup.children)) == 5
    assert list(soup.children)[0].name.strip() == 'Question'


def test_unlabeled_environment():
    """Tests that unlabeled environment is parsed and recognized.

    Check that the environment is recognized not as an argument but as an
    unlabeled environment.
    """
    soup = TexSoup(r"""{\color{blue} \textbf{This} \textit{is} some text.}""")
    assert len(list(soup.contents)) == 1, 'Environment not recognized.'


def test_ignore_environment():
    """Tests that "ignore" environments are preserved (e.g., math, verbatim)."""
    soup = TexSoup(r"""
    \begin{equation}\min_x \|Ax - b\|_2^2\end{equation}
    \begin{verbatim}
    \min_x \|Ax - b\|_2^2 + \lambda \|x\|_2^2
    \end{verbatim}
    $$\min_x \|Ax - b\|_2^2 + \lambda \|x\|_1^2$$
    $$[0,1)$$
    """)
    verbatim = list(list(soup.children)[1].contents)[0]
    assert len(list(soup.contents)) == 4, 'Special environments not recognized.'
    assert str(list(soup.children)[0]) == \
           '\\begin{equation}\min_x \|Ax - b\|_2^2\\end{equation}'
    assert verbatim.startswith('\n    '), 'Whitespace not preserved.'
    assert str(list(soup.children)[2]) == \
        '$$\min_x \|Ax - b\|_2^2 + \lambda \|x\|_1^2$$'
    assert str(list(soup.children)[3]) == '$$[0,1)$$'


def test_inline_math():
    """Tests that inline math is rendered correctly."""
    soup = TexSoup("""
    \begin{itemize}
    \item This $e^{i\pi} = -1$
    \end{itemize}""")
    assert '$e^{i\pi} = -1$' in str(soup), 'Math environment not intact.'
    assert str(soup.item).endswith('$e^{i\pi} = -1$'), \
        'Inline environment not associated with correct expression.'


def test_escaped_characters():
    """Tests that special characters are escaped properly.

    Formerly, escaped characters would be rendered as latex commands.
    """
    soup = TexSoup("""
    \begin{itemize}
    \item Ice cream costs \$4-\$5 around here. \}\]\{\[
    \end{itemize}""")
    assert str(soup.item) == r'\item Ice cream costs \$4-\$5 around here. ' \
                             r'\}\]\{\['
    assert '\\$4-\\$5' in str(soup), 'Escaped characters not properly rendered.'


def test_math_environment_weirdness():
    """Tests that math environment interacts correctly with other envs."""
    soup = TexSoup(r"""\begin{a} \end{a}$ b$""")
    assert '$' not in str(soup.a), 'Math env snuck into begin env.'
    soup2 = TexSoup(r"""\begin{a} $ b$ \end{a}""")
    assert '$' in str(next(soup2.a.contents)), 'Math env not found in begin env'
    soup3 = TexSoup(r"""\begin{verbatim} $ \end{verbatim}""")
    assert soup3.verbatim is not None


def test_item_parsing():
    """Tests that item parsing is valid."""
    soup = TexSoup(r"""\item aaa {\bbb} ccc""")
    assert str(soup.item) == r'\item aaa {\bbb} ccc'
    soup2 = TexSoup(r"""\begin{itemize}
\item hello $\alpha$
\end{itemize}""")
    assert str(soup2.item) == r'\item hello $\alpha$'


def test_comment_escaping():
    """Tests that comments can be escaped properly."""
    soup = TexSoup(r"""\caption{ 30 \%}""")
    assert '%' in str(soup.caption), 'Comment not escaped properly'


def test_comment_unparsed():
    """Tests that comments are not parsed."""
    soup = TexSoup(r"""\caption{30} % \caption{...""")
    assert '%' not in str(soup.caption)



##############
# FORMATTING #
##############


def test_basic_whitespace():
    """Tests that basic text maintains whitespace."""
    soup = TexSoup("""
    Here is some text
    with a line break
    and awko      taco spacing
    """)
    assert len(str(soup).split('\n')) == 3, 'Line breaks not persisted.'


def test_whitespace_in_command():
    """Tests that whitespace in commands are maintained."""
    soup = TexSoup(r"""
    \begin{article}
    \title {This title contains    a space}
    \section {This title contains
    line break}
    \end{article}
    """)
    assert '    ' in soup.article.title.string
    assert '\n' in soup.article.section.string


def test_math_environment_whitespace():
    """Tests that math environments are untouched."""
    soup = TexSoup("""$$\lambda
    \Sigma$$ But don't mind me \$3.00""")
    children, contents = list(soup.children), list(soup.contents)
    assert '\n' in str(children[0]), 'Whitesapce not preserved in math env.'
    assert len(children) == 1 and children[0].name == '$$', 'Math env wrong'
    assert '\$' in contents[1], 'Dollar sign not escaped!'
    soup2 = TexSoup(r"""\gamma = \beta\begin{notescaped}\gamma = \beta\end{notescaped}
\begin{equation*}\beta = \gamma\end{equation*}""")
    assert str(soup2.find('equation*')) == \
           r'\begin{equation*}\beta = \gamma\end{equation*}'
    assert str(soup2).startswith(r'\gamma = \beta')
    assert str(soup2.notescaped) == \
           r'\begin{notescaped}\gamma = \beta\end{notescaped}'


def test_math_environment_escape():
    """Tests $ escapes in math environment."""
    soup = TexSoup("$ \$ $")
    contents = list(soup.contents)
    assert '\$' in contents[0][0], 'Dollar sign not escaped!'


def test_punctuation_command_structure():
    """Tests that commands for punctuation work."""
    soup = TexSoup(r"""\right. \right[ \right( \right|
    \right\langle \right\lfloor \right\lceil \right\ulcorner""")
    assert len(list(soup.contents)) == 8
    assert len(list(soup.children)) == 8


def test_non_punctuation_command_structure():
    """Tests that normal commands do not include punctuation in the command.

    However, the asterisk is one exception.
    """
    soup = TexSoup(r"""\mycommand, hello""")
    contents = list(soup.contents)
    assert '\mycommand' == str(contents[0]), \
        'Comma considered part of the command.'
    soup2 = TexSoup(r"""\hspace*{0.2in} hello \hspace*{2in} world""")
    assert len(list(soup2.contents)) == 4, '* not recognized as part of command.'


##########
# ERRORS #
##########


def test_unclosed_commands():
    """Tests that unclosed commands result in an error."""
    with pytest.raises(TypeError):
        TexSoup(r"""\textit{hello""")

    with pytest.raises(TypeError):
        TexSoup(r"""\textit{hello %}""")

    with pytest.raises(TypeError):
        TexSoup(r"""\textit{hello \\%}""")


def test_unclosed_environments():
    """Tests that unclosed environment results in error."""
    with pytest.raises(EOFError):
        TexSoup(r"""\begin{itemize}\item haha""")


def test_unclosed_math_environments():
    """Tests that unclosed math environment results in error."""
    with pytest.raises(EOFError):
        TexSoup(r"""$$\min_x \|Xw-y\|_2^2""")

    with pytest.raises(EOFError):
        TexSoup(r"""$\min_x \|Xw-y\|_2^2""")


def test_arg_parse():
    """Test arg parsing errors."""
    from TexSoup.data import Arg
    with pytest.raises(TypeError):
        Arg.parse(('{', ']'))

    with pytest.raises(TypeError):
        Arg.parse('(]')
