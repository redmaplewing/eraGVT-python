"""命中・回避・撤退の判定とダメージ計算：`ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB`。

路徑相對 `source/earGVP/ERB/`。敵が触手（FLAG:111 == 0）と洗脳／悪堕ちキャラ（FLAG:111 != 0、S19）の分岐。
悪堕ちキャラ戦で `TENTACLE_ACCESS` を呼ばない（:115–131 等の `IF FLAG:111 == 0`）。
"""

from __future__ import annotations

from ..action import Ctx
from ..chara_common import is_female, levelstatus_up
from ..era import div, isqrt, times
from ..tentacle import enemy_type_check
from .cloth import cloth_battle_hosei
from .core import (
    MAHI,
    BETOBETO,
    KOSHIKUDAKE,
    P_EX_HANGEKI,
    P_GUARD,
    P_HANGEKI,
    P_HANGEKI_OK,
    P_NOTHING,
    correction_binsyou,
    correction_sengi,
    correction_sengi_avoid,
    correction_sengi_damage,
    correction_trans,
    fstyle_name,
    get_local,
    percent_cal,
    set_local,
    shinkyou_check,
    t,
    tc,
    tentacle_access,
    tentacle_level,
)
from .func import get_air_strike, get_brave_hit, get_chain_hit, get_counter_attack, get_evader_atk

_RANGE_DIST = {"ATTACK_RANGE_SHORT": 0, "ATTACK_RANGE_MIDDLE": 1, "ATTACK_RANGE_LONG": 2}


def _enemy_binsyou(ctx: Ctx, sengi: str) -> int:
    """LOCAL:3（敵の敏捷）。`IF FLAG:111 == 0` → TENTACLE_ACCESS "BINSYOU"、それ以外は敵キャラの MAXBASE:敏捷に
    小柄 ×1.05・長身 ×0.90 と戦技補正。sengi：
    "AVOID" = CORRECTION_SENGI_AVOID(…, 0, FLAG:111)（ACT_HANTEI_CHARA_TO_TENTACLE:115–131、_GUARD:453–469）、
    "DIST" = TCVARn:0 に応じた CORRECTION_SENGI（ACT_HANTEI_TENTACLE_TO_CHARA:654–676）、
    "TETTAI" = 小柄のみ（ACT_HANTEI_TETTAI_TENTACLE:1115–1126）。"""
    st = ctx.state
    f111 = st.flag[111]
    if f111 == 0:
        return int(tentacle_access(ctx, "BINSYOU"))
    e = st.charas[f111]
    l3 = e.maxbase[12]
    if t(ctx, e, "小柄") == 1:
        l3 = times(l3, "1.05")
    if sengi == "TETTAI":
        return l3
    if t(ctx, e, "長身") == 1:
        l3 = times(l3, "0.90")
    if sengi == "AVOID":
        return correction_sengi_avoid(ctx, l3, 0, f111)
    dist = tc(ctx).tcvarn[0]
    if dist in (1, 2, 3):
        l3 = correction_sengi(ctx, l3, dist - 1, f111)
    return l3


def _stamina(ctx: Ctx, extra: int = 0) -> int:
    """LOCAL:0（体力＋気力の残量、下限は防御依存）。:12–24 等。"""
    c = tc(ctx)
    l0 = percent_cal(c.base[0] * 2 + c.base[1], c.maxbase[0] * 2 + c.maxbase[1]) + extra
    floor = min(isqrt(max(c.base[11] - 100, 0)) * 8, 75) + extra
    if l0 < floor:
        l0 = floor
    if t(ctx, c, "不屈") > 0:
        l0 = l0 + div(100 - l0, 2)
    return l0


def _enemy_hp_bonus(ctx: Ctx, table: tuple[int, int, int], yudan_div: int) -> int:
    """LOCAL:1（敵の体力残量・油断度による補正）。"""
    st = ctx.state
    p = percent_cal(st.flag[13], st.flag[12])
    l1 = table[0] if p > 50 else table[1] if p > 25 else table[2]
    y = percent_cal(st.flag[17], st.flag[16])
    if y:
        l1 = div(l1 * (100 + div(y, yudan_div)), 100)
    return l1


def _burst_hit(ctx: Ctx, l5: int) -> int:
    """:366–382 バースト攻撃による直撃率修正（HURIHODOKU を含む全 ARGS 共通）。"""
    st = ctx.state
    c = tc(ctx)
    style = fstyle_name(ctx, st.target, c.tcvarn[0])
    if style in ("装甲", "通常"):
        return div(l5 * 125, 100) + 5
    if style in ("重撃", "使役"):
        return div(l5 * 90, 100) - 5
    if style == "広範":
        return 100
    if style == "全力":
        return l5 + 10 - c.cflag[99]
    return l5


