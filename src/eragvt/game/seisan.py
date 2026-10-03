"""特別活動（S28b）：`ゲーム内_行動実行処理/ACTION_SEISAN.ERB@SEISAN` と `ゲーム内_行動実行処理/特別活動/` 全部。

路徑相對 `source/earGVP/ERB/`（以下 `特別活動/` は `ゲーム内_行動実行処理/特別活動/` の略）。
- `ACTION_SEISAN.ERB@SEISAN`:3–192（変身選択・メニュー・スケジュール CFLAG:111・活動の派発・`_ABLUP, 1`・変身解除）。
- `特別活動/SEISAN.ERH`・`SEISAN_CALC.ERH`・`SEISAN_IDOL.ERH`（定数）、`SEISAN_INIT.ERB`（係数表：`EARN_TABLE`）、
  `CALC_SEISAN.ERB`（`calc_seisan`）、`CALC_CHARM_FEAT.ERB@CALC_CHARM_FEAT_IDOL`、`SEISAN_0_PART_TIME`〜`SEISAN_8_IDOL_LIVE`。
- 地の文 `地の文/特別活動関係/MESSAGE_SEISAN_*`（＋援助交際の変態プレイは `地の文/MESSAGE_CITIZEN_TRAIN.ERB`）は S07 catalog で実行
  （`run_chinobun`；状態変化行は `narration/hooks.py` の `SEISAN_HOOK_LINES`）。

共用 RESULT（`docs/wiki/python/result.md`）：`CALC_SEISAN`:137（RESULT:0〜1）、`SEISAN_PART_TIME_SHINBUN`:168（0〜1）、単値 RETURN と
関数終端（RESULT:0）、公衆便所の `RESULT:0 = …`（:170／:191／:213）を `st.result` に書く。後続の読み（公衆便所 :197／:222–231、
雑魚触手退治 :140 など）はそれを読む。`RANDOM(n)` は `RAND:n`（`汎用関数/RANDOM.ERB`:11–25 の非デバッグ時）。
関数内 `#DIM`（DYNAMIC なし）は静的変数（`reference/emuera-1824/Emuera/GameProc/UserDefinedVariable.cs`:27、
`GameData/Variable/VariableData.cs@SetDefaultLocalValue`:514–520）：読む前に必ず代入されるもの以外は `st.temp.locals` に保持
（ライブ公演の CHARM_BASE 等）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state import GameState
from .action import Ctx, _wait_or_line, config_check_maniac, print_transcallname
from .chara_common import is_female, talent
from .era import div, limit, mod

InputGen = Generator[None, int, None]

# 特別活動/SEISAN.ERH:5–13
ARUBAITO, KENKYU, TAIJI, ENJO, AV, TOILET, IDOL, MAKURA, LIVE = range(9)
NAMES = ("アルバイト", "研究", "雑魚触手退治", "援助交際", "AV出演", "公衆便所", "アイドル活動", "枕営業", "ライブ公演")
# :42–45 特別活動結果
SEIKOU, SHIPPAI, ZECCHOU_SHIPPAI, DAISEIKOU = 0, 1, 2, 3
# :55–57 研究、:66–67 公衆便所、:75–79 アイドル活動、:90–94 枕営業
KENKYU_JOSHU, KENKYU_SAKUNYU, KENKYU_SHIKYU = 0, 1, 2
BENKI_NIKU, BENKI_MESUINU = 0, 1
IDOL_ROJO, IDOL_TV, IDOL_GRAVURE, IDOL_CD, IDOL_EIGYOU = 0, 1, 2, 3, 4
MAKURA_FELLA, MAKURA_SEX, MAKURA_V, MAKURA_A, MAKURA_RINKAN = 0, 1, 2, 3, 4

# 特別活動/SEISAN_CALC.ERH:142–147 乱数幅
_R_HP, _R_MP, _R_SEI, _R_EARN = 7, 4, 4, 4

# 特別活動/SEISAN_CALC.ERH:157–197 の係数（体力係数, 気力係数, 性耐性係数, 稼ぎ除数, 稼ぎレベル係数, 稼ぎ加算）を
# SEISAN_INIT.ERB:7–42 の EARN_ARRAY_SET どおりに並べたもの。
# 注意：SEISAN_INIT.ERB:8 はアルバイトの「失敗」に `特活報酬_アルバイト_成功` を入れている（`_失敗` は使われない：原作どおり）。
_A_SEIKOU = (20, 10, 0, 1000, 10, 200)
EARN_TABLE: dict[tuple[int, int], tuple[int, ...]] = {
    (ARUBAITO, SEIKOU): _A_SEIKOU,
    (ARUBAITO, SHIPPAI): _A_SEIKOU,
    (ARUBAITO, ZECCHOU_SHIPPAI): (50, 70, 60, 2000, 2, 50),
    (KENKYU, KENKYU_JOSHU): (10, 20, 0, 8000, 8, 150),
    (KENKYU, KENKYU_SAKUNYU): (50, 70, 60, 4000, 16, 450),
    (KENKYU, KENKYU_SHIKYU): (20, 70, 60, 4000, 24, 1350),
    (TAIJI, SEIKOU): (30, 30, 30, 800, 5, 100),
    (TAIJI, SHIPPAI): (80, 80, 80, 0, 0, 0),
    (ENJO, SEIKOU): (3, 5, 7, 33, 0, 250),
    (AV, SEIKOU): (4, 4, 7, 200, 0, 1200),
    (TOILET, BENKI_NIKU): (7, 7, 7, 100, 0, 1),
    (TOILET, BENKI_MESUINU): (7, 7, 7, 100, 0, 1),
    (IDOL, IDOL_ROJO): (20, 10, 0, 5000, 1, 10),
    (IDOL, IDOL_TV): (40, 20, 0, 200, 0, 500),
    (IDOL, IDOL_GRAVURE): (35, 35, 0, 400, 0, 750),
    (IDOL, IDOL_CD): (35, 35, 0, 400, 0, 750),
    (IDOL, IDOL_EIGYOU): (50, 10, 0, 0, 0, 0),
    (MAKURA, MAKURA_FELLA): (20, 10, 0, 0, 0, 0),
    (MAKURA, MAKURA_SEX): (40, 10, 0, 0, 0, 0),
    (MAKURA, MAKURA_V): (50, 50, 0, 0, 0, 0),
    (MAKURA, MAKURA_A): (50, 50, 0, 0, 0, 0),
    (MAKURA, MAKURA_RINKAN): (70, 70, 0, 0, 0, 0),
    (LIVE, SEIKOU): (80, 30, 0, 1200, 10, 700),
    (LIVE, SHIPPAI): (80, 50, 30, 2400, 10, 100),
    (LIVE, ZECCHOU_SHIPPAI): (80, 80, 60, 3600, 10, 50),
    (LIVE, DAISEIKOU): (40, 15, 0, 1200, 20, 1400),
}
# 特活報酬は 9×5×6 の配列（SEISAN.ERH:106–111 活動結果最大値 = 5）。上表に無い組み合わせは 0 のまま：本作では到達しない。

# 特別活動/SEISAN_IDOL.ERH:6–15（__INT_MAX__ = Int64.MaxValue：reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs:1669–1679）
IDOL_LV_JOUKEN = (30, 100, 150, 200, 250, 300, 400, 500, 2**63 - 1)
_TV_KEISU = (30, 30, 30, 60, 60, 60, 90, 90, 90)
_GRAVURE_KEISU = (200, 200, 200, 1000, 1000, 1000, 2000, 2000, 2000)
_CD_KEISU = (200, 200, 200, 1000, 1000, 1000, 2000, 2000, 2000)
_LIVE_KEISU = (4, 4, 4, 11, 22, 22, 38, 54, 72)
DEBUT_MUMEI, DEBUT_YUUMEI, DEBUT_ROJO, DEBUT_URIKOMI = 0, 1, 2, 3

# 地の文/特別活動関係/MESSAGE_SEISAN.ERH:5–14
EJAC_CONDOM, EJAC_YABURE, EJAC_MUKYOKA, EJAC_KAFUKUBU, EJAC_KOUNAI, EJAC_WAREME, EJAC_SHIPPAI, EJAC_OKURE, EJAC_MUSHI, EJAC_DOUI = range(10)

# DIM.ERH:254／:257
DAREtomo = -1  # 誰とも知れない相手
NOZOMANAI = -4  # 望まない相手

# 静的変数（関数内 #DIM）
_KEY_LIVE = "SEISAN_IDOL_LIVE"  # (名前, 0)：CHARM_BASE／FEAT_RAND／CHARM_RAND（:12–14）


# --- 小道具 -----------------------------------------------------------------------------


def _rand(ctx: Ctx, n: int) -> int:
    return ctx.state.rng.rand(n)


def _t(ctx: Ctx, name: str) -> int:
    return talent(ctx.data, ctx.state.target_chara, name)


def _set_t(ctx: Ctx, name: str, value: int) -> None:
    ctx.state.target_chara.talent[ctx.data.index_of("TALENT", name)] = value


def _abl(ctx: Ctx, name: str) -> int:
    return ctx.state.target_chara.abl[ctx.data.index_of("ABL", name)]


def _exp(ctx: Ctx, name: str) -> int:
    return ctx.state.target_chara.exp[ctx.data.index_of("EXP", name)]


def _exp_add(ctx: Ctx, name: str, value: int) -> None:
    ctx.state.target_chara.exp[ctx.data.index_of("EXP", name)] += value


def _juel_add(ctx: Ctx, name: str, value: int) -> None:
    """`JUEL:名 += 値`（JUEL の名前は Palam.csv）。"""
    ctx.state.target_chara.juel[ctx.data.index_of("PALAM", name)] += value


def _base_idx(ctx: Ctx, name: str) -> int:
    return ctx.data.index_of("BASE", name)


def _name(ctx: Ctx) -> str:
    return print_transcallname(ctx.state, ctx.state.target)


def _female(ctx: Ctx) -> bool:
    return is_female(ctx.data, ctx.state.target_chara)


def _hole(ctx: Ctx) -> bool:
    from .battle.core import is_hole

    return is_hole(ctx)


def _girly(ctx: Ctx) -> bool:
    from .battle.core import is_girly

    return is_girly(ctx)


def _penis(ctx: Ctx) -> bool:
    from .battle.core import is_penis

    return is_penis(ctx)


def _holyvirgin(ctx: Ctx) -> int:
    from .battle.sexcom import check_holyvirgin

    return check_holyvirgin(ctx)


def _msg(ctx: Ctx, func: str, *args, fallback=None) -> bool:
    """`CALL 地の文`：catalog で実行（できなければ佔位＋fallback）。関数終端なので RESULT:0 = 0
    （`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs`:61–67；catalog 実行時は catalog が書く）。"""
    from .battle.core import run_chinobun

    ok = run_chinobun(ctx, func, tuple(args), fallback)
    if not ok:
        ctx.state.result[0] = 0
    return ok


def _dot_after(ctx: Ctx, arg: int) -> None:
    """`CALL DOT_AFTER, ARG`（`汎用関数/PRINT_LINE.ERB`:34–53、関数終端 → RESULT:0 = 0）。"""
    from .akuoti import dot_after

    dot_after(ctx, arg)
    ctx.state.result[0] = 0


def _after_pill(ctx: Ctx, arg1: int, arg2: int) -> InputGen:
    """`CALL AFTER_PILL, TARGET, ARG:1, ARG:2`（`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB`:898–957）。
    どの経路も `RETURN 0` か関数終端（INPUT の値は :957 の終端で 0 に戻る）→ RESULT:0 = 0。"""
    from .battle.ninsin import after_pill

    yield from after_pill(ctx, ctx.state.target, arg1, arg2)
    ctx.state.result[0] = 0


def _ninsin(ctx: Ctx, arg0: int, arg1: int, arg2: int) -> int:
    """`CALL NINSIN_HANTEI, …`（`PREGNANT_SOURCE_NINSIN.ERB`:11–165：受精 RETURN 1、他は 0）→ RESULT:0。"""
    from .battle.ninsin import ninsin_hantei

    r = ninsin_hantei(ctx, arg0, arg1, arg2)
    ctx.state.result[0] = r
    return r


def _ret(ctx: Ctx, *values: int) -> int:
    """`RETURN a[, b]`：RESULT:0〜 に書く（`Instraction.Child.cs@RETURN_Instruction`:2006–2023）。"""
    for i, v in enumerate(values):
        ctx.state.result[i] = v
    return values[0]


def _weekend(st: GameState) -> bool:
    d = mod(st.day[0], 7)
    return d == 0 or d == 6


# --- @SEISAN（ACTION_SEISAN.ERB:3–192） ----------------------------------------------------


def seisan(ctx: Ctx) -> InputGen:
    """`ACTION_SEISAN.ERB@SEISAN`:3–192（TARGET が対象）。:192 の BEGIN TURNEND は ACTION_MAIN:110–111 と同じ。"""
    from .battle.ablup import ablup
    from .battle.func import transform
    from .gather import action_transformation_select
    from .schedule import res_schedule

    st, out = ctx.state, ctx.out
    c = st.target_chara
    # :6 SEISAN_INIT は係数表（EARN_TABLE）、:9 LOCAL:141 = 0 は未使用
    yield from action_transformation_select(ctx, st.target, "特別活動")  # :12
    birth = _exp(ctx, "出産経験") > 0 or _t(ctx, "妊娠") in (1, 3)
    out.print("[0]アルバイト　　　　")  # :14
    out.print("[1]研究所で検査協力　" if birth else "[1]研究所助手　　　　")  # :15–19
    out.print("[2]雑魚触手退治　　　")  # :20
    out.printl()
    hole = _hole(ctx)
    yoku, roshutsu, mazo = _abl(ctx, "欲望"), _abl(ctx, "露出癖"), _abl(ctx, "マゾっ気")
    if yoku > 0 and hole:  # :23–24
        out.print("[3]援助交際　　　　　")
    if (yoku + roshutsu >= 5 or c.cflag[283] >= 10) and hole:  # :26–27
        out.print("[4]AV出演　　　　　　")
    if yoku + mazo >= 5 and hole:  # :29–30
        out.print("[5]公衆便所　　　　　")
    out.printl()
    charm = _exp(ctx, "魅了経験")
    if charm > 99 and _weekend(st):  # :33–39
        from .raid import HOTPINK

        out.set_color(HOTPINK)
        out.print("[8]★ライブ公演　　　")
        out.reset_color()
    else:
        out.print("[6]アイドル活動　　　")
    if charm > 99 and hole:  # :41–42
        out.print("[7]枕営業　　　　　　")
    out.printl()
    out.drawline()
    goto_input = False
    if c.cflag[111] > 0:  # :49–129
        result = res_schedule(c, 111)

        def fail() -> None:
            out.print("（実行不能）")
            out.printl()
            out.printl("手動で行動を選択してください")

        if result == 0:
            out.printl()
            out.print("スケジュール：アルバイト")
            out.printl()
        if result == 1:
            out.printl("　")
            out.print("スケジュール：研究所で検査協力　" if birth else "スケジュール：研究所助手　　　　")
            out.printl()
        if result == 2:
            out.printl()
            out.print("スケジュール：雑魚触手退治")
            out.printl()
        if result == 3:
            out.printl()
            out.print("スケジュール：援助交際")
            if yoku == 0 or not hole:
                fail()
                goto_input = True
        if not goto_input and result == 4:
            out.printl()
            out.print("スケジュール：AV出演")
            if (yoku + roshutsu < 5 and c.cflag[283] < 10) or not hole:
                fail()
                goto_input = True
        if not goto_input and result == 5:
            out.printl()
            out.print("スケジュール：公衆便所")
            if yoku + mazo < 5 or not hole:
                fail()
                goto_input = True
        if not goto_input and result == 6:
            if charm >= 100 and _weekend(st):
                result = 8
            else:
                out.printl()
                out.print("スケジュール：アイドル活動")
                out.printl()
        if not goto_input and result == 7:
            out.printl()
            out.print("スケジュール：枕営業")
            if charm < 100 or not hole:
                fail()
                goto_input = True
        if not goto_input and result == 8:
            out.printl()
            out.print("スケジュール：アイドル活動《★ライブ公演》")
            if charm < 100 or not _weekend(st):
                fail()
                goto_input = True
        if goto_input:
            result = yield  # GOTO INPUT_LOOP（ELSE 内の $INPUT_LOOP → INPUT）
    else:
        result = yield  # :131–132
    while True:  # :135–153
        out.printl()
        if result == 6 and charm >= 100 and _weekend(st):  # :138–140
            result = 8
        bad = (
            result < 0 or result > 8
            or (yoku < 1 and result == 3)
            or (yoku + roshutsu < 5 and c.cflag[283] < 10 and result == 4)
            or (yoku + mazo < 5 and result == 5)
            or (charm < 100 and result == 7)
            or ((charm < 100 or not _weekend(st)) and result == 8)
        )
        if (not hole and result in (3, 4, 5, 7)) or bad:  # :144–150
            out.printl("正しい値を入力してください")
            result = yield  # GOTO INPUT_LOOP
            continue
        c.cflag[101] = result  # :152
        break
    out.drawline()  # :156
    act = c.cflag[101]
    if act == ARUBAITO:  # :157–185
        part_time(ctx)
    elif act == KENKYU:
        research(ctx)
    elif act == TAIJI:
        yield from pest_control(ctx)
    elif act == ENJO:
        yield from prostitution(ctx)
    elif act == AV:
        yield from porn_video(ctx)
    elif act == TOILET:
        yield from toilet(ctx)
    elif act == IDOL:
        idol_activity(ctx)
    elif act == MAKURA:
        yield from idol_prostitution(ctx)
    elif act == LIVE:
        idol_live(ctx)
    out.printw()  # :187
    ablup(ctx, 1)  # :189
    if c.cflag[1] > 0:  # :190–191
        transform(ctx, 0)


# --- CALC_SEISAN.ERB ---------------------------------------------------------------------


def idol_lv(ctx: Ctx, who: int) -> int:
    """`特別活動/SEISAN_6_IDOL_ACTIVITY.ERB@IDOL_LV(TGTNUM)`:196–204。"""
    e = ctx.state.charas[who].exp[ctx.data.index_of("EXP", "魅了経験")]
    for level, v in enumerate(IDOL_LV_JOUKEN):
        if e < v:
            return level
    return len(IDOL_LV_JOUKEN)


def is_profitable(category: int, act_result: int) -> bool:
    """`CALC_SEISAN.ERB@IS_PROFITABLE`:148–171。"""
    if category == TAIJI and act_result == SHIPPAI:
        return False
    if category == TOILET and act_result == BENKI_MESUINU:
        return False
    if category == IDOL and act_result == IDOL_EIGYOU:
        return False
    if category == MAKURA:
        return False
    return True


def is_normal_earn(category: int, act_result: int) -> bool:
    """`CALC_SEISAN.ERB@IS_NORMAL_EARN`:179–189。"""
    return category != TOILET


def calc_seisan(ctx: Ctx, category: int, act_result: int) -> tuple[int, int]:
    """`特別活動/CALC_SEISAN.ERB@CALC_SEISAN, CATEGORY, ACT_RESULT`:15–137。戻り値（RESULT:0, RESULT:1）=（客数, 稼ぎ）。"""
    from .shop import syouhi_keigen

    st, data = ctx.state, ctx.data
    c = st.target_chara
    lb = st.temp.losebase
    lb.clear()  # :23 VARSET LOSEBASE
    coef = EARN_TABLE.get((category, act_result), (0, 0, 0, 0, 0, 0))  # :27
    multi = 125 if _t(ctx, "ラッキーチャーム") > 0 else 100  # :30–33
    sei = _base_idx(ctx, "性耐性")
    lb[0] = syouhi_keigen(data, st, st.target, div(c.maxbase[0] * (coef[0] + _rand(ctx, _R_HP)), 100), 0)  # :36
    lb[1] = syouhi_keigen(data, st, st.target, div(c.maxbase[1] * (coef[1] + _rand(ctx, _R_MP)), 100), 1)  # :37
    if coef[2] > 0:  # :38–39
        lb[sei] = div(c.maxbase[sei] * (coef[2] + _rand(ctx, _R_SEI)), 100)
    lb[0] = limit(lb[0], 0, c.base[0])  # :40–42
    lb[1] = limit(lb[1], 0, c.base[1])
    lb[sei] = limit(lb[sei], 0, c.base[sei])
    customer = lb[0]  # :45
    earn = 0
    charm = _exp(ctx, "魅了経験")
    if category == TAIJI and act_result == SHIPPAI:  # :56–66
        customer = div(customer * (50 + _rand(ctx, 3)), 100)
        _sexual_exp(ctx, customer, True)
    elif category == ENJO:  # :69–72
        customer = div(customer * (7 + _rand(ctx, 3)), 100)
        _sexual_exp(ctx, customer, False)
    elif category == AV:  # :74–78
        customer = div(customer * (5 + _rand(ctx, 3)), 100)
        customer += _rand(ctx, charm * 5 + 1)
        customer += max(charm - 100, 0) * 50
        _sexual_exp(ctx, customer, False)
    elif category == TOILET:  # :80–85
        customer = div(customer * (6 + _rand(ctx, 3)), 100)
        _sexual_exp(ctx, customer, False)
        earn = 1 + div(multi * _rand(ctx, 50), 100)
    elif category == IDOL:  # :88–108
        if act_result == IDOL_ROJO:
            customer = div(customer, 200)
        elif act_result == IDOL_TV:
            customer += charm * _TV_KEISU[idol_lv(ctx, st.target)]
            customer = div(customer, 10)
        elif act_result == IDOL_GRAVURE:
            customer += charm * _GRAVURE_KEISU[idol_lv(ctx, st.target)]
            customer = div(customer, 100)
        elif act_result == IDOL_CD:
            customer += charm * _CD_KEISU[idol_lv(ctx, st.target)]
            customer = div(customer, 100)
    elif category == LIVE:  # :113–123
        customer += charm * _LIVE_KEISU[idol_lv(ctx, st.target)]
        if act_result in (SHIPPAI, ZECCHOU_SHIPPAI) and charm < 200:
            customer = div(customer, 4)
    if is_profitable(category, act_result) and is_normal_earn(category, act_result):  # :127–128
        lv = c.abl[data.index_of("ABL", "レベル")]
        earn = div(multi * customer, coef[3]) + lv * coef[4] + _rand(ctx, _R_EARN) + coef[5]
    c.base[0] -= lb[0]  # :131–134
    c.base[1] -= lb[1]
    c.base[sei] -= lb[sei]
    st.money += earn
    lb.clear()  # :136
    _ret(ctx, customer, earn)  # :137
    return customer, earn


def _sexual_exp(ctx: Ctx, customer: int, is_defeat: bool) -> None:
    """`CALC_SEISAN.ERB@CALC_SEISAN_SEXUAL_EXP, CUSTOMER_NUM, IS_DEFEAT`:198–226。"""
    m = 10 if is_defeat else 1
    r = lambda n: _rand(ctx, n)  # noqa: E731
    _exp_add(ctx, "被姦経験", div(customer * (2 * m + r(3)), 100))
    if _female(ctx):
        _exp_add(ctx, "Ｖ経験", div(customer * (1 * m + r(3)), 100))
    _exp_add(ctx, "Ａ経験", div(customer * (1 * m + r(3)), 100))
    _exp_add(ctx, "絶頂経験", div(customer * (1 * m + r(2)), 100))
    _exp_add(ctx, "精液経験", div(customer * (1 * m + r(2)), 100))
    _exp_add(ctx, "フェラ経験", div(customer * (1 * m + r(2)), 100))
    if not is_defeat:
        _exp_add(ctx, "露出快楽経験", div(customer * (2 * m + r(3)), 100))
        _exp_add(ctx, "奉仕快楽経験", div(customer * (2 * m + r(3)), 100))
        _exp_add(ctx, "苦痛快楽経験", div(customer * (2 * m + r(3)), 100))
    _exp_add(ctx, "自慰経験", div(customer * (2 * m + r(3)), 100))
    if _penis(ctx):
        _exp_add(ctx, "射精経験", div(customer * (1 * m + r(3) * 1), 100))
    if _t(ctx, "母乳体質") > 0:
        _exp_add(ctx, "噴乳経験", div(customer * (1 * m + r(3)), 100))
    if _t(ctx, "お漏らし癖") > 0:
        _exp_add(ctx, "放尿経験", div(customer * (1 * m + r(3)), 100))


def calc_charm_feat_idol(ctx: Ctx, who: int, arg: int) -> int:
    """`特別活動/CALC_CHARM_FEAT.ERB@CALC_CHARM_FEAT_IDOL(対象, ARG)`:2–19。"""
    c = ctx.state.charas[who]
    t = lambda n: talent(ctx.data, c, n)  # noqa: E731
    if _rand(ctx, 4) == 0:
        return 0
    local = 0
    if arg > 1:
        if t("平凡"):
            local -= _rand(ctx, arg) + 1
        if t("人外の美貌"):
            local += _rand(ctx, arg) + 1
    else:
        if t("平凡"):
            local -= 1
        if t("人外の美貌"):
            local += 1
    return local


def idol_charmup(ctx: Ctx, charm_base: int, feat_rand: int, charm_rand: int, minimum: int = 0) -> int:
    """`SEISAN_6_IDOL_ACTIVITY.ERB@SEISAN_IDOL_CHARMUP`:216–228（RETURN CHARM_UP → RESULT:0）。"""
    up = charm_base + calc_charm_feat_idol(ctx, ctx.state.target, feat_rand)
    up = max(up + _rand(ctx, charm_rand), minimum)
    if up > 0:
        _exp_add(ctx, "魅了経験", up)
        ctx.out.printl(f"魅了経験が{up}上がった")
    return _ret(ctx, up)


# --- SEISAN_0_PART_TIME.ERB ---------------------------------------------------------------

_NINZU_DIV = (100, 250, 100, 50)  # :22
_NINZU_RDIV = (500, 250, 500, 150)  # :23
_NINZU_RADD = (6, 6, 8, 4)  # :24


def part_time(ctx: Ctx) -> None:
    """`特別活動/SEISAN_0_PART_TIME.ERB@SEISAN_PART_TIME`:14–113。"""
    from .gather import calc_charm_feat_other

    st, out = ctx.state, ctx.out
    ninzu_add = [10, 0, 1, 2]  # :25（DYNAMIC：毎回初期化）
    charm = popularity = 0
    event = _rand(ctx, 2) if not _hole(ctx) else _rand(ctx, 4)  # :29–33
    if event == 0:  # :38–43
        event_result, popularity = _shinbun(ctx)
        s = "軒に新聞配達し"
    elif event == 1:  # :46–72
        event_result = _hero(ctx)
        s = "人のちびっこに"
        if event_result == SEIKOU:
            s += "夢と希望を与え"
        elif event_result == SHIPPAI:
            s += "夢と性の芽生えを与え" if _hole(ctx) else "現実の厳しさを教え"
        elif event_result == ZECCHOU_SHIPPAI:
            s += "歪んだ性癖を植え付け"
        ninzu_add[1] = _abl(ctx, "レベル")
        charm = calc_charm_feat_other(ctx, st.target)
        if _rand(ctx, 100) < 10:
            popularity += 1
        if _rand(ctx, 100) < div(_exp(ctx, "魅了経験"), 10):
            popularity += 1
    elif event == 2:  # :75–84
        event_result = _family(ctx)
        s = "席の注文を取り"
        if _rand(ctx, 100) < 10:
            popularity += 1
        if _rand(ctx, 100) < div(_exp(ctx, "魅了経験"), 10):
            popularity += 1
    else:  # :87–90
        event_result = _syokudou(ctx)
        s = "品の料理を手伝い"
    r0, payment = calc_seisan(ctx, ARUBAITO, event_result)  # :95
    processed = div(r0, _NINZU_DIV[event]) + _rand(ctx, div(r0, _NINZU_RDIV[event]) + _NINZU_RADD[event]) + ninzu_add[event]
    _wait_or_line(ctx)  # :101 REDUCIBLE_PRINTW（RETURN RESULT：RESULT は変わらない）
    out.printl(f"{_name(ctx)}は{processed}{s}、{payment}＄の報酬を得ました。")
    if charm > 0:  # :105–108
        _exp_add(ctx, "魅了経験", charm)
        out.printl(f"魅了経験が{charm}上がった")
    if popularity > 0:  # :110–113
        st.flag[853] += popularity
        out.printl(f"人気度が{popularity}上がった")


def _shinbun(ctx: Ctx) -> tuple[int, int]:
    """`@SEISAN_PART_TIME_SHINBUN`:123–168（RETURN 成功, POPULARITY）。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    popularity = 0
    out.printl("アルバイト（新聞配達）")
    out.printl()
    _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SHINBUN_INTRO")
    if (_rand(ctx, 4) == 0 and st.flag[44] <= 30 and _hole(ctx)
            and (_t(ctx, "処女") < 1 or _rand(ctx, 2) == 0)):  # :133
        if _rand(ctx, 5) == 0:  # :135–136 触手拘束具化
            c.cflag[42] = 400
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SHINBUN_ACMECYCLE")
        _juel_add(ctx, "習得", 75)
        _juel_add(ctx, "恥情", 100)
    elif _rand(ctx, 3) == 0 and c.cflag[254] and _hole(ctx):  # :144
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SHINBUN_TOPNEWS")
        _juel_add(ctx, "恥情", 50)
    elif _rand(ctx, 2) == 0:  # :150
        if _rand(ctx, 2) == 0 and st.flag[44] <= 10:
            _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SHINBUN_ENCOUNT")
            popularity = 1
        else:
            _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SHINBUN_DEBAGAME")
    else:
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SHINBUN_NORMAL")
    _ret(ctx, SEIKOU, popularity)  # :168
    return SEIKOU, popularity


