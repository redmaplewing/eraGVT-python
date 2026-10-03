"""S29：口上（`ERB/口上/`）から `CALL` される「状態を変える非口上函式」の hook（`narration.hooks.KOJO_CALL_HOOKS`）。

catalog は口上の中の `CALL 名前`（名前が下表）を hook にして、ここの関数を `(ctx, *引数)` で呼ぶ。中身は既存の Python 移植で、
ERB の戻り値（RESULT:0）だけをここで合わせる：
- `RETURN 値` → RESULT:0 = 値（`GameProc/Function/Instraction.Child.cs@RETURN_Instruction`:2006–2023）。
- 函式末尾まで流れ落ち／引数なし RETURN → RESULT = 0（`GameProc/Process.ScriptProc.cs`:61–67）。
"""

from __future__ import annotations

from .action import Ctx


def hook_levelstatus(ctx: Ctx, arg: int = 0) -> None:
    """`汎用関数/コモン関数.ERB@LEVELSTATUS, ARG = 0`:885–894（RETURN なし → RESULT = 0）。
    呼び出し元：`口上/固有キャラ専用口上/kojo_131_ホムラ.ERB`:414 等の `CALL LEVELSTATUS, TARGET`。"""
    from .chara_common import level_status

    level_status(ctx.data, ctx.state, arg)
    ctx.state.result[0] = 0


def hook_transform(ctx: Ctx, arg: int = 0, who: int = -999) -> None:
    """`ゲーム内_戦闘処理/COMMON_BATTLE_FUNC.ERB@TRANSFORM, ARG, ARG:1 = -999`:426–608（RETURN 0／RETURN 1）。
    呼び出し元：`kojo_106_天野美沙緒.ERB`:302 等の `CALL TRANSFORM, 1`。"""
    from .battle.func import transform

    ctx.state.result[0] = transform(ctx, arg, who)


def hook_perform_cheers_hate(ctx: Ctx) -> None:
    """`ゲーム内_イベント発生/戦闘イベント.ERB@PERFORM_CHEERS_HATE`:309–387（引数なし RETURN／流れ落ち → RESULT = 0）。
    呼び出し元：`kojo_158_森亜るるか.ERB`:701／714／727／740。"""
    from .battle.cheers import perform_cheers_hate

    perform_cheers_hate(ctx)
    ctx.state.result[0] = 0