def act_hantei_chara_to_tentacle(ctx: Ctx, kind: str) -> tuple[int, int]:
    """`@ACT_HANTEI_CHARA_TO_TENTACLE, ARGS, ARG`:6–415。戻り値 (RESULT, RESULT:1=成功値)。
    :410／:412 の 2 値 RETURN → 共用 RESULT:0〜1。"""
    r = _act_hantei_chara_to_tentacle(ctx, kind)
    ctx.state.set_result_x(*r)
    return r


def _act_hantei_chara_to_tentacle(ctx: Ctx, kind: str) -> tuple[int, int]:
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    if kind == "HURIHODOKU":
        return _hurihodoku(ctx)
    l0 = _stamina(ctx)
    if v[12] & MAHI:
        l0 = div(l0, 2)
    if c.cflag[1] == 2:
        l0 = 100
    l1 = _enemy_hp_bonus(ctx, (100, 105, 110), 2)
    # :91–113 通常の行動
    l2 = c.maxbase[12]
    # :96 TRYCALL KYUSHUTU_NOW：引数を /4 するだけで呼び出し側に影響しない（COMF15.ERB:4–7）
    if t(ctx, c, "小柄") == 1:
        l2 = times(l2, "1.05")
    if t(ctx, c, "長身") == 1:
        l2 = times(l2, "0.90")
    l2 = correction_trans(ctx, l2)
    l2 = div(l2 * cloth_battle_hosei(ctx, "BINSYOU"), 100)
    l2 = shinkyou_check(ctx, "BINSYOU", l2)
    l3 = _enemy_binsyou(ctx, "AVOID")  # :115–131
    if st.tflag[2] >= 1 and st.flag[73] == 0:
        l3 = times(l3, "0.25")
    l4 = correction_binsyou(percent_cal(l2, l3))
    l5 = div(l0 * l1 * l4, 10000)
    lv = c.abl[50]
    mob = enemy_type_check(st, "MOB") == 1
    if kind == "ATTACK_RANGE_SHORT":
        l5 = times(l5, "1.05")
        l5 = correction_sengi(ctx, l5, 0, st.target)
        if mob and l5 < 15:
            l5 = 15
        elif l5 < 30:
            l5 = 30
        if l5 > 80:
            l5 = 80
        l5 += min(15, 3 * max(0, lv - tentacle_level(st)))
        if v.get_bit(3, 0):
            l5 += 25
    elif kind == "ATTACK_RANGE_MIDDLE":
        l5 = correction_sengi(ctx, l5, 1, st.target)
        if mob and l5 < 12:
            l5 = 12
        elif l5 < 25:
            l5 = 25
        if l5 > 85:
            l5 = 85
        l5 += min(10, 2 * max(0, lv - tentacle_level(st)))
        if v.get_bit(3, 0):
            l5 += 30
    elif kind == "ATTACK_RANGE_LONG":
        l5 = times(l5, "0.95")
        l5 = correction_sengi(ctx, l5, 2, st.target)
        if mob and l5 < 9:
            l5 = 9
        elif l5 < 20:
            l5 = 20
        if l5 > 90:
            l5 = 90
        l5 += min(5, max(0, lv - tentacle_level(st)))
        if v.get_bit(3, 0):
            l5 += 35
    else:
        raise KeyError(kind)
    style = fstyle_name(ctx, st.target, v[0])
    if style == "汎用":  # :312 （FSTYLE_NAME_F は "汎用" を返さないので常に不成立：原作どおり）
        l5 += 5
    elif style == "知略":
        l6 = c.maxbase[13]
        l6 = div(l6 * cloth_battle_hosei(ctx, "CHISEI"), 100)
        l6 = shinkyou_check(ctx, "CHISEI", l6)
        l5 += max(0, min(div(l6 * l6, 4000), 50))
    elif style == "広範":
        l5 = times(l5, "0.25")
    elif style == "全力":
        l5 = max(l5 - c.cflag[99] + 15, div(l5, 2) + 15)
    l5 += cloth_battle_hosei(ctx, "HIT")
    if t(ctx, c, "攻勢構築") > 0:
        l5 += 6
    if t(ctx, c, "秘められし力") > 0 and percent_cal(c.base[0] + c.base[1], c.maxbase[0] + c.maxbase[1]) <= 25:
        l5 += 12
    if t(ctx, c, "心眼") > 0:
        l5 += 3
    if t(ctx, c, "共生") > 0:
        l5 += 2
    if c.cflag[43] == 501:
        l5 += 10
    if st.tflag[30] > 1:
        l5 += get_brave_hit(ctx, st.tflag[30] - 1, "命中")
    if st.tflag[32] > 0:
        l5 += get_counter_attack(ctx, 1)
    if v.get_bit(216, 1) and t(ctx, c, "空中得意"):
        l5 += get_air_strike(ctx, 2)
    airplus = cloth_battle_hosei(ctx, "AIRPLUS", st.target)
    if v.get_bit(216, 1) and airplus > 0:
        l5 += 25
    if v.get_bit(216, 1) and t(ctx, c, "空中苦手"):
        l5 -= get_air_strike(ctx, 3)
    if v[2] == P_HANGEKI:
        l5 += 10
    if v[2] == P_EX_HANGEKI:
        l5 += 20
    if v.get_bit(217, 0):  # :367–382
        l5 = _burst_hit(ctx, l5)
    if l5 < 0:
        l5 = 0
    if st.rng.rand(100) < l5:
        return 1, l5
    return 0, l5


