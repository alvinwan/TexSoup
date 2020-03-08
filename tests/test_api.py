from TexSoup import TexSoup
from TexSoup.utils import TokenWithPosition
from tests.config import chikin
import re

##############
# NAVIGATION #
##############


if chikin:
    pass


def test_navigation_attributes(chikin):
    """Test navigation with attributes by dot notation"""
    assert str(chikin.section) == r'\section{Chikin Tales}'
    assert chikin.section.name == 'section'
    assert chikin.section.string == 'Chikin Tales'


def test_navigation_parent(chikin):
    """Test parent navigation"""
    assert chikin.section.parent.name == 'document'
    assert chikin.subsection.parent.name == 'document'


def test_navigation_children(chikin):
    """Test identification of all children"""
    assert len(list(chikin.children)) == 2
    docclass, document = chikin.children
    assert document.name == 'document'
    assert len(list(chikin.document.children)) == 7


def test_navigation_descendants(chikin):
    """Test identification of all descendants"""
    print(list(chikin.descendants))
    assert len(list(chikin.descendants)) == 28


def test_navigation_positions(chikin):
    assert chikin.char_pos_to_line(0) == (0, 0), '\\'
    assert chikin.char_pos_to_line(1) == (0, 1), 'documentclass'
    assert chikin.char_pos_to_line(172) == (11, 6), 'waddle'

    assert isinstance(next(next(chikin.itemize.children).contents), TokenWithPosition)

    # get position of first token
    waddle_pos = next(next(chikin.itemize.children).contents).position
    assert chikin.char_pos_to_line(waddle_pos) == (11, 6)

    # get position of item
    enumerate_first_item_pos = next(chikin.enumerate.children).name.position
    assert chikin.char_pos_to_line(enumerate_first_item_pos) == (22, 1)

    # get position of section
    section_pos = list(chikin.find_all('section'))[1].name.position
    assert chikin.char_pos_to_line(section_pos) == (15, 1)


##########
# SEARCH #
##########


def test_find_basic(chikin):
    """Find all LaTeX commands"""
    document = chikin.find('document')
    assert document.name == 'document'


def test_find_by_command(chikin):
    """Find all LaTeX blocks that match a command"""
    sections = list(chikin.find_all('section'))
    assert str(sections[0]) == r'\section{Chikin Tales}'
    assert str(sections[1]) == r'\section{Chikin Scream}'


def test_find_env():
    """Find all equations in the document"""
    soup = TexSoup(r"""\begin{equation}1+1\end{equation}""")
    equations = soup.find_all(r'\begin{equation}')
    assert len(list(equations)) > 0

################
# MODIFICATION #
################


def test_delete(chikin):
    """Delete an element from the parse tree."""
    chikin.section.delete()
    assert 'Chikin Tales' not in str(chikin)


def test_delete_arg():
    """Delete an element from an arg in the parse tree"""
    soup = TexSoup(r'\foo{\bar{\baz}}')
    soup.bar.delete()


def test_delete_token():
    """Delete TokenWithPosition"""
    soup = TexSoup(r"""
    \section{one}
    text
    \section{two}
    delete me""")

    assert 'delete me' in str(soup)
    for node in soup.all:
        if 'delete me' in node:
            node.delete()
    assert 'delete me' not in str(soup)


def test_replace_single(chikin):
    """Replace an element in the parse tree"""
    chikin.section.replace_with(chikin.subsection)
    assert 'Chikin Tales' not in str(chikin)
    assert len(list(chikin.find_all('subsection'))) == 4


def test_replace_multiple(chikin):
    """Replace an element in the parse tree"""
    chikin.section.replace_with(chikin.subsection, chikin.subsection)
    assert 'Chikin Tales' not in str(chikin)
    assert len(list(chikin.find_all('subsection'))) == 5


def test_append(chikin):
    """Add a child to the parse tree"""
    chikin.itemize.append('asdfghjkl')
    assert 'asdfghjkl' in str(chikin.itemize)


def test_insert(chikin):
    """Add a child to the parse tree at a specific position"""
    chikin.insert(0, 'asdfghjkl')
    assert 'asdfghjkl' in str(chikin)
    assert str(chikin[0]) == 'asdfghjkl'


#########
# TEXT #
########

def test_text(chikin):
    """Get text of document"""
    text = list(chikin.text)
    assert 'Chikin Tales' in text
    assert 'Chikin Fly' in text
    assert 'waddle\n' in text


def test_search_regex(chikin):
    """Find all occurenses of a regex in the document text"""
    matches = list(chikin.search_regex(r"unless[a-z ]*"))
    assert len(matches) == 1
    assert matches[0] == "unless ordered to squat"
    assert matches[0].position == 341


def test_search_regex_precompiled_pattern(chikin):
    """Find all occurenses of a regex in the document text"""
    pattern = re.compile(r"unless[a-z ]*")
    matches = list(chikin.search_regex(pattern))
    assert len(matches) == 1
    assert matches[0] == "unless ordered to squat"
    assert matches[0].position == 341
