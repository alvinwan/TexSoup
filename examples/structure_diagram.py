"""
Structure Diagram
---
This script creates a structure diagram from a given LaTeX document.
To use it, run

    python structure_diagram.py

after installing TexSoup.

@author: Simon Maenaut
@e-mail: simon@ulyssis.org
"""
import TexSoup
import textwrap


def tex_read(tex_soup, prefix=" |- "):
    result = ""
    for tex_code in tex_soup:
        if isinstance(tex_code, TexSoup.TexEnv):
            result += tex_read((prefix + tex_code.begin + str(tex_code.args)
                                + "\n" + textwrap.indent(tex_read(tex_code.all), "\t")
                                + "\n" + prefix + tex_code.end).splitlines(), prefix="")
        elif isinstance(tex_code, TexSoup.TexCmd):
            result += textwrap.indent("\\" + tex_code.name + str(tex_code.args), prefix, lambda line: True)
        elif isinstance(tex_code, TexSoup.TexText):
            result += textwrap.indent(tex_code.text.strip(), prefix, lambda line: True)
        elif isinstance(tex_code, TexSoup.Arg):
            result += tex_read((prefix + "{" + "\n"
                                + textwrap.indent(tex_read(TexSoup.TexSoup(tex_code.value).expr.all), "\t")
                                + "\n" + prefix + "}").splitlines(), prefix="")
        else:
            result += textwrap.indent(str(tex_code), prefix)
        if not result.endswith("\n"):
            result += "\n"

    return result


# Run programme as main file
if __name__ == '__main__':

    tex_path = input('LaTex file:').strip()
    tex_text = open(tex_path).read()
    tex_tree = tex_read(TexSoup.TexSoup(tex_text).expr.all)
    print("LaTeX Contents:\n== == ==\n\n")
    print(tex_tree)
