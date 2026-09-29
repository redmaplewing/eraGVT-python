"""可注入、可 seed 的亂數。遊戲邏輯一律透過 `GameRng`，不直接用 `random` 模組。"""

from __future__ import annotations

import random


class GameRng:
    """era 的 `RAND:n` 等亂數來源。不進存檔（讀檔後由呼叫端決定是否重新 seed）。"""

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    def rand(self, n: int) -> int:
        """era `RAND:n`：0 以上 n 未滿的整數。n <= 0 時 era 會出錯，這裡丟 ValueError。"""
        if n <= 0:
            raise ValueError(f"RAND 的上限必須為正：{n}")
        return self._random.randrange(n)

    def percent(self, p: int) -> bool:
        """常見寫法 `RAND:100 < p`。"""
        return self.rand(100) < p


class FixedRng(GameRng):
    """測試用：依序回傳預先給定的值（對 `rand(n)` 取 `值 % n`），用完即報錯。"""

    def __init__(self, values: list[int]) -> None:
        super().__init__(0)
        self._values = list(values)

    def rand(self, n: int) -> int:
        if n <= 0:
            raise ValueError(f"RAND 的上限必須為正：{n}")
        if not self._values:
            raise RuntimeError("FixedRng 的預設值已用完")
        return self._values.pop(0) % n
