"""非戦闘イベントのパラメータ変動：`ゲーム内_イベント発生/EVENT_PALAM_UP.ERB`（＋`.ERH` の刻印しきい値）。

路徑相對 `source/earGVP/ERB/`。UP（`TempVars.up`、添字 = PALAM 番号）を読み、JUEL に加えて VARSET UP する。
原作どおりの注意点（照翻、deviations.md「原作行為」）：
- :19–21／:137–139／:88–90 のループは `FOR LCOUNT, 0, VARSIZE("調教PALAM")`（= 12）で `UP:LCOUNT` を直接添字にするので、
  対象は UP:0〜11（快Ｃ〜快Ｂ・未使用 4〜9・潤滑 10・恭順 11）。習得〜恐怖（UP:12〜17）は 9〜10 倍・触手補正・背徳の烙印を受けない。
- :134–140 幽閉中（CFLAG:0 が 1／2／3／9）は `UP:i = RESULT:i / 100`（触手の補正 % ÷ 100）で**上書き**する（乗算ではない）。
- :265–295 `FUNC_EVENT_PALAM_CALC_TIJYOU_BONUS` の絶頂回数判定は自分の LOCAL:100〜103（どこでも代入されず 0）を見るので常に ×1.00。
"""

from __future__ import annotations

from ..action import Ctx, print_transcallname
from ..battle.core import KANKAKU_NUM, abl, is_penis, seikaku_hosei_palam, t, tc
from ..battle.palam import message_shield_state, palam_overfeel
from ..chara_common import seikaku_check
from ..era import div, isqrt, times
from ..tentacle import enemy_type_check

TRAIN_PALAM_SIZE = 12  # CSV定数定義/PALAM.ERH:10–23 VARSIZE("調教PALAM")
KAI, V, A, B = 0, 1, 2, 3
JUNKATSU, KYOUJUN, SYUTOKU, YOKUJOU, KUPPUKU, TIJOU, KUTUU, KYOUFU = 10, 11, 12, 13, 14, 15, 16, 17  # Palam.csv

# EVENT_PALAM_UP.ERH:14–97（刻印判定基礎値／防止係数、非戦闘）、:100–106 幽閉日数しきい値
_MARK_TABLES = {
    0: ((600, 1800, 6000, 18000, 60000), (60, 180, 600, 1800, 6000), "KAIRAKU"),
    1: ((500, 1500, 5000, 15000, 50000), (50, 150, 500, 1500, 5000), "KUTUU"),
    2: ((400, 1200, 4000, 12000, 40000), (40, 120, 400, 1200, 4000), "KUPPUKU"),
    3: ((400, 1200, 4000, 12000, 40000), (40, 120, 400, 1200, 4000), "KYOUHU"),
    4: ((400, 1200, 4000, 12000, 40000), (40, 120, 400, 1200, 4000), "TIJYOKU"),
}
_PRISON_DAYS_THRESHOLD = (0, 6, 12, 18, 24)
_TENTACLE_ADDICTION = {1: "1.20", 2: "1.50", 3: "2.00", 4: "2.50", 5: "4.00"}  # :144–155


def event_palam_up(ctx: Ctx, ignore_shield: int = 0) -> None:
    """`@EVENT_PALAM_UP, IGNORE_SHIELD = 0`:10–105。"""
    st, data = ctx.state, ctx.data
    c = tc(ctx)
    up = st.temp.up
    rand = st.rng.rand
    for i in range(TRAIN_PALAM_SIZE):  # :19–21
        up[i] = up[i] * 9 + rand(up[i] + 1)
    event_palam_hosei(ctx, ignore_shield)  # :24
    c.nowex.clear()  # :27 VARSET NOWEX
    for i in range(KANKAKU_NUM):  # :28–31
        if up[i] > 1000:
            c.nowex[i] = div(isqrt(up[i]), 10)
    up[TIJOU] += _tijyou_bonus(ctx)  # :34
    up[YOKUJOU] += _yokujyou_bonus(ctx)  # :37
    ex = lambda n: data.index_of("EX", n)  # noqa: E731
    ejac = sqirt = 0  # #DIM DYNAMIC（呼び出しごとに 0）
    if enemy_type_check(st, "BOSS") == 1 and is_penis(ctx):  # :42–43
        ejac = div(c.nowex[ex("Ｃ絶頂")], max(6 - abl(ctx, c, "射精中毒"), 1))
    up[YOKUJOU] += 200 * ejac  # :46–48
    up[KUPPUKU] += 200 * ejac
    up[TIJOU] += 200 * ejac
    if t(ctx, c, "母乳体質") > 0:  # :52–53
        sqirt = div(c.nowex[ex("Ｂ絶頂")], max(6 - abl(ctx, c, "噴乳中毒"), 1))
    up[KYOUJUN] += 200 * sqirt  # :56–58
    up[YOKUJOU] += 200 * sqirt
    up[TIJOU] += 200 * sqirt
    if c.cflag[0] == 1:  # :61–76
        mk = lambda n: data.index_of("MARK", n)  # noqa: E731
        got_event_sex_mark_check(ctx, 0, up[YOKUJOU], c.mark[mk("快楽刻印防止")], 65535)
        got_event_sex_mark_check(ctx, 1, up[KUTUU], c.mark[mk("苦痛刻印防止")], c.cflag[31])
        got_event_sex_mark_check(ctx, 2, up[KUPPUKU], c.mark[mk("屈服刻印防止")], c.cflag[31])
        got_event_sex_mark_check(ctx, 3, up[KYOUFU], c.mark[mk("恐怖刻印防止")], c.cflag[31])
        got_event_sex_mark_check(ctx, 4, up[TIJOU], c.mark[mk("恥辱刻印防止")], c.cflag[31])
    ce = st.temp.common_exp  # :80–83（DIM.ERH:18 COMMON_EXP、非 SAVEDATA）
    ce.clear()
    ce[22] = sum(c.nowex[i] for i in range(KANKAKU_NUM))
    ce[53] = ejac
    ce[54] = sqirt
    if t(ctx, c, "背徳の烙印") > 0:  # :87–91
        for i in range(TRAIN_PALAM_SIZE):
            up[i] = times(up[i], "1.35")
    for pid in (KAI, V, A, B, KYOUJUN, SYUTOKU, YOKUJOU, KUPPUKU, TIJOU, KUTUU, KYOUFU):  # :92–103（潤滑は加えない）
        c.juel[pid] += up[pid]
    up.clear()  # :105 VARSET UP


