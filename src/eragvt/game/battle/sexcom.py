"""触手の性攻撃：`ゲーム内_戦闘処理/戦闘コマンド(性攻撃)/`（SEX_COMABLE.ERB、SEX_COM0–20.ERB、SEX_SPCOM0–15.ERB、
SEX_COMEX.ERB、AUTO_V_DEFENCE.ERB）と `ENEMY_ACTION.ERB@ENEMY_ACTION_SEX_ROUTINE`:1162–1430、
ボス触手の `TENTACLE_BOSS_{n}_SEX_ROUTINE`／`_REACTION_REF`（`触手データ/ボス触手/`）。

路徑相對 `source/earGVP/ERB/`。

- 各 SEX_COMn の LOCAL:0〜11 は冒頭の `REPEAT 12 / LOCAL:COUNT = 0` で毎回 0 になるが、LOCAL:12（体力消費、
  PALAM_CAL の 13 番目の引数 = LOSEBASE:体力）は初期化されず `LOCAL:12 += n` で**呼び出しのたびに累積**する
  （関数の LOCAL は呼び出し間で保持：reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs@SetDefaultLocalValue:514–520）。
  原作どおり `st.temp.locals[("SEX_COMn", 12)]` に保持する。
- 雑魚敵・クズ市民（TRYCALLFORM MESSAGE_MOB_…）の分岐は未移植で停止する。
- 悪堕ちキャラ戦（S19）：本文の地の文の直前に `MESSAGE_OTHER_SEX_COMn`／`SPCOMn`（`core.msg_other`）、ペニス位置 TFLAG:18
  （`_penis_pos`）、近親交配は `INCEST_F(TARGET, FLAG:111)`（RELATION）、追加責めは SEX_COMEX_RANDOM:66–74。
- AUTO_V_DEFENCE は INPUT を含むので、SEX_COMABLE と一部の SEX_COM はジェネレータ（`yield` で入力待ち）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..action import Ctx, config_check_maniac, config_check_other, kojo_root
from ..chara_common import is_female, is_male
from ..era import div, times
from ..tentacle import enemy_type_check
from .cloth import INNER_DEF, INNER_PER, NO_INNER, OUTER_PER, cloth_battle_damage
from .core import (
    is_penis,
    msg_other,
    run_chinobun,
    DARAKU,
    KIZETU,
    KOUKOTSU,
    KYOUKOUSOKU,
    P_V_GUARD,
    abl,
    add_exp,
    config_check_balance,
    exp,
    get_local,
    is_hole,
    is_manly,
    message_branch,
    percent_cal,
    set_local,
    shinkyou_change,
    t,
    tc,
    tentacle_level,
)
from .func import state_change_hatujou
from .gaping import set_tentacle_pool, set_tentacle_size
from . import sexmsg
from .syasei import tentacle_syasei_up

SexGen = Generator[None, int, int]

C, V, A, B = 1, 2, 4, 8  # DIM.ERH:94–101
MOUTH, HAND, WAREME = 16, 32, 64
# DIM.ERH:208–210 性コマンド分類
TYPE_NORMAL, TYPE_FERA, TYPE_INSERT = 0, 1, 2

# SEX_COM*.ERB／SEX_SPCOM*.ERB の @SEX_TYPE_COM{n}（各ファイル :4–5／:16–17）
SEX_TYPE = {
    0: 0, 1: 0, 2: 0, 3: 2, 4: 0, 5: 2, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 1, 12: 1, 13: 0, 14: 0,
    15: 2, 16: 2, 17: 2, 18: 2, 19: 2, 20: 2,
    1000: 0, 1001: 2, 1002: 2, 1003: 0, 1004: 0, 1005: 1, 1006: 0, 1007: 0, 1008: 0, 1009: 2, 1010: 2, 1011: 2,
    1012: 0, 1013: 0, 1014: 0, 1015: 0,
}


# --- 小物 ------------------------------------------------------------------------------


def _tbl(v: int, vals: tuple[int, ...]) -> int | None:
    """`IF X == 0 / ELSEIF X == 1 … / ELSEIF X >= 5` の段階表（該当なし＝負の値は None）。"""
    if v < 0:
        return None
    return vals[min(v, len(vals) - 1)]


def _le2(v: int, vals: tuple[int, int, int, int]) -> int:
    """`IF X <= 2 / ELSEIF X == 3 / ELSEIF X == 4 / ELSEIF X >= 5`。"""
    return vals[0] if v <= 2 else vals[1] if v == 3 else vals[2] if v == 4 else vals[3]


def _set(L: list[int], i: int, v: int | None) -> None:
    if v is not None:
        L[i] = v


def _a(ctx: Ctx, name: str) -> int:
    return abl(ctx, tc(ctx), name)


def _mob(ctx: Ctx) -> bool:
    st = ctx.state
    return enemy_type_check(st, "MOB") == 1 or enemy_type_check(st, "CITIZEN") == 1


def _akuoti(ctx: Ctx) -> bool:
    return enemy_type_check(ctx.state, "AKUOTI") == 1


def _no_mob(ctx: Ctx, n: int | str) -> None:
    if _mob(ctx):
        raise NotImplementedError(f"雑魚敵／クズ市民の性攻撃地の文（MESSAGE_MOB_*_COM{n}）は未移植")


def _other(ctx: Ctx, name: str) -> None:
    """`SIF ENEMY_TYPE_CHECK_F("AKUOTI") == 1 / CALL MESSAGE_OTHER_SEX_{name}`（本文の地の文の直前）。"""
    if _akuoti(ctx):
        msg_other(ctx, f"SEX_{name}")


def _penis_pos(ctx: Ctx, part: int) -> None:
    """`SIF ENEMY_TYPE_CHECK_F("AKUOTI") == 1 && (ISPENIS(FLAG:111)) / TFLAG:18 = 部位`（悪堕ちキャラのペニス位置）。"""
    st = ctx.state
    if _akuoti(ctx) and is_penis(ctx, st.flag[111]):
        st.tflag[18] = part


def _begin(ctx: Ctx) -> list[int]:
    """`REPEAT 12 / LOCAL:COUNT = 0`：LOCAL:0〜11 は 0、LOCAL:12 は保持（呼び出し側で読む）。"""
    return [0] * 13


def _finish(ctx: Ctx, fname: str, L: list[int], add12: int) -> None:
    """`LOCAL:12 += add12` と `CALL PALAM_CAL, LOCAL:0〜12`。"""
    from .palam import palam_cal

    st = ctx.state
    l12 = get_local(st, fname, 12) + add12
    set_local(st, fname, 12, l12)
    palam_cal(ctx, *L[:12], losebase=l12)


def _comex(ctx: Ctx, L: list[int], part: int, strength: int) -> None:
    """`IF EX_COM / CALL SEX_COMEX, 部位, 強度, EX_COM | SH_COM / LOCAL:COUNT += RESULT:COUNT`（REPEAT 12）。"""
    st = ctx.state
    if st.temp.ex_com:
        r = sex_comex(ctx, part, strength, st.temp.ex_com | st.temp.sh_com)
        for i in range(12):
            L[i] += r[i]


def _random(ctx: Ctx, part: int, arg1: int = 0) -> None:
    """`CALL SEX_COMEX_RANDOM, 部位, ARG:1 / EX_COM = RESULT:0 / SH_COM = RESULT:1`。"""
    st = ctx.state
    st.temp.ex_com, st.temp.sh_com = sex_comex_random(ctx, part, arg1)


def _size(ctx: Ctx, n: int) -> None:
    """`CALL SET_TENTACLE_SIZE, FLAG:10, FLAG:11, ENEMY_TYPE_CHECK_F("AKUOTI"), FLAG:111, n`。"""
    st = ctx.state
    set_tentacle_size(ctx, st.flag[10], st.flag[11], enemy_type_check(st, "AKUOTI"), st.flag[111], n)


def check_holyvirgin(ctx: Ctx, who: int = -1) -> int:
    """`汎用関数/コモン関数.ERB@CHECK_HOLYVIRGIN_F,ARG=-1`:451–460。"""
    st = ctx.state
    c = st.charas[st.target if who == -1 else who]
    v = t(ctx, c, "処女")
    return 1 if v >= 2 or (config_check_other(st, 5) == 1 and v > 0) else 0


def lostvirgin(ctx: Ctx, arg0: int = 0) -> None:
    """`汎用関数/コモン関数.ERB@LOSTVIRGIN, ARG:0 = 0`:437–447。"""
    c = tc(ctx)
    idx = ctx.data.index_of("TALENT", "処女")
    if c.talent[idx] == -1:
        return
    c.talent[idx] = -1
    if arg0 != 0:
        arg0 = 1
    c.cflag[206] = 2 + arg0
    # :445 CALL MESSAGE_SEX_LOSTVIRGIN（地の文/MESSAGE_SEX.ERB:1582–1658：本文＋:1657 KOJO_ROOT）
    run_chinobun(ctx, "MESSAGE_SEX_LOSTVIRGIN", fallback=lambda: kojo_root(ctx, "SEX_LOSTVIRGIN"))
    if (message_branch(ctx) & DARAKU) == 0:
        shinkyou_change(ctx, "TOUSAKU")


def incest(ctx: Ctx, who: int, other: int, arg2: int = 0) -> int:
    """`SYSTEM/キャラメイキング関連/CHARA_RELATION.ERB@INCEST_F(ARG:0, ARG:1, ARG:2 = 0)`:1002–1016。

    ARG:2 == 0（仲間キャラ、S18）：RELATION:(ARG:0):(ARG:1) に 義理の が立っていれば 0、親子・兄弟姉妹・祖父祖母孫・おじおば・
    甥姪 のどれかなら 1（いとこ は含まない）。ARG:2 != 0：CFLAG:9（父親）との比較。"""
    if arg2 == 0:
        from ..relation import GIRI, KYOUDAI, OIMEI, OJIOBA, OYAKO, SOFUBO

        rel = ctx.state.charas[who].relation[other]
        if (rel >> GIRI) & 1:
            return 0
        return 1 if any((rel >> b) & 1 for b in (OYAKO, KYOUDAI, SOFUBO, OJIOBA, OIMEI)) else 0
    c = ctx.state.charas[who]
    if c.cflag[9] >= 200:
        return 0
    return 1 if other == c.cflag[9] else 0


def _incest_exp(ctx: Ctx, amount: int = 1, guard_akuoti: bool = True) -> None:
    """`SIF ENEMY_TYPE_CHECK_F("AKUOTI") == 0 && INCEST_F(TARGET, FLAG:10 * 100 + FLAG:11, 1) > 0 / EXP:近親交配経験 += n`
    `SIF ENEMY_TYPE_CHECK_F("AKUOTI") == 1 && INCEST_F(TARGET, FLAG:111) > 0 / EXP:近親交配経験 += n`。
    SEX_COM5:129 のみ前者に AKUOTI 判定なし（guard_akuoti=False：悪堕ちキャラ戦では FLAG:10 = FLAG:11 = 0 の
    INCEST_F(TARGET, 0, 1) ＝ CFLAG:9 == 0 との比較になる：原作どおり）。"""
    st = ctx.state
    if (not guard_akuoti or not _akuoti(ctx)) and incest(ctx, st.target, st.flag[10] * 100 + st.flag[11], 1) > 0:
        add_exp(ctx, tc(ctx), "近親交配経験", amount)
    if _akuoti(ctx) and incest(ctx, st.target, st.flag[111]) > 0:
        add_exp(ctx, tc(ctx), "近親交配経験", amount)


def state_change_pkousoku(ctx: Ctx, arg: int) -> None:
    """`ヒロイン関連/CHARA_STATE_CHANGE.ERB@STATE_CHANGE_PKOUSOKU, ARG`:314–333。"""
    from .func import _state_on

    st = ctx.state
    c = tc(ctx)
    if c.tcvarn[12] & KYOUKOUSOKU:
        return
    if c.cflag[1] == 2:
        return
    if st.rng.rand(100) > arg:
        return
    _state_on(ctx, "は", "強拘束", (200, 50, 50), "状態になってしまった！", KYOUKOUSOKU)
    c.tcvarn[2] = 0  # :332 体勢：通常


def palam_vabc_estimate(ctx: Ctx, L: list[int], *parts: int) -> None:
    """`PALAM_UP.ERB@PALAM_VABCestimate(部位, ARG:0〜4)`:1713–1753：TFLAG:100 += 予測値 / 10000。"""
    from .core import seikaku_hosei_palam
    from ..chara_common import seikaku_check
    from .palam import palam_hosei_pose, palam_hosei_seitaisei, palam_hosei_talent, palam_hosei_tentacle, palam_overfeel

    st = ctx.state
    for p in parts:
        if p == -1:
            break
        value = L[p]
        value = div(value * palam_overfeel(ctx, st.target, p), 100)
        value = palam_hosei_pose(ctx, value)
        value = palam_hosei_seitaisei(ctx, value)
        value = palam_hosei_talent(ctx, p, value)
        value = seikaku_hosei_palam(seikaku_check(ctx.data, tc(ctx)), p, value)
        value = palam_hosei_tentacle(ctx, p, value)
        st.tflag[100] += div(value, 10000)


def _pkousoku_branch(ctx: Ctx, part_a: bool, virgin_check: bool = False) -> None:
    """SEX_COM3:178–193 等の共通分岐（派生：両穴／種付け／アナルピストン＋強拘束）。

    `part_a` = True は SEX_COM5／SPCOM2 型（ELSEIF (EX_COM & Ａ) … ISHOLE() → 17）。
    `virgin_check` = True は SPCOM11:153 の `&& TALENT:処女 < 1`。
    """
    st = ctx.state
    c = tc(ctx)
    ex = st.temp.ex_com
    f = st.flag
    rand = st.rng.rand
    no_mob = not _mob(ctx)
    vg = c.tcvarn[2] == P_V_GUARD
    if percent_cal(c.base[2], c.maxbase[2]) >= 50 and rand(2) == 0:
        return  # 何もしない（TFLAG:17 は変更しない：原作どおり、空の分岐）
    if (ex & V) and (ex & A) and f[15] < f[14] and c.base[31] == 0 and c.base[32] == 0 and not vg and no_mob and \
            is_female(ctx.data, c):
        st.tflag[17] = 19
        state_change_pkousoku(ctx, 100)
    elif part_a:
        if (ex & A) and f[15] < f[14] and c.base[32] == 0 and no_mob and is_hole(ctx):
            st.tflag[17] = 17
            state_change_pkousoku(ctx, 100)
        else:
            st.tflag[17] = -1
    elif f[15] < f[14] and c.base[31] == 0 and not vg and no_mob and is_female(ctx.data, c) and (
        not virgin_check or t(ctx, c, "処女") < 1
    ):
        st.tflag[17] = 15
        state_change_pkousoku(ctx, 100)
    else:
        st.tflag[17] = -1


# 感覚の段階表
_C_WEAK = (500, 1000, 2000, 4000, 6000, 8000)
_KYOUJUN = (200, 500, 1000, 2000)  # 従順 <= 2 / 3 / 4 / >= 5
_SYUUTOKU_20 = (20, 50, 100, 200, 500, 1000)
_SYUUTOKU_50 = (50, 100, 200, 500, 1000, 2000)


def _houshi_bonus(ctx: Ctx, L: list[int]) -> None:
    """`IF ABL:奉仕精神 < 3 / ELSEIF < 4 (+500,+200) / ELSEIF < 5 (+1000,+500) / ELSE (+2000,+1000)`（LOCAL:5／LOCAL:6）。"""
    h = _a(ctx, "奉仕精神")
    if h < 3:
        return
    if h < 4:
        L[5] += 500
        L[6] += 200
    elif h < 5:
        L[5] += 1000
        L[6] += 500
    else:
        L[5] += 2000
        L[6] += 1000


def _lub_pain_a(ctx: Ctx, low: tuple[int, int, int], high: tuple[int, int, int | None]) -> int:
    """Ａ感覚と潤滑による苦痛（SEX_COM4:102–117 型）。high の最後が None は ELSE 側が空（加算なし）。"""
    c = tc(ctx)
    lub = c.palam[10]
    tab = low if _a(ctx, "Ａ感覚") < 3 else high
    v = tab[0] if lub < 100 else tab[1] if lub < 10000 else tab[2]
    return v or 0


# --- SEX_COMEX.ERB -------------------------------------------------------------------


def sex_comex_random(ctx: Ctx, arg: int, arg1: int = 0) -> tuple[int, int]:
    """`@SEX_COMEX_RANDOM, ARG, ARG:1 = 0`:17–123：(追加責め部位, 結界で阻まれた部位)。"""
    st = ctx.state
    c = tc(ctx)
    rand = st.rng.rand
    at = 0
    for i in range(4):  # :29–47
        r = 30 + min(tentacle_level(st), 30)
        if i + 1 == st.flag[11]:
            r += 25
        if st.flag[10]:
            r += 15
        if rand(100) < r:
            at |= 1 << i
    if arg1 > 0:
        at = arg1
    elif arg1 < 0:
        at = 0
    if (at & V) and is_male(ctx.data, c):  # :56–63
        at -= V
        at |= 1 if rand(2) == 0 else 4
    if _akuoti(ctx) and sexmsg.istentacler(ctx, st.flag[111]) == 0:  # :66–74
        at = 0
        # :69 `SETBIT AT_FLAG, (Ｖ - 1)`：Ｖ = 2 → ビット 1（＝Ｖ）。:72 `(Ａ - 1)`：Ａ = 4 → ビット 3（＝Ｂ：原作どおり）
        if arg == C and is_female(ctx.data, c) and rand(2) == 0:
            at |= 1 << (V - 1)
        if st.tflag[10] == 1001 and rand(2) == 0:
            at |= 1 << (A - 1)
    if arg & C:  # :77–84
        at |= C
    if (arg & V) and is_female(ctx.data, c):
        at |= V
    if arg & A:
        at |= A
    if arg & B:
        at |= B
    shielded = 0  # :87–95
    for i in range(4):
        if c.base[30 + i] > 0:
            shielded |= 1 << i
    if (at & ~shielded) == 0 and arg1 == 0:  # :98–121
        cands = [k for k in range(4) if not ((at >> k) & 1) and (t(ctx, c, "オトコ") < 1 or k != 1)]
        if cands:
            at |= 1 << cands[rand(len(cands))]
    st.set_result_x(at & ~shielded, at & shielded)  # SEX_COMEX.ERB:123（共用 RESULT:0〜1）
    return at & ~shielded, at & shielded


_AT_BASE = (400, 1000, 2000, 4000, 6000, 8000)
_AT_A_LOW = (40, 400, 1000, 2000, 4000, 10000)


def sex_comex(ctx: Ctx, arg0: int, arg1: int, arg2: int) -> list[int]:
    """`@SEX_COMEX, ARG:0（元の部位）, ARG:1（強度：未使用）, ARG:2（追加責め部位）`:129–338。"""
    st = ctx.state
    c = tc(ctx)
    lv = [0] * 12
    part = [0] * 4
    mag = [0] * 4
    shield = [0] * 4
    for i in range(4):
        if arg2 & (1 << i):
            part[i] = 1
            mag[i] = 100
        shield[i] = 1 if c.base[30 + i] > 0 else 0
    for i in range(4):
        if arg0 & (1 << i):
            part[i] = 2
            mag[i] = 200
    blocked = 0
    passed = 0
    for i in range(4):  # :182–194
        if sum(part) > 2:
            mag[i] = div(mag[i] * (130 - sum(part) * 15), 100)
        if part[i]:
            if shield[i]:
                blocked += mag[i]
            else:
                passed += 1
    for i in range(4):  # :196–252
        if part[i] > 0:
            a = c.abl[i]
            if i != 2:
                _set(lv, i, _tbl(a, _AT_BASE))
            elif config_check_balance(st, 7) == 0:
                _set(lv, i, _tbl(a, _AT_A_LOW))
            else:
                _set(lv, i, _tbl(a, _AT_BASE))
            if passed == 0:
                raise ZeroDivisionError("SEX_COMEX:248 の 0 除算（原作ではエラー）")
            mag[i] += div(blocked, passed)
            lv[i] = div(lv[i] * mag[i], 100)
    if part[0] == 1 and (is_manly(ctx) or t(ctx, c, "ふたなり") > 0):  # :256–260
        lv[0] += 100
    if part[1] == 1:  # :263–287
        if c.tcvarn[2] == P_V_GUARD:
            lv[1] = div(lv[1], 4)
        if shield[1] == 0:
            add_exp(ctx, c, "Ｖ経験", 1)
        cal = 0
        if t(ctx, c, "処女") > 0:
            cal = {0: 200, 1: 100, 2: 20}.get(_a(ctx, "Ｖ感覚"), 0)
        if shield[1]:
            cal = div(cal, 2)
        lv[11] += cal
    if part[2] == 1:  # :290–330
        if shield[2] == 0:
            add_exp(ctx, c, "Ａ経験", 1)
        lub = c.palam[10]
        if _a(ctx, "Ａ感覚") < 3:
            cal = 1000 if lub < 100 else 100 if lub < 10000 else 10
        else:
            cal = 100 if lub < 100 else 10 if lub < 10000 else 0
        if shield[2] == 0:
            lv[10] += cal
        cal = {0: 1000, 1: 500, 2: 200}.get(_a(ctx, "Ａ感覚"), 0)
        if shield[2]:
            cal = div(cal, 2)
        lv[11] += cal
    st.set_result_x(*lv)  # SEX_COMEX.ERB:338 RETURN L_VAR:0〜11（共用 RESULT）
    return lv


# --- AUTO_V_DEFENCE.ERB --------------------------------------------------------------


def auto_v_defence(ctx: Ctx, who: int) -> SexGen:
    """`@AUTO_V_DEFENCE, ARG`:2–30（清純派の自動Ｖ防御、INPUT で 0 = する / 1 = しない）。"""
    st = ctx.state
    c = st.charas[who]
    tc_ = tc(ctx)
    out = ctx.out
    if st.tflag[81] > 0:
        return 1
    if c.base[31] > 0:
        return 1
    # :7 `TCVARn:12 & 気絶 || (…)`：TCVARn は TARGET
    if (tc_.tcvarn[12] & KIZETU) or (tc_.tcvarn[41] == -1 and tc_.cflag[40 if tc_.cflag[1] == 0 else 41] == 199):
        st.tflag[81] = 1
        return 1
    if t(ctx, c, "処女") > 0:
        out.printl("このままだと処女を奪われそうだ……")
    else:
        out.printl("このままだと前の穴に挿入されそうだ……")
    out.printl("咄嗟にＶ挿入防御しますか？")
    out.printl("[0]する")
    out.printl("[1]しない")
    while True:  # :19–28 $INPUT_LOOP
        r = yield
        if r == 0:
            tc_.tcvarn[2] = P_V_GUARD
            st.tflag[81] = 1
            break
        if r == 1:
            st.tflag[81] = 1
            break
    out.printl()
    return r


def _maybe_auto_v(ctx: Ctx, need_v: bool) -> SexGen:
    """`SIF TALENT:清純派 > 0 && TCVARn:2 != 100 [&& (EX_COM & 膣)] / CALL AUTO_V_DEFENCE, TARGET`。"""
    st = ctx.state
    c = tc(ctx)
    if t(ctx, c, "清純派") > 0 and c.tcvarn[2] != 100 and (not need_v or (st.temp.ex_com & V)):
        yield from auto_v_defence(ctx, st.target)
    return 0


# --- SEX_COM0〜20 -------------------------------------------------------------------


def _mob_or_msg(ctx: Ctx, n: int, msg) -> None:
    """`IF 雑魚／市民 / TRYCALLFORM MESSAGE_MOB_… / ELSE / (悪堕ち) MESSAGE_OTHER_SEX_COMn / CALL MESSAGE_SEX_COMn`。"""
    _no_mob(ctx, n)
    _other(ctx, f"COM{n}")
    msg()


def sex_com0(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM0.ERB@SEX_COM0`:19–117（C攻め弱）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, C, arg1)
    L = _begin(ctx)
    st.tflag[3] += 25
    tentacle_syasei_up(ctx, 50)
    _size(ctx, 0)
    _set(L, 0, _tbl(_a(ctx, "Ｃ感覚"), _C_WEAK))
    if is_manly(ctx) or t(ctx, c, "ふたなり") > 0:
        L[0] += 500
    palam_vabc_estimate(ctx, L, 0, -1)
    _mob_or_msg(ctx, 0, lambda: sexmsg.msg_com0(ctx, st.temp.ex_com, st.temp.sh_com))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 4)
    _comex(ctx, L, C, 0)
    st.tflag[17] = -1
    st.tflag[20] = 0
    L[8] += 500
    L[9] += 50
    _finish(ctx, "SEX_COM0", L, 50)


def sex_com1(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM1.ERB@SEX_COM1`:7–108（C攻め強）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, C, arg1)
    L = _begin(ctx)
    st.tflag[3] += 25
    tentacle_syasei_up(ctx, 50)
    _size(ctx, 1)
    _set(L, 0, _tbl(_a(ctx, "Ｃ感覚"), (800, 1500, 3500, 6000, 10000, 20000)))
    if is_manly(ctx) or t(ctx, c, "ふたなり") > 0:
        L[0] += 1000
    palam_vabc_estimate(ctx, L, 0, -1)
    _mob_or_msg(ctx, 1, lambda: sexmsg.msg_com1(ctx, st.temp.ex_com, st.temp.sh_com))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 8)
    if _a(ctx, "Ｃ感覚") < 3 and c.palam[10] < 1000:  # :70–71
        L[10] = 200
    _comex(ctx, L, C, 1)
    st.tflag[17] = -1
    st.tflag[20] = 1
    L[6] += 1000
    L[8] += 1000
    L[9] += 50
    L[10] += 100
    L[11] += 50
    _finish(ctx, "SEX_COM1", L, 100)


def sex_com2(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM2.ERB@SEX_COM2`:7–133（V攻め弱）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, V, arg1)
    L = _begin(ctx)
    st.tflag[3] += 25
    tentacle_syasei_up(ctx, 50)
    _size(ctx, 2)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), _C_WEAK))
    if c.tcvarn[2] == P_V_GUARD:
        L[1] = div(L[1], 4)
    palam_vabc_estimate(ctx, L, 1, -1)
    _mob_or_msg(ctx, 2, lambda: sexmsg.msg_com2(ctx, st.temp.ex_com, st.temp.sh_com))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 4)
    if st.temp.ex_com & V:
        add_exp(ctx, c, "Ｖ経験", 1)
    if _a(ctx, "Ｖ感覚") < 3 and c.palam[10] < 2000 and c.base[31] <= 0:  # :73–74
        L[10] = 100
    L[4] = 200  # :77
    if t(ctx, c, "処女") > 0:  # :80–89
        _set(L, 11, {0: 200, 1: 100, 2: 20}.get(_a(ctx, "Ｖ感覚")))
    if c.base[31] > 0:
        L[11] = div(L[11], 2)
    _comex(ctx, L, V, 0)
    if st.rng.rand(2) == 0 and is_female(ctx.data, c):  # :102–107
        st.tflag[17] = 3
    else:
        st.tflag[17] = -1
    st.tflag[20] = 2
    L[8] += 500
    L[9] += 100
    L[10] += 50
    _finish(ctx, "SEX_COM2", L, 50)


def _v_pain_fear(ctx: Ctx, L: list[int], lub_low: int, lub_mid: int, fear: tuple[int, int, int, int]) -> None:
    """SEX_COM3:147–168 型：潤滑が低いと苦痛、Ｖ感覚が低いと恐怖（結界ありなら苦痛 0・恐怖半減）。"""
    c = tc(ctx)
    if c.palam[10] < 1000:
        L[10] += lub_low
    elif c.palam[10] < 2000:
        L[10] += lub_mid
    if c.base[31] > 0:
        L[10] = 0
    v = _a(ctx, "Ｖ感覚")
    if 0 <= v <= 3:
        L[11] = fear[v]
    if c.base[31] > 0:
        L[11] = div(L[11], 2)


def sex_com3(ctx: Ctx, arg: int = 0, arg1: int = 0) -> SexGen:
    """`SEX_COM3.ERB@SEX_COM3`:7–219（V攻め強）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, V, arg1)
    yield from _maybe_auto_v(ctx, need_v=False)  # :16–17
    if c.tcvarn[2] == P_V_GUARD or c.base[31] > 0:  # :20–28
        st.tflag[4] |= MOUTH
        if c.base[31] <= 0:
            st.tflag[4] |= WAREME
    else:
        st.tflag[4] |= V
        st.temp.insert |= V
    if st.temp.ex_com & A:  # :30–33
        st.tflag[4] |= A
        st.temp.insert |= A
    _penis_pos(ctx, V)  # :36–37
    L = _begin(ctx)
    st.tflag[3] += 50
    tentacle_syasei_up(ctx, 250)
    _size(ctx, 3)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (400, 1000, 2000, 4000, 10000, 20000)))
    if c.tcvarn[2] == P_V_GUARD:
        L[1] = div(L[1], 4)
    palam_vabc_estimate(ctx, L, 1, -1)
    _no_mob(ctx, 3)
    if t(ctx, c, "処女") > 0 and c.tcvarn[2] != P_V_GUARD and c.base[31] <= 0:  # :88–93
        L[10] = 10000
        lostvirgin(ctx)
    else:
        L[10] = 0
    _other(ctx, "COM3")  # :95–96
    sexmsg.msg_com3(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 8)
    if c.tcvarn[2] == P_V_GUARD:  # :107–117
        add_exp(ctx, c, "Ｖ経験", 1)
        if st.flag[15] >= st.flag[14]:
            add_exp(ctx, c, "フェラ経験", 1)
    elif st.temp.ex_com & V:
        add_exp(ctx, c, "Ｖ経験", 2)
        _incest_exp(ctx)
    L[5] = _le2(_a(ctx, "従順"), _KYOUJUN)
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), _SYUUTOKU_20))
    _v_pain_fear(ctx, L, 5000, 1000, (4000, 1000, 400, 200))
    _comex(ctx, L, V, 1)
    _pkousoku_branch(ctx, part_a=False)
    st.tflag[20] = 3
    L[6] += 1500
    L[8] += 2500
    L[9] += 200
    L[10] += 100
    L[11] += 1000
    _finish(ctx, "SEX_COM3", L, 200)
    return 1


