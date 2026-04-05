"""
Parse Key-Value Arguments
---

This script turns a TexSoup group argument containing top-level ``key=value``
pairs into a dictionary. It is useful for commands such as
``\\newglossaryentry`` or ``\\includegraphics`` where a specific argument
follows a key-value mini-language.

The parsed values preserve TexSoup's existing structure, so each dictionary
value is a list of strings and nested TexSoup objects.

To use it, run

    python parse_keyvals.py

after installing TexSoup.
"""

from TexSoup import TexSoup
from TexSoup.data import TexText


def append_text(target, text):
    """Append text to a mixed list, merging adjacent strings."""
    if not text:
        return
    if target and isinstance(target[-1], str):
        target[-1] += text
    else:
        target.append(text)


def pop_trailing_whitespace(value):
    """Remove trailing whitespace from a value list and return it."""
    if value and isinstance(value[-1], str):
        suffix = value[-1].rstrip()
        if suffix != value[-1]:
            whitespace = value[-1][len(suffix):]
            if suffix:
                value[-1] = suffix
            else:
                value.pop()
            return whitespace
    return ''


def parse_keyvals(group):
    """Parse a TexGroup containing top-level ``key=value`` pairs.

    :param TexGroup group: Group to interpret as a key-value settings block.
    :return: Mapping from key names to lists of strings / TexSoup objects.
    :rtype: dict

    >>> soup = TexSoup(r'''
    ... \\newglossaryentry{naiive}
    ... {
    ...   name=na\\"{\\i}ve,
    ...   description={is a French loanword}
    ... }
    ... ''')
    >>> settings = parse_keyvals(soup.newglossaryentry.args[1])
    >>> list(settings)
    ['name', 'description']
    >>> [str(value) for value in settings['name']]
    ['na\\\\"', '{\\\\i}', 've']
    >>> str(settings['description'][0])
    '{is a French loanword}'
    """
    keyvals = {}
    key = None
    value = []
    normalized = []

    for part in group.all:
        if isinstance(part, TexText):
            part = str(part)
        if isinstance(part, str):
            append_text(normalized, part)
        else:
            normalized.append(part)

    for part in normalized:
        if not isinstance(part, str):
            if key is None:
                raise ValueError('Unexpected LaTeX content before a key name.')
            value.append(part)
            continue

        chunk = part
        while chunk:
            if key is None:
                chunk = chunk.lstrip(' \t\r\n,')
                if not chunk:
                    break
                if '=' not in chunk:
                    raise ValueError('Expected key=value text, got %r.' % chunk)
                before, chunk = chunk.split('=', 1)
                key = before.strip()
                if not key:
                    raise ValueError('Expected a key before "=".')
                if key in keyvals:
                    raise ValueError('Duplicate key %r.' % key)
                continue

            if ',' not in chunk:
                append_text(value, chunk)
                break
            before, chunk = chunk.split(',', 1)
            append_text(value, before)
            pop_trailing_whitespace(value)
            keyvals[key] = value
            key = None
            value = []

    if key is not None:
        pop_trailing_whitespace(value)
        keyvals[key] = value

    return keyvals


if __name__ == '__main__':
    soup = TexSoup(r'''
    \newglossaryentry{naiive}
    {
      name=na\"{\i}ve,
      description={is a French loanword}
    }
    ''')
    print(parse_keyvals(soup.newglossaryentry.args[1]))
