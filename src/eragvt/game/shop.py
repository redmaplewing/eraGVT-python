"""インターミッション（SHOP）画面：`@EVENTSHOP`（初日分岐）、`@SHOW_SHOP`、`@USERSHOP` の翻寫。

路徑相對 `source/earGVP/ERB/`。互動（INPUT）的流程控制在 `eragvt.game.session`。
"""

from __future__ import annotations

from datetime import datetime

from ..data.csv_loader import GameData
from ..state import GameState
from ..state.constants import FORCE_REST_HP, MODE_OPTIONS, PARTY_MAX, ActionPlan, CharaState, GameMode, GameOption
from ..text import NarrationService, TextOutput
from .chara_common import is_female, talent
from .era import div, format_curly, format_percent, limit, times
from .opening import game_option
from .tentacle import enemy_type_check, get_lastboss_phase, tentacle_survive_check, tentacle_survive_num

# COLOR.ERH:5–22
COLOR_DISABLED = "#696969"
ACTION_COLORS = {
    ActionPlan.SORTIE: "#ffaaaa",
    ActionPlan.TRAINING: "#ffffaa",
    ActionPlan.REST: "#aaaaff",
    ActionPlan.ACTIVITY: "#aaffff",
    ActionPlan.DEFENSE: "#ffaaff",
    ActionPlan.SUPPORT: "#aaffaa",
    ActionPlan.INFORMATION: "#ffc832",
    ActionPlan.FREE: "#32c3ff",
}
TIME_COLORS = ("#e6d200", "#0082fa")  # 文字色時間帯（:16–18）
BG_COLORS = ("#0a0a00", "#000005")  # 背景色時間帯（:20–22）
COLOR_ORANGE = "#ff8000"

# CSV定数定義/CFLAG.ERH:40–74
ACTION_ORDER = (0, 101, 102, 103, 104, 105, 106, 107, 108)
ACTION_NAMES = ("", "出撃", "鍛錬", "休憩", "特別活動", "拠点防衛", "戦闘支援", "情報収集", "自由行動")
ACTION_SHORT = ("", "出撃", "鍛錬", "休憩", "活動", "防衛", "支援", "情報", "自由")
# SHOP.ERB:678–689 ACTION_STR
ACTION_STR = ("", "出撃することにしました", "鍛錬をすることにしました", "休憩することにしました", "資金を稼ぐことにしました",
              "拠点を防衛することにしました", "後方で戦闘支援に徹します", "後方で情報収集に徹します", "自由に行動することにしました")

# SHOP_SHOW_BOSS_INFO で使う @TENTACLE_BOSS_{n}_GETNAME（触手データ/ボス触手/TENTACLE_BOSS_{n}_*.ERB:7–8）
BOSS_NAMES = {1: "Ｃ触手", 2: "Ｖ触手", 3: "Ａ触手", 4: "Ｂ触手", 5: "Ｓ触手", 6: "Ｐ触手", 7: "Ｈ触手"}


def _find_action(action: int) -> int:
    """`FINDELEMENT(キャラ行動予定, ACTION)`：見つからなければ -1。"""
    return ACTION_ORDER.index(action) if action in ACTION_ORDER else -1


# --- 判定関数 ----------------------------------------------------------------


def check_gameover(state: GameState) -> bool:
    """`@CHECK_GAMEOVER_F`（オープニング処理_カスタムGAMEMODE.ERB:116–118）。"""
    return game_mode_check(state) == GameMode.GAMEOVER


def game_mode_check(state: GameState) -> int:
    """`@GAME_MODE_CHECK_F`（同:131–137）：FLAG:0 と一致するモード、無ければ -1。"""
    for mode, opts in MODE_OPTIONS.items():
        if state.flag[0] == opts:
            return int(mode)
    return -1


def game_mode_check_proc(state: GameState) -> int:
    """`@GAME_MODE_CHECK`（同:124–130、RESULT を返す CALL 版）：周回要素で時間制限を解除していれば（FLAG:906 ≠ 0）
    各モードのオプションに 64（OPTION_制限時間無し = bit 6）を足して比べる。@SAVEINFO（オープニング処理.ERB:586）が使う。"""
    extra = 64 if state.flag[906] else 0
    for mode, opts in MODE_OPTIONS.items():
        if state.flag[0] == (opts | extra):
            return int(mode)
    return -1


def change_gameover_mode(state: GameState) -> None:
    """`@CHANGE_GAMEOVER_MODE`（同:112–114）：FLAG:0 = 0（全オプション OFF = MODE_GAMEOVER、DIM.ERH:40／:83–92）、
    DAY:2 = DAY*2+TIME（全滅時点の半日数。SHOP_FLASHNEWS.ERB:93 がゲームオーバー後の経過ターン数に使う）。
    RETURN は無いが次の `@CHECK_GAMEOVER_F` ラベルで関数終端（reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67）。"""
    state.flag[0] = 0
    state.day[2] = state.day[0] * 2 + state.time


def charanum_safe(state: GameState) -> int:
    """`汎用関数/CHARANUM.ERB@CHARANUM_SAFE`:9–16。"""
    return (state.charanum - 1) - sum(1 for c in state.charas[1:] if c.cflag[0] not in (0, 10, 11))


def charanum_playable(state: GameState) -> int:
    """`@CHARANUM_PLAYABLE`（CHARANUM.ERB:19–26）。"""
    return (state.charanum - 1) - sum(1 for c in state.charas[1:] if c.cflag[0] != 0)


def charanum_partycheck(state: GameState) -> int:
    """`@CHARANUM_PARTYCHECK`（CHARANUM.ERB:135–142）。"""
    return (state.charanum - 1) - sum(1 for c in state.charas[1:] if c.cflag[999] == 0)


def charanum_reserve(state: GameState) -> int:
    """`@CHARANUM_RESERVE`（CHARANUM.ERB:146–153）。"""
    return (state.charanum - 1) - sum(1 for c in state.charas[1:] if c.cflag[999] == 1)


def charanum_safe_partycheck(state: GameState) -> int:
    """`@CHARANUM_SAFE_PARTYCHECK`（CHARANUM.ERB:114–121）。"""
    return (state.charanum - 1) - sum(
        1 for c in state.charas[1:] if c.cflag[0] in (1, 2, 3, 4, 9) or c.cflag[999] == 0
    )


