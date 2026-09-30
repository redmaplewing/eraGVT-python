"""妊娠の進行と出産：`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB` の `@BIRTH_HANTEI`:277–410、`@BIRTH_TENTACLES`:416–458、
`@ABL_UP_BIRTH`:463–574、`@BIRTH_AUTO_RANDOM` の苗床出産（:671–746）。

路徑相對 `source/earGVP/ERB/`。受精（NINSIN_HANTEI 等）は `eragvt.game.battle.ninsin`、娘の出産・子供の加入は
`eragvt.game.child`。狀態機と CFLAG 對照：`docs/wiki/era/pregnancy.md`。

Emuera 語意：
- `FOR CCOUNT, 0, CHARANUM` の終端は FOR 開始時に 1 回だけ評価（reference/emuera-1824/Emuera/GameProc/Function/
  Instraction.Child.cs@FOR_NEXT_Instruction:1731–1743）。BIRTH_HANTEI は TARGET = CCOUNT を index として使うので、
  途中の SET_PARTYMEMBER（SHIFTBACK_CHARA による並べ替え）の後は同じ index の別キャラを処理し続ける（原作どおり）。
- `&&`／`||` は短絡評価（GameData/Expression/OperatorMethod.cs:524–555）。
- `SQRT x` を命令として書くと結果は RESULT（式中関数の命令呼び出し：Instraction.Child.cs:390–409）。
- `TIMES` は decimal 乗算後の切り捨て（`era.times`）。
- 関数内 `#DIM`（LOSEDEF 等）は static（GameProc/UserDefinedVariable.cs:27、VariableData.cs@SetDefaultLocalValue:514–520）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state.constants import CharaState
from .action import Ctx, config_check_maniac, config_check_other, get_syuren, print_callname
from .battle.core import exp, run_chinobun, t, tc
from .battle.ninsin import num_child_tentacle, pregnancy_belly_expand
from .chara_common import is_female
from .era import div, isqrt, times
from .party import recover_to_party, set_partymember

InputGen = Generator[None, int, None]


def _set_t(ctx: Ctx, c, name: str, value: int) -> None:
    c.talent[ctx.data.index_of("TALENT", name)] = value


def _lactation(ctx: Ctx, c, wait: bool) -> None:
    """:305–311／:387–394：フィルタ（性嗜好 2 母乳体質）が有効で母乳体質でなければ母乳体質にする。"""
    st, out = ctx.state, ctx.out
    if t(ctx, c, "母乳体質") == 0 and config_check_maniac(st, 2) == 1:
        _set_t(ctx, c, "母乳体質", 1)
        out.printl(f"{print_callname(st, st.target, 1)}の胸が張ってきた…")
        out.printl()
        out.printl(f"{print_callname(st, st.target, 1)}は[{ctx.data.names['TALENT'].get(1, '')}]になった…")
        if wait:
            out.printw()


def _matanity(ctx: Ctx) -> None:
    """:288–293／:374–379：幽閉中でなく出産直前なら出産直前状態（CFLAG:0 = 10）へ。"""
    c = tc(ctx)
    c.cflag[0] = CharaState.BEFORE_BIRTH
    run_chinobun(ctx, "MESSAGE_MATANITY")  # 地の文/MESSAGE_NINSIN.ERB:56–67（本文のみ）
    set_partymember(ctx)
    ctx.out.drawline()


def birth_hantei(ctx: Ctx) -> InputGen:
    """`@BIRTH_HANTEI`:277–410：全キャラの妊娠日数（CFLAG:222、ターンごと）を進め、出産を判定する。

    ジェネレータ（出産時の INPUT：`eragvt.game.child`）。"""
    from .child import birth_daughter_human_origin, birth_daughter_tentacle_origin

    st, out = ctx.state, ctx.out
    saved = st.target  # :279
    n = st.charanum  # :280 FOR の終端は開始時に評価
    for cc in range(n):
        st.target = cc
        c = tc(ctx)
        if c.cflag[0] == CharaState.DEAD:  # :282–283
            continue
        p = t(ctx, c, "妊娠")
        if p in (1, 3):  # :286–326 触手に孕まされている
            if c.cflag[0] == CharaState.SAFE and (c.cflag[222] > 9 or (t(ctx, c, "苗床化") > 0 and c.cflag[222] > 3)):
                _matanity(ctx)
            c = tc(ctx)  # SET_PARTYMEMBER の並べ替え後も TARGET（= index）のキャラを読む
            c.cflag[222] += 3 if t(ctx, c, "苗床化") > 0 else 1  # :295–299
            if c.cflag[0] == CharaState.IMPRISONED:  # :301–302
                c.cflag[222] += 2
            if c.cflag[222] > 10:  # :304–326
                _lactation(ctx, c, wait=False)
                l1 = 0 if c.cflag[222] >= 30 else st.rng.rand(30 - c.cflag[222])  # :313–317
                # :318（短絡：RAND:2 は前の条件がすべて偽のときだけ）
                if (
                    (l1 == 0 and c.cflag[222] >= 10)
                    or c.cflag[222] >= 15
                    or (c.cflag[0] == CharaState.IMPRISONED and t(ctx, c, "苗床化") > 0 and st.rng.rand(2) == 0)
                ):
                    if t(ctx, c, "妊娠") == 3 and config_check_other(st, 0) > 0:  # :320–324
                        yield from birth_daughter_tentacle_origin(ctx)
                    else:
                        birth_tentacles(ctx)
        elif p == 4:  # :329–370 ヒト相手の正常妊娠（無自覚）
            c.cflag[222] += 3 if t(ctx, c, "苗床化") > 0 else 1
            name = print_callname(st, st.target, 1)
            if c.cflag[222] >= 20:
                out.printl(f"{name}の腹部が明らかに膨らんできている…")
                out.printl("もう妊娠していることは誰の目にも明らかだ…")
                if is_female(ctx.data, c) and t(ctx, c, "変身時ＴＳ") > 0 and c.cflag[1] == 0:
                    out.printw()
                    out.printl(f"{print_callname(st, st.target)}は妊娠している間は変身できなくなります")
                out.printw()
                _set_t(ctx, c, "妊娠", 5)
            elif c.cflag[222] == 12:
                out.printl(f"{name}の腹部が膨らんできたような気がする…")
                if c.cflag[21] > 0:
                    out.printl(f"幽閉された身で検査を受けられるはずもなく、{name}はただ不安げに腹部を眺めている…")
                else:
                    out.printl("今まで先延ばしにしてきたが、ちゃんと検査をしておいた方が良いだろう…")
                out.printw()
            elif c.cflag[222] == 9:
                out.printl(f"{name}の様子がおかしい…")
                out.printl("時折強い吐き気を感じているようだ…")
                out.printw()
            elif c.cflag[222] == 6:
                out.printl(f"{name}の様子がおかしい…")
                if st.rng.rand(2) == 0:
                    out.printl("前回から随分と生理が遅れているようだ…")
                else:
                    out.printl("何やら軽い吐き気のようなものを感じているようだ…")
                if c.cflag[21] > 0:
                    out.printl("もしも無事な身であれば、医務室で然るべき検査を受けられたのだろうが…")
                else:
                    out.printl("心当たりがあるなら、医務室で検査してみた方が良いかもしれない…")
                out.printw()
        elif p == 5:  # :372–404 妊娠自覚済み
            if c.cflag[0] == CharaState.SAFE and c.cflag[222] > 42:
                _matanity(ctx)
            c = tc(ctx)
            c.cflag[222] += 3 if t(ctx, c, "苗床化") > 0 else 1
            if c.cflag[222] >= 16:
                _lactation(ctx, c, wait=True)
            l1 = 0 if c.cflag[222] >= 83 else st.rng.rand(83 - c.cflag[222])  # :398–402
            if (l1 == 0 and c.cflag[222] >= 53) or c.cflag[222] >= 56:
                yield from birth_daughter_human_origin(ctx)
    st.target = saved  # :410


def birth_tentacles(ctx: Ctx) -> None:
    """`@BIRTH_TENTACLES`:416–458：孕まされた触手を産む。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    c.cflag[99] += 45 + div(pregnancy_belly_expand(ctx, st.target), 20)  # :418
    if c.cflag[0] == CharaState.BEFORE_BIRTH:  # :420–421
        recover_to_party(ctx, st.target)
    n = c.cflag[227]  # :423
    if c.cflag[21] != 0:  # :424–439 幽閉中
        # :426–435（短絡：CONFIG_CHECK_MANIAC_F(4)〔異形出産〕が有効なときだけ RAND を引く）
        if config_check_maniac(st, 4) == 1 and (
            st.rng.rand(4) == 0 or (config_check_other(st, 0) > 0 and st.rng.rand(4) != 0)
        ):
            run_chinobun(ctx, "MESSAGE_BIRTH_AINOKO_PRISON", (n,))
        else:
            run_chinobun(ctx, "MESSAGE_BIRTH_TENTACLES_PRISON", (n,))
        c.cflag[223] = 1
        c.cflag[220] += n
        st.flag[44] += n
    else:  # :440–446 組織にいる
        run_chinobun(ctx, "MESSAGE_BIRTH_TENTACLES", (n,))
        out.printl()
        st.flag[200] += n
        out.printl(f"触手の欠片＋{n}")
    abl_up_birth(ctx, n)  # :448
    from .battle.ablup import ablup

    ablup(ctx, 1)  # :449
    for k in (221, 222, 227, 228, 232, 233):  # :452–458
        c.cflag[k] = 0
    _set_t(ctx, c, "妊娠", 0)


