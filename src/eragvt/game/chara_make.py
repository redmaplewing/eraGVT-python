"""汎用キャラ（`ADDCHARA 0`、呼び名「汎用キャラ」）のランダム生成。

原作の既定の開局（キャラメイク画面で何も設定せず `[1000]★キャラメイクを完了する（未設定のキャラはおまかせ）`）で
`CHARA_MAKE_FINALIZE` → `CHARA_MAKE_INITIALIZE` から呼ばれる部分。路徑相對
`source/earGVP/ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB`（以下「DEFAULT」）。

Emuera 語意：`&&`／`||` は短絡評価（reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:524–555）、
`RAND:n` は 0〜n-1。乱数は `GameRng` から ERB の評価順に引く（系列そのものは Emuera の MT と一致させない：
deviations.md「乱数」）。
"""

from __future__ import annotations

from ..data.csv_loader import GameData
from ..state import GameState
from ..state.character import Character
from .body import chara_make_age_setting, chara_size_default, generate_bodyline
from .chara_common import is_female, is_male, seikaku_check, syuzoku_check, talent

# --- 種族（DEFAULT@CHARA_MAKE_INITIALIZE:8–72）---------------------------------------------

# FLAG:823（共通設定「種族」、CHARA_MAKE.ERB:18 で GLOBAL:21 から読む）→ 付与する素質（:12–35）
_RACE_BY_SETTING: dict[int, tuple[str, ...]] = {
    1: ("人間",), 2: ("異能力者",), 3: ("魔法使い",), 4: ("ロボっ子",), 5: ("天使",), 6: ("魔族",), 7: ("鬼",),
    8: ("妖精族",), 9: ("ケモミミ族",), 10: ("ヴァンパイア", "夜魔の貴族"), 11: ("ポリニアン",),
}

# :37–66 LOCAL = RAND:24 + 201 の分岐（210 は RAND:2 == 0 のときだけヴァンパイア、他はすべて人間）
_RACE_BY_ROLL: dict[int, tuple[str, ...]] = {201 + k - 1: v for k, v in _RACE_BY_SETTING.items() if k != 10}

# :78–114 LOCAL = RAND:18 + 10 → 性格素質
PERSONALITIES = (
    "臆病", "恥ずかしがり屋", "勝気", "元気っ子", "おっとり", "面倒くさがり", "真面目", "楽天家", "悲観的",
    "素直", "ツンデレ", "ヤンデレ", "無口", "おしゃべり", "古風", "かるい性格", "意地っ張り", "乱暴者",
)


def _set(data: GameData, c: Character, name: str, value: int = 1) -> None:
    c.talent[data.index_of("TALENT", name)] = value


def initialize_race(state: GameState, data: GameData, sel: int) -> None:
    """DEFAULT:8–72：種族が未設定（SYUZOKU_CHECK "GET_SYUZOKU_VALUE" == 0）なら自動設定。"""
    c = state.charas[sel]
    if syuzoku_check(c) != 0:
        return
    rng = state.rng
    if state.flag[823] > 0:  # :12–35
        for name in _RACE_BY_SETTING.get(state.flag[823], ()):
            _set(data, c, name)
    else:  # :36–66
        local = rng.rand(24) + 201
        if local in _RACE_BY_ROLL:
            names = _RACE_BY_ROLL[local]
        elif local == 210 and rng.rand(2) == 0:  # :58（短絡：LOCAL == 210 のときだけ RAND:2）
            names = ("ヴァンパイア", "夜魔の貴族")
        else:  # :63–65 人間が出やすいように
            names = ("人間",)
        for name in names:
            _set(data, c, name)
    # :68–71 フィートの自動設定（FLAG:824 = 共通設定「フィート自動割り当て」、既定 0＝なし）
    if state.flag[824] == 1:
        raise NotImplementedError("SET_FEAT_DEFAULT（DEFAULT:1500、FLAG:824 == 1）は未移植")


