"""自由行動（S28c1）：`ゲーム内_行動実行処理/ACTION_PASTIME.ERB` と `ゲーム内_イベント発生/自由行動中イベント/` の一般イベント。

路徑相對 `source/earGVP/ERB/`（以下 `自由/` は `ゲーム内_イベント発生/自由行動中イベント/` の略）。
- `ACTION_PASTIME.ERB@PASTIME`:3–153（編入・変身選択「気晴らし」・メニュー・スケジュール CFLAG:113・派発・FLAG:73・回復・魅了経験・
  `_ABLUP 1`・変身解除）、`@PASTIME_REST`:157–219。`@PASTIME_TSFLAG_OVERWRITE`:223–251 は全 ERB に呼び出しが無い（grep）ので移植しない。
- `自由/PASTIME_学校途中編入.ERB@PASTIME_SelectSchool`、`PASTIME_街に出る`、`PASTIME_遠出する`（＋8 か所の MESSAGE）、
  `PASTIME_運動する`（＋4 か所の MESSAGE）、`PASTIME_告られ`、`PASTIME_悪堕ち遭遇`、`PASTIME_淫気応急`（＋CALC_INKIOKYU）。
  学校は `eragvt.game.pastime_school`。
- S28c2 の範囲（ナンパ・酒ナンパ・痴漢）のうち、発生判定の `PASTIME_NANPA`（`PASTIME_ナンパ.ERB`:4–69）・`PASTIME_SAKE_NANPA`
  （`PASTIME_酒ナンパ.ERB`:4–70）・`PASTIME_CHIKAN`（`PASTIME_痴漢.ERB`:4–465：乗車〜抵抗の選択まで）を移植し、本編
  （`MESSAGE_PASTIME_NANPA`／`MESSAGE_PASTIME_SAKE_NANPA`／`MESSAGE_PASTIME_CHIKAN`）に入るところで NotImplementedError（Web 停止）。

本文中心の関数（INPUT なし）は地の文扱いで S07 catalog で実行する（`_chinobun`）：`PASTIME_FASHION`、`MESSAGE_PASTIME_FitnessClub`／
`MassageSalon`／`Pool`、遠出の 8 か所、`PASTIME_AKUOTI_EVENT`、改造制服（`KAIZOU_*`・`SHITAGI_COLOR`）、学校の授業・昼休み・部活
（`pastime_school`）、`PASTIME_TOHYO`／`PASTIME_SHASHIN`。状態変化行は `narration/hooks.py` の `PASTIME_HOOK_LINES`。
catalog で実行できないとき（Null narration）は佔位＋`_FALLBACKS`（状態変化が乱数の分岐に依存するものは NotImplementedError）。

引擎語意：
- `&&`／`||` は同じ優先度で左結合・短絡（`reference/emuera-1824/Emuera/GameData/Expression/OperatorCode.cs`:33–34、
  `OperatorMethod.cs`:532–536）。`A && B || C && D` は `((A && B) || C) && D`（街に出る:237）。
- WAIT（PRINTW）は RESULT を変えない（`GameView/EmueraConsole.cs@doInputToEmueraProgram`:701–733：整数・文字列入力だけが
  `emuera.Input*` を呼ぶ）。`DOT_AFTER` は `RETURN RESULT`（`汎用関数/PRINT_LINE.ERB`:53）なので RESULT はそのまま。
- 関数内 `#DIM`（DYNAMIC なし）は静的（`GameProc/UserDefinedVariable.cs`:27、初期値は生成時と `VariableData.cs@SetDefaultLocalValue`:514–520
  ＝新規・ロード時だけ：`GameData/Variable/VariableToken.cs@StaticInt1DVariableToken`:1847–1866）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state import GameState
from .action import Ctx, print_transcallname
from .chara_common import is_female, is_male, talent
from .era import div, limit, mod

InputGen = Generator[None, int, None]

# DIM.ERH:257 望まない相手
NOZOMANAI = -4

_STOP_NANPA = "自由行動：ナンパ（MESSAGE_PASTIME_NANPA、S28c2）は未移植"
_STOP_SAKE = "自由行動：酒ナンパ（MESSAGE_PASTIME_SAKE_NANPA、S28c2）は未移植"
_STOP_CHIKAN = "自由行動：痴漢（MESSAGE_PASTIME_CHIKAN、S28c2）は未移植"


# --- 小道具 -----------------------------------------------------------------------------


def _rand(ctx: Ctx, n: int) -> int:
    return ctx.state.rng.rand(n)


def _t(ctx: Ctx, name: str, who: int | None = None) -> int:
    st = ctx.state
    return talent(ctx.data, st.charas[st.target if who is None else who], name)


def _abl(ctx: Ctx, name: str) -> int:
    return ctx.state.target_chara.abl[ctx.data.index_of("ABL", name)]


def _exp(ctx: Ctx, name: str) -> int:
    return ctx.state.target_chara.exp[ctx.data.index_of("EXP", name)]


def _base(ctx: Ctx, name: str) -> int:
    return ctx.state.target_chara.base[ctx.data.index_of("BASE", name)]


def _maxbase(ctx: Ctx, name: str) -> int:
    return ctx.state.target_chara.maxbase[ctx.data.index_of("BASE", name)]


def _name(ctx: Ctx, who: int | None = None) -> str:
    st = ctx.state
    return print_transcallname(st, st.target if who is None else who)


def _female(ctx: Ctx) -> bool:
    return is_female(ctx.data, ctx.state.target_chara)


def _male(ctx: Ctx) -> bool:
    return is_male(ctx.data, ctx.state.target_chara)


def _hole(ctx: Ctx, who: int | None = None) -> bool:
    from .battle.core import is_hole

    return is_hole(ctx, who)


def _girly(ctx: Ctx) -> bool:
    from .battle.core import is_girly

    return is_girly(ctx)


def _manly(ctx: Ctx) -> bool:
    from .battle.core import is_manly

    return is_manly(ctx)


def _holyvirgin(ctx: Ctx) -> int:
    from .battle.sexcom import check_holyvirgin

    return check_holyvirgin(ctx)


def _item(ctx: Ctx, n: int) -> str:
    return ctx.data.names["ITEM"].get(n, "")


def _dot_after(ctx: Ctx, arg: int = 1) -> None:
    """`CALL DOT_AFTER, ARG`（`汎用関数/PRINT_LINE.ERB`:34–53）。:53 `RETURN RESULT` なので RESULT は変わらない。"""
    from .akuoti import dot_after

    dot_after(ctx, arg)


def _chinobun(ctx: Ctx, func: str, *args, fallback=None) -> bool:
    """本文中心の関数を catalog で実行（`run_function`）。実行できなければ佔位 1 行＋RESULT:0 = 0（本作の対象関数はどれも
    `RETURN 0` か関数終端：`Process.ScriptProc.cs`:61–67）＋`fallback`（状態変化の Python 移植）。"""
    from .battle.core import chinobun

    if ctx.narration.run_function(ctx, func, list(args)):
        return True
    chinobun(ctx, func)
    ctx.state.result[0] = 0
    fb = fallback if fallback is not None else _FALLBACKS.get(func.upper())
    if fb is not None:
        fb(ctx)
    return False


def _narr_static(ctx: Ctx, func: str, var: str) -> int:
    """catalog と共有する関数内 #DIM 静的変数（`narration.runtime.Interp._set_narr((関数名, 変数名), (0,), 値)`）。"""
    d = getattr(ctx.state.temp, "narr", None)
    return 0 if d is None else d.get(((func, var), (0,)), 0)


def _set_narr_static(ctx: Ctx, func: str, var: str, value: int) -> None:
    d = getattr(ctx.state.temp, "narr", None)
    if d is None:
        d = {}
        ctx.state.temp.narr = d
    d[((func, var), (0,))] = value


def _ts_count(ctx: Ctx, normal: int, ts: int) -> int:
    """`IF TALENT:変身時ＴＳ > 0 && CFLAG:1 > 0` で選ぶ回数 CFLAG（変身時ＴＳ側／通常側）。"""
    return ts if _t(ctx, "変身時ＴＳ") > 0 and ctx.state.target_chara.cflag[1] > 0 else normal


# --- catalog で実行できないときの状態変化（hooks.PASTIME_HOOK_LINES と同じ行） ------------------------------


def _fb_fashion(ctx: Ctx) -> None:
    """`自由/PASTIME_ファッション.ERB`:12–14（ISMALE → RETURN 0）、:29／:122 の分岐、:346 `CFLAG:310 += 1`。"""
    c = ctx.state.target_chara
    if _male(ctx) or _t(ctx, "淫乱") > 0:
        return
    if (_female(ctx) and _t(ctx, "変身時ＴＳ") > 0 and c.cflag[1] > 0) or mod(_t(ctx, "性別変化"), 10) == 1:
        c.cflag[310] += 1


def _fb_fitness(ctx: Ctx) -> None:
    """`自由/PASTIME_運動する.ERB@MESSAGE_PASTIME_FitnessClub`:313–374（EROEVENT は静的：初回で 1 になり以後そのまま）。"""
    c = ctx.state.target_chara
    k = _ts_count(ctx, 334, 335)
    if c.cflag[k] == 0:  # :323 CCOUNT == 0 → :347
        _set_narr_static(ctx, "MESSAGE_PASTIME_FITNESSCLUB", "EROEVENT", 1)
    c.cflag[k] += 1  # :369–373
    ctx.state.result[0] = _narr_static(ctx, "MESSAGE_PASTIME_FITNESSCLUB", "EROEVENT")  # :374


def _fb_massage(ctx: Ctx) -> None:
    """`@MESSAGE_PASTIME_MassageSalon`:379–410（EROEVENT は代入されない → 0）。"""
    ctx.state.target_chara.cflag[_ts_count(ctx, 338, 339)] += 1


def _fb_pool(ctx: Ctx) -> None:
    """`@MESSAGE_PASTIME_Pool`:415–646。:443–460 の水着（CFLAG:270）は本文の RAND で決まるので移植できない。"""
    c = ctx.state.target_chara
    if _t(ctx, "淫乱") > 0 and _t(ctx, "初心") < 1 and _girly(ctx):
        raise NotImplementedError("MESSAGE_PASTIME_Pool：catalog で実行できない（CFLAG:270 が本文の乱数で決まる）")
    if _manly(ctx):  # :462–471
        c.cflag[270] = 99
    elif 1 <= _t(ctx, "学生") <= 2:
        c.cflag[270] = 4
    else:
        c.cflag[270] = 5
    c.cflag[_ts_count(ctx, 342, 343)] += 1  # :641–645


def _fb_random(func: str):
    def fb(ctx: Ctx) -> None:
        raise NotImplementedError(f"{func}：catalog で実行できない（状態変化が本文の乱数分岐の中にある）")

    return fb


def _fb_club(ctx: Ctx) -> None:
    """`自由/PASTIME_学校に行く.ERB@Message_School_Clubactivities`:1650–1654。"""
    c = ctx.state.target_chara
    c.cflag[355 if c.cflag[1] > 0 else 354] += 1


_FALLBACKS = {
    "PASTIME_FASHION": _fb_fashion,
    "MESSAGE_PASTIME_FITNESSCLUB": _fb_fitness,
    "MESSAGE_PASTIME_MASSAGESALON": _fb_massage,
    "MESSAGE_PASTIME_POOL": _fb_pool,
    "MESSAGE_SCHOOL_CLASSWORK": _fb_random("Message_School_Classwork"),
    "MESSAGE_SCHOOL_CLUBACTIVITIES": _fb_club,
}


# --- @PASTIME（ACTION_PASTIME.ERB:3–153） --------------------------------------------------


def num_schedule_f(c, arg: int) -> int:
    """`ACTIONsub_SCHEDULE.ERB@NUM_SCHEDULE_F(ARG)`:498–500 = CFLAG:ARG % 10^18。"""
    from .schedule import E18

    return mod(c.cflag[arg], E18)


def _schedule_night(c) -> int:
    """ACTION_PASTIME.ERB:33–43：夜に通学（0）が出たら `FOR LOCAL,1,NUM_SCHEDULE_F(113)+1` で通学以外を探す（RESULT = 1 は
    すぐ RES_SCHEDULE に上書きされる）。全部通学なら NUM_SCHEDULE_F 回（最大 ~10^16）回して最後の RESULT（0）。

    RES_SCHEDULE は CFLAG:113 の実行番号（10^18 の位、0〜8）を巡回させるだけなので、同じ CFLAG 値に戻ったら残り回数を周期で割った
    余りだけ回せば最終状態は同じ。
    DEVIATION: 原作は項目が多い（NUM_SCHEDULE_F が ~10^16）と事実上止まらない（応答なし）。ここでは周期で早送りして同じ最終状態で進む
    （deviations.md「S28c1」）。項目 1〜2 個なら回数は 1／101 回で原作も止まらない。"""
    from .schedule import res_schedule

    n = num_schedule_f(c, 113)
    seen: dict[int, int] = {}
    i = 0
    result = 0
    while i < n:
        key = c.cflag[113]
        if key in seen:  # 周期（この間ずっと 0）
            period = i - seen[key]
            rest = (n - i) % period
            for _ in range(rest):
                result = res_schedule(c, 113)
            return result
        seen[key] = i
        result = res_schedule(c, 113)
        i += 1
        if result != 0:
            return result
    return result


