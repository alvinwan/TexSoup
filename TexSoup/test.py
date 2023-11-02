import TexSoup as TS
import pandas as pd

min_example = r"$ t \in [0,1] $$ t \in [0,1] $"

# min_example = r"\( t \in [0,1] \)\( t \in [0,1] \)"

cats = TS.category.categorize(min_example)

tokens = list(TS.tokens.tokenize(cats))

char_codes = list(TS.category.categorize(min_example))

print(tokens)