import itertools
from TexSoup.utils import to_navigable_iterator, NavigableIterator
from TexSoup import TexNode
from marisa_trie import Trie

##################
# CONFIGURATIONS #
##################

# characters that terminate commands
COMMAND_TERMINATORS = {'[', '{', ' ', '\\'}

# characters that terminate text blocks
TEXT_TERMINATORS = {'\n'}

#############
# INTERFACE #
#############

def buffer(source, start=0):
    """Generator for all child commands in tex source

    :param TexNode source: the LaTeX source
    :param int start: number of parsed commands to skip
    :return generator: TexNodes for each command
    """
    generator = parse(source.source)
    for _ in range(start):
        next(generator)
    for node in generator:
        node.parent = source
        yield node

@to_navigable_iterator
def parse(iterator):
    """Generator with TexNode for all commands found

    :param iterator iterator: Character-by-character iterator over LaTeX
    :return generator: generator of TexNodes
    """
    while True:
        i = iterator.peek()
        if i == '\\':
            yield parsers['command'](iterator)
            continue
        yield parsers['text'](iterator)

###########
# PARSERS #
###########

@to_navigable_iterator
def parse_command(iterator):
    """Parses and returns command, advancing iterator to end of command.

    >>> print(parse_command('\command text'))
    \command
    >>> print(parse_command('\command[opt] test'))
    \command[opt]
    >>> print(parse_command('\command{req}[opt]{req} test'))
    \command{req}[opt]{req}
    """
    assert next(iterator) == '\\', 'Command must begin with "\\"'
    command = parse_until_terminate(iterator, COMMAND_TERMINATORS)
    node = TexNode('\\' + command, command)
    # cannot detect nested braces
    while iterator.peek() in {'{', '['}:
        arg = parse_until_terminate(iterator, {'}', ']'})
        node.source += {'}': '%s}', ']': '%s]'}[next(iterator)] % arg
        node.arguments.append(arg)
    if command == 'begin':
        iterator.backward(6)
        return parsers['begin'](iterator)
    return node

@to_navigable_iterator
def parse_text(iterator):
    """Parses and returns text, advancing iterator to end of text block.

    >>> ni = NavigableIterator('''line1
    ... line2
    ... ''')
    >>> parse_text(ni)
    'line1'
    >>> parse_text(ni)
    'line2'
    """
    return parse_until_terminate(iterator, TEXT_TERMINATORS, -1)

@to_navigable_iterator
def parse_until_terminate(iterator, terminators, backward=0, required=()):
    """Return iterator up until a terminator. The terminator may be multiple
    characters long.

    :param iterator iterator: iterator over all characters
    :param set terminators: set of terminators
    :param int backward: number of steps to retrace, after parsing text

    >>> s = NavigableIterator('command text')
    >>> parse_until_terminate(s, COMMAND_TERMINATORS)
    'command'
    >>> next(s)
    ' '
    >>> parse_until_terminate('nono\end{itemize}hoho', {'\end{itemize}'})
    'nono'
    """
    result, prefix, trie, terminated = '', '', Trie(terminators), False
    for c in iterator:
        if c in terminators or prefix in trie:
            terminated = True
            break
        prefix += c
        if not trie.has_keys_with_prefix(prefix):
            result += prefix
            prefix = ''
    if not terminated and required:
        raise EOFError('Expecting a %s .' % str(required))
    iterator.backward(backward+1)
    return result

parsers = {
    'terminate': parse_until_terminate,
    'command': parse_command,
    'text': parse_text
}
