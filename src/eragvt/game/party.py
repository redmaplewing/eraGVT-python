"""隊伍整理與救出後處理（路徑相對 `source/earGVP/ERB/`）。

- `ヒロイン関連/SET_PARTYMEMBER.ERB@SET_PARTYMEMBER`:1–28、`@SHIFTBACK_CHARA`:32–44。
  `@SHIFTFOWARD_CHARA`（:48–64）は全 ERB に呼び出し元が無い（`grep -rn SHIFTFOWARD_CHARA` は定義行のみ）ので移植しない。
- `ヒロイン関連/AFTER_RESCUED.ERB@AFTER_RESCUED`:3–61、`ヒロイン関連/RECOVER_TO_PARTY.ERB@RECOVER_TO_PARTY`:1–23。
- `汎用関数/CHARANUM.ERB@CHARANUM_HOPE`:81–88。

引擎語意：
- `SWAPCHARA x, y` はキャラリストの 2 要素を入れ替えるだけで TARGET／ASSI／MASTER は調整しない
  （`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs@SwapChara`:1165–1174；
  TARGET 等を追従させるのは SORTCHARA のみ：同:1176–）。FLAG:798 など index を持つ変数も変わらない。
- `SWAP a, b` は 2 変数の値の入れ替え（`GameProc/Process.ScriptProc.cs`:341–366、添字を先に確定）。
- `VARSET LOCAL` は LOCAL 全体を 0（`GameProc/Function/ArgumentBuilder.cs`:1352–1369、`Instraction.Child.cs`:1124–1165）。
"""

from __future__ import annotations

from ..state import GameState
from ..state.constants import PARTY_MAX, ActionPlan, CharaState, GameOption
from .action import Ctx
from .opening import game_option
from .shop import charanum_active, charanum_safe_partycheck, check_gameover, check_pregnant


def shiftback_chara(ctx: Ctx, arg: int) -> None:
    """`@SHIFTBACK_CHARA, ARG`:32–44：ARG 番目のキャラを最後尾へ（RELATION の列も入れ替える）。"""
    st = ctx.state
    n = st.charanum
    for local in range(arg, n - 1):  # :34 FOR LOCAL, ARG, CHARANUM - 1
        if local == GameState.MASTER:
            continue
        for l1 in range(n):  # :38–42
            if l1 == GameState.MASTER:
                continue
            rel = st.charas[l1].relation
            rel[local], rel[local + 1] = rel[local + 1], rel[local]
        st.swap_chara(local, local + 1)  # :43


def set_partymember(ctx: Ctx) -> None:
    """`@SET_PARTYMEMBER`:1–28。

    :22–24 で離脱キャラを最後尾へ送った後も FOR は CCOUNT + 1 に進むので、繰り上がって CCOUNT に来たキャラは
    この回の判定を受けない（原作どおり）。
    """
    st, data, out = ctx.state, ctx.data, ctx.out
    if st.charanum < 3 and charanum_safe_partycheck(st) == 0:  # :4–5
        st.flag[63] = 0
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        c = st.charas[i]
        if game_option(st, GameOption.SOLO) or check_gameover(st):  # :10
            pass
        elif check_pregnant(data, st, i) and c.cflag[100] == ActionPlan.SORTIE and c.cflag[0] < 1:  # :12–15
            out.printl(f"{c.callname}は妊娠しているため出撃できなくなりました")
            out.printw()
            c.cflag[100] = ActionPlan.REST
        elif check_pregnant(data, st, i) and c.cflag[100] == ActionPlan.DEFENSE:  # :16–19
            out.printl(f"{c.callname}は妊娠しているため防衛できなくなりました")
            out.printw()
            c.cflag[100] = ActionPlan.REST
        if c.cflag[0] != CharaState.SAFE and i < st.charanum - 1 and c.cflag[999]:  # :22–24
            c.cflag[999] = 0
            shiftback_chara(ctx, i)
        elif c.cflag[0] != CharaState.SAFE and c.cflag[999]:  # :25–26
            c.cflag[999] = 0


