"""悪堕ち容姿：`ヒロイン関連/悪堕ち/CORRPUTION.ERB`（容姿の書き換え）と `CORRUPTION_RECOVER.ERB`（救出後の復帰・定着）。

路徑相對 `source/earGVP/ERB/`。地の文 `地の文/MESSAGE_AKUOTI.ERB`（CORRUPT／STAIN／FINAL 系）は S07 catalog（`run_chinobun`）。

進捗の旗標（CORRPUTION.ERB:11–14 の註解）：
- CFLAG:80 bit 0 初回登録済み・1 肌色登録・2 悪堕ち中（AFTER_RESCUED:29 の復帰判定用）・3 髪型登録・4 髪色登録・5 目色登録。
- CFLAG:81 bit 0 髪色定着・1 右目・2 左目・3 肌色・4 全定着（完堕ち）。
- CFLAG:13 bit 0 変身後名の改竄済み・1 変身後呼び名・3 名乗り。
- CSTR:50 目つき・51 髪色・52 右目・53 左目・54 肌・55 変身後名・56 変身後呼び名・57 前髪・58 髪型（:93–104）。
  登録された値と現在の値を EXCHANGE_CSTR で入れ替える（悪堕ち時に入れ替え、復帰時にもう一度入れ替えて戻す）。

原作どおりの点（照原作移植）：
- 一部の SETBIT／代入が ARG ではなく TARGET のキャラに書かれる：CORRUPT_CHANGE_LOOKS_MAIN の `SETBIT CFLAG:80, n`（:33／:41／:47／:53／
  :59／:65）、CORRUPT_CHANGE_LOOKS の `CSTR:1 == CSTR:0`（:160）・`CFLAG:42 = 0`（:193／:205）、RECOVER_CORRUPTION の
  `CFLAG:81 == 0b1111`（:47）・`CLEARBIT CFLAG:80, 2`（:58）。既存の呼び出し元（PRISON.ERB:360、SHOP_TURNEND.ERB:913、
  AFTER_RESCUED.ERB:30）はどれも ARG = TARGET。オープニング（オープニング処理.ERB:248）は ARG = LOCAL で TARGET と異なりうる。
- 変身後名の改竄（:145–165）は CFLAG:ARG:2（変身後名の登録）を見ない：未登録なら CSTR:55 は空（CORRUPT_GET_SPNAME:272–273 で
  RETURN）なので CSTR:0 が空になる。
- 髪色候補 `DATA 232//200//0`（:547）は行末にタブがあり、値にタブが含まれる（行末の空白は除かれない：Sub/EraStreamReader.cs:62–95、
  GameProc/LogicalLineParser.cs:426–434、GameProc/Function/ArgumentBuilder.cs:348–363）→ SETCOLOR_BY_STR の ISNUMERIC で失敗し色が付かない。
- CORRUPTTION_GET_NANORI_FINAL の `FIRSTSETTING_CHANGINGCALL_DETAIL(ARG:0, LOCAL)`（:790）の LOCAL はこの関数で一度も代入されない
  静的 LOCAL（常に 0）→ 性格 0 の分岐（強気系）。`REPLACE LOCALS:1,…` は式中関数を命令として使う形なので結果は RESULTS に入り
  LOCALS:1 は変わらない（Instraction.Child.cs:390–409）→ 以降の REPLACE は RESULTS を順に置換（:794–807）。
- STRDATA は `RAND(件数)` で 1 件（Process.ScriptProc.cs:730–755）。REPLACE は .NET の Regex（Creator.Method.cs@ReplaceMethod:2452–2474）。
"""

from __future__ import annotations

import re

from .action import Ctx, config_check_prison, print_transcallname, print_transname
from .battle.core import run_chinobun
from .chara_common import talent

