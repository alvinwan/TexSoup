"""
Tex Data Structures
---

Includes the data structures that users will interface with, in addition to
internally used data structures.
"""
import itertools
from .utils import TokenWithPosition, CharToLineOffset

__all__ = ['TexNode', 'TexCmd', 'TexEnv', 'Arg', 'OArg', 'RArg', 'TexArgs']

#############
# Interface #
#############


class TexNode(object):
    """Main abstraction for Tex source, a tree node representing both Tex
    environments and Tex commands.

    Take the following example. Consider the `\begin{itemize}` environment.

    ```
    \begin{itemize}
      Floating text
      \item outer text
      \begin{enumerate}
        \item nested text
      \end{enumerate}
    \end{itemize}
    ```

    Here are its three properties `contents`, `children`, and `descendants`
    below:

    - `contents`: Anything and everything inside of this command. Everything
    needed to fully reconstruct the latex.

        ex. `["Floating Text", \item outer text, \begin{enumerate}]`.

    - `children`: Same as contents, but filter out random pieces of text.

        ex. Just `[\item outer text, \begin{enumerate}]`.

    - `descendants`: all children, and all children of all children, and all
     children of all children of all... etc.

        ex. `[\item outer text, \begin{enumerate}, \item nested text]`
    """

    def __init__(self, expr, src=None):
        """Creates TexNode object

        :param (TexCmd, TexEnv) expr: a LaTeX expression, either a singleton
            command or an environment containing other commands
        """
        assert isinstance(expr, (TexCmd, TexEnv)), 'Created from TexExpr'
        super().__init__()
        self.expr = expr
        if not src is None:
            self.char_to_line = CharToLineOffset(src)
        else:
            self.char_to_line = None

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
    def extra(self):
        """Extra string not a part of the expression name.

        This typically only occurs after an \item or similar LaTeX command.
        """
        return self.expr.extra

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

    def delete(self):
        """Delete this node from the parse tree tree."""
        self.parent.remove_child(self)

    def replace(self, *nodes):
        """Replace this node in the parse tree with the provided node(s)."""
        self.parent.replace_child(self, *nodes)

    def add_children(self, *nodes):
        """Add a node to its list of children."""
        self.expr.add_contents(*nodes)

    def add_children_at(self, i, *nodes):
        """Add a node to its list of children, inserted at position i."""
        assert isinstance(i, int), (
            'Provided index "%s" is not an integer! Did you switch your '
            'arguments? The first argument to `add_children_at` is the '
            'index.' % str(i))
        self.expr.add_contents_at(i, *nodes)

    def remove_child(self, node):
        """Remove a node from its list of contents."""
        self.expr.remove_content(node.expr)

    def replace_child(self, child, *nodes):
        """Replace provided node with node(s)."""
        self.expr.add_contents_at(
            self.expr.remove_content(child.expr),
            *nodes)

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

    def __getitem__(self, item):
        return list(self.contents)[item]

    def __iter__(self):
        """
        >>> node = TexNode(TexEnv('lstlisting', ('hai', 'there')))
        >>> list(node)
        ['hai', 'there']
        """
        return self.contents

    def __str__(self):
        """Stringified command"""
        return str(self.expr)

    def __repr__(self):
        """Interpreter representation"""
        return str(self)

    def __getattr__(self, attr, default=None):
        """Convert all invalid attributes into basic find operation."""
        return self.find(attr) or default

    def char_pos_to_line(self, char_pos):
        assert not self.char_to_line is None, 'CharToLineOffset is not initialized! Pass src to TexNode!'
        return self.char_to_line(char_pos)


###############
# Expressions #
###############


class TexExpr(object):
    """General TeX expression abstract"""

    def __init__(self, name, contents=(), args=()):
        self.name = name.strip()
        self.args = TexArgs(*args)
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
                 nobegin=False):
        """Initialization for Tex environment.

        :param str name: name of environment
        :param list contents: list of contents
        :param list args: list of Tex Arguments
        :param bool preserve_whitespace: If false, elements containing only
            whitespace will be removed from contents.
        :param bool nobegin: Disable \begin{...} notation.
        """
        super().__init__(name, contents, args)
        self.preserve_whitespace = preserve_whitespace
        self.nobegin = nobegin

    @property
    def contents(self):
        for content in self._contents:
            if not isinstance(content, TokenWithPosition) or bool(content.strip()):
                yield content

    def __str__(self):
        contents = '\n'.join(map(str, self._contents))
        if self.name == '[tex]':
            return contents
        if self.nobegin:
            return '%s%s%s' % (
                self.name, contents, self.name)
        return '\\begin{%s}%s%s\\end{%s}' % (
            self.name, self.args, contents, self.name)

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

    def add_contents(self, *contents):
        """Amend extra instead of contents, as commands do not have contents."""
        self.extra += ' '.join([str(c) for c in contents])

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
    """LaTeX command argument

    >>> arg = Arg('huehue')
    >>> arg[0]
    'h'
    >>> arg[1:]
    'uehue'
    """

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
            raise TypeError('Malformed argument. First and last elements must '
                            'match a valid argument format. In this case, TexSoup'
                            ' could not find matching punctuation for: %s.\n'
                            'Common issues include: Unescaped special characters,'
                            ' mistyped closing punctuation, misalignment.' % (str(s)))
        for arg in args:
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
