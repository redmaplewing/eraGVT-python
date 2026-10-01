"""夜這い（S18）：`ゲーム内_イベント発生/強制発生イベント/FORCE_夜這い.ERB`（路徑相對 `source/earGVP/ERB/`）。

呼び出し元は `インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND`:116–117（`SIF CONFIG_CHECK_EVENT_F(2) > 0`、
基本セット FLAG:802 = 15 なので ON）のみ。YOBAI_EVENT の変身確認・相手選択と AFTER_PILL が INPUT を使うのでジェネレータ。
本文はイベント本体の中で状態変化と交互に出るので S15／S17 と同じく Python に移植。

GFLAG（`DIM.ERH`:20 `#DIM GFLAG,1000`、SAVEDATA でない）は全 ERB でこのファイルだけが使う（YOBAI_EVENT:113 で VARSET）→
YOBAI_EVENT 内のローカルなリストで表す。GFLAG:100+n／200+n／300+n／400+n = キャラ n へのプレイ内容
（双方変身なし／相手だけ変身／実行者だけ変身／双方変身。値は 1 Ｃ・2 Ｖ・4 Ａ・8 Ｂ・16 性交・32 奉仕）。

引擎語意：
- 添字省略は TARGET（`reference/emuera-1824/Emuera/GameData/Variable/VariableParser.cs`:91–134）。`&&`／`||` は短絡
  （`GameData/Expression/OperatorMethod.cs`:532–536）、式は左から評価（`ABL + RAND:4 >= 6` の RAND は常に引く）。
- LOCAL のサイズは既定 1000（`GameData/ConstantData.cs`:148）なので LOCAL:324 は有効。YOBAI_ACTION／YOBAI_HOUSHI_n は
  `VARSET LOCAL` で始まる。
- 実行中に CASE／ELSEIF／ELSE の行へ流れ着くと対応する ENDSELECT／ENDIF へ飛ぶ（`GameProc/Function/Instraction.Child.cs`
  @ELSEIF_Instruction:1805–1821、飛び先は `GameProc/ErbLoader.cs`:1155–1158）。GOTO は線形ジャンプ
  （`Instraction.Child.cs@GOTO_Instruction`:2366–2406）なので、CASE 1 から `GOTO V_SEX` 等で CASE 2／4 のラベルへ飛ぶと、
  そのラベルからその IF 分岐の終わりまでを実行し、ENDIF → 次の CASE 行 → ENDSELECT（:2643）に抜ける（`_v_sex` 等の関数）。
- `\\@ 式 ? 左 # 右 \\@` の左右は半角空白とタブを前後から除く（`Sub/LexicalAnalyzer.cs@AnalyseYenAt`:1231–1257）。
- 関数末尾まで流れ落ちると RESULT = 0（`GameProc/Process.ScriptProc.cs`:61–67）。

原作どおりの怪処（deviations「原作行為」S18）：
- YOBAI_SELECT_PLAY が `CALL CLEARRANDCHOOSE`（:545）で YOBAI の候補リスト（RANDCHOOSE_NUM）を上書きする。YOBAI_EVENT が
  SELECT_PLAY の後で -999 を返す（:275）と、REROLL はプレイ内容の候補（1／2／4／8／16／32）から TARGET を選ぶ。
  その番号のキャラが居なければ原作はエラー → ここでは停止（NotImplementedError）。
- `%CALLNAME:ARG%`（:1450、:1796）は ARG（2／4）番のキャラ名、`%CALLNAME:MASTER%` は MASTER の名前（原作の書き間違い）。

使用者裁決（2026-10-01）で原作と変えたもの（`# DEVIATION:`、deviations.md「使用者裁決 2026-10-01」）：
- YOBAI_EVENT の淫乳条件（:160–177）は `ABL:Ｃ感覚` ではなく `ABL:Ｂ感覚` を足す。
- HOUSHI_4／5 の `LOCAL:124 = LOCAL:324`（:3237、:3622）は VARSET LOCAL 前の LOCAL:324 を使う（原作は常に 0）。
- HOUSHI_4 の処女喪失（:3088–3092）の CFLAG:206 は処女を失った対象に書く（原作は実行者 LCOUNT）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state import GameState
from .action import Ctx, config_check_maniac, print_callname, print_transcallname
from .battle.core import (
    abl,
    add_randchoose,
    choicecount,
    clear_randchoose,
    clear_specific_choose,
    is_girly,
    is_manly,
    is_penis,
    randchoose_f,
    t,
)
from .chara_common import charatalent, is_female, is_male
from .era import div, format_percent, mod, times
from .relation import KYOUDAI, OYAKO, lover_f, toshiue
from .shop import charanum_active

InputGen = Generator[None, int, int]

_LOCAL_SIZE = 1000


# --- 共通の小道具 --------------------------------------------------------------------------------


def _incest(ctx: Ctx, a: int, b: int) -> int:
    """`INCEST_F(a, b)`（ARG:2 = 0：RELATION）。"""
    from .battle.sexcom import incest

    return incest(ctx, a, b, 0)


def _self_call(ctx: Ctx) -> str:
    """`口上/口上システム関係/SELF_CALL.ERB@SELF_CALL()`:31–60（オプション 0、伸ばす長さ 0、対象 TARGET）。"""
    from .firstsetting import self_call_list

    c = ctx.state.target_chara
    if c.cstr[4] != "":
        return c.cstr[4]
    return self_call_list(mod(div(c.cflag[8], 5), 20), mod(c.cflag[8], 5))


def _prison(ctx: Ctx, L: list[int]) -> None:
    """`CALL COMMON_PRISON, LOCAL:0〜11, 1`（結界が反応しない）＋ `FOR CCOUNT, 100, 200 / COMMON_PRISON_EXP`。"""
    from .prison.commands import common_prison, common_prison_exp

    common_prison(ctx, L[0:12], 1)
    for cc in range(100, 200):
        common_prison_exp(ctx, cc, L[cc])


def _ablup1(ctx: Ctx) -> None:
    from .battle.ablup import ablup

    ablup(ctx, 1)


def _ninsin(ctx: Ctx, l123: int, father: int) -> None:
    from .battle.ninsin import ninsin_hantei

    ninsin_hantei(ctx, l123, 400, ctx.state.charas[father].cflag[240] * -1 - 100)


def _after_pill(ctx: Ctx, who: int, father: int) -> InputGen:
    from .battle.ninsin import after_pill

    return (yield from after_pill(ctx, who, 75, ctx.state.charas[father].cflag[240] * -1 - 100))


def _switch(ctx: Ctx) -> int:
    """`PRINTW / PRINTFORML 【夜這い対象：…】 / LCOUNT = TARGET / TARGET = FLAG:799 / VARSET LOCAL`。戻り値 = LCOUNT。"""
    st, out = ctx.state, ctx.out
    out.printw()
    out.printl(f"【夜這い対象：{print_callname(st, st.flag[799], 1)}】")
    lcount = st.target
    st.target = st.flag[799]
    return lcount


def _family(ctx: Ctx, male_of: int) -> str:
    """:1455–1484 等：RELATION:TARGET:(FLAG:799) の 親子／兄弟姉妹 と年上判定から続柄 1 語（性別は male_of のキャラ）。"""
    st = ctx.state
    rel = st.charas[st.target].relation[st.flag[799]]
    male = is_male(ctx.data, st.charas[male_of])
    older = toshiue(st, st.target, st.flag[799]) > 0
    if (rel >> OYAKO) & 1:
        if older:
            return "父" if male else "母"
        return "息子" if male else "娘"
    if (rel >> KYOUDAI) & 1:
        if older:
            return "兄" if male else "姉"
        return "弟" if male else "妹"
    return ""


def _callname_at(ctx: Ctx, idx: int) -> str:
    """`%CALLNAME:n%`。範囲外は原作ではエラー（`reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs`
    @CheckElement:276–278「キャラ登録番号の範囲外です」）→ 停止。"""
    st = ctx.state
    if not 0 <= idx < st.charanum:
        raise NotImplementedError(f"CALLNAME:{idx} はキャラ範囲外（原作はエラー：FORCE_夜這い.ERB:1450／1796）")
    return st.charas[idx].callname


# --- @YOBAI（:8–101）------------------------------------------------------------------------------


def yobai(ctx: Ctx) -> Generator[None, int, None]:
    """`@YOBAI`:8–101。"""
    from .battle.func import transform

    st, data, out = ctx.state, ctx.data, ctx.out
    if st.time == 0:  # :11–12
        return
    if charanum_active(st) < 2:  # :14–15
        return
    if not any(st.charas[i].cflag[999] for i in range(st.charanum) if i != GameState.MASTER):  # :17–28
        return
    if st.flag[999] == 1:  # :31–34
        out.set_color((105, 105, 105))
        out.printl("------ 夜這い判定 ------")
        out.reset_color()
    clear_randchoose(st)  # :36
    for i in range(1, st.charanum):  # :37–73
        c = st.charas[i]
        if c.cflag[999] == 0:
            continue
        tl = lambda n: t(ctx, c, n)  # noqa: E731
        a = lambda n: abl(ctx, c, n)  # noqa: E731
        if tl("繁殖袋") > 0 or tl("四肢欠損") > 0:
            continue
        st.target = i  # :44
        conds = (
            tl("淫核") * 3 + a("Ｃ感覚") >= 3,
            tl("淫壷") * 3 + a("Ｖ感覚") >= 3,
            tl("淫尻") * 3 + a("Ａ感覚") >= 3,
            tl("淫乳") * 3 + a("Ｂ感覚") >= 3,
            (tl("ふたなり") > 0 or tl("変身時ふたなり") > 0 or is_male(data, c)) and a("射精中毒") > 0,
        )
        if not any(conds):  # :48、:70–71
            continue
        if c.cflag[0] != 0:  # :50–51
            continue
        l1 = (tl("淫乱") > 0) * 2 + sum(int(x) for x in conds)  # :53
        l2 = max(a("欲望") + a("自慰中毒") + a("触手中毒"), 0)  # :54
        local = (l1 * 2 + 22) * (125 + l2 * 10) if l1 else 0  # :55–56
        if 1 <= tl("交際相手") < 5:  # :57–62
            local = times(local, "0.5")
        if tl("清純派"):
            local = times(local, "0.5")
        if tl("人間不信") > 0:
            local = times(local, "0.25")
        if st.flag[999] == 1:  # :63–67
            out.set_color((105, 105, 105))
            out.printl(f"実行判定　{c.callname}　確率{local}")
            out.reset_color()
        if st.rng.rand(10000) < local:  # :68–69
            add_randchoose(st, st.target)
    while True:  # $REROLL :74–101
        if choicecount(st):
            st.target = randchoose_f(st)  # :77
            if not 0 <= st.target < st.charanum:
                raise NotImplementedError(
                    f"夜這いの REROLL で TARGET = {st.target}（YOBAI_SELECT_PLAY:545 が候補リストを上書き：原作はエラー）"
                )
            result = yield from yobai_event(ctx)  # :78
            if result == -999:  # :79–86
                clear_specific_choose(st, st.target)
                if st.flag[999] == 1:
                    out.set_color((105, 105, 105))
                    out.printl(f"{st.target_chara.callname} = -999 / REROLL")
                    out.reset_color()
                continue
            # :88 GET_STATE_EXPUP：実績のみ（deviations.md「全域資料」）
            for i in range(st.charanum):  # :90–95 全キャラの変身を解除
                if i == GameState.MASTER:
                    continue
                if st.charas[i].cflag[1] > 0 and st.charas[i].cflag[0] == 0:
                    transform(ctx, 0, i)
        elif st.flag[999] == 1:  # :96–101
            out.set_color((105, 105, 105))
            out.printl("夜這い実行なし")
            out.reset_color()
        return


# --- @YOBAI_EVENT（:105–526）--------------------------------------------------------------------


def yobai_event(ctx: Ctx) -> InputGen:
    """`@YOBAI_EVENT`:105–526。戻り値（RESULT）：-999 = 対象なし（リロール）、-1 = 変身を断って終了、999 = やめる、0 = 実行。"""
    from .battle.func import transform
    from .parasite import _relation_text

    st, data, out = ctx.state, ctx.data, ctx.out
    if charanum_active(st) == 0:  # :109–110
        return 0
    gflag = [0] * 1000  # :113 VARSET GFLAG
    me = st.target
    c = st.charas[me]
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    a = lambda n: abl(ctx, c, n)  # noqa: E731
    ct = lambda who, tr, n: charatalent(data, st.charas[who], tr, n)  # noqa: E731
    sel = {0: 0, 1: 0, 10: 0, 11: 0}  # :116–122
    low = (
        tl("淫核") * 3 + a("Ｃ感覚") < 3
        and tl("淫壷") * 3 + a("Ｖ感覚") < 3
        and tl("淫尻") * 3 + a("Ａ感覚") < 3
        # DEVIATION: 使用者裁決（2026-10-01）：原作 :160／:163／:170／:173 は `TALENT:淫乳 * 3 + ABL:Ｃ感覚` だが、
        # YOBAI の候補条件（:37–73）と同じ `ABL:Ｂ感覚` を使う（deviations.md「使用者裁決 2026-10-01」）。
        and tl("淫乳") * 3 + a("Ｂ感覚") < 3
    )
    for cc in range(st.charanum):  # :123–218
        if cc == GameState.MASTER or cc == me or st.charas[cc].cflag[999] == 0:
            continue
        if is_girly(ctx, me) or is_girly(ctx, cc):  # :136–137
            sel[0] += 1
        if is_girly(ctx, me) or ct(cc, 1, "オトコ") == 0 or ct(cc, 1, "男の娘") > 0:  # :142–143
            sel[1] += 1
        if ct(me, 1, "オトコ") == 0 or ct(me, 1, "男の娘") > 0 or is_girly(ctx, cc):  # :148–149
            sel[10] += 1
        if ct(me, 1, "オトコ") == 0 or ct(me, 1, "男の娘") > 0 or ct(cc, 1, "オトコ") == 0 or ct(cc, 1, "男の娘") > 0:
            sel[11] += 1  # :154–155
        for tr, keys in ((0, (0, 1)), (1, (10, 11))):  # :160–180
            if (ct(me, tr, "ふたなり") > 0 or ct(me, tr, "男の娘") > 0) and low and a("Ｃ感覚") + a("射精中毒") == 0:
                for k in keys:
                    sel[k] = 0
            elif ct(me, tr, "オトコ") == 0 and low:
                for k in keys:
                    sel[k] = 0
            elif ct(me, tr, "オトコ") > 0 and ct(me, tr, "男の娘") == 0 and a("Ｃ感覚") + a("射精中毒") == 0:
                for k in keys:
                    sel[k] = 0
        if ct(me, 0, "オトコ") == 0 and ct(me, 1, "オトコ") > 0 and tl("妊娠") > 0:  # :182–185
            sel[10] = sel[11] = 0
        if ct(cc, 0, "オトコ") == 0 and ct(cc, 1, "オトコ") > 0 and t(ctx, st.charas[cc], "妊娠") > 0:  # :187–190
            sel[1] = sel[11] = 0
        if ct(me, 0, "オトコ") > 0 and ct(me, 0, "男の娘") == 0 and tl("変身時ＴＳ") > 0 and tl("女体受容") == 0:  # :194–197
            sel[10] = sel[11] = 0
        if is_manly(ctx, cc) and tl("男性苦手") > 0 and tl("両刀") == 0 and st.rng.rand(4) == 0:  # :201–208
            sel[0] = sel[1] = sel[10] = sel[11] = 0
            if st.flag[999] == 1:
                out.set_color((105, 105, 105))
                out.printl("男性苦手")
                out.reset_color()
        if is_female(data, st.charas[cc]) and tl("女性苦手") > 0 and tl("両刀") == 0 and st.rng.rand(4) == 0:  # :209–216
            sel[0] = sel[1] = sel[10] = sel[11] = 0
            if st.flag[999] == 1:
                out.set_color((105, 105, 105))
                out.printl("女性苦手")
                out.reset_color()
    if st.flag[999] == 1:  # :220–223
        out.set_color((105, 105, 105))
        out.printl(f"夜這いプレイ内容抽選 {c.callname}　{sel[0]} / {sel[1]} / {sel[10]} / {sel[11]}")
        out.reset_color()
    if sel[0] + sel[1] + sel[10] + sel[11] == 0:  # :225–226
        return -999
    for k in (0, 1, 10, 11):  # :230–240
        if sel[k] > 0:
            yobai_select_play(ctx, k, gflag)
    out.drawline()  # :243–248
    out.set_bold(True)
    out.printl("（夜這い対象選択）")
    out.set_bold(False)
    out.printl()
    out.printl(f"{print_callname(st, me)}は眠れぬ夜を過ごしている・・・")
    name = lambda: print_transcallname(st, me)  # noqa: E731
    if sel[0] + sel[1] == 0:  # :251–276
        if tl("女体受容") > 0 or tl("変身時男の娘") > 0:
            if tl("変身時男の娘") > 0:
                out.printl(f"{name()}は変身で男の娘化できます。変身した状態で夜這いを行いますか？")
            else:
                out.printl(f"{name()}は変身で女体化できます。変身した状態で夜這いを行いますか？")
            out.printl(" [0]はい　[1]夜這いを行わずに終了する")
            while True:  # $INPUT_LOOP_0_0
                r = yield
                if r == 0:
                    out.printl(f"{name()}は変身した！")
                    out.printw()
                    transform(ctx, 1)
                    break
                if r == 1:
                    out.printl("夜這いを終了します。")
                    out.printw()
                    return -1
        else:
            return -999  # :275
    elif sel[10] + sel[11] > 0:  # :278–303
        if ((tl("変身時ＴＳ") > 0 or tl("変身時ふたなり") > 0) and (is_female(data, c) or tl("女体受容") > 0)) or tl(
            "変身時男の娘"
        ) > 0:
            if tl("変身時男の娘") > 0:
                out.printl(f"{name()}は変身で男の娘化できます。変身した状態で夜這いを行いますか？")
            elif is_male(data, c):
                out.printl(f"{name()}は変身で女体化できます。変身した状態で夜這いを行いますか？")
            elif tl("変身時ふたなり") > 0:
                out.printl(f"{name()}は変身でふたなり化できます。変身した状態で夜這いを行いますか？")
            else:
                out.printl(f"{name()}は変身で男性化できます。変身した状態で夜這いを行いますか？")
            out.printl("　[0]はい　　[1]いいえ")
            while True:  # $INPUT_LOOP_0_1
                r = yield
                if r == 0:
                    out.printl(f"{name()}は変身した！")
                    out.printw()
                    transform(ctx, 1)
                    break
                if r == 1:
                    out.printl("変身せずにそのまま夜這いを行います。")
                    out.printw()
                    break
    out.printl()  # :304–306
    out.printl("誰の部屋に行きますか？")
    out.printl()
    for lc in range(st.charanum):  # :307–501
        o = st.charas[lc]
        if t(ctx, o, "繁殖袋") > 0 or t(ctx, o, "四肢欠損") > 0:
            continue
        locals_ = _relation_text(ctx, c.relation[lc], lc, close_itoko=True)  # :312–452
        if not (gflag[100 + lc] > 0 or gflag[200 + lc] > 0 or gflag[300 + lc] > 0 or gflag[400 + lc] > 0):
            continue
        if (c.cflag[1] == 0 and gflag[100 + lc] > 0) or (c.cflag[1] > 0 and gflag[300 + lc] > 0):  # :456–462
            out.print(f"[{lc}] ")
        else:
            out.set_color((105, 105, 105))
            out.print_plain(f"[{lc}] ")
            out.reset_color()
        if ct(lc, 0, "男の娘") > 0:  # :463–479
            out.set_color((255, 180, 180))
            out.print("(♂)")
        elif ct(lc, 0, "オトコ") > 0:
            out.set_color((180, 180, 255))
            out.print("(♂)")
        elif ct(lc, 0, "ふたなり") > 0:
            out.set_color((255, 180, 180))
            out.print("(双)")
        else:
            out.set_color((255, 180, 180))
            out.print("(♀)")
        out.reset_color()
        out.print(f" {format_percent(o.callname, 24, True)}　{format_percent(locals_, 24, True)}")  # :480
        ts_ok = (c.cflag[1] == 0 and gflag[200 + lc] > 0) or (c.cflag[1] > 0 and gflag[400 + lc] > 0)
        if ts_ok and t(ctx, o, "変身時ＴＳ") > 0:  # :481–491
            out.print(f"　　[{lc + 100}] ＴＳ")
            if is_female(data, o) and t(ctx, o, "変身時男の娘") > 0:
                out.print("（男の娘化させる）")
            elif is_female(data, o):
                out.print("（男性化させる）")
            elif is_male(data, o) and t(ctx, o, "変身時ふたなり") > 0:
                out.print("（ふたなり女体化させる）")
            elif is_male(data, o):
                out.print("（女性化させる）")
        elif ts_ok and (t(ctx, o, "変身時ふたなり") > 0 or t(ctx, o, "変身時男の娘") > 0):  # :492–497
            if t(ctx, o, "変身時男の娘") > 0:
                out.print(f"　　[{lc + 100}] 変身（男の娘化させる）")
            else:
                out.print(f"　　[{lc + 100}] 変身（ふたなり化させる）")
        out.printl()  # :499
    out.printl("[999]夜這いは行わない")  # :502
    while True:  # $INPUT_LOOP_CHARA_LIST :503–526
        r = yield
        cf1 = c.cflag[1]
        if r == 999:
            return 999
        if 0 < r < st.charanum and ((cf1 == 0 and gflag[100 + r] != 0) or (cf1 > 0 and gflag[300 + r])):
            st.flag[799] = r  # :508
            yield from yobai_action(ctx, gflag[300 + r] if cf1 > 0 else gflag[100 + r])
            return 0
        if (
            100 < r < st.charanum + 100
            and ((cf1 == 0 and gflag[100 + r] != 0) or (cf1 > 0 and gflag[300 + r]))
            and (
                t(ctx, st.charas[r - 100], "変身時ＴＳ") > 0
                or t(ctx, st.charas[r - 100], "変身時ふたなり") > 0
                or t(ctx, st.charas[r - 100], "変身時男の娘") > 0
            )
        ):
            st.flag[799] = r - 100  # :516
            yield from yobai_action(ctx, gflag[300 + r] if cf1 > 0 else gflag[100 + r], 1)
            return 0
        out.printl("正しい値を入力してください")  # :524


# --- @YOBAI_SELECT_PLAY（:530–634）----------------------------------------------------------------


def yobai_select_play(ctx: Ctx, arg: int, gflag: list[int]) -> None:
    """`@YOBAI_SELECT_PLAY, ARG`:530–634。:545 CLEARRANDCHOOSE は YOBAI の候補リストと共有（モジュール docstring）。"""
    from .battle.func import transform

    st, data = ctx.state, ctx.data
    me = st.target
    c = st.charas[me]
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    a = lambda n: abl(ctx, c, n)  # noqa: E731
    if arg in (10, 11):  # :533–534
        transform(ctx, 1)
    for lc in range(st.charanum):  # :535–627
        if lc == GameState.MASTER:
            continue
        o = st.charas[lc]
        if o.cflag[0] != 0 or lc == me or o.cflag[999] == 0:
            continue
        clear_randchoose(st)  # :545
        if arg in (1, 11):  # :548–549
            transform(ctx, 1, lc)
        if is_penis(ctx) and is_girly(ctx, lc):  # :553–575
            l1 = a("Ｃ感覚") + a("射精中毒")
            if lover_f(st, me, lc) > 0 or lover_f(st, lc, me) > 0:
                l1 *= 2
            if tl("男の娘") > 0:
                l1 = div(l1, 3)
                if tl("淫核") + tl("淫尻") + tl("淫乳") > 0:
                    l1 = div(l1, 2)
            for _ in range(l1):  # REPEAT（0 以下なら回らない）
                if st.rng.rand(10) < a("Ｃ感覚") + a("射精中毒"):
                    add_randchoose(st, 16)
                else:
                    add_randchoose(st, 32)
        if tl("淫核") * 3 + a("Ｃ感覚") >= 3 and tl("ふたなり") < 1 and is_girly(ctx):  # :578–584
            for _ in range(a("Ｃ感覚")):
                add_randchoose(st, 1)
        if tl("淫壷") * 3 + a("Ｖ感覚") >= 3 and is_female(data, c):  # :586–595
            l1 = a("Ｖ感覚")
            if t(ctx, o, "ふたなり") > 0 or is_male(data, o):
                l1 *= 2
            for _ in range(l1):
                add_randchoose(st, 2)
        if tl("淫尻") * 3 + a("Ａ感覚") >= 3 and is_girly(ctx):  # :598–604
            for _ in range(a("Ａ感覚")):
                add_randchoose(st, 4)
        if tl("淫乳") * 3 + a("Ｂ感覚") >= 3 and is_girly(ctx):  # :607–613
            for _ in range(a("Ｂ感覚")):
                add_randchoose(st, 8)
        base = {1: 200, 10: 300, 11: 400}.get(arg, 100)  # :616–624
        if choicecount(st) > 0:  # :625–626
            gflag[base + lc] = randchoose_f(st)
    for i in range(st.charanum):  # :629–634 全キャラの変身を解除
        if i == GameState.MASTER:
            continue
        if st.charas[i].cflag[1] > 0 and st.charas[i].cflag[0] == 0:
            transform(ctx, 0, i)


# --- @YOBAI_ACTION（:641–2646）---------------------------------------------------------------------


class _Action:
    """`@YOBAI_ACTION, ARG, ARG:1`：静的 #DIM（SUIMIN・SELF・ＴＳキャラ・NAKADASHI・LCOUNT）と LOCAL を持つ。"""

    def __init__(self, ctx: Ctx, arg: int, arg1: int) -> None:
        self.ctx = ctx
        self.arg = arg
        self.arg1 = arg1
        self.suimin = 0
        self.self_ = 0
        self.ts = 0
        self.nakadashi = 0
        self.lcount = 0
        self.L = [0] * _LOCAL_SIZE

    # 名前・素質の小道具（TARGET は途中で FLAG:799 に変わるので毎回引く）
    def T(self) -> str:  # noqa: N802
        return print_callname(self.ctx.state, self.ctx.state.target)

    def F(self) -> str:  # noqa: N802
        return print_callname(self.ctx.state, self.ctx.state.flag[799])

    @property
    def c(self):
        return self.ctx.state.target_chara

    @property
    def f(self):
        return self.ctx.state.charas[self.ctx.state.flag[799]]

    def tc_(self, n: str) -> int:
        return t(self.ctx, self.c, n)

    def tf(self, n: str) -> int:
        return t(self.ctx, self.f, n)

    def ac(self, n: str) -> int:
        return abl(self.ctx, self.c, n)

    def af(self, n: str) -> int:
        return abl(self.ctx, self.f, n)

    def lover_ft(self) -> int:
        st = self.ctx.state
        return lover_f(st, st.flag[799], st.target)

    def lover_tf(self) -> int:
        st = self.ctx.state
        return lover_f(st, st.target, st.flag[799])

    def inc_tf(self) -> int:
        st = self.ctx.state
        return _incest(self.ctx, st.target, st.flag[799])

    def tsish(self) -> bool:
        """`ＴＳキャラ == 1 || TALENT:性別変化 % 10 == 1`。"""
        return self.ts == 1 or mod(self.tc_("性別変化"), 10) == 1

    def form_t(self) -> str:
        """:753–765：実行者（TARGET）の変身後の姿。"""
        if self.tc_("男の娘") > 0:
            return "かわいらしい姿"
        if is_male(self.ctx.data, self.c):
            return "男性の姿"
        if self.tc_("ふたなり") > 0:
            return "ふたなり"
        return "女性の姿"

    def form_f(self) -> str:
        """:835–847：対象（FLAG:799）の変身後の姿。"""
        if self.tf("男の娘") > 0:
            return "男の娘"
        if is_male(self.ctx.data, self.f):
            return "男性の姿"
        if self.tf("ふたなり") > 0:
            return "ふたなり"
        return "女性の姿"

    def koukan(self) -> None:
        """:1662–1674 等「これは性交ではなく、恋人／家族／仲間の悩みに応えているだけ」。"""
        out = self.ctx.out
        out.printl(f"{self.T()}を抑えつけて激しく腰を振る{self.F()}・・・")
        out.print("「これは性交ではなく、")
        if self.lover_tf() > 0:
            out.print("恋人")
        elif self.inc_tf() > 0:
            out.print("家族")
        else:
            out.print("仲間")
        out.printl("の悩みに応えているだけ」")
        out.printl("そんな言い訳はとうにどこかへと吹き飛んでしまっていた。")
        out.printl("一夜限りの契りという免罪符が逆に枷を取り払ってしまったかの如く、")
        out.printl("パンパンと打ちつける淫音が響くたびに快楽が増幅されていく。")

    def executor(self) -> None:
        self.ctx.out.printl(f"【夜這い実行者：{print_callname(self.ctx.state, self.ctx.state.target, 1)}】")

    def switch(self) -> None:
        self.lcount = _switch(self.ctx)
        self.L = [0] * _LOCAL_SIZE

    def inc_f_l(self) -> None:
        """`SIF INCEST_F(FLAG:799, LCOUNT) > 0 / LOCAL:141 = 1`。"""
        if _incest(self.ctx, self.ctx.state.flag[799], self.lcount) > 0:
            self.L[141] = 1

    def inc_t_f(self) -> None:
        """`SIF INCEST_F(TARGET, FLAG:799) > 0 / LOCAL:141 = 1`。"""
        if self.inc_tf() > 0:
            self.L[141] = 1

    def ninsin_if(self) -> None:
        """`SIF (TALENT:TARGET:淫乱 > 0 || LOVER_F(FLAG:799, TARGET) > 0) && LOCAL:123 > 0 && TALENT:TARGET:未熟 == 0`
        `/ CALL NINSIN_HANTEI, LOCAL:123, 400, CFLAG:(FLAG:799):240 * -1 - 100`。"""
        if (self.tc_("淫乱") > 0 or self.lover_ft() > 0) and self.L[123] > 0 and self.tc_("未熟") == 0:
            _ninsin(self.ctx, self.L[123], self.ctx.state.flag[799])

    def target_side_c(self) -> None:
        """対象側の定型：快C 50・絶頂・近親・射精（未熟でなければ）→ COMMON_PRISON → _ABLUP。"""
        self.L[0] = 50
        self.L[122] = 1
        self.inc_f_l()
        if self.tf("未熟") != 1:
            self.L[153] = 1
        _prison(self.ctx, self.L)
        _ablup1(self.ctx)

    def pill_if(self) -> InputGen:
        """`IF NAKADASHI == 1 / CALL AFTER_PILL, LCOUNT, 75, CFLAG:(TARGET):240 * -1 - 100`（TARGET は対象）。"""
        if self.nakadashi == 1:
            yield from _after_pill(self.ctx, self.lcount, self.ctx.state.target)
        return 0


