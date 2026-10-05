"""戰鬥共通的小函式：變數存取、PERCENT_CAL、心境、地の文分岐旗標、敵資料（TENTACLE_ACCESS）等。

路徑相對 `source/earGVP/ERB/`。Emuera 運算的注意點（引擎依據）：
- `&&`／`||` 會短路求值（reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:524–556），
  且兩者**同優先度、由左至右**結合（GameData/Expression/OperatorCode.cs:31–35，And/Or 皆 0x40）。
  因此 ERB 的 `A || B && C` 是 `(A || B) && C`，翻寫時照此加括號。
- 位元 `&`／`|`（0x50）比比較運算（0x60／0x65）優先度低。
- 函式的 LOCAL 在呼叫之間保留（見 `TempVars.locals`）。
"""

from __future__ import annotations

from dataclasses import dataclass

from ...state import GameState
from ...state.character import Character
from ..action import Ctx, config_check_maniac, config_check_screen, kojo_root, print_transcallname
from ..chara_common import is_female, is_male, seikaku_check, talent
from ..era import div, isqrt, limit, times
from ..tentacle import enemy_type_check, get_lastboss_phase


class BeginAfterTrain(Exception):
    """`BEGIN AFTERTRAIN`：呼叫堆疊全部捨棄，進入 `@EVENTEND`（Process.SystemProc.cs@beginAfterTrain:524–534）。"""


class BeginTurnend(Exception):
    """戰鬥中的 `BEGIN TURNEND`（S27：ラスボス撃破後の完全殲滅 `BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:306）。
    呼叫堆疊全部捨棄（`@EVENTEND` を通らない）、`@EVENTTURNEND` へ（Process.SystemProc.cs@beginTurnend:602–612、
    BEGIN の呼叫堆疊破棄：GameProc/Process.State.cs@Begin:263–310（:307 functionList.Clear））。"""


# --- DIM.ERH 常數 ----------------------------------------------------------------

# :129–136 TCVARn:12 の状態異常
KIZETU = 1  # 気絶
HAIRAN = 2  # 排卵
HATUJOU = 4  # 発情
MAHI = 8  # 麻痺
BETOBETO = 16  # べとべと
KOSHIKUDAKE = 32  # 腰くだけ
KOUKOTSU = 64  # 恍惚
KYOUKOUSOKU = 128  # 強拘束

# :187–205 防御体勢（TCVARn:2）
P_NOTHING = -1  # 体勢：何もしない
P_NORMAL = 0
P_GUARD = 1  # 体勢：防御
P_NASUGAMAMA = 2
P_TAERU = 3
P_UKEIRERU = 4
P_HOUSHI = 5
P_NIRAMI = 6
P_SHIBORU = 10  # 体勢：搾り取る
P_V_GUARD = 100
P_ABARE_GUARD = 200
P_ABARE_FAIL = 201
P_ABARE_CRIT = 202
P_HANGEKI = 300
P_EX_HANGEKI = 301
P_HANGEKI_OK = 302

# :213–217 地の文分岐
DARAKU = 1  # 堕落
KAIRAKU_TOROKE = 2  # 快楽蕩け
SEI_TEIKOU = 4  # 性抵抗
ZETSUBOU = 8  # 絶望
KUSEN = 16  # 苦戦

# :94–105 性部位ビット
B_V = 2
B_WAREME = 64
B_BOUHATSU = 128

KANKAKU_NUM = 4  # 感覚数（:154）
PALAM_END = 18  # PALAM終点（:127）
PALAM_MAX = 999999  # CSV定数定義/PALAM.ERH:4 PALAM上限


# --- 變數存取 ------------------------------------------------------------------


def t(ctx: Ctx, c: Character, name: str) -> int:
    """`TALENT:c:name`。"""
    return talent(ctx.data, c, name)


def abl(ctx: Ctx, c: Character, name: str) -> int:
    return c.abl[ctx.data.index_of("ABL", name)]


def exp(ctx: Ctx, c: Character, name: str) -> int:
    return c.exp[ctx.data.index_of("EXP", name)]


def add_exp(ctx: Ctx, c: Character, name: str, value: int) -> None:
    c.exp[ctx.data.index_of("EXP", name)] += value


def mark(ctx: Ctx, c: Character, name: str) -> int:
    return c.mark[ctx.data.index_of("MARK", name)]


def tc(ctx: Ctx) -> Character:
    """TARGET のキャラ。"""
    return ctx.state.target_chara


def tv(ctx: Ctx) -> object:
    """TARGET の TCVARn（IntArray）。"""
    return ctx.state.target_chara.tcvarn


def get_local(st: GameState, func: str, i: int) -> int:
    return st.temp.locals.get((func, i), 0)


def set_local(st: GameState, func: str, i: int, value: int) -> None:
    st.temp.locals[(func, i)] = value


def percent_cal(a: int, b: int) -> int:
    """`汎用関数/コモン関数.ERB@PERCENT_CAL`:216–220 ／ `@PERCENT_CAL_F`:224–229。"""
    if a == 0 or b == 0:
        return 0
    return div(a * 100, b)


def config_check_balance(st: GameState, n: int) -> int:
    """`SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG_CHECK_BALANCE_F`:529–532 = GETBIT(FLAG:803, n)。"""
    return int(st.flag.get_bit(803, n))


def get_battle_situation(st: GameState, name: str) -> int:
    """`ゲーム内_イベント発生/イベントから派生する特殊戦闘/特殊シチュエーション.ERB@GETBATTLESITUATION`:45–48
    （STRFIND：部分文字列が見つかれば 1）。"""
    return 1 if name in st.temp.battle_situation else 0


def add_battle_situation(st: GameState, name: str) -> None:
    """`特殊シチュエーション.ERB@ADDBATTLESITUATION(ARGS)`:43–44 `特殊戦闘シチュエーション'=ARGS+","`。

    `'=` は文字列の代入（追加ではない）：`reference/emuera-1824/Emuera/GameProc/Function/ArgumentBuilder.cs:786–807`
    （AssignmentStr → SpSetArgument）、`Instraction.Child.cs:466–468`（SetValue）。名前に反して既存の
    シチュエーションは消える（原作どおり）。
    """
    st.temp.battle_situation = name + ","


def unlock_achievement(ctx: Ctx, num: int, name: str) -> None:
    """ERB/インターミッション画面/SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT:6–20。"""
    from ..achievements import unlock
    unlock(ctx, num, name)


def is_penis(ctx: Ctx, who: int | None = None) -> bool:
    """`汎用関数/SEX_GENDER.ERB@ISPENIS`:9–15。"""
    c = ctx.state.charas[ctx.state.target if who is None else who]
    return is_male(ctx.data, c) or t(ctx, c, "ふたなり") > 0