def _a_sense(ctx: Ctx, low: tuple[int, ...], high: tuple[int, ...]) -> int | None:
    """`IF CONFIG_CHECK_BALANCE_F(7) == 0 / Ａ感覚表(low) / ELSEIF > 0 / 表(high)`。"""
    if config_check_balance(ctx.state, 7) == 0:
        return _tbl(_a(ctx, "Ａ感覚"), low)
    return _tbl(_a(ctx, "Ａ感覚"), high)


def sex_com4(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM4.ERB@SEX_COM4`:7–168（A攻め弱）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, A, arg1)
    L = _begin(ctx)
    st.tflag[3] += 25
    tentacle_syasei_up(ctx, 100)
    _size(ctx, 4)
    _set(L, 2, _a_sense(ctx, (40, 400, 1000, 2000, 4000, 10000), (500, 1000, 2000, 4000, 8000, 10000)))
    palam_vabc_estimate(ctx, L, 2, -1)
    _mob_or_msg(ctx, 4, lambda: sexmsg.msg_com4(ctx, st.temp.ex_com, st.temp.sh_com))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 4)
    if st.temp.ex_com & A:
        add_exp(ctx, c, "Ａ経験", 1)
    aa = _a(ctx, "Ａ感覚")
    # :87–99（>= 5 は `4500 * ABL:Ａ感覚 * 100`：原作どおり）
    _set(L, 8, _tbl(aa, (100, 200, 500, 1000, 2000, 4500 * aa * 100)))
    lub = c.palam[10]
    if aa < 3:  # :102–117
        L[10] = 1000 if lub < 100 else 100 if lub < 10000 else 10
    elif lub < 100:
        L[10] = 100
    elif lub < 10000:
        L[10] = 10
    if c.base[32] > 0:
        L[10] = 0
    _set(L, 11, {0: 1000, 1: 500, 2: 200}.get(aa))
    if c.base[32] > 0:
        L[11] = div(L[11], 2)
    _comex(ctx, L, A, 0)
    st.tflag[17] = -1
    st.tflag[20] = 4
    L[8] += 500
    L[9] += 500
    L[10] += 100
    L[11] += 100
    _finish(ctx, "SEX_COM4", L, 50)


def sex_com5(ctx: Ctx, arg: int = 0, arg1: int = 0) -> SexGen:
    """`SEX_COM5.ERB@SEX_COM5`:7–262（A攻め強）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, A, arg1)
    if c.cflag[42] == 398 and st.temp.cloth[INNER_PER] > 0 and (st.temp.ex_com & V):  # :16–20
        st.temp.ex_com -= V
    if config_check_other(st, 4) > 0 and (st.temp.ex_com & V):
        st.temp.ex_com -= V
    yield from _maybe_auto_v(ctx, need_v=True)  # :23–24
    if c.base[32] <= 0:  # :27–38
        st.tflag[4] |= A
        st.temp.insert |= A
    ex = st.temp.ex_com
    vg = c.tcvarn[2] == P_V_GUARD
    if (ex & V) and not vg and c.base[31] <= 0:
        st.tflag[4] |= V
        st.temp.insert |= V
    if (ex & V) and vg and c.base[31] <= 0:
        st.tflag[4] |= WAREME
    _penis_pos(ctx, A)  # :41–42
    L = _begin(ctx)
    st.tflag[3] += 50
    tentacle_syasei_up(ctx, 300)
    _size(ctx, 5)
    _set(L, 2, _a_sense(ctx, (80, 500, 2000, 4000, 10000, 20000), (400, 1000, 2000, 4000, 10000, 20000)))
    palam_vabc_estimate(ctx, L, 2, -1)
    _no_mob(ctx, 5)
    if t(ctx, c, "処女") > 0 and (ex & 2) and not vg and c.base[31] <= 0:  # :108–113
        L[10] = 10000
        lostvirgin(ctx)
    else:
        L[10] = 0
    _other(ctx, "COM5")  # :115–116
    sexmsg.msg_com5(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 8)
    if st.temp.ex_com & A:  # :127–133
        add_exp(ctx, c, "Ａ経験", 2)
        _incest_exp(ctx, guard_akuoti=False)
    L[5] = _le2(_a(ctx, "従順"), _KYOUJUN)
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), _SYUUTOKU_20))
    aa = _a(ctx, "Ａ感覚")
    _set(L, 8, _tbl(aa, (200, 400, 1000, 2000, 4000, 9000 + aa * 200)))
    lub = c.palam[10]
    if aa < 3:  # :179–195
        L[10] += 10000 if lub < 100 else 1000 if lub < 10000 else 100
    else:
        L[10] += 1000 if lub < 100 else 100 if lub < 10000 else 10
    if c.base[32] > 0:
        L[10] = 0
    _set(L, 11, {0: 2000, 1: 1000, 2: 500, 3: 200}.get(aa))
    if c.base[32] > 0:
        L[11] = 0
    _comex(ctx, L, A, 1)
    _pkousoku_branch(ctx, part_a=True)
    st.tflag[20] = 5
    L[6] += 2000
    L[8] += 4000
    L[9] += 800
    L[10] += 200
    L[11] += 500
    _finish(ctx, "SEX_COM5", L, 200)
    return 1


def sex_com6(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM6.ERB@SEX_COM6`:7–152（B攻め弱）。"""
    st = ctx.state
    _random(ctx, B, arg1)
    st.tflag[4] |= HAND
    st.tflag[4] |= B
    if st.rng.rand(100) < 75:
        st.tflag[4] = 0
    _penis_pos(ctx, B)  # :23–24
    L = _begin(ctx)
    st.tflag[3] += 25
    tentacle_syasei_up(ctx, 100)
    _size(ctx, 6)
    _set(L, 3, _tbl(_a(ctx, "Ｂ感覚"), _C_WEAK))
    palam_vabc_estimate(ctx, L, 3, -1)
    _mob_or_msg(ctx, 6, lambda: sexmsg.msg_com6(ctx, st.temp.ex_com, st.temp.sh_com))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 4)
    L[5] = _le2(_a(ctx, "従順"), _KYOUJUN)
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), _SYUUTOKU_50))
    _houshi_bonus(ctx, L)
    _comex(ctx, L, B, 0)
    st.tflag[17] = -1
    st.tflag[20] = 6
    L[8] += 500
    L[9] += 50
    L[10] += 200
    _finish(ctx, "SEX_COM6", L, 50)


def sex_com7(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM7.ERB@SEX_COM7`:7–99（B攻め強：追加責めは PALAM_VABCestimate より前）。"""
    st = ctx.state
    _random(ctx, B, arg1)
    L = _begin(ctx)
    st.tflag[3] += 50
    tentacle_syasei_up(ctx, 50)
    _size(ctx, 7)
    _set(L, 3, _tbl(_a(ctx, "Ｂ感覚"), (400, 1000, 2000, 4000, 10000, 20000)))
    _comex(ctx, L, B, 1)
    palam_vabc_estimate(ctx, L, 3, -1)
    _mob_or_msg(ctx, 7, lambda: sexmsg.msg_com7(ctx, st.temp.ex_com, st.temp.sh_com))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 8)
    st.tflag[17] = -1
    st.tflag[20] = 7
    L[6] += 2500
    L[8] += 1000
    L[9] += 200
    L[10] += 800
    L[11] += 100
    _finish(ctx, "SEX_COM7", L, 100)


