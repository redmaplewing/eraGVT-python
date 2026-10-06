"""戦闘後レイプ（クズ市民）：`ゲーム内_イベント発生/戦闘イベント.ERB@AFTER_TRAIN_RAPE`:962–1334 と
`ゲーム内_イベント発生/CALC_GANGBANG.ERB@CALC_GANGBANG`:3–166（路徑相對 `source/earGVP/ERB/`）。

呼び出し元は `BATTLE_TRAIN_AFTER.ERB@EVENTEND`:498–504（`after.event_end`）。戻り値 1（:1334、襲われた場合は必ず 1）は
そのまま `DOUGA_RYUSUTU, 1`（レイプ動画流出）に渡る。CALC_GANGBANG は AFTER_PILL（INPUT）を呼ぶのでジェネレータ。

引擎語意：
- LOCAL は関数ごとに静的で、`VARSET LOCAL` しない限り前回の値が残る（`reference/emuera-1824/Emuera/GameData/Variable/
  VariableToken.cs`:1712–1737；ResetData／読込でのみ 0：`VariableData.cs@SetDefaultLocalValue`:514–520）。
  AFTER_TRAIN_RAPE は :966 `VARSET LOCAL` するが、CALC_GANGBANG はしない → 条件付きでしか代入されない LOCAL
  （:11 快Ｖ、:20 苦痛、:120 Ｖ経験、:113 輪姦、:142 誘拐監禁、:150 異常、:151／152 拡張）は前回呼び出しの値が残る
  （原作どおり、`st.temp.locals` に保持）。
- `&&`／`||` は短絡（`GameData/Expression/OperatorMethod.cs`:532–536）、`IF … ELSEIF RAND:n` の RAND は前の条件が偽のとき
  だけ評価される。キャラ変数の添字省略は TARGET（`GameData/Variable/VariableParser.cs`:91–134）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..action import Ctx, print_transcallname
from ..chara_common import is_male
from ..era import div, times
from .core import abl, get_battle_situation, is_hole, is_penis, percent_cal, t, tc

InputGen = Generator[None, int, int]

# DIM.ERH:257 `#DIM CONST 望まない相手 = -4`
NOZOMANAI_AITE = -4

_GB = "CALC_GANGBANG"


def _gb_get(ctx: Ctx, i: int) -> int:
    return ctx.state.temp.locals.get((_GB, i), 0)


def _gb_set(ctx: Ctx, i: int, v: int) -> None:
    ctx.state.temp.locals[(_GB, i)] = v


def calc_gangbang(ctx: Ctx, situation: str, sao: int, nakadashi: int) -> InputGen:
    """`@CALC_GANGBANG(シチュエーション, 竿の数, NAKADASHI)`:3–166。LOCAL は静的（モジュール docstring）。"""
    from ..prison.commands import common_prison, common_prison_exp
    from .ablup import ablup
    from .ninsin import after_pill, ninsin_hantei
    from .sexcom import check_holyvirgin

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    male = lambda: is_male(data, c)  # noqa: E731
    exp = lambda n: data.index_of("EXP", n)  # noqa: E731
    shojo = data.index_of("TALENT", "処女")
    # :16 V挿入ブロッカー（三項演算子：ISMALE() が真なら CHECK_HOLYVIRGIN_F は評価しない）
    if male() or check_holyvirgin(ctx) == 1:
        nakadashi = 0
    if nakadashi:  # :20–54
        v = abl(ctx, c, "Ｖ感覚")
        _gb_set(ctx, 11, {0: 10, 1: 20, 2: 40, 3: 100, 4: 200}.get(v, 400))  # ELSE（負の値も）400
        _gb_set(ctx, 120, 10 + st.rng.rand(30))  # :36
        if c.talent[shojo] == 1:  # :38–46
            c.talent[shojo] = -1
            c.cflag[206] = 11
            _gb_set(ctx, 20, 500)
        else:
            _gb_set(ctx, 11, _gb_get(ctx, 11) * 3)
        if c.cflag[35] <= 40:  # :49–52
            c.cflag[35] += 10
            _gb_set(ctx, 151, 2)
    a = abl(ctx, c, "Ａ感覚")  # :57–69
    _gb_set(ctx, 12, {0: 6, 1: 50, 2: 200, 3: 600, 4: 900}.get(a, 1200))
    # :71 `40 - LOCAL:120 + RAND:5 - RAND:5`（左から評価）
    l121 = 40 - _gb_get(ctx, 120) + st.rng.rand(5)
    l121 -= st.rng.rand(5)
    if male():  # :72–73
        l121 = times(l121, "1.50")
    _gb_set(ctx, 121, l121)
    if c.cflag[36] <= 40:  # :75–78
        c.cflag[36] += 10
        _gb_set(ctx, 152, 2)
    _gb_set(ctx, 123, 15 + st.rng.rand(16))  # :81
    _gb_set(ctx, 124, 12 + st.rng.rand(5))  # :83
    _gb_set(ctx, 16, 100)  # :86–88
    _gb_set(ctx, 18, 500)
    _gb_set(ctx, 21, 500)
    if situation in ("監禁", "生オナホ"):  # :91–106
        c.cflag[70] += 1
        _gb_set(ctx, 142, 1)
    elif situation == "ナンパ":
        if c.cflag[1] > 1 and t(ctx, c, "変身時ＴＳ") > 0:
            c.cflag[321] += 1
        else:
            c.cflag[320] += 1
    else:
        c.cflag[286] += 1
    if male() or c.exp[exp("異常経験")] < 3:  # :111–112
        _gb_set(ctx, 150, 1)
    _gb_set(ctx, 132, 2 + st.rng.rand(3))  # :116
    if sao > 1:  # :118–119
        _gb_set(ctx, 113, 1)
    # :124 COMMON_PRISON, LOCAL:10〜LOCAL:21, 1（結界が反応しない）
    common_prison(ctx, [_gb_get(ctx, i) for i in range(10, 22)], 1)
    for cc in range(100, 200):  # :126–128（FOR の終値は開始時に 1 回評価）
        common_prison_exp(ctx, cc, _gb_get(ctx, cc))
    out.printl()  # :129
    ablup(ctx, 1)  # :131
    if nakadashi > 0 and c.talent[shojo] < 1:  # :135–142
        if nakadashi == 1 and situation != "生オナホ":
            yield from after_pill(ctx, st.target, 20, NOZOMANAI_AITE)
        if situation != "生オナホ":
            yield from ninsin_hantei(ctx, _gb_get(ctx, 123), 100, NOZOMANAI_AITE)
    if situation == "脅迫":  # :145–159
        if t(ctx, c, "淫乱") or abl(ctx, c, "欲望") >= 3 or abl(ctx, c, "マゾっ気") >= 3:
            c.cflag[99] = 10
            c.base[0] = div(c.base[0] * 20, 100)
            c.base[1] = div(c.base[1] * 20, 100)
            c.base[2] = 0
        else:
            c.cflag[15] = 3
            c.base[0] = 0
            c.base[1] = 0
            c.base[2] = 0
            c.cflag[99] = 50
    if st.rng.rand(100) < 30:  # :162–163 悪い噂
        c.cflag[825] += 1
    out.printl()  # :165–166
    out.printl()
    return 0


_KANOJO = ((8, "妻"), (7, "母さん"), (6, "娘"), (5, "彼女"), (4, "幼馴染"), (3, "姉"), (2, "妹"))


def after_train_rape(ctx: Ctx, arg: int) -> InputGen:
    """`@AFTER_TRAIN_RAPE, ARG`:962–1334。戻り値 0（襲われない）／1（レイプされた）。ARG は本体で未使用。"""
    from .sexcom import check_holyvirgin

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    ex = lambda n: c.exp[data.index_of("EXP", n)]  # noqa: E731
    ab = lambda n: abl(ctx, c, n)  # noqa: E731
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    male = lambda: is_male(data, c)  # noqa: E731
    holy = lambda: check_holyvirgin(ctx) == 1  # noqa: E731
    nakadashi = 0  # :967（#DIM は静的だが毎回 0 を代入）
    if c.cflag[0] != 0:  # :970–971
        return 0
    if not is_hole(ctx):  # :973–974（ISHOLE()：ARG 省略 = -1 → TARGET）
        return 0
    # :977–980（:966 VARSET LOCAL → 以降 LOCAL は :977 の確率値。:1139／:1184 で 1、:1232 で 0 になるだけ）
    local = min(div(5000 - st.flag[852], 100), 50) + min(c.cflag[285] * 2, 50) + (tl("嬲られ体質") > 0) * 10
    if st.flag[72] == 0:
        local = div(local, 2)
    if get_battle_situation(st, "レイプ確定") == 0 and st.rng.rand(100) >= local:  # :982–983
        return 0
    out.drawline()  # :986–990
    out.printl("――")
    out.printl("――――")
    out.printw("――――――")
    out.printl()
    # :992 分母の最後は MAXBASE ではなく BASE:性耐性 * 10（原作どおり）
    l1 = percent_cal(c.base[0] + c.base[1] + c.base[2] * 10, c.maxbase[0] + c.maxbase[1] + c.base[2] * 10)
    out.printl()
    name = print_transcallname(st, st.target)
    if get_battle_situation(st, "レイプ確定") == 0 and st.rng.rand(100) < (  # :995–1006
        div(l1 * 3, 4) + (st.tflag[98] == 1) * 6 - (st.time == 1) * 12 - (tl("嬲られ体質") > 0) * 12
    ):
        out.printl(f"{name}は誰かに尾けられているような気がしたが、")
        if local < 25 or st.rng.rand(2) == 0:
            out.printl("どうやら気のせいだったようだ・・・")
        else:
            out.printl("うまく撒くことができたようだ・・・")
        out.printw()
        return 0
    elif st.tflag[98] == 0:  # :1007–1014
        if l1 < 25:
            out.printl(f"ギリギリのところで戦闘から逃げ伸びた{name}。")
        elif l1 < 50:
            out.printl(f"不利を悟って何とか撤退した{name}。")
        else:
            out.printl(f"戦闘から離脱することに成功した{name}。")
    else:  # :1015–1022
        if l1 < 25:
            out.printl(f"ギリギリのところで戦闘に勝利した{name}。")
        elif l1 < 50:
            out.printl(f"何とか戦闘に勝利することができた{name}。")
        else:
            out.printl(f"大して苦戦することもなく勝利した{name}。")
    out.printl("緊張の糸が切れて油断したところを狙われたのか、突然現れた男たちに囲まれて")  # :1024–1026
    out.printl("人通りのない路地裏に連れ込まれてしまった！")
    out.printw()
    _rape_intro(ctx, l1)  # :1028–1079
    # :1082–1109 男が女物の下着を付けている（`CFLAG:42 != 300 || … != 397` は常に真：ISMALE() のみが条件）
    if male():
        _male_underwear(ctx)
    # :1111–1193
    if c.cflag[286] == 0 or st.rng.rand(2) == 0:
        out.printl(f"両手でそれぞれペニスを握り、口にもペニスを咥える{name}。")
        out.printl("手コキとフェラチオで限界に達した男たちが射精に至るが、正気に戻る様子はない。")
        out.printl("するといきなり男たちに押し倒されて、手足を抑えつけられてしまう。")
        out.printw()
        if tl("淫乱"):  # :1116–1120
            out.printl(f"驚きの声を上げる{name}の唇を奪い、")
        else:
            out.printl(f"制止しようとする{name}の説得も空しく、")
        out.print("男が")  # :1121
        if male():  # :1122–1135
            _anal_first(ctx, name)
        elif holy():  # :1136–1152
            if tl("貧乳") < 1 and st.rng.rand(2) == 0:
                out.printl("胸でペニスを挟ませ、パイズリさせ始めた。")
                local = 1
            else:
                _anal_first(ctx, name)
        elif tl("処女") > 0:  # :1153–1160
            out.printl("ペニスを何度か擦り付けると、ゆっくりと腰を埋めていく。")
            out.print("破瓜の痛みと共にまだ男を知らないヴァギナが貫かれ")
            if tl("淫乱") or ab("欲望") >= 3:
                out.printl("ていく。")
            else:
                out.print("、")
        else:  # :1161–1162
            out.printl("ペニスをヴァギナに深々と挿入して、ゆっくり腰を使い始めた。")
        if tl("淫乱") == 0 and ab("欲望") < 3:  # :1164–1165
            out.printl(f"{name}の悲鳴が路地に響き渡る・・・")
    else:  # :1167–1193 二度目以降
        out.printl(f"すると男はそのまま{name}を押し倒し、")
        if ex("陥落経験") > 0:  # :1169–1171
            out.printl(f"何度も謝罪の言葉を口にする{name}を平手打ちで黙らせ、")
        if male():  # :1172–1180
            if ex("Ａ経験") < 5 or c.cflag[36] <= 40:
                out.printl("ペニスでまだ犯され慣れてないアナルに捻り込んで、")
                out.printl(f"悲鳴を上げる{name}の声をＢＧＭに乱暴にピストンし始めた。")
            else:
                out.printl("アナルに挿入して乱暴にピストンし始めた。")
        elif holy():  # :1181–1187
            if tl("貧乳") < 1 and st.rng.rand(2) == 0:
                out.printl("胸でペニスを挟ませ、激しくピストンし始めた。")
                local = 1
            else:
                out.printl("悲鳴を上げる口をふさぐようにペニスをねじ込み、ピストンし始めた。")
        elif tl("処女") > 0:  # :1188–1189
            out.printl("まだ男を知らないヴァギナを貫いた。")
        else:
            out.printl("ヴァギナに挿入して乱暴にピストンし始めた。")
    if male():  # :1195–1199（同上：常に真の OR）
        out.printl("オンナモノの下着なんか着けてこうやって犯されるのが夢だったんだろ？と男が嘲笑う。")
    out.printw()  # :1200
    lewd = (tl("淫乱") or ab("欲望") >= 3 or ab("マゾっ気") >= 3) and tl("初心") < 1
    if tl("男の娘") > 0:  # :1201–1224
        if lewd:
            out.printl("乱暴にアナルを割り広げられる痛みに耐えながらも、")
            if tl("主観視点") > 0:
                out.printl(f"誰とも知らない男性に尻穴を奪われたという事実に{name}の体は興奮して")
                out.printl("すぐに快楽を感じ始めてしまう。")
            else:
                out.printl(f"誰とも知らない男性に尻穴を奪われたという事実に{name}は興奮して")
                out.printl("すぐに快楽を感じ始めてしまった。")
        elif ab("Ａ感覚") < 2:
            out.printl("乱暴にアナルを割り広げられる痛みに抵抗する気力を完全に奪われ、")
            out.printl(f"{name}は自分の身に起きた出来事を現実だと受け止めることすらできずに")
            out.printl("誰とも知らない男に腸管の純潔を押し開かれていく。")
        else:
            out.printl("乱暴にアナルを割り広げられているのに痛みは薄く、快感に声が抑えきれない。")
            out.printl("そんな自分自身にショックを受けて抵抗する気力は完全に奪われ、")
            out.printl(f"{name}は自分の身に起きた出来事を現実だと受け止めることすらできずに")
            out.printl("誰とも知らない男に潤んだ腸管を押し開かれていく。")
        out.printw()
        out.printl("身勝手なピストンで男が限界に登り詰めて直腸内に精液を放出すると、")
    elif male():  # :1225–1228
        out.printl("男が限界に登り詰めて直腸内に精液を放出すると、")
    elif holy():  # :1229–1235（LOCAL == 1：パイズリを選ばなくても確率値がちょうど 1 なら真：原作どおり）
        if local == 1:
            out.printl("男が限界に登り詰めて胸に精液をぶっかけると、")
            local = 0
        else:
            out.printl("男が口にねじ込んだまま喉に精液を放出すると、")
    elif tl("処女") > 0:  # :1236–1256
        out.set_bold(True)
        out.printl("処女喪失")
        out.set_bold(False)
        if lewd:
            out.printl("乱暴に処女膜を引き裂かれる痛みに耐えながらも、")
            if tl("主観視点") > 0:
                out.printl(f"誰とも知らない男性に処女を奪われたという事実に{name}の体は興奮して")
                out.printl("すぐに快楽を感じ始めてしまう。")
            else:
                out.printl(f"誰とも知らない男性に処女を奪われたという事実に{name}は興奮して")
                out.printl("すぐに快楽を感じ始めてしまった。")
        else:
            out.printl("乱暴に処女膜を引き裂かれる痛みに抵抗する気力を完全に奪われ、")
            out.printl(f"{name}は自分の身に起きた出来事を現実だと受け止めることすらできずに")
            out.printl("誰とも知らない男に膣肉の純潔を押し開かれていく。")
        out.printw()
        out.printl("身勝手なピストンで男が限界に登り詰めて膣内射精を決めると、")
        nakadashi = 1
    else:  # :1257–1259
        out.printl("男が限界に登り詰めて当然のように膣内射精を決めると、")
        nakadashi = 1
    if ab("射精中毒") > 1 and is_penis(ctx):  # :1262–1263
        out.printl(f"{name}の体も同時に絶頂を迎え、精子を虚空に無駄打ちし、")
    _rape_continue(ctx, name)  # :1264–1311
    out.printl("男たちの欲望をどれくらい受け止めたか分からなくなったころ、")  # :1313–1321
    out.printl(f"ようやく満足した彼らは{name}を地面に放り捨てた。")
    if c.cflag[286] > 0 or st.rng.rand(2) == 0:
        out.printl("「次も頼むわ」という言葉と共に、男たちは下卑た笑いだけ残して去っていった。")
    else:
        out.printl("男たちのうち一人がハンディカメラでレイプの一部始終を録画しており、")
        out.printl("誰かに言えばネットに動画を公開するとひと通り脅して立ち去って行った。")
    out.printw()
    out.printl(f"全身を白く染められた{name}は焦点も定まらず、")  # :1322–1328
    if lewd:
        out.printl("快楽の余韻に脳髄を蕩けさせている・・・")
    else:
        out.printl("守るべき人々に犯されたショックと疲労で動くことができなかった・・・")
    out.printw()
    yield from calc_gangbang(ctx, "戦闘後", 4, nakadashi)  # :1331
    return 1  # :1334（録画の有無にかかわらず 1 → DOUGA_RYUSUTU, 1）


def _rape_intro(ctx: Ctx, l1: int) -> None:
    """:1028–1079 初回／悪堕ち経験／その他。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    name = print_transcallname(st, st.target)
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    if c.cflag[286] == 0:  # :1028–1033
        out.printl("男たちは苦しそうに、「助けてくれ」「助けてくれ」と言いながらズボンを下ろし、")
        out.printl("勃起したペニスを露出させた。")
        out.printl(f"男たちが触手の淫気に中てられた可能性に思い当たった{name}は")
        out.printl("射精させれば正気に戻るはずだと覚悟を決めた・・・")
    elif st.rng.rand(3) == 0 and c.exp[data.index_of("EXP", "陥落経験")] > 0:  # :1034–1056
        out.print("男たちは苦々しげに、「お前のせいで")
        for n, word in _KANOJO:
            if st.rng.rand(n) == 0:
                out.print(word)
                break
        else:
            out.print("あの子")
        out.printl("が……」と言いながらズボンを下ろし、")
        out.printl("勃起したペニスを露出させた。")
        out.printl(f"自分のせいで男たちが大切な女性を失ったことを察した{name}は")
        out.printl("罪悪感と自己弁護の感情の波に飲まれ思うように抵抗できなかった・・・")
    else:  # :1057–1077
        out.printl("覆面で顔を隠した男たちに取り押さえられ、目の前に勃起したペニスが突き付けられる。")
        if tl("淫乱") and tl("初心") < 1:
            out.printl(f"{name}は誘惑するように、上目遣いで男に奉仕し始めた・・・")
        elif abl(ctx, c, "欲望") >= 3 and tl("初心") < 1:
            out.printl(f"{name}は心の中で言い訳をしながら、男のペニスに奉仕し始めた・・・")
        elif l1 < 25:
            out.printl(f"満身創痍の{name}には抵抗する力が残っておらず、")
            out.printl("碌に鍛錬もしていないであろう男たちを振り払うことができない・・・")
        elif abl(ctx, c, "従順") >= 3:
            out.printl(f"{ctx.data.str_defaults.get(2500, '')}との戦いで身体と心に服従を教え込まれている{name}は")
            out.printl("碌に鍛錬もしていないであろう男たちを振り払うことができない・・・")
        elif c.cflag[286] == 0 and tl("清純派") > 0:  # CFLAG:286 == 0 は :1028 で先に取られるので到達しない（原作どおり）
            out.printl("男たちは苦しそうに、「助けてくれ」「助けてくれ」と言いながらズボンを下ろし、")
            out.printl("勃起したペニスを露出させた。")
            out.printl(f"しかし男の性器を触った事もない{name}は躊躇って")
            out.printl("誰かと相談しようとスマートフォンを出した途端、男たちにスマホを奪われてきょとんしてしまった…")
        else:
            out.printl(f"逆らったら正体をバラすぞと脅され、{name}は")
            out.printl("簡単に振り払える相手に抵抗するのを躊躇してしまった・・・")
    out.printw()  # :1079


