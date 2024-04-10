# from typing import Optional

# class MathModeTracker:
#     in_math_mode: bool = False
#     math_mode_type: Optional[None] = None # [None, Inline, Display]

#     def __init__(self):
#         pass

#     @classmethod
#     def reset(cls):
#         cls.in_math_mode = False
#         cls.math_mode_type = None

from typing import Optional

class MathModeTracker:
    stack = []
    in_math_mode: bool = True
    math_mode_type: Optional[None] = None # [None, Inline, Display]

    def __init__(self):
        pass

    @classmethod
    def enter(cls, cur_mode):
        cls.stack.append(cur_mode)
        cls.in_math_mode = True
        cls.math_mode_type = cur_mode

    @classmethod
    def exit(cls):
        if cls.stack:
            cls.stack.pop()
        # else:
        #     cls.in_math_mode = False
        #     cls.math_mode_type = None

    @classmethod
    def math_mode_track(cls):
        if cls.stack:
            cls.in_math_mode = True
            cls.math_mode_type = cls.stack[-1]
        else:
            cls.in_math_mode = False
            cls.math_mode_type = None

    @classmethod
    def reset(cls):
        cls.in_math_mode = False
        cls.math_mode_type = None
        if cls.stack:
            cls.stack = []