# --- STRDATA（CORRPUTION.ERB）-----------------------------------------------------------------------
# :285–340 DARK_NOUN（55 件）、:349–379 DARK_NOUN:1（30 件）
_SP_DOWN = (
    "ダーク", "ヘル", "イビル", "シャドウ", "キラー", "レイス", "バンシー", "カオス", "テンタクル", "マリス", "デーモン", "サキュバス",
    "ナイトメア", "サキュメア", "プッシー", "スレイブ", "コラプション", "スローター", "ブッチャー", "エクゼキューショナー", "コラプター",
    "スレイブ", "ブリーダー", "デバステイター", "デストロイヤー", "フォールン", "エクリプス", "リバース", "トゥルース", "プレジャー",
    "エクスタシー", "アンチェインド", "ルインド", "リベレーター", "ターミネーター", "イビルクイーン", "エンプレス", "アウォークン",
    "イビルマザー", "インキュベータ", "スカージ", "ネメシス", "カロン", "ルシファー", "アナザー", "ビースト", "リリス", "アポカリプス",
    "カラミティ", "ウィックド", "ヴィシャス", "エクスターミネーター", "カームブリンガー", "ピースブリンガー", "ヘヴンブリンガー",
)
_SP_UP = (
    "ダーク", "ヘル", "イビル", "シャドウ", "キラー", "レイス", "バンシー", "カオス", "テンタクル", "デーモン", "サキュバス", "ナイトメア",
    "サキュメア", "プッシー", "スレイブ", "コラプト", "ブリード", "デストロイ", "フォールン", "リバース", "プレジャー", "チェインド",
    "ルインド", "ネメシス", "アナザー", "ビースト", "リリス", "アポカリ", "カラミティ", "ヴィシャス",
)
_FRONT_HAIR = ("かきあげ", "ぱっつん", "斜めぱっつん", "シャギーカット", "まゆ上ぱっつん")  # :493–499
_HAIR_ADJ = ("ゆるふわ", "フェミニン", "艶やか", "妖艶な", "スパイラル")  # :509–515
_HAIR_LOOSE = ("ウェーブロング", "ロングヘア")  # :518–521
_HAIR_COLORS = (  # :537–562（:547 は行末のタブ込み：モジュール docstring）
    "199//79//144", "222//67//53", "239//147//182", "227//180//102", "232//200//0\t", "93//194//136", "11//116//175",
    "109//82//171", "194//162//218", "241//241//241", "147//147//147", "115//108//121",
)
_EYE_ADJ = ("妖艶な", "煽情的な", "艶めかしい", "小悪魔的な", "妖しく光る", "蠱惑的な", "劣情を誘う", "挑発的な")  # :578–587
_EYE_COLORS = (  # :639–665
    "185//30//104", "131//39//78", "237//81//78", "179//125//64", "255//188//0", "77//165//115", "81//106//57",
    "57//158//204", "65//79//163", "162//96//191", "201//73//162", "207//97//165",
)
_THEME_SLAVE = ("淫奴", "賤奴", "肉奴", "妓奴", "触奴", "淫畜", "賤畜", "肉畜", "母畜", "淫穴", "賤穴", "爛穴", "臭穴")  # :681–699
_THEME_NAEDOKO = ("淫畜", "賤畜", "母畜", "孕袋", "産畜", "魔母", "孕畜", "苗床")  # :702–711
_THEME_OTHER = ("触手", "淫魅", "蜜穴", "性奴", "腐穴", "汁穴", "媚穴", "奴隸", "淫毒")  # :713–723
_THEME_TAIL = ("娼婦", "便器", "便女", "便所")  # :725–730
_NANORI_A = (  # :737–753
    "お触手様の", "産まれた時から", "夢はみんなの", "お触手チンポの", "戦士失格", "あっさり堕ちた", "女性失格", "人間廃業", "少女廃業",
    "お精子中毒", "お精子コキ捨て", "お触手ズボズボ", "ザーメン大好き", "セックス中毒", "卑しい雌穴",
)
_NANORI_A1 = ("性奴隷", "便器妻", "ハメ便女", "オナホール", "生オナホ", "雌オナホ", "ハメオナホ", "肉オナホ", "オナホ穴", "豚オナホ")  # :754–765
_NANORI_B = ("おちんぽハメハメ", "お触手ハメハメ", "お触手オナホ", "お触手即イキ", "淫乱ハメハメ", "淫乱オナホ", "淫乱ビッチ",
             "生ハメビッチ")  # :767–776
