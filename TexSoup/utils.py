"""
Utils for TexSoup
---

This file consists of various utilities for TexSoup, split into 2 categories by
function:

1. Decorators
2. Generalized utilities
"""

import functools, bisect

##############
# Decorators #
##############


def to_buffer(f):
    """
    Decorator converting all strings and iterators/iterables into
    Buffers.

    >>> f = to_buffer(lambda x: x[:])
    >>> f('asdf')
    'asdf'
    >>> g = to_buffer(lambda x: x)
    >>> g('').hasNext()
    False
    >>> next(g('asdf'))
    'a'
    """
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        iterator = kwargs.get('iterator', args[0])
        if not isinstance(iterator, Buffer):
            iterator = Buffer(iterator)
        return f(iterator, *args[1:], **kwargs)
    return wrap

#########################
# Generalized Utilities #
#########################


class TokenWithPosition(str):
    """Enhanced string object with knowledge of global position."""

    def __new__(cls, text, position):
        """Initializer for pseudo-string object.

        :param text: The original string
        :param position: Position in the original buffer
        """
        self = str.__new__(cls, text)
        if isinstance(text, TokenWithPosition):
            self.text, self.position = text.text, text.position
        else:
            self.text = text
            self.position = position
        return self

    def __repr__(self):
        return repr(self.text)

    def __str__(self):
        return str(self.text)

    def __getattr__(self, name):
        return getattr(self.text, name)

    def __eq__(self, other):
        """
        >>> TokenWithPosition('asdf', 0) == TokenWithPosition('asdf', 2)
        True
        >>> TokenWithPosition('asdf', 0) == TokenWithPosition('asd', 0)
        False
        """
        if isinstance(other, TokenWithPosition):
            return self.text == other.text
        else:
            return self.text == other

    def __hash__(self):
        return hash(self.text)

    def __add__(self, other):
        """Implements addition in the form of TextWithPosition(...) + (obj).

        >>> t1 = TokenWithPosition('as', 0) + TokenWithPosition('df', 1)
        >>> str(t1)
        'asdf'
        >>> t1.position
        0
        >>> t2 = TokenWithPosition('as', 1) + 'df'
        >>> str(t2)
        'asdf'
        >>> t2.position
        1
        """
        if isinstance(other, TokenWithPosition):
            return TokenWithPosition(self.text + other.text,
                                     self.position)
        else:
            return TokenWithPosition(self.text + other,
                                     self.position)

    def __radd__(self, other):
        """Implements addition in the form of (obj) + TextWithPosition(...).

        Note that if the first element is TokenWithPosition,
        TokenWithPosition(...).__add__(...) will be used. As a result, we
        can assume WLOG that `other` is a type other than TokenWithPosition.

        >>> t1 = TokenWithPosition('as', 2) + TokenWithPosition('dfg', 2)
        >>> str(t1)
        'asdfg'
        >>> t1.position
        2
        >>> t2 = 'as' + TokenWithPosition('dfg', 2)
        >>> str(t2)
        'asdfg'
        >>> t2.position
        0
        """
        return TokenWithPosition(other + self.text,
                                 self.position - len(other))

    def __iadd__(self, other):
        """Implements addition in the form of TextWithPosition(...) += ...

        >>> t1 = TokenWithPosition('as', 0)
        >>> t1 += 'df'
        >>> str(t1)
        'asdf'
        >>> t1.position
        0
        """
        if isinstance(other, TokenWithPosition):
            self.text += other.text
        else:
            self.text += other
        return self

    @classmethod
    def join(cls, tokens, glue=''):
        if len(tokens) > 0:
            return TokenWithPosition(glue.join(t.text for t in tokens),
                                     tokens[0].position)
        else:
            return ''

    def __bool__(self):
        return bool(self.text)

    def __contains__(self, item):
        """
        >>> 'rg' in TokenWithPosition('corgi', 0)
        True
        >>> 'reg' in TokenWithPosition('corgi', 0)
        False
        >>> TokenWithPosition('rg', 0) in TokenWithPosition('corgi', 0)
        True
        """
        if isinstance(item, TokenWithPosition):
            return item.text in self.text
        return item in self.text

    def __iter__(self):
        """
        >>> list(TokenWithPosition('asdf', 0))
        ['a', 's', 'd', 'f']
        """
        return iter(self.__iter())

    def __iter(self):
        for i, c in enumerate(self.text):
            yield TokenWithPosition(c, self.position + i)

    def __getitem__(self, i):
        """Access characters in object just as with strings.

        >>> t1 = TokenWithPosition('asdf', 2)
        >>> t1[0]
        'a'
        >>> t1[-1]
        'f'
        >>> t1[:]
        'asdf'
        """
        if isinstance(i, int):
            start = i
        else:
            start = i.start
        if start is None:
            start = 0
        if start < 0:
            start = len(self.text) + start
        return TokenWithPosition(self.text[i], self.position + start)

    def split(self, sep=None, maxsplit=-1):
        result = []
        split_res = self.text.split(sep=sep, maxsplit=maxsplit)
        txt = self.text
        cur_offset = 0
        for s in split_res:
            cur_offset = txt.find(s, cur_offset)
            result.append(TokenWithPosition(s, self.position + cur_offset))
        return result

    def strip(self, *args, **kwargs):
        stripped = self.text.strip()
        offset = self.text.find(stripped)
        return TokenWithPosition(stripped, self.position + offset)


