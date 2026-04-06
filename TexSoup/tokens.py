"""Tokenization for all input.

Translates string into iterable `TexSoup.utils.Buffer`, yielding one
token at a time.
"""

from TexSoup.utils import to_buffer, Buffer, Token, CC
from TexSoup.data import arg_type
from TexSoup.category import categorize  # used for tests
from TexSoup.utils import IntEnum, TC
import itertools
import string

# Custom higher-level combinations of primitives
SKIP_ENV_NAMES = ('lstlisting', 'verbatim', 'verbatimtab', 'Verbatim', 'listing')
MATH_ENV_NAMES = (
    'align', 'align*', 'alignat', 'array', 'displaymath', 'eqnarray',
    'eqnarray*', 'equation', 'equation*', 'flalign', 'flalign*', 'gather',
    'gather*', 'math', 'multline', 'multline*', 'split'
)
SPECIAL_COMMANDS = {'newcommand', 'renewcommand', 'providecommand'}
BRACKETS_DELIMITERS = {
    '(', ')', '<', '>', '[', ']', '{', '}', r'\{', r'\}', '.' '|', r'\langle',
    r'\rangle', r'\lfloor', r'\rfloor', r'\lceil', r'\rceil', r'\ulcorner',
    r'\urcorner', r'\lbrack', r'\rbrack'
}
# TODO: looks like left-right do have to match
_PUNCTUATION_PREFIXES_BY_FIRST_LETTER = {
    'l': ('left',),
    'r': ('right',),
    'b': ('bigg', 'big'),
    'B': ('Bigg', 'Big'),
}
_PUNCTUATION_DELIMITERS = tuple(sorted(
    BRACKETS_DELIMITERS.union({'|', '.'}),
    key=len,
    reverse=True,
))
PUNCTUATION_COMMANDS_BY_FIRST_LETTER = {
    first_letter: tuple(
        prefix + delimiter
        for prefix in prefixes
        for delimiter in _PUNCTUATION_DELIMITERS
    )
    for first_letter, prefixes in _PUNCTUATION_PREFIXES_BY_FIRST_LETTER.items()
}

__all__ = ['tokenize']


def in_at_letter_mode(text):
    r"""Whether command names should currently treat ``@`` as a letter.

    :param Buffer text: categorized character buffer
    :return bool: whether ``@`` should be treated as a letter

    >>> text = categorize(r'\makeatletter')
    >>> in_at_letter_mode(text)
    False
    >>> text.at_letter = True
    >>> in_at_letter_mode(text)
    True
    """
    return getattr(text, 'at_letter', False)


def is_command_name_token(token, text):
    r"""Whether token should count as a command-name character.

    :param Token token: token to test
    :param Buffer text: categorized character buffer
    :return bool: whether token can extend a command name

    >>> text = categorize('@')
    >>> token = next(text)
    >>> is_command_name_token(token, text)
    False
    >>> update_at_letter_state(text, Token('makeatletter', category=TC.CommandName))
    >>> is_command_name_token(token, text)
    True
    >>> is_command_name_token(Token('a', category=CC.Letter), text)
    True
    """
    return token.category == CC.Letter or (
        in_at_letter_mode(text) and token == '@')


def update_at_letter_state(text, token):
    r"""Apply ``\\makeatletter`` / ``\\makeatother`` tokenizer state changes.

    :param Buffer text: categorized character buffer
    :param Token token: command-name token that may change tokenizer state

    >>> text = categorize(r'\makeatletter\makeatother')
    >>> in_at_letter_mode(text)
    False
    >>> update_at_letter_state(text, Token('makeatletter', category=TC.CommandName))
    >>> in_at_letter_mode(text)
    True
    >>> update_at_letter_state(text, Token('textbf', category=TC.CommandName))
    >>> in_at_letter_mode(text)
    True
    >>> update_at_letter_state(text, Token('makeatother', category=TC.CommandName))
    >>> in_at_letter_mode(text)
    False
    """
    if token.category != TC.CommandName:
        return
    if token.text == 'makeatletter':
        text.at_letter = True
    elif token.text == 'makeatother':
        text.at_letter = False


def next_token(text, prev=None):
    r"""Returns the next possible token, advancing the iterator to the next
    position to start processing from.

    :param Union[str,iterator,Buffer] text: LaTeX to process
    :return str: the token

    >>> b = categorize(r'\textbf{Do play\textit{nice}.}   $$\min_w \|w\|_2^2$$')
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    \ textbf { Do play
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    \ textit { nice
    >>> print(next_token(b))
    }
    >>> print(next_token(categorize('.}')))
    .
    >>> next_token(b)
    '.'
    >>> next_token(b)
    '}'
    """
    while text.hasNext():
        for name, f in tokenizers:
            current_token = f(text, prev=prev)
            if current_token is not None:
                return current_token


