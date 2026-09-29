"""行動実行：`ゲーム内_行動実行処理/ACTION.ERB@ACTION_MAIN` と `REST`／`TRAINING`。

路徑相對 `source/earGVP/ERB/`。INPUT を含む処理はジェネレータ（`yield` で入力待ち、`send(値)` で再開）。
流れの制御（`BEGIN TURNEND`／`BEGIN TRAIN`）は戻り値の `Step` で呼び出し元（`eragvt.game.turn`）に返す。
"""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from enum import Enum

from ..data.csv_loader import GameData
from ..state import GameState
from ..state.character import Character
from ..state.constants import ActionPlan, GameOption
from ..text import NarrationService, TextOutput
from .chara_common import baseup_cal_shield, level_status, seikaku_check, talent
from .era import div, limit, times
from .opening import game_option
from .shop import (
    ACTION_NAMES,
    C_BROKEN,
    C_HP,
    C_LIMB,
    C_PREGNANT,
    C_SENSHI,
    C_YAMA,
    _bar,
    _find_action,
    charanum_active,
    is_action_incapable,
    number_on_frontline,
    training_downtairyoku,
)

InputGen = Generator[None, int, "Step"]


class Step(str, Enum):
    """BEGIN／JUMP の行き先。"""

    ACTION_MAIN = "action_main"  # JUMP ACTION_MAIN
    TURNEND = "turnend"  # BEGIN TURNEND
    SHOP = "shop"  # BEGIN SHOP
    TRAIN = "train"  # BEGIN TRAIN（S05）


@dataclass
class Ctx:
    state: GameState
    data: GameData
    out: TextOutput
    narration: NarrationService


# DIM.ERH:173–184 リラクゼーション施設（FLAG:53 のビット）
KANYOU = 1
JOUSHITSU_BED = 2
SAIKOUKYUU_BED = 4
MASSAGE_CHAIR = 8
SHOWER = 16
GAME_CORNER = 32
DAIYOKUJOU = 64
BIYOU_ONSEN = 128
BEAUTY_SALON = 256
FUUKEIGA = 512
OBJET = 1024
FUNSUI = 2048


# --- 共通 ----------------------------------------------------------------------


def config_check_screen(state: GameState, n: int) -> int:
    """`SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG_CHECK_SCREEN_F`:521–524 = GETBIT(FLAG:801, n)。"""
    return int(state.flag.get_bit(801, n))


def config_check_event(state: GameState, n: int) -> int:
    """`@CONFIG_CHECK_EVENT_F`（同:525–528）= GETBIT(FLAG:802, n)。"""
    return int(state.flag.get_bit(802, n))


def config_check_prison(state: GameState, n: int) -> int:
    """`@CONFIG_CHECK_PRISON_F`（同:533–536）= GETBIT(FLAG:804, n)。"""
    return int(state.flag.get_bit(804, n))


def config_check_other(state: GameState, n: int) -> int:
    """`@CONFIG_CHECK_OTHER_F`（同:537–540）= GETBIT(FLAG:805, n)。"""
    return int(state.flag.get_bit(805, n))


def config_check_maniac(state: GameState, n: int) -> int:
    """`SYSTEM/コンフィグ/CONFIG_GLOBAL_MANIAC.ERB@CONFIG_CHECK_MANIAC_F`:43–47 = 1 - GETBIT(FLAG:850, n)。"""
    return 1 - int(state.flag.get_bit(850, n))


_KOJO_SHIELD_CODES = (
    # KOJO_ROOT.ERB:23–39：部位結界（BASE:30〜33）が残っているときに口上を出さない code（STRFIND の部分一致）
    (30, ("SEX_COM0", "SEX_COM1", "SPCOM0")),
    (31, ("SEX_COM2", "SEX_COM3", "SPCOM1")),
    (32, ("SEX_COM4", "SEX_COM5", "SPCOM2")),
    (33, ("SEX_COM6", "SEX_COM7", "SPCOM3", "SPCOM5")),
)