def charanum_active(state: GameState) -> int:
    """`@CHARANUM_ACTIVE`（CHARANUM.ERB:124–131）。"""
    return (state.charanum - 1) - sum(1 for c in state.charas[1:] if c.cflag[0] != 0 or c.cflag[999] == 0)


def syouhi_keigen(data: GameData, state: GameState, who: int, amount: int, base: int) -> int:
    """`汎用関数/コモン関数.ERB@SYOUHI_KEIGEN`:947–960。"""
    local = amount
    base += 50
    threshold = 1000 if base in (50, 51) else 100
    b = state.charas[who].base[base]
    if b > threshold:
        over = b - threshold
        local = max(local - div(local * over, 2500), div(local, 2))
    return local


def training_downtairyoku(data: GameData, state: GameState, who: int) -> int:
    """`ゲーム内_行動実行処理/ACTION_TRAINING.ERB@TRAINING_DOWNTAIRYOKU`:325–340。
    原作は SYOUHI_KEIGEN に ARG ではなく TARGET を渡している（そのまま移植）。"""
    local = times(state.charas[who].maxbase[0], "0.10")
    f50 = state.flag[50]
    if f50 == 1:
        local = times(local, "2.00")
    elif f50 == 2:
        local = times(local, "1.80")
    elif f50 == 3:
        local = times(local, "1.50")
    elif f50 == 4:
        local = times(local, "1.25")
    elif f50 >= 5:
        local = times(local, "1.00")
    return syouhi_keigen(data, state, state.target, local, 0)


def check_pregnant(data: GameData, state: GameState, who: int) -> bool:
    """`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@CHECK_PREGNANT_F`:813–819。"""
    c = state.charas[who]
    p = talent(data, c, "妊娠")
    return p in (1, 3) or (p == 5 and c.cflag[222] >= 11)


# IS_ACTION_INCAPABLE.ERH
CONSTRAINT_ALL, C_HP, C_YAMA, C_SENSHI, C_SUPPORT, C_PREGNANT, C_LIMB, C_BROKEN = -1, 0, 1, 2, 3, 4, 5, 6
_HP_ACTIONS = (101, 102, 104, 105, 106, 107)
_PREGNANT_ACTIONS = (101, 105)
_YAMA_ACTIONS = (101, 104, 105, 107, 108)
_LIMB_ACTIONS = (101, 102, 104, 105, 107, 108)
_SENSHI_ACTIONS = (104, 106)


def is_action_incapable(data: GameData, state: GameState, action: int, who: int, constraint: int = CONSTRAINT_ALL) -> int:
    """`ゲーム内_行動実行処理/IS_ACTION_INCAPABLE.ERB@IS_ACTION_INCAPABLE`:21–48。"""
    c = state.charas[who]
    t = lambda n: talent(data, c, n)  # noqa: E731
    on = lambda k: constraint in (CONSTRAINT_ALL, k)  # noqa: E731
    r = 0
    if on(C_HP) and action in _HP_ACTIONS and c.base[0] <= FORCE_REST_HP:
        r = 1
    if on(C_HP) and action == ActionPlan.TRAINING and c.base[0] < training_downtairyoku(data, state, who):
        r = 1
    if on(C_YAMA) and action in _YAMA_ACTIONS and (t("夜魔の貴族") and state.time == 0):
        r = 1
    if on(C_LIMB) and action in _LIMB_ACTIONS and t("四肢欠損") > 0:
        r = 1
    if on(C_BROKEN) and action != ActionPlan.REST and t("繁殖袋") > 0:
        r = 1
    if on(C_SENSHI) and action in _SENSHI_ACTIONS and t("生粋の戦士"):
        r = 1
    if on(C_SUPPORT) and action == ActionPlan.SUPPORT and "支援無効" in state.temp.battle_situation:
        r = 1
    if on(C_PREGNANT) and action in _PREGNANT_ACTIONS and check_pregnant(data, state, who):
        r = 1
    return r


def number_on_frontline(data: GameData, state: GameState) -> int:
    """`SHOP.ERB@NUMBER_ON_FRONTLINE`:489–499。"""
    n = 0
    for i in range(1, state.charanum):
        a = state.charas[i].cflag[100]
        if a in (101, 105) and not is_action_incapable(data, state, a, i):
            n += 1
    return n


# --- @EVENTSHOP --------------------------------------------------------------


def lb(out: TextOutput) -> None:
    """`汎用関数/PRINT_LINE.ERB@LB`:12–18：50 行の改行で画面を流す。"""
    for _ in range(50):
        out.printl()


def event_shop(state: GameState, data: GameData, out: TextOutput, narration: NarrationService) -> None:
    """`event_shop_gen` を入力なしで最後まで実行する（INPUT を要求されたら RuntimeError：その経路は session が駆動する）。"""
    for _ in event_shop_gen(state, data, out, narration):
        raise RuntimeError("@EVENTSHOP が INPUT を要求した（GameSession.begin_shop で駆動すること）")


def event_shop_gen(state: GameState, data: GameData, out: TextOutput, narration: NarrationService):
    """`インターミッション画面/SHOP_TURNEND.ERB@EVENTSHOP`:141–。通常ターン（DAY != 0）は `turnend.event_shop_normal`
    （S17：寄生触手のイベントが INPUT を使うのでジェネレータ）。"""
    if state.day[0] != 0:
        from .action import Ctx
        from .turnend import event_shop_normal

        yield from event_shop_normal(Ctx(state, data, out, narration))
        return
    state.day[0] = 1
    state.time = 0
    state.flag[64] = 0
    state.flag[799] = 0
    state.target = 1
    lb(out)
    yield from show_shop_gen(state, data, out, narration)  # JUMP SHOW_SHOP（:155）


# --- @SHOW_SHOP --------------------------------------------------------------


def show_shop(state: GameState, data: GameData, out: TextOutput, narration: NarrationService) -> None:
    """無輸入呼叫端的相容入口；互動路徑由 GameSession 驅動。"""
    gen = show_shop_gen(state, data, out, narration)
    try:
        for _ in gen:
            raise RuntimeError("@SHOW_SHOP 要求 INPUT，請由 GameSession 驅動")
    finally:
        gen.close()


