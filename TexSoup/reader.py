"""Parsing mechanisms should not be directly invoked publicly, as they are
subject to change."""

from TexSoup.utils import Token, Buffer, MixedBuffer, CharToLineOffset
from TexSoup.data import *
from TexSoup.data import arg_type
from TexSoup.tokens import (
    TC,
    tokenize,
    SKIP_ENVS,
)
import functools
import string
import sys


MATH_ENVS = (
    TexDisplayMathModeEnv,
    TexMathModeEnv,
    TexDisplayMathEnv,
    TexMathEnv
)
MATH_TOKEN_TO_ENV = {env.token_begin: env for env in MATH_ENVS}
ARG_BEGIN_TO_ENV = {arg.token_begin: arg for arg in arg_type}

SIGNATURES = {
    'def': (2, 0),
    'textbf': (1, 0),
    'section': (1, 1)
}


__all__ = ['read_expr', 'read_tex']


def read_tex(buf, skip_envs=(), tolerance=0):
    r"""Parse all expressions in buffer

    :param Buffer buf: a buffer of tokens
    :param Tuple[str] skip_envs: environments to skip parsing
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :return: iterable over parsed expressions
    :rtype: Iterable[TexExpr]
    """
    while buf.hasNext():
        yield read_expr(buf,
                        skip_envs=SKIP_ENVS + skip_envs,
                        tolerance=tolerance)


def make_read_peek(f):
    r"""Make any reader into a peek function.

    The wrapped function still parses the next sequence of tokens in the
    buffer but rolls back the buffer position afterwards.

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> def read(buf):
    ...     buf.forward(3)
    >>> buf = Buffer(tokenize(categorize(r'\item testing \textbf{hah}')))
    >>> buf.position
    0
    >>> make_read_peek(read)(buf)
    >>> buf.position
    0
    """
    @functools.wraps(f)
    def wrapper(buf, *args, **kwargs):
        start = buf.position
        ret = f(buf, *args, **kwargs)
        buf.backward(buf.position - start)
        return ret
    return wrapper


def read_expr(src, skip_envs=(), tolerance=0):
    r"""Read next expression from buffer

    :param Buffer src: a buffer of tokens
    :param Tuple[str] skip_envs: environments to skip parsing
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :return: parsed expression
    :rtype: [TexExpr, Token]
    """
    c = next(src)
    if c.category in MATH_TOKEN_TO_ENV.keys():
        expr = MATH_TOKEN_TO_ENV[c.category]([], position=c.position)
        return read_math_env(src, expr)
    elif c.category == TC.Escape:
        name, args = read_command(src, tolerance=tolerance)
        if name == 'item':
            contents = read_item(src)
            expr = TexCmd(name, contents, args, position=c.position)
        elif name == 'begin':
            assert args, 'Begin command must be followed by an env name.'
            expr = TexNamedEnv(
                args[0].string, args=args[1:], position=c.position)
            if expr.name in skip_envs:
                read_skip_env(src, expr)
            else:
                read_env(src, expr, tolerance=tolerance)
        else:
            expr = TexCmd(name, args=args, position=c.position)
        return expr
    if c.category == TC.GroupBegin:
        return read_arg(src, c, tolerance=tolerance)

    assert isinstance(c, Token)
    return TexText(c)


################
# ENVIRONMENTS #
################


def read_item(src, tolerance=0):
    r"""Read the item content. Assumes escape has just been parsed.

    There can be any number of whitespace characters between \item and the
    first non-whitespace character. Any amount of whitespace between subsequent
    characters is also allowed.

    \item can also take an argument.

    :param Buffer src: a buffer of tokens
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :return: contents of the item and any item arguments

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> def read_item_from(string, skip=2):
    ...     buf = tokenize(categorize(string))
    ...     _ = buf.forward(skip)
    ...     return read_item(buf)
    >>> read_item_from(r'\item aaa {bbb} ccc\end{itemize}')
    [' aaa ', BraceGroup('bbb'), ' ccc']
    >>> read_item_from(r'\item aaa \textbf{itemize}\item no')
    [' aaa ', TexCmd('textbf', [BraceGroup('itemize')])]
    >>> read_item_from(r'\item WITCH [nuuu] DOCTORRRR 👩🏻‍⚕️')
    [' WITCH ', '[', 'nuuu', ']', ' DOCTORRRR 👩🏻‍⚕️']
    >>> read_item_from(r'''\begin{itemize}
    ... \item
    ... \item first item
    ... \end{itemize}''', skip=8)
    ['\n']
    >>> read_item_from(r'''\def\itemeqn{\item}''', skip=7)
    []
    """
    extras = []

    while src.hasNext():
        if src.peek().category == TC.Escape:
            cmd_name, _ = make_read_peek(read_command)(
                src, 1, skip=1, tolerance=tolerance)
            if cmd_name in ('end', 'item'):
                return extras
        elif src.peek().category == TC.GroupEnd:
            break
        extras.append(read_expr(src, tolerance=tolerance))
    return extras


