"""S39：expected 直接取自 CLOTH_WEAR.ERB 的指定函式，不以實作回推。

路徑：ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB。
"""
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.clothing import clothing_setting_gen, remove_tentacle_cloth_gen
from eragvt.game.clothing import cloth_wear_gen, custom_clothing_gen, custom_parts_gen
from eragvt.game.clothing_custom import encode_custom
from eragvt.game.battle.cloth import customize_commonparts_cal, cloth_hosei
from eragvt.game.session import GameSession
from eragvt.state import GameRng
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data, tmp_path):
    s = GameSession(data, tmp_path, rng=GameRng(0), narration=NullNarrationService())
    for v in (0, 0, 1):
        s.input(v)
    return Ctx(s.state, data, TextOutput(), NullNarrationService())


@pytest.mark.parametrize("slot,cid", [(40, 101), (41, 201), (42, 301), (43, 501)])
def test_choose_then_confirm(ctx, slot, cid):
    """@CLOTH_SETTING_OUTER:286–305／OUTER2:375–404／INNER:461–470／MISC:607–618。"""
    c = ctx.state.charas[1]
    old = c.cflag[slot]
    ctx.state.item[cid] = 1
    gen = clothing_setting_gen(ctx, 1, slot)
    next(gen)
    gen.send(cid)
    assert c.cflag[slot] == old
    with pytest.raises(StopIteration):
        gen.send(1)
    assert c.cflag[slot] == cid


@pytest.mark.parametrize("answer", [0, 2])
@pytest.mark.parametrize("slot", [40, 41, 42, 43])
def test_cancel_or_unset(ctx, slot, answer):
    """各 CLOTH_SETTING_*：0不改、2清零；名稱與其他欄位不清除。"""
    c = ctx.state.charas[1]
    c.cflag[slot] = 123
    c.cstr[8] = "保留名稱"
    c.equip[600] = 1
    gen = clothing_setting_gen(ctx, 1, slot)
    next(gen)
    with pytest.raises(StopIteration):
        gen.send(answer)
    assert c.cflag[slot] == (123 if answer == 0 else 0)
    assert c.cstr[8] == "保留名稱"
    assert c.equip[600] == 1


@pytest.mark.parametrize("old", [200, 201])
def test_transformed_change_resets_parts_only_when_changed(ctx, old):
    """@CLOTH_SETTING_OUTER2:394–399；相同衣裝不清部件。"""
    c = ctx.state.charas[1]
    c.cflag[41] = old
    c.equip[600] = c.equip[699] = c.equip[700] = 1
    ctx.state.item[201] = 1
    gen = clothing_setting_gen(ctx, 1, 41)
    next(gen)
    gen.send(201)
    with pytest.raises(StopIteration):
        gen.send(1)
    assert c.equip[600] == c.equip[699] == int(old == 201)
    assert c.equip[700] == 1


@pytest.mark.parametrize("count", [0, 1, 2])
def test_remove_requires_fragment(ctx, count):
    """@CLOTH_RESETTING_TENTACLECLOTH:637–663。"""
    ctx.state.charas[1].cflag[42] = 400
    ctx.state.flag[200] = count
    gen = remove_tentacle_cloth_gen(ctx, 1)
    next(gen)
    if count == 0:
        gen.send(1)
        assert ctx.state.charas[1].cflag[42] == 400
        assert ctx.state.flag[200] == 0
    else:
        with pytest.raises(StopIteration):
            gen.send(1)
        assert ctx.state.charas[1].cflag[42] == 0
        assert ctx.state.flag[200] == count - 1


@pytest.mark.parametrize("cid,custom,expected", [
    (101, [0, 2, 0, 2, 0], 2020 + 4 * 10**9 + 2 * 10**11),
    (101, [0, 0, 1, 1, 4], 41100 + 4 * 10**10 + 3 * 10**12),
    (103, [0, 0, 0, 2, 0], 2000 + 4 * 10**9 + 4 * 10**11),
    (110, [0, 1, 0, 1, 0], 1010 + 10**10 + 2 * 10**12),
    (153, [0, 3, 0, 0, 0, 0, 0], 30),  # 原作 <=3 && >=7 永不成立
    (305, [0, 0, 1, 0, 0, 0, 0], 100 + 3 * 10**10),  # 同條件重複加1和2
    (304, [0, 0, 0, 6, 0], 6000 + 2 * 10**9 + 3 * 10**11 + 2 * 10**14),
    (199, [1, 5, 3, 4], 4351),
])
def test_custom_save_original_arithmetic(cid, custom, expected):
    """CLOTHDATAアウター_通常／特殊／インナー.ERB@CLOTH_CUSTOMIZE_OPTION_{cid} 末尾。"""
    assert encode_custom(cid, custom) == expected


