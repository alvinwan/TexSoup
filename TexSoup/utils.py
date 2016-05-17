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

def to_navigable_iterator(f, i=0):
    """
    Decorator converting all strings and iterators/iterables into
    NavigableIterators.

    :param int i: index of iterator argument. Used only if not a kwarg.
    """
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        iterator = kwargs.get('iterator', args[i])
        if not isinstance(iterator, NavigableIterator):
            iterator = NavigableIterator(iterator)
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

class NavigableIterator:
    """Converts string or iterable into a navigable iterator of strings

    >>> def naturals(i):
    ...   while True:
    ...     yield str(i)
    ...     i += 1
    >>> ni = NavigableIterator(naturals(0))
    >>> next(ni)
    '0'
    >>> ni.forward()
    '1'
    >>> ni.backward(2)
    '01'
    >>> ni.peek()
    '0'
    >>> ni.peek(2)
    '01'
    >>> ni[2:4]
    '23'
    >>> ni2 = NavigableIterator(naturals(0), coerce=int)
    >>> ni2.forward(3)
    12
    """

    def __init__(self, iterator, coerce=str):
        """Initialization for NavigableIterator

        :param iterator: iterator or iterable
        :param func coerce: optional coercion to datatype (cannot be changed)
        """
        assert hasattr(iterator, '__iter__'), 'Must be an iterable.'
        self.__iterator = iter(iterator)
        self.__queue = []
        self.__i = 0
        self.__coerce = coerce

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

    def peek(self, j=1):
        """Peek at the next value(s), without advancing the NavigableIterator"""
        return self[self.__i:self.__i+j]

    def __next__(self):
        """Implements next."""
        while self.__i >= len(self.__queue):
            self.__queue.append(self.__coerce(next(self.__iterator)))
        self.__i += 1
        return self.__queue[self.__i-1]

    def __getitem__(self, i):
        """Supports indexing list"""
        j, old = i.stop if not isinstance(i, int) else i, self.__i
        while self.__i <= j:
            next(self)
        self.__i = old
        return self.__coerce(''.join(map(str, self.__queue[i])))

    def __iter__(self):
        return self