def event_palam_hosei(ctx: Ctx, ignore_shield: int) -> None:
    """`@EVENT_PALAM_HOSEI, IGNORE_SHIELD`:118–177。"""
    from .event import tentacle_access_prison

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    up = st.temp.up
    _calc_talent(ctx)  # :123
    seikaku = seikaku_check(data, c)  # :126–131
    for pid in (YOKUJOU, KUPPUKU, TIJOU, KUTUU, KYOUFU):
        up[pid] = seikaku_hosei_palam(seikaku, pid, up[pid])
    if c.cflag[0] in (1, 2, 3, 9):  # :134–140
        r = tentacle_access_prison(ctx, st.target, "PALAM_HOSEI")
        for i in range(TRAIN_PALAM_SIZE):
            up[i] = div(r[i], 100)
    factor = _TENTACLE_ADDICTION.get(abl(ctx, c, "触手中毒"))  # :143–156
    if factor:
        for i in range(TRAIN_PALAM_SIZE):
            up[i] = times(up[i], factor)
    for p in range(KANKAKU_NUM):  # :159–177
        up[p] = div(up[p] * palam_overfeel(ctx, st.target, p), 100)
        base_no = 30 + p  # CSV定数定義/BASE.ERH:9–14 基礎部位結界 = Ｃ〜Ｂ結界耐久力（30〜33）
        if c.base[base_no] > 0 and ignore_shield == 0:
            dmg = up[p] * 150 + (up[p] > 0) * 2000
            if st.flag[999] == 1:
                out.set_color((96, 96, 96))
                bname = data.names["BASE"].get(base_no, "")
                out.printl(f"/* debug */ {bname}：{c.base[base_no]} - {dmg} = {c.base[base_no] - up[p] * 150 + (up[p] > 0) * 2000}")
                out.reset_color()
            c.base[base_no] -= dmg
            if up[p] > 0:
                message_shield_state(ctx, p)
            up[p] = 0


def _calc_talent(ctx: Ctx) -> None:
    """`@EVENT_PALAM_CALC_TALENT`:182–258（:220–229 の巨乳は 快Ｖ に掛かる：原作どおり）。"""
    c = tc(ctx)
    up = ctx.state.temp.up
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    for pid, part, inn in ((KAI, "Ｃ", "淫核"), (V, "Ｖ", "淫壷"), (A, "Ａ", "淫尻")):
        if tl(f"{part}敏感") > 0:
            up[pid] = times(up[pid], "2.00")
        elif tl(f"{part}鈍感") > 0:
            up[pid] = times(up[pid], "0.50")
        if tl(inn) > 0:
            up[pid] = times(up[pid], "1.50")
    if tl("Ｂ敏感") > 0:  # :211–215
        up[B] = times(up[B], "2.00")
    elif tl("Ｂ鈍感") > 0:
        up[B] = times(up[B], "0.50")
    if tl("貧乳") == 2:  # :216–230
        up[B] = times(up[B], "0.75")
    elif tl("貧乳") == 1:
        up[B] = times(up[B], "0.80")
    elif tl("巨乳") in (1, 2, 3, 4, 5):
        up[V] = times(up[V], {5: "1.40", 4: "1.35", 3: "1.30", 2: "1.25", 1: "1.20"}[tl("巨乳")])
    if tl("淫乳") > 0:  # :231–232
        up[B] = times(up[B], "1.50")
    if tl("触手の虜") > 0:  # :235–236
        up[KYOUJUN] = times(up[KYOUJUN], "2.00")
    if tl("触手の虜") > 0:  # :241–244
        up[YOKUJOU] = times(up[YOKUJOU], "2.00")
    if tl("淫乱") > 0:
        up[YOKUJOU] = times(up[YOKUJOU], "2.00")
    if tl("触手の虜") > 0:  # :247–248
        up[KUPPUKU] = times(up[KUPPUKU], "2.00")
    if tl("パイパン") > 0:  # :251–254
        up[TIJOU] = times(up[TIJOU], "1.50")
    if tl("淫乱") > 0:
        up[TIJOU] = times(up[TIJOU], "2.00")


