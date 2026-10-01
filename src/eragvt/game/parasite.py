"""寄生触手（S17）：`ゲーム内_イベント発生/強制発生イベント/FORCE_深夜の寄生触手暴走.ERB`（路徑相對 `source/earGVP/ERB/`）。

呼び出し元は `インターミッション画面/SHOP_TURNEND.ERB@EVENTSHOP`:161 `CALL PARASITE` のみ（全 ERB で唯一）。
共生取得（:331）・慰み者（:394）・夜這い対象（:651）が INPUT を使うので、PARASITE 以下はジェネレータ
（`r = yield` で整数を受け取る。INPUT は既定値なし：`reference/emuera-1824/Emuera/GameProc/Function/
Instraction.Child.cs@INPUT_Instruction`:616–641、数値以外は受け付けない：`GameView/EmueraConsole.cs`:709–721）。

本文はイベント本体（地の文ファイルではない）の中で状態変化と交互に出力されるので、S15 の AFTER_TRAIN_RAPE と同じく
Python で移植する。

引擎語意：
- LOCAL は関数ごとに静的（`GameData/Variable/VariableToken.cs`:1712–1737、ResetData／読込でのみ 0：
  `VariableData.cs@SetDefaultLocalValue`:514–520）。PARASITE の `LOCAL:2`（:50–52 DRAWLINE を最初の 1 回だけ）は
  VARSET されないので、プロセス中で最初に暴走／慰み者が起きたときだけ DRAWLINE が出る（`st.temp.locals` に保持）。
  PARASITE_ACTION（:110）・SYNBIOSIS_ABL_UP（:958）・SYNBIOSIS_YOBAI_EVENT（:584）は VARSET LOCAL する。
- 関数末尾まで流れ落ちると RESULT = 0（`GameProc/Process.ScriptProc.cs`:61–67）、引数なし RETURN も 0。
- キャラ変数の添字省略は TARGET（`GameData/Variable/VariableParser.cs`:91–134）。
- `&&`／`||` は短絡（`GameData/Expression/OperatorMethod.cs`:532–536）。

`@SYNBIOSIS_OUT_OF_CONTROL_EVENT`（:542–565）は呼び出し 2 箇所（:411、:420）がどちらもコメントアウトされていて
全 ERB に呼び出し元が無いので移植しない（`@SHIFTFOWARD_CHARA` と同じ扱い）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state import GameState
from .action import Ctx, config_check_maniac, print_callname, print_transcallname
from .battle.core import abl, t, tc
from .chara_common import charatalent, is_female, is_male
from .era import div, format_percent
from .relation import (
    AISURU,
    DOREI,
    GIRI,
    HAIGUUSHA,
    IKIWAKARE,
    ITOKO,
    JUUSHA,
    KATAOMOI,
    KOIBITO,
    KONYAKU,
    KYOUDAI,
    OIMEI,
    OJIOBA,
    OYAKO,
    SHITASHII,
    SHUJIN,
    SOEN,
    SOFUBO,
    YUUJIN,
    ZOUO,
    toshiue,
)
from .shop import charanum_active

InputGen = Generator[None, int, int]

_LOCAL_SIZE = 200


# --- @PARASITE（:3–68）-----------------------------------------------------------------------


def parasite(ctx: Ctx) -> Generator[None, int, None]:
    """`@PARASITE`:3–68。ループで FLAG:799 を上書きする（:9、原作どおり：SHOW_SHOP:20 で 0 に戻る）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    if config_check_maniac(st, 3) == 0:  # :6–7
        return
    for i in range(st.charanum):  # :8
        st.flag[799] = i  # :9
        if i == GameState.MASTER:  # :10–11
            continue
        c = st.charas[i]
        if c.cflag[999] == 0:  # :12–13
            continue
        if not t(ctx, c, "寄生"):  # :16、:65–66
            continue
        c.exp[data.index_of("EXP", "寄生経験")] += 1  # :17
        if t(ctx, c, "共生") == 0:  # :20–21
            c.cflag[82] += 1
        if c.cflag[0] != 0:  # :24–25
            continue
        if st.time == 0:  # :28–29
            continue
        local3 = 20 if c.cflag[83] > 0 else 50  # :32–37
        if t(ctx, c, "共生") == 0 and c.cflag[82] >= local3 and c.cflag[84] == 0:  # :38–43
            yield from synbiosis_get_event(ctx)
            continue
        e = c.exp[data.index_of("EXP", "寄生経験")]
        local = min(div(e * e * 200, e), 2500)  # :46（乗除は左結合：(e*e*200)/e）
        if st.rng.rand(10000) < local:  # :48
            if st.temp.locals.get(("PARASITE", 2), 0) == 0:  # :50–52（静的 LOCAL:2）
                out.drawline()
            st.temp.locals[("PARASITE", 2)] = 1
            if t(ctx, c, "共生") == 1:  # :54–60
                yield from synbiosis_event(ctx)
            else:
                parasite_event(ctx)
        # :64 GET_STATE_EXPUP（SHOP_TROPHY.ERB:506–）：実績のみ（deviations.md「全域資料」）