def show_shop_gen(state: GameState, data: GameData, out: TextOutput, narration: NarrationService):
    """`インターミッション画面/SHOP.ERB@SHOW_SHOP`:5–189。"""
    cf = lambda i, k: state.charas[i].cflag[k]  # noqa: E731
    ok_states = (CharaState.SAFE, CharaState.BEFORE_BIRTH, CharaState.CHILDCARE)
    # :9–16 選択中のキャラが編成外なら自動変更
    # 原作は TARGET == CHARANUM のとき CFLAG:TARGET 参照でエラーになる。ここでは「編成外」扱いにする。
    if state.target > state.charanum or (
        state.flag[63] == 0
        and (state.target >= state.charanum or cf(state.target, 999) == 0 or cf(state.target, 0) not in ok_states)
    ):
        for i in range(1, state.charanum):
            if cf(i, 999) == 1 and cf(i, 0) in ok_states:
                state.target = i
                break
    state.flag[799] = 0  # :20
    lb(out)  # :23
    # :26–35 背景色：Web 側が state.time / FLAG:999 から決める
    out.drawline()
    flashnews(state, data, out)  # :40
    out.drawline()
    shop_show_boss_info(state, data, out)
    out.drawline()
    shop_show_status_target(state, data, out)
    # :51–58 パーティ一覧
    if not game_option(state, GameOption.SOLO) and charanum_playable(state) >= 2:
        out.printl()
        out.printl(f"パーティ人数( {charanum_partycheck(state)} / {PARTY_MAX} )")
        shop_show_status_party_list(state, data, out)
        if state.flag[61] and charanum_reserve(state):
            out.printl("（未實作：控えメンバー一覧 SHOP_SHOW_STATUS_RESERVE_LIST）")
    # :61–72 一括設定
    if charanum_safe(state) >= 2:
        if state.flag[9] == 1:
            out.set_bold()
            out.set_color((255, 150, 0))
        else:
            out.set_color((120, 60, 0))
        out.print("[90]一括設定")
        out.reset_color()
        out.set_bold(False)
    else:
        out.print("　　　　　　")
    out.print_plain("                         ")
    # :79–87 パーティ編成ボタン
    if state.charanum > 2 and charanum_safe(state) > 0:
        out.print("　　　　　　　　　　　")
        out.print("[50] パーティ編成　")
        out.print_plain(" ")
    else:
        out.print_plain("               ")
    if charanum_safe_partycheck(state) and state.flag[61]:
        out.print("    [60] ▲操作キャラのみ")
    elif charanum_reserve(state):
        out.print("        [60] ▼全表示")
    out.printl()
    shop_ng_action_info(state, data, out)  # :99
    if not game_option(state, GameOption.SOLO):
        out.drawline()
    # :105–111 一括選択中なら一口メッセージ用にランダムなキャラを選ぶ
    if state.flag[9] and charanum_safe_partycheck(state) > 0:
        while True:
            state.target = state.rng.rand(state.charanum - 1) + 1
            if not (cf(state.target, 999) == 0 or cf(state.target, 0) not in ok_states):
                break
    # :113–122 一口メッセージ口上
    if cf(state.target, 0) == CharaState.SAFE and state.target != GameState.MASTER:
        # MESSAGE_HITOKUTI_SHOP（地の文/MESSAGE.ERB:13–16）→ TRYCALLFORM KOJO_ROOT(CFLAG:6, "HITOKUTI_SHOP")、
        # RETURN RESULT（口上が無ければ -1 → LIMIT(4-(-1),0,4) = 4 行）
        from .action import Ctx, kojo_root_gen

        result = yield from kojo_root_gen(Ctx(state, data, out, narration), "HITOKUTI_SHOP")
        for _ in range(limit(4 - result, 0, 4)):
            out.printl()
    else:
        for _ in range(4):
            out.printl()
    shop_intermission_header(state, data, out)  # :125
    # :128–151 メニュー
    out.set_color(TIME_COLORS[state.time])
    out.print("[100]★行動開始★")
    out.printl()
    out.printl()
    out.reset_color()
    gameover = check_gameover(state)
    if not gameover:
        _cprint(out, "[101]出撃する　　　 ", ACTION_COLORS[ActionPlan.SORTIE])
        _cprint(out, "[102]鍛錬する　　　 ", ACTION_COLORS[ActionPlan.TRAINING])
        _cprint(out, "[103]休憩する　　　 ", ACTION_COLORS[ActionPlan.REST])
        _cprint(out, "[104]特別活動　　　 ", ACTION_COLORS[ActionPlan.ACTIVITY])
        out.printl()
        if not game_option(state, GameOption.SOLO):
            _cprint(out, "[105]拠点防衛　　　 ", ACTION_COLORS[ActionPlan.DEFENSE])
        else:
            _cprint_plain(out, "[105]拠点防衛　　　 ", COLOR_DISABLED)
        if state.charanum >= 3:
            _cprint(out, "[106]戦闘支援　　　 ", ACTION_COLORS[ActionPlan.SUPPORT])
        else:
            _cprint_plain(out, "[106]戦闘支援　　　 ", COLOR_DISABLED)
        _cprint(out, "[107]情報収集　　　 ", ACTION_COLORS[ActionPlan.INFORMATION])
        _cprint(out, "[108]自由行動", ACTION_COLORS[ActionPlan.FREE])
        out.printl()
    out.printl()
    out.print("[110]ステータス表示 ")
    if not gameover:
        out.print("[111]キャラの強化   ")
        out.print("[112]衣装の設定　　 ")
        out.printl("[113]メディカルルーム")
        out.print("[120]衣装の購入　　 ")
    out.print("[130]状況の確認　　 ")
    if not gameover:
        out.print("[150]施設の拡張　　 ")
        if cf(state.target, 0) != CharaState.SAFE or state.target == GameState.MASTER or state.flag[9] != 0:
            _cprint_plain(out, "[160]スケジュール設定", COLOR_DISABLED)
        else:
            out.print("[160]スケジュール設定")
    out.printl()
    if game_option(state, GameOption.JOIN_RETIRE):
        out.print("　　　　　　　　　　[169]引退者名簿")
        out.print("　　　[170]引退させる　　 ")
        out.printl("[180]新人を入れる　 ")
    out.print("[200]セーブ　　　　 ")
    out.print("[300]ロード　　　　 ")
    out.print("[700]コンフィグ　　 ")
    out.print("[800]トロフィー確認 ")
    # SHOW_SHOP は改行せずに終わる。入力待ち（Emuera の setWaitInput）で行が確定する。
    out.printl()


