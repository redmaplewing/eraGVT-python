"""S60c 氏名子頁：人工中性前態，不進共用角色編輯畫面。"""
from types import SimpleNamespace

import pytest

from eragvt.game.character_name import character_name
from eragvt.state.character import Character
from eragvt.state.sparse import IntArray, StrArray
from eragvt.text import TextOutput


@pytest.fixture
def ctx():
    charas = [Character(0), Character(1, name="原名", callname="名稱"),
              Character(2, name="同伴伴名", callname="伴名")]
    charas[1].cstr[10] = "姓氏"
    charas[2].cstr[10] = "同伴"
    for chara in charas:
        for slot in (40, 41):
            chara.base[slot] = chara.maxbase[slot] = 25
    state = SimpleNamespace(charas=charas, charanum=3, MASTER=0,
                            result=IntArray(), results=StrArray(), count=IntArray())
    data = SimpleNamespace(charas={1: SimpleNamespace(name="預設名稱", callname="名稱", cstr={})})
    out = TextOutput()
    out.printl("呼叫者保留行")
    return SimpleNamespace(state=state, data=data, out=out)


@pytest.mark.parametrize("command,choice,expected", [
    (3, 0, "姓氏名稱"), (3, 1, "名稱・姓氏"), (3, 99, "原名"),
    (4, 2, "同伴名稱"), (4, 99, "原名"),
])
def test_submenu_clears_to_entry_before_redraw(ctx, command, choice, expected):
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME:506、625–637、656–672。
    # CLEARLINE：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:488–500。
    gen = character_name(ctx, 1)
    next(gen)
    gen.send(command)
    gen.send(choice)
    gen.send("")
    texts = [line.text for line in ctx.out.lines]
    assert texts[0] == "呼叫者保留行"
    assert sum("氏名を設定してください" in text for text in texts) == 1
    assert not any("変更しました" in text or "変更せず" in text for text in texts)
    assert ctx.state.charas[1].name == expected
    with pytest.raises(StopIteration) as stopped:
        gen.send(99)
    assert stopped.value.value == 99


def test_empty_given_name_clears_error_after_wait(ctx):
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME:589–600。
    gen = character_name(ctx, 1)
    next(gen)
    gen.send(1)
    gen.send("測試")
    gen.send("")
    assert any("名前は必ず" in line.text for line in ctx.out.lines)
    gen.send("")
    assert not any("名前は必ず" in line.text for line in ctx.out.lines)
    with pytest.raises(StopIteration):
        gen.send("名稱")
    assert ctx.state.charas[1].name == "測試名稱"


@pytest.mark.parametrize("command", [0, 100, 800, 801, 802])
def test_random_name_configuration_replaces_previous_menu(ctx, command):
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME_RANDOM:800–824。
    from eragvt.game.character_name import random_character_name
    ctx.data.str_defaults = {}
    gen = random_character_name(ctx, 1)
    next(gen)
    gen.send(command)
    texts = [line.text for line in ctx.out.lines]
    assert texts[0] == "呼叫者保留行"
    assert sum(text.startswith("苗字：") for text in texts) == 1
    assert sum(text.startswith("名前：") for text in texts) == 1


@pytest.mark.parametrize("command", [200, 800, 801, 802])
def test_random_name_candidates_replace_old_buttons(ctx, command):
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME_RANDOM:989–1002。
    from eragvt.game.character_name import random_character_name
    from eragvt.state import FixedRng
    ctx.data.str_defaults = {3000: "姓", 12000: "名"}
    ctx.state.rng = FixedRng([0] * 80)
    gen = random_character_name(ctx, 1)
    next(gen)
    gen.send(200)
    gen.send(command)
    texts = [line.text for line in ctx.out.lines]
    assert texts[0] == "呼叫者保留行"
    assert sum(text.startswith("[ 0]") for text in texts) == 1
    assert sum(text.startswith("[19]") for text in texts) == 1
    assert "[ 0]" + ("名・姓" if command == 802 else "姓名") in texts
    assert sum(text.startswith("苗字：") for text in texts) == 1
    assert len(ctx.state.rng.snapshot()) == (0 if command == 200 else 40)
    with pytest.raises(StopIteration):
        gen.send(0)
    assert tuple(ctx.state.results[i] for i in range(3)) == ("姓名", "名", "姓")