def unclosed_env_handler(src, expr, end):
    """Handle unclosed environments.

    Currently raises an end-of-file error. In the future, this can be the hub
    for unclosed-environment fault tolerance.

    :param Buffer src: a buffer of tokens
    :param TexExpr expr: expression for the environment
    :param end str: Actual end token (as opposed to expected)
    """
    clo = CharToLineOffset(str(src))
    explanation = 'Instead got %s' % end if end else 'Reached end of file.'
    line, offset = clo(src.position)
    raise EOFError('[Line: %d, Offset: %d] "%s" env expecting %s. %s' % (
        line, offset, expr.name, expr.end, explanation))


def read_math_env(src, expr):
    r"""Read the environment from buffer.

    Advances the buffer until right after the end of the environment. Adds
    parsed content to the expression automatically.

    :param Buffer src: a buffer of tokens
    :param TexExpr expr: expression for the environment
    :rtype: TexExpr

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> buf = tokenize(categorize(r'\min_x \|Xw-y\|_2^2'))
    >>> read_math_env(buf, TexMathModeEnv())
    Traceback (most recent call last):
        ...
    EOFError: [Line: 0, Offset: 7] "$" env expecting $. Reached end of file.
    """
    content = src.forward_until(lambda c: c.category == expr.token_end)
    if not src.hasNext() or src.peek().category != expr.token_end:
        unclosed_env_handler(src, expr, src.peek())
    next(src)
    expr.append(content)
    return expr


def read_skip_env(src, expr):
    r"""Read the environment from buffer, WITHOUT parsing contents

    Advances the buffer until right after the end of the environment. Adds
    UNparsed content to the expression automatically.

    :param Buffer src: a buffer of tokens
    :param TexExpr expr: expression for the environment
    :rtype: TexExpr

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> buf = tokenize(categorize(r' \textbf{aa \end{foobar}ha'))
    >>> read_skip_env(buf, TexNamedEnv('foobar'))
    TexNamedEnv('foobar', [' \\textbf{aa '], [])
    >>> buf = tokenize(categorize(r' \textbf{aa ha'))
    >>> read_skip_env(buf, TexNamedEnv('foobar'))  #doctest:+ELLIPSIS
    Traceback (most recent call last):
        ...
    EOFError: ...
    """
    def condition(s): return s.startswith('\\end{%s}' % expr.name)
    contents = [src.forward_until(condition, peek=False)]
    if not src.startswith('\\end{%s}' % expr.name):
        unclosed_env_handler(src, expr, src.peek((0, 6)))
    src.forward(5)
    expr.append(*contents)
    return expr


def read_env(src, expr, tolerance=0):
    r"""Read the environment from buffer.

    Advances the buffer until right after the end of the environment. Adds
    parsed content to the expression automatically.

    :param Buffer src: a buffer of tokens
    :param TexExpr expr: expression for the environment
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :rtype: TexExpr

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> buf = tokenize(categorize(' tingtang \\end\n{foobar}walla'))
    >>> read_env(buf, TexNamedEnv('foobar'))
    TexNamedEnv('foobar', [' tingtang '], [])
    >>> buf = tokenize(categorize(' tingtang \\end\n\n{foobar}walla'))
    >>> read_env(buf, TexNamedEnv('foobar')) #doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    EOFError: [Line: 0, Offset: 1] ...
    >>> buf = tokenize(categorize(' tingtang \\end\n\n{nope}walla'))
    >>> read_env(buf, TexNamedEnv('foobar'), tolerance=1)  # error tolerance
    TexNamedEnv('foobar', [' tingtang '], [])
    """
    contents = []
    while src.hasNext():
        if src.peek().category == TC.Escape:
            name, args = make_read_peek(read_command)(
                src, 1, skip=1, tolerance=tolerance)
            if name == 'end':
                break
        contents.append(read_expr(src, tolerance=tolerance))
    error = not src.hasNext() or not args or args[0].string != expr.name
    if error and tolerance == 0:
        unclosed_env_handler(src, expr, src.peek((0, 6)))
    elif not error:
        src.forward(5)
    expr.append(*contents)
    return expr