def _cprint(out: TextOutput, text: str, color: str) -> None:
    """`汎用関数/CPRINT.ERB@CPRINT`:15–25（色を戻すのは RESETCOLOR ではなく呼び出し前の色）。"""
    out.set_color(color)
    out.print(text)
    out.reset_color()


def _cprint_plain(out: TextOutput, text: str, color: str) -> None:
    """`CPRINT.ERB@CPRINTPLAIN`:43–。"""
    out.set_color(color)
    out.print_plain(text)
    out.reset_color()


def flashnews(state: GameState, data: GameData, out: TextOutput) -> None:
    """`インターミッション画面/SHOP_FLASHNEWS.ERB@FLASHNEWS`:3–749（S26：`eragvt.game.flashnews`）。"""
    from .flashnews import flashnews as _flashnews

    _flashnews(state, data, out)


def shop_show_boss_info(state: GameState, data: GameData, out: TextOutput) -> None:
    """`インターミッション画面/SHOP_SHOW_BOSS_INFO.ERB@SHOP_SHOW_BOSS_INFO`:3–188（ボス出現中の分岐）。

    状態への影響は `SAVESTR:13 = BOSS` のみ（FLAG:11 は :46 で退避し :154 で戻す）。
    """
    f = state.flag
    found = f[47] >= f[46]
    out.set_color((255, 125, 125) if found else (255, 180, 0))
    out.printl("【探索状況】")
    out.print("　")
    if f[47] < f[46]:
        pct = 0 if f[47] == 0 or f[46] == 0 else div(f[47] * 100, f[46])  # PERCENT_CAL_F（コモン関数.ERB:224–229）
        out.print(f"探索度{pct}％ ({f[47]}/{f[46]})")
    else:
        out.print("　　ラスボス触手と交戦中！" if f[100] == 0 else "　　ボス触手の痕跡を確認！")
        rate = 40 if state.time == 0 else 50
        rate += 50 if get_lastboss_phase(state) >= 1 else f[3] * 3
        rate = div(rate * f[47], f[46])
        for c in state.charas:
            if state.flag.get_bit(803, 1) and f[18] > 0 and c.cflag[100] in (101, 105):
                rate += 4
        rate = min(rate, 95)
        out.print(f"(捕捉率 {rate}％)　")
        out.set_color((255, 255, 225))
    out.printl()
    saved11 = f[11]
    bit = 1
    lastboss = get_lastboss_phase(state) >= 1  # :53／:104（S27：ラスボス出現後は FLAG:4 体ぶん、SAVESTR:13 は触らない）
    out.print("　　　")
    if not lastboss:
        state.savestr[13] = "BOSS"
    for _ in range(f[4] if lastboss else f[3]):
        no = tentacle_survive_check(state, bit)
        if no == 0:
            out.set_color((96, 96, 96))
            if lastboss or not state.flag.get_bit(0, 4):  # :108–109 ラスボス側は GETBIT(FLAG:0,4) を見ない
                out.print("[―――]")
        else:
            f[11] = no
            if lastboss:
                from .battle.core import LASTBOSSES

                if no not in LASTBOSSES:  # 天使の樹（_GETNAME が FLAG:21 で変わる）は未移植
                    raise NotImplementedError(f"TENTACLE_LASTBOSS_{no} の表示は未移植")
                name = LASTBOSSES[no].name  # TENTACLE_ACCESS "NAME" のラスボス分岐（COMMON_TENTACLE_DATA.ERB:258–262）
            else:
                name = BOSS_NAMES.get(no, "")
            if state.flag.get_bit(803, 1) and f[18] == f[11]:
                out.set_color((255, 125, 125) if found else (255, 180, 0))
                out.print(f"[[[{name}]]]")
            elif state.flag.get_bit(803, 1):
                out.set_color((185, 85, 85) if found else (65, 65, 155))
                out.print(f"[{name}]")
            else:
                out.set_color((255, 125, 125) if found else (255, 180, 0))
                out.print(f"[{name}]")
        bit *= 2
    f[11] = saved11
    # 洗脳/悪堕ち・失踪中のキャラ（:157–186）
    darken = [c for c in state.charas[1:] if c.cflag[0] in (CharaState.BRAINWASHED, CharaState.CORRUPTED)]
    if len(darken) >= 4:
        out.printl()
        out.print("　　 ")
    for c in state.charas[1:]:
        if c.cflag[0] == CharaState.BRAINWASHED:
            out.set_color((255, 125, 185))
            out.print(f" [操:{c.callname}]")
        elif c.cflag[0] == CharaState.CORRUPTED:
            out.set_color((255, 125, 255))
            out.print(f" [堕:{c.callname}]")
    out.printl()
    missing = [c for c in state.charas[1:] if c.cflag[0] in (CharaState.IMPRISONED, CharaState.KIDNAPPED)]
    if missing:
        out.print("　　 ")
        for c in missing:
            out.set_color((155, 65, 125))
            out.print(f"【❤{c.callname}失踪中】")
        out.printl()
    out.reset_color()


def shop_print_actionplan(out: TextOutput, action: int) -> None:
    """`インターミッション画面/SHOP_PRINT_ACTIONPLAN.ERB@SHOP_PRINT_ACTIONPLAN`:5–30。"""
    i = _find_action(action)
    if action in ACTION_COLORS:
        out.set_color(ACTION_COLORS[ActionPlan(action)])
        label = ACTION_SHORT[i]
    else:
        label = "　　　"
    out.print(f"*{label}*")
    out.reset_color()


def _bar(out: TextOutput, name: str, cur: int, mx: int) -> None:
    """`CALLFORM COLORSENTENCE_BAR(名前, 6, 現在値, 最大値, 20)`（`汎用関数/コモン関数.ERB`:79–111；S25 で COLOR_BAR を移植）。"""
    from .colorbar import colorsentence_bar

    colorsentence_bar(out, name, 6, cur, mx, 20)


