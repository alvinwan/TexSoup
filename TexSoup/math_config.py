from typing import Optional

class MathModeTracker:
    in_math_mode: bool = False
    math_mode_type: Optional[None] = None # [None, Inline, Display]

    def __init__(self):
        pass
    
    # def enter_math_mode(self, mode_type):
    #     in_math_mode = True
    #     math_mode_type = mode_type

    # def exit_math_mode(self):
    #     self.in_math_mode = False
    #     self.math_mode_type = None