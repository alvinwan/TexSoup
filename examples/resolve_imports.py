"""
Resolve Imports
---

This script resolves imports and updates the parse tree, in place, in a given
tex document. To use it, run

    python resolve_imports.py

after installing TexSoup.

@author: Alvin Wan
@site: alvinwan.com
"""

from TexSoup import TexSoup


def resolve(tex):
    """Resolve all imports and update the parse tree.

    Reads from a tex file and once finished, writes to a tex file.
    """

    # soupify
    soup = TexSoup(tex)

    # resolve subimports
    for subimport in soup.find_all('subimport'):
        path = subimport.args[0] + subimport.args[1]
        subimport.replace(*resolve(open(path)).contents)

    # resolve imports
    for _import in soup.find_all('import'):
        _import.replace(*resolve(open(_import.args[0])).contents)

    # resolve includes
    for include in soup.find_all('include'):
        include.replace(*resolve(open(include.args[0])).contents)

    return soup

if __name__ == '__main__':
    new_soup = resolve(open(input('Source Tex file:').strip()))
    with open(input('Destination Tex file:').strip()) as f:
        f.write(repr(new_soup))
