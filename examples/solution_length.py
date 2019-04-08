"""
Solution Length
---

This script measures the length of solutions, given the command used to denote
answers. To use it, run

    python solution_length.py

after installing TexSoup.

@author: Alvin Wan
@site: alvinwan.com
"""

from TexSoup import TexSoup


def sollen(tex, command):
    r"""Measure solution length

    :param Union[str,buffer] tex: the LaTeX source as a string or file buffer
    :param str command: the command denoting a solution i.e., if the tex file
        uses '\answer{<answer here>}', then the command is 'answer'.
    :return int: the solution length
    """
    return sum(len(a.string) for a in TexSoup(tex).find_all(command))


if __name__ == '__main__':
    print(
        'Solution length:',
        sollen(open(input('Tex file:').strip()), input('Solution command:')))