# ABL_UP_BIRTH の TIMES 係数（:473–514）
_JUUJUN = ("0.20", "0.50", "0.70", "1.00", "1.50")  # 5 以上 2.00
_SHOKUSHU = ("1.00", "1.10", "1.30", "1.50", "2.00")  # 5 以上 2.50


def abl_up_birth(ctx: Ctx, arg: int) -> None:
    """`@ABL_UP_BIRTH, ARG`:463–574：出産による体力気力の減少・珠・経験・拡張度。ARG = 産んだ数（出産経験）。"""
    from .battle.gaping import gaping_size_to_point, v_gaping
    from .prison.commands import common_prison_exp

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    local: dict[int, int] = {}  # :465 VARSET LOCAL
    c.base[0] = max(div(c.base[0], 2) - 500, 1)  # :468
    c.base[1] = max(div(c.base[0], 2) - 500, 1)  # :469（右辺は BASE:体力：原作どおり）
    lv = 100  # :471 LOCAL
    j = a("従順")
    lv = times(lv, _JUUJUN[j] if 0 <= j <= 4 else "2.00")  # :474–486（負値は ELSE）
    s = a("触手中毒")
    lv = times(lv, _SHOKUSHU[s] if 0 <= s <= 4 else "2.50")  # :489–501
    b = exp(ctx, c, "出産経験")
    if b < 1:  # :504–514
        lv = times(lv, "0.50")
    elif b < 10:
        lv = times(lv, "0.70")
    elif b < 30:
        lv = times(lv, "1.00")
    elif b < 50:
        lv = times(lv, "2.00")
    else:
        lv = times(lv, "4.00")
    get_syuren(ctx, div(lv, 10))  # :516
    if c.cflag[0] == CharaState.BEFORE_BIRTH:  # :518–519
        lv = times(lv, "3.00")
    tv = lambda n: 1 if t(ctx, c, n) > 0 else 0  # noqa: E731
    # :521–522（左結合：((a*10)*LOCAL)*(…) / (…)）
    l1 = div((a("Ｖ感覚") + 1) * 10 * lv * (1 + tv("Ｖ敏感") + tv("淫壷")), 1 + tv("Ｖ鈍感"))
    l3 = div((a("噴乳中毒") + 1) * (a("Ｂ感覚") + 1) * 10 * lv * (1 + tv("Ｂ敏感") + tv("淫乳")), 1 + tv("Ｂ鈍感"))
    J = lambda n: data.index_of("PALAM", n)  # noqa: E731  JUEL の名前は Palam.csv
    c.juel[J("快Ｖ")] = l1  # :523–524（代入：原作どおり）
    c.juel[J("快Ｂ")] = l3
    c.juel[J("恭順")] += (a("従順") + 1) * 100 * lv
    c.juel[J("欲情")] += (a("欲望") + 1) * 25 * lv
    c.juel[J("屈服")] += (a("従順") + 1) * 250 * lv
    c.juel[J("恥情")] += (a("露出癖") + 1) * 25 * lv
    r = isqrt(exp(ctx, c, "Ｖ拡張経験") + 1)  # :529
    c.juel[J("苦痛")] += div((a("マゾっ気") + 1) * 300 * lv, r)
    r = isqrt(b + 1)  # :531
    c.juel[J("恐怖")] += div(100 * lv, r)
    local[120] = div(lv, 10)  # :534 Ｖ経験
    local[122] = div(l1 + l3, 1000)  # :536 絶頂経験
    local[132] = div(lv, 50)  # :538 苦痛快楽経験
    if t(ctx, c, "母乳体質") == 1:  # :540–541 噴乳経験
        local[154] = div(div(l3, 6 - a("噴乳中毒")), 1000)
    local[151] = 1  # :543 Ｖ拡張経験
    if b == 0:  # :547–556 初めての出産
        local[150] = local.get(150, 0) + 1
        c.cflag[204] = 1
        c.maxbase[0] += div(c.maxbase[0], 4)
        c.maxbase[1] += div(c.maxbase[1], 4)
        c.base[50] += div(c.base[50], 4)
        c.base[51] += div(c.base[51], 4)
        out.printl(f"出産の苦痛に耐えた{print_callname(st, st.target)}は体力と気力が増加しました")
        out.printl()
    local[157] = arg  # :558 出産経験
    for lc in range(100, 200):  # :561–563
        common_prison_exp(ctx, lc, local.get(lc, 0))
    # :566–573 拡張度（成長曲線 CFLAG:34 が設定済み、かつ極端な拡張を抑制していない）
    if c.cflag[34] > 0 and config_check_maniac(st, 17) == 1:
        st.temp.tentacle_size[(1, data.index_of("PALAM", "快Ｖ"))] = div(pregnancy_belly_expand(ctx, st.target), 2)
        r = v_gaping(ctx, gaping_size_to_point(ctx, "Ｖ"), st.target)
        if r > 0 and config_check_maniac(st, 16) == 1:
            out.printl(f"　膣径：＋{div(r, 10)}.{r % 10} cm\t")
            out.printl()
    out.printl()  # :574


