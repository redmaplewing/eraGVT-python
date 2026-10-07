"""原生REPEAT／FOR COUNT；LOCAL／CCOUNT迴圈不使用此工具。"""
from collections.abc import Callable, Iterator
from ..state import GameState


def count_loop(state: GameState, stop: int | Callable[[], int], start: int = 0) -> Iterator[int]:
    """CALL可覆寫共享COUNT；NEXT讀當前值。BREAK呼叫端須先加1。

    RETURN／generator close不執行NEXT，故不可使用finally步進。
    上限若讀COUNT或呼叫函式，傳callable以保持先寫start再求上限。
    reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:
    1731–1744、1997–2023、2054–2161。
    """
    state.count[0] = start
    limit = stop() if callable(stop) else stop
    while state.count[0] < limit:
        yield state.count[0]
        state.count[0] += 1