def is_girly(ctx: Ctx, who: int | None = None) -> bool:
    """`@ISGIRLY`（SEX_GENDER.ERB:28–37）。"""
    c = ctx.state.charas[ctx.state.target if who is None else who]
    return is_female(ctx.data, c) or t(ctx, c, "男の娘") != 0


def is_manly(ctx: Ctx, who: int | None = None) -> bool:
    """`@ISMANLY`（SEX_GENDER.ERB:41–50）。"""
    return not is_girly(ctx, who)


def is_hole(ctx: Ctx, who: int | None = None) -> bool:
    """`@ISHOLE`（SEX_GENDER.ERB:52–66）。引数 0 は MASTER で常に 1。"""
    if who == 0:
        return True
    return is_girly(ctx, who) or config_check_maniac(ctx.state, 5) == 1


def print_theme(ctx: Ctx) -> str:
    """`汎用関数/コモン関数.ERB@PRINT_THEME`:289–293（ARG 省略＝TARGET）。"""
    c = tc(ctx)
    return c.cstr[60] if c.cstr[60] != "" else ctx.state.savestr[10]


def shokushu_shimin(st: GameState, a: str, b: str) -> str:
    """`口上/口上システム関係/KOJO_式中関数.ERB@触手市民`:3–9。"""
    return b if st.flag[73] > 0 else a


def palamlv(ctx: Ctx, _arg: int) -> int:
    """`汎用関数/コモン関数.ERB@PALAMLV_F`:1015–1043。

    原作は引数ではなく `PALAM:LOCAL`（LOCAL＝この関数の前回の戻り値、呼び出し間で保持）を見ている。
    バグだが原作どおり移植する（引数は使わない）。
    """
    st = ctx.state
    prev = get_local(st, "PALAMLV_F", 0)
    p = tc(ctx).palam[prev]
    for i, bound in enumerate((100, 300, 600, 1500, 3000, 6000, 10000, 30000, 60000, 150000, 300000)):
        if p < bound:
            result = i
            break
    else:
        result = 11
    set_local(st, "PALAMLV_F", 0, result)
    return result


# --- 性格補正（ヒロイン関連/CHARA_SEIKAKU.ERB）-----------------------------------------

# @SEIKAKU_HOSEI_PALAM_F:472–850 の TIMES 係数（性格素質番号 → {PALAM 番号: 係数}）。無記載は補正なし。
_SEIKAKU_PALAM: dict[int, dict[int, str]] = {
    10: {11: "1.20", 17: "1.20"},
    11: {11: "0.80", 15: "1.20"},
    12: {13: "1.15", 14: "0.90", 16: "0.90", 17: "0.90"},
    13: {13: "1.05", 17: "0.90"},
    14: {11: "1.10", 13: "0.95", 14: "1.20", 16: "0.90"},
    15: {14: "1.10", 15: "0.90"},
    16: {11: "0.90", 13: "0.90", 16: "1.10"},
    17: {13: "0.95", 14: "0.95", 15: "0.95", 16: "0.95", 17: "0.95"},
    18: {11: "0.90", 13: "0.80", 14: "1.20", 16: "1.20"},
    19: {11: "1.05", 13: "1.05"},
    20: {11: "1.20", 14: "0.80", 15: "1.20", 16: "0.80"},
    21: {13: "1.40", 14: "0.90", 15: "0.90", 16: "0.40", 17: "0.40"},
    22: {13: "1.10", 15: "1.10", 16: "0.90"},
    23: {13: "1.20", 14: "1.10", 15: "0.80", 17: "1.20"},
    24: {14: "0.95", 15: "1.15", 16: "0.95", 17: "0.95"},
    25: {13: "1.10", 15: "0.90", 17: "1.10"},
    26: {11: "1.20", 13: "0.80", 14: "0.90", 16: "1.20"},
    27: {11: "1.10", 15: "0.80", 17: "1.30"},
    28: {11: "0.30", 13: "0.90", 14: "0.30", 15: "0.30", 16: "0.90", 17: "0.30"},
}


def seikaku_hosei_palam(seikaku: int, palam_id: int, value: int) -> int:
    """`ヒロイン関連/CHARA_SEIKAKU.ERB@SEIKAKU_HOSEI_PALAM_F`:472–850。"""
    factor = _SEIKAKU_PALAM.get(seikaku, {}).get(palam_id)
    return times(value, factor) if factor else value


# @SEIKAKU_HOSEI_SHINKYOU:850–1023（基本 30）
_SEIKAKU_SHINKYOU: dict[int, dict[str, int]] = {
    10: {"TOUSAKU": 10, "DOUYOU": 50},
    11: {"TOUSAKU": 10, "KOUYOU": 10},
    12: {"TOUSAKU": 50, "IKARI": 50},
    13: {"REISEI": 10, "TEIKAN": 10},
    14: {"IKARI": 10, "SYOUTIN": 10},
    15: {"TEIKAN": 50, "DOUYOU": 10},
    16: {"REISEI": 50, "DOUYOU": 50},
    17: {k: 10 for k in ("IKARI", "TEIKAN", "REISEI", "DOUYOU", "KOUYOU", "SYOUTIN")},
    18: {"TOUSAKU": 10, "TEIKAN": 50},
    19: {"KOUYOU": 50, "SYOUTIN": 50},
    20: {"IKARI": 50, "SYOUTIN": 50},
    21: {"TEIKAN": 10, "REISEI": 10},
    22: {"TOUSAKU": 50, "REISEI": 50},
    23: {"KOUYOU": 50, "DOUYOU": 50},
    24: {"TEIKAN": 50, "DOUYOU": 10},
    25: {"TOUSAKU": 50, "KOUYOU": 50},
    26: {"TEIKAN": 10, "KOUYOU": 10},
    27: {"IKARI": 50, "REISEI": 10},
    28: {k: 0 for k in ("IKARI", "TEIKAN", "REISEI", "DOUYOU", "KOUYOU", "SYOUTIN")},
}


def seikaku_hosei_shinkyou(seikaku: int, kind: str) -> int:
    return _SEIKAKU_SHINKYOU.get(seikaku, {}).get(kind, 30)


# --- 地の文分岐（地の文/MESSAGE_BRANCH.ERB）-----------------------------------------

_BRANCH_SEIKAKU = {
    10: (1, -1), 11: (-1, -1), 12: (0, 3), 13: (0, 0), 14: (3, 0), 15: (0, -1), 16: (1, 1), 17: (-1, 1),
    18: (0, -3), 19: (-2, -1), 20: (-1, -2), 21: (3, 3), 22: (0, 0), 23: (-1, 0), 24: (2, 2), 25: (-3, 0),
    26: (2, 1), 27: (1, 2), 28: (5, 5),
}
_MARK_STEP = {1: -1, 2: -2, 3: -3, 4: -5, 5: -8}