def yobai_action(ctx: Ctx, arg: int, arg1: int = 0) -> InputGen:
    """`@YOBAI_ACTION, ARG, ARG:1 = 0`:641–2646。ARG = プレイ内容、ARG:1 != 0 なら対象を変身させる。"""
    from .battle.func import transform

    st, data, out = ctx.state, ctx.data, ctx.out
    y = _Action(ctx, arg, arg1)
    rand = st.rng.rand
    c = y.c
    # :652–656 ＴＳキャラ
    y.ts = 1 if is_female(data, c) and y.tc_("変身時ＴＳ") > 0 and c.cflag[1] > 0 else 0
    out.drawline()  # :661
    if arg1 > 0:  # :663–664
        transform(ctx, 1, st.flag[799])
    f = y.f
    if f.cflag[99] > rand(30):  # :667–675 対象が熟睡（睡眠姦）
        y.suimin = 1
    elif rand(100) < y.af("欲望") * 5 + y.af("触手中毒") * 2 + y.af("自慰中毒") * 7:
        y.self_ = 1
    out.printl("――")  # :677–684
    out.printl("――――")
    out.printw("――――――")
    out.printl()
    out.set_bold(True)
    out.printl(f"夜這い（{print_callname(st, st.target, 1)}）→（{print_callname(st, st.flag[799], 1)}）")
    out.set_bold(False)
    out.printl()
    T, F = y.T, y.F
    if y.tsish():  # :687–699
        out.print(f"{T()}は女体の底なしの快楽を忘れられず、")
        if y.ts == 1:
            out.print("女体化して")
        out.printl("何度も自分を慰めていた。")
    else:
        out.print(f"{T()}は身体の芯を焦がす火照りを抑えきれずに、何度も自分")
        if rand(5) == 0 and (y.tc_("ふたなり") > 0 or (is_male(data, c) and y.tc_("男の娘") <= 0)):
            out.print("のペニス")
        out.printl("を慰めていた。")
    out.printl(f"それでも満足できなかった{T()}は夢遊病のように廊下へと彷徨い出て")
    out.printl(f"助けを求めるように{F()}の部屋の扉をノックする・・・")
    out.printw()
    if y.suimin == 1:  # :704–724
        out.printl("不用心にも扉には鍵がかかっておらず、")
        out.printl(f"{F()}は触手との戦いで疲れ果てて熟睡しているようだ。")
        if y.ac("欲望") < 4:
            if rand(2) == 0:
                out.print("少しだけ、火照りが消えたらすぐ帰るから…")
            else:
                out.print("絶対に触れる以上のことはしないから…")
            out.printl("と、言い訳しながら")
        else:
            out.print("これではまるでレイプだ…")
            if rand(3) == 0:
                out.printl("その事実に情欲が増す。")
            elif rand(2) == 0:
                out.printl("いけない事と分かっていても止めることが出来ない。")
            else:
                out.printl("その背徳感が体の奥で疼く。")
        out.printl(f"{T()}は物音を立てないように{F()}のベッドに潜り込んだ。")
    elif y.self_ == 1:  # :726–744
        out.printl("不用心にも扉には鍵がかかっておらず、扉を開けると")
        if rand(3) == 0 and is_penis(ctx, st.flag[799]):
            out.print("肉棒")
        elif rand(2) == 0 and (is_female(data, f) or y.tf("ふたなり") > 0):
            out.print("秘所")
        else:
            out.print("胸")
        out.printl(f"を慰めていた{F()}と目が合った。")
        if rand(3) == 0 and y.af("欲望") >= 4:
            out.printl(f"気まずい空気の中、手伝ってあげようかと声をかけた{T()}に対し")
            out.printl(f"{F()}は潤んだ瞳で何かを訴えかけ、{T()}をベッドへ迎え入れた。")
        elif (rand(2) == 0 and y.af("露出癖") >= 4) or y.af("自慰中毒") >= 4:
            out.printl(f"恥ずかしさからか興奮しているのか、頬を赤く染め上げた{F()}は自慰を見せつけている。")
            out.printl(f"{T()}は誘われるように{F()}のベッドに潜り込んだ。")
        else:
            out.printl(f"赤面し、今にも悲鳴を上げそうな{F()}の口を咄嗟に抑え、懇願しながら{T()}はベッドの中へ潜り込んだ。")
    elif y.af("欲望") < 3:  # :746–851
        inc = y.inc_tf() > 0
        if inc and toshiue(st, st.target, st.flag[799]) > 0:
            out.print(f"{F()}は")
            if c.cflag[1] > 0:
                out.print(f"{T()}が")
                out.print(y.form_t())
                out.printl("に変身していることに驚きながらも")
            out.print("家族と一緒の部屋で寝られる事を")
            if c.cflag[1] == 0:
                out.printl()
            out.print("無邪気に喜びながら部屋に迎え入れ")
            if arg1 > 0:
                out.print("たが")
        elif y.inc_tf() > 0 and toshiue(st, st.target, st.flag[799]) == 0:
            if c.cflag[1] > 0:
                out.print(f"{T()}が")
                out.print(y.form_t())
                out.printl("に変身していることに驚きながらも")
            else:
                out.printl(f"突然の訪問に驚いた様子の{F()}だが、")
            out.printl(f"あまりに苦しそうに喘ぐ{T()}の様子を見かねたのか")
            if is_male(data, f) and arg1 == 0:
                out.print("血の繋がった相手の無防備な肢体にドキリとしながら部屋に迎え入れ")
            elif is_male(data, f) or (is_female(data, f) and arg1 > 0):
                out.print("落ち着くまで話し相手になってやろうと部屋に迎え入れ")
            else:
                out.print("落ち着くまで添い寝してあげようと部屋に迎え入れ")
        else:
            if c.cflag[1] > 0:
                out.print(f"{T()}が")
                out.print(y.form_t())
                out.printl("に変身していることに驚きながらも")
            else:
                out.print("突然の訪問に")
            out.printl(f"驚いた様子の{F()}だが、")
            out.printl(f"あまりに苦しそうに喘ぐ{T()}の様子を見かねたのか")
            if is_male(data, f):
                out.print("とりあえず部屋に迎え入れ")
            else:
                out.print("イけるように手伝うだけだと釘を刺して部屋に迎え入れ")
        if arg1 > 0:  # :832–851
            out.printl("、")
            out.print("懇願されて戸惑いながらも")
            out.print(y.form_f())
            out.printl("に変身した・・・")
        else:
            out.printl("た・・・")
    elif y.af("欲望") < 4:  # :852–897
        out.printl(f"そういうことは良くないと断ろうとした{F()}だが、")
        if c.cflag[1] > 0:
            out.print(y.form_t())
            out.print("に変身した")
        out.printl(f"{T()}のあられもない様子に劣情を刺激されてしまい、")
        if is_male(data, f):
            out.print("胸の高鳴りを意識しながら部屋に迎え入れ")
        else:
            out.print("少しだけならばと部屋に迎え入れ")
        if arg1 > 0:
            out.printl("、")
            out.print("自分から")
            out.print(y.form_f())
            out.printl("に変身した・・・")
        else:
            out.printl("た・・・")
    else:  # :899–919 欲望が４以上
        if arg1 > 0:
            out.print("既に")
            out.print(y.form_f())
            out.print("に変身していた")
        else:
            out.print("ノックに応じた")
        out.printl(f"{F()}は言葉を交わすこともなく")
        out.printl(f"自らも興奮を堪え切れない様子で{T()}を部屋へと引き入れた。")
        out.printl(f"なりふり構わずに{T()}の唇を強引に奪うと")
        out.printl("そのままベッドへと押し倒す・・・")
    if c.cflag[99] > 0:  # :922–975 実行者の疲労
        out.printw()
        if c.cflag[99] > rand(30):  # :925–949 寝落ち
            out.printl(f"{T()}は淫欲と共に重い疲労感に悩まされている。")
            out.printl("心休まる相手との同衾が淫欲を鎮めたのか、日頃の疲れのせいか、")
            out.printl(f"ベッドの上で{F()}の身体を抱き寄せてしばらくするとそのまま寝入ってしまった。")
            out.printl()
            if y.suimin == 1:
                out.printl(f"深夜にふと目を覚ました{F()}は、背中に暖かい体温を感じた。")
                out.printl(f"振り向くと{T()}が抱きついたまま寝ていて離そうとしない。")
                if y.tc_("巨乳") > 0:
                    out.print("背中の柔らかい双球の感触")
                elif is_manly(ctx) or y.tc_("ふたなり") > 0:
                    out.print("尻に当たる硬い肉棒の感触")
                else:
                    out.print("首筋にかかる静かな吐息")
                out.printl("に赤面し身動きすることも出来ず、")
                out.printl(f"{T()}の寝顔に苦笑しながら再び眠りについた。")
            elif y.af("欲望") > 3 or y.self_ == 1:
                out.printl(f"せっかくその気になっていたのに、おあずけされた{F()}は")
                out.printl(f"{T()}の寝顔を見ながら自分を慰めた後、苦笑しながら眠りについた。")
            else:
                out.printl(f"{F()}が{T()}をぎゅっと抱きしめると、ぬくもりが一人ではない安心感を与えてくれる。")
                out.printl(f"そっと{T()}におやすみのキスをすると眠りについた。")
            return 0
        if y.suimin == 0:  # :952–973
            out.printl(f"{T()}は抑えきれない性欲と共に気怠い疲労感に悩まされている。")
            out.printl(f"一計を案じた{T()}は{F()}にマッサージを頼むことにした。")
            if c.cflag[99] > y.af("技巧") * 5:
                out.printl(f"{T()}は淫欲に苛まれ眠れぬほどであったが、")
                out.printl("日頃の疲れがよほど溜まっていたのか、")
                out.printl(f"{F()}のマッサージに身を任せてしばらくするとそのまま寝入ってしまった。")
                return 0
            out.printl(f"{F()}にマッサージをしてもらってしばらくすると、")
            out.print(f"{T()}は上気した顔で、次はここを揉んで欲しいと")
            if y.tc_("巨乳") > 0:
                out.printl("豊かな胸をさらけ出した・・・")
            elif y.tc_("男の娘") > 0:
                out.printl("たいらかな胸をさらけ出した・・・")
            elif is_penis(ctx):
                out.printl("勃起した肉棒をさらけ出した・・・")
            else:
                out.print("秘所をさらけ出した・・・")  # PRINTFORM（改行なし：:979 PRINTW で行が閉じる）
    out.printw()  # :979–982
    out.drawline()
    out.printl("暗い部屋に二人の息遣いだけが響いている・・・")
    out.printw()
    if arg == 1:  # :983–2643 SELECTCASE ARG
        yield from _case1(y)
    elif arg == 2:
        yield from _case2(y)
    elif arg == 4:
        yield from _case4(y)
    elif arg == 8:
        _case8(y)
    elif arg == 16:
        yield from _case16(y)
    elif arg == 32:
        _case32(y)
    _ablup1(ctx)  # :2645（TARGET はこの時点で FLAG:799）
    out.printw()  # :2646
    return 0