def kojo_root(ctx: Ctx, code: str, force_print: int = 0) -> int:
    """`TRYCALLFORM KOJO_ROOT(CFLAG:6, code, FORCEPRINT)`（口上/口上システム関係/KOJO_ROOT.ERB）の TARGET 分。

    DEVIATION: 口上本文は未移植（deviations.md「口上」）。NarrationService が None を返したら
    「口上が見つからない」として RETURN -1（:54–58）。状態への影響は FLAG:62 = 0（"OTHER_" を含まない code、
    :50／:71）と FLAG:900 = 0（:57／:88）。
    :17–21 気絶中（TCVARn:12 & 1）で FORCEPRINT が 0 なら FLAG:900 = 0、RETURN 0（FLAG:62 は触らない）。
    :23–39 部位結界が残っていて code が該当する性コマンドなら同様に RETURN 0（STRFIND は部分一致なので
    "SEX_COM1" は "SEX_COM10"〜"SEX_COM19" にも一致する：原作どおり）。
    """
    st = ctx.state
    c = st.target_chara
    if (c.tcvarn[12] & 1) and not force_print:
        st.flag[900] = 0
        return 0
    for base_no, codes in _KOJO_SHIELD_CODES:
        if c.base[base_no] > 0 and any(k in code for k in codes):
            st.flag[900] = 0
            return 0
    if "OTHER_" in code:
        raise NotImplementedError(f"KOJO_ROOT の OTHER_ 系（{code}）は未移植")
    text = ctx.narration.narrate(c.cflag[6], code, None)
    st.flag[62] = 0
    st.flag[900] = 0
    if text is None:
        return -1
    for line in text.split("\n"):
        ctx.out.printl(line)
    return len(text.split("\n"))


def print_transcallname(state: GameState, index: int) -> str:
    """`汎用関数/コモン関数.ERB@PRINT_TRANSCALLNAME`:251–262。"""
    c = state.charas[index]
    if c.cflag[6] == 3:
        return "あなた"
    if c.cflag[3] == 1 and c.cflag[1] != 0:
        return c.cstr[1]
    return c.callname


def print_callname(state: GameState, index: int, system: int = 0) -> str:
    """`@PRINT_CALLNAME`（コモン関数.ERB:268–285）。"""
    c = state.charas[index]
    if system == 0:
        return "あなた" if c.cflag[6] == 3 else c.callname
    return c.callname + ("(あなた)" if c.cflag[6] == 3 else "")


def _wait_or_line(ctx: Ctx) -> None:
    """`IF CONFIG_CHECK_SCREEN_F(3) == 0 / PRINTW / ELSE / PRINTL`。"""
    if config_check_screen(ctx.state, 3) == 0:
        ctx.out.printw()
    else:
        ctx.out.printl()


# --- @ACTION_MAIN ----------------------------------------------------------------


