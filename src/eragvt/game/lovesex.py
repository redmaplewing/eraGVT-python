"""いちゃラブセックス（恋人との夜の営み）：
`ゲーム内_イベント発生/強制発生イベント/FORCE_いちゃラブセックス.ERB`（LOVESEX_NIGHT／LOVESEX_KIND／SEX_V／SEX_A／SEX_V_CONDOM）。

路徑相對 `source/earGVP/ERB/`。呼び出し元は `SHOP_TURNEND.ERB@EVENTTURNEND`:112（`turnend.event_turnend`）。
SEX_V_CONDOM と AFTER_PILL は INPUT を含むのでジェネレータ（`yield` で入力待ち、`send(値)` で再開）。

地の文（`地の文/MESSAGE_SEX.ERB`@MESSAGE_LOVESEX_NIGHT:1264／MESSAGE_SEX_V:1297／MESSAGE_SEX_A:1415／
MESSAGE_KATAOMOI_NIGHT:1489）は S07 catalog（`core.run_chinobun`）。KATAOMOI の TALENT:交際相手 の代入（:1559、:1575）は
`narration/hooks.py` の `LOVESEX_HOOK_LINES`。catalog が使えないとき（NullNarrationService）の fallback は、本文を佔位にして
地の文中の RAND（と状態変化）だけを ERB と同じ順で行う（乱数列が catalog 経路と一致する）。

引擎語意：
- キャラ変数の添字省略は TARGET（`reference/emuera-1824/Emuera/GameData/Variable/VariableParser.cs`:91–134）。
  `VARSET NOWEX`／`VARSET PALAM` は TARGET のキャラの配列全体を 0（`GameProc/Function/Instraction.Child.cs`:1132–1164）。
- `&&`／`||` は短絡（RAND は左辺が決まらないときだけ引く）：`GameData/Expression/OperatorMethod.cs`:532–536。
- LOCAL・#DIM は関数ごとに静的（`GameData/Variable/VariableToken.cs`:1712–1737）：SEX_V_CONDOM の `イチャックス回数` は
  呼び出しをまたいで累積する（SAVEDATA ではない → `st.temp.locals`）。
"""

from __future__ import annotations

from .counting import count_loop

from collections.abc import Generator

from .action import Ctx, config_check_event, print_callname
from .battle.ablup import ablup
from .battle.core import abl, is_hole, is_manly, run_chinobun, t, tc
from .battle.ninsin import after_pill, check_pregnant, ninsin_hantei
from .battle.palam import palam_cal
from .battle.sexcom import check_holyvirgin, palam_vabc_estimate
from .chara_common import is_female, is_male
from .era import times
from ..state import GameState

InputGen = Generator[None, int, int]

# DIM.ERH:256 `#DIM CONST 愛する人 = -3`
AISURU_HITO = -3


def _partner_word(ctx: Ctx, yes: str, no: str) -> str:
    """`\\@ TALENT:交際相手 == 4 ? yes # no \\@`（TARGET）。"""
    return yes if t(ctx, tc(ctx), "交際相手") == 4 else no


# --- @LOVESEX_NIGHT（:5–96）--------------------------------------------------------------


