def rreplace(s, old, new, replacements='*'):
    """Replace starting from the end of the string

    >>> rreplace('haha1haha', 'ha', '')
    '1'
    >>> rreplace('haha1haha', 'ha', '', 1)
    'haha1ha'
    """
    if replacements == '*':
        return s.replace(old, new)
    return new.join(s.rsplit(old, replacements))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