# --- CASE 1：Ｃ夜這い（:985–1368）----------------------------------------------------------------


def _case1(y: _Action) -> InputGen:
    ctx = y.ctx
    st, data, out = ctx.state, ctx.data, ctx.out
    rand = st.rng.rand
    T, F, L = y.T, y.F, y.L
    if (y.af("欲望") < 2 + rand(3) and y.suimin == 0) or (
        y.tc_("男の娘") > 0 and y.tf("ふたなり") <= 0 and is_female(data, y.f)
    ):  # :987–1063 愛撫
        if y.tc_("男の娘") > 0:
            if y.suimin == 1:
                out.printl(f"ごそごそとベッドを探る気配で{F()}は起きてしまったようだ・・・")
                out.printl(f"眠そうに目を擦りながら{T()}に気付くと、微笑んでベッドに招く。")
                out.printl("まだ寝惚けているのか、夢だと思っているのかもしれない・・・")
                out.printw()
            out.printl(f"{F()}は{T()}と軽くキスを交わしながら、")
            out.printl(f"指で{T()}の股間の突起を愛撫した。")
            out.printl("溢れ出る先走り蜜がくちゅくちゅと卑猥な飛沫を上げて、ベッドのシーツを汚していく。")
            out.printw()
            out.printl("濡れ光る先端を丁寧に撫で上げながら、")
            out.printl("すっかり勃起した淫茎を摘まんでコリコリと弄びつつ、")
            out.printl("指先でくすぐるように擦って程良い刺激を与えていく。")
            out.printw()
            out.printl(f"{T()}は発情した少女の顔で涎を零す。")
            if is_male(data, y.f) and y.tf("男の娘") <= 0:
                out.printl(f"自分とは違う、{F()}の男らしい指使いでの愛撫は自慰では味わえない不思議な安心感。")
            out.printl(f"身体も脳も性感帯も{F()}とひとつに溶け合うような感覚に")
            out.printl(f"ペニスを触れられながらも女の子になったような倒錯感がないまぜになり、{T()}は自身の存在を疑った。")
            out.printw()
            out.printl("もっと強くと言われて男の娘クリトリスを扱く指先に力を込めると、")
            out.printl(f"{T()}は大きく痙攣してそのまま絶頂した・・・")
            if y.tc_("未熟") != 1:  # :1013–1014
                L[153] = 1
        else:
            out.printl(f"{F()}は{T()}と軽くキスを交わしながら、")
            out.printl(f"指で{T()}の股間の突起を愛撫した。")
            out.printl("溢れ出る先走り蜜がくちゅくちゅと卑猥な飛沫を上げて、ベッドのシーツを汚していく。")
            out.printw()
            out.printl("濡れ光る淫肉を丁寧に撫で上げながら、")
            out.printl("すっかり勃起した淫核を摘まんでコリコリと弄びつつ、")
            out.printl("舌先でくすぐるように舐め上げて程良い刺激を与えていく。")
            out.printw()
            if y.tsish():
                out.printl(f"{T()}の知らない女体の神秘、")
                if is_female(data, y.f):
                    out.printl(f"{F()}の繊細で柔らかい愛撫は男相手では味わえない至上の快楽。")
                out.printl(f"身体も脳も性感帯も{F()}とひとつに溶け合うような感覚に")
                out.printl(f"自分が無くなるような恐怖と包まれるような安心感がないまぜになり、{T()}は自身の存在を疑った。")
                out.printw()
            out.printl("もっと強くと言われてクリトリスを弄る指先に力を込めると、")
            out.printl(f"{T()}は大きく痙攣してそのまま絶頂した・・・")
        out.printw()  # :1036
        y.executor()
        L[0] = 50
        L[122] = 1
        _prison(ctx, L)
        _ablup1(ctx)
        y.switch()
        y.inc_f_l()
        _prison(ctx, y.L)
        _ablup1(ctx)
        return 0
    if y.tf("ふたなり") > 0 or is_male(data, y.f):  # :1066–1307 スマタ
        if y.tc_("男の娘") > 0:  # :1067–1135
            out.printl(f"{T()}は背後の{F()}のペニスを太股で挟み、")
            if y.suimin == 0:
                out.printl("四つん這いになって「このまま激しくシてほしい」とお尻を突き出した。")
            out.printl("挿入しなければ大丈夫だという誘惑に負け、")
            if y.suimin == 1:
                out.printl("背面騎乗位で素股を開始した。")
            else:
                out.printl(f"{F()}は腰を使って素股を開始した。")
            out.printw()
            out.printl(f"反り返った怒張が先端から根元まで{T()}の淫茎を擦り上げ、")
            out.printl("二本のペニスをまとめて下腹に押し付けられる強烈な快感となって理性を焦がしていく。")
            if is_male(data, y.f) and y.tf("男の娘") <= 0:
                out.printl(f"{F()}の肉棒の逞しさといったら、自分のものとは比べ物にならない。")
                out.printl("これと比べたら自分のものはただ射精できるだけのクリトリスといってもいい。")
                out.printl(f"その敗北感に{T()}は気が狂いそうなほど興奮した。")
            if y.suimin == 1:  # :1087–1099
                if y.ac("Ａ感覚") >= 2 and y.tc_("淫尻") > 0:
                    y.lcount = 1
                    out.printl("興奮の最高潮に達して激しさを増すばかりのピストンに二人の先走り汁が絡まり")
                    out.printl(f"腰が跳ねた拍子に亀頭が{T()}の窄まりへとズレて先端が腸内に入りかけている・・・")
                    out.printl(f"完全に理性を失った{T()}はそのままズブズブと腰を沈める。")
                    out.printl("突然の挿入にも関わらず、とろとろに蕩けた尻肉は容易く男根を飲み込み、")
                    out.printl(f"{T()}は理性の糸が切れたように蕩けた表情で")
                    out.printl("なし崩し背面騎乗位逆レイプの快楽に身を任せた・・・")
                    out.printw()
                    return (yield from _a_sex(y))  # :1098 GOTO A_SEX
            elif y.af("欲望") + rand(4) >= 6:  # :1102–1134
                y.lcount = 1
                out.printl("興奮の最高潮に達して激しさを増すばかりのピストンに二人の先走り汁が絡まり")
                out.printl(f"腰が大きく離れた拍子に亀頭が{T()}の窄まりへとズレて先端が腸内に入りかけている・・・")
                out.printw()
                if y.ac("Ａ感覚") < 2:
                    out.printl(f"「これ以上は」と首を後ろに向けた{T()}の唇を口付けが塞ぎ、")
                    out.printl(f"完全に理性を失った{F()}がペニスを窄まりにあてがった。")
                    out.printl("オトコなのに男性器に犯されてしまう。その事実は混乱と興奮を呼び、")
                    out.printl(f"目を見開いた{T()}もまた挿入の悦びに抗えず、")
                    out.printl(f"すぐに幸福に蕩けた表情で{F()}の求愛にキスで応えた。")
                    out.printw()
                    out.printl("ズブズブとペニスが腸内に押し入ってくる感触と共に、")
                    out.printl("異物に不慣れなアヌスが怯えるようにひゅくんっと痙攣する・・・")
                    sc = _self_call(ctx)
                    out.printl(f"（{sc}はオトコ、こんな見た目でも{sc}は・・・。でも今確かにオンナになってる。）")
                    out.printl(f"{T()}は、自分がどんどんオトコに戻れなくなっていくのを感じた。")
                    out.printw()
                    return (yield from _a_lostvirgin_sex(y))  # :1121 GOTO（:1123 は到達しない）
                out.printl(f"完全に理性を失った{F()}はそのままズブズブと腰を押し進めてくる。")
                out.printl("これでも一応はオトコなのにオトコに犯されることを望んでいるオンナの自分がいる。")
                out.printl("突然の挿入にも関わらず、とろとろに蕩けた腸肉は容易く男根を受け入れ、")
                out.printl(f"{T()}もまた理性の糸が切れたように蕩けた表情でキスを求め、")
                out.printl("口づけを交わしながらのなし崩しセックスに身を任せた・・・")
                out.printw()
                return (yield from _a_sex(y))  # :1132
        else:  # :1136–1216
            out.printl(f"{T()}は{F()}のペニスを太股で挟み、")
            if y.suimin == 0:
                out.printl("首に腕を回して「このまま激しくシてほしい」と囁いた。")
            out.printl("挿入しなければ大丈夫だという誘惑に負け、")
            if y.suimin == 1:
                out.printl("騎乗位で素股を開始した。")
            else:
                out.printl(f"{F()}は腰を使って素股を開始した。")
            out.printw()
            out.printl(f"勃起しきった怒張が先端から根元まで{T()}の淫核を擦り上げ、")
            out.printl("触れ合ったまま離れずに強烈な快感となって理性を焦がしていく。")
            if y.tsish():
                out.printl("こんな感覚は男では味わえないし、女の身体でも一人遊びでは得られない。")
                out.printl("女の身体で熱い肉棒を迎えなければこの快楽はない。")
                out.printl(f"その事実に{T()}は気が狂いそうなほど興奮した。")
            if y.suimin == 1:  # :1156–1168
                if y.tc_("処女") < 1 and y.tc_("淫壷") > 0:
                    y.lcount = 1
                    out.printl("興奮の最高潮に達して激しさを増すばかりのピストンに愛液が絡まり")
                    out.printl(f"亀頭が{T()}のワレメを押し広げて先端が膣内に入りかけている・・・")
                    out.printl(f"完全に理性を失った{T()}はそのままズブズブと腰を沈める。")
                    out.printl("突然の挿入にも関わらず、とろとろに蕩けた膣肉は容易く男根を飲み込み、")
                    out.printl(f"{T()}は理性の糸が切れたように蕩けた表情で")
                    out.printl("なし崩し騎乗位逆レイプの快楽に身を任せた・・・")
                    out.printw()
                    return (yield from _v_sex(y))  # :1167
            else:
                from .battle.sexcom import check_holyvirgin

                if y.af("欲望") + rand(4) >= 6 and check_holyvirgin(ctx) == 0:  # :1171–1215
                    y.lcount = 1
                    out.printl("興奮の最高潮に達して激しさを増すばかりのピストンに愛液が絡まり")
                    out.printl(f"亀頭が{T()}のワレメを押し広げて先端が膣内に入りかけている・・・")
                    out.printw()
                    if y.tc_("処女") > 0:
                        out.printl(f"「これ以上は」と言いかけた{T()}の唇を口付けが塞ぎ、")
                        out.printl(f"完全に理性を失った{F()}がペニスをワレメにあてがった。")
                        if y.ts == 1:
                            out.printl("オトコなのに処女を失ってしまう。その事実は混乱と興奮を呼び、")
                        out.printl(f"目を見開いた{T()}もまた挿入の悦びに抗えず、")
                        out.printl(f"すぐに幸福に蕩けた表情で{F()}の求愛にキスで応えた。")
                        out.printw()
                        out.printl("ズブズブとペニスが膣内に押し入ってくる感触と共に、")
                        out.printl("つぅと破瓜の血が流れ出す・・・")
                        if y.ts == 1:
                            out.printl(f"（{_self_call(ctx)}はオトコ、変身を解けば戻れる。でも今確かにオンナになった。）")
                            out.printl(f"{T()}は何故か、もうオトコに戻れない気がした。")
                        out.printl()
                        out.printl("処女喪失")
                        out.printw()
                        return (yield from _v_lostvirgin_sex(y))  # :1195（:1197–1203 は到達しない）
                    out.printl(f"完全に理性を失った{F()}はそのままズブズブと腰を沈めてくる。")
                    if y.ts == 1:
                        out.printl("本当はオトコなのにオトコに犯されることを望んでいるオンナの自分がいる。")
                    out.printl("突然の挿入にも関わらず、とろとろに蕩けた膣肉は容易く男根を受け入れ、")
                    out.printl(f"{T()}もまた理性の糸が切れたように蕩けた表情でキスを求め、")
                    out.printl("口づけを交わしながらのなし崩しセックスに身を任せた・・・")
                    out.printw()
                    return (yield from _v_sex(y))  # :1213
        out.printl(f"{T()}は唇を噛みながら、何とか声を堪えている。")  # :1218–1307
        out.printw()
        out.print("やがて絶頂が近付くと")
        if y.suimin == 1:
            out.print(f"寝ている{F()}の唇に口づけをしながら")
        else:
            out.print("二人は口づけを交わしながら")
        out.printl("腰の動きを加速させ、")
        if y.tf("未熟") == 1:
            out.printl(f"{F()}と{T()}は同時に絶頂した・・・")
        else:
            out.printl(f"{F()}が射精すると共に{T()}も絶頂した・・・")
        if y.ts == 1:
            out.printl(f"女体の絶頂は期待以上のもので{T()}はまたひとつ深みへと嵌ったことを自覚した・・・")
        out.printw()
        y.executor()
        L[0] = 50  # :1239
        if y.tc_("男の娘") > 0:  # :1241–1266
            if y.tc_("未熟") != 1:
                L[153] = 1
            if y.lcount:
                L[2] = 50
                L[121] = 1
                if y.tf("未熟") != 1:
                    L[123] = 1
        elif y.lcount:
            L[1] = 50
            L[120] = 1
            if y.tf("未熟") != 1:
                L[123] = 1
            y.nakadashi = 1
        L[122] = 1
        y.inc_t_f()
        _prison(ctx, L)
        _ablup1(ctx)
        y.ninsin_if()  # :1280–1281
        y.switch()
        y.target_side_c()
        yield from y.pill_if()
        return 0
    # :1310–1367 女同士（貝合わせ）
    if y.suimin == 1:
        out.printl(f"{T()}は自らの秘所を{F()}と重ね合わせ、")
        out.printl("起こさないように静かに淫貝を擦り合わせた。")
    else:
        out.printl(f"{F()}は自らの秘所を{T()}と重ね合わせ、")
        out.printl("口づけを交わしながら淫貝を擦り合わせた。")
    out.printl("膣肉が絡み合ってぐじゅぐじゅと卑猥な音を立て、否応にも背徳感を煽り立てる。")
    if y.tsish():
        out.printl(f"オンナとしてレズを体感する自分と、{F()}とのレズ行為を俯瞰で見ているオトコの自分がいる。")
        out.printl("そのイメージは快感を倍増させ、風船のように膨れ上がり張りつめさせる。")
    out.printw()
    out.print("やがて絶頂が近付くと")
    if y.suimin == 0:
        out.print("二人は互いの")
    out.printl("クリトリスを指で刺激しながら腰の動きを加速させ、")
    out.printl("そのまま一気に二人で果てた・・・")
    out.printw()
    y.executor()
    L[0] = 50
    L[122] = 1
    y.inc_t_f()
    _prison(ctx, L)
    _ablup1(ctx)
    y.switch()
    y.L[0] = 50
    y.L[122] = 1
    y.inc_f_l()
    _prison(ctx, y.L)
    _ablup1(ctx)
    return 0


