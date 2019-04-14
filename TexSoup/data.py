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
    search, and modification utilities. To navigate the parse tree, use
    abstractions such as ``children`` and ``descendant``. To access content in
    the parse tree, use abstractions such as ``contents``, ``text``, ``string``
    , and ``args``.

    Note that the LaTeX parse tree is largely shallow: only environments such as
    ``itemize`` or ``enumerate`` have children and thus descendants. Typical LaTeX
    expressions such as ``\section`` have *arguments* but not children.
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
        r"""Arguments for this Tex expression

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''\newcommand{reverseconcat}[3]{#3#2#1}''')
        >>> soup.newcommand.args
        [RArg('reverseconcat'), OArg('3'), RArg('#3#2#1')]
        >>> soup.newcommand.args = soup.newcommand.args[:2]
        >>> soup.newcommand
        \newcommand{reverseconcat}[3]
        """
        return self.expr.args

    @args.setter
    def args(self, args):
        assert isinstance(args, TexArgs), "Must be proper TexArgs object"
        self.expr.args = args

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
        r"""Extra string not a part of the expression name.

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
            return self.expr.args[0].value

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
        ... \begin{itemize}
        ...     \item Hello
        ... \end{itemize}
        ... \section{Hey}
        ... \textit{Willy}''')
        >>> soup.section
        \section{Hey}
        >>> soup.section.add_children(soup.textit)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        TypeError: ...
        >>> soup.section
        \section{Hey}
        >>> soup.itemize.add_children('    ', soup.item)
        >>> soup.itemize
        \begin{itemize}
            \item Hello
            \item Hello
        \end{itemize}
        """
        self.expr.add_contents(*nodes)

    def add_children_at(self, i, *nodes):
        r"""Add node(s) to this node's list of children, inserted at position i.

        :param int i: Position to add nodes to
        :param TexNode nodes: List of nodes to add

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     \item Hello
        ...     \item Bye
        ... \end{itemize}''')
        >>> item = soup.item
        >>> soup.item.delete()
        >>> soup.itemize.add_children_at(1, item)
        >>> soup.itemize
        \begin{itemize}
            \item Hello
            \item Bye
        \end{itemize}
        """
        assert isinstance(i, int), (
                'Provided index "{}" is not an integer! Did you switch your '
                'arguments? The first argument to `add_children_at` is the '
                'index.'.format(i))
        self.expr.add_contents_at(i, *nodes)

    def char_pos_to_line(self, char_pos):
        r"""Map position in the original string to parsed LaTeX position.

        :param int char_pos: Character position in the original string
        :return: (line number, index of character in line)
        :rtype: Tuple[int, int]

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \section{Hey}
        ... \textbf{Silly}
        ... \textit{Willy}''')
        >>> soup.char_pos_to_line(10)
        (1, 9)
        >>> soup.char_pos_to_line(20)
        (2, 5)
        """
        assert self.char_to_line is not None, (
            'CharToLineOffset is not initialized. Pass src to TexNode '
            'constructor')
        return self.char_to_line(char_pos)

    def count(self, name=None, **attrs):
        r"""Number of descendants matching criteria.

        :param Union[None,str] name: name of LaTeX expression
        :param attrs: LaTeX expression attributes, such as item text.
        :return: number of matching expressions
        :rtype: int

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \section{Hey}
        ... \textit{Silly}
        ... \textit{Willy}''')
        >>> soup.count('section')
        1
        >>> soup.count('textit')
        2
        """
        return len(list(self.find_all(name, **attrs)))

    def delete(self):
        r"""Delete this node from the parse tree.

        Where applicable, this will remove all descendants of this node from
        the parse tree.

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''\textit{\color{blue}{Silly}}\textit{keep me!}''')
        >>> soup.textit.delete()
        >>> soup
        \textit{keep me!}
        """
        self.parent.remove_child(self)

    def find(self, name=None, **attrs):
        r"""First descendant node matching criteria.

        Returns None if no descendant node found.

        :return: descendant node matching criteria
        :rtype: Union[None,TexExpr]

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \section{Ooo}
        ... \textit{eee}
        ... \textit{ooo}''')
        >>> soup.find('textit')
        \textit{eee}
        >>> soup.find('textbf')
        """
        try:
            return next(self.find_all(name, **attrs))
        except StopIteration:
            return None

    def find_all(self, name=None, **attrs):
        r"""Return all descendant nodes matching criteria.

        :param Union[None,str] name: name of LaTeX expression
        :param attrs: LaTeX expression attributes, such as item text.
        :return: All descendant nodes matching criteria
        :rtype: generator

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \section{Ooo}
        ... \textit{eee}
        ... \textit{ooo}''')
        >>> gen = soup.find_all('textit')
        >>> next(gen)
        \textit{eee}
        >>> next(gen)
        \textit{ooo}
        >>> next(soup.find_all('textbf'))
        Traceback (most recent call last):
        ...
        StopIteration
        """
        for descendant in self.__descendants():
            if hasattr(descendant, '__match__') and \
                    descendant.__match__(name, attrs):
                yield descendant

    def remove_child(self, node):
        r"""Remove a node from this node's list of contents.

        :param TexExpr node: Node to remove

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     \item Hello
        ...     \item Bye
        ... \end{itemize}''')
        >>> soup.itemize.remove_child(soup.item)
        >>> soup.itemize
        \begin{itemize}
            \item Bye
        \end{itemize}
        """
        self.expr.remove_content(node.expr)

    def replace(self, *nodes):
        r"""Replace this node in the parse tree with the provided node(s).

        :param TexNode nodes: List of nodes to subtitute in

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     \item Hello
        ...     \item Bye
        ... \end{itemize}''')
        >>> items = list(soup.find_all('item'))
        >>> bye = items[1]
        >>> soup.item.replace(bye)
        >>> soup.itemize
        \begin{itemize}
            \item Bye
        \item Bye
        \end{itemize}
        """
        self.parent.replace_child(self, *nodes)

    def replace_child(self, child, *nodes):
        r"""Replace provided node with node(s).

        :param TexNode child: Child node to replace
        :param TexNode nodes: List of nodes to subtitute in

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     \item Hello
        ...     \item Bye
        ... \end{itemize}''')
        >>> items = list(soup.find_all('item'))
        >>> bye = items[1]
        >>> soup.itemize.replace_child(soup.item, bye)
        >>> soup.itemize
        \begin{itemize}
            \item Bye
        \item Bye
        \end{itemize}
        """
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
        self.args = TexArgs(args)
        self.stuff = stuff
        self.parent = self.parent if hasattr(self, 'parent') else None
        self._contents = contents or []

        for content in contents:
            if isinstance(content, (TexEnv, TexCmd)):
                content.parent = self

    ##############
    # PROPERTIES #
    ##############

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

    ##################
    # PUBLIC METHODS #
    ##################

    def add_contents(self, *contents):
        self._assert_supports_contents()
        self._contents.extend(contents)

    def add_contents_at(self, i, *contents):
        self._assert_supports_contents()
        for j, content in enumerate(contents):
            self._contents.insert(i + j, content)

    def remove_content(self, expr):
        """Remove a provided expression from its list of contents.

        :return: index of the expression removed
        """
        self._assert_supports_contents()
        index = self._contents.index(expr)
        self._contents.remove(expr)
        return index

    def _assert_supports_contents(self):
        raise NotImplementedError()


