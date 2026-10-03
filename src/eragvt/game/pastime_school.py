"""自由行動「学校に行く」（S28c1）：`ゲーム内_イベント発生/自由行動中イベント/PASTIME_学校に行く.ERB`（路徑相對 `source/earGVP/ERB/`）。

- `@PASTIME_学校に行く, ARG`:1–364（服装・改造制服・通学〔PASTIME_CHIKAN〕・初登校・授業・昼休み・放課後・ナンパ・合コン・登校回数）、
  `@Message_School_Afterschool`:1445–1493、`@Message_School_SelectClub`:1497–1596（INPUT があるので Python）。
- 授業（`Message_School_Classwork`／`_CL`／`_PE`）・昼休み（`Message_School_Lunchbreak`：写真 PASTIME_SHASHIN を含む）・部活
  （`Message_School_Clubactivities`）・`School_ClubString`・改造制服（`KAIZOU_SEIFUKU`）・人気投票（`PASTIME_TOHYO`）は本文中心の
  関数として catalog で実行（`pastime._chinobun`、状態変化行は `narration/hooks.py` の `PASTIME_HOOK_LINES`）。

静的変数（関数内 `#DIM`／`#DIMS`、`GameProc/UserDefinedVariable.cs`:27）：`改造制服` は :9–10 で 1 になるだけで 0 に戻らない、
`目的地` は TALENT:学生 が 1〜4 以外なら前回値のまま：原作どおり `st.temp.locals` に保持（新規・ロードで消える）。
"""

from __future__ import annotations

from .action import Ctx
from .era import mod
from .pastime import (
    InputGen,
    _chinobun,
    _dot_after,
    _female,
    _girly,
    _male,
    _name,
    _rand,
    _t,
    message_pastime_nanpa,
    message_pastime_sake_nanpa,
    pastime_chikan,
    pastime_nanpa,
    pastime_sake_nanpa,
)

_KEY_KAIZOU = ("PASTIME_学校に行く:改造制服", 0)
_KEY_MOKUTEKI = ("PASTIME_学校に行く:目的地", 0)
_SCHOOL = {1: "小学校", 2: "中学校", 3: "高校", 4: "大学"}


def _bust_class(ctx: Ctx) -> None:
    """:153–157 等：転校生への視線（巨乳）。"""
    k = _t(ctx, "巨乳")
    if k > 2:
        ctx.out.printl("その視線がダイナミックな大きさのバストに集中しているのが気にならないではないが…")
    elif k > 0:
        ctx.out.printl("その視線が豊満な大きさのバストにささっているのが気にならないではないが…")


def _girls_noise(ctx: Ctx, n: str, topic: str) -> None:
    """:158–165 等：女生徒の反応（長身／小柄／その他）。"""
    out = ctx.out
    if _t(ctx, "長身") > 0:
        out.printl("一方で、女生徒達もスタイルの良さに対し黄色い悲鳴を上げ出しちょっとした騒ぎとなっている。")
    elif _t(ctx, "小柄") > 0:
        out.printl("一方で、女生徒達も小さくて可愛いなど小動物に対する様な声を上げ出しちょっとした騒ぎとなっている。")
    else:
        out.printl(f"一方で、女生徒達も{topic}に便乗しだしたり")
        out.printl(f"{n}を見て可愛いなど声を上げたりとちょっとした騒ぎとなっている。")


