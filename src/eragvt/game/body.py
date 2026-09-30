"""身體資料（年齢・身長・体重・スリーサイズ・胸の重量）の生成。

路徑相對 `source/earGVP/ERB/`：
- `SYSTEM/キャラメイキング関連/CHARA_SIZE.ERB`（GENERATE_CHAR_SIZE／TOP_UNDER／CUP_SIZE／GENERATE_BODYLINE／CALC_BREAST_WEIGHT）
- `SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@CHARA_SIZE_DEFAULT`:2148–2175
- `SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_TALENT.ERB@SET_PROFILE`:4–19
- `SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_AGE_SETTING`:1336–1444

BASE／MAXBASE 番號（CSV/Base.csv:20–28）：40 実年齢、41 年齢、43 身長、44 体重、45 胸囲、46 胴囲、47 腰囲、48 胸の重量。
CFLAG:33＝体型の乱数値、CFLAG:34＝成長曲線（0 なら「プロフィール未設定」、例：`地の文/MESSAGE.ERB`:258–260）。
単位：身長・スリーサイズ 1mm、体重・胸の重量 0.1kg（CHARA_SIZE.ERB:19–24 のコメント）。

Emuera 語意：整数の `/`・`%` は C# の long 演算（向 0 截斷，`era.div`／`era.mod`）、`&&`／`||` は短絡評価
（reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs@AndIntInt:524–538、OrIntInt:541–555）、
`RETURN a, b, …` は RESULT:0.. に順に代入（GameProc/Function/Instraction.Child.cs@RETURN_Instruction:1997–2025、
GameData/Variable/VariableEvaluator.cs@SetResultX:1732–1740）→ ここでは tuple で返す。
`#DIM` の関数内変数は static（GameData/Variable/VariableToken.cs:1846–1853）だが、本モジュールの各関数は
読む前に必ず代入しているので前回値は影響しない。
"""

from __future__ import annotations

from ..data.csv_loader import GameData
from ..state import GameState
from ..state.character import Character
from .chara_common import charatalent, talent
from .era import div, isqrt, limit, mod, power

# BASE 番號（CSV/Base.csv:20–28）
REAL_AGE, AGE, HEIGHT, WEIGHT, BUST, WAIST, HIP, BREAST_WEIGHT = 40, 41, 43, 44, 45, 46, 47, 48
_SIZE_SLOTS = (HEIGHT, WEIGHT, BUST, WAIST, HIP, BREAST_WEIGHT)  # RESULT:2..7 の格納先


def _override(data: GameData, c: Character, base_value: int, modulo: int, name: str) -> int:
    """`乱数値:n = 乱数値 % m` → `SIF TALENT:名 > 0 && TALENT:名 < m+1 / 乱数値:n = TALENT:名 - 1`。"""
    v = mod(base_value, modulo)
    tv = talent(data, c, name)
    if 0 < tv < modulo + 1:
        v = tv - 1
    return v


