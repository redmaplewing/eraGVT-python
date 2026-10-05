"""エンディング：`ゲーム内_イベント発生/エンディング/ENDING.ERB`（路徑相對 `source/earGVP/ERB/`）。

@ENDING_1（全滅）、@ENDING_4（ソロモードで洗脳／悪堕ち）、@ENDING_5（ソロモードで取り込まれ）。
S27：@ENDING 本体（`ending_gen`）、@ENDING_2（クリア）、@ENDING_3（日数制限超過）、@ENDING_6（呼び出し元なし）、`SCORE.ERB@SCORE`、
エンドレス分岐。S37：通關繼承由 `succession.py` 接續，完成後 BEGIN SHOP。
いずれも最後に `CALL CHANGE_GAMEOVER_MODE` → `FLAG:999 = -998` → `FORCEWAIT` で呼び出し元へ戻り、
ゲームオーバーモード（FLAG:0 = 0：全キャラが陵辱され続けるモード）でそのまま続行する（S12、`docs/wiki/era/flow.md` §9）。
FLAG:999 = -998 は次の `@PRISON`（PRISON.ERB:5–8）で 0 に戻る目印（PRISON のループを :32–33 で打ち切る）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state.constants import GameOption
from .action import Ctx, config_check_maniac, print_callname, print_transname
from .battle.core import t, tc
from .chara_common import is_male, talent
from .era import div

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
    if game_option(st, GameOption.ENDLESS) and _endless_record(ctx, True):  # :266–286（S27）
        out.wait()  # :302 FORCEWAIT
        return
    out.printl("　　ゲームオーバーモードに移行します。")  # :295–297
    out.printw("　（全キャラが凌辱され続け、終わりはありません。飽きたら終了しましょう）")
    out.printl()
    _enter_gameover_mode(ctx)  # :299–302


# --- S27：@ENDING 本体・ENDING_2／3／6・SCORE --------------------------------------------------------------


class SaveGameRequest:
    """`SAVEGAME`（ENDING.ERB:22）：ジェネレータがこれを yield すると、GameSession がセーブ画面（SystemProc@beginSaveGame:782–786
    〜@endCallSaveInfo:926–934）を出し、終わったら（[100] キャンセルでも）`loadPrevState` で続きから再開する。
    EVENTTURNEND 実行中の SystemState は Normal（__CAN_SAVE__ を含む：GameProc/Process.State.cs:76、SystemProc@beginTurnend:609–611）
    なので SAVEGAME は許される（Instraction.Child.cs@SAVELOADGAME_Instruction:1702–1712）。"""


SAVEGAME = SaveGameRequest()

# DIM.ERH:173–184 施設の FLAG:53 ビット
_FACILITY_REFUND = ((1, 500), (2, 12000), (4, 95000), (8, 25800), (16, 50000), (32, 100000), (64, 200000), (128, 500000),
                    (256, 1500000), (512, 4500), (1024, 8500), (2048, 100000))  # ENDING.ERB:45–68
_FACILITY_SCORE = _FACILITY_REFUND[:9]  # SCORE.ERB:392–409（風景画・オブジェ・噴水は数えない）


def ending_gen(ctx: Ctx) -> Generator[object, int, None]:
    """`@ENDING`:3–88。ENDING_2（クリア）→ SCORE →「クリアデータを記録しますか？」→ 施設資金の還元 → `JUMP SUCCESSION`（S37 繼承選單）。
    ENDING_3（日数制限超過）は FLAG:999 = -999 にして戻る（呼び出し側 SHOP_TURNEND.ERB:44–47 がタイトルへ）。"""
    from .opening import game_option
    from .shop import check_gameover
    from .tentacle import enemy_type_check, get_lastboss_phase, tentacle_survive_num

    st = ctx.state
    f = st.flag
    if f[64] > 0:  # :4–5 GOTO START_SUCCESSION
        return (yield from start_succession(ctx))
    if f[100] <= 0 and f[101] <= 0 and not check_gameover(st):  # :9–70
        ending_2(ctx)
        return (yield from _start_score(ctx))
    # :74–85 日数制限超過
    if f[999] == 0 and not check_gameover(st) and not game_option(st, GameOption.NO_TIME_LIMIT):
        alive = tentacle_survive_num(st)
        if enemy_type_check(st, "BOSS") == 1:
            if ((f[3] - alive + 1) * f[2] - st.day[0] + st.day[1]) <= 0 and st.time == 1:
                ending_3(ctx)
        elif get_lastboss_phase(st) >= 1:
            if (f[1] - st.day[0] + st.day[1]) == 0 and st.time == 1:
                ending_3(ctx)
    if f[999] == -997:  # :86–87 GOTO START_SCORE
        return (yield from _start_score(ctx))


def _start_score(ctx: Ctx) -> Generator[object, int, None]:
    """ENDING.ERB:11–69（$START_SCORE〜JUMP SUCCESSION）。"""
    st, out = ctx.state, ctx.out
    st.flag[999] = 0  # :12
    out.reset_bgcolor()  # ENDING.ERB@ENDING:13 RESETBGCOLOR
    st.flag[64] = score(ctx)  # :14–15
    out.printl("クリアデータを記録しますか？")  # :16–18
    out.printl("[0]はい")
    out.printl("[1]いいえ")
    while True:  # :19–28 $INPUT_LOOP_2_0（範囲外は何も出さずに INPUT をやり直す）
        r = yield
        if r == 0:
            yield SAVEGAME
            out.printl()
            break
        if r == 1:
            out.printl()
            break
    return (yield from start_succession(ctx))


def start_succession(ctx: Ctx):
    """ENDING.ERB:29–69 $START_SUCCESSION：施設関係の資金を還元してから `JUMP SUCCESSION, FLAG:64`（引き継ぎ：S37）。
    REPEAT の COUNT は 0 から（Instraction.Child.cs@REPEAT_Instruction）。"""
    st = ctx.state
    f = st.flag
    for count in range(f[50]):  # :32–36
        if count == 0:
            continue
        st.money += 5000 * count + 5000
    for count in range(f[51]):  # :37–41
        if count == 0:
            continue
        st.money += 1000 * count + 1000
    for count in range(f[52]):  # :42–44
        st.money += 10000 * count + 10000
    for bit, yen in _FACILITY_REFUND:  # :45–68
        if f[53] & bit:
            st.money += yen
    from .succession import succession_gen
    return (yield from succession_gen(ctx, f[64]))


def ending_2(ctx: Ctx) -> None:
    """`@ENDING_2`:308–428（ゲームクリア）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    rand = st.rng.rand
    s = data.str_defaults.get(2500, "")
    pc = print_callname(st, st.target)
    l1 = l2 = l3 = 0
    ls1 = ls2 = ""
    out.printl()
    out.printl(f"{s}を完全に殲滅しました！")
    out.printl("この街に平和が戻りました！！")
    for cc in range(st.charanum):  # :317–343
        if cc == 0:  # MASTER（= 0）または 0
            continue
        c = st.charas[cc]
        if c.cflag[0] in (1, 9):
            if ls1 == "":
                ls1 = c.callname
            elif rand(l1 + l2 + l3) == 0:
                ls1 = c.callname
            l1 += 1
        elif c.cflag[0] == 2:
            if ls2 == "":
                ls2 = c.callname
            elif rand(l1 + l2 + l3) == 0:
                ls2 = c.callname
            l2 += 1
        elif c.cflag[0] == 3:
            # :336–340 `IF LOCALS:3 == ""` は常に真（LOCALS:3 はどこでも代入されない）→ 毎回 LOCALS:1 を上書き（原作どおり）
            ls1 = c.callname
            l3 += 1
    out.printw()
    out.printl(_DOTS)
    out.printl()
    out.printl(f"かくして、『{s}』との壮絶な戦いは幕を閉じた。")
    out.printl(f"最後の敵に止めを刺した瞬間、世界中の{s}が次々と動きを止め、")
    out.printl("まるで糸が切れたかのようにその場に倒れ伏していった。")
    out.printl()
    out.printl(f"本体以外の{s}は全て遠隔操作されている生体端末だったとか、")
    out.printl("最大個体が死んだことにより脳波を共有する群体全てがショック死したなど、")
    out.printl("世間で様々な憶測が飛び交ったが、原因は結局よく分からずじまいであった。")
    out.print(f"しかし、{s}の脅威が去ったということを疑う者はいなかった")
    if l2 > 0:  # :355–368
        out.printl("。")
        out.printl()
        out.printl("敵によって操られていた人々も一人またひとりと正気に戻り、")
        out.print(f"洗脳されていた{ls2}")
        if l2 >= 2:
            out.print("たち")
        out.printl("もまた、自分を取り戻すことができた。")
        out.printl()
        out.printl(f"泣いて詫びる{ls2}を{pc}は優しく抱きしめ、")
        out.printl("お互いが生きていることに感謝するのであった・・・")
    else:
        out.printl("・・・")
    out.printw()
    out.printl(_DOTS)
    out.printl()
    out.printl("――決戦から一週間後。")
    out.print(f"戦いを終えた{pc}")
    if l1 + l3 == 0:
        out.print("たち")
    out.printl("は、つかの間の日常を謳歌していた。")
    out.printl("復興に湧く街の大通りは活気で溢れており、人々の顔からは不安の影が消え去っている。")
    if l1 > 0 or l3 > 0:  # :378–393
        out.print("だが、戦いの中で行方不明になった ")
        out.print(f"{ls1} ")
        if l1 + l3 >= 2:
            out.print("たち")
        out.printw("が帰ってくることはなかった・・・")
        out.printl()
        out.print("仲間")
        if l1 + l3 >= 2:
            out.print("たち")
        out.printl("の犠牲があればこそ、")
        out.printl(f"{pc}は勝利することができたのかもしれない。")
        out.printl("――それとも、別の結末が有り得たのだろうか？")
        out.printl()
        out.printl("人々の笑い声がする夕焼けを見ながら、")
        out.printl(f"{pc}はそのことについて思いを巡らせる・・・")
    else:
        out.print(f"その様子を、{pc}")
        if l1 + l3 == 0:
            out.print("たち")
        out.printl("は遠くから眩しそうに見守っていた。")
    out.printl()
    out.printl("戦いが終われば、正義の味方は必要ない。")
    out.print(f"{s}が全滅したいま、自分")
    if l1 + l3 == 0:
        out.print("たち")
    out.printl("もまた、力を捨てる時が来たのだ。")
    out.printw("・・・いや、本当にそうだろうか？")
    out.printl()
    out.printl(_DOTS)
    out.printl()
    out.printl(f"数ヶ月後、そこには再び戦場に立つ{pc}の姿があった。")
    out.printl(_ENDING_2_DATA[rand(len(_ENDING_2_DATA))])  # :411–418 PRINTDATAL
    out.printl("力ある者には責任がある。")
    out.printw(f"人々の平和を脅かす存在がある限り、{pc}の戦いが終わることはない・・・")
    out.printl()
    out.printl(_DOTS)
    out.printl()
    out.printw("　　ＣＯＮＧＲＡＴＵＬＡＴＩＯＮＳ　！！")
    out.printl()
    out.printl("お疲れ様でした")
    out.printl()
    out.wait()  # :428 FORCEWAIT