def shop_show_status_target(state: GameState, data: GameData, out: TextOutput) -> None:
    """`SHOP.ERB@SHOP_SHOW_STATUS_TARGET`:315–340。"""
    c = state.charas[state.target]
    if c.cflag[0] != CharaState.SAFE or (c.cflag[999] == 0 and state.flag[61] == 0):
        return
    out.print(f"◆{c.name}({'♀' if is_female(data, c) else '♂'})")
    if c.cstr[0] != "" and c.cstr[0] != c.name:
        out.print(f"《{c.cstr[0]}》")
    out.print(f" Lv.{c.abl[data.index_of('ABL', 'レベル')]}")
    # DEVIATION: SHOW_SHOP_STATUS_SIGN（生理周期・疲労等のマーク）は未移植
    out.printl()
    base_names = data.names["BASE"]
    for idx in (0, 1, 2):
        _bar(out, base_names.get(idx, ""), c.base[idx], c.maxbase[idx])
        out.printl()
    if game_option(state, GameOption.SOLO) or charanum_active(state) == 1:
        out.print("行動予定：")
        shop_print_actionplan(out, c.cflag[100])
        out.printl()
    out.printl("――――――――――――――――――――――――――――")  # SHORTLINE（PRINT_LINE.ERB:3–6）


def shop_show_status_party_list(state: GameState, data: GameData, out: TextOutput) -> None:
    """`インターミッション画面/SHOP_SHOW_STATUS_LIST.ERB@SHOP_SHOW_STATUS_PARTY_LIST`:9–39。

    DEVIATION: 各列の最大幅合わせ（SHOP_SHOW_STATUS_COUNT_MAXLEN）と 2 行目の詳細表示
    （SHOW_SHOP_STATUS_BASE_ONELINE・SIGN）は簡略化。
    """
    for i in range(1, state.charanum):
        c = state.charas[i]
        if c.cflag[999] == 0 or c.cflag[0] != CharaState.SAFE:
            continue
        if i == state.target and state.flag[9] == 0:
            out.set_color((0, 255, 150))
            out.print("◆")
            out.reset_color()
        else:
            out.print("◇")
        out.print(f"[{format_curly(i, 2)}] {c.name} 　　　")
        shop_print_actionplan(out, c.cflag[100])
        out.printl()
        out.print_plain("　　　　 ")
        out.print_plain(f"体力 {c.base[0]}/{c.maxbase[0]}　気力 {c.base[1]}/{c.maxbase[1]}　性耐性 {c.base[2]}/{c.maxbase[2]}")
        out.printl()


def shop_ng_action_info(state: GameState, data: GameData, out: TextOutput) -> None:
    """`SHOP.ERB@SHOP_NG_ACTION_INFO`:347–381。"""
    for i in range(1, state.charanum):
        c = state.charas[i]
        a = c.cflag[100]
        if c.cflag[0] == CharaState.SAFE and is_action_incapable(data, state, a, i):
            name = ACTION_NAMES[_find_action(a)] if _find_action(a) >= 0 else ""
            out.set_color("#ff0000")
            out.print(f"*{c.callname}は")
            if is_action_incapable(data, state, a, i, C_BROKEN):
                out.printl("廃人化しているため、休憩以外の行動ができません")
            if is_action_incapable(data, state, a, i, C_LIMB):
                out.printl(f"四肢欠損しているため、{name}ができません")
            if is_action_incapable(data, state, a, i, C_PREGNANT):
                out.printl(f"妊娠中なので、{name}ができません")
            if is_action_incapable(data, state, a, i, C_YAMA):
                out.printl(f"「夜魔の貴族」なため、昼間は{name}ができません")
            if is_action_incapable(data, state, a, i, C_SENSHI):
                out.printl(f"「生粋の戦士」なため、{name}ができません")
            if is_action_incapable(data, state, a, i, C_HP):
                out.printl(f"{name}に必要な体力がありません")
            # 原作は SETCOLORBYNAME RED の後 RESETCOLOR しない（色は次の SETCOLOR まで残る）
    out.reset_color()


_DAY_OF_WEEK = ("日", "月", "火", "水", "木", "金", "土")


def shop_intermission_header(state: GameState, data: GameData, out: TextOutput) -> None:
    """`SHOP.ERB@SHOP_INTERMISSON_HEADER`:391–478。"""
    f = state.flag
    day = state.day[0]
    out.set_color(TIME_COLORS[state.time])
    out.drawline()
    out.print("インターミッション")
    out.set_bold()
    out.print(f" {'[☀昼]' if state.time == 0 else '[🌙夜]'}  {day} 日目({_DAY_OF_WEEK[day % 7]})")
    out.set_bold(False)
    out.reset_color()
    if check_gameover(state):
        out.printl()
    elif game_option(state, GameOption.NO_TIME_LIMIT):
        out.printl("（完全殲滅まで∞日）")
    elif enemy_type_check(state, "BOSS") == 1:
        alive = tentacle_survive_num(state)
        left = (f[3] - alive + 1) * f[2] - day + state.day[1]
        if left <= 3:
            out.set_color("#ff0000")
        elif left <= 5:
            out.set_color("#ffa500")
        elif left <= 7:
            out.set_color("#ffff00")
        out.print(f"（{f[3] - alive + 1}体目殲滅猶予")
        out.set_bold()
        out.print(f" {left} ")
        out.set_bold(False)
        if game_option(state, GameOption.ENDLESS):
            out.printl("日/完全殲滅まで∞日）")
        else:
            out.printl(f"日/完全殲滅まで{f[1] - day + state.day[1]}日）")
    elif get_lastboss_phase(state) >= 1:
        rest = "∞" if game_option(state, GameOption.ENDLESS) else str(f[1] - day + state.day[1])
        out.printl(f"（完全殲滅まで{rest}日）")
    out.print(f"資金：{state.money}＄　")
    d = f[852]
    if d == 0:
        out.set_color((120, 0, 0))
    elif d < 1250:
        out.set_color((250, 0, 0))
    elif d < 2500:
        out.set_color((250, 250, 100))
    elif d < 10000:
        out.set_color((0, 250, 60))
    elif d < 20000:
        out.set_color((0, 200, 255))
    else:
        out.set_color((200, 0, 255))
    out.print(f"防衛力：{d}　　")
    p = f[853]
    if p <= -75:
        out.set_color((180, 0, 0))
    elif p <= -50:
        out.set_color((250, 50, 50))
    elif p < 0:
        out.set_color((250, 200, 200))
    elif p < 50:
        out.set_color((200, 250, 200))
    elif p < 75:
        out.set_color((100, 250, 150))
    else:
        out.set_color((100, 250, 200))
    out.print(f"人気度：{p}")
    out.reset_color()
    out.printl()
    out.set_color(TIME_COLORS[state.time])
    out.printl()
    out.drawline()
    out.reset_color()


