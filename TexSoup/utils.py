import bisect
import functools

from enum import IntEnum as IntEnumBase


##########
# Tokens #
##########


def IntEnum(name, keys, start=1):
    """Explicitly define key-value pairs. For Python3.4 compatibility"""
    return IntEnumBase(name,
                       [(key, index) for index, key in enumerate(keys, start=start)])


CC = IntEnum('CategoryCodes', (
    'Escape',
    'GroupBegin',
    'GroupEnd',
    'MathSwitch',
    'Alignment',
    'EndOfLine',
    'Macro',
    'Superscript',
    'Subscript',
    'Ignored',
    'Spacer',
    'Letter',
    'Other',
    'Active',
    'Comment',
    'Invalid',

    # custom
    'MathGroupBegin',
    'MathGroupEnd',
    'BracketBegin',
    'BracketEnd',
    'ParenBegin',
    'ParenEnd'
))


# Only includes items that cannot cause failures
TC = IntEnum('TokenCode', (
    'Escape',
    'GroupBegin',
    'GroupEnd',
    'Comment',
    'MergedSpacer',  # whitespace allowed between <command name> and arguments
    'EscapedComment',
    'MathSwitch',
    'DisplayMathSwitch',
    'MathGroupBegin',
    'MathGroupEnd',
    'DisplayMathGroupBegin',
    'DisplayMathGroupEnd',
    'LineBreak',
    'CommandName',
    'Text',
    'BracketBegin',
    'BracketEnd',
    'ParenBegin',
    'ParenEnd',

    # temporary (Replace with macros support)
    'PunctuationCommandName',
    'SizeCommand',
    'Spacer'
), start=max(CC))


