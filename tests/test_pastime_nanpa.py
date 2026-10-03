"""S28c2：自由行動中イベントの本編（ナンパ・酒ナンパ・痴漢）＋ catalog の INPUT／入れ子 GOTO／run_event_gen。

expected は ERB 原文から推導（路徑相對 `source/earGVP/ERB/ゲーム内_イベント発生/自由行動中イベント/`；行號は註解）。
開局（特装戦隊）：[1] 紅葉（女性、学生 0、処女 1、淫乱 0、従順 0、巻き込まれ体質・人外の美貌・嬲られ体質 0）。
亂數：`ZeroRng`（RAND:n は常に 0）／`MaxRng`（常に n-1）で ERB の分岐を一意に決める。
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import pastime as pt, pastime_nanpa as pn, shop
from eragvt.game.action import Ctx
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import GameSession, Phase
from eragvt.narration.extract import ExtractContext, parse_function, read_logical_lines
from eragvt.narration.hooks import HOOK_CALLS, NANPA_HOOK_LINES
from eragvt.narration.runtime import Env, Frame, Interp
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"
DIR = ERB / "ゲーム内_イベント発生" / "自由行動中イベント"
FUNCS = (
    "MESSAGE_PASTIME_NANPA", "PASTIME_NANPA_DATE", "PASTIME_NANPA_TAKEOUT", "PASTIME_NANPA_RAPE",
    "MESSAGE_PASTIME_SAKE_NANPA", "PASTIME_SAKE_NANPA_DATE", "PASTIME_SAKE_NANPA_TAKEOUT", "PASTIME_SAKE_NANPA_RAPE",
    "PASTIME_SAKE_NANPA_DEISUI_RAPE", "MESSAGE_PASTIME_CHIKAN", "PASTIME_CHIKAN_TAKEOUT",
)


class ZeroRng(GameRng):
    def __init__(self) -> None:
        super().__init__(0)

    def rand(self, n: int) -> int:
        return 0


class MaxRng(GameRng):
    def __init__(self) -> None:
        super().__init__(0)

    def rand(self, n: int) -> int:
        return n - 1


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def svc(data):
    return CatalogNarrationService(ERB, data)


@pytest.fixture
def ctx(data, svc):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    c = Ctx(s, data, TextOutput(), svc)
    s.target = 1
    return c


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def drive(gen, inputs=()):
    """入力を順に送る。戻り値（StopIteration.value）と yield 回数。足りなければ 0 を送る。"""
    inputs = list(inputs)
    n = 0
    try:
        next(gen)
        while True:
            n += 1
            gen.send(inputs.pop(0) if inputs else 0)
    except StopIteration as stop:
        return stop.value, n


def T(data, n):
    return data.index_of("TALENT", n)


def E(data, n):
    return data.index_of("EXP", n)


# --- hook 表・catalog での実行可否 ------------------------------------------------------------------


def _erb_lines(fname: str) -> list[str]:
    return (DIR / fname).read_text(encoding="utf-8-sig").split("\n")


def test_nanpa_hook_table_matches_erb(svc):
    """NANPA_HOOK_LINES の原文が ERB の該当行と一致し、本編 11 関数がすべて catalog で実行可能（＝表外の非 LOCAL 代入・
    未移植 CALL が無い）。CALL の hook 先は HOOK_CALLS にある。"""
    files = {f: _erb_lines(f) for f in ("PASTIME_ナンパ.ERB", "PASTIME_酒ナンパ.ERB", "PASTIME_痴漢.ERB")}
    owner = {}
    for f, lines in files.items():
        for i, ln in enumerate(lines, 1):
            m = re.match(r"^@([^,(\s]+)", ln)
            if m:
                owner[(f, i)] = m.group(1).upper()
    for (func, line), (text, _) in NANPA_HOOK_LINES.items():
        hits = [f for f, lines in files.items() if line <= len(lines) and lines[line - 1].strip() == text]
        assert hits, (func, line, text)
        f = hits[0]
        start = max(i for (ff, i) in owner if ff == f and i < line)
        assert owner[(f, start)] == func
        if text.startswith("CALL "):
            callee = re.match(r"CALL ([^,(\s]+)", text).group(1).upper()
            assert callee in HOOK_CALLS
    for name in FUNCS:
        assert svc.catalog.unsupported_reason(name) is None, name
    assert sum(len(svc.catalog.get(n).hooks) for n in FUNCS) == len(NANPA_HOOK_LINES) == 72


# --- catalog の拡張：INPUT（整数）・入れ子の $ラベルへの GOTO ------------------------------------------


def _fd(src: str):
    ectx = ExtractContext({}, {}, lambda n: False)
    return parse_function(ectx, "t.ERB", read_logical_lines(src.encode("utf-8")))


def test_input_and_nested_goto(ctx, svc):
    """INPUT → RESULT:0（Process.cs@InputInteger:249–252）。IF の中の $ラベルへの GOTO は「ラベル以降 → ENDIF の次」
    （ELSEIF／ELSE は ENDIF へ飛ぶだけ：Instraction.Child.cs:1805–1832）。"""
    fd = _fd(
        "@F\nPRINTL 前\nIF 1\n\tPRINTL 枝\n\t$LOOP\n\tINPUT\n\tIF RESULT == 9\n\t\tGOTO LOOP\n\tELSE\n"
        "\t\tPRINTFORML 入力{RESULT}\n\tENDIF\nELSE\n\tPRINTL 別\nENDIF\nPRINTL 後\n"
    )
    assert not fd.unsupported
    feed = iter([9, 9, 4])
    env = Env(ctx.state, ctx.data, ctx.out, {}, {}, ctx)
    env.input_fn = lambda y: next(feed)
    it = Interp(svc.catalog, env)
    it._exec_body(fd, Frame(fd, "F"))
    assert texts(ctx.out) == ["前", "枝", "入力4", "後"]
    assert ctx.state.result[0] == 4


def test_goto_into_loop_is_unsupported():
    from eragvt.narration.runtime_support import unsupported_reasons_static

    fd = _fd("@F\nFOR LOCAL, 0, 2\n\t$L\n\tPRINTL a\nNEXT\nGOTO L\n")
    assert any("GOTO 先" in r for _, r in unsupported_reasons_static(fd, None))


def test_event_gen_closed_midway(ctx):
    """run_event_gen を途中で閉じてもスレッドが残らない（_Abort で巻き戻す）。"""
    import threading

    gen = pn.message_pastime_nanpa(ctx, 0)
    next(gen)
    gen.close()
    assert not [t for t in threading.enumerate() if t.name.startswith("erb-event-")]


def test_null_narration_stops(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    c = Ctx(s, data, TextOutput(), NullNarrationService())
    s.target = 1
    with pytest.raises(NotImplementedError, match="MESSAGE_PASTIME_NANPA"):
        drive(pn.message_pastime_nanpa(c, 0))


# --- ナンパ（PASTIME_ナンパ.ERB@MESSAGE_PASTIME_NANPA） ------------------------------------------------


def test_nanpa_ignore(ctx, data):
    """MaxRng：:94 誘い内容 RAND:5 = 4（写真）、:144–172 RAND:k == 0 がすべて偽 → 知らない相手。[3]無視する → :584
    `RAND:100 < 5`（99）偽 → 諦めて去る。状態変化なし（:620 CFLAG:270 は DATE のみ）。不正値 7 は :599 GOTO で再入力（2 回 yield）。"""
    ctx.state.rng = MaxRng()
    c = ctx.state.target_chara
    ret, n = drive(pn.message_pastime_nanpa(ctx, 0), [7, 3])
    tx = texts(ctx.out)
    assert n == 2 and ret is None
    assert "紅葉はふと知らない相手に声を掛けられた。" in tx
    assert "写真を撮らせてくれないかと誘われているところを見ると、" in tx
    assert "これが噂に聞くナンパという奴かもしれない。" in tx
    assert "ナンパしてきた男はニヤニヤとした視線を紅葉のカラダに送っている。" in tx
    assert "[1]やんわりと断る（交渉失敗率45％）" in tx  # :474 ABL:従順 0 * 10 + 45
    assert tx.count("[0]着いていく") == 1
    assert "知らない相手は諦めてボヤきながら去っていった・・・" in tx
    assert c.cflag[270] == 0 and c.cflag[320] == 0


def test_nanpa_ignore_drugged_rape(ctx, data):
    """ZeroRng：:94 誘い内容 0（食事）、:144 RAND:10 == 0 → ユーチューバー。[3] → :584 `RAND:100 < 5` → PASTIME_NANPA_RAPE
    （ARG:1 省略 = 0）：:3039 CFLAG:270 = -1、RAPECOUNT = CFLAG:320 = 0 → :3053、CONFIG_CHECK_EVENT_F(5) == 0 →
    :3096 `RAPECOUNT == 0` の手コキ・フェラ → :3170 処女 → :3174–3176 処女喪失（TALENT:処女 = -1、CFLAG:206 = 11）・NAKADASHI 1 →
    :3246 CALC_GANGBANG("ナンパ") の :96–100 で CFLAG:320 += 1（:38 `TALENT:処女 == 1` はもう偽）。"""
    ctx.state.rng = ZeroRng()
    c = ctx.state.target_chara
    drive(pn.message_pastime_nanpa(ctx, 0), [3])
    tx = texts(ctx.out)
    assert "一緒に食事でもどうかと誘われているところを見ると、" in tx
    assert "ナンパしてきた男は動画サイトで人気のユーチューバーだと名乗っている。" in tx
    assert "紅葉が気が付くと、周りを複数の男に囲まれているようだ。" in tx
    assert "両手でそれぞれペニスを握り、口にもペニスを咥える紅葉。" in tx
    assert "処女喪失" in tx
    assert c.cflag[270] == -1 and c.cflag[320] == 1
    assert c.talent[T(data, "処女")] == -1 and c.cflag[206] == 11


def test_nanpa_follow_takeout_condom(ctx, data):
    """GameRng(22)：[0]着いていく → DATE（:620 CFLAG:270 = -1）→ [0] → TAKEOUT（生放送主・カラオケボックス）→ :2318 [0]断固拒否
    （EXP:10 = 0 ≤ 50 → :2322）→ NAMAHAME -1 → 処女 → :2484–2487 処女喪失（CFLAG:206 = 8、TALENT:処女 = -1）→ COMMON_PRISON_EXP
    で Ｖ経験 等。避妊したので AFTER_PILL／妊娠判定なし（NAKADASHI 0）。"""
    ctx.state.rng = GameRng(22)
    c = ctx.state.target_chara
    ret, n = drive(pn.message_pastime_nanpa(ctx, 0), [0, 0, 0])
    tx = texts(ctx.out)
    assert n == 3
    assert "有無を言わさぬ雰囲気で生放送主にコンドームを着けさせた…" in tx
    assert "処女喪失" in tx
    assert c.cflag[270] == -1 and c.cflag[206] == 8 and c.talent[T(data, "処女")] == -1
    assert c.exp[E(data, "Ｖ経験")] == 3 and "Ｖ経験：＋3" in tx


# --- 酒ナンパ（PASTIME_酒ナンパ.ERB@MESSAGE_PASTIME_SAKE_NANPA） ---------------------------------------


def test_sake_nanpa_refuse(ctx):
    """MaxRng：紅葉は 実年齢・年齢 < 20 かつ 学生 0 → :126 ELSE（知らない相手）。[2]はっきり断る → :235 `RAND:100 < 15`（99）偽
    → :246–248。"""
    ctx.state.rng = MaxRng()
    ret, n = drive(pn.message_pastime_sake_nanpa(ctx, 0), [2])
    tx = texts(ctx.out)
    assert n == 1
    assert "[2]はっきり断る　（交渉失敗率15％）" in tx
    assert "知らない相手は諦めてボヤきながら去っていった・・・" in tx


# --- 痴漢（PASTIME_痴漢.ERB@MESSAGE_PASTIME_CHIKAN） ------------------------------------------------


def test_chikan_no_takeout_group(ctx, data):
    """MaxRng：:1056 `RAND:100 < TAKEOUT`（99、TAKEOUT ≤ 19+…）偽、ARG:2（NABURARE）1・淫乱 0 → :1127 の集団痴漢：EXP:絶頂経験 +3・
    露出快楽経験 +3。:1051／:1053 痴漢された回数 CFLAG:325 += 1。RETURN 0。"""
    ctx.state.rng = MaxRng()
    c = ctx.state.target_chara
    ret, n = drive(pn.message_pastime_chikan(ctx, -1, 1, 1, "脂ぎった中年オヤジ"))
    tx = texts(ctx.out)
    assert ret == 0 and n == 0
    assert "紅葉は身動きも取れず、痴漢集団の絶え間ない責めに翻弄されていた。" in tx
    assert c.exp[E(data, "絶頂経験")] == 3 and c.exp[E(data, "露出快楽経験")] == 3
    assert c.cflag[325] == 1 and c.cflag[356] == 0


def test_chikan_alone_released(ctx, data):
    """MaxRng・NABURARE 0 → :1149 ELSE：淫乱 0、性耐性 198 ≥ 10 → :1170 PRINTFORM ＋ :1183（同じ行）。自慰経験なし。"""
    ctx.state.rng = MaxRng()
    c = ctx.state.target_chara
    before = c.exp[E(data, "自慰経験")]
    ret, _ = drive(pn.message_pastime_chikan(ctx, -1, 0, 0, "軽薄そうな男"))
    assert ret == 0
    assert "紅葉は駅に着くなり駆けるように電車を降りていった…" in texts(ctx.out)
    assert c.exp[E(data, "自慰経験")] == before and c.cflag[325] == 1


def test_chikan_takeout(ctx, data):
    """ZeroRng：:1056 `RAND:100 < TAKEOUT`（0 < 10+…）→ お持ち帰り → PASTIME_CHIKAN_TAKEOUT → :1710／:1712 CFLAG:327 += 1、
    :1736 `RAND:100 < 30` → CFLAG:825 += 1、RETURN 1 → 本編 :1097 RETURN 1。PASTIME_CHIKAN:458 も RETURN 1。"""
    ctx.state.rng = ZeroRng()
    c = ctx.state.target_chara
    ret, _ = drive(pn.message_pastime_chikan(ctx, -1, 1, 1, "脂ぎった中年オヤジ"))
    assert ret == 1
    assert c.cflag[325] == 1 and c.cflag[327] == 1 and c.cflag[825] == 1


def test_pastime_chikan_returns_1_after_takeout(ctx, monkeypatch):
    """PASTIME_CHIKAN:455–459：本編が RESULT > 0（持ち帰り）なら RETURN 1（:462–465 の DOT_AFTER を出さない）。"""

    def fake(ctx, *a):
        ctx.state.result[0] = 1
        return 1
        yield  # pragma: no cover

    monkeypatch.setattr(pt, "message_pastime_chikan", fake)
    from eragvt.state import FixedRng

    ctx.state.rng = FixedRng([60, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0])
    ret, _ = drive(pt.pastime_chikan(ctx, -1), [1])
    assert ret == 1 and ctx.state.result[0] == 1


# --- 整合：SHOP → 自由行動（街）→ ナンパ本編 → TURNEND → SHOP --------------------------------------------


def test_shop_pastime_nanpa_turnend(data, monkeypatch):
    monkeypatch.setattr(pt, "pastime_nanpa", lambda ctx: (ctx.state.result.__setitem__(0, 1), 1)[1])
    monkeypatch.setattr(pt, "pastime_sake_nanpa", lambda ctx: 0)
    with tempfile.TemporaryDirectory() as tmp:
        s = GameSession(data, Path(tmp), rng=GameRng(7), narration=CatalogNarrationService(ERB, data))
        s.input(0)
        s.input(1)  # 初期セット『特装戦隊』
        s.input(1)  # 基本セット
        assert s.phase == Phase.SHOP
        st = s.state
        day = st.day[0]
        st.charas[1].cflag[113] = 8  # スケジュール：街：公園（RESULT 5〜8 → 街(RESULT-5)：ACTION_PASTIME:29–132）
        for i, p in {1: 108, 2: 103, 3: 103}.items():
            s.input(i)
            s.input(p)
        s.input(100)
        for v in (9, 1):
            if s.phase == Phase.SHOP:
                break
            s.input(v)
        for _ in range(60):
            if s.phase in (Phase.SHOP, Phase.HALTED):
                break
            s.input(3)  # ナンパの [3]無視する（他の入力待ちは WAIT）
        assert s.phase == Phase.SHOP
        assert (st.day[0], st.time) == (day, 1)
        tx = [ln.text for ln in s.out.lines]
        assert any("[3]無視する" in t for t in tx)
        assert 5 <= st.charas[1].cflag[101] <= 8  # 街（ACTION_PASTIME:43 CFLAG:101 = 行き先 + 5）