def branch_palam(ctx: Ctx, who: int, kind: str) -> int:
    """`地の文/MESSAGE_BRANCH.ERB@BRANCH_PALAM_F`:45–371。

    「戦闘中のみ計算」部分の TCVARn:1／PALAM／TCVARn:12 は **TARGET** のもの、CFLAG:0 も TARGET（原作どおり）。
    """
    st = ctx.state
    c = st.charas[who]
    tt = lambda n: t(ctx, c, n)  # noqa: E731
    faith, brave = 10, 10
    if tt("神器の担い手") > 0:
        faith += 1
    if tt("闘争本能") > 0:
        brave += 1
    if tt("精霊交信") > 0:
        brave -= 1
    if tt("獣性の証") > 0:
        faith -= 1
    if tt("生粋の戦士") > 0:
        faith += 1
        brave += 1
    if tt("祝福") > 0:
        faith += 1
    if tt("不屈") > 0:
        brave += 1
    df, db = _BRANCH_SEIKAKU.get(seikaku_check(ctx.data, c), (0, 0))
    faith += df
    brave += db
    if tt("処女") > 0:
        faith += 3
        brave += 1
    if tt("妊娠") > 0 and tt("妊娠") != 4:
        brave -= 3
    if tt("交際相手") == 1:
        faith += 1
    if tt("交際相手") in (2, 3, 4):
        faith += 2
    if tt("家族関係") > 0:
        brave += 2
    if tt("淫乱") > 0:
        faith -= 3
    if tt("快楽に弱い") > 0:
        faith -= 2
    if tt("快楽の否定") > 0:
        faith += 2
    if tt("争いを好まない") > 0:
        brave -= 2
    if tt("喧嘩上等") > 0:
        brave += 2
    faith += _MARK_STEP.get(mark(ctx, c, "快楽刻印"), 0)
    faith += _MARK_STEP.get(mark(ctx, c, "屈服刻印"), 0)
    brave += _MARK_STEP.get(mark(ctx, c, "苦痛刻印"), 0)
    brave += _MARK_STEP.get(mark(ctx, c, "恐怖刻印"), 0)
    tgt = st.target_chara
    if st.flag[700] > 0:
        sk = tgt.tcvarn[1]
        # :242–245 `IF TCVARn:1 == 2`（倒錯のつもりだが 2 を見ている）→ 怒りの分岐には到達しない（原作どおり）
        if sk == 2:
            faith -= 1
        elif sk == 3:
            faith -= 1
            brave -= 1
        elif sk == 4:
            brave += 1
        elif sk == 5:
            brave -= 1
        elif sk == 6:
            brave += 2
        elif sk == 7:
            brave -= 2
        for base_no, is_brave in ((0, True), (1, True), (2, False)):
            p = percent_cal(c.base[base_no], c.maxbase[base_no])
            d = -4 if p == 0 else -2 if p <= 50 else -1 if p <= 75 else 0
            if is_brave:
                brave += d
            else:
                faith += d
        pl = tgt.palam
        if pl[13] >= 90000 or pl[14] >= 90000:
            faith -= 3
        elif pl[13] >= 30000 or pl[14] >= 30000:
            faith -= 2
        elif pl[13] >= 10000 or pl[14] >= 10000:
            faith -= 1
        if pl[16] >= 90000 or pl[17] >= 90000:
            brave -= 3
        elif pl[16] >= 30000 or pl[17] >= 30000:
            brave -= 2
        elif pl[16] >= 10000 or pl[17] >= 10000:
            brave -= 1
        if pl[11] >= 80000:
            faith -= 2
            brave -= 1
        elif pl[11] >= 20000:
            faith -= 1
            brave -= 1
        elif pl[11] >= 5000:
            faith -= 1
        maso = abl(ctx, tgt, "マゾっ気")
        pain = pl[16]
        if maso == 1 and pain >= 30000:
            faith -= 1
        elif maso == 2 and pain >= 20000:
            faith -= 1
        elif maso == 3 and pain >= 10000:
            faith -= 1
        elif maso == 4 and pain >= 10000:
            faith -= 1
        elif maso == 4 and pain >= 30000:
            faith -= 2
        elif maso == 5 and pain >= 10000:
            faith -= 2
        elif maso == 5 and pain >= 30000:
            faith -= 3
        if tgt.tcvarn[12] & HATUJOU:
            faith -= 2
    elif tgt.cflag[0] == 1:
        d31 = c.cflag[31]
        faith += -2 if d31 < 3 else -3 if d31 < 6 else -4 if d31 < 9 else -5 if d31 < 12 else -6
        brave += -4 if d31 < 3 else -5 if d31 < 6 else -6 if d31 < 9 else -7 if d31 < 12 else -8
    if kind == "FAITH_S":
        return faith
    if kind == "BRAVE_S":
        return brave
    return 99999


def message_branch(ctx: Ctx, who: int | None = None) -> int:
    """`地の文/MESSAGE_BRANCH.ERB@MESSAGE_BRANCH_F`:5–37。"""
    st = ctx.state
    w = st.target if who is None else who
    c = st.charas[w]
    faith = branch_palam(ctx, w, "FAITH_S")
    brave = branch_palam(ctx, w, "BRAVE_S")
    r = 0
    if faith < 1:
        r |= KAIRAKU_TOROKE
    if faith < 5:
        r |= SEI_TEIKOU
    if brave < 1:
        r |= ZETSUBOU
    if brave < 5:
        r |= KUSEN
    if t(ctx, c, "触手の虜") > 0:
        r |= DARAKU
    if t(ctx, c, "淫乱") and (r & KAIRAKU_TOROKE):
        r |= DARAKU
    if (abl(ctx, c, "奉仕精神") + abl(ctx, c, "触手中毒")) >= 3 and faith < -5:
        r |= DARAKU
    if (abl(ctx, c, "奉仕精神") >= 4 or abl(ctx, c, "触手中毒") >= 4) and (r & KAIRAKU_TOROKE):
        r |= DARAKU
    return r


# --- 敵資料（ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS、触手データ/ボス触手/）----------


@dataclass(frozen=True)
class BossData:
    """`触手データ/ボス触手/TENTACLE_BOSS_{n}_*.ERB` の各関数の値。"""

    name: str  # _GETNAME
    definition: tuple[str, str]  # _DEFENITION の 2 行
    hp: tuple[int, int]  # _HP：TENTACLE_STATUS_HOSEI(LOCAL, bonus)
    syasei: tuple[int, int]  # _SYASEI：base + TENTACLE_LEVEL * per
    sakusei: int
    yudan: int
    kougeki: int  # TENTACLE_STATUS_HOSEI(値)（bonus 100）
    bougyo: int
    binsyou: int
    chisei: int  # TENTACLE_STATUS_HOSEI(値, 10)
    short: int
    middle: int
    long: int
    hold: int
    palam_hosei: tuple[int, ...]  # 12 個（快C〜恐怖）
    attack_routine: tuple[int, int]  # (RAND:100 < 20 のときの戻り値, 20)；(0, 0) は常に 0
    # KOUGEKI／BOUGYO／BINSYOU の TENTACLE_STATUS_HOSEI の第 2 引数（ボスは全て省略 = 100、Ｋ触手は 100／50／50）
    stat_bonus: tuple[int, int, int] = (100, 100, 100)