def action_main(ctx: Ctx) -> InputGen:
    """`ゲーム内_行動実行処理/ACTION.ERB@ACTION_MAIN`:6–175。一度に 1 キャラ。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    # :10–14
    if st.flag[799] == 0:
        st.flag[798] = st.target
        out.printl()
        out.printl("行動開始！")
    # :17–21
    st.flag[799] += 1
    if st.flag[799] >= st.charanum:
        return Step.TURNEND
    # :24–33 戦闘支援人数
    st.flag[43] = 0
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        if is_action_incapable(data, st, ActionPlan.SUPPORT, i) > 0:
            continue
        c = st.charas[i]
        if c.cflag[0] == 0 and c.cflag[100] == ActionPlan.SUPPORT:
            st.flag[43] += 1
    if st.flag[43] >= charanum_active(st):
        st.flag[43] = 0
    # :36–39
    for k in (10, 11, 45, 48):
        st.flag[k] = 0
    # :42–43
    if st.charas[st.flag[799]].cflag[0] != 0:
        return Step.TURNEND
    # :46
    st.target = st.flag[799]
    c = st.target_chara
    # :49–52 控えメンバー
    if c.cflag[999] == 0:
        rest(ctx)
        return Step.TURNEND
    # :55–56
    if c.cflag[100] == ActionPlan.NONE:
        c.cflag[100] = ActionPlan.REST
    # :59–63
    out.printl()
    out.printl()
    out.printl()
    out.printl(f"【{c.callname}の行動：{ACTION_NAMES[_find_action(c.cflag[100])]}】")
    out.drawline()
    # :66–71
    if is_action_incapable(data, st, c.cflag[100], st.target):
        out.printl()
        out.printl(action_ngreason(ctx, st.target, c.cflag[100]))
        rest(ctx)
        return Step.TURNEND
    plan = c.cflag[100]
    if plan == ActionPlan.TRAINING:  # :100–106
        if game_option(st, GameOption.SOLO):
            st.flag[41] += 1
        yield from training(ctx)
        return Step.TURNEND
    if plan == ActionPlan.REST:  # :108–110
        rest(ctx)
        return Step.TURNEND
    if plan == ActionPlan.SUPPORT and number_on_frontline(data, st) == 0 and st.flag[41] == 0:
        # :133–140 戦闘に参加するキャラが居ない場合は休憩（SUPPORT 本体より前に判定される）
        out.printl()
        out.printl("戦闘を行うメンバーが居ないため、休憩にします")
        rest(ctx)
        st.flag[43] -= 1
        return Step.TURNEND
    if plan == ActionPlan.SORTIE:  # :75–96
        from .battle.encount import encount, mob_tentacle_encount

        st.flag[41] += 1
        result = encount(ctx)
        if result == 0:
            result = mob_tentacle_encount(ctx)
        if result == 0:
            _wait_or_line(ctx)
            return Step.TURNEND
        if result > 0:
            return Step.TRAIN
        # RESULT < 0（MOB_TENTACLE_BATTLE の候補なし）は SELECTCASE を抜けて ACTION_MAIN の末尾へ
        raise NotImplementedError("雑魚戦の候補なし（MOB_TENTACLE_BATTLE が -1）後の処理は未移植")
    # 活動 SEISAN／防衛 GUARD／支援 SUPPORT／情報 GATHER_INFORMATION／自由 PASTIME は未移植
    # （影響範囲は docs/wiki/era/actions.md）。
    raise NotImplementedError(f"行動「{ACTION_NAMES[_find_action(plan)]}」は未移植（休憩・鍛錬・出撃のみ移植済み）")


def action_ngreason(ctx: Ctx, who: int, action: int) -> str:
    """`ACTION.ERB@ACTION_NGREASON`:188–199。`\\@ ? # \\@` の両辺は前後の空白が除かれる
    （reference/emuera-1824/Emuera/Sub/LexicalAnalyzer.cs@AnalyseFormattedString:1217–1221、AnalyseYenAt:1238）。"""
    st, data = ctx.state, ctx.data
    name = ACTION_NAMES[_find_action(action)]
    cn = st.charas[who].callname

    def inc(k: int) -> int:
        return is_action_incapable(data, st, action, who, k)

    if inc(C_BROKEN):
        return f"{cn}は廃人化しているため、休憩以外何もできません"
    if inc(C_LIMB):
        return f"{cn}は四肢欠損していて{name}できないため、休憩します"
    if inc(C_PREGNANT):
        return f"{cn}は妊娠中なため、休憩します"
    if inc(C_YAMA) or inc(C_SENSHI):
        return f"{cn}は{name}でき" + ("ず、体力も残り少ない" if inc(C_HP) else "ない") + "ため、休憩します"
    return f"{cn}は体力が残り少ないため、休憩します"


# --- @REST -------------------------------------------------------------------------

_REST_BASE = {1: 30, 2: 40, 3: 50, 4: 60, 5: 75}  # ACTION_REST.ERB:9–19


def _fatigue_scale(value: int, fatigue: int) -> int:
    """疲労度による回復量低下（ACTION_REST.ERB:46–56、SHOP_TURNEND.ERB:629–639 と同形）。"""
    if fatigue >= 50:
        return div(value * 0, 100)
    if fatigue >= 40:
        return div(value * 5, 100)
    if fatigue >= 30:
        return div(value * 25, 100)
    if fatigue >= 20:
        return div(value * 50, 100)
    if fatigue >= 10:
        return div(value * 75, 100)
    return value


def rest(ctx: Ctx) -> None:
    """`ゲーム内_行動実行処理/ACTION_REST.ERB@REST`:3–121（TARGET が対象）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.target_chara
    t = lambda n: talent(data, c, n)  # noqa: E731
    f51, f53 = st.flag[51], st.flag[53]
    c.cflag[101] = -1  # :7
    if f51 not in _REST_BASE:
        # LOCAL は関数ごとの静的変数で、呼び出しごとには初期化されない（ResetData／ロード時のみ：
        # reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs@SetDefaultLocalValue:514–520、
        # VariableEvaluator.cs:1136、2174）。範囲外だと前回値が残るため移植しない。FLAG:51 は施設レベル 1–5。
        raise NotImplementedError(f"REST：FLAG:51 = {f51}（1–5 以外）")
    l1 = _REST_BASE[f51]
    if t("回復早い") > 0:  # :20–24
        l1 += 5
    elif t("回復遅い") > 0:
        l1 -= 5
    if t("魔力貯蔵") > 0:  # :26–32
        l1 -= 5
        if f51 >= 4:
            l1 -= 5
        if f51 >= 5:
            l1 -= 5
    if t("不老長寿") > 0:  # :33–41
        l1 -= 5
        if f51 >= 3:
            l1 -= 5
        if f51 >= 4:
            l1 -= 5
        if f51 >= 5:
            l1 -= 5
    if t("溢れる生命力") > 0:  # :42–43
        l1 += 10
    l1 = _fatigue_scale(l1, c.cflag[99])  # :46–56
    # :59–65
    local = div(c.maxbase[0] * l1, 100) + 200
    c.base[0] = limit(local + c.base[0], 0, c.maxbase[0])
    local = div(c.maxbase[1] * l1, 100) + 200
    c.base[1] = limit(local + c.base[1], 0, c.maxbase[1])
    c.base[2] = c.maxbase[2]
    if c.cflag[0] == -1:  # :67
        return
    if c.cflag[999] != 0:  # :68–74
        out.printl(f"{c.callname}は休憩しています…")
        if t("四肢欠損") == 0 and t("繁殖袋") == 0:
            kojo_root(ctx, "REST")
    if c.cflag[99] > 0:  # :77–108 疲労の回復
        c.cflag[99] -= 2
        if f53 & SHOWER:
            c.cflag[99] -= st.rng.rand(2)
        if f53 & DAIYOKUJOU:
            c.cflag[99] -= st.rng.rand(2) + 1
        if f53 & BIYOU_ONSEN:
            c.cflag[99] -= 1
        if f53 & BEAUTY_SALON:
            c.cflag[99] -= 2
        if st.time == 1 or t("夜魔の貴族") > 0:
            c.cflag[99] -= 4
            if f53 & JOUSHITSU_BED:
                c.cflag[99] -= 2
            if f53 & SAIKOUKYUU_BED:
                c.cflag[99] -= 2
        else:
            c.cflag[99] -= 2
            if f53 & GAME_CORNER:
                c.cflag[99] -= 2
        if c.cflag[99] < 0:
            c.cflag[99] = 0
        if c.cflag[999] != 0:
            if c.cflag[99] == 0:
                out.printl(f"{c.callname}の身体から疲労が完全に抜けた！")
            else:
                out.printl(f"{c.callname}の身体から疲労が少し抜けた…")
    if c.cflag[999] != 0:  # :110–120
        out.printl()
        if c.base[0] == c.maxbase[0] and c.base[1] == c.maxbase[1] and c.cflag[99] == 0:
            out.printl(f"{c.callname}は最大まで回復した！")
        _wait_or_line(ctx)


