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
        text = parsers['text'](iterator)
        if text.source:
            yield text

###########
# PARSERS #
###########

# Specific Parsers

@to_navigable_iterator
def parse_command(iterator):
    """Parses and returns command, advancing iterator to end of command.

    **WARNING** Cannot detect nested braces.

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
    while iterator.peek() in {'{', '['}:
        arg = parse_until_terminate(iterator, {'}', ']'})
        arg = {'}': '%s}', ']': '%s]'}[next(iterator)] % arg
        node.source += arg
        node.arguments.append(arg[1:-1])
    if command == 'begin':
        node.name = node.arguments[0]
        return parsers['begin'](iterator, node)
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
    string = parse_until_terminate(iterator, TEXT_TERMINATORS, -1)
    return TexNode(string, 'text', arguments=(string,))

# Body parsers
# Invoked by parse_command after the command has been removed and identified

@to_navigable_iterator
def parse_begin(iterator, env):
    """Parse environments of the form \begin{env} ... \end{env}

    **WARNING** Cannot detect nested environments.

    :param iterator iterator: an iterator beginning with the body of the
        environment, after the \begin{env} command.
    :param (string, TexNode) environment: the name of the environment
        (e.g., itemize) or a TexNode containing the source and name
    """
    string = parse_until_terminate(iterator,
        required={'\end{%s}' % env.name}, inclusive=True)
    env.source += string
    return env

# Generic Parsers

@to_navigable_iterator
def parse_until_terminate(iterator, optional=set(), backward=0, required=set(),
    inclusive=False):
    """Return iterator up until a terminator. The terminator may be multiple
    characters long.

    :param iterator iterator: iterator over all characters
    :param set terminators: set of terminators
    :param int backward: number of steps to retrace, after parsing text
    :param bool inclusive: including the terminator or not

    >>> s = NavigableIterator('command text')
    >>> parse_until_terminate(s, COMMAND_TERMINATORS)
    'command'
    >>> next(s)
    ' '
    >>> parse_until_terminate('nono\end{itemize}hoho',
    ...     required={'\end{itemize}'})
    'nono'
    """
    assert optional or required, 'Either indicate optinal terminators or required terminators.'
    terminators = optional | required
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
        raise EOFError('Expecting %s' % str(required))
    iterator.backward(backward+1)
    return result + prefix if inclusive else result

parsers = {
    'terminate': parse_until_terminate,
    'command': parse_command,
    'text': parse_text,
    'begin': parse_begin
}
