"""S60：全新人工 25 歲資料的獨立模擬基線，重用 sim 的策略與事件計數。

使用者已裁決的驗收資料替代；不修改產品、來源 CSV、既存 Character 或年齡規則。
新定義沿用各編號的數值玩法設定，使用人工姓名；生成前指定 BASE40/41 與
CSTR204–206。原作年齡指定依據：CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_AGE_SETTING:
1408–1444；既有查證見 docs/sessions/S60c-editor-resume.md。
汎用キャラ是原作分派 key，保留；其他呼び名換成人工名稱，保留其非汎用路徑。
模板其餘設定、catalog、初始化／完成流程、RNG 與 sim 輸入策略均保留。
出生、事件、變身若產生非 25 歲資料，明確 fixture 停止，絕不事後改齡。
只輸出數值、停止原因及函式事件計數；不輸出遊戲畫面或敘事。
"""
from __future__ import annotations

import argparse
import copy
import json
import multiprocessing
import sys
import tempfile
from collections import Counter
from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import sim
from eragvt.data.csv_loader import CharaDef
from eragvt.text import TextOutput

FIXTURE = 'fresh-adult-25-v1'


class FixtureAgeError(RuntimeError):
    """驗收資料條件不符；與產品未實作分開記錄。"""


def adult_data(original):
    """從設定建立新人工定義；不讀取、轉換或改齡任何既存角色／存檔。"""
    data = copy.copy(original)
    data.charas = {}
    for no, config in original.charas.items():
        values = {f.name: copy.deepcopy(getattr(config, f.name)) for f in fields(CharaDef)}
        values.update(name=f'人工成年{no}', callname=(
            '汎用キャラ' if config.callname == '汎用キャラ' else f'成年{no}'),
            nickname='', mastername='', source=None, warnings=[])
        values['base'].update({40: 25, 41: 25})
        values['cstr'].update({204: '25', 205: '25', 206: '25'})
        data.charas[no] = CharaDef(**values)
    return data


def assert_ages(state):
    """包含管理員與非 TARGET 角色；只讀檢查實／外見年齡兩組儲存格。"""
    if state is None:
        return
    for index, c in enumerate(state.charas):
        ages = [c.base[40], c.base[41], c.maxbase[40], c.maxbase[41]]
        # CHARA_SIZE_UI.ERB@CHARA_SIZE_DEFAULT:2152–2153：無變身能力時
        # MAXBASE:年齢=-1 表示未設定另一形態年齡，不是角色年齡。
        # CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE:520、533–534 在其後
        # 才賦予人間變身能力，因此不能用最終 TALENT 排除此哨兵。
        alternate_valid = ages[3] in (25, -1)
        if ages[:3] != [25, 25, 25] or not alternate_valid:
            raise FixtureAgeError(f'fixture_age index={index} no={c.no} ages={ages}')


class GuardedOutput(TextOutput):
    """任何角色的年齡違反條件時，阻止新文字／按鈕加入畫面。"""
    def __init__(self, state):
        super().__init__()
        self._fixture_state = state

    def print(self, text):
        assert_ages(self._fixture_state())
        return super().print(text)

    def print_plain(self, text):
        assert_ages(self._fixture_state())
        return super().print_plain(text)

    def button(self, label, value):
        assert_ages(self._fixture_state())
        return super().button(label, value)

    def html_print(self, html):
        assert_ages(self._fixture_state())
        return super().html_print(html)


class AdultSession(sim.GameSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        guarded = GuardedOutput(lambda: self.state)
        guarded.__dict__.update(self.out.__dict__)
        self.out = guarded

    def input(self, value):
        assert_ages(self.state)
        super().input(value)
        assert_ages(self.state)


class AdultCatalog(sim.CatalogNarrationService):
    def _interp(self, ctx, hooks=None, inputs=None):
        assert_ages(ctx.state)
        interp = super()._interp(ctx, hooks, inputs)
        original_call = interp.call

        def guarded_call(*args, **kwargs):
            assert_ages(ctx.state)
            result = original_call(*args, **kwargs)
            assert_ages(ctx.state)
            return result

        interp.call = guarded_call
        return interp


def run_one(data, narration, seed, preset, max_shop, max_steps, save_dir, actions):
    with patch.object(sim, 'GameSession', AdultSession):
        try:
            result = sim.run_one(data, narration, seed, preset, max_shop, max_steps,
                                 save_dir, actions=actions)
        except FixtureAgeError as exc:  # 開局發生；sim 迴圈尚未開始。
            result = dict(seed=seed, reason=str(exc), shops=0, defeated_at=None, gameover_at=None)
    result['fixture'] = FIXTURE
    result['fixture_stop'] = 'fixture_age' in result['reason']
    if result['fixture_stop']:
        result['reason'] = 'fixture_age' + result['reason'].split('fixture_age', 1)[1]
    return result


def _run_seed(task):
    """每個程序只跑一個 seed；模組計數包裝、catalog 快取與 RNG 不跨局。"""
    seed, preset, max_shop, max_steps, actions = task
    counts = sim.install_event_counters()
    data = adult_data(sim.load_game_data(sim.default_csv_dir()))
    narration = AdultCatalog(sim.default_csv_dir().parent / 'ERB', data)
    with tempfile.TemporaryDirectory(prefix='eragvt-adult-sim-') as tmp:
        result = run_one(data, narration, seed, preset, max_shop,
                         max_steps, Path(tmp), actions)
    for failure in narration.failures:
        counts[f'catalog 実行時失敗 {failure[:60]}'] += 1
    result['events'] = dict(counts)
    result['catalog_failures'] = len(narration.failures)
    result['preset'] = preset
    result['parameters'] = dict(max_shop=max_shop, max_steps=max_steps,
                                actions=list(actions), config_preset=1)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preset', choices=('default', 'tokusou'), default='default')
    parser.add_argument('--seeds', default='0-249')
    parser.add_argument('--max-shop', type=int, default=200)
    parser.add_argument('--max-steps', type=int, default=100000)
    parser.add_argument('--actions', default='101,102,103,104,105,106,107,108')
    parser.add_argument('--workers', type=int, default=1,
                        help='同一前景批次的程序數，每個程序只執行一局，結果按 seed 輸入順序輸出')
    parser.add_argument('--dump', required=True)
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error('--workers 必須至少為 1')
    actions = tuple(int(n) for n in args.actions.split(','))
    results = []
    tasks = [(seed, args.preset, args.max_shop, args.max_steps, actions)
             for seed in sim._parse_seeds(args.seeds)]
    # spawn 避免繼承父程序已安裝的計數包裝；每局退出，沒有跨 seed 全域殘值。
    # imap 保持輸入順序，主程序前景等待整批；中止／例外時 context 關閉所有 worker。
    with multiprocessing.get_context('spawn').Pool(args.workers, maxtasksperchild=1) as pool:
        with open(args.dump, 'w', encoding='utf-8', newline='\n') as output:
            for result in pool.imap(_run_seed, tasks, chunksize=1):
                output.write(json.dumps(result, ensure_ascii=False) + '\n')
                output.flush()
                results.append(result)
                print(f"seed={result['seed']} shops={result['shops']} reason={result['reason']} "
                      f"catalog_failures={result['catalog_failures']}", flush=True)
    print(json.dumps(dict(fixture=FIXTURE, preset=args.preset, games=len(results),
        stops=dict(Counter(r['reason'] for r in results)),
        fixture_stops=sum(r['fixture_stop'] for r in results),
        catalog_failures=sum(r['catalog_failures'] for r in results)), ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
