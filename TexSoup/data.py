"""
TexSoup transforms a LaTeX document into a complex tree of various Python
objects, but all objects fall into one of the following three categories:
``TexNode``, ``TexExpr`` (environments and commands), and ``Arg`` s.
"""
import itertools
import re
from .utils import TokenWithPosition, CharToLineOffset

__all__ = ['TexNode', 'TexCmd', 'TexEnv', 'Arg', 'OArg', 'RArg', 'TexArgs']


#############
# Interface #
#############


class TexNode(object):
    r"""A tree node representing an expression in the LaTeX document.

    Every node in the parse tree is a ``TexNode``, equipped with navigation,
    search, and modification utilities.
    """

    def __init__(self, expr, src=None):
        """Creates TexNode object

        :param TexExpr expr: a LaTeX expression, either a singleton
            command or an environment containing other commands
        :param str src: LaTeX source string
        """
        assert isinstance(expr, (TexCmd, TexEnv)), 'Created from TexExpr'
        super().__init__()
        self.expr = expr
        if src is not None:
            self.char_to_line = CharToLineOffset(src)
        else:
            self.char_to_line = None

    #################
    # MAGIC METHODS #
    #################

    def __getattr__(self, attr, default=None):
        """Convert all invalid attributes into basic find operation."""
        return self.find(attr) or default

    def __getitem__(self, item):
        return list(self.contents)[item]

    def __iter__(self):
        """
        >>> node = TexNode(TexEnv('lstlisting', ('hai', 'there')))
        >>> list(node)
        ['hai', 'there']
        """
        return self.contents

    def __match__(self, name=None, attrs=()):
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

    def __repr__(self):
        """Interpreter representation"""
        return str(self)

    def __str__(self):
        """Stringified command"""
        return str(self.expr)

    ##############
    # PROPERTIES #
    ##############

    @property
    def args(self):
        return self.expr.args

    @property
    def children(self):
        """Immediate children of this TeX element that are valid TeX objects.

        In effect, same as contents, but remove random pieces of text.

        :return: generator of all children
        """
        for child in self.expr.children:
            child.parent = self
            yield TexNode(child)

    @property
    def contents(self):
        """Any non-whitespace contents inside of this TeX element.

        :return: generator of all contents
        """
        for child in self.expr.contents:
            if isinstance(child, (TexEnv, TexCmd)):
                yield TexNode(child)
            else:
                yield child

    @property
    def descendants(self):
        """Returns all descendants for this TeX element."""
        return self.__descendants()

    @property
    def extra(self):
        """Extra string not a part of the expression name.

        This typically only occurs after an item or similar LaTeX command.
        """
        return self.expr.extra

    @property
    def name(self):
        return self.expr.name

    # Should be set by parent otherwise returns None result
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
    def text(self):
        for descendant in self.contents:
            if isinstance(descendant, TokenWithPosition):
                yield descendant
            elif hasattr(descendant, 'text'):
                yield from descendant.text

    @property
    def tokens(self):
        """Returns generator of all tokens, for this Tex element"""
        return self.expr.tokens

    ##################
    # PUBLIC METHODS #
    ##################

    def add_children(self, *nodes):
        r"""Add node(s) to this node's list of children.

        :param TexNode nodes: List of nodes to add

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \section{Hey}
        ... \textbf{Silly}
        ... \textit{Willy}''')
        >>> soup.section
        \section{Hey}
        >>> soup.section.add_children(soup.textbf, soup.textit)
        >>> soup.section
        \section{Hey} \textbf{Silly}\textit{Willy}
        """
        self.expr.add_contents(*nodes)

    def add_children_at(self, i, *nodes):
        r"""Add a node to its list of children, inserted at position i.

        :param int i: Position to add nodes to
        :param TexNode nodes: List of nodes to add
        """
        assert isinstance(i, int), (
                'Provided index "{}" is not an integer! Did you switch your '
                'arguments? The first argument to `add_children_at` is the '
                'index.'.format(i))
        self.expr.add_contents_at(i, *nodes)

    def char_pos_to_line(self, char_pos):
        r"""Translate character position in the original document to line number.

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \section{Hey}
        ... \textbf{Silly}
        ... \textit{Willy}''')
        """
        assert self.char_to_line is not None, (
            'CharToLineOffset is not initialized. Pass src to TexNode '
            'constructor')
        return self.char_to_line(char_pos)

    def count(self, name=None, **attrs):
        """Return number of descendants matching criteria"""
        return len(list(self.find_all(name, **attrs)))

    def delete(self):
        """Delete this node from the parse tree tree."""
        self.parent.remove_child(self)

    def find(self, name=None, **attrs):
        """Return first descendant node matching criteria"""
        try:
            return next(self.find_all(name, **attrs))
        except StopIteration:
            return None

    def find_all(self, name=None, **attrs):
        """Return all descendant nodes matching criteria, naively."""
        for descendant in self.__descendants():
            if hasattr(descendant, '__match__') and \
                    descendant.__match__(name, attrs):
                yield descendant

    def remove_child(self, node):
        """Remove a node from its list of contents."""
        self.expr.remove_content(node.expr)

    def replace(self, *nodes):
        """Replace this node in the parse tree with the provided node(s)."""
        self.parent.replace_child(self, *nodes)

    def replace_child(self, child, *nodes):
        """Replace provided node with node(s)."""
        self.expr.add_contents_at(
            self.expr.remove_content(child.expr),
            *nodes)

    def search_regex(self, pattern):
        for node in self.text:
            for match in re.finditer(pattern, node):
                body = match.group()  # group() returns the full match
                start = match.start()
                yield TokenWithPosition(body, node.position + start)

    def __descendants(self):
        """Implementation for descendants, hacky workaround for __getattr__
        issues.
        """
        return itertools.chain(self.contents,
                               *[c.descendants for c in self.children])


