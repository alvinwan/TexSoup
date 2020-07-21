"""
Count References
---

This script counts the number of times each label is referenced, in a given tex
document. To use it, run

    python count_reference.py

after installing TexSoup.

@author: Alvin Wan
@site: alvinwan.com
"""

from TexSoup import TexSoup


def count(tex):
    """Extract all labels, then count the number of times each is referenced in
    the provided file. Does not follow \includes.
    """

    # soupify
    soup = TexSoup(tex)

    # extract all unique labels
    labels = set(label.string for label in soup.find_all('label'))

    # create dictionary mapping label to number of references
    label_refs = {}
    for label in labels:
        refs = soup.find_all('\\ref{%s}' % label)
        pagerefs = soup.find_all('\\pageref{%s}' % label)
        label_refs[label] = len(list(refs)) + len(list(pagerefs))

    return label_refs


if __name__ == '__main__':
    counts = count(open(input('Tex file:').strip()))

    if not counts:
        print('No labels found.')
    else:
        print(counts)