def _hurihodoku(ctx: Ctx) -> tuple[int, int]:
    """`ACT_HANTEI_CHARA_TO_TENTACLE, "HURIHODOKU"`（:12–113、:230–307、:331–413 の HURIHODOKU 以外を除く部分）。"""
    from .func import calc_chisei_shien

    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    l0 = _stamina(ctx)
    if v[12] & MAHI:
        l0 = div(l0, 2)
    if c.cflag[1] == 2:
        l0 = 100
    l1 = _enemy_hp_bonus(ctx, (100, 105, 110), 2)
    l2 = c.maxbase[11]  # :41 MAXBASE:防御
    if v.get_bit(3, 1):
        l2 *= 2
    chisei = div(c.maxbase[13], 4)
    if t(ctx, c, "小柄") == 1:
        l2 = times(l2, "0.90")
    if t(ctx, c, "長身") == 1:
        l2 = times(l2, "1.05")
    if st.flag[73] > 0:
        l2 = min(l2, correction_trans(ctx, l2))
    else:
        l2 = correction_trans(ctx, l2)
    l2 = div(l2 * cloth_battle_hosei(ctx, "BOUGYO"), 100)
    chisei = div(chisei * cloth_battle_hosei(ctx, "CHISEI"), 100)
    l2 = shinkyou_check(ctx, "BOUGYO", l2)
    chisei = shinkyou_check(ctx, "CHISEI", chisei)
    chisei += calc_chisei_shien(ctx, 1)
    chisei = div(chisei * 2 * (100 - l0), 100)
    if st.flag[73] > 0:
        raise NotImplementedError("クズ市民戦の振り解く判定は未移植")
    l3 = _enemy_binsyou(ctx, "AVOID")  # :115–131
    if st.tflag[2] >= 1 and st.flag[73] == 0:
        l3 = times(l3, "0.25")
    if st.flag[999] == 1:
        raise NotImplementedError("デバッグ表示は未移植")
    l4 = correction_binsyou(percent_cal(l2, l3))
    l5 = div(l0 * l1 * l4, 10000)
    if l5 < 20:  # :232–233
        l5 = 20
    l5 += min(div(chisei, 15), 30)  # :236–238（FLAG:73 == 0）
    # DEVIATION: :241／:245 の `LOCAL:O`（英字 O）は定義のない識別子で、reference/emuera-1824 では実行時に
    # CodeEE（Process.ScriptProc.cs:38–42 → ArgumentParser.cs:52–58、ExpressionParser.cs:264–269／
    # IdentifierDictionary.cs:645）になり、原作ではこの行に来るとエラーで止まる。LOCAL:0（体力気力の残量）の
    # 誤記とみなして LOCAL:0 で判定する（deviations.md「振り解く判定の LOCAL:O」、要裁決）。
    if l5 <= 45 and l0 > 49:
        l5 = 45
    if l5 <= 60 and l0 > 74:
        l5 = 60
    if st.flag[111] == 0:  # :249–252 `IF FLAG:111 == 0 && ARGS == "HURIHODOKU"`
        l5 = div(l5 * 100, int(tentacle_access(ctx, "HOLD")))
    if v[2] in (3, 200):  # 体勢：耐える／暴れる防御
        l5 += 20
    if v[2] == 6:  # 睨みつける
        l5 += 10
    if st.temp.prevcom == 40:
        l5 += 40
    if v[2] == 201:  # 暴れる失敗
        l5 -= 10
    if l5 > 80:
        l5 = 80
    if v.get_bit(3, 1):
        l5 += 35
    if st.flag[903]:
        l5 += 10
    elif st.flag[908]:
        l5 -= 10
    if t(ctx, c, "剛腕") > 0:
        l5 += 10
    if t(ctx, c, "小さな体躯") > 0:
        l5 -= 10
    koukotsu = v[12] & 64
    if koukotsu:
        l5 -= 10
    if st.tflag[2] >= 1 and not koukotsu:
        l5 = 100  # :293–296（FLAG:73 == 0）
    if l5 < 10:
        l5 = 10
    # :331–365 共通の補正（HURIHODOKU 以外の条件が付いたものを除く）
    l5 += cloth_battle_hosei(ctx, "HIT")
    if t(ctx, c, "攻勢構築") > 0:
        l5 += 6
    if t(ctx, c, "秘められし力") > 0 and percent_cal(c.base[0] + c.base[1], c.maxbase[0] + c.maxbase[1]) <= 25:
        l5 += 12
    if t(ctx, c, "心眼") > 0:
        l5 += 3
    if t(ctx, c, "共生") > 0:
        l5 += 2
    cloth_battle_hosei(ctx, "AIRPLUS", st.target)  # :355（結果は HURIHODOKU では使わない）
    if v[2] == P_HANGEKI:
        l5 += 10
    if v[2] == P_EX_HANGEKI:
        l5 += 20
    if v.get_bit(217, 0):  # :367–382
        l5 = _burst_hit(ctx, l5)
    if l5 < 0:
        l5 = 0
    if st.rng.rand(100) < l5:
        return 1, l5
    return 0, l5