_ENDING_2_DATA = (
    "南極に突如出現した\"超空間通路\"から、謎の敵が飛来し都市を襲い始めたのだ。",
    "少女たちの欲望を喰らって成長する\"魔女\"と、人知れず死闘を繰り広げているのだ。",
    "一般市民を攫って改造人間を作り出す\"悪の組織\"の存在を見過ごすことはできない。",
    "\"人類の兵器を模倣する謎の敵\"の侵攻を食い止めるべく、新たな特殊組織が結成されたのだ。",
    "月面から飛来する\"新たな脅威\"と、日夜戦い続けているのだ。",
    "太平洋の深海から湧き出る謎の\"怪獣\"たちが、人類の新たな脅威と化していたのだ。",
)


def _endless_record(ctx: Ctx, _unused: bool = False) -> bool:
    """ENDING_1:263–293／ENDING_3:459–489／ENDING_6:707–739 のエンドレス分岐の共通部分。撃破数 >= 8 なら
    `CALL LB`・FLAG:999 = -997 にして True。
    DEVIATION: GLOBAL:114（エンドレス撃破数の歴代記録）の LOADGLOBAL／比較・新記録表示／SAVEGLOBAL は行わない
    （deviations.md「全域資料（GLOBAL）：成就・歷代紀錄不讀不寫」）。ENDLESS はモード選択未移植のため現状到達しない。"""
    from .shop import lb
    from .tentacle import tentacle_survive_num

    st, out = ctx.state, ctx.out
    local = st.flag[3] - tentacle_survive_num(st)
    out.printl(_DOTS)
    out.printl(f"ボス撃破記録　　{local} 体")
    if local >= 8:
        out.printw()
        for w in ("…", "……", "………"):
            out.printw(w)
        lb(out)
        st.flag[999] = -997
        return True
    return False