def pastime(ctx: Ctx) -> InputGen:
    """`ACTION_PASTIME.ERB@PASTIME`:3–153（TARGET が対象）。:153 の BEGIN TURNEND は ACTION_MAIN:157–163 が上書きする。"""
    from .battle.ablup import ablup
    from .battle.func import transform
    from .gather import action_transformation_select, calc_charm_feat_other
    from .pastime_school import pastime_school
    from .schedule import res_schedule

    st, out = ctx.state, ctx.out
    c = st.target_chara
    st.flag[11] = 0  # :5
    if _t(ctx, "学生") == 0 and mod(st.day[0], 30) == 0 and st.day[0] > 29:  # :8–10
        yield from select_school(ctx)
    yield from action_transformation_select(ctx, st.target, "気晴らし")  # :13
    out.print("[0]街に出る　　　　　　")  # :15–25
    out.print("[1]遠出する　　　　　　")
    out.print("[2]運動をする　　　　　")
    out.printl()
    if st.time > 0:
        out.set_color((105, 105, 105))
    if _t(ctx, "学生") > 0:
        out.print("[3]学校に行く　　　　　")
    out.reset_color()
    out.printl()
    out.drawline()
    if c.cflag[113] > 0:  # :29–81
        result = res_schedule(c, 113)
        if result == 0 and st.time == 1:  # :33–43
            result = _schedule_night(c)
        st.result[0] = result
        if result == 0:
            yield from pastime_school(ctx, 0)
        elif result == 1:  # :47–68
            if st.time == 0:
                r = _rand(ctx, 4)
                if r == 0:
                    yield from pastime_school(ctx, -1)
                elif r == 1:
                    yield from machi(ctx, _rand(ctx, 4))
                elif r == 2:
                    yield from toode(ctx, _rand(ctx, 8))
                else:
                    yield from undou(ctx, _rand(ctx, 4))
            else:
                r = 1 + _rand(ctx, 3)
                if r == 1:
                    yield from machi(ctx, _rand(ctx, 4))
                elif r == 2:
                    yield from toode(ctx, _rand(ctx, 8))
                else:
                    yield from undou(ctx, _rand(ctx, 4))
        elif result == 2:
            yield from machi(ctx, _rand(ctx, 4))
        elif result == 3:
            yield from toode(ctx, _rand(ctx, 8))
        elif result == 4:
            yield from undou(ctx, _rand(ctx, 4))
        elif 5 <= result <= 8:  # SCHEDULE の表示名（:181–227）とは順番が違う（5 = 「街：アミューズメント施設」→ ショッピングモール）：原作どおり
            yield from machi(ctx, result - 5)
        elif 9 <= result <= 16:
            yield from toode(ctx, result - 9)
        elif 17 <= result <= 20:
            yield from undou(ctx, result - 17)
        # それ以外（-1 等）は何もしない
    else:  # :96–132
        while True:
            result = yield
            st.result[0] = result
            out.printl()
            if 0 <= result <= 3:
                out.drawline()  # :101（CASE 3 の検査より前）
                if result == 3:
                    if _t(ctx, "学生") < 1:
                        out.printl("正しい値を入力してください")
                        continue
                    if st.time > 0:
                        out.printl("学校に行けるのは昼のみです")
                        continue
                break
            out.printl("正しい値を入力してください")
        if result == 0:
            yield from machi(ctx, -1)
        elif result == 1:
            yield from toode(ctx, -1)
        elif result == 2:
            yield from undou(ctx, -1)
        else:
            yield from pastime_school(ctx, -1)
    if st.flag[73] > 0:  # :135–139
        if c.cflag[1] > 0:
            transform(ctx, 0)
        return
    pastime_rest(ctx)  # :141
    local = calc_charm_feat_other(ctx, st.target)  # :144–148
    if local > 0:
        c.exp[ctx.data.index_of("EXP", "魅了経験")] += local
        out.printl(f"魅了経験が{local}上がった")
    ablup(ctx, 1)  # :150
    if c.cflag[1] > 0:  # :151–152
        transform(ctx, 0)


def pastime_rest(ctx: Ctx) -> None:
    """`ACTION_PASTIME.ERB@PASTIME_REST`:157–219。"""
    from .action import config_check_screen

    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.target_chara
    l1, l2 = 10, 30  # :164–165
    if _t(ctx, "回復早い") > 0:
        l1 += 5
        l2 += 5
    elif _t(ctx, "回復遅い") > 0:  # :170–172 気力は +5（原作どおり）
        l1 -= 5
        l2 += 5
    if _t(ctx, "魔力貯蔵") > 0:
        l1 -= 5
        l2 -= 5
    if _t(ctx, "不老長寿") > 0:
        l1 -= 5
        l2 -= 5
    if _t(ctx, "溢れる生命力") > 0:
        l1 += 10
        l2 += 10
    hp, mp, sei = data.index_of("BASE", "体力"), data.index_of("BASE", "気力"), data.index_of("BASE", "性耐性")
    local = div(c.maxbase[hp] * l1, 100) + 200  # :186–187
    c.base[hp] = limit(local + c.base[hp], 0, c.maxbase[hp])
    local = div(c.maxbase[mp] * l2, 100) + 200  # :189–190
    c.base[mp] = limit(local + c.base[mp], 0, c.maxbase[mp])
    c.base[sei] = limit(c.base[sei] + div(c.maxbase[sei], 2), 0, c.maxbase[sei])  # :192
    if c.cflag[0] != -1 and c.cflag[999] != 0:  # :194–219
        if c.cflag[99] > 0:
            c.cflag[99] -= 10
            if c.cflag[99] < 0:
                c.cflag[99] = 0
            if c.cflag[99] == 0:
                out.printl(f"{c.callname}の身体から疲労が完全に抜けた！")
            else:
                out.printl(f"{c.callname}の身体から疲労が少し抜けた…")
        out.printl()
        if c.base[hp] == c.maxbase[hp] and c.base[mp] == c.maxbase[mp] and c.cflag[99] == 0:
            out.printl(f"{c.callname}は最大まで回復した！")
        if config_check_screen(st, 3) == 0:
            out.printw()
        else:
            out.printl()


# --- 学校途中編入（自由/PASTIME_学校途中編入.ERB） -------------------------------------------