# --- @PARASITE_EVENT（:72–104）・@PARASITE_ACTION（:108–283）----------------------------------


def parasite_event(ctx: Ctx) -> None:
    """`@PARASITE_EVENT`:72–104（寄生触手の暴走）。"""
    st, out = ctx.state, ctx.out
    me = st.flag[799]
    while True:  # $LOOP :74–86
        if charanum_active(st) == 0:  # :76–77
            return
        if st.rng.rand(4) == 0:  # :78–82
            local = me
        else:
            local = st.rng.rand(st.charanum - 1) + 1
        if st.charanum < 3:  # :83–84
            local = me
        if st.charas[local].cflag[0] != 0 or st.charas[local].cflag[999] == 0:  # :85–86 GOTO LOOP
            continue
        break
    st.target = local  # :88
    out.printl()  # :90
    out.set_bold()
    out.printl("寄生触手の暴走")
    out.set_bold(False)
    out.printl()
    out.printl("深夜になると不気味な影が動き出す・・・")  # :95
    if local == me:  # :97–99
        out.printw(f"{print_callname(st, me)}は自身に寄生する触手を抑えきれずに、暴走を許してしまった！")
        parasite_action(ctx, 0)
    else:  # :101–103
        out.printw(f"{print_callname(st, me)}に寄生している触手が暴走し、本人の意志とは無関係に隣室の"
                   f"{st.target_chara.callname}に襲いかかった！")
        parasite_action(ctx, 1)


def _tbl(v: int, table: tuple[int, ...]) -> int:
    """`IF X == 0 … ELSEIF X == 4 … ELSE` 型（table は 0〜4 と ELSE の 6 要素。負の値も ELSE）。"""
    return table[v] if 0 <= v <= 4 else table[5]


_C = (100, 200, 500, 1000, 2000, 5000)
_VA_EXP = (2, 5, 8, 11, 15, 20)
_FEAR = {0: 800, 1: 400, 2: 200, 3: 100}  # :208–228（4 以上・負は代入なし）


def _sense_locals(ctx: Ctx) -> list[int]:
    """PARASITE_ACTION :111–185 ／ SYNBIOSIS_ABL_UP :960–1034（同一）。"""
    c = tc(ctx)
    a = lambda n: abl(ctx, c, n)  # noqa: E731
    L = [0] * _LOCAL_SIZE
    L[0] = _tbl(a("Ｃ感覚"), _C)  # :112–124
    if is_female(ctx.data, c):  # :128–149 オトコを除外
        L[120] = _tbl(a("Ｖ感覚"), _VA_EXP)
        L[1] = _tbl(a("Ｖ感覚"), _C)
    L[121] = _tbl(a("Ａ感覚"), _VA_EXP)  # :152–170
    L[2] = _tbl(a("Ａ感覚"), _C)
    # :173–185 快B：最初の条件だけ Ｂ感覚、ELSEIF 以降は Ｃ感覚を見ている（原作どおり）
    if a("Ｂ感覚") == 0:
        L[3] = 100
    else:
        cc = a("Ｃ感覚")
        L[3] = {1: 200, 2: 500, 3: 1000, 4: 2000}.get(cc, 5000)
    return L