@to_buffer()
def tokenize(text):
    r"""Generator for LaTeX tokens on text, ignoring comments.

    :param Union[str,iterator,Buffer] text: LaTeX to process

    >>> print(*tokenize(categorize(r'\\%}')))
    \\ %}
    >>> print(*tokenize(categorize(r'\textbf{hello \\%}')))
    \ textbf { hello  \\ %}
    >>> print(*tokenize(categorize(r'\textbf{Do play \textit{nice}.}')))
    \ textbf { Do play  \ textit { nice } . }
    >>> print(*tokenize(categorize(r'\begin{tabular} 0 & 1 \\ 2 & 0 \end{tabular}')))
    \ begin { tabular }  0 & 1  \\  2 & 0  \ end { tabular }
    """
    text.at_letter = False
    current_token = next_token(text)
    while current_token is not None:
        assert current_token.category in TC
        yield current_token
        update_at_letter_state(text, current_token)
        current_token = next_token(text, prev=current_token)


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
def tokenize_escaped_symbols(text, prev=None):
    r"""Process an escaped symbol or a known punctuation command.

    :param Buffer text: iterator over line, with current position

    >>> tokenize_escaped_symbols(categorize(r'\\'))
    '\\\\'
    >>> tokenize_escaped_symbols(categorize(r'\\%'))
    '\\\\'
    >>> tokenize_escaped_symbols(categorize(r'\}'))
    '\\}'
    >>> tokenize_escaped_symbols(categorize(r'\%'))
    '\\%'
    >>> tokenize_escaped_symbols(categorize(r'\ '))
    '\\ '
    """
    if text.peek().category == CC.Escape \
            and text.peek(1) \
            and not (
                in_at_letter_mode(text) and text.peek(1) == '@') \
            and text.peek(1).category in (
                CC.Escape, CC.GroupBegin, CC.GroupEnd, CC.MathSwitch,
                CC.Alignment, CC.EndOfLine, CC.Macro, CC.Superscript,
                CC.Subscript, CC.Spacer, CC.Active, CC.Comment, CC.Other):
        result = text.forward(2)
        result.category = TC.EscapedComment
        return result


@token('comment')
def tokenize_line_comment(text, prev=None):
    r"""Process a line comment

    :param Buffer text: iterator over line, with current position

    >>> tokenize_line_comment(categorize('%hello world\\'))
    '%hello world\\'
    >>> tokenize_line_comment(categorize('hello %world'))
    >>> tokenize_line_comment(categorize('%}hello world'))
    '%}hello world'
    >>> tokenize_line_comment(categorize('%}  '))
    '%}  '
    >>> tokenize_line_comment(categorize('%hello\n world'))
    '%hello'
    >>> b = categorize(r'\\%')
    >>> _ = next(b), next(b)
    >>> tokenize_line_comment(b)
    '%'
    >>> tokenize_line_comment(categorize(r'\%'))
    """
    result = Token('', text.position)
    if text.peek().category == CC.Comment and (
            prev is None or prev.category != CC.Comment):
        result += text.forward(1)
        while text.hasNext() and text.peek().category != CC.EndOfLine:
            result += text.forward(1)
        result.category = TC.Comment
        return result


@token('math_sym_switch')
def tokenize_math_sym_switch(text, prev=None):
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
            result.category = TC.DisplayMathSwitch
        else:
            result = Token(text.forward(1), text.position)
            result.category = TC.MathSwitch
        return result


@token('math_asym_switch')
def tokenize_math_asym_switch(text, prev=None):
    r"""Group characters in begin-end-style math switches

    :param Buffer text: iterator over line, with current position

    >>> tokenize_math_asym_switch(categorize(r'\[asf'))
    '\\['
    >>> tokenize_math_asym_switch(categorize(r'\] sdf'))
    '\\]'
    >>> tokenize_math_asym_switch(categorize(r'[]'))
    """
    mapping = {
        (CC.Escape, CC.BracketBegin):   TC.DisplayMathGroupBegin,
        (CC.Escape, CC.BracketEnd):     TC.DisplayMathGroupEnd,
        (CC.Escape, CC.ParenBegin):     TC.MathGroupBegin,
        (CC.Escape, CC.ParenEnd):       TC.MathGroupEnd
    }
    if not text.hasNext(2):
        return
    key = (text.peek().category, text.peek(1).category)
    if key in mapping:
        result = text.forward(2)
        result.category = mapping[key]
        return result


@token('line_break')
def tokenize_line_break(text, prev=None):
    r"""Extract LaTeX line breaks.

    >>> tokenize_line_break(categorize(r'\\aaa'))
    '\\\\'
    >>> tokenize_line_break(categorize(r'\aaa'))
    """
    if text.peek().category == CC.Escape and text.peek(1) \
            and text.peek(1).category == CC.Escape:
        result = text.forward(2)
        result.category = TC.LineBreak
        return result


