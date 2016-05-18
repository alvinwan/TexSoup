"""
TexSoup
---

Main file, containing most commonly used elements of TexSoup

@author: Alvin Wan
@site: alvinwan.com
"""

import itertools
import _io
from tex import *

def TexSoup(tex):
    """
    At a high-level, parses provided Tex into a navigable, searchable structure.
    This is accomplished in two steps:
    1. Tex is parsed, cleaned, and packaged.
    2. Structure fed to TexNodes for a searchable, coder-friendly interface.

    :param (iterable, string) tex: the Tex source
    :return TexNode: object representing tex document
    """
    return TexNode(read(tex))
