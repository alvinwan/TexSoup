"""Parsing mechanisms should not be directly invoked publicly, as they are
subject to change."""

from TexSoup.utils import Buffer, Token
from TexSoup.data import *
from TexSoup.tokens import (
    GCC,
    tokenize,
    ARG_START_TOKENS,
    ARG_END_TOKENS,
    SKIP_ENVS,
    COMMAND_TOKEN,
    MATH_SWITCH_TOKENS,
    END_OF_LINE_TOKENS,
    COMMENT_TOKEN,
)
import string


__all__ = ['read_tex']


def read_tex(src, skip_envs=(), context=None):
    r"""Read next expression from buffer

    :param Buffer src: a buffer of tokens
    :param Tuple[str] skip_envs: environments to skip parsing
    :param TexExpr context: parent expression
    :return: TexExpr
    """
    c = next(src)
    if c.category == GCC.Comment:
        return c
    elif c.category == GCC.MathSwitch:
        expr = TexEnv(c, [], nobegin=True)
        return read_math_env(src, expr)
    elif c.category == GCC.MathGroupStart:
        if c.startswith(TexDisplayMathEnv.start()):
            expr = TexDisplayMathEnv([])
        else:
            expr = TexMathEnv([])
        return read_math_env(src, expr)
    elif c.startswith(COMMAND_TOKEN):
        command = Token(c[1:], src.position)
        if command == 'item':
            contents, arg = read_item(src)
            mode, expr = 'command', TexCmd(command, contents, arg)
        elif command == 'begin':
            # allow whitespace TODO: should be built into command tokenization
            forward_until_non_whitespace(src)
            mode, expr, _ = 'begin', TexEnv(src.peek(1)), src.forward(3)
        else:
            mode, expr = 'command', TexCmd(command)

        expr.args = read_args(src, expr.args)

        if mode == 'begin':
            read_env(src, expr, skip_envs=skip_envs)
        return expr
    if c in ARG_START_TOKENS and isinstance(context, TexArgs) or c == '{':
        return read_arg(src, c)

    assert isinstance(c, Token)
    return TexText(c)


def stringify(string):
    return Token.join(string.split(' '), glue=' ')


def forward_until_non_whitespace(src):
    """Catch the first non-whitespace character."""
    t = Token('', src.peek().position)
    while (src.hasNext() and
            any([src.peek().startswith(sub) for sub in string.whitespace])
            and not any(t.strip(" ").endswith(c) for c in END_OF_LINE_TOKENS)):
        t += src.forward(1)
    return t


def read_item(src):
    r"""Read the item content.

    There can be any number of whitespace characters between \item and the
    first non-whitespace character. However, after that first non-whitespace
    character, the item can only tolerate one successive line break at a time.

    \item can also take an argument.

    :param Buffer src: a buffer of tokens
    :return: contents of the item and any item arguments
    """

    # Item argument such as in description environment
    arg = []
    extra = []

    if src.peek() in ARG_START_TOKENS:
        c = next(src)
        a = read_arg(src, c)
        arg.append(a)

    if not src.hasNext():
        return extra, arg

    last = stringify(forward_until_non_whitespace(src))
    extra.append(last.lstrip(" "))

    while (src.hasNext() and not str(src).strip(" ").startswith('\n\n') and
            not src.startswith(r'\item') and
            # TODO: replace witth regex? r"\\\s+?end"
            not src.startswith(r'\end') and
            not (isinstance(last, TexText) and
                 last._text.strip(" ").endswith('\n\n') and len(extra) > 1)):
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
        args.append(read_tex(src, context=args))

    # Restricted to only one line break after first argument
    line_breaks = 0
    while src.peek() in ARG_START_TOKENS or \
            (src.peek().isspace() and line_breaks == 0):
        space_index = src.num_forward_until(lambda s: not s.isspace())
        if space_index > 0:
            line_breaks += 1
            if src.peek((0, space_index)).count("\n") <= 1 and src.peek(
                    space_index) in ARG_START_TOKENS:
                args.append(read_tex(src, context=args))
        else:
            line_breaks = 0
            tex_text = read_tex(src, context=args)
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