_NANORI_B1 = ("性奴隷", "便器妻", "便器穴", "肉便器", "豚便器")  # :777–783
# :794–807 の REPLACE（LOCALS:1 の 1 回目の結果は RESULTS に入り、以降は RESULTS を順に置換）
_NANORI_REPLACE = (
    ("参上", "無様に参上"), ("見参", "無様に見参"), ("推参", "無様に推参"), ("準備完了", "生ハメ待機"), ("行く", "イク"), ("行き", "イキ"),
    ("殲滅開始", "オナニー開始"), ("負けない", "イキ果てる"), ("覚悟してね", "早くレイプしてね"), ("覚悟しなさい", "早く犯して"),
    ("始めよう", "ハメハメしよう"), ("始動じゃ", "穴は濡れまくりじゃ"), ("やるしか", "孕まされるしか"),
)

# 汎用関数/SETCOLOR_BY_STR.ERB:16–44 の色名
_COLOR_BY_NAME = {
    "赤": (255, 8, 8), "レッド": (255, 8, 8), "緑": (8, 255, 125), "グリーン": (8, 255, 125), "青": (8, 125, 255),
    "ブルー": (8, 125, 255), "黄": (245, 245, 125), "イエロー": (245, 245, 125), "金": (255, 255, 8), "ブロンド": (255, 255, 8),
    "ゴールド": (255, 255, 8), "紫": (255, 8, 255), "パープル": (255, 8, 255), "橙": (255, 125, 8), "オレンジ": (255, 125, 8),
    "桃": (255, 8, 125), "ピンク": (255, 8, 125), "銀": (200, 200, 255), "シルバー": (200, 200, 255), "茶": (88, 8, 8),
    "ブラウン": (88, 8, 8), "ブルネット": (88, 8, 8), "黒": (40, 24, 24), "ブラック": (40, 24, 24), "肌色": (255, 200, 180),
    "褐色": (183, 86, 17), "色白": (255, 236, 220),
}


def setcolor_by_str(ctx: Ctx, color: str) -> int:
    """`汎用関数/SETCOLOR_BY_STR.ERB@SETCOLOR_BY_STR, COLOR_STR`:10–55（色名か `R//G//B`。それ以外は -1 で色を変えない）。
    ISNUMERIC／TOINT は 10 進の数字列のみ（Creator.Method.cs@IsNumericMethod:2532–2569、@ToIntMethod:2357–2387）。"""
    rgb = _COLOR_BY_NAME.get(color)
    if rgb is None:
        parts = color.split("//")  # SPLIT（Process.ScriptProc.cs:522–538）
        if len(parts) != 3 or not all(re.fullmatch(r"[+-]?[0-9]+", p) for p in parts):
            return -1
        rgb = tuple(int(p) for p in parts)  # type: ignore[assignment]
    ctx.out.set_color(tuple(max(0, min(255, v)) for v in rgb))  # type: ignore[arg-type]
    return 0


def _strdata(ctx: Ctx, items: tuple[str, ...]) -> str:
    return items[ctx.state.rng.rand(len(items))]


def _exchange_cstr(ctx: Ctx, who: int, a: int, b: int) -> None:
    """`@EXCHANGE_CSTR, ARG, ARG:1, ARG:2`:221–233。"""
    c = ctx.state.charas[who]
    c.cstr[a], c.cstr[b] = c.cstr[b], c.cstr[a]


