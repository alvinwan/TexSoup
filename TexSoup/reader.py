"""Parsing mechanisms should not be directly invoked publicly, as they are
subject to change.
"""

from TexSoup.utils import to_buffer, Buffer, TokenWithPosition
from TexSoup.data import *
import TexSoup.data as data
import string

__all__ = ['tokenize', 'read_tex']

COMMAND_TOKENS = {'\\'}
MATH_TOKENS = {'$', '\[', '\]', '\(', '\)'}
COMMENT_TOKENS = {'%'}
ARG_START_TOKENS = {arg.delims()[0] for arg in data.arg_type}
ARG_END_TOKENS = {arg.delims()[1] for arg in data.arg_type}
ARG_TOKENS = ARG_START_TOKENS | ARG_END_TOKENS
ALL_TOKENS = COMMAND_TOKENS | ARG_TOKENS | MATH_TOKENS | COMMENT_TOKENS
SKIP_ENVS = ('verbatim', 'equation', 'lstlisting', 'align', 'alignat',
             'equation*', 'align*', 'math', 'displaymath', 'split', 'array',
             'eqnarray', 'eqnarray*', 'multline', 'multline*', 'gather',
             'gather*', 'flalign', 'flalign*',
             '$', '$$', '\[', '\]', '\(', '\)')
BRACKETS_DELIMITERS = {'(', ')', '<', '>', '[', ']', '{', '}',
                       '\{', '\}', '.' '|', '\langle', '\rangle',
                       '\lfloor', '\rfloor', '\lceil', '\rceil',
                       r'\ulcorner', r'\urcorner', '\lbrack', '\rbrack'}
SIZE_PREFIX = ('left', 'right', 'big', 'Big', 'bigg', 'Bigg')
PUNCTUATION_COMMANDS = {command + bracket
                        for command in SIZE_PREFIX
                        for bracket in BRACKETS_DELIMITERS.union({'|', '.'})}


#############
# Tokenizer #
#############


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
        while text.hasNext() and (c == '\\' or text.peek() not in tokens) and c not in MATH_TOKENS:
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
        return TokenWithPosition(text.forward(len(starter)), text.position)


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
    result = TokenWithPosition('', text.position)
    for c in text:
        if c == '\\' and str(text.peek()) in delimiters and str(c + text.peek()) not in delimiters:
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


##########
# Mapper #
##########


def read_tex(src, skip_envs=()):
    r"""Read next expression from buffer

    :param Buffer src: a buffer of tokens
    :return: TexExpr
    """
    c = next(src)
    if c.startswith('%'):
        return c
    elif c.startswith('$'):
        name = '$$' if c.startswith('$$') else '$'
        expr = TexEnv(name, [], nobegin=True)
        return read_math_env(src, expr)
    elif c.startswith('\[') or c.startswith("\("):
        if c.startswith('\['):
            name = 'displaymath'
            begin = '\['
            end = '\]'
        else:
            name = "math"
            begin = "\("
            end = "\)"

        expr = TexEnv(name, [], nobegin=True, begin=begin, end=end)
        return read_math_env(src, expr)
    elif c.startswith('\\'):
        command = TokenWithPosition(c[1:], src.position)
        if command == 'item':
            contents, arg = read_item(src)
            mode, expr = 'command', TexCmd(command, contents, arg)
        elif command == 'begin':
            mode, expr, _ = 'begin', TexEnv(src.peek(1)), src.forward(3)
        else:
            mode, expr = 'command', TexCmd(command)

        expr.args = read_args(src, expr.args)

        if mode == 'begin':
            read_env(src, expr, skip_envs=skip_envs)
        return expr
    if c in ARG_START_TOKENS:
        return read_arg(src, c)

    assert isinstance(c, TokenWithPosition)
    return TexText(c)


