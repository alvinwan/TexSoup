from TexSoup import TexSoup


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
    unalabeled environment.
    """
    soup = TexSoup(r"""{\color{blue} \textbf{This} \textit{is} some text.}""")
    assert len(list(soup.contents)) == 1, 'Environment not recognized.'