def generate_char_size(data: GameData, c: Character, henshin: int) -> tuple[int, int, int, int, int, int, int, int]:
    """`CHARA_SIZE.ERB@GENERATE_CHAR_SIZE, 対象キャラ, 変身値`:25–284。

    戻り値＝RESULT:0..7（乱数値, 成長曲線, 身長, 体重, 胸囲, 胴囲, 腰囲, 胸の重量）。状態は変更しない。
    """
    T = lambda n: talent(data, c, n)  # noqa: E731
    CT = lambda n: charatalent(data, c, henshin, n)  # noqa: E731
    r0 = c.cflag[33]  # :52
    curve = c.cflag[34]  # :53
    age = c.maxbase[AGE] if henshin > 0 else c.base[AGE]  # :54–58
    # :61–78 乱数値の上書きと決定
    r1 = _override(data, c, r0, 11, "身長成長率乱数")
    r2 = _override(data, c, r0, 31, "身長補正乱数")
    r3 = _override(data, c, r0, 59, "体重乱数")
    r4 = _override(data, c, r0, 15, "胴囲乱数")
    r5 = _override(data, c, r0, 16, "腰囲乱数")
    r6 = _override(data, c, r0, 13, "アンダー乱数")
    # :81–95 年齢ごとの成長値（n/100cm）
    growth = [0] * 15
    rest = curve
    for i in range(15):
        growth[i] = mod(rest, 10)
        rest = div(rest, 10)
        growth[i] *= 30
        if i < 7:
            growth[i] += 400
        elif i == 7:
            growth[i] += 210
        elif i == 8:
            growth[i] += 100
    # :102–121 最低身長（5 歳時の平均）と 0〜4 歳
    h = div(10940 * (r1 + 95), 100)
    for a, f in ((0, 605), (1, 725), (2, 808), (3, 876), (4, 939)):
        if age == a:
            h = div(h * f, 1000)
    # :125–163 年齢による伸び
    if CT("オトコ") == 0 or CT("男の娘"):
        for lc in range(5, age + 1):
            if lc < 13:
                h += growth[lc - 5]
            # :134 `ELSEIF LCOUNT < 13`（:132 と同条件、到達しない）
            elif lc < 17:
                h += div(growth[lc - 5], (lc - 12) * 2)
            elif lc < 25:
                h += div(growth[14], 8)
            elif lc < 30:
                h += div(growth[14], 12)
            elif lc < 40:
                pass
            elif lc < 50:
                h -= div(growth[14], 12)
            else:
                h -= div(growth[14], 8)
    else:
        for lc in range(5, age + 1):
            if lc < 20:
                h += growth[lc - 5]
            elif lc < 25:
                h += div(growth[14], 4)
            elif lc < 30:
                h += div(growth[14], 8)
            elif lc < 40:
                pass
            elif lc < 50:
                h -= div(growth[14], 8)
            else:
                h -= div(growth[14], 4)
    # :167 身長の乱数計算
    h = div(h * ((CT("小柄") == 0) * 25 + CT("長身") * 25 + r2 + 260), 3000)
    # :170–174 FEAT
    if T("小さな体躯") > 0:
        h = div(h * 75, 100)
        if T("妖精族") > 0:
            h = div(h * 50, 100)
    # :177–178 オトコ
    if CT("オトコ") and CT("男の娘") == 0:
        h = div(h * 1085, 1000)
    # :182–185 身長の上書き
    if T("身長指定") > 0 and henshin == 0:
        h = T("身長指定")
    if T("変身時身長指定") > 0 and henshin == 1:
        h = T("変身時身長指定")
    # :194–204 BMI・体重
    slender0 = CT("スレンダー") == 0
    bmi = (
        div(r3, 20)
        + CT("むちむち") * 20
        + CT("爆尻") * 20
        + slender0 * 20
        - CT("長身") * 20
        + CT("小柄") * 20
        - (T("妖精族") > 0) * 10
        + (T("ケモミミ族") > 0) * 10
        + 180
    )
    bmi = div(bmi * limit(age + 100, 100, 120), 120)
    # :196 ローレル指数は計算されるが以後使われない
    w0 = div(bmi * h * h, 1000000)
    w1 = div(1000000 * h, 13200000 - 6456 * h)
    w1 = div(w1 * (bmi * 5292307 - 2700000), 1000000000)
    cal = limit((1500 - h) * 4, 0, 1000)
    weight = div(w0 * (1000 - cal) + w1 * cal, 1000) + r3
    # :209–215 胴囲・腰囲・アンダー
    plain = CT("安産型") == 0 and CT("巨尻") == 0 and slender0
    waist = div(
        h
        * (
            bmi * 9
            + r4 * 30
            + CT("むちむち") * 50
            + CT("爆尻") * 50
            + CT("イカ腹") * 200
            + plain * 100
            + (T("ケモミミ族") == 0) * 50
            + 1650
        ),
        10000,
    )
    hip = div(
        h
        * (
            bmi * 7
            + r5 * 30
            + CT("安産型") * 200
            + CT("巨尻") * 350
            + CT("爆尻") * 450
            + CT("むちむち") * 25
            + (CT("イカ腹") == 0) * 50
            + slender0 * 100
            + (T("ケモミミ族") > 0) * 50
            + 3710
        ),
        10000,
    )
    under = div(h * (bmi * 5 + r6 * 5 + CT("むちむち") * 25 + CT("爆尻") * 25 + plain * 15 + 3310), 10000)
    # :218–235 25 歳以上は徐々に熟女体系化
    if 25 <= age < 30:
        lo = age - 4
        weight = div(weight * (1000 + div(lo * 2, 3)), 1000)
        waist = div(waist * (1000 + div(lo, 2)), 1000)
        hip = div(hip * (1000 + lo), 1000)
    elif 30 <= age < 40:
        lo = age - 4
        weight = div(weight * (1000 + lo), 1000)
        waist = div(waist * (1000 + div(lo * 2, 3)), 1000)
        hip = div(hip * (1000 + lo), 1000)
        under = div(under * (1000 + div(lo, 10)), 1000)
    elif age >= 40:
        lo = min(age - 4, 45)
        weight = div(weight * (1000 + div(lo * 3, 2)), 1000)
        waist = div(waist * (1000 + div(lo * 3, 4)), 1000)
        hip = div(hip * (1000 + lo), 1000)
        under = div(under * (1000 + div(lo, 8)), 1000)
    # :239–244 トップとアンダーの差（RESULT:0＝サイズ値、RESULT:1＝影響値）
    top_diff, influence = top_under(data, c, henshin)
    weight += div(div(-18600 * influence, 50), 1000)
    bust = under + top_diff
    # :249–251 カップサイズ → 胸の重量（g/100 = 0.1kg）
    cup, _label = cup_size(top_diff)
    breast = div(calc_breast_weight(bust, under, cup), 100)
    weight += breast
    # :255–259 男性はスリーサイズなし
    if CT("オトコ") and CT("男の娘") == 0:
        bust = waist = hip = -1
    # :262–281 各パラメータの上書き
    for name, is_h in (("体重指定", 0), ("変身時体重指定", 1)):
        if T(name) > 0 and henshin == is_h:
            weight = T(name)
    for name, is_h in (("胸囲指定", 0), ("変身時胸囲指定", 1)):
        if T(name) > 0 and henshin == is_h:
            bust = T(name)
    for name, is_h in (("胴囲指定", 0), ("変身時胴囲指定", 1)):
        if T(name) > 0 and henshin == is_h:
            waist = T(name)
    for name, is_h in (("腰囲指定", 0), ("変身時腰囲指定", 1)):
        if T(name) > 0 and henshin == is_h:
            hip = T(name)
    for name, is_h in (("胸の重量指定", 0), ("変身時胸の重量指定", 1)):
        if T(name) > 0 and henshin == is_h:
            breast = T(name)
    # :283 RETURN 乱数値（= 乱数値:0 = CFLAG:33）, 成長曲線, …
    return r0, curve, h, weight, bust, waist, hip, breast


