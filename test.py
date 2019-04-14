from TexSoup import TexSoup, TexNode

soup = TexSoup('This is a formula: $x<y$.')

for s in soup:
    if isinstance(s, TexNode):
        if s.name == '$':
            content = list(s.contents)[0]
            s.replace(content)
