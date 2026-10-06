"""S40：ERB/インターミッション画面/SHOP_CLOTH.ERB@SHOW_CLOTH／BUY_CLOTH 的原文預期。"""
from dataclasses import replace

import pytest

from test_clothing_menu import data, ctx
from eragvt.game.clothing_inventory import inventory_gen, inventory_items
from eragvt.game.session import GameSession
from eragvt.state import GameRng
from eragvt.text import NullNarrationService


def text(ctx):
    return "\n".join(line.text for line in ctx.out.lines)


@pytest.mark.parametrize("money,owned,left", [(1999,0,1999),(2000,1,0),(2001,1,1)])
def test_price_boundary_and_repeat(ctx, money, owned, left):
    """@BUY_CLOTH:768–781；CSV/Item.csv 的101售價2000。"""
    st = ctx.state
    st.item[101] = 0
    st.money = money
    st.result[4], st.results[0] = 314, "保留"
    gen = inventory_gen(ctx, purchase=True)
    next(gen)
    gen.send(101)
    assert st.item[101] == 0 and st.money == money
    gen.send(101)
    assert (st.item[101], st.money) == (owned,left)
    assert ("を買いました" if owned else "お金が足りません") in text(ctx)
    gen.send(101)
    assert (st.item[101],st.money) == (owned,left)
    assert st.result[0] == 1  # @SHOW_CLOTH_FOOTER:395
    assert st.result[4] == 314 and st.results[0] == "保留"


@pytest.mark.parametrize("owned", [-1,0,1,2])
def test_sale_requires_zero_ownership(ctx, owned):
    """@ISCHECK_CLOTH:757–763：不是僅排除持有1。"""
    ctx.state.item[101] = owned
    assert (101 in inventory_items(ctx,0,0,purchase=True)) == (owned == 0)


@pytest.mark.parametrize("cid", [100,200,300,400,999,1000])
def test_not_for_sale(ctx,cid):
    ctx.state.item[cid] = 0
    ctx.state.money = 999999
    gen = inventory_gen(ctx,purchase=True)
    next(gen)
    gen.send(cid)
    gen.send(cid)
    assert ctx.state.item[cid] == 0 and ctx.state.money == 999999


def test_missing_name_not_listed(ctx,monkeypatch):
    monkeypatch.setitem(ctx.data.items,101,replace(ctx.data.items[101],name=""))
    ctx.state.item[101] = 0
    assert 101 not in inventory_items(ctx,0,0,purchase=True)


@pytest.mark.parametrize("kind", [1,2])
def test_last_purchase_rewinds_page(ctx,kind):
    """@SHOW_CLOTH:187–191：以購入前最後一件的前一位置換算頁碼。"""
    for cid in range(100,300):
        ctx.state.item[cid] = 1
    for cid in range(101,106):
        ctx.state.item[cid] = 0
    ctx.state.money = 10000
    gen = inventory_gen(ctx,purchase=True)
    next(gen)
    if kind == 2:
        gen.send(10)
        gen.send(91)
    else:
        gen.send(105)
    ctx.out.drain()
    gen.send(105)
    assert ctx.state.item[105] == 1
    assert "メイド服" in text(ctx)
    assert "[105]買う" not in text(ctx)
    ctx.out.drain()
    gen.send(99)
    assert "[104]" in text(ctx)
    with pytest.raises(StopIteration):
        gen.send(99)
    assert ctx.state.result[0] == 1


@pytest.mark.parametrize("category,cid", [(0,101),(1,600),(2,301),(3,501)])
def test_categories_purchase(ctx,category,cid):
    ctx.state.item[cid] = 0
    ctx.state.money = 999999
    gen = inventory_gen(ctx,purchase=True)
    next(gen)
    gen.send(category)
    gen.send(cid)
    gen.send(cid)
    assert ctx.state.item[cid] == 1


def test_session_purchase_then_equip(data,tmp_path):
    s = GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for v in (0,1, 1000,1,0):
        s.input(v)
    s.state.item[101] = 0
    s.state.money = 2000
    for v in (120,101,101,99,99,112,1,1,101,1,999,999):
        s.input(v)
    assert s.state.item[101] == 1 and s.state.money == 0
    assert s.state.charas[1].cflag[40] == 101
    assert s.phase.value == "shop"


