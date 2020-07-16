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
END_OF_LINE_TOKENS  = ('\n', '\r')


# Only includes items that cannot cause failures
GCC = IntEnum('GroupedCategoryCodes', (
    'Comment',
    'Group',  # denoted by curly brace
    'Spacer',  # whitespace allowed between <command name> and arguments
    'EscapedComment',
    'SizeCommand',
    'MathSwitch',
    'MathGroupStart',
    'MathGroupEnd'
), start=CC.Invalid + 1)


# Supersets of category codes
MATH_START_TOKENS = (r'\[', r'\(')  # TODO: how to do this cleanly?
MATH_END_TOKENS = (r'\]', r'\)')

ARG_TOKENS = tuple(itertools.chain(*(arg.delims() for arg in arg_type)))
ARG_START_TOKENS = ARG_TOKENS[::2]
ARG_END_TOKENS = ARG_TOKENS[1::2]

# TODO: misnomer, what does ALL_TOKENS actually contain?
ALL_TOKENS = ('\\',) + ARG_TOKENS + ('%',) + MATH_START_TOKENS + MATH_END_TOKENS + ('$', '$$')

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

    >>> print(*tokenize(categorize(r'\textbf{Do play \textit{nice}.}')))
    \textbf { Do play  \textit { nice } . }
    >>> print(*tokenize(categorize(r'\begin{tabular} 0 & 1 \\ 2 & 0 \end{tabular}')))
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


@token('math_sym_switch')
def tokenize_math_sym_switch(text):
    r"""Group characters in math switches.

    :param Buffer text: iterator over line, with current position

    >>> tokenize_math_sym_switch(categorize(r'$\min_x$ \command'))
    '$'
    >>> tokenize_math_sym_switch(categorize(r'$$\min_x$$ \command'))
    '$$'
    """
    if text.peek().category == CC.MathSwitch:
        if text.peek(1) and text.peek(1).category == CC.MathSwitch:
            result = Token(text.forward(2), text.position)
        else:
            result = Token(text.forward(1), text.position)
        result.category = GCC.MathSwitch
        return result


@token('math_asym_switch')
def tokenize_math_asym_switch(text):
    r"""Group characters in begin-end-style math switches

    :param Buffer text: iterator over line, with current position

    >>> tokenize_math_asym_switch(categorize(r'\[asf'))
    '\\['
    >>> tokenize_math_asym_switch(categorize(r'\] sdf'))
    '\\]'
    >>> tokenize_math_asym_switch(categorize(r'[]'))
    """
    if text.peek((0, 2)) in MATH_START_TOKENS + MATH_END_TOKENS:
        result = text.forward(2)
        if result in MATH_START_TOKENS:
            result.category = GCC.MathGroupStart
        else:
            result.category = GCC.MathGroupEnd
        return result


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


# TODO: update string tokenizer so this isn't needed
@token('argument')
def tokenize_argument(text):
    """Process both optional and required arguments.

    :param Buffer text: iterator over line, with current position
    """
    for delim in ARG_TOKENS:
        if text.startswith(delim):
            return text.forward(len(delim))


# TODO: move me to parser
@token('command')
def tokenize_command(text):
    r"""Process command, but ignore line breaks. (double backslash)

    :param Buffer text: iterator over line, with current position

    >>> next(tokenize(categorize(r'\begin turing')))
    '\\begin'
    >>> next(tokenize(categorize(r'\bf  {turing}')))
    '\\bf'
    """
    if text.peek().category == CC.Escape:
        c = text.forward(1)
        while text.hasNext() and text.peek().category == CC.Letter \
                or text.peek() == '*':  # TODO: what do about asterisk?
            # TODO: excluded other, macro, super, sub, acttive, alignment
            # although macros can make these a part of the command name
            c += text.forward(1)
        return c


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
        if c.category == CC.Escape and str(text.peek()) in delimiters and str(
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