class Buffer:
    """Converts string or iterable into a navigable iterator of strings

    >>> def naturals(i):
    ...   while True:
    ...     yield str(i)
    ...     i += 1
    >>> b1 = Buffer(naturals(0))
    >>> next(b1)
    '0'
    >>> b1.forward()
    '1'
    >>> b1.endswith('1')
    True
    >>> b1.backward(2)
    '01'
    >>> b1.peek()
    '0'
    >>> b1.peek(2)
    '2'
    >>> b1.peek((0, 2))
    '01'
    >>> b1.startswith('01')
    True
    >>> b1[2:4]
    '23'
    >>> Buffer('asdf')[:10]
    'asdf'
    """

    def __init__(self, iterator, join=TokenWithPosition.join):
        """Initialization for Buffer

        :param iterator: iterator or iterable
        :param func join: function to join multiple buffer elements
        """
        assert hasattr(iterator, '__iter__'), 'Must be an iterable.'
        self.__iterator = iter(iterator)
        self.__queue = []
        self.__i = 0
        self.__join = join

    def hasNext(self):
        """Returns whether or not there is another element."""
        return bool(self.peek())

    def startswith(self, s):
        """
        Check if iterator starts with s, beginning from the current position
        """
        return self.peek((0, len(s))).startswith(s)

    def endswith(self, s):
        """
        Check if iterator ends with s, ending at current position
        """
        return self.peek((-len(s), 0)).endswith(s)

    def forward(self, j=1):
        """Move forward by j steps.

        >>> b = Buffer('abcdef')
        >>> b.forward(3)
        'abc'
        >>> b.forward(-2)
        'bc'
        """
        if j < 0:
            return self.backward(-j)
        self.__i += j
        return self[self.__i-j:self.__i]

    def forward_until(self, matches):
        """Forward until one of the provided matches is found.

        :param matches: set of valid strings

        >>> b = Buffer('abcdef')
        >>> b.forward_until(set('def'))
        'abc'
        >>> b.forward_until({'f'})
        'de'
        >>> b.forward_until('ambiguousstring')
        Traceback (most recent call last):
        ...
        UserWarning: forward_until accepts a set of strs, not a str
        """
        c = ''
        if isinstance(matches, str):
            raise UserWarning('forward_until accepts a set of strs, not a str')
        while self.hasNext() and not any(self.startswith(s) for s in matches):
            c += self.forward(1)
        return c

    def forward_until_not(self, matches):
        """Forward until string no longer matches one of provided matches.

        :param matches: set of valid strings

        >>> b = Buffer('abcdef')
        >>> b.forward_until_not(set('abc'))
        'abc'
        >>> b.forward_until_not(set('de'))
        'de'
        >>> b.forward_until_not('ambiguousstring')
        Traceback (most recent call last):
        ...
        UserWarning: forward_until_not accepts a set strs, not a str
        """
        c = ''
        if isinstance(matches, str):
            raise UserWarning('forward_until_not accepts a set strs, not a str')
        while self.hasNext() and any(self.startswith(s) for s in matches):
            c += self.forward(1)
        return c

    def backward(self, j=1):
        """Move backward by j steps.

        >>> b = Buffer('abcdef')
        >>> b.backward(-3)
        'abc'
        >>> b.backward(2)
        'bc'
        """
        if j < 0:
            return self.forward(-j)
        assert self.__i - j >= 0, 'Cannot move more than %d backward' % self.__i
        self.__i -= j
        return self[self.__i:self.__i+j]

    def peek(self, j=(0, 1)):
        """Peek at the next value(s), without advancing the Buffer"""
        if isinstance(j, int):
            return self[self.__i+j]
        return self[self.__i + j[0]:self.__i + j[1]]

    def __next__(self):
        """Implements next."""
        while self.__i >= len(self.__queue):
            self.__queue.append(TokenWithPosition(next(self.__iterator), self.__i))
        self.__i += 1
        return self.__queue[self.__i-1]

    def __getitem__(self, i):
        """Supports indexing list

        >>> b = Buffer('asdf')
        >>> b[5]
        Traceback (most recent call last):
            ...
        IndexError: list index out of range
        >>> b[0]
        'a'
        >>> b[1:3]
        'sd'
        >>> b[1:]
        'sdf'
        >>> b[:3]
        'asd'
        >>> b[:]
        'asdf'
        """
        j, old = i.stop if not isinstance(i, int) else i, self.__i
        while j is None or self.__i <= j:
            try:
                next(self)
            except StopIteration:
                break
        self.__i = old
        if isinstance(i, int):
            return self.__queue[i]
        return self.__join(self.__queue[i])

    def __iter__(self):
        return self

    @property
    def position(self):
        return self.__i


class CharToLineOffset(object):
    """
    Utility to convert absolute position in the source file
    to line_no:char_no_in_line.
    This can be very useful if we want to parse LaTeX and
    navigate to some elements in the generated DVI/PDF via SyncTeX.

    >>> clo = CharToLineOffset('''hello
    ... world
    ... I scream for ice cream!''')
    >>> clo(3)
    (0, 3)
    >>> clo(6)
    (1, 0)
    >>> clo(12)
    (2, 0)
    """
    def __init__(self, src):
        self.line_break_positions = [i for i, c in enumerate(src) if c == '\n']
        self.src_len = len(src)

    def __call__(self, char_pos):
        line_no = bisect.bisect(self.line_break_positions, char_pos)
        if line_no == 0:
            char_no = char_pos
        elif line_no == len(self.line_break_positions):
            line_start = self.line_break_positions[-1]
            char_no = min(char_pos - line_start - 1, self.src_len - line_start)
        else:
            char_no = char_pos - self.line_break_positions[line_no - 1] - 1
        return line_no, char_no
