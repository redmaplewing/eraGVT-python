"""S29：口上／地の文 catalog の状態書き込み（非 LOCAL 代入を GameState へ直接）・ジャーナルによる失敗回復・TCVAR・TIMES・
口上から呼ぶ状態変更函式の hook。expected は ERB の原文と Emuera の仕様（行番号は各テストの docstring）から。"""

from __future__ import annotations

import re

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.narration import nodes as N
from eragvt.narration.extract import parse_function, read_logical_lines
from eragvt.narration.runtime import Env, ErbRuntimeError, Frame, Interp, StateJournal, _Return
from eragvt.narration.runtime_support import NARRATION_DIRS
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"


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
    s.target = 1
    return Ctx(s, data, TextOutput(), svc)


def _fd(svc, src: str, rel: str = "口上/t.ERB"):
    return parse_function(svc.catalog.ctx, rel, read_logical_lines(src.encode("utf-8")))


def _exec(svc, ctx, fd):
    it = Interp(svc.catalog, Env(ctx.state, ctx.data, ctx.out, {}, {}, ctx, journal=svc.journal))
    try:
        it.exec_block(fd.body, Frame(fd, "F"))
    except _Return:
        pass
    return it


def _idx(data, var, name):
    return data.index_of(var, name)


# --- 各変数種類の代入（キャラ指定・CSV 名・複合代入・文字列） --------------------------------------------


def _expect(data, st, key):
    """key → 現在値（テスト表の比較用）。"""
    kind, *rest = key
    if kind == "cflag":
        c, i = rest
        return st.charas[c].cflag[i]
    if kind == "talent":
        c, n = rest
        return st.charas[c].talent[_idx(data, "TALENT", n)]
    if kind == "base":
        c, n = rest
        return st.charas[c].base[_idx(data, "BASE", n)]
    if kind == "maxbase":
        c, n = rest
        return st.charas[c].maxbase[_idx(data, "BASE", n)]
    if kind == "cstr":
        c, i = rest
        return st.charas[c].cstr[i]
    if kind == "name":
        return st.charas[rest[0]].name
    if kind == "callname":
        return st.charas[rest[0]].callname
    if kind == "cdflag":
        c, a, b = rest
        return st.charas[c].cdflag[(_idx(data, "CDFLAG1", a), _idx(data, "CDFLAG2", b))]
    if kind == "flag":
        return st.flag[rest[0]]
    if kind == "tflag":
        return st.tflag[rest[0]]
    if kind == "item":
        return st.item[rest[0]]
    if kind == "equip":
        c, i = rest
        return st.charas[c].equip[i]
    if kind == "tcvarn":
        c, i = rest
        return st.charas[c].tcvarn[i]
    raise KeyError(kind)