def _hero(ctx: Ctx) -> int:
    """`@SEISAN_PART_TIME_HERO`:173–241。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    out.printl("アルバイト（ヒーローショー）")
    out.printl()
    _msg(ctx, "MESSAGE_SEISAN_PART_TIME_HERO_INTRO")
    if c.cflag[42] == 400 and _rand(ctx, 2) == 0:  # :179–195
        if _exp(ctx, "魅了経験") >= 50 and _rand(ctx, 2) == 0 and _hole(ctx):
            _msg(ctx, "MESSAGE_SEISAN_PART_TIME_HERO_RYOJOKU")
            _juel_add(ctx, "習得", 125)
            _juel_add(ctx, "恥情", 100)
            _exp_add(ctx, "フェラ経験", 3)
        else:
            _msg(ctx, "MESSAGE_SEISAN_PART_TIME_HERO_SYOKUSYU")
        return _ret(ctx, ZECCHOU_SHIPPAI)
    if _rand(ctx, 3) == 0 and _t(ctx, "ラッキーチャーム") == 0:  # :198–204
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_HERO_KOROBI")
        _juel_add(ctx, "恥情", 25)
        return _ret(ctx, SHIPPAI)
    if _rand(ctx, 2) == 0 and _hole(ctx):  # :207–234
        if _exp(ctx, "魅了経験") >= 100:
            _msg(ctx, "MESSAGE_SEISAN_PART_TIME_HERO_CHIKAN")
            _juel_add(ctx, "習得", 50)
            _juel_add(ctx, "恥情", 50)
            _exp_add(ctx, "絶頂経験", 1)
            if _rand(ctx, 3) == 0 and _penis(ctx):
                _exp_add(ctx, "射精経験", 1)
                c.cflag[37] += 1  # :220（原作のメモ「なぜ膨乳値を上げている？」）
            return _ret(ctx, ZECCHOU_SHIPPAI)
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_HERO_SKIRTMEKURI")
        _juel_add(ctx, "習得", 25)
        _juel_add(ctx, "恥情", 25)
        return _ret(ctx, SHIPPAI)
    _msg(ctx, "MESSAGE_SEISAN_PART_TIME_HERO_NORMAL")  # :236–239
    return _ret(ctx, SEIKOU)


def _family(ctx: Ctx) -> int:
    """`@SEISAN_PART_TIME_FAMILY`:247–264。"""
    out = ctx.out
    out.printl("アルバイト（ウェイトレス）")
    out.printl()
    _msg(ctx, "MESSAGE_SEISAN_PART_TIME_FAMILY_INTRO")
    if _exp(ctx, "魅了経験") >= 40 and _hole(ctx):
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_FAMILY_CHIKAN")
        _juel_add(ctx, "恥情", 50)
    else:
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_FAMILY_NORMAL")
    return _ret(ctx, SEIKOU)


def _syokudou(ctx: Ctx) -> int:
    """`@SEISAN_PART_TIME_SYOKUDOU`:269–296。"""
    out = ctx.out
    out.printl("アルバイト（厨房手伝い）")
    out.printl()
    _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SYOKUDOU_INTRO")
    if _rand(ctx, 3) == 0:
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SYOKUDOU_CHIKAN")
        _juel_add(ctx, "習得", 25)
        _juel_add(ctx, "恥情", 100)
    elif _rand(ctx, 2) == 0 and (_abl(ctx, "Ｃ感覚") + _abl(ctx, "Ｖ感覚") + _abl(ctx, "Ａ感覚") + _abl(ctx, "Ｂ感覚")) <= 10:
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SYOKUDOU_DRUG")
        _juel_add(ctx, "習得", 75)
        _juel_add(ctx, "恥情", 250)
        _exp_add(ctx, "フェラ経験", 3)
        _exp_add(ctx, "精液経験", 3)
    else:
        _msg(ctx, "MESSAGE_SEISAN_PART_TIME_SYOKUDOU_NORMAL")
    return _ret(ctx, SEIKOU)


# --- SEISAN_1_RESEARCH.ERB ---------------------------------------------------------------


def research(ctx: Ctx) -> None:
    """`特別活動/SEISAN_1_RESEARCH.ERB@SEISAN_RESEARCH`:6–70。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    if (_exp(ctx, "出産経験") and _rand(ctx, 2) == 0) or _t(ctx, "妊娠") in (1, 3):  # :12–29 子宮
        out.printl("研究所で検査協力（子宮）")
        out.printl()
        shaved = 0
        if _t(ctx, "パイパン") == 0:
            _set_t(ctx, "パイパン", 1)
            shaved = 1
        _msg(ctx, "MESSAGE_SEISAN_RESEARCH_UTERUS", shaved)
        _, payment = calc_seisan(ctx, KENKYU, KENKYU_SHIKYU)
        out.printl(f"{_name(ctx)}は検査協力の報酬として{payment}＄を得ました")
        _juel_add(ctx, "習得", 25)
        _juel_add(ctx, "恥情", 50)
        _exp_add(ctx, "露出快楽経験", 1)
    elif _t(ctx, "母乳体質"):  # :32–46 搾乳
        out.printl("研究所で検査協力（搾乳）")
        out.printl()
        _msg(ctx, "MESSAGE_SEISAN_RESEARCH_MILKING")
        _, payment = calc_seisan(ctx, KENKYU, KENKYU_SAKUNYU)
        out.printl(f"{_name(ctx)}は検査協力の報酬として{payment}＄を得ました")
        _juel_add(ctx, "習得", 25)
        _juel_add(ctx, "恥情", 50)
        if _t(ctx, "ふたなり") > 0:
            _exp_add(ctx, "射精経験", 1 + _rand(ctx, 5))
        _exp_add(ctx, "噴乳経験", 1 + _rand(ctx, 5))
    else:  # :49–69 助手
        out.printl("研究所助手")
        out.printl()
        _msg(ctx, "MESSAGE_SEISAN_RESEARCH_ASSISTANT")
        _, earn = calc_seisan(ctx, KENKYU, KENKYU_JOSHU)
        chisei = _base_idx(ctx, "知性")
        payment = div(earn * c.maxbase[chisei], 100)  # :57 表示だけ（MONEY には CALC_SEISAN の稼ぎが入る：原作どおり）
        out.printl(f"{_name(ctx)}はアルバイトの報酬として{payment}＄を得ました")
        if _t(ctx, "変身能力") == -1 and _rand(ctx, 4) == 0:
            c.base[chisei] += 3
            out.printl("知性の基礎値が3上がった")
        elif _rand(ctx, 3) == 0:
            c.base[chisei] += 2
            out.printl("知性の基礎値が2上がった")
        elif _rand(ctx, 3) < 2:
            c.base[chisei] += 1
            out.printl("知性の基礎値が1上がった")