def _henshin(ctx: Ctx, who: int) -> bool:
    return talent(ctx.data, ctx.state.charas[who], "変身能力") == 1


# --- CORRUPT_CHANGE_LOOKS_MAIN ----------------------------------------------------------------------


def corrupt_change_looks_main(ctx: Ctx, who: int) -> int:
    """`@CORRUPT_CHANGE_LOOKS_MAIN, ARG`:17–100。"""
    st = ctx.state
    c = st.charas[who]
    tgt = st.charas[st.target]  # SETBIT CFLAG:80 は TARGET（モジュール docstring）
    if config_check_prison(st, 4) == 0:  # :20–21
        return 1
    if _henshin(ctx, who):  # :24–25
        corrupt_get_spname(ctx, who)
    if c.cflag[34] == 0:  # :29–30 プロフィール未設定
        return 1
    if not c.cflag.get_bit(80, 0):  # :32–33（SETBIT は :33）
        tgt.cflag.set_bit(80, 0)
    get_corrupted_eyes(ctx, who)  # :36
    if not c.cflag.get_bit(80, 3) and config_check_prison(st, 5) == 1:  # :39–42
        get_corrupted_hair(ctx, who)
        tgt.cflag.set_bit(80, 3)
    if not c.cflag.get_bit(80, 4) and config_check_prison(st, 6) == 1:  # :45–48
        corrupt_change_hair_color(ctx, who)
        tgt.cflag.set_bit(80, 4)
    if not c.cflag.get_bit(80, 5) and config_check_prison(st, 7) == 1:  # :51–54
        corrupt_change_eye_color(ctx, who)
        tgt.cflag.set_bit(80, 5)
    if (not c.cflag.get_bit(80, 1) and c.exp[ctx.data.index_of("EXP", "陥落経験")] >= 3
            and config_check_prison(st, 8) == 1):  # :57–60
        corrupt_change_skin(ctx, who)
        tgt.cflag.set_bit(80, 1)
    corrupt_change_looks(ctx, who)  # :63
    tgt.cflag.set_bit(80, 2)  # :65
    if config_check_prison(st, 5) == 1 or config_check_prison(st, 6) == 1:  # :69–72
        if c.cflag.get_bit(80, 3) or (c.cflag.get_bit(80, 4) and not c.cflag.get_bit(81, 0)):
            run_chinobun(ctx, "MESSAGE_CORRUPT_CHANGE_LOOKS_HAIR", (who,))
    if not c.cflag.get_bit(81, 4):  # :75–76
        run_chinobun(ctx, "MESSAGE_CORRUPT_CHANGE_LOOKS_EYES", (who,))
    if config_check_prison(st, 8) == 1:  # :78–81
        if c.cflag.get_bit(80, 1) and not c.cflag.get_bit(81, 3):
            run_chinobun(ctx, "MESSAGE_CORRUPT_CHANGE_LOOKS_SKIN", (who,))
    if _henshin(ctx, who) and c.cflag[2] == 1:  # :84–85
        run_chinobun(ctx, "MESSAGE_CORRUPT_CHANGE_SP_NAME", (who,))
    return 0


