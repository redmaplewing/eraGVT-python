"""キャラ設定の部品（S13：子供の加入 `ADD_CHILD` から呼ばれるもの）。路徑相對 `source/earGVP/ERB/`。

- `SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_SELFCALL`:1203–1488（一人称設定画面）
- `SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_TRANSFORMATION.ERB`：`@FIRSTSETTING_CHARA_TRANSAFTERNAME`:64–221、
  `@FIRSTSETTING_CHARA_TRANSAFTERCALLNAME`:226–294、`@FIRSTSETTING_CHARA_TRANSCALL`:298–348、`@FIRSTSETTING_CHARA_NANORI`:353–445
- `SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@SET_FEAT_DEFAULT`:1500–1776、`ヒロイン関連/CHARA_SYUZOKU.ERB@FEAT_ABLE_F`:92–239
- `SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING`:2–2145（プロフィール設定画面）、`@CONVERT_COLORCSTR`:2179–2208、
  `@CONVERT_AGE`:2213–2224
- `口上/口上システム関係/SELF_CALL.ERB@SELF_CALL_LIST`:721–798

画面（一人称設定・プロフィール設定）は AGENTS.md「暫時跳過 UI 時走原作預設路徑」により、表示せず
「何も変えずに [99] 決定」した場合の状態変化だけを行う（deviations.md「子供加入時のキャラ設定画面」）。
名前などの手入力（INPUTS）は Web が整数入力のみのため未対応で停止する。
"""

from __future__ import annotations

from collections.abc import Generator

from .action import Ctx
from .body import AGE, BREAST_WEIGHT, BUST, HEIGHT, HIP, REAL_AGE, WAIST, WEIGHT, generate_char_size, set_profile
from .chara_common import is_female, seikaku_check, talent
from .era import format_percent

InputGen = Generator[None, int, None]

# --- 一人称（SELF_CALL.ERB@SELF_CALL_LIST:721–798）-----------------------------------------------
_SELF_CALL_LIST = (
    ("私", "わたし", "ワタシ"), ("私", "わたくし", "ワタクシ"), ("私", "あたし", "アタシ"), ("私", "あたい", "アタイ"),
    ("妾", "わらわ", "ワラワ"), ("僕", "ぼく", "ボク"), ("俺", "おれ", "オレ"), ("己", "おれ", "オレ"), ("我", "われ", "われ"),
)


def self_call_list(prn: int, shw: int) -> str:
    """`@SELF_CALL_LIST(PRN_VAR, SHW_VAR)`：該当なしは ""（:798 `RETURNF` 空）。"""
    if 0 <= prn < len(_SELF_CALL_LIST) and 0 <= shw <= 2:
        return _SELF_CALL_LIST[prn][shw]
    return ""