def read_item(src):
    r"""Read the item content.

    There can be any number of whitespace characters between \item and the first
    non-whitespace character. However, after that first non-whitespace
    character, the item can only tolerate one successive line break at a time.

    \item can also take an argument.

    :param Buffer src: a buffer of tokens
    :return: contents of the item and any item arguments
    """
    def stringify(s):
        return TokenWithPosition.join(s.split(' '), glue=' ')

    def forward_until_new(s):
        """Catch the first non-whitespace character"""
        t = TokenWithPosition('', s.peek().position)
        while (s.hasNext() and
                any([s.peek().startswith(substr) for substr in string.whitespace]) and
                not t.strip(" ").endswith('\n')):
            t += s.forward(1)
        return t

    # Item argument such as in description environment
    arg = []
    extra = []

    if src.peek() in ARG_START_TOKENS:
        c = next(src)
        a = read_arg(src, c)
        arg.append(a)

    if not src.hasNext():
        return extra, arg

    last = stringify(forward_until_new(src))
    extra.append(last.lstrip(" "))

    while (src.hasNext() and not str(src).strip(" ").startswith('\n\n') and
            not src.startswith('\item') and
            not src.startswith('\end') and
            not (isinstance(last, TexText) and last._text.strip(" ").endswith('\n\n') and len(extra) > 1)):
        last = read_tex(src)
        extra.append(last)
    return extra, arg


def read_math_env(src, expr):
    r"""Read the environment from buffer.

    Advances the buffer until right after the end of the environment. Adds
    parsed content to the expression automatically.

    :param Buffer src: a buffer of tokens
    :param TexExpr expr: expression for the environment
    :rtype: TexExpr
    """
    content = src.forward_until(lambda s: s == expr.end)
    if not src.startswith(expr.end):
        end = src.peek()
        explanation = 'Instead got %s' % end if end else 'Reached end of file.'
        raise EOFError('Expecting %s. %s' % (expr.end, explanation))
    else:
        src.forward(1)
    expr.append(content)
    return expr


def read_env(src, expr, skip_envs=()):
    r"""Read the environment from buffer.

    Advances the buffer until right after the end of the environment. Adds
    parsed content to the expression automatically.

    :param Buffer src: a buffer of tokens
    :param TexExpr expr: expression for the environment
    :rtype: TexExpr
    """
    contents = []
    if expr.name in SKIP_ENVS + skip_envs:
        contents = [src.forward_until(lambda s: s == '\\end')]
    while src.hasNext() and not src.startswith('\\end{%s}' % expr.name):
        contents.append(read_tex(src))
    if not src.startswith('\\end{%s}' % expr.name):
        end = src.peek((0, 5))
        explanation = 'Instead got %s' % end if end else 'Reached end of file.'
        raise EOFError('Expecting \\end{%s}. %s' % (expr.name, explanation))
    else:
        src.forward(4)
    expr.append(*contents)
    return expr


def read_args(src, args=None):
    r"""Read all arguments from buffer.

    Advances buffer until end of last valid arguments. There can be any number
    of whitespace characters between command and the first argument.
    However, after that first argument, the command can only tolerate one
    successive line break, before discontinuing the chain of arguments.

    :param TexArgs args: existing arguments to extend
    :return: parsed arguments
    :rtype: TexArgs
    """
    args = args or TexArgs()

    # Unlimited whitespace before first argument
    candidate_index = src.num_forward_until(lambda s: not s.isspace())
    while src.peek().isspace():
        args.append(read_tex(src))

    # Restricted to only one line break after first argument
    line_breaks = 0
    while src.peek() in ARG_START_TOKENS or \
            (src.peek().isspace() and line_breaks == 0):
        space_index = src.num_forward_until(lambda s: not s.isspace())
        if space_index > 0:
            line_breaks += 1
            if src.peek((0, space_index)).count("\n") <= 1 and src.peek(space_index) in ARG_START_TOKENS:
                args.append(read_tex(src))
        else:
            line_breaks = 0
            tex_text = read_tex(src)
            args.append(tex_text)

    if not args:
        src.backward(candidate_index)

    return args


def read_arg(src, c):
    """Read the argument from buffer.

    Advances buffer until right before the end of the argument.

    :param Buffer src: a buffer of tokens
    :param str c: argument token (starting token)
    :return: the parsed argument
    :rtype: Arg
    """
    content = [c]
    while src.hasNext():
        if src.peek() in ARG_END_TOKENS:
            content.append(next(src))
            break
        else:
            content.append(read_tex(src))
    return Arg.parse(content)
