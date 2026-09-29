"""文字輸出層與敘事介面。"""

from .narration import NarrationService, NullNarrationService
from .output import Line, Part, Segment, TextOutput, split_buttons

__all__ = ["Line", "NarrationService", "Part", "NullNarrationService", "Segment", "TextOutput", "split_buttons"]