def _virgin_and_rest(ctx: Ctx, L: list[int]) -> None:
    """PARASITE_ACTION :192–236 ／ SYNBIOSIS_ABL_UP :1036–1080。"""
    from .battle.sexcom import check_holyvirgin

    c = tc(ctx)
    out = ctx.out
    if t(ctx, c, "処女") == 1 and check_holyvirgin(ctx) == 0:  # :193–200（LOSTVIRGIN は呼ばない）
        L[10] = 500
        out.printl()
        out.printl("処女喪失")
        out.printl()
        c.talent[ctx.data.index_of("TALENT", "処女")] = -1
        c.cflag[206] = 4
    L[8] = 500  # :203 屈服
    sense = abl(ctx, c, "Ｖ感覚") if is_female(ctx.data, c) else abl(ctx, c, "Ａ感覚")  # :207–229
    if sense in _FEAR:
        L[11] = _FEAR[sense]
    # :231–236 コメントは「精液経験 10／フェラ経験 2」だがどちらも LOCAL:123（精液経験）への代入 → 2（原作どおり）
    L[123] = 10
    L[123] = 2
    L[150] = 1  # 異常経験


def _prison_tail(ctx: Ctx, L: list[int]) -> None:
    """:272–283 ／ :1085–1096 `COMMON_PRISON` → `COMMON_PRISON_EXP` ×100 → PRINTL → `_ABLUP, 1` → PRINTW。"""
    from .battle.ablup import ablup
    from .prison.commands import common_prison, common_prison_exp

    common_prison(ctx, L[0:12])
    for cc in range(100, 200):
        common_prison_exp(ctx, cc, L[cc])
    ctx.out.printl()
    ablup(ctx, 1)
    ctx.out.printw()


def parasite_action(ctx: Ctx, arg: int) -> None:
    """`@PARASITE_ACTION, ARG`:108–283（ARG = 0 自分、1 仲間を襲う）。"""
    from .battle.sexcom import check_holyvirgin, palam_vabc_estimate

    st, out = ctx.state, ctx.out
    L = _sense_locals(ctx)
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :188
    _virgin_and_rest(ctx, L)
    me = st.flag[799]
    tn = print_callname(st, st.target)
    out.printl()  # :239
    if arg == 0:  # :240–254
        out.printl("触手の粘液に媚薬効果でもあるのか、")
        if is_female(ctx.data, tc(ctx)):
            out.printl(f"{tn}の秘部は本人の意志とは無関係にしっとりと濡れている。")
        else:
            out.printl(f"{tn}のアナルは本人の意志とは無関係にひくひくと伸び縮みしている。")
        out.print("完全に独立した意志を見せる触手が")
        if check_holyvirgin(ctx) == 0 and is_female(ctx.data, tc(ctx)):  # :248–249
            out.print("ヴァギナと")
        out.printl("尻穴に潜り込み、")
        out.printl(f"口まで犯された{tn}はくぐもった悲鳴を上げるしかない。")
        out.printw()
        out.printl("抵抗できないと見るや触手は更にその数を増やし、")
        out.printl(f"{tn}が気絶するまで一方的な行為は続いた・・・")
    else:  # :255–268
        out.printl(f"蠢く触手の不意打ちに{tn}は咄嗟に反応できずに捕まってしまい、全身を愛撫されている。")
        if is_male(ctx.data, tc(ctx)):
            out.printl(f"{print_callname(st, me)}は仲間のピンチに何とかアナルを貫こうとする触手を止めようとするが、")
        else:
            out.printl(f"{print_callname(st, me)}は仲間のピンチに何とか秘部とアナルを貫こうとする触手を止めようとするが、")
        out.printl("逆に触手に絡め取られてしまう。")
        out.printw()
        out.printl("触手の粘液に媚薬効果でもあるのか、")
        out.printl("翻弄される二人は絡み合い、どちらともなく唇を重ね合った・・・")
    out.printw()  # :269
    _prison_tail(ctx, L)


# --- @SYNBIOSIS_GET_EVENT（:287–362）---------------------------------------------------------