# --- CASE 2：Ｖ夜這い（:1370–1778）----------------------------------------------------------------


def _case2(y: _Action) -> InputGen:
    from .battle.sexcom import check_holyvirgin

    ctx = y.ctx
    st, data, out = ctx.state, ctx.data, ctx.out
    rand = st.rng.rand
    T, F, L = y.T, y.F, y.L
    if (
        (y.tf("ふたなり") < 1 and is_female(data, y.f))
        or check_holyvirgin(ctx) == 1
        or (y.af("欲望") < 2 + rand(3) and y.suimin == 0)
    ):  # :1372–1435 クンニ／貝合わせ
        if y.suimin == 1:
            out.printl(f"{T()}は自らの秘所を{F()}と重ね合わせ、")
            out.printl("起こさないように静かに淫貝を擦り合わせた。")
            out.printl("膣肉が絡み合ってぐじゅぐじゅと卑猥な音を立て、否応にも背徳感を煽り立てる。")
            if y.tsish():
                out.printl(f"オンナとしてレズを体感する自分と、{F()}とのレズ行為を俯瞰で見ているオトコの自分がいる。")
                out.printl("そのイメージは快感を倍増させ、風船のように膨れ上がり張りつめさせる。")
            out.printw()
            out.print("やがて絶頂が近付くと腰の動きを加速させ、大きく痙攣して果てた・・・")
            out.printw()
        else:
            out.printl(f"{F()}は{T()}の股間に顔をうずめ、")
            out.printl(f"口で{T()}の秘所を愛撫した。")
            out.printl("丁寧に舌で肉穴をほぐし、溢れ出る愛蜜を吸い上げていく。")
            out.printw()
            out.printl(f"{F()}の攻めに{T()}は身体を震わせて反応しつつ")
            out.printl(f"大腿で顔を挟み込むようにしながら{F()}の髪に指を絡めて愛しそうに撫でている。")
            out.printl(f"やがて{F()}の吸引が激しさを増していく。")
            if y.tsish():
                out.printl("膣口の入り口を甘く愛撫されるさざ波のような快感と、不意打ちされるＧスポットの刺激に満たされ、")
                out.printl(f"{T()}は決してオトコでは得られない蜜壷の快楽に酔いしれている。")
            out.printw()
            out.printl(f"強く膣口を吸い上げられて{T()}が痺れたように身を捩り、")
            out.printl("本気の膣イキに恍惚としながら絶頂に達した・・・")
        out.printw()
        y.executor()
        L[1] = 50
        L[120] = 1
        L[122] = 1
        y.inc_t_f()
        _prison(ctx, L)
        _ablup1(ctx)
        y.switch()
        y.inc_f_l()
        _prison(ctx, y.L)
        _ablup1(ctx)
        return 0
    if y.tc_("処女") > 0:  # :1437–1630 処女・挿入
        if y.suimin == 1:
            out.printl(f"瞳を潤わせて{F()}のペニスを丹念にしゃぶるとそれは猛々しく勃起し、")
            out.printl(f"{T()}は自らのワレメに{F()}のペニスをあてがった。")
            out.printl("痛くないようにゆっくりと亀頭を挿入し、ずぶずぶと飲み込んでいく。")
        elif y.c.talent[800] == 4 and (y.tc_("淫乱") > 0 or y.lover_ft() > 0):  # 処女人妻
            out.printl(f"{T()}は瞳を潤わせて、「夫ではなく、{F()}に初めてを捧げたい」と懇願する。")
            out.printl(f"本当に良いのか、と問う{F()}に{T()}は頬を染めながら頷く、")
            out.printl("何か覚悟が決まっているように、左手の薬指にはめている結婚指輪を外していた。")
            out.printl(f"怯えつつ、恥らいながら、{T()}は{F()}に跨ると、手を繋いだまま腰を浮かせた、")
            out.printl("少し恥ずかしそうな表情で腰を動かし膣口と亀頭をあわせると、ゆっくりと腰を落とす。")
            out.printl(f"ずぷ、と、{_callname_at(ctx, y.arg)}の膣内へと{_callname_at(ctx, GameState.MASTER)}の一物が挿入された。")
        else:
            if y.inc_tf() > 0:  # :1453–1497
                out.print(f"{F()}は")
                out.print(_family(ctx, st.flag[799]))
                if is_female(data, y.c) and y.tc_("変身時ＴＳ") > 0 and y.c.cflag[1] > 0:
                    out.printl("が女体化して入ってきた時から予感はあった。")
                elif y.tf("変身時ＴＳ") > 0 and y.f.cflag[1] > 0 and is_male(data, y.f):
                    out.printl("に男性化するよう命じられた時から予感はあった。")
                out.printl(f"今から{T()}の処女を捧げられるのだろう、と。")
                out.printl(f"触手に奪われる前に愛する家族に…{F()}も同じ立場ならそうしただろう。")
                out.printw()
            if y.ts == 1:
                out.printl(f"オトコの自分が挿入をねだって変に思われたら、と一抹の不安に駆られる{T()}。")
            out.printl(f"瞳を潤わせて「犯して欲しい」と懇願する{T()}の誘惑に耐えきれず、")
            out.printl(f"{F()}は{T()}のワレメに自らのペニスをあてがった。")
            out.printl("痛がらないようにゆっくりと亀頭を挿入し、ずぶずぶと押し込んでいくと、")
            out.printl(f"自ら受け入れるように{T()}が脚を絡めて抱き寄せた。")
        out.printw()  # :1508
        out.printl("ペニスを半ばまで挿入したところで膜の破れる感触と共に破瓜の証がつぅと滲み出るが、")
        out.printl(f"{T()}は涙を浮かべながらも幸せそうな表情をしている・・・")
        if y.ts == 1:
            out.printl(f"（{_self_call(ctx)}はオトコ、変身を解けば戻れる。それでも確かにオンナになった・・・）")
            out.printl(f"{T()}は何故か、もうオトコに戻れない気がした。")
        out.printl()
        out.printl("処女喪失")
        out.printw()
        return (yield from _v_lostvirgin_sex(y))
    # :1632–1778 非処女・挿入
    if y.tf("未熟") == 1 or y.suimin == 1:
        out.printl(f"{T()}は{F()}に覆いかぶさると、")
        out.printl("濡れそぼったヴァギナで勃起したペニスの先端に口づけをした。")
        out.printl("そのままゆっくり腰を降ろして膣奥まで飲み込んでいくと、")
        out.printl("至福の表情を浮かべながら抽送を開始した・・・")
    else:
        out.printl(f"{F()}は{T()}に覆いかぶさると、")
        out.printl("勃起しきったペニスを膣奥に根元まで挿入して深い抽送を開始した。")
        out.printl(f"すでに濡れきっていた{T()}は痛がる様子も無く、")
        out.printl("むしろ快楽を貪るようにして互いの口づけを求め合う・・・")
    if y.tsish():
        out.printl("オトコの身体では決して得られない、膣内に肉棒を受け入れ満たされる感覚に身を震わせる。")
    out.printw()
    return (yield from _v_sex(y))


def _v_lostvirgin_sex(y: _Action) -> InputGen:
    """`$V_LOSTVERGIN_SEX`:1518–1630（→ ENDIF:1778 → ENDSELECT）。"""
    from .battle.ninsin import estrus_text

    ctx = y.ctx
    st, out = ctx.state, ctx.out
    T, F, L = y.T, y.F, y.L
    if y.suimin == 1:
        out.printl("にちゅにちゅと粘着質な水音と荒い息遣いが部屋の空気を震わせる。")
        out.printl(f"{F()}が起きないようにゆっくりと深く、熱い肉棒で膣内を満たし、")
    else:
        out.printl("パンパンと肉と肉のぶつかる音と荒い息遣いが部屋の空気を震わせる。")
        out.printl("激しくはないが情熱的なピストンに膣内を抉られ、")
    out.printl(f"{T()}は痛みよりも快楽のほうが勝っている様子で声を堪えている。")
    husband = "夫ではなく" if y.c.talent[800] == 4 and (y.tc_("淫乱") > 0 or y.lover_ft() > 0) else ""
    out.printl(f"深々とペニスを咥えこんだ秘所は、{husband}{F()}の彼女を女にした逞しい男根の形を覚えた。")
    out.printw()
    if y.suimin == 1:  # :1531–1543
        out.printl(f"{F()}のペニスが硬さと太さを増し限界を予感させると、")
        if y.tf("未熟") == 1:
            out.printl(f"初めての挿入にも関わらず、{T()}がアクメを迎えたのは同時だった・・・")
        elif y.tc_("淫乱") > 0 or y.lover_ft() > 0:
            out.printl(f"{T()}は足を絡めて無言で中出しを促した。")
            out.printl("初めての挿入にも関わらず二人は同時に絶頂し、勢いよく精液が膣内へと注ぎこまれていった・・・")
            y.nakadashi = 1
        else:
            out.printl(f"ギリギリで{F()}のペニスを引き抜いて射精させるのと、")
            out.printl(f"初めての挿入にも関わらず{T()}が絶頂したのは同時だった・・・")
    else:  # :1544–1566
        if y.tf("未熟") == 1:
            out.printl(f"限界に達した{F()}が恍惚の表情を浮かべて絶頂するのと、")
            out.printl(f"初めての挿入にも関わらず{T()}がアクメを迎えたのは同時だった・・・")
        elif y.tc_("淫乱") > 0 or y.lover_ft() > 0:
            if y.c.talent[800] == 4:
                out.printl("辛うじて残っていた理性が中出しだけは回避しなければと警告するが、")
                out.printl(f"{T()}は頬を赤くしながら、情熱的なキスで{F()}の唇に塞ぐと、")
                out.printl(f"ずっしりと体重をかけて{F()}のペニスを奥深くまで咥えこみ、無言で膣内射精をねだった。")
                out.printl(f"{F()}もまた我慢できなくなり、その誘いに応えて膣奥へと精液を解き放った、")
                out.printl(f"誰にも染められていなかった無垢な{estrus_text(ctx, st.target)}子宮が白く染め上げられていく。")
                out.printl(f"{T()}は甘い喘ぎ声を漏らし、自らの最も大事な場所に夫以外の子種を受け入れる喜びに浸っていた・・・")
            else:
                out.printl(f"限界に達した{F()}が腰を引こうとすると、")
                out.printl(f"{T()}は足を絡めて無言で中出しを懇願した。")
                out.printl("初めての挿入にも関わらず二人は同時に絶頂し、勢いよく精液が膣内へと注ぎこまれていった・・・")
            y.nakadashi = 1
        else:
            out.printl(f"限界に達した{F()}がペニスを引き抜いて射精するのと、")
            out.printl(f"初めての挿入にも関わらず{T()}が絶頂したのは同時だった・・・")
    if y.ts == 1:
        out.printl(f"長い長い絶頂を迎え、{T()}は自他の区別も時間も消え去った純白に包まれる。")
        out.printl("無限の幸せが続くような感覚から目を覚ますと、恍惚とした満足気な笑みを浮かべた・・・")
    out.printw()
    y.executor()
    L[1] = 50
    L[10] = 50
    L[120] = 2
    L[122] = 1
    if y.tf("未熟") != 1:
        L[123] = 1
    y.inc_t_f()
    y.c.talent[ctx.data.index_of("TALENT", "処女")] = -1  # :1588
    y.c.cflag[206] = 5 if y.lover_tf() > 0 else 6  # :1590–1594
    _prison(ctx, L)
    _ablup1(ctx)
    y.ninsin_if()
    y.switch()
    y.target_side_c()
    yield from y.pill_if()
    return 0


def _v_sex(y: _Action) -> InputGen:
    """`$V_SEX`:1649–1777（→ ENDIF:1778 → ENDSELECT）。"""
    from .battle.ninsin import estrus_text

    ctx = y.ctx
    st, out = ctx.state, ctx.out
    T, F, L = y.T, y.F, y.L
    if y.suimin == 1:
        out.printl(f"逆レイプ騎乗位で腰を振り続ける{T()}に、")
        out.printl(f"{F()}は寝ながら性交快楽を与えられ微かな喘ぎ声を漏らしている。")
        out.printl(f"{F()}が起きてしまうスリルに酔いしれながら、")
        out.printl("パンパンと打ちつける淫音が響くたびに快楽が増幅されていく。")
    elif y.tf("未熟") == 1:
        out.printl(f"まるで逆レイプするかのように騎乗位で腰を振り続ける{T()}に、")
        out.printl(f"{F()}もまた未熟な男根を膣肉にシゴき上げられる快楽に我を忘れている。")
        out.printl("どちらともなく唇を交わして唾液交換の美酒に酔いしれながら、")
        out.printl("パンパンと打ちつける淫音が響くたびに快楽が増幅されていく。")
    else:
        y.koukan()
    out.printw()
    if y.tf("未熟") == 1:  # :1677–1705
        out.printl(f"やがて{F()}がほどなく限界に達し、{T()}もまた絶頂を迎えた。")
        out.printl(f"膣内にペニスを受け入れたまま倒れかかった{T()}の表情は")
    elif y.tc_("淫乱") > 0 or y.lover_ft() > 0:
        out.printl("辛うじて残っていた理性が中出しだけは回避しなければと警告するが、")
        if y.suimin == 1:
            out.printl("女の本能が妊娠を望み、脳が膣内射精の快楽信号を欲している。")
            out.printl(f"昂った欲情の内奥で{F()}の子種をすべて受け止めた。")
        else:
            out.printl(f"{T()}は{F()}の腰に足を絡めて放さない。")
            out.printl("それどころか「出して、膣内に出して」と懇願されては誘惑に耐えきれるはずもなく、")
            out.printl(f"昂った欲情の中で{F()}は内奥で子種を一気に放出した。")
        if y.ts == 1:
            out.printl("熱い精液を受け止めた満足感と、このカラダは妊娠できるのかという好奇心に、")
        out.printl(f"{estrus_text(ctx, st.target)}子宮でドクドクと精液を受け止める{T()}の表情は")
        y.nakadashi = 1
    else:
        if y.ts == 1:
            out.printl("熱い精液を受け止めたい誘惑と、このカラダは妊娠できるのかという好奇心に心が揺らぐも、")
        out.printl("辛うじて残っていた理性が中出しだけは回避しなければと警告する。")
        out.printl(f"絶頂を迎えた{T()}から爆発寸前のペニスが引き抜かれると、")
        out.printl(f"軽くフェラチオをしてから{F()}を口の中で射精させる。")
        out.printl(f"ごくごくと精液を飲み干していく{T()}の表情は")
        L[324] = 1
    out.printl("まるで普段とは別人のように恍惚としている・・・")
    out.printl()
    if y.suimin == 1:  # :1709–1725
        out.printl(f"やがて落ち着きを取り戻した{T()}は")
        if y.tc_("淫乱") > 0:
            out.printl(f"いまだ眠り続ける{F()}を逆レイプしてしまった背徳感に胸を熱くした。")
            out.printl(f"起きない{F()}が悪いと言い訳を呟きながら半勃ち状態のペニスをお掃除フェラで綺麗にすると、")
            out.printl("名残惜しそうに部屋を後にした。")
        else:
            out.printl(f"正気に戻り{F()}を逆レイプしてしまった罪悪感に胸を絞めつけられた。")
            out.printl(f"謝罪の言葉を繰り替えし囁きながら{F()}の体を綺麗に拭いて証拠隠滅すると")
            out.printl("追われるように部屋を後にした。")
        out.printw()
        if st.rng.rand(10) == 0:
            out.printl(f"何事もなかったかのように静まり返った、しかし性臭の漂う部屋で{F()}は")
            out.printl("先ほどの夢のような出来事を反芻しながら自慰に耽っていた・・・")
    out.printw()
    y.executor()
    L[1] = 50
    L[120] = 2
    L[122] = 1
    if y.tf("未熟") != 1:
        L[123] = 1
    L[124] = L[324]
    y.inc_t_f()
    _prison(ctx, L)
    _ablup1(ctx)
    y.ninsin_if()
    y.switch()
    y.target_side_c()
    yield from y.pill_if()
    return 0