def corrupt_change_looks(ctx: Ctx, who: int) -> None:
    """`@CORRUPT_CHANGE_LOOKS, ARG`:102–217：登録済みの容姿（CSTR:50〜）と現在の容姿を入れ替える。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[who]
    tgt = st.charas[st.target]
    if _henshin(ctx, who):  # :110–123
        hairstyle, haircolor, reye, leye, skin = 14, 31, 34, 35, 37
    else:
        hairstyle, haircolor, reye, leye, skin = 13, 30, 32, 33, 36
    _exchange_cstr(ctx, who, 50, 18)  # :126 目つき
    if c.cflag.get_bit(80, 3) and config_check_prison(st, 5) == 1:  # :128–131 髪型
        _exchange_cstr(ctx, who, 57, 12)
        _exchange_cstr(ctx, who, 58, hairstyle)
    if c.cflag.get_bit(80, 4) and config_check_prison(st, 6) == 1:  # :133–134 髪色
        _exchange_cstr(ctx, who, 51, haircolor)
    if c.cflag.get_bit(80, 5) and config_check_prison(st, 7) == 1:  # :136–139 目色
        _exchange_cstr(ctx, who, 52, reye)
        _exchange_cstr(ctx, who, 53, leye)
    if c.cflag.get_bit(80, 1) and config_check_prison(st, 8) == 1:  # :141–142 肌
        _exchange_cstr(ctx, who, 54, skin)
    if _henshin(ctx, who):  # :145–166 変身後名の改竄
        if not c.cflag.get_bit(13, 0):
            c.cflag.set_bit(13, 0)
            out.printl(f"{print_transname(st, who)}の変身後名が書き換えられてゆく……")
            out.set_color((96, 96, 96))
            out.printl(f"　　　　{c.cstr[0]}")
            _exchange_cstr(ctx, who, 55, 0)
            setcolor_by_str(ctx, "紫")
            out.printl(f"　　　　　————{c.cstr[0]}")
            out.reset_color()
            out.printw()
            # :160 `CSTR:1 == CSTR:0` は TARGET のキャラ（ARG ではない：原作どおり）
            if not c.cflag.get_bit(13, 1) and tgt.cstr[1] == tgt.cstr[0]:
                c.cflag.set_bit(13, 1)
                _exchange_cstr(ctx, who, 56, 1)
    if talent(data, c, "完堕ち") == 1:  # :168–211
        if _henshin(ctx, who):
            if not c.cflag.get_bit(13, 3):  # :171–188 名乗りの改竄
                c.cflag.set_bit(13, 3)
                out.printl(f"{print_transname(st, who)}の決め台詞が書き換えられていく……")
                corruption_get_theme(ctx, who)
                out.set_color((96, 96, 96))
                out.printl(f"　{c.cstr[3]}")
                corruption_get_nanori_final(ctx, who)
                setcolor_by_str(ctx, "橙")
                out.printl(f"　　————{c.cstr[3]}")
                out.reset_color()
                out.printw()
            if c.cflag[41] != 402:  # :191–198 淫縛の鎖
                c.cflag[41] = 402
                tgt.cflag[42] = 0  # :193 `CFLAG:42 = 0` は TARGET
                setcolor_by_str(ctx, "桃")
                out.printl(f"{print_transname(st, who)}の変身後衣装が【{data.names['ITEM'].get(402, '')}】になった！")
                out.reset_color()
                out.printw()
        else:
            if c.cflag[40] != 196:  # :203–210 触手の花嫁
                c.cflag[40] = 196
                tgt.cflag[42] = 0  # :205
                setcolor_by_str(ctx, "桃")
                out.printl(f"{print_transname(st, who)}の衣装が【{data.names['ITEM'].get(196, '')}】になった！")
                out.reset_color()
                out.printw()


def corrupt_change_hair_color(ctx: Ctx, who: int) -> int:
    """`@CORRUPT_CHANGE_HAIR_COLOR, ARG`:240–254。"""
    c = ctx.state.charas[who]
    if c.cstr[51] != "":
        return 1
    c.cstr[51] = get_corrupted_hair_color(ctx, c.cstr[31] if _henshin(ctx, who) else c.cstr[30])
    return 0


def corrupt_get_spname(ctx: Ctx, who: int) -> int:
    """`@CORRUPT_GET_SPNAME, ARG`:262–410：悪堕ち変身名（CSTR:55・56）。"""
    st = ctx.state
    c = st.charas[who]
    up = c.cstr[201]
    down = c.cstr[202]
    if c.cflag[2] == 0:  # :272–273
        return 1
    if c.cstr[55] != "":  # :275–276
        return 1
    up = up.replace("・", "")  # :279 `REPLACE(STR_UP, "・", "")`（正規表現としても「・」1 文字）
    noun = _strdata(ctx, _SP_DOWN)  # :285
    noun1 = _strdata(ctx, _SP_UP)  # :349
    rand = st.rng.rand
    if up == "" and down == "":  # :387–392
        c.cstr[55] = f"{c.cstr[0]}・{noun}" if rand(2) == 0 else f"{noun}・{c.cstr[0]}"
    elif st.flag[6] == 1 and st.savestr[11] == up:  # :396–397
        c.cstr[55] = f"{noun1}{down}"
    elif rand(2) == 0:  # :401–402
        c.cstr[55] = f"{up}・{noun}"
    else:
        c.cstr[55] = f"{noun1}・{down}"
    c.cstr[56] = c.cstr[55]  # :407
    return 0


def corrupt_change_skin(ctx: Ctx, who: int) -> int:
    """`@CORRUPT_CHANGE_SKIN, ARG`:417–430。"""
    c = ctx.state.charas[who]
    if c.cstr[54] != "":
        return 1
    c.cstr[54] = get_corrupted_skin(ctx, c.cstr[37] if _henshin(ctx, who) else c.cstr[36])
    return 0


def get_corrupted_skin(ctx: Ctx, args: str) -> str:
    """`@GET_CORRUPTED_SKIN, ARGS`:440–472。"""
    if args in ("183//86//17", "褐色"):
        return _strdata(ctx, ("40//24//24", "255//236//220"))
    if args in ("255//236//220", "色白"):
        return _strdata(ctx, ("40//24//24", "183//86//17"))
    if args in ("40//24//24", "黒"):
        return "255//236//220"
    return _strdata(ctx, ("40//24//24", "183//86//17", "255//236//220"))


def get_corrupted_hair(ctx: Ctx, who: int) -> int:
    """`@GET_CORRUPTED_HAIR, ARG`:479–526：前髪（CSTR:57）と髪型（CSTR:58）。"""
    c = ctx.state.charas[who]
    hair = c.cstr[14] if _henshin(ctx, who) else c.cstr[13]
    if c.cstr[57] == "" and c.cstr[12] in ("目隠れ", "ぼさぼさ"):  # :492–501
        c.cstr[57] = _strdata(ctx, _FRONT_HAIR)
    elif c.cstr[57] == "":
        c.cstr[57] = c.cstr[12]
    if c.cstr[58] != "":  # :505–506
        return 0
    adj = _strdata(ctx, _HAIR_ADJ)  # :509
    if hair in ("三つ編み", "おさげ", "一本結び"):  # :517–522
        hair = _strdata(ctx, _HAIR_LOOSE)
    c.cstr[58] = f"{adj}{hair}"
    return 0


def get_corrupted_hair_color(ctx: Ctx, args: str) -> str:
    """`@GET_CORRUPTED_HAIR_COLOR, ARGS`:533–567（元の色と同じなら引き直す）。"""
    while True:
        v = _strdata(ctx, _HAIR_COLORS)
        if v != args:
            return v


def get_corrupted_eyes(ctx: Ctx, who: int) -> int:
    """`@GET_CORRUPTED_EYES, ARG`:572–595：目つき（CSTR:50）。"""
    c = ctx.state.charas[who]
    if c.cstr[50] != "":
        return 1
    adj = _strdata(ctx, _EYE_ADJ)
    c.cstr[50] = f"{adj}瞳" if c.cstr[18] == "普通" else f"{adj}{c.cstr[18]}"
    return 0


def corrupt_change_eye_color(ctx: Ctx, who: int) -> int:
    """`@CORRUPT_CHANGE_EYE_COLOR, ARG`:600–629（元がオッドアイ、または 10% でオッドアイ）。"""
    st = ctx.state
    c = st.charas[who]
    if _henshin(ctx, who):
        reye, leye = c.cstr[34], c.cstr[35]
    else:
        reye, leye = c.cstr[32], c.cstr[33]
    if c.cstr[52] == "":
        c.cstr[52] = get_corrupted_eye_color(ctx, reye)
    if c.cstr[53] != "":
        return 1
    if reye != leye or st.rng.rand(10) == 0:  # :620（|| の短絡：REYE != LEYE なら RAND を引かない）
        while True:
            c.cstr[53] = get_corrupted_eye_color(ctx, leye)
            if c.cstr[53] != c.cstr[52]:
                break
    else:
        c.cstr[53] = c.cstr[52]
    return 0


def get_corrupted_eye_color(ctx: Ctx, args: str) -> str:
    """`@GET_CORRUPTED_EYE_COLOR, ARGS`（#FUNCTIONS）:634–670。"""
    while True:
        v = _strdata(ctx, _EYE_COLORS)
        if v != args:
            return v