@token('ignore')
def tokenize_ignore(text, prev=None):
    r"""Filter out ignored or invalid characters

    >>> print(*tokenize(categorize('\x00hello')))
    hello
    """
    while text.peek().category in (CC.Ignored, CC.Invalid):
        text.forward(1)


@token('spacers')
def tokenize_spacers(text, prev=None):
    r"""Combine spacers [ + line break [ + spacer]]

    >>> tokenize_spacers(categorize('\t\n{there'))
    '\t\n'
    >>> tokenize_spacers(categorize('\t\nthere'))
    >>> tokenize_spacers(categorize('      \t     '))
    '      \t     '
    >>> tokenize_spacers(categorize(r' ccc'))
    """
    result = Token('', text.position)
    while text.hasNext() and text.peek().category == CC.Spacer:
        result += text.forward(1)
    if text.hasNext() and text.peek().category == CC.EndOfLine:
        result += text.forward(1)
    while text.hasNext() and text.peek().category == CC.Spacer:
        result += text.forward(1)
    result.category = TC.MergedSpacer

    if text.hasNext() and text.peek().category in (CC.Letter, CC.Other):
        text.backward(text.position - result.position)
        return

    if result:
        return result


@token('symbols')
def tokenize_symbols(text, prev=None):
    r"""Process singletone symbols as standalone tokens.

    :param Buffer text: iterator over line, with current position. Escape is
                        isolated if not part of escaped char

    >>> next(tokenize(categorize(r'\begin turing')))
    '\\'
    >>> next(tokenize(categorize(r'\bf  {turing}')))
    '\\'
    >>> next(tokenize(categorize(r'{]}'))).category
    <TokenCode.GroupBegin: 23>
    """
    mapping = {
        CC.Escape:          TC.Escape,
        CC.GroupBegin:      TC.GroupBegin,
        CC.GroupEnd:        TC.GroupEnd,
        CC.BracketBegin:     TC.BracketBegin,
        CC.BracketEnd:    TC.BracketEnd
    }
    if text.peek().category in mapping.keys():
        result = text.forward(1)
        result.category = mapping[result.category]
        return result


# TODO: move me to parser (should parse punctuation as arg +
# store punctuation commads as macro)
@token('punctuation_command_name')
def tokenize_punctuation_command_name(text, prev=None):
    """Process command that augments or modifies punctuation.

    This is important to the tokenization of a string, as opening or closing
    punctuation is not supposed to match.

    :param Buffer text: iterator over text, with current position
    """
    current = text.peek()
    if text.peek(-1) and text.peek(-1).category == CC.Escape and current:
        for point in PUNCTUATION_COMMANDS_BY_FIRST_LETTER.get(str(current), ()):
            if text.peek((0, len(point))) == point:
                result = text.forward(len(point))
                result.category = TC.PunctuationCommandName
                return result


@token('command_name')
def tokenize_command_name(text, prev=None):
    r"""Extract most restrictive subset possibility for command name.

    Parser can later join allowed spacers and macros to assemble the final
    command name and arguments.

    >>> b = categorize(r'\bf{')
    >>> _ = next(b)
    >>> tokenize_command_name(b)
    'bf'
    >>> b = categorize(r'\bf,')
    >>> _ = next(b)
    >>> tokenize_command_name(b)
    'bf'
    >>> b = categorize(r'\bf*{')
    >>> _ = next(b)
    >>> tokenize_command_name(b)
    'bf*'
    """
    token = text.peek()
    if text.peek(-1) and text.peek(-1).category == CC.Escape \
            and is_command_name_token(token, text):
        parts = [next(text)]
        token = text.peek()
        while token and (is_command_name_token(token, text) or token == '*'):
            # TODO: excluded other, macro, super, sub, acttive, alignment
            # although macros can make these a part of the command name.
            # We also allow '*' here for starred forms like \section*, but it
            # should really be treated as a trailing suffix, not a character
            # that can appear in the middle of a command name.
            parts.append(next(text))
            token = text.peek()
        result = Token.join(parts)
        result.category = TC.CommandName
        return result


@token('string')
def tokenize_string(text, prev=None):
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
    >>> print(tokenize_string(categorize(r'0 & 1\\\command')))
    0 & 1
    """
    parts = []
    position = text.position
    token = text.peek()
    while token and token.category not in (
            CC.Escape,
            CC.GroupBegin,
            CC.GroupEnd,
            CC.MathSwitch,
            CC.BracketBegin,
            CC.BracketEnd,
            CC.Comment):
        parts.append(next(text).text)
        token = text.peek()
    return Token(''.join(parts), position, category=TC.Text)
