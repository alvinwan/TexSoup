"""
Parse Key-Value Arguments
---

This script parses a TexSoup group containing top-level ``key=value`` entries
while preserving surrounding whitespace and separator text. Detected entries
are wrapped in a ``TexKeyVal`` object, while untouched formatting remains as
plain strings in the returned list.

If you only need a quick dictionary of raw string values, you could also use
TexSoup's built-in ``group.keyvals`` helper and then run TexSoup parsing again
on each value. That approach is simpler, but it reparses each value string and
is therefore less efficient than the preserved-object approach in this example.

To use it, run

    python parse_keyvals.py

after installing TexSoup.
"""

import re

from TexSoup import TexSoup
from TexSoup.data import TexText


class TexKeyVal(object):
    """Structured key=value entry extracted from a TexSoup group."""

    KEY_RE = re.compile(r'^([\s\S]*?)([A-Za-z][\w-]*)\s*$')

    def __init__(self, key, value):
        self.key = key
        self.value = list(value)

    def __eq__(self, other):
        if isinstance(other, TexKeyVal):
            return self.key == other.key and self.value == other.value
        return False

    def __repr__(self):
        return "TexKeyVal(%r, %r)" % (self.key, self.value)

    @staticmethod
    def _append_text(target, text):
        """Append text to a mixed list, merging adjacent strings."""
        if not text:
            return
        if target and isinstance(target[-1], str):
            target[-1] += text
        else:
            target.append(text)

    @staticmethod
    def _pop_trailing_whitespace(value):
        """Remove trailing whitespace from a value list and return it."""
        if value and isinstance(value[-1], str) and value[-1].isspace():
            return value.pop()
        return ''

    @classmethod
    def parse_parts(cls, parts):
        """Parse top-level key=value entries from group contents.

        :param iterable parts: Usually ``group.all`` from a ``TexGroup``.
        :return: Mixed list of preserved text fragments and ``TexKeyVal``.
        :rtype: list

        >>> soup = TexSoup(r'''
        ... \\newglossaryentry{naiive}
        ... {
        ...   name=na\\"{\\i}ve,
        ...   description={is a French loanword}
        ... }
        ... ''')
        >>> parts = parse_keyvals(soup.newglossaryentry.args[1])
        >>> parts[0]
        '\\n  '
        >>> parts[1]
        TexKeyVal('name', ['na\\\\"', BraceGroup(TexCmd('i')), 've'])
        >>> parts[2]
        '\\n  '
        >>> parts[3]
        TexKeyVal('description', [BraceGroup('is a French loanword')])
        >>> parts[4]
        '\\n'
        """
        parsed = []
        prefix_text = ''
        key = None
        value = []
        normalized = []

        def finish_value():
            nonlocal key, value
            parsed.append(cls(key, value))
            key = None
            value = []

        for part in parts:
            if isinstance(part, TexText):
                part = str(part)
            if isinstance(part, str):
                cls._append_text(normalized, part)
            else:
                normalized.append(part)

        for part in normalized:
            if not isinstance(part, str):
                if key is None:
                    cls._append_text(parsed, prefix_text)
                    prefix_text = ''
                    parsed.append(part)
                else:
                    value.append(part)
                continue

            chunk = part
            while chunk:
                if key is None:
                    if '=' not in chunk:
                        prefix_text += chunk
                        break
                    before, chunk = chunk.split('=', 1)
                    match = cls.KEY_RE.match(prefix_text + before)
                    if match is None:
                        prefix_text += before + '='
                        continue
                    prefix, key = match.groups()
                    cls._append_text(parsed, prefix)
                    prefix_text = ''
                    continue

                if ',' not in chunk:
                    cls._append_text(value, chunk)
                    break
                before, chunk = chunk.split(',', 1)
                cls._append_text(value, before)
                finish_value()

        if key is None:
            cls._append_text(parsed, prefix_text)
        else:
            suffix = cls._pop_trailing_whitespace(value)
            finish_value()
            cls._append_text(parsed, suffix + prefix_text)
        return parsed


def parse_keyvals(group):
    """Parse a TexSoup group into preserved text plus ``TexKeyVal`` entries.

    This example keeps the original top-level formatting and reuses the parsed
    TexSoup objects already present in ``group.all``. Compared with calling the
    built-in ``group.keyvals`` helper and reparsing each raw value string, this
    avoids extra parsing work and preserves nested objects more faithfully.
    """
    return TexKeyVal.parse_parts(group.all)


if __name__ == '__main__':
    soup = TexSoup(r'''
    \newglossaryentry{naiive}
    {
      name=na\"{\i}ve,
      description={is a French loanword}
    }
    ''')
    print(parse_keyvals(soup.newglossaryentry.args[1]))