def act_hantei_chara_to_tentacle_guard(ctx: Ctx, kind: str) -> int:
    """`@ACT_HANTEI_CHARA_TO_TENTACLE_GUARD, ARGS`:419–570（カス当たり判定）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    l0 = _stamina(ctx)
    if c.cflag[1] == 2:
        l0 = 100
    l1 = _enemy_hp_bonus(ctx, (100, 105, 110), 2)
    l2 = c.maxbase[12]
    if t(ctx, c, "小柄") == 1:
        l2 = times(l2, "1.05")
    if t(ctx, c, "長身") == 1:
        l2 = times(l2, "0.90")
    l3 = _enemy_binsyou(ctx, "AVOID")  # :453–469
    l4 = div(correction_binsyou(percent_cal(l2, l3)), 2) + 50
    l5 = div(l0 * l1 * l4, 10000)
    if kind == "ATTACK_RANGE_SHORT":
        l5 = times(l5, "0.95")
        l5 = correction_sengi(ctx, l5, 0, st.target)
        if l5 < 35:
            l5 = 35
    elif kind == "ATTACK_RANGE_MIDDLE":
        l5 = correction_sengi(ctx, l5, 1, st.target)
        if l5 < 45:
            l5 = 45
    elif kind == "ATTACK_RANGE_LONG":
        l5 = times(l5, "1.05")
        l5 = correction_sengi(ctx, l5, 2, st.target)
        if l5 < 50:
            l5 = 50
    else:
        raise KeyError(kind)
    style = fstyle_name(ctx, st.target, v[0])
    if style == "広範":
        l5 += 35
    if style == "全力":
        l5 = times(l5, "0.85")
    if c.cflag[43] == 501:
        l5 -= 10
    if v.get_bit(3, 0):
        l5 += 100
    if v[2] == P_HANGEKI:
        l5 += 15
    if v[2] == P_EX_HANGEKI:
        l5 += 25
    if v.get_bit(217, 0) and style == "全力":  # :545–550
        l5 = 0
    return 1 if st.rng.rand(100) < l5 else 0


_AVOID_TABLE = {
    # ARGS: {距離: (最低値の除数, 最低値の上限, 最高値, EX防加算)}（:754–994）
    "AVOID_KOUGEKI": {1: (15, 30, 80, 35), 2: (12, 35, 85, 40), 3: (10, 40, 90, 45)},
    "AVOID_KARAMITUKU": {1: (15, 30, 70, 35), 2: (12, 35, 75, 40), 3: (10, 40, 80, 45)},
    "AVOID_TAIEKI": {1: (10, 40, 85, 40), 2: (12, 35, 80, 45), 3: (15, 30, 75, 50)},
    "AVOID_OSHITAOSU": {1: (15, 30, 70, 35), 2: (12, 35, 75, 40), 3: (10, 40, 80, 45)},
    "AVOID_HADOU": {1: (10, 40, 75, 55), 2: (12, 35, 70, 60), 3: (15, 30, 65, 65)},
}


def breast_weight_term(ctx: Ctx, c, value: int) -> int:
    """胸部重量の補正項 `value * (1 + 胸の重量) / (1 + BASE:体重)`（女性のみ、男性は 0）。
    被弾判定 :606–614・撤退判定 :1097–1105 では引き、DAMAGE :1207–1214 では足す。
    SP変身中（変身能力 == 1 && CFLAG:1 == 2）は胸の重量だけ MAXBASE、体重は常に BASE（原文どおり）。
    身体データ未生成（BASE:44 = BASE:48 = 0）だと項は value 自身になる（初期セットのキャラは原作でもこの状態、
    `docs/wiki/era/body-profile.md`）。"""
    if not is_female(ctx.data, c):
        return 0
    breast = c.maxbase[48] if (t(ctx, c, "変身能力") == 1 and c.cflag[1] == 2) else c.base[48]
    return div(value * (1 + breast), 1 + c.base[44])


def act_hantei_tentacle_to_chara(ctx: Ctx, kind: str) -> int:
    """`@ACT_HANTEI_TENTACLE_TO_CHARA, ARGS`:574–1052。

    戻り値 1＝キャラが回避、2＝その距離にいない（空振り）、0＝被弾。
    """
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    l0 = _stamina(ctx)
    if v[12] & MAHI:
        l0 = div(l0, 2)
    if c.cflag[1] == 2:
        l0 = 100
    l1 = _enemy_hp_bonus(ctx, (100, 105, 110), 2)
    l2 = c.maxbase[12]
    l2 -= breast_weight_term(ctx, c, l2)  # :606–614 胸部重量ペナルティ
    l6 = c.maxbase[11]
    if v.get_bit(3, 1):
        l6 *= 2
    if t(ctx, c, "小柄") == 1:
        l2 = times(l2, "1.05")
    if t(ctx, c, "長身") == 1:
        l2 = times(l2, "0.90")
    l2 = correction_trans(ctx, l2)
    l6 = correction_trans(ctx, l6)
    l2 = div(l2 * cloth_battle_hosei(ctx, "BINSYOU"), 100)
    l6 = div(l6 * cloth_battle_hosei(ctx, "BOUGYO"), 100)
    l2 = shinkyou_check(ctx, "BINSYOU", l2)
    l6 = shinkyou_check(ctx, "BOUGYO", l6)
    if st.temp.selectcom in (0, 73):
        l2 = times(l2, "1.50")
    l2 = correction_sengi_avoid(ctx, l2, 0, st.target)
    l6 = correction_sengi_avoid(ctx, l6, 0, st.target)
    l3 = _enemy_binsyou(ctx, "DIST")  # :654–676
    if st.tflag[2] >= 1:
        l3 = times(l3, "0.50")
    if st.tflag[12] == 1:
        l3 = times(l3, "1.2")
    if st.tflag[12] == 3:
        l3 = times(l3, "0.8")
    if kind == "AVOID_HADOU":
        l3 = times(l3, "1.5")
    l4 = correction_binsyou(percent_cal(l2, l3))
    dist_key = {1: "SHORT", 2: "MIDDLE", 3: "LONG"}.get(v[0])
    if dist_key and st.flag[111] == 0:  # :697–709
        l4 = div(l4 * 100, int(tentacle_access(ctx, dist_key)))
    l5 = div(l0 * l1 * l4, 10000)
    l5 += cloth_battle_hosei(ctx, "AVOID")
    if c.cflag[43] == 502:
        l5 += 5
    style = fstyle_name(ctx, st.target, v[0])
    if style == "重撃":
        l5 = times(l5, "0.70")
    if st.tflag[30] > 1:
        l5 -= get_brave_hit(ctx, st.tflag[30] - 1, "回避")
    if v[2] == P_HANGEKI:
        l5 = times(l5, "0.75")
    elif v[2] == P_EX_HANGEKI:
        l5 = times(l5, "0.90")
    if v[0] == 1:
        l5 = times(l5, "0.85")
    elif v[0] == 3:
        l5 = times(l5, "1.15")
    tab = _AVOID_TABLE[kind].get(v[0])
    if tab:
        dv, cap, top, ex = tab
        floor = min(div(l6, dv), cap)
        if l5 < floor:
            l5 = floor
        if l5 > top:
            l5 = top
        if v.get_bit(3, 1):
            l5 += ex
    if kind == "AVOID_HADOU" and v[2] in (P_HANGEKI, P_EX_HANGEKI):
        l5 -= 10
    # :997 対空攻撃に対して空中にいると 25% で回避率 0
    if v.get_bit(216, 1) and (st.tflag[11] & 8) and st.rng.rand(100) < 25:
        l5 = 0
    if v.get_bit(216, 2) and t(ctx, c, "小さな体躯") == 0:
        l5 = 0
    if v.get_bit(217, 0) and fstyle_name(ctx, st.target, v[0]) in ("広範", "全力"):  # :1006–1013
        l5 = 0
    tf11 = st.tflag[11]
    if (
        (v[0] == 1 and not (tf11 >> 0) & 1)
        or (v[0] == 2 and not (tf11 >> 1) & 1)
        or (v[0] == 3 and not (tf11 >> 2) & 1)
    ):
        l5 = -1
    if v.get_bit(216, 1) and not (tf11 >> 3) & 1 and st.rng.rand(100) < get_air_strike(ctx, 1):
        l5 = -1
    if v[2] == P_NOTHING:
        l5 = 0
    if l5 == -1:
        return 2
    if st.rng.rand(100) < l5:
        return 1
    if t(ctx, c, "超反応") > 0 and st.tflag[80] == 0 and v[2] != P_NOTHING:
        st.tflag[80] += 1
        ctx.out.set_color((255, 128, 0))
        ctx.out.printw("[超反応]が発動、攻撃を絶対に回避する！")
        ctx.out.reset_color()
        ctx.out.printl()
        return 1
    return 0


def act_hantei_tettai_tentacle(ctx: Ctx) -> int:
    """`@ACT_HANTEI_TETTAI_TENTACLE`:1056–1171。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    l0 = _stamina(ctx, 20)
    if (v[12] & BETOBETO) or (v[12] & KOSHIKUDAKE):
        l0 = div(l0, 2)
    if c.cflag[1] == 2:
        l0 = 120
    l1 = _enemy_hp_bonus(ctx, (100, 120, 140), 1)
    l2 = c.maxbase[12]
    if t(ctx, c, "小柄") == 1:
        l2 = times(l2, "1.05")
    if t(ctx, c, "長身") == 1:
        l2 = times(l2, "0.90")
    l2 = correction_trans(ctx, l2)
    l2 -= breast_weight_term(ctx, c, l2)  # :1097–1105 胸部重量ペナルティ
    l2 = div(l2 * cloth_battle_hosei(ctx, "BINSYOU"), 100)
    l2 = shinkyou_check(ctx, "BINSYOU", l2)
    l3 = _enemy_binsyou(ctx, "TETTAI")  # :1115–1126
    if st.tflag[2] >= 1:
        l3 = times(l3, "0.50")
    l4 = correction_binsyou(percent_cal(l2, l3))
    l5 = div(l0 * l1 * l4, 10000)
    if l5 < 50:
        l5 = 50
    l5 += 20 * st.flag[43]
    if st.flag[70] + st.flag[71] > 0:
        l5 = 0
    if st.flag[999] == 1:
        raise NotImplementedError("デバッグモードの撤退率入力は未移植")
    if st.rng.rand(100) < l5:
        return 1
    if enemy_type_check(st, "CITIZEN") == 1:
        return 1
    return 0


