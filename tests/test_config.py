"""S24：コンフィグ（CONFIG_INIT・HEROINE_PRESET・CONFIG 画面・グローバルデータ）。

expected は ERB 原文から（路徑相對 `source/earGVP/ERB/`）：
- `SYSTEM/コンフィグ/CONFIG_初期設定.ERB@CONFIG_INIT`:4–61
- `SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG`:68–513
- `SYSTEM/コンフィグ/CONFIG_GLOBAL_MANIAC.ERB@CONFIG_F`／`CONFIG_GLOBAL_MOB.ERB@CONFIG_M`／`CONFIG_GLOBAL_TRANSFORM.ERB@CONFIG_T`
- `バージョン間互換処理.ERB@UPDATE_GLOBAL`:12–91、`@UPDATE`:95–128
- `ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST`:29–51・:291、`@MODE_SELECT`:360–402、`@HEROINE_PRESET`:617–759
引擎：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs@SaveGlobal`:2200–2252、`@LoadGlobal`:2256–2310、
`@ResetData`:1132–1141（GLOBAL は初期化しない）。
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import config
from eragvt.game.config import config_gen, config_init, update, update_global
from eragvt.game.opening import PRESET_TOKUSOU, event_first, event_first_gen
from eragvt.game.session import GameSession, Phase
from eragvt.state import GameRng, GameState, GlobalState
from eragvt.state.savefile import GameIdentity, GlobalStore, dump_global
from eragvt.text import TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


def _texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def _buttons(out: TextOutput, start: int = 0) -> list[int]:
    return [v for ln in out.lines[start:] for (_, v) in ln.buttons]


def _drive(gen, inputs):
    """ジェネレータに inputs を順に送る。終了したら (True, 戻り値)、入力待ちなら (False, None)。"""
    try:
        next(gen)
        for v in inputs:
            gen.send(v)
    except StopIteration as stop:
        return True, stop.value
    return False, None


FLAGS = (800, 801, 802, 803, 804, 805)


# --- CONFIG_INIT ------------------------------------------------------------------

@pytest.mark.parametrize("preset, expected", [
    # CONFIG_初期設定.ERB:17–29 基本セット
    (1, (0, 1, 1 + 2 + 4 + 8, 1 + 2 + 4 + 256, 1, 2)),
    # :32–44 淫獄セット
    (2, (0, 1 + 8 + 16, 1 + 2 + 4 + 8 + 16, 1 + 2 + 4 + 128 + 256, 1 + 2 + 4 + 16 + 32 + 64 + 128, 1 + 2 + 64)),
    # :47–59 クズ市民セット
    (3, (0, 1 + 8 + 16, 1 + 2 + 4 + 8 + 16 + 32, 1 + 2 + 4 + 128 + 256, 1 + 2 + 4 + 16 + 32 + 64 + 128 + 1024, 1 + 2 + 64)),
])
def test_config_init_presets(preset, expected):
    st = GameState()
    config_init(st, preset)
    assert tuple(st.flag[k] for k in FLAGS) == expected


def test_config_init_0_copies_global():
    """:8–15 CASE 0：FLAG:800 = 1、FLAG:801〜805 = GLOBAL:11〜15（メモリの値）。"""
    store = GlobalStore()
    for i, v in enumerate((7, 9, 11, 13, 17)):
        store.mem.global_[11 + i] = v
    st = GameState()
    st.flag[801] = 99
    config_init(st, 0, store)
    assert tuple(st.flag[k] for k in FLAGS) == (1, 7, 9, 11, 13, 17)
    st2 = GameState()
    config_init(st2, 0, GlobalStore())  # GLOBAL が空（初回起動）→ すべて 0
    assert tuple(st2.flag[k] for k in FLAGS) == (1, 0, 0, 0, 0, 0)


def test_config_init_unknown_case_does_nothing():
    st = GameState()
    st.flag[801] = 5
    config_init(st, 4)  # SELECTCASE に該当 CASE なし（CASEELSE もない）
    assert st.flag[801] == 5 and st.flag[800] == 0


# --- HEROINE_PRESET（event_first の入力）---------------------------------------------

@pytest.mark.parametrize("preset, expected", [
    (0, (1, 0, 0, 0, 0, 0)),  # 初回起動（GLOBAL なし）で [0] 引き継ぎ → GLOBAL:11〜15 = 0
    (1, (0, 1, 15, 263, 1, 2)),
    (2, (0, 25, 31, 391, 247, 67)),
    (3, (0, 25, 63, 391, 1271, 67)),
])
def test_event_first_heroine_preset(data, preset, expected):
    st = GameState.new(data, rng=GameRng(5))
    event_first(st, data, preset=PRESET_TOKUSOU, config_preset=preset)
    assert tuple(st.flag[k] for k in FLAGS) == expected
    # 初回起動：雑魚敵フィルタは 100（:36–43）、性嗜好フィルタ FLAG:850 は 0
    assert st.mob_flag[(0, 1)] == 100 and st.mob_flag[(9, 2)] == 100 and st.flag[850] == 0


def test_event_first_default_preset_unchanged(data):
    """既定（config_preset 省略）は [1] 基本セット＝S23 までの開局と同じ状態。"""
    a = GameState.new(data, rng=GameRng(9))
    event_first(a, data)
    b = GameState.new(data, rng=GameRng(9))
    event_first(b, data, config_preset=1)
    assert a == b
    assert tuple(a.flag[k] for k in FLAGS) == (0, 1, 15, 263, 1, 2)


def _start_heroine_preset(data, store=None, chara=1):
    st = GameState.new(data, rng=GameRng(3))
    out = TextOutput()
    store = store or GlobalStore()
    gen = event_first_gen(st, data, out, store)
    done, _ = _drive(gen, [chara])
    assert not done
    return st, out, store, gen


def test_heroine_preset_screen(data):
    st, out, _, gen = _start_heroine_preset(data)
    t = _texts(out)
    assert "◆ヒロインデータ確認" in t
    # :629–631 [{19+LOCAL}]●%NAME:LOCAL,20,LEFT%（初期セット：紅葉・桃香・蒼美）
    assert any(x.startswith("　[20]●") for x in t) and any(x.startswith("　[22]●") for x in t)
    assert " [30]ヒロインに相関関係を設定する" in t
    assert "　┣[2]「淫獄セット」　　で開始　：雑魚敵との戦闘やヒロイン悪堕ち等の追加オプションがONになります" in t
    assert {0, 1, 2, 3, 10, 20, 21, 22, 30}.issubset(_buttons(out))
    # :753–754 範囲外は再入力（表示なし）
    n = len(out.lines)
    gen.send(4)
    gen.send(-1)
    assert len(out.lines) == n
    with pytest.raises(StopIteration):
        gen.send(2)
    assert st.flag[802] == 31


def test_heroine_preset_relation_menu(data):
    _, out, _, gen = _start_heroine_preset(data)
    gen.send(30)
    assert "相関関係設定" in _texts(out)
    gen.send(99)
    assert "◆ヒロインデータ確認" in _texts(out)


def test_heroine_preset_10_config_mainmenu(data):
    """[10] → CONFIG("mainmenu")：[999]／[9999] は表示しない（:417–419）が入力は受け付ける（:429–436）。"""
    st, out, _, gen = _start_heroine_preset(data)
    start = len(out.lines)
    gen.send(10)
    assert 999 not in _buttons(out, start) and 9999 not in _buttons(out, start)
    assert "[100]ページ切り替え" in _texts(out)
    gen.send(61)  # FLAG:804 bit1 反転（このあと CONFIG_INIT で上書きされる）
    assert st.flag.get_bit(804, 1) == 1
    gen.send(999)  # 戻る → HEROINE_PRESET 再表示
    assert _texts(out).count("◆ヒロインデータ確認") == 2
    with pytest.raises(StopIteration):
        gen.send(1)
    assert st.flag[804] == 1  # CONFIG_INIT(1)


# --- MODE_SELECT の [100]／[200]（開局 2 択の画面）-------------------------------------

def test_mode_select_footer_and_title(data):
    st = GameState.new(data, rng=GameRng(3))
    out = TextOutput()
    gen = event_first_gen(st, data, out, GlobalStore())
    done, _ = _drive(gen, [])
    assert not done
    assert {0, 1, 100, 200, 300} == set(_buttons(out))
    done, value = _drive_send(gen, 100)
    assert done and value is False  # :82–85 RESETDATA → BEGIN TITLE


def _drive_send(gen, value):
    try:
        gen.send(value)
    except StopIteration as stop:
        return True, stop.value
    return False, None


def test_mode_select_200_global_config(data):
    """[200]（:393–402）：FLAG:801〜805 = GLOBAL:11〜15 → UPDATE_GLOBAL → CONFIG("mainmenu")。
    GLOBAL:3 = 0（空）なので UPDATE_GLOBAL の全分岐が走り、SAVEGLOBAL する（バージョン間互換処理.ERB:13–91）。"""
    st = GameState.new(data, rng=GameRng(3))
    out = TextOutput()
    store = GlobalStore()
    gen = event_first_gen(st, data, out, store)
    _drive(gen, [200])
    assert tuple(st.flag[k] for k in (801, 802, 803, 804, 805)) == (0, 0, 0, 0, 0)
    assert store.exists() and store.mem.global_[3] == 408
    assert (store.mem.global_[11], store.mem.global_[12], store.mem.global_[13], store.mem.global_[14]) == (4, 31, 88, 5)
    assert "Ｃ　Ｏ　Ｎ　Ｆ　Ｉ　Ｇ" in "".join(_texts(out))
    gen.send(999)  # 戻る → モード選択を再表示
    assert _texts(out)[-1].startswith("[100] タイトルに戻る")
    with pytest.raises(NotImplementedError, match="TUTORIAL"):
        gen.send(300)


# --- CONFIG 画面のビット切り替え ---------------------------------------------------------

def _base_state():
    st = GameState()
    config_init(st, 1)  # FLAG:800〜805 = 0, 1, 15, 263, 1, 2
    return st


@pytest.mark.parametrize("inputs, flag, expected", [
    ([0], 800, 1),  # :439–441 INVERTBIT FLAG:800, 0
    ([10], 801, 0),  # :476–478
    ([15], 801, 1 + 32),
    ([17], 801, 1 + 128),
    ([30], 802, 14),  # :480–484
    ([34], 802, 15 + 16),
    ([35], 802, 15 + 32),  # :485–488 クズ市民イベント ON のときだけ反転
    ([35, 33], 802, 7),  # [33] でクズ市民イベント OFF → bit5 も消える（:482–483）
    ([33, 35], 802, 7),  # OFF の間は [35] は無効
    ([36], 802, 15 + 64),  # :489–491
    ([50], 803, 262),  # :493–495
    ([58], 803, 7),
    ([60], 804, 0),  # :497–499
    ([61], 804, 3),
    ([71], 804, 1 + 2048),
    ([74], 805, 2 + 4),  # :501–504 bit2 反転・bit3 消去
    ([75], 805, 2 + 8),  # bit3 反転・bit2 消去
    ([74, 75], 805, 2 + 8),
    ([75, 74], 805, 2 + 4),
    ([74, 74], 805, 2),
    ([72], 805, 3),  # :506–508
    ([73], 805, 0),
    ([80], 805, 2 + 256),
    ([100, 54], 803, 263 + 16),  # ページ切り替えは状態を変えない
])
def test_config_toggle(data, inputs, flag, expected):
    st = _base_state()
    out = TextOutput()
    gen = config_gen(st, data, out, GlobalStore())
    done, _ = _drive(gen, inputs + [999])
    assert done
    assert st.flag[flag] == expected


def test_config_invalid_input_message(data):
    st = _base_state()
    out = TextOutput()
    gen = config_gen(st, data, out, GlobalStore())
    _drive(gen, [37])
    assert _texts(out)[-1] == "正しい値を入力してください"  # :509–512
    assert st.flag[802] == 15


def test_config_screen_pages(data):
    st = _base_state()
    out = TextOutput()
    gen = config_gen(st, data, out, GlobalStore())
    _drive(gen, [])
    t = _texts(out)
    assert "Ｃ　Ｏ　Ｎ　Ｆ　Ｉ　Ｇ　　　　　　　page(1/2)" in t
    assert "　[1000]性嗜好フィルタ" in t and "　[34]雑魚敵との戦闘" in t
    assert "[999]現在のセーブデータのみに適用して戻る　　[9999]グローバル設定に保存して戻る" in t
    assert not any("[16]" in x for x in t)  # FLAG:801 bit5 OFF → [16][17] は出ない（:148–160）
    gen.send(100)
    t = _texts(out)
    assert "Ｃ　Ｏ　Ｎ　Ｆ　Ｉ　Ｇ　　　　　　　page(2/2)" in t
    assert "　[61]▼ヒロイン悪堕ち機能を使用する" in t
    assert not any("[62]" in x for x in t)
    gen.send(61)
    t = _texts(out)
    assert "　[61]▲ヒロイン悪堕ち機能を使用する" in t and "　 ┣[62]ただし苗床化したヒロインは産む機械として取り込む" in t
    # 色：ON = 120,255,255、OFF = 105,105,105（:274–281）
    line = next(ln for ln in reversed(out.lines) if ln.text == "　[60]オトコの敗北時に女体化させる")
    assert line.parts[0].segments[0].color == "#78ffff"
    line = next(ln for ln in reversed(out.lines) if ln.text == "　[70]クズ市民による幽閉を許可する")
    assert line.parts[0].segments[0].color == "#696969"


def test_config_global_save_load(data):
    """[1] SAVE GLOBAL（:442–452）・[2] LOAD GLOBAL（:453–462）・[9999]（:430–436）。"""
    with tempfile.TemporaryDirectory() as tmp:
        store = GlobalStore.in_dir(Path(tmp), GameIdentity.from_data(data))
        st = _base_state()
        out = TextOutput()
        gen = config_gen(st, data, out, store)
        _drive(gen, [61, 1])
        assert "現在のグローバルコンフィグを保存しました。" in _texts(out)
        raw = json.loads((Path(tmp) / "global.json").read_text(encoding="utf-8"))
        assert raw["format"] == "eragvt-global" and raw["game_code"] == 891216222 and raw["game_version"] == 408
        assert raw["global"]["global"]["14"] == 3  # GLOBAL:14 = FLAG:804
        assert "3" not in raw["global"]["global"]  # GLOBAL:3 は 0 のまま（[1] は UPDATE_GLOBAL を呼ばない）
        # [2]：FLAG ← GLOBAL（3 = 1+2）→ UPDATE_GLOBAL（GLOBAL:3 = 0 → :21–31 で GLOBAL:11〜14 が 4/31/88/5 に）
        st.flag[804] = 1
        gen.send(2)
        assert st.flag[804] == 3 and st.flag[801] == 1
        assert store.mem.global_[14] == 5 and store.mem.global_[3] == 408
        gen.send(50)
        with pytest.raises(StopIteration):
            gen.send(9999)
        assert store.mem.global_[13] == 262
        reloaded = GlobalStore.in_dir(Path(tmp), GameIdentity.from_data(data))
        assert reloaded.load() and reloaded.mem == store.mem


# --- UPDATE_GLOBAL ---------------------------------------------------------------------

def test_update_global_from_zero():
    """GLOBAL:3 = 0：:13–91 の全分岐。"""
    st = GameState()
    store = GlobalStore()
    g = store.mem.global_
    g[9] = 5
    g[0] = g[1] = g[2] = 1
    g[150] = 7
    g[110] = 3
    g[20] = 8
    store.mem.globals_[18] = "宝石の名前"
    out = TextOutput()
    update_global(st, store, out, 408)
    assert g[9] == 0  # :13–16
    assert st.mob_flag[(0, 1)] == 100 and store.mem.mob_global[(0, 1)] == 100  # :17–20
    assert (g[0], g[1], g[2], g[10], g[11], g[12], g[13], g[14]) == (0, 0, 0, 0, 4, 31, 88, 5)  # :21–31
    # :32–36（bit 16・17）と :56–66（bit 7・8・9・11・12・19・20）の反転
    assert g[4] == sum(1 << b for b in (16, 17, 7, 8, 9, 11, 12, 19, 20))
    assert (g[15], g[16]) == (0, 0)  # :38–42
    assert (g[150], g[250], g[113], g[110]) == (0, 7, 3, 0)  # :44–54
    assert g[8] == 6 and store.mem.globals_[18] == ""  # :68–77（transnamegenre:5 = 宝石の名前）
    assert g[20] == 9  # :79–83
    assert g[3] == 408 and store.exists()  # :87–91 SAVEGLOBAL
    assert "【グローバル設定を最新バージョンにアップデートしました】" in _texts(out)


def test_update_global_current_version_noop():
    st = GameState()
    store = GlobalStore()
    store.mem.global_[3] = 408
    store.mem.global_[11] = 77
    out = TextOutput()
    update_global(st, store, out, 408)
    assert store.mem.global_[11] == 77 and not store.exists() and _texts(out) == []


# --- UPDATE（自動ロード）・GLOBAL 存讀往返 -----------------------------------------------

def _saved_global(data, g11_15=(1, 2, 3, 4, 5), g4=0, mob=None):
    store = GlobalStore(identity=GameIdentity.from_data(data))
    store.mem.global_[3] = 408
    for i, v in enumerate(g11_15):
        store.mem.global_[11 + i] = v
    store.mem.global_[4] = g4
    for k, v in (mob or {}).items():
        store.mem.mob_global[k] = v
    store.save()
    return store


@pytest.mark.parametrize("auto, expected", [(1, (1, 2, 3, 4, 5)), (0, (9, 9, 9, 9, 9))])
def test_update_applies_global(data, auto, expected):
    """:99–125：LOADGLOBAL 成功 → FLAG:800 bit0 なら FLAG:801〜805 = GLOBAL:11〜15。FLAG:850・MOB_FLAG は常に。
    存在しない雑魚番号は 0（:121–122）。"""
    store = _saved_global(data, g4=1 << 16, mob={(0, 1): 30, (9, 2): 0, (0, 50): 77})
    st = GameState()
    st.flag[800] = auto
    for k in range(801, 806):
        st.flag[k] = 9
    st.mob_flag[(1, 1)] = 100
    st.mob_flag[(0, 50)] = 5
    out = TextOutput()
    update(st, store, out, 408)
    assert tuple(st.flag[k] for k in range(801, 806)) == expected
    assert st.flag[850] == 1 << 16
    assert st.mob_flag[(0, 1)] == 30 and st.mob_flag[(1, 1)] == 0 and st.mob_flag[(9, 2)] == 0
    assert st.mob_flag[(0, 50)] == 0  # TENTACLE_MOB_50 は無い → 0


def test_update_without_global_changes_nothing(data):
    st = GameState()
    st.flag[801] = 9
    st.mob_flag[(0, 1)] = 100
    update(st, GlobalStore(), TextOutput(), 408)
    assert st.flag[801] == 9 and st.mob_flag[(0, 1)] == 100 and st.flag[850] == 0


def test_global_store_load_rules(data, tmp_path):
    ident = GameIdentity.from_data(data)
    store = GlobalStore.in_dir(tmp_path, ident)
    assert store.load() is False  # ファイルなし（LoadGlobal:2259–2260）
    store.mem.global_[5] = 1
    store.mem.globals_[15] = "主題"
    store.mem.mob_global[(3, 1)] = 40
    store.save()
    other = GlobalStore.in_dir(tmp_path, ident)
    other.mem.global_[99] = 123  # 読み込みで全置換（保存値の無い要素は 0：EraDataStream.cs:101–102）
    assert other.load() and other.mem == store.mem and other.mem.global_[99] == 0
    # 代碼違い → 失敗、メモリは変わらない（LoadGlobal:2283–2284）
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "global.json").write_bytes(dump_global(GlobalState(), GameIdentity(code=1, version=408)))
    s2 = GlobalStore.in_dir(bad, ident)
    s2.mem.global_[1] = 5
    assert s2.load() is False and s2.mem.global_[1] == 5
    (bad / "global.json").write_bytes(b"broken")
    assert s2.load() is False


def test_new_game_with_saved_global(data):
    """EVENTFIRST:29–32 LOADGLOBAL 成功 → UPDATE（MOB_FLAG = MOB_GLOBAL、FLAG:850 = GLOBAL:4）。
    [0] 引き継ぎなら FLAG:801〜805 = GLOBAL（CONFIG_INIT(0) と :291 UPDATE）。"""
    store = _saved_global(data, g11_15=(1, 31, 263, 3, 66), g4=1 << 6, mob={(0, 1): 20, (9, 2): 100})
    st = GameState.new(data, rng=GameRng(4))
    event_first(st, data, preset=PRESET_TOKUSOU, config_preset=0, store=store)
    assert tuple(st.flag[k] for k in FLAGS) == (1, 1, 31, 263, 3, 66)
    assert st.flag[850] == 1 << 6
    assert st.mob_flag[(0, 1)] == 20 and st.mob_flag[(0, 2)] == 0 and st.mob_flag[(9, 2)] == 100
    st2 = GameState.new(data, rng=GameRng(4))
    event_first(st2, data, preset=PRESET_TOKUSOU, config_preset=2, store=store)
    assert tuple(st2.flag[k] for k in FLAGS) == (0, 25, 31, 391, 247, 67)  # プリセットは FLAG:800 = 0 → 上書きしない
    assert st2.flag[850] == 1 << 6 and st2.mob_flag[(0, 1)] == 20


# --- CONFIG_F／CONFIG_M／CONFIG_T ----------------------------------------------------

def test_config_f_toggles_and_save(data):
    st = GameState()
    store = GlobalStore()
    out = TextOutput()
    gen = config.config_f_gen(st, out, store)
    _drive(gen, [])
    assert "[11]ふたなりの取得　　　　　　　　　【○】" in _texts(out)
    assert "[16]▲淫紋の取得　　　　　　　　　　【○】" in _texts(out)
    gen.send(16)  # INVERTBIT FLAG:850, 6（:191–198）
    assert st.flag.get_bit(850, 6) == 1
    assert "[16]▼淫紋の取得　　　　　　　　　　【×】" in _texts(out)
    assert not any(x.startswith("[17]") for x in _texts(out)[-30:])
    gen.send(11)  # bit1 ON（ふたなり ×）
    gen.send(22)  # bit12 ON → :195–196 で bit1 を消す（原文どおり）
    assert st.flag.get_bit(850, 12) == 1 and st.flag.get_bit(850, 1) == 0
    gen.send(21)  # bit11 ON → :193–194 で bit12 を消す
    assert st.flag.get_bit(850, 11) == 1 and st.flag.get_bit(850, 12) == 0
    gen.send(5)  # 範囲外 → 再入力
    with pytest.raises(StopIteration):
        gen.send(200)
    assert store.mem.global_[4] == st.flag[850] and store.exists()


def test_config_m(data):
    st = GameState()
    for n in config.MOB_NAMES:
        st.mob_flag[(n // 100, n % 100)] = 100
    store = GlobalStore()
    out = TextOutput()
    gen = config.config_m_gen(st, out, store)
    _drive(gen, [])
    # %種族:LOCAL,16,LEFT%（全角 2 として 16 桁に詰める：StrForm.cs@FormatPercent）
    assert "[0]無形" + " " * 12 + "　[10]0％　[20]100％" in _texts(out)
    gen.send(10)  # カテゴリ 0 を 0%（:148–157）
    assert [st.mob_flag[(0, j)] for j in (1, 2, 3)] == [0, 0, 0] and st.mob_flag[(1, 1)] == 100
    assert any(x.startswith("[0]無形") for x in _texts(out))
    line = next(ln for ln in reversed(out.lines) if ln.text.startswith("[0]無形"))
    assert line.parts[0].segments[0].color == "#808080"  # 平均 0 → Gray（:44–46）
    gen.send(4)  # 種族:4 は選べない → 再入力（:56、:199–200）
    gen.send(9)  # カテゴリ 9（天使・悪魔系）
    assert any("セラプー" in x and x.startswith("[  1] ") and x.endswith("　100％") for x in _texts(out))
    assert " ---" in _texts(out)
    st.tflag[17] = 3
    gen.send(1)  # セラプー → 出現率入力（GETNAME で TFLAG:17 = -1：TENTACLE_MOB_901:11–12）
    assert st.tflag[17] == -1
    assert _texts(out)[-1] == "セラプーの出現率を入力してください （  0 - 100 ％）"
    gen.send(101)  # 0〜100 以外 → 再入力
    gen.send(40)
    assert st.mob_flag[(9, 1)] == 40
    gen.send(202)
    assert any("PAGE(2/5)" in x for x in _texts(out))
    gen.send(200)  # カテゴリ選択に戻る
    with pytest.raises(StopIteration):
        gen.send(200)  # 保存（:191–198）
    assert store.mem.mob_global[(9, 1)] == 40 and store.mem.mob_global[(0, 1)] == 0
    assert store.mem.mob_global[(1, 1)] == 100


def test_config_t(data):
    st = GameState()
    store = GlobalStore()
    store.mem.global_[52] = 2
    out = TextOutput()
    gen = config.config_t_gen(st, out, store)
    _drive(gen, [])
    assert "　[11]通常の変身の場合　　　　　　    【選択肢を表示する】" in _texts(out)
    assert "　[12]変身時に女体化する場合          【常に変身しない】" in _texts(out)
    _drive_send(gen, 11)  # 0 → 1
    _drive_send(gen, 12)  # 2 → 0
    _drive_send(gen, 19)  # 0 → 1
    _drive_send(gen, 19)  # 1 → 2
    assert "　[11]通常の変身の場合　　　　　　    【常に変身する】" in _texts(out)
    assert store.mem.global_[51] == 0  # [200] まで保存しない
    done, _ = _drive_send(gen, 200)
    assert done
    assert [store.mem.global_[51 + i] for i in range(9)] == [1, 0, 0, 0, 0, 0, 0, 0, 2]


# --- Session／Web 統合 -----------------------------------------------------------------

def test_session_inyoku_set_and_shop_config(data):
    """新遊戲 → 淫獄セット → SHOP；[700] コンフィグで 1 項目切り替え → [999] で SHOP に戻る。"""
    from eragvt.web import create_app

    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(data, Path(tmp), rng_factory=lambda: GameRng(5), now=lambda: datetime(2026, 10, 2))
        c = TestClient(app)
        c.post("/api/input", json={"value": 0})
        c.post("/api/input", json={"value": 0})  # おまかせ
        s = c.post("/api/input", json={"value": 2}).json()  # [2]「淫獄セット」
        assert s["phase"] == "shop"
        st = app.state.session.state
        assert tuple(st.flag[k] for k in FLAGS) == (0, 25, 31, 391, 247, 67)
        assert 700 in [p["button"] for ln in s["lines"] for p in ln["parts"] if p["button"] is not None]
        s = c.post("/api/input", json={"value": 700}).json()
        assert s["phase"] == "turn"
        texts = ["".join(x["text"] for p in ln["parts"] for x in p["segments"]) for ln in s["lines"]]
        assert any("page(1/2)" in t for t in texts)
        c.post("/api/input", json={"value": 34})  # 雑魚敵との戦闘 OFF
        s = c.post("/api/input", json={"value": 999}).json()
        assert s["phase"] == "shop"
        assert app.state.session.state.flag[802] == 15
        assert not (Path(tmp) / "global.json").exists()  # [999] は GLOBAL に保存しない


def test_session_global_autoload_on_load(data):
    """FLAG:800 bit0 のセーブをロード → EVENTLOAD:7 UPDATE で GLOBAL:11〜15 を反映（:105–113）。

    原作どおりの癖：初回起動のまま CONFIG [9999] で保存すると GLOBAL:3（グローバルのバージョン）が 0 のまま
    （UPDATE_GLOBAL を一度も通っていない）→ 次の UPDATE で UPDATE_GLOBAL:21–31 が走り、GLOBAL:11〜15 が
    4／31／88／5／0（:27–30、:40）に上書きされてから FLAG に写される。"""
    with tempfile.TemporaryDirectory() as tmp:
        s = GameSession(data, Path(tmp), rng=GameRng(2), now=lambda: datetime(2026, 10, 2))
        s.input(0)
        s.input(1)
        s.input(0)  # [0] グローバルコンフィグを引き継いで開始（初回起動 → 全 0）
        assert s.phase == Phase.SHOP
        assert tuple(s.state.flag[k] for k in FLAGS) == (1, 0, 0, 0, 0, 0)
        s.input(200)
        s.input(3)  # 3 番にセーブ
        s.input(700)
        s.input(13)  # FLAG:801 bit3
        s.input(9999)  # GLOBAL に保存して戻る
        assert s.phase == Phase.SHOP and s.globals.mem.global_[11] == 8
        assert "3" not in json.loads((Path(tmp) / "global.json").read_text(encoding="utf-8"))["global"]["global"]
        s.input(300)
        s.input(3)  # ロード → UPDATE：UPDATE_GLOBAL（GLOBAL:3 = 0）→ FLAG:801〜805 = GLOBAL:11〜15
        assert s.phase == Phase.SHOP
        assert tuple(s.state.flag[k] for k in range(801, 806)) == (4, 31, 88, 5, 0)
        assert s.globals.mem.global_[3] == 408
        # 2 回目からは GLOBAL:3 = 408 なので保存した値がそのまま入る
        s.input(700)
        s.input(13)  # 4 → 12
        s.input(9999)
        s.input(300)
        s.input(3)
        assert s.state.flag[801] == 12
        # 別セッション（プロセス再起動相当）でも global.json から読む
        s2 = GameSession(data, Path(tmp), rng=GameRng(2))
        s2.input(1)
        s2.input(3)
        assert s2.state.flag[801] == 12


def test_session_mode_select_back_to_title(data):
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(2))
    s.input(0)
    assert s.phase == Phase.NEW_GAME
    s.input(100)
    assert s.phase == Phase.TITLE and s.state is None
    s.input(0)
    s.input(0)
    s.input(1)
    assert s.phase == Phase.SHOP