############
# COMMANDS #
############


# TODO: handle macro-weirdness e.g., \def\blah[#1][[[[[[[[#2{"#1 . #2"}
# TODO: add newcommand macro
def read_args(src, n_required=-1, n_optional=-1, args=None, tolerance=0):
    r"""Read all arguments from buffer.

    This function assumes that the command name has already been parsed. By
    default, LaTeX allows only up to 9 arguments of both types, optional
    and required. If `n_optional` is not set, all valid bracket groups are
    captured. If `n_required` is not set, all valid brace groups are
    captured.

    :param Buffer src: a buffer of tokens
    :param TexArgs args: existing arguments to extend
    :param int n_required: Number of required arguments. If < 0, all valid
                           brace groups will be captured.
    :param int n_optional: Number of optional arguments. If < 0, all valid
                           bracket groups will be captured.
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :return: parsed arguments
    :rtype: TexArgs

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> test = lambda s, *a, **k: read_args(tokenize(categorize(s)), *a, **k)
    >>> test('[walla]{walla}{ba]ng}')  # 'regular' arg parse
    [BracketGroup('walla'), BraceGroup('walla'), BraceGroup('ba', ']', 'ng')]
    >>> test('\t[wa]\n{lla}\n\n{b[ing}')  # interspersed spacers + 2 newlines
    [BracketGroup('wa'), BraceGroup('lla')]
    >>> test('\t[\t{a]}bs', 2, 0)  # use char as arg, since no opt args
    [BraceGroup('['), BraceGroup('a', ']')]
    >>> test('\n[hue]\t[\t{a]}', 2, 1)  # check stop opt arg capture
    [BracketGroup('hue'), BraceGroup('['), BraceGroup('a', ']')]
    >>> test('\t\\item')
    []
    >>> test('   \t    \n\t \n{bingbang}')
    []
    >>> test('[tempt]{ing}[WITCH]{doctorrrr}', 0, 0)
    []
    """
    args = args or TexArgs()
    if n_required == 0 and n_optional == 0:
        return args

    n_optional = read_arg_optional(src, args, n_optional, tolerance)
    n_required = read_arg_required(src, args, n_required, tolerance)

    if src.hasNext() and src.peek().category == TC.BracketBegin:
        n_optional = read_arg_optional(src, args, n_optional, tolerance)
    if src.hasNext() and src.peek().category == TC.GroupBegin:
        n_required = read_arg_required(src, args, n_required, tolerance)
    return args


def read_arg_optional(src, args, n_optional=-1, tolerance=0):
    """Read next optional argument from buffer.

    If the command has remaining optional arguments, look for:

       a. A spacer. Skip the spacer if it exists.
       b. A bracket delimiter. If the optional argument is bracket-delimited,
          the contents of the bracket group are used as the argument.

    :param Buffer src: a buffer of tokens
    :param TexArgs args: existing arguments to extend
    :param int n_optional: Number of optional arguments. If < 0, all valid
                           bracket groups will be captured.
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :return: number of remaining optional arguments
    :rtype: int
    """
    while n_optional != 0:
        spacer = read_spacer(src)
        if not (src.hasNext() and src.peek().category == TC.BracketBegin):
            if spacer:
                src.backward(1)
            break
        args.append(read_arg(src, next(src), tolerance=tolerance))
        n_optional -= 1
    return n_optional


def read_arg_required(src, args, n_required=-1, tolerance=0):
    r"""Read next required argument from buffer.

    If the command has remaining required arguments, look for:

       a. A spacer. Skip the spacer if it exists.
       b. A curly-brace delimiter. If the required argument is brace-delimited,
          the contents of the brace group are used as the argument.
       c. Spacer or not, if a brace group is not found, simply use the next
          character.

    :param Buffer src: a buffer of tokens
    :param TexArgs args: existing arguments to extend
    :param int n_required: Number of required arguments. If < 0, all valid
                           brace groups will be captured.
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :return: number of remaining optional arguments
    :rtype: int

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> buf = tokenize(categorize('{wal]la}\n{ba ng}\n'))
    >>> args = TexArgs()
    >>> read_arg_required(buf, args)  # 'regular' arg parse
    -3
    >>> args
    [BraceGroup('wal', ']', 'la'), BraceGroup('ba ng')]
    >>> buf.hasNext() and buf.peek().category == TC.MergedSpacer
    True
    """
    while n_required != 0 and src.hasNext():
        spacer = read_spacer(src)

        if src.hasNext() and src.peek().category == TC.GroupBegin:
            args.append(read_arg(src, next(src), tolerance=tolerance))
            n_required -= 1
            continue
        elif src.hasNext() and n_required > 0:
            args.append('{%s}' % next(src))
            n_required -= 1
            continue

        if spacer:
            src.backward(1)
        break
    return n_required


