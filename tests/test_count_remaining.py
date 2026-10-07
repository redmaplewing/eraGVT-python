"""S90 原生COUNT：來源／預期在各案例註解；沿用25歲人工前態。"""
import pytest
from test_body_editor import data, ctx
from eragvt.game.counting import count_loop


def test_native_loop_call_next_break_return(ctx):
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023、2054–2161。
    st = ctx.state
    seen = []
    for i in count_loop(st, 5):
        seen.append(i)
        if i == 0:
            st.count[0] = 3  # CALL覆寫後NEXT讀共享值。
    assert seen == [0, 4]
    assert st.count[0] == 5
    g = count_loop(st, 5)
    assert next(g) == 0
    g.close()  # caller RETURN，沒有NEXT。
    assert st.count[0] == 0
    for i in count_loop(st, 5):
        st.count[0] += 1  # 原作BREAK仍需一步。
        break
    assert st.count[0] == 1


def test_preset_menu_count(ctx):
    # ERB/SYSTEM/キャラメイキング関連/SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI:10–12。
    from eragvt.game.creation_menu import preset_menu
    st = ctx.state
    st.count[0] = 73
    g = preset_menu(ctx)
    next(g)
    assert st.count[0] == 99
    with pytest.raises(StopIteration): g.send(99)
    assert st.count[0] == 99


@pytest.mark.parametrize("name,expected", [("_juel",12),("_personality",3),("_sexual_personality",6)])
def test_status_leaf_count(ctx,name,expected):
    # PAGE2@SHOW_STATUS_CHARA_JUEL:266；PAGE5@PERSONALITY:320／SEXUAL_PERSONALITY:351。
    from eragvt.game import status_screen
    ctx.state.count[0] = 73
    getattr(status_screen,name)(ctx,1)
    assert ctx.state.count[0] == expected


@pytest.mark.parametrize("mode,value,expected", [(1,0,5),(1,250,3),(1,600,0),(2,600,5),(0,0,73)])
def test_status_ex_only_original_repeat_paths(ctx,mode,value,expected):
    # CHARA_STATUS.ERB@STATUS_PRINT_EX:1203／1209；ARG0是展開IF而非REPEAT。
    from eragvt.game.battle.status_display import _ex_stock
    ctx.state.count[0] = 73
    ctx.state.charas[1].tcvarn[5] = value
    _ex_stock(ctx,mode)
    assert ctx.state.count[0] == expected


@pytest.mark.parametrize("upper,initial,expected", [(0,10,0),(4,0,1),(4,10,4)])
def test_restraint_repeat_break(ctx,upper,initial,expected):
    # 戦闘コマンド(ヒロイン)/COMF45.ERB@COM45:39–48；COM46:36–45同一形狀。
    from eragvt.game.battle.restraint import _fatigue_decay
    st=ctx.state
    st.charas[1].cflag[99]=upper
    st.count[0]=73
    _fatigue_decay(ctx,initial,"0.96","0.92")
    assert st.count[0]==expected


@pytest.mark.parametrize("screen,arg1,expected", [(0,0,299),(1,0,250),(1,2,299)])
def test_talent_display_count_full_scan(ctx,screen,arg1,expected):
    # CHARA_STATUS.ERB@SHOW_STATUS_TALENT:324–633／691–694，FOR LOCAL後段不覆寫。
    from eragvt.game.status_talent import show_status_talent
    st=ctx.state
    st.flag[801]=screen
    st.charas[1].talent[600]=1
    st.charas[1].talent[1100]=1
    st.count[0],st.count[1]=73,74
    show_status_talent(ctx,1,arg1)
    assert (st.count[0],st.count[1])==(expected,74)


@pytest.mark.parametrize("name,expected", [("_abl",15),("_mark",5),("_exp",37)])
def test_status_array_iteration_count(ctx,name,expected):
    # PAGE2@ABL:74–84／MARK:139–147／EXP:195–205：原OUTPUT陣列長度。
    from eragvt.game import status_screen
    getattr(status_screen,name)(ctx,1)
    assert ctx.state.count[0]==expected