def _maso_fear(ctx: Ctx, L: list[int], a: int, b: int, c_: int, d: int) -> None:
    """`IF ABL:従順 < 3 / IF マゾっ気 < 3 (a) ELSE (b) / ELSE / IF マゾっ気 < 3 (c) ELSE (d)`（LOCAL:11）。"""
    lowm = _a(ctx, "マゾっ気") < 3
    if _a(ctx, "従順") < 3:
        L[11] = a if lowm else b
    else:
        L[11] = c_ if lowm else d


def sex_com8(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM8.ERB@SEX_COM8`:7–106（スパンキング）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 0
    st.temp.sh_com = 0
    L = _begin(ctx)
    st.tflag[3] += 5
    tentacle_syasei_up(ctx, 25)
    _size(ctx, 8)
    palam_vabc_estimate(ctx, L, -1)
    _mob_or_msg(ctx, 8, lambda: sexmsg.msg_com8(ctx))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 15)
    add_exp(ctx, c, "苦痛快楽経験", 1)
    _set(L, 8, _tbl(_a(ctx, "マゾっ気"), (40, 200, 400, 1000, 2000, 4000)))
    _maso_fear(ctx, L, 1000, 100, 100, 10)
    st.tflag[17] = -1
    st.tflag[20] = 8
    L[8] += 1000
    L[9] += 100
    L[10] += 4000
    L[11] += 4000
    _finish(ctx, "SEX_COM8", L, 50)


def sex_com9(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM9.ERB@SEX_COM9`:7–113（針）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 0
    st.temp.sh_com = 0
    L = _begin(ctx)
    st.tflag[3] += 25
    tentacle_syasei_up(ctx, 25)
    _size(ctx, 9)
    palam_vabc_estimate(ctx, L, -1)
    _mob_or_msg(ctx, 9, lambda: sexmsg.msg_com9(ctx))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 10)
    m = _a(ctx, "マゾっ気")
    if m:
        add_exp(ctx, c, "苦痛快楽経験", 1)
    tab = {0: (200, 10000), 1: (400, 4000), 2: (1000, 2000), 3: (2000, 1000), 4: (4000, 400)}
    if m in tab:
        L[8], L[11] = tab[m]
    elif m >= 5:
        L[11], L[8] = 200, 10000
    _maso_fear(ctx, L, 5000, 500, 500, 50)
    st.tflag[17] = -1
    st.tflag[20] = 9
    L[8] += 500
    L[10] += 5000
    L[11] += 2500
    _finish(ctx, "SEX_COM9", L, 300)


def sex_com10(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM10.ERB@SEX_COM10`:7–137（手淫）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, 0, arg1)
    st.tflag[4] |= HAND
    if st.rng.rand(100) < 75:
        st.tflag[4] = 0
    _penis_pos(ctx, HAND)  # :22–23
    L = _begin(ctx)
    st.tflag[3] += 25
    tentacle_syasei_up(ctx, 150)
    _size(ctx, 10)
    palam_vabc_estimate(ctx, L, -1)
    _mob_or_msg(ctx, 10, lambda: sexmsg.msg_com10(ctx, st.temp.ex_com, st.temp.sh_com))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 5)
    add_exp(ctx, c, "奉仕快楽経験", 1)
    L[5] = _le2(_a(ctx, "従順"), _KYOUJUN)
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), _SYUUTOKU_50))
    _houshi_bonus(ctx, L)
    _comex(ctx, L, 0, 0)
    st.tflag[17] = -1
    st.tflag[20] = 10
    L[6] += 2000
    L[8] += 400
    L[9] += 100
    _finish(ctx, "SEX_COM10", L, 50)


def sex_com11(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM11.ERB@SEX_COM11`:7–168（フェラ）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, 0, arg1)
    st.tflag[4] |= HAND
    st.tflag[4] |= MOUTH
    if st.rng.rand(100) < 40:
        st.tflag[4] = 0
    _penis_pos(ctx, MOUTH)  # :23–24
    L = _begin(ctx)
    st.tflag[3] += 50
    tentacle_syasei_up(ctx, 200)
    _size(ctx, 11)
    palam_vabc_estimate(ctx, L, -1)
    _mob_or_msg(ctx, 11, lambda: sexmsg.msg_com11(ctx, st.temp.ex_com, st.temp.sh_com))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 5)
    add_exp(ctx, c, "フェラ経験", 1)
    add_exp(ctx, c, "奉仕快楽経験", 1)
    L[5] = _le2(_a(ctx, "従順"), _KYOUJUN)
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (100, 200, 500, 1000, 2000, 5000)))
    L[7] = _le2(_a(ctx, "欲望"), _KYOUJUN)
    _set(L, 8, _tbl(_a(ctx, "従順"), (100, 200, 500, 1000, 2000, 5000)))
    _houshi_bonus(ctx, L)
    if _a(ctx, "従順") < 3:
        L[11] = 2000
    _comex(ctx, L, 0, 0)
    st.tflag[17] = -1
    st.tflag[20] = 11
    L[6] += 2500
    L[8] += 800
    L[9] += 500
    L[10] += 1000
    L[11] += 100
    _finish(ctx, "SEX_COM11", L, 100)


