from reader import *
from data import *


def read(tex):
    """Read and parse all LaTeX source

    :param str tex: LaTeX source
    :return TexEnv: the global environment
    """
    buf, children = Buffer(itertools.chain(*tokenize_lines(lines))), []
    while buf.hasNext():
        children.append(read_tex(buf))
    return TexEnv('[tex]', children)