# --- BIRTH_AUTO_RANDOM の苗床出産（:671–746）----------------------------------------------------

_LOSEDEF = ("BIRTH_AUTO_RANDOM:LOSEDEF", 0)  # #DIM LOSEDEF,1（static・VARSET LOCAL の対象外）

_NAE_SUBJ = (
    "触手に吸収されてしまった{n}",
    "凄惨な出産専用便器へと改造された{n}",
    "意識の無い触手を産む装置と化した{n}",
    "絶望の中で触手に吸収された{n}",
    "触手に支配されて出産母畜と化した{n}",
    "意識を切断されて豚人間となった{n}",
    "触手によって完全に壊造された{n}",
    "かつて勇敢に触手と戦っていた{n}",
    "かつて人類の希望だった{n}",
)
_NAE_STATE = (
    "が、巨大なボテ腹を触手に好き放題突き上げられている。",
    "が、手足のない体をピクピクと震わせている。",
    "が、肉塊のような胴体だけを無様に震わせている。",
    "は、既に蜜壷もアナルも尿道も苗床と化して蠢いている。",
    "が、触手の動きに合わせて不釣り合いに大きな乳房を揺らしている。",
    "。肉壁の外に露出しているのは巨大な乳房とボテ腹だけだった。",
    "は、既に「人」と呼ばれる資格を失っていた。",
    "の、光沢のある腹部に異形の稜線が膨らんでいた。",
    "は、へそまで種付けされて穴という穴を繁殖袋にされていた。",
    "は手足と意識を奪われたが、死ぬことはできなかった。",
)
_NAE_HOW = (
    "産道をこじ開けられて痙攣しながら",
    "高濃度の媚薬羊水を大量に排出し、同時に",
    "開ききった股間から白濁羊水を噴き出しながら",
    "声も上げず、ただ醜い汁を噴き出すと同時に",
    "敗北の証として醜く乳を噴き出しながら",
    "お腹の中で音がして粘液がべちゃりと出てくると同時に、",
    "勢いよく噴き出した尿で黄色い弧を描きながら、",
    "触手精液と何ら変わらない母乳を噴き散らしながら、",
    "出産アクメと共に",
    "媚薬羊水と共に",
    "白濁羊水を噴きながら",
    "無様な潮吹きと共に",
    "敗北噴乳をキメながら",
)
_NAE_END = (
    "絶え間ない受精と出産は、今や{n}の身体に許された唯一の悦びだった……",
    "触手愛用の苗床便器{n}が、今日も終わりなき出産地獄に堕ちていく……",
    "意識を失った身体は快楽のみを感じ、{n}はもはや完全に肉人形だ……",
    "かつて強力な魔法少女だった{n}も、今となっては触手の一器官に過ぎない……",
)


