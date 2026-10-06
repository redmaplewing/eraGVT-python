"""キャラ設定の部品（S13：子供の加入 `ADD_CHILD` から呼ばれるもの）。路徑相對 `source/earGVP/ERB/`。

- `SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_SELFCALL`:1203–1488（一人称設定画面）
- `SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_TRANSFORMATION.ERB`：`@FIRSTSETTING_CHARA_TRANSAFTERNAME`:64–221、
  `@FIRSTSETTING_CHARA_TRANSAFTERCALLNAME`:226–294、`@FIRSTSETTING_CHARA_TRANSCALL`:298–348、`@FIRSTSETTING_CHARA_NANORI`:353–445
- `SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@SET_FEAT_DEFAULT`:1500–1776、`ヒロイン関連/CHARA_SYUZOKU.ERB@FEAT_ABLE_F`:92–239
- `SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING`:2–2145（プロフィール設定画面）、`@CONVERT_COLORCSTR`:2179–2208、
  `@CONVERT_AGE`:2213–2224
- `口上/口上システム関係/SELF_CALL.ERB@SELF_CALL_LIST`:721–798

S69子供プロフィール設定改由body_editor.size_setting等待真實輸入。
命名INPUTS已於S35接通；S68一人稱改由self_call_setting.selfcall_gen等待真實輸入。
"""

from __future__ import annotations

from collections.abc import Generator

from .action import Ctx
from .body import AGE, HIP, set_profile
from .chara_common import seikaku_check, talent
from .era import format_percent
from .input_request import inputs, input_number
from .naming import random_naming, random_naming_all

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


def chara_callname(ctx: Ctx, who: int) -> Generator[None, int, int]:
    """`FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_CALLNAME, ARG`:1072–1101（呼び名の設定）。戻り値：[99] は 99、他は 0
    （関数終端：RESULT:0 = 0）。[1] 等待文字輸入。"""
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
        r = yield from input_number(ctx)
        if r == 0:
            if c.cstr[200] == "":
                continue
            c.callname = c.cstr[200]
            out.printl(f"キャラの呼び名を 『{c.callname}』 に設定しました")
            break
        if r == 1:
            out.printl("キャラの呼び名を入力してください。")
            while True:  # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_CALLNAME:1088–1095
                value = yield from inputs(ctx)
                if value != "":
                    break
            c.callname = value
            out.printl(f"キャラの呼び名を 『{c.callname}』 に設定しました")
            break
        if r == 99:
            ctx.state.result[0] = 99
            return 99
    out.printl()
    out.printl()
    ctx.state.result[0] = 0
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
    """`@FIRSTSETTING_CHARA_TRANSAFTERNAME, ARG`:64–221：手輸入、隨機與組合命名。"""
    st, out = ctx.state, ctx.out
    c = st.charas[who]
    st.results[0] = ""  # :67；不清 RESULTS:1 以後
    old_up, old_down = c.cstr[201], c.cstr[202]
    c.cstr[201] = ""  # :71–75
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
        r = yield from input_number(ctx)
        if (st.flag[6] == 0 and (r < 0 or r > 4)) or (st.flag[6] == 1 and (r < 0 or r > 8)):
            continue
        break
    if r == 0:
        c.cflag[2] = 0
        c.cflag[3] = 0
        c.cstr[1] = ""
        out.printl("変身後名を設定しませんでした")
    elif r == 1:
        c.cflag[2] = 1
        out.printl("変身後名を入力してください")
        if c.cstr[0] != "":
            out.printl(f"[999]変更しない（{c.cstr[0]}）")
        while True:
            value = yield from inputs(ctx)
            if value != "":
                break
        if value != "999" or c.cstr[0] == "":
            c.cstr[0] = value
        out.printl(f"変身後名を 『{c.cstr[0]}』 に設定しました")
        c.cstr[1], c.cflag[3] = c.cstr[0], 1
    elif r == 2:
        selected = yield from random_naming_all(ctx)
        if selected == 99:
            out.printl("変身後名を選ばずに戻ります")
            st.result[0] = 0  # :124 RETURN
            return
        c.cflag[2] = 1
        c.cstr[201] = ctx.data.str_defaults.get(st.da[0, selected], "")
        c.cstr[202] = ctx.data.str_defaults.get(st.da[1, selected], "")
        c.cstr[0] = c.cstr[201] + c.cstr[202]
        out.printl(f"変身後名を 『{c.cstr[0]}』 に設定しました")
        c.cstr[1], c.cflag[3] = c.cstr[0], 1
    elif r in (3, 4):
        c.cflag[2] = 1
        prefix = c.callname if r == 3 else st.savestr[11]
        c.cstr[201] = prefix
        out.printl()
        out.print("組み合わせる単語の")
        while True:
            yield from random_naming(ctx, who, prefix)
            out.printl()
            if st.result[1] == 1:
                continue
            out.printl(f"変身後名を 『{st.results[0]}』 に設定します。よろしいですか？")
            out.printl()
            out.printl("[0]いいえ")
            out.printl("[1]はい")
            if c.cstr[0] != "":
                out.printl(f"[2]変更しない（{c.cstr[0]}）")
            while True:
                answer = yield from input_number(ctx)
                if answer in (0, 1, 2):
                    break
            if answer == 0:
                c.cstr[201], c.cstr[202] = old_up, old_down
                continue
            if answer == 1:
                c.cstr[0] = st.results[0]
                out.printl(f"変身後名を 『{c.cstr[0]}』 に設定しました")
                c.cstr[1], c.cflag[3] = c.cstr[0], 1
            break
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
    st.result[0] = 0  # Process.ScriptProc.cs:61–67：一般函式終端