def fstyle_attack(ctx: Ctx, who: int, dist: int) -> int:
    """`武器と衣装/武器カスタマイズ関連/FIGHT_STYLE.ERB@FSTYLE_ATTACK, ARG, ARG:1`:42–111。

    :67–74 の小柄・長身は TARGET の素質を見る（原作どおり）。
    """
    st = ctx.state
    c = st.charas[who]
    l10 = div(c.maxbase[10] * cloth_battle_hosei(ctx, "KOUGEKI", who), 100)
    l11 = div(c.maxbase[11] * cloth_battle_hosei(ctx, "BOUGYO", who), 100)
    l12 = div(c.maxbase[12] * cloth_battle_hosei(ctx, "BINSYOU", who), 100)
    l13 = div(c.maxbase[13] * cloth_battle_hosei(ctx, "CHISEI", who), 100)
    tgt = st.target_chara
    if t(ctx, tgt, "小柄") == 1:
        l10 = times(l10, "0.95")
        l12 = times(l12, "1.05")
    if t(ctx, tgt, "長身") == 1:
        l10 = times(l10, "1.05")
        l12 = times(l12, "0.95")
    style = fstyle_name(ctx, who, dist)
    attack = {
        "連続": lambda: div(l10 * 25, 100) + div(l12 * 20, 100),
        "装甲": lambda: div(l10 * 45, 100) + div(l11 * 40, 100),
        "撹乱": lambda: div(l10 * 75, 100) + div(l12 * 35, 100),
        "重撃": lambda: div(l10 * 90, 100) + div(l11 * 30, 100),
        "広範": lambda: div(l10 * 115, 100),
        "全力": lambda: div(l10 * 150, 100),
        "知略": lambda: div(l10 * 75, 100) + div(l13 * 25, 100),
        "設置": lambda: div(l10 * 50, 100) + div(l13 * 30, 100),
        "使役": lambda: div(l10 * 25, 100) + div(l13 * 20, 100),
        "反撃": lambda: div(l10 * 70, 100) + div(l11 * 50, 100),
        "通常": lambda: div(l10 * 100, 100),
    }[style]()
    if fstyle_name(ctx, st.target, tgt.tcvarn[0]) == "反撃":  # :102–110
        if tgt.tcvarn.get_bit(217, 0):  # :104–105 バーストの場合は半減
            attack = div(l10 * 35, 100) + div(l11 * 25, 100)
        elif tgt.tcvarn[2] != P_HANGEKI_OK:
            attack = div(l10 * 25, 100) + div(l11 * 15, 100)
    return attack