def lovesex_night(ctx: Ctx) -> Generator[None, int, None]:
    """`@LOVESEX_NIGHT`:5–96：夜のみ。各キャラの条件と RAND:100 < 欲望等 で夜の営み（片思いは告白）。"""
    st, data = ctx.state, ctx.data
    if st.time != 1:  # :7–8
        return
    saved = st.target  # :10
    for i in range(st.charanum):  # :11
        if i == GameState.MASTER:  # :12–13
            continue
        c = st.charas[i]
        if c.cflag[999] == 0:
            continue
        st.target = i  # :17
        if c.cflag[0] != 0:  # :20–21
            continue
        if c.cflag[99] >= 30:  # :24–25
            continue
        partner = t(ctx, c, "交際相手")
        if partner == 0 or partner >= 5 or (partner == 1 and st.rng.rand(10) > 4):  # :28–29
            continue
        if (not is_hole(ctx)) or (is_male(data, c) and abl(ctx, c, "Ａ感覚") < 2):  # :32–33
            continue
        if check_holyvirgin(ctx) == 1 and abl(ctx, c, "奉仕精神") + abl(ctx, c, "精液中毒") + abl(ctx, c, "Ａ感覚") < 3:
            continue  # :36–37
        if is_manly(ctx) and partner == 1:  # :40–41
            continue
        l1 = 0
        l3 = 0
        if t(ctx, c, "処女") > 0:  # :47–65
            l3 = {2: 12, 3: 6, 4: 3}.get(partner, 0)
            l3 += {1: 16, 2: 8, 3: 4, 4: 2}.get(t(ctx, c, "学生"), 0)
            if st.day[0] < l3 and st.rng.rand(4) != 0:
                continue
        l1 += abl(ctx, c, "欲望") * 5  # :67
        l1 += abl(ctx, c, "精液中毒") * 2  # :69
        houshi = abl(ctx, c, "奉仕精神")  # :71–81
        if houshi >= 5:
            l1 += 35
        elif houshi >= 1:
            l1 += {4: 30, 3: 25, 2: 20, 1: 15}[houshi]
        if st.rng.rand(100) < l1:  # :82
            if partner == 1:
                message_kataomoi_night(ctx)  # :85
            else:
                run_chinobun(ctx, "MESSAGE_LOVESEX_NIGHT")  # :88（RAND・状態変化なし）
                yield from lovesex_kind(ctx, st.target, 0)  # :89
                ablup(ctx, 0)  # :90
            ctx.out.printw()  # :92
            tc(ctx).palam.clear()  # :93 VARSET PALAM
    st.target = saved  # :96


def message_kataomoi_night(ctx: Ctx) -> None:
    """`地の文/MESSAGE_SEX.ERB@MESSAGE_KATAOMOI_NIGHT`:1489–1576。fallback は :1547 の RAND:100 と交際相手の変化のみ。"""

    def fallback() -> None:
        c = tc(ctx)
        idx = ctx.data.index_of("TALENT", "交際相手")
        r = ctx.state.rng.rand(100)  # :1547
        if r >= 95:
            c.talent[idx] = 0  # :1559
        elif r >= 65:
            pass
        else:
            c.talent[idx] += 1  # :1575

    run_chinobun(ctx, "MESSAGE_KATAOMOI_NIGHT", fallback=fallback)


# --- @LOVESEX_KIND（:100–147）------------------------------------------------------------


def lovesex_kind(ctx: Ctx, arg: int, arg1: int) -> InputGen:
    """`@LOVESEX_KIND, ARG, ARG:1`:100–147。"""
    st, data = ctx.state, ctx.data
    c = st.charas[arg]
    l0 = l1 = 0
    sex_twice = 0  # :107
    tc(ctx).nowex.clear()  # :110 VARSET NOWEX
    l2 = st.rng.rand(10)  # :112
    if t(ctx, c, "淫壷") > 0 and l2 > 5 and check_holyvirgin(ctx) == 0:  # :114–116
        yield from sex_v(ctx, arg, 0)
        sex_twice += 1
    elif t(ctx, c, "淫尻") > 0:  # :117–118
        yield from sex_a(ctx, arg)
    tc(ctx).nowex.clear()  # :122
    if abl(ctx, c, "Ａ感覚") > 1:  # :125–126
        l0 = 1
    if l0 == 0:  # :128–133
        yield from sex_v(ctx, arg, 1 if sex_twice == 1 else 0)
    else:  # :134–145
        if is_female(data, c) and check_holyvirgin(ctx) == 0:
            l1 = st.rng.rand(100)
        if l1 >= 50:
            yield from sex_v(ctx, arg, 1 if sex_twice == 1 else 0)
        else:
            yield from sex_a(ctx, arg)
    return 1