def charanum_hope(st: GameState) -> int:
    """`@CHARANUM_HOPE`:81–88：CHARANUM-1 から 洗脳(2)／悪堕ち(3)／死亡(9) を引いた数。"""
    return (st.charanum - 1) - sum(1 for c in st.charas[1:] if c.cflag[0] in (2, 3, 9))


def recover_to_party(ctx: Ctx, who: int) -> None:
    """`@RECOVER_TO_PARTY, ARG`:1–23。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[who]
    c.cflag[0] = CharaState.SAFE
    if charanum_active(st) < PARTY_MAX and c.cflag[999] == 0:  # :5
        c.cflag[999] = 1
        out.printl()
        if c.talent[data.index_of("TALENT", "繁殖袋")] == 1:
            out.printl(f"{c.callname} は生命監視機能の付いた自室に戻されました")
            out.printl("慣れ親しんだ環境が理性を取り戻す助けになると良いのですが...")
        elif c.talent[data.index_of("TALENT", "四肢欠損")] == 1:
            out.printl(f"{c.callname}がパーティメンバーに加わりました")
            out.printl(f"ただし、今の{c.callname}に提供できるのは後方支援だけです...")
        else:
            out.printl(f"{c.callname}がパーティメンバーに加わりました")
        out.printw()
    else:
        out.printl()
        out.printl(f"{c.callname}が控えメンバーに加わりました")
        out.printw()


def after_rescued(ctx: Ctx, who: int) -> None:
    """`@AFTER_RESCUED, ARG`:3–61。

    :23 は `CFLAG:32` ではなく `FLAG:32 = 0` と書かれている（原作どおり FLAG:32 を 0 にし、CFLAG:32 は残る）。
    """
    from .battle.after import event_battle_reset_costume
    from .battle.func import transform
    from .era import div
    from .tattoo import save_tattoo, tattoo_access

    st, data, out = ctx.state, ctx.data, ctx.out
    saved = st.target  # :5 LCOUNT = TARGET（#DIM LCOUNT）
    st.target = who
    c = st.charas[who]
    tal = lambda n: c.talent[data.index_of("TALENT", n)]  # noqa: E731
    event_battle_reset_costume(ctx, st.target)  # :9
    out.printl()
    out.printl(f"{c.callname}は治療を受けています・・・")
    transform(ctx, 0)  # :14
    c.cflag[100] = ActionPlan.REST  # :16
    result = int(tattoo_access(ctx, "PROGRESS_VAR"))  # :19
    if tal("完堕ち") != 1:  # :20–21
        result = div(result * 7, 10)
    if result == 0:  # :22–26
        st.flag[32] = 0
    else:
        save_tattoo(ctx, result)
    if (c.cflag[80] >> 2) & 1 == 1:  # :29–30
        from .corruption import recover_corruption

        recover_corruption(ctx, who)
    if check_pregnant(data, st, who):  # :32–36
        out.printl("妊娠していたため、大事を取って特別病棟に移りました・・・")
        out.printl()
        c.cflag[0] = CharaState.BEFORE_BIRTH
        set_partymember(ctx)
    elif tal("繁殖袋") == 1:  # :37–42
        out.printl("完全に意識不明で、いつ回復するかも分かりません・・・")
        out.printl()
        out.printl()
        c.cflag[0] = 0
        recover_to_party(ctx, who)
    elif tal("四肢欠損") == 1:  # :43–48
        out.printl("全く動くことができず、今後の生活がどうなるかわかりません。・・・")
        out.printl("もしかしたら触手を使った研究の成果で復元できるかも？")
        out.printl()
        c.cflag[0] = 0
        recover_to_party(ctx, who)
    elif tal("完堕ち") > 0:  # :49–54
        out.printl("妙な事を言ったり、奇妙な名前を名乗ったりしています")
        out.printl("目の前にいるのは本当に同一人物なのでしょうか…")
        out.printl()
        c.cflag[0] = 0
        recover_to_party(ctx, who)
    else:  # :55–60
        out.printl("幸い命に別条はないようです・・・")
        out.printl()
        c.cflag[0] = CharaState.SAFE
        recover_to_party(ctx, who)
    st.target = saved  # :61