def initialize_personality(state: GameState, data: GameData, sel: int) -> None:
    """DEFAULT:74–165：性格が未設定（SEIKAKU_CHECK_F == 0）なら性格ガチャ・BASE の性格補正・一人称。"""
    from .action import seikaku_hosei  # action → opening の循環を避ける

    c = state.charas[sel]
    if seikaku_check(data, c) != 0:
        return
    if state.flag[825] != 0:
        # :129–138 口上あり限定（TRYCCALLFORM KOJO_0_COLOR_{LOCAL}）。既定の FLAG:825（GLOBAL:23）は 0。
        raise NotImplementedError("性格ガチャの口上あり限定（FLAG:825 == 1）は未移植")
    # :77–140 WHILE の 1 周目：RAND:18 + 10 の素質を立てる。他キャラとの被りチェック（:118–124）は local:1 を
    # 進めるだけで、FLAG:825 == 0 なら :126–127 で BREAK するので結果に影響しない。
    _set(data, c, PERSONALITIES[state.rng.rand(18)])
    # :141–153 体力などの BASE を性格補正（SEIKAKU_HOSEI_F）し、MAXBASE にも
    seikaku = seikaku_check(data, c)
    for k in range(7):
        b = k if k <= 2 else k + 7
        c.base[b] = seikaku_hosei(seikaku, b, c.base[b])
        c.maxbase[b] = c.base[b]
    # :155–164 一人称（CFLAG:8 が 0 のときだけ）
    if c.cflag[8]:
        pass
    elif talent(data, c, "古風"):
        c.cflag[8] = 20
    elif talent(data, c, "かるい性格"):
        c.cflag[8] = 11
    else:
        c.cflag[8] = 0


# --- CHARA_MAKE_BASE_PROFILE の汎用キャラ分岐（DEFAULT:507–980）------------------------------------


def base_profile_generic(state: GameState, data: GameData, sel: int) -> None:
    """DEFAULT@CHARA_MAKE_BASE_PROFILE:507–980（呼び名が「汎用キャラ」＝未初期化キャラ）。"""
    from .opening import changingcall_detail

    c = state.charas[sel]
    rng = state.rng
    # :508–512 女性なら処女・清純派
    if is_female(data, c):
        _set(data, c, "処女")
        _set(data, c, "清純派")
    # :513–520
    generate_bodyline(state, data, c)
    chara_make_age_setting(state, data, c)
    chara_make_status_talent(state, data, sel)
    chara_make_status_talent_flavor(state, data, sel)
    chara_size_default(data, c)
    # :524–529 髪型（STR:30000〜 前髪、STR:30100〜 後ろ髪）
    s = data.str_defaults
    c.cstr[12] = s.get(30000 + rng.rand(9), "")
    c.cstr[13] = s.get(30100 + rng.rand(15), "")
    c.cstr[14] = c.cstr[13]
    if rng.rand(2) == 0:
        c.cstr[14] = s.get(30100 + rng.rand(15), "")
    # :531–534 人間には必ず変身能力
    if talent(data, c, "人間") == 1:
        _set(data, c, "変身能力")
    # :539–542
    if talent(data, c, "変身能力") == 1 and c.cflag[41] == 0:
        c.cflag[41] = 200
    # :546–900 名前と外見
    surname_no, surname, given = _random_name_and_looks(state, data, c)
    # :902–913
    if surname_no < 3500 or 16000 <= surname_no < 16500:
        full = surname + given
    elif 19000 <= surname_no < 19100:
        full = f"{surname}・{given}"
    else:
        full = f"{given}・{surname}"
    c.name = full
    c.callname = given
    c.cstr[10] = surname
    if c.callname != "":  # :915–916
        c.cstr[200] = c.callname
    # :919–960 共通設定からの変身名（汎用キャラ用）
    if c.cstr[0] == "" and talent(data, c, "変身能力") == 1:
        head = state.savestr[11]
        tail = c.callname
        if state.flag[820] > 0:
            raise NotImplementedError("RANDOMNAMING_FROMGENRE（FLAG:820 > 0）は未移植")
        if head + tail != "":
            c.cstr[0] = head + tail
            c.cstr[201] = head
            c.cstr[202] = tail
            c.cflag[2] = 1
            if c.cstr[3] == "":
                c.cstr[3] = state.savestr[10] + c.cstr[0] + changingcall_detail(state, seikaku_check(data, c))
                c.cflag[5] = 1
    # :962–969 一人称を低確率で変更（|| は短絡：RAND:20 が先）
    if rng.rand(20) == 0 or is_male(data, c):
        if rng.rand(2) == 0:
            c.cflag[8] = 25 + rng.rand(3)
        else:
            c.cflag[8] = 30 + rng.rand(3)
    # :972–979
    if c.cstr[1] == "" and c.cstr[0] != "":
        c.cstr[1] = c.cstr[0]
        c.cflag[3] = 1
    if c.cstr[2] == "" and state.savestr[12] != "":
        c.cstr[2] = state.savestr[12]
        c.cflag[4] = 1
    # :980 GENERATE_BODYLINE の成長曲線を 1 で上書きする（原作どおり）
    c.cflag[34] = 1