# --- 快感度テーブル -----------------------------------------------------------------------

_C_TABLE = (200, 1000, 2000, 4000, 10000, 20000)  # SEX_V:176–188 Ｃ感覚
_B_TABLE = (200, 400, 1000, 2000, 4000, 10000)  # :191–203 Ｂ感覚
_V_TABLE = (200, 400, 1000, 4000, 10000, 20000)  # :206–218 Ｖ感覚
_A_TABLE = (0, 0, 2000, 4000, 10000, 20000)  # SEX_A:354–362 Ａ感覚（0・1 は代入なし＝0）
_GIKOU = (None, None, "1.10", "1.25", "1.50", "2.00")  # :234–252／:365–375 技巧
_V_ROSHUTSU = (50, 100, 200, 500, 1000, 2000)  # SEX_V:263–290 屈服・恥情
_A_ROSHUTSU = (100, 200, 500, 1000, 2000, 4000)  # SEX_A:385–412
_YOKUJOU = (0, 1000, 2000, 5000, 10000, 20000)  # :293–303／:415–425 奉仕精神（0 は代入なし＝0）
_SHUTOKU = (200, 400, 800, 1000, 2000, 4000)  # :307–319／:429–441


def _tbl(table: tuple, v: int):
    """`IF … == 0 … ELSEIF … >= 5`：負の値はどの分岐にも当たらない（0 のまま）。"""
    if v < 0:
        return 0 if isinstance(table[0], int) else None
    return table[min(v, 5)]


def _gikou(ctx: Ctx, c, *values: int) -> list[int]:
    f = _tbl(_GIKOU, abl(ctx, c, "技巧"))
    return [times(v, f) if f else v for v in values]


# --- @SEX_V（:151–337）---------------------------------------------------------------------


def sex_v(ctx: Ctx, arg: int, arg1: int = 0) -> InputGen:
    """`@SEX_V, ARG, ARG:1 = 0`:151–337（ARG:1 == 1 → 淫壷による二回目）。"""
    st, data = ctx.state, ctx.data
    c = st.charas[arg]
    l100 = 0  # :152
    if arg1 == 1 or t(ctx, tc(ctx), "処女") > 0:  # :155–160
        pass
    elif config_check_event(st, 6) == 1:
        l100 = yield from sex_v_condom(ctx, arg)
    L = [0 for _ in count_loop(ctx.state, 12)] + [0]  # :165–167 REPEAT 12（LOCAL:12 は :322 で代入）
    ex = lambda n: data.index_of("EXP", n)  # noqa: E731
    if check_holyvirgin(ctx) == 0:  # :170–171
        c.exp[ex("Ｖ経験")] += 1
    c.exp[ex("精液経験")] += 1  # :173
    c.exp[ex("フェラ経験")] += 1  # :174
    L[0] = _tbl(_C_TABLE, abl(ctx, c, "Ｃ感覚"))
    L[3] = _tbl(_B_TABLE, abl(ctx, c, "Ｂ感覚"))
    L[1] = _tbl(_V_TABLE, abl(ctx, c, "Ｖ感覚"))
    tcc = tc(ctx)
    if t(ctx, tcc, "処女") == 1 and check_holyvirgin(ctx) == 0:  # :220–224
        tcc.talent[data.index_of("TALENT", "処女")] = -1
        tcc.cflag[206] = 5
        L[10] = 2500
    if config_check_event(st, 6) == 1 and l100 == 1:  # :227–231
        L[0] = times(L[0], "0.95")
        L[1] = times(L[1], "0.90")
        L[3] = times(L[3], "0.95")
    L[0], L[1], L[3] = _gikou(ctx, c, L[0], L[1], L[3])  # :234–252
    palam_vabc_estimate(ctx, L, 0, 1, 3, -1)  # :255
    message_sex_v(ctx, l100)  # :259
    ro = abl(ctx, c, "露出癖")
    L[8] = _tbl(_V_ROSHUTSU, ro)  # :263–275
    L[9] = _tbl(_V_ROSHUTSU, ro)  # :278–290
    houshi = abl(ctx, c, "奉仕精神")
    L[7] = _tbl(_YOKUJOU, houshi)  # :293–303
    L[6] = _tbl(_SHUTOKU, houshi)  # :307–319
    L[12] = 150  # :322
    yield from palam_cal(ctx, *L[:12], losebase=L[12])  # :325
    if config_check_event(st, 6) == 1 and l100 == 1:  # :328–337
        return 0
    tcc.cflag[218] += 1  # :331
    yield from after_pill(ctx, st.target, 75, AISURU_HITO)  # :333
    if is_female(data, tcc):  # :335–336
        yield from ninsin_hantei(ctx, 6, 800, AISURU_HITO)
    return 0