def _tijyou_bonus(ctx: Ctx) -> int:
    """`@FUNC_EVENT_PALAM_CALC_TIJYOU_BONUS`:262–295（:284–293 は常に ×1.00：モジュール docstring）。"""
    up = ctx.state.temp.up
    local = up[KAI] + up[V] * 2 + up[A] * 2 + up[B]
    if local == 0:
        return 0
    for bound, v in ((1000, 200), (3000, 500), (5000, 1000), (10000, 2000), (30000, 5000), (50000, 10000)):
        if local < bound:
            return v
    return 20000


def _yokujyou_bonus(ctx: Ctx) -> int:
    """`@FUNC_EVENT_PALAM_CALC_YOKUJYOU_BONUS`:299–387。"""
    c = tc(ctx)
    up = ctx.state.temp.up
    local = up[KAI] + up[V] * 2 + up[A] * 2 + up[B]
    l1 = 0
    if local == 0:
        l1 = 0
    else:
        for bound, v in ((1000, 100), (3000, 200), (5000, 500), (10000, 1000), (20000, 2000), (35000, 5000)):
            if local < bound:
                l1 = v
                break
        else:
            l1 = 10000
    local = sum(c.nowex[i] for i in range(KANKAKU_NUM))  # :327–336
    if local < 10:
        l1 = times(l1, "1.00")
    elif local < 25:
        l1 = times(l1, "2.00")
    elif local < 50:
        l1 = times(l1, "3.00")
    else:
        l1 = times(l1, "4.00")
    tj = up[TIJOU]  # :339–349
    l2 = 0 if tj == 0 else 500 if tj < 1000 else 1000 if tj < 3000 else 2000 if tj < 5000 else 5000
    ro = abl(ctx, c, "露出癖")  # :352–362
    if ro < 2:
        l2 = times(l2, "0.00")
    elif ro in (2, 3, 4, 5):
        l2 = times(l2, {2: "0.75", 3: "1.00", 4: "1.25", 5: "1.50"}[ro])
    kt = up[KUTUU]  # :365–375
    l3 = 0 if kt == 0 else 100 if kt < 1000 else 200 if kt < 3000 else 500 if kt < 5000 else 1000
    if abl(ctx, c, "マゾっ気") == 3:  # :378–385（> 3 が先に当たるので 4／5 の分岐には来ない）
        l3 = times(l3, "0.50")
    return l1 + l2 + l3


def got_event_sex_mark_check(ctx: Ctx, mark_id: int, upvalue: int, prevent: int, days: int) -> None:
    """`@GOT_EVENT_SEX_MARK_CHECK`:401–435。

    - `VARSIZE("THRESHOLD_BASE")` は参照先配列の長さ 5（`reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs`:367–376 →
      `GameData/IdentifierDictionary.cs`:461–477 でプライベート変数を解決 → `GameData/Variable/VariableToken.cs`:432–439）。
    - `幽閉日数しきい値` は添字省略の 1 次元配列 = 要素 0（`GameData/Variable/VariableParser.cs`:160–168）で値 0。
    """
    from ..battle.core import run_chinobun
    from ..battle.palam import _mark_message

    st = ctx.state
    c = tc(ctx)
    base, factor, code = _MARK_TABLES[mark_id]
    m = c.mark[mark_id]
    if m < 0 or m >= len(base):  # :417–418
        return
    if upvalue >= base[m] + prevent * factor[m] and days >= _PRISON_DAYS_THRESHOLD[0]:  # :421
        c.mark[mark_id] += 1
        lv = c.mark[mark_id]
        run_chinobun(ctx, f"MESSAGE_SEX_MARK_{code}_{lv}", fallback=lambda: _mark_message(ctx, code, lv))
        if c.cflag[20] == 2:  # :427–428
            run_chinobun(ctx, f"MESSAGE_OTHER_SEX_MARK_{code}_{lv}")
        out = ctx.out
        out.print(f"{print_transcallname(st, st.target)}は")
        out.set_bold(True)
        out.print(f"{ctx.data.names['MARK'].get(mark_id, '')}{lv}")
        out.set_bold(False)
        out.printl("を取得した")
        out.printl()