@pytest.mark.parametrize(
    "src,pre,key,expected",
    [
        # 添字 1 つのキャラ変数は TARGET（VariableParser.cs:104–118）。TARGET = 1
        ("CFLAG:270 = 3", {}, ("cflag", 1, 270), 3),
        ("cflag:270 = 4", {}, ("cflag", 1, 270), 4),  # 大文字小文字を無視（emuera.config:1）
        ("CFLAG:(FLAG:112):35 += 300", {"flag112": 2, "cflag2_35": 5}, ("cflag", 2, 35), 305),
        ("CFLAG:TARGET:20 = 7", {}, ("cflag", 1, 20), 7),
        ("SETBIT CFLAG:271, 1", {}, ("cflag", 1, 271), 2),
        ("INVERTBIT CFLAG:271, 0", {"cflag1_271": 3}, ("cflag", 1, 271), 2),
        ("TALENT:魔力貯蔵 = 1", {}, ("talent", 1, "魔力貯蔵"), 1),  # CSV 名の添字（Talent.csv）
        ("TALENT:(FLAG:112):母乳体質 = MAX(TALENT:(FLAG:112):母乳体質,1)", {"flag112": 2}, ("talent", 2, "母乳体質"), 1),
        ("BASE:敏捷 -= 5", {"base1_敏捷": 30}, ("base", 1, "敏捷"), 25),
        # BASE と MAXBASE は連動しない（CharaInt1DVariableToken.SetValue:1066–1070）
        ("BASE:攻撃 += 10", {"base1_攻撃": 50, "maxbase1_攻撃": 50}, ("base", 1, "攻撃"), 60),
        ("BASE:攻撃 += 10", {"base1_攻撃": 50, "maxbase1_攻撃": 50}, ("maxbase", 1, "攻撃"), 50),
        ("MAXBASE:空中ダッシュ ++", {"maxbase1_空中ダッシュ": 1}, ("maxbase", 1, "空中ダッシュ"), 2),
        ("MAXBASE:空中ダッシュ --", {"maxbase1_空中ダッシュ": 1}, ("maxbase", 1, "空中ダッシュ"), 0),
        ("CSTR:3 = 炎の%CALLNAME:TARGET%", {}, ("cstr", 1, 3), "炎の" + "@callname1"),
        ("CSTR:TARGET:5 = あ", {}, ("cstr", 1, 5), "あ"),
        ("CSTR:5 += \"い\"", {"cstr1_5": "あ"}, ("cstr", 1, 5), "あい"),
        ("NAME:TARGET = 新しい名前", {}, ("name", 1), "新しい名前"),
        ("CALLNAME:TARGET = 新", {}, ("callname", 1), "新"),
        # CDFLAG：第 1 添字は CDFLAG1、第 2 添字は CDFLAG2 の名前（ConstantData.cs:826–844）
        ("CDFLAG:TARGET:遠距離:戦闘スタイル = 2", {}, ("cdflag", 1, "遠距離", "戦闘スタイル"), 2),
        ("FLAG:5 = 9", {}, ("flag", 5), 9),
        ("TFLAG:97 |= 4", {"tflag97": 1}, ("tflag", 97), 5),
        ("ITEM:3 = 1", {}, ("item", 3), 1),
        ("EQUIP:10 = 2", {}, ("equip", 1, 10), 2),
        ("TCVARn:20 += 1", {}, ("tcvarn", 1, 20), 1),
        # TIMES（Instraction.Child.cs:905–916：decimal で掛けて切り捨て）
        ("TIMES CFLAG:5, 0.5", {"cflag1_5": 7}, ("cflag", 1, 5), 3),
        ("TIMES CFLAG:5, 0.20", {"cflag1_5": -7}, ("cflag", 1, 5), -1),
    ],
)
def test_state_assign(svc, ctx, data, src, pre, key, expected):
    st = ctx.state
    for k, v in pre.items():
        m = re.fullmatch(r"(cflag|base|maxbase|cstr)(\d+)_(.+)", k)
        if k == "flag112":
            st.flag[112] = v
        elif k == "tflag97":
            st.tflag[97] = v
        elif m:
            c = st.charas[int(m.group(2))]
            i = m.group(3)
            if m.group(1) in ("base", "maxbase"):
                getattr(c, m.group(1))[_idx(data, "BASE", i)] = v
            else:
                getattr(c, m.group(1))[int(i)] = v
    fd = _fd(svc, f"@F\n{src}\n")
    assert fd.unsupported == []
    _exec(svc, ctx, fd)
    if isinstance(expected, str):
        expected = expected.replace("@callname1", st.charas[1].callname)
    assert _expect(data, st, key) == expected


@pytest.mark.parametrize(
    "src,err",
    [
        ("CFLAG:2000 = 1", ErbRuntimeError),  # VariableSize.csv:2 CFLAG 2000 → 0〜1999（CharaVariableToken.CheckElement:275–283）
        ("CFLAG:99:0 = 1", ErbRuntimeError),  # キャラ登録番号の範囲外
        ("TALENT:1300 = 1", ErbRuntimeError),  # VariableSize.csv TALENT 1300
        ("BASE:100 = 1", ErbRuntimeError),  # 既定 100（ConstantData.cs:168）
        ("CSTR:300 = あ", ErbRuntimeError),  # VariableSize.csv CSTR 300
        ("CDFLAG:1:100:0 = 1", ErbRuntimeError),  # VariableSize.csv CDFLAG 100,1000
        ("FLAG:10000 = 1", ErbRuntimeError),  # FLAG 10000（ConstantData.cs:149）
        ("X = TCVAR:100", None),
    ],
)
def test_state_assign_range_error(svc, ctx, src, err):
    if err is None:  # TCVAR の範囲外（既定 100）は読みでも引擎エラー
        fd = _fd(svc, "@F\nLOCAL = TCVAR:100\n")
        err = ErbRuntimeError
    else:
        fd = _fd(svc, f"@F\n{src}\n")
    with pytest.raises(err):
        _exec(svc, ctx, fd)


