Parsing Mechanics
===================================

.. automodule:: TexSoup.reader

Parser
-----------------------------------

.. autofunction:: read_tex
.. autofunction:: read_expr
.. autofunction:: read_spacer

Environment Parser
-----------------------------------

.. autofunction:: read_item
.. autofunction:: unclosed_env_handler
.. autofunction:: read_math_env
.. autofunction:: read_skip_env
.. autofunction:: read_env

Argument Parser
-----------------------------------

.. autofunction:: read_args
.. autofunction:: read_arg_optional
.. autofunction:: read_arg_required
.. autofunction:: read_arg

Command Parser
-----------------------------------

.. autofunction:: peek_command