def synbiosis_get_event(ctx: Ctx) -> Generator[None, int, None]:
    """`@SYNBIOSIS_GET_EVENT`:287–362（共生取得の確認。INPUT は値を検査しない：0 = はい、9 = 以後確認しない、他 = いいえ）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    me = st.flag[799]
    c = st.charas[me]
    n = print_callname(st, me)
    out.set_bold()  # :305–307
    out.printl(f"寄生触手との共生（{n}）")
    out.set_bold(False)
    out.printl()
    out.printl(f"{n}の身体が触手に寄生されてから、随分と時間が経過した。")  # :310–313
    out.printl(f"最近、逆に体の調子が良くなっていることに疑問を抱いた{n}は")
    out.printl("念のために精密検査をする事にしたようだ。")
    out.printw()
    out.printl("――")  # :315–318
    out.printl("――――")
    out.printw("――――――")
    out.printl()
    out.printl(f"精密検査の結果、{n}の肉体は寄生触手に順応し始めていることが分かった。")  # :320–326
    out.printl("このまま順応しきれば、寄生触手との関係は、寄生ではなく共生となる可能性もある。")
    out.printl("上手く触手と共生関係となる事が出来れば、")
    out.printl("触手が持つ能力――強力な再生能力や攻撃能力の恩恵を受けることが出来るだろう。")
    out.printl("但しその場合、体内の触手の除去が不可能となってしまうとの事だ。")
    out.printl("・・・触手との共生を望みますか？")
    out.printl()
    out.printl("[0]はい")  # :328–330
    out.printl("[1]いいえ")
    out.printl("[9]いいえ（次から確認しない）")
    r = yield  # :331 INPUT
    if r == 9:  # :333–334
        c.cflag[84] = 1
    out.printl()  # :336
    if r == 0:  # :337–347
        c.talent[data.index_of("TALENT", "共生")] = 1
        c.cflag[83] += c.cflag[82]
        c.cflag[82] = 0
        tn = print_transcallname(st, me)
        out.printl("触手の能力を自分のものに出来るのなら、これからの戦闘で優位に立つことが出来る。")
        out.printl("人類の敵を排除できるのなら、やむを得ない犠牲だろう。")
        out.printl(f"{tn}はそう自分に言い聞かせ、触手との共生を望んだ・・・。")
        out.printl()
        out.printl(f"{tn}は {data.names['TALENT'].get(163, '')} を得た")
    else:  # :348–360
        out.printl("流石に、体内に触手を飼ったまま一生を過ごすのは御免だ。")
        out.printl("医師に何とかならないかと尋ねると、特殊な薬を服用すれば一応対処は可能だと言う。")
        if r == 1:
            out.printl("但し一時しのぎにしかならず、時間が経てばまた同じことが起こるだろう、と。")
            out.printl(f"{n}は医師の言葉に同意し、用意された薬を服用した・・・。")
        else:
            out.printl("但し、この薬では体内の触手の除去までは出来ない")
            out.printl("何とかして寄生触手を除去しなければ、状況は好転しないだろう。")
            out.printl(f"{n}は担当医の言葉に同意し、用意された薬を服用した・・・。")
    out.printw()  # :362


# --- @SYNBIOSIS_EVENT（:367–424）・@SYNBIOSIS_SOLO_EVENT（:429–537）---------------------------


def synbiosis_event(ctx: Ctx) -> Generator[None, int, None]:
    """`@SYNBIOSIS_EVENT`:367–424（寄生触手の慰み者）。"""
    st, out = ctx.state, ctx.out
    n = print_callname(st, st.flag[799])
    out.printl()  # :370
    out.set_bold()
    out.printl(f"寄生触手の慰み者（{n}）")
    out.set_bold(False)
    out.printw()
    out.printl(f"夜も更けた頃、{n}は強烈な渇きを感じて目を覚ました。")  # :376–380
    out.printl("渇きを潤すために冷たい水を飲んだものの、気分は一向に晴れない。")
    out.printl("水では癒されない、人の体液が欲しい")
    out.printl(f"そう思った{n}は――")
    out.printl()
    y_result = check_synbiosis_yobai_target(ctx)  # :383–384
    out.printl("[0]自分自身を慰み者にする")  # :386–391
    if y_result == 0:
        out.printl("[1]仲間の元へ向かう")
    out.printl("[999]我慢して寝る")
    while True:  # $INPUT_LOOP_SYNBIOSIS_EVENT :393–424
        r = yield
        out.printl()  # :396
        if r == 0:
            synbiosis_solo_event(ctx)
        elif r == 1 and y_result == 0:  # :400–412
            res = yield from synbiosis_yobai_event(ctx)
            if res == 999:
                out.printl()
                out.printl("やはり止めよう、仲間を傷付けるわけにはいかない。")
                out.printl(f"そう思った{print_callname(st, st.flag[799])}は、喉の渇きを我慢しつつベッドの中に潜り込んだ。")
                out.printw()
                # :411 CALL SYNBIOSIS_OUT_OF_CONTROL_EVENT はコメントアウト（原作）
        elif r == 999:  # :413–420
            out.printl("なんて恐ろしいことを考えているのだろう")
            out.printl("これではまるで、自分が触手となってしまったようじゃないか")
            out.printl(f"そう思った{print_callname(st, st.flag[799])}は、喉の渇きを我慢しつつベッドの中に潜り込んだ。")
            out.printw()
            # :420 CALL SYNBIOSIS_OUT_OF_CONTROL_EVENT はコメントアウト（原作）
        else:  # :421–423
            out.printl("正しい値を入力してください")
            continue
        return


_HIP = {1: "ぷるぷると震える安産型のお尻に", 2: "むっちりとした柔らかい肉付きのお尻に",
        5: "むちむちとしたボリュームたっぷりのお尻に", 6: "ぶるんぶるんと弾むほど膨れ上がったお尻に"}


def _dash(ctx: Ctx) -> None:
    """`DRAWLINE / PRINTL ―― / PRINTL ―――― / PRINTW ―――――― / PRINTL`（:435–439、:672–676）。"""
    out = ctx.out
    out.drawline()
    out.printl("――")
    out.printl("――――")
    out.printw("――――――")
    out.printl()


def synbiosis_solo_event(ctx: Ctx) -> None:
    """`@SYNBIOSIS_SOLO_EVENT`:429–537（自分自身を慰み者にする）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    st.target = st.flag[799]  # :431
    c = tc(ctx)
    tl = lambda name: t(ctx, c, name)  # noqa: E731
    n = print_callname(st, st.target)
    _dash(ctx)
    out.printl(f"{n}は粘液でぬめりを帯びた触手を展開すると、")
    out.print("その")
    if tl("小柄") == 1:
        out.print("小柄な")
    if tl("長身") == 1:
        out.print("スラリと伸びた")
    if charatalent(data, c, 0, "オトコ") == 0:  # :442–493
        out.printl("身体に舌を這わせるかのように絡みつかせ、")
        if tl("巨乳") > 2:
            out.printl("はち切れんばかりの乳房や")
        elif tl("巨乳") > 0:
            out.printl("たわわに実った乳房や")
        elif tl("貧乳") > 0:
            out.printl("小ぶりで愛らしい乳房や")
        else:
            out.printl("程よい大きさに育った乳房や")
        out.print(_HIP.get(tl("外見"), "程よい肉付きのお尻に"))
        out.printl("触手を這わせ、激しく愛撫しだした。")
        out.printl()
        out.printl(f"媚薬効果のある粘液に塗れ、全身が性感帯のように敏感になった{n}は、")
        if tl("母乳体質"):
            out.print("母乳と")
        if tl("ふたなり") > 0:
            out.print("精液と")
        out.printl("潮をまき散らしながら、何度も絶頂を繰り返す。")
        out.printl(f"やがて、それでも満足できなくなった{n}は")
        out.printl("うねり猛る触手を前後の穴に添えさせ一気に貫かせた。")
    else:  # :494–534
        if tl("男の娘") == 1:
            out.print("少女然とした")
        out.printl("身体に舌を這わせるかのように絡みつかせ、")
        out.printl("かすかに震える桜色の乳首や")
        out.print(_HIP.get(tl("外見"), "程よい肉付きのお尻に"))
        out.printl("触手を這わせ、激しく愛撫しだした。")
        out.printl()
        out.printl(f"媚薬効果のある粘液に塗れ、全身が性感帯のように敏感になった{n}は、")
        out.printl("精液をまき散らしながら、何度も絶頂を繰り返す。")
        out.printl(f"やがて、それでも満足できなくなった{n}は")
        out.printl("うねり猛る触手を唇と後ろの穴に添えさせ一気に貫かせた。")
    out.printl()
    out.printl("それから数時間後。")
    out.printl(f"触手が放つ白濁の液体に塗れ、ようやく満足した{n}は、")
    out.printl("深い眠りについた。")
    synbiosis_abl_up(ctx, 0)  # :537


