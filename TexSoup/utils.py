"""
Utils for TexSoup
---

This file consists of various utilities for TexSoup, split into 2 categories by
function:

1. Decorators
2. Generalized utilities
"""

import functools

##############
# Decorators #
##############

def to_buffer(f, i=0):
    """
    Decorator converting all strings and iterators/iterables into
    Buffers.

    :param int i: index of iterator argument. Used only if not a kwarg.
    """
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        iterator = kwargs.get('iterator', args[i])
        if not isinstance(iterator, Buffer):
            iterator = Buffer(iterator)
        if 'iterator' in kwargs:
            kwargs['iterator'] = iterator
        else:
            args = list(args)
            args[i] = iterator
        return f(*args, **kwargs)
    return wrap

#########################
# Generalized Utilities #
#########################

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
    >>> b2 = Buffer(naturals(0), coerce=int)
    >>> b2.forward(3)
    12
    >>> Buffer('asdf')[:10]
    'asdf'
    """

    def __init__(self, iterator, coerce=str):
        """Initialization for Buffer

        :param iterator: iterator or iterable
        :param func coerce: optional coercion to datatype (cannot be changed)
        """
        assert hasattr(iterator, '__iter__'), 'Must be an iterable.'
        self.__iterator = iter(iterator)
        self.__queue = []
        self.__i = 0
        self.__coerce = coerce

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
        """Move forward by j steps."""
        if j < 0:
            return self.backward(-j)
        self.__i += j
        return self[self.__i-j:self.__i]

    def backward(self, j=1):
        """Move backward by j steps."""
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
            self.__queue.append(self.__coerce(next(self.__iterator)))
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
        return self.__coerce(''.join(map(str, self.__queue[i])))

    def __iter__(self):
        return self
