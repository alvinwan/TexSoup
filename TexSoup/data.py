"""
Tex Data Structures
---

Includes the data structures that users will interface with, in addition to
internally used data structures.
"""
import itertools

__all__ = ['TexNode', 'TexCmd', 'TexEnv', 'Arg', 'OArg', 'RArg', 'TexArgs']

#############
# Interface #
#############

class TexNode(object):
    """Main abstraction for Tex source, a tree node representing both Tex
    environments and Tex commands.
    """

    def __init__(self, expr):
        """Creates TexNode object

        :param (TexCmd, TexEnv) expr: a LaTeX expression, either a singleton
            command or an environment containing other commands
        """
        assert isinstance(expr, (TexCmd, TexEnv)), 'Created from TexExpr'
        super().__init__()
        self.expr = expr

    @property
    def name(self):
        return self.expr.name

    @property
    def args(self):
        return self.expr.args

    @property
    def parent(self):
        return self.expr.parent

    @property
    def string(self):
        """Returns 'string' content, which is valid if and only if (1) the
        expression is a TexCmd and (2) the command has only one argument.
        """
        if isinstance(self.expr, TexCmd) and len(self.expr.args) == 1:
            return str(self.expr.args[0])

    @property
    def tokens(self):
        """Returns generator of all tokens, for this Tex element"""
        return self.expr.tokens

    @property
    def contents(self):
        """Returns a generator of all contents, for this TeX element"""
        for child in self.expr.contents:
            if isinstance(child, (TexEnv, TexCmd)):
                yield TexNode(child)
            else:
                yield child

    @property
    def children(self):
        """Returns all immediate children of this TeX element"""
        for child in self.expr.children:
            child.parent = self
            yield TexNode(child)

    @property
    def descendants(self):
        """Returns all descendants for this TeX element."""
        return self.__descendants()

    def __descendants(self):
        """Implementation for descendants, hacky workaround for __getattr__
        issues.
        """
        return itertools.chain(self.contents,
            *[c.descendants for c in self.children])

    def find_all(self, name=None, **attrs):
        """Return all descendant nodes matching criteria, naively."""
        for descendant in self.__descendants():
            if hasattr(descendant, '__match__') and \
                descendant.__match__(name, attrs):
                yield descendant

    def find(self, name=None, **attrs):
        """Return first descendant node matching criteria"""
        try:
            return next(self.find_all(name, **attrs))
        except StopIteration:
            return None

    def count(self, name=None, **attrs):
        """Return number of descendants matching criteria"""
        return len(list(self.find_all(name, **attrs)))

    def __match__(self, name=None, attrs={}):
        r"""Check if given attributes match current object

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'\ref{hello}\ref{hello}\ref{hello}\ref{nono}')
        >>> soup.count(r'\ref{hello}')
        3
        """
        if '{' in name or '[' in name:
            return str(self) == name
        attrs['name'] = name
        for k, v in attrs.items():
            if getattr(self, k) != v:
                return False
        return True

    def __str__(self):
        """Stringified command"""
        return str(self.expr)

    def __repr__(self):
        """Interpreter representation"""
        return str(self)

    def __getattr__(self, attr, default=None):
        """Convert all invalid attributes into basic find operation."""
        return self.find(attr) or default

###############
# Expressions #
###############

class TexExpr(object):
    """General TeX expression abstract"""

    def __init__(self, name, contents=(), args=()):
        self.name = name
        self.args = TexArgs(*args)
        self._contents = contents or []

        for content in contents:
            if isinstance(content, (TexEnv, TexCmd)):
                content.parent = self

    def addContents(self, *contents):
        self._contents.extend(contents)

    @property
    def contents(self):
        """Returns all tokenized chunks for a particular expression."""
        raise NotImplementedError()

    @property
    def tokens(self):
        """Further breaks down all tokens for a particular expression into
        words and other expressions."""
        for content in self.contents:
            if isinstance(str, content):
                for word in content.split():
                    yield word
            yield content

    @property
    def children(self):
        """Returns all child expressions for a particular expression."""
        return filter(lambda x: isinstance(x, (TexEnv, TexCmd)), self.contents)


class TexEnv(TexExpr):
    r"""Abstraction for a LaTeX command, denoted by \begin{env} and \end{env}.
    Contains three attributes: (1) the environment name itself, (2) the
    environment arguments, whether optional or required, and (3) the
    environment's contents.

    >>> t = TexEnv('tabular', ['0 & 0 & * \\\\', '1 & 1 & * \\\\'],
    ...     [RArg('c | c c')])
    >>> t
    TexEnv('tabular', ['0 & 0 & * \\\\', '1 & 1 & * \\\\'], [RArg('c | c c')])
    >>> print(t)
    \begin{tabular}{c | c c}
    0 & 0 & * \\
    1 & 1 & * \\
    \end{tabular}
    >>> len(list(t.children))
    0
    """

    def __init__(self, name, contents=(), args=(), preserve_whitespace=False):
        """Initialization for Tex environment.

        :param str name: name of environment
        :param list contents: list of contents
        :param list args: list of Tex Arguments
        :param bool preserve_whitespace: If false, elements containing only
            whitespace will be removed from contents.
        """
        super().__init__(name, contents, args)

    @property
    def contents(self):
        for content in self._contents:
            if not isinstance(content, str) or bool(content.strip()):
                yield content

    def __str__(self):
        return '\\begin{%s}%s\n%s\n\\end{%s}' % (
            self.name, self.args,'\n'.join(map(str, self._contents)), self.name)

    def __repr__(self):
        if not self.args:
            return "TexEnv('%s')" % self.name
        return "TexEnv('%s', %s, %s)" % (self.name,
            repr(self._contents), repr(self.args))