BOSSES: dict[int, BossData] = {
    # TENTACLE_BOSS_1_Ｃ触手.ERB:7–133
    1: BossData("Ｃ触手", ("（巨大イモ虫の頭部が無数の触手に枝分かれしたようなボス触手）",
                          "（それぞれの触手の先端からはさらに大量の毛細触手が飛び出し蠢いている）"),
                (9000, 1500), (920, 20), 100, 1760, 180, 150, 105, 45, 100, 100, 100, 105,
                (120, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100), (0, 0)),
    # TENTACLE_BOSS_2_Ｖ触手.ERB
    2: BossData("Ｖ触手", ("（無数の触手が絡まり合った根元から巨大な勃起ペニスが生えた姿のボス触手）",
                          "（地を這うように移動し、それぞれの先端からは精液らしき液体を垂れ流している）"),
                (10500, 1500), (940, 15), 100, 1610, 210, 125, 115, 35, 120, 100, 80, 140,
                (100, 120, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100), (0, 0)),
    # TENTACLE_BOSS_3_Ａ触手.ERB
    3: BossData("Ａ触手", ("（まるでスライムかアメーバのような不定形の姿をした半透明のボス触手）",
                          "（中心に大きな核が透けて見え、その周囲には臓器らしき肉塊が並んでいる）"),
                (6500, 1500), (900, 25), 100, 1710, 180, 350, 50, 55, 120, 140, 120, 180,
                (100, 100, 120, 100, 100, 100, 100, 100, 120, 100, 120, 120), (0, 0)),
    # TENTACLE_BOSS_4_Ｂ触手.ERB
    4: BossData("Ｂ触手", ("（まるで巨大な赤ん坊のような見た目の異形のボス触手）",
                          "（触手の先端が壺のような形状をしており、開口部がぱくぱくと動いている）"),
                (16000, 4000), (980, 5), 100, 1560, 200, 60, 180, 50, 120, 100, 100, 145,
                (100, 100, 100, 120, 100, 100, 100, 100, 100, 100, 100, 100), (0, 0)),
    # TENTACLE_BOSS_5_Ｓ触手.ERB（ATTACK_ROUTINE：RAND:100 < 20 → 1）
    5: BossData("Ｓ触手", ("（長い２本の触腕が特徴的な巨大イカのようなボス触手）",
                          "（全体が微妙に発光しており、時折放電している）"),
                (8000, 5000), (920, 20), 120, 1860, 230, 100, 155, 40, 150, 75, 100, 120,
                (100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 200, 200), (1, 20)),
    # TENTACLE_BOSS_6_Ｐ触手.ERB（PALAM_HOSEI は TFLAG:23 で 1/4、ATTACK_ROUTINE → 2）
    6: BossData("Ｐ触手", ("（蔦のごとく触手を生やした食虫植物のような姿のボス触手）",
                          "（ウツボカズラ状の胴体には得体のしれない液体が蓄えられている）"),
                (8500, 2500), (700, 25), 60, 1560, 150, 175, 85, 80, 110, 140, 125, 180,
                (100, 100, 100, 100, 100, 120, 200, 100, 120, 100, 100, 100), (2, 20)),
    # TENTACLE_BOSS_7_Ｈ触手.ERB（ATTACK_ROUTINE → 3）
    7: BossData("Ｈ触手", ("（無数の触手が絡まりあった中心に巨大な目玉を持つボス触手）",
                          "（空中を浮遊しており、地面にドロドロと得体のしれない液体を垂れ流している）"),
                (8000, 4000), (940, 15), 90, 2060, 175, 145, 155, 120, 85, 90, 150, 165,
                (100, 100, 100, 100, 100, 100, 120, 100, 120, 200, 100, 100), (3, 20)),
}


# ラスボス：`触手データ/ボス触手/TENTACLE_LASTBOSS_{n}_*.ERB`。本作は 1（Ｋ触手）と 2（天使の樹）の 2 個
# （GET_LASTBOSS_ERB_NUM：COMMON_TENTACLE_DATA.ERB:428–438）。天使の樹は周回（FLAG:854 > 0：SCORE.ERB:749 でのみ増え、
# 引き継ぎ SUCCESSION.ERBでしか次の周に持ち越せない）かつ HARDCORE でしか出現しない（BATTLE_COM_AFTER.ERB:176、:270）
# 。S38 已接通第二隻末王。
LASTBOSSES: dict[int, BossData] = {
    # TENTACLE_LASTBOSS_1_Ｋ触手.ERB:7–123（ATTACK_ROUTINE／SEX_ROUTINE／REACTION_REF／PRISON_ROUTINE／TENTACLE_SIZE は専用関数）
    1: BossData("Ｋ触手", ("（数十メートルはある巨大な図体をしたラスボス触手）",
                          "（その禍々しい威容はまさしく触手たちの王を名乗るにふさわしい）"),
                (30000, 2000), (1250, 25), 100, 2260, 300, 200, 100, 65, 150, 150, 150, 200,
                (120, 120, 120, 120, 100, 100, 100, 100, 100, 100, 100, 100), (0, 0), (100, 50, 50)),
}
LASTBOSS_ERB_NUM = 2
LASTBOSS_NAMES = {1: "Ｋ触手", 2: "天使の樹"}  # _GETNAME（TENTACLE_LASTBOSS_2_天使の樹.ERB:8–15 依 FLAG:21 變化，由 angel_tree.py 提供）


def lastboss_attack_routine(ctx: Ctx) -> int:
    """`TENTACLE_LASTBOSS_1_ATTACK_ROUTINE`（TENTACLE_LASTBOSS_1_Ｋ触手.ERB:129–154）。BASE:防御 は TARGET のもの。"""
    st = ctx.state
    if st.flag[11] == 2:
        from .angel_tree import attack
        return attack(ctx)
    c = tc(ctx)
    l1 = st.rng.rand(100)
    l2 = c.base[ctx.data.index_of("BASE", "防御")] - 200
    if st.flag[17] >= st.flag[16] and l1 < 35:  # :134–135 油断していると距離を取る
        return 4
    if l2 and l1 < div(l2, 2):  # :137–144（l2 が負なら成立しない）
        return 1 if l1 < 5 else 3 if l1 < 35 else 2
    if l1 < 50:
        return 1
    if l1 < 74:
        return 2
    if l1 < 98:
        return 3
    return 4


