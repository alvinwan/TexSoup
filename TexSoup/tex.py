from TexSoup.reader import read_expr, read_tex
from TexSoup.data import *
from TexSoup.utils import *
from TexSoup.tokens import tokenize
from TexSoup.category import categorize
import itertools


def read(tex, skip_envs=(), tolerance=0):
    """Read and parse all LaTeX source.

    :param Union[str,iterable] tex: LaTeX source
    :param Union[str] skip_envs: names of environments to skip parsing
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :return TexEnv: the global environment
    """
    if not isinstance(tex, str):
        tex = ''.join(itertools.chain(*tex))
    buf = categorize(tex)
    buf = tokenize(buf)
    buf = read_tex(buf, skip_envs=skip_envs, tolerance=tolerance)
    return TexEnv('[tex]', begin='', end='', contents=buf), tex
