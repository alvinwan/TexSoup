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
        assert hasattr(iterator, '__iter__'), 'Must be an iterable.'
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

class Arguments(list):
    """List data structure, supporting additional ops for command arguments

    Use regular indexing to access the argument value. Use parentheses, like
    a method invocation, to access a dictionary of all information related
    to the argument. Use dot notation with args.tex<index> to access the
    stringified argument.

    >>> args = Arguments('{arg0}', '[arg1]', '{arg2}')
    >>> args[2]
    'arg2'
    >>> args(2)['type']
    'required'
    >>> args(2)['value']
    'arg2'
    >>> args.append('[arg3]')
    >>> args[3]
    'arg3'
    >>> len(args)
    4
    >>> args.tex1
    '[arg1]'
    >>> args.tex2
    '{arg2}'
    """

    def __init__(self, *args):
        """Append all arguments to list"""
        self.__types = []
        for arg in args:
            self.append(arg)

    def append(self, value):
        """Append a value to the list"""
        if not isinstance(value, (str, int)) or value == '':
            raise TypeError('Invalid item type for argument.')
        delimiter = self.str_to_type(value)
        if delimiter is None:
            raise TypeError('Malformed argument. Must either be in brackets or curly braces.')
        self.__types.append(delimiter)
        list.append(self, value[1:-1])

    def __call__(self, i):
        """
        Access more information about an argument using function-call syntax.
        """
        return {'type': self.__types[i], 'value': self[i] }

    def __getattr__(self, i):
        """Use dot notation to access stringified arguments."""
        if i[:3] == 'tex' and i[3:].isnumeric():
            i = int(i[3:])
            return self.type_to_str(self.__types[i], self[i])
        return list.__getattr__(self, i)

    @staticmethod
    def str_to_type(s):
        """Converts string to type"""
        if not isinstance(s, str):
            raise TypeError('Invalid string provied to str_to_type.')
        try:
            return {
                '{': 'required',
                '[': 'optional'
            }[s[0]]
        except KeyError:
            return None

    @staticmethod
    def type_to_str(t, string):
        """Converts type to string"""
        if t == 'required':
            return '{%s}' % string
        if t == 'optional':
            return '[%s]' % string
        raise TypeError('Invalid type. Must be either optional or required.')
