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
        self.command = self.parseFirstCommand(tex)
        self.name, self.string = self.command
        self.innerTex = self.stripCommand(tex, self.command)
        self.branches = self.parseBranches(self.innerTex)
        self.descendants = self.expandDescendants(self.branches)

    @staticmethod
    def parseFirstCommand(tex):
        r"""Extract name of latex element from tex

        :return Tag: first tag in the available Tex

        >>> TexNode.parseFirstCommand('\\textbf{hello}\\textbf{yolo}')
        \textbf{hello}
        """
        return Command.fromLatex(tex)

    @staticmethod
    def stripCommand(tex, cmd):
        r"""Strip a tag from the provided tex, only from the beginning and end.

        >>> TexNode.stripCommand('\\section{b}\\item y',
        ... Command.fromLatex('\\section{b}'))
        '\\item y'
        >>> TexNode.stripCommand('\\begin{b}\\begin{b}\\item y\\end{b}\\end{b}',
        ... Command.fromLatex('\\begin{b}'))
        '\\begin{b}\\item y\\end{b}'
        """
        stripped = tex.replace(str(cmd), '', 1)
        if cmd.operator == 'begin':
            stripped = rreplace(stripped,
                str(cmd.update(operator='end', params=cmd.params[0])), '', 1)
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

        >>> TexNode().parseBranches('''
        ... \\section{Hello}
        ... This is some text.
        ... \\begin{enumerate}
        ... \\item Item!
        ... \\end{enumerate}
        ... \\section{Yolo}
        ... ''')
        []
        """
        return []

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
    rdelimiters = dict(p[::-1] for p in delimiters.items())

    def __init__(self, operator, params=(), tex=None):
        """Initializer for a Command

        :param str operator: The operator
        :param list params: List of parameters
        :param str tex: raw tex
        """
        self.operator = operator
        self.params = params
        self.tex = tex

    def update(self, **kwargs):
        """Set attributes"""
        self.tex = None
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def __iter__(self):
        params = [p for p in self.params if p.strip().startswith('{')]
        return iter((self.operator, params[0] if params else None))

    def __repr__(self):
        return str(self)

    def __str__(self):
        """
        >>> cmd = Command.fromLatex(r'\\item[2.]{hello there}')
        >>> cmd.operator, cmd.params
        ('item', ['[2.]', '{hello there}'])
        >>> cmd.tex = None
        >>> cmd
        \\item[2.]{hello there}
        """
        if self.tex:
            return self.tex
        return '\\%s%s' % (self.operator, ''.join(self.params))

    @staticmethod
    def fromLatex(tex):
        """Converts single tex command into Command object

        >>> Command.fromLatex(r'\\hoho haha')
        \\hoho
        >>> Command.fromLatex(r'\\hoho{haha}[hehe] huehue')
        \\hoho{haha}[hehe]
        >>> cmd = Command.fromLatex(r'\\answer{You \\textbf{so?}}{Grrr.}')
        >>> cmd.operator, cmd.params
        ('answer', ['{You \\\\textbf{so?}}', '{Grrr.}'])
        >>> cmd
        \\answer{You \\textbf{so?}}{Grrr.}
        """
        ntex = '\\'
        delimiters = {}
        operator, param, params = '', '', []
        is_operator, is_param = True, False
        for c in '\\'.join(tex.split('\\')[1:]):

            # Test if parameter is started
            if c in Command.delimiters:
                delimiters.setdefault(c, 0)
                delimiters[c] += 1
                if is_operator: is_operator = False
                is_param = True

            # Test if parameter is terminated
            if c in Command.delimiters.values():
                delimiters[Command.rdelimiters[c]] -= 1
                if delimiters[Command.rdelimiters[c]] == 0:
                    is_param = False
                    params.append(param+c)
                    param = ''
                    ntex += c
                    continue

            # Close if space reached and all parameters closed
            if not any(delimiters.values()) and c in {' ', '\\'}:
                break

            # Append to string
            if is_operator:     operator += c
            elif is_param:      param += c
            ntex += c

        return Command(operator, params, ntex)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