def ending_3(ctx: Ctx) -> None:
    """`@ENDING_3`:432–498（日数制限超過）。通常は GAME OVER → FLAG:999 = -999（SHOP_TURNEND.ERB:44–47 で RESETDATA・BEGIN TITLE）。"""
    from .akuoti import dot_after
    from .opening import game_option
    from .shop import lb

    st, data, out = ctx.state, ctx.data, ctx.out
    s = data.str_defaults.get(2500, "")
    lb(out)
    dot_after(ctx, 1)
    out.printl()
    out.printw("時間切れです・・・")
    out.printl()
    out.printl(_DOTS)
    out.printl()
    male = is_male(data, tc(ctx))
    if male:
        out.printl(f"{s}との戦いを続ける少年たち。しかし、彼らの行動は遅すぎた。")
    else:
        out.printl(f"{s}との戦いを続ける少女たち。しかし、彼女たちの行動は遅すぎた。")
    out.printl(f"その日、残る全ての{s}が一斉に街に現れ、そして一つの巨大な{s}へと融合していった。")
    out.printl(f"その巨大な{s}からは無数の小さな{s}がとめどなくあふれ出している。")
    out.printl(f"{'少年' if male else '少女'}たちの抵抗もむなしく、瞬く間に街は{s}によって飲み込まれていった・・・")
    out.printl("一人、また一人と力尽き、触手と汚液の奔流に沈んでゆく可憐な花たち。")
    out.printw(f"命運を察した{print_callname(st, st.target)}の頬にも、白濁化粧に混ざって一筋の涙が流れ落ちていた・・・")
    out.printl(" ")  # :458 `PRINTL  `（引数は空白 1 字）
    # :460–497：エンドレスで撃破数 8 以上なら FLAG:999 = -997（スコアへ）、それ以外は GAME OVER（エンドレスは記録表示の後にもう一度区切り線）
    if not (game_option(st, GameOption.ENDLESS) and _endless_record(ctx, False)):
        out.printl(_DOTS)
        out.printl()
        out.printl("　　ＧＡＭＥ　ＯＶＥＲ")
        out.printl()
        out.printw("タイトル画面に戻ります")
        st.flag[999] = -999
    out.wait()  # :498 FORCEWAIT


