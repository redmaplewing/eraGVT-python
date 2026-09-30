"""エンディング：`ゲーム内_イベント発生/エンディング/ENDING.ERB`（路徑相對 `source/earGVP/ERB/`）。

@ENDING_1（全滅）、@ENDING_4（ソロモードで洗脳／悪堕ち）、@ENDING_5（ソロモードで取り込まれ）。
いずれも最後に `CALL CHANGE_GAMEOVER_MODE` → `FLAG:999 = -998` → `FORCEWAIT` で呼び出し元へ戻り、
ゲームオーバーモード（FLAG:0 = 0：全キャラが陵辱され続けるモード）でそのまま続行する（S12、`docs/wiki/era/flow.md` §9）。
FLAG:999 = -998 は次の `@PRISON`（PRISON.ERB:5–8）で 0 に戻る目印（PRISON のループを :32–33 で打ち切る）。
"""

from __future__ import annotations

from .action import Ctx, config_check_maniac, print_callname
from .battle.core import t, tc
from .chara_common import is_male

_DOTS = "・" * 66


def _gameover(ctx: Ctx) -> None:
    out = ctx.out
    out.printl()
    out.printl(_DOTS)
    out.printl()
    out.printw("　　ＧＡＭＥ　ＯＶＥＲ")
    out.printl()
    out.printl("　　ゲームオーバーモードに移行します。")
    out.printw("　（全キャラが凌辱され続け、終わりはありません。飽きたら終了しましょう）")
    out.printl()
    _enter_gameover_mode(ctx)


def _enter_gameover_mode(ctx: Ctx) -> None:
    """ENDING_1:299–302／ENDING_4:560–563／ENDING_5:651–654：`CALL CHANGE_GAMEOVER_MODE`、`FLAG:999 = -998`、`FORCEWAIT`
    （スキップで省略できない WAIT：reference/emuera-1824/Emuera/GameProc/Function/BuiltInFunctionCode.cs:52、
    FunctionIdentifier.cs:198 `new WAIT_Instruction(true)`）。"""
    from .shop import change_gameover_mode

    change_gameover_mode(ctx.state)
    ctx.state.flag[999] = -998
    ctx.out.wait()


def ending_4(ctx: Ctx) -> None:
    """`@ENDING_4`:503–564。PRINTDATA は RAND:件数 で 1 件を改行なしで出す
    （reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:171–185、:202–231）。"""
    st, out = ctx.state, ctx.out
    rand = st.rng.rand
    s = ctx.data.str_defaults.get(2500, "")
    pc = print_callname(st, st.target)
    out.printl()
    out.printw("希望は失われました・・・")
    out.printl()
    out.printl(_DOTS)
    out.printl()
    out.printl(f"かくして、『{s}』に対抗しうる唯一の存在であった{pc}は闇へと飲まれた。")
    if t(ctx, tc(ctx), "触手の虜") > 0:  # :510–527
        out.printl("与えられる快楽にその身も心も捧げ、本来の使命を忘れて自ら異形たちの尖兵となり果てたのだ。")
        out.printl(f"{pc}という司令塔を手に入れた『{s}』は組織的に人々を襲うようになり、")
        out.printl(f"『{s}』の群れを率いて街を襲っては虐殺と欲望の限りを尽くす{pc}は")
        out.print("人類の裏切り者")
        out.print(("\"魔装の", "\"触装の", "\"淫装の", "\"淫獄の", "\"魔獄の")[rand(5)])
        out.print(("悪魔\"", "隷姫\"", "妖姫\"", "隷嬢\"", "妖花\"")[rand(5)])
    else:  # :528–544
        out.printl("望まずとも身体が勝手に動き、異形たちの意のままに操られる肉人形となり果てたのだ。")
        out.printl(f"{pc}の知識を吸収した『{s}』は組織的に人々を襲うようになり、")
        out.printl(f"感情も見せずに同じ人間をためらいなく殺戮していく{pc}は")
        out.print("人類の裏切り者")
        out.print(("\"魔装の", "\"触装の", "\"魔獄の")[rand(3)])
        out.print(("悪魔\"", "隷姫\"", "隷嬢\"", "隷花\"")[rand(4)])
    out.printw("として恐れられるようになる・・・")
    out.printl()
    out.printw("そして、人類という種が滅亡することは、このときに既に決まっていたのだった・・・")
    _gameover(ctx)