def select_school(ctx: Ctx) -> InputGen:
    """`@PASTIME_SelectSchool`:1–45（:3／:25 の IF はコメントアウト）。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    n = _name(ctx)
    out.printl(f"{n}が休日をどう過ごすか考えていると、")
    out.printl("組織の人間が声をかけてきた。")
    if _rand(ctx, 5) == 0:
        out.printl("曰く、学校のような閉鎖的社会で触手生物が活動する例もある。")
        out.printl("そこで君に長期の潜入捜査をお願いしたい…と。")
    elif _rand(ctx, 3) == 0:
        out.printl("曰く、同年代の友人を作るのもストレス解消に良いのでは…と。")
    else:
        out.printl("曰く、暇を持て余しているなら学業に精を出してはどうか…と。")
    out.printl("折角の休日だ、どう過ごすのも自由だが・・・")
    out.printw()
    out.printl("[0]編入しない")
    age, mage = _base(ctx, "年齢"), _maxbase(ctx, "年齢")
    if (c.cflag[1] == 0 and age <= 12) or (c.cflag[1] > 0 and mage <= 12):  # :18–19
        out.printl("[1]小学校に編入する")
    if (c.cflag[1] == 0 and age <= 15) or (c.cflag[1] > 0 and mage <= 15):  # :21–22
        out.printl("[2]中学校に編入する")
    out.printl("[3]高校に編入する")
    out.printl("[4]大学に編入する")
    while True:  # :26–42（表示の有無に関わらず 0〜4 を受け付ける：原作どおり）
        result = yield
        st.result[0] = result
        out.print(f"{n}は")
        if 0 <= result <= 4:
            out.printl(("どこにも編入しないことにした。", "小学校に編入することにした。", "中学校に編入することにした。",
                        "高校に編入することにした。", "大学に編入することにした。")[result])
            break
        out.printl("正しい値を入力してください")
    c.talent[ctx.data.index_of("TALENT", "学生")] = result  # :44–45


# --- ナンパ／酒ナンパの発生判定（S28c2 の前段） --------------------------------------------------


def _nanpa_bonus(ctx: Ctx, student: tuple[int, int, int, int], naki: int) -> int:
    t = lambda n: _t(ctx, n)  # noqa: E731
    v = 10 + _rand(ctx, 10)
    v += student[t("学生") - 1] if 1 <= t("学生") <= 4 else 0
    if t("巨乳") > 0:
        v += 3
    if t("小柄") > 0:
        v -= 3
    if t("女体受容") > 0:
        v += 2
    if t("男の娘") > 0:
        v += 1
    for k in ("社交的", "母性的", "小悪魔", "目立ちたがり", "上品"):
        if t(k) > 0:
            v += 3
    if t("泣き虫") > 0:
        v += naki
    if t("清純派") > 0:
        v += 3
    if ctx.state.target_chara.cflag[1] > 0:
        if t("変身時外見") > 0:
            v += 3
    elif t("外見") > 0:
        v += 3
    if t("巻き込まれ体質") > 0:
        v += 5
    if t("人外の美貌") > 0:
        v += 5
    if t("小さな体躯") > 0:
        v -= 3
    return v


def pastime_nanpa(ctx: Ctx) -> int:
    """`自由/PASTIME_ナンパ.ERB@PASTIME_NANPA`:4–69（RETURN → RESULT:0）。"""
    if _manly(ctx):  # :8–9
        ctx.state.result[0] = 0
        return 0
    nanpa = _nanpa_bonus(ctx, (-3, 1, 3, 3), 3)  # :12–64
    r = 1 if _rand(ctx, 100) <= nanpa else 0  # :66–69
    ctx.state.result[0] = r
    return r


def pastime_sake_nanpa(ctx: Ctx) -> int:
    """`自由/PASTIME_酒ナンパ.ERB@PASTIME_SAKE_NANPA`:4–70（RETURN → RESULT:0）。"""
    if _manly(ctx):  # :8–10
        ctx.state.result[0] = 0
        return 0
    v = _nanpa_bonus(ctx, (-1, 2, 3, 4), 5)  # :13–65
    r = 1 if _rand(ctx, 100) <= v else 0  # :67–70
    ctx.state.result[0] = r
    return r


def message_pastime_nanpa(ctx: Ctx, arg: int) -> None:
    """`CALL MESSAGE_PASTIME_NANPA, ARG`（`PASTIME_ナンパ.ERB`:73–605）：S28c2。"""
    raise NotImplementedError(_STOP_NANPA)


def message_pastime_sake_nanpa(ctx: Ctx, arg: int) -> None:
    """`CALL MESSAGE_PASTIME_SAKE_NANPA, ARG`（`PASTIME_酒ナンパ.ERB`:74–263）：S28c2。"""
    raise NotImplementedError(_STOP_SAKE)


def message_pastime_chikan(ctx: Ctx, arg: int, pos: int, naburare: int, aite: str) -> None:
    """`CALL MESSAGE_PASTIME_CHIKAN, ARG, CHIKAN_POS, NABURARE, 痴漢してきた相手`（`PASTIME_痴漢.ERB`:470–1191）：S28c2。"""
    raise NotImplementedError(_STOP_CHIKAN)


# --- 痴漢の発生判定（自由/PASTIME_痴漢.ERB@PASTIME_CHIKAN:4–465） ------------------------------------


_AITE = ("脂ぎった中年オヤジ", "威圧感のあるチンピラ", "軽薄そうな男", "爽やかな好青年", "温厚そうな紳士", "気弱そうな学生")


def _stand_line(ctx: Ctx, n: str, stand: int, back: bool) -> None:
    out = ctx.out
    if stand == 0:
        out.printl(f"{n}が立ち通していると")
    elif stand == 1:
        out.printl(f"{n}がドアを背にしていると" if back else f"{n}がドアの前に立って景色を眺めていると")
    else:
        out.printl(f"{n}が壁を背にしていると" if back else f"{n}が窓の前に立って景色を眺めていると")


def pastime_chikan(ctx: Ctx, arg: int) -> Generator[None, int, int]:
    """`@PASTIME_CHIKAN, ARG`:4–465。戻り値 = RESULT（本編で持ち帰られたら 1：S28c2）。

    呼び出し元は自分の ARG をそのまま渡す（遠出 -1／0〜7、学校 -1／0）ので、ARG == 1（遠出の文）は水族館の予約、
    ARG == 3（通学の混雑・文）は植物園の予約のときだけになる：原作どおり。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    n = _name(ctx)
    t = lambda k: _t(ctx, k)  # noqa: E731
    teikou = 0  # :15–16
    naburare = 0
    pos = 0  # CHIKAN_POS（静的、:224 でのみ代入・本編でのみ使用）
    if arg == 3 and c.cflag[356] != 2 and arg == 3:  # :17–18
        c.cflag[356] = 0
    kou = t("嬲られ体質") > 0
    gakkou = ""
    if arg == 3:  # :23–44
        if c.cflag[358] == 1:
            konzatu = _rand(ctx, 30) + 70 + 30 + (5 if kou else 0)
            gakkou = "都心"
        else:
            konzatu = _rand(ctx, 70) + 30 + (10 if kou else 0)
            gakkou = "郊外"
    elif kou:
        konzatu = _rand(ctx, 60) + 40
    else:
        konzatu = _rand(ctx, 95)
        if st.time < 1:
            konzatu += 5
        if st.time > 0:
            konzatu -= 5
    if arg == 1:  # :46–64
        out.printl(f"{n}は少しばかり遠出する為に電車に乗っている。")
    elif arg == 3:
        mokuteki = {1: "小学校", 2: "中学校", 3: "高校", 4: "大学"}.get(t("学生"), "")
        out.printl(f"{n}は{gakkou}の{mokuteki}に通う為に電車に乗っている。")
    if st.time > 0:  # :65–85
        who = "帰宅途上のサラリーマンや学生"
    else:
        who = "出勤中のサラリーマンや登校中の学生"
    if konzatu >= 70:
        out.printl(f"車内は{who}で満員だ。")
    elif 40 <= konzatu < 70:
        out.printl(f"車内は{who}で混雑している。")
    elif 15 <= konzatu < 40:
        out.printl("車内にはまばらに人がいるが座席に座れない事もなさそうだ。")
    else:
        out.printl("車内はガラガラだ。")
    if st.flag[852] < 1000:  # :86–91
        out.printl()
        out.printl("ここ数日、侵食の度合いを強くする触手に対し人々は為すすべもなく蹂躙されていた。")
        out.printl("誰もが一様に陰鬱な面持ちで電車に揺られ、明日への希望などとうに手放していても不思議ではない。")
        out.printl("辛うじて日常を送れる程度に社会が保たれている為、仕方なしに日常のサイクルを続けているだけだ。")
    out.printw()
    if _hole(ctx):  # :94–106
        if konzatu >= 40 and _rand(ctx, 4) == 0 and _female(ctx):
            out.printl(f"人の流れに乗り車内を進む{n}だったが")
            out.printl("何かに引っかかりスカートがめくれそうになっている事に気がつき慌ててスカートを抑えつけた。")
        elif konzatu >= 40 and _rand(ctx, 3) == 0:
            out.printl(f"車内へ乗り込んだものの{n}は濁流の様な流れに逆らえず")
            out.printl("グイグイと人の流れに押し流されていってしまった。")
        elif konzatu >= 40:
            out.printl("混雑する車内にどうにか入ったもののろくに身動きが取れない上に")
            out.printl(f"周囲から漂うむせ返る様な汗臭さに{n}は息苦しさを感じている。")
        out.printl()
    if konzatu < 40 or (konzatu < 45 and _rand(ctx, 4) == 0):  # :109–124
        out.printl(f"座席を確保できた{n}は座って一息ついた・・・")
        stand = -1
    elif _rand(ctx, 4) == 0:
        out.printl(f"なんとか開かない側のドアの前を確保できた{n}は一息ついた・・・")
        stand = 1
    elif _rand(ctx, 3) == 0:
        out.printl(f"なんとか車両端の壁の前を確保できた{n}は一息ついた・・・")
        stand = 2
    elif _rand(ctx, 2) == 0:
        out.printl(f"なんとか入口付近の窓の前を確保できた{n}は一息ついた・・・")
        stand = 3
    else:
        out.printl(f"人混みの真っ只中に落ち着いた{n}は電車が動き出すと一息ついた・・・")
        stand = 0
    check = 10 + _rand(ctx, 10)  # :127–181
    check += {1: -3, 2: 1, 3: 3, 4: 3}.get(t("学生"), 0)
    if t("巨乳") > 0:
        check += 3
    if t("小柄") > 0:
        check -= 3
    if t("女体受容") > 0:
        check += 2
    if t("男の娘") > 0:
        check += 1
    for k in ("社交的", "母性的", "小悪魔", "目立ちたがり", "上品", "泣き虫", "清純派"):
        if t(k) > 0:
            check += 3
    if c.cflag[1] > 0:
        if t("変身時外見") > 0:
            check += 3
    elif t("外見") > 0:
        check += 3
    if t("巻き込まれ体質") > 0:
        check += 5
    if t("人外の美貌") > 0:
        check += 5
    if t("小さな体躯") > 0:
        check -= 3
    if kou:
        check += 10
    local = 0  # :183–203
    a, b = (326, 328) if t("変身時ＴＳ") > 0 and c.cflag[1] > 0 else (325, 327)
    local += 10 if c.cflag[a] >= 10 else c.cflag[a]
    local += 10 if c.cflag[b] >= 10 else c.cflag[b]
    check += local
    r6 = 5  # :205–217
    for i, k in enumerate((6, 5, 4, 3, 2)):
        if _rand(ctx, k) == 0:
            r6 = i
            break
    aite = _AITE[r6]
    if (_rand(ctx, 80) <= check and _hole(ctx)) and konzatu >= 40 and stand >= 0:  # :222
        pos = _rand(ctx, 2)  # :224
        out.printw()
        if pos > 0:  # :226–275
            if _rand(ctx, 4) == 0:
                _stand_line(ctx, n, stand, False)
                out.printl(f"混雑に押されてきた背後に立つ{aite}と密着する体勢になってしまった。")
                out.printl()
                out.printl(f"ふとももの辺りにくすぐったさを感じてもしやと思った{n}が足元を見ると")
                out.printl(f"{aite}の手が{n}のふとももに伸びている様に見える…")
            elif _rand(ctx, 3) == 0:
                _stand_line(ctx, n, stand, False)
                out.printl(f"混雑に押されてきた背後に立つ{aite}と密着する体勢になってしまった。")
                out.printl()
                out.printl(f"お尻に何か硬い物が当たる感触がした{n}が怪訝な顔で辺りを見渡すと、")
                out.printl(f"背後の{aite}が股間の膨らみを押し付けている気がする…")
            elif _rand(ctx, 2) == 0:
                _stand_line(ctx, n, stand, False)
                out.printl(f"混雑に押されてきた背後に立つ{aite}と密着する体勢になってしまった。")
                out.printl()
                out.printl(f"突然のお尻を撫でられる感触に{n}は小さな悲鳴を上げてしまい慌てて口を抑える。")
                out.printl(f"{n}が周りを見回すと、背後の{aite}の手がお尻に伸びている様に見える…")
            else:
                _stand_line(ctx, n, stand, False)
                out.printl(f"混雑に押されてきた背後に立つ{aite}と密着する体勢になってしまった。")
                out.printl()
                out.printl(f"細い何かにふとももを撫でられ{n}は小さな悲鳴を上げてしまい慌てて口を抑える。")
                out.printl(f"{n}が周りを見回すと、背後の{aite}の手がふとももを撫でている様に見える…")
        else:  # :276–314
            if _rand(ctx, 3) == 0:
                _stand_line(ctx, n, stand, True)
                out.printl(f"混雑に押されてきた{aite}と密着する体勢になってしまった。")
                out.printl()
                out.printl(f"ふとももの辺りにくすぐったさを感じてもしやと思った{n}が足元を見ると")
                out.printl(f"{aite}の手が{n}のふとももに伸びている様に見える…")
            elif _rand(ctx, 2) == 0:
                _stand_line(ctx, n, stand, True)
                out.printl(f"混雑に押されてきた{aite}と密着する体勢になってしまった。")
                out.printl()
                out.printl(f"身体に何か硬い物が当たる感触がした{n}は怪訝な顔で辺りを見渡すと、")
                out.printl(f"目の前の{aite}が股間の膨らみを押し付けている気がする…")
            else:
                _stand_line(ctx, n, stand, True)
                out.printl(f"混雑に押されてきた{aite}と密着する体勢になってしまった。")
                out.printl()
                out.printl(f"胸を何かに触られている気がした{n}が胸に目を向けると")
                out.printl(f"{aite}がスマホを手にし、その画面を凝視しており")
                out.printl(f"電車が揺れる度にスマホを持った手が{n}の胸に触れている…")
        if _female(ctx) and t("変身時ＴＳ") > 0 and t("女体受容") == 0:  # :316–325
            out.printl(f"この状況に、体は女でも心は男のつもりの{n}は")
            out.printl("嫌悪感と奇妙な興奮のないまぜになった感情を昂らせ、激しい動悸に襲われている。")
        elif t("女体受容") == 1:
            out.printl(f"この状況に、心も身体もすっかり女になった{n}は")
            out.printl("女のカラダでなければ味わえないスリルと快楽を期待して、胸の高鳴りを抑えきれないでいる。")
        elif t("男の娘") > 0:
            out.printl(f"この状況に、いくらよく女の子と勘違いされてもしっかり男のつもりの{n}は")
            out.printl("嫌悪感と困惑と、それに混ざった説明のつかない奇妙な感情を昂らせ、激しい動悸に襲われている。")
        out.printl()  # :327
        if (_female(ctx) and t("変身時ＴＳ") > 0) or t("男の娘") > 0:  # :328–340
            if (c.cflag[326] > 14 or c.cflag[325] > 14) and t("初心") < 1:
                out.printl(f"{n}は日常的に痴漢されるうちに、常連痴漢のクセや好きな責めがわかるほどになっていた。")
                out.printl("どの路線、いつの時間帯か。位置取りの仕方、どこを責めるのが好きか、得意な技は何か。")
                out.printl(f"それは痴漢男も同じことで、{n}の生活リズムや性感帯などは熟知している。")
            elif c.cflag[326] > 9 or c.cflag[325] > 9:
                out.printl(f"何度も痴漢の餌食になった{n}はその男に見覚えがあった。どうやら痴漢の中にも常連というものがあるらしい。")
            elif c.cflag[326] > 4 or c.cflag[325] > 4:
                out.printl(f"何度も痴漢されている{n}は自分が痴漢しやすい『女』だと思われていると自覚した。")
            elif c.cflag[326] > 2 or c.cflag[325] > 2:
                out.printl(f"今までも何度か痴漢の餌食になった{n}は身を強張らせた。")
        out.printw()
        out.printl()
        yoku, juujun = _abl(ctx, "欲望"), _abl(ctx, "従順")
        sei = _base(ctx, "性耐性")
        if (yoku >= 3 and t("初心") < 1) or sei < 10:  # :343–347
            out.printl("[0]なすがまま")
        else:
            out.printl("[0]我慢する")
        out.printl(f"[1]抵抗　　　　　　　　（抵抗失敗率{juujun * 10 + local + 35}％）")
        out.printl(f"[2]電車を降りる　　　　（抵抗失敗率{juujun * 7 + 5 + (1 if kou else 0) * 20}％）")
        out.printl("[3]防犯ブザーを鳴らす　（抵抗失敗率 0％）")
        while True:  # :351–450
            result = yield
            st.result[0] = result
            if 0 <= result <= 3:
                break
        if result == 0:
            out.printl()
            if _rand(ctx, 4) == 0 and yoku >= 3 and t("初心") < 1:
                out.printl(f"痴漢かもしれないと察した{n}は")
                out.printl("高揚感を感じながら様子を見ることにした・・・")
            elif _rand(ctx, 3) == 0:
                out.printl(f"自分の気のせいかもしれないと思った{n}は")
                out.printl("不快感を感じながらも我慢することにした・・・")
            elif _rand(ctx, 2) == 0:
                out.printl(f"すぐにやめてくれるかもしれないと考えた{n}は")
                out.printl("怯えつつも我慢することにした・・・")
            else:
                out.printl("ここで大事にすると面倒になる。")
                out.printl(f"相手もそれは望まないだろうと考えた{n}は")
                out.printl("速く目的地に着くことを祈りながら我慢することにした・・・")
            if st.flag[852] < 1000:
                out.printl(f"気のせいか他の乗客たちも{n}のいる方へ詰めて来ているようだ・・・")
            teikou = 1
            naburare = 1
        elif result == 1:
            out.printl()
            if _rand(ctx, 100) < juujun * 10 + local + 35:  # :376
                # :377／:380 `RAND:n == 0 &&(…) || BASE:性耐性 < 10` は ((RAND && …) || 性耐性 < 10)
                if (_rand(ctx, 5) == 0 and (yoku >= 3 and t("初心") < 1)) or sei < 10:
                    out.printl(f"このままどうされるのかと考えた{n}は")
                    out.printl("抗わない事にした・・・")
                elif (_rand(ctx, 4) == 0 and (yoku >= 3 and t("初心") < 1)) or sei < 10:
                    out.printl(f"抵抗しようとした{n}だったが")
                    out.printl("痴漢されることを期待してしまい何も出来ずにいる・・・")
                elif _rand(ctx, 4) == 0 and t("初心") < 1:
                    out.printl(f"抵抗しようとした{n}だったが")
                    out.printl("従わせられる安心感に身を任せて何も出来ずにいる・・・")
                elif _rand(ctx, 3) == 0:
                    out.printl(f"抵抗しようとした{n}だったが")
                    out.printl("恐怖に見を竦ませてしまい何も出来ずにいる・・・")
                elif _rand(ctx, 2) == 0:
                    out.printl(f"声を上げようとした{n}だったが")
                    out.printl(f"口を開いた瞬間、{aite}に口を抑えられ声を発することができなかった・・・")
                else:
                    out.printl(f"相手の腕を掴もうとした{n}だったが、")
                    out.printl(f"逆に自分の腕を{aite}に掴まれてしまった・・・")
                if st.flag[852] < 1000:
                    out.printl(f"気のせいか他の乗客たちも{n}のいる方へ詰めて来ているようだ・・・")
                    naburare = 1
                teikou = 1
            else:
                out.printl(f"{n}が弱々しく抵抗すると")
                out.printl(f"{aite}は気まずそうに離れていった・・・")
                teikou = 0
        elif result == 2:
            out.printw()
            out.printl()
            out.printl(f"{n}は最寄りの駅に着くなり逃げ出せるように身構えた…")
            out.printw()
            if _rand(ctx, 100) < juujun * 7 + 5 + (1 if kou else 0) * 20:  # :411
                if _rand(ctx, 4) == 0:
                    out.printl(f"電車が停止し扉が開いた瞬間、逃げようとした{n}だったが")
                    out.printl("恐怖に見を竦ませてしまい何も出来ずにいる。")
                    out.printl("恐怖を振り払おうとするも、気を取り直す前に扉は閉まってしまった・・・")
                elif _rand(ctx, 3) == 0:
                    out.printl(f"電車が停止し扉が開いた瞬間、{n}は降りようとしたが")
                    out.printl("しっかり腕を掴まれてしまい動くことができなかった。")
                    out.printl("引き離そうとするも相手の力に敵わず、悪戦苦闘してる内に扉は閉まってしまった・・・")
                elif _rand(ctx, 2) == 0:
                    out.printl(f"電車が停止し扉が開いた瞬間、逃げようとした{n}だったが")
                    out.printl("カラダを押し付けられて身動きが取れなくなってしまった。")
                    out.printl("相手のカラダを押し退けようとするが、その前に扉は閉まってしまった・・・")
                else:
                    out.printl(f"電車が停止し扉が開いた瞬間、逃げようとした{n}だったが")
                    out.printl("停車する際に大きく揺れ動き、人混みが流れてきた為更に大きな圧力がかかってしまった。")
                    out.printl("なんとか振り払って出入口に進もうとするが、一歩も進めずに扉は閉まってしまった・・・")
                if st.flag[852] < 1000 or t("巻き込まれ体質") > 0 or t("人外の美貌") > 0 or kou:
                    out.printl(f"気のせいか他の乗客たちも{n}のいる方へ詰めて来ているようだ・・・")
                    naburare = 1
                c.cflag[356] = 3 if c.cflag[356] > 1 else 1  # :433–437
                teikou = 1
            else:
                out.printl("電車が停止し扉が開いた瞬間")
                out.printl(f"{n}は全力で逃げ出した・・・")
                teikou = 0
        else:
            out.printl("けたたましい音が車内に響くと")
            out.printl(f"{aite}は即座に離れていった・・・")
            teikou = 0
    out.printw()  # :452
    if teikou > 0:  # :455–460 抵抗失敗 → 本編（S28c2）
        message_pastime_chikan(ctx, arg, pos, naburare, aite)
    out.printl()  # :462–465
    _dot_after(ctx, 1)
    out.printl()
    st.result[0] = 0
    return 0