# --- @TRAINING ---------------------------------------------------------------------

# (体力を減らしてから上げる BASEUP の種類, 元値 LOCAL:0 か LOCAL:1 か, 地の文)  ACTION_TRAINING.ERB:76–166、:233–251
_SIMPLE_TRAININGS = {
    0: ("TAIRYOKU", 0, "走りこみ", "HASHIRI"),
    1: ("KIRYOKU", 0, "精神鍛錬", "SEISHIN"),
    2: ("SEITAISEI", 1, "瞑想", "MEISOU"),
    3: ("KOUGEKI", 1, "筋トレ", "KINTORE"),
    4: ("BOUGYO", 1, "自衛訓練", "JIEI"),
    5: ("BINSYOU", 1, "ダッシュ", "DASH"),
    9: ("CHISEI", 1, "戦術研究訓練", "TACTICS"),
}
# 戦技訓練（:167–232）：(BASEUP 1, BASEUP 2, EXP 番号, 表示名, SENGIUP 種別)
_SKILL_TRAININGS = {
    6: ("KOUGEKI", "BINSYOU", 5, "近距離", 0, "SHORT"),
    7: ("KOUGEKI", "BOUGYO", 6, "中距離", 1, "MIDDLE"),
    8: ("BOUGYO", "BINSYOU", 7, "遠距離", 2, "LONG"),
}


