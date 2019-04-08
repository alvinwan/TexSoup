Navigation
===================================

Take the following example. Consider the ``\begin{itemize}`` environment:

  >>> tex = r'''
  ... \begin{itemize}
  ...   Floating text
  ...   \item outer text
  ...   \begin{enumerate}
  ...     \item nested text
  ...   \end{enumerate}
  ... \end{itemize}
  ... '''

Here are four different properties for contents in this node:
- ``name``
- ``contents``,
- ``children``, and
- ``descendants`` below::

  >>> soup = TexSoup(tex)
  >>> expr = soup.itemize
  >>> expr.name  # name of document
  'itemize'
  >>> list(expr.contents)
  >>> list(expr.children)
  >>> list(expr.descendants)