# --- 悪堕ち遭遇（自由/PASTIME_悪堕ち遭遇.ERB） ------------------------------------------------


def akuoti_encounter(ctx: Ctx) -> None:
    """`@PASTIME_AKUOTI_ENCOUNTER`:4–28（:28 PASTIME_AKUOTI_EVENT は本文のみ → catalog）。"""
    from .battle.core import add_randchoose, choicecount, clear_randchoose, randchoose_f
    from .era import isqrt

    st = ctx.state
    local = 40 if st.time == 0 else 20  # :6–12（VARSET LOCAL の後）
    clear_randchoose(st)  # :14
    for cc in range(st.charanum):  # :15–21
        if cc == GameState.MASTER:
            continue
        if st.charas[cc].cflag[0] == 3 and _hole(ctx, cc):
            # DEVIATION: D4（使用者裁決 2026-10-02「防衛力が負なら 0」）：FLAG:852 < 0 の SQRT は原作 CodeEE
            # （reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs@SqrtMethod:1074–1080）、ここでは 0。
            sq = isqrt(st.flag[852]) if st.flag[852] >= 0 else 0
            if min(_rand(ctx, div(sq, 2) + 20), 100) < local:
                add_randchoose(st, cc)
    if choicecount(st) == 0:  # :23–24
        st.result[0] = 0
        return
    ctx.out.drawline()  # :26
    st.flag[111] = randchoose_f(st)  # :27
    _chinobun(ctx, "PASTIME_AKUOTI_EVENT")  # :28（:259 RETURN 0）
    st.result[0] = 0  # :28 の後で関数終端


# --- 街に出る（自由/PASTIME_街に出る.ERB） -----------------------------------------------------


_MACHI = ("ショッピングモール", "アミューズメント施設", "繁華街", "公園")


def _hip_word(local: int) -> str:
    """`IF LOCAL == 2 むちむちとした …`（外見／変身時外見によるヒップの形容）。"""
    return {2: "むちむちとした", 1: "豊満な", 0: "整った", 6: "尻肉が弾むほど豊満な", 5: "ボリュームたっぷりの"}.get(local, "小振りな")


def _appearance(ctx: Ctx) -> int:
    """`SIF CFLAG:1 == 0 / LOCAL = TALENT:外見 / SIF CFLAG:1 >= 1 / LOCAL = TALENT:変身時外見`。"""
    c = ctx.state.target_chara
    local = 0
    if c.cflag[1] == 0:
        local = _t(ctx, "外見")
    if c.cflag[1] >= 1:
        local = _t(ctx, "変身時外見")
    return local


def _exposure(ctx: Ctx, n: str, park: bool) -> bool:
    """:276–316（繁華街）／:377–415（公園）。どれかの分岐に入ったら True（ELSE の文は呼び出し側）。"""
    out = ctx.out
    c = ctx.state.target_chara
    inran = (_t(ctx, "淫乱") > 0 or _abl(ctx, "露出癖") > 2) and _t(ctx, "初心") < 1
    if _rand(ctx, 3) == 0 and _female(ctx):
        out.printl(f"突然、強風が吹いて{n}のスカートが捲れ上がり")
        if 300 <= c.cflag[42] < 400:
            out.printl(f"スカートに隠されていた{_item(ctx, c.cflag[42])}が衆目に晒されてしまった！")
        elif c.cflag[42] == 400:
            out.printl("触手にいじられ続ける秘所が衆目に晒されてしまった！")
        else:
            out.printl("スカートに隠されていた秘所が衆目に晒されてしまった！")
        if inran:
            out.printl("慌てた様子も見せずにスカートを抑えたがしっかり目にされたらしくスケベな視線を感じる。")
            out.printl(f"下着を見られてしまった{n}だったが")
            out.printl("特に気にもせず堂々とその場を立ち去った・・・")
        else:
            out.printl("慌ててスカートを抑えるも一瞬とは言えしっかり目にされたらしくスケベな視線を感じる。")
            out.printl(f"下着を見られてしまい顔を真赤にした{n}は")
            out.printl("足早にその場を立ち去った・・・")
        return True
    if _rand(ctx, 3) == 0 and (_male(ctx) and _hole(ctx)):
        if park:
            out.printl(f"突然、近くでよろめいたお年寄りが{n}の服を掴んで転倒し")
        else:
            out.printl(f"突然、近くでよろめいた酔っ払いが{n}の服を掴んで転倒し")
        if 300 <= c.cflag[42] < 400:
            out.printl(f"その下に隠されていた{_item(ctx, c.cflag[42])}が衆目に晒されてしまった！")
        elif c.cflag[42] == 400:
            out.printl("触手にいじられ続けるペニスとアナルが衆目に晒されてしまった！")
        else:
            out.printl("その下に隠されていた股間が衆目に晒されてしまった！")
        if park:
            if inran:
                out.printl("慌てた様子も見せずにお年寄りを助け起こしたが、その間にも周囲からスケベな視線を感じる。")
                out.printl(f"下着を見られてしまった{n}だったが")
                out.printl("特に気にもせずズリ落ちた服を整えると堂々とその場を立ち去った・・・")
            else:
                out.printl("慌てながらも先にお年寄りを助け起こしたが、その間にも周囲からスケベな視線を感じる。")
                out.printl(f"下着を見られてしまい顔を真赤にした{n}は")
                out.printl("涙目になりながらズリ落ちた服を整えると足早にその場を立ち去った・・・")
        else:
            if inran:
                out.printl("慌てた様子も見せずにズリ落ちた服を整えたがしっかり目にされたらしくスケベな視線を感じる。")
                out.printl(f"下着を見られてしまった{n}だったが")
                out.printl("特に気にもせず堂々とその場を立ち去った・・・")
            else:
                out.printl("慌ててズリ落ちた服を整えるも一瞬とは言えしっかり目にされたらしくスケベな視線を感じる。")
                out.printl(f"下着を見られてしまい顔を真赤にした{n}は")
                out.printl("足早にその場を立ち去った・・・")
        return True
    return False


def _bust_glance(ctx: Ctx, n: str) -> None:
    """:264–273／:366–375：`RAND:3 == 0 && ISHOLE() == 1 && TALENT:巨乳 > 0` のバスト視線。"""
    out = ctx.out
    if _rand(ctx, 3) == 0 and _hole(ctx) and _t(ctx, "巨乳") > 0:
        out.printl(f"すれ違う男共の視線が{n}の服の上からでもわかる")
        out.print("ダイナミックな大きさの" if _t(ctx, "巨乳") > 2 else "豊満な")
        out.printl("バストにささっている。")
        out.printl()


def _skirt_flutter(ctx: Ctx, n: str) -> None:
    """:119–133 ／ :170–184（ダンスゲーム・ボーリング）。"""
    out = ctx.out
    if _male(ctx):
        out.printl("熱中のあまり激しく身体を動かしすぎてその度にシャツが翻り")
    else:
        out.printl("熱中のあまり激しく身体を動かしすぎてその度にスカートが翻り")
    if _male(ctx):
        out.printl("チラチラと素肌が見えてしまっているのだが")
    else:
        out.printl("チラチラと下着が見えてしまっているのだが")
    out.printl(f"集中している{n}その事に気がついていない。")