# :560–593／:704–742 名前の言語（FLAG:822、FLAG:821）→ (RAND の幅, 基点)
_GIVEN_JP_SURNAME = {1: (500, 12000), 2: (1000, 12500), 3: (500, 13500), 4: (1000, 14000), 5: (500, 15000),
                     6: (500, 15500), 7: (1000, 16500), 8: (500, 18000)}
_GIVEN_FOREIGN = {1: (500, 12000), 2: (1000, 12500), 3: (500, 13500), 4: (1000, 14000), 5: (500, 15000),
                  6: (500, 15500), 7: (1000, 16500), 8: (500, 19200), 9: (500, 18000)}
_SURNAME_FOREIGN = {2: (2000, 3500), 3: (2000, 5500), 4: (1500, 7500), 5: (2000, 9000), 6: (1000, 11000),
                    7: (500, 16000)}


def _str(data: GameData, i: int) -> str:
    return data.str_defaults.get(i, "")


def _chinese_second_char(state: GameState, data: GameData, name: str) -> str:
    """:595–600／:744–749 中国語は単漢字の組み合わせ（`FLAG:822 == 7 && RAND:2`：短絡）。"""
    if state.flag[822] == 7 and state.rng.rand(2):
        i = state.rng.rand(1000) + 16500
        while _str(data, i) == "":
            i = state.rng.rand(1000) + 16500
        name += _str(data, i)
    return name


def _set_colors(c: Character, hair: str | None = None, eyes: str | None = None, skin: str | None = None) -> None:
    if hair is not None:
        c.cstr[30] = c.cstr[31] = hair
    if eyes is not None:
        c.cstr[32] = c.cstr[33] = c.cstr[34] = c.cstr[35] = eyes
    if skin is not None:
        c.cstr[36] = c.cstr[37] = skin


