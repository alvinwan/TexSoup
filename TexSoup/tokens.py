"""Tokenization for all input.

Translates string into iterable `TexSoup.utils.Buffer`, yielding one
token at a time.
"""

from TexSoup.utils import to_buffer, Buffer, Token
from TexSoup.data import arg_type
import itertools
import string


# Core category code primitives
# https://www.overleaf.com/learn/latex/Table_of_TeX_category_codes
COMMAND_TOKENS      = ('\\',)
START_GROUP_TOKENS  = ('{',)
END_GROUP_TOKENS    = ('}',)
MATH_SWITCH_TOKENS  = ('$', '$$')
ALIGNMENT_TOKENS    = ('&',)
END_OF_LINE_TOKENS  = ('\n', '\r')
MACRO_TOKENS        = ('#',)
SUPERSCRIPT_TOKENS  = ('^',)
SUBSCRIPT_TOKENS    = ('_',)
IGNORED_TOKENS      = (chr(0),)
SPACER_TOKENS       = (chr(32), chr(9))
LETTER_TOKENS       = tuple(string.ascii_letters)  # + lots of unicode
OTHER_TOKENS        = None  # not defined, just anything left
ACTIVE_TOKENS       = ('~',)
COMMENT_TOKENS      = ('%',)
INVALID_TOKENS      = (chr(127),)

# Primitive supersets
MATH_START_TOKENS = (r'\[', r'\(')
MATH_END_TOKENS = (r'\]', r'\)')
MATH_TOKENS = MATH_SWITCH_TOKENS + MATH_START_TOKENS + MATH_END_TOKENS

ARG_TOKENS = tuple(itertools.chain(*(arg.delims() for arg in arg_type)))
ARG_START_TOKENS = ARG_TOKENS[::2]
ARG_END_TOKENS = ARG_TOKENS[1::2]

# TODO: misnomer, what does ALL_TOKENS actually contain?
ALL_TOKENS = COMMAND_TOKENS + ARG_TOKENS + MATH_TOKENS + COMMENT_TOKENS

# Custom higher-level combinations of primitives
SKIP_ENVS = ('verbatim', 'equation', 'lstlisting', 'align', 'alignat',
             'equation*', 'align*', 'math', 'displaymath', 'split', 'array',
             'eqnarray', 'eqnarray*', 'multline', 'multline*', 'gather',
             'gather*', 'flalign', 'flalign*',
             '$', '$$', r'\[', r'\]', r'\(', r'\)')
BRACKETS_DELIMITERS = {'(', ')', '<', '>', '[', ']', '{', '}',
                       r'\{', r'\}', '.' '|', r'\langle', r'\rangle',
                       r'\lfloor', '\rfloor', r'\lceil', r'\rceil',
                       r'\ulcorner', r'\urcorner', r'\lbrack', r'\rbrack'}
SIZE_PREFIX = ('left', 'right', 'big', 'Big', 'bigg', 'Bigg')
PUNCTUATION_COMMANDS = {command + bracket
                        for command in SIZE_PREFIX
                        for bracket in BRACKETS_DELIMITERS.union({'|', '.'})}

__all__ = ['tokenize']


@to_buffer
def next_token(text):
    r"""Returns the next possible token, advancing the iterator to the next
    position to start processing from.

    :param Union[str,iterator,Buffer] text: LaTeX to process
    :return str: the token

    >>> b = Buffer(r'\textbf{Do play\textit{nice}.}   $$\min_w \|w\|_2^2$$')
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    \textbf { Do play \textit
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    { nice } .
    >>> print(next_token(b))
    }
    >>> print(next_token(Buffer('.}')))
    .
    >>> next_token(b)
    '   '
    >>> next_token(b)
    '$$'
    >>> b2 = Buffer(r'\gamma = \beta')
    >>> print(next_token(b2), next_token(b2), next_token(b2))
    \gamma  =  \beta
    """
    while text.hasNext():
        for name, f in tokenizers:
            current_token = f(text)
            if current_token is not None:
                return current_token