def message_sex_v(ctx: Ctx, arg0: int) -> None:
    """`地の文/MESSAGE_SEX.ERB@MESSAGE_SEX_V(ARG:0)`:1297–1411。fallback は RAND のみ（:1315 RAND:4、CASE 2 の :1352 RAND:5）。"""

    def fallback() -> None:
        rand = ctx.state.rng.rand
        if t(ctx, tc(ctx), "処女") == 1:  # :1301
            return
        if rand(4) == 2:  # :1315 SELECTCASE RAND:4 → CASE 2
            rand(5)  # :1352

    run_chinobun(ctx, "MESSAGE_SEX_V", (arg0,), fallback=fallback)


# --- @SEX_A（:341–447）---------------------------------------------------------------------


def sex_a(ctx: Ctx, arg: int) -> Generator[None, int, None]:
    """`@SEX_A, ARG`:341–447。"""
    st, data = ctx.state, ctx.data
    c = st.charas[arg]
    L = [0 for _ in count_loop(ctx.state, 12)] + [0]  # :345–347
    ex = lambda n: data.index_of("EXP", n)  # noqa: E731
    c.exp[ex("精液経験")] += 1  # :350
    c.exp[ex("Ａ経験")] += 1  # :351
    c.exp[ex("フェラ経験")] += 1  # :352
    L[2] = _tbl(_A_TABLE, abl(ctx, c, "Ａ感覚"))  # :354–362
    (L[2],) = _gikou(ctx, c, L[2])  # :365–375
    palam_vabc_estimate(ctx, L, 2, -1)  # :378
    message_sex_a(ctx)  # :382
    ro = abl(ctx, c, "露出癖")
    L[8] = _tbl(_A_ROSHUTSU, ro)  # :385–397
    L[9] = _tbl(_A_ROSHUTSU, ro)  # :400–412
    houshi = abl(ctx, c, "奉仕精神")
    L[7] = _tbl(_YOKUJOU, houshi)  # :415–425
    L[6] = _tbl(_SHUTOKU, houshi)  # :429–441
    L[12] = 150  # :444
    yield from palam_cal(ctx, *L[:12], losebase=L[12])  # :447


def message_sex_a(ctx: Ctx) -> None:
    """`@MESSAGE_SEX_A`:1415–1485。fallback は RAND のみ（:1419 RAND:2、:1429 RAND:10）。"""

    def fallback() -> None:
        rand = ctx.state.rng.rand
        if rand(2) == 1:
            rand(10)

    run_chinobun(ctx, "MESSAGE_SEX_A", fallback=fallback)


# --- @SEX_V_CONDOM（:451–528）--------------------------------------------------------------


