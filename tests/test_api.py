from config import *
from TexSoup.utils import TokenWithPosition

##############
# NAVIGATION #
##############


def test_navigation_attributes(chikin):
    """Test navigation with attributes by dot notation"""
    assert str(chikin.section) == '\section{Chikin Tales}'
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

    assert isinstance(next(next(chikin.itemize.children).tokens), TokenWithPosition)

    # get position of first token
    waddle_pos = next(next(chikin.itemize.children).tokens).position
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
    assert str(sections[0]) == '\section{Chikin Tales}'
    assert str(sections[1]) == '\section{Chikin Scream}'


################
# MODIFICATION #
################


def test_delete(chikin):
    """Delete an element from the parse tree."""
    chikin.section.delete()
    assert 'Chikin Tales' not in str(chikin)


def test_replace_single(chikin):
    """Replace an element in the parse tree"""
    chikin.section.replace(chikin.subsection)
    assert 'Chikin Tales' not in str(chikin)
    assert len(list(chikin.find_all('subsection'))) == 4


def test_replace_multiple(chikin):
    """Replace an element in the parse tree"""
    chikin.section.replace(chikin.subsection, chikin.subsection)
    assert 'Chikin Tales' not in str(chikin)
    assert len(list(chikin.find_all('subsection'))) == 5


def test_add_children(chikin):
    """Add a child to the parse tree"""
    chikin.section.add_children('asdfghjkl')
    assert 'asdfghjkl' in str(chikin.section)