def _random_name_and_looks(state: GameState, data: GameData, c: Character) -> tuple[int, str, str]:
    """DEFAULT:546–900：苗字・名前（STR）と髪・瞳・肌の色（CSTR:30–37）。戻り値は (苗字の STR 番号, 苗字, 名前)。"""
    rng = state.rng
    f821, f822 = state.flag[821], state.flag[822]
    # :551 既定（FLAG:821 == 0）では 3/4 で日本語苗字（|| と && は短絡）
    if f821 == 1 or (f821 == 0 and rng.rand(4) != 0):
        surname_no = rng.rand(500) + 3000  # :552–556
        while _str(data, surname_no) == "":
            surname_no = rng.rand(500) + 3000
        surname = _str(data, surname_no)
        given = ""
        while given == "":  # :558–603
            width, base = _GIVEN_JP_SURNAME.get(f822, (500, 12000))
            given = _chinese_second_char(state, data, _str(data, rng.rand(width) + base))
        # :606–646 日本人風の外見
        if rng.rand(8) == 0:
            if rng.rand(3) == 0:
                _set_colors(c, hair="赤")
            elif rng.rand(2) == 0:
                _set_colors(c, hair="緑")
            else:
                _set_colors(c, hair="青")
        elif rng.rand(3) != 0:
            _set_colors(c, hair="茶")
        else:
            _set_colors(c, hair="黒")
        _set_colors(c, eyes="黒")
        _set_colors(c, skin="褐色" if rng.rand(4) == 0 else "肌色")
        if rng.rand(15) == 0:  # :637–646 アルビノ
            _set_colors(c, hair="銀", eyes="赤", skin="色白")
    else:
        surname = ""
        surname_no = 0
        while surname == "":  # :652–701
            if f821 == 8:  # 韓国
                r = rng.rand(100)
                if r < 22:
                    surname_no = 19000
                elif r < 37:
                    surname_no = 19001
                elif r < 46:
                    surname_no = 19002
                elif r < 51:
                    surname_no = 19003
                elif r < 55:
                    surname_no = 19004
                elif r < 65:
                    surname_no = rng.rand(4) + 19005
                elif r < 80:
                    surname_no = rng.rand(10) + 19009
                else:
                    surname_no = rng.rand(81) + 19019
            else:
                width, base = _SURNAME_FOREIGN.get(f821, (8500, 3500))
                surname_no = rng.rand(width) + base
            surname = _str(data, surname_no)
        given = ""
        while given == "":  # :703–751
            key = f821 if f822 == 0 else f822
            width, base = _GIVEN_FOREIGN.get(key, (3500, 12500))
            given = _chinese_second_char(state, data, _str(data, rng.rand(width) + base))
        # :753–836 西洋風の外見
        if rng.rand(6) == 0:
            _set_colors(c, hair="銀")
        elif rng.rand(4) == 0:
            _set_colors(c, hair="赤")
        elif rng.rand(14) == 0:
            _set_colors(c, hair="緑")
        elif rng.rand(12) == 0:
            _set_colors(c, hair="青")
        elif rng.rand(2) == 0:
            _set_colors(c, hair="茶")
        else:
            _set_colors(c, hair="金")
        if rng.rand(12) == 0:
            _set_colors(c, eyes="赤")
        elif rng.rand(8) == 0:
            _set_colors(c, eyes="紫")
        elif rng.rand(4) == 0:
            _set_colors(c, eyes="青")
        else:
            _set_colors(c, eyes="茶")
        if rng.rand(20) == 0:
            _set_colors(c, skin="銀")
        elif rng.rand(20) == 0:
            _set_colors(c, skin="黒")
        elif rng.rand(4) == 0:
            _set_colors(c, skin="褐色")
        elif rng.rand(10) == 0:
            _set_colors(c, skin="肌色")
        else:
            _set_colors(c, skin="色白")
        if rng.rand(6) == 0:  # :812–817 褐色娘
            _set_colors(c, hair="銀", skin="褐色")
        elif rng.rand(5) == 0:  # :818–825 金髪碧眼
            _set_colors(c, hair="金", eyes="青")
        elif rng.rand(10) == 0:  # :826–835 アルビノ
            _set_colors(c, hair="銀", eyes="赤", skin="色白")
    # :839–856 変身後の髪色（CSTR:31）
    if rng.rand(4) == 0:
        color = _descending_color(state)
        if color:
            c.cstr[31] = color
    # :858–900 変身後の瞳の色
    if rng.rand(50) == 0:  # オッドアイ：CSTR:(34 + RAND:2) の片方だけ（代入先の RAND は色の判定の後）
        color = _descending_color(state)
        if color:
            c.cstr[34 + rng.rand(2)] = color
    elif rng.rand(4) == 0:
        color = _descending_color(state)
        if color:
            c.cstr[34] = c.cstr[35] = color
    return surname_no, surname, given