# --- CASE 4：Ａ夜這い（:1780–2255）----------------------------------------------------------------


def _case4(y: _Action) -> InputGen:
    ctx = y.ctx
    st, data, out = ctx.state, ctx.data, ctx.out
    rand = st.rng.rand
    T, F, L = y.T, y.F, y.L
    f799 = st.flag[799]
    if y.tc_("男の娘") > 0 and y.ac("Ａ感覚") <= 3 and is_penis(ctx, f799):  # :1783–1953
        if y.suimin == 1:
            out.printl(f"瞳を潤わせて{F()}のペニスを丹念にしゃぶるとそれは猛々しく勃起し、")
            out.printl(f"{T()}は自らのアヌスに{F()}のペニスをあてがった。")
            out.printl("痛くないようにゆっくりと亀頭を挿入し、ずぶずぶと飲み込んでいく。")
        elif y.c.talent[800] == 4 and (y.tc_("淫乱") > 0 or y.lover_ft() > 0):
            out.printl(f"{T()}は瞳を潤わせて、「夫ではなく、{F()}に身体を捧げたい」と懇願する。")
            out.printl(f"本当に良いのか、と問う{F()}に{T()}は頬を染めながら頷く、")
            out.printl("何か覚悟が決まっているように、左手の薬指にはめている結婚指輪を外していた。")
            out.printl(f"怯えつつ、恥じらいながら、{T()}は{F()}に背を向けると、四つん這いになってお尻を掲げた、")
            out.printl("少し恥ずかしそうな表情で腰を動かし菊穴と亀頭をあわせると、ゆっくりとお尻を押しつける。")
            out.printl(f"ずぷ、と、{_callname_at(ctx, y.arg)}の腸内へと{_callname_at(ctx, GameState.MASTER)}の一物が挿入された。")
        else:
            if y.inc_tf() > 0:  # :1799–1843
                out.print(f"{F()}は")
                out.print(_family(ctx, f799))
                if y.tc_("男の娘") > 0 and y.tc_("変身時男の娘") < 0 and y.c.cflag[1] > 0:
                    out.printl("が男の娘になって入ってきた時から予感はあった。")
                elif y.tf("変身時ＴＳ") > 0 and y.f.cflag[1] > 0 and is_male(data, y.f):
                    out.printl("に男性化するよう命じられた時から予感はあった。")
                out.printl(f"今から{T()}の肉体を捧げられるのだろう、と。")
                out.printl(f"触手に蹂躙される前に愛する家族に…{F()}も同じ立場ならそうしたのだろうか。")
                out.printw()
            out.printl(f"一応はオトコの自分が挿入をねだって変に思われたら、と一抹の不安に駆られる{T()}。")
            out.printl(f"四つん這いになり瞳を潤わせて「犯して欲しい」と懇願する{T()}の誘惑に耐えきれず、")
            out.printl(f"{F()}は{T()}の窄まりに自らのペニスをあてがった。")
            out.printl("痛がらないようにゆっくりと亀頭を挿入し、ずぶずぶと押し込んでいくと、")
            out.printl(f"自ら受け入れるように{T()}がお尻を掲げて力を抜いた。")
        out.printw()  # :1851
        out.printl("ペニスを半ばまで挿入したところでまだ異物に慣れ始めたばかりのアヌスが怯えるようにひゅくんっと痙攣するが、")
        out.printl(f"{T()}は涙を浮かべながらも幸せそうな表情をしている・・・")
        sc = _self_call(ctx)
        out.printl(f"（{sc}はオトコ、こんな見た目でも{sc}は・・・。でも今確かにオンナになってる。）")
        out.printl(f"{T()}は、自分がどんどんオトコに戻れなくなっていくのを感じた。")
        out.printw()
        return (yield from _a_lostvirgin_sex(y))
    if y.tc_("男の娘") > 0 and is_penis(ctx, f799):  # :1955–2095
        if y.tf("未熟") == 1 or y.suimin == 1:
            out.printl(f"{T()}は{F()}にお尻を向けると、")
            out.printl("濡れそぼったアヌスで勃起したペニスの先端に口づけをした。")
            out.printl("そのままゆっくり腰を進めて腸奥まで飲み込んでいくと、")
            out.printl("至福の表情を浮かべながら抽送を開始した・・・")
        else:
            out.printl(f"{F()}は{T()}を四つん這いにさせると、")
            out.printl("勃起しきったペニスを腸奥に根元まで挿入して深い抽送を開始した。")
            out.printl(f"すでに腸愛液で濡れきっていた{T()}は痛がる様子も無く、")
            out.printl("むしろ快楽を貪るようにして首を回して互いの口づけを求め合う・・・")
        out.printl("女の子扱いされなければ得られない、体内に肉棒を受け入れ満たされる感覚に身を震わせる。")
        out.printw()
        return (yield from _a_sex(y))
    if (y.tf("ふたなり") < 1 and is_female(data, y.f)) or y.af("欲望") < 2 + rand(3):  # :2096–2155 尻愛撫
        if y.suimin == 1:
            out.printl(f"{T()}は{F()}のアヌスに口付けし、丁寧に愛撫した。")
            out.printl("十分にほぐれたアヌスに指を挿入していき、くちゅくちゅと前後に動かしていく。")
        else:
            out.printl(f"{F()}は{T()}と口付けし、")
            out.printl("腰に腕を回して尻穴を丁寧に愛撫した。")
            out.printl("十分にほぐれたアヌスに指を挿入していき、くちゅくちゅと前後に動かしていく。")
        out.printw()
        if y.ts == 1:
            out.printl("この感覚だけはオトコもオンナも変わらない。")
            out.printl("尻穴で膣口以上の快楽を得られれば、オトコの身体でもオンナの快楽を疑似的に楽しめる。")
            out.printl(f"だから{T()}はオンナの身体でも敢えてアナル快楽を求める。")
            out.printw()
        out.printl("指だけでは物足りないのか、菊穴はくっぽりと良い具合に口を開いている。")
        if y.suimin == 1:
            out.printl(f"{T()}は自分と{F()}のアナルに双頭ディルドを挿入して繋ぐと、")
        else:
            out.printl(f"期待に目を潤わせる{T()}に{F()}がアナルバイブを挿入すると、")
        out.printl(f"尻穴を押し広げられる悦びに{T()}の興奮が最高潮に達する。")
        out.printw()
        out.printl("完全に性感帯として開発された尻穴がもたらす快楽は大きく、")
        out.printl(f"絶頂に達した{T()}は涎を垂らしながら痙攣している・・・")
        out.printw()
        y.executor()
        L[2] = 50
        L[121] = 1
        L[122] = 1
        y.inc_t_f()
        _prison(ctx, L)
        _ablup1(ctx)
        y.switch()
        y.inc_f_l()
        _prison(ctx, y.L)
        _ablup1(ctx)
        return 0
    # :2157–2254 アナルセックス・相手竿
    if y.ts == 1:
        out.printl("アナルの感覚だけはオトコもオンナも変わらない。")
        out.printl("尻穴で膣口以上の快楽を得られれば、オトコの身体でもオンナの快楽を疑似的に楽しめる。")
        out.printl(f"だから{T()}はオンナの身体でも敢えてアナル快楽を求める。")
        out.printw()
    if y.suimin == 1:
        out.printl(f"後ろの穴を犯して欲しい情欲に憑りつかれた{T()}は")
        out.printl(f"{F()}のペニスに情熱的な奉仕をして勃起させると、")
        out.printl(f"自ら尻を突き出して{F()}に覆いかぶさった。")
        out.printw()
        out.printl("アヌスに勃起しきったペニスを挿入していくと、")
        out.printl("尻肉がまるで女性器のようにぎゅうぎゅうと収縮する・・・")
        out.printw()
        out.printl(f"{F()}を起こさないようにゆっくり腰を上下する{T()}・・・")
        out.printl("「後ろの穴ならセックスじゃない」")
        out.printl("そんな言い訳が逆に枷を取り払ってしまったかの如く、")
        out.printl("ぐちゅぐちゅと打ちつける淫音が響くたびに快楽が増幅されていく。")
    else:
        out.printl(f"{T()}は後ろの穴を犯して欲しいと言い、")
        out.printl(f"自ら尻を突き出して{F()}を誘惑した。")
        out.printw()
        out.printl("「後ろの穴ならセックスじゃない」")
        out.printl("そう言い聞かせる言葉は目の前の魅力的な肉穴の前にすぐに霧散してしまい、")
        out.printl(f"{F()}は{T()}に覆いかぶさった。")
        out.printl("勃起しきったペニスをアヌスに挿入していくと、")
        out.printl("尻肉がまるで女性器を犯しているかのように絡み付いてくる・・・")
        out.printw()
        y.koukan()
    out.printw()
    if y.tf("未熟") == 1:
        out.printl(f"やがて二人同時に絶頂を迎えた{T()}の表情は")
    else:
        out.printl(f"{T()}が絶頂を迎えるのと同時に、")
        if y.suimin == 0:
            out.print("我慢できずに")
        out.printl(f"達した{F()}が直腸内に精を放った。")
        out.printl(f"ビュルッビュルッと注がれる精液を尻穴で絞り取る{T()}の表情は")
    out.printl("まるで普段とは別人のように恍惚としている・・・")
    out.printw()
    y.executor()
    L[2] = 50
    L[121] = 2
    L[122] = 1
    if y.tf("未熟") != 1:
        L[123] = 1
    y.inc_t_f()
    _prison(ctx, L)
    _ablup1(ctx)
    y.switch()
    y.target_side_c()
    return 0


def _a_lostvirgin_sex(y: _Action) -> InputGen:
    """`$A_LOSTVERGIN_SEX`:1857–1953（→ ENDIF:2255 → ENDSELECT）。中出しでもアフターピル・妊娠判定はない。"""
    ctx = y.ctx
    out = ctx.out
    T, F, L = y.T, y.F, y.L
    if y.suimin == 1:
        out.printl("にちゅにちゅと粘着質な水音と荒い息遣いが部屋の空気を震わせる。")
        out.printl(f"{F()}が起きないようにゆっくりと深く、熱い肉棒で腸内を満たし、")
    else:
        out.printl("パンパンと肉と肉のぶつかる音と荒い息遣いが部屋の空気を震わせる。")
        out.printl("激しくはないが情熱的なピストンに腸内を抉られ、")
    out.printl(f"{T()}は異物感と快楽がせめぎ合っている様子で声を堪えている。")
    husband = "夫ではなく" if y.c.talent[800] == 4 and (y.tc_("淫乱") > 0 or y.lover_ft() > 0) else ""
    out.printl(f"深々とペニスを咥えこんだ菊門は、{husband}{F()}の逞しい男根の形を覚えた。")
    out.printw()
    if y.suimin == 1:  # :1870–1883
        out.printl(f"{F()}のペニスが硬さと太さを増し限界を予感させると、")
        if y.tf("未熟") == 1:
            out.printl(f"まだ初々しさの残る挿入にも関わらず、{T()}がアナルアクメを迎えたのは同時だった・・・")
        elif y.tc_("淫乱") > 0 or y.lover_ft() > 0:
            out.printl(f"{T()}は菊門をきゅっと締めて無言で中出しを促した。")
            out.printl("まだ初々しさの残る挿入にも関わらず二人は同時に絶頂し、勢いよく精液が腸内へと注ぎこまれていった・・・")
            y.nakadashi = 1
        else:
            out.printl(f"ギリギリで{F()}のペニスを引き抜こうとするも一歩遅く、")
            out.printl("ビュルッビュルッと尻穴に勢いよく精液を注ぎこまれてしまった・・・")
            out.printl(f"まだ初々しさの残る挿入にも関わらず{T()}が絶頂したのは同時だった・・・")
    else:  # :1884–1906
        if y.tf("未熟") == 1:
            out.printl(f"限界に達した{F()}が恍惚の表情を浮かべて絶頂するのと、")
            out.printl(f"まだ初々しさの残る挿入にも関わらず{T()}がアナルアクメを迎えたのは同時だった・・・")
        elif y.tc_("淫乱") > 0 or y.lover_ft() > 0:
            if y.c.talent[800] == 4:
                out.printl("辛うじて残っていた理性によって中出しは回避したほうがと頭をよぎるが、")
                out.printl(f"{T()}は頬を赤くしながら、情熱的なおねだりで{F()}の思考を遮ると、")
                out.printl(f"ぐいぐいとしりたぶを{F()}の腰に押しつけてペニスを奥深くまで咥えこみ、身体でも腸内射精をねだった。")
                out.printl(f"{F()}もまた我慢できなくなり、その誘いに応えて腸奥へと精液を解き放った、")
                out.printl("オトコの味に慣れていない初心な直腸内が白く染め上げられていく。")
                out.printl(f"{T()}は甘い喘ぎ声を漏らし、自らの最も大事な場所に夫以外の子種を受け入れる喜びに浸っていた・・・")
            else:
                out.printl(f"限界に達した{F()}が腰を引こうとすると、")
                out.printl(f"{T()}はぐいぐいとしりたぶを押しつけて無言で中出しを懇願した。")
                out.printl("まだ初々しさの残る挿入にも関わらず二人は同時に絶頂し、勢いよく精液が腸内へと注ぎこまれていった・・・")
        else:
            out.printl(f"絶頂が近付いた{F()}は爆発寸前のペニスを引き抜こうとするも、")
            out.printl(f"きゅっと締めつけたアヌスに我慢できず、謝りながら{T()}の直腸内に精を放った。")
            out.printl(f"まだ初々しさの残る挿入にも関わらず{T()}が絶頂したのは同時だった・・・")
    out.printl(f"長い長い絶頂を迎え、{T()}は自他の区別も時間も消え去った純白に包まれる。")
    out.printl("無限の幸せが続くような感覚から目を覚ますと、恍惚とした満足気な笑みを浮かべた・・・")
    out.printw()
    y.executor()
    L[2] = 50
    L[10] = 50
    L[121] = 2
    L[122] = 1
    if y.tf("未熟") != 1:
        L[123] = 1
    y.inc_t_f()
    _prison(ctx, L)
    _ablup1(ctx)
    y.switch()
    y.target_side_c()
    return 0
    yield  # pragma: no cover（ジェネレータにするため）


def _a_sex(y: _Action) -> InputGen:
    """`$A_SEX`:1971–2095（→ ENDIF:2255 → ENDSELECT）。"""
    ctx = y.ctx
    st, out = ctx.state, ctx.out
    T, F, L = y.T, y.F, y.L
    if y.suimin == 1:
        out.printl(f"逆レイプ背面騎乗位で腰を振り続ける{T()}に、")
        out.printl(f"{F()}は寝ながら性交快楽を与えられ微かな喘ぎ声を漏らしている。")
        out.printl(f"{F()}が起きてしまうスリルに酔いしれながら、")
        out.printl("パンパンと打ちつける淫音が響くたびに快楽が増幅されていく。")
    elif y.tf("未熟") == 1:
        out.printl(f"まるで動物のように四つん這いで腰を振り続ける{T()}に、")
        out.printl(f"{F()}もまた未熟な男根を腸肉にシゴき上げられる快楽に我を忘れている。")
        out.printl(f"{T()}が首を回すと二人で唇を交わして唾液交換の美酒に酔いしれながら、")
        out.printl("パンパンと打ちつける淫音が響くたびに快楽が増幅されていく。")
    else:
        y.koukan()
    out.printw()
    if y.tf("未熟") == 1:  # :1999–2024
        out.printl(f"やがて{F()}がほどなく限界に達し、{T()}もまた絶頂を迎えた。")
        out.printl(f"腸内にペニスを受け入れたまま倒れかかった{T()}の表情は")
    elif y.tc_("淫乱") > 0 or y.lover_ft() > 0:
        out.printl("辛うじて残っていた理性によって中出しは回避したほうがと頭をよぎるが、")
        if y.suimin == 1:
            out.printl("快楽に倒錯した本能がメスに染まって妊娠を望み、脳が腸内射精の快楽信号を欲している。")
            out.printl(f"昂った欲情の内奥で{F()}の子種をすべて受け止めた。")
        else:
            out.printl(f"{T()}は{F()}の腰にぐいぐいとお尻を押しつけて放さない。")
            out.printl("それどころか「出して、ナカに出して」と懇願されては誘惑に耐えきれるはずもなく、")
            out.printl(f"昂った欲情の中で{F()}は内奥で子種を一気に放出した。")
        out.printl("熱い精液を受け止めた満足感と、こんなに出されたら本当に妊娠してしまうかもという歪んだ昂奮に、")
        out.printl(f"ドクドクと精液を直腸で受け止める{T()}の表情は")
    else:
        out.printl(f"{T()}は熱い精液を受け止めたい誘惑と、")
        out.printl("ナカに出されたら妊娠してしまうかもという歪んだ昂奮に心が揺らぐも、")
        out.printl("辛うじて残っていた理性によって中出しは回避したほうがと頭をよぎる。")
        out.printl(f"絶頂が近付いた{F()}の爆発寸前のペニスを引き抜こうとするが、")
        out.printl("思わずアヌスをきゅっと締めつけてしまい、直腸内に暴発した精を放たれてしまった・・・。")
        out.printl(f"同時に絶頂を迎えて痙攣する{T()}の尻穴にビュルッビュルッと精液を注ぎ込む{F()}の表情は")
    out.printl("まるで普段とは別人のように恍惚としている・・・")
    out.printl()
    if y.suimin == 1:  # :2028–2050
        out.printl(f"やがて落ち着きを取り戻した{T()}は")
        if y.tc_("淫乱") > 0:
            out.printl(f"いまだ眠り続ける{F()}を逆レイプしてしまった背徳感に胸を熱くした。")
            if config_check_maniac(st, 15) == 1:  # スカトロフィルター
                out.printl(f"起きない{F()}が悪いと言い訳を呟きながら半勃ち状態のペニスに見惚れながら綺麗に拭くと、")
            else:
                out.printl(f"起きない{F()}が悪いと言い訳を呟きながら不浄の味が残る半勃ち状態のペニスをお掃除フェラで綺麗にすると、")
                L[324] = 1
            out.printl("名残惜しそうに部屋を後にした。")
        else:
            out.printl(f"正気に戻り{F()}を逆レイプしてしまった罪悪感に胸を絞めつけられた。")
            out.printl(f"謝罪の言葉を繰り替えし囁きながら{F()}の体を綺麗に拭いて証拠隠滅すると")
            out.printl("追われるように部屋を後にした。")
        out.printw()
        if st.rng.rand(10) == 0:
            out.printl(f"何事もなかったかのように静まり返った、しかし性臭の漂う部屋で{F()}は")
            out.printl("先ほどの夢のような出来事を反芻しながらアナルオナニーに耽っていた・・・")
    out.printw()
    y.executor()
    L[2] = 50
    L[121] = 2
    L[122] = 1
    if y.tf("未熟") != 1:
        L[123] = 1
    L[124] = L[324]
    y.inc_t_f()
    _prison(ctx, L)
    _ablup1(ctx)
    y.switch()
    y.target_side_c()
    return 0
    yield  # pragma: no cover