# --- @USERSHOP の各処理 -------------------------------------------------------


def select_target(state: GameState, out: TextOutput, value: int) -> None:
    """USERSHOP:198–205 操作キャラの選択。"""
    if state.charanum > value and state.charas[value].cflag[999] != 0 and state.charas[value].cflag[0] == 0:
        state.flag[9] = 0
        state.target = value
        out.printl()
        out.printl(f"操作キャラを{state.charas[value].callname}に変更しました")
        out.printl()


def usershop_calls_submenu(state: GameState, value: int) -> bool:
    """USERSHOP:246–278 の [110]〜[150]：原作がその画面を呼ぶか（呼ぶ画面自体は未移植）。
    ゲームオーバーモードでは [111]〜[150] は何もしない（`SIF CHECK_GAMEOVER_F() == 0 && …`）。
    [110] は呼ぶ前に `TARGET = LIMIT(TARGET, 1, CHARANUM-1)`（:248）。"""
    if value == 110:
        state.target = limit(state.target, 1, state.charanum - 1)
        return True
    gameover = check_gameover(state)
    if value in (111, 112):  # :252–259
        return not gameover and charanum_active(state) != 0
    if value in (113, 120):  # :262–269
        return not gameover and state.flag[63] == 0
    if value == 150:  # :276–278
        return not gameover
    raise ValueError(value)


def schedule_selectable(state: GameState) -> bool:
    """USERSHOP:281–285 [160]：`CFLAG:0 != 状態_無事 || TARGET == MASTER || FLAG:9` なら
    「スケジュールを設定するキャラクターが選択されていません」（PRINTW）。"""
    t = state.charas[state.target]
    return not (t.cflag[0] != CharaState.SAFE or state.target == GameState.MASTER or state.flag[9])


def toggle_party_view(state: GameState, out: TextOutput) -> None:
    """USERSHOP:218–227 控え表示切り替え。"""
    if charanum_safe_partycheck(state):
        if state.flag[61]:
            out.printl("キャラを全員表示します")
            state.flag[61] = 0
        else:
            out.printl("パーティのみ表示します")
            state.flag[61] = 1


def multi_set(state: GameState, out: TextOutput) -> None:
    """USERSHOP:230–238 一括設定。"""
    if charanum_safe(state) >= 2:
        if state.target == GameState.MASTER:
            state.target = state.rng.rand(state.charanum - 1) + 1
        if state.flag[9] == 0:
            out.printl("一括設定モードに変更しました")
            state.flag[9] = 1


def usershop_set_action(state: GameState, data: GameData, out: TextOutput, action: int, multiset: int) -> None:
    """`SHOP.ERB@USERSHOP_SET_ACTION`:610–664。"""
    t = state.charas[state.target]
    if check_gameover(state) or state.target == GameState.MASTER or (t.cflag[0] != CharaState.SAFE and not multiset):
        return
    if action == ActionPlan.DEFENSE and game_option(state, GameOption.SOLO):
        return
    if action == ActionPlan.SUPPORT and state.charanum < 3:
        return
    has_incapable = False
    if multiset == 0:
        if is_action_incapable(data, state, action, state.target):
            has_incapable = True
        else:
            t.cflag[100] = action
        print_action_msg(state, data, out, action, state.target)
    else:
        for i in range(state.charanum):
            c = state.charas[i]
            if i == GameState.MASTER or c.cflag[999] == 0:
                continue
            if c.cflag[0] in (CharaState.IMPRISONED, CharaState.BRAINWASHED, CharaState.KIDNAPPED, CharaState.DEAD):
                continue
            if is_action_incapable(data, state, action, i):
                has_incapable = True
            else:
                c.cflag[100] = action
            print_action_msg(state, data, out, action, i)
    if has_incapable:
        out.wait()


def print_action_msg(state: GameState, data: GameData, out: TextOutput, action: int, who: int) -> None:
    """`SHOP.ERB@USERSHOP_PRINT_ACTION_MSG`:674–718。"""
    i = _find_action(action)
    name = ACTION_NAMES[i]
    callname = state.charas[who].callname
    out.printl()
    if is_action_incapable(data, state, action, who, C_HP):
        out.printl(f"{callname}は{name}に必要な体力がありません")
    elif is_action_incapable(data, state, action, who, C_PREGNANT):
        out.printl(f"{callname}は妊娠中のため{name}ができません")
    elif is_action_incapable(data, state, action, who, C_LIMB):
        out.printl(f"{callname}は四肢欠損しているため{name}ができません")
    elif is_action_incapable(data, state, action, who, C_BROKEN):
        out.printl(f"{callname}は廃人化しているため{name}ができません")
    elif is_action_incapable(data, state, action, who, C_YAMA):
        out.set_color(COLOR_ORANGE)
        out.printl(f"{callname}は[夜魔の貴族]の効果で昼間は外出できません！")
        out.reset_color()
    elif is_action_incapable(data, state, action, who, C_SENSHI):
        out.set_color(COLOR_ORANGE)
        out.printl(f"{callname}は[生粋の戦士]の効果で{name}に参加できません！")
        out.reset_color()
    else:
        out.print(f"{callname}は{ACTION_STR[i]}")
    out.printl()


def action_plandisp(state: GameState, data: GameData, out: TextOutput) -> None:
    """`SHOP.ERB@USERSHOP_ACTION_PLANDISP`:564–605。"""
    out.printl("【行動予定】")
    skipped = 0
    shown = 0
    for i in range(state.charanum):
        c = state.charas[i]
        if i == GameState.MASTER or c.cflag[999] == 0:
            continue
        if c.cflag[0] != CharaState.SAFE:
            skipped += 1
            continue
        if shown % 3 == 0 and shown != 0:
            out.printl()
        out.print_plain(f"[{i}]{c.callname}：")
        a = c.cflag[100]
        shop_print_actionplan(out, a)
        out.print("  ")
        for k, label in ((C_HP, "（体力不足）"), (C_YAMA, "（夜魔の貴族＆昼）"), (C_SENSHI, "（生粋の戦士）"),
                         (C_SUPPORT, "（支援無効）"), (C_PREGNANT, "（妊娠中）"), (C_LIMB, "（四肢欠損）"),
                         (C_BROKEN, "（廃人）")):
            if is_action_incapable(data, state, a, i, k):
                out.print(label)
        shown += 1
    # 原作は改行せずに戻り、呼び出し元の PRINTL（:510）で行が閉じる