def _descending_color(state: GameState) -> str:
    """`IF RAND:8 == 0 … ELSEIF RAND:7 == 0 … ELSEIF RAND:2 == 0` の 7 段（赤 緑 青 黄 紫 橙 桃）。どれも外れたら ""。"""
    for n, color in zip((8, 7, 6, 5, 4, 3, 2), ("赤", "緑", "青", "黄", "紫", "橙", "桃")):
        if state.rng.rand(n) == 0:
            return color
    return ""


# --- 素質のランダム設定（DEFAULT@CHARA_MAKE_STATUS_TALENT:985–1058）-----------------------------------


def chara_make_status_talent(state: GameState, data: GameData, sel: int) -> None:
    """DEFAULT@CHARA_MAKE_STATUS_TALENT, ARG:985–1058。"""
    c = state.charas[sel]
    rng = state.rng
    female = is_female(data, c)
    v_exp = data.index_of("EXP", "Ｖ経験")
    if female and c.exp[v_exp] == 0:  # :986–995 80% で処女
        if rng.rand(100) < 20:
            _set(data, c, "処女", 0)
            c.exp[v_exp] = 1 + rng.rand(4)
        else:
            _set(data, c, "処女")
    if rng.rand(100) < 20 + talent(data, c, "処女") * 50:  # :997–1000
        _set(data, c, "清純派")
    if rng.rand(100) < 20:  # :1002–1005
        _set(data, c, "パイパン")
    # :1007–1036 敏感・鈍感（V は女性のみ）
    for part, female_only in (("Ｃ", False), ("Ｖ", True), ("Ａ", False), ("Ｂ", False)):
        r = rng.rand(100)
        ok = female or not female_only
        if r < 3 and ok:
            _set(data, c, f"{part}敏感")
        elif r > 96 and ok:
            _set(data, c, f"{part}鈍感")
    r = rng.rand(100)  # :1038–1044 乳
    if r < 20 and female:
        _set(data, c, "貧乳")
    elif r > 79 and female:
        _set(data, c, "巨乳")
    r = rng.rand(100)  # :1045–1051 体型
    if r < 20:
        _set(data, c, "小柄")
    elif r > 79:
        _set(data, c, "長身")
    r = rng.rand(100)  # :1052–1058 濡れやすさ
    if r < 10 and female:
        _set(data, c, "濡れやすい")
    elif r > 89 and female:
        _set(data, c, "濡れにくい")


def chara_make_status_talent_flavor(state: GameState, data: GameData, sel: int) -> None:
    """DEFAULT@CHARA_MAKE_STATUS_TALENT_FLAVOR, ARG:1063–1229（コメントアウト部分は実行されない）。"""
    c = state.charas[sel]
    rng = state.rng
    female = is_female(data, c)
    p1, p2, p3, p4, p5 = 4, 4, 2, 6, 1  # :1064–1069
    p201, p202 = 2, 2  # :1074–1075
    age = c.base[41]  # BASE:年齢（Base.csv:21）
    if 6 <= age <= 12:  # :1077–1087
        _set(data, c, "学生", 1)
    elif 13 <= age <= 15:
        _set(data, c, "学生", 2)
    elif 16 <= age <= 18:
        _set(data, c, "学生", 3)
    elif 19 <= age <= 22:
        _set(data, c, "学生", 4)
    r = rng.rand(100)  # :1137–1149 交際相手
    if r < p1:
        _set(data, c, "交際相手", 1)
    elif r < p1 + p2 and female:
        _set(data, c, "交際相手", 2)
    elif r < p1 + p2 + p3:
        _set(data, c, "交際相手", 3)
    elif r < p1 + p2 + p3 + p4 and female:
        _set(data, c, "交際相手", 4)
    elif r < p1 + p2 + p3 + p4 + p5 and female:
        _set(data, c, "交際相手", 5)
    r = rng.rand(100)  # :1179–1185 家族関係
    if r < p201:
        _set(data, c, "家族関係", 1)
    elif r < p201 + p202:
        _set(data, c, "家族関係", 2)
    r = rng.rand(100)  # :1186–1196 アクセサリ
    if female:
        if r < 6:
            _set(data, c, "アクセサリ", 1)
        elif r < 12:
            _set(data, c, "アクセサリ", 2)
        elif r < 18:
            _set(data, c, "アクセサリ", 3)
    r = rng.rand(100)  # :1197–1214 外見
    if female:
        for limit_, v in ((4, 1), (8, 2), (12, 3), (16, 4)):
            if r < limit_:
                _set(data, c, "外見", v)
                _set(data, c, "変身時外見", v)
                break
    r = rng.rand(100)  # :1215–1226 小学生のイカ腹
    if talent(data, c, "長身"):
        r += 12
    if talent(data, c, "小柄"):
        r //= 2  # 非負なので C# の除算と同じ
    if r < 12 and talent(data, c, "学生") == 1 and female:
        _set(data, c, "外見", 3)
        _set(data, c, "変身時外見", 3)
    r = rng.rand(100)  # :1227–1229
    if r < 75 and talent(data, c, "パイパン") == 0:
        _set(data, c, "パイパン")


