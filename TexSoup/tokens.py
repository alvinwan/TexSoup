"""Tokenization for all input.

Translates string into iterable `TexSoup.utils.Buffer`, yielding one
token at a time.
"""

from TexSoup.utils import to_buffer, Buffer, Token, CC
from TexSoup.data import arg_type
from TexSoup.category import categorize  # used for tests
from enum import IntEnum
import itertools
import string


# Core category codes
# https://www.overleaf.com/learn/latex/Table_of_TeX_category_codes
COMMAND_TOKEN       = '\\'
START_GROUP_TOKEN   = '{'  # not used
END_GROUP_TOKEN     = '}'  # not used
MATH_SWITCH_TOKENS  = ('$$', '$')
ALIGNMENT_TOKEN     = '&'  # not used
END_OF_LINE_TOKENS  = ('\n', '\r')
MACRO_TOKEN         = '#'  # not used
SUPERSCRIPT_TOKEN   = '^'  # not used
SUBSCRIPT_TOKEN     = '_'  # not used
IGNORED_TOKEN       = chr(0)  # not used
SPACER_TOKENS       = (chr(32), chr(9))    # not used
LETTER_TOKENS       = tuple(string.ascii_letters)  # + lots of unicode
OTHER_TOKENS        = None  # not defined, just anything left
ACTIVE_TOKEN        = '~'  # not used
COMMENT_TOKEN       = '%'
INVALID_TOKEN       = chr(127)  # not used


# Only includes items that cannot cause failures
GCC = IntEnum('GroupedCategoryCodes', (
    'Comment',
    'Group',  # denoted by curly brace
    'Spacer',  # whitespace allowed between \, <command name>, and arguments
    'EscapedComment',
    'SizeCommand',
), start=CC.Invalid + 1)


# Supersets of category codes
MATH_START_TOKENS = (r'\[', r'\(')
MATH_END_TOKENS = (r'\]', r'\)')
MATH_TOKENS = MATH_SWITCH_TOKENS + MATH_START_TOKENS + MATH_END_TOKENS

ARG_TOKENS = tuple(itertools.chain(*(arg.delims() for arg in arg_type)))
ARG_START_TOKENS = ARG_TOKENS[::2]
ARG_END_TOKENS = ARG_TOKENS[1::2]

# TODO: misnomer, what does ALL_TOKENS actually contain?
ALL_TOKENS = (COMMAND_TOKEN,) + ARG_TOKENS + MATH_TOKENS + (COMMENT_TOKEN,)

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
# TODO: looks like left-right do have to match
SIZE_PREFIX = ('left', 'right', 'big', 'Big', 'bigg', 'Bigg')
PUNCTUATION_COMMANDS = {command + bracket
                        for command in SIZE_PREFIX
                        for bracket in BRACKETS_DELIMITERS.union({'|', '.'})}

__all__ = ['tokenize']


def next_token(text):
    r"""Returns the next possible token, advancing the iterator to the next
    position to start processing from.

    :param Union[str,iterator,Buffer] text: LaTeX to process
    :return str: the token

    >>> b = categorize(r'\textbf{Do play\textit{nice}.}   $$\min_w \|w\|_2^2$$')
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    \textbf { Do play \textit
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    { nice } .
    >>> print(next_token(b))
    }
    >>> print(next_token(categorize('.}')))
    .
    >>> next_token(b)
    '   '
    >>> next_token(b)
    '$$'
    >>> b2 = categorize(r'\gamma = \beta')
    >>> print(next_token(b2), next_token(b2), next_token(b2))
    \gamma  =  \beta
    """
    while text.hasNext():
        for name, f in tokenizers:
            current_token = f(text)
            if current_token is not None:
                return current_token


@to_buffer()
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


@token('escaped_symbols')
def tokenize_escaped_symbols(text):
    r"""Process an escaped symbol.

    :param Buffer text: iterator over line, with current position

    >>> tokenize_escaped_symbols(categorize('\\'))
    >>> tokenize_escaped_symbols(categorize(r'\%'))
    '\\%'
    >>> tokenize_escaped_symbols(categorize(r'\ %'))  # not even one spacer is allowed
    """
    if text.peek().category == CC.Escape \
            and text.peek(1) \
            and text.peek(1).category in (
                CC.Escape, CC.GroupStart, CC.GroupEnd, CC.MathSwitch,
                CC.Comment):
        result = text.forward(2)
        result.category = GCC.EscapedComment
        return result