def corruption_get_theme(ctx: Ctx, who: int) -> None:
    """`@CORRUPTTION_GET_THEME, ARG`:678–731：完堕ちキャラ個別の冠名（CSTR:60、PRINT_THEME が優先して返す）。"""
    c = ctx.state.charas[who]
    tl = lambda n: talent(ctx.data, c, n)  # noqa: E731
    if tl("嬲られ体質") > 0 or tl("触手の虜") > 0:
        noun = _strdata(ctx, _THEME_SLAVE)
    elif tl("苗床化") > 0:
        noun = _strdata(ctx, _THEME_NAEDOKO)
    else:
        noun = _strdata(ctx, _THEME_OTHER)
    noun1 = _strdata(ctx, _THEME_TAIL)
    c.cstr[60] = f"{noun}{noun1}"


def _print_theme(ctx: Ctx, who: int) -> str:
    """`汎用関数/コモン関数.ERB@PRINT_THEME(ARG)`:289–293（ARG == 0 なら TARGET）。"""
    st = ctx.state
    c = st.charas[who if who != 0 else st.target]
    return c.cstr[60] if c.cstr[60] != "" else st.savestr[10]


def corruption_get_nanori_final(ctx: Ctx, who: int) -> None:
    """`@CORRUPTTION_GET_NANORI_FINAL(ARG)`:733–816：名乗り（CSTR:3）の改竄、CFLAG:5 = 1。"""
    from .opening import changingcall_detail

    st = ctx.state
    c = st.charas[who]
    if st.rng.rand(100) <= 90:  # :735 SELECTCASE RAND:100、CASE 0 TO 90
        a = _strdata(ctx, _NANORI_A)
        a1 = _strdata(ctx, _NANORI_A1)
    else:
        a = _strdata(ctx, _NANORI_B)
        a1 = _strdata(ctx, _NANORI_B1)
    # :786 `CALL STRMATCH(CSTR:ARG:3, CSTR:ARG:55)`（汎用関数/コモン関数.ERB:1378–1393）：STRFINDU が -1 なら RESULTS:2 を
    # 書かない（RESULTS:0／1 だけ空にする）→ :787 の RESULTS:2 は前の値（Python では RESULTS を共用していないので再現できない）
    src, word = c.cstr[3], c.cstr[55]
    # StrfindMethod(unicode):2264–2273（空の target は -1）。UNVERIFIED: IndexOf の文化依存比較を序数比較で代用（unresolved.md S21）
    idx = src.find(word) if src != "" else -1
    st.result[0] = 0  # STRMATCH の RETURN
    if idx < 0:
        raise NotImplementedError("STRMATCH 不成立時の RESULTS:2（前回の値）は再現できない（CORRUPTTION_GET_NANORI_FINAL:786–791）")
    after = src[idx + len(word):]
    if after != "":  # :787–791
        locals1 = after
    else:
        locals1 = changingcall_detail(st, 0)  # LOCAL は静的で未代入（常に 0：モジュール docstring）
    results = re.sub("[！？♪]", "❤", locals1)  # :794
    for pat, rep in _NANORI_REPLACE:  # :795–807
        results = results.replace(pat, rep)
    locals1 = results + "❤❤"  # :809
    c.cstr[3] = f"{a}{a1}❤ {_print_theme(ctx, who)}{c.cstr[0]}{locals1}"  # :812–813
    c.cflag[5] = 1  # :816


