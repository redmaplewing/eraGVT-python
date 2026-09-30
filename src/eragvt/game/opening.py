"""新遊戲：`@EVENTFIRST` の翻寫。路徑相對 `source/earGVP/ERB/`。

既定の経路（AGENTS.md「跳過 UI 必須走原作預設路徑」：プレイヤーが何も設定を変えずに確定した場合）：
- 全域資料（GLOBAL）不存在＝真正的初次啟動（本程式尚未寫入全域檔）。
- ゲームモード選択 `[1] NORMAL`（`オープニング処理.ERB@MODE_SELECT`:297。既定値のない選択なので先頭の NORMAL）。
- キャラメイキング：何も設定せず `[1000]★キャラメイクを完了する（未設定のキャラはおまかせ）`
  （`SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN`:5、:206–209）→ 3 名の汎用キャラをランダム生成。
- ヒロインデータ確認 `[1]「基本セット」で開始`（`オープニング処理.ERB@HEROINE_PRESET`:617）。
- プロローグ `[0]いいえ`。

選択肢として `preset=PRESET_TOKUSOU`：キャラメイキングで `[200]プリセットを読み込む` → `[0] 特装戦隊` → `[1]はい`
→ `[1000]`（S03〜S09 の開局）。

與原作不同之處都標 `DEVIATION:`，並列在 `docs/wiki/bridge/deviations.md`。
"""

from __future__ import annotations

from ..data.csv_loader import GameData
from ..state import GameState
from ..state.constants import MODE_OPTIONS, ActionPlan, Base, CharaState, GameMode, GameOption, PARTY_MAX
from .chara_common import (
    charatalent,
    is_female,
    is_male,
    level_status,
    seikaku_check,
    talent,
)
from .era import div, isqrt, limit
from .body import chara_make_age_setting, chara_size_default, generate_bodyline
from .chara_make import base_profile_generic, initialize_personality, initialize_race
from .tentacle import BOSS_ERB_NUM, MOB_TENTACLE_NUMBERS, get_lastboss_phase, tentacle_survive_num

PRESET_TOKUSOU = 0  # 初期セット/0_特捜戦隊.ERB


def game_option(state: GameState, option: GameOption) -> bool:
    """`GAME_OPTION_CHECK_F(n)` = `GETBIT(FLAG:0, n)`（オープニング処理_カスタムGAMEMODE.ERB:89–91）。"""
    return state.flag.get_bit(0, int(option))


# --- @EVENTFIRST ------------------------------------------------------------