def action_confirm_prompt(state: GameState, data: GameData, out: TextOutput) -> str:
    """`SHOP.ERB@USERSHOP_ACTION_CONFIRM`:503–557 の前半。

    戻り値：`"input"`（確認の INPUT 待ち）、`"begin"`（確認なしで JUMP ACTION_MAIN）。
    """
    no_front = number_on_frontline(data, state) == 0 and not game_option(state, GameOption.SOLO)
    if state.flag[40] == 0 and not check_gameover(state):
        out.drawline()
        out.printl()
        out.printl("各キャラの行動予定は下のようです")
        out.printl()
        action_plandisp(state, data, out)
        out.printl()
        out.printl("この設定で行動を開始しますか？")
        out.printl("※ 行動を設定していないキャラは自動的に休憩になります")
        if no_front:
            out.printl("※ 誰も出撃しない場合は防衛力が低下します")
        out.drawline()
        _yes_no_nine(out)
        return "input"
    if state.flag[40] == 1 and no_front and not check_gameover(state):
        out.drawline()
        out.printl()
        out.printl("出撃・防衛を行う予定のキャラが一人も居ません")
        out.printl()
        action_plandisp(state, data, out)
        out.printl()
        out.printl("このまま行動を開始して宜しいですか？")
        out.printl("※ 出撃または防衛しないことにより防衛力が低下します")
        out.drawline()
        _yes_no_nine(out)
        return "input_second"
    return "begin"


def _yes_no_nine(out: TextOutput) -> None:
    out.printl("[0]いいえ")
    out.printl("[1]はい")
    out.printl("[9]はい（次から確認しない）")


def action_confirm_answer(state: GameState, data: GameData, kind: str, value: int) -> bool:
    """確認 INPUT の処理（:521–532、:545–553）。True = 行動開始（JUMP ACTION_MAIN）。

    原作の SELECTCASE は `CASE 9` と `CASEELSE → RETURN 0` しか無いため、`[1]はい` も中断になる（原作どおり）。
    """
    if value != 9:
        return False
    if kind == "input":
        state.flag[40] = 1
        if number_on_frontline(data, state) == 0 and not game_option(state, GameOption.SOLO):
            state.flag[40] = 2
    else:
        state.flag[40] = 2
    return True


# --- @SAVEINFO ---------------------------------------------------------------

_MODE_NAMES = ("GAMEOVER", "NORMAL", "SOLO", "HARDCORE", "SURVIVAL", "FREEPLAY", "SANDBOX", "INSTANT")  # DIM.ERH:49–59


def save_info(state: GameState, data: GameData, now: datetime | None = None) -> str:
    """`ゲーム内_イベント発生/オープニング処理.ERB@SAVEINFO`:583–614 の PUTFORM 内容。

    共用 RESULTS:0 も原作どおり書く（S26b）：:585 `GETTIME` → 日時文字列（reference/emuera-1824/Emuera/GameProc/
    Process.ScriptProc.cs:368–379）、:604 `SUBSTRING LOCALS:2, 1, 3`（命令としての式中関数 → RESULTS:0：GameProc/Function/
    Instraction.Child.cs@METHOD_Instruction:398–405）→ 最終値は版数の下 3 桁（GameBase.csv バージョン 408 → "408"）。
    オートセーブ（SystemProc@endCallEventShop:630–640 → @beginAutoSave:642–654）は @EVENTSHOP の後・@SHOW_SHOP の前に
    毎回これを呼ぶので、FLASHNEWS:74–87 が読む「前回の RESULTS:0」はこの値になる（`docs/wiki/python/result.md`）。
    """
    stamp = now or datetime.now()
    state.results[0] = stamp.strftime("%Y/%m/%d %H:%M:%S")  # :585 GETTIME（RESULT:0 の数値は模型化しない）
    mode = game_mode_check_proc(state)  # :586 CALL GAME_MODE_CHECK
    s0 = f"{_MODE_NAMES[mode]}モード" if 0 <= mode < len(_MODE_NAMES) else "☆カスタムモード"
    alive = tentacle_survive_num(state)
    if state.flag[64] > 0:
        s1 = "★GAMECLEAR"
    elif enemy_type_check(state, "BOSS") == 1:
        s1 = f"{state.flag[3] - alive + 1}体目"
    else:
        s1 = f"{state.flag[3] + alive}体目"
    ver = data.game_base_int("バージョン", 0)
    sub = str(1000 + ver)[1:4]  # :603–604 LOCALS:2 = {1000 + GAMEBASE_VERSION} / SUBSTRING LOCALS:2, 1, 3（半角数字なので幅＝文字数）
    state.results[0] = sub
    s2 = f"{div(ver, 1000)}.{sub}"  # :605
    s3 = f"{state.day[0]}日目"
    if state.flag[64] > 0:
        return f"{format_percent(s0, 14, True)} {format_percent(s3, 7, False)} {format_percent(s1, 12, False)}    ver{s2}"
    return f"{format_percent(s0, 14, True)} {format_percent(s3, 7, False)} {format_percent(s1, 6, False)}殲滅中    ver{s2}"


# --- [130] 状況の確認（SHOP_SHOW_SITUATION_LIST.ERB）-------------------------------------------------


