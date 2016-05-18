from utils import to_buffer, Buffer
import functools
import itertools
import data

__all__ = ['read_line', 'read_lines']

WHITESPACE = {' ', '\t', '\r', '\n'}
COMMAND_TOKENS = {'\\'}
ARG_TOKENS = set(itertools.chain(*[arg.delims() for arg in data.args]))
ALL_TOKENS = COMMAND_TOKENS | ARG_TOKENS

#######################
# Convenience Methods #
#######################

def read_line(line):
    r"""Read a single line

    >>> print(read_line(r'\textbf{Do play \textit{nice}.}'))
    \textbf{Do play \textit{nice}.}
    """
    return tex_read(Buffer(tokenize_line(line)))

def read_lines(*lines):
    r"""Read multiple lines

    >>> print(read_lines('\begin{itemize}', '\item text1', '\item text2',
    ... '\item text3', '\end{itemize}'))
    \begin{itemize}
    \item text1
    \item text2
    \item text3
    \end{itemize}
    """
    return tex_read(Buffer(tokenize_lines(lines)))

#############
# Tokenizer #
#############

@to_buffer
def next_token(line):
    r"""Returns the next possible token, advancing the iterator to the next
    position to start processing from.

    :param (str, iterator, Buffer) line: LaTeX to process
    :return str: the token

    >>> b = Buffer(r'\textbf{Do play \textit{nice}.}')
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    \ textbf { Do play
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    \ textit { nice
    >>> print(next_token(b), next_token(b), next_token(b))
    } . }
    >>> print(next_token(Buffer('.}')))
    .
    >>> next_token(b)
    """
    while line.hasNext():
        for name, f in tokenizers:
            token = f(line)
            if token is not None:
                return token

@to_buffer
def tokenize_line(line):
    r"""Generator for LaTeX tokens on a single line, ignoring comments.

    :param (str, iterator, Buffer) line: LaTeX to process

    >>> print(*tokenize_line(r'\textbf{Do play \textit{nice}.}'))
    \ textbf { Do play  \ textit { nice } . }
    """
    token = next_token(line)
    while token is not None:
        yield token
        token = next_token(line)

def tokenize_lines(lines):
    """Generator for LaTeX tokens across multiple lines, ignoring comments.

    :param list lines: list of strings or iterator over strings
    """
    return map(tokenize_line, lines)

##########
# Tokens #
##########

tokenizers = []

def token(name):
    """Marker for a token

    :param str name: Name of tokenizer
    """
    def wrap(f):
        tokenizers.append((name, f))
        return f
    return wrap

@token('command')
def tokenize_command(line):
    """Process command

    :param Buffer line: iterator over line, with current position
    """
    if line.peek() == '\\':
        return next(line)

@token('argument')
def tokenize_argument(line):
    """Process both optional and required arguments.

    :param Buffer line: iterator over line, with current position
    """
    for delim in ARG_TOKENS:
        if line.startswith(delim):
            return line.forward(len(delim))

@token('string')
def tokenize_string(line, delimiters=ALL_TOKENS):
    r"""Process a string of text

    :param Buffer line: iterator over line, with current position

    >>> tokenize_string(Buffer('hello'))
    'hello'
    >>> b = Buffer('hello again\command')
    >>> tokenize_string(b)
    'hello again'
    >>> print(b.peek())
    \
    """
    result = ''
    for c in line:
        if c in delimiters:  # assumes all tokens are single characters
            line.backward(1)
            return result
        result += c
    return result

##########
# Mapper #
##########

def tex_read(src):
    r"""Read next expression from buffer

    :param Buffer src: a buffer of tokens
    """
    
