"""GameState／Character／存讀檔。

角色初期值 expected 由角色 CSV 原文手抄（`CSV/Chara/Chara300~400_Shokiset/` 各檔行號附註）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.state import (
    Character,
    FixedRng,
    GameRng,
    GameState,
    GlobalState,
    SaveFormatError,
    dump_save,
    load_save,
)
from eragvt.state.constants import ActionPlan, CharaState, GameMode, GameOption, MODE_OPTIONS
from eragvt.state.savefile import dump_global, load_global, load_global_file, save_to_file, load_from_file


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


def opening_state(data, seed=1):
    """S03 開局要用的狀態：MASTER + 特捜戦隊 301/302/303（初期セット/0_特捜戦隊.ERB:25–29）。"""
    st = GameState.new(data, rng=GameRng(seed))
    for no in (301, 302, 303):
        st.add_chara(data, no)
    return st


# --- 角色列表 ---------------------------------------------------------------


def test_new_state_has_only_master(data):
    st = GameState.new(data)
    assert st.charanum == 1
    assert st.master.no == 999 and st.master.name == "ダミー"  # Chara999ダミー.CSV:1–2
    assert st.master.base[0] == 1000  # :4 基礎,0,1000


def test_opening_party_order(data):
    st = opening_state(data)
    assert [c.no for c in st.charas] == [999, 301, 302, 303]
    assert [c.callname for c in st.charas[1:]] == ["紅葉", "桃香", "蒼美"]


@pytest.mark.parametrize(
    ("no", "attr", "index", "value"),
    [
        (302, "base", 0, 1200),  # Chara302花園 桃香.csv:5
        (302, "maxbase", 0, 1200),  # 基礎 → MAXBASE 也設定
        (302, "base", 1, 1400),  # :6
        (302, "talent", 17, 1),  # :16 素質,17,;楽天家
        (302, "talent", 182, 1),  # :20 中距離得意
        (302, "talent", 999, 1),  # :42 素質,固有キャラ,1
        (302, "talent", 16, 0),  # 未設定 → 0
        (302, "cflag", 41, 200),  # :26
        (302, "cstr", 10, "花園"),  # :4
        (302, "cstr", 11, ""),  # 未設定 → ""
        (303, "base", 0, 1500),  # Chara303海野 蒼美.csv:5
        (303, "maxbase", 1, 1300),  # :6
        (303, "talent", 16, 1),  # :16 真面目
        (303, "talent", 184, 1),  # :20 遠距離得意
        (303, "cstr", 10, "海野"),
        (301, "base", 0, 1400),  # Chara301赤羽 紅葉.csv:5
        (301, "cflag", 11, 120),
    ],
)
def test_add_chara_initial_values(data, no, attr, index, value):
    st = opening_state(data)
    chara = next(c for c in st.charas if c.no == no)
    assert getattr(chara, attr)[index] == value


def test_characters_are_independent_copies(data):
    st = GameState.new(data)
    a = st.add_chara(data, 301)
    b = st.add_chara(data, 301)
    a.base[0] = 1
    assert b.base[0] == 1400
    assert data.charas[301].base[0] == 1400  # CharaDef 不被改動


def test_del_and_swap_chara(data):
    st = opening_state(data)
    st.swap_chara(1, 3)
    assert [c.no for c in st.charas] == [999, 303, 302, 301]
    st.del_chara(2)
    assert [c.no for c in st.charas] == [999, 303, 301]
    with pytest.raises(ValueError):
        st.del_chara(0)
    with pytest.raises(KeyError):
        st.add_chara(data, 4242)


def test_target_chara(data):
    st = opening_state(data)
    st.target = 2
    assert st.target_chara.name == "花園 桃香"


# --- 常數 -------------------------------------------------------------------


def test_constants_match_source():
    # CFLAG.ERH:30–38 / :13–22
    assert ActionPlan.SORTIE == 101 and ActionPlan.FREE == 108
    assert CharaState.SAFE == 0 and CharaState.DEAD == 9
    # DIM.ERH:86 `0b00000001010` = SOLO → OPTION_normal(1) 與 OPTION_solo(3)
    solo = MODE_OPTIONS[GameMode.SOLO]
    assert solo >> GameOption.SOLO & 1 and solo >> GameOption.NORMAL & 1
    assert not solo >> GameOption.HARDCORE & 1


# --- 存讀檔 -----------------------------------------------------------------


def _mutated_state(data):
    st = opening_state(data)
    st.day, st.time, st.money, st.target = 3, 1, 5000, 1
    st.flag[852] = 5000  # 防衛力（オープニング処理.ERB:76）
    st.flag.set_bit(100, 2)
    st.item[100] = 1
    st.savestr[10] = "特装戦隊"
    st.shield[0] = 30
    st.mob_flag[(0, 3)] = 100
    st.charas[1].cflag[100] = ActionPlan.SORTIE  # IntEnum 直接寫入
    st.charas[1].cdflag[(1, 300)] = 5
    st.charas[2].tcvarn[12] = 4
    st.charas[3].talent[0] = -1
    st.temp.turn_limit = 50  # 不存
    return st


def test_intenum_stored_as_plain_int(data):
    st = _mutated_state(data)
    assert type(st.charas[1].cflag[100]) is int and st.charas[1].cflag[100] == 101


def test_roundtrip_bytes_identical(data):
    st = _mutated_state(data)
    raw1 = dump_save(st, comment="1日目 夜")
    st2, comment = load_save(raw1)
    raw2 = dump_save(st2, comment=comment)
    assert raw1 == raw2
    assert st2 == st
    assert comment == "1日目 夜"


def test_temp_and_rng_not_saved(data):
    st = _mutated_state(data)
    obj = json.loads(dump_save(st))
    assert "temp" not in obj["state"] and "rng" not in obj["state"]
    st2, _ = load_save(dump_save(st))
    assert st2.temp.turn_limit == 0


def test_save_header(data):
    obj = json.loads(dump_save(GameState.new(data)))
    assert obj["format"] == "eragvt-save" and obj["version"] == 1


def test_save_is_canonical_utf8_lf(data):
    raw = dump_save(_mutated_state(data))
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    assert "花園".encode() in raw  # ensure_ascii=False


@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b'{"format": "other", "version": 1}',
        b'{"format": "eragvt-save", "version": 0, "state": {}}',
        b'{"format": "eragvt-save", "version": 99, "state": {}}',
        b'{"format": "eragvt-save", "version": "1", "state": {}}',
    ],
)
def test_bad_saves_rejected(raw):
    with pytest.raises(SaveFormatError):
        load_save(raw)


def test_file_roundtrip(tmp_path: Path, data):
    st = _mutated_state(data)
    p = tmp_path / "saves" / "save00.json"
    save_to_file(p, st, "c")
    st2, c = load_from_file(p)
    assert st2 == st and c == "c"


def test_global_roundtrip(tmp_path: Path):
    g = GlobalState()
    g.global_[3] = 408  # GLOBAL:3 = GLOBALのバージョン（一覧:789）
    g.globals_[5] = "美少女戦士"
    g.mob_global[(2, 10)] = 50
    raw = dump_global(g)
    assert json.loads(raw)["format"] == "eragvt-global"
    assert load_global(raw) == g
    assert dump_global(load_global(raw)) == raw
    assert load_global_file(tmp_path / "none.json") == GlobalState()


def test_character_json_missing_fields_default():
    c = Character.from_json({"no": 7, "name": "x"})
    assert c.no == 7 and c.base[0] == 0 and c.cstr[1] == ""


# --- RNG --------------------------------------------------------------------


def test_rng_seeded_reproducible():
    a, b = GameRng(42), GameRng(42)
    assert [a.rand(100) for _ in range(10)] == [b.rand(100) for _ in range(10)]


def test_rng_range_and_errors():
    r = GameRng(0)
    assert all(0 <= r.rand(3) < 3 for _ in range(100))
    with pytest.raises(ValueError):
        r.rand(0)


def test_fixed_rng():
    r = FixedRng([5, 150, 99])
    assert r.rand(10) == 5
    assert r.rand(100) == 50
    assert r.percent(100) is True
    with pytest.raises(RuntimeError):
        r.rand(2)
