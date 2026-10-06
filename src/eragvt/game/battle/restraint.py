"""拘束中のヒロインのコマンド：`ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/`の COMABLE.ERB（8〜15、40、44〜47、
70、100〜104）と COMF8〜15.ERB、COMF40.ERB、COMF44〜46.ERB、COMF100〜104.ERB、地の文
`地の文/MESSAGE_BATTLE.ERB`:634–990（振り解く〜反抗する）。

路徑相對 `source/earGVP/ERB/`。ボス触手戦と洗脳／悪堕ちキャラ戦（FLAG:110 == 1、S19：敵名・MESSAGE_OTHER_*・
COM47 説得する）の分岐を移植（雑魚・市民は停止）。
ヒロイン側の性攻撃（100〜104）の地の文（`地の文/MESSAGE_SEX.ERB`:1932–2200）は catalog（無ければ chinobun）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..action import Ctx, kojo_root, print_transcallname
from ..chara_common import is_male
from ..era import div, isqrt, times
from ..tentacle import enemy_type_check
from . import mob
from .cloth import INNER_DEF, INNER_PER, OUTER_PER, cloth_battle_damage, cloth_battle_hosei
from .core import (
    DARAKU,
    KAIRAKU_TOROKE,
    KIZETU,
    KOUKOTSU,
    KUSEN,
    KYOUKOUSOKU,
    MAHI,
    P_ABARE_CRIT,
    P_ABARE_FAIL,
    P_ABARE_GUARD,
    P_HOUSHI,
    P_NASUGAMAMA,
    P_NIRAMI,
    P_SHIBORU,
    P_TAERU,
    P_UKEIRERU,
    P_V_GUARD,
    SEI_TEIKOU,
    ZETSUBOU,
    abl,
    msg_other,
    print_enemy_prefix,
    run_chinobun,
    correction_trans,
    exp,
    is_hole,
    mark,
    message_branch,
    percent_cal,
    print_distance,
    shinkyou_change,
    shinkyou_check,
    t,
    tc,
    tentacle_access,
)
from .func import act_limit

ComGen = Generator[None, int, int]

# 体勢（DIM.ERH:187–205）
P_BATOU = 7  # 罵倒する
P_HANKOU = 8  # 反抗する
P_SETTOKU = 9  # 説得する（DIM.ERH:197）
MOUTH, HAND, WAREME, BOUHATSU = 16, 32, 64, 128


def _mb(ctx: Ctx) -> int:
    return message_branch(ctx)


def _mob(ctx: Ctx) -> bool:
    st = ctx.state
    return enemy_type_check(st, "MOB") == 1 or enemy_type_check(st, "CITIZEN") == 1


def _need_boss(ctx: Ctx) -> None:
    # COMABLE.ERB@COM_ABLE103:991–1018：市民共用 MOB 型別與反應分派。
    pass


def _akuoti(ctx: Ctx) -> bool:
    return enemy_type_check(ctx.state, "AKUOTI") == 1


def _other(ctx: Ctx, name: str) -> None:
    """`SIF ENEMY_TYPE_CHECK_F("AKUOTI") == 1 / CALL MESSAGE_OTHER_BATTLE_CHARA_{name}`。"""
    if _akuoti(ctx):
        msg_other(ctx, f"BATTLE_CHARA_{name}")


def _enemy_locals(ctx: Ctx) -> tuple[str, str]:
    """MESSAGE_BATTLE.ERB の HIKIHAGASU／BATOU／PERSUADE 冒頭（:797–808 等）：(LOCALS, LOCALS:1)。
    FLAG:110 == 1 なら寄生なしでふたなり・オトコの敵は "ペニス"、それ以外 "触手"、LOCALS:1 は敵の呼び名。"""
    st = ctx.state
    if st.flag[110] == 0:
        return "触手", str(tentacle_access(ctx, "GETNAME"))
    from .sexmsg import istentacler

    e = st.charas[st.flag[111]]
    penis = istentacler(ctx, st.flag[111]) == 0 and (t(ctx, e, "ふたなり") > 0 or is_male(ctx.data, e))
    return ("ペニス" if penis else "触手"), print_transcallname(st, st.flag[111])


# --- COM_ABLE（COMABLE.ERB）-------------------------------------------------------------


def chara_sex_comable(ctx: Ctx, arg: int) -> int:
    """`@CHARA_SEX_COMABLE_F(ARG)`:1082–1111。"""
    st = ctx.state
    c = tc(ctx)
    if t(ctx, c, "触手の虜") > 0 or t(ctx, c, "淫乱") > 0:
        return 1
    local = -2 if arg == 102 else -3 if arg == 103 else -1
    if _mb(ctx) & SEI_TEIKOU:
        local += 1
    if c.palam[10] + c.palam[11] + c.palam[13] >= 3000:
        local += 1
    local += isqrt(st.tflag[0] + 1)
    return 1 if local > 0 else 0


def prison_chara(ctx: Ctx) -> int:
    """`COMF15.ERB@PRISON_CHARA`:22–29。"""
    st = ctx.state
    for i in range(st.charanum):
        if i == 0:  # MASTER
            continue
        o = st.charas[i]
        if st.flag[11] == o.cflag[21] and o.cflag[0] == 1:
            return i
    return -1


def com_able_restraint(ctx: Ctx, n: int) -> tuple[int, tuple[int, int, int] | None]:
    """拘束中専用コマンドの `@COM_ABLE{n}`（`TCVARn:8 < 10` の判定は呼び出し側で +10 している前提）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    guard = v[8] >= 10
    tt = lambda name: t(ctx, c, name)  # noqa: E731
    s12 = v[12]
    all0 = c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0
    pink = (250, 60, 250)
    if n == 8:  # :190–206
        if v[0] >= 1 or (s12 & KYOUKOUSOKU) or (s12 & KIZETU) or not guard:
            return 0, None
        if st.flag[73] > 0 and st.tflag[0] < 5:
            return 0, None
        return 1, None
    if n == 9:  # :210–232
        if v[0] >= 1 or (s12 & KYOUKOUSOKU) or (s12 & MAHI) or (s12 & KIZETU) or (s12 & KOUKOTSU):
            return 0, None
        if tt("変身能力") != 0 and c.cflag[1] == 0:
            return 0, None
        return (1 if guard else 0), None
    if n == 10:  # :236–267
        if v[0] >= 1 or all0:
            return 0, None
        mb = _mb(ctx)
        if (mb & DARAKU) or (mb & KAIRAKU_TOROKE) or (mb & ZETSUBOU):
            return 0, None
        if mark(ctx, c, "苦痛刻印") + mark(ctx, c, "恐怖刻印") > 3 and c.palam[16] + c.palam[17] > 7999:
            return 0, None
        if mark(ctx, c, "快楽刻印") + mark(ctx, c, "屈服刻印") + mark(ctx, c, "恥辱刻印") + abl(ctx, c, "欲望") > 5 and (
            c.palam[13] + c.palam[14] + div(c.palam[15], 5)
        ) > 29999:
            return 0, None
        if abl(ctx, c, "従順") + abl(ctx, c, "奉仕精神") + abl(ctx, c, "触手中毒") > 5 and c.palam[11] > 3999:
            return 0, None
        if (s12 & KIZETU) or not guard:
            return 0, None
        return 1, None
    if n == 11:  # :271–295
        if not guard:
            return 0, None
        if s12 & KIZETU:
            return 1, None
        if v[0] >= 1:
            return 0, None
        if all0:
            return 1, None
        if _mb(ctx) & KUSEN:
            return 1, None
        if st.flag[73] > 0:
            return 1, None
        if mark(ctx, c, "苦痛刻印") + mark(ctx, c, "恐怖刻印") < 4:
            return 0, None
        return 1, None
    if n == 12:  # :299–318
        if v[0] >= 1 or (s12 & KIZETU) or not guard:
            return 0, None
        if _mb(ctx) & SEI_TEIKOU:
            return 1, None
        if c.palam[13] + c.palam[14] + div(c.palam[15], 5) >= 30000:
            return 1, None
        if abl(ctx, c, "欲望") + mark(ctx, c, "快楽刻印") + mark(ctx, c, "屈服刻印") + mark(ctx, c, "恥辱刻印") < 6:
            return 0, None
        return 1, None
    if n == 13:  # :322–338
        if v[0] >= 1 or (s12 & KIZETU) or not guard:
            return 0, None
        if _mb(ctx) & DARAKU:
            return 1, None
        if abl(ctx, c, "従順") + abl(ctx, c, "奉仕精神") + abl(ctx, c, "触手中毒") < 6 or c.palam[11] < 4000:
            return 0, None
        return 1, None
    if n == 14:  # :342–358
        if is_male(ctx.data, c):
            return 0, None
        if (s12 & KYOUKOUSOKU) and st.tflag[20] in (3, 15, 19, 1001, 1011, 1014):
            return 0, None
        if v[0] >= 1 or (s12 & KIZETU) or not guard:
            return 0, None
        return 1, None
    if n == 15:  # :362–386
        if (s12 & KYOUKOUSOKU) or (s12 & KIZETU) or (s12 & KOUKOTSU) or not guard:
            return 0, None
        if st.tflag[19] != 1 and v[0] == 0 and st.tflag[2] >= 1 and prison_chara(ctx) != -1:
            return 1, None
        return 0, None
    if n == 40:  # :457–482
        if is_male(ctx.data, c) or all0 or (s12 & KYOUKOUSOKU) == 0 or v[0] >= 1:
            return 0, None
        if (s12 & KIZETU) or (s12 & MAHI) or (s12 & KOUKOTSU) or not guard:
            return 0, None
        return 1, None
    if n == 44:  # :486–520
        if tt("感情乏しい") > 0 or v[0] >= 1 or st.tflag[20] in (16, 1006) or st.temp.prevcom == 44:
            return 0, None
        if c.base[1] == 0:
            return 0, None
        mb = _mb(ctx)
        if (mb & DARAKU) or (mb & ZETSUBOU) or (s12 & KOUKOTSU) or (s12 & KIZETU) or not guard:
            return 0, None
        return 1, None
    if n in (45, 46):  # :524–617
        if n == 45 and tt("感情乏しい") > 0:
            return 0, None
        if v[0] >= 1 or st.tflag[20] in (11, 12, 16, 1006) or st.temp.prevcom == n:
            return 0, None
        if percent_cal(c.base[1], c.maxbase[1]) > 75 or (_mb(ctx) & DARAKU):
            return 0, None
        if enemy_type_check(st, "AKUOTI") > 0:  # :555–558／:602–605 相手が悪堕ちキャラなら強気な性格かどうか
            strong = tt("勝気") or tt("古風") or tt("乱暴者")
            if n == 45 and not strong:
                return 0, None
            if n == 46 and strong:
                return 0, None
        else:
            timid = tt("臆病") or tt("恥ずかしがり屋") or tt("悲観的")
            if n == 45 and timid:
                return 0, None
            if n == 46 and not timid and tt("感情乏しい") == 0:
                return 0, None
        if (s12 & KOUKOTSU) or (s12 & KIZETU) or not guard:
            return 0, None
        return 1, None
    if n == 47:  # :621–652（拘束中でなくても使える）
        if enemy_type_check(st, "AKUOTI") == 0:
            return 0, None
        if st.temp.prevcom in (1, 2, 3, 9) or st.tflag[20] in (11, 12, 16, 1006) or st.temp.prevcom == 47:
            return 0, None
        if (s12 & KOUKOTSU) or (s12 & KIZETU) or not guard:
            return 0, None
        return 1, None
    if n == 70:  # :676–698
        from .commands import _no_attack
        from .core import get_battle_situation

        if v[0] > 0:
            return 0, None
        if v[4] + v[6] < 300 and c.cflag[1] < 2:
            return 0, None
        if tt("変身能力") and c.cflag[1] == 0:
            return 0, None
        if (s12 & KIZETU) or _no_attack(ctx) or get_battle_situation(st, "EX不可") == 1 or not guard:
            return 0, None
        return 1, None
    if n in (100, 101, 102, 103, 104):  # :845–1075
        return _com_able_sex(ctx, n, guard, pink)
    raise KeyError(n)


