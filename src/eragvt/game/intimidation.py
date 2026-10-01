"""クズ市民の脅迫・拉致監禁（S18）：`ゲーム内_イベント発生/強制発生イベント/FORCE_クズ市民の脅迫.ERB`
（路徑相對 `source/earGVP/ERB/`）。

呼び出し元は `インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND`:90–101 のみ（全 ERB で唯一）：
- `CONFIG_CHECK_PRISON_F(10) == 1`（「クズ市民による幽閉」、基本セットは OFF：FLAG:804 = 1）かつ CFLAG:0 が 無事／5 かつ
  CFLAG:286 + 320 + 321 > 0 → INTIMIDATION_EVENT。
- そうでなく CFLAG:0 == 状態_クズ監禁（4、`CSV定数定義/CFLAG.ERH`:18）→ KIDNAPPING（昼夜とも）。

本文はイベント本体の中で状態変化と交互に出るので S15／S17 と同じく Python に移植。CALC_GANGBANG（AFTER_PILL の INPUT）を
呼ぶのでジェネレータ。地の文 `地の文/MESSAGE_CITIZEN_TRAIN.ERB@MESSAGE_CITIZEN_HIACED` は状態変化なし → catalog。

フラグ（`●開発者向け資料/●GVTフラグ一覧.txt`:231–233、350–354、362–363）：CFLAG:70 誘拐監禁回数（CALC_GANGBANG "監禁" で +1）、
71 監禁救出フラグ（救出までの必要ポイント。減るのは情報収集 `ACTION_GATHER_INFORMATION.ERB`:1004–1041 のみ：未移植）、
72 監禁クールダウン（8 を代入するだけで**減らす処理は全 ERB に無い**：一度救出・解放されると以後脅迫は起きない）、
290 脅迫イベント進行状態、291 脅迫イベントリセット回数（全 ERB で代入なし＝常に 0）。

引擎語意：
- 添字省略は TARGET（`reference/emuera-1824/Emuera/GameData/Variable/VariableParser.cs`:91–134）。`&&`／`||` は短絡、
  `&&` は `||` より先に結合（`GameData/Expression/OperatorMethod.cs`:532–536、`ExpressionParser.cs` の優先順位）。
- PRINTDATA は `GetNextRand(件数)` で 1 件選び改行しない（`GameProc/Function/Instraction.Child.cs@PRINT_DATA_Instruction`:195–）。
- PRINT 系の引数は命令の後の 1 文字（空白）の次から（`PRINTFORML  何巡も…` は先頭に半角空白が 1 つ残る）。
- `RAND(a, b)` = a + GetNextRand(b - a)（`GameData/Function/Creator.Method.cs`:953–972）。
- INTIMIDATION_EVENT の LOCAL は :8 VARSET。:238／:269 で LOCAL = 1（パイズリ）にしない限り、:290 `IF LOCAL == 1` は
  発生確率の値（:27–54 の LOCAL）を見る（原作どおり：その値がちょうど 1 なら胸射の文になる）。
"""

from __future__ import annotations

from collections.abc import Generator

from .action import Ctx, config_check_event, print_transcallname
from .battle.core import abl, is_hole, run_chinobun, t, tc
from .chara_common import is_male
from .era import div
from ..state.constants import CharaState

InputGen = Generator[None, int, int]

_KIDNAPPED = CharaState.KIDNAPPED  # 4：CSV定数定義/CFLAG.ERH:18 状態_クズ監禁


def _pd(ctx: Ctx, items: tuple[str, ...]) -> str:
    """PRINTDATA の選択（GetNextRand(件数)）。"""
    return items[ctx.state.rng.rand(len(items))]


def charanum_enslaved(ctx: Ctx) -> int:
    """`汎用関数/CHARANUM.ERB@CHARANUM_ENSLAVED`:70–77。"""
    st = ctx.state
    return sum(1 for i in range(1, st.charanum) if st.charas[i].cflag[0] == _KIDNAPPED)


