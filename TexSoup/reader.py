
from buffer import Buffer

def read_line(line):
    """Read a single line"""
    return tex_read(Buffer(tokenize_line(line)))

def read_lines(lines):
    """Read lines"""
    return tex_read(Buffer(tokenize_lines(lines)))

def tokenize_line(line):
    """Generator for LaTeX tokens on a single line, ignoring comments."""


def tokenize_lines(lines):
    """Generator for LaTeX tokens across multiple lines, ignoring comments."""
    return map(tokenize_line, lines)

def tex_read(src):
    r"""Read next expression from buffer

    :param Buffer src: a buffer of tokens

    >>> print(read_line('\textbf{Do play \textit{nice}.}'))
    \textbf{Do play \textit{nice}.}
    >>> print(read_lines(('\begin{itemize}', '\item text1', '\item text2',
    ... '\item text3', '\end{itemize}')
    \begin{itemize}
    \item text1
    \item text2
    \item text3
    \end{itemize}
    """