###############
# Expressions #
###############


class TexExpr(object):
    """General TeX expression abstract"""

    def __init__(self, name, contents=(), args=(), stuff=()):
        self.name = name.strip()
        self.args = TexArgs(*args)
        self.stuff = stuff
        self.parent = self.parent if hasattr(self, 'parent') else None
        self._contents = contents or []

        for content in contents:
            if isinstance(content, (TexEnv, TexCmd)):
                content.parent = self

    def add_contents(self, *contents):
        self._contents.extend(contents)

    def add_contents_at(self, i, *contents):
        for j, content in enumerate(contents):
            self._contents.insert(i + j, content)

    def remove_content(self, expr):
        """Remove a provided expression from its list of contents.

        :return: index of the expression removed
        """
        index = self._contents.index(expr)
        self._contents.remove(expr)
        return index

    @property
    def contents(self):
        """Returns all tokenized chunks for a particular expression."""
        raise NotImplementedError()

    @property
    def arguments(self):
        return AllArgs(self.stuff)

    @property
    def tokens(self):
        """Further breaks down all tokens for a particular expression into
        words and other expressions.

        >>> tex = TexEnv('lstlisting', ('var x = 10',))
        >>> list(tex.tokens)
        ['var x = 10']
        """
        for content in self.contents:
            if isinstance(content, TokenWithPosition):
                for word in content.split():
                    yield word
            else:
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

    >>> t = TexEnv('tabular', ['\n0 & 0 & * \\\\\n1 & 1 & * \\\\\n'],
    ...     [RArg('c | c c')])
    >>> t
    TexEnv('tabular', ['\n0 & 0 & * \\\\\n1 & 1 & * \\\\\n'], [RArg('c | c c')])
    >>> print(t)
    \begin{tabular}{c | c c}
    0 & 0 & * \\
    1 & 1 & * \\
    \end{tabular}
    >>> len(list(t.children))
    0
    """

    def __init__(self, name, contents=(), args=(), preserve_whitespace=False,
                 nobegin=False, begin=False, end=False, stuff=()):
        """Initialization for Tex environment.

        :param str name: name of environment
        :param iterable contents: list of contents
        :param iterable args: list of Tex Arguments
        :param bool preserve_whitespace: If false, elements containing only
            whitespace will be removed from contents.
        :param bool nobegin: Disable \begin{...} notation.
        """
        super().__init__(name, contents, args, stuff)
        self.preserve_whitespace = preserve_whitespace
        self.stuff = stuff if stuff else []

        self.nobegin = nobegin
        self.begin = begin if begin else (self.name if self.nobegin else "\\begin{%s}" % self.name)
        self.end = end if end else (self.name if self.nobegin else "\\end{%s}" % self.name)

    @property
    def contents(self):
        for content in self._contents:
            if not isinstance(content, TokenWithPosition) or bool(content.strip()) or self.preserve_whitespace:
                yield content

    @property
    def everything(self):
        for content in self._contents:
            yield content

    def __str__(self):
        contents = ''.join(map(str, self._contents))
        if self.name == '[tex]':
            return contents
        else:
            return '%s%s%s' % (
                self.begin + str(self.args), contents, self.end)

    def __repr__(self):
        if not self.args:
            return "TexEnv('%s')" % self.name
        return "TexEnv('%s', %s, %s)" % (self.name, repr(self._contents), repr(self.args))


class TexCmd(TexExpr):
    r"""Abstraction for a LaTeX command. Contains two attributes: (1) the
    command name itself and (2) the command arguments, whether optional or
    required.

    :param str name: name of the command, e.g., "textbf"
    :param list args: Arg objects
    :param list extra: TexExpr objects

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

    def __init__(self, name, args=(), extra=(), stuff=()):
        super().__init__(name, [], args, stuff)
        self.extra = extra if extra else []
        self.stuff = stuff if stuff else []

    @property
    def contents(self):
        """All contents of command arguments"""
        for arg in self.args:
            for expr in arg:
                yield expr
        if self.extra:
            for expr in self.extra:
                yield expr

    def add_contents(self, *contents):
        """Amend extra instead of contents, as commands do not have contents."""
        self.extra.extend(contents)

    def __str__(self):
        if self.extra:
            return '\\%s%s %s' % (self.name, self.args, ''.join(
                [str(e) for e in self.extra]))
        return '\\%s%s' % (self.name, self.args)

    def __repr__(self):
        if not self.args:
            return "TexCmd('%s')" % self.name
        return "TexCmd('%s', %s)" % (self.name, repr(self.args))