@pytest.mark.parametrize("active", [0,1])
def test_attack_clear_and_merge_count(ctx,monkeypatch,active):
    # SEX_COM0.ERB@SEX_COM0:29–31、85–87；37個清零／22個合併共用本體。
    from eragvt.game.battle import sexcom
    st=ctx.state
    st.count[0]=73
    values=sexcom._begin(ctx)
    assert st.count[0]==12 and values==[0]*13
    def call(*args):
        st.count[0]=99
        return list(range(12))
    monkeypatch.setattr(sexcom,"sex_comex",call)
    st.count[0]=73
    st.temp.ex_com=active
    sexcom._comex(ctx,values,0,0)
    assert st.count[0]==(12 if active else 73)
    assert values[:12]==(list(range(12)) if active else [0]*12)


@pytest.mark.parametrize("high,expected", [(False,5),(True,1)])
def test_abl_sense_break_count(ctx,high,expected):
    # ABL_UP_CHECK.ERB@ABL_UP_0:1024–1027；命中上限BREAK仍加1。
    from eragvt.game.battle.ablup import _abl_up_sense
    c=ctx.state.charas[1]
    for name in ("Ｃ感覚","Ｖ感覚","Ａ感覚","Ｂ感覚"):
        c.abl[ctx.data.index_of("ABL",name)]=10 if high else 0
    _abl_up_sense(ctx,c,"Ｃ感覚")
    assert ctx.state.count[0]==expected


def test_abl_addiction_early_return_preserves_count(ctx):
    # ABL_UP_CHECK.ERB@ABL_UP_20:491–495：刻印不足先RETURN LOCAL，未進REPEAT。
    from eragvt.game.battle.ablup import _abl_up_addiction
    st=ctx.state
    st.charas[1].mark[ctx.data.index_of("MARK","屈服刻印")]=0
    st.count[0]=73
    _abl_up_addiction(ctx,st.charas[1],"触手中毒")
    assert st.count[0]==73


@pytest.mark.parametrize("flags,expected", [((1,1,0),0),((3,2,4),4)])
def test_facility_refund_count(ctx,flags,expected):
    # SUCCESSION.ERB@SUCCESSION:278–290：三REPEAT，前兩組COUNT0 CONTINUE。
    from eragvt.game.succession import facility_value
    st=ctx.state
    for k,value in zip((50,51,52),flags):st.flag[k]=value
    facility_value(st)
    assert st.count[0]==expected


@pytest.mark.parametrize("number,expected", [(2,1),(1,73),(4,3)])
def test_creation_count_change(ctx,number,expected):
    # CHARA_MAKE.ERB@CHARA_MAKE_MAIN:343–352；相等分支根本不進REPEAT。
    from eragvt.game.creation_menu import _count_setting
    st=ctx.state
    if number==1:  # 選項至少2人，準備已經2人的相等前態。
        st.add_chara(ctx.data,0)
        number=2
    st.count[0]=73
    g=_count_setting(ctx);next(g)
    with pytest.raises(StopIteration):g.send(number)
    assert st.count[0]==expected
    assert st.charanum==number+1


@pytest.mark.parametrize("debug,expected", [(0,30),(1,73)])
def test_raid_warning_count(ctx,debug,expected):
    # 襲擊共通@RAID_ATTACK:67–96／救援共通@RAID_RESCUE:59–88。
    from eragvt.game.raid import _warning_loop
    st=ctx.state;st.flag[999]=debug;st.count[0]=73
    _warning_loop(ctx,"中性警示",lambda value:(value,0,0))
    assert st.count[0]==expected


