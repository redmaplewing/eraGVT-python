"""S30：catalog から呼ばれる非口上の小さな ERB 函式の Python 実装（`runtime_support.PY_FUNCTIONS` に名前を登録、
`service._interp` で py_functions に入れる）。状態の書き込みは `StateJournal` に記録する（失敗時に戻せる）。

- `汎用関数/RANDCHOOSE.ERB`：ADDRANDCHOOSE・CLEARRANDCHOOSE（ARG = 0 のみ）・RANDCHOOSE_F・CHOICECOUNT_F。
  候補リスト RANDCHOOSE_NUM（`DIM.ERH`:13、SAVEDATA なし）は Python 移植と共用の `GameState.temp.randchoose`
  （`eragvt.game.battle.core.add_randchoose` 等と同じ配列）。
- `ERB/インターミッション画面/SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT`：共用成就取得與保存。
"""

from __future__ import annotations

from typing import Any

from .runtime import ErbRuntimeError, NotSupported

RANDCHOOSE_MAX = 1000000  # DIM.ERH:12 `#DIM CONST RANDCHOOSE_MAX = 1000000`


def _arg(args: list, i: int, default: Any = 0) -> Any:
    return args[i] if i < len(args) and args[i] is not None else default


def _rc_for_write(it):
    """RANDCHOOSE_NUM を書く前に配列を複製して差し替える（ジャーナルは差し替えを記録 → 失敗時は元の配列に戻る）。"""
    st = it.st
    it.journal.set_attr(st.temp, "randchoose", st.temp.randchoose.copy())
    return st.temp.randchoose


def py_addrandchoose(it, args: list) -> int:
    """`@ADDRANDCHOOSE(ARG)`:3–21。負の ARG はエラー表示（PRINTW）して RETURN。空き（0）の添字を RANDCHOOSE_NUM:0+1 から探して
    ARG+1 を入れ、RANDCHOOSE_NUM:0 をその添字にする。RETURN／流れ落ち → RESULT = 0（Process.ScriptProc.cs:61–67）。"""
    arg = _arg(args, 0)
    if arg < 0:  # :5–9
        it.out.printw("ERROR 候補に負の数を指定することはできません")
        it._set_result([0])
        return 0
    rc = _rc_for_write(it)
    rc[0] += 1  # :10
    hoge = rc[0]  # :11
    while True:  # :12–20 $LOOP
        if rc[hoge] == 0:
            rc[hoge] = arg + 1
            break
        if hoge < RANDCHOOSE_MAX:
            hoge += 1
            if hoge >= RANDCHOOSE_MAX:
                raise ErbRuntimeError("RANDCHOOSE_NUM の添字が範囲外")  # 次の RANDCHOOSE_NUM:HOGE が要素数を超える
            continue
        it.out.printw("ERROR ADDRANDCHOOSE の候補が多すぎます")  # pragma: no cover（上で範囲外になる）
        break
    rc[0] = hoge  # :21
    it._set_result([0])
    return 0


def py_clearrandchoose(it, args: list) -> int:
    """`@CLEARRANDCHOOSE(ARG = 0)`:52–61。ARG == 0 → VARSET RANDCHOOSE_NUM。ARG ≠ 0（ARRAYSHIFT）は catalog から使われないので未対応。"""
    arg = _arg(args, 0)
    if arg != 0:
        raise NotSupported("CLEARRANDCHOOSE（ARG ≠ 0：ARRAYSHIFT）")
    st = it.st
    it.journal.set_attr(st.temp, "randchoose", type(st.temp.randchoose)())
    it._set_result([0])
    return 0


def py_randchoose_f(it, args: list) -> int:
    """`@RANDCHOOSE_F()`（#FUNCTION）:39–47：`RAND:(RANDCHOOSE_NUM:0)` + 1 の位置の値 - 1。RAND:0 は引擎エラー。"""
    rc = it.st.temp.randchoose
    n = rc[0]
    if n <= 0:
        raise ErbRuntimeError("RAND の引数が 0 以下")
    local = it.st.rng.rand(n) + 1
    return rc[local] - 1


def py_choicecount_f(it, args: list) -> int:
    """`@CHOICECOUNT_F()`（#FUNCTION）:78–81。"""
    return it.st.temp.randchoose[0]


def py_unlock_achievement(it, args: list) -> int:
    """ERB/インターミッション画面/SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT:6–20。
    首次取得包含持久化副作用，標記不可回滾，不能因後續 catalog 錯誤偷偷重放或撤銷。
    """
    from ..game.achievements import unlock
    from ..game.opening import game_option
    from ..state.constants import GameOption
    ctx = it.env.ctx
    num = _arg(args, 0)
    if not game_option(ctx.state, GameOption.NO_ACHIEVEMENT_END) and ctx.globals.mem.global_[num] == 0:
        it.journal.irreversible += 1
        it.side_effects += 1
    unlock(ctx, num, _arg(args, 1, ""))
    it._set_result([0])
    return 0


def py_mob_901_getname(it, args: list) -> int:
    """触手データ/雑魚敵/TENTACLE_MOB_901_天界（セラプー）.ERB@TENTACLE_MOB_901_GETNAME:9–13。"""
    from ..game.config import MOB_NAMES

    if it.st.tflag[17] in (3,5):
        it.journal.set_item(it.st.tflag,17,-1)
    it.st.results[0] = MOB_NAMES[901]
    it._set_result([0])
    return 0


def py_event_cloth_option_3004(it, args: list) -> int:
    """3004 プール奇襲.ERB@BATTLE_EVENT_CLOTH_STATUS_3004:8–79 的 option 邊界。

    info 狀態仍由 game.raid.battle_event_cloth_status 原生處理，不開放整個 ERB 函式。
    CLOTHDATA※イベント専用装備.ERB@CLOTH_CUSTOMIZE_OPTION_DRAW_990／991／992:102–120
    會動態呼叫本函式；OUTER、OUTER_TRANS 及其他 parts 都只清 RESULTS:0。
    落尾 RESULT:0=0：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    """
    if _arg(args, 0, "") != "option":
        raise NotSupported("BATTLE_EVENT_CLOTH_STATUS_3004：僅接 option 顯示")
    it.st.results[0] = ""
    if _arg(args, 1, "") == "INNER":
        variant = it.st.target_chara.cflag[270]
        if variant in (0, 1, 2, 3):
            it.call(f"MESSAGE_EVENT_CLOTH_3004_{variant}", [])
    it._set_result([0])
    return 0


PY_FUNCS = {
    "BATTLE_EVENT_CLOTH_STATUS_3004": py_event_cloth_option_3004,
    "TENTACLE_MOB_901_GETNAME": py_mob_901_getname,
    "ADDRANDCHOOSE": py_addrandchoose,
    "CLEARRANDCHOOSE": py_clearrandchoose,
    "RANDCHOOSE_F": py_randchoose_f,
    "CHOICECOUNT_F": py_choicecount_f,
    "UNLOCK_ACHIEVEMENT": py_unlock_achievement,
}