def trans_after_callname(ctx: Ctx, who: int) -> InputGen:
    """`@FIRSTSETTING_CHARA_TRANSAFTERCALLNAME, ARG`:226–294。手輸入沿既有等待通道。"""
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
            r = yield from input_number(ctx)
            if 0 <= r <= 2:
                break
        if r == 0:
            yield from _manual_trans_callname(ctx, c)
        else:
            c.cstr[1] = c.cstr[0] if r == 1 else c.callname
    else:  # :260–292
        out.printl(f"[0]変身後呼び名を 『{c.cstr[201]}』 に設定")
        out.printl(f"[1]変身後呼び名を 『{c.cstr[202]}』 に設定")
        out.printl("[2]自分で設定")
        out.printl(f"[3]変身後名と同じに設定（変身後名：『{c.cstr[0]}』）")
        out.printl("[4]変身前の呼び名をそのまま使う")
        while True:
            r = yield from input_number(ctx)
            if 0 <= r <= 4:
                break
        if r == 2:
            yield from _manual_trans_callname(ctx, c)
        else:
            c.cstr[1] = {0: c.cstr[201], 1: c.cstr[202], 3: c.cstr[0], 4: c.callname}[r]
    out.printl(f"変身後呼び名を 『{c.cstr[1]}』 に設定しました")
    out.printl()
    out.printl()
    ctx.state.result[0] = 0


def _manual_trans_callname(ctx, c):
    # FIRSTSETTING_CHARA_TRANSFORMATION.ERB@FIRSTSETTING_CHARA_TRANSAFTERCALLNAME:245–253／277–285。
    ctx.out.printl("変身後呼び名を入力してください")
    if c.cstr[1] != "":
        ctx.out.printl(f"[999]変更しない（{c.cstr[1]}）")
    while True:
        value = yield from inputs(ctx)
        if value != "":
            break
    if value != "999":  # 與正式名不同：即使舊呼び名空白也保留
        c.cstr[1] = value


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
    """`@FIRSTSETTING_CHARA_TRANSCALL, ARG`:298–348。[2] 自分で設定等待文字輸入。"""
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
        r = yield from input_number(ctx)
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
                r2 = yield from input_number(ctx)
                if 0 <= r2 <= 1:
                    break
            if r2 == 1:
                out.printl(f"かけ声を 『{c.cstr[2]}』 に設定しました")
                break
    elif r == 2:
        c.cflag[4] = 1
        out.printl("かけ声を入力してください")
        while True:
            value = yield from inputs(ctx)
            if value != "":
                break
        c.cstr[2] = value
        out.printl(f"かけ声を 『{c.cstr[2]}』 に設定しました")
    elif r == 3:
        c.cflag[4] = 1
        c.cstr[2] = st.savestr[12]
        out.printl(f"かけ声を 『{c.cstr[2]}』 に設定しました")
    out.printl()
    out.printl()
    ctx.state.result[0] = 0


def nanori(ctx: Ctx, who: int) -> InputGen:
    """`@FIRSTSETTING_CHARA_NANORI, ARG`:353–445。自分で設定等待文字輸入。"""
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
            r = yield from input_number(ctx)
            if 0 <= r <= 1:
                break
        if r == 0:
            c.cflag[5] = 0
            out.printl("名乗り口上を設定しませんでした")
        else:
            c.cflag[5] = 1
            out.printl("名乗り口上を入力してください")
            while True:
                value = yield from inputs(ctx)
                if value != "":
                    break
            c.cstr[3] = value
            out.printl(f"名乗り口上を 『{c.cstr[3]}』 に設定しました")
    elif c.cflag[2] == 1:  # :387–443
        out.printl("[0]いいえ")
        out.printl("[1]主題 ＋ 変身後名 ＋ 一文 の構成で自動生成")
        out.printl("[2]変身後名 ＋ 一文 の構成で自動生成")
        out.printl("[3]自分で設定")
        while True:
            r = yield from input_number(ctx)
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
                    r2 = yield from input_number(ctx)
                    if 0 <= r2 <= 1:
                        break
                if r2 == 1:
                    out.printl(f"名乗り口上を 『{c.cstr[3]}』 に設定しました")
                    break
        else:
            c.cflag[5] = 1
            out.printl("名乗り口上を入力してください")
            while True:
                value = yield from inputs(ctx)
                if value != "":
                    break
            c.cstr[3] = value
            out.printl(f"名乗り口上を 『{c.cstr[3]}』 に設定しました")
    out.printl()
    out.printl()
    ctx.state.result[0] = 0


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