def _transfer_intro(ctx: Ctx, n: str, first: str, waiting: str, last1: str) -> None:
    """:136–177／:239–280（変身 TS の初登校・通常の転校生）の小中高。"""
    out = ctx.out
    out.printl(first)
    out.printl("さっそく担任の教師に案内され教室の前まで来ると、廊下で待つように告げられ担任だけが教室に入っていった。")
    out.printl("扉の前で暫く待っていると教室の中からざわめきと歓声が聞こえてくる。")
    out.printl(waiting)
    out.printw()
    out.printl(f"扉が開かれ、担任が{n}に入ってくるよう促した。")
    out.printl(f"言われるがままに教室に入った{n}は教壇の側に立つと")
    out.printl("クラスメイトに初めましての挨拶と自己紹介をした。")
    out.printl()
    if _male(ctx):
        out.printl(f"顔を上げた{n}に対して")
        out.printl("女生徒達が黄色い悲鳴にも似た声で質問攻めを始め")
        out.printl("教師が静かにするように注意をする。")
    else:
        out.printl(f"顔を上げた{n}に対して")
        out.printl("男子生徒達が荒ぶりだし、矢継ぎ早にやれ彼氏はいるのかだのタイプの男はだの質問攻めを始める。")
        _bust_class(ctx)
        _girls_noise(ctx, n, "恋愛関係の話題")
        out.printw()
        out.printl(f"{n}が周囲への対応に困っていると、")
        out.printl("助け舟を出すように担任が静かにするように何度も注意するが、騒ぎはなかなか収まらない。")
        out.printl("朝礼の時間を使い果たし授業が始まる頃になってようやく、教室は静けさを取り戻したのだった。")
    out.printw()
    out.printl(last1)
    out.printl(f"無事に挨拶を終えた{n}は指定された席に着席した。")
    out.printl()
    out.printl(f"かくして、{n}の第二の学校生活が始まったのだった…")
    out.printw()


def _university_first(ctx: Ctx, n: str, line1: str) -> None:
    out = ctx.out
    out.printl(line1)
    out.printl("部外者も多数訪れる大学では見慣れない顔が一つ増えた程度では気にも留められないようだ。")
    out.printl()
    out.printl(f"かくして、{n}の第二の大学生活が始まったのだった…")
    out.printw()