@pytest.mark.parametrize("mode,initial,expected", [("HP", 80, 70), ("KOUGEKI", 100, 105), ("BOUGYO", 100, 95), ("BINSYOU", 100, 115), ("HIT", 0, 0)])
def test_parts_additive(ctx, mode, initial, expected):
    """CLOTHDATAカスタム.ERB@CLOTH_CUSTOMIZE_COMMONPARTS_CAL:9–18及600/601/610各補正函式。"""
    ctx.state.target = 1
    for cid in (600, 601, 610):
        ctx.state.target_chara.equip[cid] = 1
    assert customize_commonparts_cal(ctx, initial, mode) == expected


@pytest.mark.parametrize("cid,equip,mode,expected", [(106, 10**13, "NOINNER", 1), (117, 0, "DEF", 80), (117, 10**13, "DEF", 25), (199, 4351, "KOUGEKI", 325), (199, 4351, "BINSYOU", 357)])
def test_special_cloth_hosei(ctx, cid, equip, mode, expected):
    """CLOTHDATA通常@CLOTH_HOSEI_DEF_117、特殊@CLOTH_HOSEI_KOUGEKI_199等。"""
    ctx.state.target = 1
    ctx.state.target_chara.cflag[1] = 0
    ctx.state.target_chara.equip[cid-100] = equip
    assert cloth_hosei(ctx, 1, cid, mode) == expected


def test_real_shop_entry(data, tmp_path):
    s = GameSession(data, tmp_path, rng=GameRng(0), narration=NullNarrationService())
    for value in (0, 0, 1, 112, 1, 11, "衣装名", 999, 999):
        s.input(value)
    assert s.state.charas[1].cstr[8] == "衣装名"
    assert s.phase.value == "shop"


def test_custom_101_and_target_residue(ctx):
    """通常@OPTION_101:179–267、CLOTH_WEAR@CUSTOMIZE_OUTER:930–937。"""
    st = ctx.state
    st.target = 2
    st.charas[1].cflag[40] = 101
    gen = custom_clothing_gen(ctx, 1, 40)
    next(gen)
    gen.send(10)
    gen.send(2)
    assert st.charas[1].equip[1] == 20 + 2 * 10**9
    with pytest.raises(StopIteration):
        gen.send(99)
    assert st.target == 1
    assert st.charas[1].cflag[1] == 0


def test_part_replacement_while_full(ctx):
    """CLOTH_WEAR@CUSTOMIZE_OUTER2:1245–1277：先清同類別，再檢查剩餘槽。"""
    st = ctx.state
    st.target = 2
    c = st.charas[1]
    c.cflag[41] = 401  # SLOT1
    c.equip[660] = 1
    st.item[660] = st.item[661] = 1
    gen = custom_parts_gen(ctx, 1)
    next(gen)
    gen.send(661)
    assert c.equip[660] == 0 and c.equip[661] == 1
    with pytest.raises(StopIteration):
        gen.send(999)
    assert st.target == 2