@pytest.mark.parametrize("flag,value,expected", [(283,3,3),(284,4,14),(287,4,34),(283,0,50)])
def test_news_weighting_count_before_rng(ctx,flag,value,expected):
    # SHOP_FLASHNEWS.ERB@FLASHNEWS_CHOOSEIDOL:959–993；候選末組決定殘值。
    from eragvt.game.flashnews import flashnews_chooseidol
    st=ctx.state;c=st.charas[1]
    c.exp[ctx.data.index_of("EXP","魅了経験")]=0
    c.cflag[flag]=value
    class Rng:
        def rand(self,n):
            assert st.count[0]==expected
            return 0
    st.rng=Rng()
    assert flashnews_chooseidol(st,ctx.data,"内容",1)==0
    assert st.count[0]==expected


def test_native_return_after_catalog_count_is_not_incremented(ctx,monkeypatch):
    # COMMON_BATTLE_FUNC.ERB@ACT_LIMIT:296–390：選中分支後CALL→RETURN1，沒有NEXT。
    from eragvt.game.battle import func
    from eragvt.state import FixedRng
    st=ctx.state;c=st.charas[1]
    c.mark[0]=1
    st.rng=FixedRng([0])
    monkeypatch.setattr(func,"_land_and_print",lambda ctx:None)
    def message(ctx,count):
        assert count==0 and st.count[0]==0
        st.count[0]=41
    monkeypatch.setattr(func,"_disaction_message",message)
    assert func.act_limit(ctx)==1
    assert st.count[0]==41


@pytest.mark.parametrize("made,expected", [(0,289),(1,272)])
def test_export_input_break_and_final_count(ctx,monkeypatch,made,expected):
    # EXPORT_CSV.ERB@EXPORT_CSV:21–35 BREAK；末段:563–574僅尚未製作時執行。
    from eragvt.game import export_csv
    from eragvt.state import dump_save,load_save
    st=ctx.state;c=st.charas[1]
    c.cflag[34]=made
    original=export_csv.exist_csv
    monkeypatch.setattr(export_csv,"exist_csv",lambda ctx,no: int(no<103))
    g=export_csv.export_csv(ctx);next(g)
    assert st.count[0]==3  # 101、102有CSV，103 BREAK(2→3)。
    monkeypatch.setattr(export_csv,"exist_csv",original)
    with pytest.raises(StopIteration):g.send(0)
    assert st.count[0]==expected
    loaded,_=load_save(dump_save(st))
    assert loaded.count[0]==expected


def test_native_loop_initial_bound_and_nested_call(ctx):
    st=ctx.state;st.count[0]=73
    assert list(count_loop(st,lambda:st.count[0]))==[]
    assert st.count[0]==0  # REPEAT COUNT先清0後求上限。
    seen=[]
    for i in count_loop(st,3):
        seen.append(i)
        for j in count_loop(st,4):pass
    assert seen==[0] and st.count[0]==5



def test_existing_catalog_message_repeat_shared(ctx):
    # TENTACLE_MOB_801_物質（カージャッカー）.ERB@MESSAGE_MOB_801_COM2:383。
    # 只將PRINT字面內容中性化，保留原函式控制流／亂數／COUNT及寫入；不新增情節。
    import re
    from pathlib import Path
    from eragvt.narration.service import CatalogNarrationService
    from eragvt.state import FixedRng
    root=Path(__file__).resolve().parents[1]/"source/earGVP/ERB"
    svc=CatalogNarrationService(root,ctx.data)
    rel="ゲーム内_戦闘処理/触手データ/雑魚敵/TENTACLE_MOB_801_物質（カージャッカー）.ERB"
    svc.catalog._lines[rel]=[(n,re.sub(r"^PRINT.*","PRINTL 中性計數驗證",line))
                             for n,line in svc.catalog.lines_of(rel)]
    ctx.narration=svc
    ctx.state.rng=FixedRng([0]*20)
    ctx.state.count[0]=73
    assert svc.run_function(ctx,"MESSAGE_MOB_801_COM2",[0,0]), svc.failures
    assert ctx.state.count[0]==2  # 2+0+0輪，末次NEXT留下2。
    assert ctx.state.tflag[4]&32
    assert not svc.failures
