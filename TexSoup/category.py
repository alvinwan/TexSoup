"""Categorize all characters into one of category codes."""

from TexSoup.utils import CC, Token, to_buffer
import string


# Core category codes
# https://www.overleaf.com/learn/latex/Table_of_TeX_category_codes
CATEGORY_CODES = {
    CC.Escape:     '\\',
    CC.GroupStart:  '{',  # not used
    CC.GroupEnd:    '}',  # not used
    CC.MathSwitch:  ('$$', '$'),
    CC.Alignment:   '&',  # not used
    CC.EndOfLine:   ('\n', '\r'),
    CC.Macro:       '#',  # not used
    CC.Superscript: '^',  # not used
    CC.Subscript:   '_',  # not used
    CC.Ignored:     chr(0),  # not used
    CC.Spacer:      (chr(32), chr(9)),    # not used
    CC.Letter:      tuple(string.ascii_letters),  # + lots of unicode
    CC.Other:       (),  # not defined, just anything left
    CC.Active:      '~',  # not used
    CC.Comment:     '%',
    CC.Invalid:      chr(127),  # not used
}


@to_buffer()
def categorize(text):
    r"""Generator for category code tokens on text, ignoring comments.

    :param Union[str,iterator,Buffer] text: LaTeX to process

    >>> chars = list(categorize(r'\bf{}%hello'))
    >>> chars[0].category
    <CategoryCodes.Escape: 1>
    >>> chars[1].category
    <CategoryCodes.Letter: 12>
    >>> chars[3].category
    <CategoryCodes.GroupStart: 2>
    >>> chars[4].category
    <CategoryCodes.GroupEnd: 3>
    >>> chars[5].category
    <CategoryCodes.Comment: 15>
    >>> print(*chars)
    \ b f { } % h e l l o
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