# --- 夜這い（:570–760）---------------------------------------------------------------------------


def _yobai_candidates(ctx: Ctx, stop_at_first: bool) -> list[int]:
    """:596–623 ／ :729–754 の対象選別（実行者の性別は考慮しない、性別嗜好のみ）。"""
    st, data = ctx.state, ctx.data
    me = st.charas[st.flag[799]]
    tm = lambda name: t(ctx, me, name)  # noqa: E731
    found: list[int] = []
    for i in range(st.charanum):
        if i == GameState.MASTER or i == st.flag[799]:
            continue
        o = st.charas[i]
        if o.cflag[999] == 0:
            continue
        if t(ctx, o, "繁殖袋") > 0 or t(ctx, o, "四肢欠損") > 0:
            continue
        if (tm("男性苦手") > 0 and tm("両刀") == 0) and is_male(data, o):
            continue
        if (tm("女性苦手") > 0 and tm("両刀") == 0) and is_female(data, o):
            continue
        found.append(i)
        if stop_at_first:  # :752–753 BREAK
            break
    return found


def check_synbiosis_yobai_target(ctx: Ctx) -> int:
    """`@CHECK_SYNBIOSIS_YOBAI_TARGET`:718–760：対象がいれば 0、いなければ -999。"""
    if charanum_active(ctx.state) < 2:  # :724–725
        return -999
    return 0 if _yobai_candidates(ctx, True) else -999


