"""敵（触手／洗脳・悪堕ちキャラ）の行動：`ゲーム内_戦闘処理/ENEMY_ACTION.ERB`（非拘束分岐・SELECT_TENTACLE_ACTION・
SELECT_ENEMY_ACTION）と `FORECAST.ERB@ATTACK_PLACE_DECISION`。

悪堕ちキャラ戦（S19）：各地の文の後に `MESSAGE_OTHER_BATTLE_TENTACLE_*`（敵キャラ側の口上、`core.msg_other`）、
押し倒す（TFLAG:10 = 5）・邪悪な波動（6）、拘束中は ENEMY_ACTION_SEX_ROUTINE の悪堕ち分岐（:947–964、再行動なし）。

路徑相對 `source/earGVP/ERB/`。拘束中の性攻撃（SEX_ROUTINE／SEX_COM）は S06、反撃（HANGEKI_TO_TENTACLE）は S23（`hangeki.py`）。
地の文は `地の文/MESSAGE_BATTLE.ERB`（行番号は各関数の docstring）。
"""

from __future__ import annotations

from ..counting import count_loop

from collections.abc import Generator

from ..action import Ctx, kojo_root, print_transcallname
from ..chara_common import is_female
from ..era import div, isqrt, limit, times
from ..opening import game_option
from ...state.constants import GameOption
from ..tentacle import enemy_type_check
from .cheers import perform_cheers_tentacle_hit_hantei, perform_cheers_tentacle_miss_hantei
from .cloth import INNER_PER, OUTER_PER, cloth_battle_damage, cloth_battle_hosei
from .core import (
    KIZETU,
    P_EX_HANGEKI,
    P_GUARD,
    P_HANGEKI,
    P_NOTHING,
    P_V_GUARD,
    abl,
    config_check_balance,
    fstyle_name,
    msg_other,
    percent_cal,
    print_enemy_prefix,
    shinkyou_change,
    shinkyou_check,
    t,
    tc,
    tentacle_access,
    tentacle_level,
)
from .func import (
    calc_chisei_shien,
    cheers_enabled,
    get_counter_attack,
    state_change_betobeto,
    state_change_extraeffect,
    state_change_hairan,
    state_change_kizetu_damage,
)
from .hangeki import hangeki_to_tentacle
from .hantei import act_hantei_tentacle_to_chara, damage
from .palam import palam_cal
from .sexmsg import istentacler


def _enemy_prefix(ctx: Ctx) -> None:
    print_enemy_prefix(ctx)


def _other(ctx: Ctx, name: str) -> None:
    """`SIF ENEMY_TYPE_CHECK_F("AKUOTI") / CALL MESSAGE_OTHER_BATTLE_TENTACLE_{name}`。"""
    if enemy_type_check(ctx.state, "AKUOTI"):
        msg_other(ctx, f"BATTLE_TENTACLE_{name}")


def _range_marks(ctx: Ctx) -> None:
    """攻撃範囲の表示「（近中遠）対空」（MESSAGE_BATTLE.ERB:1096–1116 等）。"""
    out = ctx.out
    f = ctx.state.tflag[11]
    out.print("（")
    out.print("近" if f & 1 else "　")
    out.print("中" if f & 2 else "　")
    out.print("遠" if f & 4 else "　")
    out.print("）")
    out.print("対空" if f & 8 else "　　")
    out.printl()


def _style_hit_note(ctx: Ctx) -> None:
    """ATTACK_CRITICAL_HIT／HIT／TAIEKI_HIT 冒頭のスタイル文（:1126–1132）。"""
    st = ctx.state
    style = fstyle_name(ctx, st.target, tc(ctx).tcvarn[0])
    name = print_transcallname(st, st.target)
    if style == "撹乱" or (tc(ctx).tcvarn.get_bit(217, 0) and style == "全力"):
        ctx.out.printl(f"{name}は防御に不安のある体勢で直撃を受けてしまった！")
        ctx.out.printl()
    elif style == "装甲":
        ctx.out.printl(f"{name}は咄嗟に身構え、ダメージを軽減した！")
        ctx.out.printl()


def _colored(ctx: Ctx, color: tuple[int, int, int], text: str, bold: bool = False) -> None:
    out = ctx.out
    out.set_color(color)
    if bold:
        out.set_bold(True)
    out.printl(text)
    if bold:
        out.set_bold(False)
    out.reset_color()