def intimidation_event(ctx: Ctx) -> InputGen:
    """`@INTIMIDATION_EVENT`:4–441。"""
    from .battle.rape import calc_gangbang
    from .battle.sexcom import check_holyvirgin

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    a = lambda n: abl(ctx, c, n)  # noqa: E731
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    male = lambda: is_male(data, c)  # noqa: E731
    rand = st.rng.rand
    nakadashi = 0  # :7
    local = 0  # :8 VARSET LOCAL
    if st.time != 1:  # :9–10
        return 0
    if not is_hole(ctx):  # :11–12
        return 0
    if c.cflag[72] > 0:  # :13–14 クールダウン中
        return 0
    if config_check_event(st, 3) == 0:  # :15–16
        return 0
    if st.flag[852] > 5000:  # :19–20
        return 0
    if c.cflag[286] + c.cflag[320] + c.cflag[321] == 0:  # :23–24
        return 0
    if c.cflag[286] > 0:  # :27–28
        local += c.cflag[286]
    if c.cflag[320] > 0 or c.cflag[321] > 0:  # :29–30
        local += c.cflag[320] + c.cflag[321]
    if c.cflag[284] > 0:  # :31–32
        local += c.cflag[284]
    if a("従順") + a("マゾっ気") > 2:  # :34–35
        local += a("従順") + a("マゾっ気")
    if c.cflag[290] > 0:  # :37–38
        local += c.cflag[290] * 2
    if 0 < c.cflag[291] <= 10:  # :41–42
        local -= c.cflag[291]
    if c.cflag[291] > 0 and c.cflag[291] > 10:  # :43–44
        local = div(local, 2)
    if tl("巻き込まれ体質") > 0:  # :47–52
        local += 1
    if tl("人外の美貌") > 0:
        local += 1
    if tl("嬲られ体質") > 0:
        local += 3
    if local < rand(30):  # :54–55
        return 0
    name = lambda: print_transcallname(st, st.target)  # noqa: E731
    # :58–180 取り囲まれるまで
    out.drawline()
    out.set_bold(True)
    out.printl(f"クズ市民の脅迫:{name()}")
    out.set_bold(False)
    out.printl()
    timid = bool(tl("臆病") or tl("恥ずかしがり屋") or tl("悲観的") or a("従順") > 3)
    if c.cflag[290] == 0:  # :63–118 初回
        out.printl("夜――")
        out.printl(f"日課の訓練と勉強を終え、風呂から上がったばかりの{name()}は、携帯が鳴り続けている事に気づいた。")
        out.printl("こんな時間に誰だろうと通知画面を確認すると、登録した覚えもない名前が表示されていた。")
        out.printl("間違い電話かもしれないし、もしかしたらうっかり忘れただけかもしれない。")
        out.printl(f"{name()}は電話に出てみる事にしたが……")
        out.printw("画面の向こうから聞こえたのは、トラウマを呼び覚ます男の声だった。")
        out.printl()
        out.printl("この前は楽しかったぜと楽しそうに告げる男は、これから指示されたところに来いと命令し、")
        out.print(f"もし来なければ{name()}が男たちに犯された時の写真や映像をばらまく")
        if c.cflag[284]:  # :73–78
            out.printl("、")
            out.printl("加えて触手に犯された事も知っている、友人たちに正体もバラすなどと脅してきた。")
        else:
            out.printl("と脅してきた。")
        out.printl()
        if timid:  # :80–86
            out.printl(f"突然の脅迫に{c.callname}が思考を硬直させていると、")
            out.printl("男達は電話を切った後、携帯に動画url付きのメールが一件送信されてきた。")
        else:
            out.printl(f"思い通りにされるつもりなどない{c.callname}は「警察に通報する」と強気に告げて通話を切ったが、")
            out.printl("その直後、携帯に動画url付きのメールが一件送信されてきた。")
        out.printl("……リンク先の動画は確認するまでもなく、")
        out.printw(f"{name()}が男たちに輪姦されていた時の動画だった。")
        out.printl("男達がその気になれば、指先一つで世界に痴態と個人情報を広められてしまう……")
        out.printl("こんな動画まで突き出されては、さすがにじっとしてもいられない。")
        out.printl("内容が内容だけに他人に相談するのも難しく、")
        out.printw(f"{name()}は仕方なく言われた通りの場所まで一人で向かうことにした。")
        out.printl()
        out.print(f"十数分後、{name()}は")  # :95–101
        if timid:
            out.print("男達へ懇願するために、指定された廃ビルへ辿り着いた。")
        else:
            out.print("男達と直談判するために、指定された廃ビルへ辿り着いた。")
        out.printl()
        out.printl(f"誰もいないと思った途端、後ろから誰かに拘束される{name()}。")
        out.printl(f"口元に押し当てられた布から刺激臭を感じた瞬間、{name()}のカラダから急に力が抜け……")
        if male():  # :104–110
            out.printl(f"……{name()}というメス男子の脳も、触手由来の淫気には決して抗えない。")
        else:
            out.printl(f"……{name()}という女性の脳も、触手由来の淫気には決して抗えない。")
        out.print(_pd(ctx, ("「エンジェル・ダスト」", "「スレイヴメーカー」", "「TEMPTATION XXX」", "「T-L Potion」",
                            "「ラブベラドンナ」")))  # :111–117
        out.printw(f"を嗅がされ意識を失った{name()}は、男達に廃ビルの中へ担ぎ込まれてしまった…")
    else:  # :119–179 2 回目以降
        out.printl(f"日が落ちる頃に、{c.callname}を脅迫している男から再び呼び出しの電話がかかってきた。")
        out.printl()
        slave = bool((tl("淫乱") or (tl("マゾ気質") and a("マゾっ気") >= 3)) and tl("初心") < 1)
        if slave:  # :123–127
            out.printl(f"すっかり男達の飼い犬になってしまった{c.callname}は、命令された通り")
            out.printl("コートの下は一糸纏わぬハダカで、更に与えられた首輪を付けたまま指示された場所へ向かった……")
            out.printl(f"男達が集まってくると、{name()}はおずおずとコートを脱ぎ捨てた。")
            out.printl("男達は堕ちた雌犬をひとしきり嘲笑し、ご褒美とばかりにズボンを下ろしてペニスを突き出す。")
        else:  # :128–176
            out.printl(f"こんなことはもう止めてほしいと{name()}は懇願したが、聞き入れてもらえる様子はない。")
            out.printl("それどころか「さっさと来いメス犬！」と怒鳴られ、男達にそのまま電話を切られてしまった。")
            out.printl()
            out.printl("……これ以上機嫌を損ねれば、屈辱にまみれた凌辱映像の数々が間違いなく「流出」する。")
            if male():  # :133–139
                out.printl("全世界に向けて、ありとあらゆる個人情報と共に公開される恥辱の記録…仮にもオトコとして到底耐えられるはずもない。")
            else:
                out.printl("全世界に向けて、ありとあらゆる個人情報と共に公開される恥辱の記録…女性として到底耐えられるはずもない。")
            out.printl(f"この先の人生、そして尊厳を人質に取られた{name()}に、抵抗できる余地は無い。")
            out.printl("いずれ男達の気が変わるか、助けが来るか、あるいは何かの拍子に好機が訪れれば……")
            out.printw(f"頼りない希望を抱きつつ、{name()}は仕方なく指示された場所に向かったが・・・")
            out.printl()
            out.printl(f"いつも通りにズボンをおろし、{name()}を囲むように近づいてきた男達。")
            out.print(f"{name()}が")  # :146–160
            choice = rand(4)  # PRINTDATA :147–152（選んだ DATAFORM だけを評価）
            if choice == 0:
                out.print("「こんな事は犯罪だ」")
            elif choice == 1:
                out.print("「良心があるなら許してほしい」")
            elif choice == 2:
                out.print(f"「{'オトコ' if male() else '女性'}を嬲り者にして恥ずかしくないのか」")
            else:
                out.print("「今ならまだ許される」")
            out.print("と")
            out.print(_pd(ctx, ("涙ながらに", "勇気を出して", "恐る恐る", "怖気付きつつも")))
            out.printl("訴えてみると……")
            out.printl("舐めているのかとばかりにヤクザらしき男に殴られ、下腹部を力強く蹴り飛ばされてしまった。")
            if slave:  # :166–176（同じ条件：上の IF で偽なのでこの分岐は到達しない＝原作どおり）
                out.printl("直撃された性器は、激しく弾け飛んだかのように絶頂の信号を発した。")
                out.printl(f"{name()}はあっさりとオーガズムに屈し、目を大きく見開いてあてもなく涙を流す。")
                out.printl("噴き出した唾液が空中に舞い上がって体に飛び散り、下半身から飛び散ったものは汁か尿か区別がつかない。")
                out.printl(f"{name()}は地面を何度も転がりながら、無防備な姿で男たちの壁にぶつかり、ついに止まった。")
                out.printl("全く抵抗できないうちに、後ろ手に縛られ、服を乱暴に剥ぎ取られ、全裸で卑猥な姿にされたまま意識が朦朧としていた…。")
            else:
                out.printl(f"抵抗できるはずの速度だったが、{name()}の本能は既に屈服しつつあるのかもしれない。")
                out.printl(f"よろめいた{name()}は無防備な体勢のまま後ろの男にぶつかってしまい、")
                out.printw("抵抗一つ出来ないうちに羽交い絞めにされて服を脱がされ、呆気なく一糸纏わぬ姿へと剥かれてしまった……")
        out.printl()  # :178
    # :183–350 本番
    out.printw()
    rapecount = c.cflag[290]  # :185
    out.drawline()
    out.printl("――")
    out.printl("――――")
    out.printw("――――――")
    out.printl()
    if rapecount == 0:  # :191–199
        out.printl(f"気が付くと、{name()}は周りを複数の男に囲まれていた。")
        out.printl(f"取り囲んでいる男の一人が{name()}の意識が戻った事に気付き、")
        out.printl(f"周囲に合図を送ると{name()}に向かってにじり寄ってくる…")
    else:
        out.printl(f"気が付くと、{name()}は周りを複数の男に囲まれているようだった。")
        out.printl("取り囲んでいる男の一人が、今回も頼むぜと下卑た声で声を掛けてきた。")
        out.printl(f"どうやら以前{name()}を犯した男の一人だったようだ…")
    out.printl()
    out.printl(f"{name()}は覆面で顔を隠した男たちに取り押さえられ、目の前に勃起したペニスを突き付けられている。")
    if tl("淫乱") and tl("初心") < 1:  # :202–214
        out.printl(f"{name()}は誘惑するように、上目遣いで男に奉仕し始めた・・・")
    elif a("欲望") >= 3 and tl("初心") < 1:
        out.printl("これは逃げるため…私は戦い続けなければ…だから今は彼らの要求に応えるしか…")
        out.printl(f"{name()}は心の中で言い訳をしながら、男のペニスに奉仕を始めた・・・")
    elif a("従順") >= 3:
        out.printl(f"{data.str_defaults.get(2500, '')}との戦いで身体と心に服従を教え込まれている{name()}は、")
        out.printl("適切な鍛錬をしなかったせいで、こんな男たちすら振り払えなくなった…と心の中で考えるしかない。")
    else:
        out.printl(f"薬物や暴行の影響なのか、{name()}は身体にまったく力が入らず、")
        out.printl("碌に鍛錬もしていないであろう男たちを振り払うことができない・・・")
    out.printw()
    if rapecount == 0 or rand(2) == 0:  # :219–259
        out.printl(f"両手でそれぞれペニスを握り、口にもペニスを咥える{name()}。")
        out.printl("手コキとフェラチオで限界に達した男たちが射精に至るが、男根は全く衰える様子をみせない。")
        out.printl(f"このままでは……と{name()}が焦りを覚えた次の瞬間、")
        out.printl(f"{name()}は男たちに無理矢理押し倒され、手足まで抑えつけられてしまう。")
        out.printw()
        if tl("淫乱"):
            out.printl(f"驚きの声を上げる{name()}の唇を奪い、")
        else:
            out.printl(f"制止しようとする{name()}の説得も空しく、")
        out.print("男は")
        if male():  # :231–252
            out.printl("ペニスでアナルをほぐして挿入し、ピストンを始めた。")
        elif check_holyvirgin(ctx) == 1:
            if tl("貧乳") < 1 and rand(2) == 0:
                out.printl("胸でペニスを挟ませ、パイズリを強要した。")
                local = 1
            else:
                out.printl("ペニスでアナルをほぐして挿入し、ピストンし始めた。")
        elif tl("処女") > 0:
            out.printl("ペニスを何度か擦り付けると、ゆっくりと腰を埋めていく。")
            out.print("破瓜の痛みと共に、まだ男を知らないヴァギナが貫かれ")
            if tl("淫乱") or a("欲望") >= 3:
                out.printl("てゆく中、")
            else:
                out.print("る痛みの中、")  # PRINT（改行なし：原作どおり、次の文が同じ行に続く）
        else:
            out.printl("ペニスをヴァギナに深々と挿入して、ゆっくり腰を使い始めた。")
        if tl("交際相手") > 2:  # :253–257
            out.printl(f"{name()}は無駄な事と知りながら、愛する人に助けを求め続けた・・・")
        elif tl("交際相手") > 0:
            out.printl(f"{name()}は無駄な事と知りながら、恋する人に助けを求め続けた・・・")
        if tl("淫乱") == 0 and a("欲望") < 3:  # :258–259
            out.printl(f"{name()}の悲鳴が辺りに響き渡る・・・")
    else:  # :260–283
        out.printl(f"すると男はそのまま{name()}を押し倒し、")
        if male():
            out.printl("アナルに挿入して乱暴にピストンを始めた。")
        elif check_holyvirgin(ctx) == 1:
            if tl("貧乳") < 1 and rand(2) == 0:
                out.printl("胸でペニスを挟ませ、激しいピストンを開始した。")
                local = 1
            else:
                out.printl("悲鳴を上げる口をふさぐようにペニスをねじ込み、乱暴にピストンを始めた。")
        elif tl("処女") > 0:
            out.printl("まだ男を知らないヴァギナを貫いた。")
        else:
            out.printl("ヴァギナに挿入し、乱暴にピストンし始めた。")
        if tl("交際相手") > 2:
            out.printl(f"{name()}は無駄な事と知りながら、愛する人に許しを求め続けた・・・")
        elif tl("交際相手") > 0:
            out.printl(f"{name()}は無駄な事と知りながら、恋する人に助けを求め続けた・・・")
    out.printw()  # :284
    if male():  # :285–324
        out.printl("限界に達した男が直腸内に精液を放出すると、")
    elif check_holyvirgin(ctx) == 1:
        if local == 1:
            out.printl("限界に達した男が胸に精液をぶちまけると、")
            local = 0
        else:
            out.printl("男が口にねじ込んだまま喉に精液を放出すると、")
    elif tl("処女") > 0:
        out.set_bold(True)
        out.printl("処女喪失")
        c.talent[data.index_of("TALENT", "処女")] = -1  # :299–301（LOCAL:20 = 500 は以後使われない）
        c.cflag[206] = 11
        out.set_bold(False)
        if (tl("淫乱") or a("欲望") >= 3 or a("マゾっ気") >= 3) and tl("初心") < 1:
            out.printl("乱暴に処女膜を引き裂かれる痛みに耐えながらも、")
            out.printl("誰とも知らない男性に処女を奪われたという事実に、")
            if tl("主観視点") > 0:
                out.printl(f"{name()}の体は興奮して快楽を感じ始めてしまう。")
            else:
                out.printl(f"{name()}は興奮して快楽を感じ始めてしまう。")
        else:
            out.printl("乱暴に処女膜を引き裂かれる痛みに抵抗する気力を完全に奪われ、")
            out.printl("自分の身に起きた出来事を現実だと受け止めることすらできずに")
            out.printl(f"{name()}は誰とも知らない男に膣肉の純潔を押し開かれていく。")
        out.printw()
        out.printl("身勝手なピストンで男が限界に登り詰め、そのまま膣内射精を決めると、")
        nakadashi = 1
    else:  # :320–324（LOCAL:11 *= 3 は以後使われない）
        out.printl("男が限界に登り詰め、当然のように膣内射精を決めると、")
        nakadashi = 1
    if rapecount > 2 or rand(3) != 0:  # :325–350
        out.printl("順番待ちをしていた仲間と場所を代わり、すぐに凌辱が再開される。")
        if (tl("淫乱") or a("欲望") >= 3) and tl("初心") < 1:
            out.printl(f"既に男たちの相手にも慣れてきた{name()}は、")
            out.printl("蕩け顔を晒しながら手際よく精液を搾り取っていく。")
        elif rapecount > 6 or rand(2) == 0:
            out.printl(f"既に何度もレイプされたことのある{name()}は、")
            out.printl("目から希望の光を失い、少しでも早く終わるように")
            out.printl("少しでも自分の心が壊れないように、無心になって奉仕している。")
        else:
            out.printl(f"既に何度も呼び付けられている{name()}は")
            if tl("主観視点") > 0:
                out.printl("屈辱に歯を食いしばり、諦めたように奉仕に専念する。")
            else:
                out.printl("屈辱に歯を食いしばり、諦めたように奉仕に専念している。")
    else:
        out.printl("順番待ちをしていた仲間と場所を代わり、すぐに凌辱が再開される。")
        out.printl("全員に順番が回っても即座に２巡目、３巡目が始まって休むことも許されず、")
        if tl("主観視点") > 0:
            out.printl(f"体を穢され続ける痛みと屈辱に、{name()}の頬を熱い液体が伝っていく。")
        else:
            out.print(f"男達に脅迫され逆らえない{name()}は、目の端に涙を滲ませながら凌辱に耐えている。")  # PRINTFORM（改行なし）
    c.cflag[290] += 1  # :352
    out.drawline()
    out.set_bold(True)
    out.printl("脅迫輪姦・その後")
    out.set_bold(False)
    out.printl()
    out.printl("――")
    out.printl("――――")
    out.printw("――――――")
    out.printl()
    # :365–436 拉致監禁への派生
    traits = (tl("嬲られ体質") > 0) + (tl("巻き込まれ体質") > 0) + (tl("人外の美貌") > 0)
    if charanum_enslaved(ctx) == 0 and (
        c.cflag[290] >= 3 or rand(100) < 20 + min(20, c.cflag[286] + c.cflag[320] + c.cflag[321]) + traits * 10
    ):
        out.printl(f" 何巡も輪姦されて力尽き、男達の前で無防備に失神している{name()}。")
        out.printl(" このまま奴隷として飼ってしまわないか？ と提案されたリーダーらしき男は、")
        out.printl(f" 足元に倒れ伏す{name()}を冷酷な目付きで舐め回す。")
        if male():
            out.printl(" やがて値踏みを終えたらしい男が周囲に合図を出すと、他の男達は一斉に少年を取り囲み…")
        else:
            out.printl(" やがて値踏みを終えたらしい男が周囲に合図を出すと、他の男達は一斉に少女を取り囲み…")
        out.printl(f" 意識の無い{name()}を、首輪や鎖などで手早く拘束してゆく。")
        out.printl()
        run_chinobun(ctx, "MESSAGE_CITIZEN_HIACED", (st.target, "男たち", "脅迫"))  # :379
        c.cflag[0] = _KIDNAPPED  # :381
        c.cflag[71] = 30  # :383 救出までの必要ポイント
        nakadashi *= 2  # :385 拉致されたらピルは使えない
    elif charanum_enslaved(ctx) == 0 and rand(100) < 36 and tl("初心") < 1 and (
        tl("淫乱") or (tl("マゾ気質") and a("マゾっ気") >= 3)
    ):  # :388–423 ほいほいついていく
        out.printl("男たちの欲望をどれくらい受け止めたか分からなくなったころ、")
        out.printl(f"ようやく満足した男たちが{name()}を地面に放り捨て、そのまま去ろうとしたところ、")
        out.printl(f"快楽に蕩けきった{name()}は、「まって‥行っちゃいや…」とか細い懇願の声を漏らした。")
        out.printl(f"すっかり快楽の虜に堕ちた{name()}を見た男達は互いに顔を見合わせると、")
        if male():
            out.printl(f"ここに至るまでの{name()}のあらゆる反応を嘲笑い、口々に淫乱なメス男子を罵り始めた。")
        else:
            out.printl(f"ここに至るまでの{name()}のあらゆる反応を嘲笑い、口々に淫乱な少女を罵り始めた。")
        if male():
            out.printl("ヒトとして決して許すべきでない最低の罵倒、下卑た笑い声……")
        else:
            out.printl("女として決して許すべきでない最低の罵倒、下卑た笑い声……")
        out.printl(f"やがてリーダーらしき男が近寄ると、{name()}の首筋にスタンガンを押し当て…")
        out.printl(f"“バチン”と視界が弾け、{name()}の意識はあっさりとブラックアウトしてしまう。")
        if male():
            out.printw("哀れな少年は、守るべき市民のはずであった男達によって、性奴隷として連れ去られた……")
        else:
            out.printw("哀れな少女は、守るべき市民のはずであった男達によって、性奴隷として連れ去られた……")
        out.printl()
        out.set_color("#ffff00")
        out.printl(f" {name()}はクズ市民たちに拉致された。")
        out.reset_color()
        c.cflag[0] = _KIDNAPPED  # :421
        c.cflag[71] = 40  # :423
    else:  # :424–435
        out.printl("男たちの欲望をどれくらい受け止めたか分からなくなったころ、")
        out.printl(f"ようやく満足した男たちは{name()}をそのまま地面に放り捨てた。")
        out.printw("「次も頼むわ」という呪いの言葉と共に、嘲笑だけを残して去っていく男達。")
        out.printl()
        out.printl(f"全身を白く染められた{name()}は焦点すら定まらず、")
        if (tl("淫乱") or a("欲望") >= 3 or a("マゾっ気") >= 3) and tl("初心") < 1:
            out.printl("ただ快楽の余韻に脳髄を蕩けさせていた……")
        else:
            out.printl("犯されたショックと疲労で動くことができなかった……")
        out.printw()
    yield from calc_gangbang(ctx, "脅迫", 5, nakadashi)  # :439
    return 0