class TexCmd(TexExpr):
    r"""Abstraction for a LaTeX command. Contains two attributes: (1) the
    command name itself and (2) the command arguments, whether optional or
    required.

    >>> t = TexCmd('textbf',[RArg('big ',TexCmd('textit',[RArg('slant')]),'.')])
    >>> t
    TexCmd('textbf', [RArg('big ', TexCmd('textit', [RArg('slant')]), '.')])
    >>> print(t)
    \textbf{big \textit{slant}.}
    >>> children = list(map(str, t.children))
    >>> len(children)
    1
    >>> print(children[0])
    \textit{slant}
    """

    def __init__(self, name, args=(), extra=''):
        super().__init__(name, [], args)
        self.extra = extra

    @property
    def contents(self):
        """All contents of command arguments"""
        for arg in self.args:
            for expr in arg:
                yield expr
        if self.extra:
            yield self.extra

    def __str__(self):
        if self.extra:
            return '\\%s%s %s' % (self.name, self.args, self.extra)
        return '\\%s%s' % (self.name, self.args)

    def __repr__(self):
        if not self.args:
            return "TexCmd('%s')" % self.name
        return "TexCmd('%s', %s)" % (self.name, repr(self.args))

#############
# Arguments #
#############

class Arg(object):
    """LaTeX command argument"""

    def __init__(self, *exprs):
        """Initialize argument using list of expressions.

        :param [str, TexCmd, TexEnv] exprs: Tex expressions contained in the
            argument. Can be other commands or environments, or even strings.
        """
        self.exprs = exprs

    @property
    def value(self):
        """Argument value, without format."""
        return ''.join(map(str, self.exprs))

    @staticmethod
    def parse(s):
        """Parse a string or list and return an Argument object

        :param (str, list) s: Either a string or a list, where the first and
            last elements are valid argument delimiters.
        """
        if isinstance(s, args):
            return s
        if isinstance(s, (list, tuple)):
            for arg in args:
                if [s[0], s[-1]] == arg.delims():
                    return arg(*s[1:-1])
            raise TypeError('Malformed argument. First and last elements must match a valid argument format: %s' % s)
        for arg in args:
            if arg.__is__(s):
                return arg(arg.__strip__(s))
        raise TypeError('Malformed argument. Must be an Arg or a string in either brackets or curly braces.')

    def __getitem__(self, i):
        """Retrieve an argument's value"""
        return self.value[i]

    @classmethod
    def delims(cls):
        """Returns delimiters"""
        return cls.fmt.split('%s')

    @classmethod
    def __is__(cls, s):
        """Test if string matches format."""
        return s.startswith(cls.delims()[0]) and s.endswith(cls.delims()[1])

    @classmethod
    def __strip__(cls, s):
        """Strip string of format."""
        sides = cls.fmt.split('%s')
        return s[len(cls.delims()[0]):-len(cls.delims()[1])]

    def __iter__(self):
        """Iterator iterates over all argument contents."""
        return iter(self.exprs)

    def __repr__(self):
        """Makes argument display-friendly."""
        return '%s(%s)' % (self.__class__.__name__,
            ', '.join(map(repr, self.exprs)))

    def __str__(self):
        """Stringifies argument value."""
        return self.fmt % self.value

class OArg(Arg):
    """Optional argument."""

    fmt = '[%s]'
    type = 'optional'

class RArg(Arg):
    """Required argument."""

    fmt = '{%s}'
    type = 'required'

args = (OArg, RArg)

class TexArgs(list):
    """List data structure, supporting additional ops for command arguments

    Use regular indexing to access the argument value. Use parentheses, like
    a method invocation, to access an Arg object.

    >>> args = TexArgs(RArg('arg0'), '[arg1]', '{arg2}')
    >>> args
    [RArg('arg0'), OArg('arg1'), RArg('arg2')]
    >>> args(2)
    RArg('arg2')
    >>> args[2]
    'arg2'
    >>> args(2).type
    'required'
    >>> str(args(2))
    '{arg2}'
    >>> args.append('[arg3]')
    >>> args(3)
    OArg('arg3')
    >>> len(args)
    4
    """

    def __init__(self, *args):
        """Append all arguments to list"""
        self.__args = []
        for arg in args:
            self.append(arg)

    def append(self, value):
        """Append a value to the list"""
        arg = Arg.parse(value)
        self.__args.append(arg)
        list.append(self, arg.value)

    def __call__(self, i):
        """
        Access more information about an argument using function-call syntax.
        """
        return self.__args[i]

    def __iter__(self):
        """Iterator iterates over all argument objects."""
        return iter(self.__args)

    def __str__(self):
        """Stringifies a list of arguments.

        >>> str(TexArgs('{a}', '[b]', '{c}'))
        '{a}[b]{c}'
        """
        return ''.join(map(str, self.__args))

    def __repr__(self):
        """Makes list of arguments command-line friendly.

        >>> TexArgs('{a}', '[b]', '{c}')
        [RArg('a'), OArg('b'), RArg('c')]
        """
        return '[%s]' % ', '.join(map(repr, self.__args))