def event_first(state: GameState, data: GameData, preset: int | None = None) -> None:
    """`ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST`:19–292（最後の BEGIN SHOP の直前まで）。

    `state` は `GameState.new(data)`（endOpenning 後：キャラ 0 と 999）であること。
    `preset` が None なら既定の経路（汎用キャラ 3 名をおまかせ生成）、番号ならその初期セットを読み込む。
    """
    # :29–45 LOADGLOBAL 失敗（初回起動）→ 雑魚敵出現率フィルターを 100 で初期化
    for n in MOB_TENTACLE_NUMBERS:
        state.mob_flag[(n // 100, n % 100)] = 100
    # :48–49
    state.time = 1
    state.money = 5000
    # :51
    config_init(state, 1)
    # :53–59 所持衣装
    for item in (100, 200, 201, 202, 299, 300, 401):
        state.item[item] = 1
    # :63–64 MASTER にダミー（999）を入れ、TARGET（キャラ 0）を消す
    state.swap_chara(0, 1)
    state.del_chara(1)
    # :73–87 モード選択（ボスフラグ・防衛力のリセット → MODE_SELECT で NORMAL）
    state.flag[100] = 0
    state.flag[101] = 0
    state.flag[852] = 5000
    state.flag[0] = MODE_OPTIONS[GameMode.NORMAL]  # MODE_SELECT:372–376
    # :90–105
    state.flag[50] = 1
    state.flag[51] = 1
    state.flag[3] = BOSS_ERB_NUM
    state.flag[4] = 1
    for i in range(state.flag[3]):
        state.flag.set_bit(100, i)
    state.flag[101] = 0
    # :111–122 モードに応じたデフォルト人数の汎用キャラ
    for _ in range(1 if game_option(state, GameOption.SOLO) else 3):
        state.add_chara(data, 0)
        state.flag[8] += 1
    # :127 CALL CHARA_MAKE_MAIN, 0
    if preset is None:
        chara_make_main_default(state, data)
    else:
        chara_make_main_preset(state, data, preset)
    # :135 キャラメイク完了処理（CHARA_MAKE_MAIN の [1000] に続いて 2 回目）
    chara_make_finalize(state, data)
    # :143–166 口上番号・行動予定
    kojo_setting = data.index_of("TALENT", "口上設定")
    robot = data.index_of("TALENT", "ロボっ子")
    for i, c in enumerate(state.charas):
        if i == GameState.MASTER:
            continue
        c.cflag[6] = c.no
        if c.no == 0 and is_male(data, c):
            c.cflag[6] = 1
        if c.no == 0 and c.talent[robot] > 0:
            c.cflag[6] = 2
        k = c.talent[kojo_setting]
        if k == -2:
            c.cflag[6] = -2
        elif k == 0 and is_male(data, c):
            c.cflag[6] = 1
        elif k == 0:
            c.cflag[6] = 0
        elif k == 1:
            c.cflag[6] = 2
        elif k == 2:
            c.cflag[6] = 3
        elif k == 3:
            c.cflag[6] = 4
        c.cflag[100] = ActionPlan.REST
    # :169
    set_limit_day(state)
    # :173 HEROINE_PRESET → [1] 基本セット → CONFIG_INIT(1)（:787–790）
    config_init(state, 1)
    # :177–238 プロローグ：表示のみ。:241–250 デフォルト悪堕ち：該当なし（CFLAG:0 はすべて 0）
    if any(c.cflag[0] == CharaState.CORRUPTED for c in state.charas[1:]):
        raise NotImplementedError("CORRUPT_CHANGE_LOOKS_MAIN は未移植")
    # :254–267 口上の初期設定
    for i in range(state.charanum):
        if i == GameState.MASTER:
            continue
        state.target = i
        c = state.charas[i]
        if c.cflag[0] != CharaState.SAFE and c.cflag[20] == 0 and c.cflag[21] == 0:
            c.cflag[21] = state.rng.rand(7) + 1
        # CALL MESSAGE_FIRST（地の文/MESSAGE.ERB:4）→ KOJO_ROOT(CFLAG:6, "FIRST")。
        # 状態への影響は FLAG:62 = 0 と FLAG:900 = 0 のみ（口上/口上システム関係/KOJO_ROOT.ERB:50–90）。
        # DEVIATION: 口上テキストは未移植（S07）。表示は @LB で流されるため画面上の差もない。
        state.flag[62] = 0
        state.flag[900] = 0
        if i <= PARTY_MAX:
            c.cflag[999] = 1
    # :269–283 初期キャラの衣装を所持品に
    for i in range(state.charanum - 1):
        c = state.charas[i + 1]
        for k in (40, 41, 42, 43):
            if state.item[c.cflag[k]] == 0:
                state.item[c.cflag[k]] = 1
        for eq in range(600, 700):
            if c.equip[eq]:
                state.item[eq] = 1
    # :286–288
    state.flag[41] = 1
    research_quota(state)
    # :291 CALL UPDATE：GLOBAL なし・LASTLOAD_VERSION == -1 のため状態変化なし
    #（バージョン間互換処理.ERB@UPDATE:95–131、:131 `IF LASTLOAD_VERSION != -1`）


def config_init(state: GameState, preset: int) -> None:
    """`SYSTEM/コンフィグ/CONFIG_初期設定.ERB@CONFIG_INIT(ARG)`:4–61（プリセット 1＝基本セットのみ）。"""
    if preset != 1:
        raise NotImplementedError("CONFIG_INIT は基本セット(1)のみ移植")
    state.flag[800] = 0
    state.flag[801] = 1
    state.flag[802] = 1 + 2 + 4 + 8
    state.flag[803] = 1 + 2 + 4 + 256
    state.flag[804] = 1
    state.flag[805] = 2


def set_limit_day(state: GameState) -> None:
    """`オープニング処理.ERB@SET_LIMIT_DAY`:411–452（[SKIPSTART]〜[SKIPEND] は実行されない）。"""
    f = state.flag
    f[2] = 11
    if game_option(state, GameOption.HARDCORE):
        f[2] += 2
    if game_option(state, GameOption.SOLO):
        f[2] += 1
    if game_option(state, GameOption.ENDLESS) or game_option(state, GameOption.NO_TIME_LIMIT):
        f[2] -= 2
    if game_option(state, GameOption.JOIN_RETIRE):
        f[2] -= 1
    if game_option(state, GameOption.STAT_DECLINE):
        f[2] += 1
    if not game_option(state, GameOption.SOLO):
        f[2] -= (state.charanum - 1) - 3
    f[1] = 0
    if not game_option(state, GameOption.ENDLESS):
        f[1] = f[3] * f[2] + f[4] * 10


def research_quota(state: GameState) -> None:
    """`ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@RESEARCH_QUOTA`:455–505。"""
    kills = min(state.flag[3] - tentacle_survive_num(state) + 1, 9)
    local = 12
    if game_option(state, GameOption.HARDCORE):
        local += 6
    if game_option(state, GameOption.SOLO):
        local -= 6
    if game_option(state, GameOption.JOIN_RETIRE):
        local += 1
    if game_option(state, GameOption.STAT_DECLINE):
        local -= 1
    kill_bonus = div(kills * local, 3) + 24
    if game_option(state, GameOption.NO_TIME_LIMIT):
        kill_bonus = div(kill_bonus, 2)
    if game_option(state, GameOption.SOLO):
        kill_bonus -= 12
    local = 2
    if game_option(state, GameOption.NO_TIME_LIMIT):
        local -= 4
    if game_option(state, GameOption.HARDCORE):
        local += 1
    day_bonus = isqrt(state.day[0]) * local
    local = kill_bonus + day_bonus
    if local < 10:
        local = 10
    # DEVIATION: 乱数の消費回数・系列は Emuera（MT）と一致させない（deviations.md「乱数」）。
    if game_option(state, GameOption.SOLO) and local >= 60 + state.rng.rand(5):
        local = 60
    elif local >= 90 + state.rng.rand(5):
        local = 90
    if get_lastboss_phase(state) >= 1:
        local = div(local * 6, 5)
    state.flag[46] = local
    state.flag[47] = 0


# --- キャラメイキング ---------------------------------------------------------


def _chara_make_load_global(state: GameState) -> None:
    """`CHARA_MAKE.ERB@CHARA_MAKE_MAIN`:9–21：LOADGLOBAL（失敗）後、GLOBAL の既定値（すべて 0／空）から共通設定を読む。
    つまり主題・変身名・かけ声なし、苗字／名前の言語「デフォルト」、種族「ランダム」、フィート自動割り当て「なし」、
    性格「完全ランダム」（:32–40 の表示）。"""
    for k in (5, 6, 7, 820, 821, 822, 823, 824, 825):
        state.flag[k] = 0
    for k in (10, 11, 12):
        state.savestr[k] = ""


def chara_make_main_default(state: GameState, data: GameData) -> None:
    """`CHARA_MAKE.ERB@CHARA_MAKE_MAIN`:5 で何も設定せず [1000] を押した場合の状態変化。"""
    _chara_make_load_global(state)
    # :206–209 [1000] キャラメイクを完了する → CHARA_MAKE_FINALIZE（未設定のキャラは INITIALIZE でおまかせ生成）
    chara_make_finalize(state, data)


def chara_make_main_preset(state: GameState, data: GameData, preset: int) -> None:
    """`CHARA_MAKE.ERB@CHARA_MAKE_MAIN`:5 で [200] → 初期セット → [1000] と進んだ場合の状態変化。"""
    if preset != PRESET_TOKUSOU:
        raise NotImplementedError("初期セットは 0_特捜戦隊 のみ移植")
    _chara_make_load_global(state)
    # :316–322 [200] → SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI:5–45 → [0] → [1]はい
    for _ in range(state.charanum - 1):
        state.del_chara(1)
        state.flag[8] -= 1
    shokiset_select_0(state, data)
    shokiset_csvfix(state, data)  # SHOKISET.ERB:45
    # :206–209 [1000] キャラメイクを完了する
    chara_make_finalize(state, data)


def shokiset_select_0(state: GameState, data: GameData) -> None:
    """`SYSTEM/キャラメイキング関連/初期セット/0_特捜戦隊.ERB@SHOKISET_SELECT_0`:18–32。"""
    state.flag[5] = 1
    state.savestr[10] = "特装戦隊"
    state.flag[7] = 1
    state.savestr[12] = "特命特捜!"
    for no in (301, 302, 303):
        state.add_chara(data, no)
        state.flag[8] += 1
    shokiset_csvfix(state, data)


def shokiset_csvfix(state: GameState, data: GameData) -> None:
    """`SHOKISET.ERB@SHOKISET_CSVFIX`:96–103。"""
    for i in range(state.charanum):
        if i == GameState.MASTER:
            continue
        firstsetting_chara_csvfix(state, data, i)


def _csvbase(data: GameData, no: int, index: int) -> int:
    """`CSVBASE(no, index)`：CSV の「基礎」（テンプレートの Maxbase、未定義は 0）
    （reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs@GetCharacterIntfromCSVData:1383–1396）。"""
    return data.charas[no].base.get(index, 0)


def firstsetting_chara_csvfix(state: GameState, data: GameData, index: int) -> None:
    """`SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_CSVFIX`:1624–1670。"""
    c = state.charas[index]
    level = data.index_of("ABL", "レベル")
    if c.abl[level] < 1:
        c.abl[level] = 1
    for k in range(7):
        b = k if k <= 2 else k + 7
        if _csvbase(data, c.no, b) == 0 and b in (0, 1):
            c.maxbase[b] = 1000
            c.base[b] = c.maxbase[b]
        elif _csvbase(data, c.no, b) == 0:
            c.maxbase[b] = 100
            c.base[b] = c.maxbase[b]
    if c.cstr[36] == "":
        c.cstr[36] = c.cstr[34]
        c.cstr[34] = c.cstr[32]
        c.cstr[35] = c.cstr[33]
        c.cstr[37] = c.cstr[36]
    for dist in (1, 2, 3):
        if c.cstr[dist + 14] != "":
            decode_weapon_data(data, state, index, dist)
    c.cstr[15] = ""
    c.cstr[16] = ""
    c.cstr[17] = ""


_BATTLE_STYLES = {"連続": 1, "装甲": 2, "撹乱": 3, "重撃": 4, "広範": 5, "全力": 6, "知略": 7, "設置": 8, "使役": 9, "反撃": 10}


def decode_weapon_data(data: GameData, state: GameState, index: int, dist: int) -> int:
    """`武器と衣装/武器カスタマイズ関連/WEAPON_ARCHIVE.ERB@DECODE_WEAPON_DATA`:7–50。"""
    c = state.charas[index]
    s = c.cstr[dist + 14]
    if s == "":
        return -1
    parts = s.split("//")  # SPLIT（Process.ScriptProc.cs:522–537）
    if len(parts) < 3:
        # LOCALS は関数ごとに保持されるため、要素が足りないと前回の値が残る。本作の初期セットでは発生しない。
        raise NotImplementedError(f"武器データの節が 3 未満：{s!r}")
    c.cstr[dist + 4] = parts[0]
    style_index = data.index_of("CDFLAG2", "戦闘スタイル")  # Cdflag2.csv:73 `500,戦闘スタイル`
    style = parts[2]
    value = 0
    for i, (name, v) in enumerate(_BATTLE_STYLES.items(), start=1):
        if style == name or style == str(i):
            value = v
            break
    c.cdflag[(dist, style_index)] = value
    return 0


def chara_make_finalize(state: GameState, data: GameData, arg: int = 0) -> None:
    """`SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_FINALIZE`:221–487。"""
    level = data.index_of("ABL", "レベル")
    for sel in range(1, state.charanum):
        if arg != 0 and sel != arg:
            continue
        chara_make_initialize(state, data, sel)
        c = state.charas[sel]
        if c.maxbase[Base.EJACULATION] < 1:
            c.maxbase[Base.EJACULATION] = 10000
        if c.maxbase[Base.LACTATION] < 1:
            c.maxbase[Base.LACTATION] = 10000
        if c.cflag[240] == 0:
            c.cflag[240] = sel
        tp = data.index_of("PALAM", "修練P")  # JUEL:修練P（JUEL の名前は Palam.csv と共通）
        if c.juel[tp] >= 10:
            for _ in range(div(c.juel[tp], 10)):
                c.cflag[50 + state.rng.rand(7)] += 1
                c.juel[tp] -= 10
        # ジャンプ性能（:249–253、変身能力による分岐はどちらも同じ式）
        c.maxbase[Base.AIR_DASH] = limit(_csvbase(data, c.no, 22), 0, 8)
        if talent(data, c, "空中得意"):
            c.maxbase[Base.AIR_DASH] = min(c.maxbase[Base.AIR_DASH] + talent(data, c, "空中得意"), 8)
        if talent(data, c, "空中苦手"):
            c.maxbase[Base.AIR_DASH] = max(c.maxbase[Base.AIR_DASH] - talent(data, c, "空中苦手"), 0)
        _set_basic_values(data, c)
        c.base[Base.HP] += c.cflag[50] * 10
        c.base[Base.ENERGY] += c.cflag[51] * 10
        c.base[Base.SEX_RESIST] += c.cflag[52]
        c.base[Base.ATTACK] += c.cflag[53]
        c.base[Base.DEFENSE] += c.cflag[54]
        c.base[Base.AGILITY] += c.cflag[55]
        c.base[Base.INTELLECT] += c.cflag[56]
        for k in range(7):
            b = k if k <= 2 else k + 7
            c.maxbase[b] = c.base[b]
        if c.abl[level] < 1:
            c.abl[level] = 1
        c.base[50] = c.base[Base.HP]  # 体力基礎
        c.base[51] = c.base[Base.ENERGY]  # 気力基礎
        c.base[52] = c.base[Base.SEX_RESIST]  # 性耐性基礎
        level_status(data, state, sel)
        c.base[Base.HP] = c.maxbase[Base.HP]
        c.base[Base.ENERGY] = c.maxbase[Base.ENERGY]
        c.base[Base.SEX_RESIST] = c.maxbase[Base.SEX_RESIST]
        # 初期衣装（:402–429）
        if c.cflag[40] == 0:
            c.cflag[40] = 100
        if c.cflag[40] == -1:
            c.cflag[40] = 0
        if talent(data, c, "変身能力") == 1 and c.cflag[41] == 0:
            c.cflag[41] = 200
        if c.cflag[41] == -1:
            c.cflag[41] = 0
        if c.cflag[42] == 0:
            # CLOTH_NO_INNER（武器と衣装/衣装関連/CLOTH_BATTLE.ERB:452）は未移植。初期セット 0・汎用キャラ（Chara000 CSV `フラグ,42,300`）とも 300 が入っている。
            raise NotImplementedError("CFLAG:42 == 0（CLOTH_NO_INNER）は未移植")
        if c.cflag[42] == -1:
            c.cflag[42] = 0
        if c.cflag[43] == -1:
            c.cflag[43] = 0
        if c.cflag[10] == 0:
            c.cflag[10] = 25
        if c.cflag[11] == 0:
            c.cflag[11] = 110
        for dist in (1, 2, 3):
            if c.cstr[dist + 14] != "":
                decode_weapon_data(data, state, sel, dist)
        c.cstr[15] = ""
        c.cstr[16] = ""
        c.cstr[17] = ""
        if talent(data, c, "噂好きの友人"):
            c.cflag[120] = 1
        if talent(data, c, "警察関係者") == 1 and c.cflag[121] < 2:
            c.cflag[121] = 1
        if talent(data, c, "警察関係者") == 2:
            c.cflag[121] = 2
        if talent(data, c, "情報屋") == 1 and c.cflag[122] == 0:
            c.cflag[122] = 1
            c.cflag[122] |= 2
            rng = state.rng
            if rng.rand(7) == 0:
                c.cflag.set_bit(122, 2)
            elif rng.rand(6) == 0:
                c.cflag.set_bit(122, 3)
            elif rng.rand(5) == 0:
                c.cflag.set_bit(122, 4)
            elif rng.rand(4) == 0:
                c.cflag.set_bit(122, 2)
                c.cflag.set_bit(122, 3)
            elif rng.rand(3) == 0:
                c.cflag.set_bit(122, 2)
                c.cflag.set_bit(122, 4)
            elif rng.rand(2) == 0:
                c.cflag.set_bit(122, 3)
                c.cflag.set_bit(122, 4)
        if talent(data, c, "裕福な実家") == 1 or c.cflag[123] > 0:
            c.cflag[123] = 1
            state.money += 2500
        v_exp = data.index_of("EXP", "Ｖ経験")
        if c.exp[v_exp] > 0:
            pass
        elif talent(data, c, "処女") < 1 and is_female(data, c):
            c.exp[v_exp] = 1 + state.rng.rand(4)
        else:
            c.exp[v_exp] = 0


def _set_basic_values(data: GameData, c) -> None:
    """素質基本値の保存（CHARA_MAKE_DEFAULT.ERB:260–354）：BASE（通常時）と MAXBASE（変身時）の 90〜93。"""
    for store, t in ((c.base, 0), (c.maxbase, 1)):
        # 性別
        if charatalent(data, c, t, "オトコ") > 0:
            store[90] = 3 if charatalent(data, c, t, "男の娘") > 0 else 1
        elif charatalent(data, c, t, "ふたなり") > 0:
            store[90] = 2
        else:
            store[90] = 0
        if t == 0:
            # 体格・胸サイズ（通常時は CHARATALENT_F で判定）
            if charatalent(data, c, 0, "小柄") > 0:
                store[91] = -1
            elif charatalent(data, c, 0, "長身") > 0:
                store[91] = 1
            else:
                store[91] = 0
            for name, v in (("絶壁", -2), ("貧乳", -1), ("奇乳", 5), ("魔乳", 4), ("超乳", 3), ("爆乳", 2), ("巨乳", 1)):
                if charatalent(data, c, 0, name) > 0:
                    store[92] = v
                    break
            else:
                store[92] = 0
        else:
            # 変身時は素質の変動値をそのまま（:333–334）
            store[91] = talent(data, c, "変身時体格変動")
            store[92] = talent(data, c, "変身時胸サイズ変動")
        for name, v in (("安産型", 1), ("むちむち", 2), ("イカ腹", 3), ("スレンダー", 4), ("巨尻", 5), ("爆尻", 6)):
            if charatalent(data, c, t, name) > 0:
                store[93] = v
                break
        else:
            store[93] = 0


def chara_make_initialize(state: GameState, data: GameData, sel: int) -> None:
    """`CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_INITIALIZE`:5–211。"""
    c = state.charas[sel]
    initialize_race(state, data, sel)  # :8–72
    initialize_personality(state, data, sel)  # :74–164
    # :166 CALL CHARA_MAKE_BASE_PROFILE(SELECT)
    chara_make_base_profile(state, data, sel)
    # 変身名のロード（:166–209）
    if c.callname != "汎用キャラ" and talent(data, c, "変身能力") == 1:
        if c.cstr[0] == "":
            head = state.savestr[11]
            tail = c.callname
            if state.flag[820] > 0:
                raise NotImplementedError("RANDOMNAMING_FROMGENRE は未移植")
            if head + tail != "":
                c.cstr[0] = head + tail
                c.cflag[2] = 1
                if c.cstr[3] == "":
                    c.cstr[3] = state.savestr[10] + c.cstr[0] + changingcall_detail(state, seikaku_check(data, c))
                    c.cflag[5] = 1
        if c.cstr[1] == "" and c.cstr[0] != "":
            c.cstr[1] = c.cstr[0]
            c.cflag[3] = 1
        if c.cstr[2] == "" and state.savestr[12] != "":
            c.cstr[2] = state.savestr[12]
            c.cflag[4] = 1


def chara_make_base_profile(state: GameState, data: GameData, sel: int) -> None:
    """`CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE(SELECT)`:493–980（身体データの生成）。

    CSV キャラ（呼び名が「汎用キャラ」でない）は、プロフィール未設定（CFLAG:34 == 0）かつ `NO == 0` のときだけ
    GENERATE_BODYLINE → CHARA_MAKE_AGE_SETTING → CHARA_SIZE_DEFAULT を行い、いずれにせよ :505 で RETURN する。
    NO は CSV の番号（reference/emuera-1824/Emuera/GameData/Variable/CharacterData.cs:99 `NO = tmpl.No`）なので、
    初期セットのキャラ（301〜303 など）では何もしない＝BASE:40–48 は 0、CFLAG:34 は 0 のまま（原作どおり）。
    """
    c = state.charas[sel]
    if c.callname != "汎用キャラ":  # :496
        if c.cflag[34] == 0 and c.no == 0:  # :498–503
            generate_bodyline(state, data, c)
            chara_make_age_setting(state, data, c)
            chara_size_default(data, c)
        return  # :505
    # :507–975 未初期化キャラ（汎用キャラ）のランダム生成（既定の開局はここを通る）
    base_profile_generic(state, data, sel)


_CALL_HEAD = ("、参上", "、見参", "、推参", "、準備完了")
_CALL_TAIL: list[tuple[tuple[int, ...], tuple[str, ...]]] = [
    ((10, 11, 18), ("……！", "……！", "……！", "。……っ！ 行きます！", "。やるしか……ないよね……！")),
    ((13, 17, 19, 23, 25), ("！", "！", "っ！", "！ よーし行くぞぉ！", "！ 覚悟してねっ！")),
    ((14, 15), ("…♪", "……用意はいいかしら？", "……さて、行きますよ")),
    ((21, 22, 28), ("", "", "", "。行く……ッ", "。……殲滅開始")),
    ((24,), ("", "", "。さて、始めようぞ", "。始動じゃ、覚悟せい")),
]
_CALL_TAIL_DEFAULT = ("！", "！", "！", "…さあ、行くわよ！", "…負けないわよ！", "…覚悟しなさい！")


def changingcall_detail(state: GameState, seikaku: int) -> str:
    """`FIRSTSETTING_変身デフォルト口上.ERB@FIRSTSETTING_CHANGINGCALL_DETAIL`:33–137。
    STRDATA は `rand(件数)` で 1 件選ぶ（reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:730–755）。"""
    tails = _CALL_TAIL_DEFAULT
    for group, options in _CALL_TAIL:
        if seikaku in group:
            tails = options
            break
    head = _CALL_HEAD[state.rng.rand(len(_CALL_HEAD))]
    tail = tails[state.rng.rand(len(tails))]
    return head + tail