# --- SEISAN_2_PEST_CONTROL.ERB -------------------------------------------------------------


def pest_control(ctx: Ctx) -> InputGen:
    """`特別活動/SEISAN_2_PEST_CONTROL.ERB@SEISAN_PEST_CONTROL`:7–82。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    out.printl("雑魚触手退治")
    out.printl()
    _msg(ctx, "MESSAGE_SEISAN_PEST_CONTROL_INTRO")
    if _holyvirgin(ctx) == 0 and (_t(ctx, "触手の虜") > 0 or (c.cflag[42] == 400 and _rand(ctx, 4) == 0)):  # :17
        lost_virgin = 0
        if _t(ctx, "処女") > 0:
            _set_t(ctx, "処女", -1)
            c.cflag[206] = 2
            lost_virgin = 1
        tentacle, _ = calc_seisan(ctx, TAIJI, SHIPPAI)
        name = _name(ctx)
        if _t(ctx, "触手の虜") > 0:  # :30–35
            _msg(ctx, "MESSAGE_SEISAN_PEST_CONTROL_TORIKO", lost_virgin)
            out.printl(f"仲間が助けに来るまでの間、{name}は{tentacle}匹の触手に陵辱されてしまった。")
            _juel_add(ctx, "欲情", 200)
        else:  # :38–44
            _msg(ctx, "MESSAGE_SEISAN_PEST_CONTROL_DEFEAT", lost_virgin)
            out.printl(f"帰りが遅いのを不審に思った仲間が助けに来るまでの間、{name}は{tentacle}匹の触手に陵辱されてしまった。")
            _juel_add(ctx, "苦痛", 200)
        _exp_add(ctx, "戦闘経験", div(tentacle * (10 + _rand(ctx, 3)), 100))  # :47
        _juel_add(ctx, "習得", 50)
        v_kekkai, a_kekkai = _base_idx(ctx, "Ｖ結界耐久力"), _base_idx(ctx, "Ａ結界耐久力")
        if _female(ctx) and c.base[v_kekkai] == 0:  # :49–55
            _exp_add(ctx, "Ｖ経験", div(tentacle, 2) + 2)
            _juel_add(ctx, "快Ｖ", div(tentacle * _abl(ctx, "Ｖ感覚"), 2) + 2)
        elif c.base[a_kekkai] == 0:
            _exp_add(ctx, "Ａ経験", div(tentacle, 4) + 1)
            _juel_add(ctx, "快Ａ", div(tentacle * _abl(ctx, "Ａ感覚"), 4) + 1)
        if c.base[a_kekkai] == 0:  # :56–59
            _exp_add(ctx, "Ａ経験", div(tentacle, 4) + 1)
            _juel_add(ctx, "快Ａ", div(tentacle * _abl(ctx, "Ａ感覚"), 4) + 1)
        _exp_add(ctx, "フェラ経験", div(tentacle, 2) + 2)
        _exp_add(ctx, "精液経験", div(tentacle, 2) + 2)
        if _penis(ctx):  # :62–65
            _exp_add(ctx, "射精経験", div(tentacle, 2) + 2)
            c.cflag[37] += div(tentacle, 2) + 2
        if _female(ctx) and c.base[v_kekkai] == 0:  # :68–71
            yield from _after_pill(ctx, 5, 200)
            _ninsin(ctx, div(st.result[0], 10) + 2, 50, 200)  # :70 RESULT:0 は AFTER_PILL の 0（原作どおり）
    else:  # :74–82
        _msg(ctx, "MESSAGE_SEISAN_PEST_CONTROL_NORMAL")
        calc_seisan(ctx, TAIJI, SEIKOU)
        out.printl(f"{_name(ctx)}は{st.result[0]}匹の触手を駆除し、{st.result[1]}＄の報酬を得ました。")
        _exp_add(ctx, "戦闘経験", div(st.result[0] * (1 + _rand(ctx, 5) * 1), 100))


# --- SEISAN_3_PROSTITUTION.ERB -------------------------------------------------------------


def prostitution(ctx: Ctx) -> InputGen:
    """`特別活動/SEISAN_3_PROSTITUTION.ERB@SEISAN_PROSTITUTION`:5–126。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    out.printl("援助交際")
    out.printl()
    _msg(ctx, "MESSAGE_SEISAN_PROSTITUTION_INTRO")
    if _rand(ctx, 5) != 0 and _girly(ctx):  # :14–18 通常の援交
        payment = yield from _prostitution_normal(ctx)
        out.printl(f"{_name(ctx)}は街で声をかけてきた男に{payment}＄のお小遣いをもらった")
    elif _rand(ctx, 3) == 0:  # :21–40 調教
        if _rand(ctx, 2) == 0 and _hole(ctx):
            _msg(ctx, "MESSAGE_SEISAN_PROSTITUTION_TRAIN_BLOWJOB")
            _juel_add(ctx, "習得", 100)
            _exp_add(ctx, "フェラ経験", 3)
            _exp_add(ctx, "精液経験", 3)
        else:
            _msg(ctx, "MESSAGE_SEISAN_PROSTITUTION_TRAIN_KISS")
            _juel_add(ctx, "習得", 50)
        _, payment = calc_seisan(ctx, ENJO, SEIKOU)
        out.printl(f"{_name(ctx)}は街で声をかけてきた男に{payment}＄のお小遣いをもらった")
    elif _rand(ctx, 2) == 0:  # :43–90 変態プレイ
        out.printw("黴臭いビルの地下室で、")
        if _rand(ctx, 4) == 0:  # 浣腸
            _msg(ctx, "MESSAGE_CITIZEN_TRAIN_KANCHO", st.target, "男", "特別活動")
            _juel_add(ctx, "快Ａ", 15 * _abl(ctx, "Ａ感覚"))
            _juel_add(ctx, "習得", 150)
            _exp_add(ctx, "Ａ経験", 3)
            _exp_add(ctx, "フェラ経験", 1)
            _exp_add(ctx, "精液経験", 1)
        elif _rand(ctx, 3) == 0:  # 豚
            _msg(ctx, "MESSAGE_CITIZEN_TRAIN_PIG", st.target, "男", "特別活動")
            _juel_add(ctx, "習得", 150)
            _juel_add(ctx, "苦痛", 300)
            _exp_add(ctx, "苦痛快楽経験", 3)
            _exp_add(ctx, "フェラ経験", 1)
            _exp_add(ctx, "精液経験", 1)
        elif _rand(ctx, 2) == 0:  # 犬
            _msg(ctx, "MESSAGE_CITIZEN_TRAIN_DOG", st.target, "男", "特別活動", fallback=lambda: _dog_fallback(ctx))
            _juel_add(ctx, "習得", 150)
            _juel_add(ctx, "苦痛", 100)
            _juel_add(ctx, "欲情", 100)
            _juel_add(ctx, "恥情", 100)
            _exp_add(ctx, "苦痛快楽経験", 2)
            _exp_add(ctx, "フェラ経験", 1)
            _exp_add(ctx, "精液経験", 1)
        else:  # 女王様
            _msg(ctx, "MESSAGE_SEISAN_PROSTITUTION_QUEEN")
            _juel_add(ctx, "習得", 100)
            _juel_add(ctx, "欲情", 100)
            _exp_add(ctx, "フェラ経験", 1)
            _exp_add(ctx, "精液経験", 1)
        _wait_or_line(ctx)  # :87
        _, payment = calc_seisan(ctx, ENJO, SEIKOU)
        out.printl(f"{_name(ctx)}は街で声をかけてきた変態趣味の男に{payment}＄のお小遣いをもらった")
    else:  # :93–113 お姉様
        _msg(ctx, "MESSAGE_SEISAN_PROSTITUTION_LADY")
        _juel_add(ctx, "習得", 150)
        _juel_add(ctx, "欲情", 100)
        if not _female(ctx) and _t(ctx, "男の娘") <= 0:
            _exp_add(ctx, "射精経験", 2)
        _, payment = calc_seisan(ctx, ENJO, SEIKOU)
        out.printl(f"{_name(ctx)}は街で声をかけてきた欲求不満のおねえさまに{payment}＄のお小遣いをもらった")
    local2 = 0  # :116–124
    if _rand(ctx, 100) < 20:
        local2 += 1
    if _rand(ctx, 100) < div(_exp(ctx, "魅了経験"), 8):
        local2 += 1
    if local2 > 0:
        st.flag[853] += local2
        out.printl(f"人気度が{local2}上がった")
    if _rand(ctx, 100) < 25:  # :125–126
        c.cflag[825] += 1