def shop_show_situation_list(state: GameState, data: GameData, out: TextOutput, narration: NarrationService) -> None:
    """`インターミッション画面/SHOP_SHOW_SITUATION_LIST.ERB@SHOP_SHOW_SITUATION_LIST`:3–209。

    :10 で退避した FLAG:11 は戻さない（最後に表示した生存ボスの番号が残る）、:14 `SAVESTR:13 = BOSS`：原作どおり。
    """
    from .action import Ctx, print_transcallname
    from .battle.core import tentacle_access
    from .prison.event import tentacle_access_prison
    from .tentacle import tentacle_survive_check

    ctx = Ctx(state, data, out, narration)
    f = state.flag
    # RESULT:0 の追跡（:126 が読む）：@USERSHOP の RESULT（入力値 130：SystemProc@shopWaitInput:727–731）を
    # :6 LB がそのまま返す（PRINT_LINE.ERB:17–18 `RETURN RESULT`）。:16–38 のループは各回 TENTACLE_SURVIVE_CHECK
    # （RETURN n か関数終端 0：COMMON_TENTACLE_DATA.ERB:55–122）、生存なら TENTACLE_ACCESS "NAME"（関数終端 0：:198–211）
    # なので 1 回でも回れば 0。:97 TENTACLE_ACCESS_PRISON "NAME" も 0（:314–320）、:88–94 は見つかった番号か 0。
    # CHECK_PREGNANT_F 等の #FUNCTION は RESULT を書かない（Process.State.cs@ReturnF:502–525）。
    result0 = 130
    lb(out)  # :6
    out.printl()
    bit = 1  # :10–39
    if enemy_type_check(state, "BOSS") == 1:
        out.printl(f"現在活動中の{data.str_defaults.get(2502, '')}")
        state.savestr[13] = "BOSS"
        out.drawline()
        for _ in range(f[3]):
            r = tentacle_survive_check(state, bit)
            if r > 0:
                f[11] = r
                out.print("[")
                tentacle_access(ctx, "NAME")
                out.print("]")
            bit *= 2
            result0 = 0
    elif get_lastboss_phase(state) >= 1:  # :26–38（S27）：SAVESTR:13 は設定しない、FLAG:11 は戻さない
        out.printl(f"現在活動中の{data.str_defaults.get(2503, '')}")
        out.drawline()
        for _ in range(f[4]):
            r = tentacle_survive_check(state, bit)
            if r > 0:
                f[11] = r
                out.print("[")
                tentacle_access(ctx, "NAME")
                out.print("]")
            bit *= 2
            result0 = 0
    out.printl()
    out.drawline()
    others = [i for i in range(1, state.charanum)]
    # :44–70 入院／育児中
    if any(state.charas[i].cflag[0] in (CharaState.BEFORE_BIRTH, CharaState.CHILDCARE) for i in others):
        out.printl("入院/育児中のキャラ")
        out.drawline()
        for i in others:
            c = state.charas[i]
            if c.cflag[0] == CharaState.BEFORE_BIRTH:
                out.print(f" {c.callname}：特別病棟に入院　")
            elif c.cflag[0] == CharaState.CHILDCARE:
                out.print(f" {c.callname}：育児中　")
            if check_pregnant(data, state, i) and c.cflag[0] in (CharaState.BEFORE_BIRTH, CharaState.CHILDCARE):
                out.print("[妊娠中]")
            if c.cflag[0] in (CharaState.BEFORE_BIRTH, CharaState.CHILDCARE):
                out.printl()
        out.drawline()
    # :72–111 幽閉中
    out.printl("幽閉中のキャラ")
    out.drawline()
    n = 0
    for i in others:
        c = state.charas[i]
        if c.cflag[0] != CharaState.IMPRISONED:
            continue
        out.print(f" {c.callname}：")
        if c.cflag[20] == 2:  # :87–95（RESULT = 最後に一致した番号、BREAK は一致した直後）
            who = 0
            for k in range(state.charanum):
                who = 0
                if c.cflag[21] == state.charas[k].cflag[240]:
                    who = k
                if who:
                    break
            out.print(print_transcallname(state, who))
            result0 = who
        else:
            tentacle_access_prison(ctx, i, "NAME")
            result0 = 0
        out.print(f"によって幽閉中 {div(c.cflag[31], 2)}日目　")
        if check_pregnant(data, state, i):
            out.print("[妊娠中]　")
        if c.cflag[220] and state.flag.get_bit(805, 0) == 0:  # CONFIG_CHECK_OTHER_F(0) == 0
            out.print(f"育児中の子触手：{c.cflag[220]}")
        out.printl()
        n += 1
    if n == 0:
        out.printl("なし")
    out.drawline()
    # :113–138 拉致監禁中
    out.printl("拉致監禁中のキャラ")
    out.drawline()
    n = 0
    for i in others:
        c = state.charas[i]
        if c.cflag[0] != CharaState.KIDNAPPED:
            continue
        # :126 `PRINT_TRANSCALLNAME(RESULT)`：添字が CCOUNT ではなく直前の RESULT:0（原作の不具合）。`result0` 参照。
        if not 0 <= result0 < state.charanum:
            raise NotImplementedError(f"SHOP_SHOW_SITUATION_LIST:126 PRINT_TRANSCALLNAME({result0})：原作でも添字範囲外エラー")
        out.print(f"{print_transcallname(state, result0)}：廃ビルに拉致監禁中 {div(c.cflag[70], 2)}日目　")
        if check_pregnant(data, state, i):
            out.print("[妊娠中]　")
        if talent(data, c, "四肢欠損") > 0:
            out.print("[生オナホ]")
        out.printl()
        n += 1
    if n == 0:
        out.printl("なし")
    out.drawline()
    # :140–169 洗脳／悪堕ち
    out.printl("洗脳/悪堕ち中のキャラ")
    out.drawline()
    n = 0
    for i in others:
        c = state.charas[i]
        if c.cflag[0] == CharaState.BRAINWASHED:
            out.print(f" {c.callname}：洗脳（")
            if c.cflag[20] < 2:
                tentacle_access_prison(ctx, i, "NAME")
            elif c.cflag[20] == 2:
                out.print(print_transcallname(state, c.cflag[21]))
            out.print("）　")
        elif c.cflag[0] == CharaState.CORRUPTED:
            out.print(f" {c.callname}：悪堕ち　")
        if check_pregnant(data, state, i) and c.cflag[0] in (CharaState.BRAINWASHED, CharaState.CORRUPTED):
            out.print("[妊娠中]")
        if c.cflag[0] in (CharaState.BRAINWASHED, CharaState.CORRUPTED):
            out.printl()
            n += 1
    if n == 0:
        out.printl("なし")
    out.drawline()
    # :172–196 取り込まれたキャラ
    if not game_option(state, GameOption.SOLO):
        out.printl("取り込まれたキャラ")
        out.drawline()
        n = 0
        for i in others:
            c = state.charas[i]
            if c.cflag[0] != CharaState.DEAD:
                continue
            out.print(f" {c.callname}：")
            out.print("苗床化" if talent(data, c, "繁殖袋") else "取り込まれ")
            out.printl()
            n += 1
        if n == 0:
            out.printl("なし")
        out.drawline()
    # :199–208 子触手
    local = f[44] - sum(c.cflag[220] for c in state.charas)
    if local:
        out.printl("活動中の子触手の総数")
        out.drawline()
        out.printl(f" {local}匹")
        out.drawline()
    out.printw()  # :209