def damage(ctx: Ctx, kind: str) -> int:
    """`@DAMAGE, ARGS`:1175–1546。LOCAL:7 は呼び出し間で保持される（:1500–1510 で代入されない場合がある）。
    LOCAL:1 も同様：悪堕ちキャラ戦の "ABARERU"（:1365–1373 は FLAG:111 == 0 のときだけ代入）では前回の値のまま
    （関数の LOCAL は呼び出し間で保持：reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs@SetDefaultLocalValue:514–520）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    f111 = st.flag[111]
    l5 = fstyle_attack(ctx, st.target, v[0])
    if v.get_bit(3, 0):
        l5 = div(l5 * (150 if c.cflag[1] == 2 else 200), 100)
    l5 = correction_trans(ctx, l5)
    piercing = t(ctx, c, "乳首ピアス")
    if piercing in (1, 2, 3, 4, 5):
        l5 = times(l5, {1: "1.40", 2: "1.60", 3: "1.80", 4: "2.00", 5: "5.00"}[piercing])
    l5 += breast_weight_term(ctx, c, l5)  # :1207–1214 巨乳攻撃ボーナス
    l6 = c.maxbase[11]
    if v.get_bit(3, 1):
        l6 = div(l6 * 200, 100)
    l6 = correction_trans(ctx, l6)
    l6 = div(l6 * cloth_battle_hosei(ctx, "BOUGYO"), 100)
    style = fstyle_name(ctx, st.target, v[0])
    if style == "撹乱":
        l6 = times(l6, "0.85")
    elif style == "装甲":
        l6 += 50
        l6 = times(l6, "1.15")
    tt = lambda n: t(ctx, c, n)  # noqa: E731
    if kind in _RANGE_DIST:
        dist = _RANGE_DIST[kind]
        l0 = shinkyou_check(ctx, "KOUGEKI", l5)
        l0 = times(l0, ("2.50", "2.25", "2.00")[dist])
        l0 = correction_sengi_damage(ctx, l0, dist, st.target)
        # :1248–1255 等 `IF FLAG:111 == 0` 触手の防御力 / 敵キャラの MAXBASE:防御
        l1 = int(tentacle_access(ctx, "BOUGYO")) if f111 == 0 else st.charas[f111].maxbase[11]
        if st.tflag[2] >= 1:
            l1 = times(l1, "0.50")
        # 得意・苦手による補正（:1261–1351）
        tab = {
            0: ("1.20", "0.60", "0.85", "1.15", "0.85", "1.10", "1.16"),
            1: ("0.90", "1.20", "1.25", "0.70", "0.90", "1.10", "1.085"),
            2: ("0.95", "1.20", "0.95", "1.10", "1.30", "0.80", "1.0275"),
        }[dist]
        for name, f in zip(("近距離得意", "近距離苦手", "中距離得意", "中距離苦手", "遠距離得意", "遠距離苦手"), tab):
            if tt(name):
                l0 = times(l0, f)
        if tt("近距離得意") and tt("中距離得意") and tt("遠距離得意"):
            l0 = times(l0, tab[6])
    elif kind == "ABARERU":  # :1353–1377
        l0 = shinkyou_check(ctx, "KOUGEKI", l5)
        if enemy_type_check(st, "MOB") == 1:
            l0 = times(l0, "0.125")
        elif f111 == 0:
            l0 = times(l0, "1.00")
        else:
            l0 = times(l0, "2.00")
        if f111 == 0:
            l1 = div(int(tentacle_access(ctx, "BOUGYO")), 2)
            if st.tflag[2] >= 1:
                l1 = times(l1, "0.50")
        else:
            l1 = get_local(st, "DAMAGE", 1)  # 前回の DAMAGE の LOCAL:1（原作どおり）
        if v.get_bit(3, 0):
            l1 *= 2
    elif kind == "CHARA":
        if f111 == 0:  # :1380–1396
            l0 = int(tentacle_access(ctx, "KOUGEKI"))
        else:
            l0 = st.charas[f111].maxbase[10]
            if v[0] in (1, 2, 3):
                l0 = correction_sengi_damage(ctx, l0, v[0] - 1, f111)
        if st.tflag[2] >= 1:
            l0 = times(l0, "0.75")
        lv = tentacle_level(st)
        if v[0] in (1, 2, 3):
            l3 = 75 + lv * 2
        elif v[0] == 0:
            l3 = div(75 + lv, 2)
        else:
            raise NotImplementedError(f"DAMAGE：TCVARn:0 = {v[0]}")
        l0 = div(l0 * l3, 100)
        if st.tflag[12] == 2:
            l0 = times(l0, "0.90")
        if st.tflag[12] == 3:
            l0 = times(l0, "0.80")
        l1 = shinkyou_check(ctx, "BOUGYO", l6)
        if v[2] == P_GUARD:
            l0 = div(l0, 2)
        # :1432 `(TFLAG:10 != 2 || 5)` は常に真
        if v[2] == P_HANGEKI:
            l0 = times(l0, "0.65" if st.tflag[12] < 3 else "0.85")
        if c.cflag[1] != 2:
            v[6] += max(0, min(isqrt(max(c.base[11] - 100, 0)), 20)) + 5
    else:
        raise NotImplementedError(f"DAMAGE, {kind!r} は未移植")
    set_local(st, "DAMAGE", 1, l1)
    l6b = 100
    l3 = max(div(div(500000 * (l0 + l6b), l1 + l6b), 1000), 80)
    if kind == "CHARA":
        l3 = max(l3 + 100 - div((l1 - levelstatus_up(100, c.abl[50], 50, 9999)) * 175, 100), 80)
    if v.get_bit(217, 0) and kind != "CHARA":  # :1461–1479 与ダメージ修正
        mul = {"連続": 40, "撹乱": 110, "重撃": 150, "全力": 150, "使役": 300, "通常": 110}.get(style)
        if mul is not None:
            l3 = div(l3 * mul, 100)
        if tt("フルバースト") > 0:
            l3 = div(l3 * 125, 100)
    if v.get_bit(217, 0) and kind == "CHARA" and style == "全力":  # :1482–1487 被ダメージ修正
        l3 = div(l3 * 125, 100)
    if st.tflag[31] > 1 and kind != "CHARA":
        l3 = div(l3 * get_chain_hit(ctx, st.tflag[31] - 1), 100)
    if st.tflag[32] > 0 and kind == "CHARA":
        l3 = div(l3 * (100 - get_counter_attack(ctx, 2)), 100)
    if st.tflag[33] > 1 and kind != "CHARA":
        l3 = div(l3 * (div(get_evader_atk(ctx, st.tflag[33] - 1) - 100, 2) + 100), 100)
    l7 = get_local(st, "DAMAGE", 7)
    if c.cflag[99] > 0 and kind != "CHARA":
        if c.cflag[99] >= 50:
            l7 = 750
        elif c.cflag[99] >= 30:
            l7 = 500
        elif c.cflag[99] >= 20:
            l7 = 250
        # 20 未満では LOCAL:7 は前回の値のまま（:1500–1507）
    else:
        l7 = 0
    set_local(st, "DAMAGE", 7, l7)
    l3 = div(l3 * (1000 - l7), 1000)
    if st.flag[73] > 0:
        l3 = 1
    r = st.rng.rand(100)
    if r < 20:
        l3 = times(l3, "1.08")
    elif r < 40:
        l3 = times(l3, "1.05")
    elif r < 60:
        pass
    elif r < 80:
        l3 = times(l3, "0.95")
    else:
        l3 = times(l3, "0.92")
    return l3
