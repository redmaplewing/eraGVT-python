"""パラメータ上昇：`ゲーム内_戦闘処理/COMMON_PALAM_CAL.ERB@PALAM_CAL` と `PALAM_UP.ERB@PALAM_UP`。

路徑相對 `source/earGVP/ERB/`。S05 の範囲（非拘束の被弾・運動による快感）で通る部分を移植。
絶頂（快部位が絶頂しきい値に届く）・射精／噴乳・拘束中の体力等の減少・触手の射精は S06 で、
到達したら NotImplementedError で停止する。
"""

from __future__ import annotations

from ..action import Ctx, config_check_maniac, config_check_screen, kojo_root, print_transcallname
from ..chara_common import is_female, seikaku_check
from ..era import div, times
from ..tentacle import enemy_type_check
from .cloth import INNER_PER, NO_INNER, OUTER_PER, cloth_battle_hosei, figure_split
from .core import (
    DARAKU,
    KAIRAKU_TOROKE,
    KIZETU,
    KOUKOTSU,
    KUSEN,
    P_HOUSHI,
    P_SHIBORU,
    P_TAERU,
    P_UKEIRERU,
    PALAM_MAX,
    SEI_TEIKOU,
    ZETSUBOU,
    abl,
    add_exp,
    get_battle_situation,
    message_branch,
    percent_cal,
    seikaku_hosei_palam,
    shokushu_shimin,
    t,
    tc,
    tentacle_access,
    tentacle_level,
    tentacle_palam_hosei,
    unlock_achievement,
)

# CSV定数定義/PALAM.ERH
KAI_PALAM = (0, 1, 2, 3)  # 快部位PALAM
NIJI_PALAM = (12, 14, 16, 17)  # 二次計算PALAM（PALAM_UP.ERB:20–25：習得・屈服・苦痛・恐怖）
BUI_IGAI_PALAM = (10, 11, 12, 13, 14, 15, 16, 17)  # 部位以外調教PALAM
ZECCHOU_SHIKII = 10000  # 快部位絶頂しきい値:0（PALAM_UP.ERH:11–22）
_KAI_TALENT = ("淫核", "淫壷", "淫尻", "淫乳")  # CSV定数定義/TALENT.ERH:101–106 淫部位素質

# PALAM_UP.ERH：刻印判定基礎値・刻印防止係数（クズ市民補正はクズ市民戦のみ）
_MARK_TABLE = {
    # MARK 番号: (判定基礎値, 防止係数, クズ市民補正, 地の文コード, 防止 MARK 番号)
    0: ((12000, 24000, 48000, 96000, 192000), (300, 600, 1200, 2400, 4800), (5000, 10000, 20000, 40000, 80000), "KAIRAKU", 90),
    1: ((10000, 20000, 40000, 80000, 160000), (250, 500, 1000, 2000, 4000), (4000, 8000, 16000, 32000, 64000), "KUTUU", 91),
    2: ((8000, 16000, 32000, 64000, 128000), (200, 400, 800, 1600, 3200), (3000, 6000, 12000, 24000, 48000), "KUPPUKU", 92),
    3: ((8000, 16000, 32000, 64000, 128000), (200, 400, 800, 1600, 3200), (1500, 3000, 6000, 12000, 24000), "KYOUHU", 93),
    4: ((8000, 16000, 32000, 64000, 128000), (200, 400, 800, 1600, 3200), (1000, 2000, 4000, 8000, 16000), "TIJYOKU", 94),
}


def palam_cal(ctx: Ctx, *args: int, losebase: int = 0) -> None:
    """`COMMON_PALAM_CAL.ERB@PALAM_CAL`:10–24：12 個の引数を UP:快Ｃ〜恐怖 に入れて PALAM_UP。"""
    st = ctx.state
    ids = (0, 1, 2, 3, 10, 11, 12, 13, 14, 15, 16, 17)
    for pid, value in zip(ids, args):
        st.temp.up[pid] = value
    st.temp.losebase[0] = losebase
    palam_up(ctx)


# --- 補正（PALAM_UP.ERB:378–656）-------------------------------------------------------