#############
# Arguments #
#############


# A general Argument class
class Arg(object):
    """LaTeX command argument

    >>> arg = Arg('huehue')
    >>> arg[0]
    'h'
    >>> arg[1:]
    'uehue'
    """

    def __init__(self, *exprs):
        """Initialize argument using list of expressions.

        :param Union[str,TexCmd,TexEnv] exprs: Tex expressions contained in the
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

        :param Union[str,iterable] s: Either a string or a list, where the first and
            last elements are valid argument delimiters.
        """
        if isinstance(s, arg_type):
            return s
        if isinstance(s, (list, tuple)):
            for arg in arg_type:
                if [s[0], s[-1]] == arg.delims():
                    return arg(*s[1:-1])
            raise TypeError('Malformed argument. First and last elements must '
                            'match a valid argument format. In this case, TexSoup'
                            ' could not find matching punctuation for: %s.\n'
                            'Common issues include: Unescaped special characters,'
                            ' mistyped closing punctuation, misalignment.' % (str(s)))
        for arg in arg_type:
            if arg.__is__(s):
                return arg(arg.__strip__(s))
        raise TypeError('Malformed argument. Must be an Arg or a string in '
                        'either brackets or curly braces.')

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

    fmt = "%s"


class OArg(Arg):
    """Optional argument."""

    fmt = '[%s]'
    type = 'optional'


class RArg(Arg):
    """Required argument."""

    fmt = '{%s}'
    type = 'required'


arg_type = (OArg, RArg)


class TexArgs(list):
    """List data structure, supporting additional ops for command arguments

    Use regular indexing to access the argument value. Use parentheses, like
    a method invocation, to access an Arg object.

    >>> arguments = TexArgs(RArg('arg0'), '[arg1]', '{arg2}')
    >>> arguments
    [RArg('arg0'), OArg('arg1'), RArg('arg2')]
    >>> arguments(2)
    RArg('arg2')
    >>> arguments[2]
    'arg2'
    >>> arguments(2).type
    'required'
    >>> str(arguments(2))
    '{arg2}'
    >>> arguments.append('[arg3]')
    >>> arguments(3)
    OArg('arg3')
    >>> len(arguments)
    4
    """

    def __init__(self, *args):
        """Append all arguments to list"""
        super().__init__()
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


class AllArgs(list):

    def __init__(self, stuff):
        super().__init__()
        self.stuff = stuff

    def __str__(self):
        return "".join([str(tex) for tex in self.stuff])

    def __repr__(self):
        return self.stuff

    def __iter__(self):
        return iter(self.stuff)