def _dog_fallback(ctx: Ctx) -> None:
    """catalog が使えないときの `MESSAGE_CITIZEN_TRAIN_DOG` の状態変化（`地の文/MESSAGE_CITIZEN_TRAIN.ERB`:342–403）。
    `ARGS:1 == "特別活動"` なので :342 は `TALENT:嬲られ体質 > 0 && MARK:屈服刻印 >= 3 && ISFEMALE()`。"""
    c = ctx.state.target_chara
    if not (_t(ctx, "嬲られ体質") > 0 and c.mark[ctx.data.index_of("MARK", "屈服刻印")] >= 3 and _female(ctx)):
        return
    r = lambda a, b: a + _rand(ctx, b - a)  # noqa: E731  RAND(a, b)：Creator.Method.cs:953–973
    _exp_add(ctx, "精液経験", 2 + r(2, 5))
    _exp_add(ctx, "絶頂経験", 3 + r(2, 5))
    _exp_add(ctx, "異常経験", 1)
    _exp_add(ctx, "Ｖ拡張経験", 2 + r(2, 5))
    _exp_add(ctx, "Ｖ経験", 3 + r(3, 6))


def _prostitution_normal(ctx: Ctx) -> Generator[None, int, int]:
    """`@SEISAN_PROSTITUTION_NORMAL`:140–298（RETURN PAYMENT → RESULT:0）。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    use_vagina = 1 if _t(ctx, "男の娘") == 0 else 0  # :148–150
    if use_vagina and _t(ctx, "処女") > 0:  # :153–166
        namahame = 0
    elif not use_vagina and _abl(ctx, "Ａ感覚") < 2:
        namahame = 0
    else:
        _msg(ctx, "MESSAGE_SEISAN_PROSTITUTION_NAMAHAME_REQUEST")
        namahame = yield from _namahame_answer(ctx)
        _dot_after(ctx, 2)
    lost_virgin = 0
    if use_vagina and _t(ctx, "処女") > 0:  # :169–173
        c.cflag[206] = 8
        _set_t(ctx, "処女", _t(ctx, "処女") * -1)
        lost_virgin = 1
    _msg(ctx, "MESSAGE_SEISAN_PROSTITUTION_MAINPLAY", use_vagina, namahame, lost_virgin)  # :176
    if use_vagina:  # :179–187
        _juel_add(ctx, "快Ｖ", 15 * _abl(ctx, "Ｖ感覚"))
        _exp_add(ctx, "Ｖ経験", 3)
    else:
        _juel_add(ctx, "快Ａ", 15 * _abl(ctx, "Ａ感覚"))
        _exp_add(ctx, "Ａ経験", 3)
    _juel_add(ctx, "習得", 250)
    _exp_add(ctx, "精液経験", 3)
    _, payment = calc_seisan(ctx, ENJO, SEIKOU)  # :190–191
    out.printw()  # :192
    nakadashi = 0

    def ejac(kind: int, bonus: int) -> None:
        nonlocal payment
        _msg(ctx, "MESSAGE_SEISAN_PROSTITUTION_AFTER_EJAC", kind, use_vagina)
        payment += bonus
        st.money += bonus

    if namahame == 2:  # :196–203
        ejac(EJAC_DOUI, 500)
        nakadashi = 3
    elif namahame == 1:  # :205–258
        if _rand(ctx, 5) == 0:
            if _rand(ctx, 8) == 0:
                ejac(EJAC_MUSHI, 200)
                nakadashi = 3
            elif _rand(ctx, 2) == 0:
                ejac(EJAC_OKURE, 250)
                nakadashi = 1
            else:
                ejac(EJAC_SHIPPAI, 300)
                nakadashi = 3
        elif _rand(ctx, 3) == 0:
            ejac(EJAC_WAREME, 250)
        elif _rand(ctx, 2) == 0 and (use_vagina or config_check_maniac(st, 15) == 1):
            ejac(EJAC_KOUNAI, 250)
        else:
            ejac(EJAC_KAFUKUBU, 250)
    elif namahame < 1:  # :260–288
        if _rand(ctx, 10) == 0:
            nakadashi = 3
            if _rand(ctx, 4) == 0 and namahame == -1:
                ejac(EJAC_MUKYOKA, 150)
            else:
                ejac(EJAC_YABURE, 100)
        else:
            ejac(EJAC_CONDOM, namahame * 100)
    if use_vagina and nakadashi > 0:  # :291–296
        yield from _after_pill(ctx, 35, DAREtomo)
        _ninsin(ctx, nakadashi, 800, DAREtomo)
    _ret(ctx, payment)  # :298
    return payment


def _namahame_answer(ctx: Ctx) -> Generator[None, int, int]:
    """`@SEISAN_PROSTITUTION_NAMAHAME_ANSWER`:304–334（想定外の入力は何も出さずに INPUT し直す）。"""
    out = ctx.out
    juujun = _abl(ctx, "従順")
    out.printl()
    out.printl("[0]断固拒否する（報酬減少）")
    out.printl(f"[1]やんわりと断る（交渉失敗率{juujun * 15 + 15}％）")
    out.printl("[2]外で出すよう約束させる（報酬増加・小）")
    out.printl("[3]中出しＯＫする（報酬増加・大）")
    while True:
        r = yield
        if r == 0:
            out.printl("有無を言わさぬ雰囲気で男にコンドームを着けさせた…")
            return _ret(ctx, -1)
        if r == 1:
            if _rand(ctx, 100) < juujun * 15 + 15:
                out.printl("男を説得しようとしたが、雰囲気に流され押し切られてしまった…")
                return _ret(ctx, 1 + _rand(ctx, 2))
            out.printl("男はしぶしぶコンドームを着けることを受け入れた…")
            return _ret(ctx, 0)
        if r == 2:
            out.printl("中出しＮＧを条件に要求を受け入れた…")
            return _ret(ctx, 1)
        if r == 3:
            out.printl("中出ししても良いと伝えると、男の目が興奮の色に変わった…")
            return _ret(ctx, 2)


# --- SEISAN_4_PORN_VIDEO.ERB ---------------------------------------------------------------


def porn_video(ctx: Ctx) -> InputGen:
    """`特別活動/SEISAN_4_PORN_VIDEO.ERB@SEISAN_PORN_VIDEO`:7–139。"""
    from .battle.core import unlock_achievement
    from .battle.ninsin import check_pregnant

    st, out = ctx.state, ctx.out
    c = st.target_chara
    out.printl("AV出演")
    out.printl()
    _msg(ctx, "MESSAGE_SEISAN_PORN_VIDEO_INTRO")
    sales, payment = calc_seisan(ctx, AV, SEIKOU)  # :17–19
    name = _name(ctx)
    henshin = _t(ctx, "変身能力") == 1
    charm = _exp(ctx, "魅了経験")
    # :23 `ISFEMALE() && ((…) && EXP:戦闘経験 > 0 && RANDOM(5) < 1) || TALENT:完堕ち > 0`（&&／|| は短絡：
    # reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:524–555）
    maso = ((_abl(ctx, "マゾっ気") > 4 and _abl(ctx, "欲望") > 4) or _t(ctx, "マゾ気質") > 0
            or (_t(ctx, "乳首ピアス") + _t(ctx, "クリピアス") > 5))
    if (_female(ctx) and maso and _exp(ctx, "戦闘経験") > 0 and _rand(ctx, 5) < 1) or _t(ctx, "完堕ち") > 0:
        c.cflag[282] = 12
        if henshin:
            title = (f"『アイドル魔法少女{name}、大長編６時間ノンストップ雌畜調教大公開！』" if charm > 200
                     else f"『魔法少女天使{name}、大長編４時間ノンストップ雌畜調教大公開！』")
        else:
            title = (f"『美少女アイドル戦士{name}、大長編６時間ノンストップ雌畜調教大公開！』" if charm > 200
                     else f"『美少女天使{name}、大長編４時間ノンストップ雌畜調教大公開！』")
        payment = div(st.result[1] * (200 + _rand(ctx, 200)), 100)  # :38 RAND(200,400)：Creator.Method.cs:953–973
    elif _rand(ctx, 11) == 0 and _holyvirgin(ctx) == 0:  # :40–42
        c.cflag[282] = 11
        title = f"『おしおきされてイキまくるドジっ娘メイド {c.name}』"
    elif _rand(ctx, 10) == 0 and _t(ctx, "マゾ気質") < 1:  # :44–46（`\@ 変身能力 == 1 ?#すぷらったー☆\@`：真なら空）
        c.cflag[282] = 3
        title = f"『サディスティック魔法少女 {'' if henshin else 'すぷらったー☆'}{name}』"
    elif _rand(ctx, 9) == 0:  # :48–50
        c.cflag[282] = 1
        title = f"『コスプレ魔法少女　{'' if henshin else 'マジカル☆'}{name}』"
    elif (_girly(ctx) and _penis(ctx)) and _rand(ctx, 8) == 0:  # :52–54
        c.cflag[282] = 4
        title = f"『ふたなりな妹とえっちしてみませんか？ {c.name}』"
    elif check_pregnant(ctx, st.target) > 0 and _rand(ctx, 7) == 0:  # :56–58
        c.cflag[282] = 5
        title = "『私の子●はお父さんとの子 腹ボテ小○生 鬼畜父親中出し 近親相姦成長記録』"
    elif _rand(ctx, 6) == 0:
        c.cflag[282] = 6
        title = f"『ネコ耳{name}のニャンニャンしちゃうぞ』"
    elif _rand(ctx, 5) == 0:
        c.cflag[282] = 7
        title = f"『淫語 卑猥語 BEST SELECTION {c.name}』"
    elif _rand(ctx, 4) == 0:
        c.cflag[282] = 8
        title = f"『萌え萌えコスプレ7 {c.name}』"
    elif _rand(ctx, 3) == 0:
        c.cflag[282] = 9
        title = f"『かわゆ過ぎる{name}と僕のパコパコ同棲性活』"
    elif _rand(ctx, 2) == 0:
        c.cflag[282] = 10
        title = "『無理矢理犯されるアナル 4時間』"
    else:  # :80–82
        c.cflag[282] = 2
        title = f"『凌辱ヒロイン {'' if henshin else 'プリティー☆'}{name} セカンドシーズン』"
    _msg(ctx, "MESSAGE_SEISAN_PORN_VIDEO_CAPTION", c.cflag[282])  # :86
    out.printw(f"{title}は{sales}本売れ、{payment}＄の報酬を得ました。")
    if payment >= 2000:  # :90–92
        unlock_achievement(ctx, 257, "ＡＶ女優")
    out.printl()
    out.printl("どうやらサンプルディスクが郵送されてきたようだ。")
    if c.cflag[281] == 0:  # :96–108
        out.printl("……ちょっとだけ見てみようか？")
        out.printl("[0] はい")
        out.printl("[1] いいえ")
        out.printl("[9] はい　（次から確認しない）")
        out.printl("[10]いいえ（次から確認しない）")
        result = yield
    else:
        result = 9 if c.cflag[281] == 1 else 10
        if result == 9:
            out.printl("……ちょっとだけ見てみよう。")
    st.result[0] = result
    if result in (0, 9):  # :109–120
        c.cflag[281] = 1 if result == 9 else 0
        _msg(ctx, "MESSAGE_SEISAN_PORN_VIDEO_SAMPLE", c.cflag[282])
    elif result in (1, 10):
        c.cflag[281] = 2 if result == 10 else 0
        out.printl(f"{name}はパッケージを見て顔を真っ赤にしている。")
    else:
        out.printl("正しい値を入力してください")
    st.savestr[20 + st.target] = title  # :122
    if _rand(ctx, 100) < 75:  # :123–124
        c.cflag[285] += 1
    _juel_add(ctx, "習得", 150)  # :127–138
    if _female(ctx) and _holyvirgin(ctx) == 0:
        _exp_add(ctx, "Ｖ経験", 2)
        _juel_add(ctx, "快Ｖ", 10 * _abl(ctx, "Ｖ感覚"))
    else:
        _exp_add(ctx, "Ａ経験", 2)
        _juel_add(ctx, "快Ａ", 10 * _abl(ctx, "Ａ感覚"))
    _exp_add(ctx, "Ａ経験", 2)
    _juel_add(ctx, "快Ａ", 10 * _abl(ctx, "Ａ感覚"))
    _exp_add(ctx, "フェラ経験", 1)
    _exp_add(ctx, "精液経験", 5)


# --- SEISAN_5_TOILET.ERB ---------------------------------------------------------------------


def toilet(ctx: Ctx) -> InputGen:
    """`特別活動/SEISAN_5_TOILET.ERB@SEISAN_TOILET`:6–93。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    ijou = "異常経験"
    if _rand(ctx, 3) == 0 and _girly(ctx):  # :11–31 浮浪者
        out.printl("公衆便所（浮浪者）")
        out.printl()
        lost_virgin = 0
        if _t(ctx, "処女") > 0:
            c.cflag[206] = 9
            _set_t(ctx, "処女", -1)
            _exp_add(ctx, ijou, 1)
            lost_virgin = 1
        if _t(ctx, "男の娘") > 0 and _abl(ctx, "Ａ感覚") < 2:
            _exp_add(ctx, ijou, 1)
        _msg(ctx, "MESSAGE_SEISAN_TOILET_HOMELESS", lost_virgin)
        calc_seisan(ctx, TOILET, BENKI_NIKU)
        payment = st.result[1]
        st.result[0] = div(st.result[0], 10) + _rand(ctx, 5) + 1  # :30
        out.printl(f"肉便器{_name(ctx)}は{st.result[0]}人に使われたが、使用料は{payment}＄しか入っていなかった…")
    elif _rand(ctx, 2) == 0:  # :34–57 路地裏放置
        out.printl("公衆便所（路地裏放置）")
        out.printl()
        if _female(ctx) and _t(ctx, "処女") > 0:
            c.cflag[206] = 9
            _set_t(ctx, "処女", -1)
            _exp_add(ctx, ijou, 1)
        elif _t(ctx, "男の娘") > 0 and _abl(ctx, "Ａ感覚") < 2:
            _exp_add(ctx, ijou, 1)
        _msg(ctx, "MESSAGE_SEISAN_TOILET_BACK_ARRAY", 0)  # :47 LOST_VIRGIN は DYNAMIC の 0 のまま（この分岐では代入されない：原作どおり）
        calc_seisan(ctx, TOILET, BENKI_NIKU)
        payment = st.result[1]
        st.result[0] = div(st.result[0], 10) + _rand(ctx, 5) + 1  # :51
        out.printl(f"肉便器{_name(ctx)}は{st.result[0]}人に使われたが、使用料は{payment}＄しか入っていなかった…")
        yield from _after_pill(ctx, 10, DAREtomo)  # :54（RESULT:0 = 0）
        if _female(ctx):  # :56–57（RESULT:0 は AFTER_PILL の 0：原作どおり）
            _ninsin(ctx, div(st.result[0], 2) + 2, 100, DAREtomo)
    else:  # :59–74 野良犬
        out.printl("公衆便所（野良犬）")
        out.printl()
        if _t(ctx, "処女") > 0 and _female(ctx):
            c.cflag[206] = 10
            _set_t(ctx, "処女", -1)
            _exp_add(ctx, ijou, 1)
        _msg(ctx, "MESSAGE_SEISAN_TOILET_DOG", 0)
        calc_seisan(ctx, TOILET, BENKI_MESUINU)
        st.result[0] = div(st.result[0], 20) + _rand(ctx, 5) + 1  # :73
        out.printl(f"肉便器{_name(ctx)}は{st.result[0]}匹の野良犬に使われたが、当然使用料は１＄たりとも得られなかった…")
    c.cflag[285] += 1  # :76
    # :79–91 RESULT:0 は直前の値（路地裏放置では AFTER_PILL／NINSIN_HANTEI の戻り値：原作どおり）
    n = st.result[0]
    _juel_add(ctx, "習得", 200)
    _juel_add(ctx, "恥情", 100)
    if _female(ctx):
        _exp_add(ctx, "Ｖ経験", div(n, 2) + 2)
        _juel_add(ctx, "快Ｖ", div(n * _abl(ctx, "Ｖ感覚"), 2) + 2)
    else:
        _exp_add(ctx, "Ａ経験", div(n, 4) + 1)
        _juel_add(ctx, "快Ａ", div(n * _abl(ctx, "Ａ感覚"), 4) + 1)
    _exp_add(ctx, "Ａ経験", div(n, 4) + 1)
    _juel_add(ctx, "快Ａ", div(n * _abl(ctx, "Ａ感覚"), 4) + 1)
    _exp_add(ctx, "フェラ経験", div(n, 2) + 2)
    _exp_add(ctx, "精液経験", div(n, 2) + 2)
    if _rand(ctx, 100) < 25:  # :92–93
        c.cflag[825] += 1