# --- CASE 8：Ｂ夜這い（:2257–2470）----------------------------------------------------------------


def _case8(y: _Action) -> None:
    ctx = y.ctx
    st, data, out = ctx.state, ctx.data, ctx.out
    T, F, L = y.T, y.F, y.L
    oto = y.tc_("男の娘") > 0
    if y.af("欲望") < 2 + st.rng.rand(3) or y.suimin == 1:  # :2258–2333
        if y.suimin == 1:
            out.printl(f"{T()}が{F()}の口元に{'薄い胸' if oto else '乳房'}をあてがうと、")
            out.printl(f"赤ん坊の頃の夢でも見ているのか、{F()}は口で{T()}の乳首を愛撫しはじめた。")
            out.printw()
            out.printl(f"柔らかな{'胸肌を唇が押すとかすかに' if oto else '双丘を唇が食むと'}弾力を返し、")
            out.printl(f"そっと舌で乳頭を舐め上げると敏感に反応した{T()}が細い声を漏らす。")
            out.printw()
            out.print(f"やがて{T()}が限界に達し絶頂すると")
            if y.tc_("母乳体質"):
                out.printl(f"母乳が噴き出し、乳頭に吸い付いた{F()}がそれを飲み干していく・・・")
            else:
                out.printl("、涎を垂らしながら大きく痙攣した・・・")
        else:
            out.printl(f"{F()}は{T()}の{'薄い胸を揉みながら' if oto else '乳房を揉みながら'}、")
            out.printl(f"口で{T()}の乳首を愛撫した。")
            out.printw()
            out.printl(f"柔らかな{'胸肌' if oto else '双丘'}は手のひらで包み込むと{'かすかに' if oto else ''}弾力を返し、")
            out.printl(f"そっと舌で{'きめ細かな肌' if oto else '曲線'}を舐め上げると敏感に反応した{T()}が細い声を漏らす。")
            if y.tc_("母乳体質"):
                out.printl("乳首を刺激するとじわりと先端から母乳が滲み出し、")
                out.printl(f"{F()}が乳頭を甘噛みすると母乳が止め処なく流れ出てくる。")
                out.printw()
                out.printl(f"やがて{T()}が大きく痙攣して絶頂すると母乳が噴き出し、")
                out.printl(f"乳頭に吸い付いた{F()}がそれを飲み干していく・・・")
            else:
                out.printl("たちまち充血して勃起した乳頭に吸い付き、")
                out.printl(f"{'薄い胸を手で包むように揉みしだき' if oto else '激しく揉み上げ'}ながら舌と唇で敏感な先端を丹念にねぶっていく。")
                out.printw()
                out.printl(f"{F()}が{'胸肌' if oto else '乳房'}を揉みながら乳首に歯を立てて甘噛みしていくと、")
                out.printl(f"限界に達した{T()}が涎を垂らしながら大きく痙攣した・・・")
        if y.tsish():  # :2294–2299
            out.printl("乳首の刺激だけならオトコの身体でも感じるが、乳房を揉まれる多幸感は母になれるオンナの特権だ。")
            if y.tc_("母乳体質"):
                out.printl("射乳の快楽もオトコの射精と似て非なるもので、")
            out.printl(f"{T()}はオンナの身体の良さに浸った。")
        out.printw()
        y.executor()
        L[3] = 50
        L[122] = 1
        y.inc_t_f()
        if y.tc_("母乳体質"):
            L[154] = 1
        _prison(ctx, L)
        _ablup1(ctx)
        y.switch()
        y.inc_f_l()
        _prison(ctx, y.L)
        _ablup1(ctx)
        return
    if oto:  # :2335–2399 自分男の娘で相手の欲望高
        out.printl(f"{F()}は座らせた{T()}を後ろから抱き締めると、")
        out.printl("あらわになった薄い胸の先端を指でくりくりともてあそんだ。")
        if y.tc_("淫乳") > 0:
            out.printl("淫らに開発されきった乳首の快感、それだけで全身を玩具のように跳ねさせて、")
        out.printl(f"かわいらしい声をあげる{T()}に欲望を刺激され、強引に横向かせて後ろからキスをする。")
        out.printw()
        out.printl(f"{T()}はぐちゅぐちゅと舌を絡め取られて吸い上げられながら、")
        out.printl("息つく間もなく与えられる口と胸の快楽に、自分が本当に女の子になったかのように陶然としていた・・・")
        if is_male(data, y.f) and y.tf("男の娘") <= 0:
            out.printl("オトコにキスされ愛撫されているのに嫌悪感はなく、カラダを抱き締めて貰える安心感に包まれる。")
        out.printl("広げた手のひらで薄い胸を柔らかく揉まれながら、")
        out.printl("悪戯っぽく、少しおっぱいがあるねと囁かれると、本当にそんな気がしてくる。")
        out.printw()
        out.printl(f"いつしか{T()}は仰向けに押し倒され、ちゅぱっちゅぱっと音を立てて乳首を吸われていた。")
        out.printl(f"快感に喘ぐ唇が{F()}に塞がれて唾液を交換されたかと思うと、今度は薄い胸全体に舌を這わされる。")
        out.printl(f"二人の混合唾液が淫らな膜となって{T()}の乳首や胸肌を覆っていく。")
        out.printw()
        if is_penis(ctx, st.flag[799]) and y.tf("未熟") != 1:
            out.printl(f"やがて絶頂が近付くと{F()}は自らのペニスを取り出して、{T()}の薄い胸に擦りつける。")
            out.printl(f"たちまち迸った精液が乳首にまとわりつく熱くぬめついた感触に、{T()}も一気に果てた・・・")
        else:
            out.printl(f"やがて絶頂が近付くと{F()}が乳首にカリッと強く噛みついて、")
            out.printl(f"あられもない嬌声をあげた{T()}は涎を垂らしながら大きく痙攣した・・・")
        out.printw()
        y.executor()
        L[3] = 50
        L[122] = 1
        y.inc_t_f()
        _prison(ctx, L)
        _ablup1(ctx)
        y.switch()
        y.inc_f_l()
        if is_penis(ctx, st.flag[799]) and y.tf("未熟") != 1:  # :2384–2392
            y.L[0] = 50
            y.L[122] = 1
            y.L[153] = 1
        _prison(ctx, y.L)
        _ablup1(ctx)
        return
    # :2401–2469 欲望高
    out.printl(f"{F()}と{T()}は互いの胸を揉みながら、")
    out.printl("唇を重ねて絡み合った。")
    out.printl("指や舌を交えながら互いの乳房と乳首を愛撫していく。")
    out.printw()
    if y.tsish():
        out.printl("乳首の刺激だけならオトコの身体でも感じるが、乳房を揉まれる多幸感は母になれるオンナの特権だ。")
        if is_male(data, y.f):
            out.printl(f"{T()}は{F()}の胸を盗み見て、微かな優越感を味わった。")
            out.printl("せめて乳首だけでもオンナと同じくらいの快楽を教えてあげようと技を尽くす。")
        else:
            out.printl(f"オンナとしてレズを体感する自分と、{F()}とのレズ行為を俯瞰で見ているオトコの自分がいる。")
            out.printl("そのイメージは快楽を倍増させ、風船のように膨れ上がり張りつめさせる。")
    if y.tc_("母乳体質") and y.tf("母乳体質"):
        out.printl("やがて絶頂が近付くと二人は同時に乳首から母乳を噴出し、")
    elif y.tc_("母乳体質"):
        out.printl(f"やがて絶頂が近付くと{T()}が乳首から母乳を噴出し、")
    elif y.tf("母乳体質"):
        out.printl(f"やがて絶頂が近付くと{F()}が乳首から母乳を噴出し、")
    else:
        out.printl("やがて絶頂が近付くと互いの胸を鷲掴みするように痙攣し、")
    out.printl("そのまま一気に二人で果てた・・・")
    out.printw()
    y.executor()
    L[3] = 50
    L[122] = 1
    y.inc_t_f()
    if y.tc_("母乳体質"):
        L[154] = 1
    _prison(ctx, L)
    _ablup1(ctx)
    y.switch()
    y.L[3] = 50
    y.L[122] = 1
    y.inc_f_l()
    if y.tf("母乳体質"):
        y.L[154] = 1
    _prison(ctx, y.L)
    _ablup1(ctx)


# --- CASE 16：性交を迫る（:2472–2593）／CASE 32：奉仕を迫る（:2597–2642）--------------------------------


def _case16(y: _Action) -> InputGen:
    from .battle.sexcom import check_holyvirgin

    ctx = y.ctx
    st, out = ctx.state, ctx.out
    rand = st.rng.rand
    T, F = y.T, y.F
    args = (y.suimin, y.self_, y.ts)
    lov = lambda: lover_f(st, st.target, st.flag[799])  # noqa: E731
    if y.suimin == 1:  # :2474–2519
        if y.tf("男の娘") > 0 and y.ac("欲望") < 4:
            out.printl(f"{T()}は勃起しきったペニスを{F()}の下腹部にあてがい")
            out.printl("もう我慢できない…と呻き声を漏らす。")
            out.printl("気付かれなければ大丈夫、ちょっとお尻を使わせて貰うだけと言い訳をしながら")
            out.printl(f"{F()}の括約筋をほぐし始めた・・・")
            out.printw()
            yobai_houshi_5(ctx, *args)
        elif y.tf("男の娘") > 0:
            out.printl(f"{T()}は勃起しきったペニスを{F()}の下腹部にあてがい")
            out.printl(f"{F()}の腸内のどこまで届くかを検分している。")
            if y.af("Ａ感覚") < 2:
                out.printl(f"{F()}の密やかな窄まりを寝ている間に押し広げることに昏い興奮を覚えた・・・")
            elif y.tf("交際相手") > 1 and lov() == 0:
                out.printl(f"{F()}を寝取ることに昏い興奮を覚えた・・・")
            else:
                out.printl(f"{F()}を汚すことに興奮を覚えた・・・")
            out.printw()
            yield from yobai_houshi_4(ctx, *args)
        elif y.ac("欲望") < 4 or y.tf("処女") > 1:
            out.printl(f"{T()}は勃起しきったペニスを{F()}の下腹部にあてがい")
            out.printl(f"もう我慢できない…と呻き声を漏らすが、{F()}の")
            if y.tf("処女") > 0:
                out.print("処女を奪う")
            else:
                out.print("貞操を汚す")
            out.printl("ことに抵抗を覚え、")
            out.printl("前の穴での本番は駄目だが、アナルならセックスじゃないからと言い訳をしながら")
            out.printl(f"{F()}の括約筋をほぐし始めた・・・")
            out.printw()
            yobai_houshi_5(ctx, *args)
        else:
            out.printl(f"{T()}は勃起しきったペニスを{F()}の下腹部にあてがい")
            out.printl(f"{F()}の膣内のどこまで届くかを検分している。")
            if y.tf("処女") > 0:
                out.printl(f"{F()}の処女を寝ている間に奪うことに昏い興奮を覚えた・・・")
            elif y.tf("交際相手") > 1 and lov() == 0:
                out.printl(f"{F()}を寝取ることに昏い興奮を覚えた・・・")
            else:
                out.printl(f"{F()}を汚すことに興奮を覚えた・・・")
            out.printw()
            yield from yobai_houshi_4(ctx, *args)
        return 0
    if y.af("欲望") < 2:  # :2521–2540 断られる
        out.printl(f"{T()}は{F()}に勃起しきったペニスを見せて")
        out.printl("もう我慢できない、挿入させて欲しいと頼み込んだが、")
        out.printl("さすがにエッチするのは・・・と断られてしまった。")
        if rand(2) == 0 and y.tf("巨乳") > 0:
            out.printl(f"代わりに胸で抜いてあげるから、と{F()}が慰めると")
            out.printl(f"{T()}の表情がぱっと明るくなった・・・")
            out.printw()
            yobai_houshi_3(ctx, *args)
        elif rand(2) == 0:
            out.printl(f"代わりに口で抜いてあげるから、と{F()}が慰めると")
            out.printl(f"{T()}は頬を染めながら頷いた・・・")
            out.printw()
            yobai_houshi_2(ctx, *args)
        else:
            out.printl(f"代わりに手で抜いてあげるから、と{F()}が慰めると")
            out.printl(f"{T()}は渋々引き下がった・・・")
            out.printw()
            yobai_houshi_1(ctx, *args)
        return 0
    head = (f"{T()}は{F()}に勃起しきったペニスを見せて",)  # :2543 等の共通の 1 行目
    if y.tf("男の娘") > 0 and y.af("Ａ感覚") < 2 and y.af("欲望") < 4:  # :2542–2550
        out.printl(head[0])
        out.printl(f"もう我慢できない、挿入させて欲しいと頼み込むと{F()}は")
        out.printl("これでも一応オトコだから・・・と首を振る。")
        out.printw()
        out.printl(f"しかし、諦める様子のない{T()}にお尻で擦るだけでもと縋られると、")
        out.printl(f"最後には{F()}もそれだけなら・・・と頷いた。")
        out.printw()
        yobai_houshi_5(ctx, *args)
    elif y.tf("男の娘") > 0 and y.af("Ａ感覚") < 2:  # :2552–2557
        out.printl(head[0])
        out.printl("もう我慢できない、挿入させて欲しいと頼み込むと")
        out.printl(f"{F()}は欲情に上気した顔で自分をオンナにしてほしい、と応えた・・・")
        out.printw()
        yobai_houshi_5(ctx, *args)
    elif y.tf("男の娘") > 0:  # :2559–2564
        out.printl(head[0])
        out.printl("もう我慢できない、挿入させて欲しいと頼み込むと")
        out.printl(f"{F()}は頬を染めながら頷いた・・・")
        out.printw()
        yobai_houshi_5(ctx, *args)
    elif check_holyvirgin(ctx, st.flag[799]) == 1 and y.af("欲望") < 4:  # :2566–2571
        out.printl(head[0])
        out.printl(f"もう我慢できない、挿入させて欲しいと頼み込むと{F()}は")
        out.printl("処女なので前の穴での本番は駄目だが、アナルなら・・・と頷いた。")
        out.printw()
        yobai_houshi_5(ctx, *args)
    elif y.tf("処女") == 1:  # :2573–2578
        out.printl(head[0])
        out.printl("もう我慢できない、挿入させて欲しいと頼み込むと")
        out.printl(f"{F()}は欲情に上気した顔で処女を貰ってほしい、と応えた・・・")
        out.printw()
        yield from yobai_houshi_4(ctx, *args)
    elif rand(2) == 0 or y.tf("処女") > 1:  # :2580–2585
        out.printl(head[0])
        out.printl("もう我慢できない、挿入させて欲しいと頼み込むと")
        out.printl(f"{F()}は頬を染めながらアナルでして欲しい、と応えた・・・")
        out.printw()
        yobai_houshi_5(ctx, *args)
    else:  # :2587–2592
        out.printl(head[0])
        out.printl("もう我慢できない、挿入させて欲しいと頼み込むと")
        out.printl(f"{F()}は頬を染めながら頷いた・・・")
        out.printw()
        yield from yobai_houshi_4(ctx, *args)
    return 0


def _case32(y: _Action) -> None:
    ctx = y.ctx
    st, out = ctx.state, ctx.out
    rand = st.rng.rand
    T, F = y.T, y.F
    args = (y.suimin, y.self_, y.ts)
    if y.suimin == 1:  # :2599–2610
        out.printl(f"{T()}は勃起しきったペニスをさらけ出して")
        if rand(4) == 0 and y.tf("巨乳") > 0:
            out.printl("胸で抜くことにした。")
            yobai_houshi_3(ctx, *args)
        elif rand(8) == 0:
            out.printl("手で抜くことにした。")
            yobai_houshi_1(ctx, *args)
        else:
            out.printl("口で抜くことにした。")
            yobai_houshi_2(ctx, *args)
        return
    out.printl(f"{T()}は{F()}に勃起しきったペニスを見せて")  # :2612–2641
    out.printl("抜かせて欲しいと頼み込んだ。")
    if y.af("欲望") < 2 + rand(3):
        out.printl(f"見るからに限界に達しつつあるペニスを見て{F()}は")
        if rand(8) == 0 and y.tf("巨乳") > 0:
            out.printl("胸で抜いてあげることにしたようだ・・・")
            out.printw()
            yobai_houshi_3(ctx, *args)
        elif rand(4) == 0:
            out.printl("口で抜いてあげることにしたようだ・・・")
            out.printw()
            yobai_houshi_2(ctx, *args)
        else:
            out.printl("手で抜いてあげることにしたようだ・・・")
            out.printw()
            yobai_houshi_1(ctx, *args)
    else:
        out.printl(f"見るからに限界に達しつつあるペニスを見て{F()}は")
        if rand(4) == 0 and y.tf("巨乳") > 0:
            out.printl("胸で抜いてあげることにしたようだ。")
            yobai_houshi_3(ctx, *args)
        elif rand(8) == 0:
            out.printl("手で抜いてあげることにしたようだ。")
            yobai_houshi_1(ctx, *args)
        else:
            out.printl("口で抜いてあげることにしたようだ。")
            yobai_houshi_2(ctx, *args)