def _is_lastboss_access(st: GameState) -> bool:
    """TENTACLE_ACCESS の分岐（COMMON_TENTACLE_DATA.ERB:202）：GET_LASTBOSS_PHASE_F() != 0 で雑魚／クズ市民でなければ
    ラスボス側（`TENTACLE_LASTBOSS_{FLAG:11}_*`）。FLAG:10 は見ない（ラスボス出現後の悪堕ちキャラ戦もこちら）。"""
    return not (get_lastboss_phase(st) == 0 or enemy_type_check(st, "MOB") == 1 or enemy_type_check(st, "CITIZEN") == 1)


def tentacle_level(st: GameState) -> int:
    """`COMMON_TENTACLE_DATA.ERB@TENTACLE_LEVEL`:356–406（S04 で移植済みの関数を使う）。"""
    from ..turnend import tentacle_level as _tl

    return _tl(st)


def tentacle_status_hosei(st: GameState, value: int, bonus: int = 100) -> int:
    """`COMMON_TENTACLE_DATA.ERB@TENTACLE_STATUS_HOSEI`:348–352：((Lv*10 + 95) * 値) / 100 + bonus。"""
    return div((tentacle_level(st) * 10 + 95) * value, 100) + bonus


def boss_data(st: GameState) -> BossData:
    """TENTACLE_ACCESS の分岐（:202）：ボス（SAVESTR:13 == "BOSS"）とラスボス 1（Ｋ触手、S27）。"""
    if _is_lastboss_access(st):
        if st.flag[11] == 2:
            from .angel_tree import data
            return data(st)
        if st.flag[11] not in LASTBOSSES:
            raise NotImplementedError(f"TENTACLE_LASTBOSS_{st.flag[11]} は存在しない（TRYCALLFORM 不発の RESULT は再現しない）")
        return LASTBOSSES[st.flag[11]]
    if enemy_type_check(st, "MOB") == 1 or enemy_type_check(st, "CITIZEN") == 1:
        raise NotImplementedError("雑魚／クズ市民の触手データは未移植（S05 はボス触手のみ）")
    if st.savestr[13] != "BOSS" or st.flag[11] not in BOSSES:
        raise NotImplementedError(f"TENTACLE_{st.savestr[13]}_{st.flag[11]} のデータは未移植")
    return BOSSES[st.flag[11]]


def _tentacle_func_missing(st: GameState) -> bool:
    """TENTACLE_ACCESS のボス分岐（:202 GET_LASTBOSS_PHASE_F() == 0）で `TENTACLE_{SAVESTR:13}_{FLAG:11}_*` が存在しない
    （本作のボスは 1〜7：tentacle.BOSS_ERB_NUM）。数値を返すキーでは RESULT が前の値のままになり再現できないので
    呼び出し側は停止する（boss_data）。"""
    if _is_lastboss_access(st):
        # S27：ラスボス側（:258–306）で TENTACLE_LASTBOSS_{FLAG:11} が無い（ラスボス出現後の悪堕ちキャラ戦 FLAG:11 = 0）
        return st.flag[11] not in LASTBOSS_NAMES
    return (
        enemy_type_check(st, "MOB") == 0
        and enemy_type_check(st, "CITIZEN") == 0
        and st.savestr[13] == "BOSS"
        and st.flag[11] not in BOSSES
    )


def tentacle_access(ctx: Ctx, key: str) -> int | str:
    """`COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS, ARGS`:198–309（ボス触手分）。

    "NAME" は名前を PRINTFORM して "" を返す、"GETNAME" は名前（RESULTS）を返す。
    """
    st = ctx.state
    if enemy_type_check(st, "CITIZEN") == 1:
        from .citizen import access

        return access(ctx, key)
    if enemy_type_check(st, "MOB") == 1:
        from .mob import access

        return access(ctx, key)
    if key in ("NAME", "GETNAME") and _tentacle_func_missing(st):
        # :200 `RESULTS'="【エラー："+SAVESTR:13+"_"+TOSTR(FLAG:11)+"に対するTENTACLE_ACCESS('"+ARGS+"')関数失敗】"` の後
        # TRYCALLFORM が不発なので RESULTS はそのまま（"NAME" は内部で "GETNAME" を呼ぶので 'GETNAME' の文になる）。
        # 悪堕ちキャラ戦（FLAG:11 = 0：ACTION.ERB:38）で無条件に呼ばれる箇所（MESSAGE_BATTLE.ERB:1898 など）で起こる。
        name = f"【エラー：{st.savestr[13]}_{st.flag[11]}に対するTENTACLE_ACCESS('GETNAME')関数失敗】"
        if key == "NAME":
            ctx.out.print(name)
            return ""
        return name
    if _is_lastboss_access(st) and st.flag[11] == 2:
        from .angel_tree import access
        return access(ctx,key)
    b = boss_data(st)
    if key == "NAME":
        ctx.out.print(b.name)
        return ""
    if key == "GETNAME":
        return b.name
    if key == "HP":
        return tentacle_status_hosei(st, b.hp[0], b.hp[1])
    if key == "SYASEI":
        return b.syasei[0] + tentacle_level(st) * b.syasei[1]
    if key == "SAKUSEI":
        return b.sakusei
    if key == "YUDAN":
        return b.yudan
    if key == "KOUGEKI":
        return tentacle_status_hosei(st, b.kougeki, b.stat_bonus[0])
    if key == "BOUGYO":
        return tentacle_status_hosei(st, b.bougyo, b.stat_bonus[1])
    if key == "BINSYOU":
        return tentacle_status_hosei(st, b.binsyou, b.stat_bonus[2])
    if key == "CHISEI":
        return tentacle_status_hosei(st, b.chisei, 10)
    if key == "SHORT":
        return b.short
    if key == "MIDDLE":
        return b.middle
    if key == "LONG":
        return b.long
    if key == "HOLD":
        return b.hold
    if key == "ATTACK_ROUTINE":
        if _is_lastboss_access(st):  # S27：Ｋ触手の専用ルーチン
            return lastboss_attack_routine(ctx)
        value, per = b.attack_routine
        if per == 0:
            return 0
        return value if st.rng.rand(100) < per else 0
    raise KeyError(key)


def tentacle_palam_hosei(ctx: Ctx) -> tuple[int, ...]:
    """TENTACLE_ACCESS "PALAM_HOSEI"（Ｐ触手は TFLAG:23 が非 0 なら全て /4：TENTACLE_BOSS_6_Ｐ触手.ERB:125–129）。"""
    st = ctx.state
    if enemy_type_check(st, "CITIZEN") == 1:
        # CITIZEN_1.ERB@TENTACLE_CITIZEN_1150_PALAM_HOSEI:97–123。
        r = (100,100,100,100,50,50,50,50,50,50,50,50)
        st.set_result_x(*r)
        return r
    if enemy_type_check(st, "MOB") == 1:
        from .mob import PALAM

        r = PALAM[st.flag[11]]
        st.set_result_x(*r)
        return r
    b = boss_data(st)
    r = (tuple(div(v, 4) for v in b.palam_hosei)
         if not _is_lastboss_access(st) and st.flag[11] == 6 and st.tflag[23] else b.palam_hosei)
    # ボスの PALAM_HOSEI の 12 値 RETURN（例 TENTACLE_BOSS_1_Ｃ触手.ERB:125）→ TENTACLE_ACCESS:253 も同じ 12 値（共用 RESULT）
    st.set_result_x(*r)
    return r