@to_buffer
def tokenize(text):
    r"""Generator for LaTeX tokens on text, ignoring comments.

    :param Union[str,iterator,Buffer] text: LaTeX to process

    >>> print(*tokenize(r'\textbf{Do play \textit{nice}.}'))
    \textbf { Do play  \textit { nice } . }
    >>> print(*tokenize(r'\begin{tabular} 0 & 1 \\ 2 & 0 \end{tabular}'))
    \begin { tabular }  0 & 1 \\ 2 & 0  \end { tabular }
    """
    current_token = next_token(text)
    while current_token is not None:
        yield current_token
        current_token = next_token(text)


##############
# Tokenizers #
##############

tokenizers = []


def token(name):
    """Marker for a token.

    :param str name: Name of tokenizer
    """

    def wrap(f):
        tokenizers.append((name, f))
        return f

    return wrap


@token('punctuation_command')
def tokenize_punctuation_command(text):
    """Process command that augments or modifies punctuation.

    This is important to the tokenization of a string, as opening or closing
    punctuation is not supposed to match.

    :param Buffer text: iterator over text, with current position
    """
    if text.peek() == '\\':
        for point in PUNCTUATION_COMMANDS:
            if text.peek((1, len(point) + 1)) == point:
                return text.forward(len(point) + 1)


@token('command')
def tokenize_command(text):
    """Process command, but ignore line breaks. (double backslash)

    :param Buffer text: iterator over line, with current position
    """
    if text.peek() == '\\':
        c = text.forward(1)
        tokens = set(string.punctuation + string.whitespace) - {'*'}
        while text.hasNext() and (c == '\\' or text.peek()
                                  not in tokens) and c not in MATH_TOKENS:
            c += text.forward(1)
        return c


@token('line_comment')
def tokenize_line_comment(text):
    r"""Process a line comment

    :param Buffer text: iterator over line, with current position

    >>> tokenize_line_comment(Buffer('hello %world'))
    >>> tokenize_line_comment(Buffer('%hello world'))
    '%hello world'
    >>> tokenize_line_comment(Buffer('%hello\n world'))
    '%hello'
    """
    result = Token('', text.position)
    if text.peek() == '%' and text.peek(-1) != '\\':
        result += text.forward(1)
        while text.peek() != '\n' and text.hasNext():
            result += text.forward(1)
        return result


@token('argument')
def tokenize_argument(text):
    """Process both optional and required arguments.

    :param Buffer text: iterator over line, with current position
    """
    for delim in ARG_TOKENS:
        if text.startswith(delim):
            return text.forward(len(delim))


@token('math')
def tokenize_math(text):
    r"""Prevents math from being tokenized.

    :param Buffer text: iterator over line, with current position

    >>> b = Buffer(r'$\min_x$ \command')
    >>> tokenize_math(b)
    '$'
    >>> b = Buffer(r'$$\min_x$$ \command')
    >>> tokenize_math(b)
    '$$'
    """
    if text.startswith('$') and (
       text.position == 0 or text.peek(-1) != '\\' or text.endswith(r'\\')):
        starter = '$$' if text.startswith('$$') else '$'
        return Token(text.forward(len(starter)), text.position)


@token('string')
def tokenize_string(text, delimiters=None):
    r"""Process a string of text

    :param Buffer text: iterator over line, with current position
    :param Union[None,iterable,str] delimiters: defines the delimiters

    >>> tokenize_string(Buffer('hello'))
    'hello'
    >>> b = Buffer(r'hello again\command')
    >>> tokenize_string(b)
    'hello again'
    >>> print(b.peek())
    \
    >>> print(tokenize_string(Buffer(r'0 & 1 \\\command')))
    0 & 1 \\
    """
    if delimiters is None:
        delimiters = ALL_TOKENS
    result = Token('', text.position)
    for c in text:
        if c == '\\' and str(text.peek()) in delimiters and str(
                c + text.peek()) not in delimiters:
            c += next(text)
        elif str(c) in delimiters:  # assumes all tokens are single characters
            text.backward(1)
            return result
        result += c
        if text.peek((0, 2)) == '\\\\':
            result += text.forward(2)
        if text.peek((0, 2)) == '\n\n':
            result += text.forward(2)
            return result
    return result