# 每衣裝選一個原文非零設定；tuple為(低位外觀,重量,防護下降,防護上升,14位,15位)。
# 來源為clothing_text.MENUS各source指向的同名函式末尾，數值人工依ERB抄錄。
@pytest.mark.parametrize("cid,low,w,down,up,extra,oil", [
    (101,20,-2,0,0,0,0),(102,400,-5,0,0,0,0),(103,2000,-4,4,0,0,0),
    (104,30,-3,1,0,0,0),(105,2000,-2,2,0,0,0),(106,30000,-2,0,0,1,0),
    (107,2000,2,0,2,0,0),(108,40,2,0,0,0,0),(109,50,-2,0,0,0,0),
    (110,1000,0,0,1,0,0),(111,30,-3,0,0,0,0),(112,50,-3,0,0,0,0),
    (113,30,2,0,0,0,0),(114,500,-6,0,1,0,0),(115,4000,-2,0,0,1,0),
    (116,4000,1,0,1,0,0),(117,3000,-1,0,0,1,0),(119,800,-3,0,0,0,0),
    (120,100000,0,0,1,0,0),(121,1,-2,0,0,0,0),(122,1000,2,0,2,0,0),
    (123,4000,-2,2,0,0,0),(124,1000000,-1,1,0,0,0),(125,60000,0,0,1,0,0),
    (130,1000,-1,0,0,0,0),(131,1000,-2,2,0,0,0),(132,2,-1,0,0,0,0),
    (137,4000,-3,3,0,0,0),(138,20,-4,0,0,0,0),(139,4000,-2,2,0,0,0),
    (140,1000,1,0,1,0,0),(141,3000,-4,3,0,0,0),(142,200,2,0,0,0,0),
    (143,20,-2,0,0,0,0),(144,40000,1,0,1,0,0),(145,2000,-2,2,0,0,0),
    (146,4000000,-3,3,0,0,0),(147,300000,-2,2,0,0,0),(148,3000,0,1,0,0,0),
    (149,30,1,0,0,0,0),(150,50000,1,0,1,0,0),(151,7000,0,1,0,0,0),
    (152,400,1,0,0,0,0),(153,30000,-2,0,0,1,0),(196,40000,-1,0,1,0,0),
    (199,4351,0,0,0,0,0),(301,5000,1,0,2,2,0),(302,60,0,0,0,0,2),
    (303,5000,1,0,2,2,0),(304,7000,-1,4,0,0,1),(305,100,3,0,0,0,0),
    (306,11,0,0,0,0,0),(309,1,0,0,0,0,0),(310,60,0,0,0,0,2),
    (312,6000,-3,0,0,2,0),(313,3000,1,0,2,2,0),(314,1001,0,0,0,0,0),
])
def test_all_clothing_save_matrix(cid, low, w, down, up, extra, oil):
    from eragvt.game.clothing_text import MENUS
    custom = [(low // 10**i) % 10 for i in range(MENUS[cid]["count"])]
    expected = low + (-w * 10**9 if w < 0 else w * 10**10) + down * 10**11 + up * 10**12 + extra * 10**13 + oil * 10**14
    assert encode_custom(cid, custom) == expected


@pytest.mark.parametrize("cid,field,value,initial,expected", [
    (102,0,1,[0,0,4,0,0,0],[1,0,0,0,0,0]),
    (102,2,7,[0,1,0,1,0,0],[0,0,7,0,0,0]),
    (104,1,3,[0,0,0,0,0,0],[0,3,2,1,0,0]),
    (106,1,2,[0,0,1,0,0,0],[0,2,0,0,0,0]),
    (111,1,3,[0,0,0,0,0],[0,3,1,0,0]),
    (114,2,5,[0,0,0,1,2,3,4],[0,0,5,0,0,0,0]),
    (115,1,2,[0,0,0,4,0],[0,2,0,0,0]),
    (117,1,1,[0,0,2,0,0],[0,1,0,0,0]),
    (119,2,8,[0,0,0,1,0,0],[0,0,8,0,0,0]),
    (120,2,4,[0,0,0,1,2,0,0],[0,0,4,0,0,0,0]),
    (121,1,5,[0,0,1,0,0],[0,5,0,0,0]),
    (123,1,2,[0,0,0,0,0],[0,2,2,0,0]),
    (123,3,1,[0,0,0,0,4],[0,0,0,1,0]),
    (130,1,0,[0,1,1,0,0],[0,0,0,0,0]),
    (132,0,1,[0,4,0,0,0],[1,0,0,0,0]),
    (140,3,1,[0,0,0,0,4],[0,0,0,1,0]),
    (149,1,2,[0,0,1,0,0],[0,2,0,0,0]),
    (153,2,3,[0,0,0,0,5,0,0],[0,0,3,2,4,0,0]),
])
def test_dependent_fields(cid, field, value, initial, expected):
    from eragvt.game.clothing_custom import change_custom
    change_custom(cid, field, value, initial)
    assert initial == expected


@pytest.mark.parametrize("cid,field,changed_index,changed_value", [
    (102,0,2,4),(102,1,2,7),(104,2,1,3),(106,2,1,2),(109,0,1,4),
    (111,2,1,3),(114,6,2,5),(119,3,2,8),(120,3,2,4),(120,4,2,5),
    (121,2,1,5),(123,2,1,2),(123,4,3,1),(132,2,1,5),(140,4,3,1),
    (149,2,1,2),(153,3,2,3),
])
def test_category_conditions(cid, field, changed_index, changed_value):
    from eragvt.game.clothing_custom import category_blocked
    custom = [0]*9
    assert not category_blocked(cid,field,custom,5)
    custom[changed_index] = changed_value
    assert category_blocked(cid,field,custom,5)


@pytest.mark.parametrize("cid,field,choice,index,value", [
    (102,2,4,0,1),(109,1,4,0,1),(121,1,4,0,1),(132,1,4,0,1),
    (104,3,0,1,3),(115,3,4,1,2),(117,2,2,1,1),(120,4,2,2,4),(153,4,5,2,3),
])
def test_choice_conditions(cid, field, choice, index, value):
    from eragvt.game.clothing_custom import choice_blocked
    custom = [0]*9
    assert not choice_blocked(cid,field,choice,custom,308,5)
    custom[index] = value
    assert choice_blocked(cid,field,choice,custom,308,5)


@pytest.mark.parametrize("field,option,level", [(1,1,1),(1,5,5),(2,1,3),(3,1,2),(3,2,4),(3,3,3),(3,4,5)])
def test_research_thresholds(field, option, level):
    from eragvt.game.clothing_custom import choice_blocked
    assert choice_blocked(199,field,option,[0]*4,300,level-1)
    assert not choice_blocked(199,field,option,[0]*4,300,level)


@pytest.mark.parametrize("cid", [101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,119,120,121,122,123,124,125,130,131,132,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,196,199,301,302,303,304,305,306,309,310,312,313,314])
def test_all_custom_menu_roundtrip(ctx, cid):
    """每個原文選單都選一個有效欄位的0選項→99，不靠實作回推expected。"""
    slot = 40 if cid < 300 else 42
    ctx.state.flag[54] = 5
    ctx.state.charas[1].cflag[slot] = cid
    gen = custom_clothing_gen(ctx,1,slot)
    next(gen)
    command = 10 if cid in (103,108,139,140,141,142) else 0
    gen.send(command)
    gen.send(0)
    with pytest.raises(StopIteration):
        gen.send(99)
    assert ctx.state.charas[1].equip[cid-100 if cid<200 else cid] == 0


def test_inner_reverts_spats_and_disguised_item(ctx):
    c = ctx.state.charas[1]
    c.equip[3] = c.equip[103] = 2000 + 4*10**9 + 4*10**11
    ctx.state.item[399] = 1
    gen = clothing_setting_gen(ctx,1,42)
    next(gen)
    gen.send(399)
    with pytest.raises(StopIteration):
        gen.send(1)
    assert c.cflag[42] == 400
    assert c.equip[3] == c.equip[103] == 0
    text = "\n".join(line.text for line in ctx.out.lines)
    assert "PRINT_CALLNAME" not in text
    assert "突如、" in text


def test_inventory_filters_and_return(ctx):
    from eragvt.game.clothing_inventory import inventory_gen, inventory_items
    ctx.state.item.clear()
    ctx.state.item[101] = ctx.state.item[600] = ctx.state.item[601] = 1
    assert inventory_items(ctx,0,1) == [101]
    assert inventory_items(ctx,1,1 << 1) == [600]  # 負補正でも関数があれば採用
    gen = inventory_gen(ctx)
    next(gen)
    gen.send(101)
    gen.send(99)
    with pytest.raises(StopIteration):
        gen.send(99)
    assert ctx.state.result[0] == 1


def test_hosei_customization_reads_target_not_arg(ctx):
    """CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_HOSEI:132–147：EQUIP未寫角色索引。"""
    ctx.state.target = 1
    ctx.state.charas[1].cflag[1] = 0
    ctx.state.charas[1].equip[1] = 2 * 10**9
    assert cloth_hosei(ctx,0,101,"HP") == 90


def test_disabled_custom_button_is_plain_and_numeric_rejected(ctx):
    """CLOTH_WEAR@CLOTH_WEAR:126–133 的 PRINTPLAIN 不產生按鈕。"""
    c = ctx.state.charas[1]
    c.cflag[40] = 100
    gen = cloth_wear_gen(ctx)
    next(gen)
    gen.send(1)
    assert not any(value == 10 for line in ctx.out.lines for _,value in line.buttons)
    gen.send(10)
    assert c.cflag[40] == 100


@pytest.mark.parametrize("ability,accepted", [(-1,True),(0,False),(1,False)])
def test_197_restriction_checked_at_confirmation(ctx, ability, accepted):
    c = ctx.state.charas[1]
    c.talent[ctx.data.index_of("TALENT","変身能力")] = ability
    ctx.state.item[197] = 1
    gen = clothing_setting_gen(ctx,1,40)
    next(gen)
    gen.send(197)
    if accepted:
        with pytest.raises(StopIteration):
            gen.send(1)
        assert c.cflag[40] == 197
    else:
        gen.send(1)
        assert c.cflag[40] != 197


def test_401_requires_experience_but_not_item(ctx):
    c = ctx.state.charas[1]
    ctx.state.item[401] = 0
    c.exp[ctx.data.index_of("EXP","陥落経験")] = 1
    gen = clothing_setting_gen(ctx,1,41)
    next(gen)
    gen.send(401)
    with pytest.raises(StopIteration):
        gen.send(1)
    assert c.cflag[41] == 401


def test_shared_results_other_slots_unchanged(ctx):
    c = ctx.state.charas[1]
    c.cflag[40] = 101
    ctx.state.result[1] = 876
    ctx.state.results[2] = "殘值"
    gen = custom_clothing_gen(ctx,1,40)
    next(gen)
    gen.send(10)
    gen.send(1)
    with pytest.raises(StopIteration):
        gen.send(99)
    assert ctx.state.result[0] == 0
    assert ctx.state.result[1] == 876
    assert ctx.state.results[2] == "殘值"