# TOP_UNDER のサイズ表（:334–366）：(サイズ値, 最小値, 最大値)
_TOP_TABLE = (
    ("絶壁", (-65, 0, 124)),
    ("貧乳", (-40, 0, 149)),
    ("奇乳", (170, 275, 999)),
    ("魔乳", (130, 250, 474)),
    ("超乳", (90, 225, 399)),
    ("爆乳", (50, 200, 324)),
    ("巨乳", (25, 175, 249)),
)


def top_under(data: GameData, c: Character, henshin: int) -> tuple[int, int]:
    """`CHARA_SIZE.ERB@TOP_UNDER, 対象キャラ, 変身値`:287–380。戻り値＝(サイズ値, 影響値)（RESULT:0, RESULT:1）。"""
    CT = lambda n: charatalent(data, c, henshin, n)  # noqa: E731
    r0 = c.cflag[33]  # :298
    t1 = _override(data, c, r0, 23, "胸の張り乱数")  # :301–309
    t2 = _override(data, c, r0, 7, "胸成長率乱数")
    t3 = _override(data, c, r0, 53, "胸サイズ補正乱数")
    age = c.maxbase[AGE] if henshin > 0 else c.base[AGE]  # :312–319
    if age > 22:
        age = 22
    influence = div((age + 10) * (t2 * 2 + 26 - t1), 15) + div(t3, 4)  # :322
    if age < 5:  # :323–331
        influence += age * 6
    elif age < 10:
        influence += 24 + (age - 4) * 12
    elif age < 15:
        influence += 84 + (age - 9) * 3
    else:
        influence += 99 + (age - 14) * 1
    size, lo, hi = 0, 100, 174  # ELSE 分岐（:362–365）
    if CT("絶壁") or CT("男の娘"):  # :334
        size, lo, hi = _TOP_TABLE[0][1]
    else:
        for name, row in _TOP_TABLE[1:]:
            if CT(name):
                size, lo, hi = row
                break
    lo = max(lo - div(75 * max(15 - age, 0), 15), 0)  # :367–368
    hi = max(hi - div(75 * max(15 - age, 0), 15), 0)
    size = div(size * (t3 + 50), 50) + influence + talent(data, c, "膨乳改造値")  # :369
    size = div(size * (100 + CT("むちむち") * 5), 100)  # :371–373
    size = div(size * (100 + CT("爆尻") * 5), 100)
    size = div(size * (100 - CT("イカ腹") * 10), 100)
    size = limit(size, lo, hi)  # :375
    if CT("オトコ") and CT("男の娘") == 0:  # :377–378
        size = -1
    return size, influence