def sex_com12(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM12.ERB@SEX_COM12`:7–150（イラマチオ）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 0
    st.temp.sh_com = 0
    st.tflag[4] |= MOUTH
    st.tflag[4] |= B
    if st.rng.rand(100) < 25:
        st.tflag[4] = 0
    _penis_pos(ctx, MOUTH)  # :20–21
    L = _begin(ctx)
    st.tflag[3] += 50
    tentacle_syasei_up(ctx, 350)
    _size(ctx, 12)
    palam_vabc_estimate(ctx, L, -1)
    _mob_or_msg(ctx, 12, lambda: sexmsg.msg_com12(ctx))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 5)
    add_exp(ctx, c, "フェラ経験", 2)
    if _a(ctx, "マゾっ気") >= 2:
        add_exp(ctx, c, "苦痛快楽経験", 1)
    if _a(ctx, "奉仕精神") >= 2:
        add_exp(ctx, c, "奉仕快楽経験", 1)
    L[5] = _le2(_a(ctx, "従順"), _KYOUJUN)
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (100, 200, 500, 1000, 2000, 5000)))
    _set(L, 8, _tbl(_a(ctx, "従順"), (100, 200, 500, 1000, 2000, 5000)))
    _houshi_bonus(ctx, L)
    if _a(ctx, "従順") < 3:
        L[11] = 500
    st.tflag[17] = -1
    st.tflag[20] = 12
    L[6] += 4000
    L[7] += 400
    L[8] += 2500
    L[10] += 8500
    L[11] += 1000
    _finish(ctx, "SEX_COM12", L, 300)


def sex_com13(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM13.ERB@SEX_COM13`:7–119（絶頂禁止）。雑魚・市民でも MESSAGE_SEX_COM13 を呼ぶ（:37–41）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 0
    st.temp.sh_com = 0
    if st.rng.rand(3) == 0 or c.tcvarn[40]:  # :11–16
        _random(ctx, 0, arg1)
    L = _begin(ctx)
    st.tflag[3] += 5
    tentacle_syasei_up(ctx, 10)
    _size(ctx, 13)
    palam_vabc_estimate(ctx, L, -1)
    _other(ctx, "COM13")  # :37–38
    sexmsg.msg_com13(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    m = c.abl[15]  # :48 ABL:15 = マゾっ気
    _set(L, 8, {0: 200, 1: 400, 2: 1000, 3: 2000, 4: 4000, 5: 10000}.get(m))  # :48–60（== 5 のみ）
    lowm = m < 3
    if c.abl[10] < 3:  # :63–75 ABL:10 = 従順
        L[11] = 5000 if lowm else 500
    else:
        L[11] = 500 if lowm else 50
    if c.tcvarn[40] > 0:  # :77–82
        c.tcvarn[40] = 0
    else:
        c.tcvarn[40] = st.rng.rand(max(1, min(div(50 - st.tflag[0], 5), 50))) + 3
    _comex(ctx, L, 0, 0)
    st.tflag[17] = -1
    st.tflag[20] = 13
    L[8] += 500
    L[11] += 1000
    _finish(ctx, "SEX_COM13", L, 250)


def sex_com14(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM14.ERB@SEX_COM14`:7–117（衣装を破く）。:46 の `ABL:恥情` は DIM.ERH:119 の定数 15 ＝ ABL:15（マゾっ気）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    st.temp.ex_com = 0
    st.temp.sh_com = 0
    L = _begin(ctx)
    st.tflag[3] += 10
    tentacle_syasei_up(ctx, 50)
    _size(ctx, 14)
    palam_vabc_estimate(ctx, L, -1)
    _mob_or_msg(ctx, 14, lambda: sexmsg.msg_com14(ctx))
    set_tentacle_pool(ctx)
    L[9] = _le2(c.abl[15], (2000, 1000, 500, 100))
    cl = st.temp.cloth
    if cl[OUTER_PER] > 90:  # :57–63
        L[9] = times(L[9], "0.25")
    elif cl[OUTER_PER] > 75:
        L[9] = times(L[9], "0.75")
    elif cl[INNER_PER] < 25:
        L[9] = times(L[9], "1.25")
    ju = _a(ctx, "従順")  # :66–76
    if ju == 1:
        L[11] = 2000
    elif ju == 2:
        L[11] = 1000
    elif ju == 3:
        L[11] = 500
    elif ju == 4:
        L[5] = 200
    elif ju >= 5:
        L[5] = 600
    dmg = st.rng.rand(11) + st.rng.rand(11) + 10  # :79
    out.set_bold(True)
    out.printl(f"衣装に{dmg}の損傷を受けた！")
    out.set_bold(False)
    out.printl()
    cloth_battle_damage(ctx, dmg)
    if st.tflag[20] == 14:  # :89–90
        st.tflag[17] = -1
    st.tflag[20] = 14
    L[9] += 1000
    _finish(ctx, "SEX_COM14", L, 0)


def _com15_20_head(ctx: Ctx) -> None:
    """SEX_COM15／17／19 冒頭：`SIF (TCVARn:12 & 強拘束) == 0 / CALL STATE_CHANGE_PKOUSOKU, 100`。"""
    if (tc(ctx).tcvarn[12] & KYOUKOUSOKU) == 0:
        state_change_pkousoku(ctx, 100)


def sex_com15(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM15.ERB@SEX_COM15`:7–169（種付けピストン）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, V, arg1)
    st.temp.insert |= V
    _com15_20_head(ctx)
    _penis_pos(ctx, V)  # :21–22
    L = _begin(ctx)
    st.tflag[3] += 5
    tentacle_syasei_up(ctx, 450)
    _size(ctx, 15)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (40, 100, 200, 400, 1000, 2000)))
    palam_vabc_estimate(ctx, L, 1, -1)
    _mob_or_msg(ctx, 15, lambda: sexmsg.msg_plain(ctx, 15))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 2)
    add_exp(ctx, c, "Ｖ経験", 1)
    _incest_exp(ctx)
    L[5] = _le2(_a(ctx, "従順"), (20, 50, 100, 200))
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (10, 25, 50, 100, 250, 500)))
    if c.palam[10] < 1000:
        L[10] += 1000
    elif c.palam[10] < 2000:
        L[10] += 200
    _set(L, 11, {0: 400, 1: 100, 2: 40, 3: 20}.get(_a(ctx, "Ｖ感覚")))
    _comex(ctx, L, V, 1)
    f = st.flag
    if f[15] >= f[14] * 2:  # :135–143
        st.tflag[17] = 16
    elif (st.temp.ex_com & A) and f[15] >= f[14] and c.base[32] == 0 and not _mob(ctx) and is_hole(ctx):
        st.tflag[17] = 19
    else:
        st.tflag[17] = 15
    st.tflag[20] = 15
    L[6] += 150
    L[7] += 100
    L[8] += 100
    L[9] += 100
    L[10] += 50
    L[11] += 150
    _finish(ctx, "SEX_COM15", L, 1)


def _finish_tflag4_hand_mouth(ctx: Ctx) -> None:
    """SEX_COM16／18／20 :19–23 `IF 悪堕ち && 寄生なし && ペニス持ち / ELSE / TFLAG:4 |= 手 | 口`。"""
    st = ctx.state
    e = st.charas[st.flag[111]]
    if st.flag[110] == 1 and sexmsg.istentacler(ctx, st.flag[111]) == 0 and (
        t(ctx, e, "ふたなり") > 0 or is_male(ctx.data, e)
    ):
        return
    st.tflag[4] |= HAND
    st.tflag[4] |= MOUTH


def sex_com16(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM16.ERB@SEX_COM16`:7–173（種付けフィニッシュ）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, V, arg1)
    st.tflag[4] |= V
    _finish_tflag4_hand_mouth(ctx)
    if st.temp.ex_com & B:
        st.tflag[4] |= B
    _penis_pos(ctx, V)  # :29–30
    L = _begin(ctx)
    st.tflag[3] += 200
    tentacle_syasei_up(ctx, 1000)
    _size(ctx, 16)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (4600, 5500, 8000, 11000, 14000, 20000)))
    palam_vabc_estimate(ctx, L, 1, -1)
    _mob_or_msg(ctx, 16, lambda: sexmsg.msg_plain(ctx, 16))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 2)
    add_exp(ctx, c, "Ｖ経験", 1)
    _incest_exp(ctx)
    L[5] = _le2(_a(ctx, "従順"), (300, 750, 1500, 3000))
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (10, 25, 50, 100, 250, 500)))
    if c.palam[10] < 1000:
        L[10] += 1000
    elif c.palam[10] < 2000:
        L[10] += 200
    _set(L, 11, {0: 8000, 1: 2000, 2: 800, 3: 400}.get(_a(ctx, "Ｖ感覚")))
    _comex(ctx, L, V, 1)
    st.tflag[17] = -1
    st.tflag[20] = 16
    if c.tcvarn[12] & KYOUKOUSOKU:
        c.tcvarn[12] -= KYOUKOUSOKU
    L[6] += 50
    L[7] += 1000
    L[8] += 4000
    L[9] += 1000
    L[11] += 1500
    _finish(ctx, "SEX_COM16", L, 500)


def sex_com17(ctx: Ctx, arg: int = 0, arg1: int = 0) -> SexGen:
    """`SEX_COM17.ERB@SEX_COM17`:7–211（アナルピストン）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, A, arg1)
    st.temp.insert |= A
    _com15_20_head(ctx)
    if c.cflag[42] == 398 and st.temp.cloth[INNER_PER] > 0 and (st.temp.ex_com & V):  # :21–25
        st.temp.ex_com -= V
    if config_check_other(st, 4) > 0 and (st.temp.ex_com & V):
        st.temp.ex_com -= V
    yield from _maybe_auto_v(ctx, need_v=True)  # :28–29
    _penis_pos(ctx, A)  # :32–33
    L = _begin(ctx)
    st.tflag[3] += 5
    tentacle_syasei_up(ctx, 550)
    _size(ctx, 17)
    _set(L, 2, _a_sense(ctx, (8, 50, 200, 400, 1000, 2000), (40, 100, 200, 400, 1000, 2000)))
    palam_vabc_estimate(ctx, L, 2, -1)
    _mob_or_msg(ctx, 17, lambda: sexmsg.msg_plain(ctx, 17))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 2)
    add_exp(ctx, c, "Ａ経験", 1)
    _incest_exp(ctx)
    L[5] = _le2(_a(ctx, "従順"), (20, 50, 100, 200))
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (10, 25, 50, 100, 250, 500)))
    aa = _a(ctx, "Ａ感覚")
    _set(L, 8, _tbl(aa, (20, 40, 100, 200, 400, 900 + aa * 20)))
    if c.palam[10] < 1000:
        L[10] += 1000
    elif c.palam[10] < 2000:
        L[10] += 200
    _set(L, 11, {0: 200, 1: 100, 2: 50, 3: 20}.get(aa))
    _comex(ctx, L, A, 1)
    f = st.flag
    if f[15] >= f[14] * 2:  # :177–185
        st.tflag[17] = 18
    elif (st.temp.ex_com & V) and f[15] >= f[14] and c.base[31] == 0 and c.tcvarn[2] != P_V_GUARD and \
            not _mob(ctx) and is_female(ctx.data, c):
        st.tflag[17] = 19
    else:
        st.tflag[17] = 17
    st.tflag[20] = 17
    L[6] += 200
    L[7] += 100
    L[8] += 400
    L[9] += 200
    L[10] += 100
    L[11] += 50
    _finish(ctx, "SEX_COM17", L, 1)
    return 1


def sex_com18(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM18.ERB@SEX_COM18`:7–195（アナルフィニッシュ）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, A, arg1)
    st.tflag[4] |= A
    st.temp.insert |= A
    _finish_tflag4_hand_mouth(ctx)
    if st.temp.ex_com & B:
        st.tflag[4] |= B
    if st.temp.ex_com & V:
        st.tflag[4] |= WAREME
    _penis_pos(ctx, A)  # :32–33
    L = _begin(ctx)
    st.tflag[3] += 200
    tentacle_syasei_up(ctx, 1150)
    _size(ctx, 18)
    _set(L, 2, _a_sense(ctx, (920, 2750, 8000, 11000, 14000, 20000), (4600, 5500, 8000, 11000, 14000, 20000)))
    palam_vabc_estimate(ctx, L, 2, -1)
    _mob_or_msg(ctx, 18, lambda: sexmsg.msg_plain(ctx, 18))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 2)
    add_exp(ctx, c, "Ａ経験", 1)
    _incest_exp(ctx)
    L[5] = _le2(_a(ctx, "従順"), (300, 750, 1500, 3000))
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (10, 25, 50, 100, 250, 500)))
    if c.palam[10] < 1000:
        L[10] += 1000
    elif c.palam[10] < 2000:
        L[10] += 200
    _set(L, 11, {0: 4000, 1: 2000, 2: 1000, 3: 400}.get(_a(ctx, "Ａ感覚")))
    _comex(ctx, L, A, 1)
    st.tflag[17] = -1
    st.tflag[20] = 18
    if c.tcvarn[12] & KYOUKOUSOKU:
        c.tcvarn[12] -= KYOUKOUSOKU
    L[6] += 50
    L[7] += 1000
    L[8] += 4000
    L[9] += 1000
    L[11] += 1500
    _finish(ctx, "SEX_COM18", L, 500)


def _va_fear(ctx: Ctx, L: list[int]) -> None:
    """SEX_COM19:188–208／SEX_COM20:179–199：Ｖ感覚表のあとＡ感覚表で上書き（どちらも 4 以上は変更なし）。"""
    _set(L, 11, {0: 300, 1: 75, 2: 30, 3: 15}.get(_a(ctx, "Ｖ感覚")))
    _set(L, 11, {0: 150, 1: 75, 2: 35, 3: 15}.get(_a(ctx, "Ａ感覚")))


