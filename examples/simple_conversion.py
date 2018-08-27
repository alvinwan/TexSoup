"""
Simple Conversion
---
This script converts a given LaTeX document to a json file and checks the conversion.
To use it, run

    python simple_conversion.py

after installing TexSoup.

@author: Simon Maenaut
@e-mail: simon@ulyssis.org
"""
import TexSoup
import json


def to_dictionary(tex_tree):
    str_tree = []
    for i in tex_tree:
        if isinstance(i, list):
            str_tree.append(i)
        elif isinstance(i, TexSoup.TexEnv):
            str_tree.append(
                {
                    i.name: [
                        {"begin": i.begin + str(i.arguments)},
                        to_dictionary(i.everything),
                        {"end": i.end},
                    ]
                }
            )
        elif isinstance(i, TexSoup.TexCmd):
            str_tree.append({i.name: "\\" + i.name + str(i.arguments)})
        elif isinstance(i, TexSoup.TokenWithPosition):
            str_tree.append(str(i.text))
        elif isinstance(i, TexSoup.Arg):
            str_tree.append(["{", to_dictionary(TexSoup.TexSoup(i.value).expr.everything), "}"])
        else:
            str_tree.append(str(i))

    return str_tree


def to_latex(tex_json):
    if isinstance(tex_json, dict):
        tex_code = "".join([to_latex(val) for val in tex_json.values()])
    elif isinstance(tex_json, list):
        tex_code = "".join([to_latex(val) for val in tex_json])
    else:
        tex_code = tex_json

    return tex_code


# Run programme as main file.
# This should always print True as output.
if __name__ == '__main__':

    import os

    tex_path = input('LaTex file:').strip()
    tex_text = open(tex_path).read()
    tex_dict = {"latex": {"contents": to_dictionary(TexSoup.TexSoup(tex_text).expr.everything)}}

    new_path = ".".join(tex_path.split(".")[:-1]) + "__tmp.json"
    json.dump(tex_dict, open(new_path, "x"), indent="  ")
    new_json = json.load(open(new_path))
    os.remove(new_path)
    new_text = to_latex(new_json)

    print(tex_text == new_text, "\n\n\n", json.dumps(new_json, indent="  "))