def _com_able_sex(ctx: Ctx, n: int, guard: bool, pink: tuple[int, int, int]) -> tuple[int, tuple[int, int, int] | None]:
    from .sexcom import SEX_TYPE, boss_reaction_ref, lastboss_reaction_ref

    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    s12 = v[12]
    tt = lambda name: t(ctx, c, name)  # noqa: E731
    if tt("清純派") > 0:
        return 0, None
    e = st.charas[st.flag[111]]
    fem_enemy = enemy_type_check(st, "AKUOTI") == 1 and not is_male(ctx.data, e) and t(ctx, e, "ふたなり") < 1 and \
        t(ctx, e, "寄生") == 0
    if n == 104:  # :1040–1075
        if is_male(ctx.data, c):
            return 0, None
        if c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0:
            return 0, None
        if (s12 & KYOUKOUSOKU) == 0 or v[0] >= 1 or abl(ctx, c, "技巧") < 3:
            return 0, None
    else:
        if n != 100 and fem_enemy:
            return 0, None
        if not is_hole(ctx):
            return 0, None
        if n in (102, 103) and (s12 & KYOUKOUSOKU):
            return 0, None
        if v[0] >= 1:
            return 0, None
        if n == 102 and abl(ctx, c, "技巧") < 1:
            return 0, None
        if n == 103 and abl(ctx, c, "技巧") < 2:
            return 0, None
        if n in (101, 102, 103) and st.temp.prevcom == n:
            return 0, None
        if n == 101 and (s12 & KYOUKOUSOKU) == 0:  # :893–905
            _need_boss(ctx)
            typ = mob.sex_type(st.flag[11],st.tflag[20]) if _mob(ctx) else SEX_TYPE.get(st.tflag[20])
            if typ is None:  # TRYCCALLFORM SEX_TYPE_COM{TFLAG:20} が無い → CATCH で RETURN 0
                return 0, None
            if (typ & 1) == 0:
                return 0, None
        if n == 103:  # :991–1020
            _need_boss(ctx)
            if enemy_type_check(st,"CITIZEN") == 1:
                return 0,None  # COMABLE.ERB:992–995：TRYCCALLFORM MOB_1150 缺函式 → CATCH。
            if _mob(ctx):
                r = mob.reaction_ref(ctx,2)
            elif enemy_type_check(st, "LASTBOSS") >= 1:  # :996–1000（S27）
                r = lastboss_reaction_ref(ctx, st.flag[11], 2)
            elif st.flag[11] not in range(1, 8):  # TENTACLE_BOSS_{FLAG:11}_REACTION_REF が無い（悪堕ちキャラ戦は 0）→ CATCH
                return 0, None
            else:
                r = boss_reaction_ref(ctx, st.flag[11], 2)
            typ = mob.sex_type(st.flag[11],r) if _mob(ctx) else SEX_TYPE.get(r)
            if typ is None:
                return 0, None
            if (typ & 2) == 0:
                return 0, None
    if (s12 & MAHI) or (s12 & KOUKOTSU) or (s12 & KIZETU) or not guard:
        return 0, None
    if chara_sex_comable(ctx, n) == 0:
        return 0, None
    return 1, pink


def label_hurihodoku(ctx: Ctx) -> int:
    """PRINT_COMNAME.ERB:6–13：振り解くの成功率表示（判定関数を呼ぶので RAND:100 を 1 回引く：原作どおり）。"""
    from .hantei import act_hantei_chara_to_tentacle

    return min(act_hantei_chara_to_tentacle(ctx, "HURIHODOKU")[1], 100)


def label_hikihagasu(ctx: Ctx) -> int:
    """PRINT_COMNAME.ERB:14–24。"""
    r = min(com40_hantei(ctx), 100)
    st = ctx.state
    if enemy_type_check(st, "BOSS") == 1 and st.flag[11] == 3:
        r = 0
    return r


# --- 地の文（地の文/MESSAGE_BATTLE.ERB:634–990）------------------------------------------