def ending_6(ctx: Ctx) -> None:
    """`@ENDING_6`:661–749（クズ市民に処刑された全滅エンド）。原作の注釈（:657–659）どおり呼び出し元が無い（全 ERB を grep：
    定義行のみ）デッドコード。移植だけして呼ばない。"""
    from .opening import game_option

    st, data, out = ctx.state, ctx.data, ctx.out
    s = data.str_defaults.get(2500, "")
    c = tc(ctx)
    pc = print_callname(st, st.target)
    out.printl()
    out.printl("全滅した・・・")
    out.wait()
    out.printl(f"最後の魔法少女{pc}は、{s}との戦いで倒れはしなかった。")
    out.printl("クズ市民によって不必要に捕らえられ、監禁され、凌辱され、支配され、")
    out.printw("最終的には家畜のように屠殺された。")
    out.printl()
    out.printl("魔法少女が消えた後も触手の攻撃は止まらず、")
    out.printl("ついには政府や軍も壊滅、社会は完全に崩壊した。")
    out.printw("人々は暴力に走り、本能のままに欲望を満たしてゆく・・・")
    out.printw()
    head = "腕と脚が切り落とされた" if talent(data, c, "四肢欠損") > 0 else ""  # :673 \@ … ? … # \@
    out.printl(f"{head}{pc} の身体は剥製化され、")
    out.printw("ピアスポールに取り付けられたまま、裏社会の秘密の拠点に勝利旗のように掲げられていた。")
    out.printl()
    big = talent(data, c, "巨乳")
    if big >= 5:
        out.printl("膨らんだ乳房があられもなく垂れ下がり、魔法少女の淫らな肉体を見せつける。")
    elif big >= 4:
        out.printl("最期の瞬間がいかに美しかったか物語るように、その豊満な胸が前に突き出される。")
    elif big >= 3:
        out.printl("豊かな乳房と発情したまま最期を迎えた体は、死後もその魅力を保ち続ける。")
    else:
        out.printl("隆起し硬くなった乳首は、死の瞬間の性的興奮を永遠に残している。")
    out.printl("遺体には処刑に立ち会った男らの署名、侮辱的な落書きが連なっていた。")
    out.printl("金属棒で押し開げられ腐敗した淫らな性器が丸見えになり、")
    out.printw(f"「{pc}」は今も生前の白目を剥いた絶頂の表情を保っていた。")
    out.printl(f"{pc}の体を「利用する」男は今も絶えない。")
    out.printl(f"欲望の精液が{pc}に叩き付けられ、地面に流れてゆく。")
    out.printw(f"{pc}の体からはいつも激しい生臭さが漂っている……")
    out.printl("新たな獲物を捕まえるたび、男たちは彼女の死体を見せに行った。")
    out.printl(f"魔法少女{print_transname(st, st.target)}さえもこのような運命にあると知れば、")
    out.printl("獲物はあっさりと従順になる……")
    out.printw("この世界の末路など、もう誰も気にしていない……")
    out.printl()
    out.printl(f"その日、{s}が一斉に街路に出現し、うねり狂いながら巨大な一つの{s}として合体した。")
    out.printl(f"{s}の巨体から中小の{s}が無数に溢れ出し、")
    out.printl(f"瞬く間に街は{s}の津波に飲み込まれてしまった。")
    out.printl("人間の世界が終わった時間だった……")
    out.printl(" ")  # :704 `PRINTL  `
    out.printw(" ")  # :705 `PRINTW  `
    if not (game_option(st, GameOption.ENDLESS) and _endless_record(ctx, True)):
        out.printl("　　ゲームオーバーモードに移行します。")
        out.printw("　（全キャラが凌辱され続け、終わりはありません。飽きたら終了しましょう）")
        out.printl()
        st.flag[0] = 0  # :736–738（CHANGE_GAMEOVER_MODE ではなく直接）
        st.flag[999] = -998
        st.day[2] = st.day[0] * 2 + st.time
    out.wait()  # :749 FORCEWAIT