# --- RECOVER_CORRUPTION（CORRUPTION_RECOVER.ERB）-----------------------------------------------------


def recover_corruption(ctx: Ctx, who: int) -> int:
    """`@RECOVER_CORRUPTION, ARG`:6–60：救出後（AFTER_RESCUED:29–30、CFLAG:80 bit 2 のとき）の容姿復帰と定着。"""
    st, data = ctx.state, ctx.data
    c = st.charas[who]
    tgt = st.charas[st.target]
    rand = st.rng.rand
    exp_corrupt = c.exp[data.index_of("EXP", "陥落経験")]  # :8
    if config_check_prison(st, 4) == 0:  # :11–12
        return 1
    if c.cflag[34] == 0:  # :15–16
        return 1
    if not c.cflag.get_bit(80, 0):  # :19–20
        return 1
    henshin = _henshin(ctx, who)
    # :23–26 髪（`&&` の短絡：前の条件が成り立つときだけ RAND を引く）
    if c.cflag.get_bit(80, 4) and not c.cflag.get_bit(81, 0) and rand(100) <= exp_corrupt * 15:
        c.cstr[51] = c.cstr[31] if henshin else c.cstr[30]  # STAIN_CORRUPTED_HAIR_COLOR:64–72
        run_chinobun(ctx, "MESSAGE_STAIN_CORRUPTED_HAIR_COLOR", (who,))
        c.cflag.set_bit(81, 0)
    if c.cflag.get_bit(80, 5) and not c.cflag.get_bit(81, 1) and rand(100) <= (exp_corrupt - 1) * 15:  # :29–32 右目
        c.cstr[52] = c.cstr[34] if henshin else c.cstr[32]
        run_chinobun(ctx, "MESSAGE_STAIN_CORRUPTED_EYE_COLOR_RIGHT", (who,))
        c.cflag.set_bit(81, 1)
    if c.cflag.get_bit(80, 5) and not c.cflag.get_bit(81, 2) and rand(100) <= (exp_corrupt - 1) * 15:  # :35–38 左目
        c.cstr[53] = c.cstr[35] if henshin else c.cstr[33]
        run_chinobun(ctx, "MESSAGE_STAIN_CORRUPTED_EYE_COLOR_LEFT", (who,))
        c.cflag.set_bit(81, 2)
    if c.cflag.get_bit(80, 1) and not c.cflag.get_bit(81, 3) and rand(100) <= (exp_corrupt - 1) * 15:  # :41–44 肌
        c.cstr[54] = c.cstr[37] if henshin else c.cstr[36]
        run_chinobun(ctx, "MESSAGE_STAIN_CORRUPTED_SKIN_COLOR", (who,))
        c.cflag.set_bit(81, 3)
    # :47–52 陥落経験 10 超または全定着（`CFLAG:81 == 0b1111` は TARGET のキャラ）で完堕ち
    if talent(data, c, "完堕ち") == 0 and (exp_corrupt > 10 or tgt.cflag[81] == 0b1111):
        c.cstr[50] = c.cstr[18]
        run_chinobun(ctx, "MESSAGE_CORRUPTION_FINAL", (who,))
        c.cflag.set_bit(81, 4)
        c.talent[data.index_of("TALENT", "完堕ち")] = 1
    corrupt_change_looks(ctx, who)  # :55
    tgt.cflag.set_bit(80, 2, False)  # :58 `CLEARBIT CFLAG:80, 2` は TARGET
    return 0
