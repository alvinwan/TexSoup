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
    assert str(children[0]) == r'\section{Chikin Tales}'
    assert str(children[1]) == r'\subsection{Chikin Fly}'


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
    assert str(children[0]) == r'\section{Chikin Tales}'
    assert str(children[1]) == r'\subsection{Chikin Fly}'
    itemize = children[2]
    assert itemize.name == 'itemize'
    items = list(itemize.children)
    assert len(items) == 2


def test_commands_envs_text():
    """Tests that parser for commands, environments, and strings work."""
    soup = TexSoup(r"""
    \begin{document}
    \title{Chikin}
    \date{\today}
    \section
    [Tales]{Chikin Tales}
    \subsection
    {Chikin Fly}

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
    assert str(children[0]) == r'\title{Chikin}'
    assert str(children[1]) == r'\date{\today}'
    assert str(children[2]) == r'\section[Tales]{Chikin Tales}'
    assert str(children[3]) == r'\subsection{Chikin Fly}'
    assert len(children) == 5
    assert len(contents) == 6
    everything = list(doc.expr.all)
    assert len(everything) == 12
    # arguments = str(doc.section.expr.arguments)
    # assert arguments == "\n    [Tales]{Chikin Tales}"
    # arguments_list = [str(arg) for arg in doc.section.expr.arguments]
    # assert arguments_list == ['\n    ', '[Tales]', '{Chikin Tales}']


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
    assert len(list(with_space_not_arg.item.contents)) == 1
    assert next(with_space_not_arg.item.contents) == '(10 points)'

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
    \[[0,1)\]
    \begin{flalign} will break if TexSoup starts parsing math[ \end{flalign}
    \begin{align*} hah [ \end{align*}
    """)
    verbatim = list(list(soup.children)[1].contents)[0]
    assert len(list(soup.contents)) == 6, 'Special environments not recognized.'
    assert str(list(soup.children)[0]) == r'\begin{equation}\min_x \|Ax - b\|_2^2\end{equation}'
    # hacky workaround for odd string types
    assert verbatim[0] == '\n' and verbatim[1:].startswith('   '), 'Whitespace not preserved: {}'.format(verbatim)
    assert str(list(soup.children)[2]) == r'$$\min_x \|Ax - b\|_2^2 + \lambda \|x\|_1^2$$'
    assert str(list(soup.children)[3]) == r'\[[0,1)\]'


def test_inline_math():
    """Tests that inline math is rendered correctly."""
    soup = TexSoup(r"""
    \begin{itemize}
    \item This $e^{i\pi} = -1$
    \item How \(e^{i\pi} + 1 = 0\)
    \item Therefore!
    \end{itemize}""")
    assert r'$e^{i\pi} = -1$' in str(soup), 'Math environment not kept intact.'
    assert r'$e^{i\pi} = -1$' in str(list(soup.itemize.children)[0]), 'Environment incorrectly associated.'
    assert r'\(e^{i\pi} + 1 = 0\)' in str(soup), 'Math environment not kept intact.'
    assert r'\(e^{i\pi} + 1 = 0\)' in str(list(soup.itemize.children)[1]), 'Environment incorrectly associated.'


def test_escaped_characters():
    """Tests that special characters are escaped properly.
    Formerly, escaped characters would be rendered as latex commands.
    """
    soup = TexSoup(r"""
    \begin{itemize}
    \item Ice cream costs \$4-\$5 around here. \}[\{]
    \end{itemize}""")
    assert str(soup.item).strip() == r'\item Ice cream costs \$4-\$5 around here. \}[\{]'
    assert '\\$4-\\$5' in str(soup), 'Escaped characters not properly rendered.'


def test_math_environment_weirdness():
    """Tests that math environment interacts correctly with other envs."""
    soup = TexSoup(r"""\begin{a} \end{a}$ b$""")
    assert '$' not in str(soup.a), 'Math env snuck into begin env.'
    soup = TexSoup(r"""\begin{a} $ b$ \end{a}""")
    assert '$' in str(next(soup.a.contents)), 'Math env not found in begin env'
    soup = TexSoup(r"""\begin{verbatim} $ \end{verbatim}""")
    assert soup.verbatim is not None
    # GH48
    soup = TexSoup(r"""a\\$a$""")
    assert '$' in str(soup), 'Math env not correctly parsed after \\\\'
    # GH55
    soup = TexSoup(r"""\begin{env} text\\$formula$ \end{env}""")
    assert '$' in str(soup.env), 'Math env not correctly parsed after \\\\'


def test_item_parsing():
    """Tests that item parsing is valid."""
    soup = TexSoup(r"""\item aaa {\bbb} ccc""")
    assert str(soup.item) == r'\item aaa {\bbb} ccc'
    soup = TexSoup(r"""\begin{itemize}
    \item hello $\alpha$
    \end{itemize}""")
    assert str(soup.item).strip() == r'\item hello $\alpha$'
    soup = TexSoup(r"""\begin{itemize}
    \item
    \item first item
    \end{itemize}""")
    assert len(list(soup.item.contents)) == 0, \
        "Zeroth item should have no contents"
    soup = TexSoup(r"""\begin{itemize}
    \item second item
    \item


    third item
    with third item

    floating text
    \end{itemize}""")
    items = list(soup.find_all('item'))
    content = next(items[1].contents)
    assert 'third item' in content, 'Item does not tolerate starting line breaks (as it should)'
    assert 'with' in content, 'Item does not tolerate line break in middle (as it should)'
    assert 'floating' not in content, 'Item should not tolerate multiple line breaks in middle'
    soup = TexSoup(r"""\begin{itemize}
    \item This item contains code!
    \begin{lstlisting}
    Code code code
    \end{lstlisting}
    \item hello
    \end{itemize}""")
    assert ' Code code code' in str(soup.item.lstlisting), 'Item does not correctly parse contained environments.'
    assert '\n    Code code code\n    ' in soup.item.lstlisting.expr.contents
    soup = TexSoup(r"""\begin{itemize}
    \item\label{some-label} waddle
    \item plop
    \end{itemize}""")
    assert str(soup.item.label) == r'\label{some-label}'