_SCORE_ABL = (  # SCORE.ERB:156–335：(ABL 名, Lv1〜Lv5 以上の加点)
    ("Ｃ感覚", (1, 2, 3, 4, 5)), ("Ｖ感覚", (2, 4, 6, 8, 10)), ("Ａ感覚", (2, 4, 6, 8, 10)), ("Ｂ感覚", (1, 2, 3, 4, 5)),
    ("従順", (4, 6, 9, 12, 15)), ("欲望", (3, 4, 6, 8, 10)), ("技巧", (3, 4, 6, 8, 10)), ("奉仕精神", (4, 6, 9, 12, 15)),
    ("露出癖", (3, 4, 6, 8, 10)), ("マゾっ気", (3, 4, 6, 8, 10)), ("触手中毒", (7, 10, 15, 20, 25)),
    ("自慰中毒", (6, 8, 12, 16, 20)), ("精液中毒", (6, 8, 12, 16, 20)), ("噴乳中毒", (9, 12, 18, 24, 30)),
    ("射精中毒", (9, 12, 18, 24, 30)),
)
_RANK = {1: "E", 2: "D", 3: "C", 4: "B", 5: "A", 6: "S"}


def _grade_lt(value: int, bounds: tuple[int, ...]) -> int:
    """`IF value < b1 → 1 ELSEIF < b2 → 2 … ELSE 6`。"""
    for i, b in enumerate(bounds):
        if value < b:
            return i + 1
    return 6


def score_values(ctx: Ctx) -> tuple[int, int, int, int, int, int, int]:
    """`@SCORE`:3–461 の評価計算部分。戻り値 (生存, 日数／撃破, 純潔, 性成長, 人気, 資産, 総合)。"""
    from .opening import game_option
    from .shop import charanum_safe
    from .tentacle import tentacle_survive_num

    st, data = ctx.state, ctx.data
    f = st.flag
    solo = game_option(st, GameOption.SOLO)
    exp_i = lambda n: data.index_of("EXP", n)  # noqa: E731
    others = range(1, st.charanum)  # MASTER = 0 を飛ばす
    # :8–64 生存
    if solo and st.charanum < 3:
        y = st.charas[1].exp[exp_i("幽閉経験")]
        l1 = 1 if y >= 5 else 2 if y >= 4 else 3 if y >= 3 else 4 if y >= 2 else 5 if y >= 1 else 6
    else:
        local = 100
        for cc in others:
            st0 = st.charas[cc].cflag[0]
            if st0 == 1:
                local -= div(60, st.charanum - 1)
            if st0 in (2, 3):
                local -= div(30, st.charanum - 1)
            if st0 == 9:
                local -= div(90, st.charanum - 1)
        l1 = _grade_lt(local, (40, 55, 70, 85, 100))
    # :66–111 撃破数／残り日数
    if game_option(st, GameOption.ENDLESS):
        l2 = _grade_lt(f[3] - tentacle_survive_num(st), (10, 15, 20, 40, 50))
    else:
        l2 = _grade_lt(div((f[1] - st.day[0]) * 100, f[2]), (30, 70, 110, 150, 190))
    # :113–146 被姦経験と素質
    local = 0
    for cc in others:
        c = st.charas[cc]
        virgin, pure = talent(data, c, "処女") > 0, talent(data, c, "清純派") > 0
        hikan = c.exp[exp_i("被姦経験")]
        local += hikan if (virgin or pure) else hikan * 2
        if virgin and pure:
            local -= 1
    l3 = 1 if local >= 150 else 2 if local >= 100 else 3 if local >= 50 else 4 if local >= 10 else 5 if local >= 1 else 6
    # :148–362 生存キャラの性能力。DEVIATION: :150 `FOR CCOUNT, O, CHARANUM` の `O` は全作に無い識別子（1.824 では
    # 実行時に IdentifierNotFoundCodeEE で停止：GameProc/Process.ScriptProc.cs:38–42、GameData/IdentifierDictionary.cs:645）。
    # 振り解く判定の `LOCAL:O`（deviations.md）と同じく 0 の誤記として扱う（0 = MASTER は :151 で飛ばすので 1 始まりと同じ）。
    local = 0
    for cc in others:
        c = st.charas[cc]
        if c.cflag[0] != 0:
            continue
        for name, pts in _SCORE_ABL:
            lv = c.abl[data.index_of("ABL", name)]
            if lv >= 1:
                local += pts[min(lv, 5) - 1]
    safe = charanum_safe(st)
    if safe:  # :341–342
        local = div(local, safe)
    l4 = _grade_lt(local, (20, 50, 80, 120, 150))
    # :364–384 人気度
    p = f[853]
    if p <= -10:
        l5 = 1
    elif p < 15:
        l5 = 2
    elif p < 30 or (not solo and p < 30):
        l5 = 3
    elif p < 35 or (not solo and p < 40):
        l5 = 4
    elif p < 40 or (not solo and p < 50):
        l5 = 5
    else:
        l5 = 6
    # :386–437 総資産
    local = st.money * 2
    local += 5000 * (f[50] - 1) + 5000
    local += 1000 * (f[51] - 1) + 1000
    local += 10000 * f[52] + 10000
    for bit, yen in _FACILITY_SCORE:
        if f[53] & bit:
            local += yen
    if solo:
        local *= 3
    for no in range(999):  # :415–418
        if st.item[no]:
            it = data.items.get(no)
            local += it.price if it is not None else 0
    l6 = _grade_lt(local, (100000, 125000, 150000, 175000, 200000))
    l98 = l3 if l3 >= l4 else l4  # :441–445
    total = div(l1 + l2 + l98 + l5 + div(l6, 2) + 3, 5)  # :447
    return l1, l2, l3, l4, l5, l6, total