def palam_overfeel(ctx: Ctx, who: int, part: int) -> int:
    """`@PALAM_OVERFEEL, ARG:0, ARG:1`:1692–1705。"""
    cal = 100
    lv = ctx.state.charas[who].abl[part] - 5
    if lv > 0:
        cal = div(cal * 6, 5)
        for i in range(lv - 1):
            cal = div(cal * (1087 - i), 1000)
    return cal


def palam_hosei_pose(ctx: Ctx, value: int) -> int:
    """`@PALAM_HOSEI_POSE`:629–639。"""
    pose = tc(ctx).tcvarn[2]
    if pose == P_TAERU:
        value = times(value, "0.65")
    if pose == P_UKEIRERU:
        value = times(value, "1.25")
    if pose == P_SHIBORU:
        value = times(value, "1.50")
    return value


def palam_hosei_seitaisei(ctx: Ctx, value: int) -> int:
    """`@PALAM_HOSEI_SEITAISEI`:440–460。"""
    c = tc(ctx)
    local = percent_cal(c.base[2], c.maxbase[2]) if c.base[2] > 0 else 0
    if local > 80:
        return value
    if local > 60:
        return times(value, "1.10")
    if local > 40:
        return times(value, "1.20")
    if local > 20:
        return times(value, "1.35")
    if local > 10:
        return times(value, "1.50")
    return times(value, "1.70")


def palam_hosei_talent(ctx: Ctx, pid: int, value: int) -> int:
    """`@PALAM_HOSEI_TALENT`:464–554。"""
    c = tc(ctx)
    tt = lambda n: t(ctx, c, n)  # noqa: E731
    if pid in (0, 1, 2):
        part = "ＣＶＡ"[pid]
        if tt(f"{part}敏感") > 0:
            value = times(value, "1.25")
        elif tt(f"{part}鈍感") > 0:
            value = times(value, "0.75")
        if tt(_KAI_TALENT[pid]) > 0:
            value = times(value, "1.50")
    elif pid == 3:
        if tt("Ｂ敏感") > 0:
            value = times(value, "1.25")
        elif tt("Ｂ鈍感") > 0:
            value = times(value, "0.75")
        if tt("貧乳") == 2:
            value = times(value, "0.75")
        elif tt("貧乳") == 1:
            value = times(value, "0.80")
        elif tt("巨乳") in (1, 2, 3, 4, 5):
            value = times(value, {5: "1.40", 4: "1.35", 3: "1.30", 2: "1.25", 1: "1.20"}[tt("巨乳")])
        if tt("淫乳") > 0:
            value = times(value, "1.50")
    elif pid == 10:
        if tt("濡れやすい") > 0:
            value = times(value, "2.00")
        elif tt("濡れにくい") > 0:
            value = times(value, "0.50")
        if tt("淫乱") > 0:
            value = times(value, "2.00")
    elif pid == 11:
        if tt("触手の虜") > 0:
            value = times(value, "2.00")
    elif pid == 13:
        if tt("触手の虜") > 0:
            value = times(value, "2.00")
        if tt("淫乱") > 0:
            value = times(value, "2.00")
    elif pid == 14:
        if tt("触手の虜") > 0:
            value = times(value, "2.00")
    elif pid == 15:
        if tt("パイパン") > 0:
            value = times(value, "1.50")
        if tt("淫乱") > 0:
            value = times(value, "2.00")
    return value


def palam_hosei_tentacle(ctx: Ctx, pid: int, value: int) -> int:
    """`@PALAM_HOSEI_TENTACLE`:564–609。"""
    st = ctx.state
    if st.flag[700] == 0 or enemy_type_check(st, "AKUOTI"):
        return value
    r = tentacle_palam_hosei(ctx)
    idx = {0: 0, 1: 1, 2: 2, 3: 3, 10: 4, 11: 5, 12: 6, 13: 7, 14: 8, 15: 9, 16: 10, 17: 11}.get(pid)
    if idx is None:
        return value
    return div(value * r[idx], 100)


def palam_hosei_poisoning(ctx: Ctx, value: int) -> int:
    """`@PALAM_HOSEI_POISONING_TENTACLE`:613–625。"""
    lv = abl(ctx, tc(ctx), "触手中毒")
    f = {1: "1.20", 2: "1.50", 3: "2.00", 4: "2.50", 5: "4.00"}.get(lv)
    return times(value, f) if f else value


