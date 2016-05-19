from TexSoup.reader import *
from TexSoup.data import *
from TexSoup.utils import *
import itertools

def read(tex):
    """Read and parse all LaTeX source

    :param str tex: LaTeX source
    :return TexEnv: the global environment
    """
    if isinstance(tex, str):
        tex = tex.strip().splitlines()
    buf, children = Buffer(itertools.chain(*tokenize_lines(tex))), []
    while buf.hasNext():
        content = read_tex(buf)
        if content is not None:
            children.append(content)
    return TexEnv('[tex]', children)
