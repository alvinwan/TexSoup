from typing import Optional

class MathModeTracker:
    in_math_mode: bool = False
    math_mode_type: Optional[None] = None # [None, Inline, Display]

    def __init__(self):
        pass