def print_enemy_prefix(ctx: Ctx) -> None:
    """`IF ENEMY_TYPE_CHECK_F("AKUOTI") == 0 / CALL TENTACLE_ACCESS, "NAME" / ELSEIF … == 1 /
    PRINTFORM %PRINT_TRANSCALLNAME(FLAG:111)%`（地の文で多用される敵名の表示。例：MESSAGE_BATTLE.ERB:1083–1087）。"""
    from ..action import print_transcallname

    st = ctx.state
    if enemy_type_check(st, "AKUOTI") == 0:
        tentacle_access(ctx, "NAME")
    else:
        ctx.out.print(print_transcallname(st, st.flag[111]))


def msg_other(ctx: Ctx, name: str, args: tuple = ()) -> None:
    """`CALL MESSAGE_OTHER_{name}`（`地の文/MESSAGE_OTHER.ERB`：洗脳／悪堕ちキャラ側の口上
    `TRYCALLFORM KOJO_ROOT(CFLAG:(FLAG:111):6, "OTHER_{name}")` を SETCOLOR 96,96,96〜RESETCOLOR で囲んだもの）。
    catalog で実行できなければ口上呼び出しだけを行う。"""
    from ..action import kojo_root_full

    st = ctx.state
    # MESSAGE_OTHER.ERB:56–97 の 4 関数は `ARG = 0` を取り `SIF ARG == 0` のときだけ口上、ATTACK_GUARD は
    # "OTHER_BATTLE_CHARA_ATTACK_FALSE" を呼ぶ（原作どおり）。その他は本体が口上 1 行だけ（MESSAGE_OTHER.ERB 全関数を確認）。
    code = "OTHER_BATTLE_CHARA_ATTACK_FALSE" if name == "BATTLE_CHARA_ATTACK_GUARD" else f"OTHER_{name}"

    def fallback() -> None:
        if not (args and args[0] != 0):
            kojo_root_full(ctx, st.charas[st.flag[111]].cflag[6], code)
        ctx.out.reset_color()

    run_chinobun(ctx, f"MESSAGE_OTHER_{name}", args, fallback=fallback)


# --- 心境（ヒロイン関連/CHARA_SHINKYOU.ERB）-----------------------------------------

_SHINKYOU_NAMES = {0: "普通", 1: "倒錯", 2: "怒り", 3: "諦観", 4: "冷静", 5: "動揺", 6: "高揚", 7: "消沈"}
# @SHINKYOU_CHECK:5–117（値：その心境で TIMES する係数）
_SHINKYOU_FACTOR: dict[int, dict[str, str]] = {
    1: {"KOUGEKI": "0.80", "BOUGYO": "0.80", "BINSYOU": "0.80"},
    2: {"KOUGEKI": "1.20", "BOUGYO": "1.20", "CHISEI": "0.80"},
    3: {"KOUGEKI": "0.80", "BOUGYO": "0.80", "CHISEI": "0.80"},
    4: {"BOUGYO": "1.20", "BINSYOU": "1.20", "CHISEI": "1.20"},
    5: {"BOUGYO": "0.80", "BINSYOU": "0.80", "CHISEI": "1.20"},
    6: {"KOUGEKI": "1.20", "BINSYOU": "1.20"},
    7: {"KOUGEKI": "0.80", "BINSYOU": "0.80"},
}


def shinkyou_name(ctx: Ctx) -> str:
    return _SHINKYOU_NAMES.get(tv(ctx)[1], "")  # type: ignore[index]


def shinkyou_check(ctx: Ctx, kind: str, value: int) -> int:
    """`@SHINKYOU_CHECK, ARGS, ARG`（CHARA_SHINKYOU.ERB:5–117）。"PRINT" は心境名を PRINT する。"""
    sk = tc(ctx).tcvarn[1]
    if sk not in _SHINKYOU_NAMES:
        # 0–7 以外では関数終端（RETURN なし）→ RESULT = 0（Process.ScriptProc.cs:61–67）
        return 0
    if kind == "PRINT":
        ctx.out.print(_SHINKYOU_NAMES[sk])
        return value
    factor = _SHINKYOU_FACTOR.get(sk, {}).get(kind)
    return times(value, factor) if factor else value


def _print_shinkyou_changed(ctx: Ctx, code: str, wait: bool = True) -> None:
    """地の文/MESSAGE_BATTLE.ERB@MESSAGE_SHINKYOU_CHANGE_*:1910–1973。"""
    st = ctx.state
    ctx.out.print(f"{print_transcallname(st, st.target)}は ")
    shinkyou_check(ctx, "PRINT", 0)
    ctx.out.printl("状態 になった")
    kojo_root(ctx, f"BATTLE_SHINKYOU_CHANGE_{code}")
    if wait:
        ctx.out.printw()


def _shinkyou_set(ctx: Ctx, kind: str, value: int, code: str, wait: bool = True) -> None:
    """SHINKYOU_CHANGE_IKARI 等の共通部（:271–391）。"""
    st = ctx.state
    c = tc(ctx)
    per = seikaku_hosei_shinkyou(seikaku_check(ctx.data, c), kind)
    if st.rng.rand(100) < per:
        if c.tcvarn[1] != value:
            c.tcvarn[1] = value
            _print_shinkyou_changed(ctx, code, wait)
            c.tcvarn[11] = 0


def _hp_ki_percent(ctx: Ctx) -> tuple[int, int]:
    c = tc(ctx)
    l0 = percent_cal(c.base[0], c.maxbase[0])
    l1 = percent_cal(c.base[1], c.maxbase[1])
    if c.cflag[1] == 2:
        return 100, 100
    return l0, l1