def kidnapping(ctx: Ctx) -> InputGen:
    """`@KIDNAPPING`:444–672。"""
    from .party import after_rescued

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    male = lambda: is_male(data, c)  # noqa: E731
    name = lambda: print_transcallname(st, st.target)  # noqa: E731
    rand = st.rng.rand
    if c.cflag[71] <= 0:  # :447–522 情報収集による救出
        out.drawline()
        out.set_bold(True)
        out.printl("拉致監禁・救出")
        out.set_bold(False)
        out.printl()
        out.printl("どれくらいの時間が経ったのだろうか…")
        out.printl(f"男達に監禁され、性処理道具として扱われ続けた{name()}からは、")
        if male():
            out.printl("もはや日付や昼夜の感覚、魔法少年としての誇り……ヒトとしての自覚すら消え去りつつあった。")
            out.printl("奉仕を命じられれば表情一つ変えずに男根を咥え、輪姦されるとなれば従順にアナルを差し出す。")
        else:
            out.printl("もはや日付や昼夜の感覚、魔法少女としての誇り……ヒトとしての自覚すら消え去りつつあった。")
            out.printl("奉仕を命じられれば表情一つ変えずに男根を咥え、輪姦されるとなれば従順に女性器を差し出す。")
        out.printw(f"それが{name()}という便器の新たな日常であり、性奴隷として課された使命でもあった……")
        out.printl()
        out.printl(f"いつものように“役目”を果たした{name()}は、")
        out.printl("その晩も白濁に沈んだままぴくりとも動けず、精臭にまみれながらぼんやり虚空を眺めていた。")
        out.printl(f"明日も、明後日も、使い潰され故障してしまうまで、{name()}は男達に「使われ」続ける。")
        out.printl(f"悲惨な運命を嘆くだけの力さえ、今や{name()}の中から消え果てようとしつつある……そんな時だった。")
        out.printl()
        out.printl("にわかに男達の様子が慌ただしくなり、外から言い争うような騒ぎ声まで聞こえ始めていた。")
        out.printw(f"外で何が起きているのか理解するだけの意識は、もう{name()}という便器に残っていなかったが――")
        out.printl()
        out.printl("「ここです、早くっ！」")
        out.printl()
        out.printw("聞き覚えのある叫び声と共にドアが破られ、仲間の少女たちが警察と共に地下倉庫へ雪崩れ込む。")
        out.printl(f"仲間たちは一目散に{name()}のもとへ駆け寄り、大粒の涙を流しながら抱き着いてきた。")
        out.printl(f"男達の精液で服が汚れるのも構わず{name()}を固く抱きしめ、")
        out.printl("「よかった」「遅くなってごめん」などと口々に声を掛け続ける少女たち……")
        out.printl("腕から伝わる確かな暖かい感触、久しく向けられていなかった慈しみの感情。")
        out.printl(f"心まで性処理便器になりつつあった{name()}の中に、ヒトとしてのあるべき感情が蘇る。")
        out.printw(f"生気の消えた{name()}の目に、ゆっくりと小さな光が戻り――")
        out.printl()
        out.printl("心から信頼する仲間たちの手で救われ抱き締められた歓び")
        if male():
            out.printl("男達に好き放題尊厳を貶められた一人のヒトとしての悔しさ")
        else:
            out.printl("男達に好き放題尊厳を貶められた一人の女性としての悔しさ")
        out.printl("もう心を殺して輪姦され続ける必要はないのだと理解できた安らぎ")
        out.printl("便器として穢され開発されきった身体を直視しなければならない恐怖")
        out.printl()
        if male():
            out.printl(f"少年一人の許容量を遥かに超える大量の感情が涙と共に溢れ出し、{name()}の視界は再び暗転してゆく。")
        else:
            out.printl(f"少女一人の許容量を遥かに超える大量の感情が涙と共に溢れ出し、{name()}の視界は再び暗転してゆく。")
        out.printl(f"突然意識を失った{name()}に動揺し、慌てて抱き寄せ呼吸を確かめる少女たち。")
        out.printw("警察はそんな彼女ら全員を庇いつつ、その場にいる男を手早く逮捕していった。")
        out.printl()
        out.printl(f"ついで医療班も救援要請に応じて突入し、{name()}を助けてと懇願する少女たちの腕の中、")
        out.printw(f"最も信じられる仲間に抱かれた{name()}は、穏やかな表情で寝息を立て始めていた……")
        out.printl()
        out.set_color("#ffff00")
        out.printl(f" {name()}は仲間たちに救出された。")
        out.reset_color()
        c.cflag[0] = -1  # :518 状態_救出直後
        c.cflag[71] = 0
        c.cflag[72] = 8  # :520 脅迫クールダウン（減らす処理は全 ERB に無い）
        c.cflag[290] = 0
        after_rescued(ctx, st.target)  # :522
    elif c.cflag[70] > 6 and rand(10) < 2 + min(2, div(c.cflag[70] - 6, 2)):  # :523–635 低確率で解放
        out.drawline()
        out.set_bold(True)
        out.printl("拉致監禁・廃棄")
        out.set_bold(False)
        out.printl()
        out.printl("どれくらいの時間が経ったのだろうか…")
        limbless = t(ctx, c, "四肢欠損") > 0
        if limbless:  # :531–548
            out.printw(f"人間オナホールとして残酷に改造された{name()}は、今日も男たちによって蹂躙されていた。")
            out.print("窒息状態が長時間続き、反応がどんどん弱くなっていく")
        else:
            out.printw(f"男達に監禁された{name()}は、今日も")
            out.print(_pd(ctx, ("性処理道具", "性奴隷", "人間便器")))
            out.printw("として乱暴に扱われていた。")
            out.print(_pd(ctx, ("抵抗する気力はとうに失せ、反応も鈍ってきた", "抵抗力を失い、従順に媚びるだけの雌家畜となった",
                                "ただ男の言葉に従い、抵抗する力もない", "目の輝きを失い、ただ無感覚に奉仕するだけの")))
        out.printl(f"{name()}。次第に男性たちは不満を抱き始め、")
        out.printw("臭い、もう飽きた、そろそろ新しい獲物を捕まえよう、などと身勝手な会話を交わしている・・・")
        out.printl()
        out.printl("・・・")
        out.printl(f"それから更に数日後、リーダーの男が“期限切れの”{name()}を「処理」するよう命じた。")
        out.printl(f"男達は{name()}の髪を乱暴に掴むと、強引に担ぎ上げて地下倉庫から持ち去り……")
        # :559 `IF 1==0 && …` はデッドコード（短絡：RAND(10) も評価されない）→ :589 ELSE
        if limbless:  # :592–607
            out.printw(f"もはやヒトの原型を留めていない{name()}を、乱雑にゴミ処分場へ投棄して去っていった。")
            out.printl()
            if male():
                out.printl("……その後、「手足のない少年がゴミ処分場で生き埋めになっている」という恐ろしい通報を受けて急いで現場に駆けつけた付近の婦警により、")
            else:
                out.printl("……その後、「手足のない少女がゴミ処分場で生き埋めになっている」という恐ろしい通報を受けて急いで現場に駆けつけた付近の婦警により、")
            out.printl(f"ゴミの中にほぼ完全に埋もれ、全身打撲傷があり、外界に対する反応はほとんど消えた状態の{name()}が発見された。")
            out.printw(f"その後すぐに情報を察知した仲間たちが現場を引き継ぎに来て、{name()} は正常に「回収」されたのだった・・・")
            out.printl()
            out.set_color("#ffff00")
            out.printl(f" 人間オナホールとして終わりのない拷問を受けた{name()}は基地に送り返されました。")
            out.reset_color()
        else:  # :608–627
            out.printw(f"意識の無い{name()}を、裸のままゴミ捨て場に投げ込み捨て去っていった。")
            out.printl()
            if male():
                out.printl("……その後、「生ゴミ袋の間に裸の少年が埋もれている」との通報を受けて駆け付けた近隣の婦警が、")
                out.printl(f"ゴミに埋もれた少年――アナルに煙草の吸殻や使用済みティッシュを詰め込まれた{name()}の姿を発見した。")
            else:
                out.printl("……その後、「生ゴミ袋の間に裸の少女が埋もれている」との通報を受けて駆け付けた近隣の婦警が、")
                out.printl(f"ゴミに埋もれた少女――膣に煙草の吸殻や使用済みティッシュを詰め込まれた{name()}の姿を発見した。")
            out.printl(f"居合わせた近隣住民の協力もあって{name()}は即座に「回収」され、")
            out.printw("“無事に”仲間たちの元へと運ばれ、送り届けられたのだった・・・")
            out.printw()
            out.set_color("#ffff00")
            out.printl(f" {name()}は監禁から「解放」された。")
            out.reset_color()
        yield from calc_gangbang_kanki(ctx)  # :629
        c.cflag[0] = -1  # :630–632
        c.cflag[70] = 0
        c.cflag[72] = 8
        after_rescued(ctx, st.target)  # :633（:634 LOCAL:999 = 1 は以後使われない）
    else:  # :636–672 監禁継続
        out.drawline()
        out.set_bold(True)
        out.printl(f"拉致監禁：{name()}")
        out.set_bold(False)
        out.printl()
        out.printl(" どれくらいの時間が経ったのだろうか…")
        out.printw(f" 黴臭いビルの地下室に監禁され、{name()}は今も性処理道具として男達に使われている。")
        out.printl()
        # :648 `IF 1==0 && …` はデッドコード → :655 ELSE。:656 SELECTCASE RAND(35) の CASE は全てコメントアウト → CASEELSE
        rand(35)
        yield from intimidation_rape(ctx)  # :668
        c_juel = data.index_of("JUEL", "修練P")
        c.juel[c_juel] += 50 + (rand(20) + 20)  # :670 JUEL:TARGET:修練P += (50 + RAND(20,40))
    return 0


