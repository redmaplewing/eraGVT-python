"""口上／地の文的文字來源介面。

原作所有口上都經 `口上/口上システム関係/KOJO_ROOT.ERB@KOJO_ROOT(口上番號, 代碼)` 派發，
找不到對應函式時回傳 -1，由呼叫端回落地の文。這裡以同樣的介面抽象：
回傳 `None` = 沒有這段口上。S07 的 catalog、之後的 AI 敘事都實作這個 Protocol。
"""

from __future__ import annotations

from typing import Protocol


class NarrationService(Protocol):
    def narrate(self, kojo_no: int, code: str, seikaku: int | None = None) -> str | None:
        """`kojo_no` = CFLAG:6；`code` = 如 "FIRST"、"TURNEND"；`seikaku` = 汎用口上的性格番號。"""
        ...


class NullNarrationService:
    """尚無 catalog／AI 時的預設：永遠沒有口上。"""

    def narrate(self, kojo_no: int, code: str, seikaku: int | None = None) -> str | None:
        return None
