"""娘の出産と子供の加入：`ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB`（`@GROW_HANTEI`:4–27、`@BIRTH_DAUGHTER_TENTACLE_ORIGIN`:53–272、
`@ADD_CHILD`:278–1107、`@CHILD_GROW_1`:1113–1145、`@CHILD_GROW_2`:1150–1205、`@RESCUE_CHILD`:1210–1299）と
`ヒロイン関連/PREGNANT_CHILD_BIRTH_N.ERB@BIRTH_DAUGHTER_HUMAN_ORIGIN`:6–198。路徑相對 `source/earGVP/ERB/`。
（`@TRAINING_HOSEI_CHILD`:32–47 は S04 で `eragvt.game.action.training_hosei_child` に移植済み。）

INPUT を含むのでジェネレータ。S35：名前の手入力は Web 文字輸入を待つ。
キャラ設定画面（一人称・プロフィール）は `eragvt.game.firstsetting` の「何も変えずに決定」を使う。

Emuera 語意：
- `ADDCHARA 0` は CSV 番号 0 のキャラを末尾に追加（reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs@AddCharacter:1026）、
  `DELCHARA` は後ろを詰める（同 DelCharacter）。
- 関数内 `#DIM`（PAPA_POWER など）は static（GameProc/UserDefinedVariable.cs:27）。VARSET LOCAL の対象外。
- FOR の終端は開始時に評価（GameProc/Function/Instraction.Child.cs:1731–1743）。GROW_HANTEI で ADD_CHILD が
  TARGET を新キャラに変えた後、同じ周回の :16–25（性徴）は **新キャラ** に対して行われる（原作どおり）。
- `&&`／`||` は短絡評価（GameData/Expression/OperatorMethod.cs:524–555）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state import GameState
from ..state.constants import REGISTER_MAX, CharaState, GameOption
from .action import Ctx, print_callname
from .battle.core import exp, mark, run_chinobun, t, tc
from .battle.ninsin import _dot_after, pregnancy_belly_expand
from .body import AGE, REAL_AGE, chara_size_default, generate_bodyline, set_profile
from .chara_common import is_female, is_male, level_status, seikaku_check, syuzoku_check
from .era import div
from .input_request import inputs, input_number
from .opening import game_option
from .party import recover_to_party
from .shop import charanum_safe, check_gameover

InputGen = Generator[None, int, None]

AISURU_HITO, DAREMO, KINSHIN, NOZOMANAI = -3, -1, -2, -4  # DIM.ERH:254–257
_PAPA_POWER = ("ADD_CHILD:PAPA_POWER", 0)  # #DIM PAPA_POWER（static）


def _T(ctx: Ctx, name: str) -> int:
    return ctx.data.index_of("TALENT", name)


def _str(ctx: Ctx, i: int) -> str:
    return ctx.data.str_defaults.get(i, "")


def _draw_str(ctx: Ctx, width: int, base: int, retry_width: int | None = None) -> str:
    """`LOCAL = RAND:w + b / WHILE STR:LOCAL == "" / LOCAL = RAND:w' + b / WEND`。"""
    rand = ctx.state.rng.rand
    i = rand(width) + base
    while _str(ctx, i) == "":
        i = rand(retry_width or width) + base
    return _str(ctx, i)


# 名前の言語 → (RAND の幅, 基点)：ADD_CHILD:341–405／BIRTH_DAUGHTER_TENTACLE_ORIGIN:183–231
_NAME_LANG = {99: (4000, 12000), 0: (500, 12000), 1: (1000, 12500), 2: (500, 13500), 3: (1000, 14000),
              4: (500, 15000), 5: (500, 15500)}


def _random_given_name(ctx: Ctx, lang: int, add_child: bool) -> str | None:
    """名前のランダム生成。該当しない入力は None（GOTO INPUT_LOOP_CHILD_NAME_RANDOM）。
    ADD_CHILD 版（add_child=True）は [6] 中国語と「日本語＋男性 → STR:18000〜（中性的な名前）」がある。"""
    if add_child and lang == 0 and is_male(ctx.data, tc(ctx)):  # :350–357
        return _draw_str(ctx, 500, 18000)
    if add_child and lang == 6:  # :400–414
        name = _draw_str(ctx, 500, 16500, 1000)
        if ctx.state.rng.rand(2):
            name += _draw_str(ctx, 500, 16500, 1000)
        return name
    if lang in _NAME_LANG:
        w, b = _NAME_LANG[lang]
        return _draw_str(ctx, w, b)
    return None


def _ask_random_name(ctx: Ctx, add_child: bool, sex: str | None) -> Generator[None, int, str]:
    """$INPUT_CHILD_NAME_YN 〜 名前の決定（隨機生成或手輸入）。"""
    out = ctx.out
    while True:  # $INPUT_CHILD_NAME_YN
        out.printl("キャラの名前を自分で決めますか？" + (f"（性別：{sex}）" if sex is not None else ""))
        out.printl("[0]いいえ（ランダム生成）")
        out.printl("[1]はい（手動入力）")
        r = yield from input_number(ctx)
        if r == 0:
            while True:  # $INPUT_LOOP_CHILD_NAME_RANDOM
                out.printl("[0]日本語で構成")
                out.printl("[1]英語で構成")
                out.printl("[2]フランス語で構成")
                out.printl("[3]ドイツ語で構成")
                out.printl("[4]イタリア語で構成")
                out.printl("[5]ロシア語で構成")
                if add_child:
                    out.printl("[6]中国語で構成")
                out.printl("[99]完全ランダム")
                lang = yield from input_number(ctx)
                name = _random_given_name(ctx, lang, add_child)
                if name is not None:
                    return name
        elif r == 1:
            while True:
                out.printl("キャラの名前を入力してください")
                name = yield from inputs(ctx)
                if name != "":
                    return name
        else:
            out.printl("正しい数値を入力してください")


# --- 出産（人間相手：PREGNANT_CHILD_BIRTH_N.ERB）---------------------------------------------------------

_KOUSAI = {1: "片思いの相手", 2: "大好きな恋人", 3: "将来を誓ったフィアンセ", 4: "愛する夫", 5: "今は無き夫"}


def message_birth_daughter_human_origin(ctx: Ctx) -> None:
    """`地の文/MESSAGE_NINSIN.ERB@MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN`:712–742。

    :731／:734 の `CFLAG:TARGET:226`（子供の性別）の代入は `narration/hooks.py` の NINSIN_HOOK_LINES。
    catalog が使えないときは本文を佔位にして :729 の RAND:2 と代入だけを行う。"""
    def fallback() -> None:
        tc(ctx).cflag[226] = 0 if ctx.state.rng.rand(2) == 0 else 1

    run_chinobun(ctx, "MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN", fallback=fallback)


def _gave_up_line(ctx: Ctx, c) -> str:
    """:163–171／:183–191 子供を手放す文。"""
    papa, k = c.cflag[230], c.talent[800]
    if papa == NOZOMANAI:
        return "熟考の末、子供を施設に預けて忘れることにしました。"
    if (papa == AISURU_HITO and k == 2) or (papa != KINSHIN and k == 3):
        return "熟考の末、子供は彼の実家に預けることにしました。"
    if k == 4:
        return "熟考の末、子供は夫が自宅で育てることになりました。"
    return "熟考の末、子供に別れを告げて施設に預けることにしました。"


def birth_daughter_human_origin(ctx: Ctx) -> InputGen:
    """`@BIRTH_DAUGHTER_HUMAN_ORIGIN`:6–198：人間の子を出産。病院（CFLAG:0 == 10）なら $10000 で育てるかの INPUT。"""
    from .battle.ablup import ablup
    from .pregnancy import abl_up_birth

    st, out = ctx.state, ctx.out
    c = tc(ctx)
    me = st.target
    c.cflag[99] += 45 + div(pregnancy_belly_expand(ctx, me), 20)  # :10
    c.cflag[222] = 0  # :11–14
    c.cflag[227] = 0
    c.cflag[228] = 0
    c.talent[_T(ctx, "妊娠")] = 0
    out.drawline()  # :16–19
    out.set_bold(True)
    out.printl(f"出産（{print_callname(st, me, 1)}）")
    out.set_bold(False)
    if c.cflag[0] != CharaState.BEFORE_BIRTH:  # :21–26 幽閉中の出産
        run_chinobun(ctx, "MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN_PRISON")
        if c.cflag[230] == AISURU_HITO:
            c.cflag[219] += 1
    else:  # :28–195 病院で出産
        message_birth_daughter_human_origin(ctx)
        _dot_after(ctx)
        out.printl()
        out.printl(f"数時間後、病室に戻された{print_callname(st, me)}は")
        out.printl("自分の腕の中の小さな赤ん坊を見つめながら思案に暮れていた…")
        out.printw()
        pn = print_callname(st, me)
        locs = ""
        k = c.talent[800]  # TALENT:交際相手
        if k > 0 and c.cflag[218] == 0 and exp(ctx, c, "出産経験") == 0:  # :38–53
            locs = _KOUSAI.get(k, "愛しい ”あの人” ")
        papa = c.cflag[230]
        if papa <= -100:  # :55–86
            for cc in range(st.charanum):
                if cc == GameState.MASTER or cc == me:
                    continue
                o = st.charas[cc]
                if o.cflag[240] == papa * -1 - 100:
                    out.printl(f"それは、{pn}と{o.callname}の子だった。")
                    if locs != "":
                        out.printl(f"{o.callname}とは知らない仲でこそないが、{locs}に対する{pn}の裏切りである事は違いない。")
                        out.printl()
                    if k == 2:
                        out.printl("付き合っている彼に本当のことは明かしていない。")
                        out.printl("それに、この子をどうするべきかもまだ決めていなかった…")
                    elif k == 3:
                        out.printl("婚約者の彼に本当のことは明かしていない。")
                        out.printl("もちろん、相手の両親には彼との子だと説明はしてあるが、")
                        out.printl("この子をどうするべきか、正直まだ迷っている…")
                    elif k == 4:
                        out.printl("愛する夫に本当のことは明かしていない。")
                        out.printl("自分の子供だと信じて疑わない彼を前に、ついに真実を言い出せなかった。")
                        out.printl("夫は自分一人でも子供を育てるつもりだと言っているが…")
                    elif o.cflag[0] == 0:
                        out.printl(f"見舞いに来た{o.callname}は二人で一緒に育てようと言ってくれたが、")
                        out.printl("どうするべきなのだろうか…")
                    else:
                        out.printl("触手との戦いを続けながら子供を育てるのは困難だ。")
                        out.printl("危険を避けるためにも安全な場所に預けるべきなのではないだろうか…？")
        elif papa == DAREMO:  # :87–111
            if locs != "":
                out.set_color((255, 96, 96))
                out.printl(f"{locs}の子供を産む\"初出産\"の機会が永久に失われた事実を、{pn}は嫌でも理解してしまう。")
                out.reset_color()
                out.printl()
            if k == 2:
                out.printl("付き合っている彼に本当のことは明かしていないが、それは行きずりの相手との子だった。")
                out.printl("当然と言うべきか、彼には子供を育てる意志はまったく無いようで")
                out.printl("話し合ってもなおこの子をどうするか決めかねている…")
            elif k == 3:
                out.printl("婚約者の彼に本当のことは明かしていないが、それは行きずりの相手との子だった。")
                out.printl("相手の両親には何とかそれらしい説明をしたが、罪悪感が心に重くのしかかる。")
                out.printl("話し合いの結果、子供は婚約者の元で預かってくれると言ってくれたが…")
            elif k == 4:
                out.printl("愛する夫に本当のことは明かしていないが、それは行きずりの相手との子だった。")
                out.printl("重く鈍い岩塊のような罪悪感に打ち明けて楽になりたい気持ちで一杯になったが")
                out.printl("心の底から嬉しそうにしている夫の顔を見ると、どうしても言い出せなくなってしまう。")
                out.printl("夫は自分一人でも子供を育てるつもりだと言っているが…")
            else:
                out.printl("それはどこの誰とも知れない、行きずりの相手との子だった。")
                out.printl("子供に愛情を感じないわけではないが、触手との戦いのことを考えると、")
                out.printl("この子を手放した方が良いのではないかという考えが浮かんでは消える…")
        elif papa == KINSHIN:  # :112–115
            out.printl("だがそれは近親相姦によって産まれた禁忌の子だった。")
            out.printl("このことは誰にも、子供本人にすら言えないという罪悪感を飲み込みながら、")
            out.printl(f"{c.callname}はこれから育児をどうするべきか悩み続けた…")
        elif papa == AISURU_HITO:  # :116–132
            c.cflag[219] += 1
            if k == 2:
                out.printl("それは付き合っている彼との愛の結晶だった。")
                out.printl(f"しかし{pn}が自分で育児するには不都合が大きく、何より危険だということで")
                out.printl("話し合いの結果、子供は彼の実家で預かってくれると言うのだが…")
            elif k == 3:
                out.printl("それは婚約者の彼との愛の結晶だった。")
                out.printl("未婚ながら子供が生まれたことを相手の両親は喜んでくれて、")
                out.printl("もし良ければ子供は彼の実家で預かってくれると言うのだが…")
            elif k == 4:
                out.printl("それは正真正銘、愛する夫との愛の結晶だった。")
                out.printl(f"{pn}としても出来るだけ自分の手で子供を育てたい気持ちだが")
                out.printl(f"夫は自分一人でも育てる覚悟だと{pn}に言ってくれた。")
                out.printl("家族三人で抱き合い、束の間の水入らずに心が温まる気持ちだ…")
        elif papa == NOZOMANAI:  # :133–142
            out.printl("それは望まぬ性交を強要されて、無理やり孕まされた子だった。")
            if locs != "":
                out.set_color((255, 96, 96))
                out.printl(f"{locs}の子供を産む\"初出産\"の機会が永久に失われた事実を、{pn}は嫌でも理解してしまう。")
                out.reset_color()
                out.printl()
            out.printl("子供に罪はないが、正直なところ母親らしい愛情を抱けるか自信がない。")
            out.printl("ましてや使命のことを考えると、自分で育てるのは難しいように思える…")
        out.printw()  # :144
        if st.money >= 10000 and st.charanum < REGISTER_MAX + 1:  # :145–176
            out.printl("しばらくして新生児の遺伝子検査の結果が伝えられた。")
            out.printl("幸か不幸か、この子には非常に高い潜在能力が秘められていることが分かったらしい。")
            out.printl("政府に$10000を支払えば、人工的に成長を促進させて育児の負担を小さくすることができるが、")
            out.printl(f"その代わり、子供は{pn}と同じく触手と戦う道を歩むことになるだろう。")
            out.printw()
            out.printl("我が子に過酷な運命を課してまで、手元に置いておくべきだろうか？")
            out.printl()
            out.printl("[0]いいえ")
            out.printl(f"[1]はい（所持金:${st.money}）")
            while True:  # $INPUT_CHILD_CRADLE
                r = yield
                if r == 1:
                    st.money -= 10000
                    out.printl("やはり、母親の居ない子供にしてしまうわけにはいかない。")
                    run_chinobun(ctx, "MESSAGE_CHILD_CRADLE")
                    c.cflag[0] = CharaState.CHILDCARE
                    break
                if r == 0:
                    out.printl(_gave_up_line(ctx, c))
                    recover_to_party(ctx, me)
                    break
                out.printl("正しい数値を入力してください")
        else:  # :177–194
            if st.charanum >= REGISTER_MAX + 1:
                out.printl("（これ以上仲間を増やせないので選択肢を省略します）")
            elif st.money < 10000:
                out.printl("（資金不足なので選択肢を省略します）")
            out.printl(_gave_up_line(ctx, c))
            if c.cflag[0] == CharaState.BEFORE_BIRTH:
                recover_to_party(ctx, me)
    abl_up_birth(ctx, 1)  # :197
    ablup(ctx, 1)  # :198


# --- 出産（触手の子種の娘：育児機能 ON）---------------------------------------------------------------


def birth_daughter_tentacle_origin(ctx: Ctx) -> InputGen:
    """`@BIRTH_DAUGHTER_TENTACLE_ORIGIN`:53–272（CONFIG_CHECK_OTHER_F(0)「触手の子種からも娘を妊娠する」ON のときのみ）。"""
    from .battle.ablup import ablup
    from .pregnancy import abl_up_birth

    st, out = ctx.state, ctx.out
    c = tc(ctx)
    me = st.target
    c.cflag[99] += 45 + div(pregnancy_belly_expand(ctx, me), 20)  # :56
    out.drawline()
    out.set_bold(True)
    out.printl(f"出産（{print_callname(st, me, 1)}）")
    out.set_bold(False)
    if t(ctx, c, "繁殖袋"):  # :63–71
        out.printl(f"{print_callname(st, me, 1)}は何も知覚しないまま子供を産み落とした…。")
    elif t(ctx, c, "四肢欠損"):
        out.printl(f"{print_callname(st, me, 1)}は苦しみながら子供を産み落とした……")
    elif c.cflag[0] != CharaState.BEFORE_BIRTH:
        run_chinobun(ctx, "MESSAGE_BIRTH_DAUGHTER_TENTACLE_ORIGIN_PRISON")
    else:
        run_chinobun(ctx, "MESSAGE_BIRTH_DAUGHTER_TENTACLE_ORIGIN")
    abl_up_birth(ctx, 1)  # :73–74
    ablup(ctx, 1)
    for k in (221, 222, 227, 228, 232, 233):  # :77–83
        c.cflag[k] = 0
    c.talent[_T(ctx, "妊娠")] = 0
    solo = game_option(st, GameOption.SOLO)
    if c.cflag[0] == CharaState.BEFORE_BIRTH:  # :86–119 病院で出産
        if st.money >= 5000 and st.charanum < REGISTER_MAX + 1 and not solo:
            out.drawline()
            out.printl("娘が産まれた")
            out.printl("娘を育てるためには養育費として$5000かかります")
            out.printl("娘を育てますか？")
            out.printl()
            out.printl("[0]いいえ")
            out.printl(f"[1]はい（所持金:${st.money}）")
            r = yield
        else:
            if solo:
                pass
            elif st.charanum >= REGISTER_MAX + 1:
                out.printl("（これ以上仲間を増やせないので選択肢を省略します）")
            elif st.money < 5000:
                out.printl("（資金不足なので選択肢を省略します）")
            elif t(ctx, c, "繁殖袋") or t(ctx, c, "四肢欠損"):
                out.printl("（子育て可能な状態ではないため選択肢を省略します）")
            r = 0
        while True:
            if r == 1:
                st.money -= 5000
                run_chinobun(ctx, "MESSAGE_CHILD_CRADLE")
                c.cflag[0] = CharaState.CHILDCARE
                break
            if r == 0:
                run_chinobun(ctx, "MESSAGE_CHILD_ASLYM")
                recover_to_party(ctx, me)
                break
            out.printl("正しい数値を入力してください")
            r = yield  # GOTO INPUT_CHILD_CRADLE（:95 のラベルは INPUT の直前）
    elif c.cflag[0] in (1, 2, 3):  # :122–270 幽閉中／陥落済み
        if st.charanum < REGISTER_MAX + 1 and c.cflag[22] == 0:
            out.drawline()
            out.printl("娘が産まれた")
            pn = print_callname(st, me)
            if c.cflag[0] == 1:
                if check_gameover(st) or solo:
                    out.printl("いずれ助け出すチャンスは巡ってくるかもしれないが、触手の脅威がある限りは難しいだろう。")
                    out.printl(f"我が子を救う以前に、唯一の希望たる{pn}自身すら今は囚われの身なのだから……")
                elif not solo and charanum_safe(st):
                    out.printl(f"今の{pn}にはどうすることもできないが、")
                    out.printl("仲間が娘を救出してくれるかもしれない。")
                else:
                    out.printl(f"今の{pn}にはどうすることもできないが、")
                    out.printl("いつか誰かが助けてくれるかもしれない。")
            elif c.cflag[0] == 2:
                if t(ctx, c, "主観視点") > 0:
                    out.printl(f"{pn}の胸の奥底にはまだ微かに我が子を思う心が残っている……")
                else:
                    out.printl(f"虚ろな瞳のまま反応を示さないように見える{pn}だが、")
                    out.printl("その胸の奥底にはまだ微かに我が子を思う心が残っているようだ……")
            elif c.cflag[0] == 3:
                if t(ctx, c, "主観視点") > 0:
                    out.printl(f"{pn}は甘えるような声で触手に\"娘を育てたい\"と懇願した……")
                else:
                    out.printl(f"{pn}は甘えるような声で触手に\"娘を育てたい\"と懇願している。")
                    out.printl("闇に堕ちた身であっても我が子は愛しいようだ。")
            if check_gameover(st) or solo:  # :154–155
                pass
            else:  # :157–267
                out.printl("無事を祈って名前を付けてあげますか？")
                out.printl()
                out.printl("[0]いいえ")
                out.printl("[1]はい")
                while True:  # $INPUT_CHILD_PRAYER
                    r = yield
                    if r == 1:
                        while True:
                            name = yield from _ask_random_name(ctx, add_child=False, sex=None)
                            out.printl(f"キャラの名前は 『{name}』 でよろしいですか？")
                            out.printl("[0]いいえ")
                            out.printl("[1]はい")
                            while True:  # $INPUT_CHILD_NAME_YN_1
                                r2 = yield
                                if r2 in (0, 1):
                                    break
                            if r2 == 1:
                                c.cstr[11] = name
                                c.cflag[22] = c.cflag[21]
                                break
                        run_chinobun(ctx, "MESSAGE_CHILD_PRAYER")
                        break
                    if r == 0:
                        run_chinobun(ctx, "MESSAGE_CHILD_GIVEUP")
                        break
                    out.printl("正しい数値を入力してください")


# --- 育児（GROW_HANTEI）・加入（ADD_CHILD）・性徴 ------------------------------------------------------


def grow_hantei(ctx: Ctx) -> InputGen:
    """`@GROW_HANTEI`:4–27：育児中（CFLAG:0 == 11）・幽閉された娘の成長待ち（CFLAG:22 > 0）の日数（CFLAG:224）、
    子供の性徴（CFLAG:225）。"""
    st = ctx.state
    saved = st.target
    n = st.charanum  # FOR の終端は開始時
    for cc in range(n):
        st.target = cc
        c = tc(ctx)
        if c.cflag[0] == CharaState.CHILDCARE or c.cflag[22] > 0:  # :10–15
            c.cflag[224] += 1
            if (c.cflag[224] >= 4 and st.rng.rand(2) == 0) or c.cflag[224] >= 10:
                yield from add_child(ctx, st.target)
        c = tc(ctx)  # ADD_CHILD 後の TARGET は新キャラ（:309）
        if t(ctx, c, "性徴停滞") > 0:  # :16–25
            pass
        elif c.cflag[225] > 14:
            child_grow_2(ctx)
            c.cflag[225] = 0
        elif c.cflag[225] == 7:
            child_grow_1(ctx)
            c.cflag[225] += 1
        elif c.cflag[225] > 0:
            c.cflag[225] += 1
    st.target = saved


_COLORS = ("赤", "緑", "青", "黄", "紫", "橙", "桃")


def add_child(ctx: Ctx, arg: int) -> InputGen:
    """`@ADD_CHILD, ARG`（ARG = 母親の index）:278–1107：子供を新キャラとして加入させる。"""
    from .firstsetting import (
        feat_select_ui, nanori, set_feat_default, size_setting_default, trans_after_callname,
        trans_after_name, trans_call,
    )
    from .relation import check_all_relation
    from .self_call_setting import selfcall_gen
    from .tentacle import tentacle_bitvalue, tentacle_survive_check

    st, data, out = ctx.state, ctx.data, ctx.out
    rand = st.rng.rand
    m = st.charas[arg]
    papa_chara = 0  # :287
    out.printl()
    out.printl()
    if m.cflag[0] == CharaState.CHILDCARE:  # :291–305
        out.printl(f"{print_callname(st, arg)}の子供が異常な速度で育ち、十分に闘えるようになりました。")
    elif m.cflag[22]:
        if tentacle_survive_check(st, tentacle_bitvalue(st, m.cflag[22])) > 0:
            out.printl(f"{print_callname(st, arg)}の子供が異常な速度で育ち、幼児期を終えました。")
        else:
            out.printl(f"{print_callname(st, arg)}と生き別れた子供は、ついに見つかりませんでした……。")
            m.cstr[11] = ""
            m.cflag[22] = 0
            m.cflag[224] = 0
            return
    st.add_chara(data, 0)  # :306
    st.flag[8] += 1
    st.charas[st.charanum - 1].cflag[240] = st.flag[8]
    st.target = st.charanum - 1  # :309
    me = st.target
    c = tc(ctx)
    c.cflag[7] = m.cflag[240]
    if m.cflag[226] > 0:  # :312–317
        c.talent[_T(ctx, "オトコ")] = 1
        sex = "♂"
    else:
        sex = "♀"
    m.cflag[226] = 0
    # :322–505 名前
    if m.cstr[11] == "":
        while True:
            given = yield from _ask_random_name(ctx, add_child=True, sex=sex)
            l2 = m.cstr[10]  # :433–443 母姓／父姓
            l3 = m.cstr[10]
            if m.cflag[230] <= -100:
                for cc in range(st.charanum):
                    if cc == GameState.MASTER:
                        continue
                    if st.charas[cc].cflag[240] == m.cflag[230] * -1 - 100:
                        l3 = st.charas[cc].cstr[10]
            out.printl(f"キャラの名前は 『{given}』 でよろしいですか？")
            out.printl("[0]いいえ")
            out.printl("[1]はい")
            while True:  # $INPUT_CHILD_NAME_YN_1
                r = yield
                if r in (0, 1):
                    break
            if r == 1:
                break
        if l2 != "" or l3 != "":  # :452–492
            out.printl("キャラのフルネームを決めてください。")
            out.printl("・" * 53)
            out.printl(f"[0]{given} (苗字なし)")
            if l2 != l3:
                out.printl()
                out.printl("母姓")
            out.printl(f"[1]{l2} {given}")
            out.printl(f"[2]{given} {l2}")
            if l2 != l3:
                out.printl()
                out.printl("父姓")
                out.printl(f"[3]{l3} {given}")
                out.printl(f"[4]{given} {l3}")
            while True:  # $INPUT_LOOP_CHILD_NARABI
                r = yield
                if r == 0:
                    c.name, c.cstr[10] = given, ""
                elif r == 1:
                    c.name, c.cstr[10] = f"{l2} {given}", l2
                elif r == 2:
                    c.name, c.cstr[10] = f"{given} {l2}", l2
                elif r == 3 and l2 != l3:
                    c.name, c.cstr[10] = f"{l3} {given}", l3
                elif r == 4 and l2 != l3:
                    c.name, c.cstr[10] = f"{given} {l3}", l3
                else:
                    continue
                break
            c.callname = given
        else:
            c.name = given
            c.callname = given
    else:  # :497–505 幽閉された娘
        c.cstr[10] = m.cstr[10]
        c.name = m.cstr[11]
        c.callname = m.cstr[11]
        c.cflag[20] = st.flag[10]
        c.cflag[21] = m.cflag[22]
    if rand(20) == 0 or is_male(data, c):  # :508–514（|| は短絡：RAND:20 が先）
        c.cflag[8] = 25 + rand(3) if rand(2) == 0 else 30 + rand(3)
    # :515 單次 CALL；99提交、98取消後皆續行，不插入共用角色主選單。
    yield from selfcall_gen(ctx, me)
    # :523–532 種族（母親の最後の種族素質を CFLAG:231 に記録）
    for k in range(201, 250):
        if m.talent[k] > 0:
            c.cflag[231] = k
    if data.names["TALENT"].get(c.cflag[231], "") == "ロボっ子":
        c.talent[_T(ctx, "人間")] = 1
    else:
        c.talent[c.cflag[231]] = 1
    race = syuzoku_check(c)  # :534–535
    # ERB/ヒロイン関連/CHARA_SYUZOKU.ERB@SYUZOKU_CHECK:5–24 的 RETURN 覆寫一人稱回傳值。
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023。
    st.result[0] = race
    pn = print_callname(st, me)
    out.printl(f"{pn}の種族は『{data.names['TALENT'].get(race, '')}』です")
    out.printl("フィートを設定しますか？")
    out.printl("[0]はい")
    out.printl("[1]いいえ")
    out.printl("[2]ランダムに設定する")
    while True:  # $INPUT_LOOP_0
        r = yield
        if r == 0:
            yield from feat_select_ui(ctx, me, race)
        elif r == 1:
            out.printl(f"{pn}にはフィートを設定しません")
            out.printw()
        elif r == 2:
            set_feat_default(ctx, me, race)
            set_profile(data, c, st.result)  # :635
            out.printl("ランダムにフィートを設定しました")
            out.printw()
        else:
            continue
        break
    # :643–667 変身能力・服
    if m.cflag[22] > 0:
        c.talent[_T(ctx, "変身能力")] = -1
        c.cflag[40] = 0
        c.cflag[42] = 0
    else:
        c.cflag[40] = 100
        c.cflag[42] = 300
        c.cflag[10] = m.cflag[10]
        c.cflag[11] = m.cflag[11]
        if t(ctx, m, "人間") == 1:
            if rand(4) != 0:
                c.talent[_T(ctx, "変身能力")] = 1
                c.cflag[41] = 200
        elif rand(4) == 0:
            c.talent[_T(ctx, "変身能力")] = 1
            c.cflag[41] = 200
    if t(ctx, c, "変身能力") == 1:  # :668–685
        out.printl(f"{pn}には変身能力が付きました")
        yield from trans_after_name(ctx, me)
        if c.cflag[2] == 1:
            c.cflag[3] = 1
            yield from trans_after_callname(ctx, me)
        yield from trans_call(ctx, me)
        yield from nanori(ctx, me)
    if is_female(data, c):  # :686–693
        c.talent[_T(ctx, "処女")] = 1
    c.talent[_T(ctx, "パイパン")] = 1
    c.talent[_T(ctx, "未熟")] = 1
    for k in range(4):  # :697–699 生まれたては鈍感
        c.talent[101 + k * 2] = 1
    papa = m.cflag[230]
    c.cflag[9] = papa  # :701
    pp = st.temp.locals.get(_PAPA_POWER, 0)
    bits = {1: "Ｃ", 2: "Ｖ", 3: "Ａ", 4: "Ｂ"}
    if papa in bits:  # :704–726
        part = bits[papa]
        c.talent[_T(ctx, f"{part}敏感")] = 1
        c.talent[_T(ctx, f"{part}鈍感")] = 0
        pp = 10
        c.relation[me] = c.relation[me] | (1 << papa)  # SETBIT RELATION:TARGET:TARGET, Ｘ触手（DIM.ERH:245–248）
    elif papa == 5:  # :728–731
        c.abl[data.index_of("ABL", "マゾっ気")] = 3
        pp = 10
        c.relation[me] = c.relation[me] | (1 << 5)
    elif papa == 6:
        c.abl[data.index_of("ABL", "露出癖")] = 3
        pp = 10
        c.relation[me] = c.relation[me] | (1 << 6)
    elif papa == 7:
        c.abl[data.index_of("ABL", "奉仕精神")] = 3
        pp = 10
        c.relation[me] = c.relation[me] | (1 << 7)
    elif 100 <= papa < 200:  # :743–756 ラスボス系
        c.talent[_T(ctx, "Ｃ敏感")] = 1
        if is_female(data, c):
            c.talent[_T(ctx, "Ｖ敏感")] = 1
        c.talent[_T(ctx, "Ａ敏感")] = 1
        c.talent[_T(ctx, "Ｂ敏感")] = 1
        for part in ("Ｃ", "Ｖ", "Ａ", "Ｂ"):
            c.talent[_T(ctx, f"{part}鈍感")] = 0
        pp = 15
        c.relation[me] = c.relation[me] | (1 << 0)  # 血統不明 = 0
    elif papa >= 200:  # :758–759
        pp = 1
    elif papa <= -100:  # :761–776
        papa_chara = 0
        for cc in range(st.charanum):
            if cc == GameState.MASTER:
                continue
            if st.charas[cc].cflag[240] == papa * -1 - 100:
                papa_chara = cc
        h = t(ctx, st.charas[papa_chara], "変身能力")
        pp = 6 if h == 1 else (2 if h == -1 else 4)
    elif papa <= -1:  # :778–779
        pp = 0
    else:  # :780–783（PAPA_POWER は前回の値のまま）
        out.printl("父親不明!?")
        out.printl(f"触手番号{papa}が父親です")
    if is_male(data, c):  # :786–793
        if t(ctx, c, "Ｖ敏感") > 0:
            c.talent[_T(ctx, "Ｃ敏感")] = 1
            c.talent[_T(ctx, "Ｃ鈍感")] = 0
        c.talent[_T(ctx, "Ｖ敏感")] = 0
        c.talent[_T(ctx, "Ｖ鈍感")] = 0
    mb = m.base
    if pp > 0:  # :796–803
        c.base[50] = div(mb[50] * 6, 10) + 15 * pp + rand(40 * pp)
        c.base[51] = div(mb[51] * 6, 10) + 15 * pp + rand(40 * pp)
        c.base[52] = div(mb[52] * 6, 10) + 3 * pp + rand(4 * pp)
        for k in (10, 11, 12, 13):
            c.base[k] = max(100, div(mb[k] * 6, 10) + 3 * pp + rand(4 * pp))
    elif pp < 0:  # :804–812
        pp *= -1
        c.base[50] = div(mb[50] * 6, 10) - 15 * pp - rand(40 * pp)
        c.base[51] = div(mb[51] * 6, 10) - 15 * pp - rand(40 * pp)
        c.base[52] = div(mb[52] * 6, 10) - 3 * pp - rand(4 * pp)
        for k, lo in ((10, 10), (11, 10), (12, 10), (13, 80)):
            c.base[k] = max(lo, div(mb[k] * 6, 10) - 3 * pp - rand(4 * pp))
    else:  # :813–821
        c.base[50] = div(mb[50] * 6, 10)
        c.base[51] = div(mb[51] * 6, 10)
        c.base[52] = div(mb[52] * 6, 10)
        for k in (10, 11, 12, 13):
            c.base[k] = max(100, div(mb[k] * 6, 10))
    st.temp.locals[_PAPA_POWER] = pp
    c.maxbase[0] = c.base[50]  # :823–825
    c.maxbase[1] = c.base[51]
    c.maxbase[2] = c.base[52]
    from .action import seikaku_hosei
    from .opening import _csvbase

    sk = seikaku_check(data, c)  # :828–834 子供の基礎値を記録
    c.cflag[60] = c.maxbase[0] - seikaku_hosei(sk, 0, _csvbase(data, c.no, 0))
    c.cflag[61] = c.maxbase[1] - seikaku_hosei(sk, 1, _csvbase(data, c.no, 1))
    c.cflag[62] = c.maxbase[2] - seikaku_hosei(sk, 2, _csvbase(data, c.no, 2))
    for k in (10, 11, 12, 13):
        c.cflag[63 + k - 10] = c.base[k] - seikaku_hosei(sk, k, _csvbase(data, c.no, k))
    for k in (0, 1, 2):  # :837–846
        c.base[k] = c.maxbase[k]
    for k in (50, 51, 52, 10, 11, 12, 13):
        c.maxbase[k] = c.base[k]
    level_status(data, st, me)  # :847
    if papa == 5:  # :849–867 性格
        if rand(4) == 0:
            c.talent[_T(ctx, "臆病")] = 1
        elif rand(3) == 0:
            c.talent[_T(ctx, "乱暴者")] = 1
        else:
            c.talent[rand(18) + 10] = 1
    elif papa == 6:
        if rand(4) == 0:
            c.talent[_T(ctx, "恥ずかしがり屋")] = 1
        elif rand(3) == 0:
            c.talent[_T(ctx, "古風")] = 1
        else:
            c.talent[rand(18) + 10] = 1
    else:
        c.talent[rand(18) + 10] = 1
    sk = seikaku_check(data, c)  # :869–880
    l1 = l2 = 0
    for k3 in range(7):
        l1 = k3 + 7 if k3 > 2 else k3
        l2 = c.base[l1]  # :876 補正前の値
        c.base[l1] = seikaku_hosei(sk, l1, l2)
        c.maxbase[l1] = c.base[l1]
    l3 = 7  # FOR LOCAL:3, 0, 7 の終了後は 7。LOCAL:1〜3 は :951–1023 の色の決定まで引き継がれる
    m221 = m.cflag[221]  # :883–894 精液中毒
    if m221 != 0:
        lv = 1 if m221 < 10 else 2 if m221 < 25 else 3 if m221 < 75 else 4 if m221 < 200 else 5
        c.abl[data.index_of("ABL", "精液中毒")] = lv
    if is_female(data, c):  # :898–905
        c.talent[_T(ctx, "貧乳")] = 1
    c.talent[_T(ctx, "濡れにくい")] = 1
    c.talent[_T(ctx, "回復早い")] = 1
    c.talent[_T(ctx, "小柄")] = 1
    if rand(5) == 0:  # :908–917 距離の得意・不得意
        l2 = rand(3)
        c.talent[180 + l2 * 2] = 1
    if rand(5) == 0:
        l2 = rand(3)
        if c.talent[180 + l2 * 2] != 1:
            c.talent[181 + l2 * 2] = 1
    blood = data.index_of("MARK", "血族補正")
    c.mark[blood] = mark(ctx, m, "血族補正") + 1  # :919
    c.cflag[225] = 1  # :921
    s = lambda i: _str(ctx, i)  # noqa: E731
    c.cstr[12] = s(30000 + rand(9))  # :925–931 髪型
    c.cstr[13] = s(30100 + rand(15))
    if t(ctx, c, "変身能力") > 0:
        c.cstr[14] = c.cstr[13]
        if rand(4) == 0:
            c.cstr[14] = s(30100 + rand(15))
    # :935–945 色を両親から継承（LOCAL:30〜37 に継承フラグ）
    inherit: dict[int, int] = {}
    pc = st.charas[papa_chara]
    for k in range(30, 38):
        if m.cflag[34] > 0 or (papa_chara > 0 and pc.cflag[34] > 0 and rand(2) == 0):
            c.cstr[k] = m.cstr[k]
            inherit[k] = 1
        elif papa_chara > 0 and pc.cflag[34] > 0:
            c.cstr[k] = pc.cstr[k]
            inherit[k] = 1
        else:
            inherit[k] = 0
    for k in range(30, 36):  # :951–1023
        if k == 30:
            l1 = rand(4)
            l2 = rand(7)
        elif k == 31:
            if l1 == 0 and rand(4) == 0:
                l1 = rand(4)
                l2 = rand(7)
        elif k == 32:
            l1 = rand(4)
            l2 = rand(7)
        elif k == 33:
            if l1 == 0:
                l1 = 1 if rand(3) == 0 else 0
            else:
                l1 = rand(3)
                l2 = rand(7)
        elif k == 34:
            l1 = rand(4)
            if c.cstr[32] == c.cstr[33]:
                if l1 == 0:
                    l2 = rand(7)
                    l3 = l2
            else:
                l1 = 9
        elif k == 35:
            if l1 == 9:
                l1 = 9
            elif l1 == 0:
                l2 = l3
                if rand(3) == 0:
                    l2 = rand(7)
            elif rand(3) == 0:
                l2 = rand(7)
        if inherit[k] != 1:
            l1 = 0
        if l1 == 0 and 0 <= l2 <= 6:
            c.cstr[k] = _COLORS[l2]
    if rand(4) == 0 or m.cflag[34] == 0:  # :1026–1040 肌の色
        if rand(4) == 0:
            skin = "黒"
        elif rand(3) == 0:
            skin = "褐色"
        elif rand(2) == 0:
            skin = "色白"
        else:
            skin = "肌色"
        c.cstr[36] = c.cstr[37] = skin
    c.base[AGE] = rand(5) + 6  # :1042–1046
    c.maxbase[AGE] = c.base[AGE]
    chara_size_default(data, c, st.result)
    c.base[REAL_AGE] = 0
    if rand(12) == 0:  # :1049–1073 パーソナリティ
        np = 1
    elif rand(6) == 0:
        np = 2
    else:
        np = 3
    if np > 0:
        while True:
            c.cstr[40] = s(30500 + rand(500))
            if not (c.cstr[40] == "" or c.cstr[40] == "CSTR:41" or c.cstr[40] == "CSTR:42"):
                break
    if np > 1:
        while True:
            c.cstr[41] = s(30500 + rand(500))
            # :1065 3 項目は `CSTR:40 == "CSTR:42"`（原作どおり）
            if not (c.cstr[41] == "" or c.cstr[41] == "CSTR:40" or c.cstr[40] == "CSTR:42"):
                break
    if np > 2:
        while True:
            c.cstr[42] = s(30500 + rand(500))
            if not (c.cstr[42] == "" or c.cstr[42] == "CSTR:40" or c.cstr[42] == "CSTR:41"):
                break
    if c.cflag[34] == 0:  # :1076–1078
        generate_bodyline(st, data, c)
    size_setting_default(ctx, me)
    if m.cflag[0] == CharaState.CHILDCARE:  # :1083–1092
        out.printl(f"{print_callname(st, arg)}は育児を終了しました。通常状態に復帰します")
        out.printl(f"{print_callname(st, me)}が組織に加入しました")
        out.printl()
        recover_to_party(ctx, arg)
        m.cflag[224] = 0
        recover_to_party(ctx, me)
        check_all_relation(ctx)
    elif m.cflag[22] > 0:  # :1093–1106
        out.printl(f"{print_callname(st, me)}は種付けの対象として認識されたようです。")
        out.printl(f"{print_callname(st, me)}は幽閉されました・・・")
        out.printw()
        c.cflag[0] = CharaState.IMPRISONED
        m.cstr[11] = ""
        m.cflag[22] = 0
        m.cflag[224] = 0
        c.cflag[6] = -1
        check_all_relation(ctx)


def child_grow_1(ctx: Ctx) -> None:
    """`@CHILD_GROW_1`:1113–1145：一次性徴。"""
    from .body import chara_size_default as csd

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    rand = st.rng.rand
    out.printl()
    out.set_bold(True)
    out.printl("一次性徴")
    out.set_bold(False)
    pn = print_callname(st, st.target)
    out.printl(f"{pn}は成長して体質が変わった")
    if t(ctx, c, "未熟") == 1:
        out.printl(f"{pn}は射精できるようになった" if is_male(data, c) else f"{pn}は妊娠できるようになった")
        c.talent[_T(ctx, "未熟")] = 0
    out.printw()
    if rand(4) == 0:  # :1131–1132
        c.talent[_T(ctx, "パイパン")] = 0
    for k in range(4):  # :1135–1138
        if rand(100) < 80:
            c.talent[101 + 2 * k] = 0
    n = rand(5) + 1  # :1141–1144
    c.base[AGE] += n
    c.maxbase[AGE] += n
    csd(data, c)
    out.drawline()


def child_grow_2(ctx: Ctx) -> None:
    """`@CHILD_GROW_2`:1150–1205：二次性徴。"""
    from .body import chara_size_default as csd

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    rand = st.rng.rand
    T = lambda n: t(ctx, c, n)  # noqa: E731
    out.printl()
    out.set_bold(True)
    out.printl("二次性徴")
    out.set_bold(False)
    out.printl(f"{print_callname(st, st.target)}は成長して体質がさらに変わった")
    out.printw()
    if rand(4) != 0:  # :1159–1160
        c.talent[_T(ctx, "パイパン")] = 0
    for k in range(4):  # :1162–1168（&& の右辺は左辺が真のときだけ：RAND は左辺）
        if rand(100) < 80 and c.talent[101 + 2 * k] == 1:
            c.talent[101 + 2 * k] = 0
        elif rand(100) > 80 and c.talent[100 + 2 * k] == 0:
            c.talent[100 + 2 * k] = 1
    if is_female(data, c):  # :1170–1184
        r = rand(100)
        if r < 70 and T("貧乳") > 0:
            c.talent[_T(ctx, "貧乳")] -= 1
        elif r > 70 and T("貧乳") == 0 and T("巨乳") < 5:
            c.talent[_T(ctx, "巨乳")] += 1
        r = rand(100)
        if r < 70 and T("濡れにくい") == 1:
            c.talent[_T(ctx, "濡れにくい")] = 0
        elif r > 70 and T("濡れにくい") == 0:
            c.talent[_T(ctx, "濡れやすい")] = 1
    r = rand(100)  # :1186–1191
    if r < 70 and T("回復早い") == 1:
        c.talent[_T(ctx, "回復早い")] = 0
    elif r > 70 and T("回復早い") == 0:
        c.talent[_T(ctx, "回復遅い")] = 1
    r = rand(100)  # :1193–1198
    if r < 70 and T("小柄") > 0:
        c.talent[_T(ctx, "小柄")] = 0
    elif r > 70 and T("小柄") == 0:
        c.talent[_T(ctx, "長身")] = 1
    n = rand(5) + 1  # :1201–1204
    c.base[AGE] += n
    c.maxbase[AGE] += n
    csd(data, c)
    out.drawline()


def rescue_child(ctx: Ctx, arg: int) -> Generator[None, int, int]:
    """`@RESCUE_CHILD, ARG`:1210–1299：救出された娘（CFLAG:6 == -1）。戻り値 = LOCAL:99（施設に預けたら -1）。"""
    st, out = ctx.state, ctx.out
    mother = 0
    for cc in range(st.charanum):  # :1214–1219
        if cc == GameState.MASTER:
            continue
        if st.charas[cc].cflag[240] == st.charas[arg].cflag[7]:
            mother = cc
    ret = 0  # VARSET LOCAL（LOCAL:99）
    a = st.charas[arg]
    mo = st.charas[mother]

    def give_up() -> None:
        if mo.cflag[0] == 0:
            out.printl(f"{print_callname(st, mother)}は{a.callname}が自分の娘だと知りながらも")
            out.printl("戦いに巻き込むわけにはいかないと判断し、施設へと預けることにした・・・")
        else:
            out.printl("触手との厳しい戦いにこんな子供を巻き込むわけにはいかない。")
            out.printl(f"{a.callname}と名乗る少女を施設へと預けることにした・・・")

    out.drawline()
    out.printl("助け出されたまだ幼い少女が、")
    out.printl(f"カタコトで『{a.callname}』と名乗っている。")
    out.printl(f"どうやら{mo.callname}の娘らしいが・・・")
    out.printl()
    if st.money >= 5000 and st.charanum < REGISTER_MAX + 1:  # :1220–1275
        out.printl("仲間に加えるためには養育費として$5000かかります")
        out.printl("仲間に加えますか？")
        out.printl()
        out.printl("[0]いいえ")
        out.printl("[1]はい")
        while True:
            r = yield
            if r == 1:
                if mo.cflag[0] == 0:
                    out.printl("母と子の間に言葉は要らなかった。")
                    out.printl(f"{print_callname(st, mother)}は何も言わずに{a.callname}を強く抱きしめ、")
                    out.printl(f"{a.callname}もまた、そっと抱き返すのだった・・・")
                else:
                    out.printl("行く宛ても無い幼い少女を野に放り出すわけにもいかない。")
                    out.printl("共に闘う仲間として引き取ることにした・・・")
                out.printw()
                if a.cstr[10] != "":
                    out.printl("キャラのフルネームを決めてください。")
                    out.printl(f"[0]{a.cstr[10]} {a.callname}")
                    out.printl(f"[1]{a.callname} {a.cstr[10]}")
                    while True:
                        r2 = yield
                        if r2 == 0:
                            a.name = f"{a.cstr[10]} {a.callname}"
                        elif r2 == 1:
                            a.name = f"{a.callname} {a.cstr[10]}"
                        else:
                            continue
                        break
                out.printl(f"{a.callname}は驚異的な知能を発揮して短期間で言葉を覚えた！")
                st.money -= 5000
                recover_to_party(ctx, arg)
                a.cflag[6] = 0
                break
            if r == 0:
                give_up()
                st.del_chara(arg)
                ret -= 1
                break
            out.printl("正しい数値を入力してください")
    else:  # :1276–1297
        if st.charanum >= REGISTER_MAX + 1:
            out.printl("（これ以上仲間を増やせないので選択肢を省略します）")
        elif st.money < 5000:
            out.printl("（資金不足なので選択肢を省略します）")
        give_up()
        st.del_chara(arg)
        ret -= 1
    out.drawline()
    return ret