@pytest.mark.parametrize("gameover,blocked", [(True,False),(False,True)])
def test_shop_entry_gate(data,tmp_path,gameover,blocked):
    """ERB/インターミッション画面/SHOP.ERB@USERSHOP:267–269。"""
    s = GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for v in (0,1, 1000,1,0):
        s.input(v)
    if gameover:
        s.state.flag[0] = 0
    s.state.flag[63] = int(blocked)
    s.input(120)
    assert s.phase.value == "shop"


def test_filters_reject_outside_list_and_reset(ctx):
    """@SHOW_CLOTH:172–177；@FILTER_CLOTH_HOSEI:732–737：部件依函式有無。"""
    ctx.state.item[600] = ctx.state.item[601] = 0
    ctx.state.money = 999999
    gen = inventory_gen(ctx,purchase=True)
    next(gen)
    gen.send(1)
    gen.send(51)  # BOUGYO；600有負補正也列出，601沒有該函式。
    assert 600 in inventory_items(ctx,1,2,purchase=True)
    assert 601 not in inventory_items(ctx,1,2,purchase=True)
    gen.send(601)
    gen.send(601)
    assert ctx.state.item[601] == 0
    gen.send(98)
    gen.send(601)
    gen.send(601)
    assert ctx.state.item[601] == 1


def test_empty_category_and_disabled_buy_button(ctx):
    ctx.state.money = 1999
    ctx.state.item[101] = 0
    gen = inventory_gen(ctx,purchase=True)
    next(gen)
    ctx.out.drain()
    gen.send(101)
    assert "[101]買う" in text(ctx)
    assert not any(value == 101 for line in ctx.out.lines for _,value in line.buttons)
    gen.send(99)
    for cid in range(100,300):
        ctx.state.item[cid] = 1
    ctx.out.drain()
    gen.send(0)
    assert not any(100 <= value < 300 for line in ctx.out.lines for _,value in line.buttons)
    gen.send(91)
    gen.send(90)
    with pytest.raises(StopIteration):
        gen.send(99)


@pytest.mark.parametrize("count,expected", [(9,[]),(10,[269]),(29,[269]),(30,[269,274])])
def test_return_achievement_count(ctx,monkeypatch,count,expected):
    """@SHOW_CLOTH:76–92：加ITEM值，排除100/200/300；非實際件數。"""
    from eragvt.game.battle import core
    calls = []
    monkeypatch.setattr(core,"unlock_achievement",lambda ctx,num,name: calls.append(num))
    ctx.state.item.clear()
    ctx.state.item[100] = ctx.state.item[200] = ctx.state.item[300] = 99
    ctx.state.item[101] = count
    gen = inventory_gen(ctx,purchase=True)
    next(gen)
    with pytest.raises(StopIteration):
        gen.send(99)
    assert calls == expected


@pytest.mark.parametrize("display", [10,11])
def test_display_toggle_and_manual_item_outside_page(ctx,display):
    """@SHOW_CLOTH:140–170／172–198：有效ID檢查整個分類清單，並非當頁。"""
    ctx.state.item[101] = ctx.state.item[102] = 0
    ctx.state.money = 10000
    gen = inventory_gen(ctx,purchase=True)
    next(gen)
    gen.send(display)
    gen.send(91)
    gen.send(101)
    if display == 11:  # 簡易情報第一次只進詳情。
        assert ctx.state.item[101] == 0
        gen.send(101)
    assert ctx.state.item[101] == 1
    assert ctx.state.money == 8000
    ctx.out.drain()
    gen.send(-1)  # 原作 INPUT_NO 的無動作哨兵。
    assert "想定外" not in text(ctx)


def test_item_outside_category_resets_selected_position(ctx):
    """@SHOW_CLOTH:173–176：FINDELEMENT失敗留下-1；後續切目錄由第0頁開始。"""
    for cid in range(100,300):
        ctx.state.item[cid] = 1
    for cid in (101,102,103,104,105,600):
        ctx.state.item[cid] = 0
    gen = inventory_gen(ctx,purchase=True)
    next(gen)
    gen.send(105)
    gen.send(600)
    ctx.out.drain()
    gen.send(10)
    assert "セーラー服" in text(ctx)
    assert "ステージ衣装" not in text(ctx)