def sex_v_condom(ctx: Ctx, arg: int) -> InputGen:
    """`@SEX_V_CONDOM, ARG`:451–528：RESULT 1 = ゴム有り、0 = 無し。"""
    st, out = ctx.state, ctx.out
    c = st.charas[arg]
    tcc = tc(ctx)
    idx = ctx.data.index_of("TALENT", "交際相手")
    l0 = 0
    for i in range(st.charanum):  # :456–462
        if i == GameState.MASTER:
            continue
        if 1 < st.charas[i].talent[idx] < 5:
            l0 += 1
    key = ("SEX_V_CONDOM", "イチャックス回数")
    st.temp.locals[key] = st.temp.locals.get(key, 0) + 1  # :464
    l1 = st.rng.rand(3) + 2 + l0  # :465
    if not st.temp.locals[key] > l1:  # :468
        return 1
    name = print_callname(st, st.target)
    out.printl(f"{_partner_word(ctx, '夫', '彼氏')}はどうやらゴムを着けずに生でのセックスがしたいようだ・・・")
    out.printl("受け入れますか？")
    out.printl("[0]はい")
    out.printl("[1]いいえ")
    st.temp.locals[key] = 0  # :474
    while True:  # :475–525
        r = yield
        if r == 0:
            if check_pregnant(ctx, st.target) > 0:
                if t(ctx, tcc, "苗床化") > 0:
                    out.printl(f"触手の苗床と成り果て仔を孕んだ身体を愛してくれる{_partner_word(ctx, '夫', '彼氏')}を抱きしめ、")
                    out.printl(f"{name}は情欲に塗れた瞳でペニスを直に受け入れた・・・")
                elif tcc.cflag[222] > 3:
                    out.printl(f"{name}はお腹の子に優しくしてと言いながら、ギンギンに反り返る男根を")
                    out.printl("期待に涎を垂らす下の口へと迎え入れた・・・")
                else:
                    out.printl(f"{_partner_word(ctx, '夫', '想い人')}の子を孕んでもいいと熱に浮かされたようにうなずく{name}は、")
                    out.printl("すでに胎児が子宮に宿っていることに気づかぬまま剛直を蜜壺へと飲み込んだ・・・")
            else:
                if abl(ctx, c, "欲望") >= 6 and abl(ctx, c, "精液中毒") >= 2:
                    out.printl("子作り交尾への熱い眼差しを向けられた瞬間、直接注ぎ込まれる精液の熱さを想像して")
                    out.printl(f"{name}は子宮の疼きが止まらなくなってしまう。")
                    out.printl("自らぐっしょりと濡れた秘所を拡げると、完全に発情した様子でペニスを迎え入れた・・・")
                elif abl(ctx, c, "欲望") >= 4:
                    out.printl(f"いつもより一回り大きく固く屹立するペニスを前にして、{name}は")
                    out.printl("ソレに直接膣内を掻き回される誘惑に抗えず、コンドームを脇へと追いやった・・・")
                else:
                    out.printl(f"一瞬戦いへの影響が脳裏にチラつくが、肉体の火照りと{_partner_word(ctx, '夫', '想い人')}の熱い押しに抗いきれなかった")
                    out.printl(f"{name}は子を孕むかもしれない性交を受け入れた・・・")
            out.printl()
            return 0
        if r == 1:
            if check_pregnant(ctx, st.target) > 0:
                if t(ctx, tcc, "苗床化") > 0:
                    out.printl("すでに触手の苗床と成り果てた身体に、人間の精液では満足出来な――……")
                    out.printl("……正常に産めるかどうかわからないと、どこか虚ろな眼で")
                elif tcc.cflag[222] > 3:
                    out.printl("お腹の子に影響があるといけないからと、疼く身体を抑えながら")
                else:
                    out.printl("すでに胎児が子宮に宿っていることに気づかぬまま、避妊のためにと")
            else:
                out.printl("何が起きるかわからない触手という災禍の中、不用意に妊娠するわけにはいかない。")
                out.print("もどかしさを感じながら、")
            out.printl(f"{name}は{_partner_word(ctx, '夫', '彼氏')}のペニスにゴムを装着した・・・")
            out.printl()
            return 1
        # :523–524 GOTO INPUT_LOOP_0（何も出さずに再入力）