def training(ctx: Ctx) -> Generator[None, int, None]:
    """`ゲーム内_行動実行処理/ACTION_TRAINING.ERB@TRAINING`:3–300（TARGET が対象）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    who = st.target
    c = st.target_chara
    f50 = st.flag[50]
    henshin = talent(data, c, "変身能力")
    # :13–30
    l0 = 45 + div(f50 * 25, 100)
    l1 = 3 + div(f50, 2)
    if not game_option(st, GameOption.HARDCORE):
        l1 += 2
    l2 = 7 + div(f50, 2)
    l3 = 2 + st.rng.rand(5 + f50 * 2)
    l0 = training_hosei_child(data, c, l0)
    l1 = training_hosei_child(data, c, l1)
    l2 = training_hosei_child(data, c, l2)
    l4 = training_downtairyoku(data, st, who)  # :33
    out.printl()
    # :37 MESSAGE_TRAINING_BEGIN（地の文/MESSAGE.ERB:22–27）：口上 RESULT == 1 のときだけ PRINTW
    if kojo_root(ctx, "TRAINING_BEGIN") == 1 and config_check_screen(st, 3) == 0:
        out.printw()
    out.printl("どの鍛錬を行いますか？")
    out.printl(f"現在の設備レベル：Lv.{f50}　消費体力：{l4}")
    # :42–64
    out.drawline()
    show_status_base_training(ctx, who)
    for label in ("[0] 走りこみ", "[1] 精神鍛錬", "[2] 瞑想"):
        out.print_lc(label)
    out.printl()
    for label in ("[3] 筋トレ", "[4] 自衛訓練", "[5] ダッシュ"):
        out.print_lc(label)
    out.printl()
    if henshin != -1:
        for label in ("[6] 近距離戦闘訓練", "[7] 中距離戦闘訓練", "[8] 遠距離戦闘訓練"):
            out.print_lc(label)
        out.printl()
    out.print_lc("[9] 戦術研究")
    if henshin == -1:
        out.print_lc("[10]戦闘基礎訓練")
    out.printl()
    out.drawline()
    # :66–71
    if c.cflag[110] > 0:
        raise NotImplementedError("鍛錬スケジュール（RES_SCHEDULE, CFLAG:110）は未移植")
    while True:
        result = yield  # INPUT
        out.printl()  # :72
        c.cflag[101] = result  # :74
        if result in _SIMPLE_TRAININGS:
            kind, src, label, code = _SIMPLE_TRAININGS[result]
            _message_training(ctx, label, code)
            c.base[0] = limit(c.base[0] - l4, 0, c.maxbase[0])
            l100 = l0 if src == 0 else l1
            if result == 9 and henshin == -1:  # :241–242 非戦闘員は知性ボーナス
                l100 = times(l100, "1.5")
            if c.cflag[42] == 400:
                l100 = times(l100, "0.8")
                _message_tentaclecloth(ctx)
            baseup(ctx, kind, who, l100)
            break
        if result in _SKILL_TRAININGS and henshin != -1:
            k1, k2, exp_no, dist, sengi, code = _SKILL_TRAININGS[result]
            _message_training(ctx, f"{dist}戦闘訓練", code)
            l1 = times(l1, "0.30")
            c.base[0] = limit(c.base[0] - l4, 0, c.maxbase[0])
            if c.cflag[42] == 400:
                l1 = times(l1, "0.8")
                _message_tentaclecloth(ctx)
            baseup(ctx, k1, who, l1)
            baseup(ctx, k2, who, l1)
            c.exp[exp_no] += l2
            out.printl(f"{dist}戦闘が{'少し' if l2 <= 3 + f50 else ''}上達した（＋{l2}）")
            sengiup(ctx, who, sengi)
            break
        if result == 10 and henshin == -1:  # :252–272
            _message_training(ctx, "戦闘基礎訓練", "BASIS")
            l1 = times(l1, "0.30")
            c.base[0] = limit(c.base[0] - l4, 0, c.maxbase[0])
            if c.cflag[42] == 400:
                l1 = times(l1, "0.8")
                _message_tentaclecloth(ctx)
            baseup(ctx, "CHISEI", who, l1)
            l2 = div(l2 * (150 + c.abl[data.index_of("ABL", "戦闘基礎")] * 50), 100) + st.rng.rand(3)
            c.exp[8] += l2
            out.printl(f"戦闘の基礎が{'少し' if l2 <= 30 + f50 * 2 else ''}上達した（＋{l2}）")
            sengiup(ctx, who, 3)
            break
        # :273–280
        if c.cflag[111] > 0:
            rest(ctx)
            return  # GOTO END_TRAINING → BEGIN TURNEND
        out.printl("正しい値を入力してください")
    # :283–297
    get_exp(ctx, 10 + st.rng.rand(5))
    get_syuren(ctx, l3)
    baseup_cal_shield(data, st, who)
    get_state_trophy(ctx, who)
    out.printl()
    if kojo_root(ctx, "TRAINING_END") == 1 and config_check_screen(st, 3) == 0:  # MESSAGE.ERB:30–35
        out.printw()
    out.printw()


def _message_training(ctx: Ctx, label: str, code: str) -> None:
    """`地の文/MESSAGE.ERB@MESSAGE_TRAINING_*`:38–179（11 個とも PRINTL／PRINTFORML／口上／PRINTW の同形）。"""
    ctx.out.printl()
    ctx.out.printl(f"{print_callname(ctx.state, ctx.state.target, 1)}は{label}を開始した")
    kojo_root(ctx, "TRAINING_" + code)
    _wait_or_line(ctx)


def _message_tentaclecloth(ctx: Ctx) -> None:
    """`地の文/MESSAGE.ERB@MESSAGE_TRAINING_TENTACLECLOTH`:181–190。"""
    item = ctx.data.names["ITEM"].get(ctx.state.target_chara.cflag[42], "")
    ctx.out.printl(f"しかし、服の下で蠢く{item}が気になって集中することができない・・・")
    kojo_root(ctx, "TRAINING_TENTACLECLOTH")
    _wait_or_line(ctx)


def training_hosei_child(data: GameData, c: Character, value: int) -> int:
    """`ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@TRAINING_HOSEI_CHILD`:32–47（MARK:血族補正 は TARGET）。"""
    l4 = c.mark[data.index_of("MARK", "血族補正")]
    if l4 <= 0:
        return value
    l4 = min(l4, 12)
    l2, l3 = 3 + l4, 2 + l4
    l1 = value
    for _ in range(l4):
        l1 = l1 * l2
    for _ in range(l4):
        l1 = div(l1, l3)
    return l1


def show_status_base_training(ctx: Ctx, who: int) -> None:
    """`ヒロイン関連/CHARA_STATUS.ERB@SHOW_STATUS_BASE_TRAINING`:210–245。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[who]
    tc = st.target_chara
    out.printl()
    out.printl(f"{c.callname} Lv.{c.abl[data.index_of('ABL', 'レベル')]} （{c.juel[50]}％）")
    for name, idx in (("体力", 0), ("気力", 1), ("性耐性", 2)):
        _bar(out, name, c.base[idx], c.maxbase[idx])  # DEVIATION（表示のみ）：COLORSENTENCE_BAR は近似
        out.printl()
    m = c.maxbase
    out.printl(f"戦闘力　　攻撃：{m[10]}  防御：{m[11]}  敏捷：{m[12]}  知性：{m[13]}")
    out.print("性格    　")
    s = seikaku_check(data, c)  # SEIKAKU_CHECK "PRINT"（CHARA_SEIKAKU.ERB:5–35）
    out.print(data.names["TALENT"].get(s, "") if s else "ランダム")
    out.printl()
    out.printl(f"修練P　 　{tc.juel[20]}P")  # JUEL:修練P は TARGET
    # DEVIATION（表示のみ）：SHOW_STATUS_TALENT（CHARA_STATUS.ERB:251–953、素質一覧）は未移植
    _shortline(out)
    out.print_lc(f"体力基礎：{c.base[50]}")
    out.print_lc(f"気力基礎：{c.base[51]}")
    out.print_lc(f"性耐性基礎：{c.base[52]}")
    out.printl()
    out.print_lc(f"攻撃基礎：{c.base[10]}")
    out.print_lc(f"防御基礎：{c.base[11]}")
    out.print_lc(f"敏捷基礎：{c.base[12]}")
    out.printl()
    out.print_lc(f"知性基礎：{c.base[13]}")
    out.printl()
    a = c.abl
    if talent(data, tc, "変身能力") != -1:  # TALENT:変身能力（TARGET）
        out.print_lc(f"近距離戦技：LV.{a[30]}")
        out.print_lc(f"中距離戦技：LV.{a[31]}")
        out.print_lc(f"遠距離戦技：LV.{a[32]}")
    else:
        out.print_lc(f"基本戦闘技能：LV.{a[33]}")
    out.printl()
    _shortline(out)