# --- SEISAN_6_IDOL_ACTIVITY.ERB --------------------------------------------------------------

_KEY_BOOK_TITLE = (("MESSAGE_SEISAN_IDOL_GRAVURE_PHOTOSHOOT", "BOOK_TITLE"), (0,))
_BOOK_TITLES = ("『ピュエアリーＫＩＳＳ {}』", "『マジかるエン★ジェル {}』", "『純情ＨＥＡＲＴ {}』", "『{} ゆうわくビーチ』",
                "『ガールズ＆スタイルズ {}』")


def _gravure_title(ctx: Ctx) -> str:
    """`MESSAGE_SEISAN_IDOL_GRAVURE_PHOTOSHOOT, BOOK_TITLE`（`地の文/特別活動関係/MESSAGE_SEISAN_6_IDOL_ACTIVITY.ERB`:70–90）の
    `#DIMS REF BOOK_TITLE` の代入結果。catalog は REF を値渡しの関数内変数として扱う（`st.temp.narr` に残る）ので、実行後にそれを
    読む（呼び出し時に引数 "" で初期化され、:78–87 のどの分岐でも代入される）。catalog が使えなければ :78–87 を Python で選ぶ。"""
    st = ctx.state
    title = st.temp.narr.get(_KEY_BOOK_TITLE)
    return title if isinstance(title, str) else ""


