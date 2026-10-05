"""S60 已裁決的人工 25 歲模擬；驗工具契約，不另訂遊戲規則。"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.state import GameState
from tools.sim_adult import FixtureAgeError, assert_ages, adult_data, GuardedOutput


def test_fresh_definitions_preserve_mechanics_and_leave_source_data_untouched():
    original = load_game_data(default_csv_dir())
    snapshot = deepcopy(original.charas)
    data = adult_data(original)
    assert original.charas == snapshot
    assert data is not original
    assert set(data.charas) == set(original.charas)
    for no, definition in data.charas.items():
        before = original.charas[no]
        assert definition is not before
        assert definition.source is None
        assert definition.name == f"人工成年{no}"
        assert definition.base[40] == definition.base[41] == 25
        assert [definition.cstr[n] for n in (204, 205, 206)] == ['25'] * 3
        for field in ('abl', 'talent', 'exp', 'mark', 'juel', 'cflag', 'equip', 'relation'):
            assert getattr(definition, field) == getattr(before, field)
        assert definition.callname == ('汎用キャラ' if before.callname == '汎用キャラ' else f'成年{no}')


@pytest.mark.parametrize('store,slot,value', [('base',40,0), ('base',41,17), ('maxbase',40,26), ('maxbase',41,24)])
def test_guard_rejects_any_non_25_without_mutation(store, slot, value):
    data = adult_data(load_game_data(default_csv_dir()))
    state = GameState.new(data)
    state.add_chara(data, 0)
    assert_ages(state)
    getattr(state.charas[1], store)[slot] = value
    before = state.to_json()
    with pytest.raises(FixtureAgeError, match='fixture_age'):
        assert_ages(state)
    assert state.to_json() == before


def test_output_guard_stops_before_appending_invalid_state_text():
    data = adult_data(load_game_data(default_csv_dir()))
    state = GameState.new(data)
    out = GuardedOutput(lambda: state)
    out.printl('safe')
    state.charas[0].base[41] = 17
    with pytest.raises(FixtureAgeError):
        out.printl('must not append')
    assert [line.text for line in out.lines] == ['safe']


@pytest.mark.parametrize('ability,valid', [(0, True), (1, True)])
def test_no_transformation_age_sentinel_is_not_a_person_age(ability, valid):
    # CHARA_SIZE_UI.ERB@CHARA_SIZE_DEFAULT:2152–2153；
    # CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE:520、533–534 之後才授予能力。
    data = adult_data(load_game_data(default_csv_dir()))
    state = GameState.new(data)
    c = state.add_chara(data, 0)
    c.maxbase[41] = -1
    c.talent[data.index_of('TALENT', '変身能力')] = ability
    if valid:
        assert_ages(state)
    else:
        with pytest.raises(FixtureAgeError):
            assert_ages(state)


def test_foreground_workers_produce_identical_ordered_seed_results(tmp_path):
    results = []
    for workers in (1, 2):
        path = tmp_path / f'workers-{workers}.jsonl'
        completed = subprocess.run([
            sys.executable, '-X', 'utf8', str(Path(__file__).resolve().parents[1] / 'tools/sim_adult.py'),
            '--workers', str(workers), '--preset', 'default', '--seeds', '0-1',
            '--max-shop', '2', '--actions', '101,102,103,104,105,106,107,108',
            '--dump', str(path),
        ], capture_output=True, text=True, encoding='utf-8', timeout=90)
        assert completed.returncode == 0, completed.stderr
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        assert [row['seed'] for row in rows] == [0, 1]
        assert all(row['reason'] == '上限' and row['shops'] == 3 for row in rows)
        results.append(rows)
    assert results[0] == results[1]