def test_item_argument_parsing():
    """Tests that item arguments are correctly associated with item."""
    soup = TexSoup(r"""\item[marker]""")
    assert str(soup.item) == r'\item[marker]'


def test_comment_escaping():
    """Tests that comments can be escaped properly."""
    soup = TexSoup(r"""\caption{ 30 \%}""")
    assert '%' in str(soup.caption), 'Comment not escaped properly'


def test_comment_unparsed():
    """Tests that comments are not parsed."""
    soup = TexSoup(r"""\caption{30} % \caption{...""")
    assert '%' not in str(soup.caption)


def test_items_with_labels():
    """Items can have labels with square brackets such as in the description
    environment. See Issue #32."""
    soup = TexSoup(r"""\begin{description}
    \item[Python] a high-level general-purpose interpreted programming language.
    \end{description}""")
    assert "Python" in soup.description.item.args


def test_multiline_args():
    """Tests that macros with arguments are different lines are parsed
    properly. See Issue #31."""
    soup = TexSoup(r"""\mytitle{Essay title}
    {Essay subheading.}""")
    assert "Essay subheading." in soup.mytitle.args
    # Only one newline allowed
    soup = TexSoup(r"""\mytitle{Essay title}

    {Essay subheading.}""")
    assert "Essay subheading." not in soup.mytitle.args
    assert "Essay title" in soup.mytitle.args
    soup = TexSoup(r"""\title{Arguments}
    {appear}
    \subtitle{everywhere}
    in \LaTeX.

    \date{\today}
    """)
    assert "Arguments" in soup.title.args
    assert "appear" in soup.title.args
    assert "everywhere" in soup.subtitle.args
    assert "\n    in " in list(soup.contents)
    assert len(list(soup.contents)) == 6


def test_nested_commands():
    """Tests that nested commands are parsed correctly."""
    soup = TexSoup(r'\emph{Some \textbf{bold} words}')
    assert soup.textbf is not None
    assert len(list(soup.emph.contents)) == 3


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
    assert len(str(soup).split('\n')) == 5, 'Line breaks not persisted.'


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
    soup = TexSoup(r"""$$\lambda
    \Sigma$$ But don't mind me \$3.00""")
    children, contents = list(soup.children), list(soup.contents)
    assert '\n' in str(children[0]), 'Whitesapce not preserved in math env.'
    assert len(children) == 1 and children[0].name == '$$', 'Math env wrong'
    assert r'\$' in contents[1], 'Dollar sign not escaped!'
    soup = TexSoup(r"""\gamma = \beta\begin{notescaped}\gamma = \beta\end{notescaped}
    \begin{equation*}\beta = \gamma\end{equation*}""")
    assert str(soup.find('equation*')) == r'\begin{equation*}\beta = \gamma\end{equation*}'
    assert str(soup).startswith(r'\gamma = \beta')
    assert str(soup.notescaped) == r'\begin{notescaped}\gamma = \beta\end{notescaped}'


def test_math_environment_escape():
    """Tests $ escapes in math environment."""
    soup = TexSoup(r"$ \$ $")
    contents = list(soup.contents)
    assert r'\$' in contents[0][0], 'Dollar sign not escaped!'


def test_punctuation_command_structure():
    """Tests that commands for punctuation work."""
    soup = TexSoup(r"""\right. \right[ \right( \right|
    \right\langle \right\lfloor \right\lceil \right\ulcorner \big{ \bigg{
    \Big{ \Bigg}""")
    assert len(list(soup.contents)) == 12
    assert len(list(soup.children)) == 12


def test_non_punctuation_command_structure():
    """Tests that normal commands do not include punctuation in the command.

    However, the asterisk is one exception.
    """
    soup = TexSoup(r"""\mycommand, hello""")
    contents = list(soup.contents)
    assert r'\mycommand' == str(contents[0]), 'Comma considered part of the command.'

    soup = TexSoup(r"""\hspace*{0.2in} hello \hspace*{2in} world""")
    assert len(list(soup.contents)) == 4, '* not recognized as part of command.'


##########
# BUFFER #
##########


def test_buffer():
    from TexSoup.utils import Buffer
    b = Buffer('abcdef')
    assert b.forward_until(lambda s: s in 'def') == 'abc'
    assert b.forward_until(lambda s: s in 'f') == 'de'
    assert b.backward(5) == 'abcde'
    assert b.forward_until(lambda s: s not in 'abc') == 'abc'
    assert b.forward_until(lambda s: s in 'def') == ''
    assert b.backward(3) == 'abc'
    assert b.num_forward_until(lambda s: s in 'def') == 3
    assert b.forward(3) == 'abc'
    assert b.num_forward_until(lambda s: s in 'g') == 3
    assert b.forward(3) == 'def'
    assert b.num_forward_until(lambda s: s in 'z') == 0
    assert b.backward(6) == 'abcdef'
    assert b.num_forward_until(lambda s: s not in 'abc') == 3


def test_to_buffer():
    from TexSoup.utils import to_buffer
    f = to_buffer(lambda x: x[:])
    assert f('asdf') == 'asdf'
    g = to_buffer(lambda x: x)
    assert not g('').hasNext()
    assert next(g('asdf')) == 'a'


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