def idol_activity(ctx: Ctx) -> None:
    """`特別活動/SEISAN_6_IDOL_ACTIVITY.ERB@SEISAN_IDOL_ACTIVITY`:11–184。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    lv = idol_lv(ctx, st.target)
    if lv == 0:  # :21–39 売り出し
        out.printl("アイドル活動（売り出し）")
        out.printl()
        _msg(ctx, "MESSAGE_SEISAN_IDOL_BUDDING")
        if st.day[0] < 14:
            idol_charmup(ctx, 30, 5, 5, IDOL_LV_JOUKEN[0])
            _msg(ctx, "MESSAGE_SEISAN_IDOL_DEBUT", DEBUT_MUMEI)
        else:
            idol_charmup(ctx, 25 + min(st.day[0], 28), 5, 5, IDOL_LV_JOUKEN[0] + 5)
            _msg(ctx, "MESSAGE_SEISAN_IDOL_DEBUT", DEBUT_YUUMEI)
        return
    if lv == 1:  # :42–78 下積み
        out.printl("アイドル活動（下積み）")
        out.printl()
        if _rand(ctx, 3) == 0:  # 路上ライブ
            _msg(ctx, "MESSAGE_SEISAN_IDOL_STREET_LIVE")
            audience, payment = calc_seisan(ctx, IDOL, IDOL_ROJO)
            if audience > 10:  # :56–61（+200 は表示だけ：MONEY は CALC_SEISAN の稼ぎのみ）
                payment += 200
                out.printl(f"{audience}人の聴衆から喝采を受け、{payment}＄の資金を稼いだ。")
            else:
                out.printl(f"{audience}人が投げ銭を行い、{payment}＄の資金を稼いだ。")
            idol_charmup(ctx, 2, 2, 4)
            _msg(ctx, "MESSAGE_SEISAN_IDOL_DEBUT", DEBUT_ROJO)
        else:  # 売り込み
            _msg(ctx, "MESSAGE_SEISAN_IDOL_SALES")
            idol_charmup(ctx, 4, 2, 2)
            _msg(ctx, "MESSAGE_SEISAN_IDOL_DEBUT", DEBUT_URIKOMI)
        return
    # :81–183 プロデビュー後
    if _rand(ctx, 3) == 0 and c.cflag[42] != 400 and _hole(ctx):  # :83–108 グラビア撮影
        out.printl("アイドル活動（グラビア撮影）")
        out.printl()
        if _rand(ctx, 3) == 0:
            _msg(ctx, "MESSAGE_SEISAN_IDOL_PORNO_PHOTOSHOOT")
        else:
            box: list[str] = []
            if _msg(ctx, "MESSAGE_SEISAN_IDOL_GRAVURE_PHOTOSHOOT", "", fallback=lambda: box.append(_gravure_fallback(ctx))):
                title = _gravure_title(ctx)
            else:
                title = box[0] if box else ""
            sales, payment = calc_seisan(ctx, IDOL, IDOL_GRAVURE)
            out.printl(f"写真集{title}は{sales}部売れ、ギャラとして{payment}＄の資金を稼いだ。")
            st.savestr[23 + st.target] = title  # :100
        if idol_lv(ctx, st.target) >= 5:
            idol_charmup(ctx, 8, 4, 6)
        else:
            idol_charmup(ctx, 4, 2, 4)
    elif _rand(ctx, 4) == 0:  # :110–122 テレビ出演
        out.printl("アイドル活動（テレビ出演）")
        out.printl()
        _msg(ctx, "MESSAGE_SEISAN_IDOL_TVSHOW")
        _, payment = calc_seisan(ctx, IDOL, IDOL_TV)
        out.printl(f"{_name(ctx)}はギャラとして{payment}＄の資金を稼いだ。")
        idol_charmup(ctx, 4, 2, 2)
    elif _rand(ctx, 3) == 0:  # :124–141 新曲の収録
        out.printl("アイドル活動（新曲の収録）")
        out.printl()
        _msg(ctx, "MESSAGE_SEISAN_IDOL_RECORDING")
        sales, payment = calc_seisan(ctx, IDOL, IDOL_CD)
        out.printl(f"ＣＤは{sales}枚売れ、ギャラとして{payment}＄の資金を稼いだ。")
        if idol_lv(ctx, st.target) >= 5:
            idol_charmup(ctx, 12, 6, 4)
        else:
            idol_charmup(ctx, 6, 3, 2)
    elif _rand(ctx, 2) == 0:  # :143–156 エロレッスン
        _msg(ctx, "MESSAGE_SEISAN_IDOL_EROTIC_LESSON")
        calc_seisan(ctx, IDOL, IDOL_EIGYOU)
        if _exp(ctx, "魅了経験") >= 250:
            idol_charmup(ctx, 10, 5, 4)
        else:
            idol_charmup(ctx, 8, 4, 4)
    else:  # :158–172 通常営業
        out.printl("アイドル活動（通常営業）")
        out.printl()
        _msg(ctx, "MESSAGE_SEISAN_IDOL_NORMAL_EVENT")
        calc_seisan(ctx, IDOL, IDOL_EIGYOU)
        if _exp(ctx, "魅了経験") >= 250:
            idol_charmup(ctx, 10, 5, 4)
        else:
            idol_charmup(ctx, 8, 4, 4)
    local2 = 0  # :175–183 人気度
    if _rand(ctx, 100) < 10:
        local2 += 1
    if _rand(ctx, 100) < 10:
        local2 += 1
    if local2 > 0:
        st.flag[853] += local2
        out.printl(f"人気度が{local2}上がった")


def _gravure_fallback(ctx: Ctx) -> str:
    """catalog が使えないとき：`MESSAGE_SEISAN_IDOL_GRAVURE_PHOTOSHOOT`:78–87 の写真集タイトル選択だけ（:74 の口上は無し）。"""
    name = ctx.state.target_chara.name
    for k, n in enumerate((5, 4, 3, 2)):
        if _rand(ctx, n) == 0:
            return _BOOK_TITLES[k].format(name)
    return _BOOK_TITLES[4].format(name)


# --- SEISAN_7_IDOL_PROSTITUTION.ERB -----------------------------------------------------------


def idol_prostitution(ctx: Ctx) -> InputGen:
    """`特別活動/SEISAN_7_IDOL_PROSTITUTION.ERB@SEISAN_IDOL_PROSTITUTION`:5–235。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    out.printl("枕営業")
    out.printl()

    def producer_blowjob() -> None:  # :15–29／:81–95
        _msg(ctx, "MESSAGE_SEISAN_IDOL_PROSTITUTION_PRODUCER_BLOWJOB")
        calc_seisan(ctx, MAKURA, MAKURA_FELLA)
        _juel_add(ctx, "習得", 100)
        _exp_add(ctx, "フェラ経験", 3 + _rand(ctx, 3))
        _exp_add(ctx, "精液経験", 1)
        idol_charmup(ctx, 8, 4, 4)
        c.cflag[283] += 1

    if _t(ctx, "処女") > 0 or (_t(ctx, "男の娘") > 0 and _abl(ctx, "Ａ感覚") < 2):  # :11–73
        if _rand(ctx, 4) != 0:
            producer_blowjob()
        else:  # :32–72 顧客に犯される
            nakadashi = 1 if _rand(ctx, 2) == 0 else 0
            _msg(ctx, "MESSAGE_SEISAN_IDOL_PROSTITUTION_VIRGIN_CLIENT", nakadashi)
            if nakadashi and _female(ctx):
                yield from _after_pill(ctx, 35, NOZOMANAI)
            calc_seisan(ctx, MAKURA, MAKURA_SEX)
            if _female(ctx):
                _set_t(ctx, "処女", -1)
                c.cflag[206] = 7
                _juel_add(ctx, "習得", 175)
                _exp_add(ctx, "Ｖ経験", 3)
                _juel_add(ctx, "快Ｖ", 15 * _abl(ctx, "Ｖ感覚"))
            else:
                _juel_add(ctx, "習得", 175)
                _exp_add(ctx, "Ａ経験", 3)
                _juel_add(ctx, "快Ａ", 15 * _abl(ctx, "Ａ感覚"))
            _exp_add(ctx, "Ａ経験", 1)
            _juel_add(ctx, "快Ａ", 5 * _abl(ctx, "Ａ感覚"))
            _exp_add(ctx, "フェラ経験", 1)
            _exp_add(ctx, "精液経験", 5)
            idol_charmup(ctx, 12, 8, 6)
            c.cflag[283] += 2
            if nakadashi and _female(ctx):
                _ninsin(ctx, 5, 80, NOZOMANAI)
    elif _rand(ctx, 3) == 0:  # :77–132 Ｐへの枕
        if st.time == 0:
            producer_blowjob()
        else:  # :98–131
            _msg(ctx, "MESSAGE_SEISAN_IDOL_PROSTITUTION_PRODUCER_SEX")
            calc_seisan(ctx, MAKURA, MAKURA_SEX)
            _juel_add(ctx, "習得", 150)
            if _female(ctx):
                _exp_add(ctx, "Ｖ経験", 3 + _rand(ctx, 3))
                _juel_add(ctx, "快Ｖ", 10 * _abl(ctx, "Ｖ感覚"))
            else:
                _exp_add(ctx, "Ａ経験", 2)
                _juel_add(ctx, "快Ａ", 10 * _abl(ctx, "Ａ感覚"))
            _exp_add(ctx, "Ａ経験", 2 + _rand(ctx, 3))
            _juel_add(ctx, "快Ａ", 10 * _abl(ctx, "Ａ感覚"))
            _exp_add(ctx, "フェラ経験", 2 + _rand(ctx, 2))
            _exp_add(ctx, "精液経験", 6 + _rand(ctx, 3))
            _exp_add(ctx, "絶頂経験", _rand(ctx, 3))
            idol_charmup(ctx, 10, 5, 2)
            c.cflag[283] += 2
            yield from _after_pill(ctx, 35, NOZOMANAI)
            if _female(ctx):
                _ninsin(ctx, 5, 40, NOZOMANAI)
    elif _rand(ctx, 2) == 0:  # :135–183 お偉いさん
        if _rand(ctx, 2) == 0 and _girly(ctx):  # V
            _msg(ctx, "MESSAGE_SEISAN_IDOL_PROSTITUTION_VIP_V")
            calc_seisan(ctx, MAKURA, MAKURA_V)
            _juel_add(ctx, "習得", 225)
            _juel_add(ctx, "恐怖", 100)
            if _female(ctx):
                _exp_add(ctx, "Ｖ経験", 26 + _rand(ctx, 5))
                _juel_add(ctx, "快Ｖ", 20 * _abl(ctx, "Ｖ感覚"))
            else:
                _exp_add(ctx, "Ａ経験", 26 + _rand(ctx, 5))
                _juel_add(ctx, "快Ａ", 20 * _abl(ctx, "Ａ感覚"))
            _exp_add(ctx, "フェラ経験", 2 + _rand(ctx, 2))
            _exp_add(ctx, "精液経験", 13 + _rand(ctx, 3))
            _exp_add(ctx, "絶頂経験", 3 + _rand(ctx, 3))
            if _female(ctx):
                _ninsin(ctx, 10, 5, NOZOMANAI)
        else:  # A
            _msg(ctx, "MESSAGE_SEISAN_IDOL_PROSTITUTION_VIP_A")
            calc_seisan(ctx, MAKURA, MAKURA_A)
            _juel_add(ctx, "習得", 225)
            _juel_add(ctx, "恥情", 100)
            _juel_add(ctx, "快Ａ", 20 * _abl(ctx, "Ａ感覚"))
            _exp_add(ctx, "Ａ経験", 26 + _rand(ctx, 5))
            _exp_add(ctx, "フェラ経験", 2 + _rand(ctx, 2))
            _exp_add(ctx, "精液経験", 13 + _rand(ctx, 3))
            _exp_add(ctx, "絶頂経験", 3 + _rand(ctx, 3))
        idol_charmup(ctx, 16, 8, 3)
        c.cflag[283] += 2
    else:  # :186–229 ファン枕
        _msg(ctx, "MESSAGE_SEISAN_IDOL_PROSTITUTION_FAN")
        calc_seisan(ctx, MAKURA, MAKURA_RINKAN)
        _juel_add(ctx, "習得", 300)
        if _female(ctx):
            _exp_add(ctx, "Ｖ経験", 27 + _rand(ctx, 5))
            _juel_add(ctx, "快Ｖ", 20 * _abl(ctx, "Ｖ感覚"))
        else:
            _exp_add(ctx, "Ａ経験", 27 + _rand(ctx, 5))
            _juel_add(ctx, "快Ａ", 20 * _abl(ctx, "Ａ感覚"))
        _exp_add(ctx, "Ａ経験", 27 + _rand(ctx, 5))
        _juel_add(ctx, "快Ａ", 20 * _abl(ctx, "Ａ感覚"))
        _exp_add(ctx, "フェラ経験", 28 + _rand(ctx, 5))
        _exp_add(ctx, "精液経験", 30 + _rand(ctx, 5))
        _exp_add(ctx, "絶頂経験", 10 + _rand(ctx, 5))
        idol_charmup(ctx, 20, 10, 12)
        c.cflag[283] += 3
        local2 = 0
        if _rand(ctx, 100) < 50:
            local2 += 1
        if _rand(ctx, 100) < 25:
            local2 += 1
        if local2 > 0:
            st.flag[853] += local2
            out.printl(f"人気度が{local2}上がった")
        yield from _after_pill(ctx, 10, DAREtomo)
        if _female(ctx):
            _ninsin(ctx, 15, 80, DAREtomo)
    if _rand(ctx, 100) < 50:  # :234–235
        c.cflag[285] += 1


