from TexSoup import TexSoup


###############
# BASIC TESTS #
###############


#########
# CASES #
#########


def test_commands_without_arguments():
    """Tests that commands without arguments can still be searched."""
    soup = TexSoup(r"""
    \Question \textbf{Question Title}

    Here is what chickens do:

    \sol{They fly!}

    \Question
    \textbf{Question 2 Title}
    """)
    assert len(list(soup.find_all('Question'))) == 2


def test_commands_without_arguments_searchable():
    """Tests that command without arguments can still be found."""
    soup = TexSoup(r"""\Question (10 points)
This is the question here.

\Question (6 points)""")
    assert len(list(soup.find_all('Question'))) == 2
