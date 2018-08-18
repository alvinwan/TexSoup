from TexSoup import TexSoup
import os
import pytest


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