class TexEnv(TexExpr):
    r"""Abstraction for a LaTeX command, denoted by \begin{env} and \end{env}.
    Contains three attributes:

    1. the environment name itself,
    2. the environment arguments, whether optional or required, and
    3. the environment's contents.

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

    #################
    # MAGIC METHODS #
    #################

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

    ##############
    # PROPERTIES #
    ##############

    @property
    def contents(self):
        for content in self._contents:
            if not isinstance(content, TokenWithPosition) or bool(content.strip()) or self.preserve_whitespace:
                yield content

    @property
    def everything(self):
        for content in self._contents:
            yield content

    def _assert_supports_contents(self):
        pass


class TexCmd(TexExpr):
    r"""Abstraction for a LaTeX command. Contains two attributes:

    1. the command name itself and
    2. the command arguments, whether optional or required.

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

    def __str__(self):
        if self.extra:
            return '\\%s%s %s' % (self.name, self.args, ''.join(
                [str(e) for e in self.extra]))
        return '\\%s%s' % (self.name, self.args)

    def __repr__(self):
        if not self.args:
            return "TexCmd('%s')" % self.name
        return "TexCmd('%s', %s)" % (self.name, repr(self.args))

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
        r"""Amend extra where appropriate.

        If \item, amend extra. If otherwise, throw error, since commands don't
        have children.
        """
        self._assert_supports_contents()
        self.extra.extend(contents)

    def _assert_supports_contents(self):
        if self.name != 'item':
            raise TypeError(
                'Command "{}" has no children. `add_contents` is only valid for'
                ': 1. environments like `itemize` and 2. `\\item`. Alternatively'
                ', you can add, edit, or delete arguments by modifying `.args`'
                ', which behaves like a list.'.format(self.name))


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

    >>> arguments = TexArgs([RArg('arg0'), '[arg1]', '{arg2}'])
    >>> arguments
    [RArg('arg0'), OArg('arg1'), RArg('arg2')]
    >>> arguments[2]
    RArg('arg2')
    >>> arguments[2].type
    'required'
    >>> str(arguments[2])
    '{arg2}'
    >>> arguments.append('[arg3]')
    >>> arguments[3]
    OArg('arg3')
    >>> len(arguments)
    4
    >>> arguments[:2]
    [RArg('arg0'), OArg('arg1')]
    >>> isinstance(arguments[:2], TexArgs)
    True
    """

    def __init__(self, args):
        super().__init__()
        self.extend(args)

    def append(self, arg):
        """Append a value to the list"""
        if isinstance(arg, str):
            arg = Arg.parse(arg)
        list.append(self, arg)

    def extend(self, args):
        for arg in args:
            self.append(arg)

    def tovalues(self):
        return [arg.value for arg in self]

    def __getitem__(self, key):
        value = super().__getitem__(key)
        if isinstance(value, list):
            return TexArgs(value)
        return value

    def __contains__(self, item):
        if isinstance(item, str):
            return item in self.tovalues()
        return super().__contains__(item)

    def __str__(self):
        """Stringifies a list of arguments.

        >>> str(TexArgs(['{a}', '[b]', '{c}']))
        '{a}[b]{c}'
        """
        return ''.join(map(str, self))

    def __repr__(self):
        """Makes list of arguments command-line friendly.

        >>> TexArgs(['{a}', '[b]', '{c}'])
        [RArg('a'), OArg('b'), RArg('c')]
        """
        return '[%s]' % ', '.join(map(repr, self))


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
