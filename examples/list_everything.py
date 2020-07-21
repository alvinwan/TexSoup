"""
List Everything
---
This script creates a tree of lists from a given LaTeX document.
To use it, run

    python list_everything.py

after installing TexSoup.

@author: Simon Maenaut
@e-mail: simon@ulyssis.org
"""
import TexSoup
import pprint


def everything(tex_tree):
    """
    Accepts a list of Union[TexNode,Token] and returns a nested list
    of strings of the entire source document.
    """
    result = []
    for tex_code in tex_tree:
        if isinstance(tex_code, TexSoup.TexEnv):
            result.append([tex_code.begin + str(tex_code.args), everything(tex_code.all), tex_code.end])
        elif isinstance(tex_code, TexSoup.TexCmd):
            result.append(["\\" + tex_code.name + str(tex_code.args)])
        elif isinstance(tex_code, TexSoup.TexText):
            result.append(tex_code.text)
        elif isinstance(tex_code, TexSoup.TexGroup):
            result.append(["{", everything(TexSoup.TexSoup(tex_code.value).expr.all), "}"])
        else:
            result.append([str(tex_code)])

    return result


# Run programme as main file
if __name__ == '__main__':

    tex_file = open(input('LaTex file:').strip())
    tex_soup = TexSoup.TexSoup(tex_file)
    tex_text = everything(tex_soup.expr.all)
    print("LaTeX Contents:\n== == ==\n\n")
    pprint.pprint(tex_text)