# --- @YOBAI_HOUSHI_1〜5（:2651–3633）---------------------------------------------------------------


class _Houshi(_Action):
    """YOBAI_HOUSHI_n：`VARSET LOCAL` / LCOUNT = 0 / SUIMIN・SELF・ＴＳキャラ = ARG:0〜2。"""

    def __init__(self, ctx: Ctx, suimin: int, self_: int, ts: int) -> None:
        super().__init__(ctx, 0, 0)
        self.suimin = suimin
        self.self_ = self_
        self.ts = ts

    def f_ts_female(self) -> bool:
        """`TALENT:(FLAG:799):変身時ＴＳ > 0 && CFLAG:(FLAG:799):1 == 1 && ISFEMALE(FLAG:799)`。"""
        return self.tf("変身時ＴＳ") > 0 and self.f.cflag[1] == 1 and is_female(self.ctx.data, self.f)

    def executor_houshi(self) -> None:
        """実行者側の定型（:2700–2717 等）：快C 100・絶頂・近親・射精 2（未熟でなければ）→ COMMON_PRISON → _ABLUP。"""
        self.executor()
        self.L[0] = 100
        self.L[122] = 1
        self.inc_t_f()
        if self.tc_("未熟") != 1:
            self.L[153] = 2
        _prison(self.ctx, self.L)
        _ablup1(self.ctx)

    def semen_l(self) -> None:
        """`SIF TALENT:LCOUNT:未熟 != 1 / LOCAL:123 = 2`。"""
        if t(self.ctx, self.ctx.state.charas[self.lcount], "未熟") != 1:
            self.L[123] = 2


def yobai_houshi_1(ctx: Ctx, suimin: int, self_: int, ts: int) -> None:
    """`@YOBAI_HOUSHI_1`:2651–2735（手）。"""
    y = _Houshi(ctx, suimin, self_, ts)
    out, data = ctx.out, ctx.data
    T, F = y.T, y.F
    if suimin == 1:
        out.printl(f"{T()}は{F()}の手を取ってペニスを握らせ、")
    else:
        out.printl(f"{F()}は{T()}のペニスを手で握り、")
    out.printl("ゆっくりと上下に動かし始めた。")
    if y.f_ts_female() and suimin == 0:
        out.printl(f"{F()}はオトコの時の自慰を思い出し、自分が感じた部位を責めると、")
    out.printl(f"すでに限界まで勃起したかに見えた{T()}のペニスが掌の柔らかな感触に反応して")
    out.printl("さらに怒張を強く硬く反り返らせる・・・")
    out.printw()
    if y.tc_("未熟") == 1 and (is_female(data, y.f) or y.tf("男の娘") > 0):  # :2675–2693
        oto = y.tf("男の娘") > 0
        if suimin == 1:
            out.printl(f"快楽にあえぐ{T()}が{F()}の{'薄い胸' if oto else '乳房'}を露出させると、")
            out.printl(f"{T()}は陶酔した表情で夢中で{'かすかな弾力' if oto else '乳房'}を揉みほぐした。")
            out.printl(f"柔らかい{'男の娘胸' if oto else '乳房'}と手の感触に{T()}が全身を痙攣させて絶頂するまで")
            out.printl("背徳的な手コキは続けられた・・・")
        else:
            out.printl(f"快楽にあえぐ{T()}に応えて{F()}が{'薄い胸' if oto else '乳房'}を露出させると、")
            out.printl(f"{T()}は陶酔した表情で夢中で乳首に吸い付いた。")
            out.printl(f"優しく髪を撫でられる{T()}が全身を痙攣させて絶頂するまで")
            out.printl("背徳的な授乳手コキは続けられた・・・")
    elif y.tc_("未熟") == 1:
        out.printl(f"ほどなくして{T()}は全身を痙攣させて絶頂した・・・")
    else:
        out.printl("上下のストロークと共に先走り汁が噴き出してくる。")
        out.printl(f"そのまま一気に加速すると{T()}は大きく痙攣し、")
        out.printl(f"{F()}の身体に大量の精液を放った・・・")
    if suimin == 1:
        out.printl(f"やがて落ち着きを取り戻した{T()}は罪悪感に胸を絞めつけられた。")
        out.printl(f"謝罪の言葉を繰り替えし囁きながら{F()}の体を綺麗に拭いて証拠隠滅すると")
        out.printl("追われるように部屋を後にした。")
    out.printw()
    y.executor_houshi()
    y.switch()
    y.semen_l()
    y.inc_f_l()
    _prison(ctx, y.L)
    _ablup1(ctx)


def yobai_houshi_2(ctx: Ctx, suimin: int, self_: int, ts: int) -> None:
    """`@YOBAI_HOUSHI_2`:2739–2829（口）。"""
    y = _Houshi(ctx, suimin, self_, ts)
    out = ctx.out
    T, F = y.T, y.F
    if suimin == 1:
        out.printl(f"{T()}は{F()}の唇に怒張を這わせ、")
        out.printl("ゆっくりと口の中に侵入させた。")
        out.printl(f"{T()}がもどかしそうに腰を前後に動かしながらペニスで咥内を犯す。、")
        out.printl(f"{F()}は無意識のうちに甘噛みしたり、舌で亀頭の先端やカリ裏に刺激を与えている・・・")
        out.printw()
        out.printl(f"やがて限界に近付いた{T()}はフィニッシュとばかりに大きく痙攣し、")
    else:
        out.printl(f"{F()}は{T()}の怒張に舌を這わせ、")
        out.printl("ゆっくりと口の中に飲み込んでいった。")
        if y.f_ts_female():
            out.printl(f"{F()}はオトコの時の自慰を思い出し、{T()}が感じている快楽を想像しながら奉仕する。")
        out.printl(f"{F()}が前後に動きながらペニスを唇で締め上げ、")
        out.printl("舌で亀頭の先端やカリ裏を細かく刺激していった・・・")
        out.printw()
        out.printl(f"やがて限界に近付いていることを察した{F()}がフィニッシュとばかりに")
        out.printl(f"ジュルジュルと音を立ててペニスを吸い上げると、{T()}は大きく痙攣し、")
    if y.tc_("未熟") == 1:  # :2770–2790
        out.printl("至福の表情を浮かべながら絶頂を迎えた・・・")
    else:
        out.printl(f"そのまま{F()}の口内に大量の精液を放った・・・")
        if suimin == 1:
            out.printl(f"やがて落ち着きを取り戻した{T()}は罪悪感に胸を絞めつけられ、")
            out.printl("証拠隠滅しようとしたが、口内射精など後始末のしようがない。")
            out.printl(f"謝罪の言葉を繰り替えし囁きながら{T()}は逃げるように部屋を後にした。")
        elif y.f_ts_female():
            out.printl(f"{F()}は理想の女性像を演じるべく、精液を一滴もこぼさず嚥下して")
            out.printl("いたずらっぽく笑いながら口の中が空っぽなのを見せてきた。")
        elif y.af("精液中毒") > 2:
            out.printl(f"口腔一杯に広がった精液の味と香りに心を奪われた{F()}は、")
            out.printl("嚥下しながら頬を窄めてペニスに強く吸いついて、尿道に残る最後の一滴までも絞り出した・・・")
            if y.af("精液中毒") > 4:
                out.printl(f"その後も{T()}が引き剥がすまで正気に戻らず、さらなる精液を求めてペニスをしゃぶり続けていた。")
        elif y.tf("男の娘") > 0:
            out.printl(f"{F()}は{T()}のために理想の女の子を演じるべく、精液を一滴もこぼさず嚥下して")
            out.printl("いたずらっぽく笑いながら口の中が空っぽなのを見せてきた。")
    out.printw()
    y.executor_houshi()
    y.switch()
    y.semen_l()
    y.L[124] = 1
    y.inc_f_l()
    _prison(ctx, y.L)
    _ablup1(ctx)


def yobai_houshi_3(ctx: Ctx, suimin: int, self_: int, ts: int) -> None:
    """`@YOBAI_HOUSHI_3`:2833–2915（胸）。"""
    y = _Houshi(ctx, suimin, self_, ts)
    out = ctx.out
    T, F = y.T, y.F
    if suimin == 1:
        out.printl(f"{T()}は{F()}の豊満な胸でペニスを包み込み、")
        out.printl("手で谷間を押しつけてゆっくりとシゴいた。")
        out.printl("乳房の柔らかな感触と乳首のコリコリした感触に刺激されて")
        out.printl(f"{T()}の脳内を快楽物質が駆け巡る・・・")
        out.printw()
        out.printl(f"やがて限界に近付いた{T()}はフィニッシュとばかりに大きく痙攣し、")
    else:
        if y.f_ts_female():
            out.printl(f"みんなやっぱりおっぱいが好きなんだなと、{F()}は苦笑し、")
            out.printl("えっちな動画で見て自分が憧れたパイズリプレイを再現することにした。")
        out.printl(f"{F()}は豊満な胸で{T()}のペニスを包み込み、")
        out.printl("手で谷間を押しつけてゆっくりとシゴきながら、先端からはみ出した亀頭に舌を這わせた。")
        out.printl("乳房の柔らかな感触と先端を舐め上げる舌と唇の温かさ、")
        out.printl("そして乳首のコリコリした感触に刺激されて")
        out.printl(f"{T()}の脳内を快楽物質が駆け巡る・・・")
        out.printw()
        out.printl(f"やがて限界に近付いていることを察した{F()}がフィニッシュとばかりに")
        out.printl(f"ジュルジュルと音を立ててペニスを吸い上げると、{T()}は大きく痙攣し、")
    if y.tc_("未熟") == 1:
        out.printl("至福の表情を浮かべながら絶頂を迎えた・・・")
    else:
        out.print(f"そのまま{F()}の胸")
        if suimin == 0:
            out.print("と口内")
        out.printl("に大量の精液を放った・・・")
    out.printw()
    y.executor_houshi()
    y.switch()
    y.L[3] = 80
    y.semen_l()
    y.L[124] = 1
    y.inc_f_l()
    _prison(ctx, y.L)
    _ablup1(ctx)


def _houshi_family(y: _Houshi, ts_male_line: str, ts_target_line: str, ts_target_cond) -> None:
    """HOUSHI_4／5 の血縁者テスト（:2934–2974／:3343–3383）。続柄の性別は ISMALE()＝実行者（原作どおり）。"""
    ctx = y.ctx
    st, data, out = ctx.state, ctx.data, ctx.out
    out.print(f"{y.F()}は")
    out.print(_family(ctx, st.target))
    if is_male(data, y.c) and y.tc_("変身時ＴＳ") > 0 and y.c.cflag[1] > 0:
        out.printl(ts_male_line)
    elif ts_target_cond():
        out.printl(ts_target_line)
    else:
        out.printl("が入ってきた時から予感はあった。")


def _houshi_suimin_after(y: _Houshi, hole: str, always: bool) -> None:
    """HOUSHI_4／5 の睡眠姦後の文（:3028–3046 ほか）。always = False なら最後の 2 行は RAND:5 == 0 のとき。"""
    ctx = y.ctx
    out = ctx.out
    T, F = y.T, y.F
    out.printl(f"やがて落ち着きを取り戻した{T()}は")
    if y.tc_("淫乱") > 0:
        out.printl(f"いまだ眠り続ける{F()}をレイプしてしまった背徳感に胸を熱くした。")
        out.printl(f"起きない{F()}が悪いと言い訳を呟きながら")
        out.printl(f"白濁液の溢れ出る{hole}を綺麗にすると、名残惜しそうに部屋を後にした。")
    else:
        out.printl(f"正気に戻り{F()}をレイプしてしまった罪悪感に胸を絞めつけられた。")
        out.printl(f"謝罪の言葉を繰り替えし囁きながら{F()}の体を綺麗に拭いて証拠隠滅すると")
        out.printl("追われるように部屋を後にした。")
    out.printw()
    if always:
        out.printl(f"何事もなかったかのように静まり返った、しかし性臭の漂う部屋で{F()}は")
        if y.lover_ft() > 0 or y.tf("淫乱") > 0:
            out.printl("先ほどの夢のような出来事を反芻しながら自慰に耽っていた・・・")
        else:
            out.printl("これはきっと夢だと言い聞かせながら枕を涙で濡らしていた・・・")
    elif ctx.state.rng.rand(5) == 0:
        out.printl(f"何事もなかったかのように静まり返った、性臭の漂う部屋で{F()}は")
        if y.tf("淫乱") > 0 or y.lover_ft() > 0:
            out.printl("先ほどの夢のような出来事を反芻しながら自慰に耽っていた・・・")
        else:
            out.printl("これはきっと夢だと言い聞かせながら枕を涙で濡らしていた・・・")