def palam_hosei_random(ctx: Ctx, value: int) -> int:
    """`@PALAM_HOSEI_RANDOM`:643–656。"""
    r = ctx.state.rng.rand(100)
    if r < 20:
        return times(value, "1.10")
    if r < 40:
        return times(value, "1.05")
    if r < 60:
        return times(value, "1.00")
    if r < 80:
        return times(value, "0.95")
    return times(value, "0.90")


def palam_hosei(ctx: Ctx, pid: int, value: int) -> int:
    """`@PALAM_HOSEI, PALAMID, UPVALUE`:378–435。"""
    st = ctx.state
    if value > 0:
        if pid in KAI_PALAM:
            # :386 `UPVALUE *= RESULT / 100`（整数除算）
            value *= div(palam_overfeel(ctx, st.target, pid), 100)
        value = palam_hosei_pose(ctx, value)
        if pid == 15:
            if st.flag[71] or get_battle_situation(st, "常時撮影"):
                value = div(value * (360 + st.flag[71] * 40 + st.flag[70] * 20), 100)
            elif st.flag[70]:
                value = div(value * (180 + st.flag[70] * 20), 100)
        if pid != 10:
            value = palam_hosei_seitaisei(ctx, value)
        value = palam_hosei_talent(ctx, pid, value)
        value = seikaku_hosei_palam(seikaku_check(ctx.data, tc(ctx)), pid, value)
        value = palam_hosei_tentacle(ctx, pid, value)
        if pid in (14, 13, 11):
            value = palam_hosei_poisoning(ctx, value)
        value = palam_hosei_random(ctx, value)
        if value <= 0:
            value = 1
    return value


# --- 個別計算（PALAM_UP.ERB:989–1326）--------------------------------------------------