def msg_hurihodoku(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_CHARA_HURIHODOKU`:634–648。"""
    st = ctx.state
    _need_boss(ctx)
    if _akuoti(ctx):
        ctx.out.printl(f"{print_transcallname(st, st.target)}は{print_transcallname(st, st.flag[111])}の拘束を振り解こうと全力で暴れた・・・")
    else:
        ctx.out.printl(f"{print_transcallname(st, st.target)}は手足に絡みついた触手を振り解こうと全力で暴れた・・・")
    kojo_root(ctx, "BATTLE_CHARA_HURIHODOKU")
    ctx.out.printw()


def msg_hurihodoku_success(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_CHARA_HURIHODOKU_SUCCESS`:651–666。"""
    st = ctx.state
    out = ctx.out
    _need_boss(ctx)
    out.print("すると一瞬")
    out.print(print_transcallname(st, st.flag[111]) if _akuoti(ctx) else "触手")
    out.printl("の拘束が緩み、")
    out.printl(f"その隙を突いた{print_transcallname(st, st.target)}は辛くも窮地を脱することに成功した！")
    kojo_root(ctx, "BATTLE_CHARA_HURIHODOKU_SUCCESS")
    out.printw()


def msg_hurihodoku_false(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_CHARA_HURIHODOKU_FALSE`:669–692。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    name = print_transcallname(st, st.target)
    _need_boss(ctx)
    out.print("しかし")
    out.print(print_transcallname(st, st.flag[111]) if _akuoti(ctx) else "触手")
    if t(ctx, c, "感情乏しい") > 0:
        out.printl("の拘束はびくともしなかった・・・")
    elif t(ctx, c, "主観視点") > 0:
        out.printl("の拘束はびくともせず、")
        out.printl(f"{name}の眉が苦渋に歪む・・・")
    else:
        out.printl("の拘束はびくともせず、")
        out.printl(f"{name}は苦渋に眉を顰めた・・・")
    kojo_root(ctx, "BATTLE_CHARA_HURIHODOKU_FALSE")
    out.printw()


def _simple_msg(ctx: Ctx, code: str, lines: list[str], extra_blank: bool = False) -> None:
    out = ctx.out
    for line in lines:
        out.printl(line)
    if extra_blank:
        out.printl()
    kojo_root(ctx, code)
    out.printw()


# --- COMF8〜15 ------------------------------------------------------------------------


def com8(ctx: Ctx) -> ComGen:
    """`COMF8.ERB@COM8`:2–53（振り解く）。"""
    from .hantei import act_hantei_chara_to_tentacle

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if act_limit(ctx) == 1:
        return 1
    print_distance(ctx)
    out.printl()
    msg_hurihodoku(ctx)
    if act_hantei_chara_to_tentacle(ctx, "HURIHODOKU")[0] == 1:
        c.tcvarn[0] = 2
        st.tflag[4] = 0
        st.tflag[16] = -1
        st.tflag[17] = -1
        msg_hurihodoku_success(ctx)
        _other(ctx, "HURIHODOKU_SUCCESS")  # :29–30
        st.tflag[1] = 1
        c.tcvarn[8] = 1
    else:
        msg_hurihodoku_false(ctx)
        _other(ctx, "HURIHODOKU_FALSE")  # :41–42
    c.ex[99] += 1
    if t(ctx, c, "剛腕") > 0:
        st.tflag[99] += 1
    return 1
    yield  # pragma: no cover


def com9(ctx: Ctx) -> ComGen:
    """`COMF9.ERB@COM9`:2–107（暴れる）。"""
    from .hantei import damage

    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    hit_flag = 1
    if act_limit(ctx) == 1:
        return 1
    print_distance(ctx)
    out.printl()
    _need_boss(ctx)
    # MESSAGE_BATTLE_CHARA_ABARERU（MESSAGE_BATTLE.ERB:697–713）
    if _akuoti(ctx) and t(ctx, st.charas[st.flag[111]], "寄生") == 0:
        out.printl(f"{print_transcallname(st, st.target)}は{print_transcallname(st, st.flag[111])}に拘束された状態からでも")
    else:
        out.printl(f"{print_transcallname(st, st.target)}は触手に絡まれた状態からでも")
    _simple_msg(ctx, "BATTLE_CHARA_ABARERU", ["なんとかダメージを与えようと苦し紛れにもがいた！"])
    _other(ctx, "ABARERU")  # :18–19
    if st.flag[111] == 0:  # :24–31
        l0 = int(tentacle_access(ctx, "KOUGEKI"))
    else:
        l0 = st.charas[st.flag[111]].maxbase[10]
    if st.tflag[2] >= 1:
        l0 = 1
    l1 = shinkyou_check(ctx, "BOUGYO", correction_trans(ctx, c.maxbase[11]))
    l1 = div(cloth_battle_hosei(ctx, "BOUGYO") * l1, 100)
    if v.get_bit(3, 1):
        l1 *= 2
    l0 = max(5, min(div(20 * l1, l0) + 5, 70))
    if _mob(ctx):
        l0 = div(l0, 2)
    v[2] = P_ABARE_GUARD if st.rng.rand(100) < l0 else P_ABARE_FAIL  # :48–52
    from .enemy import _colored

    if st.rng.rand(100) < 5 + cloth_battle_hosei(ctx, "CRITICAL"):  # :56–77
        l0 = 15
        hit_flag = 2
        _colored(ctx, (255, 0, 0), "CRITICAL HIT!", bold=True)  # MESSAGE_BATTLE_CHARA_ATTACK_CRITICAL_HIT:522–532
        kojo_root(ctx, "BATTLE_CHARA_ATTACK_CRITICAL_HIT")
        _other(ctx, "ATTACK_CRITICAL_HIT")  # :65–66
        v[2] = P_ABARE_CRIT
    else:
        l0 = 10
        _colored(ctx, (255, 255, 0), "HIT!")  # MESSAGE_BATTLE_CHARA_ATTACK_HIT:535–543
        kojo_root(ctx, "BATTLE_CHARA_ATTACK_HIT")
        _other(ctx, "ATTACK_HIT")  # :74–75
    r = damage(ctx, "ABARERU")  # :80–86
    st.flag[13] -= div(r * l0, 10)
    out.set_bold(True)
    out.printl(f"{div(r * l0, 10)}のダメージを与えた！")
    out.set_bold(False)
    out.printw()
    cloth_battle_damage(ctx, 4)
    c.ex[99] += 3
    if t(ctx, c, "サド気質") > 0 and hit_flag > 0:  # :95–105
        l1 = st.rng.rand(max(div(c.maxbase[1] * hit_flag * 8, 100), 1)) + 10
        if c.base[1] + l1 >= c.maxbase[1]:
            l1 = c.maxbase[1] - c.base[1]
        c.base[1] += l1
        st.temp.common_palam[7] += l1 * 10
        if l1 > 0:
            out.printl(f"サディスティックな快楽で{ctx.data.names['BASE'].get(1, '')}が{l1}回復した")
    return 1
    yield  # pragma: no cover


def com10(ctx: Ctx) -> ComGen:
    """`COMF10.ERB@COM10`:2–25（耐える）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if act_limit(ctx) == 1:
        return 1
    print_distance(ctx)
    out.printl()
    c.tcvarn[2] = P_TAERU
    _need_boss(ctx)
    out.print(f"{print_transcallname(st, st.target)}は")  # MESSAGE_BATTLE_CHARA_TAERU:716–729
    out.print("ぐっと唇を噛んで")
    print_enemy_prefix(ctx)
    out.printl("の陵辱に耐えている・・・")
    _simple_msg(ctx, "BATTLE_CHARA_TAERU", [], extra_blank=True)
    _other(ctx, "TAERU")  # :19–20
    c.ex[99] += 1
    return 1
    yield  # pragma: no cover


def com11(ctx: Ctx) -> ComGen:
    """`COMF11.ERB@COM11`:2–26（なすがまま）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    c.tcvarn[2] = P_NASUGAMAMA
    st.tflag[3] += 25
    name = print_transcallname(st, st.target)
    if c.tcvarn[12] & KIZETU:
        out.printl(f"{name}は意識を失っている…")
        out.printw()
    else:
        _need_boss(ctx)
        out.print(f"{name}は身を竦ませ、")  # MESSAGE_BATTLE_CHARA_NASUGAMAMA:734–745
        print_enemy_prefix(ctx)
        out.printl("の陵辱になすがままにされている・・・")
        kojo_root(ctx, "BATTLE_CHARA_NASUGAMAMA")
        out.printw()
        _other(ctx, "NASUGAMAMA")  # :22–23
    return 1
    yield  # pragma: no cover


def com12(ctx: Ctx) -> ComGen:
    """`COMF12.ERB@COM12`:2–20（受け入れる）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    c.tcvarn[2] = P_UKEIRERU
    st.tflag[3] += 50
    _need_boss(ctx)
    out.print(f"{print_transcallname(st, st.target)}は")  # MESSAGE_BATTLE_CHARA_UKEIRERU:750–761
    print_enemy_prefix(ctx)
    out.printl("の与える快楽をすすんで受け入れた・・・")
    kojo_root(ctx, "BATTLE_CHARA_UKEIRERU")
    out.printw()
    _other(ctx, "UKEIRERU")  # :17–18
    return 1
    yield  # pragma: no cover


def com13(ctx: Ctx) -> ComGen:
    """`COMF13.ERB@COM13`:2–46（奉仕する）。"""
    from .syasei import tentacle_syasei_up

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    st.tflag[4] |= HAND
    if abl(ctx, c, "技巧") >= 2:
        st.tflag[4] |= MOUTH
    if c.tcvarn[12] & KYOUKOUSOKU:
        st.tflag[4] = 0
    c.tcvarn[2] = P_HOUSHI
    st.tflag[3] += 100
    g = abl(ctx, c, "技巧")
    local = 70 if g < 2 else 100 if g == 2 else 140 if g == 3 else 190 if g == 4 else 250
    tentacle_syasei_up(ctx, local)
    _need_boss(ctx)
    # MESSAGE_BATTLE_CHARA_HOUSI:766–781
    if _akuoti(ctx):
        out.printl(f"{print_transcallname(st, st.target)}は自分から{print_transcallname(st, st.flag[111])}への熱心な奉仕を始めた・・・")
    else:
        out.printl(f"{print_transcallname(st, st.target)}は近くにあった触手を手に取り熱心な奉仕を始めた・・・")
    kojo_root(ctx, "BATTLE_CHARA_HOUSI")
    out.printw()
    _other(ctx, "HOUSI")  # :40–41
    c.ex[99] += 1
    return 1
    yield  # pragma: no cover


def com14(ctx: Ctx) -> ComGen:
    """`COMF14.ERB@COM14`:2–28（Ｖ挿入防御）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if act_limit(ctx) == 1:
        return 1
    print_distance(ctx)
    out.printl()
    st.tflag[3] += 5
    c.tcvarn[2] = P_V_GUARD
    _need_boss(ctx)
    # MESSAGE_BATTLE_CHARA_ANTI_V:786–791
    out.printl(f"{print_transcallname(st, st.target)}はせめて膣への挿入だけでも防ごうと身構えた・・・")
    kojo_root(ctx, "BATTLE_CHARA_ANTI_V")
    out.printw()
    _other(ctx, "ANTI_V")  # :22–23
    c.ex[99] += 1
    return 1
    yield  # pragma: no cover


def com15(ctx: Ctx) -> ComGen:
    """`COMF15.ERB@COM15`:34–59（救出する）。地の文は `地の文/MESSAGE_KYUUSHUTU.ERB`（catalog）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if act_limit(ctx) == 1:  # :36–38
        return 1
    print_distance(ctx)  # :41–42
    out.printl()
    _kyuushutu_msg(ctx, "MESSAGE_BATTLE_CHARA_KYUUSHUTU")  # :45
    if act_hantei_kyuushutu(ctx) == 1:  # :46–54
        _kyuushutu_msg(ctx, "MESSAGE_BATTLE_CHARA_KYUUSHUTU_SUCCESS")
        st.tflag[19] = 1
    else:
        _kyuushutu_msg(ctx, "MESSAGE_BATTLE_CHARA_KYUUSHUTU_FALSE")
    out.printw()  # :55
    c.ex[99] += 1  # :57 EX:行動ポイント
    return 1
    yield  # pragma: no cover


def _kyuushutu_msg(ctx: Ctx, name: str) -> None:
    """`地の文/MESSAGE_KYUUSHUTU.ERB` の各関数（本文のみ、状態変化なし）。catalog で実行できなければ本文を Python で出す。"""
    if ctx.narration.run_function(ctx, name, []):
        return
    # DEVIATION（表示のみ）：catalog が無いときは同じ本文を Python で出す（deviations.md「幽閉的地の文與淫紋顯示」）
    st = ctx.state
    s2500 = ctx.data.str_defaults.get(2500, "")
    me = print_transcallname(st, st.target)
    from ..action import print_callname

    who = prison_chara(ctx)
    other = print_callname(st, who) if who >= 0 else ""
    text = {
        "MESSAGE_BATTLE_CHARA_KYUUSHUTU": f"{me}は {s2500}に囚われた仲間を救出しようとあがいた！",  # :4–5
        "MESSAGE_BATTLE_CHARA_KYUUSHUTU_SUCCESS": f"{me}は {s2500}に取り込まれた{other}の救出に成功した！",  # :10–12
        "MESSAGE_BATTLE_CHARA_KYUUSHUTU_FALSE": f"{s2500}に取り込まれた仲間を探しても、隠されているのかどこにも見つからない……",
        "MESSAGE_KYUUSHUTU_SUCCESS": f"{me}は{other}を触手から大きく離れた地点まで運んだ！",  # :31–33
        "MESSAGE_ESCAPE_RESCUED": f"{other}は息も絶え絶えながらなんとか反応している……",  # :38–40
    }[name]
    ctx.out.printl(text)


def act_hantei_kyuushutu(ctx: Ctx) -> int:
    """`COMF15.ERB@ACT_HANTEI_CHARA_TO_TENTACLE_KYUUSHUTU`:102–174。"""
    from .core import correction_binsyou

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    l0 = percent_cal(c.base[0] * 2 + c.base[1], c.maxbase[0] * 2 + c.maxbase[1])  # :107
    r = percent_cal(st.flag[13], st.flag[12])  # :110–117
    l1 = 100 if r > 50 else 105 if r > 25 else 110
    l2 = c.maxbase[ctx.data.index_of("BASE", "敏捷")]  # :120
    if t(ctx, c, "小柄") == 1:  # :123–126
        l2 = times(l2, "0.90")
    if t(ctx, c, "長身") == 1:
        l2 = times(l2, "1.20")
    l2 = correction_trans(ctx, l2)  # :129
    l2 = div(l2 * cloth_battle_hosei(ctx, "BINSYOU"), 100)  # :132–133
    l2 = shinkyou_check(ctx, "BINSYOU", l2)  # :136–137
    l3 = int(tentacle_access(ctx, "BINSYOU"))  # :140–141
    if st.tflag[2] == 1:  # :144–145
        l3 = times(l3, "0.50")
    l4 = correction_binsyou(percent_cal(l2, l3))  # :148
    l5 = div((div(l0, 2) + 50) * l1 * l4, 10000)  # :151
    if l5 > 50:  # :153–157
        l5 = 50
    if l5 < 10:
        l5 = 10
    if st.flag[999] == 1:  # :159–166
        for k, v in enumerate((l0, l1, l2, l3, l4)):
            out.printl(f"LOCAL:{k} ＝ {v}")
        out.printl(f"行動成功値：{l5}")
    return 1 if st.rng.rand(100) < l5 else 0


def kyushutu_success(ctx: Ctx) -> None:
    """`COMF15.ERB@KYUSHUTU_SUCCESS`:77–97（撤退成功時、TFLAG:19 == 1）。"""
    st = ctx.state
    who = prison_chara(ctx)  # :79–82
    if who < 0:
        return
    _kyuushutu_msg(ctx, "MESSAGE_KYUUSHUTU_SUCCESS")  # :83
    saved = st.target  # :84–88
    st.target = who
    _kyuushutu_msg(ctx, "MESSAGE_ESCAPE_RESCUED")
    st.target = saved
    o = st.charas[who]  # :90–97
    o.cflag[0] = -1
    o.cflag[20] = 0
    o.cflag[21] = 0
    o.cflag[30] = 0
    o.cflag[31] = 0
    o.base[0] = 1
    o.base[1] = 1
    o.base[2] = 1


# --- COMF40（引き剥がす）-------------------------------------------------------------------


def com40_hantei(ctx: Ctx) -> int:
    """`COMF40.ERB@COM40_HANTEI`:51–102。"""
    from .core import get_battle_situation  # noqa: F401

    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    l0 = percent_cal(c.base[0] * 2 + c.base[1], c.maxbase[0] * 2 + c.maxbase[1])
    floor = min(isqrt(max(c.base[11] - 100, 0)) * 8, 75)
    if l0 < floor:
        l0 = floor
    if v[12] & MAHI:
        l0 = div(l0, 2)
    if c.cflag[1] == 2:
        l0 = 100
    l0 = div(l0, 4)
    r = percent_cal(st.flag[13], st.flag[12])
    l1 = 75 if r > 50 else 100 if r > 25 else 125
    l2 = div((l0 + 40) * l1, 100)
    if v[2] == P_ABARE_GUARD:
        l2 += 25
    if v[2] == P_TAERU:
        l2 += 10
    if v[2] == P_NIRAMI:
        l2 += 20
    if v[2] == P_BATOU:
        l2 += 15
    if v[2] == P_HANKOU:
        l2 += 15
    if enemy_type_check(st, "BOSS") == 1 and st.flag[11] == 3:
        l2 = 1
    if v.get_bit(3, 1):
        l2 += 50
    return l2


def com40(ctx: Ctx) -> ComGen:
    """`COMF40.ERB@COM40`:2–47（引き剥がす）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if act_limit(ctx) == 1:
        return 1
    print_distance(ctx)
    out.printl()
    _need_boss(ctx)
    lkind, ename = _enemy_locals(ctx)
    name = print_transcallname(st, st.target)
    # MESSAGE_BATTLE_CHARA_HIKIHAGASU:796–811
    out.printl(f"{name}は{ename}に犯されながらも激しく抵抗した・・・")
    kojo_root(ctx, "BATTLE_CHARA_HIKIHAGASU")
    out.printw()
    local = com40_hantei(ctx)
    if enemy_type_check(st, "BOSS") == 1 and st.flag[11] == 3:  # :22–29（Ａ触手は失敗）
        pass
    elif st.rng.rand(100) < local:
        st.tflag[1] = 1
        if c.tcvarn[12] & KYOUKOUSOKU:
            c.tcvarn[12] -= KYOUKOUSOKU
    if st.tflag[1] == 1:  # MESSAGE_BATTLE_CHARA_HIKIHAGASU_SUCCESS:815–836（:829 は括弧あり）
        _lk, ename = _enemy_locals(ctx)
        if lkind == "ペニス" or ename == "Ｃ触手" or (ename == "Ｂ触手" and st.tflag[20] == 1011):
            out.print(f"何とか{ename}を突き飛ばすことに成功した！")
        else:
            out.printl("触手を両手で掴んで抑え込み、力尽くで引き抜くことに成功した！")
        kojo_root(ctx, "BATTLE_CHARA_HIKIHAGASU_SUCCESS")
        out.printw()
        _other(ctx, "HIKIHAGASU_SUCCESS")  # COMF40.ERB:35–36
    else:  # MESSAGE_BATTLE_CHARA_HIKIHAGASU_FALSE:839–871
        # :852 は括弧なし：`&&` と `||` は同順位・左結合（reference/emuera-1824/Emuera/GameData/Expression/
        # OperatorCode.cs:33–34、ExpressionParser.cs:502–506）なので ((ペニス || Ｃ触手 || Ｂ触手) && TFLAG:20 == 1011)
        _lk, ename = _enemy_locals(ctx)
        if (lkind == "ペニス" or ename in ("Ｃ触手", "Ｂ触手")) and st.tflag[20] == 1011:
            out.printl(f"{name}は何とかして{ename}を跳ね除けようとするが、")
            out.printl("激しいピストンで姿勢を崩されて思うように抵抗できない・・・")
        elif ename == "Ａ触手":
            out.printl(f"{name}は何とかして{ename}を引き離そうとするが、")
            out.printl("相手が不定形では空しい抵抗でしかない・・・")
        else:
            out.printl(f"{name}は自分を犯している触手を何とか掴んで引き抜こうとしたが、")
            rand = st.rng.rand
            if rand(3) == 0:
                out.printl("絶妙なタイミングでズンと突き上げられて力が抜けてしまった・・・")
            elif rand(2) == 0:
                out.printl("伸ばした手を別の触手に拘束され失敗してしまった・・・")
            else:
                out.printl("ぬるぬるした粘液で滑る触手を上手く掴むことができなかった・・・")
        kojo_root(ctx, "BATTLE_CHARA_HIKIHAGASU_FALSE")
        out.printw()
        _other(ctx, "HIKIHAGASU_FALSE")  # COMF40.ERB:41–42
    c.ex[99] += 1
    return 1
    yield  # pragma: no cover


# --- COMF44〜46（睨みつける・罵倒する・反抗する）-------------------------------------------------


def _kiryoku_recover(ctx: Ctx, factor: tuple[str, str, str]) -> int:
    """COMF44:27–44 型：気力回復量（回復早い／遅い／通常の TIMES 係数）。"""
    c = tc(ctx)
    l1 = c.maxbase[1] + div(c.base[11] * cloth_battle_hosei(ctx, "BOUGYO") * 4, 200)
    if t(ctx, c, "溢れる生命力") > 0:
        l1 = times(l1, "1.25")
    if t(ctx, c, "回復早い") == 1:
        l1 = times(l1, factor[0])
    elif t(ctx, c, "回復遅い") == 1:
        l1 = times(l1, factor[1])
    else:
        l1 = times(l1, factor[2])
    if c.base[1] + l1 >= c.maxbase[1]:
        l1 = c.maxbase[1] - c.base[1]
    if c.base[1] == 0:
        l1 = 0
    return l1


def _fatigue_decay(ctx: Ctx, l1: int, stamina: str, normal: str) -> int:
    """COMF45:39–48 `REPEAT CFLAG:99 / SIF LOCAL:1 <= 1 BREAK / TIMES`。"""
    c = tc(ctx)
    for _ in range(max(c.cflag[99], 0)):
        if l1 <= 1:
            break
        l1 = times(l1, stamina if t(ctx, c, "スタミナ") > 0 else normal)
    return l1


def _print_kiryoku(ctx: Ctx, l1: int) -> None:
    c = tc(ctx)
    bname = ctx.data.names["BASE"].get(1, "")
    if c.base[1]:
        ctx.out.printl(f"{bname}が{l1}回復した")
    else:
        ctx.out.printl(f"{bname}は既に尽きてしまっている……")


def _shinkyou_after(ctx: Ctx, a: str, b: str) -> None:
    """COMF45:69–77／COMF46:66–74（`RAND < TCVARn:11*20 || TCVARn:1 == 0`：RAND を先に引く）。"""
    st = ctx.state
    v = tc(ctx).tcvarn
    if st.rng.rand(100) < v[11] * 20 or v[1] == 0:
        mb = _mb(ctx)
        shinkyou_change(ctx, a if (mb & KAIRAKU_TOROKE) or (mb & ZETSUBOU) else b)
    else:
        v[11] += 1
    ctx.out.printl()


def _nirami_head(ctx: Ctx) -> str:
    """MESSAGE_BATTLE_CHARA_NIRAMI:875–920 の前半（TFLAG:5／TFLAG:20 による状況説明）。"""
    st = ctx.state
    c = tc(ctx)
    timid = t(ctx, c, "臆病") or t(ctx, c, "恥ずかしがり屋") or t(ctx, c, "悲観的")
    s0, s1 = ("涙目で", "勇気を振り絞り") if timid else ("キッと", "好きにさせまいと")
    tf5, tf20 = st.tflag[5], st.tflag[20]
    if tf5 & BOUHATSU:
        return f"精液で全身を汚されながらも{s0}"
    if tf20 in (0, 1, 2, 4, 6, 7, 8, 1007):
        return f"手も足も出ない悔しさを堪えながら{s0}"
    if tf20 in (11, 12):
        return f"口元から精液と唾液の混合物を垂れ流しながらも{s0}" if tf5 & MOUTH else f"口を犯されながらも{s1}"
    if tf20 in (9, 1004, 1008, 1015):
        return f"苦痛を伴う責めに息を荒げながらも{s0}"
    if tf20 in (3, 5, 15, 16, 1001, 1002, 1009, 1010, 1011, 1014):
        if (tf5 & 2) and (tf5 & 4):
            return f"前後の穴に精液を注ぎこまれながらも{s0}"
        if tf5 & 2:
            return f"無残に中出しされ精液を垂れ流しながらも{s0}"
        if tf5 & 4:
            return f"アナルに精液を注ぎこまれながらも{s0}"
        return f"為すすべなく犯されながらも戦意を失わずに{s0}"
    if tf20 in (1000, 1003, 1005, 1012):
        return f"激しい凌辱に悶え乱れながらも{s0}"
    return "自分を鼓舞し奮い立たせるかのように"


def com44(ctx: Ctx) -> ComGen:
    """`COMF44.ERB@COM44`:2–63（睨みつける）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    st.tflag[3] += 25
    c.tcvarn[2] = P_NIRAMI
    rand = st.rng.rand
    if c.cflag[99] < 5:
        c.tcvarn[6] += 20 + rand(16)
    elif c.cflag[99] < 15:
        c.tcvarn[6] += 15 + rand(11)
    else:
        c.tcvarn[6] += 10 + rand(6)
    l1 = _kiryoku_recover(ctx, ("0.06", "0.04", "0.05"))
    c.base[1] += l1
    _need_boss(ctx)
    out.print(f"{print_transcallname(st, st.target)}は{_nirami_head(ctx)}")  # MESSAGE_BATTLE_CHARA_NIRAMI
    out.printl("相手を睨みつけた！")
    out.printl()
    kojo_root(ctx, "BATTLE_CHARA_NIRAMI")
    out.printw()
    _other(ctx, "NIRAMI")  # :49–50
    c.ex[99] += 1
    _print_kiryoku(ctx, l1)
    out.printl("ＥＸゲージが少し溜まった！")
    out.printl()
    return 1
    yield  # pragma: no cover


def com45(ctx: Ctx) -> ComGen:
    """`COMF45.ERB@COM45`:2–79（罵倒する）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    c.tcvarn[6] += 25
    st.tflag[3] += 5
    c.tcvarn[2] = P_BATOU
    l1 = _fatigue_decay(ctx, _kiryoku_recover(ctx, ("0.66", "0.54", "0.60")), "0.96", "0.92")
    c.base[1] += l1
    st.tflag[99] += 1
    _need_boss(ctx)
    _lk, ename = _enemy_locals(ctx)
    name = print_transcallname(st, st.target)
    mb = _mb(ctx)  # MESSAGE_BATTLE_CHARA_BATOU:926–957
    if mb & ZETSUBOU:
        out.printl(f"{name}は{ename}を罵ったが言葉に勢いがなく、")
        out.printl("虚勢を張っているだけなのは誰の目にも明らかだ・・・")
    elif mb & KAIRAKU_TOROKE:
        out.printl(f"{name}は{ename}を口汚く罵倒したが")
        if t(ctx, c, "主観視点") > 0:
            out.printl("快楽に蕩けさせられた舌では呂律が回らない・・・")
        else:
            out.printl("快楽に蕩けさせられ呂律が回っていないため強がりが筒抜けだ・・・")
    elif mb & KUSEN:
        out.printl(f"{name}は{ename}を口汚く罵り何とか戦意を奮い起した！")
    else:
        out.printl(f"{name}は負けないという意志を込めて{ename}を口汚く罵った！")
    out.printl()
    kojo_root(ctx, "BATTLE_CHARA_BATOU")
    out.printw()
    _other(ctx, "BATOU")  # :56–57
    c.ex[99] += 1
    _print_kiryoku(ctx, l1)
    _shinkyou_after(ctx, "DOUYOU", "IKARI")
    return 1
    yield  # pragma: no cover


def com46(ctx: Ctx) -> ComGen:
    """`COMF46.ERB@COM46`:2–76（反抗する）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    st.tflag[3] += 5
    c.tcvarn[2] = P_HANKOU
    l1 = _fatigue_decay(ctx, _kiryoku_recover(ctx, ("0.33", "0.27", "0.30")), "0.995", "0.99")
    c.base[1] += l1
    st.tflag[99] += 1
    _need_boss(ctx)
    name = print_transcallname(st, st.target)
    mb = _mb(ctx)  # MESSAGE_BATTLE_CHARA_RESISTANCE:962–989（:963–974 の LOCALS は表示に使われない）
    if mb & ZETSUBOU:
        out.printl(f"心を折られた{name}はもはや形だけの抵抗をしている・・・")
    elif mb & KAIRAKU_TOROKE:
        out.printl(f"快楽漬けにされた{name}はもはや形だけの抵抗をしている・・・")
    elif mb & KUSEN:
        out.printl(f"{name}はまだ諦めていないことを態度で示した！")
    else:
        out.printl(f"{name}はまだ凌辱に屈していないことを態度で示した！")
    out.printl()
    kojo_root(ctx, "BATTLE_CHARA_RESISTANCE")
    out.printw()
    _other(ctx, "RESISTANCE")  # :53–54
    c.ex[99] += 1
    _print_kiryoku(ctx, l1)
    _shinkyou_after(ctx, "TEIKAN", "REISEI")
    return 1
    yield  # pragma: no cover


def com47(ctx: Ctx) -> ComGen:
    """`COMF47.ERB@COM47`:2–78（説得する）。地の文は MESSAGE_BATTLE_CHARA_PERSUADE（MESSAGE_BATTLE.ERB:992–1016）。
    `RAND:RESULT / 2` は (RAND:RESULT) / 2（ExpressionParser.cs@ReduceVariableArgument:192–198）。"""
    from .commands import _tofull
    from ..action import print_callname

    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    rand = st.rng.rand
    print_distance(ctx)  # :5–6
    out.printl()
    st.tflag[3] += 5  # :9
    v[2] = P_SETTOKU  # :12
    name = print_transcallname(st, st.target)  # :15 MESSAGE_BATTLE_CHARA_PERSUADE（:993–1004 の LOCALS は表示に使わない）
    if t(ctx, c, "主観視点") > 0:
        out.printl(f"{name}はなんとか言葉で説得しようとした・・・")
    else:
        out.printl(f"{name}はこんなことを止めるように説得しようとしている・・・")
    out.printl()
    kojo_root(ctx, "BATTLE_CHARA_PERSUADE")
    out.printw()
    _other(ctx, "PERSUADE")  # :17–18
    l0 = div(c.maxbase[ctx.data.index_of("BASE", "知性")] * cloth_battle_hosei(ctx, "CHISEI"), 100)  # :21–25
    l0 = shinkyou_check(ctx, "CHISEI", l0)  # :28–29
    if enemy_type_check(st, "AKUOTI"):  # :32–37
        l1 = st.charas[st.flag[111]].maxbase[13]
    else:
        l1 = int(tentacle_access(ctx, "CHISEI"))
    result = percent_cal(l0, l1)  # :39
    if rand(360) + 90 < result:  # :40–46
        local = 650 + div(rand(result), 2)
        st.tflag[3] += local
        out.printl("迫真の言葉に相手は動揺している！")
        out.printl(f"油断度＋（{_tofull(local)}）")
    elif rand(240) + 60 < result:  # :47–53
        local = 400 + div(rand(result), 2)
        st.tflag[3] += local
        out.printl("相手を少し動揺させることができたようだ・・・")
        out.printl(f"油断度＋（{_tofull(local)}）")
    elif rand(180) + 30 < result:  # :54–60
        local = 250 + div(rand(result), 4)
        st.tflag[3] += local
        out.printl("相手の瞳の奥に微かな変化があったようにも見える・・・")
        out.printl(f"油断度＋（{_tofull(local)}）")
    else:
        out.printl("相手は聞く耳を持たない様子だ・・・")
    out.printl()  # :64
    c.ex[99] += 1  # :67
    # :69 `TCVARn:1 > 0 && RAND:100 < (TCVARn:11 * 10)`（短絡：TCVARn:1 が 0 なら RAND を引かない）
    if v[1] > 0 and rand(100) < v[11] * 10:
        v[1] = 6
        out.print(f"{print_callname(st, st.target)}の心境が")
        shinkyou_check(ctx, "PRINT", 0)
        out.printl("に変化した")
    else:
        v[11] += 1
    out.printl()
    return 1
    yield  # pragma: no cover


# --- COMF100〜104（ヒロイン側の性攻撃）----------------------------------------------------------


def _sex_attack_msg(ctx: Ctx, n: int) -> None:
    """`MESSAGE_BATTLE_CHARA_SEX_ATTACK{n}`（地の文/MESSAGE_SEX.ERB:1932–2200、本文は chinobun）と
    悪堕ちキャラ戦の `MESSAGE_OTHER_BATTLE_CHARA_SEX_ATTACK{n}`（COMF100.ERB:24–25 等）。"""
    _need_boss(ctx)
    # 本文の末尾で TRYCALLFORM KOJO_ROOT(CFLAG:6, "BATTLE_CHARA_SEX_ATTACK{n}")（100〜104 すべて：:2001／:2063／:2101／
    # :2146／:2213）。S06 は 104 の KOJO_ROOT を落としていたので fallback でも呼ぶ。
    run_chinobun(ctx, f"MESSAGE_BATTLE_CHARA_SEX_ATTACK{n}",
                 fallback=lambda: kojo_root(ctx, f"BATTLE_CHARA_SEX_ATTACK{n}"))
    _other(ctx, f"SEX_ATTACK{n}")


def _pleasure_given(ctx: Ctx, before: int, wait_split: bool = False) -> None:
    """「{敵}に{n}の快楽を与えた！」（COMF100:34–45 等）。"""
    st = ctx.state
    out = ctx.out
    out.printl()
    if st.flag[110] == 0:  # COMF100.ERB:35–39 等
        tentacle_access(ctx, "NAME")
    elif st.flag[110] == 1:
        out.print(print_transcallname(st, st.flag[111]))
    out.print("に")
    out.set_bold(True)
    out.print(f"{st.flag[15] - before}の快楽")
    out.set_bold(False)
    if wait_split:
        out.printw("を与えた！")
    else:
        out.printl("を与えた！")
        out.printw()


def _houshi_juel(ctx: Ctx, base: int, per: int) -> None:
    c = tc(ctx)
    ctx.state.temp.common_palam[6] += base + per * (abl(ctx, c, "従順") + abl(ctx, c, "奉仕精神") * 2)


def com100(ctx: Ctx) -> ComGen:
    """`COMF100.ERB@COM100`:2–70（手淫攻撃）。"""
    from .sexcom import boss_reaction_ref, lastboss_reaction_ref
    from .syasei import tentacle_syasei_check, tentacle_syasei_up

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    if st.flag[15] >= st.flag[14] * 2 or st.rng.rand(2) == 0:  # :9（短絡）
        st.tflag[4] |= HAND
    if c.tcvarn[12] & KYOUKOUSOKU:
        st.tflag[4] = 0
    c.tcvarn[2] = P_HOUSHI
    g = abl(ctx, c, "技巧")
    st.tflag[3] += 55 + 5 * g
    _sex_attack_msg(ctx, 100)
    before = st.flag[15]
    tentacle_syasei_up(ctx, min(div(c.maxbase[2], 5), 75) + 100 + g * 25)
    _pleasure_given(ctx, before)
    r0 = (yield from tentacle_syasei_check(ctx))[0]  # RESULT = RESULT:0
    out.printl()
    if g >= 3 and st.rng.rand(100) < 10:  # :52–62
        _need_boss(ctx)
        if enemy_type_check(st,"CITIZEN") == 1:
            r = r0  # COMF100.ERB:53–60：MOB_1150 缺函式，保留 TENTACLE_SYASEI_CHECK。
        elif _mob(ctx):
            r = mob.reaction_ref(ctx,3)
        elif enemy_type_check(st, "LASTBOSS") >= 1:  # COMF100.ERB:55–56（S27）
            r = lastboss_reaction_ref(ctx, st.flag[11], 3)
        elif st.flag[11] in range(1, 8):
            r = boss_reaction_ref(ctx, st.flag[11], 3)
        else:
            # TENTACLE_BOSS_{FLAG:11}_REACTION_REF が無い（悪堕ちキャラ戦は FLAG:11 = 0）→ TRYCALLFORM 不発で RESULT は
            # 直前の TENTACLE_SYASEI_CHECK の RESULT（＝RESULT:0）のまま
            r = r0
        if r >= 0:
            st.tflag[17] = r
    _houshi_juel(ctx, 450, 25)
    c.ex[99] += 1
    return 1
    yield  # pragma: no cover


def com101(ctx: Ctx) -> ComGen:
    """`COMF101.ERB@COM101`:2–71（フェラ攻撃）。"""
    from .syasei import tentacle_syasei_check, tentacle_syasei_up

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    st.tflag[4] |= MOUTH
    if c.tcvarn[12] & KYOUKOUSOKU:
        st.tflag[4] = 0
    c.tcvarn[2] = P_HOUSHI
    g = abl(ctx, c, "技巧")
    st.tflag[3] += 25 + 5 * g * g
    _sex_attack_msg(ctx, 101)
    before = st.flag[15]
    local = 50 + g * min(div(c.maxbase[2] - 50, 5) + 10, 50)
    fe = exp(ctx, c, "フェラ経験")
    if fe <= 5:
        local += fe * 10
    elif fe <= 10:
        local += 50 + (fe - 5) * 5
    elif fe <= 20:
        local += 75 + (fe - 10) * 2
    elif fe <= 25:
        local += 95 + (fe - 20)
    else:
        local += 100
    tentacle_syasei_up(ctx, local)
    _pleasure_given(ctx, before)
    yield from tentacle_syasei_check(ctx)
    out.printl()
    _houshi_juel(ctx, 800, 40)
    c.exp[ctx.data.index_of("EXP", "フェラ経験")] += 1
    c.ex[99] += 1
    return 1
    yield  # pragma: no cover


def com102(ctx: Ctx) -> ComGen:
    """`COMF102.ERB@COM102`:2–93（足コキ攻撃）。"""
    from .sexcom import SEX_TYPE, enemy_action_sex_routine
    from .syasei import tentacle_syasei_check, tentacle_syasei_up

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    select = enemy_action_sex_routine(ctx)  # :13–14
    _need_boss(ctx)
    # COMF102.ERB:15–22：缺函式時保留 SELECT。
    local = mob.sex_type(st.flag[11],select,select) if _mob(ctx) else SEX_TYPE.get(select,select)
    g = abl(ctx, c, "技巧")
    rand = st.rng.rand
    # :26 `(LOCAL & 挿入) && RAND:100 < 95 || (RAND:100 < SQRT(1 + 50 * ABL:技巧))`（左結合・短絡）
    if ((local & 2) and rand(100) < 95) or rand(100) < isqrt(1 + 50 * g):
        st.tflag[4] |= WAREME
        st.tflag[4] |= BOUHATSU
        st.tflag[3] += 105 + 5 * g
        _sex_attack_msg(ctx, 102)
        before = st.flag[15]
        tentacle_syasei_up(ctx, min(div(c.maxbase[2], 2), 150) + 150 + 75 * g)
        _pleasure_given(ctx, before)
        yield from tentacle_syasei_check(ctx)
        out.printl()
        _houshi_juel(ctx, 1050, 25)
        st.tflag[17] = -1
        st.tflag[1] = 1
        c.ex[99] += 1
        return 1
    name = print_transcallname(st, st.target)
    out.printl(f"{name}は足コキ攻撃の構え！")
    out.printw()
    out.printl(f"しかし{name}の行動は失敗した！")
    out.printl()
    _houshi_juel(ctx, 250, 25)
    c.ex[99] += 1
    st.flag[17] = select  # :90 FLAG:17（TFLAG ではない：原作どおり）
    return 1
    yield  # pragma: no cover


def com103(ctx: Ctx) -> ComGen:
    """`COMF103.ERB@COM103`:2–202（素股焦らし）。"""
    from .sexcom import boss_reaction_ref, check_holyvirgin, lastboss_reaction_ref
    from .syasei import tentacle_syasei_check, tentacle_syasei_up

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    cp = st.temp.common_palam
    print_distance(ctx)
    out.printl()
    g = abl(ctx, c, "技巧")
    st.tflag[3] += 25 + 5 * g
    cc = abl(ctx, c, "Ｃ感覚")
    if cc >= 0:
        cp[0] = (250, 500, 1000, 2000, 3000, 4000)[min(cc, 5)]
    vv = abl(ctx, c, "Ｖ感覚")
    if vv >= 0:
        cp[1] = (125, 250, 500, 1000, 1500, 2000)[min(vv, 5)]
    local = 35 + g * 5
    mi = exp(ctx, c, "魅了経験")
    if mi >= 200:
        local += 20
    elif mi >= 100:
        local += 10 + div(mi - 100, 10)
    elif mi >= 50:
        local += div(mi - 50, 5)
    suit = c.cflag[40 if c.cflag[1] == 0 else 41] == 199 and c.tcvarn[41] != 0
    if suit:
        local -= 20
    elif c.cflag[42] == 400:
        local -= 10
    if check_holyvirgin(ctx) == 1:
        local = 0
    if st.flag[999]:
        raise NotImplementedError("デバッグ表示は未移植")
    cl = st.temp.cloth
    name = print_transcallname(st, st.target)
    # :67 `RAND:100 < LOCAL || CLOTH_OUTER_PER > 90 || CLOTH_INNER_PER >= CLOTH_INNER_DEF`（RAND を先に引く）
    if st.rng.rand(100) < local or cl[OUTER_PER] > 90 or cl[INNER_PER] >= cl[INNER_DEF]:
        cloth_battle_damage(ctx, 12)
        _sex_attack_msg(ctx, 103)
        before = st.flag[15]
        tentacle_syasei_up(ctx, min(div(c.maxbase[2], 4), 75) + 50 + 25 * g)
        _pleasure_given(ctx, before, wait_split=True)
        out.print("次のターン相手は")
        out.set_bold(True)
        out.print("挿入系コマンド")
        out.set_bold(False)
        out.printl("を選択しやすくなった！")
        out.printw()
        yield from tentacle_syasei_check(ctx)
        out.printl()
        _houshi_juel(ctx, 250, 25)
        st.tflag[1] = 1
        c.ex[99] += 1
        return 1
    out.printl(f"{name}は素股焦らしの構え！")
    out.printw()
    if c.base[31] > 0:  # :120–124
        out.printl(f"しかし{name}の行動は失敗した！")
        out.printl("無防備な体勢で触手に抑え込まれ、触手の攻勢に晒されるＶ結界が")
        out.printl("たちまち輝きを失っていく…")
        cp[1] *= 4
    elif t(ctx, c, "処女") > 0:  # :125–159
        out.printl(f"挑発するように素股していた{name}だったが")
        if suit or c.cflag[42] == 400:  # :127–144
            out.print(_cloth_tentacle_name(ctx, suit))
            out.printl("の触手に強制開脚させられてしまう。")
            out.printl()
            _sumata_tentacle_line(ctx)
            out.printl("なし崩し的にズブリと男根の侵入を許してしまった！")
        else:  # :145–151
            out.printl("まだ性交したことのないヴァギナに亀頭の先端がぐちゅっと挿入り込み、")
            out.printl("未知の感覚に思わず「んッ・・・❤」と色付いた吐息を漏らしてしまう。")
            out.printl()
            out.printl(f"その拍子に{name}は膣圧の加減を間違えてしまい、")
            out.printl("なし崩し的にズブリと男根の侵入を許してしまった！")
        out.printw()  # :152
        out.printl("処女喪失")
        out.printl()
        out.printl("不意に訪れた破瓜の痛みに驚き慌てて引き抜こうとするも時既に遅く、")
        out.printl(f"{name}はそのまま強制交尾の体勢に持ち込まれてしまった・・・")
        out.printw()
        cp[10] = 10000  # :156 苦痛が大量に入る
        c.talent[ctx.data.index_of("TALENT", "処女")] = -1  # :157（LOSTVIRGIN は呼ばない：原作どおり）
        c.cflag[206] = 2  # :158
    else:
        out.printl(f"しかし{name}の行動は失敗した！")
        if suit or c.cflag[42] == 400:  # :160–175
            out.print(_cloth_tentacle_name(ctx, suit))
            out.print("の触手に")
            _sumata_tentacle_line(ctx)
            out.printl("なし崩し的に挿入を許してしまう・・・")
        elif _mb(ctx) & KUSEN:
            out.printl("先走り汁に光る先端を淫裂に押し当てられたところで腰を浮かそうとするが、")
            out.printl("力で抑え込まれそのまま挿入されてしまう・・・")
        else:
            out.printl("素股だけのつもりが、先端が少しだけ挿入ったタイミングでズンと突き上げられ、")
            out.printl("そのまま雪崩れ込むように膣穴を犯されてしまう・・・")
    _houshi_juel(ctx, 50, 25)
    c.ex[99] += 1
    # :192–200。悪堕ちキャラ戦（FLAG:11 = 0：ACTION.ERB:38）は TENTACLE_BOSS_0_REACTION_REF が無く TRYCALLFORM 不発 →
    # RESULT は前の値のまま：失敗の経路では :5 PRINT_DISTANCE の関数終端（RESULT = 0）以降 CALL が無い（式中関数のみ）ので 0。
    _need_boss(ctx)
    if _mob(ctx):
        r = mob.reaction_ref(ctx,2 - (1 if c.base[31] > 0 else 0))
    elif enemy_type_check(st, "LASTBOSS") >= 1:  # :193–195（S27：MOB → LASTBOSS → BOSS の順）
        r = lastboss_reaction_ref(ctx, st.flag[11], 2 - (1 if c.base[31] > 0 else 0))
    elif st.flag[11] in range(1, 8):
        r = boss_reaction_ref(ctx, st.flag[11], 2 - (1 if c.base[31] > 0 else 0))
    else:
        r = st.result[0]
    if r >= 0:
        st.tflag[17] = r
    return 1
    yield  # pragma: no cover


def _cloth_tentacle_name(ctx: Ctx, suit: bool) -> str:
    """COMF103:128–132／:162–166：`暴走した%ITEMNAME:199%`（暴走テンタクルスーツ）または `%ITEMNAME:400%`（触手拘束具）。"""
    names = ctx.data.names["ITEM"]
    return f"暴走した{names.get(199, '')}" if suit else names.get(400, "")


def _sumata_tentacle_line(ctx: Ctx) -> None:
    """COMF103:135–141／:168–174 の 3 択（`RAND:3 == 0`、`RAND:2 == 0` の順に引く）。"""
    rand = ctx.state.rng.rand
    if rand(3) == 0:
        ctx.out.printl("拘束されて雌穴をくぱぁと広げられ、")
    elif rand(2) == 0:
        ctx.out.printl("種付けを受け入れる屈辱的な体勢を無理やり取らされ、")
    else:
        ctx.out.printl("思わぬタイミングで体勢を崩され、")


def com104(ctx: Ctx) -> ComGen:
    """`COMF104.ERB@COM104`:2–50（搾り取る）。"""
    from .syasei import tentacle_syasei_check, tentacle_syasei_up

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    g = abl(ctx, c, "技巧")
    st.tflag[3] += 80 + 20 * g
    c.tcvarn[2] = P_SHIBORU
    _sex_attack_msg(ctx, 104)
    before = st.flag[15]
    tentacle_syasei_up(ctx, 225 + g * g * isqrt(div(st.flag[15], 2) + 50))
    _pleasure_given(ctx, before)
    yield from tentacle_syasei_check(ctx)
    out.printl()
    _houshi_juel(ctx, 450, 25)
    c.ex[99] += 1
    return 1
    yield  # pragma: no cover


RESTRAINT_COMS = {8: com8, 9: com9, 10: com10, 11: com11, 12: com12, 13: com13, 14: com14, 15: com15, 40: com40,
                  44: com44, 45: com45, 46: com46, 47: com47, 100: com100, 101: com101, 102: com102, 103: com103, 104: com104}
