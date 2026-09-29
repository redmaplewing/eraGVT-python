"""文字輸出層與敘事介面。"""

from .narration import NarrationService, NullNarrationService
from .output import Line, Segment, TextOutput, split_buttons

__all__ = ["Line", "NarrationService", "NullNarrationService", "Segment", "TextOutput", "split_buttons"]