def shinkyou_change(ctx: Ctx, kind: str) -> None:
    """`@SHINKYOU_CHANGE, ARGS`（CHARA_SHINKYOU.ERB:125–204）。"""
    st = ctx.state
    c = tc(ctx)
    sk = c.tcvarn[1]
    local = 0
    mb = lambda: message_branch(ctx)  # noqa: E731
    if sk == 1:
        if mb() & DARAKU:
            local += 1
        if mb() & KAIRAKU_TOROKE:
            local += 2
        if mb() & SEI_TEIKOU:
            local += 1
        if c.tcvarn[11] < 1:
            local = 20
    elif sk == 2:
        if (mb() & KUSEN) == 0:
            local += 1
        if kind == "REISEI":
            local += 1
        if c.tcvarn[0] == 0:
            local += 1
        if c.tcvarn[11] < 2:
            local = 20
    elif sk == 3:
        if mb() & ZETSUBOU:
            local += 2
        if mb() & KUSEN:
            local += 1
        if kind not in ("TOUSAKU", "DOUYOU", "SYOUTIN"):
            local += 1
        if c.tcvarn[0] == 0:
            local += 2
        if c.tcvarn[11] < 1:
            local = 20
    elif sk == 4:
        if mb() & ZETSUBOU:
            local += 2
        if (mb() & SEI_TEIKOU) == 0:
            local += 1
        if kind == "KOUYOU":
            local += 1
        if c.tcvarn[11] < 2:
            local = 20
    elif sk == 5:
        if mb() & ZETSUBOU:
            local += 1
        if mb() & KUSEN:
            local += 1
        if c.tcvarn[0] == 0:
            local += 2
        if c.tcvarn[11] < 1:
            local = 20
    elif sk == 6:
        if (mb() & KUSEN) == 0:
            local += 1
        if (mb() & SEI_TEIKOU) == 0:
            local += 1
        if c.tcvarn[11] < 2:
            local = 20
        if c.tcvarn[0] == 0:
            local = 0
    elif sk == 7:
        if mb() & ZETSUBOU:
            local += 1
        if mb() & KUSEN:
            local += 1
        if c.tcvarn[11] < 1:
            local = 20
    if st.rng.rand(100) < local * 5:  # :201–202
        return
    # :204 TRYCALLFORM SHINKYOU_CHANGE_%ARGS%
    if kind == "NORMAL":  # :209–218
        if c.tcvarn[1] == 0:
            return
        c.tcvarn[1] = 0
        ctx.out.printl()
        from ..action import print_callname

        ctx.out.print(f"{print_callname(st, st.target, 1)}の心境が")
        shinkyou_check(ctx, "PRINT", 0)
        ctx.out.printl("に戻った")
        c.tcvarn[11] = 0
    elif kind == "TOUSAKU":  # :223–246
        l0, l1 = _hp_ki_percent(ctx)
        if l0 <= 60 and l1 <= 60:
            _shinkyou_set(ctx, "TOUSAKU", 1, "TOUSAKU")
    elif kind in ("IKARI_TEIKAN", "REISEI_DOUYOU", "KOUYOU_SYOUTIN"):  # :253–365
        l0, l1 = _hp_ki_percent(ctx)
        hi, lo = {
            "IKARI_TEIKAN": (("IKARI", 2, "IKARI", True), ("TEIKAN", 3, "TEIKAN", True)),
            "REISEI_DOUYOU": (("REISEI", 4, "REISEI", False), ("DOUYOU", 5, "DOUYOU", True)),
            "KOUYOU_SYOUTIN": (("KOUYOU", 6, "KOUYOU", True), ("SYOUTIN", 7, "SYOUTIN", True)),
        }[kind]
        if l0 >= 60 and l1 >= 60:
            _shinkyou_set(ctx, hi[0], hi[1], hi[2], hi[3])
        elif l0 <= 20 and l1 <= 20:
            _shinkyou_set(ctx, lo[0], lo[1], lo[2], lo[3])
    elif kind in ("IKARI", "TEIKAN", "REISEI", "DOUYOU", "KOUYOU", "SYOUTIN"):
        value = {"IKARI": 2, "TEIKAN": 3, "REISEI": 4, "DOUYOU": 5, "KOUYOU": 6, "SYOUTIN": 7}[kind]
        # MESSAGE_SHINKYOU_CHANGE_REISEI のみ PRINTW なし（MESSAGE_BATTLE.ERB:1937–1943）
        _shinkyou_set(ctx, kind, value, kind, kind != "REISEI")
    else:
        raise KeyError(kind)


# --- 変身補正・戦技補正（COMMON_BATTLE_FUNC.ERB）------------------------------------


def correction_binsyou(arg: int) -> int:
    """`@CORRECTION_BINSYOU_F`（COMMON_BATTLE_FUNC.ERB:22–35）。"""
    if arg < 10:
        return div(arg * 15, 100)
    if arg < 25:
        return div(arg * 38, 100)
    if arg < 45:
        return div(arg * 75, 100)
    if arg >= 75:
        return 64 + div(arg * 15, 100)
    return arg


def correction_trans(ctx: Ctx, value: int) -> int:
    """`@CORRECTION_TRANS`（:39–50）：TARGET の変身状態による補正。"""
    c = tc(ctx)
    tr = t(ctx, c, "変身能力")
    if (tr == 1 and c.cflag[1] == 0) or tr == -1:
        return div(value * c.cflag[10], 100)
    if tr == 1 and c.cflag[1] == 2:
        return div(value * max(c.cflag[11], 100), 100)
    return value


_SENGI = {
    0: ("0.90", "0.95", "1.00", "1.025", "1.05", "1.075", "1.10", "1.125", "1.1375", "1.15"),
}
_SENGI_DAMAGE = {
    0: ("1.00", "1.10", "1.15", "1.20", "1.25", "1.30", "1.35", "1.40", "1.45", "1.50"),
    1: ("0.95", "1.00", "1.10", "1.20", "1.30", "1.40", "1.45", "1.50", "1.55", "1.60"),
    2: ("0.90", "0.95", "1.05", "1.15", "1.30", "1.40", "1.50", "1.60", "1.65", "1.70"),
}
_SENGI_AVOID = ("0.75", "0.80", "0.85", "0.90", "0.95", "1.00", "1.025", "1.05", "1.075", "1.10")


def correction_sengi(ctx: Ctx, value: int, dist: int, who: int) -> int:
    """`@CORRECTION_SENGI`（:54–84）：ABL:(30+dist) の Lv 0–9 で TIMES（範囲外は無補正）。"""
    lv = ctx.state.charas[who].abl[30 + dist]
    return times(value, _SENGI[0][lv]) if 0 <= lv <= 9 else value


def correction_sengi_damage(ctx: Ctx, value: int, dist: int, who: int) -> int:
    """`@CORRECTION_SENGI_DAMAGE`（:88–160）。"""
    lv = ctx.state.charas[who].abl[30 + dist]
    return times(value, _SENGI_DAMAGE[dist][lv]) if 0 <= lv <= 9 else value


def correction_sengi_avoid(ctx: Ctx, value: int, dist: int, who: int) -> int:
    """`@CORRECTION_SENGI_AVOID`（:164–191）：近距離（ABL:30）のみ。"""
    if dist != 0:
        return value
    lv = ctx.state.charas[who].abl[30]
    return times(value, _SENGI_AVOID[lv]) if 0 <= lv <= 9 else value


# --- 戦闘スタイル（武器と衣装/武器カスタマイズ関連/FIGHT_STYLE.ERB）-------------------------