def score(ctx: Ctx) -> int:
    """`@SCORE`:3–750。`RETURN LOCAL`（総合評価 1〜6）。GLOBAL:110（最高評価）・GLOBAL:100〜102（モード別クリア回数）の
    歷代紀錄 SAVEGLOBAL 留待 W01 後續成果；成就211–213已接共用取得。FLAG:854（周回数）+1。"""
    from .action import _shortline
    from .opening import game_option

    st, out = ctx.state, ctx.out
    solo = game_option(st, GameOption.SOLO)
    endless = game_option(st, GameOption.ENDLESS)
    l1, l2, l3, l4, l5, l6, local = score_values(ctx)
    r = _RANK
    total = r.get(local, "S")  # :449–461（1〜5 以外は S）
    out.printl("*** クリアスコア ***")
    _shortline(out)
    out.printl(f"キャラの生存・・・{r[l1]}")
    out.printl(f"{'ボス撃破数・・・・' if endless else 'クリア日数・・・・'}{r[l2]}")
    if l3 >= l4:
        out.printl(f"キャラの純潔度・・{r[l3]}    キャラの性成長・・{r[l4]}")
    else:
        out.printl(f"キャラの性成長・・{r[l4]}    キャラの純潔度・・{r[l3]}")
    out.printl(f"人気度・・・・・・{r[l5]}")
    out.printl(f"総資産・・・・・・{r[l6]}")
    out.printl()
    out.printl(f"総合評価・・・・・{total}")
    _shortline(out)
    out.printw()
    out.printl("クリアおめでとうございます。")
    out.printl("このコーナーではスコアに対する評価をしていきたいと思います。")
    out.printw()
    for line in _score_comments(st, l1, l2, l3, l4, l5, l6, solo, endless):
        if line is None:
            out.printw()
        else:
            out.printl(line)
    last = st.temp.last_load_version == -1  # LASTLOAD_VERSION == -1（新規開始からセーブ＆ロードなし）
    if local == 1:  # :699–709
        out.printl("ついに…　ついに総合Ｅ評価が出てしまいましたか…")
        out.printl("これを見ているアナタはへっぽこ大魔王を名乗る義務があります。")
        if last:
            out.printl("と思ったら、セーブ＆ロードなし…だと！？")
            out.printl("やるじゃねぇか旦那ァ、見直したぜッ！！！！")
        else:
            out.printl("な…　何かの間違いですよね？　…もしや確信犯ではありませんか？")
        out.printw()
    elif local == 6:  # :710–722
        out.printl("ついに…　ついに総合Ｓ評価が出ましたか！")
        out.printl("これを見ているアナタはGVTマスターを名乗る資格があります。")
        if last:
            out.printl("おまけにセーブ＆ロードなし…だと！？")
            out.printl("そのリセットしない姿勢に感服致します！　おめでとうございます！！！")
        else:
            out.printl("何とも素晴らしい！　おめでとうございます！")
        out.printl()
        out.printl("ブラボーハラショーッ！")
        out.printw()
    elif last:  # :724–729
        out.printl("な、なんと…なんとなんと！！")
        out.printl("アナタ、セーブ＆ロードしてませんね！！")
        out.printl("こいつはぁたまげた！！！")
        out.printl()
        out.printl("そのリセットしない姿勢に感服致します！　おめでとうございます！")
    else:
        out.printl("以上、コメントコーナーでした。役に立つヒントはありましたか？")
        out.printl("ぜひとも次のプレイでまたお会いしましょう！")
    from .achievements import unlock
    if local == 1:
        unlock(ctx, 212, "へっぽこ大魔王")
    elif local == 6:
        unlock(ctx, 213, "eraGVTマスター")
    if last:
        unlock(ctx, 211, "覇者の証")
    out.printw()  # :738
    st.flag[854] += 1  # :749
    return local