def read_arg(src, c, tolerance=0):
    r"""Read the argument from buffer.

    Advances buffer until right before the end of the argument.

    :param Buffer src: a buffer of tokens
    :param str c: argument token (starting token)
    :param int tolerance: error tolerance level (only supports 0 or 1)
    :return: the parsed argument
    :rtype: TexGroup

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> s = r'''{\item\abovedisplayskip=2pt\abovedisplayshortskip=0pt~\vspace*{-\baselineskip}}'''
    >>> buf = tokenize(categorize(s))
    >>> read_arg(buf, next(buf))
    BraceGroup(TexCmd('item'))
    >>> buf = tokenize(categorize(r'{\incomplete! [complete]'))
    >>> read_arg(buf, next(buf), tolerance=1)
    BraceGroup(TexCmd('incomplete'), '! ', '[', 'complete', ']')
    """
    content = [c]
    arg = ARG_BEGIN_TO_ENV[c.category]
    while src.hasNext():
        if src.peek().category == arg.token_end:
            src.forward()
            return arg(*content[1:], position=c.position)
        else:
            content.append(read_expr(src, tolerance=tolerance))

    if tolerance == 0:
        clo = CharToLineOffset(str(src))
        line, offset = clo(c.position)
        raise TypeError(
            '[Line: %d, Offset %d] Malformed argument. First and last elements '
            'must match a valid argument format. In this case, TexSoup'
            ' could not find matching punctuation for: %s.\n'
            'Just finished parsing: %s' %
            (line, offset, c, content))
    return arg(*content[1:], position=c.position)


def read_spacer(buf):
    r"""Extracts the next spacer, if there is one, before non-whitespace

    Define a spacer to be a contiguous string of only whitespace, with at most
    one line break.

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> read_spacer(Buffer(tokenize(categorize('   \t    \n'))))
    '   \t    \n'
    >>> read_spacer(Buffer(tokenize(categorize('   \t    \n\t \n  \t\n'))))
    '   \t    \n\t '
    >>> read_spacer(Buffer(tokenize(categorize('{'))))
    ''
    >>> read_spacer(Buffer(tokenize(categorize('   \t    \na'))))
    ''
    >>> read_spacer(Buffer(tokenize(categorize('   \t    \n\t \n  \t\na'))))
    '   \t    \n\t '
    """
    if buf.hasNext() and buf.peek().category == TC.MergedSpacer:
        return next(buf)
    return ''


def read_command(buf, n_required_args=-1, n_optional_args=-1, skip=0,
                 tolerance=0):
    r"""Parses command and all arguments. Assumes escape has just been parsed.

    No whitespace is allowed between escape and command name. e.g.,
    :code:`\ textbf` is a backslash command, then text :code:`textbf`. Only
    :code:`\textbf` is the bold command.

    >>> from TexSoup.category import categorize
    >>> from TexSoup.tokens import tokenize
    >>> buf = Buffer(tokenize(categorize('\\sect  \t    \n\t{wallawalla}')))
    >>> next(buf)
    '\\'
    >>> read_command(buf)
    ('sect', [BraceGroup('wallawalla')])
    >>> buf = Buffer(tokenize(categorize('\\sect  \t   \n\t \n{bingbang}')))
    >>> _ = next(buf)
    >>> read_command(buf)
    ('sect', [])
    >>> buf = Buffer(tokenize(categorize('\\sect{ooheeeee}')))
    >>> _ = next(buf)
    >>> read_command(buf)
    ('sect', [BraceGroup('ooheeeee')])
    >>> buf = Buffer(tokenize(categorize(r'\item aaa {bbb} ccc\end{itemize}')))
    >>> read_command(buf, skip=1)
    ('item', [])
    >>> buf.peek()
    ' aaa '
    """
    # Broken because abcd is incorrectly tokenized with leading space
    # >>> buf = Buffer(tokenize(categorize('\\sect abcd')))
    # >>> _ = next(buf)
    # >>> peek_command(buf)
    # ('sect', ('a',), 2)
    for _ in range(skip):
        next(buf)

    name = next(buf)
    token = Token('', buf.position)
    if n_required_args < 0 and n_optional_args < 0:
        n_required_args, n_optional_args = SIGNATURES.get(name, (-1, -1))
    args = read_args(buf, n_required_args, n_optional_args,
                     tolerance=tolerance)
    return name, args