def pastime_school(ctx: Ctx, arg: int) -> InputGen:
    """`@PASTIME_学校に行く, ARG`:1–364。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    t = lambda k: _t(ctx, k)  # noqa: E731
    locs = st.temp.locals
    if c.cflag[40] in (101, 102) and c.cflag[1] < 1:  # :9–10
        locs[_KEY_KAIZOU] = 1
    kaizou = locs.get(_KEY_KAIZOU, 0) == 1
    if t("学生") in _SCHOOL:  # :13–24
        locs[_KEY_MOKUTEKI] = _SCHOOL[t("学生")]  # type: ignore[assignment]
    mokuteki = locs.get(_KEY_MOKUTEKI, "") or ""
    gakusei = t("学生")
    chuko = gakusei in (2, 3)
    n = _name(ctx)

    def seifuku() -> None:
        _chinobun(ctx, "KAIZOU_SEIFUKU")

    gal = ("制服を露出の多くなるように着こなし、スカート丈も下着が見えそうなマイクロミニ。",)
    out.printl("学校に行く")  # :26–27
    out.printl()
    if _female(ctx) and t("変身時ＴＳ") > 0 and c.cflag[1] > 0:  # :29–70
        if t("淫乱") > 0 and t("初心") <= 0:
            out.printl(f"女性の姿に変身した{n}は、身綺麗にして{mokuteki}に登校した。")
            out.printw()
            if chuko:
                if kaizou:
                    seifuku()
                else:
                    out.printl(gal[0])
                    out.printl("校則違反になる派手な色のソックスを身に付けた姿はいかにも腰の軽そうなギャル風だ。")
            else:
                out.printl("露出の多い服装に下着が見えそうなマイクロミニスカート。")
                out.printl("とどめに派手な色のサイハイソックスを身に付けた姿はいかにも腰の軽そうなギャル風だ。")
            out.printw()
        elif t("女体受容") > 0:
            out.printl(f"{n}は女性化した状態で{mokuteki}に行くことにした。")
            if kaizou and chuko:
                seifuku()
            out.printw()
            out.printl("以前に感じていた違和感を今は全く感じなくなり")
            out.printl("すっかり変身中のカラダに慣れた事を実感する。")
            out.printw()
        else:
            out.printl("少しでも変身中のカラダに慣れておこうと考え")
            out.printl(f"{n}は女性化した状態で{mokuteki}に行くことにした。")
            out.printw()
            if chuko:
                if kaizou:
                    seifuku()
                out.printl("着慣れない女子用の制服に身を包み身嗜みもしっかり整えたつもりだが")
                out.printl("不慣れな為か変な目で見られていないかと気になってしまう。")
            else:
                out.printl("ネットや雑誌を参考に服装はしっかり整えたつもりだが")
                out.printl("不慣れな為か変な目で見られていないかと気になってしまう。")
            out.printw()
    elif t("淫乱") > 0 and t("初心") <= 0 and _girly(ctx):  # :72–85
        out.printl(f"{n}は、身綺麗にして{mokuteki}に登校した。")
        out.printw()
        if chuko:
            if kaizou:
                seifuku()
            else:
                out.printl(gal[0])
                out.printl("とどめに派手な色のサイハイソックスを身に付けた姿はいかにも腰の軽そうなギャル風だ。")
        else:
            out.printl("露出の多い服装に下着が見えそうなマイクロミニスカート。")
            out.printl("とどめに派手な色のサイハイソックスを身に付けた姿はいかにも腰の軽そうなギャル風だ。")
    elif t("女体受容") > 0:  # :86–93
        out.printl(f"{n}は{mokuteki}に行くことにした。")
        if kaizou:
            seifuku()
        out.printw()
        out.printl("以前に感じていた違和感を今は全く感じなくなり")
        out.printl("すっかりオンナのカラダに慣れた事を実感する。")
        out.printw()
    elif mod(t("性別変化"), 10) == 1 and _female(ctx):  # :94–106
        out.printl("もはやオンナのカラダに慣れるしかないと覚悟し")
        out.printl(f"{n}は女らしい格好で{mokuteki}に行くことにした。")
        out.printw()
        if chuko:
            if kaizou:
                seifuku()
            out.printl("着慣れない女子用の制服に身を包み身嗜みもしっかり整えたつもりだが")
            out.printl("不慣れな為か変な目で見られていないかと気になってしまう。")
        else:
            out.printl("ネットや雑誌を参考に服装はしっかり整えたつもりだが")
            out.printl("不慣れな為か変な目で見られていないかと気になってしまう。")
    elif t("男の娘") > 0 and kaizou:  # :107–113
        out.printl("触手共はオトコより女性を狙いやすい、囮となって捜索するには…")
        out.printl(f"そんな理由があって、{n}はやむにやまれず女子の服を着ていた。")
        seifuku()
        out.printw()
        out.printl("うまく女性らしく振る舞えるようになるには普段の生活から。")
        out.printl("任務のために嫌々着ているはずなのに、奇妙な胸の高鳴りがずっと治まらなかった。")
    else:  # :114–119
        out.printl(f"{n}は、{mokuteki}に行くことにした。")
        if kaizou and chuko:
            seifuku()
        out.printw()
    out.printl()  # :120–122
    _dot_after(ctx, 1)
    out.printl()
    if (yield from pastime_chikan(ctx, arg)) != 0:  # :123–124
        return
    if t("変身時ＴＳ") > 0 and c.cflag[1] > 0 and c.cflag[351] < 1:  # :126–178 変身 TS の初登校
        if gakusei == 4:
            _university_first(ctx, n, f"変身した姿で大学へと訪れた{n}だったが、案の定というべきか")
        else:
            _transfer_intro(ctx, n, f"変身した姿で登校した{n}は、職員室に立ち寄り挨拶を済ませた。",
                            f"教室の中では「見知らぬ転校生」である{n}に注目が集まっているのだろう……",
                            "普段の自分を見る目とは異なる視線に晒され緊張したものの")
    elif mod(t("性別変化"), 10) == 1 and c.cflag[357] < 1:  # :181–226 完全／強制女体化の初登校
        if gakusei == 4:
            out.printl(f"女体化した体で大学へと訪れた{n}だったが、事の経緯はデタラメで誤魔化し、")
            out.printl("あらためて自己紹介するまで案の定というべきか、友人や顔見知りの学生たちに気付かれなかった。")
            out.printl("自己紹介した後ですら散々疑われたが、当人以外知り得ない思い出話などでようやく納得された始末だ。")
            out.printl()
            out.printl(f"かくして、{n}の第二の大学生活が始まったのだった…")
            out.printw()
        else:
            out.printl(f"女体化した体で登校した{n}は、職員室に立ち寄り挨拶を済ませた。")
            out.printl("戸惑う担任の教師に案内され教室の前まで来ると、廊下で待つように告げられ担任だけが教室に入っていった。")
            out.printl("扉の前で暫く待っていると教室の中からざわめきと歓声が聞こえてくる。")
            out.printw()
            out.printl(f"扉が開かれ、担任が{n}に入ってくるよう促した。")
            out.printl(f"言われるがままに教室に入った{n}は教壇の側に立つと")
            out.printl("クラスメイトに改めて挨拶と自己紹介をした。")
            out.printl()
            out.printl(f"顔を上げた{n}に対して")
            out.printl(f"男子生徒達が荒ぶりだし、本当に{n}なのかだの好みのタイプだなどと吠え始める。")
            _bust_class(ctx)
            _girls_noise(ctx, n, "髪型がどうとかの話題")
            out.printw()
            out.printl(f"{n}が周囲への対応に困っていると、")
            out.printl(f"担任が、事情があって{n}は女になったが以前と同じように接するように、")
            out.printl("特に女子は色々助けてやってくれ、とフォローする。")
            out.printl("朝礼の時間を使い果たし授業が始まる頃になってようやく、教室は静けさを取り戻したのだった。")
            out.printw()
            out.printl("以前の自分を見る目とは異なる視線に晒され緊張したものの")
            out.printl(f"無事に挨拶を終えた{n}はいつもの席に着席した。")
            out.printl()
            out.printl(f"かくして、{n}の第二の学校生活が始まったのだった…")
            out.printw()
    elif c.cflag[359] == 1 and c.cflag[350] == 0:  # :229–281 通常の転校生
        if gakusei == 4:
            _university_first(ctx, n, f"新たに編入した大学を訪れた{n}だったが、案の定というべきか")
        else:
            _transfer_intro(ctx, n, f"編入先の学校へと登校した{n}は、職員室に立ち寄り挨拶を済ませた。",
                            f"教室の中では見知らぬ転校生である{n}に注目が集まっているのだろう……",
                            "戦いの中で自分に集まる注目とは異なる視線に晒され緊張したものの、")
    else:  # :284–313 通常の登校
        if gakusei == 4:
            out.printl(f"大学に訪れた{n}は講義の予定を確認した。")
            out.printl("ついでに連絡事項の確認をするが…")
            if _rand(ctx, 10) == 0:
                out.printl("どうやら同じ大学の学生が触手の被害にあったようで")
                out.printl("警戒を呼び掛けるお知らせが届いている。")
            else:
                out.printl("特にこれと言った連絡事項はないようだ。")
        elif c.cflag[356] > 0:
            if c.cflag[356] == 1:
                out.printl(f"{n}は遅刻してしまい、ホームルームに間に合わなかった。")
            c.cflag[356] = 0  # :302
        else:
            out.printl(f"{n}は始業時間までに登校した。")
            out.printl("ホームルームにて連絡事項を告げられるが…")
            if _rand(ctx, 10) == 0:
                out.printl("どうやら同じ学校の生徒が触手の被害にあったようだ。")
                out.printl("教師が沈痛な面持ちで注意を呼びかけ、微妙な雰囲気の中で授業が始まった…")
            else:
                out.printl("特にこれと言った連絡事項はないようだ。")
        out.printw()
    for label, func in (("【午前】", "Message_School_Classwork"), ("【昼休み】", "Message_School_Lunchbreak"),
                        ("【午後】", "Message_School_Classwork")):  # :316–329
        out.printl()
        out.printl(label)
        _chinobun(ctx, func)
    out.printl()  # :332–334
    out.printl("【放課後】")
    yield from afterschool(ctx)
    if pastime_nanpa(ctx) > 0:  # :340–346
        yield from message_pastime_nanpa(ctx, arg)
    else:
        out.printl(f"{n}は、学業を果たしてきたようだ。")
        out.printw()
    if gakusei == 4:  # :349–354 合コン
        if pastime_sake_nanpa(ctx) > 0:
            yield from message_pastime_sake_nanpa(ctx, arg)  # :352 `CALL …, ARG`（学校の ARG）
    if t("変身時ＴＳ") > 0 and c.cflag[1] > 0:  # :358–363
        c.cflag[351] += 1
    else:
        c.cflag[350] += 1
        c.cflag[357] += 1
    st.result[0] = 0


def afterschool(ctx: Ctx) -> InputGen:
    """`@Message_School_Afterschool`:1445–1493。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    gakusei = _t(ctx, "学生")
    n = _name(ctx)
    if _rand(ctx, 5) == 0:  # :1447–1448
        _chinobun(ctx, "PASTIME_TOHYO")
    cf1 = c.cflag[1]
    if c.cflag[352] not in (0, 10, 20) and cf1 < 1:  # :1451–1454
        _chinobun(ctx, "Message_School_Clubactivities")
    elif c.cflag[353] not in (0, 10, 20) and cf1 > 0:
        _chinobun(ctx, "Message_School_Clubactivities")
    elif _t(ctx, "変身時ＴＳ") > 0 and c.cflag[351] == 0 and cf1 > 0:  # :1455–1469
        if gakusei == 4:
            out.printl(f"{n}が敷地内を歩いているとサークルメンバー募集と書かれたポスターが目に入った。")
            out.printl("大学としては特にサークルに参加することを強制している訳ではないが・・・")
        elif gakusei == 1:
            out.printl(f"担任教師に呼び止められた{n}はクラブ活動をどうするか尋ねられた。")
            out.printl("学校としては特にクラブに参加することを強制している訳ではないが・・・")
        else:
            out.printl(f"担任教師に呼び止められた{n}は部活動をどうするか尋ねられた。")
            out.printl("学校としては特に部活に参加することを強制している訳ではないが・・・")
        out.printw()
        yield from select_club(ctx)
        out.printw()
    elif (c.cflag[350] == 0 and cf1 < 1) or (mod(c.cflag[350], 10) == 0 and cf1 < 1) or (mod(c.cflag[351], 10) == 0 and cf1 > 0):
        if gakusei == 4:  # :1470–1482
            out.printl(f"{n}が敷地内を歩いているとサークルメンバー募集と書かれたポスターが目に入った。")
        elif gakusei == 1:
            out.printl(f"{n}が校内を歩いているとメンバー募集と書かれたポスターが目に入った。")
        else:
            out.printl(f"{n}が校内を歩いていると部員募集と書かれたポスターが目に入った。")
        out.printl("折角の学生生活だ、そろそろどこかに所属してみても良いのではないだろうか・・・")
        out.printw()
        yield from select_club(ctx)
        out.printw()
    if gakusei == 4:  # :1485–1492
        out.printl(f"{n}は大学を後にするようだ・・・")
    else:
        out.printl(f"{n}は友人と別れて帰路に着くようだ・・・")
    out.printw()
    st.result[0] = 0  # :1493


