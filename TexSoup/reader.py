from utils import to_navigable_iterator
from buffer import Buffer

#######################
# Convenience Methods #
#######################

def read_line(line):
    """Read a single line"""
    return tex_read(Buffer(tokenize_line(line)))

def read_lines(lines):
    """Read lines"""
    return tex_read(Buffer(tokenize_lines(lines)))

#############
# Tokenizer #
#############

@to_navigable_iterator
def next_token(line):
    """Returns the next possible token, advancing the iterator to the next
    position to start processing from.

    :param (str, iterator, NavigableIterator) line: LaTeX to process
    :return (str, NavigableIterator): the token and the line iterator
    """
    while True:
        c = next(line)
        if c == '\\':
            pass
    return None, line

@to_navigable_iterator
def tokenize_line(line):
    """Generator for LaTeX tokens on a single line, ignoring comments.

    :param (str, iterator, NavigableIterator) line: LaTeX to process
    """


def tokenize_lines(lines):
    """Generator for LaTeX tokens across multiple lines, ignoring comments.

    :param list lines: list of strings or iterator over strings
    """
    return map(tokenize_line, lines)

##########
# Mapper #
##########

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
