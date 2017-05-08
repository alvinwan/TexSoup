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
    with_space_not_arg = TexSoup(r"""\Question (10 points)""")
    assert with_space_not_arg.Question is not None
    assert with_space_not_arg.Question.extra == '(10 points)'

    with_linebreak_not_arg = TexSoup(r"""\Question
(10 points)""")
    assert with_linebreak_not_arg.Question is not None
    assert with_linebreak_not_arg.Question.extra == ''

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
    """)
    verbatim = list(list(soup.children)[1].contents)[0]
    assert len(list(soup.contents)) == 3, 'Special environments not recognized.'
    assert str(list(soup.children)[0]) == \
           '\\begin{equation}\n\min_x \|Ax - b\|_2^2\n\\end{equation}'
    assert verbatim.startswith('    '), 'Whitespace not preserved.'
    assert str(list(soup.children)[2]) == \
        '$$\min_x \|Ax - b\|_2^2 + \lambda \|x\|_1^2$$'


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
    \item Ice cream costs \$4-\$5 around here.
    \end{itemize}""")
    assert '\\$4-\\$5' in str(soup), 'Escaped characters not properly rendered.'


##########
# ERRORS #
##########


def test_unclosed_environments():
    """Tests that unclosed environment results in error."""
    with pytest.raises(EOFError):
        TexSoup(r"""\begin{itemize}\item haha""")


def test_unclosed_math_environments():
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