def _male_underwear(ctx: Ctx) -> None:
    """:1084–1107。SHITAGI_COLOR／KAIZOU_PANT（`PASTIME_改造制服.ERB`:134／359、表示のみ）は catalog。"""
    from .core import run_chinobun

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    name = print_transcallname(st, st.target)
    out.print(f"男が{name}の服を乱暴に剥ぐと")
    inner = c.cflag[42]
    if inner in (0, 398):  # :1086–1088
        out.print("隠すもののないお尻")
    elif inner in (307, 311, 400):  # :1089–1092
        if inner == 400:
            out.print("普通のパンツに擬態した")
        out.print(data.names["ITEM"].get(inner, ""))
    else:  # :1093–1097
        run_chinobun(ctx, "SHITAGI_COLOR")
        out.print("の")
        run_chinobun(ctx, "KAIZOU_PANT")
    out.printl("が露わになった。")
    if t(ctx, c, "男の娘") > 0:  # :1099–1107
        out.printl("男たちの興奮とも怒号ともつかない歓声が沸き起こる。")
        out.printl("オンナみたいな顔とカラダで騙しやがって、と理不尽な罵声を浴びせられながら、")
        out.printl(f"硬い靴の裏でぐりぐりと{name}のペニスが踏みつけられる。")
        out.printl("苦悶に顔を歪める頭上で、見た目通りのメスにしてやるよ、と男の下卑た笑い声が響いた。")
    else:
        out.printl("男たちの興奮とも冷笑ともつかない歓声が沸き起こる。")
        out.printl("メスになりたいなら手伝ってやるよ、と男の下卑た笑い声が響いた。")