class Token(str):
    """Enhanced string object with knowledge of global position."""

    # noinspection PyArgumentList
    def __new__(cls, text='', position=None, category=None):
        """Initializer for pseudo-string object.

        :param text: The original string
        :param position: Position in the original buffer
        :param category: Category of token
        """
        self = str.__new__(cls, text)
        if isinstance(text, Token):
            self.text = text.text
            self.position = text.position
            self.category = category or text.category
        else:
            self.text = text
            self.position = position
            self.category = category
        return self

    def __repr__(self):
        return repr(self.text)

    def __str__(self):
        return str(self.text)

    def __getattr__(self, name):
        return getattr(self.text, name)

    def __eq__(self, other):
        """
        >>> Token('asdf', 0) == Token('asdf', 2)
        True
        >>> Token('asdf', 0) == Token('asd', 0)
        False
        """
        if isinstance(other, Token):
            return self.text == other.text
        else:
            return self.text == other

    def __hash__(self):
        """
        >>> hash(Token('asf')) == hash('asf')
        True
        """
        return hash(self.text)

    def __add__(self, other):
        """Implements addition in the form of TextWithPosition(...) + (obj).

        >>> t1 = Token('as', 0) + Token('df', 1)
        >>> str(t1)
        'asdf'
        >>> t1.position
        0
        >>> t2 = Token('as', 1) + 'df'
        >>> str(t2)
        'asdf'
        >>> t3 = Token(t2)
        >>> t3.position
        1
        """
        if isinstance(other, Token):
            return Token(self.text + other.text, self.position, self.category)
        else:
            return Token(self.text + other, self.position, self.category)

    def __radd__(self, other):
        """Implements addition in the form of (obj) + TextWithPosition(...).

        Note that if the first element is Token,
        Token(...).__add__(...) will be used. As a result, we
        can assume WLOG that `other` is a type other than Token.

        >>> t1 = Token('as', 2) + Token('dfg', 2)
        >>> str(t1)
        'asdfg'
        >>> t1.position
        2
        >>> t2 = 'as' + Token('dfg', 2)
        >>> str(t2)
        'asdfg'
        >>> t2.position
        0
        """
        return Token(
            other + self.text, self.position - len(other), self.category)

    def __iadd__(self, other):
        """Implements addition in the form of TextWithPosition(...) += ...

        >>> t1 = Token('as', 0)
        >>> t1 += 'df'
        >>> str(t1)
        'asdf'
        >>> t1.position
        0
        """
        if isinstance(other, Token):
            new = Token(self.text + other.text, self.position, self.category)
        else:
            new = Token(self.text + other, self.position, self.category)
        return new

    @classmethod
    def join(cls, tokens, glue=''):
        if len(tokens) > 0:
            return Token(
                glue.join(t.text for t in tokens),
                tokens[0].position,
                tokens[0].category)
        else:
            return Token.Empty

    def __bool__(self):
        return bool(self.text)

    def __contains__(self, item):
        """
        >>> 'rg' in Token('corgi', 0)
        True
        >>> 'reg' in Token('corgi', 0)
        False
        >>> Token('rg', 0) in Token('corgi', 0)
        True
        """
        if isinstance(item, Token):
            return item.text in self.text
        return item in self.text

    def __iter__(self):
        """
        >>> list(Token('asdf', 0))
        ['a', 's', 'd', 'f']
        """
        return iter(self.__iter())

    def __iter(self):
        for i, c in enumerate(self.text):
            yield Token(c, self.position + i, self.category)

    def __getitem__(self, i):
        """Access characters in object just as with strings.

        >>> t1 = Token('asdf', 2)
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
        return Token(self.text[i], self.position + start, self.category)

    def strip(self, *args, **kwargs):
        stripped = self.text.strip(*args, **kwargs)
        offset = self.text.find(stripped)
        return Token(stripped, self.position + offset, self.category)

    def lstrip(self, *args, **kwargs):
        """Strip leading whitespace for text.

        >>> t = Token('  asdf  ', 2)
        >>> t.lstrip()
        'asdf  '
        """
        stripped = self.text.lstrip(*args, **kwargs)
        offset = self.text.find(stripped)
        return Token(stripped, self.position + offset, self.category)

    def rstrip(self, *args, **kwargs):
        """Strip trailing whitespace for text.

        >>> t = Token('  asdf  ', 2)
        >>> t.rstrip()
        '  asdf'
        """
        stripped = self.text.rstrip(*args, **kwargs)
        offset = self.text.find(stripped)
        return Token(stripped, self.position + offset, self.category)


Token.Empty = Token('', position=0)


# TODO: Rename to Buffer (formerly MixedBuffer) and StringBuffer
# but needs test refactoring to change defaults
class Buffer:
    """Converts string or iterable into a navigable iterator of strings.

    >>> b1 = Buffer("012345")
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
    >>> def gen():
    ...     for i in range(10):
    ...         yield i
    >>> list(gen())
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    >>> list(Buffer(gen()))
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    """

    def __init__(self, iterator, join=Token.join, empty=lambda: '',
                 init=lambda content, index: Token(content, index)):
        """Initialization for Buffer.

        :param iterator: iterator or iterable
        :param func join: function to join multiple buffer elements
        """
        assert hasattr(iterator, '__iter__'), 'Must be an iterable.'
        self.__iterator = iter(iterator)
        self.__queue = []
        self.__i = 0
        self.__join = join
        self.__init = init
        self.__empty = empty

    # noinspection PyPep8Naming
    def hasNext(self, n=1):
        """Returns whether or not there is another element."""
        return bool(self.peek(n - 1))

    def startswith(self, s):
        """Check if iterator starts with s, beginning from the current
        position."""
        return self.peek((0, len(s))).startswith(s)

    def endswith(self, s):
        """Check if iterator ends with s, ending at current position."""
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
        return self[self.__i - j:self.__i]

    def num_forward_until(self, condition):
        """Forward until one of the provided matches is found.

        :param condition: set of valid strings
        """
        i, c = 0, ''
        while self.hasNext() and not condition(self.peek()):
            c += self.forward(1)
            i += 1
        assert self.backward(i) == c
        return i

    def forward_until(self, condition, peek=True):
        """Forward until one of the provided matches is found.

        The returned string contains all characters found before the condition
        was met. In other words, the condition will be true for the remainder
        of the buffer.

        :param Callable condition: lambda condition for the token to stop at

        >>> buf = Buffer(map(str, range(9)))
        >>> _ = buf.forward_until(lambda x: int(x) > 3)
        >>> c = buf.forward_until(lambda x: int(x) > 6)
        >>> c
        '456'
        >>> c.position
        4
        """
        c = self.__init(self.__empty(), self.peek().position)
        while self.hasNext() and not condition(self.peek() if peek else self):
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
        assert self.__i - j >= 0, 'Cannot move more than %d back' % self.__i
        self.__i -= j
        return self[self.__i:self.__i + j]

    def peek(self, j=0):
        """Peek at the next value(s), without advancing the Buffer.

        Return None if index is out of range.
        """
        try:
            if isinstance(j, int):
                return self[self.__i + j]
            return self[self.__i + j[0]:self.__i + j[1]]
        except IndexError:
            return None

    def __next__(self):
        """Implements next."""
        while self.__i >= len(self.__queue):
            self.__queue.append(self.__init(
                next(self.__iterator), self.__i))
        self.__i += 1
        return self.__queue[self.__i - 1]

    def __getitem__(self, i):
        """Supports indexing list.

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
        if isinstance(i, int):
            old, j = self.__i, i
        else:
            old, j = self.__i, i.stop

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
    """Utility to convert absolute position in the source file to
    line_no:char_no_in_line. This can be very useful if we want to parse LaTeX
    and navigate to some elements in the generated DVI/PDF via SyncTeX.

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


class MixedBuffer(Buffer):

    def __init__(self, iterator):
        """Initialization for Buffer, accepting types beyond strings.

        :param iterator: iterator or iterable
        :param func join: function to join multiple buffer elements

        >>> buf = MixedBuffer([324, 'adsf', lambda x: x])
        >>> buf.peek()
        324
        """
        super().__init__(iterator,
                         join=lambda x: x, empty=lambda x: [],
                         init=lambda content, index: content)


##############
# Decorators #
##############


def to_buffer(convert_in=True, convert_out=True, Buffer=Buffer):
    """Decorator converting all strings and iterators/iterables into
    Buffers.

    :param bool convert_in: Convert inputs where applicable to Buffers
    :param bool convert_out: Convert output to a Buffer
    :param type Buffer: Type of Buffer to convert into
    """
    def decorator(f):
        @functools.wraps(f)
        def wrap(*args, **kwargs):
            iterator = args[0]
            if convert_in:
                iterator = kwargs.get('iterator', iterator)
                if not isinstance(iterator, Buffer):
                    iterator = Buffer(iterator)
            output = f(iterator, *args[1:], **kwargs)
            if convert_out:
                return Buffer(output)
            return output
        return wrap
    return decorator


def to_list(f):
    """Converts generator or iterable output to list

    >>> class A:
    ...     @property
    ...     @to_list
    ...     def a(self):
    ...         for i in range(3):
    ...             yield i
    >>> A().a
    [0, 1, 2]
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return list(f(*args, **kwargs))
    return wrapper