def palam_tijou_cloth_damage(ctx: Ctx) -> int:
    """`@PALAM_TIJOU_CLOTH_DAMAGE`:989–1031。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    cl = st.temp.cloth
    tr = c.cflag[1]
    if (tr == 0 and v[20] == -1) or (tr >= 1 and v[22] == -1):
        cid = c.cflag[40 if tr == 0 else 41]
        if cid == 199 and figure_split(c.equip[99 if tr == 0 else 199], 1) != 0 and v[41] == 0:
            return 0  # :993 RETURN（値なし）→ RESULT = 0
        if cid in (299, 401):
            return 350
    local = 0
    if v[21 if tr == 0 else 23] == 0 and (v[25] == 0 or cl[NO_INNER]):
        local += 500
    elif cl[NO_INNER]:
        op = cl[OUTER_PER]
        local += 350 if op < 25 else 150 if op < 50 else 50 if op < 75 else 0
    else:
        op, ip = cl[OUTER_PER], cl[INNER_PER]
        local += 100 if op < 25 else 50 if op < 50 else 0
        local += 250 if ip < 25 else 100 if ip < 50 else 50 if ip < 100 else 0
    if st.flag[700]:
        local = div(local * cloth_battle_hosei(ctx, "SHYNESS"), 100)
    return local


def _steps(value: int, bounds: tuple[int, ...], adds: tuple[int, ...]) -> int:
    """`IF ARG == 0 / ELSEIF ARG < b0 … / ELSE` 形式の段階加算。"""
    if value == 0:
        return 0
    for b, a in zip(bounds, adds):
        if value < b:
            return a
    return adds[-1]


def _nowex_add(n: int, adds: tuple[int, int, int]) -> int:
    return adds[0] if n == 1 else adds[1] if n == 2 else adds[2] if n > 2 else 0


def palam_tijou(ctx: Ctx, ups: tuple[int, int, int, int]) -> int:
    """`@PALAM_TIJOU`:1035–1059。"""
    c = tc(ctx)
    local = 0
    for i, u in enumerate(ups):
        local += _steps(u, (100, 1000, 2000, 5000), (50, 100, 200, 500, 1000))
        local += _nowex_add(c.nowex[i], (500, 1000, 2000))
    return local


_EXPO = {
    1: (10, 20, 50, 100, 200),
    2: (20, 50, 100, 200, 500),
    3: (50, 100, 200, 500, 1000),
    4: (100, 200, 500, 1000, 2000),
    5: (200, 500, 1000, 2000, 5000),
}


def palam_yokujou(ctx: Ctx, ups: tuple[int, int, int, int], shame: int, pain: int) -> int:
    """`@PALAM_YOKUJOU`:1063–1227。"""
    c = tc(ctx)
    local = 0
    for i, u in enumerate(ups):
        local += _steps(u, (100, 500, 1000, 2000, 5000, 7500), (500, 900, 1200, 1500, 2000, 3500, 5000))
        local += _nowex_add(c.nowex[i], (1000, 2000, 5000))
    ro = abl(ctx, c, "露出癖")
    if ro in _EXPO:
        local += _steps(shame, (100, 1000, 2000, 5000), _EXPO[ro])
    ma = abl(ctx, c, "マゾっ気")
    if ma in _EXPO:
        local += _steps(pain, (100, 1000, 2000, 5000), _EXPO[ma])
    return local


def palam_junkatu(value: int) -> int:
    """`@PALAM_JUNKATU`:1231–1247。"""
    return _steps(value, (100, 1000, 2000, 5000, 10000), (50, 100, 200, 500, 1000, 2000))


def palam_kyoujun(ctx: Ctx, ups: tuple[int, int, int, int]) -> int:
    """`@PALAM_KYOUJUN`:1251–1275。"""
    c = tc(ctx)
    local = 0
    for i, u in enumerate(ups):
        local += _steps(u, (4000, 8000, 12000, 20000), (50, 100, 200, 400, 800))
        local += _nowex_add(c.nowex[i], (500, 1000, 2000))
    return local


def palam_personality_adjust(ctx: Ctx) -> None:
    """`@PALAM_CALC_PERSONALITY_ADJUST`:1279–1326。"""
    up = ctx.state.temp.up
    c = tc(ctx)
    tt = lambda n: t(ctx, c, n) > 0  # noqa: E731

    def tm(pid: int, f: str) -> None:
        up[pid] = times(up[pid], f)

    if tt("小心者"):
        tm(15, "0.90")
        tm(16, "1.10")
    if tt("プライド高い") and c.mark[2] >= 3:
        tm(14, "1.20")
    elif tt("プライド高い"):
        tm(14, "0.90")
    if tt("保守的"):
        tm(12, "0.90")
    if tt("好奇心"):
        tm(12, "1.10")
    if tt("快楽に弱い"):
        tm(11, "1.10")
        tm(16, "0.90")
    if tt("快楽の否定"):
        tm(13, "0.90")
        tm(14, "1.10")
    if tt("争いを好まない"):
        tm(14, "0.90")
        tm(17, "1.10")
    if tt("喧嘩上等"):
        tm(13, "1.10")
        tm(17, "0.90")
    if tt("恥じらい"):
        tm(11, "0.90")
        tm(15, "1.10")
    if tt("度胸"):
        tm(13, "1.10")
        tm(15, "0.90")
    if tt("母性的"):
        tm(11, "1.10")
    if tt("小悪魔"):
        tm(14, "1.10")
    if tt("目立ちたがり"):
        tm(16, "1.10")
    if tt("上品"):
        tm(15, "1.10")
    if tt("泣き虫"):
        tm(17, "1.10")


# --- 刻印（PALAM_UP.ERB:1767–1801、地の文/MESSAGE_SEX.ERB:401–762）------------------------

_MARK_MSG = {
    "KAIRAKU": ("{e}のもたらす快楽に", ("とまどっている・・・", "自分の理性が揺らいでいくのを感じる・・・",
                                       "飲み込まれそうになっている・・・", "完全に飲み込まれてしまった・・・", None)),
    "KUTUU": ("{e}の痛みを伴う激しい攻めに", (None, "自分の戦意が揺らいでいくのを感じる・・・",
                                            "打ちのめされそうになっている・・・", "完全に打ちのめされてしまった・・・", None)),
    "KUPPUKU": ("触手から与えられる屈辱に", (None, "自分の無力さを痛感している・・・", "心が折れそうになっている・・・",
                                          "完全に心が折れてしまった・・・", "倒錯した悦びを感じている・・・")),
    "KYOUHU": ("触手の容赦ない行動に", ("内心で冷や汗を流す・・・", None, "強い身の危険を感じている・・・",
                                     "完全に竦み上がっている・・・", "錯乱状態に陥り理性を失っている・・・")),
    "TIJYOKU": ("触手からの辱めに", ("顔を赤らめている・・・", "何とか耐えている・・・", "プライドがぐらついている・・・",
                                  "完全にプライドを打ち砕かれてしまった・・・", "人としての尊厳を見失ってしまった・・・")),
}


def _mark_message(ctx: Ctx, code: str, level: int) -> None:
    """`MESSAGE_SEX_MARK_{code}_{level}`（地の文/MESSAGE_SEX.ERB:401–762、触手戦の分岐のみ）。"""
    st = ctx.state
    out = ctx.out
    if enemy_type_check(st, "AKUOTI") == 1:
        raise NotImplementedError("悪堕ちキャラ戦の刻印地の文は未移植")
    name = print_transcallname(st, st.target)
    subjective = t(ctx, tc(ctx), "主観視点") > 0
    if st.flag[700] == 1 or st.target_chara.cflag[0] == 1:
        head_tpl, tails = _MARK_MSG[code]
        head = head_tpl.format(e=shokushu_shimin(st, "触手", "男たち"))
        tail = tails[level - 1]
        if code == "KAIRAKU" and level == 5:  # :453–471
            out.print(f"{name}は{shokushu_shimin(st, '触手', '男たち')}のもたらす快楽を貪る")
            out.printl("一匹の雌奴隷へと、完全に作り替えられてしまった・・・" if subjective else "一匹の雌豚と化した・・・")
        elif code == "KUTUU" and level == 1:  # :474–491
            out.print(f"{name}は{head}")
            out.printl("思わず顔を歪めてしまう・・・" if subjective else "辛そうに顔を歪めた・・・")
        elif code == "KUTUU" and level == 5:  # :533–549
            e = shokushu_shimin(st, "触手", "男たち")
            if subjective:
                out.print(f"気付くと{name}は{e}に向かって")
                out.printl("命乞いをしてしまっていた・・・")
            else:
                out.print(f"{name}は{head}")
                out.printl("命乞いを始めた・・・")
        elif code == "KUPPUKU" and level == 1:  # :552–570
            out.print(f"{name}は{head}")
            out.printl("思わず顔を歪めてしまった・・・" if subjective else "悔しそうに顔を歪めた・・・")
        elif code == "KYOUHU" and level == 2:  # :638–656
            out.print(f"{name}は{head}")
            out.printl("底知れない恐怖を感じる・・・" if subjective else "怯え始めた・・・")
        else:
            out.print(f"{name}は{head}")
            out.printl(str(tail))
    kojo_root(ctx, f"SEX_MARK_{code}_{level}")


def got_sex_mark_check(ctx: Ctx, mark_id: int, upvalue: int) -> None:
    """`@GOT_SEX_MARK_CHECK`:1767–1801。"""
    st = ctx.state
    c = tc(ctx)
    base, factor, kuzu, code, prevent_id = _MARK_TABLE[mark_id]
    m = c.mark[mark_id]
    if m < 0 or m >= len(base) or (st.flag[700] != 1 and c.cflag[0] != 1) or (c.tcvarn[12] & KIZETU):
        return
    need = base[m] + c.mark[prevent_id] * factor[m] + (kuzu[m] if st.flag[73] > 0 else 0)
    if upvalue >= need:
        c.mark[mark_id] += 1
        _mark_message(ctx, code, c.mark[mark_id])
        out = ctx.out
        out.print(f"{print_transcallname(st, st.target)}は")
        out.set_bold(True)
        out.print(f"{ctx.data.names['MARK'].get(mark_id, '')}{c.mark[mark_id]}")
        out.set_bold(False)
        out.printl("を取得した")
        out.printl()


def message_branch_faith_down(ctx: Ctx) -> None:
    """`地の文/MESSAGE_SEX.ERB@MESSAGE_BRANCH_MESSAGE_FAITH_DOWN`:1851–1897。"""
    st = ctx.state
    out = ctx.out
    name = print_transcallname(st, st.target)
    mb = message_branch(ctx)
    subjective = t(ctx, tc(ctx), "主観視点") > 0
    if mb & DARAKU:
        if (st.tflag[97] & DARAKU) == 0:
            out.set_bold(True)
            out.printl("理性陥落")
            out.set_bold(False)
            if subjective:
                out.printl(f"常軌を逸した快楽に{name}の理性はどんどん溶かされていく・・・")
            else:
                out.printl(f"快楽に屈した{name}の瞳から理性の光が消えていく・・・")
            out.printl()
            st.tflag[97] |= DARAKU
    elif mb & KAIRAKU_TOROKE:
        if (st.tflag[97] & KAIRAKU_TOROKE) == 0:
            out.set_bold(True)
            out.printl("理性破損")
            out.set_bold(False)
            fainted = tc(ctx).tcvarn[12] & KIZETU
            if message_branch(ctx) & ZETSUBOU:
                if fainted:
                    raise NotImplementedError("PRINT_SWOON（気絶中の理性破損文）は未移植")
                if st.tflag[0] < 5:
                    out.print("早々に")
                out.print("戦意を挫かれ完全に快楽に屈した")
                out.printl(f"{name}は無様なアヘ顔を晒している・・・")
            elif message_branch(ctx) & KUSEN:
                if fainted:
                    out.printl(f"意識を失った{name}の身体は、暴力的な快楽に最後の抵抗を続けている・・・")
                else:
                    out.printl(f"快楽に理性を失いかけながらも、{name}はまだ戦う意志を失っていない・・・")
            else:
                if fainted:
                    out.printl(f"意識と共に理性の庇護を喪った{name}の身体は、本能によって快楽に蝕まれつつある・・・")
                else:
                    out.printl(f"{name}の意志とは裏腹に、身体は快楽を受け入れてしまっている・・・")
            out.printl()
            st.tflag[97] |= KAIRAKU_TOROKE
    elif mb & SEI_TEIKOU:
        if (st.tflag[97] & SEI_TEIKOU) == 0:
            # :1892–1895 FONTBOLD／「理性低下」だけで TFLAG:97 は立てない（毎回出る：原作どおり）
            out.set_bold(True)
            out.printl("理性低下")
            unlock_achievement(ctx, 280, "ダルマ牧場")


# --- 敵の反応（PALAM_UP.ERB:1806–1890）------------------------------------------------


def palam_up_enemy_reaction(ctx: Ctx) -> None:
    st = ctx.state
    c = tc(ctx)
    if st.tflag[23] == -1 or (c.base[0] <= 0 and c.base[1] <= 0 and c.base[2] <= 0):
        return
    local = cloth_battle_hosei(ctx, "YUDAN")
    l1 = min(tentacle_level(st), 60)
    if t(ctx, c, "平凡") > 0:
        local += 25
    if t(ctx, c, "攻勢構築") > 0:
        local -= 25
    if st.flag[700] == 1:
        st.tflag[3] *= div(local, 100)  # :1823 `TFLAG:3 *= LOCAL / 100`（整数除算）
        st.flag[17] = max(0, min(st.flag[17] + st.tflag[3], st.flag[16] * 2))
        if c.tcvarn[0] == 0:
            st.flag[17] += div(st.flag[16] * 6 * local, 10000)
        elif st.tflag[2] > 0:
            st.flag[17] -= div(st.flag[16] * 12, 100)
        else:
            st.flag[17] -= div(st.flag[16] * 1, 100)
        if st.flag[17] < 0:
            st.flag[17] = 0
        if st.flag[999]:
            raise NotImplementedError("デバッグ表示は未移植")
        st.tflag[3] = 0
        if 0 < st.tflag[2] <= 2 and st.flag[17] < st.flag[16]:
            st.flag[17] = st.flag[16]
        elif st.tflag[2] >= 12 - div(l1, 10):
            st.flag[17] = 0
        if st.flag[17] >= st.flag[16]:
            st.tflag[2] += 1
        elif st.tflag[2] > 0:
            st.tflag[2] = 0
            st.flag[17] = 0
            ctx.out.printl()
            if st.flag[110] == 0:
                tentacle_access(ctx, "NAME")
                ctx.out.printl("は油断から立ち直った")
            else:
                raise NotImplementedError("悪堕ちキャラ戦は未移植")
    if c.tcvarn[0] == 0 and st.flag[700] == 1:
        raise NotImplementedError("凌辱時の応援（PERFORM_CHEERS_TENTACLE_SEX_HANTEI）は S06")
    if st.tflag[2] > 0 and st.flag[700] == 1:
        ctx.out.printl()
        if st.flag[110] == 0:
            tentacle_access(ctx, "NAME")
            ctx.out.printl("は油断しているようだ")
        else:
            raise NotImplementedError("悪堕ちキャラ戦は未移植")


# --- @PALAM_UP（PALAM_UP.ERB:13–367）-------------------------------------------------


def palam_up(ctx: Ctx) -> None:
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    up = st.temp.up
    cp = st.temp.common_palam
    # :31–46 快部位の補正と絶頂可能性
    possible = 0
    for pc in range(4):
        up[pc] = palam_hosei(ctx, pc, up[pc])
        up[pc] += cp[pc]
        if c.palam[pc] + up[pc] > ZECCHOU_SHIKII:
            possible += c.palam[pc] + div(div(up[pc] * c.abl[pc], 15) * (t(ctx, c, _KAI_TALENT[pc]) + 5), 5)
    if possible > 0:
        raise NotImplementedError("快部位の絶頂判定（FUNC_PALAM_CALC_ENDURE_ECSTACY 以降）は S06")
    # :49 ECS_FLAG = -1（BASE_PALAM <= 0）
    for pc in range(4):
        if up[pc] > 0:
            add = up[pc]
            if c.base[30 + pc] > 0 and st.flag[700] and v[0] == 0 and st.tflag[10] != 1006:
                raise NotImplementedError("部位結界の処理（拘束中）は S06")
            c.palam[pc] += add
            # :79 PALAM_CALC_ECSTASY（IS_FORBID_EX = -1）：PALAM がしきい値以上なら絶頂
            if c.palam[pc] >= ZECCHOU_SHIKII:
                raise NotImplementedError("快部位の絶頂（PALAM_CALC_ECSTASY）は S06")
            c.nowex[pc] = 0
    # :92 PALAM_CALC_GAPING（TFLAG:1 == 0 のとき）
    if st.tflag[1] == 0:
        if st.flag[700] > 0 and config_check_maniac(st, 16) == 1 and c.cflag[34] > 0:
            raise NotImplementedError("PRINT_TENTACLE_SIZE（拡張度表示）は未移植")
        if st.temp.insert:
            raise NotImplementedError("挿入による拡張（GAPING）は S06")
    for pc in range(4):
        cp[pc] = 0
    # :100–113 動画撮影フラグ
    if st.flag[71] > 0 or get_battle_situation(st, "常時撮影"):
        if c.stain[3] & 4:
            st.tflag.set_bit(21, 4)
        if c.stain[4] & 4:
            st.tflag.set_bit(21, 5)
        if (c.stain[0] & 4) or (c.stain[1] & 4) or (c.stain[2] & 4):
            st.tflag.set_bit(21, 6)
    # :120–133 二次計算（原作は PALAM_HOSEI に PCOUNT（0〜3）を渡しており、快部位用の補正が掛かる：原作どおり）
    for pc, pid in enumerate(NIJI_PALAM):
        up[pid] = palam_hosei(ctx, pc, up[pid])
        up[pid] += cp[pid]
        cp[pid] = 0
    if v[2] == P_HOUSHI:
        up[12] += 150 + 15 * (abl(ctx, c, "従順") + abl(ctx, c, "奉仕精神") * 2)
    # :144–152 触手の射精チェック
    if st.flag[700] == 1:
        if st.flag[15] >= st.flag[14]:
            raise NotImplementedError("触手の射精（TENTACLE_SYASEI_CHECK）は S06")
        st.tflag[5] = 0
    # :155 PALAM_CALC_EJAC（射精は NOWEX:Ｃ絶頂 > 0 が前提。絶頂は上で停止するので射精値の加算のみ）
    if not (t(ctx, c, "ふたなり") == 0 and (is_female(ctx.data, c) or t(ctx, c, "未熟") == 1)):
        if up[0]:
            if config_check_screen(st, 1) > 0:
                raise NotImplementedError("調教ステータス表示（CONFIG_CHECK_SCREEN_F(1)）は未移植")
            c.base[20] += up[0] + 500 * (c.nowex[0] + 1)
    # :158 PALAM_CALC_MILK_SQIRT（同上）
    if t(ctx, c, "母乳体質") == 1 and up[3]:
        if config_check_screen(st, 1) > 0:
            raise NotImplementedError("調教ステータス表示（CONFIG_CHECK_SCREEN_F(1)）は未移植")
        c.base[21] += div(up[3], 4) + 500 * (c.nowex[3] + 1)
    ctx.out.printl()
    # :165–174 恥情
    up[15] += palam_tijou_cloth_damage(ctx)
    ups = (up[0], up[1], up[2], up[3])
    up[15] += palam_tijou(ctx, ups)
    up[15] = palam_hosei(ctx, 15, up[15])
    # :180–185 欲情
    up[13] += palam_yokujou(ctx, ups, up[15], up[16])
    up[13] = palam_hosei(ctx, 13, up[13])
    # :191–196 潤滑
    up[10] += palam_junkatu(up[13])
    up[10] = palam_hosei(ctx, 10, up[10])
    # :202–213 恭順（ECS_NUM = 0）
    up[11] += palam_kyoujun(ctx, ups)
    up[11] = palam_hosei(ctx, 11, up[11])
    # :217–228
    if v[12] & KIZETU:
        for pid in (14, 15, 16, 17):
            up[pid] = times(up[pid], "0.25")
    elif v[12] & KOUKOTSU:
        for pid in (11, 12, 13, 14):
            up[pid] = times(up[pid], "1.25")
    # :231–246 絶頂回数（0）による珠・油断：変化なし
    # :250–259 経験
    if up[15] > 2000 and up[13] > 2000:
        add_exp(ctx, c, "露出快楽経験", 1)
    if up[13] > 2000 and (v[2] == P_HOUSHI or (st.temp.selectcom >= 100 and st.temp.selectcom < 200)):
        add_exp(ctx, c, "奉仕快楽経験", 1)
    if up[16] > 2000 and up[13] > 2000:
        add_exp(ctx, c, "苦痛快楽経験", 1)
    # :262–275 絶頂の地の文（絶頂なし・ECS_FLAG = -1 のため何も出ない）
    # :282–295 TFLAG:20（性攻撃の番号）による状態異常：非拘束時は TFLAG:20 が -999／-1 なので該当しない
    if st.tflag[20] in (1004, 6, 1000, 1001, 1012, 1015, 8, 9, 12, 1009, 1010, 1013):
        raise NotImplementedError(f"TFLAG:20 = {st.tflag[20]} の状態異常は S06")
    palam_personality_adjust(ctx)
    if any(up[i] for i in range(0, 100)) and config_check_screen(st, 1) > 0:
        raise NotImplementedError("調教ステータス表示（CONFIG_CHECK_SCREEN_F(1)）は未移植")
    for pid in BUI_IGAI_PALAM:
        if up[pid] > 0:
            c.palam[pid] += min(up[pid], PALAM_MAX)
    # :320–330 体力・気力・性耐性の減算（拘束中または暴走した触手服のみ）
    if st.flag[700] == 1 and (v[0] == 0 or (v[41] != 0 and c.cflag[40 if c.cflag[1] == 0 else 41] == 199)):
        raise NotImplementedError("PALAM_TAIRYOKUDOWN 等（拘束中の消耗）は S06")
    for mark_id, pid in ((0, 13), (1, 16), (2, 14), (3, 17), (4, 15)):
        got_sex_mark_check(ctx, mark_id, up[pid])
    message_branch_faith_down(ctx)
    # :352 GET_STATE_EXPUP：実績のみ（UNLOCK_ACHIEVEMENT、deviations「全域資料」）
    if st.flag[13] <= 0 and st.flag[700] == 1:
        raise NotImplementedError("搾精による撃破（PALAM_UP から JUMP SOURCE_CHECK）は S06")
    palam_up_enemy_reaction(ctx)
    if c.cflag[1] > 0 and t(ctx, c, "処女") == -1 and is_female(ctx.data, c) and t(ctx, c, "変身時非処女") == 0:
        c.talent[ctx.data.index_of("TALENT", "変身時非処女")] = 1
    st.temp.up.clear()
    st.temp.losebase.clear()