def _shortline(out: TextOutput) -> None:
    """`汎用関数/PRINT_LINE.ERB@SHORTLINE`:3–7。"""
    out.print("――――――――――――――――――――――――――――")
    out.printl()


# --- 汎用関数/コモン関数.ERB ---------------------------------------------------------

# BASEUP の種類 → (BASE 番号, SEIKAKU_HOSEI_F の ARG:1, 表示する BASENAME 番号)  コモン関数.ERB:498–548、:590–636
_BASEUP_KINDS = {
    "TAIRYOKU": (50, 0, 0),
    "KIRYOKU": (51, 1, 1),
    "SEITAISEI": (52, 2, 2),
    "KOUGEKI": (10, 10, 10),
    "BOUGYO": (11, 11, 11),
    "BINSYOU": (12, 12, 12),
    "CHISEI": (13, 13, 13),
}

# `ヒロイン関連/CHARA_SEIKAKU.ERB@SEIKAKU_HOSEI_F`:63–465：性格 → {ARG:1: TIMES 係数}。記載のない組は無補正。
SEIKAKU_HOSEI: dict[int, dict[int, str]] = {
    10: {1: "0.90", 12: "1.10", 13: "1.20"},
    11: {2: "0.90", 11: "1.10", 12: "1.20"},
    12: {10: "1.20", 11: "0.80"},
    13: {0: "1.20", 13: "0.80"},
    14: {11: "1.20", 12: "0.80", 13: "1.20"},
    15: {0: "0.90", 1: "0.90", 10: "1.10", 11: "1.10", 12: "1.10", 13: "0.90"},
    16: {1: "1.20", 2: "0.80", 13: "1.10"},
    17: {2: "1.20", 10: "0.90"},
    18: {1: "0.90", 11: "1.10", 13: "1.10"},
    19: {0: "1.10", 1: "1.10", 2: "1.10"},
    20: {1: "1.10", 2: "0.90"},
    22: {1: "1.10", 2: "1.10", 10: "1.10", 11: "0.90", 13: "1.10"},
    23: {0: "1.10", 12: "1.10"},
    24: {2: "0.80", 10: "1.10", 11: "1.10"},
    25: {0: "0.80", 1: "0.90", 2: "1.10", 10: "1.10", 12: "1.10"},
    26: {1: "1.10", 2: "1.20", 12: "0.90"},
    27: {0: "1.10", 10: "1.30", 12: "0.90", 13: "0.80"},
    28: {0: "0.95", 1: "0.95", 11: "0.95", 12: "0.95", 13: "1.20"},
}


