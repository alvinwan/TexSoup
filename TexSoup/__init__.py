"""
TexSoup
---

Main file consisting of
"""

import itertools
import _io
from reader import tex_read
from data import *

def TexSoup(tex):
    """
    At a high-level, parses provided Tex into navigable, searchable structure.
    This is accomplished in two steps:
    1. Tex is parsed.
    2. Structure fed to TexNodes for a searchable, coder-friendly interface.

    :param (iterable, string) tex: the Tex source
    :return TexNode: object representing tex document
    """
    return TexNode(tex_read(tex))
