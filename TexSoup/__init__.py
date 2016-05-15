

def TexSoup(tex):
    """
    At a high-level, parses provided Tex into navigable, searchable structure.

    :param (iterable, string) tex: the Tex source
    :return TexNode: object representing tex document
    """
    return TexNode(tex)


class TexNode(object):
    """Abstraction for Tex source"""

    def __init__(self, source):
        """Creates TexNode object

        :param source: Tex source
        """
        assert source, 'Source cannot be empty.'
        self.__source = source

    ##############
    # PROPERTIES #
    ##############

    @property
    def command(self):
        """Returns command"""
        return next(parser.buffer(self))

    @property
    def name(self):
        """Returns name of command"""
        return self.command[1:].split('{')[0]

    @property
    def string(self):
        """Returns string of command"""
        return self.command[:-1].split('{')[1]

    def arg(self, i):
        """Returns arg of index i"""
        raise NotImplementedError()

    @property
    def contents(self):
        """Returns a list of all children, of this TeX element"""
        return list(self.children)

    @property
    def children(self):
        """Returns all immediate children of this TeX element"""
        return parser.buffer(self, start=1, recursive=False)

    @property
    def descendants(self):
        """Returns all descendants of this TeX element."""
        return parser.buffer(self, start=1)

    ##########
    # SEARCH #
    ##########

    def find_all(name=None, attrs={}):
        """Return all descendant nodes matching criteria, naively."""
        for descendant in self.descendants:
            if self.__match(name, attrs):
                yield descendant

    def find(name=None, attrs={}):
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

    def __getattr__(self, attr, default=None):
        """Convert all invalid attributes into basic find operation."""
        return self.find(attr, *default) or default