def synbiosis_yobai_event(ctx: Ctx) -> InputGen:
    """`@SYNBIOSIS_YOBAI_EVENT`:570–663。戻り値（RESULT）：999 = やめる、-999 = 対象なし、それ以外 0。"""
    st, out = ctx.state, ctx.out
    if charanum_active(st) < 2:  # :592–593
        return 0
    targets = _yobai_candidates(ctx, False)  # :596–623
    find = len(targets)
    if st.flag[999] == 1:  # :626–635 デバッグ
        out.set_color((105, 105, 105))
        out.printl("夜這い可能キャラリスト")
        for i in targets:
            out.printl(f"対象　{st.charas[i].callname}, キャラ番号:{i}")
        out.reset_color()
    if find <= 0:  # :638–639
        return -999
    out.printl()  # :643–645
    out.printl("誰の部屋に行きますか？")
    out.printl()
    print_chara_list(ctx, targets)  # :648
    while True:  # $INPUT_LOOP_CHARA_LIST :650–663
        r = yield
        if r == 999:
            return 999
        if 0 < r < st.charanum:  # :655–659（リスト外のキャラ番号も受け付ける：原作どおり）
            st.target = r
            synbiosis_yobai_action(ctx)
            return 0
        out.printl("正しい値を入力してください")


