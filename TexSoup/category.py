"""Categorize all characters into one of category codes."""

from TexSoup.utils import CC, Token, to_buffer
import string


# Core category codes
# https://www.overleaf.com/learn/latex/Table_of_TeX_category_codes
others = set(string.printable) - set(string.ascii_letters) - \
    set('{}\\$&\n\r#^_~%\x00\x7d \t[]()')
CATEGORY_CODES = {
    CC.Escape:      '\\',
    CC.GroupBegin:  '{',
    CC.GroupEnd:    '}',
    CC.MathSwitch:  '$',
    CC.Alignment:   '&',  # not used
    CC.EndOfLine:   ('\n', '\r'),
    CC.Macro:       '#',  # not used
    CC.Superscript: '^',  # not used
    CC.Subscript:   '_',  # not used
    CC.Ignored:     chr(0),
    CC.Spacer:      (chr(32), chr(9)),
    CC.Letter:      tuple(string.ascii_letters),  # + lots of unicode
    CC.Other:       tuple(others),
    CC.Active:      '~',  # not used
    CC.Comment:     '%',
    CC.Invalid:      chr(127),

    # custom
    CC.BracketBegin: '[',
    CC.BracketEnd:  ']',
    CC.ParenBegin:  '(',
    CC.ParenEnd:    ')'
}


@to_buffer()
def categorize(text):
    r"""Generator for category code tokens on text, ignoring comments.

    :param Union[str,iterator,Buffer] text: LaTeX to process

    >>> chars = list(categorize(r'\bf{}%[ello+😂'))
    >>> chars[0].category
    <CategoryCodes.Escape: 1>
    >>> chars[1].category
    <CategoryCodes.Letter: 12>
    >>> chars[3].category
    <CategoryCodes.GroupBegin: 2>
    >>> chars[4].category
    <CategoryCodes.GroupEnd: 3>
    >>> chars[5].category
    <CategoryCodes.Comment: 15>
    >>> chars[6].category
    <CategoryCodes.BracketBegin: 19>
    >>> chars[-2].category
    <CategoryCodes.Other: 13>
    >>> chars[-1].category
    <CategoryCodes.Other: 13>
    >>> print(*chars)
    \ b f { } % [ e l l o + 😂
    >>> next(categorize(r'''
    ... ''')).category
    <CategoryCodes.EndOfLine: 6>
    """
    for position, char in enumerate(text):

        value = None
        for cc, values in CATEGORY_CODES.items():
            if char in values:
                value = char
                break

        if value is None:
            yield Token(char, position, CC.Other)
        else:
            yield Token(char, position, cc)