def seikaku_hosei(seikaku: int, which: int, value: int) -> int:
    """`@SEIKAKU_HOSEI_F(性格, どのベース, 元値)`。"""
    factor = SEIKAKU_HOSEI.get(seikaku, {}).get(which)
    return times(value, factor) if factor else value


def baseup_cal_randam(ctx: Ctx, value: int) -> int:
    """`@BASEUP_CAL_RANDAM`（コモン関数.ERB:556–587）。回復早い／遅いは TARGET の素質。"""
    st = ctx.state
    f50 = st.flag[50]
    local = st.rng.rand(100) + f50 * 5
    if local < f50 * 10:
        local = f50 * 10
    for bound, pct in ((20, 70), (30, 75), (40, 80), (50, 85), (60, 90), (70, 95), (80, 100), (95, 105)):
        if local < bound:
            l1 = pct
            break
    else:
        l1 = 110
    tc = st.target_chara
    if talent(ctx.data, tc, "回復早い") > 0:
        l1 -= 5
    if talent(ctx.data, tc, "回復遅い") > 0:
        l1 += 5
    return div(value * l1, 100)


def baseup(ctx: Ctx, kind: str, who: int, value: int) -> None:
    """`@BASEUP, ARGS, ARG:0, ARG:1`（コモン関数.ERB:465–553）。"ALL" は未使用なので未移植。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[who]
    seikaku = seikaku_check(data, c)
    if seikaku == 0:
        return
    base_no, which, name_no = _BASEUP_KINDS[kind]
    v = baseup_cal_randam(ctx, value)
    r = seikaku_hosei(seikaku, which, v)
    c.base[base_no] += r
    if r > 0:
        out.printl(f"{data.names['BASE'].get(name_no, '')}の基礎値が{r}上がった")
    level_status(data, st, who)
    baseup_cal_shield(data, st, who)


def get_exp(ctx: Ctx, value: int) -> None:
    """`@GET_EXP`（コモン関数.ERB:404–415）。TARGET が対象。"""
    st, data = ctx.state, ctx.data
    c = st.target_chara
    if talent(data, c, "内向的") > 0:
        value = times(value, "1.10")
    if talent(data, c, "自分勝手") > 0:
        value = times(value, "1.10")
    c.juel[50] += value
    ctx.out.printl(f"{print_transcallname(st, st.target)}は経験値を{value}％得た")
    check_levelup(ctx)


def check_levelup(ctx: Ctx) -> None:
    """`@CHECK_LEVELUP`（コモン関数.ERB:921–936）。"""
    st, data = ctx.state, ctx.data
    c = st.target_chara
    lv = data.index_of("ABL", "レベル")
    local = 0
    while c.juel[50] > 100 and c.abl[lv] < 998:
        c.juel[50] -= 100
        local += 1
    if local > 0:
        c.abl[lv] += local
        ctx.out.printl(f"{print_transcallname(st, st.target)}はレベルが{local}上がった")
        level_status(data, st, st.target)
        get_state_trophy(ctx, st.target)
    if c.abl[lv] >= 999:
        c.juel[50] = 0


def get_syuren(ctx: Ctx, value: int) -> None:
    """`@GET_SYUREN`（コモン関数.ERB:418–421）。"""
    ctx.state.target_chara.juel[20] += value
    ctx.out.printl(f"{ctx.data.names['PALAM'].get(20, '')}を{value}P手に入れた")


_SENGI_NEED = {0: 25, 1: 60, 2: 105, 3: 160, 4: 225, 5: 300, 6: 470, 7: 660, 8: 870}


def sengiup(ctx: Ctx, who: int, kind: int) -> None:
    """`@SENGIUP, ARG:0, ARG:1`（コモン関数.ERB:675–799）。"""
    st, data = ctx.state, ctx.data
    c = st.charas[who]
    abl_no, exp_no = {0: (30, 5), 1: (31, 6), 2: (32, 7), 3: (33, 8)}[kind]
    need = _SENGI_NEED.get(c.abl[abl_no])
    if need is None:
        # ABL が 9 以上だと LOCAL:2 は前回値のまま（静的 LOCAL）だが、:732 の `ABL < 9` で必ず不成立
        return
    t = lambda n: talent(data, c, n)  # noqa: E731
    near, mid, far = t("近距離得意") == 1, t("中距離得意") == 1, t("遠距離得意") == 1
    near_n, mid_n, far_n = t("近距離苦手") == 1, t("中距離苦手") == 1, t("遠距離苦手") == 1
    # :714–717 `A && k0 || B && k1 || C && k2`：&& と || は同順位・左結合
    # （reference/emuera-1824/Emuera/GameData/Expression/OperatorCode.cs:33–34、ExpressionParser.cs:502–506）
    # なので ((((A && k0) || B) && k1) || C) && k2 と評価される（原作どおり）
    if (((near and kind == 0) or mid) and kind == 1 or far) and kind == 2:
        need = times(need, "0.9")
    if (((near_n and kind == 0) or mid_n) and kind == 1 or far_n) and kind == 2:
        need = times(need, "1.1")
    if near and kind != 0:
        need = times(need, "1.05")
    if mid and kind != 1:
        need = times(need, "1.05")
    if far and kind != 2:
        need = times(need, "1.05")
    if near_n and kind != 0:
        need = times(need, "0.95")
    if mid_n and kind != 1:
        need = times(need, "0.95")
    if far_n and kind != 2:
        need = times(need, "0.95")
    if c.exp[exp_no] >= need and c.abl[abl_no] < 9:  # :732
        c.abl[abl_no] += 1
        ctx.out.printl(f"{print_transcallname(st, who)}の{data.names['ABL'].get(abl_no, '')}Lvが上がった")
        if t("変身能力") == -1 and c.abl[abl_no] >= 5 and abl_no == 33:
            raise NotImplementedError("戦闘基礎 Lv5 による変身能力の獲得（SENGIUP:737–790）は未移植")
        ctx.out.printl()
        get_state_trophy(ctx, who)


def get_state_trophy(ctx: Ctx, who: int) -> None:
    """`インターミッション画面/SHOP_TROPHY.ERB@GET_STATE_TROPHY`:398–441。

    DEVIATION: 実績は GLOBAL（UNLOCK_ACHIEVEMENT:6–20、GLOBAL:num と SAVEGLOBAL）にのみ記録され、本作の
    GLOBAL は読み書きしない（deviations.md「全域資料」）。そのため達成判定と「【実績：…】を達成しました！」の
    表示を行わない（SAVEDATA への影響はない）。
    """