def ending_5(ctx: Ctx) -> None:
    """`@ENDING_5`:568–655。"""
    st, out = ctx.state, ctx.out
    s = ctx.data.str_defaults.get(2500, "")
    pc = print_callname(st, st.target)
    out.printl()
    out.printw("希望は失われました・・・")
    out.printl()
    out.printl(_DOTS)
    out.printl()
    out.printl(f"かくして、『{s}』に対抗しうる唯一の存在であった{pc}は肉壁の奥へと沈んだ。")
    out.printl()
    out.printl("……急激に数を増した強大な触手生物を前に人類は成すすべなく蹂躙され、")
    out.printl("都市インフラの維持すらまもなく不可能となった。")
    out.printl()
    out.printl("かつて自宅、学校、市街地だった場所で、数多くの女性が触手に犯され続けていた。")
    out.printl("暴力的な快感に正気を失ったかのごとく喘ぐ女性、終わらぬ凌辱に涙も悲鳴も枯れ果てた女性……")
    out.printl("彼女らが辿る悲惨な運命は、それでも触手の巣へと連れ去られた\"花嫁\"たちのそれに比べれば可愛いものだった。")
    out.printl("少なくとも「ヒトとして生きてはいる」のだから……")
    out.printw()
    out.printl(_DOTS)
    out.printl()
    if config_check_maniac(st, 14) > 0:  # :587–591
        out.printl("薄暗い触手洞窟の奥深く。年若き少女たちが手脚を失った状態で肉壁に固定され、あらゆる穴を蹂躙されていた。")
    else:
        out.printl("薄暗い肉の洞窟の奥深く。年若き少女たちが壁に手足を埋め込まれ、穴という穴を蹂躙されていた。")
    out.printl("狂ったように卵子を排出する卵巣、挿入された触手のストロークに合わせて潮を噴き続ける膣穴…")
    out.printl("苗床として造り替えられた子宮、全身を循環する高濃度の媚液、脊髄から指先まで張り巡らされた快楽神経…")
    out.printl("雌としてのすべてがヒトとしての脳を裏切り、鈍らせ、侵し、尊厳までも蕩けさせてゆく。")
    out.printw()
    out.printl("ほんの僅かばかり前までは学校に通い、友人らと笑い合い、恋に悩む普通の少女であったはずの「それ」らは、")
    out.printl("華やかな人生、日常を奪われた理由も分からぬまま、今では臨月の妊婦より膨らんだ腹部を痙攣させて揺れ動いていた。")
    out.printl("最早「それ」らは触手の巣に属する苗床に過ぎず、二度と少女としての生には戻れぬ哀れな繁殖器官だった…")
    out.printl()
    if is_male(ctx.data, tc(ctx)):  # :601–618
        out.printl(f"オトコである{pc}もまた、例外ではなかった。")
        out.printl("その力か、容姿か、なにを触手達が気に入ったのかはわからないが、")
        out.printw(f"{pc}は他のオトコ達とは違って、特別な肉体改造を施されていた。")
        out.printl()
        out.printl("ペニスは不必要だとばかりに縮み上がり、もはや勃起することもできずに薄い精液を力なく垂れ流し続けている。")
        out.printl("代わりに、微かに膨らんだ胸の頂にある肥大化した乳首からは、")
        out.printl("真っ白な母乳が射精のような勢いで断続的に噴き出して、触手の子達に降り注いでいた。")
        out.printl()
        out.printl(f"その触手の子達は、まぎれもなく{pc}が孕んで産み落とした子ども達だ。")
        out.printl("直腸の奥に触手の子だけを孕むことのできる苗床子宮を造られてしまい、")
        out.printl("アナルを抉る野太い触手に種付けされるか、ボテ腹を抱えながらアナルから触手の子どもをひり出すか。")
        out.printw(f"常に繁殖に使われ、もう{pc}の尻穴が閉じることはなかった…")
        out.printl()
    else:  # :619–641
        out.printl(f"力尽きた{pc}もまた、例外ではなかった。")
        out.printl("その力か、女性として類い稀なほどの容姿か、なにを触手達が気に入ったのかはわからないが…")
        out.printw(f"もはや抵抗のかなわぬ{pc}は、特に念入りに肉体改造を施されていた。")
        out.printl()
        out.printl(f"肥大化した{pc}の双丘では頂で乳首が嬲られて痛ましいまでに腫れあがり、")
        out.printl("拡張された乳腺からは白濁した母乳がごぼごぼと断続的に噴き出し、触手の子達へと降り注ぎ続けた。")
        out.printl()
        out.printl(f"…その触手の子達は、まぎれもなく{pc}が孕んで産み落とした子ども達だ。")
        out.printl("開ききった雌穴から垂れ下がる“へその緒”は一本残らず異形の触手達に直結され、")
        out.printw(f"孕み袋として生まれ変わった{pc}の新たな現実を示していた。")
        out.printl()
        out.printl("乳房の内部や直腸の奥、果ては子宮の奥や喉にまで……")
        out.printl(f"肉体改造によって全身に苗床子宮を造られた{pc}は、疑う余地もなく特上の孕み袋だった。")
        out.printl(f"{pc}本来の子宮も、壊造された苗床子宮も、種付けを繰り返す触手にとっては何ら違いが無い。")
        out.printl(f"繁殖袋にされた{pc}の「雌穴」は触手で満たされ、一秒たりとも閉じることがない。")
        out.printl()
        out.printl(f"耕され、抉り殺され、ボテ腹を抱えながらイキ果てては、穴という穴から触手をひり出す{pc}。")
        out.printl("広がりきった全ての「雌穴」からは、とめどなく溢れる愛液に混じって無数の“へその緒”が垂れ下がる。")
        out.printl("見る影もない無様な表情で出産と絶頂だけを繰り返す、触手専用の繁殖袋…")
        out.printw("触手専用の哀れな苗床少女に、もう人類の希望だった頃の…ヒトであった頃の面影は無い。")
        out.printl()
    out.printl("人類という種の滅亡は、このときに既に決まっていたのだった。")
    out.printl("だがヒト未満の存在と化した孕み袋たちにとって、人類の命運などはもう知る由も無い。")
    out.printw(f"嬌声だけが鳴り響く絶望の宴の中で、今日も{pc}たちは触手を産み落とし続けるのだ……")
    _gameover(ctx)


