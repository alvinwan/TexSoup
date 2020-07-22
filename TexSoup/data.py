"""TexSoup transforms a LaTeX document into a complex tree of various Python
objects, but all objects fall into one of the following three categories:

``TexNode``, ``TexExpr`` (environments and commands), and ``TexGroup`` s.
"""

import itertools
import re
from TexSoup.utils import CharToLineOffset, Token, TC, to_list

__all__ = ['TexNode', 'TexCmd', 'TexEnv', 'TexGroup', 'BracketGroup',
           'BraceGroup', 'TexArgs', 'TexText', 'TexMathEnv',
           'TexDisplayMathEnv', 'TexNamedEnv', 'TexMathModeEnv',
           'TexDisplayMathModeEnv']


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

    Note that the LaTeX parse tree is largely shallow: only environments such
    as ``itemize`` or ``enumerate`` have children and thus descendants. Typical
    LaTeX expressions such as ``\section`` have *arguments* but not children.
    """

    def __init__(self, expr, src=None):
        """Creates TexNode object.

        :param TexExpr expr: a LaTeX expression, either a singleton
            command or an environment containing other commands
        :param str src: LaTeX source string
        """
        assert isinstance(expr, TexExpr), \
            'Expression given to node must be a valid TexExpr'
        super().__init__()
        self.expr = expr
        self.parent = None
        if src is not None:
            self.char_to_line = CharToLineOffset(src)
        else:
            self.char_to_line = None

    #################
    # MAGIC METHODS #
    #################

    def __contains__(self, other):
        """Use custom containment checker where applicable (TexText, for ex)"""
        if hasattr(self.expr, '__contains__'):
            return other in self.expr
        return other in iter(self)

    def __getattr__(self, attr, default=None):
        """Convert all invalid attributes into basic find operation."""
        return self.find(attr) or default

    def __getitem__(self, item):
        return list(self.contents)[item]

    def __iter__(self):
        """
        >>> node = TexNode(TexNamedEnv('lstlisting', ('hai', 'there')))
        >>> list(node)
        ['hai', 'there']
        """
        return iter(self.contents)

    def __match__(self, name=None, attrs=()):
        r"""Check if given attributes match current object

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'\ref{hello}\ref{hello}\ref{hello}\ref{nono}')
        >>> soup.count(r'\ref{hello}')
        3
        """
        return self.expr.__match__(name, attrs)

    def __repr__(self):
        """Interpreter representation."""
        return str(self)

    def __str__(self):
        """Stringified command."""
        return str(self.expr)

    ##############
    # PROPERTIES #
    ##############

    @property
    @to_list
    def all(self):
        r"""Returns all content in this node, regardless of whitespace or
        not. This includes all LaTeX needed to reconstruct the original source.

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \newcommand{reverseconcat}[3]{#3#2#1}
        ... ''')
        >>> alls = soup.all
        >>> alls[0]
        <BLANKLINE>
        <BLANKLINE>
        >>> alls[1]
        \newcommand{reverseconcat}[3]{#3#2#1}
        """
        for child in self.expr.all:
            assert isinstance(child, TexExpr)
            node = TexNode(child)
            node.parent = self
            yield node

    @property
    def args(self):
        r"""Arguments for this node. Note that this argument is settable.

        :rtype: TexArgs

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''\newcommand{reverseconcat}[3]{#3#2#1}''')
        >>> soup.newcommand.args
        [BraceGroup('reverseconcat'), BracketGroup('3'), BraceGroup('#3#2#1')]
        >>> soup.newcommand.args = soup.newcommand.args[:2]
        >>> soup.newcommand
        \newcommand{reverseconcat}[3]
        """
        return self.expr.args

    @args.setter
    def args(self, args):
        assert isinstance(args, TexArgs), "`args` must be of type `TexArgs`"
        self.expr.args = args

    @property
    @to_list
    def children(self):
        r"""Immediate children of this TeX element that are valid TeX objects.

        This is equivalent to contents, excluding text elements and keeping
        only Tex expressions.

        :return: generator of all children
        :rtype: Iterator[TexExpr]

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     Random text!
        ...     \item Hello
        ... \end{itemize}''')
        >>> soup.itemize.children[0]
        \item Hello
        <BLANKLINE>
        """
        for child in self.expr.children:
            node = TexNode(child)
            node.parent = self
            yield node

    @property
    @to_list
    def contents(self):
        r"""Any non-whitespace contents inside of this TeX element.

        :return: generator of all nodes, tokens, and strings
        :rtype: Iterator[Union[TexNode,str]]

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     Random text!
        ...     \item Hello
        ... \end{itemize}''')
        >>> contents = soup.itemize.contents
        >>> contents[0]
        '\n    Random text!\n    '
        >>> contents[1]
        \item Hello
        <BLANKLINE>
        """
        for child in self.expr.contents:
            if isinstance(child, TexExpr):
                node = TexNode(child)
                node.parent = self
                yield node
            else:
                yield child

    @contents.setter
    def contents(self, contents):
        self.expr.contents = contents

    @property
    def descendants(self):
        r"""Returns all descendants for this TeX element.

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     \begin{itemize}
        ...         \item Nested
        ...     \end{itemize}
        ... \end{itemize}''')
        >>> descendants = list(soup.itemize.descendants)
        >>> descendants[1]
        \item Nested
        <BLANKLINE>
        """
        return self.__descendants()

    @property
    def name(self):
        r"""Name of the expression. Used for search functions.

        :rtype: str

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''\textbf{Hello}''')
        >>> soup.textbf.name
        'textbf'
        >>> soup.textbf.name = 'textit'
        >>> soup.textit
        \textit{Hello}
        """
        return self.expr.name

    @name.setter
    def name(self, name):
        self.expr.name = name

    @property
    def string(self):
        r"""This is valid if and only if

        1. the expression is a :class:`.TexCmd` AND has only one argument OR
        2. the expression is a :class:`.TexEnv` AND has only one TexText child

        :rtype: Union[None,str]

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''\textbf{Hello}''')
        >>> soup.textbf.string
        'Hello'
        >>> soup.textbf.string = 'Hello World'
        >>> soup.textbf.string
        'Hello World'
        >>> soup.textbf
        \textbf{Hello World}
        >>> soup = TexSoup(r'''\begin{equation}1+1\end{equation}''')
        >>> soup.equation.string
        '1+1'
        >>> soup.equation.string = '2+2'
        >>> soup.equation.string
        '2+2'
        """
        if isinstance(self.expr, TexCmd):
            assert len(self.expr.args) == 1, \
                '.string is only valid for commands with one argument'
            return self.expr.args[0].string

        contents = list(self.contents)
        if isinstance(self.expr, TexEnv):
            assert len(contents) == 1 and \
                isinstance(contents[0], (TexText, str)), \
                '.string is only valid for environments with only text content'
            return contents[0]

    @string.setter
    def string(self, string):
        if isinstance(self.expr, TexCmd):
            assert len(self.expr.args) == 1, \
                '.string is only valid for commands with one argument'
            self.expr.args[0].string = string

        contents = list(self.contents)
        if isinstance(self.expr, TexEnv):
            assert len(contents) == 1 and \
                isinstance(contents[0], (TexText, str)), \
                '.string is only valid for environments with only text content'
            self.contents = [string]

    @property
    def position(self):
        r"""Position of first character in expression, in original source.

        Note this position is NOT updated as the parsed tree is modified.
        """
        return self.expr.position

    @property
    @to_list
    def text(self):
        r"""All text in descendant nodes.

        This is equivalent to contents, keeping text elements and excluding
        Tex expressions.

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     \begin{itemize}
        ...         \item Nested
        ...     \end{itemize}
        ... \end{itemize}''')
        >>> soup.text[0]
        ' Nested\n    '
        """
        for descendant in self.contents:
            if isinstance(descendant, (TexText, Token)):
                yield descendant
            elif hasattr(descendant, 'text'):
                yield from descendant.text

    ##################
    # PUBLIC METHODS #
    ##################

    def append(self, *nodes):
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
        >>> soup.section.append(soup.textit)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        TypeError: ...
        >>> soup.section
        \section{Hey}
        >>> soup.itemize.append('    ', soup.item)
        >>> soup.itemize
        \begin{itemize}
            \item Hello
            \item Hello
        \end{itemize}
        """
        self.expr.append(*nodes)

    def insert(self, i, *nodes):
        r"""Add node(s) to this node's list of children, at position i.

        :param int i: Position to add nodes to
        :param TexNode nodes: List of nodes to add

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     \item Hello
        ...     \item Bye
        ... \end{itemize}''')
        >>> item = soup.item.copy()
        >>> soup.item.delete()
        >>> soup.itemize.insert(1, item)
        >>> soup.itemize
        \begin{itemize}
            \item Hello
            \item Bye
        \end{itemize}
        >>> item.parent.name == soup.itemize.name
        True
        """
        assert isinstance(i, int), (
            'Provided index "{}" is not an integer! Did you switch your '
            'arguments? The first argument to `insert` is the '
            'index.'.format(i))
        for node in nodes:
            if not isinstance(node, TexNode):
                continue
            assert not node.parent, (
                'Inserted node should not already have parent. Call `.copy()` '
                'on node to fix.'
            )
            node.parent = self

        self.expr.insert(i, *nodes)

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

    def copy(self):
        r"""Create another copy of the current node.

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \section{Hey}
        ... \textit{Silly}
        ... \textit{Willy}''')
        >>> s = soup.section.copy()
        >>> s.parent is None
        True
        """
        return TexNode(self.expr)

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
        >>> soup = TexSoup(r'''
        ... \textit{\color{blue}{Silly}}\textit{keep me!}''')
        >>> soup.textit.color.delete()
        >>> soup
        <BLANKLINE>
        \textit{}\textit{keep me!}
        >>> soup.textit.delete()
        >>> soup
        <BLANKLINE>
        \textit{keep me!}
        """

        # TODO: needs better abstraction for supports contents
        parent = self.parent
        if parent.expr._supports_contents():
            parent.remove(self)
            return

        # TODO: needs abstraction for removing from arg
        for arg in parent.args:
            if self.expr in arg.contents:
                arg._contents.remove(self.expr)

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
            return self.find_all(name, **attrs)[0]
        except IndexError:
            return None

    @to_list
    def find_all(self, name=None, **attrs):
        r"""Return all descendant nodes matching criteria.

        :param Union[None,str,list] name: name of LaTeX expression
        :param attrs: LaTeX expression attributes, such as item text.
        :return: All descendant nodes matching criteria
        :rtype: Iterator[TexNode]

        If `name` is a list of `str`'s, any matching section will be matched.

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \section{Ooo}
        ... \textit{eee}
        ... \textit{ooo}''')
        >>> gen = soup.find_all('textit')
        >>> gen[0]
        \textit{eee}
        >>> gen[1]
        \textit{ooo}
        >>> soup.find_all('textbf')[0]
        Traceback (most recent call last):
        ...
        IndexError: list index out of range
        """
        for descendant in self.__descendants():
            if hasattr(descendant, '__match__') and \
                    descendant.__match__(name, attrs):
                yield descendant

    def remove(self, node):
        r"""Remove a node from this node's list of contents.

        :param TexExpr node: Node to remove

        >>> from TexSoup import TexSoup
        >>> soup = TexSoup(r'''
        ... \begin{itemize}
        ...     \item Hello
        ...     \item Bye
        ... \end{itemize}''')
        >>> soup.itemize.remove(soup.item)
        >>> soup.itemize
        \begin{itemize}
            \item Bye
        \end{itemize}
        """
        self.expr.remove(node.expr)

    def replace_with(self, *nodes):
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
        >>> soup.item.replace_with(bye)
        >>> soup.itemize
        \begin{itemize}
            \item Bye
        \item Bye
        \end{itemize}
        """
        self.parent.replace(self, *nodes)

    def replace(self, child, *nodes):
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
        >>> soup.itemize.replace(soup.item, bye)
        >>> soup.itemize
        \begin{itemize}
            \item Bye
        \item Bye
        \end{itemize}
        """
        self.expr.insert(
            self.expr.remove(child.expr),
            *nodes)

    def search_regex(self, pattern):
        for node in self.text:
            for match in re.finditer(pattern, node):
                body = match.group()  # group() returns the full match
                start = match.start()
                yield Token(body, node.position + start)

    def __descendants(self):
        """Implementation for descendants, hacky workaround for __getattr__
        issues."""
        return itertools.chain(self.contents,
                               *[c.descendants for c in self.children])


###############
# Expressions #
###############


class TexExpr(object):
    """General abstraction for a TeX expression.

    An expression may be a command or an environment and is identified
    by a name, arguments, and place in the parse tree. This is an
    abstract and is not directly instantiated.
    """

    def __init__(self, name, contents=(), args=(), preserve_whitespace=False,
                 position=-1):
        """Initialize a tex expression.

        :param str name: name of environment
        :param iterable contents: list of contents
        :param iterable args: list of Tex Arguments
        :param bool preserve_whitespace: If false, elements containing only
            whitespace will be removed from contents.
        :param int position: position of first character in original source
        """
        self.name = name.strip()  # TODO: should not ever have space
        self.args = TexArgs(args)
        self.parent = None
        self._contents = list(contents) or []
        self.preserve_whitespace = preserve_whitespace
        self.position = position

        for content in contents:
            if isinstance(content, (TexEnv, TexCmd)):
                content.parent = self

    #################
    # MAGIC METHODS #
    #################

    def __eq__(self, other):
        """Check if two expressions are equal. This is useful when defining
        data structures over TexExprs.

        >>> exprs = [
        ...     TexExpr('cake', ['flour', 'taro']),
        ...     TexExpr('corgi', ['derp', 'collar', 'drool', 'sass'])
        ... ]
        >>> exprs[0] in exprs
        True
        >>> TexExpr('cake', ['flour', 'taro']) in exprs
        True
        """
        return str(other) == str(self)

    def __match__(self, name=None, attrs=()):
        """Check if given attributes match current object."""
        # TODO: this should re-parse the name, instead of hardcoding here
        if '{' in name or '[' in name:
            return str(self) == name
        if isinstance(name, list):
            node_name = getattr(self, 'name')
            if node_name not in name:
                return False
        else:
            attrs['name'] = name
        for k, v in attrs.items():
            if getattr(self, k) != v:
                return False
        return True

    def __repr__(self):
        if not self.args:
            return "TexExpr('%s', %s)" % (self.name, repr(self._contents))
        return "TexExpr('%s', %s, %s)" % (
            self.name, repr(self._contents), repr(self.args))

    ##############
    # PROPERTIES #
    ##############

    @property
    @to_list
    def all(self):
        r"""Returns all content in this expression, regardless of whitespace or
        not. This includes all LaTeX needed to reconstruct the original source.

        >>> expr1 = TexExpr('textbf', ('\n', 'hi'))
        >>> expr2 = TexExpr('textbf', ('\n', 'hi'), preserve_whitespace=True)
        >>> list(expr1.all) == list(expr2.all)
        True
        """
        for arg in self.args:
            for expr in arg.contents:
                yield expr
        for content in self._contents:
            yield content

    @property
    @to_list
    def children(self):
        return filter(lambda x: isinstance(x, (TexEnv, TexCmd)), self.contents)

    @property
    @to_list
    def contents(self):
        r"""Returns all contents in this expression.

        Optionally includes whitespace if set when node was created.

        >>> expr1 = TexExpr('textbf', ('\n', 'hi'))
        >>> list(expr1.contents)
        ['hi']
        >>> expr2 = TexExpr('textbf', ('\n', 'hi'), preserve_whitespace=True)
        >>> list(expr2.contents)
        ['\n', 'hi']
        >>> expr = TexExpr('textbf', ('\n', 'hi'))
        >>> expr.contents = ('hehe', '👻')
        >>> list(expr.contents)
        ['hehe', '👻']
        >>> expr.contents = 35  #doctest:+ELLIPSIS
        Traceback (most recent call last):
            ...
        TypeError: ...
        """
        for content in self.all:
            if isinstance(content, TexText):
                content = content._text
            is_whitespace = isinstance(content, str) and content.isspace()
            if not is_whitespace or self.preserve_whitespace:
                yield content

    @contents.setter
    def contents(self, contents):
        if not isinstance(contents, (list, tuple)) or not all(
                isinstance(content, (str, TexExpr)) for content in contents):
            raise TypeError(
                '.contents value "%s" must be a list or tuple of strings or '
                'TexExprs' % contents)
        _contents = [TexText(c) if isinstance(c, str) else c for c in contents]
        self._contents = _contents

    @property
    def string(self):
        """All contents stringified. A convenience property

        >>> expr = TexExpr('hello', ['naw'])
        >>> expr.string
        'naw'
        >>> expr.string = 'huehue'
        >>> expr.string
        'huehue'
        >>> type(expr.string)
        <class 'TexSoup.data.TexText'>
        >>> str(expr)
        "TexExpr('hello', ['huehue'])"
        >>> expr.string = 35  #doctest:+ELLIPSIS
        Traceback (most recent call last):
            ...
        TypeError: ...
        """
        return TexText(''.join(map(str, self._contents)))

    @string.setter
    def string(self, s):
        if not isinstance(s, str):
            raise TypeError(
                '.string value "%s" must be a string or TexText. To set '
                'non-string content, use .contents' % s)
        self.contents = [TexText(s)]

    ##################
    # PUBLIC METHODS #
    ##################

    def append(self, *exprs):
        """Add contents to the expression.

        :param Union[TexExpr,str] exprs: List of contents to add

        >>> expr = TexExpr('textbf', ('hello',))
        >>> expr
        TexExpr('textbf', ['hello'])
        >>> expr.append('world')
        >>> expr
        TexExpr('textbf', ['hello', 'world'])
        """
        self._assert_supports_contents()
        self._contents.extend(exprs)

    def insert(self, i, *exprs):
        """Insert content at specified position into expression.

        :param int i: Position to add content to
        :param Union[TexExpr,str] exprs: List of contents to add

        >>> expr = TexExpr('textbf', ('hello',))
        >>> expr
        TexExpr('textbf', ['hello'])
        >>> expr.insert(0, 'world')
        >>> expr
        TexExpr('textbf', ['world', 'hello'])
        >>> expr.insert(0, TexText('asdf'))
        >>> expr
        TexExpr('textbf', ['asdf', 'world', 'hello'])
        """
        self._assert_supports_contents()
        for j, expr in enumerate(exprs):
            if isinstance(expr, TexExpr):
                expr.parent = self
            self._contents.insert(i + j, expr)

    def remove(self, expr):
        """Remove a provided expression from its list of contents.

        :param Union[TexExpr,str] expr: Content to add
        :return: index of the expression removed
        :rtype: int

        >>> expr = TexExpr('textbf', ('hello',))
        >>> expr.remove('hello')
        0
        >>> expr
        TexExpr('textbf', [])
        """
        self._assert_supports_contents()
        index = self._contents.index(expr)
        self._contents.remove(expr)
        return index

    def _supports_contents(self):
        return True

    def _assert_supports_contents(self):
        pass


class TexEnv(TexExpr):
    r"""Abstraction for a LaTeX command, with starting and ending markers.
    Contains three attributes:

    1. a human-readable environment name,
    2. the environment delimiters
    3. the environment's contents.

    >>> t = TexEnv('displaymath', r'\[', r'\]',
    ...     ['\\mathcal{M} \\circ \\mathcal{A}'])
    >>> t
    TexEnv('displaymath', ['\\mathcal{M} \\circ \\mathcal{A}'], [])
    >>> print(t)
    \[\mathcal{M} \circ \mathcal{A}\]
    >>> len(list(t.children))
    0
    """

    _begin = None
    _end = None

    def __init__(self, name, begin, end, contents=(), args=(),
                 preserve_whitespace=False, position=-1):
        r"""Initialization for Tex environment.

        :param str name: name of environment
        :param str begin: string denoting start of environment
        :param str end: string denoting end of environment
        :param iterable contents: list of contents
        :param iterable args: list of Tex Arguments
        :param bool preserve_whitespace: If false, elements containing only
            whitespace will be removed from contents.
        :param int position: position of first character in original source

        >>> env = TexEnv('math', '$', '$', [r'\$'])
        >>> str(env)
        '$\\$$'
        >>> env.begin = '^^'
        >>> env.end = '**'
        >>> str(env)
        '^^\\$**'
        """
        super().__init__(name, contents, args, preserve_whitespace, position)
        self._begin = begin
        self._end = end

    @property
    def begin(self):
        return self._begin

    @begin.setter
    def begin(self, begin):
        self._begin = begin

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end):
        self._end = end

    def __match__(self, name=None, attrs=()):
        """Check if given attributes match environment."""
        if name in (self.name, self.begin +
                    str(self.args), self.begin, self.end):
            return True
        return super().__match__(name, attrs)

    def __str__(self):
        contents = ''.join(map(str, self._contents))
        if self.name == '[tex]':
            return contents
        else:
            return '%s%s%s' % (
                self.begin + str(self.args), contents, self.end)

    def __repr__(self):
        if self.name == '[tex]':
            return str(self._contents)
        if not self.args and not self._contents:
            return "%s('%s')" % (self.__class__.__name__, self.name)
        return "%s('%s', %s, %s)" % (
            self.__class__.__name__, self.name, repr(self._contents),
            repr(self.args))


class TexNamedEnv(TexEnv):
    r"""Abstraction for a LaTeX command, denoted by ``\begin{env}`` and
    ``\end{env}``. Contains three attributes:

    1. the environment name itself,
    2. the environment arguments, whether optional or required, and
    3. the environment's contents.

    **Warning**: Note that *setting* TexNamedEnv.begin or TexNamedEnv.end
    has no effect. The begin and end tokens are always constructed from
    TexNamedEnv.name.

    >>> t = TexNamedEnv('tabular', ['\n0 & 0 & * \\\\\n1 & 1 & * \\\\\n'],
    ...     [BraceGroup('c | c c')])
    >>> t
    TexNamedEnv('tabular', ['\n0 & 0 & * \\\\\n1 & 1 & * \\\\\n'], [BraceGroup('c | c c')])
    >>> print(t)
    \begin{tabular}{c | c c}
    0 & 0 & * \\
    1 & 1 & * \\
    \end{tabular}
    >>> len(list(t.children))
    0
    >>> t = TexNamedEnv('equation', [r'5\sum_{i=0}^n i^2'])
    >>> str(t)
    '\\begin{equation}5\\sum_{i=0}^n i^2\\end{equation}'
    >>> t.name = 'eqn'
    >>> str(t)
    '\\begin{eqn}5\\sum_{i=0}^n i^2\\end{eqn}'
    """

    def __init__(self, name, contents=(), args=(), preserve_whitespace=False,
                 position=-1):
        """Initialization for Tex environment.

        :param str name: name of environment
        :param iterable contents: list of contents
        :param iterable args: list of Tex Arguments
        :param bool preserve_whitespace: If false, elements containing only
            whitespace will be removed from contents.
        :param int position: position of first character in original source
        """
        super().__init__(name, r"\begin{%s}" % name, r"\end{%s}" % name,
                         contents, args, preserve_whitespace, position=position)

    @property
    def begin(self):
        return r"\begin{%s}" % self.name

    @property
    def end(self):
        return r"\end{%s}" % self.name


class TexUnNamedEnv(TexEnv):

    name = None
    begin = None
    end = None

    def __init__(self, contents=(), args=(), preserve_whitespace=False,
                 position=-1):
        """Initialization for Tex environment.

        :param iterable contents: list of contents
        :param iterable args: list of Tex Arguments
        :param bool preserve_whitespace: If false, elements containing only
            whitespace will be removed from contents.
        :param int position: position of first character in original source
        """
        assert self.name, 'Name must be non-falsey'
        assert self.begin and self.end, 'Delimiters must be non-falsey'
        super().__init__(self.name, self.begin, self.end,
                         contents, args, preserve_whitespace, position=position)


class TexDisplayMathModeEnv(TexUnNamedEnv):

    name = '$$'
    begin = '$$'
    end = '$$'
    token_begin = TC.DisplayMathSwitch
    token_end = TC.DisplayMathSwitch


class TexMathModeEnv(TexUnNamedEnv):

    name = '$'
    begin = '$'
    end = '$'
    token_begin = TC.MathSwitch
    token_end = TC.MathSwitch


class TexDisplayMathEnv(TexUnNamedEnv):

    name = 'displaymath'
    begin = r'\['
    end = r'\]'
    token_begin = TC.DisplayMathGroupBegin
    token_end = TC.DisplayMathGroupEnd


class TexMathEnv(TexUnNamedEnv):

    name = 'math'
    begin = r'\('
    end = r'\)'
    token_begin = TC.MathGroupBegin
    token_end = TC.MathGroupEnd


class TexCmd(TexExpr):
    r"""Abstraction for a LaTeX command. Contains two attributes:

    1. the command name itself and
    2. the command arguments, whether optional or required.

    >>> textit = TexCmd('textit', args=[BraceGroup('slant')])
    >>> t = TexCmd('textbf', args=[BraceGroup('big ', textit, '.')])
    >>> t
    TexCmd('textbf', [BraceGroup('big ', TexCmd('textit', [BraceGroup('slant')]), '.')])
    >>> print(t)
    \textbf{big \textit{slant}.}
    >>> children = list(map(str, t.children))
    >>> len(children)
    1
    >>> print(children[0])
    \textit{slant}
    """

    def __str__(self):
        if self._contents:
            return '\\%s%s%s' % (self.name, self.args, ''.join(
                [str(e) for e in self._contents]))
        return '\\%s%s' % (self.name, self.args)

    def __repr__(self):
        if not self.args:
            return "TexCmd('%s')" % self.name
        return "TexCmd('%s', %s)" % (self.name, repr(self.args))

    def _supports_contents(self):
        return self.name == 'item'

    def _assert_supports_contents(self):
        if not self._supports_contents():
            raise TypeError(
                'Command "{}" has no children. `add_contents` is only valid'
                'for: 1. environments like `itemize` and 2. `\\item`. '
                'Alternatively, you can add, edit, or delete arguments by '
                'modifying `.args`, which behaves like a list.'
                .format(self.name))


class TexText(TexExpr, str):
    r"""Abstraction for LaTeX text.

    Representing regular text objects in the parsed tree allows users to
    search and modify text objects as any other expression allows.

    >>> obj = TexNode(TexText('asdf gg'))
    >>> 'asdf' in obj
    True
    >>> 'err' in obj
    False
    >>> TexText('df ').strip()
    'df'
    """

    _has_custom_contain = True

    def __init__(self, text, position=-1):
        """Initialize text as tex expresssion.

        :param str text: Text content
        :param int position: position of first character in original source
        """
        super().__init__('text', [text], position=position)
        self._text = text

    def __contains__(self, other):
        """
        >>> obj = TexText(Token('asdf'))
        >>> 'a' in obj
        True
        >>> 'b' in obj
        False
        """
        return other in self._text

    def __eq__(self, other):
        """
        >>> TexText('asdf') == 'asdf'
        True
        >>> TexText('asdf') == TexText('asdf')
        True
        >>> TexText('asfd') == 'sdddsss'
        False
        """
        if isinstance(other, TexText):
            return self._text == other._text
        if isinstance(other, str):
            return self._text == other
        return False

    def __str__(self):
        """
        >>> TexText('asdf')
        'asdf'
        """
        return str(self._text)

    def __repr__(self):
        """
        >>> TexText('asdf')
        'asdf'
        """
        return repr(self._text)


#############
# Arguments #
#############


class TexGroup(TexUnNamedEnv):
    """Abstraction for a LaTeX environment with single-character delimiters.

    Used primarily to identify and associate arguments with commands.
    """

    def __init__(self, *contents, preserve_whitespace=False, position=-1):
        """Initialize argument using list of expressions.

        :param Union[str,TexCmd,TexEnv] exprs: Tex expressions contained in the
            argument. Can be other commands or environments, or even strings.
        :param int position: position of first character in original source
        """
        super().__init__(contents, preserve_whitespace=preserve_whitespace,
                         position=position)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(map(repr, self._contents)))

    @classmethod
    def parse(cls, s):
        """Parse a string or list and return an Argument object.

        Naive implementation, does not parse expressions in provided string.

        :param Union[str,iterable] s: Either a string or a list, where the
            first and last elements are valid argument delimiters.

        >>> TexGroup.parse('[arg0]')
        BracketGroup('arg0')
        """
        assert isinstance(s, str)
        for arg in arg_type:
            if s.startswith(arg.begin) and s.endswith(arg.end):
                return arg(s[len(arg.begin):-len(arg.end)])
        raise TypeError('Malformed argument: %s. Must be an TexGroup or a string in'
                        ' either brackets or curly braces.' % s)


class BracketGroup(TexGroup):
    """Optional argument, denoted as ``[arg]``"""

    begin = '['
    end = ']'
    name = 'BracketGroup'
    token_begin = TC.BracketBegin
    token_end = TC.BracketEnd


class BraceGroup(TexGroup):
    """Required argument, denoted as ``{arg}``."""

    begin = '{'
    end = '}'
    name = 'BraceGroup'
    token_begin = TC.GroupBegin
    token_end = TC.GroupEnd


arg_type = (BracketGroup, BraceGroup)


class TexArgs(list):
    r"""List of arguments for a TeX expression. Supports all standard list ops.

    Additional support for conversion from and to unparsed argument strings.

    >>> arguments = TexArgs(['\n', BraceGroup('arg0'), '[arg1]', '{arg2}'])
    >>> arguments
    [BraceGroup('arg0'), BracketGroup('arg1'), BraceGroup('arg2')]
    >>> arguments.all
    ['\n', BraceGroup('arg0'), BracketGroup('arg1'), BraceGroup('arg2')]
    >>> arguments[2]
    BraceGroup('arg2')
    >>> len(arguments)
    3
    >>> arguments[:2]
    [BraceGroup('arg0'), BracketGroup('arg1')]
    >>> isinstance(arguments[:2], TexArgs)
    True
    """

    def __init__(self, args=[]):
        """List of arguments for a command.

        :param list args: List of parsed or unparsed arguments
        """
        super().__init__()
        self.all = []
        self.extend(args)

    def __coerce(self, arg):
        if isinstance(arg, str) and not arg.isspace():
            arg = TexGroup.parse(arg)
        return arg

    def append(self, arg):
        """Append whitespace, an unparsed argument string, or an argument
        object.

        :param TexGroup arg: argument to add to the end of the list

        >>> arguments = TexArgs([BraceGroup('arg0'), '[arg1]', '{arg2}'])
        >>> arguments.append('[arg3]')
        >>> arguments[3]
        BracketGroup('arg3')
        >>> arguments.append(BraceGroup('arg4'))
        >>> arguments[4]
        BraceGroup('arg4')
        >>> len(arguments)
        5
        >>> arguments.append('\\n')
        >>> len(arguments)
        5
        >>> len(arguments.all)
        6
        """
        self.insert(len(self), arg)

    def extend(self, args):
        """Extend mixture of unparsed argument strings, arguments objects, and
        whitespace.

        :param List[TexGroup] args: Arguments to add to end of the list

        >>> arguments = TexArgs([BraceGroup('arg0'), '[arg1]', '{arg2}'])
        >>> arguments.extend(['[arg3]', BraceGroup('arg4'), '\\t'])
        >>> len(arguments)
        5
        >>> arguments[4]
        BraceGroup('arg4')
        """
        for arg in args:
            self.append(arg)

    def insert(self, i, arg):
        r"""Insert whitespace, an unparsed argument string, or an argument
        object.

        :param int i: Index to insert argument into
        :param TexGroup arg: Argument to insert

        >>> arguments = TexArgs(['\n', BraceGroup('arg0'), '[arg2]'])
        >>> arguments.insert(1, '[arg1]')
        >>> len(arguments)
        3
        >>> arguments
        [BraceGroup('arg0'), BracketGroup('arg1'), BracketGroup('arg2')]
        >>> arguments.all
        ['\n', BraceGroup('arg0'), BracketGroup('arg1'), BracketGroup('arg2')]
        >>> arguments.insert(10, '[arg3]')
        >>> arguments[3]
        BracketGroup('arg3')
        """
        arg = self.__coerce(arg)

        if isinstance(arg, TexGroup):
            super().insert(i, arg)

        if len(self) <= 1:
            self.all.append(arg)
        else:
            if i > len(self):
                i = len(self) - 1

            before = self[i - 1]
            index_before = self.all.index(before)
            self.all.insert(index_before + 1, arg)

    def remove(self, item):
        """Remove either an unparsed argument string or an argument object.

        :param Union[str,TexGroup] item: Item to remove

        >>> arguments = TexArgs([BraceGroup('arg0'), '[arg2]', '{arg3}'])
        >>> arguments.remove('{arg0}')
        >>> len(arguments)
        2
        >>> arguments[0]
        BracketGroup('arg2')
        >>> arguments.remove(arguments[0])
        >>> arguments[0]
        BraceGroup('arg3')
        >>> arguments.remove(BraceGroup('arg3'))
        >>> len(arguments)
        0
        >>> arguments = TexArgs([
        ...     BraceGroup(TexCmd('color')),
        ...     BraceGroup(TexCmd('color', [BraceGroup('blue')]))
        ... ])
        >>> arguments.remove(arguments[0])
        >>> len(arguments)
        1
        >>> arguments.remove(arguments[0])
        >>> len(arguments)
        0
        """
        item = self.__coerce(item)
        self.all.remove(item)
        super().remove(item)

    def pop(self, i):
        """Pop argument object at provided index.

        :param int i: Index to pop from the list

        >>> arguments = TexArgs([BraceGroup('arg0'), '[arg2]', '{arg3}'])
        >>> arguments.pop(1)
        BracketGroup('arg2')
        >>> len(arguments)
        2
        >>> arguments[0]
        BraceGroup('arg0')
        """
        item = super().pop(i)
        j = self.all.index(item)
        return self.all.pop(j)

    def reverse(self):
        r"""Reverse both the list and the proxy `.all`.

        >>> args = TexArgs(['\n', BraceGroup('arg1'), BracketGroup('arg2')])
        >>> args.reverse()
        >>> args.all
        [BracketGroup('arg2'), BraceGroup('arg1'), '\n']
        >>> args
        [BracketGroup('arg2'), BraceGroup('arg1')]
        """
        super().reverse()
        self.all.reverse()

    def clear(self):
        r"""Clear both the list and the proxy `.all`.

        >>> args = TexArgs(['\n', BraceGroup('arg1'), BracketGroup('arg2')])
        >>> args.clear()
        >>> len(args) == len(args.all) == 0
        True
        """
        super().clear()
        self.all.clear()

    def __getitem__(self, key):
        """Standard list slicing.

        Returns TexArgs object for subset of list and returns an TexGroup object
        for single items.

        >>> arguments = TexArgs([BraceGroup('arg0'), '[arg1]', '{arg2}'])
        >>> arguments[2]
        BraceGroup('arg2')
        >>> arguments[:2]
        [BraceGroup('arg0'), BracketGroup('arg1')]
        """
        value = super().__getitem__(key)
        if isinstance(value, list):
            return TexArgs(value)
        return value

    def __contains__(self, item):
        """Checks for membership. Allows string comparisons to args.

        >>> arguments = TexArgs(['{arg0}', '[arg1]'])
        >>> 'arg0' in arguments
        True
        >>> BracketGroup('arg0') in arguments
        False
        >>> BraceGroup('arg0') in arguments
        True
        >>> 'arg3' in arguments
        False
        """
        if isinstance(item, str):
            return any([item == arg.string for arg in self])
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
        [BraceGroup('a'), BracketGroup('b'), BraceGroup('c')]
        """
        return '[%s]' % ', '.join(map(repr, self))
