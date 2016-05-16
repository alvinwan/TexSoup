import functools

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

class NavigableIterator:
    """Converts string or iterable into a navigable iterator

    >>> ni = NavigableIterator('asdfghjkl')
    >>> next(ni)
    'a'
    >>> ni.forward()
    >>> next(ni)
    'd'
    >>> ni.backward(2)
    >>> next(ni)
    's'
    >>> ni.peek()
    'd'
    >>> next(ni)
    'd'
    """

    def __init__(self, iterator):
        self.__iterator = iterator
        if isinstance(iterator, str):
            self.__iterator = iter(iterator)
        self.__queue = []
        self.__i = 0

    def forward(self, j=1):
        """Move forward by j steps."""
        if j < 0:
            self.backward(-j)
        self.__i += j

    def backward(self, j=1):
        """Move backward by j steps."""
        if j < 0:
            self.forward(-j)
        assert self.__i - j >= 0, 'Cannot move more than %d backward' % self.__i
        self.__i -= j

    def peek(self):
        """Peek at the next value, without advancing the NavigableIterator"""
        v = next(self)
        self.__i -= 1
        return v

    def __next__(self):
        """Implements next."""
        while self.__i >= len(self.__queue):
            self.__queue.append(next(self.__iterator))
        self.__i += 1
        return self.__queue[self.__i-1]

    def __iter__(self):
        return self