# --- SEISAN_8_IDOL_LIVE.ERB -------------------------------------------------------------------


def idol_live(ctx: Ctx) -> None:
    """`特別活動/SEISAN_8_IDOL_LIVE.ERB@SEISAN_IDOL_LIVE`:9–100。

    CHARM_BASE／FEAT_RAND／CHARM_RAND（:12–14）は DYNAMIC でない関数内 #DIM ＝静的変数で、絶頂失敗・失敗の分岐では代入されない
    → 前回のライブ公演の値（初回は 0）で :79–80 の魅了経験上昇が起きる（原作どおり）。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    loc = st.temp.locals
    out.printl("ライブ公演")
    out.printl()
    charm = _exp(ctx, "魅了経験")
    if c.cflag[42] == 400 and _rand(ctx, 2) == 0:  # :19–26
        _msg(ctx, "MESSAGE_SEISAN_IDOL_LIVE", ZECCHOU_SHIPPAI)
        audience, payment = calc_seisan(ctx, LIVE, ZECCHOU_SHIPPAI)
    elif _t(ctx, "ラッキーチャーム") == 0 and _rand(ctx, 2 + div(charm, 20)) == 0:  # :29–36
        _msg(ctx, "MESSAGE_SEISAN_IDOL_LIVE", SHIPPAI)
        audience, payment = calc_seisan(ctx, LIVE, SHIPPAI)
    elif _rand(ctx, 8) < div(charm, 100):  # :39–51
        _msg(ctx, "MESSAGE_SEISAN_IDOL_LIVE", DAISEIKOU)
        audience, payment = calc_seisan(ctx, LIVE, DAISEIKOU)
        loc[(_KEY_LIVE + ":CHARM_BASE", 0)] = 12
        loc[(_KEY_LIVE + ":FEAT_RAND", 0)] = 6
        loc[(_KEY_LIVE + ":CHARM_RAND", 0)] = 2
    else:  # :54–72
        _msg(ctx, "MESSAGE_SEISAN_IDOL_LIVE", SEIKOU)
        audience, payment = calc_seisan(ctx, LIVE, SEIKOU)
        if idol_lv(ctx, st.target) < 4:
            vals = (8, 4, 2)
        else:
            vals = (2, 0, 3)
        for k, v in zip(("CHARM_BASE", "FEAT_RAND", "CHARM_RAND"), vals):
            loc[(_KEY_LIVE + ":" + k, 0)] = v
    out.printl(f"{audience}人の来場者を迎え、{_name(ctx)}はギャラとして{payment}＄の資金を稼ぎました。")  # :75
    c.cflag[400] = audience  # :76
    cb = loc.get((_KEY_LIVE + ":CHARM_BASE", 0), 0)
    if cb > 0:  # :79–80
        idol_charmup(ctx, cb, loc.get((_KEY_LIVE + ":FEAT_RAND", 0), 0), loc.get((_KEY_LIVE + ":CHARM_RAND", 0), 0))
    local2 = 0  # :83–93
    for _ in range(3):
        if _rand(ctx, 100) < 50:
            local2 += 1
    if local2 > 0:
        st.flag[853] += local2
        out.printl(f"人気度が{local2}上がった")
    if _exp(ctx, "魅了経験") < 100:  # :96–97
        c.exp[ctx.data.index_of("EXP", "魅了経験")] = 100
    # :100 GET_STATE_EXPUP は実績（UNLOCK_ACHIEVEMENT）のみ：`インターミッション画面/SHOP_TROPHY.ERB`:506–533