def test_non_narration_assign_still_unsupported(svc):
    """口上／地の文以外の ERB の函式では従来どおり unsupported（catalog は口上・地の文の実行器）。"""
    fd = _fd(svc, "@F\nCFLAG:270 = 3\n", rel="汎用関数/t.ERB")
    assert fd.unsupported and "非 LOCAL 変数 CFLAG への代入" in fd.unsupported[0][1]
    fd = _fd(svc, "@F\nMONEY = 3\n")  # 状態モデルに無い／書けない変数は口上でも unsupported
    assert fd.unsupported and "状態モデルに欄位が無い" in fd.unsupported[0][1]


def test_tcvar_reads_zero_and_never_written(svc, ctx):
    """TCVAR は本作のどこでも書かれない（VariableSize.csv:7 で非使用）→ 常に 0（VariableEvaluator.cs:1458–1460 の 0 クリアのみ）。"""
    pat = re.compile(r"(?<![A-Za-z_])TCVAR(?![A-Za-z_n])\s*(:[^=<>!&|]*)?\s*([-+*/|&^]?=(?!=)|\+\+|--)", re.I)
    instr = re.compile(r"^\s*(SETBIT|CLEARBIT|INVERTBIT|VARSET|TIMES|SPLIT|FOR)\s+TCVAR(?![A-Za-z_n])", re.I)
    hits = []
    for p in ERB.rglob("*"):
        if p.suffix.upper() not in (".ERB", ".ERH"):
            continue
        for no, line in enumerate(p.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
            s = line.split(";", 1)[0]
            if instr.match(s) or (pat.search(s) and not re.match(r"^\s*(IF|ELSEIF|SIF|PRINT|CASE|DATA|RETURN)", s, re.I)):
                hits.append((p.name, no, line))
    assert hits == []
    st = ctx.state
    fd = _fd(svc, "@F\nLOCAL = TCVAR:2 + TCVAR:40 + 5\n")
    _exec(svc, ctx, fd)
    assert st.temp.locals[("F", 0)] == 5


# --- 代表的な口上函式 ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "jii,rng,cflag270,lines",
    [
        # 鍛錬.ERB:126–136：ELSE → CFLAG:270 = 3、PRINTDATAL（6 件の 2 番目）、PRINTFORM（改行なし）
        (0, [1], 3, ["「……ふぅ」", "座禅を組み、{cn}は静かに瞑想している。"]),
        # :111–125：自慰中毒 3 → CFLAG:270 = 3、PRINTDATAL ×2
        (3, [2, 0], 3, ["(しゅ、集中、しなきゃ……)", "瞑想中に{cn}は身体の疼きを覚え、集中を乱してしまった。"]),
    ],
)
def test_kojo_training_meisou_writes_cflag(svc, ctx, data, jii, rng, cflag270, lines):
    """`口上/女性汎用口上/★KOJO_0_16_真面目/鍛錬.ERB@KOJO_0_TRAINING_MEISOU_16`:53–136。"""
    st = ctx.state
    c = st.charas[1]
    c.abl[_idx(data, "ABL", "自慰中毒")] = jii
    c.cflag[270] = 0
    st.rng = FixedRng(rng)
    assert svc.catalog.unsupported_reason("KOJO_0_TRAINING_MEISOU_16") is None
    assert svc.run_function(ctx, "KOJO_0_TRAINING_MEISOU_16")
    assert c.cflag[270] == cflag270
    out = [ln.text for ln in ctx.out.lines] + [p.text for p in ctx.out._pending]
    assert [x for x in out if x] == [x.format(cn=c.callname) for x in lines]
    assert svc.journal.depth == 0 and svc.journal.entries == []