# --- 年齢指定（DEFAULT@CHARA_MAKE_AGE_SETTING:1408–1444、@RANDOM_AGE_F:1448–1497）---------------------

_RANDOM_AGE: list[tuple[tuple[str, ...], int, int]] = [
    (("赤子",), 4, 0),
    (("幼児", "幼稚園児"), 3, 3),
    (("児童", "幼女"), 6, 4),
    (("子供", "少女", "少年"), 9, 7),
    (("ティーン",), 7, 13),
    (("若者",), 11, 15),
    (("大人", "青年"), 11, 20),
    (("妙齢",), 11, 25),
    (("中年",), 16, 30),
    (("壮年",), 26, 35),
    (("小学生",), 8, 5),
    (("中学生",), 4, 13),
    (("高校生",), 3, 16),
    (("大学生",), 4, 19),
]


def random_age_f(state: GameState, s: str) -> int:
    """DEFAULT@RANDOM_AGE_F(ARGS):1448–1497。該当なしは -99（RAND を引かない）。"""
    for names, width, base in _RANDOM_AGE:
        if s in names:
            return state.rng.rand(width) + base
    return -99


def toint(s: str) -> int:
    """Emuera `TOINT`（reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs@ToIntMethod:2357–2387）。

    空文字 → 0、全角文字（cp932 で 2 バイト）を含む → 0、先頭が数字／符号+数字でない → 0、
    数字の後に `.`＋数字以外が続く → 0。10 進の整数のみ移植（`0x`／`0b`／指数 `e`・`p` は
    Sub/LexicalAnalyzer.cs@ReadInt64:133–190 の処理があるが本作の到達経路では使われないので未移植）。
    """
    if s == "":
        return 0
    try:
        if len(s.encode("cp932")) > len(s):  # :2363 str.Length < GetStrlenLang(str)
            return 0
    except UnicodeEncodeError:
        # GetStrlenLang は Encoding(932).GetByteCount（_Library/LangManager.cs:17–20）。cp932 にない文字のバイト数は
        # .NET の置換フォールバック次第で reference からは確定できない。本作の到達経路では使われないので停止にする。
        raise NotImplementedError(f"TOINT：cp932 にない文字を含む：{s!r}") from None
    i = 0
    sign = 1
    if s[0] in "+-":
        if len(s) < 2 or not s[1].isdigit():  # :2368
            return 0
        sign = -1 if s[0] == "-" else 1
        i = 1
    elif not s[0].isdigit():  # :2366
        return 0
    if s[i:i + 2].lower() in ("0x", "0b"):
        raise NotImplementedError(f"TOINT の 16／2 進表記は未移植：{s!r}")
    j = i
    while j < len(s) and s[j].isdigit():
        j += 1
    value = sign * int(s[i:j])
    rest = s[j:]
    if rest == "":
        return value
    if rest[0] in "eEpP":
        raise NotImplementedError(f"TOINT の指数表記は未移植：{s!r}")
    if rest[0] == "." and all(ch.isdigit() for ch in rest[1:]):  # :2373–2382
        return value
    return 0
