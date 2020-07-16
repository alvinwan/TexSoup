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
    if isinstance(tex, str):
        tex = tex
    else:
        tex = ''.join(itertools.chain(*tex))
    buf, children = tokenize(categorize(tex)), []
    while buf.hasNext():
        children.append(read_tex(buf, skip_envs=skip_envs))
    return TexEnv('[tex]', children), tex