def synbiosis_yobai_action(ctx: Ctx) -> None:
    """`@SYNBIOSIS_YOBAI_ACTION`:667–713（共生触手による夜這い）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    me = print_callname(st, st.flag[799])
    tn = print_callname(st, st.target)
    _dash(ctx)
    out.printl(f"{me}は無意識の内に、{tn}の部屋の前まで足を運んでいた。")  # :678–682
    out.printl(f"扉には鍵が掛かっていたが、{me}は鍵穴に細長い触手を潜り込ませ開錠してしまう。")
    out.printl(f"{me}は部屋の中に忍び込むと、ベッドの上で静かに寝息を立てる{tn}の枕元に音もなく近づき、")
    out.printl(f"粘液に塗れた触手を{tn}に巻き付かせた。")
    out.printl()
    out.printl(f"突然触手に襲われ、悲鳴を上げようとする{tn}だったが、口腔に押し込まれた触手によって遮られてしまう。")  # :684–687
    out.printl(f"直後、ドロっとした粘着性のある液体を注ぎ込まれ、抵抗も出来ない{tn}は喉を鳴らして飲み干していく。")
    out.printl(f"強力な媚毒が含まれた液体を注ぎ込まれた{tn}の身体は情欲に支配され、")
    out.printl(f"心ではいけないと思いつつも、その肢体を{me}の前にさらけ出した。")
    out.printw()  # :689–692
    out.drawline()
    out.printl("暗い部屋に卑猥な水音と嬌声が響いている・・・")
    out.printw()
    c = tc(ctx)
    if is_male(data, c) or t(ctx, c, "貧乳") > 0:  # :694–700
        out.printl(f"{me}は{tn}の胸に触手を這わせ、その先端を強く引っ張るように愛撫した。")
        out.printl(f"柔らかな胸突起への触手の力加減を変わるたびに、{tn}はびくびくと背を反らしている。")
    else:
        out.printl(f"{me}は{tn}の胸に触手を巻き付かせ、締め上げるように愛撫した。")
        out.printl("柔らかな双丘は触手の力加減を変えるたびに、ぐにぐにと形を変えている。")
    out.printl("通常ならば痛みを感じるはずのその行為も、触手が分泌する粘液の効果によりにより快感へと変わっているようで、")
    out.printl(f"{tn}は甘い喘ぎ声を上げながら身をよじっている。")
    out.printl()
    out.printl(f"{me}の触手はぬちゃりと大きく口を開くと、")  # :705–708
    out.printl("ピンと尖った乳首に吸い付き、じゅるじゅると大きな音を立てながら執拗に攻め立てる。")
    out.printl(f"やがて限界に達した{tn}は、一際大きな嬌声と共に全身を大きく震わせた。")
    out.printl()
    out.printl(f"脳を揺さぶられるかのような快楽に{tn}はぐったりと項垂れるも、{me}の渇きはまだ収まらず、")  # :710–711
    out.printl(f"{me}の触手による攻めは、{tn}が気を失うまで続いた・・・")
    synbiosis_abl_up(ctx, 1)  # :713


def _relation_text(ctx: Ctx, rel: int, other: int) -> str:
    """`@PRINT_CHARA_LIST` :790–933 の LOCALS（GETBIT は RELATION:(FLAG:799):(対象)）。"""
    st, data = ctx.state, ctx.data
    g = lambda bit: (rel >> bit) & 1 == 1  # noqa: E731
    male = is_male(data, st.charas[other])
    blood = g(OYAKO) or g(KYOUDAI) or g(SOFUBO) or g(OJIOBA) or g(OIMEI) or g(ITOKO)
    bond = g(YUUJIN) or g(KATAOMOI) or g(KOIBITO) or g(KONYAKU) or g(HAIGUUSHA)
    master = g(SHUJIN) or g(JUUSHA) or g(DOREI)
    s = ""
    if not (blood or bond or master):  # :794–807
        if g(SOEN) and g(SHITASHII):
            s += "微妙な距離感の知人"
        elif g(SHITASHII):
            s += "親しい間柄"
        elif g(SOEN):
            s += "顔見知り"
        elif g(AISURU) and g(ZOUO):
            s += "複雑な関係"
        elif g(AISURU):
            s += "大事な人"
        elif g(ZOUO):
            s += "仇敵"
        return s
    if g(IKIWAKARE):  # :809–810
        s += "生き別れの"
    if g(SOEN) and g(SHITASHII):  # :811–817
        s += "微妙な距離感の"
    elif g(SHITASHII) and not g(YUUJIN):
        s += "親しい"
    elif g(SOEN):
        s += "疎遠な"
    if g(AISURU) and g(ZOUO):  # :818–824
        s += "愛憎渦巻く"
    elif g(AISURU):
        s += "愛する"
    elif g(ZOUO):
        s += "憎悪する"
    if blood:  # :825–832
        s += "("
        s += "義理の" if g(GIRI) else "実の"
    # :834／:851／:868 の TOSHIUE_F の第 1 引数は TARGET（実行者 FLAG:799 ではない：原作どおり）
    older = toshiue(st, st.target, other)
    if g(OYAKO):  # :833–849
        if older > 0:
            s += "息子" if male else "娘"
        else:
            s += "父親" if male else "母親"
        if g(KYOUDAI) or g(SOFUBO) or g(OJIOBA) or g(OIMEI) or g(ITOKO):
            s += "/"
    if g(KYOUDAI):  # :850–866
        if older:
            s += "弟" if male else "妹"
        else:
            s += "兄" if male else "姉"
        if g(SOFUBO) or g(OJIOBA) or g(OIMEI) or g(ITOKO):
            s += "/"
    if g(SOFUBO):  # :867–879
        if older:
            s += "孫"
        else:
            s += "祖父" if male else "祖母"
        if g(OJIOBA) or g(OIMEI) or g(ITOKO):
            s += "/"
    if g(OJIOBA):  # :880–888
        s += "おじ" if male else "おば"
        if g(ITOKO):
            s += "/"
    if g(OIMEI):  # :889–897
        s += "甥" if male else "姪"
        if g(ITOKO):
            s += "/"
    if g(ITOKO):  # :898–900
        s += "いとこ"
    if blood and bond:  # :901–902
        s += "かつ"
    if g(YUUJIN):  # :903–909
        s += "親友" if g(SHITASHII) else "友人"
    if g(KATAOMOI):  # :910–915
        s += "片思いの相手"
    if g(KOIBITO):
        s += "恋人"
    if g(KONYAKU):
        s += "婚約者"
    if g(HAIGUUSHA):  # :916–922
        s += "夫" if male else "妻"
    if (blood or bond) and master:  # :923–924
        s += "かつ"
    if g(SHUJIN):  # :925–930
        s += "主人"
    if g(JUUSHA):
        s += "従者"
    if g(DOREI):
        s += "奴隷"
    # :931–932 閉じ括弧の条件に いとこ が含まれない（いとこだけなら "(" が閉じない：原作どおり）
    if g(OYAKO) or g(KYOUDAI) or g(SOFUBO) or g(OJIOBA) or g(OIMEI):
        s += ")"
    return s


def print_chara_list(ctx: Ctx, targets: list[int]) -> None:
    """`@PRINT_CHARA_LIST(TARGET_COUNT, TARGET_LIST)`:767–948（表示のみ）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    if st.flag[999] == 1:  # :778–787 デバッグ
        out.set_color((105, 105, 105))
        out.printl(f"- PRINT_CHARA_LIST - TARGETCOUNT:{len(targets)}")
        for i in targets:
            out.printl(f"対象　{st.charas[i].callname}, キャラ番号:{i}")
        out.reset_color()
    me = st.charas[st.flag[799]]
    for i in targets:
        o = st.charas[i]
        s = _relation_text(ctx, me.relation[i], i)
        out.print(f"[{i}] ")  # :936（末尾の空白も引数）
        if charatalent(data, o, 0, "オトコ") > 0:  # :937–943
            out.print("(♂)")
        elif charatalent(data, o, 0, "ふたなり") > 0:
            out.print("(双)")
        else:
            out.print("(♀)")
        # :944 `PRINTFORM  %CALLNAME…%`：命令の後の 1 文字（空白）の次から引数なので先頭に空白 1 つ
        out.print(f" {format_percent(o.callname, 24, True)}　{format_percent(s, 24, True)}")
        out.printl()  # :945
    out.printl("[999]夜這いは行わない")  # :948


# --- @SYNBIOSIS_ABL_UP（:955–1096）--------------------------------------------------------------


def synbiosis_abl_up(ctx: Ctx, arg: int) -> None:
    """`@SYNBIOSIS_ABL_UP, ARG`:955–1096（ARG は本体で使われない：0 自分、1 夜這い、2 暴走）。"""
    L = _sense_locals(ctx)
    _virgin_and_rest(ctx, L)
    ctx.out.printw()  # :1082
    _prison_tail(ctx, L)
