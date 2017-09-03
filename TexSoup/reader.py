from TexSoup.utils import to_buffer, Buffer
from TexSoup.data import *
import TexSoup.data as data
import functools
import itertools

__all__ = ['tokenize', 'read_tex']

COMMAND_TOKENS = {'\\'}
MATH_TOKENS = {'$'}
ARG_START_TOKENS = {arg.delims()[0] for arg in data.args}
ARG_END_TOKENS = {arg.delims()[1] for arg in data.args}
ARG_TOKENS = ARG_START_TOKENS | ARG_END_TOKENS
ALL_TOKENS = COMMAND_TOKENS | ARG_TOKENS | MATH_TOKENS
SKIP_ENVS = ('verbatim', 'equation', 'lstlisting')
PUNCTUATION_COMMANDS = ('right', 'left')


#############
# Tokenizer #
#############


@to_buffer
def next_token(text):
    r"""Returns the next possible token, advancing the iterator to the next
    position to start processing from.

    :param (str, iterator, Buffer) text: LaTeX to process
    :return str: the token

    >>> b = Buffer(r'\textbf{Do play\textit{nice}.}   $$\min_w \|w\|_2^2$$')
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    \ textbf { Do play
    >>> print(next_token(b), next_token(b), next_token(b), next_token(b))
    \ textit { nice
    >>> print(next_token(b), next_token(b), next_token(b))
    } . }
    >>> print(next_token(Buffer('.}')))
    .
    >>> next_token(b)
    '   '
    >>> next_token(b)
    '$$\\min_w \\|w\\|_2^2$$'
    >>> next_token(b)
    """
    while text.hasNext():
        for name, f in tokenizers:
            token = f(text)
            if token is not None:
                return token


@to_buffer
def tokenize(text):
    r"""Generator for LaTeX tokens on text, ignoring comments.

    :param (str, iterator, Buffer) text: LaTeX to process

    >>> print(*tokenize(r'\textbf{Do play \textit{nice}.}'))
    \ textbf { Do play  \ textit { nice } . }
    >>> print(*tokenize(r'\begin{tabular} 0 & 1 \\ 2 & 0 \end{tabular}'))
    \ begin { tabular }  0 & 1 \\ 2 & 0  \ end { tabular }
    >>> print(*tokenize(r'$$\min_x \|Xw-y\|_2^2$$'))
    $$\min_x \|Xw-y\|_2^2$$
    """
    token = next_token(text)
    while token is not None:
        yield token
        token = next_token(text)


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


@token('punctuation_command')
def tokenize_punctuation_command(text):
    """Process command that augments or modifies punctuation.

    This is important to the tokenization of a string, as opening or closing
    punctuation is not supposed to match.

    :param Buffer text: iterator over text, with current position
    """
    if text.peek() == '\\':
        for string in PUNCTUATION_COMMANDS:
            if text.peek((1, len(string) + 1)) == string:
                return text.forward(len(string) + 3)


@token('command')
def tokenize_command(text):
    """Process command, but ignore line breaks. (double backslash)

    :param Buffer text: iterator over line, with current position
    """
    if text.peek() == '\\' and text.peek(1) not in ALL_TOKENS:
        return next(text)


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

    >>> b = Buffer('$$\min_x$$ \command')
    >>> tokenize_math(b)
    '$$\\min_x$$'
    """
    result = ''
    if text.startswith('$'):
        starter = '$$' if text.startswith('$$') else '$'
        result += text.forward(len(starter))
        while text.hasNext() and text.peek((0, len(starter))) != starter:
            result += next(text)
        if not text.startswith(starter):
            raise EOFError('Expecting %s. Instead got %s' % (
                starter, text.peek((0, 5))))
        result += text.forward(len(starter))
        return result


@token('string')
def tokenize_string(text, delimiters=ALL_TOKENS):
    r"""Process a string of text

    :param Buffer line: iterator over line, with current position

    >>> tokenize_string(Buffer('hello'))
    'hello'
    >>> b = Buffer('hello again\command')
    >>> tokenize_string(b)
    'hello again'
    >>> print(b.peek())
    \
    >>> print(tokenize_string(Buffer('0 & 1 \\\\\command')))
    0 & 1 \\
    """
    result = ''
    for c in text:
        if c == '\\' and text.peek() in delimiters:
            c += next(text)
        elif c in delimiters:  # assumes all tokens are single characters
            text.backward(1)
            return result
        result += c
        if text.peek((0, 2)) == '\\\\':
            result += text.forward(2)
    return result


##########
# Mapper #
##########


def read_tex(src):
    r"""Read next expression from buffer

    :param Buffer src: a buffer of tokens
    """
    c = next(src)
    if c.startswith('$'):
        name = '$$' if c.startswith('$$') else '$'
        return TexEnv(name, [c[len(name):-len(name)]], nobegin=True)
    if c == '\\':
        if src.peek().startswith('item '):
            mode, expr = 'command', TexCmd('item', (),
                ' '.join(next(src).split(' ')[1:]).strip())
        elif src.peek() == 'begin':
            mode, expr = next(src), TexEnv(Arg.parse(src.forward(3)).value)
        else:
            mode, candidate, expr = 'command', next(src), None
            for i, c in enumerate(candidate):
                if c.isspace():
                    expr = TexCmd(candidate[:i], (), candidate[i+1:])
                    break
            if not expr:
                expr = TexCmd(candidate)
        while src.peek() in ARG_START_TOKENS:
            expr.args.append(read_tex(src))
        if mode == 'begin':
            read_env(src, expr)
        if src.startswith('$'):
            expr.add_contents(read_tex(src))
        return expr
    if c.startswith('\\'):
        return TexCmd(c[1:])
    if c in ARG_START_TOKENS:
        return read_arg(src, c)
    return c


def read_env(src, expr):
    r"""Read the environment from buffer.

    Advances the buffer until right after the end of the environment. Adds
    parsed content to the expression automatically.

    :param Buffer src: a buffer of tokens
    :param TexExpr expr: expression for the environment
    """
    contents = []
    while src.hasNext() and not src.startswith('\\end{%s}' % expr.name):
        if expr.name in SKIP_ENVS:
            if not contents:
                contents = [next(src)]
            else:
                contents[-1] = contents[-1] + next(src)
        elif src.peek() in ALL_TOKENS:
            contents.append(read_tex(src))
        else:
            contents.append(next(src))
    if not src.startswith('\\end{%s}' % expr.name):
        raise EOFError('Expecting \\end{%s}. Instead got %s' % (
            expr.name, src.peek((0, 5))))
    else:
        src.forward(5)
    expr.add_contents(*contents)
    return expr


def read_arg(src, c):
    """Read the argument from buffer.

    Advances buffer until right before the end of the argument.

    :param Buffer src: a buffer of tokens
    :param str c: argument token (starting token)
    :return: the parsed argument
    """
    content = [c]
    while src.hasNext():
        if src.peek() in ARG_END_TOKENS:
            content.append(next(src))
            break
        elif src.peek() in ALL_TOKENS:
            content.append(read_tex(src))
        else:
            content.append(next(src))
    return Arg.parse(content)