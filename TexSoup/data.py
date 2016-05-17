"""
Tex Data Structures
---

Includes the data structures that users will interface with, in addition to
internally used data structures.
"""
__all__ = ['TexNode', 'TexCmd', 'Arg', 'OArg', 'RArg', 'TexArgs']

#############
# Interface #
#############

class TexNode(object):
    """Main abstraction for Tex source, a tree node"""

    def __init__(self, cmd):
        """Creates TexNode object

        :param TexCmd cmd: a LaTeX command
        """
        self.cmd = command

    @property
    def contents(self):
        """Returns a list of all children, of this TeX element"""
        return list(self.children)

    @property
    def children(self):
        """Returns all immediate children of this TeX element"""
        return self.cmd.children

    @property
    def descendants(self):
        """Returns all descendants for this TeX element."""
        return itertools.chain(self.children,
            *[c.descendants for c in self.children])

    def find_all(self, name=None, attrs={}):
        """Return all descendant nodes matching criteria, naively."""
        for descendant in self.descendants:
            if descendant.__match__(name, attrs):
                yield descendant

    def find(self, name=None, attrs={}):
        """Return first descendant node matching criteria"""
        try:
            return next(self.find_all(name, attrs))
        except StopIteration:
            return None

    def __match__(self, name=None, attrs={}):
        """Check if given attributes match current object"""
        attrs['name'] = name
        for k, v in attrs.items():
            if getattr(self, k) != v:
                return False
        return True

    def __str__(self):
        """Stringified command"""
        return str(self.cmd)

    def __repr__(self):
        """Interpreter representation"""
        return '<TexNode name:%s args:%d>' % (
            self.cmd.name, len(self.cmd.args))

    def __getattr__(self, attr, default=None):
        """Convert all invalid attributes into basic find operation."""
        return self.find(attr) or default

###########
# Command #
###########

class TexCmd(object):
    r"""Abstraction for a LaTeX command. Contains two attributes: (1) the
    command name itself and (2) the command arguments, whether optional or
    required.

    >>> t = TexCmd('textbf', RArg('big ', TexCmd('textit', RArg('slant')), '.'))
    >>> t
    TexCmd('textbf', RArg('big ', TexCmd('textit', RArg('slant')), '.'))
    >>> print(t)
    \textbf{big \textit{slant}.}
    """

    def __init__(self, name, *args):
        self.name = name
        self.args = TexArgs(*args)

    def __str__(self):
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
        self.exprs = exprs

    @property
    def value(self):
        return ''.join(map(str, self.exprs))

    @staticmethod
    def parse(s):
        if isinstance(s, args):
            return s
        for arg in args:
            if arg.__is__(s):
                return arg(arg.__strip__(s))
        raise TypeError('Malformed argument. Must be an Arg or a string in either brackets or curly braces.')

    def __getitem__(self, i):
        return self.value[i]

    @classmethod
    def __is__(cls, s):
        """Test if string matches format."""
        sides = cls.fmt.split('%s')
        return s.startswith(sides[0]) and s.endswith(sides[1])

    @classmethod
    def __strip__(cls, s):
        """Strip string of format."""
        sides = cls.fmt.split('%s')
        return s[len(sides[0]):-len(sides[1])]

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
            ', '.join(map(repr, self.exprs)))

    def __str__(self):
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
    RArg('arg0'), OArg('arg1'), RArg('arg2')
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

    def __str__(self):
        """Stringifies a list of arguments.

        >>> str(TexArgs('{a}', '[b]', '{c}'))
        '{a}[b]{c}'
        """
        return ''.join(map(str, self.__args))

    def __repr__(self):
        """Stringifies a list of arguments.

        >>> TexArgs('{a}', '[b]', '{c}')
        RArg('a'), OArg('b'), RArg('c')
        """
        return ', '.join(map(repr, self.__args))