_CUP_LABELS = "AAA AA A B C D E F G H I J K L M N O P Q R S T U V W X Y Z".split()


def cup_size(arg: int) -> tuple[int, str]:
    """`CHARA_SIZE.ERB@CUP_SIZE, ARG`:386–456。戻り値＝(RESULT, RESULTS)。

    RESULTS：25 未満は「―」、25〜74 は AAA、以後 25 刻みで AA〜Z（750 以上も Z）。
    RESULT：25 未満は 1、以上は MAX(2, (ARG-25)/25)。
    """
    if arg < 25:
        label = "―"
    elif arg < 75:
        label = _CUP_LABELS[0]
    else:
        label = _CUP_LABELS[min(div(arg - 50, 25), len(_CUP_LABELS) - 1)]
    value = 1 if arg < 25 else max(2, div(arg - 25, 25))
    return value, label


# CALC_BREAST_WEIGHT のカップ別目安（:619–656、SELECTCASE cupsize-1）
_CUP_GUIDE = (18, 60, 100, 300, 460, 590, 758, 1060, 1620, 2200, 3000, 3800, 5000, 6200)


def calc_breast_weight(tb: int, ub: int, cupsize: int) -> int:
    """`CHARA_SIZE.ERB@CALC_BREAST_WEIGHT(nTB, nUB, cupsize)`:554–670（#FUNCTION）。乳房 2 つ分の重量（g）。"""
    hemi = div(div(ub * 100, 48), 25)  # :591
    cup_v = div((tb - ub) * 2, 5)  # :592
    ball_r = div((div(ub, 15) + cup_v) * 45, 100)  # :596
    bottom_r = div((div(ub, 15) + cup_v) * 45, 100) - div(abs(cup_v - hemi) * 39, 100)  # :598
    if power(ball_r, 2) - power(bottom_r, 2) < 0:  # :601–602
        return 0
    root = isqrt(power(ball_r, 2) - power(bottom_r, 2))
    h = ball_r + root if cup_v >= hemi else ball_r - root  # :604–609
    volume = div(div(h * (3 * h * (2 * ball_r - h) + power(h, 2)) * 314, 100), 6)  # :611
    weight = div(div(volume * 2 * 87, 100), 1000)  # :614
    if cupsize > -1:  # :617
        k = cupsize - 1
        guide = _CUP_GUIDE[k] if 0 <= k < len(_CUP_GUIDE) else 6200 + 1200 * (cupsize - 13)
        if cupsize >= 9:  # :658–669
            if cupsize == 9:
                weight = div(guide * 12 + weight * 2, 14)
            elif cupsize == 10:
                weight = div(guide * 11 + weight * 2, 13)
            else:
                weight = div(guide * 10 + weight * 2, 12)
        else:
            weight = div(guide + weight * 10, 11)
    return weight


# GENERATE_BODYLINE の年齢別分布（:491–505）
_DEV_VAR = (83, 80, 75, 83, 113, 108, 50, 40, 30, 20, 10, 10, 10, 8, 6)
_BODY_RAND = 11 * 31 * 59 * 15 * 16 * 13 * 23 * 7 * 53


def generate_bodyline(state: GameState, data: GameData, c: Character) -> None:
    """`CHARA_SIZE.ERB@GENERATE_BODYLINE, 対象キャラ`:460–544：CFLAG:33（乱数値）と CFLAG:34（成長曲線）を決める。

    成長値（15 年分、各 0〜9）に 60 回、`_DEV_VAR` の重みで 1 ずつ配る（9 に達した年は引き直し）。
    内側 FOR の BREAK はカウンタを 1 進めてから抜けるので（reference/emuera-1824/Emuera/GameProc/Function/
    Instraction.Child.cs@BREAK_Instruction:2054–2077）、`成長値:(LCOUNT:1 - 1)` は当たった年そのもの。
    外側の `LCOUNT:0 -= 1` → CONTINUE（同 CONTINUE_Instruction:2079–2109、カウンタを進めて判定）は「やり直し」。
    """
    rng = state.rng
    r = rng.rand(_BODY_RAND)  # :475
    if talent(data, c, "体型乱数値指定") > 0:  # :488–489
        r = talent(data, c, "体型乱数値指定")
    total = sum(_DEV_VAR)  # :507–510
    growth = [0] * 15
    done = 0
    while done < 60:  # :512–525
        cal = rng.rand(total)
        acc = 0
        hit = 14
        for i, w in enumerate(_DEV_VAR):
            acc += w
            if cal < acc:
                hit = i
                break
        if growth[hit] >= 9:
            continue
        growth[hit] += 1
        done += 1
    curve = 0  # :527–532
    for i in range(15):
        curve = curve * 10 + growth[14 - i]
    if talent(data, c, "体型成長曲線指定") > 0:  # :535–536
        curve = talent(data, c, "体型成長曲線指定")
    c.cflag[33] = r  # :539–540
    c.cflag[34] = curve


