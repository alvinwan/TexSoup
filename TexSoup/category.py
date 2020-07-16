"""Categorize all characters into one of category codes."""

from TexSoup.utils import CC, Token, to_buffer
import string


# Core category codes
# https://www.overleaf.com/learn/latex/Table_of_TeX_category_codes
CATEGORY_CODES = {
    CC.Command:     '\\',
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

    >>> chars = list(categorize(r'\textbf{'))
    >>> chars[0].category
    <CategoryCodes.Command: 1>
    >>> chars[1].category
    <CategoryCodes.Letter: 12>
    >>> chars[-1].category
    <CategoryCodes.GroupStart: 2>
    >>> print(*chars)
    \ t e x t b f {
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