def ending_1(ctx: Ctx) -> None:
    """`@ENDING_1`:93–304（全滅 ED）。`BATTLE_TRAIN_AFTER.ERB@EVENTEND`:527–528 から TARGET = 最後の敗北者で呼ばれる。

    PRINTFORM（改行なし）の連続は 1 行になり、`PRINTL` で改行、`PRINTW` は空行＋入力待ち。
    """
    from .action import print_transcallname
    from .battle.core import is_manly
    from .opening import game_option
    from ..state.constants import GameOption

    st, data, out = ctx.state, ctx.data, ctx.out
    s = data.str_defaults.get(2500, "")
    pc = print_callname(st, st.target)
    male = is_male(data, tc(ctx))
    boy = "少年" if male else "少女"

    def para(*parts: str) -> None:
        for p in parts:
            out.print(p)
        out.printl()
        out.printw()

    out.printl()
    out.printl("全滅しました・・・")
    out.wait()  # :96 FORCEWAIT
    if not is_manly(ctx):  # :98–99 SIF ISMANLY() GOTO SKIP
        out.printl(_DOTS)  # :100
        out.printl()
        para(f"　『{s}』との戦いに仲間たちが一人また一人と敗北していく中、それでも",
             f"最後まで戦い続けていた{pc}だったが、その抵抗もついに途絶えることとなる日が訪れた。")  # :102–105
        para(f"　相手が最後の“敵”であることを知っているかのように、{pc}を囲んだ",
             f"{s}の群れはぐったりとした{'少女然とした' if male else '少女の'}身体を代わる代わるに弄り出した。",
             f"　戦闘が決着した時にはまだ多少なりとも残っていた{pc}の衣服は完全に",
             "破られ、間もなくして手首や襟元にほんの僅かな名残を留めるだけになってしまった。")  # :106–117
        out.printl(_DOTS)
        out.printl()
        para(f"　全裸よりも扇情的な姿になった{pc}に四本の触手が巻きつき、四肢を",
             f"大の字に開かせていく。かすかに呻き声を上げた{boy}には、まだ意識が戻る",
             f"様子はない。だが少しして息苦しさのためか、{boy}は小さく口を開いた。")  # :120–136
        para("　その瞬間、唇と唇の隙間を掻き分けて肉色をした太い触手が入り込んだ。",
             f"　口腔内に太く硬い肉質を押し込まれ、{pc}は苦鳴を洩らす。",
             f"　しかし触手の動きは止まることなく、{pc}のさらに奥深くへと侵入していった。",
             f"　{boy}は異物感にえずきながら、止めようのない涙を零しはじめた。")  # :137–148
        para(f"　それがきっかけになったのだろうか、それまで思い思いに{pc}の身体を",
             f"弄くっていた触手達が、先を争うように{pc}の孔という孔へと先端を押し",
             f"付け出した。{'陰茎の鈴口' if male else '秘裂'}やアヌス、口腔は言うにおよばず、鼻腔や耳穴、さらには",
             f"涙腺にまで、{pc}の身体を触手で埋め尽くそうというように無数の触手が蠢きはじめた……。")  # :149–160
        out.printl(_DOTS)
        out.printl()
        para(f"　{pc}の尿道口に差し込まれていた触手が、ドリル状に回転しつつ緩やか",
             f"に抜き取られていく。黄金色の液体をだらしなく撒き散らす{pc}の足元に",
             f"は、それからの数時間で行なわれた陵辱を表すように、{'精液' if male else '愛液'}と小水で出来た水溜まりが幾つも生まれていた。")  # :163–173
        para(f"　{boy}の表情からはもはや正気が完全に失われ、今やここに居るのは人々を",
             f"守ろうとしていた健気な{boy}ではなく、{s}に与えられる淫欲と被虐の虜に堕ちた、肉の苗床だという事は明白だった。")  # :174–189
        para(f"　数え切れないほど繰り返し貫かれ、限界以上に拡張された{pc}の{'' if male else '秘裂と'}",
             "アヌスへ、また何本かの触手が絡み合いながら入っていく。",
             f"　{pc}は{'少女然とした' if male else '少女の'}見た目には似合わないほどの嬌声を上げ、快楽に自ら腰を",
             f"くねらせた。{s}と{boy}の肉の饗宴はそのまま、空が白み始めるまで続くのだった……")  # :190–213
        out.printl(_DOTS)
        out.printl()
        para(f"　……だが、夜が明けても{pc}が解放されることはなかった。",
             f"　陽の光から逃げるかのように{s}が影の中へ沈み始めた時、{pc}が目に",
             f"したのは――{pc}と同じように{s}と戦い、そして敗北して取り込まれた少女達の裸身だった。")  # :216–220
        ls = ["", "", "見知らぬ苗床魔法少女"]  # :221–235
        for i in range(1, st.charanum):
            if i != st.target and st.charas[i].cflag[0] != 9:
                if ls[0] == "":
                    ls[0] = print_transcallname(st, i)
                elif ls[1] == "":
                    ls[1] = print_transcallname(st, i)
                elif ls[2] == "":
                    ls[2] = print_transcallname(st, i)
                    break
        if ls[1] != "":  # :236–243
            out.printl(f"　妖しく淫らに微笑みながら自ら触手に奉仕する{ls[0]}")
            out.printl(f"　悲壮な泣き顔で許しを請いながら必死に腰を振る{ls[1]}")
            out.printl(f"　内臓まで突き上げられて絶叫しながら瞳を見開く{ls[2]}")
            out.printl()
        else:
            out.printl("　禁悦に犯された瞳、妖しい淫らな微笑み、娼婦のように揺れる腰……")
        out.print("　まるで恋人に寄り添うように触手を愛撫する彼女達の腹部は大きく膨らみ、")  # :244–246
        out.printw(f"{s}の“種”を孕んでいることが一見してわかった。")
        out.printl()
        para(f"　{pc}へと手を伸ばす少女達の姿を前に、",
             f"自分も「ああなる」のだと、{pc}は最後の思考で理解していた……")  # :247–250
        out.printl(_DOTS)
        out.printl()
        out.printl(f"　　その後、{boy}達がどうなったかを知るものは……to be continued ?")  # :253–259
        out.printw()
    # $SKIP :261–304
    if game_option(st, GameOption.ENDLESS):
        raise NotImplementedError("エンドレスモードの全滅（ENDING_1:266–）は未移植")
    out.printl("　　ゲームオーバーモードに移行します。")  # :295–297
    out.printw("　（全キャラが凌辱され続け、終わりはありません。飽きたら終了しましょう）")
    out.printl()
    _enter_gameover_mode(ctx)  # :299–302
