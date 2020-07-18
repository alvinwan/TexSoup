from TexSoup.reader import read_tex
from TexSoup.data import *
from TexSoup.utils import *
from TexSoup.tokens import tokenize
from TexSoup.category import categorize
import itertools


def read(tex, skip_envs=()):
    """Read and parse all LaTeX source.

    :param Union[str,iterable] tex: LaTeX source
    :return TexEnv: the global environment
    """
    if not isinstance(tex, str):
        tex = ''.join(itertools.chain(*tex))
    buf = categorize(tex)
    buf = tokenize(buf)
    children = []
    while buf.hasNext():
        children.append(read_tex(buf, skip_envs=skip_envs))
    return TexEnv('[tex]', children), tex
