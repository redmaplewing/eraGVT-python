"""自由行動中イベントの本編（S28c2）：ナンパ・酒ナンパ・痴漢。

路徑相對 `source/earGVP/ERB/ゲーム内_イベント発生/自由行動中イベント/`。
- `PASTIME_ナンパ.ERB@MESSAGE_PASTIME_NANPA`:73–605 ＋ `@PASTIME_NANPA_DATE`:607–1760、`@PASTIME_NANPA_TAKEOUT`:1762–3022、
  `@PASTIME_NANPA_RAPE`:3024–3249。
- `PASTIME_酒ナンパ.ERB@MESSAGE_PASTIME_SAKE_NANPA`:74–263 ＋ `@PASTIME_SAKE_NANPA_DATE`:265–647、`@PASTIME_SAKE_NANPA_TAKEOUT`:649–1611、
  `@PASTIME_SAKE_NANPA_RAPE`:1613–1877、`@PASTIME_SAKE_NANPA_DEISUI_RAPE`:1883–2083。
- `PASTIME_痴漢.ERB@MESSAGE_PASTIME_CHIKAN`:470–1191 ＋ `@PASTIME_CHIKAN_TAKEOUT`:1193–1737。

分工：この 11 関数は本文がほぼ全部で、INPUT（選択肢）と少数の状態変化が本文の分岐の中に混ざっている。手翻すると
約 6,800 行の本文を Python に書き写すことになるので、S07 catalog で原文をそのまま実行する（`CatalogNarrationService.run_event_gen`：
INPUT で本当に中断して待つ）。状態変化行は `narration/hooks.py` の `NANPA_HOOK_LINES`（代入は書き込み許可で実行、CALL は下の hook_*
＝既存の Python 移植）。catalog が無い（NullNarrationService）・実行できないときは NotImplementedError（Web 停止）。

RESULT：本編の中で RESULT を読むのは INPUT の直後だけ（`grep RESULT`：他は PASTIME_痴漢.ERB:458 の本編の戻り値のみ）。hook の CALL
は元の関数と同じく RESULT:0 を書く（関数終端 → 0：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs`:61–67。
NINSIN_HANTEI は既存の hook（`battle.ninsin.ninsin_hantei`）で RESULT を書かないが、直後は関数終端か RETURN なので読まれない）。
"""

from __future__ import annotations

from collections.abc import Generator

from .action import Ctx

InputGen = Generator[object, int, None]

_STOP = "自由行動：{}（{}）を catalog で実行できません（原作 ERB が必要）"


def _run(ctx: Ctx, func: str, args: list, label: str) -> Generator[object, int, int]:
    ok = yield from ctx.narration.run_event_gen(ctx, func, args)
    if not ok:
        raise NotImplementedError(_STOP.format(label, func))
    return ctx.state.result[0]


def message_pastime_nanpa(ctx: Ctx, arg: int) -> InputGen:
    """`CALL MESSAGE_PASTIME_NANPA, ARG`（`PASTIME_ナンパ.ERB`:73–605）。ARG は呼び出し元の ARG（0／1 街・遠出、2 運動、3 学校、
    他は :409 の ELSE 側：原作どおり、呼び出し元の ARG は予約内容なので値の対応は S28c1 の actions.md 補足を参照）。"""
    yield from _run(ctx, "MESSAGE_PASTIME_NANPA", [arg], "ナンパ")


def message_pastime_sake_nanpa(ctx: Ctx, arg: int) -> InputGen:
    """`CALL MESSAGE_PASTIME_SAKE_NANPA, ARG`（`PASTIME_酒ナンパ.ERB`:74–263）。"""
    yield from _run(ctx, "MESSAGE_PASTIME_SAKE_NANPA", [arg], "酒ナンパ")


def message_pastime_chikan(ctx: Ctx, arg: int, pos: int, naburare: int, aite: str) -> Generator[object, int, int]:
    """`CALL MESSAGE_PASTIME_CHIKAN, ARG, CHIKAN_POS, NABURARE, 痴漢してきた相手`（`PASTIME_痴漢.ERB`:470–1191）。
    戻り値 = RESULT（:1097 お持ち帰り後 RETURN 1、:482／:1188 RETURN 0）。"""
    return (yield from _run(ctx, "MESSAGE_PASTIME_CHIKAN", [arg, pos, naburare, aite], "痴漢"))


# --- hook（NANPA_HOOK_LINES の CALL 行） --------------------------------------------------------------


def hook_common_prison(ctx: Ctx, *args: int) -> None:
    """`CALL COMMON_PRISON, LOCAL:10〜LOCAL:21, 1`（`ゲーム内_イベント発生/敗北幽閉中イベント/COMMON_PRISON.ERB`:21–38）。"""
    from .prison.commands import common_prison

    common_prison(ctx, list(args[:12]), args[12] if len(args) > 12 else 0)
    ctx.state.result[0] = 0


def hook_common_prison_exp(ctx: Ctx, arg0: int, arg1: int = 0) -> None:
    """`CALL COMMON_PRISON_EXP, CCOUNT, LOCAL:CCOUNT`（同:75–87）。"""
    from .prison.commands import common_prison_exp

    common_prison_exp(ctx, arg0, arg1)
    ctx.state.result[0] = 0


def hook_ablup(ctx: Ctx, arg: int = 0) -> None:
    """`CALL _ABLUP, 1`（`ヒロイン関連/ABL_UP_CHECK.ERB@_ABLUP`）。"""
    from .battle.ablup import ablup

    ablup(ctx, arg)
    ctx.state.result[0] = 0


def hook_after_pill(ctx: Ctx, who: int, arg1: int, arg2: int = 0):
    """`CALL AFTER_PILL, TARGET, 35, 望まない相手`（`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB`:898–957、INPUT → ジェネレータ）。"""
    from .battle.ninsin import after_pill

    yield from after_pill(ctx, who, arg1, arg2)
    ctx.state.result[0] = 0


def hook_calc_gangbang(ctx: Ctx, situation: str, sao: int, nakadashi: int):
    """`CALL CALC_GANGBANG("ナンパ",3,NAKADASHI)`（`ゲーム内_イベント発生/CALC_GANGBANG.ERB`:3–166、INPUT → ジェネレータ）。"""
    from .battle.rape import calc_gangbang

    yield from calc_gangbang(ctx, situation, sao, nakadashi)
    ctx.state.result[0] = 0


def hook_encount_citizen(ctx: Ctx, *args) -> None:
    """PASTIME_ナンパ.ERB@PASTIME_NANPA_RAPE:3086；酒ナンパ同:1696。"""
    from .battle.citizen import encount_citizen

    encount_citizen(ctx,*args)