def machi(ctx: Ctx, arg: int) -> InputGen:
    """`@PASTIME_街に出る, ARG`:1–429（ARG = -1 で行き先を INPUT）。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    out.printl("街に出る")  # :4–5
    out.printl()
    _chinobun(ctx, "PASTIME_FASHION")  # :7
    out.printw()  # :9–12
    out.printl()
    n = _name(ctx)
    out.printl(f"街に出た{n}の行き先は・・・")
    out.printl()
    if arg == -1:  # :13–24
        for i, s in enumerate(_MACHI):
            out.printl(f"[{i}]{s}")
        out.printl()
        out.drawline()
        result = yield
    else:
        result = arg
    st.result[0] = result
    while True:  # :25–38
        out.printl()
        out.drawline()
        if 0 <= result <= 3:
            out.printl(_MACHI[result])
            break
        out.printl("正しい値を入力してください")
        result = yield  # GOTO INPUT_LOOP
        st.result[0] = result
    local = result  # :39–43
    out.printl()
    c.cflag[101] = local + 5
    out.printl()  # :46–48
    _dot_after(ctx, 1)
    out.printl()
    mokuteki = ""
    if result == 0:  # :49–109
        mokuteki = "ショッピングモール"
        akuoti_encounter(ctx)  # :52
        if _rand(ctx, 2) == 0:
            out.printl(f"ショッピングモールに訪れた{n}は")
            if _rand(ctx, 2) == 0 and (_female(ctx) or (_t(ctx, "淫乱") > 0 and _t(ctx, "初心") <= 0)):
                out.printl("ランジェリーショップでウインドウショッピングを楽しんでいる。")
            else:
                out.printl("ブティックでウインドウショッピングを楽しんでいる。")
            out.printl()
            out.printl("何点か気に入った服を手に取ると、店員を呼び止め試着室へ案内して貰った。")
            out.printl(f"試着して問題がないことを確認した{n}は何着かお買い上げすると")
            out.printl("満足げな顔で次の店を見に行くようだ・・・")
        else:
            out.printl(f"ショッピングモールに訪れた{n}は")
            out.printl("店舗を回ってウインドウショッピングを楽しんでいる。")
            out.printl()
            if _rand(ctx, 3) == 0 and _girly(ctx):
                if _t(ctx, "男の娘") > 0:
                    out.printl("やけに押しの強い店員に絡まれて適当に相槌を打っていると、")
                    out.printl("いつの間にかおすすめの服を試着することになっていた。")
                    out.printl(f"しかも案の定、{n}は女の子だと思われていたようで、")
                    out.printl("かわいらしいワンピースを流されるままに着てしまった・・・")
                    out.printw()
                    out.printl(f"試着室を出た{n}に似合いますよとまくしたてると、")
                    out.printl("口を挟む暇もなく、店員は呼び出しを受けて別の階へと駆け出していった。")
                    out.printl(f"服をどこに返せばいいのか聞いておこうと、{n}は反射的に店員を追いかける。")
                    out.printl("せめて着替えてから追い掛ければ良かったと気付いたのは、走り出したあとだった・・・")
                    out.printl()
                out.printl(f"階を移動しようとエスカレーターへ向かう{n}の後ろに")
                out.printl("挙動不審な男がぴたりと着いて来ている。")
                out.printl(f"どうやら{n}のスカートの中を覗こうと企んでいるようだ。")
                out.printl()
                if _rand(ctx, 3) == 0:
                    out.printl(f"後を着いてくる気配に気がついた{n}は")
                    out.printl("足早に立ち去り不審者を撒く事に成功した…")
                else:
                    out.printl(f"しかし、{n}は不審者に気が付かずエスカレーターに乗ってしまった。")
                    if _rand(ctx, 2) == 0:
                        out.printl(f"不審者は小型カメラで{n}のスカートの中を撮影している。")
                    else:
                        out.printl(f"不審者はビデオカメラで{n}のスカートの中を撮影している。")
                    if _rand(ctx, 2) == 0:
                        out.printl(f"降りる直前で不審者に気がついた{n}は")
                        out.printl("顔を真赤にしてその場を立ち去っていった・・・")
                    else:
                        out.printl(f"結局、{n}は降りてからも暫く不審者に気が付かず")
                        out.printl("スカートの中を散々撮影されてしまった・・・")
            else:
                out.printl(f"{n}は人気のブランドやお気に入りの店で季節物の新作などに目を通しているが")
                out.printl("次々と気になる服に目移りしどれを買おうか悩んでいる・・・")
    elif result == 1:  # :110–232
        if _rand(ctx, 3) == 0:
            mokuteki = "ゲームセンター"
            out.print(f"ゲームセンターに訪れた{n}は")
            if _rand(ctx, 3) == 0 and _hole(ctx):
                out.printl("ダンスゲームを楽しんでいる。")
                out.printl()
                _skirt_flutter(ctx, n)
                out.printl(f"一通り楽しんだ{n}は筐体から離れ移動していった・・・")
            else:
                out.printl("クレーンゲームを楽しんでいる。")
                out.printl()
                if _rand(ctx, 3) == 0 and _hole(ctx):
                    local = _appearance(ctx)
                    out.printl(f"すれ違う男共の視線が{n}の無防備に晒された")
                    out.print(_hip_word(local))
                    out.printl("ヒップにささっているが")
                    out.printl(f"熱中のあまり{n}は気付いていない。")
                    out.printl()
                out.printl(f"{n}は一目見て気に入ったキャラクターグッズを狙っているが")
                out.printl("あと一歩のところで上手く行かず、コインを何枚も吸い込まれている・・・")
        elif _rand(ctx, 2) == 0:
            mokuteki = "ボーリング"
            out.print(f"ボーリング場に訪れた{n}は")
            out.printl("ボーリングを楽しんでいる。")
            if _rand(ctx, 3) == 0 and _hole(ctx):
                out.printl()
                _skirt_flutter(ctx, n)
                out.printl()
            out.printl(f"{n}の投げたボールは")
            if _rand(ctx, 3) == 0:
                out.printl("綺麗にレーンの真ん中を転がっていくと全てのピンをなぎ倒した。")
                out.printl("見事なストライクだ。")
            else:
                out.printl("レーンの端に吸い寄せられるようによっていくと側溝に落ち込んでしまった。")
                out.printl("残念ながらガーターだ。")
            out.printl()
            out.printl(f"１ゲーム終えた{n}は一息しようとレーンから離れていった・・・")
        else:
            mokuteki = "映画館"
            out.print(f"映画館に訪れた{n}は")
            if _rand(ctx, 6) == 0:
                out.printl("サメ映画を観賞している。")
                out.printl()
                out.printl("間違いなくクソ映画だ。")
            elif _rand(ctx, 5) == 0:
                out.printl("ゾンビ映画を観賞している。")
                out.printl()
                out.printl("間違いなくクソ映画だ。")
            elif _rand(ctx, 4) == 0:
                out.printl("アメコミヒーロー映画を観賞している。")
                out.printl()
                out.printl("戦いの参考にならないかと思い、その目は真剣そのものだ。")
            elif _rand(ctx, 3) == 0:
                out.printl("パニックホラー映画を観賞している。")
                out.printl()
                out.printl(f"{n}は悲鳴を堪えるのに必死になっている。")
            elif _rand(ctx, 2) == 0:
                out.printl("コメディ映画を観賞している。")
                out.printl()
                out.printl(f"{n}は笑いを堪えるのに必死になっている。")
            else:
                out.printl("恋愛映画を観賞している。")
                out.printl()
                if _female(ctx):
                    out.printl("スクリーンの中のヒロインに自己投影してしまいうっとりしている。")
                elif _rand(ctx, 2) == 0 and _t(ctx, "男の娘") > 0:
                    out.printl("いつのまにかスクリーンの中のヒロインに自己投影していた自分に気付いて戸惑っている。")
                else:
                    out.printl("スクリーンの中のヒロインに見惚れてしまいうっとりしている。")
            out.printl(f"観賞を終えた{n}は余韻に浸りつつシアターを後にした・・・")
    elif result == 2:  # :233–331
        mokuteki = "繁華街"
        out.printl(f"繁華街に訪れた{n}は、")
        real, age, mage = _base(ctx, "実年齢"), _base(ctx, "年齢"), _maxbase(ctx, "年齢")
        cf1 = c.cflag[1]
        ts_loli = (real >= 20 or age >= 20) and _female(ctx) and _t(ctx, "変身時ＴＳ") > 0 and cf1 > 0 and mage < 20
        # :237 `TIME > 0 && (…) || 実年齢 >= 20 && (…)` は同順位・左結合で ((TIME > 0 && TSロリ) || 実年齢 >= 20) && (見た目未成年)
        if ((st.time > 0 and ts_loli) or real >= 20) and ((cf1 == 0 and age < 20) or (cf1 > 0 and mage < 20)):
            out.printl("日頃の疲れを癒すべく居酒屋に立ち寄ったが")
            out.printl("未成年に酒を飲ませる訳にはいかないと追い払われた。")
            out.printl(f"{n}は実際には{real}歳だが")
            if cf1 > 0 and mage < 20:
                out.printl(f"今は誰がどう見ても{mage}歳のそれである。")
            elif cf1 == 0 and age < 20:
                out.printl(f"誰がどう見ても{age}歳のそれである。")
            if ts_loli:
                out.printl(f"原因は不明だが{n}は月に数回、変身が解けなくなることがあった。")
                out.printl("一晩経てば変身は解けるので大して気にも留めていなかったが")
                out.printl("運悪くどうしても酒が飲みたい今夜にそれが当たってしまった。")
            out.printl("店の前で抗議しようかとも考えたが、この見た目で成人だと言い張るには無理があると頭を冷やして諦めた。")
        if st.time > 0 and real < 20 and age < 20 and mage >= 20 and cf1 > 0:  # :254–259
            out.printl(f"居酒屋の多い通りを{n}がうろうろしている。")
            out.printl(f"大人の世界に興味を持った{n}はお酒にも興味を持っていた。")
            out.printl("しかし変身したとは言え元は未成年であり、それは許されるのかと逡巡している。")
            out.printl("やがて周囲の奇異の目に気付き、足早にその場を立ち去った…")
        out.printw()  # :260
        if _rand(ctx, 2) == 0:  # :261–326
            out.printl("特に当てもなく通りを散策している。")
            out.printl()
            _bust_glance(ctx, n)
            if not _exposure(ctx, n, park=False):
                out.printl("しばらくして喉が乾いてきたのか、喫茶店にでも入ろうかと悩んでいる・・・")
        else:
            out.printl("話題の洋菓子店を訪れている。")
            out.printl()
            out.printl(f"行列に並んで待っていると、暫くして{n}の番となった。")
            out.printl("噂から想像した以上の美味しさで待った甲斐があったと満足そうだ。")
            out.printl(f"甘いお菓子に舌鼓を打った{n}は幸福そうな顔で店を後にした・・・")
        if pastime_sake_nanpa(ctx) > 0 and st.time > 0:  # :327–331
            message_pastime_sake_nanpa(ctx, arg)
            st.result[0] = 0
            return
    elif result == 3:  # :332–419
        mokuteki = "公園"
        if _rand(ctx, 3) == 0:
            out.printl(f"公園に訪れた{n}は")
            out.printl("据え付けられたベンチに座って日向ぼっこをしている。")
            out.printl()
            out.printl("ポカポカとした暖かな日差しが心地よい・・・")
            out.printw()
        elif _rand(ctx, 2) == 0:
            out.printl(f"公園に訪れた{n}は")
            out.printl("どこかのんびりできそうな場所を探している。")
            out.printl()
            if _rand(ctx, 4) == 0:
                out.printl("いい場所はないかと探していると数匹の子猫達にじゃれつかれた。")
                out.printl("野良猫のようだが随分人懐っこい。")
                out.printl("もふもふの毛玉達に癒やされる・・・")
            elif _rand(ctx, 3) == 0:
                out.printl("いい場所はないかと探していると首輪をした小型犬にじゃれつかれた。")
                out.printl("よく躾られているらしくお手などちょっとした芸にも応えてくれた。")
                out.printl("程なくして飼い主が来ると謝罪を述べながら引き連れていった・・・")
            elif _rand(ctx, 2) == 0:
                out.printl("いい場所はないかと探していると首輪をした大型犬にじゃれつかれた。")
                out.printl("尻尾を振り回しながら体重を載せて抱きついて顔を舐めてくる。")
                out.printl(f"飼い主が来て引き離すまで{n}は散々舐め回されてしまった・・・")
            else:
                out.printl("いい場所はないかと探していると目の前をカルガモの親子が横切った。")
                out.printl("よちよち歩きで親鳥に着いていく雛が可愛らしい。")
                out.printl(f"{n}はカルガモ親子のお引越しをその場で見届けた・・・")
            out.printw()
        else:
            out.printl(f"公園に訪れた{n}は")
            out.printl("池に沿うように設けられた遊歩道で散歩している。")
            out.printl()
            _bust_glance(ctx, n)
            if not _exposure(ctx, n, park=True):
                out.printl("木陰から漏れる日差しとそよ風が心地よい・・・")
    out.printw()  # :421
    if pastime_nanpa(ctx) > 0:  # :423–428
        message_pastime_nanpa(ctx, arg)
    else:
        out.printl(f"{n}は、{mokuteki}を満喫してきたようだ。")
    st.result[0] = 0  # :429


# --- 遠出する（自由/PASTIME_遠出する.ERB） -----------------------------------------------------


_TOODE = ("動物園", "水族館", "遊園地", "植物園", "ライブ", "ウォーターパーク", "海辺", "温泉")
_TOODE_FUNC = ("MESSAGE_PASTIME_Zoo", "MESSAGE_PASTIME_Aquarium", "MESSAGE_PASTIME_AmusementPark",
               "MESSAGE_PASTIME_BotanicalGarden", "MESSAGE_PASTIME_LiveShow", "MESSAGE_PASTIME_WaterPark",
               "MESSAGE_PASTIME_BeachSide", "MESSAGE_PASTIME_Spa")


def toode(ctx: Ctx, arg: int) -> InputGen:
    """`@PASTIME_遠出する, ARG`:1–108。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    out.printl("遠出する")
    out.printl()
    _chinobun(ctx, "PASTIME_FASHION")  # :7
    out.printw()
    out.printl()
    n = _name(ctx)
    out.printl(f"電車を待つ{n}の行き先は・・・")
    out.printl()
    if arg == -1:  # :13–31
        out.print("[0]動物園　　　　　　　　")
        out.print("[1]水族館　　　　　　　　")
        out.printl()
        out.print("[2]遊園地　　　　　　　　")
        out.print("[3]植物園　　　　　　　　")
        out.printl()
        out.print("[4]ライブ　　　　　　　　")
        out.print("[5]ウォーターパーク　　　")
        out.printl()
        out.print("[6]海辺　　　　　　　　　")
        out.print("[7]温泉　　　　　　　　　")
        out.printl()
        out.printl()
        out.drawline()
        result = yield
    else:
        result = arg
    st.result[0] = result
    while True:  # :35–56
        out.printl()
        out.drawline()
        if 0 <= result <= 7:
            out.printl(_TOODE[result])
            break
        out.printl("正しい値を入力してください")
        result = yield
        st.result[0] = result
    local = result
    out.printl()
    c.cflag[101] = local + 9  # :61
    out.printl()
    _dot_after(ctx, 1)
    out.printl()
    if (yield from pastime_chikan(ctx, arg)) == 0:  # :67–68
        _chinobun(ctx, _TOODE_FUNC[local])  # :69–93
        if pastime_nanpa(ctx) > 0:  # :97–100
            message_pastime_nanpa(ctx, arg)
        elif _rand(ctx, 100) > div(st.flag[852], 100):  # :102–103
            yield from inkioukyu(ctx, 0)
        else:
            out.printl(f"{n}は、{_TOODE[local]}を楽しんできたようだ。")
            out.printw()
    st.result[0] = 0  # 関数終端


# --- 運動する（自由/PASTIME_運動する.ERB） -----------------------------------------------------


_UNDOU = ("運動公園", "フィットネスクラブ", "マッサージサロン", "プール")