def _score_comments(st, l1, l2, l3, l4, l5, l6, solo, endless) -> list[str | None]:
    """SCORE.ERB:487–694 の評価コメント（None = PRINTW の空行＋待ち）。"""
    r = _RANK
    o: list[str | None] = [f"生存評価：{r[l1]}"]
    if solo:
        if l1 <= 3:
            o += ["ソロモードでは幽閉されてもゲームオーバーにならない代わりに、", "幽閉された回数で生存評価が低下してしまいます。",
                  "また、洗脳/悪堕ちするとゲームオーバーになるという", "ソロモード独自の仕様があるので要注意です。"]
        elif l1 <= 5:
            o += ["ソロモードでは一回や二回くらい幽閉されても余裕で脱出できます。", "しかし、Ｓ評価を目指すならば一度も幽閉されずにクリアする必要があります。",
                  "純潔度評価Ｓを目指せば自然と生存評価も良くなるので、同時に目指してみましょう。"]
        else:
            o += ["一度も幽閉されずにクリアできたようですね。", "たった一人でずいぶん大変だったろうと思います。"]
            if l4 >= 3:
                o += ["おまけに性成長評価が高いということは、茨の道を歩んできた証拠。", "そんなアナタに敬礼です。"]
            else:
                o += ["性成長評価を高めようとすると自然と幽閉されるプレイになると思うので、", "生存評価と両立するのはもはや苦行の領域かもしれません。"]
    elif l1 <= 2:
        o += ["苦しい戦いだったかもしれませんが、よく頑張りました。", "体力や気力が減ると命中率や回避率が大きく落ちてしまうので、", "早めに撤退すれば敗北は避けられます。"]
    elif l1 == 3:
        o += ["あらら・・・ずいぶん犠牲者が出てしまったようですね。", "仲間を幽閉したボスは遭遇率がグーンと伸びるので、諦めずに救出に向かいましょう。"]
    elif l1 == 4:
        o += ["一人が捕まったくらいなら、防衛力を維持しながら鍛錬するのも容易いはず。", "戦闘支援を利用すれば撤退しやすくなるので、試しに使ってみては如何でしょう？"]
    elif l1 == 5:
        o += ["洗脳や悪堕ちしてしまった仲間を見捨てていませんか？", "仲間が全員揃っていればクリア評価はＳになるので、もうひと踏ん張りです。"]
    else:
        o += ["全員を無事に生存させたみたいですね。", "実は仲間が捕まってしまうと制限日数が増加するので、", "あえて捕まらせて日数を稼ぐという戦略もあります。", "知ってました？"]
    o.append(None)
    if endless:
        o.append(f"撃破評価：{r[l2]}")
        if l2 <= 2:
            o += ["あまり撃破数が伸びなかったようですね。", "鍛錬するかボスに挑むかのバランスが攻略の鍵です。", "ENDLESSモードではボスのレベルアップが少しだけ遅いので、",
                  "思い切って突撃してみると意外と倒せたりします。"]
        elif l2 == 3:
            o += ["普通にプレイした場合の平均的な撃破数ですね。", "キャラクターにも苦手な相手と得意な相手が居ると思うので、", "どのボスが出現するか等の運の要素も絡んできます。"]
        elif l2 == 4:
            o += ["ENDLESSモードではボス撃破数20を突破すると期限があまり伸びなくなるので、", "この先はひたすら制限日数との戦いになります。",
                  "ここまで来たらキャラ引き継ぎやレベル引き継ぎで最高の戦力を用意して挑みましょう。"]
        elif l2 == 5:
            o += ["素晴らしい撃破数ですが、おしい。", "どんな手段を使ってでも期日を延ばして１体でも多くのボスを撃破しましょう。", "最高評価まではあと一歩です！"]
        else:
            o += ["お見事です。かなり効率的なプレイをしたみたいですね。", "この数のボスを撃破するのは並大抵のことではありません。", "堂々のＳ評価おめでとうございます。"]
    else:
        o.append(f"日数評価：{r[l2]}")
        if l2 == 1:
            o += ["かなりギリギリだったようですね。", "時間を掛け過ぎるとボスのレベルが上がってしまうので、", "慎重になりすぎるのも考えものです。"]
        elif l2 == 2:
            o += ["慎重なプレイスタイルだったみたいですね。", "ラスボスのＨＰはかなり多いので、こまめに削っていくことが重要です。"]
        elif l2 == 3:
            o += ["初見プレイならば標準的な日数でクリアできました。", "より効率的な戦い方もできるので、探してみるのも楽しいですよ？"]
        elif l2 == 4:
            o += ["残り日数を意識してプレイすればこのくらいになるでしょうか。", "鍛錬施設Lvを早めに上げれば、もっと短縮できるはずです。"]
        elif l2 == 5:
            o += ["惜しいところでしたね。", "ボスとうまく遭遇できない場合もあるので、仕方ないかもしれません。"]
        else:
            o += ["お見事です。かなり効率的なプレイをしたみたいですね。", "さらなる記録を目指すのもよし、別の攻略法を試してみるのも良いでしょう。", "ともかく、Ｓ評価おめでとうございます。"]
    o.append(None)
    if l3 >= l4:
        o.append(f"純潔度評価：{r[l3]}　　性成長評価：{r[l4]}")
        if l3 <= 3:
            o += ["エッチなことを避けようとしたのに、犯されてしまったようですね。", "このくらいが正しい楽しみ方をしているとも言います。", "あえてリセットしないそのスタイルは好感に値します。"]
        elif l3 == 4:
            o += ["エッチは回避して進んだものの、油断があったみたいですね。", "処女を守り通したキャラは多少エッチなことをされても", "純潔度が高くなるので、気を付けてみましょう。"]
        elif l3 == 5:
            o += ["かなり頑張りましたが、残念。Ａ評価です。", "一度でも捕まってしまうとＳ評価にはならないので、", "さらに上を目指すには敏捷性特化にする必要があるかもしれません。"]
        else:
            o += ["お見事としか言いようがありません。", "エロゲーでここまで本気で純潔を守ったアナタは立派です。", "堂々のＳ評価、おめでとうございます。"]
    else:
        o.append(f"性成長評価：{r[l4]}　　純潔度評価：{r[l3]}")
        if l4 <= 2:
            o += ["エッチなことを避けようとしたのに、エッチになってしまったようですね。", "開き直ってエロエロなキャラを目指す遊び方もありますよ。"]
        elif l4 in (3, 4):
            o += ["そこそこエッチな娘（たち）になってしまったようですね。", "このくらいが正しい楽しみ方をしているとも言います。", "どうせならもっとエロい娘を目指して、自分から捕まっちゃいましょう。"]
        elif l4 == 5:
            o.append("かなりヤられちゃいましたね。")
            if solo:
                o += ["キャラが捕まると期限が延びるので、わざと幽閉されて日数を稼ぐ", "マッチポンプ戦法もオススメです。"]
            else:
                o += ["キャラが捕まると期限が延びるので、「救出」コマンドを利用した", "マッチポンプ戦法もオススメです。"]
        else:
            o += ["すごい事になってますね。", "わざと捕まったりしなければこの評価にはならないと思うので、", "お楽しみ頂けたようで何よりです。", "ともかく、Ｓ評価おめでとうございます。"]
    o.append(None)
    o.append(f"人気度評価：{r[l5]}")
    if l5 == 1:
        o += ["もしかして防衛力のことを完全に忘れていませんか？", "ずっと出撃や防衛をせずに放置すると触手による侵攻が進んでしまいます。", "また、何度も繰り返し戦闘で敗北すると、フォローが利かなくなります。"]
    elif l5 == 2:
        if solo:
            o += ["ソロモードでは防衛力の管理が簡単なので、", "人気度の維持をすること自体は難しくないはず。", "まずはボスに敗北せずにクリアすることを目指しましょう。"]
        else:
            o += ["ヒーローとしてはまずまずの評価です。", "ボスに苦戦して、何度か敗北してしまったのではないでしょうか？", "やられるくらいなら撤退した方が良いので、戦闘では引き際が肝心です。"]
    elif l5 == 3:
        o += ["特に意識せずにプレイしていてもこの程度にはなるでしょう。", "人気度は変動しにくい数値なので、", "なるべく低下させないように心がけると、自然と上昇していくはずです。"]
    elif l5 == 4:
        o += ["ただ触手を倒すだけでは真の英雄とは呼べません。", "ここからさらに上を目指すには、市民たちに親しみを覚えてもらう必要がありそうです。",
              "アルバイトをしてみたり、あとは…アイドルとして活動してみると、", "応援してくれる人が増えるかもしれません。"]
    elif l5 == 5:
        o += ["なかなか順調にプレイが進んだようですね。", "リセットなしでここまで来れれば、", "大分このゲームを攻略できていると言えそうです。"]
    elif endless:
        o += ["残念ながら、ENDLESSモードでは触手に勝つことはできません。", "せめて正義の味方たちが苦しまずに最期を迎えられたことを祈るばかりです。"]
    else:
        o += ["この評価ということは、正義の味方らしく街を守りきったのですね。", "恐らくあなたたちに感謝している人々も多いはず。", "おめでとうございます、あなたは正真正銘の英雄です！"]
    o.append(None)
    o.append(f"資産評価：{r[l6]}")
    if l6 <= 2:
        o += ["お金のことを意識せずにプレイすればこんなものでしょう。", "資産評価は現金のほうが好評価になるので、", "あえて使わずに取っておくべきかもしれません。"]
    elif l6 in (3, 4):
        # :673–684 `PRINT なかなかのお金持ちですね。` の後に PRINTFORML で同じ行
        o.append("なかなかのお金持ちですね。" + ("Ｃ評価です。" if l6 == 3 else "Ｂ評価です。"))
        o.append("戦力に余裕があるならバイトしてみるのも手です。")
        o.append("特に知力の高いキャラは研究助手をするのが良いでしょう。" if l6 == 3 else "無駄な買い物を控えれば、もっと好評価になるでしょう。")
    elif l6 == 5:
        o += ["かなりの大金持ちですね。ここまで来たらＳ評価を目指しましょう。", "アイドル稼業って最初は辛いけれども、", "有名になればなるほど稼げる…　ハズです。"]
    else:
        o += ["ワンダフル！　これだけのお金を貯めるとは！", "あえてお金を使わず取っておいたりなど、苦労されたかと思います。", "そんなあなたに惜しみない賛辞を。素晴らしいです！"]
    o.append(None)  # :694
    return o
