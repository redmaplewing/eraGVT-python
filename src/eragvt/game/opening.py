"""新遊戲：`@EVENTFIRST` の翻寫。路徑相對 `source/earGVP/ERB/`。

既定の経路（AGENTS.md「跳過 UI 必須走原作預設路徑」：プレイヤーが何も設定を変えずに確定した場合）：
- 全域資料（GLOBAL）不存在＝真正的初次啟動（本程式尚未寫入全域檔）。
- ゲームモード選択 `[1] NORMAL`（`オープニング処理.ERB@MODE_SELECT`:297。既定値のない選択なので先頭の NORMAL）。
- キャラメイキング：何も設定せず `[1000]★キャラメイクを完了する（未設定のキャラはおまかせ）`
  （`SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN`:5、:206–209）→ 3 名の汎用キャラをランダム生成。
- ヒロインデータ確認 `[1]「基本セット」で開始`（`オープニング処理.ERB@HEROINE_PRESET`:617）。S24 からは画面を表示して
  入力を受ける（`event_first_gen`；[0]〜[3]・[10] 編集。非対話の `event_first` は `config_preset`（既定 1）を入力する）。
- プロローグ `[0]いいえ`。

選択肢として `preset=PRESET_TOKUSOU`：キャラメイキングで `[200]プリセットを読み込む` → `[0] 特装戦隊` → `[1]はい`
→ `[1000]`（S03〜S09 の開局）。

グローバルデータ（S24）：`GlobalStore`（メモリ＋ global.json）。:29 LOADGLOBAL 成功時は `CALL UPDATE`（GLOBAL の
config・性嗜好フィルタ・雑魚敵フィルタを反映）、失敗時（真の初回起動）は MOB_FLAG を 100 で初期化。

與原作不同之處都標 `DEVIATION:`，並列在 `docs/wiki/bridge/deviations.md`。
"""

from __future__ import annotations

from collections.abc import Generator

from ..data.csv_loader import GameData
from ..state import GameState
from ..state.savefile import GameIdentity, GlobalStore
from ..text import TextOutput
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
from .config import config_gen, config_init, heroine_preset_gen, update, update_global
from .tentacle import BOSS_ERB_NUM, MOB_TENTACLE_NUMBERS, get_lastboss_phase, tentacle_survive_num

PRESET_TOKUSOU = 0  # 初期セット/0_特捜戦隊.ERB


def game_option(state: GameState, option: GameOption) -> bool:
    """`GAME_OPTION_CHECK_F(n)` = `GETBIT(FLAG:0, n)`（オープニング処理_カスタムGAMEMODE.ERB:89–91）。"""
    return state.flag.get_bit(0, int(option))


# --- @EVENTFIRST ------------------------------------------------------------


def event_first(
    state: GameState,
    data: GameData,
    preset: int | None = None,
    config_preset: int = 1,
    store: GlobalStore | None = None,
    out: TextOutput | None = None,
    narration=None,
) -> None:
    """`event_first_gen` を固定の入力で最後まで実行する（テスト・模擬用）。

    輸入：開局二擇（None 為 [0]、初期セット為 [1]）→ CHARA_MAKE_MAIN [1000] → HEROINE_PRESET [config_preset]。
    `store` 省略時は空のメモリ上グローバル（ファイルなし＝真の初回起動）。
    """
    gen = event_first_gen(state, data, out or TextOutput(), store or GlobalStore(identity=GameIdentity.from_data(data)), narration)
    inputs = [0 if preset is None else 1, 1000, config_preset]
    try:
        next(gen)
        for v in inputs:
            gen.send(v)
    except StopIteration:
        return
    raise RuntimeError("event_first：入力が足りない（未対応の画面で INPUT 待ち）")


MODE_SELECT_FOOTER = ("[100] タイトルに戻る　　　　　　　　", "[200] グローバルコンフィグの編集　　　　　　　　", "[300] ゲームの説明")


def _show_mode_select(out: TextOutput) -> None:
    # DEVIATION: 模式選擇仍由既有開局二擇代替；S55 已接通後續角色製作主選單。
    # （[0] が原作の既定＝何も変えずに確定した場合、[1] はキャラメイクで初期セットを読み込んだ場合）。
    # 末尾の [100]／[200]／[300] は MODE_SELECT:360–368 の原文。
    out.drawline()
    out.printl("[0] おまかせで開始（原作の既定：汎用キャラ 3 名をランダム生成）")
    out.printl("[1] 初期セット『特装戦隊』で開始")
    out.printl()
    for text in MODE_SELECT_FOOTER:
        out.print(text)
    out.printl()


