import re
from utils import rreplace


def TexSoup(tex):
    """Creates abstraction using Latex

    :param str tex: Latex
    :return: TexNode object
    """
    if tex.strip().startswith('\\begin{document}'):
        return TexNode(tex)
    return TexNode(tex, name='[document]', string='')


class TexNode(object):
    """Abstraction for Latex source"""

    __element = re.compile('(?P<name>[\S]+?)\{(?P<string>[\S\s]+?)\}')

    def __init__(self, tex='', name=None, string=None, options=None,
        branches=()):
        """Construct TexNode object

        :param str name: name of latex command
        :param str string: content of latex command
        :param str options: options for latex command
        :param str tex: original tex
        :param list TexNode branches: list of children
        """
        self.tex = tex
        Command.create(name, string, options, self)
        self.name, self.string, self.options = command
        self.innerTex = self.stripCommand(tex, command)
        self.branches = branches or self.parseBranches(self.innerTex)
        self.descendants = self.expandDescendants(self.branches)


    @staticmethod
    def stripCommand(tex, tag, form='\\%s{%s}'):
        r"""Strip a tag from the provided tex, only from the beginning and end.

        >>> TOC.stripCommand('\\begin{b}\\item y\\end{b}', 'begin', 'b')
        '\\item y'
        >>> TOC.stripCommand('\\begin{b}\\begin{b}\\item y\\end{b}\\end{b}',
        ... 'begin', 'b')
        '\\begin{b}\\item y\\end{b}'
        """
        stripped = tex.replace(form % tag, '', 1)
        if name == 'begin':
            stripped = rreplace(stripped, form % ('end', tag.string), '', 1)
        return stripped

    @staticmethod
    def parseFirstCommand(tex):
        r"""Extract name of latex element from tex

        :return Tag: first tag in the available Tex

        >>> TOC.parseTag('\\textbf{hello}\\textbf{yolo}')
        ('\\textbf', 'hello')
        """
        match = re.search(TOC.__element, tex)
        if not match:
            return '', ''
        return Tag(match.group('name'), match.group('string'), self)

    def splitByTag(self, tex, tag):
        """Split a latex file by a specific tag"""


    #####################
    # Tree Abstractions #
    #####################

    @staticmethod
    def expandDescendants(branches):
        """Expand descendants from list of branches

        :param list branches: list of immediate children as TexNode objs
        :return: list of all descendants
        """
        return sum([b.descendants() for b in branches], []) + branches

    def parseBranches(self, tex, hierarchy=None):
        r"""
        Parse top level of provided latex

        >>> TOC().parseBranches('''
        ... \\section{Hello}
        ... This is some text.
        ... \\begin{enumerate}
        ... \\item Item!
        ... \\end{enumerate}
        ... \\section{Yolo}
        ... ''')
        """
        hierarchy = hierarchy or self.hierarchy
        tag = self.parseTopTag(tex, hierarchy)

    def __getattr__(self, attr, *default):
        """Check source for attributes"""
        pass

    ###################
    # Utility Methods #
    ###################

    def __repr__(self):
        """Display contents"""
        return str(self)

    def __str__(self):
        """Display contents"""
        return self.string

    def __iter__(self):
        """Iterator over children"""
        return iter(self.branches)

    def __getitem__(self, i):
        return self.branches[i]


class Command(object):
    """command object"""

    def __init__(self, tex=None, name=None, string=None, options=None, toc):
        self.name = name
        self.string = string

    def s(self, form='\\%s{%s}'):
        return form % (self.name, self.string)

    @staticmethod
    def create(name, string, toc):
        """Creates tag if name and string are not available"""
        if not name:
            return toc.parseFirstCommand(toc.tex)
        return Tag(name, string, toc)

    def __iter__(self):
        return iter((name, string))

    def __repr__(self):
        return str(self)

    def __str__(self):
        return 'Tag(name=%s string=%s)' % self

if __name__ == '__main__':
    import doctest
    doctest.testmod()