def yobai_houshi_4(ctx: Ctx, suimin: int, self_: int, ts: int) -> InputGen:
    """`@YOBAI_HOUSHI_4`:2919–3255（Ｖ性交）。"""
    from .battle.ninsin import estrus_text

    y = _Houshi(ctx, suimin, self_, ts)
    st, data, out = ctx.state, ctx.data, ctx.out
    T, F = y.T, y.F
    if y.tf("処女") > 0:  # :2932–3106
        if y.inc_tf() > 0:
            _houshi_family(
                y,
                "が男性化して入ってきた時から予感はあった。",
                "に女体化するよう命じられた時から予感はあった。",
                lambda: y.tf("変身時ＴＳ") > 0 and y.f.cflag[1] > 0 and is_female(data, y.f),
            )
            out.printl(f"今から{F()}の処女を捧げることになるのだろう、と。")
            out.printl(f"触手に奪われる前に愛する家族が…{F()}も同じ立場ならそうしただろう。")
        out.printw()
        out.printl(f"{T()}は{F()}のワレメに自らのペニスをあてがうと、")
        out.printl("痛がらないようにゆっくりと亀頭を挿入し、ずぶずぶと押し込んでいった。")
        if suimin == 0:
            out.printl(f"自ら受け入れるように{F()}が脚を絡めて抱き寄せる。")
        out.printw()
        out.print("ペニスを半ばまで挿入したところで膜の破れる感触と共に破瓜の証がつぅと滲み出る")
        out.printl("が、" if suimin == 0 else "。")
        if suimin == 0:
            out.printl(f"{F()}は涙を浮かべながらも幸せそうな表情をしている・・・")
        out.printl()
        out.printl("処女喪失")
        out.printw()
        out.printl("パンパンと肉と肉のぶつかる音と荒い息遣いが部屋の空気を震わせる。")
        out.printl("激しくはないが情熱的なピストンに膣内を抉られ、")
        if suimin == 1:
            out.printl(f"{F()}は眠ったまま初めてにも関わらず甘い喘ぎ声を漏らしている。")
        else:
            out.printl(f"{F()}は痛みよりも快楽のほうが勝っている様子で声を堪えている。")
        out.printw()
        if y.tc_("未熟") == 1:  # :3001–3025
            out.printl(f"限界に達した{T()}が恍惚の表情を浮かべて絶頂するのと、")
            out.printl(f"初めての挿入にも関わらず{F()}がアクメを迎えたのは同時だった・・・")
        elif y.tc_("淫乱") > 0 or y.lover_ft() > 0:
            if suimin == 1:
                out.printl(f"{F()}の寝込みを襲い、ゴムも付けずに生挿入し、無抵抗を良いことに処女を奪い、")
                out.printl("そのうえ無責任中出ししたらと想像すると、動悸が激しくなり怒張もさらに張りつめる。")
                out.printl(f"限界に近付いた{T()}はペニスを膣奥に押し付け、無言で中出しを敢行した。")
                out.printl(f"{F()}は寝入ったまま膣内射精を迎え、")
                out.printl("初めての挿入にも関わらず二人は同時に絶頂し、勢いよく精液が膣内へと注ぎこまれていった・・・")
            elif y.f_ts_female():
                out.printl(f"{F()}は本当はオトコだから妊娠しないはずだ、変身を解けば全てなかったことになるはずだ、")
                out.printl(f"限界に達した{T()}は身勝手で無根拠な言い訳を並べ立てて、無言で中出しを敢行した。")
                out.printl("初めての挿入にも関わらず二人は同時に絶頂し、勢いよく精液が膣内へと注ぎこまれていった・・・")
            else:
                out.printl(f"限界に近付いた{T()}が中に出しても良いかと問うと、")
                out.printl(f"{F()}は足を絡めて無言で中出しを許可した。")
                out.printl("初めての挿入にも関わらず二人は同時に絶頂し、勢いよく精液が膣内へと注ぎこまれていった・・・")
            y.nakadashi = 1
        else:
            out.printl(f"限界に達した{T()}がペニスを引き抜いて射精するのと、")
            out.printl(f"初めての挿入にも関わらず{F()}が絶頂したのは同時だった・・・")
        out.printl()
        if suimin == 1:
            _houshi_suimin_after(y, "膣口", always=True)
        out.printw()
        y.executor_houshi()
        y.switch()
        L = y.L
        L[1] = 100
        L[10] = 50
        L[120] = 2
        L[122] = 1
        y.semen_l()
        y.inc_f_l()
        lc = st.charas[y.lcount]
        y.c.talent[data.index_of("TALENT", "処女")] = -1  # :3086（TARGET = 対象）
        # DEVIATION: 使用者裁決（2026-10-01）：原作 :3088–3092 は CFLAG:LCOUNT:206（実行者）に書くが、処女を失った
        # 対象（TARGET = FLAG:799）の CFLAG:206 に書く。値の条件 LOVER_F(LCOUNT, FLAG:799) は原作どおり
        # （deviations.md「使用者裁決 2026-10-01」）。
        y.c.cflag[206] = 5 if lover_f(st, y.lcount, st.flag[799]) > 0 else 6
        _prison(ctx, L)
        if (t(ctx, lc, "淫乱") > 0 or lover_f(st, y.lcount, st.target) > 0) and L[123] > 0 and t(ctx, lc, "未熟") == 0:
            _ninsin(ctx, L[123], y.lcount)  # :3100–3101
        _ablup1(ctx)
        if y.nakadashi == 1:  # :3103–3106
            yield from _after_pill(ctx, st.target, y.lcount)
        return 0
    # :3109–3255 非処女
    out.printl(f"{T()}は{F()}に覆いかぶさると、")
    out.printl("勃起しきったペニスを膣奥まで挿入して深い抽送を開始した。")
    out.printl(f"すでに濡れきっていた{F()}は痛がる様子も無く、")
    if suimin == 1:
        out.printl("眠りながらもきゅうきゅうと膣壁を収縮させ、夢の中で快楽を享受しているようだ・・・")
    else:
        out.printl("むしろ快楽を貪るようにして互いの口づけを求め合う・・・")
    out.printw()
    out.printl(f"{F()}を抑えつけて激しく腰を振る{T()}・・・")
    out.printl("一夜限りの契りという免罪符が逆に枷を取り払ってしまったかの如く、")
    out.printl("パンパンと打ちつける淫音が響くたびに快楽が増幅されていく。")
    out.printw()
    t_love = y.tc_("淫乱") > 0 or y.lover_tf() > 0
    if y.tc_("未熟") == 1:  # :3125–3178
        out.printl(f"やがて{T()}がほどなく限界に達し、{F()}もまた絶頂を迎えた。")
        out.printl(f"{F()}に抱き付いたまま余韻に蕩けきった{T()}の表情は")
    elif suimin == 1:
        if y.tc_("淫乱") > 0:
            out.printl(f"{F()}の寝込みを襲い、ゴムも付けずに生挿入し、")
            out.printl("そのうえ無責任中出ししたらと想像すると、動悸が激しくなり怒張もさらに張りつめる。")
            out.printl(f"限界に近付いたペニスを膣奥に押し付け、無言で中出しを敢行した{T()}の表情は")
            y.nakadashi = 1
        else:
            out.printl(f"限界に達したペニスを引き抜いて射精した{T()}の表情は")
    elif t_love and (y.tf("淫乱") > 0 or y.lover_ft() > 0):
        out.printl(f"膣内に出したい、と{T()}が言うと{F()}は紅潮した顔で頷き、")
        out.printl(f"口づけを交わしながら{T()}の背に手足を絡めて引き寄せた。")
        if y.f_ts_female():
            out.printl(f"{F()}は本当はオトコだから妊娠しないはずだ、変身を解けば全てなかったことになるはずだ、")
            if y.lover_ft() > 0:
                out.printl(f"それでも妊娠させたい、{_self_call(ctx)}の子どもを産んで欲しい、と")
            else:
                out.printl("オトコのくせに吸い付いてくるマンコが気持ち良すぎる、もし孕んでも責任はとらない、と")
            out.printl(f"{T()}は身勝手で無根拠な言い訳を並べ立てて、一層激しく腰を打ちつける。")
        out.printl("激しくなっていくピストンが限界に達すると子宮の内奥に昂った欲情が一気に放出され、")
        out.printl(f"同時に絶頂して精液を{estrus_text(ctx, st.flag[799])}子宮で受け止める{F()}の表情は")
        y.nakadashi = 1
    elif t_love:
        out.printl(f"膣内に出したい、と{T()}が言うと{F()}は咄嗟に首を横に振ったが、")
        out.printl(f"もはや欲望の虜になっている{T()}が中出しの誘惑に耐えきれるはずもなく、")
        if y.f_ts_female():
            out.printl(f"{F()}は本当はオトコだから妊娠しないはずだ、変身を解けば全てなかったことになるはずだ、")
            if y.lover_ft() > 0:
                out.printl(f"それでも妊娠させたい、{_self_call(ctx)}の子どもを産んで欲しい、")
            else:
                out.printl("オトコのくせに吸い付いてくるマンコが気持ち良すぎる、もし孕んでも責任はとらないぞ、")
            out.printl("と身勝手で無根拠な言い訳を並べ立てて、一層激しく腰を打ちつける。")
        out.printl("限界に達すると子宮の内奥に腰を突き入れて昂った欲情を一気に放出した。")
        out.printl(f"同時に絶頂して精液を{estrus_text(ctx, st.flag[799])}子宮で受け止める{F()}の表情は")
        y.nakadashi = 1
    else:
        out.printl("辛うじて残っていた理性が中出しだけは回避しなければと警告する。")
        out.printl(f"絶頂を迎えた{F()}から爆発寸前のペニスが引き抜かれると、")
        out.printl(f"軽くフェラチオをしてから{T()}を口の中で射精させる。")
        out.printl(f"ビュルビュルと射精を続ける{T()}の表情は")
        y.L[324] = 1
    out.printl("まるで普段とは別人のように恍惚としている・・・")
    out.printl()
    if suimin == 1:
        _houshi_suimin_after(y, "膣口", always=False)
    out.printw()
    y.executor_houshi()
    fellatio = y.L[324]  # VARSET LOCAL（y.switch）前の値（下の DEVIATION 参照）
    y.switch()
    L = y.L
    L[1] = 100
    L[120] = 2
    L[122] = 1
    y.semen_l()
    # DEVIATION: 使用者裁決（2026-10-01）：原作 :3237 `LOCAL:124 = LOCAL:324` は VARSET LOCAL の後なので恆 0。
    # VARSET 前の LOCAL:324（口内射精＝フェラあり）を保持し、:1738／:2063 と同じくフェラ経験に反映する
    # （deviations.md「使用者裁決 2026-10-01」）。
    L[124] = fellatio
    y.inc_f_l()
    _prison(ctx, L)
    lc = st.charas[y.lcount]
    if (t(ctx, lc, "淫乱") > 0 or lover_f(st, y.lcount, st.target) > 0) and L[123] > 0 and t(ctx, lc, "未熟") == 0:
        _ninsin(ctx, L[123], y.lcount)  # :3248–3249
    _ablup1(ctx)
    if y.nakadashi == 1:
        yield from _after_pill(ctx, st.target, y.lcount)
    return 0


def yobai_houshi_5(ctx: Ctx, suimin: int, self_: int, ts: int) -> None:
    """`@YOBAI_HOUSHI_5`:3260–3633（Ａ性交）。中出しの文でもアフターピル・妊娠判定はない。"""
    y = _Houshi(ctx, suimin, self_, ts)
    st, out = ctx.state, ctx.out
    T, F = y.T, y.F
    if y.tf("男の娘") <= 0:  # :3272–3337
        out.printl(f"{T()}は{F()}に覆いかぶさり")
        out.printl("勃起しきったペニスをアヌスに挿入していくと、")
        out.printl("尻肉がまるで女性器を犯しているかのように絡み付いてくる・・・")
        out.printw()
        if y.f_ts_female() and suimin == 0:
            out.printl(f"女の姿で喘ぐ{F()}に男の時の面影が重なるが、不思議と萎える事はなく怒張は張りつめたまま。")
            out.printl(f"近いうちに男のままの{F()}としてみるのも悪くはない、と{T()}は昏い興奮を覚える。")
        out.printl(f"{F()}を抑えつけて激しく腰を振る{T()}・・・")
        out.printl("一夜限りの契りという免罪符が逆に枷を取り払ってしまったかの如く、")
        out.printl("パンパンと打ちつける淫音が響くたびに快楽が増幅されていく。")
        out.printw()
        if y.tc_("未熟") == 1:
            out.printl(f"やがて二人同時に絶頂を迎えた{T()}の表情は")
        else:
            if suimin == 0:
                out.printl(f"{F()}が絶頂を迎えるのと同時に、")
            out.printl(f"我慢できずに達した{T()}が直腸内に精を放った。")
            out.printl(f"ビュルッビュルッと尻穴に精液を注ぎ込む{T()}の表情は")
        out.printl("まるで普段とは別人のように恍惚としている・・・")
        out.printw()
        y.executor_houshi()
        y.switch()
        L = y.L
        L[2] = 100
        L[121] = 2
        L[122] = 1
        y.semen_l()
        y.inc_f_l()
        _prison(ctx, L)
        _ablup1(ctx)
        return
    if y.af("Ａ感覚") < 2:  # :3341–3498 不慣れ
        if y.inc_tf() > 0:
            _houshi_family(
                y,
                "が男性化して入ってきた時から予感はあった。",
                "に男の娘になるよう命じられた時から予感はあった。",
                lambda: y.tf("男の娘") > 0 and y.tf("変身時男の娘") < 0 and y.f.cflag[1] > 0,
            )
            out.printl(f"今から{F()}のカラダを捧げることになるのだろう、と。")
            out.printl(f"触手に蹂躙される前に愛する家族が…{F()}も同じ立場ならそうしたのだろうか。")
        out.printw()
        out.printl(f"{T()}は{F()}の窄まりに自らのペニスをあてがうと、")
        out.printl("痛がらないようにゆっくりと亀頭を挿入し、ずぶずぶと押し込んでいった。")
        if suimin == 0:
            out.printl(f"自ら受け入れるように{F()}が脚を絡めて抱き寄せる。")
        out.printw()
        out.print("ペニスを半ばまで挿入したところでまだ異物に不慣れなアヌスが怯えるようにひゅくんっと痙攣する")
        out.printl("が、" if suimin == 0 else "。")
        if suimin == 0:
            out.printl(f"{F()}は涙を浮かべながらも幸せそうな表情をしている・・・")
        out.printl()
        out.printw()
        out.printl("パンパンと肉と肉のぶつかる音と荒い息遣いが部屋の空気を震わせる。")
        out.printl("激しくはないが情熱的なピストンに腸内を抉られ、")
        if suimin == 1:
            out.printl(f"{F()}は眠ったまま尻穴を犯されているにも関わらず甘い喘ぎ声を漏らしている。")
        else:
            out.printl(f"{F()}は異物感と快楽がせめぎ合っている様子で声を堪えている。")
        out.printw()
        if y.tc_("未熟") == 1:  # :3409–3432
            out.printl(f"限界に達した{T()}が恍惚の表情を浮かべて絶頂するのと、")
            out.printl(f"男性器に犯されているにも関わらず{F()}がアナルアクメを迎えたのは同時だった・・・")
        elif y.tc_("淫乱") > 0 or y.lover_ft() > 0:
            if suimin == 1:
                out.printl(f"{F()}の寝込みを襲い、ゴムも付けずに生挿入し、無抵抗を良いことにアヌスを奪い、")
                out.printl("そのうえ女性器にするように無責任中出ししたらと想像すると、動悸が激しくなり怒張もさらに張りつめる。")
                out.printl(f"限界に近付いた{T()}はペニスを腸奥に押し付け、無言で中出しを敢行した。")
                out.printl(f"{F()}は寝入ったまま腸内射精を迎え、")
                out.printl("不慣れな尻穴性交にも関わらず二人は同時に絶頂し、勢いよく精液が腸内へと注ぎこまれていった・・・")
            elif st.rng.rand(2) == 0:
                out.printl(f"{F()}はアナルセックスだから妊娠しない、いくら出してもなんともないはずだ、")
                out.printl(f"限界に達した{T()}は身勝手な言い訳を並べ立てて、強引に中出しを敢行した。")
                out.printl("不慣れな尻穴性交にも関わらず二人は同時に絶頂し、勢いよく精液が腸内へと注ぎこまれていった・・・")
            else:
                out.printl(f"限界に近付いた{T()}が中に出しても良いかと問うと、")
                out.printl(f"{F()}は足を絡めて無言で中出しを許可した。")
                out.printl("不慣れな尻穴性交にも関わらず二人は同時に絶頂し、勢いよく精液が腸内へと注ぎこまれていった・・・")
        else:
            out.printl(f"我慢できずに達した{T()}が謝りながら直腸内に精を放つのと、")
            out.printl(f"不慣れな尻穴性交にも関わらず{F()}が絶頂したのは同時だった・・・")
        out.printl()
        if suimin == 1:
            _houshi_suimin_after(y, "菊門", always=True)
        out.printw()
        y.executor_houshi()
        y.switch()
        L = y.L
        L[2] = 100
        L[10] = 50
        L[121] = 2
        L[122] = 1
        y.semen_l()
        y.inc_f_l()
        _prison(ctx, L)
        _ablup1(ctx)
        return
    # :3501–3633 Ａ感覚２以上
    out.printl(f"{T()}は{F()}に覆いかぶさると、")
    out.printl("勃起しきったペニスを腸奥まで挿入して深い抽送を開始した。")
    out.printl("尻肉がまるで女性器を犯しているかのように、いや、それ以上に絡み付いてくる・・・")
    out.printl(f"すでに内側が潤いきっていた{F()}は痛がる様子も無く、")
    if suimin == 1:
        out.printl("眠りながらもきゅうきゅうと腸壁を収縮させ、夢の中で快楽を享受しているようだ・・・")
    else:
        out.printl("むしろ快楽を貪るようにして互いの口づけを求め合う・・・")
    out.printw()
    out.printl(f"{F()}を抑えつけて激しく腰を振る{T()}・・・")
    out.printl("一夜限りの契りという免罪符が逆に枷を取り払ってしまったかの如く、")
    out.printl("パンパンと打ちつける淫音が響くたびに快楽が増幅されていく。")
    out.printw()
    t_love = y.tc_("淫乱") > 0 or y.lover_tf() > 0
    if y.tc_("未熟") == 1:  # :3518–3563
        out.printl(f"やがて{T()}がほどなく限界に達し、{F()}もまた絶頂を迎えた。")
        out.printl(f"{F()}に抱き付いたまま余韻に蕩けきった{T()}の表情は")
    elif suimin == 1:
        if y.tc_("淫乱") > 0:
            out.printl(f"{F()}の寝込みを襲い、ゴムも付けずに生挿入し、無抵抗を良いことにアヌスを奪い、")
            out.printl("そのうえ女性器にするように無責任中出ししたらと想像すると、動悸が激しくなり怒張もさらに張りつめる。")
            out.printl(f"限界に近付いたペニスを腸奥に押し付け、無言で中出しを敢行した{T()}の表情は")
        else:
            out.printl(f"限界に達したペニスを引き抜いて射精した{T()}の表情は")
    elif t_love and (y.tf("淫乱") > 0 or y.lover_ft() > 0):
        out.printl(f"腸内に出したい、と{T()}が言うと{F()}は紅潮した顔で頷き、")
        out.printl(f"口づけを交わしながら{T()}の背に手足を絡めて引き寄せた。")
        out.printl(f"{F()}はこんなにかわいいから妊娠できるはずだ、中出しすれば孕んでしまうはずだ、")
        if y.lover_ft() > 0:
            out.printl(f"だから妊娠させたい、{_self_call(ctx)}の子どもを産んで欲しい、と")
        else:
            out.printl("我慢しようとしても吸い付いてくる男の娘マンコが気持ち良すぎる、もし孕んでも責任はとらない、と")
        out.printl(f"{T()}は熱に浮かされたように並べ立てて、一層激しく腰を打ちつける。")
        out.printl("激しくなっていくピストンが限界に達すると直腸の内奥に昂った欲情が一気に放出され、")
        out.printl(f"同時に絶頂して精液をアヌスで受け止める{F()}の表情は")
    elif t_love:
        out.printl(f"腸内に出したい、と{T()}が言うと{F()}は咄嗟に首を横に振ったが、")
        out.printl(f"もはや欲望の虜になっている{T()}が中出しの誘惑に耐えきれるはずもなく、")
        out.printl(f"{F()}はこんなにかわいいから妊娠できるはずだ、中出しすれば孕んでしまうはずだ、")
        if y.lover_ft() > 0:
            out.printl(f"だから妊娠させたい、{_self_call(ctx)}の子どもを産んで欲しい、と")
        else:
            out.printl("我慢しようとしても吸い付いてくる男の娘マンコが気持ち良すぎる、もし孕んでも責任はとらない、と")
        out.printl(f"{T()}は熱に浮かされたように並べ立てて、一層激しく腰を打ちつける。")
        out.printl("限界に達すると直腸の内奥に腰を突き入れて昂った欲情を一気に放出した。")
        out.printl(f"同時に絶頂して精液をアヌスで受け止める{F()}の表情は")
    else:
        out.printl(f"絶頂が近付いた{T()}は爆発寸前のペニスを引き抜こうとするも、")
        out.printl(f"きゅっと締めつけたアヌスに我慢できず、謝りながら{F()}の直腸内に精を放った。")
        out.printl(f"同時に絶頂を迎えて痙攣する{F()}の尻穴にビュルッビュルッと精液を注ぎ込む{T()}の表情は")
        y.L[324] = 1
    out.printl("まるで普段とは別人のように恍惚としている・・・")
    out.printl()
    if suimin == 1:
        _houshi_suimin_after(y, "菊門", always=False)
    out.printw()
    y.executor_houshi()
    fellatio = y.L[324]  # VARSET LOCAL（y.switch）前の値（下の DEVIATION 参照）
    y.switch()
    L = y.L
    L[2] = 100
    L[121] = 2
    L[122] = 1
    y.semen_l()
    # DEVIATION: 使用者裁決（2026-10-01）：原作 :3622 `LOCAL:124 = LOCAL:324` は VARSET LOCAL の後なので恆 0。
    # VARSET 前の LOCAL:324（口内射精＝フェラあり）を保持し、:1738／:2063 と同じくフェラ経験に反映する
    # （deviations.md「使用者裁決 2026-10-01」）。
    L[124] = fellatio
    y.inc_f_l()
    _prison(ctx, L)
    _ablup1(ctx)
