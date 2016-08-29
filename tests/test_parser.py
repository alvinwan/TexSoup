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


def test_commands_without_arguments():
    """Tests that commands without arguments are parsed correctly."""
    soup = TexSoup(r"""
    \Question \textbf{Question Title}

    Here is what chickens do:

    \sol{They fly!}
    """)
    assert len(list(soup.contents)) == 4
    assert soup[0].name.strip() == 'Question'
    assert len(list(soup.children)) == 3
    assert list(soup.children)[0].name.strip() == 'Question'
    assert len(list(soup.find_all('Question'))) == 1