def sex_com19(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM19.ERB@SEX_COM19`:7–250（両穴ピストン）。:62／:77 はどちらも `CONFIG_CHECK_BALANCE_F(7) == 0`
    （2 つ目の表には到達しない：原作どおり）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, V | A, arg1)
    st.temp.insert |= V
    st.temp.insert |= A
    _com15_20_head(ctx)
    if _akuoti(ctx) and is_penis(ctx, st.flag[111]):  # :22–28（RAND は短絡：先に引く）
        st.tflag[18] = V if (st.rng.rand(2) == 0 or c.tcvarn[2] == P_V_GUARD) else A
    L = _begin(ctx)
    st.tflag[3] += 8
    tentacle_syasei_up(ctx, 600)
    _size(ctx, 19)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (30, 75, 150, 300, 750, 1500)))
    if config_check_balance(st, 7) == 0:
        _set(L, 2, _tbl(_a(ctx, "Ａ感覚"), (6, 35, 150, 300, 750, 1500)))
    palam_vabc_estimate(ctx, L, 1, 2, -1)
    _no_mob(ctx, 19)
    if t(ctx, c, "処女") > 0 and c.tcvarn[2] != P_V_GUARD and c.base[31] <= 0:  # :111–116
        L[10] = 10000
        lostvirgin(ctx)
    else:
        L[10] = 0
    _other(ctx, "COM19")  # :118–119
    sexmsg.msg_plain(ctx, 19)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 3)
    add_exp(ctx, c, "Ｖ経験", 1)
    add_exp(ctx, c, "Ａ経験", 1)
    _incest_exp(ctx)
    L[5] = _le2(_a(ctx, "従順"), (30, 75, 150, 300))
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (15, 35, 70, 135, 300, 600)))
    aa = _a(ctx, "Ａ感覚")
    _set(L, 8, _tbl(aa, (20, 40, 100, 200, 400, 900 + aa * 20)))
    if c.palam[10] < 1000:
        L[10] += 1000
    elif c.palam[10] < 2000:
        L[10] += 200
    _va_fear(ctx, L)
    _comex(ctx, L, V | A, 1)
    st.tflag[17] = 20 if st.flag[15] >= st.flag[14] * 2 else 19
    st.tflag[20] = 19
    L[6] += 350
    L[7] += 200
    L[8] += 500
    L[9] += 300
    L[10] += 150
    L[11] += 200
    _finish(ctx, "SEX_COM19", L, 5)


def sex_com20(ctx: Ctx, arg: int = 0, arg1: int = 0) -> None:
    """`SEX_COM20.ERB@SEX_COM20`:7–240（両穴フィニッシュ）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, V | A, arg1)
    st.tflag[4] |= V
    st.tflag[4] |= A
    st.temp.insert |= V
    st.temp.insert |= A
    _finish_tflag4_hand_mouth(ctx)
    if st.temp.ex_com & B:
        st.tflag[4] |= B
    if _akuoti(ctx) and is_penis(ctx, st.flag[111]):  # :31–37
        st.tflag[18] = V if st.rng.rand(2) == 0 else A
    L = _begin(ctx)
    st.tflag[3] += 300
    tentacle_syasei_up(ctx, 1200)
    _size(ctx, 20)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (3450, 4125, 6000, 8250, 10500, 15000)))
    _set(L, 2, _a_sense(ctx, (690, 2065, 6000, 8250, 10500, 15000), (3450, 4125, 6000, 8250, 10500, 15000)))
    palam_vabc_estimate(ctx, L, 1, 2, -1)
    _mob_or_msg(ctx, 20, lambda: sexmsg.msg_plain(ctx, 20))
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 3)
    add_exp(ctx, c, "Ｖ経験", 1)
    add_exp(ctx, c, "Ａ経験", 1)
    _incest_exp(ctx)
    L[5] = _le2(_a(ctx, "従順"), (400, 1000, 2000, 4000))
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (15, 35, 80, 135, 300, 600)))
    aa = _a(ctx, "Ａ感覚")
    _set(L, 8, _tbl(aa, (15, 30, 75, 150, 300, 650 + aa * 15)))
    if c.palam[10] < 1000:
        L[10] += 1500
    elif c.palam[10] < 2000:
        L[10] += 300
    _va_fear(ctx, L)
    _comex(ctx, L, V | A, 1)
    st.tflag[17] = -1
    st.tflag[20] = 20
    if c.tcvarn[12] & KYOUKOUSOKU:
        c.tcvarn[12] -= KYOUKOUSOKU
    L[6] += 100
    L[7] += 2000
    L[8] += 8000
    L[9] += 2000
    L[11] += 3000
    _finish(ctx, "SEX_COM20", L, 1000)


# --- SEX_SPCOM0〜15 ------------------------------------------------------------------


def sex_spcom0(ctx: Ctx) -> None:
    """`SEX_SPCOM0.ERB@SEX_SPCOM0`:7–112（C攻めSP）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, C)
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 100)
    _size(ctx, 1000)
    _set(L, 0, _tbl(_a(ctx, "Ｃ感覚"), (2000, 4000, 10000, 20000, 40000, 100000)))
    if is_manly(ctx) or t(ctx, c, "ふたなり") > 0:
        L[0] += 1500
    _comex(ctx, L, C, 2)
    palam_vabc_estimate(ctx, L, 0, -1)
    _no_mob_sp(ctx, 0)
    sexmsg.msg_spcom0(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 8)
    add_exp(ctx, c, "苦痛快楽経験", 1)
    if _a(ctx, "Ｃ感覚") < 4:  # :79–82
        L[10] = 1000
        L[11] = 1000
    st.tflag[17] = -1
    st.tflag[20] = 1000
    L[6] += 500
    L[8] += 2000
    L[10] += 500
    L[11] += 1000
    _finish(ctx, "SEX_SPCOM0", L, 200)


def _no_mob_sp(ctx: Ctx, n: int) -> None:
    """SPCOM は雑魚分岐を持たず、悪堕ちのときだけ MESSAGE_OTHER_SEX_SPCOMn を先に呼ぶ（SPCOM0〜7）。"""
    _other(ctx, f"SPCOM{n}")


def sex_spcom1(ctx: Ctx) -> SexGen:
    """`SEX_SPCOM1.ERB@SEX_SPCOM1`:7–209（V攻めSP）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, V)
    yield from _maybe_auto_v(ctx, need_v=False)  # :16–17
    vg = c.tcvarn[2] == P_V_GUARD
    if not vg and c.base[31] <= 0:  # :20–31
        st.tflag[4] |= V
        st.temp.insert |= V
    if vg and c.base[31] <= 0:
        st.tflag[4] |= WAREME
    if (st.temp.ex_com & 4) and c.base[32] <= 0 and (st.flag[110] == 0 or sexmsg.istentacler(ctx, st.flag[111]) == 1):
        st.tflag[4] |= A
        st.temp.insert |= A
    _penis_pos(ctx, V)  # :34–35
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 600)
    _size(ctx, 1001)
    if t(ctx, c, "処女") > 0 and not vg and c.base[31] <= 0:  # :53–58
        L[10] = 10000
        lostvirgin(ctx)
    else:
        L[10] = 0
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (1000, 2000, 4000, 10000, 20000, 40000)))
    if c.tcvarn[2] == P_V_GUARD:
        L[1] = div(L[1], 4)
    palam_vabc_estimate(ctx, L, 1, -1)
    _no_mob_sp(ctx, 1)
    sexmsg.msg_spcom1(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 8)
    ex = st.temp.ex_com
    if ex & V:
        add_exp(ctx, c, "Ｖ経験", 3)
    if ex & A:
        add_exp(ctx, c, "Ａ経験", 2)
    if (ex & V) or (ex & A):
        _incest_exp(ctx)
    ju = _a(ctx, "従順")  # :108–116（== 2 から：0／1 は 0 のまま）
    _set(L, 5, {2: 200, 3: 500, 4: 1000}.get(ju, 2000 if ju >= 5 else None))
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (10, 20, 50, 100, 200, 500)))
    if c.palam[10] < 1000:
        L[10] += 5000
    elif c.palam[10] < 2000:
        L[10] += 1000
    _set(L, 11, {0: 2000, 1: 1000, 2: 500, 3: 200, 4: 100}.get(_a(ctx, "Ｖ感覚")))
    if c.base[31] > 0:
        L[11] = div(L[11], 2)
    if c.base[31] > 0:
        L[10] = 0
    _comex(ctx, L, V, 2)
    _pkousoku_branch(ctx, part_a=False)
    st.tflag[20] = 1001
    L[6] += 2000
    L[8] += 4000
    L[10] += 1000
    L[11] += 1000
    _finish(ctx, "SEX_SPCOM1", L, 200)
    return 1


def sex_spcom2(ctx: Ctx) -> SexGen:
    """`SEX_SPCOM2.ERB@SEX_SPCOM2`:7–253（A攻めSP）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, A)
    if c.cflag[42] == 398 and st.temp.cloth[INNER_PER] > 0 and (st.temp.ex_com & V):  # :16–20
        st.temp.ex_com -= V
    if config_check_other(st, 4) > 0 and (st.temp.ex_com & V):
        st.temp.ex_com -= V
    yield from _maybe_auto_v(ctx, need_v=True)  # :23–24
    if c.base[32] <= 0:  # :27–35
        st.tflag[4] |= A
        st.temp.insert |= A
    ex = st.temp.ex_com
    vg = c.tcvarn[2] == P_V_GUARD
    if (ex & V) and not vg and c.base[31] <= 0:
        st.tflag[4] |= V
        st.temp.insert |= V
    _penis_pos(ctx, A)  # :38–39
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 450)
    _size(ctx, 1002)
    if t(ctx, c, "処女") > 0 and (ex & 2) and not vg and c.base[31] <= 0:  # :57–62
        L[10] = 10000
        lostvirgin(ctx)
    else:
        L[10] = 0
    _set(L, 2, _tbl(_a(ctx, "Ａ感覚"), (1000, 2000, 4000, 10000, 20000, 40000)))
    palam_vabc_estimate(ctx, L, 2, -1)
    _no_mob_sp(ctx, 2)
    sexmsg.msg_spcom2(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 8)
    ex = st.temp.ex_com
    if ex & V:
        add_exp(ctx, c, "Ｖ経験", 2)
    if ex & A:
        add_exp(ctx, c, "Ａ経験", 3)
    add_exp(ctx, c, "フェラ経験", 1)
    add_exp(ctx, c, "苦痛快楽経験", 1)
    if (ex & V) or (ex & A):
        _incest_exp(ctx)
    aa = _a(ctx, "Ａ感覚")
    _set(L, 8, _tbl(aa, (200, 400, 1000, 2000, 4000, 9000 + aa * 200)))
    lub = c.palam[10]
    if aa < 3:  # :127–143
        L[10] += 50000 if lub < 100 else 5000 if lub < 10000 else 500
    else:
        L[10] += 5000 if lub < 100 else 500 if lub < 10000 else 50
    _set(L, 11, {0: 10000, 1: 5000, 2: 2000, 3: 1000, 4: 500}.get(aa))
    _set(L, 6, _tbl(_a(ctx, "技巧"), (100, 200, 500, 1000, 2000, 5000)))
    L[5] = _le2(_a(ctx, "従順"), _KYOUJUN)
    _houshi_bonus(ctx, L)
    if c.base[32] > 0:
        L[10] = div(L[10], 2)
    if c.base[32] > 0:
        L[11] = div(L[11], 2)
    _comex(ctx, L, A, 2)
    _pkousoku_branch(ctx, part_a=True)
    st.tflag[20] = 1002
    L[6] += 1500
    L[8] += 2000
    L[10] += 1000
    L[11] += 1000
    _finish(ctx, "SEX_SPCOM2", L, 200)
    return 1


def sex_spcom3(ctx: Ctx) -> None:
    """`SEX_SPCOM3.ERB@SEX_SPCOM3`:7–111（B攻めSP）。"""
    st = ctx.state
    _random(ctx, B)
    st.tflag[4] |= B
    if st.rng.rand(100) < 75:
        st.tflag[4] = 0
    _penis_pos(ctx, B)  # :22–23
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 250)
    _size(ctx, 1003)
    _set(L, 3, _tbl(_a(ctx, "Ｂ感覚"), (1000, 2000, 4000, 10000, 20000, 40000)))
    _comex(ctx, L, B, 2)
    palam_vabc_estimate(ctx, L, 3, -1)
    _no_mob_sp(ctx, 3)
    sexmsg.msg_spcom3(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 8)
    st.tflag[17] = -1
    st.tflag[20] = 1003
    L[6] += 1500
    L[8] += 2000
    L[10] += 2000
    L[11] += 1000
    _finish(ctx, "SEX_SPCOM3", L, 200)


def sex_spcom4(ctx: Ctx) -> None:
    """`SEX_SPCOM4.ERB@SEX_SPCOM4`:7–96（電撃）。EX_COM／SH_COM は変更しない（前回値のまま：原作どおり）。"""
    st = ctx.state
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 10)
    _size(ctx, 1004)
    palam_vabc_estimate(ctx, L, -1)
    _no_mob_sp(ctx, 4)
    sexmsg.msg_spcom4(ctx)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 20)
    _set(L, 8, _tbl(_a(ctx, "マゾっ気"), (500, 1000, 2000, 5000, 10000, 20000)))
    lowm = _a(ctx, "マゾっ気") < 4
    if _a(ctx, "従順") < 4:  # :55–67
        L[11] = 10000 if lowm else 1000
    else:
        L[11] = 1000 if lowm else 100
    st.tflag[17] = -1
    st.tflag[20] = 1004
    L[8] += 5000
    L[10] += 20000
    L[11] += 2000
    _finish(ctx, "SEX_SPCOM4", L, 100)


def sex_spcom5(ctx: Ctx) -> None:
    """`SEX_SPCOM5.ERB@SEX_SPCOM5`:7–167（パイズリ）。"""
    st = ctx.state
    c = tc(ctx)
    _random(ctx, B)
    st.tflag[4] |= HAND
    st.tflag[4] |= MOUTH
    st.tflag[4] |= B
    if st.rng.rand(100) < 50:
        st.tflag[4] = 0
    _penis_pos(ctx, MOUTH)  # :24–25
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 450)
    _size(ctx, 1005)
    _set(L, 3, _tbl(_a(ctx, "Ｂ感覚"), (200, 1000, 2000, 4000, 10000, 20000)))
    palam_vabc_estimate(ctx, L, 3, -1)
    _no_mob_sp(ctx, 5)
    sexmsg.msg_spcom5(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 4)
    add_exp(ctx, c, "フェラ経験", 1)
    L[5] = _le2(_a(ctx, "従順"), _KYOUJUN)
    _set(L, 6, _tbl(_a(ctx, "技巧"), (500, 1000, 2000, 5000, 10000, 20000)))
    _set(L, 8, _tbl(_a(ctx, "従順"), (400, 1000, 2000, 4000, 10000, 20000)))
    _houshi_bonus(ctx, L)
    _comex(ctx, L, B, 2)
    st.tflag[17] = -1
    st.tflag[20] = 1005
    L[6] += 2500
    L[7] += 1000
    L[8] += 5000
    L[10] += 1000
    L[11] += 1000
    _finish(ctx, "SEX_SPCOM5", L, 300)


def sex_spcom6(ctx: Ctx) -> None:
    """`SEX_SPCOM6.ERB@SEX_SPCOM6`:8–45（強制自慰）。自慰本体は SELF_KIND（`self_kind.py`、ARG:1 = 0）。"""
    st = ctx.state
    L = _begin(ctx)
    st.tflag[3] += 50
    tentacle_syasei_up(ctx, 50)
    _size(ctx, 1006)
    palam_vabc_estimate(ctx, L, -1)
    _no_mob_sp(ctx, 6)
    sexmsg.msg_spcom6(ctx)
    set_tentacle_pool(ctx)
    st.tflag[17] = -1
    st.tflag[20] = 1006
    from .self_kind import self_kind

    self_kind(ctx, st.target, 0)  # :45


def sex_spcom7(ctx: Ctx) -> SexGen:
    """`SEX_SPCOM7.ERB@SEX_SPCOM7`:7–108（羞恥プレイ）。地の文の INPUTS（CFLAG:34 > 0）のためジェネレータ。"""
    st = ctx.state
    c = tc(ctx)
    L = _begin(ctx)
    st.tflag[3] += 50
    tentacle_syasei_up(ctx, 100)
    _size(ctx, 1007)
    palam_vabc_estimate(ctx, L, -1)
    _no_mob_sp(ctx, 7)
    yield from sexmsg.msg_spcom7(ctx)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 4)
    add_exp(ctx, c, "露出快楽経験", 1)
    ro = _a(ctx, "露出癖")
    _set(L, 7, _tbl(ro, (50, 100, 200, 500, 1000, 2000)))
    _set(L, 9, _tbl(ro, (2000, 2500, 3500, 4500, 5000, 5500)))
    _set(L, 11, _tbl(ro, (2000, 1000, 500, 200, 100, 50)))
    if ro >= 2:  # :89–97
        L[7] = {2: 500, 3: 1000, 4: 2000}.get(ro, 5000)
    st.tflag[17] = -1
    st.tflag[20] = 1007
    _finish(ctx, "SEX_SPCOM7", L, 150)


def sex_spcom8(ctx: Ctx) -> None:
    """`SEX_SPCOM8.ERB@SEX_SPCOM8`:7–130（尿道攻め）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 1
    st.temp.sh_com = 0
    L = _begin(ctx)
    st.tflag[3] += 50
    tentacle_syasei_up(ctx, 50)
    _size(ctx, 1008)
    _set(L, 0, _tbl(_a(ctx, "Ｃ感覚"), (2000, 4000, 8000, 10000, 20000, 40000)))
    if is_manly(ctx) or t(ctx, c, "ふたなり") > 0:
        L[0] += 1500
    palam_vabc_estimate(ctx, L, 0, -1)
    sexmsg.msg_spcom8(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 1)
    add_exp(ctx, c, "放尿経験", 1)
    add_exp(ctx, c, "露出快楽経験", 1)
    ro = _a(ctx, "露出癖")
    L[8] = 2000 if ro < 3 else 4000 if ro == 3 else 8000 if ro == 4 else 20000
    L[9] = 2000 if ro < 3 else 800 if ro == 3 else 400 if ro == 4 else 200
    ny = exp(ctx, c, "放尿経験")  # :92–100（直前の +1 を含む）
    L[11] = 8000 if ny == 0 else 6400 if ny == 1 else 3200 if ny == 2 else 800
    st.tflag[17] = -1
    st.tflag[20] = 1008
    L[6] += 500
    L[8] += 2000
    L[9] += 400
    L[10] += 500
    L[11] += 4000
    _finish(ctx, "SEX_SPCOM8", L, 50)


def _gaping_exp_tables(ctx: Ctx, L: list[int], ex: int) -> None:
    """SPCOM9:95–139／SPCOM10:85–129：拡張経験で LOCAL:8／9／10／11。"""
    b = 0 if ex < 3 else 1 if ex < 5 else 2 if ex < 8 else 3
    L[8] = (2000, 4000, 8000, 20000)[b]
    L[9] = (200, 400, 800, 2000)[b]
    L[10] += (4000, 3200, 1600, 400)[b]
    L[11] = (8000, 6400, 3200, 800)[b]


def _gaping_sense(v: int, ex: int) -> int:
    """`IF EXP:拡張経験 < 3 / TIMES 0.10 / < 5 / 0.50 / < 8 / 0.80 / ELSE`。"""
    if ex < 3:
        return times(v, "0.10")
    if ex < 5:
        return times(v, "0.50")
    if ex < 8:
        return times(v, "0.80")
    return v


def sex_spcom9(ctx: Ctx) -> None:
    """`SEX_SPCOM9.ERB@SEX_SPCOM9`:7–188（V拡張攻め）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 2
    st.temp.sh_com = 0
    st.tflag[4] |= V
    st.temp.insert |= V
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 800)
    if st.flag[15] < st.flag[14] * 2:  # :31–32
        st.tflag[4] = 0
    _size(ctx, 1009)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (1000, 2000, 4000, 10000, 20000, 40000)))
    vx = exp(ctx, c, "Ｖ拡張経験")
    L[1] = _gaping_sense(L[1], vx)
    palam_vabc_estimate(ctx, L, 1, -1)
    sexmsg.msg_spcom9(ctx, st.temp.ex_com, st.temp.sh_com)
    if t(ctx, c, "処女") > 0:  # :70–77
        L[10] = 20000
        c.talent[ctx.data.index_of("TALENT", "処女")] = -1
        c.cflag[206] = 3
        c.tcvarn[1] = 1
    else:
        L[10] = 0
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 2)
    add_exp(ctx, c, "Ｖ経験", 5)
    _incest_exp(ctx)
    _gaping_exp_tables(ctx, L, exp(ctx, c, "Ｖ拡張経験"))
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), _SYUUTOKU_20))
    if c.palam[10] < 2000:
        L[10] += 2000
    st.tflag[17] = -1
    st.tflag[20] = 1009
    L[6] += 2000
    L[7] += 500
    L[8] += 4000
    L[10] += 1500
    L[11] += 1500
    _finish(ctx, "SEX_SPCOM9", L, 50)


def sex_spcom10(ctx: Ctx) -> None:
    """`SEX_SPCOM10.ERB@SEX_SPCOM10`:7–178（A拡張攻め）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 4
    st.temp.sh_com = 0
    st.tflag[4] |= A
    st.temp.insert |= A
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 800)
    if st.flag[15] < st.flag[14] * 2:
        st.tflag[4] = 0
    _size(ctx, 1010)
    _set(L, 2, _tbl(_a(ctx, "Ａ感覚"), (1000, 2000, 4000, 10000, 20000, 40000)))
    L[2] = _gaping_sense(L[2], exp(ctx, c, "Ａ拡張経験"))
    palam_vabc_estimate(ctx, L, 2, -1)
    sexmsg.msg_spcom10(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 2)
    add_exp(ctx, c, "Ａ経験", 5)
    _incest_exp(ctx)
    _gaping_exp_tables(ctx, L, exp(ctx, c, "Ａ拡張経験"))
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (10, 20, 50, 100, 200, 500)))
    if c.palam[10] < 2000:
        L[10] += 2000
    st.tflag[17] = -1
    st.tflag[20] = 1010
    L[6] += 2000
    L[8] += 4000
    L[9] += 500
    L[10] += 2000
    L[11] += 1000
    _finish(ctx, "SEX_SPCOM10", L, 50)


def sex_spcom11(ctx: Ctx) -> None:
    """`SEX_SPCOM11.ERB@SEX_SPCOM11`:7–187（甘えん坊授乳プレイ）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 10
    st.temp.sh_com = 0
    st.tflag[4] |= V
    st.temp.insert |= V
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 800)
    _size(ctx, 1011)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (2000, 4000, 8000, 10000, 20000, 40000)))
    _set(L, 3, _tbl(_a(ctx, "Ｂ感覚"), (3000, 4500, 6000, 8000, 16000, 20000)))
    palam_vabc_estimate(ctx, L, 1, 3, -1)
    sexmsg.msg_spcom11(ctx, st.temp.ex_com, st.temp.sh_com)
    if t(ctx, c, "処女") == 1 and check_holyvirgin(ctx) == 0:  # :72–79
        L[10] = 10000
        c.talent[ctx.data.index_of("TALENT", "処女")] = -1
        c.cflag[206] = 3
        c.tcvarn[1] = 1
    else:
        L[10] = 0
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 1)
    add_exp(ctx, c, "Ｖ経験", 5)
    add_exp(ctx, c, "奉仕快楽経験", 1)
    _incest_exp(ctx)
    if t(ctx, c, "母乳体質"):  # :97–98
        c.base[21] += c.maxbase[21]
    ju = _a(ctx, "従順")  # :101–110
    _set(L, 5, {2: 200, 3: 500, 4: 1000}.get(ju, 2000 if ju >= 5 else None))
    L[5] += min(exp(ctx, c, "出産経験") * 100, 2000)
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), (10, 20, 50, 100, 200, 500)))
    if c.palam[10] < 2000:
        L[10] += 1000
    _set(L, 11, {0: 2000, 1: 1000, 2: 500, 3: 200, 4: 100}.get(_a(ctx, "Ｖ感覚")))
    _pkousoku_branch(ctx, part_a=False, virgin_check=True)
    st.tflag[20] = 1011
    L[6] += 2000
    L[7] += 500
    L[8] += 2000
    L[9] += 2000
    L[11] += 4000
    _finish(ctx, "SEX_SPCOM11", L, 200)


def sex_spcom12(ctx: Ctx) -> None:
    """`SEX_SPCOM12.ERB@SEX_SPCOM12`:7–93（ヘソ快楽攻め）。"""
    st = ctx.state
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 100)
    _size(ctx, 1012)
    palam_vabc_estimate(ctx, L, -1)
    sexmsg.msg_spcom12(ctx, st.temp.ex_com, st.temp.sh_com)
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 5)
    _set(L, 8, _tbl(_a(ctx, "マゾっ気"), (2000, 4000, 6000, 8000, 16000, 24000)))
    lowm = _a(ctx, "マゾっ気") < 4
    if _a(ctx, "従順") < 4:
        L[11] = 20000 if lowm else 2000
    else:
        L[11] = 2000 if lowm else 200
    st.tflag[17] = -1
    st.tflag[20] = 1012
    L[7] += 10000
    L[8] += 5000
    L[11] += 2000
    _finish(ctx, "SEX_SPCOM12", L, 1050)


def sex_spcom13(ctx: Ctx) -> None:
    """`SEX_SPCOM13.ERB@SEX_SPCOM13`:7–325（丸飲み精液攻め：Ｐ触手）。"""
    from .ninsin import ninsin_hantei

    st = ctx.state
    c = tc(ctx)
    L = _begin(ctx)
    _size(ctx, 1013)
    add12 = 0
    if st.tflag[23] == 0:  # :18–54 準備
        sexmsg.msg_spcom13_pre(ctx, st.temp.ex_com, st.temp.sh_com)
        if t(ctx, c, "触手の虜"):
            L[7] = 1500
        else:
            L[11] = 1500
        L[4] = 0
        L[8] += 200
    elif (c.tcvarn[12] & KIZETU) or st.rng.rand(100) < 20 + st.tflag[23] * 15:  # :56–247 丸飲み
        female = is_female(ctx.data, c)
        if female:
            st.tflag[4] |= V
            st.tflag[4] |= WAREME
            st.temp.insert |= V
        for bit in (A, B, HAND, MOUTH):
            st.tflag[4] |= bit
        st.temp.insert |= A
        tentacle_syasei_up(ctx, 1000)
        if female:
            _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (400, 1000, 2000, 4000, 10000, 20000)))
        _set(L, 2, _a_sense(ctx, (80, 500, 2000, 4000, 10000, 20000), (400, 1000, 2000, 4000, 10000, 20000)))
        palam_vabc_estimate(ctx, L, 1, 2, -1)
        sexmsg.msg_spcom13(ctx, st.temp.ex_com, st.temp.sh_com)
        st.tflag[23] = -1  # :133
        cloth_battle_damage(ctx, 25)  # TFLAG:23 == -1 なので CLOTH_BATTLE_DAMAGE は即 RETURN（:197 付近）
        if female:
            add_exp(ctx, c, "Ｖ経験", 5)
        add_exp(ctx, c, "Ａ経験", 5)
        add_exp(ctx, c, "フェラ経験", 5)
        add_exp(ctx, c, "精液経験", 20)
        _incest_exp(ctx, 2)
        L[4] = 10000
        _set(L, 8, _tbl(_a(ctx, "精液中毒"), (2000, 4000, 6000, 8000, 16000, 24000)))
        if t(ctx, c, "処女") > 0:  # :170–177
            L[10] = 10000
            c.talent[ctx.data.index_of("TALENT", "処女")] = -1
            c.cflag[206] = 3
            c.tcvarn[1] = 1
        else:
            L[10] = 0
        L[5] = _le2(_a(ctx, "従順"), _KYOUJUN)
        _set(L, 6, _tbl(_a(ctx, "奉仕精神"), _SYUUTOKU_20))
        lows = _a(ctx, "精液中毒") < 4
        if _a(ctx, "従順") < 4:
            L[11] = 20000 if lows else 2000
        else:
            L[11] = 2000 if lows else 200
        L[7] += 10000
        L[8] += 5000
        L[9] += 500
        L[11] += 2000
        add12 = 1050
        if female:  # :242–243
            ninsin_hantei(ctx, 5, 3)
        c.base[0] = 0  # :246–247
        c.base[1] = 0
    else:  # :248–314 失敗
        st.tflag[3] += 200
        sexmsg.msg_spcom13_miss(ctx, st.temp.ex_com, st.temp.sh_com)
        cloth_battle_damage(ctx, 10)
        add_exp(ctx, c, "精液経験", 2)
        L[4] = 200
        _set(L, 8, _tbl(_a(ctx, "精液中毒"), (200, 400, 1000, 2000, 3000, 4000)))
        lows = _a(ctx, "精液中毒") < 4
        if _a(ctx, "従順") < 4:
            L[11] = 1000 if lows else 100
        else:
            L[11] = 500 if lows else 50
        L[6] += 100
        L[8] += 200
        L[9] += 200
        add12 = 300
    set_tentacle_pool(ctx)
    st.tflag[17] = -1
    st.tflag[20] = 1013
    _finish(ctx, "SEX_SPCOM13", L, add12)


def sex_spcom14(ctx: Ctx) -> None:
    """`SEX_SPCOM14.ERB@SEX_SPCOM14`:7–140（催眠姦）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 2
    st.temp.sh_com = 0
    st.tflag[4] |= V
    st.temp.insert |= V
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 800)
    _size(ctx, 1014)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (1000, 2000, 4000, 10000, 20000, 40000)))
    palam_vabc_estimate(ctx, L, 1, -1)
    sexmsg.msg_spcom14(ctx, st.temp.ex_com, st.temp.sh_com)
    if t(ctx, c, "処女") > 0:  # :56–63
        L[10] = 10000
        c.talent[ctx.data.index_of("TALENT", "処女")] = -1
        c.cflag[206] = 3
        c.tcvarn[1] = 1
    else:
        L[10] = 0
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 2)
    add_exp(ctx, c, "Ｖ経験", 3)
    _incest_exp(ctx)
    _set(L, 6, _tbl(_a(ctx, "奉仕精神"), _SYUUTOKU_20))
    if c.palam[10] < 2000:
        L[10] += 2000
    _pkousoku_branch(ctx, part_a=False)
    st.tflag[20] = 1014
    L[7] += 1000
    L[8] += 3000
    L[9] += 3000
    _finish(ctx, "SEX_SPCOM14", L, 500)


def sex_spcom15(ctx: Ctx) -> None:
    """`SEX_SPCOM15.ERB@SEX_SPCOM15`:7–159（サブミッションファック）。"""
    st = ctx.state
    c = tc(ctx)
    st.temp.ex_com = 2
    st.temp.sh_com = 0
    st.tflag[4] |= V
    st.tflag[4] |= MOUTH
    st.temp.insert |= V
    L = _begin(ctx)
    st.tflag[3] += 100
    tentacle_syasei_up(ctx, 800)
    if st.flag[15] < st.flag[14] * 2:
        st.tflag[4] = 0
    _size(ctx, 1015)
    _set(L, 1, _tbl(_a(ctx, "Ｖ感覚"), (1000, 2000, 4000, 10000, 20000, 40000)))
    m = _a(ctx, "マゾっ気")  # :53–60
    if m == 3:
        L[1] += 1000
    elif m == 4:
        L[1] += 2000
    elif m >= 5:
        L[1] += 6000
    palam_vabc_estimate(ctx, L, 1, -1)
    sexmsg.msg_spcom15(ctx, st.temp.ex_com, st.temp.sh_com)
    if t(ctx, c, "処女") > 0:
        L[10] = 10000
        c.talent[ctx.data.index_of("TALENT", "処女")] = -1
        c.cflag[206] = 3
        c.tcvarn[1] = 1
    else:
        L[10] = 0
    set_tentacle_pool(ctx)
    cloth_battle_damage(ctx, 2)
    add_exp(ctx, c, "Ｖ経験", 3)
    add_exp(ctx, c, "苦痛快楽経験", 2)
    _incest_exp(ctx)
    _set(L, 8, _tbl(m, (2000, 4000, 6000, 8000, 16000, 24000)))
    if _a(ctx, "従順") < 4:  # :111–125
        L[11] = 20000 if m <= 2 else 10000 if m == 3 else 2000
    else:
        L[11] = 1500 if m < 4 else 200
    if c.palam[10] < 2000:
        L[10] += 2000
    st.tflag[17] = -1
    st.tflag[20] = 1015
    L[6] += 2000
    L[7] += 500
    L[10] += 15000
    L[11] += 1500
    _finish(ctx, "SEX_SPCOM15", L, 1050)


# --- SEX_COMABLE.ERB ------------------------------------------------------------------

_COM_FUNCS = {
    0: sex_com0, 1: sex_com1, 2: sex_com2, 4: sex_com4, 6: sex_com6, 7: sex_com7, 8: sex_com8, 9: sex_com9,
    10: sex_com10, 11: sex_com11, 12: sex_com12, 13: sex_com13, 14: sex_com14, 15: sex_com15, 16: sex_com16,
    18: sex_com18, 19: sex_com19, 20: sex_com20,
}
_COM_GENS = {3: sex_com3, 5: sex_com5, 17: sex_com17}
_SP_FUNCS = {
    1000: sex_spcom0, 1003: sex_spcom3, 1004: sex_spcom4, 1005: sex_spcom5, 1006: sex_spcom6,
    1008: sex_spcom8, 1009: sex_spcom9, 1010: sex_spcom10, 1011: sex_spcom11, 1012: sex_spcom12,
    1013: sex_spcom13, 1014: sex_spcom14, 1015: sex_spcom15,
}
_SP_GENS = {1001: sex_spcom1, 1002: sex_spcom2, 1007: sex_spcom7}


def _run(ctx: Ctx, n: int, local: int) -> SexGen:
    """`CALL SEX_COM{n}, FLAG:11, LOCAL` ／ `CALL SEX_SPCOM{n-1000}`。"""
    st = ctx.state
    if n in _COM_GENS:
        yield from _COM_GENS[n](ctx, st.flag[11], local)
    elif n in _COM_FUNCS:
        _COM_FUNCS[n](ctx, st.flag[11], local)
    elif n in _SP_GENS:
        yield from _SP_GENS[n](ctx)
    elif n in _SP_FUNCS:
        _SP_FUNCS[n](ctx)
    else:
        raise KeyError(n)
    return 1


def _clear_kyoukousoku(ctx: Ctx) -> None:
    v = tc(ctx).tcvarn
    if v[12] & KYOUKOUSOKU:
        v[12] -= KYOUKOUSOKU


def sex_comable(ctx: Ctx, arg: int) -> SexGen:
    """`@SEX_COMABLE, ARG`:5–593。戻り値は RESULT（0 = 実行しなかった）。TFLAG:10 に実行するコマンド番号。"""
    st = ctx.state
    c = tc(ctx)
    cl = st.temp.cloth
    no_inner, outer_per, inner_per, inner_def = cl[NO_INNER], cl[OUTER_PER], cl[INNER_PER], cl[INNER_DEF]
    if _mob(ctx):  # :17–23
        raise NotImplementedError("雑魚敵／クズ市民の追加責め部位指定（SEXCOM_OPTION_MOB_*）は未移植")
    local = 0
    if c.cflag[42] == 398 and no_inner == 0 and arg in (5, 1002, 1010):  # :29–33 前貼り
        inner_def = 100
    st.tflag[10] = arg
    male = is_male(ctx.data, c)
    otokonoko = t(ctx, c, "男の娘") > 0
    hole = is_hole(ctx)
    holy = lambda: check_holyvirgin(ctx) == 1  # noqa: E731
    cruel = config_check_maniac(st, 14)
    kizetu = c.tcvarn[12] & KIZETU
    breakable = outer_per > 90 or inner_per > inner_def
    breakable_half = outer_per > 90 or inner_per > div(inner_def, 2)

    def go(n: int, tf10: int | None = None) -> SexGen:
        if tf10 is not None:
            st.tflag[10] = tf10
        return (yield from _run(ctx, n, local))

    if arg == 0:
        yield from go(0)
    elif arg in (1, 3, 5, 7) and breakable:  # :42／:64／:97／:115 衣装破壊を優先
        yield from go(14, 14)
    elif arg == 1:
        yield from go(1)
    elif arg == 2:  # :49–60
        if otokonoko:
            yield from go(4, 0)
        elif male:
            yield from go(0, 0)
        else:
            yield from go(2)
    elif arg == 3:  # :68–83
        if otokonoko:
            yield from go(5, 1)
        elif male:
            yield from go(1, 1)
        elif holy():
            yield from go(2, 2)
        else:
            yield from go(3)
    elif arg == 4:
        yield from (go(0, 0) if not hole else go(4))
    elif arg == 5:
        yield from (go(1, 1) if not hole else go(5))
    elif arg == 6:
        yield from go(6)
    elif arg == 7:
        yield from (go(0, 0) if not hole else go(7))
    elif arg == 8:
        yield from go(8)
    elif arg == 9:
        yield from (go(8, 8) if cruel == 0 else go(9))
    elif arg == 10:
        yield from (go(0, 0) if kizetu else go(10))
    elif arg == 11:
        yield from (go(8, 8) if not hole else go(11))
    elif arg == 12:
        if not hole:
            yield from go(8, 8)
        elif cruel == 0:
            yield from go(11, 11)
        else:
            yield from go(12)
    elif arg == 13:
        yield from go(13)
    elif arg == 14:  # :174–181（RAND は短絡：前半が真のときだけ引く）
        if breakable and st.rng.rand(100) < 70:
            yield from go(14)
        elif (outer_per > 90 or inner_per > 0) and st.rng.rand(100) < 15:
            yield from go(14)
        else:
            return 0
    elif arg in (15, 16):  # :183–235
        fin = arg == 16
        if otokonoko:
            _clear_kyoukousoku(ctx)
            yield from go(18 if fin else 17, 1)
        elif male or holy():
            _clear_kyoukousoku(ctx)
            yield from go(1, 1)
        else:
            yield from go(arg)
    elif arg in (17, 18):  # :237–259
        if not hole:
            _clear_kyoukousoku(ctx)
            yield from go(1, 1)
        else:
            yield from go(arg)
    elif arg in (19, 20):  # :261–307
        fin = arg == 20
        e = st.charas[st.flag[111]]
        if male or (st.flag[110] == 1 and t(ctx, e, "寄生") == 0):
            if st.tflag[20] == 15:
                yield from go(16 if fin else 15, 16 if fin else 15)
            elif st.tflag[20] == 17:
                yield from go(18 if fin else 17, 18 if fin else 17)
            else:
                _clear_kyoukousoku(ctx)
                yield from go(1, 1)
        elif holy():
            yield from go(18 if fin else 17, 18 if fin else 17)
        else:
            yield from go(arg)
    elif arg in (1000, 1001, 1002, 1008, 1009, 1010, 1011, 1012, 1014, 1015) and breakable_half and \
            arg != 1012:  # 衣装破壊を優先（:311 等、INNER_DEF / 2）
        yield from go(14, 14)
    elif arg == 1012 and breakable_half:  # :504
        yield from go(14, 14)
    elif arg == 1000:
        yield from go(1000)
    elif arg == 1001:  # :324–339
        if otokonoko:
            yield from go(5, 1)
        elif male or holy():
            yield from go(1, 1)
        else:
            yield from go(1001)
    elif arg == 1002:  # :348–358
        if not hole:
            yield from go(1000, 1000)
        elif c.cflag[41] == 299 and c.cflag[1] > 0:
            yield from go(5, 5)
        else:
            yield from go(1002)
    elif arg == 1003:  # :363–373
        if outer_per > 90:
            yield from go(14, 14)
        elif not hole:
            yield from go(6, 6)
        else:
            yield from go(1003)
    elif arg == 1004:
        yield from go(1004)
    elif arg == 1005:
        yield from (go(7, 7) if male else go(1005))
    elif arg == 1006:
        yield from (go(0, 0) if kizetu else go(1006))
    elif arg == 1007:
        if kizetu:
            yield from go(0, 0)
        elif not hole:
            yield from go(1, 1)
        else:
            yield from go(1007)
    elif arg == 1008:  # :416–421
        if c.base[30] > 0 or st.tflag[20] < 0:
            yield from go(1000, 1000)
        else:
            yield from go(1008)
    elif arg == 1009:  # :430–452（:447 の 2 つ目の聖処女分岐には到達しない）
        if otokonoko:
            yield from go(5, 1)
        elif male or holy():
            yield from go(1, 1)
        elif c.base[31] > 0 or st.tflag[20] < 0:
            yield from go(1001, 1001)
        else:
            yield from go(1009)
    elif arg == 1010:  # :461–474
        if not hole:
            yield from go(1000, 1000)
        elif c.cflag[41] == 299 and c.cflag[1] > 0:
            yield from go(5, 5)
        elif c.base[32] > 0 or st.tflag[20] < 0:
            yield from go(1002, 1002)
        else:
            yield from go(1010)
    elif arg == 1011:  # :483–499（RAND は短絡）
        if otokonoko:
            yield from go(7, 1)
        elif male:
            yield from go(1, 1)
        elif c.base[33] > 0 or (st.tflag[20] < 0 and st.rng.rand(2) == 0):
            yield from go(1005, 1005)
        elif c.base[31] > 0 or st.tflag[20] < 0:
            yield from go(1001, 1001)
        else:
            yield from go(1011)
    elif arg == 1012:  # :508–512
        yield from (go(8, 8) if cruel == 0 else go(1012))
    elif arg == 1013:  # :517–533
        if outer_per > 90:
            yield from go(14, 14)
        elif not hole:
            yield from go(1000, 1000)
        elif c.base[31] > 0 or (st.tflag[20] < 0 and st.rng.rand(2) == 0):
            yield from go(1001, 1001)
        elif c.base[32] > 0 or st.tflag[20] < 0:
            yield from go(1002, 1002)
        else:
            yield from go(1013)
    elif arg == 1014:  # :542–563
        if otokonoko:
            yield from go(5, 1)
        elif male or holy():
            yield from go(1, 1)
        elif c.base[31] > 0 or st.tflag[20] < 0:
            yield from go(1001, 1001)
        elif kizetu and t(ctx, c, "交際相手") == 0:
            yield from go(1001, 1001)
        else:
            yield from go(1014)
    elif arg == 1015:  # :572–586
        if otokonoko:
            yield from go(5, 1)
        elif male:
            yield from go(1, 1)
        elif c.base[31] > 0 or cruel == 0 or kizetu or st.tflag[20] < 0:
            yield from go(1001, 1001)
        else:
            yield from go(1015)
    elif 2000 <= arg <= 2999:  # :589–591（雑魚敵専用：ボス戦では何もしない）
        pass
    return 1


# --- ENEMY_ACTION_SEX_ROUTINE（ENEMY_ACTION.ERB:1162–1430）------------------------------


def boss_sex_routine(ctx: Ctx, boss: int) -> int:
    """`TENTACLE_BOSS_{n}_SEX_ROUTINE`（触手データ/ボス触手/TENTACLE_BOSS_{n}_*.ERB）。RETURN の無い終端は 0。"""
    st = ctx.state
    c = tc(ctx)
    rand = st.rng.rand
    if boss == 1:  # TENTACLE_BOSS_1_Ｃ触手.ERB:137–161
        if rand(100) < 12:
            return 14
        lo = rand(100)
        for b, r in ((20, 0), (35, 1), (40, 1000), (45, 2), (55, 3), (60, 11), (75, 1008)):
            if lo < b:
                return r
        return -1
    if boss == 2:  # TENTACLE_BOSS_2_Ｖ触手.ERB:137–167（SIF の RAND は左から評価）
        if rand(3) == 0 and t(ctx, c, "男の娘") > 0:
            return 11
        if rand(2) == 0 and t(ctx, c, "男の娘") > 0:
            return 12
        if is_male(ctx.data, c):
            return 0
        lo = rand(100)
        if lo < 60 and c.palam[10] < 2000:
            return 2
        for b, r in ((10, 2), (40, 3), (55, 1001), (70, 1009), (75, 11), (80, 12)):
            if lo < b:
                return r
        return -1
    if boss == 3:  # TENTACLE_BOSS_3_Ａ触手.ERB:137–175
        lo = rand(100)
        for b, r in ((32, 4), (51, 5), (59, 1002), (64, 1010), (69, 2), (74, 1)):
            if lo < b:
                return r
        if config_check_other(st, 4) > 0:
            lo = rand(100)
            for b, r in ((22, 8), (44, 9), (66, 10), (84, 11), (88, 1004), (92, 1006), (96, 1007)):
                if lo < b:
                    return r
            return 1010
        return 0  # :175 ENDIF の後は関数終端（RESULT = 0：Process.ScriptProc.cs:61–67）
    if boss == 4:  # TENTACLE_BOSS_4_Ｂ触手.ERB:137–169
        if rand(100) < 15:
            return 14
        lo = rand(100)
        if st.tflag[0] > 10 and lo < 25:
            return 1011
        for b, r in ((15, 6), (30, 7), (35, 1003), (45, 1005), (55, 1011), (60, 2), (65, 3), (70, 11), (75, 12)):
            if lo < b:
                return r
        return -1
    if boss == 5:  # TENTACLE_BOSS_5_Ｓ触手.ERB:140–170
        if rand(100) < 5:
            return 14
        lo = rand(100)
        if c.base[0] == 0 and c.base[1] == 0 and lo < 40:
            return 3
        if lo < 15 and st.tflag[0] > 5:
            return 1012
        if lo < 20:
            return 8
        if lo < 35 and check_holyvirgin(ctx) == 0:
            return 9
        for b, r in ((40, 1004), (45, 2), (55, 11), (80, 12), (85, 13)):
            if lo < b:
                return r
        return -1
    if boss == 6:  # TENTACLE_BOSS_6_Ｐ触手.ERB:146–178
        if rand(100) < 12:
            return 14
        lo = rand(100)
        if c.base[2] == 0 and st.tflag[23] in (0, 100):
            return 1013
        # :156 `TFLAG:23 && RAND:100 < 90 - TFLAG:23 * 5`（TFLAG:23 が 0 なら RAND を引かない）
        if st.tflag[23] and rand(100) < 90 - st.tflag[23] * 5:
            return 1013
        for b, r in ((20, 10), (35, 11), (40, 1005), (45, 2), (50, 3), (60, 5), (70, 12), (75, 13)):
            if lo < b:
                return r
        return -1
    if boss == 7:  # TENTACLE_BOSS_7_Ｈ触手.ERB:141–175
        if rand(100) < 25:
            return 14
        lo = rand(100)
        # :147 `(TCVARn:12 & 恍惚) && RAND:100 < 50`（短絡）
        if (c.tcvarn[12] & KOUKOTSU) and rand(100) < 50:
            return 1014
        for b, r in ((5, 0), (15, 1006), (30, 1007), (40, 6), (43, 2), (50, 3), (60, 11), (70, 12), (75, 13),
                     (85, 1014)):
            if lo < b:
                return r
        return -1
    raise NotImplementedError(f"TENTACLE_BOSS_{boss}_SEX_ROUTINE は未移植")


def lastboss_sex_routine(ctx: Ctx, n: int) -> int:
    """`TENTACLE_LASTBOSS_1_SEX_ROUTINE`（TENTACLE_LASTBOSS_1_Ｋ触手.ERB:158–180）。"""
    if n != 1:
        raise NotImplementedError(f"TENTACLE_LASTBOSS_{n}_SEX_ROUTINE は未移植")
    lo = ctx.state.rng.rand(100)
    for b, r in ((5, 1000), (10, 1001), (15, 1002), (20, 1003), (25, 1004), (30, 1005), (35, 1006), (40, 1007), (50, 1015)):
        if lo < b:
            return r
    return -1


def lastboss_reaction_ref(ctx: Ctx, n: int, arg: int = 0) -> int:
    """`TENTACLE_LASTBOSS_1_REACTION_REF, ARG`（TENTACLE_LASTBOSS_1_Ｋ触手.ERB:187–204）。"""
    if n != 1:
        raise NotImplementedError(f"TENTACLE_LASTBOSS_{n}_REACTION_REF は未移植")
    if arg == 1:
        lo = ctx.state.rng.rand(6)
        return 3 if lo < 2 else 5 if lo < 4 else 1001 if lo < 5 else 1002
    if arg == 2:
        return 15
    if arg == 3:
        return 11
    return -1


def boss_reaction_ref(ctx: Ctx, boss: int, arg: int = 0) -> int:
    """`TENTACLE_BOSS_{n}_REACTION_REF, ARG`（ARG=1 素股焦らし成功、2 失敗、3 フェラ誘発）。"""
    if boss not in range(1, 8):
        raise NotImplementedError(f"TENTACLE_BOSS_{boss}_REACTION_REF は未移植")
    if arg == 1:  # 全ボス共通（例：TENTACLE_BOSS_1_Ｃ触手.ERB:166–177）
        lo = ctx.state.rng.rand(6)
        return 3 if lo < 2 else 5 if lo < 4 else 1001 if lo < 5 else 1002
    if arg == 2:
        return 15
    if arg == 3:
        return 12 if boss == 5 else 11  # Ｓ触手のみ 12（TENTACLE_BOSS_5_Ｓ触手.ERB:188–189）
    return -1


def _akuoti_sex_routine(ctx: Ctx, select: int) -> int:
    """`@ENEMY_ACTION_SEX_ROUTINE`:1172–1343 悪堕ちキャラの性コマンド選択：敵キャラの ABL を重みにした区間
    （LOCAL:10〜16 が下限、LOCAL:0〜6 が上限。下限は累積の上限を足しこむため区間が重なり・広がる：原作どおり）で RAND:100 を
    振り、該当しなければ `GOTO SELECTED_SEXCOM_LOOP`。条件式の `&&` は短絡（reference/emuera-1824/Emuera/GameData/
    Expression/OperatorMethod.cs:524–555）なので RAND は左の条件が真のときだけ引く。"""
    st = ctx.state
    e = st.charas[st.flag[111]]
    rand = st.rng.rand
    ea = lambda n: abl(ctx, e, n)  # noqa: E731
    ek = lambda n: t(ctx, e, n)  # noqa: E731
    l10 = 0  # :1178–1182 C
    l0 = ea("Ｃ感覚") + 5
    if ea("欲望") >= 3 and ek("処女") < 1 and is_female(ctx.data, e) and is_penis(ctx):
        l0 += 25
    l11 = l10 + l0  # :1185–1187 V
    l1 = ea("Ｖ感覚") + 15 + l11
    l12 = l11 + l1  # :1190–1192 A
    l2 = ea("Ａ感覚") + 10 + l12
    l13 = l12 + l2  # :1195–1197 B
    l3 = ea("Ｂ感覚") + 10 + l13
    l14 = l13 + l3  # :1201–1203 苦痛系
    l4 = ea("マゾっ気") + 5 + l14
    l15 = l14 + l4  # :1206–1209 奉仕系
    l5 = max(0, min(ea("従順") + ea("奉仕精神"), 5)) + 10 + l15
    l16 = l15 + l5  # :1212–1215 羞恥系
    l6 = ea("露出癖") + 5 + l16
    tentacler = sexmsg.istentacler(ctx, st.flag[111]) == 1
    l101 = 1 if (tentacler or ek("ふたなり") > 0 or is_male(ctx.data, e)) else 0  # :1218–1220
    c_sp = lambda: (tentacler or (ek("処女") < 1 and is_female(ctx.data, e) and is_penis(ctx)))  # noqa: E731
    while True:  # $SELECTED_SEXCOM_LOOP（:1223）
        l99 = rand(100)
        if (select == -1 and l10 <= l99 <= l0) or select in (0, 1, 1000):  # :1227–1240 C
            if ea("欲望") >= 3 and c_sp() and rand(100) < 40 and l101:
                select = 1000
            elif rand(100) < 40 and l101:
                select = 1
            else:
                select = 0
        elif (select == -1 and l11 <= l99 <= l1) or select in (2, 3, 1001):  # :1241–1270 V
            if is_male(ctx.data, tc(ctx)):
                if ea("欲望") >= 3 and c_sp() and rand(100) < 40 and l101:
                    select = 1000
                elif rand(100) < 40 and l101:
                    select = 1
                else:
                    select = 0
            elif check_holyvirgin(ctx) == 1:
                select = 2
            elif rand(100) < 40 and l101 and ea("欲望") >= 3:
                select = 1001
            elif rand(100) < 40 and l101:
                select = 3
            else:
                select = 2
        elif (select == -1 and l12 <= l99 <= l2) or select in (4, 5, 1002):  # :1271–1284 A
            if rand(100) < 40 and l101 and ea("欲望") >= 3 and tentacler:
                select = 1002
            elif rand(100) < 40 and l101:
                select = 5
            else:
                select = 4
        elif (select == -1 and l13 <= l99 <= l3) or select in (6, 7, 1003):  # :1285–1298 B
            if rand(100) < 40 and l101 and ea("欲望") >= 3:
                select = 1003
            elif rand(100) < 40 and l101:
                select = 7
            else:
                select = 6
        elif (select == -1 and l14 <= l99 <= l4) or select in (8, 9, 1004):  # :1299–1312 苦痛系
            if rand(100) < 40 and tentacler and ea("マゾっ気") >= 3:
                select = 1004
            elif rand(100) < 40 and tentacler:
                select = 9
            else:
                select = 8
        elif ((select == -1 and l15 <= l99 <= l5) or select in (10, 11, 12, 1005)) and l101:  # :1313–1329 奉仕系
            if rand(100) < 40 and l101 and ea("従順") + ea("奉仕精神") >= 3:
                select = 1005
            elif rand(100) < 20:
                select = 12
            elif rand(100) < 40:
                select = 11
            else:
                select = 10
        elif (select == -1 and l16 <= l99 <= l6) or select in (1006, 1007):  # :1330–1339 羞恥系
            if rand(100) < 40 and ea("露出癖") >= 3:
                select = 1007
            else:
                select = 1006
        else:  # :1340–1342
            select = -1
            continue
        return select


def enemy_action_sex_routine(ctx: Ctx) -> int:
    """`@ENEMY_ACTION_SEX_ROUTINE`:1162–1430（触手と悪堕ちキャラ（:1172–1343）による性コマンドの選択）。"""
    st = ctx.state
    c = tc(ctx)
    rand = st.rng.rand
    select = -1
    if st.tflag[17] >= 0:  # :1168–1169
        select = st.tflag[17]
    if st.tflag[10] < 15 or st.tflag[10] > 20:  # :1170–1171 VARSET INSERT
        st.temp.insert = 0
    if _akuoti(ctx) and c.tcvarn[0] == 0:
        return _akuoti_sex_routine(ctx, select)
    if c.tcvarn[0] != 0:
        return select
    if c.tcvarn[40] == 1 and select < 0:  # :1349–1350
        select = 13
    if rand(100) < 8 and select < 0:  # :1353–1354（RAND を先に引く）
        select = 14
    if select < 0:  # :1357–1360 専用ルーチン（TENTACLE_ACCESS "SEX_ROUTINE"）
        from .core import _is_lastboss_access, boss_data

        boss_data(st)  # ボス・ラスボス 1 以外は停止
        if _is_lastboss_access(st):  # TENTACLE_ACCESS:303（S27）
            select = lastboss_sex_routine(ctx, st.flag[11])
        else:
            select = boss_sex_routine(ctx, st.flag[11])
    if select < 0:  # :1363–1428 汎用ルーチン
        n = 13
        while True:  # $TENTACLE_HANYOU_COMMOND
            lo = rand(n * 10)
            if lo < n:
                select = 0
            elif lo < n + div(n, 2):
                select = 1
            elif lo < n * 2 + div(n, 2):
                select = 2
            elif lo < n * 3:
                select = 3
            elif lo < n * 4:
                select = 4
            elif lo < n * 4 + div(n, 2):
                select = 5
            elif lo < n * 5 + div(n, 2):
                select = 6
            elif lo < n * 6:
                select = 7
            elif lo < n * 7:
                if c.tcvarn[40] > 0 and rand(3):
                    continue
                select = 8
            elif lo < n * 7 + div(n, 2):
                if c.tcvarn[40] > 0 and rand(3):
                    continue
                select = 9
            elif lo < n * 8 + div(n, 2):
                select = 10
            elif lo < n * 9:
                select = 11
            elif lo < n * 10:
                if c.tcvarn[40] > 0 and rand(3):
                    continue
                select = 12
            else:
                # :1420–1422 `ELSEIF LOCAL:2 < LOCAL:0 * 10 && …`（直前と同じ上限なので到達しない）、:1423–1426 ELSE は GOTO
                continue
            break
    return select
