"""開局遊戲說明：ERB/ゲーム内_イベント発生/オープニング処理.ERB@TUTORIAL:454–581。"""
from collections.abc import Generator

from ..state import GameState
from ..text import TextOutput
from .input_request import WaitInputRequest
from .tutorial_text import TEXT

Menu = Generator[None | WaitInputRequest, int | str, int]
# 各章 PRINTL 範圍與末尾 PRINTW 行號；跳過 :480–482 已註解的文字。
CHAPTERS = {0: (469, 479, 483), 1: (486, 500, 501),
            2: (504, 515, 516), 3: (519, 539, 540)}


def _show(out: TextOutput, first: int, last: int) -> None:
    for line in range(first, last+1):
        out.printl(TEXT[line])


def _number(state: GameState, out: TextOutput) -> Generator[None, int, int]:
    # reference/emuera-1824/Emuera/GameProc/Process.cs:249–252：只寫 RESULT:0。
    value = yield
    state.result[0] = value
    out.printl(str(value))
    return value


def _wait(out: TextOutput, line: int) -> Generator[WaitInputRequest, int | str, None]:
    # PRINTW 換行並等待；不是 INPUTS，不寫 RESULTS。
    # reference/emuera-1824/Emuera/GameData/Expression/ExpressionMediator.cs:50–65；
    # GameView/EmueraConsole.cs:497–508、701–734（非數值／字串輸入不寫結果）。
    out.printw(TEXT[line])
    out.printl("（按 Enter 繼續）")
    yield WaitInputRequest()
    out.clearline(1)


def tutorial(state: GameState, out: TextOutput) -> Menu:
    """原作 :455–580；無效輸入只重等，讀完章節才重印選單。"""
    while True:
        _show(out, 456, 465)
        while True:
            value = yield from _number(state, out)
            if value == 999:
                # :578 RETURN 999，保留 RESULT／RESULTS 其他格。
                state.result[0] = 999
                return 999
            if value in CHAPTERS or value == 4:
                break
        if value in CHAPTERS:
            first, last, wait_line = CHAPTERS[value]
            _show(out, first, last)
            yield from _wait(out, wait_line)
            continue
        _show(out, 543, 558)
        while True:
            value = yield from _number(state, out)
            if value in (1, 99):
                break
        if value == 99:
            continue
        _show(out, 566, 574)
        yield from _wait(out, 575)