_STYLES = {1: "連続", 2: "装甲", 3: "撹乱", 4: "重撃", 5: "広範", 6: "全力", 7: "知略", 8: "設置", 9: "使役", 10: "反撃"}


def fstyle_name(ctx: Ctx, who: int, dist: int) -> str:
    """`@FSTYLE_NAME_F, ARG, ARG:1`（FIGHT_STYLE.ERB:8–35）：CDFLAG:who:dist:戦闘スタイル。"""
    idx = ctx.data.index_of("CDFLAG2", "戦闘スタイル")
    if dist < 0:
        raise IndexError(dist)
    return _STYLES.get(ctx.state.charas[who].cdflag[(dist, idx)], "通常")


# --- 画面の小物 ---------------------------------------------------------------------


def print_distance(ctx: Ctx) -> None:
    """`BATTLE_SHOW_STATUS.ERB@PRINT_DISTANCE`:424–463（色は省略せず近似：近=赤 中=黄 遠=緑）。"""
    out = ctx.out
    v = tc(ctx).tcvarn
    out.reset_color()
    out.print("[")
    if v[0] == 0:
        if v[12] & KYOUKOUSOKU:
            out.set_color((200, 50, 50))
            s0 = "強拘束"
        else:
            out.set_color((255, 146, 238))
            s0 = "拘束中"
        s1 = ""
    else:
        out.set_color({1: (255, 0, 0), 2: (255, 255, 0), 3: (64, 255, 64)}.get(v[0], (255, 255, 255)))
        s0 = {1: "近", 2: "中", 3: "遠"}.get(v[0], "")
        s1 = "空中" if v.get_bit(216, 1) else "着地" if v.get_bit(216, 2) else "距離"
    out.print(s0)
    if v.get_bit(216, 1):
        out.set_color((0, 60, 255))
    elif v.get_bit(216, 2):
        out.set_color((255, 128, 0))
    out.print(s1)
    out.reset_color()
    out.print("]")
    ctx.state.result[0] = 0  # 関数終端（RETURN なし：Process.ScriptProc.cs:61–67）。COMF103:197 の不発 TRYCALLFORM が読む


def printw_or_l(ctx: Ctx) -> None:
    """`IF CONFIG_CHECK_SCREEN_F(3) == 0 / PRINTW / ELSE / PRINTL`。"""
    if config_check_screen(ctx.state, 3) == 0:
        ctx.out.printw()
    else:
        ctx.out.printl()


def isqrt_e(value: int) -> int:
    """SQRT（負数はエラー）。"""
    return isqrt(value)


def lim(v: int, lo: int, hi: int) -> int:
    return limit(v, lo, hi)


# --- ランダム抽選（汎用関数/RANDCHOOSE.ERB）-------------------------------------------
# RANDCHOOSE_NUM:0 = 候補数、:1〜 = 候補値 + 1（0 は空き）。


def clear_randchoose(st: GameState) -> None:
    """`@CLEARRANDCHOOSE`（ARG = 0：VARSET RANDCHOOSE_NUM）:52–61。"""
    st.temp.randchoose.clear()


def add_randchoose(st: GameState, arg: int) -> None:
    """`@ADDRANDCHOOSE(ARG)`:3–21。"""
    rc = st.temp.randchoose
    if arg < 0:
        raise NotImplementedError("ADDRANDCHOOSE に負の値（原作はエラー表示）")
    rc[0] += 1
    hoge = rc[0]
    while rc[hoge] != 0:
        hoge += 1
    rc[hoge] = arg + 1
    rc[0] = hoge


def choicecount(st: GameState) -> int:
    """`@CHOICECOUNT_F()`:78–81。"""
    return st.temp.randchoose[0]


def randchoose_f(st: GameState) -> int:
    """`@RANDCHOOSE_F()`:39–47。"""
    rc = st.temp.randchoose
    local = st.rng.rand(rc[0]) + 1
    return rc[local] - 1


def clear_specific_choose(st: GameState, arg: int) -> None:
    """`@CLEARSPECIFICCHOOSE(ARG)`:65–74：ARG の候補を全て ARRAYREMOVE で詰めて取り除く。

    候補は 1〜RANDCHOOSE_NUM:0 に詰めて入っている（ADDRANDCHOOSE）ので、結果は「値の一致する要素を除いた列」。
    """
    rc = st.temp.randchoose
    values = [rc[k] for k in range(1, rc[0] + 1)]
    kept = [x for x in values if x != arg + 1]
    for k in range(1, rc[0] + 1):
        rc[k] = kept[k - 1] if k - 1 < len(kept) else 0
    rc[0] = len(kept)


# --- 性攻撃系の地の文（S06）------------------------------------------------------------


def chinobun(ctx: Ctx, func: str) -> None:
    """性攻撃・絶頂・射精などの地の文（`地の文/MESSAGE_SEX*.ERB` ほか）の本文の代わりに 1 行出す。

    DEVIATION（表示のみ）：S06 では地の文の本文は移植せず、関数名を示す 1 行に置き換える
    （本文は S07 の地の文 catalog で扱う）。地の文の中にある状態変化（SET_TENTACLE_SIZE_BY_MESSAGE、
    TFLAG:4／TFLAG:21／TFLAG:23、FLAG:900、LOSTVIRGIN、NINSIN_HANTEI など）は各呼び出し側で移植している。
    本文だけを選ぶための RAND は引かない（deviations.md「亂數」の範囲）。
    """
    ctx.out.printl(f"〈地の文：{func}〉")


def run_chinobun(ctx: Ctx, func: str, args: tuple = (), fallback=None) -> bool:
    """S07：地の文 `func` を catalog（`ctx.narration.run_function`）で実行する。実行できなければ `chinobun` の
    1 行を出し、`fallback`（その地の文の中の本文以外の処理＝KOJO_ROOT 呼び出し等の Python 移植）を実行する。"""
    if ctx.narration.run_function(ctx, func, list(args)):
        return True
    chinobun(ctx, func)
    if fallback is not None:
        fallback()
    return False


_SWOON_SUBJ = ("朦朧とした意識の", "倒れ込んだ", "地に伏せた", "寝そべった", "気を失いかけた", "気絶しかけている",
               "倒れている", "伏せっている", "寝そべっている", "気を失いかけている")
_SWOON = ("気絶した", "倒れ込んだ", "地に伏せた", "寝そべった", "気を失った", "気絶している", "倒れている",
          "伏せっている", "寝そべっている", "気を失っている")


def print_swoon(ctx: Ctx) -> str:
    """`地の文/MESSAGE.ERB@PRINT_SWOON`:192–245（気絶中のみ RAND:10 で形容を選ぶ。非気絶は空文字）。"""
    c = tc(ctx)
    if not (c.tcvarn[12] & KIZETU):
        return ""
    r = ctx.state.rng.rand(10)
    return (_SWOON_SUBJ if t(ctx, c, "主観視点") > 0 else _SWOON)[r]
