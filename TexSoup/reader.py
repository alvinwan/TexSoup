from TexSoup.utils import to_buffer, Buffer, TokenWithPosition
from TexSoup.data import *
import TexSoup.data as data
import string

__all__ = ['tokenize', 'read_tex']

COMMAND_TOKENS = {'\\'}
MATH_TOKENS = {'$'}
ARG_START_TOKENS = {arg.delims()[0] for arg in data.args}
ARG_END_TOKENS = {arg.delims()[1] for arg in data.args}
ARG_TOKENS = ARG_START_TOKENS | ARG_END_TOKENS
ALL_TOKENS = COMMAND_TOKENS | ARG_TOKENS | MATH_TOKENS
SKIP_ENVS = ('verbatim', 'equation', 'lstlisting', '$', '$$')
BRACKETS_DELIMITERS = {'(', ')', '<', '>', '\[', '[', ']', '{',
                       '\{', '\}', '.' '|', '\langle', '\rangle',
                       '\lfloor', '\rfloor', '\lceil', '\rceil',
                       r'\ulcorner', r'\urcorner', '\lbrack', '\rbrack'}
PUNCTUATION_COMMANDS = {command + bracket
                        for command in ('left', 'right')
                        for bracket in BRACKETS_DELIMITERS.union({'|', '.'})}


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
    \textbf { Do play  \textit { nice } . }
    >>> print(*tokenize(r'\begin{tabular} 0 & 1 \\ 2 & 0 \end{tabular}'))
    \begin { tabular }  0 & 1 \\ 2 & 0  \end { tabular }
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
                return text.forward(len(string) + 1)


@token('command')
def tokenize_command(text):
    """Process command, but ignore line breaks. (double backslash)

    :param Buffer text: iterator over line, with current position
    """
    if text.peek() == '\\':
        c = text.forward(1)
        tokens = string.punctuation + string.whitespace
        while text.hasNext() and text.peek() not in tokens:
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
    result = TokenWithPosition('', text.position)
    if text.peek() == '%':
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

    >>> b = Buffer('$\min_x$ \command')
    >>> tokenize_math(b)
    '$'
    >>> b = Buffer('$$\min_x$$ \command')
    >>> tokenize_math(b)
    '$$'
    """
    if text.startswith('$') and (text.position == 0 or text.peek(-1) != '\\'):
        starter = '$$' if text.startswith('$$') else '$'
        return TokenWithPosition(text.forward(len(starter)), text.position)


@token('string')
def tokenize_string(text, delimiters=ALL_TOKENS):
    r"""Process a string of text

    :param Buffer text: iterator over line, with current position

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
    result = TokenWithPosition('', text.position)
    for c in text:
        if c == '\\' and str(text.peek()) in delimiters:
            c += next(text)
        elif str(c) in delimiters:  # assumes all tokens are single characters
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
        expr = TexEnv(name, [], nobegin=True)
        return read_math_env(src, expr)
    if c.startswith('\\'):
        command = TokenWithPosition(c[1:], src.position)
        if command == 'item':
            extra = src.forward_until({'\n', '\end', '\item'})
            mode, expr = 'command', TexCmd(command, (),
                TokenWithPosition.join(extra.split(' '), glue=' ').strip())
        elif command == 'begin':
            mode, expr, _ = 'begin', TexEnv(src.peek(1)), src.forward(3)
        else:
            mode, expr = 'command', TexCmd(command)

        # TODO: allow this whitespace between arguments
        # TODO: allow only one line break
        # TODO: should really be handled by tokenizer
        whitespace = src.forward_until_not(set(string.whitespace))
        while src.peek() in ARG_START_TOKENS:
            expr.args.append(read_tex(src))
        if mode == 'begin':
            read_env(src, expr, whitespace=whitespace)  # TODO: hacky fix. use src.backward instead
        return expr
    if c in ARG_START_TOKENS:
        return read_arg(src, c)
    return c


def read_math_env(src, expr, whitespace=''):
    r"""Read the environment from buffer.

    Advances the buffer until right after the end of the environment. Adds
    parsed content to the expression automatically.

    :param Buffer src: a buffer of tokens
    :param TexExpr expr: expression for the environment
    :param whitespace str: temporary prefix for skip_envs
    """
    content = whitespace + src.forward_until({expr.name})
    if not src.startswith(expr.name):
        end = src.peek()
        explanation = 'Instead got %s' % end if end else 'Reached end of file.'
        raise EOFError('Expecting %s. %s' % (expr.name, explanation))
    else:
        src.forward(1)
    expr.add_contents(content)
    return expr


def read_env(src, expr, whitespace=''):
    r"""Read the environment from buffer.

    Advances the buffer until right after the end of the environment. Adds
    parsed content to the expression automatically.

    :param Buffer src: a buffer of tokens
    :param TexExpr expr: expression for the environment
    :param whitespace str: temporary prefix for skip_envs
    """
    contents = []
    if expr.name in SKIP_ENVS:
        contents = [whitespace + src.forward_until({'\\end'})]
    while src.hasNext() and not src.startswith('\\end{%s}' % expr.name):
        contents.append(read_tex(src))
    if not src.startswith('\\end{%s}' % expr.name):
        end = src.peek((0, 5))
        explanation = 'Instead got %s' % end if end else 'Reached end of file.'
        raise EOFError('Expecting \\end{%s}. %s' % (expr.name, explanation))
    else:
        src.forward(4)
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