def undou(ctx: Ctx, arg: int = -1) -> InputGen:
    """`@PASTIME_運動する, ARG=-1`:1–74。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    eroevent = 0  # :5
    out.printl("運動する")
    out.printl()
    _chinobun(ctx, "PASTIME_FASHION")  # :10
    out.printw()
    out.printl()
    n = _name(ctx)
    out.printl(f"身体を動かそうと思った{n}の行き先は・・・")
    out.printl()
    if arg == -1:
        for i, s in enumerate(_UNDOU):
            out.printl(f"[{i}]{s}")
        out.printl()
        out.drawline()
        result = yield
    else:
        result = arg
    st.result[0] = result
    while True:  # :28–42
        out.printl()
        out.drawline()
        if 0 <= result <= 3:
            out.printl(_UNDOU[result])
            break
        out.printl("正しい値を入力してください")
        result = yield
        st.result[0] = result
    local = result
    out.printl()
    c.cflag[101] = local + 17  # :47
    out.printl()
    _dot_after(ctx, 1)
    out.printl()
    if local == 0:  # :53–66
        yield from sports_park(ctx)
    elif local == 1:
        _chinobun(ctx, "MESSAGE_PASTIME_FitnessClub")
        eroevent = st.result[0]  # :59 EROEVENT = RESULT（RETURN EROEVENT）
    elif local == 2:
        _chinobun(ctx, "MESSAGE_PASTIME_MassageSalon")
    else:
        _chinobun(ctx, "MESSAGE_PASTIME_Pool")
    if pastime_nanpa(ctx) > 0 and eroevent < 1:  # :69–74
        message_pastime_nanpa(ctx, arg)
    else:
        out.printl(f"{n}は、{_UNDOU[local]}で身体を存分に動かしたようだ。")
    st.result[0] = 0


def _bust_word(ctx: Ctx, rand_taware: bool, nonbig: str, otokonoko: str, plain: str, small: str, flat: str) -> str:
    """運動公園／プールのバスト形容（`TALENT:巨乳 > 2 … ELSE 下着が必要ないくらい未熟な`）。rand_taware は
    `TALENT:巨乳 > 0 && RAND:2 == 0` の RAND を引く形かどうか。"""
    k = _t(ctx, "巨乳")
    if k > 2:
        return "ダイナミックな大きさの"
    if k > 1:
        return nonbig
    if k > 0 and (not rand_taware or _rand(ctx, 2) == 0):
        return "たわわに実った"
    if k > 0:
        return "豊満な"
    if otokonoko and _t(ctx, "男の娘") > 0:
        return otokonoko
    if k == 0 and _t(ctx, "貧乳") == 0:
        return plain
    if _t(ctx, "貧乳") < 2:
        return small
    return flat


def sports_park(ctx: Ctx) -> InputGen:
    """`@MESSAGE_PASTIME_SportsPark`:79–308（:94 PASTIME_KOKURARE に INPUT があるので Python）。RETURN EROEVENT（静的・代入なし → 0）。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    t = lambda k: _t(ctx, k)  # noqa: E731
    n = _name(ctx)
    out.print(f"運動公園に訪れた{n}は")  # :89–91
    out.printl("身動きしやすい格好に着替えランニングを始めた。")
    out.printl()
    if t("交際相手") == 0:  # :93–95
        yield from kokurare(ctx)
    k = t("巨乳")
    if _rand(ctx, 3) == 0 and _hole(ctx) and k > 0:  # :97–111
        out.printl(f"すれ違う男共の視線が{n}の服の上からでもわかる")
        if k > 2:
            out.print("ダイナミックな大きさの")
        elif k > 1:
            out.print("上下に揺れる立派な")
        elif k > 0 and _rand(ctx, 2) == 0:
            out.print("たわわに実った")
        else:
            out.print("豊満な")
        out.printl("バストにささっている。")
        out.printl()
    elif _rand(ctx, 2) == 0 and _hole(ctx):  # :112–133
        out.printl(f"すれ違う男共の視線が{n}のバストにささっている。")
        out.print("汗に濡れたＴシャツから")
        out.print(_bust_word(ctx, True, "上下に揺れる立派な", "ぺたんこながらも柔らかな", "わずかに揺れる程よい", "控えめに膨らんだ",
                             "下着が必要ないくらい未熟な"))
        out.printl("胸が透けて見えている。")
        out.printl()
    if _rand(ctx, 2) == 0 and t("Ｂ敏感") > 0:  # :135–138
        out.printl(f"{n}の乳首は他人に比べて敏感で、")
        out.printl("走るリズムに合わせて甘い快感を与えていた。")
    if _rand(ctx, 2) == 0 and t("淫乳") > 0 and t("初心") < 1:  # :139–143
        out.printl(f"{n}の息遣いは荒く苦しそうだが口元はにやけていた。")
        out.printl(f"{n}の乳首は度重なる淫闘で開発され、")
        out.printl(f"一歩走るごとにこすれる乳首が{n}の脳の快楽中枢を刺激していた。")
    if _rand(ctx, 2) == 0 and t("母乳体質") > 0:  # :144–149
        out.printl(f"{n}の乳首は擦れる刺激だけで母乳が出るようになってしまっていた。")
        out.printl("誰かに吸われているわけでもなく、性的興奮があるわけでもないのに、")
        out.printl(f"走るごとにこすれる乳首が{n}のブラを母乳で濡らしていく。")
        out.printl(f"すれ違う男の視線を感じて{n}は頬を赤く染めた。")
    out.printw()  # :150
    if _rand(ctx, 4) == 0 and _hole(ctx) and st.time > 0:  # :152–243 夜の触手
        _stray_tentacles(ctx, n)
    out.printw()  # :244
    if _rand(ctx, 3) == 0 and _hole(ctx) and t("巨乳") > 0:  # :247–277
        if _rand(ctx, 2) == 0:
            out.printl(f"走り終えた{n}は息も絶え絶えに")
            out.printl("膝に手を当てて屈みながら休憩している・・・")
            out.print("両腕に挟まれた")
        else:
            out.printl(f"走り終えた{n}は息も絶え絶えに")
            out.printl("芝生に大の字になって休憩している・・・")
            out.print("呼吸に合わせて上下する")
        k = t("巨乳")
        if k > 2:
            out.print("ダイナミックな大きさの")
        elif k > 1:
            out.print("立派な")
        elif k > 0 and _rand(ctx, 2) == 0:
            out.print("たわわに実った")
        else:
            out.print("豊満な")
        if _rand(ctx, 2) == 0:
            out.printl("胸が、その谷間を強調している。")
        else:
            out.printl("胸が、その双丘の存在感を強調している。")
        if t("淫乱") > 0:
            out.printl(f"{n}はその双丘を見せつけるようにして")
            out.printl("男たちの欲情した目線を楽しんでいる。")
        else:
            out.printl("通り過ぎる男たちの好色な目がその双丘に釘付けになっていることに")
            out.printl(f"{n}は気付いていない。")
    elif _rand(ctx, 3) == 0 and t("男の娘") > 0:  # :278–294
        if _rand(ctx, 2) == 0:
            out.printl(f"走り終えた{n}は息も絶え絶えに")
            out.printl("膝に手を当てて屈みながら休憩している・・・")
            out.printl("両腕の間から覗く汗塗れのぺたんこな胸が、フェミニンな身体つきを強調している。")
        else:
            out.printl(f"走り終えた{n}は息も絶え絶えに")
            out.printl("芝生に大の字になって休憩している・・・")
            out.printl("呼吸に合わせて上下する汗塗れのぺたんこな胸が、フェミニンな身体つきを強調している。")
        if t("淫乱") > 0:
            out.printl(f"{n}は汗に濡れそぼった肢体を見せつけるようにして")
            out.printl("男たちの欲情した目線を楽しんでいる。")
        else:
            out.printl("通り過ぎる男たちの好色な目が汗に濡れそぼった肢体に釘付けになっていることに")
            out.printl(f"{n}は気付いていない。")
    else:  # :295–299
        out.printw()
        out.printl(f"走り終えた{n}はいい汗をかけたようで")
        out.printl("心地良い疲労感を感じながら休憩している・・・")
    out.printw()  # :300
    c.cflag[_ts_count(ctx, 330, 331)] += 1  # :303–307
    st.result[0] = 0  # :308 RETURN EROEVENT（:80 `#DIM EROEVENT = 0` は代入されない）


def _stray_tentacles(ctx: Ctx, n: str) -> None:
    """運動公園:152–243 夜の捨て犬（仔触手）。"""
    out = ctx.out
    t = lambda k: _t(ctx, k)  # noqa: E731
    out.printl("捨て犬")
    out.printl("")
    out.printl(f"夜の運動公園で{n}が走っていると物陰から仔犬のような鳴き声が聞こえてきた。")
    out.printl("近寄ってみると段ボール箱が捨てられており、中には産まれたばかりの桃色肌の仔犬が数匹……")
    out.printl("仔犬のようなそれをよく見ると四本の足と尻尾は醜く蠢く触手だった。")
    out.printl(f"{n}は思わず身構えたが、この程度の仔触手なら子供でも叩き潰せるほど無力だ。")
    out.print(f"{n}は")
    lewd = (t("淫乱") > 0 or _abl(ctx, "自慰中毒") > 2) and t("初心") < 1
    if t("母乳体質") > 0:  # :161–178
        out.printl("ふと自分が母乳体質であることを思い出した。")
        out.printl(f"これは敵であるが産まれたばかりの無力さが{n}の母性本能を呼び起こす。")
    elif lewd:
        out.printl("ふと邪まな考えが浮かんだ。")
        out.printl("これほど無力な触手なら自慰グッズと同じなのではないかと。")
        out.printl("人としても触手と戦う者としても、最低のひらめきかも知れない。")
    elif t("触手の虜") > 0 or t("寄生") > 0:
        out.printl("なぜか自分が助けねばという使命感に駆られた。")
        out.print("その原因が")
        if t("触手の虜") > 0:
            out.print("触手の虜になってしまっているせいだと")
        elif t("寄生") > 0:
            out.print("触手に寄生されているせいだと")
        out.printl("理性では反論出来ても")
        out.printl(f"産まれたばかりの無力さが{n}の母性本能を呼び起こす。")
    out.printl("試しに人差し指を仔触手犬の口に近づけると、母犬のおっぱいを吸うように人差し指を吸っていた。")
    if t("男の娘") > 0:
        out.printl("女の子扱いばかりされる生活の中で、心の内に育っていた倒錯した好奇心が頭をもたげる……")
    if _male(ctx):
        out.printl(f"{n}は周囲に人影のないことを確認すると、シャツをまくり上げ")
    else:
        out.printl(f"{n}は周囲に人影のないことを確認すると、シャツをまくり上げブラを緩め")
    k = t("巨乳")  # :189–203
    if k > 2:
        out.print("ダイナミックな大きさの")
    elif k > 1:
        out.print("たわわな")
    elif k > 0:
        out.print("豊満な")
    elif t("男の娘") > 0:
        out.print("ぺたんこな")
    elif k == 0 and t("貧乳") == 0:
        out.print("程よい大きさの")
    elif t("貧乳") < 2:
        out.print("控えめな")
    else:
        out.print("未熟な")
    out.printl("胸を仔触手犬の口に近づけると、ようやく母乳にありつけたとばかりに物凄い吸引力で吸い付いた。")
    out.printl(f"{n}はその吸引力に驚いて離そうとしたが、")
    out.printl("仔触手犬が吸い付いたまま離れようとしないので")
    out.printl("その生命力の強さに気圧されて諦めた・・・")
    out.printw()
    milk = t("母乳体質") > 0
    if lewd:  # :209–227
        if milk:
            out.printl(f"母乳を与え始めてわずかのうちに、{n}の淫乳は性感の火を灯し、")
            out.printl("か弱い命を救うためではなく快楽に耽った結果として乳を噴き出していた。")
        else:
            out.printl(f"悪戯心で乳を吸わせ始めてわずかのうちに、{n}の淫乳は性感の火を灯していた。")
        out.printl("片方の乳首は二匹の、もう片方は三匹の仔触手犬が競うように乳首を奪い合っている。")
        out.printl(f"その不規則な刺激といざ{'母乳' if milk else '獲物'}にありつけた本気の乳吸いは")
        out.printl(f"{n}をさらなる{'噴乳' if milk else '悦楽'}の高みへと押し上げる。")
        if _male(ctx):
            out.printl("片腕で仔触手犬たちを抱きかかえながら、もう片方の手は疼くお尻の中心に伸びていた。")
        else:
            out.printl("片腕で仔触手犬たちを抱きかかえながら、もう片方の手は濡れた股間に伸びていた。")
        out.printl("もはや母性本能など消え去り、性玩具としか見ていない邪まな乳狂いぶりだった。")
        out.printl()
    elif t("触手の虜") > 0 or t("寄生") > 0:  # :228–239
        if milk:
            out.printl(f"母乳は順調に出始め慣れてきた{n}は")
            out.printl("もう一匹を空いている胸にあてがい、二匹ずつ同時に授乳した。")
        else:
            out.printl(f"母乳など出るはずもない{n}だったが")
            out.printl("もう一匹を空いている胸にあてがい、二匹ずつ同時に授乳ごっこをした。")
        out.printl(f"{n}は生命の尊さと多幸感を感じ取り、")
        out.printl("その異常さに気付きながらも仔触手犬たちに癒された。")
        out.printl()
    out.printl(f"{n}は今この場で処理しようか悩んでいたが")
    out.printl("触手生物を研究している機関を思い出し、そこへ連絡することにした。")
    out.printl(f"情けをかけたつもりか、死よりも残酷な仕打ちを与えたのか、{n}にも分からなかった…")


# --- 告られ（自由/PASTIME_告られ.ERB） ----------------------------------------------------------


