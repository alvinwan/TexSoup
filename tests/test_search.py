from TexSoup import TexSoup


###############
# BASIC TESTS #
###############


#########
# CASES #
#########


def test_commands_without_any_sort_arguments():
    """Tests that commands without any sort argument can still be searched."""
    soup = TexSoup(r"""
    \Question \textbf{Question Title}

    Here is what chickens do:

    \sol{They fly!}

    \Question
    \textbf{Question 2 Title}
    """)
    assert len(list(soup.find_all('Question'))) == 2
    assert soup.find('section') is None


def test_commands_with_one_or_more_arguments():
    """Tests that commands with one or more argument can still be searched."""
    soup = TexSoup(r"""
    \section{Chikin Tales}
    \subsection{Chikin Fly}
    \section{Chikin Sequel}
    """)
    assert len(list(soup.find_all('section'))) == 2
    assert soup.find('title') is None