@token('comment')
def tokenize_line_comment(text):
    r"""Process a line comment

    :param Buffer text: iterator over line, with current position

    >>> tokenize_line_comment(categorize('%hello world\\'))
    '%hello world\\'
    >>> tokenize_line_comment(categorize('hello %world'))
    >>> tokenize_line_comment(categorize('%hello world'))
    '%hello world'
    >>> tokenize_line_comment(categorize('%hello\n world'))
    '%hello'
    >>> tokenize_line_comment(categorize('\%'))
    """
    result = Token('', text.position)
    if text.peek().category == CC.Comment \
            and text.peek(-1).category != CC.Escape:
        result += text.forward(1)
        while text.hasNext() and text.peek().category != CC.EndOfLine:
            result += text.forward(1)
        result.category = GCC.Comment
        return result


@token('math_switch')
def tokenize_math(text):
    r"""Group characters in math switches.

    :param Buffer text: iterator over line, with current position

    >>> b = categorize(r'$\min_x$ \command')
    >>> tokenize_math(b)
    '$'
    >>> b = categorize(r'$$\min_x$$ \command')
    >>> tokenize_math(b)
    '$$'
    """
    if text.peek().category == CC.MathSwitch:
        if text.peek(1) and text.peek(1).category == CC.MathSwitch:
            return Token(text.forward(2), text.position)
        return Token(text.forward(1), text.position)


# TODO: move me to parser
@token('punctuation_command')
def tokenize_punctuation_command(text):
    """Process command that augments or modifies punctuation.

    This is important to the tokenization of a string, as opening or closing
    punctuation is not supposed to match.

    :param Buffer text: iterator over text, with current position
    """
    if text.peek().category == CC.Escape:
        for point in PUNCTUATION_COMMANDS:
            if text.peek((1, len(point) + 1)) == point:
                return text.forward(len(point) + 1)


# TODO: move me to parser
@token('command')
def tokenize_command(text):
    """Process command, but ignore line breaks. (double backslash)

    :param Buffer text: iterator over line, with current position
    """
    if text.peek() == COMMAND_TOKEN:
        c = text.forward(1)
        # TODO: replace with constants
        tokens = set(string.punctuation + string.whitespace) - {'*'}
        while text.hasNext() and (c == COMMAND_TOKEN or text.peek()
                                  not in tokens) and c not in MATH_TOKENS:
            c += text.forward(1)
        return c


# TODO: update string tokenizer so this isn't needed
@token('argument')
def tokenize_argument(text):
    """Process both optional and required arguments.

    :param Buffer text: iterator over line, with current position
    """
    for delim in ARG_TOKENS:
        if text.startswith(delim):
            return text.forward(len(delim))


# TODO: clean up
@token('string')
def tokenize_string(text, delimiters=None):
    r"""Process a string of text

    :param Buffer text: iterator over line, with current position
    :param Union[None,iterable,str] delimiters: defines the delimiters

    >>> tokenize_string(categorize('hello'))
    'hello'
    >>> b = categorize(r'hello again\command')
    >>> tokenize_string(b)
    'hello again'
    >>> print(b.peek())
    \
    >>> print(tokenize_string(categorize(r'0 & 1 \\\command')))
    0 & 1 \\
    """
    if delimiters is None:
        delimiters = ALL_TOKENS
    result = Token('', text.position)
    for c in text:
        if c == COMMAND_TOKEN and str(text.peek()) in delimiters and str(
                c + text.peek()) not in delimiters:
            c += next(text)
        elif str(c) in delimiters:  # assumes all tokens are single characters
            text.backward(1)
            return result
        result += c
        if text.peek((0, 2)) == '\\\\':  # TODO: replace with constants
            result += text.forward(2)
        if text.peek((0, 2)) == '\n\n':  # TODO: replace with constants
            result += text.forward(2)
            return result
    return result