def nae_birth(ctx: Ctx, who: int, drawn: bool) -> int:
    """`@BIRTH_AUTO_RANDOM`:675–741 の 1 キャラ分（苗床化＋取り込まれ〔CFLAG:0 == 9〕、RAND:4 == 0 のとき）。
    戻り値 = 産んだ子触手の数（呼び出し側が LOCAL:1 に加算）。

    原作どおり：NUM_CHILD_TENTACLE は TARGET の出産経験等を読む（`battle.ninsin.num_child_tentacle`）、
    :729–732 の `TALENT:母乳体質`／`TALENT:膨乳改造値` はキャラ指定なし＝ **TARGET** に代入、
    LOSEDEF は static で呼び出しをまたいで累積し、毎回その累積値を防衛力から引く。
    """
    st, out = ctx.state, ctx.out
    pick = lambda xs: xs[st.rng.rand(len(xs))]  # noqa: E731  PRINTDATA（Instraction.Child.cs@PRINT_DATA_Instruction:152–）
    name = st.charas[who].callname
    if not drawn:  # :676–679
        out.drawline()
    result = num_child_tentacle(ctx)  # :680
    out.printl("【苗床出産】")
    out.print(pick(_NAE_SUBJ).format(n=name))  # :682–692 PRINTDATA
    out.printl(pick(_NAE_STATE))  # :693–704 PRINTDATAL
    out.print(pick(_NAE_HOW))  # :705–719 PRINTDATA
    out.printw(f"{result}匹の子触手を産み落としている{name}。")  # :720
    out.printl()  # :721
    out.print(pick(_NAE_END).format(n=name))  # :722–727 PRINTDATA
    tgt = st.target_chara
    if config_check_maniac(st, 2) == 1:  # :729–730
        _set_t(ctx, tgt, "母乳体質", 1)
    if config_check_maniac(st, 19) == 1:  # :731–732
        tgt.talent[ctx.data.index_of("TALENT", "膨乳改造値")] += 10
    losedef = st.temp.locals.get(_LOSEDEF, 0) + result * (st.rng.rand(2) + 2)  # :734 RAND(2,4)（Creator.Method.cs:953–973）
    st.temp.locals[_LOSEDEF] = losedef
    out.printl()  # :736 PRINTFORML（空）
    st.flag[852] -= losedef  # :737
    out.printl(f"{name}が産み落とす子触手たちは、いずれ次の犠牲者を苗床に堕としてしまうのだろう……")
    out.printl(f"防衛力が{losedef}低下した！")
    out.drawline()
    return result