def chara_size_default(data: GameData, c: Character) -> None:
    """`CHARA_SIZE_UI.ERB@CHARA_SIZE_DEFAULT, C_ID`:2148–2175（BASE:年齢を先に設定してから呼ぶ）。"""
    if talent(data, c, "変身能力") < 1:  # :2153–2154
        c.maxbase[AGE] = -1
    r = generate_char_size(data, c, 0)  # :2156–2164
    c.cflag[33] = r[0]
    c.cflag[34] = r[1]
    for slot, v in zip(_SIZE_SLOTS, r[2:]):
        c.base[slot] = v
    if talent(data, c, "変身能力") > 0:  # :2167–2175
        r = generate_char_size(data, c, 1)
        for slot, v in zip(_SIZE_SLOTS, r[2:]):
            c.maxbase[slot] = v


def set_profile(data: GameData, c: Character) -> None:
    """`FIRSTSETTING_CHARA_TALENT.ERB@SET_PROFILE, ARG`:4–19：通常時・変身時の身長〜胸の重量を再計算する
    （CFLAG:33／34 と年齢はそのまま。プロフィール未設定（CFLAG:34 = 0）でも実行される）。"""
    r = generate_char_size(data, c, 0)
    for slot, v in zip(_SIZE_SLOTS, r[2:]):
        c.base[slot] = v
    r = generate_char_size(data, c, 1)
    for slot, v in zip(_SIZE_SLOTS, r[2:]):
        c.maxbase[slot] = v


def chara_make_age_setting(state: GameState, data: GameData, c: Character) -> None:
    """`CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_AGE_SETTING, ARG`:1336–1444（年齢の初期値）。"""
    rng = state.rng
    T = lambda n: talent(data, c, n)  # noqa: E731
    c.base[AGE] = rng.rand(11) + 10  # :1342
    c.base[REAL_AGE] = c.base[AGE]
    # :1345–1350（&& は短絡評価：RAND:4 は前 2 条件が真のときだけ引く）
    if T("変身能力") > 0 and c.maxbase[AGE] <= 18 and rng.rand(4) == 0:
        c.maxbase[AGE] = c.base[AGE] + rng.rand(6)
    elif T("変身能力") > 0:
        c.maxbase[AGE] = c.base[AGE]
    age = c.base[AGE]  # :1357
    student = T("学生")
    if student == 1:  # :1359–1373
        age = rng.rand(7) + 6
    elif student == 2:
        age = rng.rand(5) + 12
    elif student == 3:
        age = rng.rand(5) + 15
    elif student == 4:
        age = rng.rand(6) + 18
    if T("交際相手") >= 4 and age < 25:  # :1375–1384
        if student == 3:
            age = 16 + rng.rand(3)
        elif student == 4:
            age = 19 + rng.rand(4)
        else:
            age = T("交際相手") * 5 + rng.rand(11)
    real = age  # :1387
    if T("ロボっ子") > 0:  # :1390–1402
        real = rng.rand(6)
    if T("妖精族") > 0:
        real += rng.rand(100)
    if T("不老長寿") > 0:
        real += rng.rand(500)
    old = T("天使") > 0 or T("魔族") > 0 or T("ヴァンパイア") > 0
    if old and rng.rand(2) == 0:
        real += rng.rand(1000)
    if old and rng.rand(10) == 0:
        real += rng.rand(10000)
    c.base[AGE] = age  # :1404–1406
    c.maxbase[AGE] = age
    c.base[REAL_AGE] = real
    if c.cstr[204] != "" or c.cstr[205] != "" or c.cstr[206] != "":
        # :1409–1444 年齢指定（TOINT・RANDOM_AGE_F）。本作の到達経路（初期セット）では空。
        raise NotImplementedError("CHARA_MAKE_AGE_SETTING の年齢指定（CSTR:204–206）は未移植")