def calc_gangbang_kanki(ctx: Ctx) -> InputGen:
    """`CALL CALC_GANGBANG("監禁",5,2)`（NAKADASHI = 2：AFTER_PILL なし）。"""
    from .battle.rape import calc_gangbang

    return (yield from calc_gangbang(ctx, "監禁", 5, 2))


def intimidation_rape(ctx: Ctx) -> InputGen:
    """`@INTIMIDATION_RAPE, ARG:0`:676–786（ARG:0 は本体で未使用、:678 VARSET LOCAL の LOCAL も未使用）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    a = lambda n: abl(ctx, c, n)  # noqa: E731
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    name = lambda: print_transcallname(st, st.target)  # noqa: E731
    if c.cflag[70] > 2:  # :679–683
        out.printl(f"{name()}は、もはやマスクで顔を隠しすらしない男たちの勃起したペニスを唇に突き付けられている。")
    else:
        out.printl(f"{name()}は、マスクで顔を隠した男たちの勃起したペニスを唇に突き付けられている。")
    if tl("淫乱") and tl("初心") < 1:  # :684–694
        out.printl(f"{name()}は誘惑するように男たちを見上げ、潤んだ上目遣いで奉仕し始めた・・・")
    elif a("欲望") > 3 and tl("初心") < 1:
        out.printl(f"{name()}は心の中で言い訳をしながら、男のペニスに奉仕し始めた・・・")
    elif a("従順") > 3:
        out.printl(f"{data.str_defaults.get(2500, '')}との戦いで身体と心に服従を教え込まれている{name()}は")
        out.printl("鍛錬不足のせいで男たちに抵抗できないのだと心の中で信じ切っている・・・")
    else:
        out.printl(f"薬を飲まされているせいか、力が入らない{name()}は")
        out.printl("碌に鍛錬もしていないであろう男にさえ抵抗することができない・・・")
    out.printw()
    out.printl(f"すると男はそのまま{name()}を組み敷いて、")
    if is_male(data, c):  # :697–717
        if c.cflag[36] <= 40:
            out.print("明らかにオトコ慣れしていないアナルにペニスを捻り込んで、")
        else:
            out.print("アナルに挿入して、")
        out.printl("乱暴にピストンし始めた。")
    elif tl("処女") > 0:
        out.printl("穴という穴を埋め尽くさんばかりに凌辱が始まった。")
        out.printl(f"最も「良い」位置に立っていた男が無造作に{name()}の両脚を掴むと、")
        out.printl("穴を猛々しいペニスで貫いた。")
        out.printl(f"{name()}の絶望的な甘い叫びも気にせず、何度も抜き差しを繰り返す。")
        out.printl("処女の蜜壷からにじみ出る血は優れた潤滑油だった。")
        out.printl("やがて愛液が血液と混ざり合い、押し広げられた秘裂は汁でびしょ濡れになっていった・・・・・・")
        c.talent[data.index_of("TALENT", "処女")] *= -1  # :711
        c.cflag[206] = 12
        out.printl()
        out.printl("処女喪失")
    else:
        out.printl("ヴァギナに挿入し、乱暴にピストンし始めた。")
    out.print(f"{name()}が")  # :718–732
    out.print(_pd(ctx, ("堕ちきった從順な", "必死に媚びた", "淫らに", "淑やかに", "蕩けきった")))
    out.printl("うめき声を上げる中、")
    out.printw()
    if is_male(data, c):  # :735–741
        out.printl("男が限界に登り詰めて直腸内に精液を放出すると、")
    else:
        out.printl("男が限界に登り詰めて当然のように膣内射精を決めると、")
    out.printl("順番待ちをしていた仲間と場所を代わり、すぐに凌辱が再開される。")
    if tl("淫乱") or a("欲望") >= 3:  # :743–762
        out.printl(f"男たちの相手にも慣れてきた{name()}は、")
        out.printl("両手で常に誰かのペニスをしごきながら、手際よく精液を搾り取っていく。")
        out.printl("常にふしだらな蕩け顔を晒し、今では両穴への同時挿入も珍しくはない…。")
    else:
        if c.cflag[0] == _KIDNAPPED or c.cflag[70] > 0:
            out.print("監禁中に何度も調教され、暴力的な支配によって“躾け”られてしまった")
        elif c.cflag[290] > 2:
            out.print("何度も身体を蹂躙された")
        else:
            out.print("男たちの脅迫に逆らえない")
        out.printl(f"{name()}は、")
        if tl("主観視点") > 0:
            out.printl("悔しさに歯を食いしばりながらも、諦めたように奉仕に専念する。")
        else:
            out.printl("悔しさに歯を食いしばりながらも、諦めたように奉仕に専念している。")
    out.printw()
    if c.cflag[0] == _KIDNAPPED:  # :764–780
        out.printl("白濁と欲望をどれくらい受け止めたか分からなくなったころ、")
        out.printl(f"ようやく満足したらしい男達は、既にピクリとも動かない{name()}を冷たい床に打ち捨てた。")
    else:
        out.printl("男たちの白濁と欲望をどれくらい受け止めたのだろうか・・・")
        out.printl(f"{name()}はすっかり諦め、未だに満足する様子を見せない男達に奉仕を続けるしかなかった…")
        out.printl("・")
        out.printl("・")
        out.printl("・")
    out.printw()
    yield from calc_gangbang_kanki(ctx)  # :786
    return 0
