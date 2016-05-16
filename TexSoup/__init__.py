import TexSoup
import _io

def TexSoup(tex):
    """
    At a high-level, parses provided Tex into navigable, searchable structure.

    :param (iterable, string) tex: the Tex source
    :return TexNode: object representing tex document
    """
    return TexNode(tex)


class TexNode(object):
    """Abstraction for Tex source"""

    def __init__(self, source, name='[tex]', arguments=()):
        """Creates TexNode object

        :param source: Tex source
        """
        assert hasattr(source, '__iter__'), 'TexNode source must be iterable.'
        self.source = source
        if isinstance(source, _io.TextIOWrapper):
            self.source = '\n'.join(source)
        self.name = name
        self.arguments = arguments or []

    ##############
    # PROPERTIES #
    ##############

    @property
    def contents(self):
        """Returns a list of all children, of this TeX element"""
        return list(self.children)

    @property
    def children(self):
        """Returns all immediate children of this TeX element"""
        return TexSoup.parser.buffer(self, start=1)

    @property
    def descendants(self):
        """Returns all descendants of this TeX element."""
        return TexSoup.parser.buffer(self, start=1)

    ##########
    # SEARCH #
    ##########

    def find_all(self, name=None, attrs={}):
        """Return all descendant nodes matching criteria, naively."""
        for descendant in self.descendants:
            if self.__match(name, attrs):
                yield descendant

    def find(self, name=None, attrs={}):
        """Return first descendant node matching criteria"""
        try:
            return next(self.find_all(name, attrs))
        except StopIteration:
            return None

    def __match(self, name=None, attrs={}):
        """Check if given attributes match current object"""
        attrs['name'] = name
        for k, v in attrs.items():
            if getattr(self, k) != v:
                return False
        return True

    def __str__(self):
        return self.source

    def __repr__(self):
        return self.source

    def __getattr__(self, attr, default=None):
        """Convert all invalid attributes into basic find operation."""
        return self.find(attr) or default