_CLUBS = {4: ("所属しない", "体育系サークル", "文系サークル", "アニメサークル"),
          1: ("所属しない", "スポーツクラブ", "図書委員", "新聞委員")}
_CLUBS_DEFAULT = ("帰宅部", "運動部", "文系部", "風紀委員")


def select_club(ctx: Ctx) -> InputGen:
    """`@Message_School_SelectClub`:1497–1596。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    gakusei = _t(ctx, "学生")
    names = _CLUBS.get(gakusei, _CLUBS_DEFAULT)
    out.printl()
    for i, s in enumerate(names):
        out.printl(f"[{i}]{s}")
    out.printl()
    out.drawline()
    while True:  # :1518–1560
        result = yield
        st.result[0] = result
        out.printl()
        out.drawline()
        if 0 <= result <= 3:
            out.printl(names[result])
            out.printl()
            break
        out.printl("正しい値を入力してください")
    local = 20 + result if gakusei == 4 else result if gakusei == 1 else 10 + result  # :1562–1569
    if c.cflag[1] > 0:  # :1572–1576
        c.cflag[353] = local
    else:
        c.cflag[352] = local
    out.print(f"{_name(ctx)}は")
    if result in (0, 10, 20):  # :1579（RESULT は入力値 0〜3 → 0 のときだけ）
        cnt = c.cflag[351] if c.cflag[1] > 0 else c.cflag[350]
        out.printl("帰宅部のままでいることにした。" if cnt > 0 else "どこにも入部しないことにした。")
    else:
        _chinobun(ctx, "School_ClubString")
        out.printl("に所属することにすると、入部届を提出した。")
    st.result[0] = 0  # 関数終端