def test_kojo_call_hooks_by_name(svc):
    """口上の `CALL LEVELSTATUS／TRANSFORM／PERFORM_CHEERS_HATE` は名前で hook（kojo_calls の Python 移植）になる。"""
    cat = svc.catalog
    rel = "口上/固有キャラ専用口上/kojo_131_ホムラ.ERB"
    found = {}
    for name, e in cat.index.items():
        if e.rel != rel:
            continue
        fd = cat.get(name)
        for h in fd.hooks:
            if isinstance(h.args[0], N.CallStmt):
                found[h.line] = h.args[0].name
        assert "LEVELSTATUS" not in fd.calls
    assert {414: "LEVELSTATUS", 1844: "LEVELSTATUS", 1963: "LEVELSTATUS"}.items() <= found.items()
    # 地の文・非口上では名前 hook にしない
    fd2 = _fd(svc, "@F\nCALL LEVELSTATUS, TARGET\n", rel="地の文/t.ERB")
    assert not fd2.hooks and "LEVELSTATUS" in fd2.calls


def test_levelstatus_hook_matches_python(svc, ctx, data):
    """`CALL LEVELSTATUS, TARGET`（コモン関数.ERB:885–894）→ chara_common.level_status と同じ MAXBASE、RESULT = 0。"""
    from copy import deepcopy

    from eragvt.game.chara_common import level_status

    st = ctx.state
    st.result[0] = 5
    ref = deepcopy(st.charas[1])
    s2 = deepcopy(st)
    level_status(data, s2, 1)
    fd = _fd(svc, "@F\nCALL LEVELSTATUS, TARGET\n")
    ok, _ = svc._run(ctx, lambda it: it.exec_block(fd.body, Frame(fd, "F")), "F")
    assert ok
    assert st.charas[1].maxbase == s2.charas[1].maxbase
    assert st.result[0] == 0
    assert ref.base == st.charas[1].base


# --- 失敗回復（ジャーナル） --------------------------------------------------------------------------------


