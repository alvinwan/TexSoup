from TexSoup import TexSoup


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
    assert str(children[0]) == '\section{Chikin Tales}'
    assert str(children[1]) == '\subsection{Chikin Fly}'
    assert children[2].name == 'itemize'
    assert len(children) == 3


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
    contents = list(doc.contents)
    assert len(list(doc.children)) == 3
    assert len(contents) == 4
