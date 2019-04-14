Parsing Mechanics
===================================

.. automodule:: TexSoup.reader

Tokenizer
-----------------------------------

.. autofunction:: tokenize
.. autofunction:: next_token

.. autofunction:: token
.. autofunction:: tokenize_punctuation_command
.. autofunction:: tokenize_command
.. autofunction:: tokenize_line_comment
.. autofunction:: tokenize_argument
.. autofunction:: tokenize_math
.. autofunction:: tokenize_string

Mapper
-----------------------------------

.. autofunction:: read_tex
.. autofunction:: read_item
.. autofunction:: read_math_env
.. autofunction:: read_env
.. autofunction:: read_args
.. autofunction:: read_arg
