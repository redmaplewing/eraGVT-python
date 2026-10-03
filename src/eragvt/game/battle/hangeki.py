"""[反撃]スタイルの反撃（S23）：`ゲーム内_戦闘処理/HANGEKI_STYLE.ERB@HANGEKI_TO_TENTACLE`:1–104。

路徑相對 `source/earGVP/ERB/`。呼び出し元は `ENEMY_ACTION.ERB`:933–934（`enemy._enemy_action_once` の非拘束分岐の末尾）。

注意（原作どおり）：
- 反撃成功時に設定されるのは `体勢：ＥＸ反撃`（301、:56）であり、`体勢：反撃成功`（302、`DIM.ERH`:205）は本作のどこでも
  代入されない（全域 grep：`TCVARn:2` への代入 口上以外 201 行・口上 99 行に 302／反撃成功 は 0 件）。したがって
  `COM_ATTACK_COMMON.ERB`:38 の `MESSAGE_BATTLE_CHARA_ATTACK_HANGEKI`、`FIGHT_STYLE.ERB`:107 の「反撃成功時の攻撃力」は到達しない。
- 反撃の攻撃は `COM_ATTACK_COMMON` をそのまま呼ぶ（:70）。その末尾（:417–426）で [反撃]スタイルなら再び `体勢：反撃` になる。
"""

from __future__ import annotations

from collections.abc import Generator

from ..action import Ctx, print_transcallname, sengiup
from .core import BETOBETO, P_EX_HANGEKI, t, tc


def hangeki_to_tentacle(ctx: Ctx, arg: int, arg1: int, arg2: int) -> Generator[None, int, int]:
    """`@HANGEKI_TO_TENTACLE, ARG, ARG:1, ARG:2`。S28a：SENGIUP の戦闘基礎 Lv5（INPUT あり）のためジェネレータ。

    ARG = 敵の選んだコマンド（TFLAG:10）、ARG:1 = 敵コマンドの成否（0 攻撃成功、1 回避／カス当たり、2 範囲外回避）、
    ARG:2 = そのターンに反撃で軽減・無効化したダメージ（ENEMY_ACTION の LOCAL:2）。
    """
    from .commands import com_attack_common  # commands → hantei …（循環を避けて遅延 import）

    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    # :9–14 範囲外回避は、空中にいて自分の距離が攻撃範囲内（エアストライクで回避）のときだけ反撃できる
    if arg1 == 2:
        f = st.tflag[11]
        if not (v.get_bit(216, 1) and ((v[0] == 1 and (f & 1)) or (v[0] == 2 and (f & 2)) or (v[0] == 3 and (f & 4)))):
            return 0
    # :19–20 完全防御（TCVARn:200）なら各コマンドの条件を飛ばして成功
    if not v[200] > 0:
        # :25–52
        if arg == 4:  # 距離をとる：確定失敗
            return 0
        if arg in (2, 3, 5, 6) and arg1 == 0:  # 絡みつく・体液・押し倒す・波動：被弾時は失敗
            return 0
    # :56 反撃成功（代入されるのは 体勢：ＥＸ反撃）
    v[2] = P_EX_HANGEKI
    # :58–64
    out.printl()
    out.set_bold(True)
    out.set_color((0, 255, 150))
    out.printl("********** 自分の行動 **********")
    out.reset_color()
    out.set_bold(False)
    out.printl()
    v[205] += arg2  # :67 防いだ被害を蓄積
    com_attack_common(ctx)  # :70
    # :73–88 戦技経験
    if t(ctx, c, "変身能力") != -1:
        exp_name, kind = {1: ("近距離戦闘経験", 0), 2: ("中距離戦闘経験", 1), 3: ("遠距離戦闘経験", 2)}.get(v[0], (None, None))
        if exp_name is not None:  # SELECTCASE TCVARn:0 に CASEELSE なし
            c.exp[ctx.data.index_of("EXP", exp_name)] += st.rng.rand(5) + 1
            yield from sengiup(ctx, st.target, kind)
    else:
        c.exp[ctx.data.index_of("EXP", "戦闘基礎経験")] += st.rng.rand(5) + 1
        yield from sengiup(ctx, st.target, 3)
    c.ex[99] += 2  # :91 EX:行動ポイント
    # :94–102 べとべと：ＥＸ反撃による完全防御で確定回復（距離をとる以外）
    if (v[12] & BETOBETO) and v[200] > 0 and st.tflag[10] != 4:
        name = print_transcallname(st, st.target)
        out.printl(f"○ {name}は纏わり付いた粘液を振り払った！")
        out.printl(f"　 {name}は[べとべと]状態から回復した！")
        out.printw()
        v[12] -= BETOBETO
    return 0
