import re
from utils import rreplace


def TexSoup(tex):
    """Creates abstraction using Latex

    :param str tex: Latex
    :return: TexNode object
    """
    if tex.strip().startswith('\\begin{document}'):
        return TexNode(tex)
    return TexNode('\\begin{document}%s\\end{document}' % tex)


class TexNode(object):
    """Abstraction for Latex source"""

    def __init__(self, tex=''):
        """
        Construct TexNode object, by running several initializations:
        - parse the current command name, string, and options
        - extract the innerTex
        - find all branches and descendants

        :param str tex: original tex
        """
        self.tex = tex
        self.command = self.parseFirstCommand()
        self.name, self.string, self.options = self.command
        self.innerTex = self.stripCommand(tex, self.command)
        self.branches = branches or self.parseBranches(self.innerTex)
        self.descendants = self.expandDescendants(self.branches)

    @staticmethod
    def parseFirstCommand(tex):
        r"""Extract name of latex element from tex

        :return Tag: first tag in the available Tex

        >>> TOC.parseTag('\\textbf{hello}\\textbf{yolo}')
        \\textbf{hello}
        """
        return Command.fromLatex(tex, self)

    @staticmethod
    def stripCommand(tex, cmd):
        r"""Strip a tag from the provided tex, only from the beginning and end.

        >>> TOC.stripCommand('\\section{b}\\item y', 'section', 'b')
        '\\item y'
        >>> TOC.stripCommand('\\begin{b}\\begin{b}\\item y\\end{b}\\end{b}',
        ... 'begin', 'b')
        '\\begin{b}\\item y\\end{b}'
        """
        stripped = tex.replace(str(cmd), '', 1)
        if cmd.name == 'begin':
            stripped = rreplace(stripped, str(cmd.update(name='end')), '', 1)
        return stripped

    def splitByCommand(self, tex, cmd):
        """Split a latex file by a specific command"""
        pass

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

    def parseBranches(self, tex):
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
    """Generalized Command object for LaTeX sources"""

    delimiters = {'{': '}', '[': ']'}

    def __init__(self, operator, params, node, tex=None):
        """Initializer for a Command

        :param str operator: The operator
        :param list params: List of parameters
        :param TexNode node: a tex node
        :param str tex: raw tex
        """
        self.name = name
        self.params = params
        self.toc = toc
        self.tex = tex

    def update(**kwargs):
        """Set attributes"""
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def __repr__(self):
        return str(self)

    def __str__(self):
        """
        >>> cmd = Command.fromLatex(r'\\item[2.]{hello there}')
        >>> cmd.name, cmd.params
        ('item', ['[2.]', '{hello there}'])
        >>> cmd.tex = None
        >>> cmd
        \\item[2.]{hello there}
        """
        if self.tex:
            return self.tex
        return '\\%s%s' % (self.name, ''.join(self.params))

    @staticmethod
    def fromLatex(tex, toc):
        """Converts single tex command into Command object

        >>> Command.fromLatex()"""
        string = '\\'
        delimiters = {}
        for c in '\\'.join(tex.split('\\')[1:]):
            if c in self.delimiters:
                delimiters.setdefault(c, 0)
                delimiters[c] += 1
            if c in self.delimiters.values():
                delimiters[c] -= 1
            if not any(delimiters.values()) and c == ' ':
                break
            string += c
        return string

if __name__ == '__main__':
    import doctest
    doctest.testmod()
