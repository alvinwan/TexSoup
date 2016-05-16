from config import *
import pytest
import os

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

def test_navigation_children(chikin):
    """Test identification of all children"""
    assert len(list(chikin.children)) == 1
    assert next(chikin.children).name == 'document'
    assert len(list(chikin.document.children)) == 2

def test_navigation_descendants(chikin):
    """Test identification of all descendants"""
    assert len(list(chikin.descendants)) == 15

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
    assert sections[0] == '\section{Chikin Tales}'
    assert sections[1] == '\section{Chikin Scream}'