def kokurare(ctx: Ctx) -> InputGen:
    """`@PASTIME_KOKURARE`:1–88。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    t = lambda k: _t(ctx, k)  # noqa: E731
    n = _name(ctx)
    cf1, c330, c331 = c.cflag[1], c.cflag[330], c.cflag[331]
    if ((t("交際相手") == 0 and cf1 < 1 and mod(c330, 15) == 0 and c330 > 14)
            or (t("交際相手") == 0 and cf1 > 0 and mod(c331, 15) == 0 and c331 > 14)) and _hole(ctx):  # :12
        out.printl(f"{n}は親しいランナーに、恋人として付き合ってほしい、と告白された。")
        if _female(ctx) and t("変身時ＴＳ") > 0 and cf1 > 0:
            if t("女体受容") > 0:
                out.printl(f"女としての身体に馴染んだ{n}は、ごく当たり前のように赤面している…。")
            else:
                out.printl(f"女体化した{n}は男性から性的な視線を受けたことは何度もあったが、")
                out.printl("まさか告白されるほど魅力的に見えていたのかと言う、驚きと嬉しさと恥ずかしさとが困惑を生み、")
                out.printl("耳まで真っ赤になっている…。")
        elif t("男の娘") > 0:
            out.printl(f"{n}は自分がオトコには見えないことは嫌でも自覚させられていたし、")
            out.printl("勝手に勘違いした男性から性的な視線を受けたことは何度もあったが、")
            out.printl("まさか告白されるほど魅力的に見えていたのかと言う、驚きと嬉しさと恥ずかしさとが困惑を生み、")
            out.printl("耳まで真っ赤になっている…。")
            out.printw()
            out.printl("こんな見た目でも女ではなくオトコだと言っても口だけではわかって貰えず、")
            out.printl("思いきって股間の膨らみを見せるとようやく信じては貰えたが…。")
            out.printl("それでも構わない、彼女になって欲しい、と告白してきたランナーが諦める様子はない。")
            out.printl(f"ますます真っ赤になった{n}は激しく鼓動する胸を抑えている…。")
        elif _male(ctx):
            out.printl(f"{n}が親しい友人と思っていたランナーは随分積極的だったが、")
            out.printl("オトコ同士なのだからこういう時が来るなどとはまったく予想はしていなかった。")
            out.printl(f"返答はどうあれ、面と向かっての告白は{n}の頬を赤く染めている…。")
        else:
            out.printl(f"{n}が親しい友人と思っていたランナーは随分積極的だったので、")
            out.printl("望むと望まざるに関わらずいつかこういう時が来るのではと微かに予想はしていたのだが、")
            out.printl(f"返答はどうあれ、面と向かっての告白は{n}の頬を赤く染めている…。")
        out.printw()
        out.printl("[0]断る")
        out.printl("[1]付き合う")
        out.printl()
        while True:  # :46–74
            result = yield
            st.result[0] = result
            if result == 0:
                out.print(f"{n}は")
                if _exp(ctx, "精液経験") > 100:
                    out.printl("誰か一人に愛されるような綺麗なカラダではない、と自嘲気味に断った。")
                elif _rand(ctx, 2) == 0:
                    out.printl("自分と付き合えば不幸になるかもしれない、と茶化しながら断った。")
                else:
                    out.printl("自分には恋人よりも大切な使命があるから、と悲しそうに断った。")
                break
            if result == 1:
                out.print(f"{n}は")
                if t("淫乱") > 0 and t("初心") < 1:
                    out.printl("触手や市民に犯され尽くし、時に使命を忘れ快楽に溺れる自分の本性を、")
                    out.printl("この純な男性が知ったら一体どんな顔をするだろうと想像し興奮しながらＯＫした。")
                elif _exp(ctx, "被姦経験") > 100:
                    out.printl("触手や市民に犯され抜いた身体で純粋な愛を注がれて良いのか、と目に涙を浮かべた。")
                elif _rand(ctx, 2) == 0:
                    out.printl("触手や市民に穢された身体であるとこの人に知られたら、")
                    out.printl("どんな顔をされるかと不安に駆られながらも、愛される喜びを肯定した。")
                else:
                    out.printl("告白を受け止め、この人の為に強くなれると、誓いを新たにした。")
                c.talent[ctx.data.index_of("TALENT", "交際相手")] = 2  # :70
                break
            out.printl("正しい値を入力してください")
    elif (cf1 < 1 and c330 == 13) or (cf1 > 0 and c331 == 13):  # :75–87
        out.print("友人のランナーと連絡先を交換した。")
    elif (cf1 < 1 and c330 > 10) or (cf1 > 0 and c331 > 10):
        out.print("友人のランナーとダイエット論について語り合った。")
    elif (cf1 < 1 and c330 > 8) or (cf1 > 0 and c331 > 8):
        out.print("知り合いのランナーと世間話しながら並走した。")
    elif (cf1 < 1 and c330 > 6) or (cf1 > 0 and c331 > 6):
        out.print("知り合いのランナーと少しの間、並走した。")
    elif (cf1 < 1 and c330 > 4) or (cf1 > 0 and c331 > 4):
        out.print("顔なじみのランナーを挨拶を交わした。")
    elif (cf1 < 1 and c330 > 2) or (cf1 > 0 and c331 > 2):
        out.print("顔なじみのランナーと会釈をした。")
    out.print("")  # :88 PRINT（空）
    out.printw()
    st.result[0] = 0


# --- 淫気応急（自由/PASTIME_淫気応急.ERB） -----------------------------------------------------


def inkioukyu(ctx: Ctx, arg: int = 0) -> InputGen:
    """`@PASTIME_INKIOKYU, ARG`:1–400。"""
    from .battle.cloth import cloth_no_inner, costume_name

    st, out = ctx.state, ctx.out
    c = st.target_chara
    t = lambda k: _t(ctx, k)  # noqa: E731
    shojo = 0  # :7–8
    s_sei = 0
    if not _hole(ctx):  # :11–12
        st.result[0] = 0
        return
    n = _name(ctx)
    for s in ("淫気─応急処置─", "",
              f"物陰から淫気を感じとった{n}が用心深く探ると、", "淫気に浸された男がうずくまっていた。",
              "助けてくれ…死にたくない…といいながら陰茎をこすり上げている。", "",
              "通常、淫気に侵された人間は猛烈な性欲に支配されるが、", "性欲の強すぎる男性は触手に成り果ててしまうケースも多い。",
              "政府公認の応急処置方法は性欲の発散であり、自慰より性交の方が最も効果的とされる。", "",
              "淫気浸食患者のフリをして女性に暴行する事件も起こっているが、",
              f"{n}の見つけた男は触手になる恐怖と戦いながら自慰をしているように見えた。"):
        out.printl(s)
    if _male(ctx):  # :27–28
        out.printl("男同士での行為に多少の抵抗はあるが、まったく経験がないわけではない。")
    out.printl("ましてや善良な一市民が苦しんでいるのを見捨てられる訳がない。")
    out.printl(f"意を決して{n}は男に、もう大丈夫です必ず助かりますよ、と声をかけ、")
    out.printl("これは必要な応急処置だからと心の中で言い訳をしながら")
    if _rand(ctx, 7) == 0 and t("巨乳") > 0:  # :33–65
        out.print("パイズリ")
        bui, bui_s = 7, "双丘"
    elif _rand(ctx, 6) == 0:
        out.print("フェラ")
        bui, bui_s = 6, "顔"
    elif _rand(ctx, 5) == 0:
        out.print("尻コキ")
        bui, bui_s = 5, "尻肉"
    elif _rand(ctx, 4) == 0:
        out.print("足コキ")
        bui, bui_s = 4, "脚"
    elif _rand(ctx, 3) == 0:
        out.print("下着越し素股")
        bui, bui_s = 3, "下着"
    elif _rand(ctx, 2) == 0 and _female(ctx):
        out.print("ノーパン素股")
        bui, bui_s = 2, "割れ目"
    elif _rand(ctx, 2) == 0 and _male(ctx):
        out.print("後背位ノーパン素股")
        bui, bui_s = 2, "太腿"
    else:
        out.print("手コキ")
        bui, bui_s = 1, "手"
    out.printl("で性処理の手伝いをした。")
    out.printw()
    out.printl("やがて男が絶頂を迎えると、人間とは思えない大量の白濁液が")
    out.printl(f"{n}の{bui_s}を汚したが、男根は萎えることなく充血し続けている。")
    out.printl()
    out.printl()
    shojo_i = ctx.data.index_of("TALENT", "処女")

    def lose_virgin() -> None:
        c.talent[shojo_i] = -1
        c.cflag[206] = 11
        out.printl("処女喪失")
        out.printl()

    def rough_virgin_text() -> None:
        if (t("淫乱") or (_abl(ctx, "欲望") >= 3 and _abl(ctx, "従順") >= 3) or _abl(ctx, "マゾっ気") >= 3) and t("初心") < 1:
            out.printl("乱暴に処女膜を引き裂かれる痛みに耐えながらも、")
            out.printl(f"淫気に支配された男に処女を奪われたという事実に{n}は興奮して")
            out.printl("すぐに快楽を感じ始めてしまった。")
        else:
            out.printl("乱暴に処女膜を引き裂かれる痛みに抵抗する気力を完全に奪われ、")
            out.printl(f"{n}は自分の身に起きた出来事を現実だと受け止めることすらできず")
            out.printl("淫気に支配された男に膣肉の純潔を押し開かれていく。")

    v_kekkai, a_kekkai = _base(ctx, "Ｖ結界耐久力"), _base(ctx, "Ａ結界耐久力")
    if c.cflag[42] == 400 and _rand(ctx, 3) == 0:  # :74–141 触手拘束具
        out.printl(f"すると普通の下着に擬態していた{_item(ctx, c.cflag[42])}が淫気に反応したのか")
        out.printl(f"突然暴れ始め、{n}の自由を奪ってしまった！")
        out.printl()
        out.print("誘うように拡げられた")
        if _male(ctx) or _rand(ctx, 2) == 0 or _holyvirgin(ctx) == 1:
            out.print("アナル")
            shojo = 6
        else:
            out.print("雌穴")
            shojo = 5
        out.printl("を突き出す格好で拘束された目の前の供物に、")
        out.printl(f"理性の限界に達した男は{n}へ男根を突き入れた……")
        if (shojo == 5 and v_kekkai > 0) or (shojo == 6 and a_kekkai > 0):
            out.printl("一瞬、結界が薄っすらと淡く光ったような気がしたが、")
            out.printl("それを確認する間も無く肉棒が深々と突き刺さった……")
        if t("処女") > 0 and shojo == 5:
            lose_virgin()
            rough_virgin_text()
        out.printw()
        out.printl(f"――{n}は触手に強制され、")
        if _rand(ctx, 3) == 0:
            out.printl("さながら獣の交尾のように激しく結合部を叩きつけ合わされている")
            out.printl("悲鳴とも狂喜ともつかない喘ぎ声が")
            out.printl("肉と肉が激しくぶつかり合う音に混じって、")
            out.printl("男の怒張を更に限界まで膨れ上がらせてゆく……")
        elif _rand(ctx, 3) == 1:
            out.printl("ねっとりと絡みつくような腰遣いで奉仕させられている")
            out.printl()
            out.printl(f"否定の声を上げる{n}だが、")
            out.printl("男根に抉られ続けるにつれ、強張った動きが")
            out.printl("段々と自分の意思であるかのように淫らなものへと変わっていく……")
        else:
            out.printl("まるで恋人か娼婦のように男に抱き着いている")
            out.printl()
            out.printl("密着感に興奮した男のピストンがより激しくなり、")
            out.printl("射精が近付くにつれ恐怖と快感に震える四肢の拘束が強固になる")
            out.printl("愛の無い見た目だけの蜜月中出し交尾を無理強いされても、")
            out.printl(f"{n}は頭を振って嬌声を上げる事しか出来ない……")
        out.printl()
        out.printl(f"異常な勢いで何度も熱い迸りを{n}の中へ注ぎ込んだ後、")
        out.printl("どうにか一命を取り留めた男性は気を失った")
        out.printl()
        out.printl(f"終わるまでの間、{_item(ctx, c.cflag[42])}によってずっと子種が漏れぬよう")
        out.printl(f"ピッチりと穴を塞がれていた{n}の腹部は、")
        out.printl("人間同士の性交だったとは思えぬほど精液で大きく膨らんでいた……")
        if _male(ctx):
            out.printl()
            out.printl("オトコでありながら男性に犯されて妊娠させられたような有様に、")
            out.printl(f"{n}は自分の精液ボテ腹に光を失った瞳を向けて茫然としている……")
    elif _rand(ctx, 2) == 0 and t("淫乱") > 0 and t("初心") < 1:  # :143–174 淫乱
        out.printl(f"{n}は異常な絶倫状態の男根を目の当たりにし、")
        out.printl("口元に笑みが浮かびそうになるのをこらえた。")
        out.printl("射精したい男と性欲を持て余した者が出会ったら誰だってやりまくるだろう。")
        out.printl("旺盛な性欲を発散するのにこれほど都合の良い相手はいない。")
        out.printl()
        out.printl("出会ったばかりの他人の男根を愛おしそうに味わった後、")
        out.printl("発情した様子でそのはちきれんばかりの剛直を")
        if (_male(ctx) and _rand(ctx, 5) == 2) or _rand(ctx, 5) == 0 or _rand(ctx, 5) == 1 or _holyvirgin(ctx) == 1:
            shojo = 4
            out.print("ひくつくアナルに")
        elif (_rand(ctx, 5) == 2 or _rand(ctx, 5) == 3) and _female(ctx):
            shojo = 3
            out.print("ひくつく雌穴に")
        else:
            out.print("ゆっくりと喉奥まで")
        out.printl("受け入れた……")
        if t("処女") > 0 and shojo == 3:
            lose_virgin()
            out.printl("乱暴に処女膜を引き裂かれる痛みに耐えながらも、")
            out.printl(f"淫気に支配された男に処女を奪われたという事実に{n}は興奮して")
            out.printl("すぐに快楽を感じ始めてしまった。")
        out.printw()
        out.printl("お互いの肉体を貪りあうように重ね合わせ、")
        out.printl(f"{n}が満足するまで応急処置の名を借りた性欲処理は続けられた…")
    elif _rand(ctx, 5) == 0 or (_rand(ctx, 2) == 0 and st.flag[852] <= 2500) or (_rand(ctx, 3) == 0 and st.flag[852] < 5000):
        # :176–245 暴走レイプ
        out.printl(f"{n}は男の淫気が抜けきるまで処理をし続けていたが、")
        out.printl("何度射精しても収まりがつかず暴走した男が襲い掛かってきた。")
        out.printl("")
        out.printl(f"猛獣のような力で服を引き裂き、制止する{n}の声も聞かず")
        out.print("いきり立った肉棒を")
        if _male(ctx) or _rand(ctx, 2) == 0 or _holyvirgin(ctx) == 1:
            out.print("アナル")
            shojo = 2
        else:
            out.print("秘裂")
            shojo = 1
        out.printl("に突き入れる。")
        if (shojo == 1 and v_kekkai > 0) or (shojo == 2 and a_kekkai > 0):
            out.printl("一瞬、結界が薄っすらと淡く光ったような気がしたが、")
            out.printl("それを確認する間も無く肉棒が深々と突き刺さった……")
        if _male(ctx):
            out.printl(f"{n}の肉尻穴は長時間の奉仕と淫気に当たったことで熟れきっており、")
        else:
            out.printl(f"{n}の肉穴は長時間の奉仕と淫気に当たったことで熟れきっており、")
        out.printl("男の本能に従ったピストンも容易に受け入れてしまった。")
        if t("処女") > 0 and shojo == 1:
            lose_virgin()
            rough_virgin_text()
        out.printw()
        out.printl("いくら拒絶を言葉にしてもそれを上回る喘ぎ声に掻き消される。")
        if _male(ctx):
            out.printl(f"男は声にならない声を上げながら{n}の肉尻穴にありったけの子種を注ぎ込むと、")
        else:
            out.printl(f"男は声にならない声を上げながら{n}の肉穴にありったけの子種を注ぎ込むと、")
        out.printl("息も絶え絶えに助かった…と呟きながら気を失った。")
        out.printl("")
        if t("淫乱") > 0 and t("初心") < 1:
            out.printl(f"恍惚と涎を垂らす{n}の表情は、")
            out.printl("犯されたショックや中出しへの絶望よりも快楽が勝っているようだった")
            out.printl(f"精を注がれ絶頂に震えながらも、自分の使命を思い出した{n}は")
            out.printl("なんとか手を動かして本部に連絡を取り男性の救助を要請した…")
        else:
            out.printl("淫気のせいとは言え助けようとした市民に犯されたショックと、")
            if _male(ctx):
                out.printl("中出しされた絶望感と、アナルに中出しされて絶頂してしまった自己嫌悪")
            else:
                out.printl("中出しされた絶望感と、中出しされて絶頂してしまった自己嫌悪")
            out.printl("快楽を感じている複雑な感情に呆然としながらも")
            out.printl("なんとか手を動かして本部に連絡を取り男性の救助を要請した…")
    else:  # :247–385 通常処理
        out.printl(f"{n}は何度も精液を浴びながら、男の淫気が抜けきるまで処理をし続けた…")
        cf42 = c.cflag[42]
        plain_inner = cf42 in (300, 307, 308, 311, 397, 398)
        if _female(ctx):
            r = cloth_no_inner(ctx, st.target)  # :251 CALL CLOTH_NO_INNER, TARGET（RESULT）
            st.result[0] = r
            if bui == 3 and r > 0:
                out.printl(f"恐怖と本能に突き動かされ、男は{n}の性器へ")
                out.printl(f"肉棒をグリグリと{costume_name(ctx, st.target)}越しに押し付ける")
                if c.cflag[41] == 299:
                    out.printl("精液がべっとりと張り付いたスーツの下腹部を見ながら、")
                    out.printl(f"{n}は妊娠はしないはずだと頭の中で繰り返して")
                    out.printl("暴れる強直を抑え込み、腰を振り続けている……")
                else:
                    out.printl(f"射精を導き命を救うために腰を振る{n}だったが、")
                    out.printl("股の間でどんどんと濃くなっていく白濁と精の臭いに身体が震えている……")
            elif bui == 2 or (bui == 3 and cf42 == 0):
                out.printl("命の危機という切迫さの中、ぬちゅぬちゅと性器同士が触れ合う疑似性交は")
                out.printl("射精する間も絶えず腰を振り続けて行われた")
                out.printl()
                out.printl("気付けば肉棒に擦り上げられる過程で割れ目の中心目掛けて")
                out.printl("何度か熱い白濁が注がれており、未挿入ながら")
                out.printl("ねっとりとした感覚が淫猥に歪む花弁から伝い零れている")
                out.printl(f"{n}はそれでも総身を震わせつつ、肉棒から精を吐き出させ続けた……")
                s_sei += 3 + _rand(ctx, 6)
            elif bui == 3:
                if cf42 == 400:
                    out.printl(f"普通のパンツに擬態していた{_item(ctx, cf42)}は")
                    out.printl(f"性器同士が擦れるのに合わせて{n}の性感帯を蹂躙していた")
                    out.printl(f"刺激に翻弄される{n}を弄ぶように、")
                    out.printl("何度も秘肉を割り開いて男性器の挿入を導こうとしてくる")
                    out.printl()
                    out.printl("どうにか素股を続けたものの、")
                    out.printl("何度か先端が挿入りかけて白濁をその膣内に注がれてしまった……")
                    s_sei += 2 + _rand(ctx, 3)
                elif plain_inner:
                    out.printl(f"肉棒を挟んで腰を振り、吸い取れる水分量の限界に近づいた{_item(ctx, cf42)}に")
                    out.printl(f"大量の白濁液を浴びせ続けられる{n}")
                    out.printl()
                    out.printl("射精の勢いに任せ、びゅくっ、びゅくっ、と異常な量の精液が少しづつ")
                    out.printl("ぐちょぐちょになった布地を超え膣内へと染み込んでいく")
                else:
                    out.printl("股間に一心不乱に男性器を擦り付けられ、")
                    out.print(f"{n}の")
                    _chinobun(ctx, "KAIZOU_PANT")
                    out.printl("は白濁に染められていく")
                    out.printl()
                    out.printl("度重なる射精でずっしりと重くなったソレは、")
                    out.printl("肉棒で押し潰される度にグジュグジュと淫猥な音を立てて")
                    out.printl(f"{n}の羞恥心を煽り立て続けた")
                s_sei += 2 + _rand(ctx, 3)
        elif t("男の娘") > 0:  # :306–383
            r = cloth_no_inner(ctx, st.target)
            st.result[0] = r
            kanchigai = ("男は理性を欠いているせいか", "女の子にはないはずの膨らみに当たっているにも関わらず、",
                         f"それでもまだ{n}を女の子だと思っているようだ")
            if bui == 3 and r > 0:
                out.printl(f"恐怖と本能に突き動かされ、男は{n}の股間へ")
                out.printl(f"肉棒をグリグリと{costume_name(ctx, st.target)}越しに押し付ける")
                out.printl()
                for s in kanchigai:
                    out.printl(s)
                out.printl()
                if c.cflag[41] == 299:
                    out.printl("精液がべっとりと張り付いたスーツの下腹部を見ながら、")
                    out.printl(f"{n}は直接触れてはいないからと頭の中で繰り返して")
                    out.printl("暴れる強直を抑え込み、腰を振り続けている……")
                else:
                    out.printl(f"射精を導き命を救うために腰を振る{n}だったが、")
                    out.printl("股の間でどんどんと濃くなっていく他人の白濁と精の臭いに身体が震えている……")
            elif bui in (5, 2):
                out.print("命の危機という切迫さの中、ぬちゅぬちゅと")
                out.print("尻肉" if bui == 5 else "太腿")
                out.printl("と男性器が触れ合う疑似性交は")
                out.printl("射精する間も絶えず腰を振り続けて行われた")
                out.printl()
                out.printl("気付けば肉棒に擦り上げられる過程でお尻の中心目掛けて")
                out.printl("何度か熱い白濁が注がれており、未挿入ながら")
                out.printl("ねっとりとした感覚が淫猥に歪む菊門から伝い零れている")
                out.printl(f"{n}はそれでも総身を震わせつつ、肉棒から精を吐き出させ続けた……")
            elif bui == 3:
                if cf42 == 400:
                    out.printl(f"普通のパンツに擬態していた{_item(ctx, cf42)}は")
                    out.printl(f"性器同士が擦れるのに合わせて{n}の性感帯を蹂躙していた")
                    out.printl(f"刺激に翻弄される{n}を弄ぶように、")
                    out.printl("何度もアナルを割り開いて男性器の挿入を導こうとしてくる")
                    out.printl()
                    for s in kanchigai:
                        out.printl(s)
                    out.printl()
                    out.printl("どうにか素股を続けたものの、")
                    out.printl("何度か先端が挿入りかけて白濁をその腸内に注がれてしまった……")
                elif plain_inner:
                    out.printl(f"肉棒を挟んで腰を振り、吸い取れる水分量の限界に近づいた{_item(ctx, cf42)}に")
                    out.printl(f"大量の白濁液を浴びせ続けられる{n}")
                    out.printl()
                    for s in kanchigai:
                        out.printl(s)
                    out.printl()
                    out.printl("射精の勢いに任せ、びゅくっ、びゅくっ、と異常な量の他人の精液が少しづつ")
                    out.printl(f"ぐちょぐちょになった布地を超え{n}のペニスと腸内へと染み込んでいく")
                else:
                    out.printl("股間に一心不乱に男性器を擦り付けられ、")
                    out.print(f"{n}の")
                    _chinobun(ctx, "KAIZOU_PANT")
                    out.printl("は白濁に染められていく")
                    out.printl()
                    for s in kanchigai:
                        out.printl(s)
                    out.printl()
                    out.print("度重なる射精でずっしりと重くなった")
                    _chinobun(ctx, "KAIZOU_PANT")
                    out.printl("は、")
                    out.printl("肉棒で押し潰される度にグジュグジュと淫猥な音を立てて")
                    out.printl(f"{n}の羞恥心を煽り立て続けた")
        out.printl("……ようやく男が気を失って静かになる頃には、全身他人の精液まみれで臭いがこびりついていた……")
    out.printw()  # :388
    if not 1 <= shojo <= 6:  # :391–398
        if s_sei >= 1 and c.cflag[41] == 299:
            s_sei = 0
    yield from calc_inkioukyu(ctx, bui, shojo, s_sei)
    out.printl()  # :400


def calc_inkioukyu(ctx: Ctx, bui: int, shojo: int = 0, s_sei: int = 0) -> InputGen:
    """`@CALC_INKIOKYU, ARG:0, ARG:1 = 0, ARG:2 = 0`:404–561（部位, 性交の種類, 膣内精液）。"""
    from .battle.ablup import ablup
    from .battle.core import is_penis
    from .battle.ninsin import after_pill, ninsin_hantei
    from .prison.commands import common_prison_exp

    st, out = ctx.state, ctx.out
    t = lambda k: _t(ctx, k)  # noqa: E731
    a = lambda k: _abl(ctx, k)  # noqa: E731
    local = [0] * 1000  # :412 VARSET LOCAL
    s_kai = 12 + _rand(ctx, 5)  # :420
    local[123] = 15 + _rand(ctx, 16)  # :422
    moto = div(_base(ctx, "体力") * (10 + _rand(ctx, 3)), 100)  # :424
    va, aa = a("Ｖ感覚"), a("Ａ感覚")
    if shojo == 1:  # :427–455
        local[120] += 1
    elif shojo == 2:
        local[121] += 1
    elif shojo == 3:
        if va >= 4 and aa >= 4:
            local[120] += 2 + _rand(ctx, 5)
            local[121] += 2 + _rand(ctx, 5)
        elif va >= aa:
            local[120] += 4 + _rand(ctx, 5)
        else:
            local[121] += 4 + _rand(ctx, 5)
    elif shojo == 4:
        local[121] += 4 + _rand(ctx, 5)
    elif shojo == 5:
        local[120] = s_kai - 6
    elif shojo == 6:
        local[121] = s_kai - 6
    if shojo in (1, 2, 5, 6):  # :458–459
        local[110] += 1
    climax = ((bui == 7 and a("Ｂ感覚") >= 4) or (bui == 6 and a("精液中毒") >= 4) or (bui == 3 and a("Ｃ感覚") >= 3)
              or (bui == 2 and a("Ｃ感覚") >= 2))

    def extras() -> None:
        local[131] += div(moto * (2 + _rand(ctx, 3)), 100)
        if is_penis(ctx):
            local[153] += div(moto * (1 + _rand(ctx, 3)), 100)
        if t("母乳体質") > 0:
            local[154] += div(moto * (1 + _rand(ctx, 3)), 100)
        if t("お漏らし癖") > 0:
            local[155] += div(moto * (1 + _rand(ctx, 3)), 100)

    if shojo in (1, 2):  # :462–475
        local[122] += 1
        if climax:
            local[122] += div(moto * (1 + _rand(ctx, 2)), 100) + _rand(ctx, 4)
            extras()
    elif shojo in (3, 4):  # :476–494
        if climax:
            local[122] += div(moto * (1 + _rand(ctx, 2)), 100)
        if va >= 4 and aa >= 4:
            local[122] += div(moto * (1 + _rand(ctx, 2)), 100) + _rand(ctx, 1 + div(va + aa, 4))
        elif va >= aa:
            local[122] += div(moto * (1 + _rand(ctx, 2)), 100) + _rand(ctx, 2 + div(va + 4, 4))
        else:
            local[122] += div(moto * (1 + _rand(ctx, 2)), 100) + _rand(ctx, 2 + div(aa + 4, 4))
        extras()
    elif shojo in (5, 6):  # :496–510
        if shojo == 5:
            local[122] += div(moto * (1 + _rand(ctx, 2)), 100) + _rand(ctx, 2 + div(va + 4, 4))
        else:
            local[122] += div(moto * (1 + _rand(ctx, 2)), 100) + _rand(ctx, 2 + div(aa + 4, 4))
        extras()
    else:  # :511–524
        if climax:
            local[122] += div(moto * (1 + _rand(ctx, 2)), 100) + _rand(ctx, 4)
            extras()
    if bui == 6 or shojo in (3, 4):  # :527–533
        local[124] = max(s_kai - (local[120] + local[121]), 0)
    elif bui in (1, 7) or shojo in (5, 6):
        local[124] = max(s_kai - (local[120] + local[121] + _rand(ctx, 3)), 0)
    else:
        local[124] = max(s_kai - (local[120] + local[121] + 4 + _rand(ctx, 6)), 0)
    if shojo == 1:  # :537–543
        s_sei += min(local[120] + 10 + _rand(ctx, 6), local[123])
    elif shojo == 3 and ((va >= 4 and aa >= 4) or va >= aa):
        s_sei += min(local[120] + local[120] * _rand(ctx, 3), local[123])
    elif shojo == 5:
        s_sei += min(local[120] + local[120] * _rand(ctx, 4), local[123])
    if _female(ctx) and t("処女") < 1:  # :545–546
        st.result[0] = ninsin_hantei(ctx, s_sei, 100, NOZOMANAI)
    if s_sei > 0:  # :548–552
        if _female(ctx) and t("処女") < 1:
            yield from after_pill(ctx, st.target, 20, NOZOMANAI)
            st.result[0] = 0
        out.printl()
    for cc in range(100, 200):  # :557–559
        common_prison_exp(ctx, cc, local[cc])
    ablup(ctx, 1)  # :561
    st.result[0] = 0