def selfcall_default(ctx: Ctx, who: int) -> None:
    """`@FIRSTSETTING_CHARA_SELFCALL, ARG` で何も変えずに [99] 決定した場合（:1462–1487）。

    :1215–1218 CALL_VAR:0 = CFLAG:8 / 5 % 20、CALL_VAR:1 = CFLAG:8 % 5、CALL_STR:1 = SELF_CALL(0, 0, ARG)
    （CSTR:4 が空なら SELF_CALL_LIST：SELF_CALL.ERB:51–60）。:1465–1466 INRANGE(CALL_VAR:0, 0, 一人称_最大〔20〕) なら
    CFLAG:8 = CALL_VAR:0 * 5 + CALL_VAR:1（CFLAG:8 < 100 では元の値と同じ）、:1475 CSTR:4 = CALL_STR:1。
    CALL_STR:0（読み = SELF_CALL(7, …)）が空だと [99] は受け付けられない（:1463–1465）が、ADD_CHILD の一人称
    （CFLAG:8 = 0、25–27、30–32 → PRN 0／5／6）はすべて読みの符号がある（SELF_CALL.ERB@SELF_CALL_SUBSTRING:140–159）。
    """
    c = ctx.state.charas[who]
    cv0 = (c.cflag[8] // 5) % 20 if c.cflag[8] >= 0 else None
    if cv0 is None:
        raise NotImplementedError("FIRSTSETTING_CHARA_SELFCALL：CFLAG:8 が負")
    cv1 = c.cflag[8] % 5
    call1 = c.cstr[4] if c.cstr[4] != "" else self_call_list(cv0, cv1)
    if call1 == "":
        raise NotImplementedError("FIRSTSETTING_CHARA_SELFCALL：一人称が空（[99] を受け付けない）")
    c.cflag[8] = cv0 * 5 + cv1
    c.cstr[4] = call1


def chara_callname(ctx: Ctx, who: int) -> Generator[None, int, int]:
    """`FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_CALLNAME, ARG`:1072–1101（呼び名の設定）。戻り値：[99] は 99、他は 0
    （関数終端：RESULT:0 = 0）。[1] 自分で設定（INPUTS）は Web が整数入力のみのため未移植で停止。"""
    out = ctx.out
    c = ctx.state.charas[who]
    out.printl(f"{who}人目のキャラの呼び名を設定してください")
    out.printl("（※ 通常の地の文などで表示されるキャラ名です）")
    out.printl("・" * 53)
    if c.cstr[200] != "":
        out.printl(f"[0]名前を呼び名に設定（名前：{c.cstr[200]}）")
    out.printl("[1]自分で設定")
    out.printl("[99]もどる")
    while True:  # $INPUT_LOOP
        r = yield
        if r == 0:
            if c.cstr[200] == "":
                continue
            c.callname = c.cstr[200]
            out.printl(f"キャラの呼び名を 『{c.callname}』 に設定しました")
            break
        if r == 1:
            out.printl("キャラの呼び名を入力してください。")
            raise NotImplementedError("呼び名の手入力（INPUTS）は未移植")
        if r == 99:
            return 99
    out.printl()
    out.printl()
    return 0


# --- フィート（FEAT_ABLE_F、SET_FEAT_DEFAULT）--------------------------------------------------------

_FEAT_ABLE = {
    "人間": ("平凡", "巻き込まれ体質", "秘められし力", "ラッキーチャーム", "祝福", "不屈"),
    "異能力者": ("攻勢構築", "秘められし力", "生粋の戦士", "ホットスタート", "狩人の勘", "心眼"),
    "魔法使い": ("魔力貯蔵", "ラッキーチャーム", "空中浮遊", "フルバースト", "不老長寿", "叡智の冠"),
    "ロボっ子": ("超反応", "剛腕", "空中浮遊", "ホットスタート", "フルバースト", "スタミナ"),
    "天使": ("神器の担い手", "有翼", "空中浮遊", "祝福", "叡智の冠", "背徳の烙印"),
    "魔族": ("闘争本能", "有翼", "生粋の戦士", "不屈", "狩人の勘", "背徳の烙印"),
    "鬼": ("溢れる生命力", "生粋の戦士", "剛腕", "不屈", "スタミナ", "不老長寿"),
    "妖精族": ("精霊交信", "小さな体躯", "不老長寿", "叡智の冠", "心眼", "人外の美貌"),
    "ケモミミ族": ("獣性の証", "小さな体躯", "スタミナ", "狩人の勘", "心眼", "エアマスター"),
    "ヴァンパイア": ("夜魔の貴族", "剛腕", "有翼", "人外の美貌", "背徳の烙印", "エアマスター"),
    "ポリニアン": ("超反応", "剛腕", "空中浮遊", "ホットスタート", "フルバースト", "スタミナ"),
}


def feat_able(ctx: Ctx, race: int, feat: int) -> int:
    """`@FEAT_ABLE_F, ARG, ARG:1`:92–239：種族 ARG（TALENT 番号）でフィート ARG:1 が取得可能なら 1（名前で比較）。"""
    names = ctx.data.names["TALENT"]
    return 1 if names.get(feat, "") in _FEAT_ABLE.get(names.get(race, ""), ()) and names.get(feat, "") != "" else 0


def set_feat_default(ctx: Ctx, who: int, race: int) -> None:
    """`@SET_FEAT_DEFAULT, ARG, ARG:1`:1500–1776：フィートのランダム設定。

    :1760–1772 は FEAT_NUM > 0 なら「取得可能でまだ持っていないフィート」を全候補に入れ、`FOR LOCAL, 0, CHOICECOUNT_F()`
    （終端は開始時に 1 回だけ評価：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1731–1743）で
    候補数と同じ回数 RANDCHOOSE_F → 取得 → CLEARSPECIFICCHOOSE を繰り返す。つまり FEAT_NUM の値に関係なく
    残りの取得可能フィートを **すべて** 取得する（原作どおり。RAND は候補数ぶん消費）。
    """
    from .battle.core import add_randchoose, choicecount, clear_randchoose, clear_specific_choose, randchoose_f

    st, data = ctx.state, ctx.data
    c = st.charas[who]
    rand = st.rng.rand
    names = data.names["TALENT"]

    def on(name: str) -> None:
        c.talent[data.index_of("TALENT", name)] = 1

    if rand(8) == 0:  # :1505–1511
        num = 1
    elif rand(4) == 0:
        num = 2
    else:
        num = 3
    rname = names.get(race, "")
    if rname == "ヴァンパイア":  # :1512–1513（TALENTNAME:(ARG:1)）
        num -= 1
    if rand(4) != 0:  # :1516–1758 プリセット
        if rname == "人間":
            if rand(4) == 0:
                on("平凡")
                num -= 1
            elif rand(3) == 0:
                on("巻き込まれ体質")
                num -= 1
            elif rand(2) == 0:
                on("秘められし力")
                on("不屈")
                num -= 2
            else:
                on("祝福")
                on("不屈")
                num -= 2
            if rand(2) == 0:
                num -= 1
        elif rname == "異能力者":
            if rand(4) == 0:
                on("攻勢構築")
                num -= 1
            elif rand(3) == 0:
                on("秘められし力")
                on("心眼")
                num -= 2
            elif rand(2) == 0:
                on("生粋の戦士")
                on("狩人の勘")
                num -= 2
            else:
                on("攻勢構築")
                on("心眼")
                num -= 2
        elif rname == "魔法使い":
            if rand(5) == 0:
                on("魔力貯蔵")
                num -= 1
            elif rand(4) == 0:
                on("不老長寿")
                num -= 1
            elif rand(3) == 0:
                on("ラッキーチャーム")
                on("叡智の冠")
                num -= 2
            elif rand(2) == 0:
                on("魔力貯蔵")
                on("フルバースト")
                num -= 2
            else:
                on("空中浮遊")
                on("不老長寿")
                num -= 2
        elif rname in ("ロボっ子", "ポリニアン"):  # :1586–1612／:1730–1756（同一内容）
            if rand(2) == 0:
                on("超反応")
                num -= 1
            elif rand(2) == 0:
                on("スタミナ")
                if rand(3) == 0:
                    on("剛腕")
                elif rand(3) == 0:
                    on("空中浮遊")
                elif rand(2) == 0:
                    on("ホットスタート")
                else:
                    on("フルバースト")
                num -= 2
            else:
                on("ホットスタート")
                on("フルバースト")
                num -= 2
            if rand(3) == 0:
                num -= 1
        elif rname == "天使":
            if rand(4) != 0:
                on("神器の担い手")
                num -= 1
            elif rand(3) == 0:
                on("祝福")
                on("叡智の冠")
                num -= 2
            elif rand(2) == 0:
                on("有翼")
                on("空中浮遊")
                num -= 2
            else:
                num = 3
        elif rname == "魔族":
            if rand(4) != 0:
                on("闘争本能")
                num -= 1
            elif rand(3) == 0:
                on("闘争本能")
                on("不屈")
                num -= 2
            elif rand(2) == 0:
                on("生粋の戦士")
                on("狩人の勘")
                num -= 2
            else:
                num = 3
        elif rname == "鬼":
            if rand(4) != 0:
                on("溢れる生命力")
                num -= 1
            elif rand(3) == 0:
                on("不屈")
                on("スタミナ")
                num -= 2
            elif rand(2) == 0:
                on("生粋の戦士")
                on("剛腕")
                num -= 1  # :1665（2 個取得して 1 減：原作どおり）
            else:
                on("不老長寿")
                num -= 1
        elif rname == "妖精族":
            if rand(4) != 0:
                on("精霊交信")
                num -= 1
            elif rand(2) == 0:
                on("小さな体躯")
                on("人外の美貌" if rand(2) == 0 else "エアマスター")
                num -= 2
            else:
                on("叡智の冠")
                on("人外の美貌" if rand(2) == 0 else "不老長寿")
                num -= 2
        elif rname == "ケモミミ族":
            if rand(4) != 0:
                on("獣性の証")
                num -= 1
            elif rand(3) == 0:
                on("小さな体躯")
                on("エアマスター")
                num -= 2
            elif rand(2) == 0:
                on("獣性の証")
                on("心眼")
                num -= 2
            else:
                on("スタミナ")
                num -= 1
        elif rname == "ヴァンパイア":
            if rand(4) == 0:
                on("剛腕")
                on("有翼")
                num -= 2
            elif rand(3) == 0:
                on("人外の美貌")
                on("背徳の烙印")
                num -= 2
            else:
                num = 2
    if num > 0:  # :1760–1772
        clear_randchoose(st)
        for f in range(1100, 1300):
            if feat_able(ctx, race, f) > 0 and c.talent[f] == 0:
                add_randchoose(st, f)
        for _ in range(choicecount(st)):
            pick = randchoose_f(st)
            c.talent[pick] = 1
            clear_specific_choose(st, pick)
    set_profile(data, c, st.result)  # :1774


def feat_select_ui(ctx: Ctx, who: int, race: int) -> InputGen:
    """ADD_CHILD の「[0]はい（フィートを設定する）」:549–627（選択画面：[100]〜 で切り替え、[0] 決定〔3 個以下〕）。

    `#DIM FEAT_SELECT, 300` は :551 で VARSET。種族・フィートの説明（SYUZOKU_INFO／FEAT_INFO：表示のみ）は catalog で出す。
    """
    from .shop import lb

    st, data, out = ctx.state, ctx.data, ctx.out
    names = data.names["TALENT"]
    c = st.charas[who]
    sel = [0] * 300  # :551
    for f in range(100, 300):  # :552–555
        if feat_able(ctx, race, f + 1000) == 0:
            sel[f] = 0
    lb(out)  # :556
    while True:  # $MASTER_LOOP_1（:557）
        if race == 9:  # :559–560（RACE は TALENT 番号 201〜なので成立しない：原作どおり）
            sel[110] = 1
        num = sum(1 for f in range(100, 300) if sel[f] > 0)
        out.printl(names.get(race, ""))
        out.print("――――――――――――――――――――――――――――")  # SHORTLINE（汎用関数/PRINT_LINE.ERB:3–7）
        out.printl()
        if not ctx.narration.run_function(ctx, "SYUZOKU_INFO", [race]):
            out.printl(f"〈SYUZOKU_INFO {race}〉")
        out.printl()
        out.printl("(取得可能フィート)          選択")
        for f in range(100, 300):  # :572–594
            if feat_able(ctx, race, f + 1000) == 0:
                continue
            out.print("　★" if f < 200 else "　☆")
            out.print(f"{format_percent(names.get(f + 1000, ''), 22, True)}  [{f}]  ")
            if f == 110 and sel[f] > 0:
                out.set_color((255, 0, 0))
                out.print("◎")
                out.reset_color()
                out.print_plain(" 固定取得")
            elif sel[f] > 0:
                out.set_color((255, 128, 0))
                out.print("○")
                out.reset_color()
            else:
                out.print("×")
            out.printl()
        out.printl()
        out.printl(f"選択したフィート({num}/3)")
        if num > 3:
            out.set_color((128, 128, 128))
        out.printl("[0]決定")
        out.reset_color()
        done = False
        while True:  # $INPUT_LOOP_1（:601–617）
            r = yield
            if r == 0 and num <= 3:
                done = True
                break
            if 100 <= r <= 300 and feat_able(ctx, race, r + 1000) > 0:
                lb(out)
                if not ctx.narration.run_function(ctx, "FEAT_INFO", [r + 1000]):
                    out.printl(f"〈FEAT_INFO {r + 1000}〉")
                out.printl()
                sel[r] = 0 if sel[r] > 0 else 1
                break  # GOTO MASTER_LOOP_1
        if done:
            break
    for f in range(100, 300):  # :619–625
        c.talent[f + 1000] = 1 if sel[f] > 0 else 0
    set_profile(data, c, ctx.state.result)  # :627


# --- 変身後名・呼び名・かけ声・名乗り（FIRSTSETTING_CHARA_TRANSFORMATION.ERB）-------------------------


def trans_after_name(ctx: Ctx, who: int) -> InputGen:
    """`@FIRSTSETTING_CHARA_TRANSAFTERNAME, ARG`:64–221。[0]〔設定しない〕と FLAG:6 == 1 の [5]／[6] を移植。
    [1] 自分で設定（INPUTS）、[2] ランダム（FIRSTSETTING_RANDOMNAMING_ALL）、[3]／[4]（FIRSTSETTING_RANDOMNAMING）は未移植で停止。"""
    st, out = ctx.state, ctx.out
    c = st.charas[who]
    c.cstr[201] = ""  # :71–75（上の句・下の句を退避して初期化；退避値は [3]／[4] の「いいえ」でのみ使う）
    c.cstr[202] = ""
    out.printl(f"{who}人目のキャラ 『{c.callname}』 の変身後名を設定してください")
    out.printl("（変身中の正式なキャラ名です。一部の地の文やステータス表示などに使用されます）")
    out.printl("・" * 53)
    out.printl("[0]設定しない")
    out.printl("[1]自分で設定")
    out.printl("[2]ランダム にする")
    out.printl(f"[3]『{c.callname}』とランダムの組み合わせにする")
    if st.flag[6] == 1:
        out.printl(f"[4]『{st.savestr[11]}』とランダムの組み合わせにする")
        out.printl(f"[5]『{st.savestr[11]}{c.callname}』 にする")
        out.printl(f"[6]『{c.callname}{st.savestr[11]}』 にする")
    while True:  # $INPUT_LOOP（:90–94）
        r = yield
        if (st.flag[6] == 0 and (r < 0 or r > 4)) or (st.flag[6] == 1 and (r < 0 or r > 8)):
            continue
        break
    if r == 0:
        c.cflag[2] = 0
        c.cflag[3] = 0
        c.cstr[1] = ""
        out.printl("変身後名を設定しませんでした")
    elif r in (1, 2, 3, 4):
        raise NotImplementedError(f"変身後名の設定 [{r}]（手入力／ランダム命名画面）は未移植")
    elif r in (5, 6):
        c.cflag[2] = 1
        head, tail = (st.savestr[11], c.callname) if r == 5 else (c.callname, st.savestr[11])
        c.cstr[201] = head
        c.cstr[202] = tail
        c.cstr[0] = head + tail
        out.printl(f"変身後名を 『{c.cstr[0]}』 に設定しました")
        c.cstr[1] = c.cstr[0]
        c.cflag[3] = 1
    # r == 7／8（FLAG:6 == 1 で受け付けるが分岐なし）は何もしない（:93 の範囲判定どおり）
    out.printl()
    out.printl()


def trans_after_callname(ctx: Ctx, who: int) -> InputGen:
    """`@FIRSTSETTING_CHARA_TRANSAFTERCALLNAME, ARG`:226–294。手入力（INPUTS）の選択肢は未移植で停止。"""
    st, out = ctx.state, ctx.out
    c = st.charas[who]
    out.printl(f"{who}人目のキャラ 『{c.callname}』 の変身後呼び名を設定してください")
    out.printl("（※ 変身中に通常の地の文などで表示されるキャラ名です）")
    out.printl("・" * 53)
    if c.cstr[201] == "" and c.cstr[202] == "":  # :232–257
        out.printl("[0]自分で設定")
        out.printl(f"[1]変身後名と同じに設定（変身後名：『{c.cstr[0]}』）")
        out.printl("[2]変身前の呼び名をそのまま使う")
        while True:
            r = yield
            if 0 <= r <= 2:
                break
        if r == 0:
            raise NotImplementedError("変身後呼び名の手入力（INPUTS）は未移植")
        c.cstr[1] = c.cstr[0] if r == 1 else c.callname
    else:  # :260–292
        out.printl(f"[0]変身後呼び名を 『{c.cstr[201]}』 に設定")
        out.printl(f"[1]変身後呼び名を 『{c.cstr[202]}』 に設定")
        out.printl("[2]自分で設定")
        out.printl(f"[3]変身後名と同じに設定（変身後名：『{c.cstr[0]}』）")
        out.printl("[4]変身前の呼び名をそのまま使う")
        while True:
            r = yield
            if 0 <= r <= 4:
                break
        if r == 2:
            raise NotImplementedError("変身後呼び名の手入力（INPUTS）は未移植")
        c.cstr[1] = {0: c.cstr[201], 1: c.cstr[202], 3: c.cstr[0], 4: c.callname}[r]
    out.printl(f"変身後呼び名を 『{c.cstr[1]}』 に設定しました")
    out.printl()
    out.printl()


_CHANGINGCALL = (
    "変身！", "装着！", "装填！", "チェンジ！", "メタモルフォーゼ！", "セット！", "インストール！", "インジェクション！",
    "モジュレーション！", "オーバーライド！", "フュージョン！", "アトラクション！", "メイクアップ！", "ドレスアップ！",
    "ビートアップ！", "フルバースト！", "クロックアップ！", "エンゲージ！", "アナザーフォーム！",
)


def changingcall_random(ctx: Ctx) -> str:
    """`FIRSTSETTING_変身デフォルト口上.ERB@FIRSTSETTING_CHANGINGCALL_RANDOM`:3–27（STRDATA：rand(件数)、
    reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:730–755）。"""
    return _CHANGINGCALL[ctx.state.rng.rand(len(_CHANGINGCALL))]


def trans_call(ctx: Ctx, who: int) -> InputGen:
    """`@FIRSTSETTING_CHARA_TRANSCALL, ARG`:298–348。[2] 自分で設定（INPUTS）は未移植で停止。"""
    st, out = ctx.state, ctx.out
    c = st.charas[who]
    out.printl(f"{who}人目のキャラ 『{c.callname}』 の変身時のかけ声を設定しますか？")
    out.printl("・" * 53)
    out.printl("[0]いいえ")
    out.printl("[1]ランダムに設定")
    out.printl("[2]自分で設定")
    if st.flag[7] == 1:
        out.printl("[3]共通のかけ声に設定")
    while True:
        r = yield
        if (st.flag[7] == 0 and (r < 0 or r > 2)) or (st.flag[7] == 1 and (r < 0 or r > 3)):
            continue
        break
    if r == 0:
        c.cflag[4] = 0
        out.printl("かけ声を設定しませんでした")
    elif r == 1:
        c.cflag[4] = 1
        while True:  # $INPUT_LOOP_CHILD_1_1
            c.cstr[2] = changingcall_random(ctx)
            out.printl(f"かけ声を 『{c.cstr[2]}』 とします。よろしいですか？")
            out.printl("[0]もう一度選びなおす")
            out.printl("[1]はい")
            while True:
                r2 = yield
                if 0 <= r2 <= 1:
                    break
            if r2 == 1:
                out.printl(f"かけ声を 『{c.cstr[2]}』 に設定しました")
                break
    elif r == 2:
        raise NotImplementedError("かけ声の手入力（INPUTS）は未移植")
    elif r == 3:
        c.cflag[4] = 1
        c.cstr[2] = st.savestr[12]
        out.printl(f"かけ声を 『{c.cstr[2]}』 に設定しました")
    out.printl()
    out.printl()


def nanori(ctx: Ctx, who: int) -> InputGen:
    """`@FIRSTSETTING_CHARA_NANORI, ARG`:353–445。自分で設定（INPUTS）は未移植で停止。"""
    from .opening import changingcall_detail

    st, out = ctx.state, ctx.out
    c = st.charas[who]
    seikaku = seikaku_check(ctx.data, c)  # :356–357 SEIKAKU_CHECK "GET_TALENT_VALUE"
    out.printl(f"{who}人目のキャラ 『{c.callname}』 の変身後の名乗り口上を設定しますか？")
    out.printl("（※ 口上側で設定されている場合はそちらが優先されます）")
    out.printl("・" * 53)
    if c.cflag[2] == 0:  # :364–385
        out.printl("[0]いいえ")
        out.printl("[1]自分で設定")
        while True:
            r = yield
            if 0 <= r <= 1:
                break
        if r == 0:
            c.cflag[5] = 0
            out.printl("名乗り口上を設定しませんでした")
        else:
            raise NotImplementedError("名乗り口上の手入力（INPUTS）は未移植")
    elif c.cflag[2] == 1:  # :387–443
        out.printl("[0]いいえ")
        out.printl("[1]主題 ＋ 変身後名 ＋ 一文 の構成で自動生成")
        out.printl("[2]変身後名 ＋ 一文 の構成で自動生成")
        out.printl("[3]自分で設定")
        while True:
            r = yield
            if 0 <= r <= 3:
                break
        if r == 0:
            c.cflag[5] = 0
            out.printl("名乗り口上を設定しませんでした")
        elif r in (1, 2):
            c.cflag[5] = 1
            while True:
                head = st.savestr[10] if r == 1 else ""
                c.cstr[3] = head + c.cstr[0] + changingcall_detail(st, seikaku)
                out.printl(f"名乗り口上を 『{c.cstr[3]}』 とします。よろしいですか？")
                out.printl("[0]もう一度選びなおす")
                out.printl("[1]はい")
                while True:
                    r2 = yield
                    if 0 <= r2 <= 1:
                        break
                if r2 == 1:
                    out.printl(f"名乗り口上を 『{c.cstr[3]}』 に設定しました")
                    break
        else:
            raise NotImplementedError("名乗り口上の手入力（INPUTS）は未移植")
    out.printl()
    out.printl()


# --- プロフィール設定画面（CHARA_SIZE_UI.ERB@SIZE_SETTING）-----------------------------------------


def convert_colorcstr(c) -> None:
    """`@CONVERT_COLORCSTR, ARG`:2179–2208（旧形式の色 CSTR:30–34 → 30–37）。"""
    if c.cstr[30] != "" and c.cstr[36] != "":
        return
    c.cstr[36] = c.cstr[34]
    c.cstr[34] = c.cstr[32]
    c.cstr[35] = c.cstr[33]
    c.cstr[37] = c.cstr[36]


def convert_age(c) -> None:
    """`@CONVERT_AGE, ARG`:2213–2224（実年齢 BASE:40 が無かった頃の配置 40–46 → 41–47）。"""
    if c.cflag[34] == 0 or c.base[HIP]:
        return
    for k in range(7):
        c.base[47 - k] = c.base[46 - k]
    if c.maxbase[AGE] < 0:
        return
    for k in range(7):
        c.maxbase[47 - k] = c.maxbase[46 - k]


def _talent_change(ctx: Ctx, c) -> int:
    """`汎用関数/コモン関数.ERB@TALENT_CHANGE_F, ARG`:1327–1337。"""
    T = lambda n: talent(ctx.data, c, n)  # noqa: E731
    if T("変身時体格変動") != 0 or T("変身時胸サイズ変動") != 0 or T("変身時ＴＳ") != 0:
        return 1
    return 1 if T("外見") != T("変身時外見") else 0


_SLOTS = (HEIGHT, WEIGHT, BUST, WAIST, HIP, BREAST_WEIGHT)


def size_setting_default(ctx: Ctx, who: int) -> None:
    """`@SIZE_SETTING, ARG`（プロフィール設定画面）で何も変えずに [99]「決定して戻る」を押した場合の状態変化。

    :22–24 CONVERT_COLORCSTR／CONVERT_AGE、:29–55 CFLAG・BASE → 作業変数、:58–61 変身能力なしなら 年齢値:1 = -1、
    :62–63 通常時と変身時が同一なら 年齢値:1 = -1。DO の 1 周目（:67–）：:68–70 BASE:年齢・MAXBASE:年齢・BASE:実年齢 を
    作業変数から書き戻し、DISPLAY_FLAG = 3 なので :76–95 GENERATE_CHAR_SIZE（通常／年齢値:1 >= 0 なら変身時）で作業変数を
    再計算（表示部分 :133–1452 は代入・RAND なし）。INPUT 99（INPUT_MODE = -1）→ :1731–1753 パーソナリティ CSTR:40–42 を
    前に詰め、女性または変身時ＴＳなしなら 変身時濡れやすさ変動／変身時Ｖ感覚変動 = 0、BREAK。:2110–2139 書き戻し。
    """
    st, data = ctx.state, ctx.data
    c = st.charas[who]
    keep = st.target  # :20–21
    st.target = who
    convert_colorcstr(c)
    convert_age(c)
    real = c.base[REAL_AGE]
    age0, age1 = c.base[AGE], c.maxbase[AGE]
    v0 = [c.base[s] for s in _SLOTS]
    v1 = [c.maxbase[s] for s in _SLOTS]
    if talent(data, c, "変身能力") < 1:  # :58–61
        age1 = -1
        disp1 = False
    else:
        disp1 = True
    if (  # :62–63
        age0 == age1 and _talent_change(ctx, c) == 0 and v0[0] == v1[0] and v0[1] == v1[1] and v0[2] == v1[2]
        and v0[3] == v1[3] and v0[4] == v1[4]
        and c.cstr[13] == c.cstr[14] and c.cstr[30] == c.cstr[31] and c.cstr[32] == c.cstr[34]
        and c.cstr[33] == c.cstr[35] and c.cstr[36] == c.cstr[37]
    ):
        age1 = -1
    # DO 1 周目
    c.base[AGE] = age0
    c.maxbase[AGE] = age1
    c.base[REAL_AGE] = real
    v0 = list(generate_char_size(data, c, 0, st.result)[2:])  # :76–85
    if age1 >= 0 and disp1:  # :87–95
        v1 = list(generate_char_size(data, c, 1, st.result)[2:])
    # :1731–1753 [99]
    while True:
        if c.cstr[40] == "" and (c.cstr[41] != "" or c.cstr[42] != ""):
            c.cstr[40] = c.cstr[41]
            c.cstr[41] = c.cstr[42]
            c.cstr[42] = ""
            continue
        if c.cstr[41] == "" and c.cstr[42] != "":
            c.cstr[41] = c.cstr[42]
            c.cstr[42] = ""
            continue
        break
    if is_female(data, c) or talent(data, c, "変身時ＴＳ") == 0:
        c.talent[data.index_of("TALENT", "変身時濡れやすさ変動")] = 0
        c.talent[data.index_of("TALENT", "変身時Ｖ感覚変動")] = 0
    # :2110–2139
    if age1 == age0 and _talent_change(ctx, c) == 0 and v1[0] == v0[0] and v1[2] == v0[2]:
        if c.cstr[30] == c.cstr[31] and c.cstr[32] == c.cstr[34] and c.cstr[33] == c.cstr[35] and c.cstr[36] == c.cstr[37]:
            age1 = -1
    c.base[AGE] = age0
    c.base[REAL_AGE] = real
    for s, v in zip(_SLOTS, v0):
        c.base[s] = v
    if age1 >= 0:
        c.maxbase[AGE] = age1
        for s, v in zip(_SLOTS, v1):
            c.maxbase[s] = v
    elif talent(data, c, "変身能力") == 1:
        c.maxbase[AGE] = age0
        for s, v in zip(_SLOTS, v0):
            c.maxbase[s] = v
    st.target = keep  # :2141