def msg_tentacle_attack(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_ATTACK`:1081–1122（ボスには MESSAGE_BATTLE_MOB_{n}_TENTACLE_ATTACK が無い）。"""
    st = ctx.state
    if enemy_type_check(st, "MOB") == 1:
        from .mob import message

        if message(ctx,f"MESSAGE_BATTLE_MOB_{st.flag[11]}_TENTACLE_ATTACK"):
            return
    _enemy_prefix(ctx)
    ctx.out.print({1: "の攻撃！", 2: "の二点同時攻撃！"}.get(st.tflag[12], "の全方位攻撃！"))
    _range_marks(ctx)
    kojo_root(ctx, "BATTLE_TENTACLE_ATTACK")
    ctx.out.printl()


def msg_simple_hit(ctx: Ctx, code: str, critical: bool = False) -> None:
    """ATTACK_CRITICAL_HIT（:1125–1140）／ATTACK_HIT（:1143–1156）／TAIEKI_HIT（:1373–1386）。"""
    _style_hit_note(ctx)
    if critical:
        _colored(ctx, (255, 0, 0), "CRITICAL HIT!", bold=True)
    else:
        _colored(ctx, (255, 255, 0), "HIT!")
    kojo_root(ctx, code)
    ctx.out.printl()


def msg_miss(ctx: Ctx, text: str, code: str) -> None:
    """ATTACK_FALSE（:1159–1166）／KARAMITUKU_FALSE（:1313–1320）／TAIEKI_FALSE（:1389–1396）。"""
    st = ctx.state
    _colored(ctx, (255, 0, 255), "MISS!")
    ctx.out.printl(f"{print_transcallname(st, st.target)}{text}")
    kojo_root(ctx, code)
    ctx.out.printl()


def msg_graze(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_ATTACK_GRAZE`:1169–1176。"""
    st = ctx.state
    _colored(ctx, (0, 255, 255), "GRAZE!")
    ctx.out.printl(f"{print_transcallname(st, st.target)}は紙一重で攻撃を回避したが、衣装の一部を引き裂かれた！")
    kojo_root(ctx, "BATTLE_TENTACLE_ATTACK_GRAZE")
    ctx.out.printl()


def msg_guard(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_ATTACK_GUARD`:1179–1198。"""
    st = ctx.state
    name = print_transcallname(st, st.target)
    _colored(ctx, (0, 255, 255), "GUARD!")
    if fstyle_name(ctx, st.target, tc(ctx).tcvarn[0]) == "反撃":
        ctx.out.printl(f"{name}は攻撃を防いでから、待っていたかのようにすぐ次の攻撃を仕掛けた！")
    else:
        ctx.out.print(f"{name}は")
        _enemy_prefix(ctx)
        ctx.out.printl("の攻撃に耐えた！")
    # TRYCCALLFORM KOJO_ROOT(…, "BATTLE_TENTACLE_ATTACK_GUARD") → CATCH は KOJO_ROOT が無い場合のみ（KOJO_ROOT は必ずある）
    kojo_root(ctx, "BATTLE_TENTACLE_ATTACK_GUARD")


def msg_perfect_guard(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_ATTACK_PERFECT_GUARD`:1201–1223。"""
    st = ctx.state
    name = print_transcallname(st, st.target)
    _colored(ctx, (255, 0, 255), "PERFECT GUARD!")
    if fstyle_name(ctx, st.target, tc(ctx).tcvarn[0]) == "反撃":
        # :1206–1209 PRINTDATAL：DATA 2 件から GetNextRand(2) で 1 件（reference/emuera-1824/Emuera/GameProc/Function/
        # Instraction.Child.cs:202–203）、行末で改行（:225–226）
        if st.rng.rand(2) == 0:
            ctx.out.printl(f"{name}は攻撃を完全に封じ込めた後, すぐに敵のすき間に向かって進んだ！")
        else:
            ctx.out.printl(f"{name}はすべての攻撃をかわし, その勢いで反撃に乗り出した！")
    else:
        ctx.out.print(f"{name}は ")
        _enemy_prefix(ctx)
        ctx.out.printl("の攻撃を完全に防ぐことができた！")
    kojo_root(ctx, "BATTLE_TENTACLE_ATTACK_PERFECT_GUARD")


def msg_absence(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_ABSENCE`:1402–1417。"""
    st = ctx.state
    v = tc(ctx).tcvarn
    name = print_transcallname(st, st.target)
    _colored(ctx, (255, 0, 255), "MISS!")
    if v[0] == 0:
        ctx.out.printw("ERROR ! 拘束中に距離不在回避が発生しています！エラー")
    elif v.get_bit(216, 1) and (st.tflag[11] >> (v[0] - 1)) & 1:
        ctx.out.printl(f"{name}は空中でうまく身をかわした！")
    else:
        ctx.out.printl(f"{name}はそこにはいない！")
    kojo_root(ctx, "BATTLE_TENTACLE_ABSENCE")
    ctx.out.printl()


def msg_karamituku(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_KARAMITUKU`:1247–1287。"""
    st = ctx.state
    if enemy_type_check(st, "MOB") == 1:
        from .mob import message

        if not message(ctx,f"MESSAGE_BATTLE_MOB_{st.flag[11]}_KARAMITUKU"):
            raise NotImplementedError("原作 CALLFORM 的雜魚函式不存在")
        return
    if enemy_type_check(st, "CITIZEN") == 1:
        from .mob import message

        message(ctx,"MESSAGE_BATTLE_MOB_1150_KARAMITUKU")
        kojo_root(ctx,"BATTLE_TENTACLE_KARAMITUKU")
        ctx.out.printl()
        return
    _enemy_prefix(ctx)
    if st.tflag[12] == 1:
        ctx.out.print("は触手を伸ばして絡みつこうとしてきた！")
    else:
        ctx.out.print("は広範囲に触手を伸ばして絡みつこうとしてきた！")
    _range_marks(ctx)
    kojo_root(ctx, "BATTLE_TENTACLE_KARAMITUKU")
    ctx.out.printl()


_KARAMI_SUCCESS = (
    "全身を触手に巻き付かれて人外の筋力で壁際に押し付けられる！",
    "触手に吹き飛ばされて壁にぶつかり、地面に倒れたところをズルズルと引き摺られていく！",
    "正面から押し寄せてきた触手の波に飲まれ、その場に押し倒される！",
    "足元から無数の触手が飛び出し、逃げる間もなく全身に絡み付いていく！",
    "素早く伸びた触手が足に絡み付き、そのまま上下逆さまに空高く吊し上げられる！",
)


def msg_karamituku_success(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_KARAMITUKU_SUCCESS`:1290–1310。"""
    st = ctx.state
    if enemy_type_check(st,"CITIZEN") == 1:
        from .mob import message

        message(ctx,"MESSAGE_BATTLE_MOB_1150_KARAMITUKU_SUCCESS")
        kojo_root(ctx,"BATTLE_TENTACLE_KARAMITUKU_SUCCESS")
        ctx.out.printl()
        return
    ctx.out.printl(_KARAMI_SUCCESS[st.rng.rand(5)])
    ctx.out.printl(f"{print_transcallname(st, st.target)}は触手に拘束されてしまった！")
    kojo_root(ctx, "BATTLE_TENTACLE_KARAMITUKU_SUCCESS")
    ctx.out.printl()


def msg_taieki(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_TAIEKI`:1327–1370。"""
    st = ctx.state
    if enemy_type_check(st, "MOB") == 1:
        from .mob import message

        if message(ctx,f"MESSAGE_BATTLE_MOB_{st.flag[11]}_TENTACLE_TAIEKI"):
            return
    _enemy_prefix(ctx)
    ctx.out.print("は大きく身震いすると先端から腐臭のする体液を")
    ctx.out.print({1: "直線状に放ってきた！", 2: "放ってきた！"}.get(st.tflag[12], "広範囲に放ってきた！"))
    _range_marks(ctx)
    kojo_root(ctx, "BATTLE_TENTACLE_TAIEKI")
    ctx.out.printl()


def msg_takeaway(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_TAKEAWAY`:1422–1436。"""
    _enemy_prefix(ctx)
    ctx.out.printl("は一度距離をとって力を温存させているようだ・・・")
    kojo_root(ctx, "BATTLE_TENTACLE_TAKEAWAY")
    ctx.out.printl()


def msg_oshitaosu(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_OSHITAOSU`:1439–1444。"""
    st = ctx.state
    ctx.out.print(print_transcallname(st, st.flag[111]))
    ctx.out.printl(f"は怪しげな足取りで{print_transcallname(st, st.target)}ににじり寄る！")
    kojo_root(ctx, "BATTLE_TENTACLE_OSHITAOSU")
    ctx.out.printl()


def msg_oshitaosu_success(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_OSHITAOSU_SUCCESS`:1447–1451。"""
    st = ctx.state
    ctx.out.printl(f"{print_transcallname(st, st.target)}は{print_transcallname(st, st.flag[111])}に勢い良く押し倒されてしまった！")
    kojo_root(ctx, "BATTLE_TENTACLE_OSHITAOSU_SUCCESS")
    ctx.out.printl()


def msg_oshitaosu_false(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_OSHITAOSU_FALSE`:1454–1461。"""
    st = ctx.state
    _colored(ctx, (255, 0, 255), "MISS!")
    ctx.out.printl(f"危機を感じた{print_transcallname(st, st.target)}はなんとか{print_transcallname(st, st.flag[111])}から距離をとった！")
    kojo_root(ctx, "BATTLE_TENTACLE_OSHITAOSU_FALSE")
    ctx.out.printl()


def msg_hadou(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_HADOU`:1468–1510（TRYCCALLFORM MESSAGE_BATTLE_MOB_{FLAG:11}_TENTACLE_HADOU は
    901／902／803 のみ存在：触手データ/雑魚敵/。雑魚敵は未移植なので停止）。"""
    st = ctx.state
    if enemy_type_check(st, "MOB") == 1:
        from .mob import message

        if message(ctx,f"MESSAGE_BATTLE_MOB_{st.flag[11]}_TENTACLE_HADOU"):
            return
    if enemy_type_check(st, "AKUOTI") == 0:
        tentacle_access(ctx, "NAME")
        ctx.out.print("は邪悪な波動を")
    else:
        ctx.out.print(f"{print_transcallname(st, st.flag[111])}は邪悪な波動を")
    ctx.out.print({1: "直線状に放ってきた！", 2: "放ってきた！"}.get(st.tflag[12], "広範囲に放ってきた！"))
    _range_marks(ctx)
    kojo_root(ctx, "BATTLE_TENTACLE_HADOU")
    ctx.out.printl()


def msg_hadou_false(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_TENTACLE_HADOU_FALSE`:1529–1536。"""
    msg_miss(ctx, "は波動を回避した！", "BATTLE_TENTACLE_HADOU_FALSE")


# --- @ENEMY_ACTION（ENEMY_ACTION.ERB:4–1015）--------------------------------------------


def enemy_action(ctx: Ctx) -> Generator[None, int, None]:
    """`@ENEMY_ACTION`:4–1015。`$LOOP_TOP`（:5）への GOTO（絡みつく成功直後、:380）はループで表す。
    拘束中の性攻撃は AUTO_V_DEFENCE の INPUT を含むのでジェネレータ。"""
    while True:
        again = yield from _enemy_action_once(ctx)
        if not again:
            break
    # :1011–1015
    if enemy_type_check(ctx.state, "AKUOTI"):
        select_enemy_action(ctx)
    else:
        select_tentacle_action(ctx)


def _restraint_sex_akuoti(ctx: Ctx) -> Generator[None, int, None]:
    """:947–964 悪堕ちキャラの拘束中性コマンド（再行動判定なし）。"""
    from .sexcom import enemy_action_sex_routine, sex_comable

    st = ctx.state
    c = tc(ctx)
    while True:  # $ROUTINE_LOOP_0（:949）
        select = enemy_action_sex_routine(ctx)
        r = yield from sex_comable(ctx, select)
        if r == 0:  # :956–959
            st.tflag[17] = -1
            continue
        break
    c.exp[ctx.data.index_of("EXP", "被姦経験")] += 1  # :962
    shinkyou_change(ctx, "TOUSAKU")  # :964


def _restraint_sex(ctx: Ctx) -> Generator[None, int, None]:
    """:969–1009 触手の拘束中性コマンド（再行動判定・SEX_ROUTINE・SEX_COMABLE・連続行動）。"""
    from .sexcom import enemy_action_sex_routine, sex_comable

    st = ctx.state
    out = ctx.out
    c = tc(ctx)
    l3 = 0
    lv = tentacle_level(st)
    # :973–976 `WHILE RAND:100 < min(RESULT,50) && RAND:2`（RESULT は TENTACLE_LEVEL のまま）
    while st.rng.rand(100) < min(lv, 50) and st.rng.rand(2):
        if lv >= 10:
            l3 += 1
    if enemy_type_check(st, "MOB") == 1 and st.rng.rand(2) == 0:  # :978–979
        l3 += 1
    while True:  # $ROUTINE_LOOP_1（:980）
        select = enemy_action_sex_routine(ctx)
        r = yield from sex_comable(ctx, select)
        if r == 0:  # :987–990
            st.tflag[17] = -1
            continue
        c.exp[ctx.data.index_of("EXP", "被姦経験")] += 1  # :993
        if l3 and st.flag[13] > 0:  # :995–1006
            l3 -= 1
            for i in count_loop(st, 4):
                c.ex[i] += c.nowex[i]
            c.nowex.clear()
            out.printw()
            out.set_bold(True)
            out.printl("連続行動！")
            out.set_bold(False)
            out.printl()
            continue
        break
    shinkyou_change(ctx, "TOUSAKU")  # :1009


def _enemy_action_once(ctx: Ctx) -> Generator[None, int, bool]:
    """:5–1009 の 1 回分。`GOTO LOOP_TOP` するときは True を返す。"""
    st = ctx.state
    out = ctx.out
    c = tc(ctx)
    v = c.tcvarn
    loc: dict[int, int] = {}  # VARSET LOCAL（:8）
    if v[2] == P_NOTHING:  # :11–20
        if st.flag[11] == 1150 and v[0] > 1:
            pass
        else:
            st.tflag[10] = 2
            # :16–17 絡みつく場合、寄生なし悪堕ちキャラなら押し倒す
            if enemy_type_check(st, "AKUOTI") and st.tflag[10] == 2 and istentacler(ctx, st.flag[111]) == 0:
                st.tflag[10] = 5
            attack_place_decision(ctx)
    if v[0] <= 0:
        if enemy_type_check(st, "AKUOTI"):  # :947–964
            yield from _restraint_sex_akuoti(ctx)
        else:
            yield from _restraint_sex(ctx)
        return False
    if st.tflag[16] >= 0:  # :25–26
        st.tflag[10] = st.tflag[16]
    action = st.tflag[10]
    name = print_transcallname(st, st.target)
    if action == 1:  # :29–264 攻撃
        msg_tentacle_attack(ctx)
        _other(ctx, "ATTACK")
        r = act_hantei_tentacle_to_chara(ctx, "AVOID_KOUGEKI")
        loc[0] = r
        if r == 1:
            st.tflag[33] += 1
            r2 = act_hantei_tentacle_to_chara(ctx, "AVOID_KOUGEKI")
            if r2 == 0 and st.temp.cloth[OUTER_PER] + st.temp.cloth[INNER_PER] > 0:
                msg_graze(ctx)
                _other(ctx, "ATTACK_GRAZE")
                cloth_battle_damage(ctx, 8)
            else:
                msg_miss(ctx, "は攻撃を回避した！", "BATTLE_TENTACLE_ATTACK_FALSE")
                _other(ctx, "ATTACK_FALSE")
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        elif r == 2:
            if v[2] != P_EX_HANGEKI:
                st.tflag[33] += 1
            msg_absence(ctx)
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        else:
            # :87 完全防御（RAND は短絡評価：ＥＸ反撃なら RAND を引かない）
            if v[2] == P_EX_HANGEKI or (v[2] == P_GUARD and st.rng.rand(100) < 10) or (
                v[2] == P_HANGEKI and st.rng.rand(100) < 7
            ):
                loc[1] = 10
                v[200] = 1
                msg_perfect_guard(ctx)
                _other(ctx, "ATTACK_PERFECT_GUARD")
            # :100 `生粋の戦士 == 0 && (RAND < 5 && 装甲以外) || (RAND < 10 && 反撃)`（左結合）
            elif (t(ctx, c, "生粋の戦士") == 0 and (
                st.rng.rand(100) < 5 and fstyle_name(ctx, st.target, v[0]) != "装甲"
            )) or (st.rng.rand(100) < 10 and v[2] == P_HANGEKI):
                loc[1] = 15
                msg_simple_hit(ctx, "BATTLE_TENTACLE_ATTACK_CRITICAL_HIT", critical=True)
                _other(ctx, "ATTACK_CRITICAL_HIT")
            elif v[2] in (P_GUARD, P_HANGEKI):
                loc[1] = 10
                msg_guard(ctx)
                _other(ctx, "ATTACK_GUARD")
            else:
                loc[1] = 10
                msg_simple_hit(ctx, "BATTLE_TENTACLE_ATTACK_HIT")
                _other(ctx, "ATTACK_HIT")
            l2 = div(damage(ctx, "CHARA") * loc[1], 10)
            l2 = div(l2 * cloth_battle_hosei(ctx, "TAIRYOKU"), 100)
            out.set_bold(True)
            if fstyle_name(ctx, st.target, v[0]) == "反撃":
                out.printl(f"{l2}のダメージを蓄積した！")
            elif v[200] > 0:
                out.printl(f"{l2}のダメージが無効化された！")
            else:
                out.printl(f"{l2}のダメージを受けた！")
            out.printl()
            if v[200] <= 0:  # :191–192 完全防御ならダメージとソースをスキップ
                if c.base[0] - l2 <= 0:
                    l2 = c.base[0]
                c.base[0] -= l2
                pct = div(100 * l2, c.maxbase[0])
                for bound, a8, a10, a11 in ((5, 0, 150, 0), (15, 0, 300, 0), (25, 0, 600, 0), (35, 0, 1000, 200),
                                            (45, 200, 2000, 400), (55, 400, 4000, 1000), (65, 1000, 10000, 2000),
                                            (75, 2000, 20000, 4000)):
                    if pct < bound:
                        loc[8], loc[10], loc[11] = a8, a10, a11
                        break
                else:
                    loc[8], loc[10], loc[11] = 4000, 40000, 10000
                loc[8] += div(l2, 8)
                loc[10] += l2
                loc[11] += div(l2, 4)
            loc[2] = l2
            out.set_bold(False)
            cloth_battle_damage(ctx, div(8 * (loc[1] + div(loc.get(10, 0), 2000)), 10))
            if cheers_enabled(ctx):
                perform_cheers_tentacle_hit_hantei(ctx)
            if v[14] > 0:
                state_change_extraeffect(ctx)
            state_change_kizetu_damage(ctx, l2)
            if v[200] > 0:
                shinkyou_change(ctx, "KOUYOU")
            elif (v[12] & KIZETU) == 0:
                shinkyou_change(ctx, "IKARI_TEIKAN")
    elif action == 2:  # :265–382 絡みつく
        msg_karamituku(ctx)
        _other(ctx, "KARAMITUKU")
        r = act_hantei_tentacle_to_chara(ctx, "AVOID_KARAMITUKU")
        loc[0] = r
        if r == 1:
            st.tflag[33] += 1
            msg_miss(ctx, "は拘束攻撃を回避した！", "BATTLE_TENTACLE_KARAMITUKU_FALSE")
            _other(ctx, "KARAMITUKU_FALSE")
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        elif r == 2:
            if v[2] != P_EX_HANGEKI:
                st.tflag[33] += 1
            msg_absence(ctx)
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        else:
            dmg = times(damage(ctx, "CHARA"), "0.25")
            v[0] = 0
            v[8] = 2
            msg_karamituku_success(ctx)
            _other(ctx, "KARAMITUKU_SUCCESS")
            l2 = div(dmg * cloth_battle_hosei(ctx, "TAIRYOKU"), 100)
            out.set_bold(True)
            out.printl(f"{l2}のダメージを受けた！")
            out.set_bold(False)
            if c.base[0] - l2 <= 0:
                l2 = c.base[0]
            c.base[0] -= l2
            l3 = 25 if v[2] == P_GUARD else 50
            l3 = div(l3 * cloth_battle_hosei(ctx, "KIRYOKU"), 100)
            out.set_bold(True)
            out.printl(f"{ctx.data.names['BASE'].get(1, '')}が{l3}減った！")
            out.set_bold(False)
            out.printl()
            if c.base[1] < l3:
                l3 = c.base[1]
            c.base[1] -= l3
            out.set_bold(True)
            out.set_color((250, 0, 0))
            out.printl(f"{name}は拘束されてしまった！")
            out.reset_color()
            out.set_bold(False)
            cloth_battle_damage(ctx, 8)
            if v[14] > 0:
                state_change_extraeffect(ctx)
            shinkyou_change(ctx, "REISEI_DOUYOU")
            out.printl()
            if abl(ctx, c, "欲望") < 3 and is_female(ctx.data, c) and c.base[0] > 0:
                v[2] = P_V_GUARD
            return True  # :380 GOTO LOOP_TOP → 拘束中の性攻撃
    elif action == 3:  # :383–572 体液を吐く
        msg_taieki(ctx)
        _other(ctx, "TAIEKI")
        r = act_hantei_tentacle_to_chara(ctx, "AVOID_TAIEKI")
        loc[0] = r
        if r == 1:
            st.tflag[33] += 1
            msg_miss(ctx, "は体液を回避した！", "BATTLE_TENTACLE_TAIEKI_FALSE")
            _other(ctx, "TAIEKI_FALSE")
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        elif r == 2:
            if v[2] != P_EX_HANGEKI:
                st.tflag[33] += 1
            msg_absence(ctx)
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        else:
            if (v[2] == P_GUARD and st.rng.rand(100) < 20) or (v[2] == P_EX_HANGEKI and st.rng.rand(100) < 15) or (
                v[2] == P_HANGEKI and st.rng.rand(100) < 7
            ):
                v[200] = 1
                msg_perfect_guard(ctx)
                _other(ctx, "ATTACK_PERFECT_GUARD")
            else:
                msg_simple_hit(ctx, "BATTLE_TENTACLE_TAIEKI_HIT")
                _other(ctx, "TAIEKI_HIT")
            lv = tentacle_level(st)
            l2 = 120 + lv * 20
            l3 = l2
            if v[2] in (P_GUARD, P_HANGEKI):
                l2 = div(l2, 2)
                l3 = div(l3, 2)
            if st.tflag[32] > 0:
                l2 = div(l2 * (100 - get_counter_attack(ctx, 2)), 100)
                l3 = div(l3 * (100 - get_counter_attack(ctx, 2)), 100)
            # :460–461 `CALL TENTACLE_ACCESS, "GETNAME"` は悪堕ちキャラ戦でも呼ばれるが、FLAG:11 = 0（ACTION.ERB:38）で
            # TRYCALLFORM が不発になるだけ（RESULTS のみ変化）で結果は使われないので呼ばない
            if enemy_type_check(st, "AKUOTI") == 0 and tentacle_access(ctx, "GETNAME") == "Ｐ触手":
                l2 *= 2
                l3 *= 2
            if t(ctx, c, "祝福") > 0:
                l2 = div(l2 * 125, 100)
                l3 = div(l3 * 125, 100)
            if st.tflag[12] == 2:
                l2 = times(l2, "0.90")
                l3 = times(l3, "0.90")
            elif st.tflag[12] == 3:
                l2 = times(l2, "0.80")
                l3 = times(l3, "0.80")
            l2 = div(l2 * cloth_battle_hosei(ctx, "TAIRYOKU"), 100)
            l3 = div(l3 * cloth_battle_hosei(ctx, "KIRYOKU"), 100)
            liquid = cloth_battle_hosei(ctx, "LIQUID")
            l2 = div(l2 * liquid, 100)
            l3 = div(l3 * liquid, 100)
            # :490–496 屈服・苦痛・恐怖のソース（`IF TCVARn:200 > 0`：完全防御のときだけ入る。原作どおり）
            if v[200] > 0:
                loc[8] = loc.get(8, 0) + div(l2, 4)
                loc[10] = loc.get(10, 0) + l2 * 2
                loc[11] = loc.get(11, 0) + div(l2, 2)
            style = fstyle_name(ctx, st.target, v[0])
            if style == "撹乱":
                l2, l3 = times(l2, "1.15"), times(l3, "1.15")
            elif style == "装甲":
                l2, l3 = times(l2, "0.85"), times(l3, "0.85")
            elif v.get_bit(217, 0) and style == "全力":
                l2, l3 = times(l2, "1.25"), times(l3, "1.25")
            out.set_bold(True)
            if v[200] > 0:
                out.printl(f"{l2}のダメージが無効化された！")
            else:
                out.printl(f"{l2}のダメージを受けた！")
                out.printl(f"{ctx.data.names['BASE'].get(1, '')}が{l3}減った！")
            if v[200] <= 0:
                if c.base[0] - l2 <= 0:
                    l2 = c.base[0]
                c.base[0] -= l2
                if c.base[1] - l3 <= 0:
                    l3 = c.base[1]
                c.base[1] -= l3
            loc[2] = l2  # :446–525 LOCAL:2（:934 HANGEKI_TO_TENTACLE の ARG:2）
            if game_option(st, GameOption.STAT_DECLINE):
                out.printl(f"{ctx.data.names['BASE'].get(1, '')}基礎が{div(l3, 2)}減った！")
            out.set_bold(False)
            out.printl()
            # ENEMY_ACTION.ERB@ENEMY_ACTION:532–540：完全防禦也經過此處，且不鉗制基礎值。
            if game_option(st, GameOption.STAT_DECLINE):
                c.base[51] -= div(l3, 2)
            cloth_battle_damage(ctx, 15)
            if v[14] > 0:
                state_change_extraeffect(ctx)
            state_change_betobeto(ctx, 25)
            state_change_hairan(ctx, 2)
            if cheers_enabled(ctx):
                perform_cheers_tentacle_hit_hantei(ctx)
            if v[200] > 0:
                shinkyou_change(ctx, "KOUYOU")
            else:
                shinkyou_change(ctx, "IKARI_TEIKAN")
            if c.cflag[1] != 2:
                v[6] += limit(isqrt(max(c.base[11] - 100, 0)), 0, 20) + 5
    elif action == 4:  # :574–628 距離をとる（敵の体力回復）
        # ERB/ゲーム内_戦闘処理/ENEMY_ACTION.ERB@ENEMY_ACTION:577–593。
        # 先按敵類取比例並截斷，再除以2+回復係數；強化HP已在遭遇時套用。
        if enemy_type_check(st, "AKUOTI"):
            l3 = times(st.flag[12], "0.08")
        else:
            lastboss = enemy_type_check(st, "LASTBOSS") >= 1
            rate = "0.04" if lastboss else "0.16" if enemy_type_check(st, "MOB") == 1 else "0.08"
            l3 = times(st.flag[12], rate)
            # ERB/ゲーム内_戦闘処理/LASTBOSS_POWERUP.ERB@LASTBOSS_REST:16–22。
            st.result[0] = 8 if config_check_balance(st, 5) > 0 and lastboss else 0
            l3 = div(l3, 2 + st.result[0])
        if st.flag[13] + l3 > st.flag[12]:
            l3 = st.flag[12] - st.flag[13]
        st.flag[13] += l3
        _enemy_prefix(ctx)
        out.printl(f"の体力が{l3}回復した")
        l4 = times(st.flag[16], "0.25")
        st.flag[17] = limit(st.flag[17] - l4, 0, st.flag[17])
        if st.tflag[2] == 1 and st.flag[17] < st.flag[16]:
            st.flag[17] = st.flag[16]
        elif st.flag[17] < st.flag[16]:
            st.tflag[2] = 0
            out.printl()
            _enemy_prefix(ctx)
            out.printl("は油断から立ち直った")
            out.printl()
        msg_takeaway(ctx)
        _other(ctx, "TAKEAWAY")
    elif action == 5:  # :630–747 押し倒す
        msg_oshitaosu(ctx)
        _other(ctx, "OSHITAOSU")
        r = act_hantei_tentacle_to_chara(ctx, "AVOID_OSHITAOSU")
        loc[0] = r
        if r == 1:
            st.tflag[33] += 1
            msg_oshitaosu_false(ctx)
            _other(ctx, "OSHITAOSU_FALSE")
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        elif r == 2:
            if v[2] != P_EX_HANGEKI:
                st.tflag[33] += 1
            msg_absence(ctx)
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        else:
            dmg = times(damage(ctx, "CHARA"), "0.25")
            v[0] = 0
            v[8] = 2
            msg_oshitaosu_success(ctx)
            _other(ctx, "OSHITAOSU_SUCCESS")
            l2 = div(dmg * cloth_battle_hosei(ctx, "TAIRYOKU"), 100)
            out.set_bold(True)
            out.printl(f"{l2}のダメージを受けた！")
            out.set_bold(False)
            if c.base[0] - l2 <= 0:
                l2 = c.base[0]
            c.base[0] -= l2
            l3 = 25 if v[2] == P_GUARD else 50
            l3 = div(l3 * cloth_battle_hosei(ctx, "KIRYOKU"), 100)
            out.set_bold(True)
            out.printl(f"{ctx.data.names['BASE'].get(1, '')}が{l3}減った！")
            out.set_bold(False)
            out.printl()
            if c.base[1] < l3:
                l3 = c.base[1]
            c.base[1] -= l3
            out.set_bold(True)
            out.set_color((250, 0, 0))
            out.printl(f"{name}は押し倒されてしまった！")
            out.reset_color()
            out.set_bold(False)
            cloth_battle_damage(ctx, 4)
            if v[14] > 0:
                state_change_extraeffect(ctx)
            shinkyou_change(ctx, "REISEI_DOUYOU")
            out.printl()
            if abl(ctx, c, "欲望") < 3 and is_female(ctx.data, c):  # :743–744（体力の条件なし）
                v[2] = P_V_GUARD
            return True  # :745 GOTO LOOP_TOP
    elif action == 6:  # :748–928 邪悪な波動
        msg_hadou(ctx)
        _other(ctx, "HADOU")
        r = act_hantei_tentacle_to_chara(ctx, "AVOID_HADOU")
        loc[0] = r
        if r == 1:
            st.tflag[33] += 1
            msg_hadou_false(ctx)
            _other(ctx, "HADOU_FALSE")
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        elif r == 2:
            if v[2] != P_EX_HANGEKI:
                st.tflag[33] += 1
            msg_absence(ctx)
            if cheers_enabled(ctx):
                perform_cheers_tentacle_miss_hantei(ctx)
        else:
            # :794 完全防御（短絡：防御中でなければ最初の RAND を引かない）
            if (v[2] == P_GUARD and st.rng.rand(100) < 15) or (v[2] == P_EX_HANGEKI and st.rng.rand(100) < 10):
                v[200] = 1
                msg_perfect_guard(ctx)
                _other(ctx, "ATTACK_PERFECT_GUARD")
            else:
                msg_simple_hit(ctx, "BATTLE_TENTACLE_HADOU_HIT")  # :1513–1526（ATTACK_HIT と同形）
                _other(ctx, "HADOU_HIT")
            lv = tentacle_level(st)
            l2 = 60 + lv * 10
            l3 = 180 + lv * 25
            if enemy_type_check(st, "AKUOTI"):  # :813–822
                e = st.charas[st.flag[111]]
                l2 += st.rng.rand(max(div(e.maxbase[10], 2), 1))
                l3 += st.rng.rand(max(e.maxbase[10], 1))
            else:
                kg = int(tentacle_access(ctx, "KOUGEKI"))
                l2 += st.rng.rand(div(kg, 8))
                l3 += st.rng.rand(div(kg, 4))
            if v[2] == P_GUARD:
                l2 = div(l2, 2)
                l3 = div(l3, 2)
            if st.tflag[32] > 0:
                l2 = div(l2 * (100 - get_counter_attack(ctx, 2)), 100)
                l3 = div(l3 * (100 - get_counter_attack(ctx, 2)), 100)
            if t(ctx, c, "祝福") > 0:
                l2 = div(l2 * 125, 100)
                l3 = div(l3 * 125, 100)
            if st.tflag[12] == 2:
                l2 = times(l2, "0.90")
                l3 = times(l3, "0.90")
            elif st.tflag[12] == 3:
                l2 = times(l2, "0.80")
                l3 = times(l3, "0.80")
            l2 = div(l2 * cloth_battle_hosei(ctx, "TAIRYOKU"), 100)
            l3 = div(l3 * cloth_battle_hosei(ctx, "KIRYOKU"), 100)
            wave = cloth_battle_hosei(ctx, "WAVE")
            l2 = div(l2 * wave, 100)
            l3 = div(l3 * wave, 100)
            if v[200] == 0:  # :859–863
                loc[8] = loc.get(8, 0) + div(l2, 4)
                loc[10] = loc.get(10, 0) + l2 * 2
                loc[11] = loc.get(11, 0) + div(l2, 2)
            style = fstyle_name(ctx, st.target, v[0])
            if style == "撹乱":
                l2, l3 = times(l2, "1.15"), times(l3, "1.15")
            elif style == "装甲":
                l2, l3 = times(l2, "0.85"), times(l3, "0.85")
            elif v.get_bit(217, 0) and style == "全力":
                l2, l3 = times(l2, "1.25"), times(l3, "1.25")
            out.set_bold(True)
            if v[200] > 0:
                out.printl(f"{l2}のダメージが無効化された！")
            else:
                out.printl(f"{l2}のダメージを受けた！")
                if c.base[0] - l2 <= 0:
                    l2 = c.base[0]
                c.base[0] -= l2
                out.printl(f"{ctx.data.names['BASE'].get(1, '')}が{l3}減った！")
                out.printl()
                if c.base[1] - l3 <= 0:
                    l3 = c.base[1]
                c.base[1] -= l3
            out.set_bold(False)
            loc[2] = l2
            cloth_battle_damage(ctx, 6)
            if cheers_enabled(ctx):
                perform_cheers_tentacle_hit_hantei(ctx)
            if v[14] > 0:
                state_change_extraeffect(ctx)
            if v[200] > 0:
                shinkyou_change(ctx, "KOUYOU")
            else:
                shinkyou_change(ctx, "IKARI_TEIKAN")
            if c.cflag[1] != 2:
                v[6] += limit(isqrt(max(c.base[11] - 100, 0)), 0, 20) + 5
    else:
        raise NotImplementedError(f"敵の行動 TFLAG:10 = {action}")
    # :933–934 反撃判定（`!(気絶) && 反撃 || ＥＸ反撃`）
    # （`&&`／`||` は同優先度 0x40・左結合：reference/emuera-1824/Emuera/GameData/Expression/OperatorCode.cs:33–34）
    if ((v[12] & KIZETU) == 0 and v[2] == P_HANGEKI) or v[2] == P_EX_HANGEKI:
        yield from hangeki_to_tentacle(ctx, st.tflag[10], loc.get(0, 0), loc.get(2, 0))
    v[200] = 0
    if st.tflag[10] != 4 and loc.get(0, 0) == 0:
        st.tflag[33] = 0
    yield from palam_cal(ctx, 0, 0, 0, 0, 0, 0, 0, loc.get(7, 0), loc.get(8, 0), loc.get(9, 0), loc.get(10, 0), loc.get(11, 0))
    return False


def select_tentacle_action(ctx: Ctx) -> None:
    """`@SELECT_TENTACLE_ACTION`（ENEMY_ACTION.ERB:1019–1069）。"""
    st = ctx.state
    c = tc(ctx)
    st.tflag[11] = 0
    st.tflag[12] = 0
    st.tflag[10] = int(tentacle_access(ctx, "ATTACK_ROUTINE"))
    if st.tflag[10] == 0:
        r = st.rng.rand(100)
        st.tflag[10] = 1 if r < 40 else 2 if r < 70 else 3 if r < 95 else 4
    if st.flag[902] and st.tflag[10] == 2:
        r = st.rng.rand(100)
        if r < 15:
            st.tflag[10] = 1
        elif r < 30:
            st.tflag[10] = 3
        elif r < 35:
            st.tflag[10] = 4
    elif st.flag[907] and st.rng.rand(100) < 20:
        st.tflag[10] = 2
    if st.tflag[10] == 4 and percent_cal(st.flag[13], st.flag[12]) >= 75:
        st.tflag[10] = 1
    if st.tflag[10] == 1 and c.base[0] <= 0:
        st.tflag[10] = st.rng.rand(2) + 2
        if c.base[1] <= 0:
            st.tflag[10] = 2
    attack_place_decision(ctx)


def select_enemy_action(ctx: Ctx) -> None:
    """`@SELECT_ENEMY_ACTION`（ENEMY_ACTION.ERB:1073–1156）：悪堕ちキャラの行動選択。
    1=攻撃 2=絡みつく 3=体液を吐く 4=距離を取る 5=押し倒す 6=邪悪な波動。専用ルーチンは無く（:1079 は註解）TFLAG:10 = 0。"""
    st = ctx.state
    c = tc(ctx)
    e = st.charas[st.flag[111]]
    rand = st.rng.rand
    st.tflag[11] = 0
    st.tflag[12] = 0
    st.tflag[10] = 0  # :1080–1081
    lo = rand(100)  # :1084–1102
    st.tflag[10] = 1 if lo < 55 else 6 if lo < 70 else 2 if lo < 85 else 3 if lo < 95 else 4
    if st.flag[902] and st.tflag[10] == 2:  # :1104–1114
        lo = rand(100)
        if lo < 15:
            st.tflag[10] = 1
        elif lo < 30:
            st.tflag[10] = 3
        elif lo < 35:
            st.tflag[10] = 4
        elif lo < 40:
            st.tflag[10] = 6
    elif st.flag[907] and rand(100) < 20:  # :1116–1117
        st.tflag[10] = 2
    if st.tflag[10] == 4 and percent_cal(st.flag[13], st.flag[12]) >= 90:  # :1121–1122
        st.tflag[10] = 1
    if c.base[0] <= 0 and c.base[1] > 0:  # :1125–1133
        lo = rand(100)
        st.tflag[10] = 6 if lo < 40 else 2 if lo < 80 else 3
    elif c.base[1] <= 0 and c.base[0] > 0:  # :1135–1143
        lo = rand(100)
        st.tflag[10] = 1 if lo < 40 else 2 if lo < 80 else 3
    elif c.base[0] <= 0 and c.base[1] <= 0:  # :1145–1146
        st.tflag[10] = 2
    if st.tflag[10] == 2 and t(ctx, e, "寄生") == 0:  # :1149–1150
        st.tflag[10] = 5
    if st.tflag[10] == 3 and t(ctx, e, "寄生") == 0:  # :1153–1154
        st.tflag[10] = 1
    attack_place_decision(ctx)


# --- FORECAST.ERB ------------------------------------------------------------------


def attack_place_decision(ctx: Ctx) -> None:
    """`@ATTACK_PLACE_DECISION`（FORECAST.ERB:2–204）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    tt = lambda n: t(ctx, c, n)  # noqa: E731
    rand = st.rng.rand
    while True:  # $SELECT_LOOP
        a = st.tflag[10]
        if a == 1:
            for bit, tal in ((1, "近距離得意"), (2, "中距離得意"), (4, "遠距離得意")):
                if rand(2) == 0:
                    st.tflag[11] |= bit
                elif tt(tal) and rand(3) == 0:
                    st.tflag[11] |= bit
            if rand(10) == 0:
                st.tflag[11] |= 8
            elif tt("空中得意") and rand(8) == 0:
                st.tflag[11] |= 8
        elif st.flag[73] > 0:
            st.tflag[11] |= 1
            if rand(4) == 0:
                st.tflag[11] |= 2
        elif a in (2, 5):
            for bit in (1, 2, 4):
                if rand(4) == 0:
                    st.tflag[11] |= bit
            if rand(10) == 0:
                st.tflag[11] |= 8
        elif a == 3:
            if rand(3) != 0:
                st.tflag[11] |= 1
            if rand(4) != 0:
                st.tflag[11] |= 2
            if rand(5) != 0:
                st.tflag[11] |= 4
            if rand(10) == 0:
                st.tflag[11] |= 8
        elif a == 6:
            if rand(5) != 0:
                st.tflag[11] |= 1
            if rand(4) != 0:
                st.tflag[11] |= 2
            if rand(3) != 0:
                st.tflag[11] |= 4
            if rand(10) == 0:
                st.tflag[11] |= 8
        if v[0] == 1 and v[2] == P_NOTHING:
            st.tflag[11] |= 1
        elif v[0] == 2 and v[2] == P_NOTHING:
            st.tflag[11] |= 2
        elif v[0] == 3 and v[2] == P_NOTHING:
            st.tflag[11] |= 4
        elif v.get_bit(216, 1) and v[2] == P_NOTHING:
            st.tflag[11] |= 8
        if config_check_balance(st, 8) and ((v[12] & KIZETU) or (v[12] & 32)):
            if v[0] in (1, 2, 3):
                st.tflag[11] |= (1, 2, 4)[v[0] - 1]
        for bit in (1, 2, 4):
            if (st.tflag[11] & bit) == bit:
                st.tflag[12] += 1
        if st.tflag[12] == 0 and st.tflag[10] != 4:
            continue
        break
    a = st.tflag[10]
    if st.flag[11] == 1150:
        pass
    elif a == 1:
        if rand(4) == 0:
            st.tflag[11] |= 8
        elif tt("空中得意") and rand(4) == 0:
            st.tflag[11] |= 8
    elif a in (2, 5):
        if rand(5) == 0:
            st.tflag[11] |= 8
    elif a == 3:
        if rand(3) != 0:
            st.tflag[11] |= 8
    elif a == 6:
        if rand(5) == 0:
            st.tflag[11] |= 8
    if not v.get_bit(216, 1) and rand(2) == 0:
        st.tflag.set_bit(11, 3, False)
    if st.tflag[12] == 3 and rand(4) != 0:
        st.tflag.set_bit(11, 3, False)
    # :135–204 予測
    l0 = c.maxbase[13]
    if st.tflag[25] > 0:
        l0 = div(l0 * 3, 2) + 25
    st.tflag[25] = 0
    r = percent_cal(c.base[1] * 2, c.maxbase[1])
    if r < 100:
        l0 = div(l0 * (r + 300), 400)
    l0 = div(l0 * cloth_battle_hosei(ctx, "CHISEI"), 100)
    l0 = shinkyou_check(ctx, "CHISEI", l0)
    l0 += calc_chisei_shien(ctx, 0)
    if enemy_type_check(st, "AKUOTI"):  # :162–168
        l1 = st.charas[st.flag[111]].maxbase[13]
    else:
        l1 = int(tentacle_access(ctx, "CHISEI"))
    l2 = l0 + l1
    l3 = div(160 * l0, l2) + 96
    if st.flag[999] == 1:
        raise NotImplementedError("デバッグ表示は未移植")
    # :180 ファンブル（`RAND < … && SELECTCOM != 7 && (…)`：RAND を先に引く）
    if rand(256) < div(256 - l3, 4) and st.temp.selectcom != 7 and (
        not v.get_bit(217, 0) or fstyle_name(ctx, st.target, v[0]) != "知略"
    ):
        v[30] = -1
        v[31] = -1
        v[32] = -1
    for i in range(3):
        if rand(256) < l3:
            ev = int_eval(ctx, l0, l1)
            v[30 + i] = inversion_probability(ctx, (st.tflag[11] >> i) & 1, ev)
        else:
            v[30 + i] = -1
    if rand(256) < l3:
        ev = int_eval(ctx, l0 * 2, l1)
        v[33] = inversion_probability(ctx, (st.tflag[11] >> 3) & 1, ev)
    else:
        v[33] = -1


def int_eval(ctx: Ctx, pc_int: int, en_int: int) -> int:
    """`@INT_EVAL, PC_INT, EN_INT`（FORECAST.ERB:397–504）。"""
    st = ctx.state
    rand = st.rng.rand
    if enemy_type_check(st, "AKUOTI") == 1:
        local = 0
    elif enemy_type_check(st, "BOSS") == 1:
        local = 25 + rand(50)
    elif enemy_type_check(st, "LASTBOSS") >= 1:
        local = 25 + rand(75)
    elif enemy_type_check(st, "MOB") == 1:
        local = 50 + rand(25)
    else:
        # どれにも該当しない（クズ市民）→ LOCAL は前回値（静的 LOCAL）
        from .core import get_local

        local = get_local(st,"INT_EVAL",0)
    if game_option(st, GameOption.HARDCORE):
        local = times(local, "1.50")
    if game_option(st, GameOption.EASY):
        local = times(local, "0.75")
    if game_option(st, GameOption.SOLO):
        local = times(local, "0.50")
    # FORECAST.ERB@INT_EVAL:409–426；LOCAL 屬函式靜態狀態（沿用 core 的 LOCAL 儲存）。
    from .core import set_local
    set_local(st,"INT_EVAL",0,local)
    en_int += local
    per = percent_cal(pc_int, en_int)
    rv = [0] * 12
    for i in range(11):
        rv[i] = div((i * 2 - 10) * (105 - per) + i * 5 + 250, 33)
        if per < 40:
            if i < 3:
                rv[i] = 0
            f = {3: "0.50", 4: "0.75", 5: "1.25", 6: "1.50", 7: "1.25"}.get(i)
            if f:
                rv[i] = times(rv[i], f)
        elif per < 80:
            if i < 2:
                rv[i] = 0
            f = {2: "0.50", 3: "0.75", 5: "1.25"}.get(i)
            if f:
                rv[i] = times(rv[i], f)
        elif per < 120:
            if i == 0:
                rv[i] = 0
            f = {1: "0.50", 2: "0.75", 9: "0.75", 10: "0.50"}.get(i)
            if f:
                rv[i] = times(rv[i], f)
        elif per < 150:
            if i == 0 or i == 10:
                rv[i] = 0
            f = {1: "0.75", 8: "0.75", 9: "0.50"}.get(i)
            if f:
                rv[i] = times(rv[i], f)
        rv[11] += rv[i]
    rv[11] = rand(rv[11])
    lc = 0
    while lc < 11:
        if rv[11] < rv[lc]:
            break
        rv[11] -= rv[lc]
        lc += 1
    return lc - 1


def inversion_probability(ctx: Ctx, bln: int, iv: int) -> int:
    """`@INVERSION_PROBABILITY, BLN_VAR, INT_VAR`（FORECAST.ERB:509–543）。"""
    rand = ctx.state.rng.rand
    if bln:
        if iv == 0:
            return 100
        if iv <= rand(20):
            return 100 - iv * 5
        if rand(2) == 0:
            return -1
        return iv * 5
    if iv == 0:
        return 0
    if iv <= rand(20):
        return iv * 5
    if rand(2) == 0:
        return -1
    return 100 - iv * 5

