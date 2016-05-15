from TexSoup import TexSoup
import pytest
import os

def seed(path):
    """Filepath relative to test directory"""
    return os.path.join(os.path.split(os.path.realpath(__file__))[0], path)

############
# FIXTURES #
############

@pytest.fixture(scope='function')
def chikin():
    """Instance of the chikin tex file"""
    return TexSoup(open(seed('samples/chikin.tex')))

##############
# NAVIGATION #
##############

def test_navigation_attributes(chikin):
    """Test navigation with attributes by dot notation"""
    assert chikin.section == '\section{Chikin Tales}'
    assert chikin.section.name == 'section'
    assert chikin.section.string == 'Chikin Tales'
    assert chikin.section.parent.name == 'document'

def test_navigation_parent(chikin):
    """Test parent navigation"""
    assert chikin.section.parent.name == 'document'
    assert chikin.subsection.parent.name == 'section'
    assert chikin.subsection.parent.string == 'Chikin Tales'

def test_navigation_descendants(chikin):
    """Test identification of all descendants"""
    assert len(list(chikin.descendants)) == 15

##########
# SEARCH #
##########

def test_find_by_command(chikin):
    """Find all LaTeX blocks that match a command"""
    sections = chikin.find_all('section')
    assert sections[0] == '\section{Chikin Tales}'
    assert sections[1] == '\section{Chikin Scream}'