def event_first_gen(
    state: GameState, data: GameData, out: TextOutput, store: GlobalStore, narration=None
) -> Generator[None, int, bool]:
    """`ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST`:19–292（最後の BEGIN SHOP の直前まで）。

    `state` は `GameState.new(data)`（endOpenning 後：キャラ 0 と 999）であること。
    戻り値：True＝BEGIN SHOP へ、False＝MODE_SELECT の [100]（:82–85 RESETDATA → BEGIN TITLE）。
    """
    out.reset_bgcolor()  # オープニング処理.ERB@EVENTFIRST:27。
    version = GameIdentity.from_data(data).version
    # :29–44 LOADGLOBAL：成功 → CALL UPDATE、失敗（初回起動）→ 雑魚敵出現率フィルターを 100 で初期化
    if store.load():
        update(state, store, out, version)
    else:
        for n in MOB_TENTACLE_NUMBERS:
            state.mob_flag[(n // 100, n % 100)] = 100
    # :48–49
    state.time = 1
    state.money = 5000
    # :51
    config_init(state, 1, store)
    # :53–59 所持衣装
    for item in (100, 200, 201, 202, 299, 300, 401):
        state.item[item] = 1
    # :63–64 MASTER にダミー（999）を入れ、TARGET（キャラ 0）を消す
    state.swap_chara(0, 1)
    state.del_chara(1)
    # :73–87 モード選択（ボスフラグ・防衛力のリセット → MODE_SELECT で NORMAL）
    while True:
        state.flag[100] = 0
        state.flag[101] = 0
        state.flag[852] = 5000
        preset: int | None = None
        _show_mode_select(out)
        while True:  # MODE_SELECT:369 $INPUT_LOOP_MODE
            r = yield
            if r in (0, 1):
                preset = None if r == 0 else PRESET_TOKUSOU
                break
            if r == 100:  # :391–392 RETURN 999 → :82–85 RESETDATA・BEGIN TITLE
                return False
            if r == 200:  # :393–402（引継ぎフラグ == 0）
                for i in range(5):
                    state.flag[801 + i] = store.mem.global_[11 + i]
                update_global(state, store, out, version)
                yield from config_gen(state, data, out, store, "mainmenu")
                _show_mode_select(out)  # GOTO MASTER_LOOP（MODE_SELECT:300）
                continue
            if r == 300:  # :403–405 CALL TUTORIAL
                from .tutorial import tutorial
                yield from tutorial(state, out)
                _show_mode_select(out)  # :405 GOTO MASTER_LOOP
                continue
            out.clearline(1)
            out.printl("無効な値です")
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
        from .action import Ctx
        # 保留同一輸出與口上服務；非互動 helper 未提供時，由性格初始化按需載入 catalog。
        generation_ctx = Ctx(state, data, out, narration, store)
        from .creation_menu import creation_menu
        result = yield from creation_menu(generation_ctx, preset)
        if result == -1:  # EVENTFIRST:128–132：清除角色但不歸零 FLAG:8。
            for _ in range(state.charanum - 1):
                state.del_chara(1)
            continue
        break
    # :135 キャラメイク完了処理（CHARA_MAKE_MAIN の [1000] に続いて 2 回目）
    chara_make_finalize(state, data, ctx=generation_ctx)
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
    # :173 HEROINE_PRESET（:617–759）→ 選んだプリセットで CONFIG_INIT（:758）
    yield from heroine_preset_gen(state, data, out, store)
    # :177–238 プロローグ：表示のみ。:241–250 デフォルト悪堕ち（`GROUPMATCH(CFLAG:LOCAL:0, 状態_悪堕ち,)`：末尾の空引数は
    # 引数にならない＝ExpressionParser.cs@ReduceArguments:63–117）。既定の開局では該当なし（CFLAG:0 はすべて 0）。
    # event_first は出力を持たない（deviations「開局 MESSAGE_FIRST」）ので表示は捨てる。
    for i in range(1, state.charanum):
        if state.charas[i].cflag[0] == CharaState.CORRUPTED:
            from ..text import NullNarrationService, TextOutput
            from .action import Ctx
            from .corruption import corrupt_change_looks_main

            corrupt_change_looks_main(Ctx(state, data, TextOutput(), NullNarrationService()), i)
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
    # :291 CALL UPDATE（バージョン間互換処理.ERB@UPDATE:95–846）：LOADGLOBAL 成功時は GLOBAL を反映。
    # LASTLOAD_VERSION == -1 なので :131 以降は通らない。
    update(state, store, out, version)
    return True




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


def _chara_make_load_global(state: GameState, store: GlobalStore) -> None:
    """`CHARA_MAKE.ERB@CHARA_MAKE_MAIN`:9–21：LOADGLOBAL 後、メモリ上の GLOBAL から共通設定を読む（成否は見ない）。
    GLOBAL:5〜9・20〜23／GLOBALS:15〜17 由既有全域檔案讀入；不存在時為 0／空。
    S55 的互動選單位於 creation_menu，這裡保留直接完成的相容 helper。"""
    store.load()
    g, gs = store.mem.global_, store.mem.globals_
    for k, gk in ((5, 5), (6, 6), (7, 7), (820, 8), (821, 9), (822, 20), (823, 21), (824, 22), (825, 23)):
        state.flag[k] = g[gk]
    for k in (10, 11, 12):
        state.savestr[k] = gs[k + 5]


def chara_make_main_default(state: GameState, data: GameData, store: GlobalStore | None = None, *, ctx=None) -> None:
    """`CHARA_MAKE.ERB@CHARA_MAKE_MAIN`:5 で何も設定せず [1000] を押した場合の状態変化。"""
    _chara_make_load_global(state, store or GlobalStore())
    # :206–209 [1000] キャラメイクを完了する → CHARA_MAKE_FINALIZE（未設定のキャラは INITIALIZE でおまかせ生成）
    chara_make_finalize(state, data, ctx=ctx)


def chara_make_main_preset(state: GameState, data: GameData, preset: int, store: GlobalStore | None = None, *, ctx=None) -> None:
    """`CHARA_MAKE.ERB@CHARA_MAKE_MAIN`:5 で [200] → 初期セット → [1000] と進んだ場合の状態変化。"""
    from .initial_preset_data import PRESET_DATA
    if preset not in PRESET_DATA:raise ValueError(preset)
    _chara_make_load_global(state, store or GlobalStore())
    # :316–322 [200] → SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI:5–45 → [0] → [1]はい
    for _ in range(state.charanum - 1):
        state.del_chara(1)
        state.flag[8] -= 1
    shokiset_select(state, data, preset)
    shokiset_csvfix(state, data)  # SHOKISET.ERB:45
    # :206–209 [1000] キャラメイクを完了する
    chara_make_finalize(state, data, ctx=ctx)


def shokiset_select_0(state: GameState, data: GameData) -> None:
    """`SYSTEM/キャラメイキング関連/初期セット/0_特捜戦隊.ERB@SHOKISET_SELECT_0`:18–32。"""
    shokiset_select(state, data, 0)


def shokiset_select(state: GameState, data: GameData, preset: int) -> None:
    """各初期セット/*.ERB@SHOKISET_SELECT_n；固定字串與編號由原文抽取。"""
    from .initial_preset_data import PRESET_DATA
    if preset == 10:
        # 固定經驗初始化直接引用未成年模板；具體來源見wiki/era/initial-presets.md。
        raise NotImplementedError('SHOKISET_SELECT_10 固定經驗初始化涉及未成年模板，保留未實作')
    ids,title,call=PRESET_DATA[preset]
    state.flag[5]=1
    state.savestr[10]=title
    # 沒有寫FLAG:7／SAVESTR:12的套組保留上次設定，不能重設。
    if call is not None:
        state.flag[7]=1
        state.savestr[12]=call
    for no in ids:
        state.add_chara(data,no)
        state.flag[8]+=1
    shokiset_csvfix(state,data)


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


def chara_make_finalize(state: GameState, data: GameData, arg: int = 0, *, ctx=None) -> None:
    """`SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_FINALIZE`:221–487。"""
    level = data.index_of("ABL", "レベル")
    for sel in range(1, state.charanum):
        if arg != 0 and sel != arg:
            continue
        chara_make_initialize(state, data, sel, ctx=ctx)
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
        # 初期衣裝（:387–418）
        if c.cflag[40] == 0:
            c.cflag[40] = 100
        if c.cflag[40] == -1:
            c.cflag[40] = 0
        if talent(data, c, "変身能力") == 1 and c.cflag[41] == 0:
            c.cflag[41] = 200
        if c.cflag[41] == -1:
            c.cflag[41] = 0
        if c.cflag[42] == 0:
            from .action import Ctx
            from .battle.cloth import cloth_no_inner
            from ..text import NullNarrationService

            clothing_ctx = ctx or Ctx(state, data, TextOutput(), NullNarrationService())
            # :400–412 先讀目前形態；變身能力恰為1才再讀另一形態，最後固定回0。
            # CLOTH_NO_INNER原文讀TARGET衣裝，不在此將TARGET改成SELECT。
            no_inner = int(cloth_no_inner(clothing_ctx, sel, registers=True) != 0)
            if talent(data, c, "変身能力") == 1:
                c.cflag[1] = 1
                no_inner += int(cloth_no_inner(clothing_ctx, sel, registers=True) != 0)
                c.cflag[1] = 0
            if no_inner == 0:
                c.cflag[42] = 300
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
    # 原文:489自然落尾；reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    state.result[0] = 0


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


def chara_make_initialize(state: GameState, data: GameData, sel: int, *, ctx=None) -> None:
    """`CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_INITIALIZE`:5–211。"""
    c = state.charas[sel]
    initialize_race(state, data, sel, ctx=ctx)  # :8–72
    initialize_personality(state, data, sel, ctx=ctx)  # :74–164
    # :166 CALL CHARA_MAKE_BASE_PROFILE(SELECT)
    chara_make_base_profile(state, data, sel)
    # 変身名のロード（:166–209）
    if c.callname != "汎用キャラ" and talent(data, c, "変身能力") == 1:
        if c.cstr[0] == "":
            head = state.savestr[11]
            tail = c.callname
            if state.flag[820] > 0:
                from .genre_naming import genre_name_tail
                tail = genre_name_tail(state, data, sel, generic=False)
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
            chara_size_default(data, c, state.result)
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
