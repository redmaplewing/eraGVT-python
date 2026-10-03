"""INPUTS 的等待標記，沿用既有 generator／catalog 巢狀輸入通道。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TextInputRequest:
    pass


def inputs(ctx):
    """無預設的 INPUTS：空字串也交回 ERB 呼叫端，不去除空白。

    reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:722–733、
    GameProc/Process.cs:257–260：只寫 RESULTS:0，不碰 RESULT／RESULTS 其他格。
    """
    value = str((yield TextInputRequest()))
    ctx.state.results[0] = value
    ctx.out.printl(value)
    return value


def input_number(ctx):
    """Process.cs:249–252：INPUT 只寫 RESULT:0。"""
    value = yield
    ctx.state.result[0] = value
    return value