def test_rollback_restores_state_writes(svc, ctx, data):
    """中途で失敗（0 除算＝引擎エラー）→ 出力・亂數・GameState の書き込みすべて呼び出し前に戻る。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[270] = 1
    c.cstr[3] = "前"
    name0 = c.name
    t0 = c.talent[_idx(data, "TALENT", "魔力貯蔵")]
    st.flag[5] = 0
    st.rng = FixedRng([4, 4])
    ctx.out.print("前")
    fd = _fd(
        svc,
        "@F\nCFLAG:270 = 3\nCSTR:3 = 後\nNAME:TARGET = 別人\nTALENT:魔力貯蔵 = 1\nFLAG:5 += RAND:9\nTARGET = 2\n"
        "CDFLAG:1:近距離:戦闘スタイル = 1\nPRINTFORML x\nPRINTFORML {1/0}\n",
    )
    ok, _ = svc._run(ctx, lambda it: it.exec_block(fd.body, Frame(fd, "F")), "F")
    assert ok is False
    assert (c.cflag[270], c.cstr[3], c.name, st.flag[5], st.target) == (1, "前", name0, 0, 1)
    assert c.talent[_idx(data, "TALENT", "魔力貯蔵")] == t0
    assert c.cdflag[(1, 500)] == 0
    assert st.rng.snapshot() == [4, 4]
    assert [ln.text for ln in ctx.out.lines] == [] and ctx.out._pending[0].text == "前"
    assert svc.journal.depth == 0 and svc.journal.entries == []


def test_rollback_through_kojo_root(svc, ctx, data):
    """地の文 → KOJO_ROOT → 口上（CFLAG:270 を書く）→ 戻ってから失敗：口上の書き込みも KOJO_ROOT の FLAG:62／900 も戻る。"""
    st = ctx.state
    c = st.charas[1]
    for i in range(10, 50):
        c.talent[i] = 0
    c.talent[16] = 1  # 真面目（SEIKAKU_CHECK_F：CHARA_SEIKAKU.ERB:41–56）
    c.cflag[6] = 0  # 汎用口上 C_NO 0
    c.cflag[270] = 1
    st.flag[62] = 7
    st.flag[900] = 8
    st.rng = FixedRng([0] * 20)
    fd = _fd(svc, '@F\nCALL KOJO_ROOT, 0, "TRAINING_MEISOU"\nLOCAL = 1 / 0\n', rel="地の文/t.ERB")
    seen = {}

    def run(it):
        try:
            it.exec_block(fd.body, Frame(fd, "F"))
        finally:
            seen["cflag"] = c.cflag[270]

    ok, _ = svc._run(ctx, run, "F")
    assert ok is False and seen["cflag"] == 3  # 実行中は書き込まれていた
    assert (c.cflag[270], st.flag[62], st.flag[900]) == (1, 7, 8)
    assert svc.journal.depth == 0


def test_irreversible_hook_then_failure_stops(svc, ctx):
    """Python 移植の hook（記録できない状態変化）の後で失敗したら戻せない → NotImplementedError（従来どおり）。"""
    fd = _fd(svc, "@F\nCALL LEVELSTATUS, TARGET\nLOCAL = 1 / 0\n")
    with pytest.raises(NotImplementedError):
        svc._run(ctx, lambda it: it.exec_block(fd.body, Frame(fd, "F")), "F")
    assert svc.journal.depth == 0


def test_journal_nested():
    """入れ子：内側の rollback は内側だけ、外側の rollback は内側で commit した分も戻す。区間外は記録しない。"""
    from eragvt.state.sparse import IntArray

    j = StateJournal()
    a = IntArray()
    j.set_item(a, 0, 1)
    assert j.entries == []
    m1 = j.begin()
    j.set_item(a, 1, 1)
    m2 = j.begin()
    j.set_item(a, 2, 1)
    j.rollback(m2)
    assert (a[1], a[2]) == (1, 0)
    m3 = j.begin()
    j.set_item(a, 3, 1)
    j.commit(m3)
    assert a[3] == 1 and j.depth == 1
    j.rollback(m1)
    assert (a[0], a[1], a[3]) == (1, 0, 0) and j.depth == 0 and j.entries == []


def test_run_function_gen_replays_after_state_write(svc, ctx):
    """INPUT 前の状態書き込みはジャーナルで戻して再実行できる（S29 前は NotImplementedError）。"""
    st = ctx.state
    st.charas[1].cflag[270] = 0
    fd = _fd(svc, "@F\nCFLAG:270 += 1\nINPUT\nCFLAG:271 = RESULT\n")
    svc.catalog._parsed["S29_TEST_F"] = fd
    svc.catalog.index["S29_TEST_F"] = svc.catalog.index["KOJO_0_TRAINING_MEISOU_16"]
    fd.name = "S29_TEST_F"
    try:
        g = svc.run_function_gen(ctx, "S29_TEST_F")
        next(g)
        assert st.charas[1].cflag[270] == 1
        with pytest.raises(StopIteration) as e:
            g.send(5)
        assert e.value.value is True
        assert (st.charas[1].cflag[270], st.charas[1].cflag[271]) == (1, 5)  # 二重に加算されない
        assert svc.journal.depth == 0
    finally:
        del svc.catalog._parsed["S29_TEST_F"]
        del svc.catalog.index["S29_TEST_F"]
        svc.catalog._support.pop("S29_TEST_F", None)
        svc.catalog._input.pop("S29_TEST_F", None)


# --- 覆蓋率回歸 ---------------------------------------------------------------------------------------------


def test_all_narration_assignments_supported(svc):
    """口上／地の文の函式自身に「非 LOCAL 代入」「TCVAR」の unsupported が 1 つも無い（全代入が GameState へ書ける）。
    残るのは呼び出し先（非口上の ERB 函式）の理由だけ：ADDRANDCHOOSE（RANDCHOOSE_NUM）と UNLOCK_ACHIEVEMENT（GLOBAL）。"""
    cat = svc.catalog
    own = []
    callee = set()
    for name in cat.narration_functions():
        fd = cat.get(name)
        for line, why in fd.unsupported:
            if "非 LOCAL" in why or "TCVAR" in why:
                own.append((name, line, why))
        r = cat.unsupported_reason(name)
        if r and ("非 LOCAL" in r or "TCVAR" in r):
            callee.add(r.split(":", 1)[0])
    assert own == []
    assert callee <= {"ADDRANDCHOOSE", "UNLOCK_ACHIEVEMENT"}
    assert all(not cat.index[c].rel.startswith(NARRATION_DIRS) for c in callee)


def test_coverage_numbers(svc):
    r = svc.catalog.report()
    assert r["total"] == 13384 and r["ok"] >= 13161
