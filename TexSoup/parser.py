
def buffer(source, start=0, recursive=True):
    """Generator for all commands in tex source

    :param TexNode source: the LaTeX source
    :param bool recursive: whether or not to include nested commands
    :param int start: number of commands to skip
    :return generator: for all commands
    """
    