def _anal_first(ctx: Ctx, name: str) -> None:
    """:1124–1134（= :1141–1151）初回のアナル。"""
    c = tc(ctx)
    out = ctx.out
    a_exp = c.exp[ctx.data.index_of("EXP", "Ａ経験")]
    if a_exp < 1 and c.cflag[36] <= 30:
        out.printl("指すら入った事ないアナルをハンドクリームを使って")
        out.printl("何度もほぐしてからペニスを後穴にあてがい、ゆっくり埋めていく。")
        out.printl("肛門の裂け傷による痛みと共に、性器として認識されてなかったアヌスが男に貫かれた")
        out.print(f"{name}の悲鳴をＢＧＭにし、男はそのまま")
    elif a_exp < 5 or c.cflag[36] <= 40:
        out.print("ペニスで明らかにオトコ慣れしていないアナルに捻り込んで、")
    else:
        out.print("ペニスでアナルをほぐして挿入し、")
    out.printl("ピストンし始めた。")


def _rape_continue(ctx: Ctx, name: str) -> None:
    """:1264–1311 輪姦の続き。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    yok = abl(ctx, c, "欲望")
    shukan = tl("主観視点") > 0
    if c.cflag[286] > 2 or st.rng.rand(3) == 0:  # :1264–1283
        out.printl("順番待ちをしていた仲間と場所を代わってすぐに凌辱が再開される。")
        if (tl("淫乱") or yok >= 3) and tl("初心") < 1:
            out.printl(f"既に男たちの相手をすることにも慣れてきた{name}は")
            out.printl("手際よく精液を搾り取っていく。")
        elif c.cflag[286] > 9:
            out.printl(f"既に何度もレイプされたことのある{name}は")
            if shukan:
                out.printl("虚ろな表情で、嵐が過ぎ去るのを待つように奉仕に専念する。")
            else:
                out.printl("虚ろな表情で、嵐が過ぎ去るのを待つように奉仕に専念している。")
        else:
            out.printl(f"既に何度もレイプされたことのある{name}は")
            if shukan:
                out.printl("歯を食いしばり、諦めたように奉仕に専念する。")
            else:
                out.printl("歯を食いしばり、諦めたように奉仕に専念している。")
    elif c.cflag[286] > 0 and st.rng.rand(2) == 0:  # :1284–1291
        out.printl("順番待ちをしていた仲間と場所を代わってすぐに凌辱が再開される。")
        out.printl("全員に順番が回ると２週目、３週目が始まって休むことも許されず、")
        if shukan:
            out.printl(f"体を穢され続ける痛みと屈辱に、{name}の頬を熱い液体が伝っていく。")
        else:
            out.printl(f"{name}は目の端に涙を滲ませながら凌辱に耐えている。")
    else:  # :1292–1310
        # :1293 `(淫乱 || 欲望 >= 3 && 主観視点 > 0) && 初心 < 1`（&& が || より先）
        if (tl("淫乱") or (yok >= 3 and shukan)) and tl("初心") < 1:
            out.print("いつの間にか快楽に流されつつある")
        elif (tl("淫乱") or yok >= 3) and tl("初心") < 1:
            out.print("すっかり快楽に染められて反応の鈍くなった")
        elif shukan:
            out.print("湧き上がる悪寒に体を震わせている")
        else:
            out.print("なおも諦めずに止めるよう説得を続ける")
        out.printl(f"{name}を嘲笑うように")
        out.printl("最初からレイプ目的で芝居をしていたことを暴露した。")
        if tl("淫乱") == 0 and yok < 3 and shukan:
            out.printl("沸き立つ怒りと屈辱に任せて目の前の男を殴りつけようとするものの、")
            out.printl("過酷な戦闘と長時間の凌辱で疲弊しきった体は、満足に動かすことすらできない・・・")
        elif tl("淫乱") == 0 and yok < 3:
            out.printl(f"絶望に染め上げられた{name}の瞳が光を失っていく・・・")
    out.printw()  # :1311
