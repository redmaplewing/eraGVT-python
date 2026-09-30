"""口上／地の文的文字來源介面。

原作所有口上都經 `口上/口上システム関係/KOJO_ROOT.ERB@KOJO_ROOT(口上番號, 代碼)` 派發，
找不到對應函式時回傳 -1，由呼叫端回落地の文。`call_kojo` 對應其中 :46–90 的派發部分
（気絶・結界的判定在 `eragvt.game.action.kojo_root_full`），可寫入 TextOutput、讀寫 GameState。
`run_function` 執行地の文等 ERB 函式（可執行時 True；否則呼叫端輸出佔位）。
`run_function_gen` 是其 generator 版（S14）：函式內有 INPUTS 時以 `yield` 取得輸入（`value = yield`），回傳值同上。
實作：`eragvt.narration.service.CatalogNarrationService`（原作 ERB 抽取）、`NullNarrationService`（無 catalog）。
"""

from __future__ import annotations

from typing import Any, Generator, Optional, Protocol


class NarrationService(Protocol):
    def call_kojo(self, ctx: Any, c_no: int, code: str) -> int:
        """KOJO_ROOT.ERB:46–90。回傳 -1 = 找不到；999 = 口上的特殊回傳值；其他 = 輸出行數。"""
        ...

    def run_function(self, ctx: Any, name: str, args: Optional[list] = None, hooks: Optional[dict] = None) -> bool:
        """執行 ERB 函式 `name`（地の文等）。不可執行（或不存在）時不做任何事並回傳 False。"""
        ...

    def run_function_gen(
        self, ctx: Any, name: str, args: Optional[list] = None, hooks: Optional[dict] = None
    ) -> Generator[None, Any, bool]:
        """同 `run_function`，但允許 INPUTS（generator；以 `yield from` 呼叫）。"""
        ...


class NullNarrationService:
    """尚無 catalog 時的預設：永遠沒有口上（KOJO_ROOT.ERB:46–90 的「見つからない」路徑）。"""

    def call_kojo(self, ctx: Any, c_no: int, code: str) -> int:
        st = ctx.state
        st.flag[62] = 1 if "OTHER_" in code else 0  # :50／:61／:73／:76
        ctx.out.reset_color()  # :55／:66／:84 CATCH 内の RESETCOLOR
        st.flag[900] = 0
        return -1

    def run_function(self, ctx: Any, name: str, args: Optional[list] = None, hooks: Optional[dict] = None) -> bool:
        return False

    def run_function_gen(
        self, ctx: Any, name: str, args: Optional[list] = None, hooks: Optional[dict] = None
    ) -> Generator[None, Any, bool]:
        return False
        yield  # pragma: no cover
