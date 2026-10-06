"""S47：預期由 FIRSTSETTING_CHARA.ERB:1203–1491 與 SELF_CALL.ERB 推導。"""
import pytest
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.opening import event_first
from eragvt.state import GameState, GameRng
from eragvt.text import TextOutput, NullNarrationService
from eragvt.game import self_call_setting as sc

@pytest.fixture(scope="module")
def data(): return load_game_data(default_csv_dir())

@pytest.fixture
def ctx(data):
    st=GameState.new(data,GameRng(3)); event_first(st,data)
    st.charas[1].cflag[8]=0; st.charas[1].cstr[4]=""
    return Ctx(st,data,TextOutput(),NullNarrationService())

def drive(g,values):
    next(g)
    for v in values:
        try: g.send(v)
        except StopIteration as e: return e.value
    raise AssertionError("仍等待輸入")

@pytest.mark.parametrize("value,result,codes",[
    ("わたし",0,[86,31,22,0]),("ワタシ",1,[86,31,22,0]),
    ("きゃ",0,[126,0,0,0]),("ヴァ",1,[111,0,0,0]),
    ("ヴぁ",0,[111,0,0,0]),("ーー",1,[95,95,0,0]),
    ("あいうえ",0,[1,2,3,4]),("",1,[0,0,0,0]),
    ("あいうえお",-3,None),("あ"*11,-3,None),("あア",-2,None),
    ("漢字",-1,None),("ゔ",-1,None),(" ",-1,None),("　",-1,None),
])
def test_analysis(ctx,value,result,codes):
    # SELF_CALL.ERB@SELF_CALL_ANALYSIS:307–356／CHECK_SINGLE_SOUND:363–428。
    sc.analyze(ctx,value)
    assert ctx.state.result[0]==result
    if codes is not None: assert [ctx.state.result[i] for i in range(1,5)]==codes

@pytest.mark.parametrize("pron,forms",list(enumerate([
    ("私","わたし","ワタシ"),("私","わたくし","ワタクシ"),
    ("私","あたし","アタシ"),("私","あたい","アタイ"),
    ("妾","わらわ","ワラワ"),("僕","ぼく","ボク"),
    ("俺","おれ","オレ"),("己","おれ","オレ"),("我","われ","われ") ])))
@pytest.mark.parametrize("style",range(3))
def test_presets(ctx,pron,forms,style):
    # FIRSTSETTING_CHARA_SELFCALL:1291–1302、1466–1487。
    assert drive(sc.selfcall_gen(ctx,1),[pron,30+style,99])==99
    c=ctx.state.charas[1]
    assert (c.cflag[8],c.cstr[4])==(pron*5+style,forms[style])

@pytest.mark.parametrize("values",[[6,98],[22,"星","ほし",98],[21,"99","",98]])
def test_cancel_keeps_character(ctx,values):
    ctx.state.charas[1].callname="星"
    assert drive(sc.selfcall_gen(ctx,1),values)==98
    assert ctx.state.charas[1].cflag[8]==0 and ctx.state.charas[1].cstr[4]==""

@pytest.mark.parametrize("value,code",[("わたし",(86+31*1000+22*1000000)*100+99),
    ("キャ",126*100+98),("私",(86+31*1000+22*1000000)*100+99)])
def test_custom(ctx,value,code):
    values=[22,value]+(["わたし"] if value=="私" else [])+[99]
    drive(sc.selfcall_gen(ctx,1),values)
    assert (ctx.state.charas[1].cflag[8],ctx.state.charas[1].cstr[4])==(code,value)

@pytest.mark.parametrize("talents,pron",[((),0),(("かるい性格",),2),(("古風","かるい性格"),4),
    (("オトコ",),5),(("オトコ","乱暴者","古風"),6)])
def test_personality(ctx,talents,pron):
    # :1303–1322 優先男性，再古風，再輕浮；保留已選字形。
    c=ctx.state.charas[1]
    for name in ("オトコ","乱暴者","古風","かるい性格"): c.talent[ctx.data.index_of("TALENT",name)]=int(name in talents)
    drive(sc.selfcall_gen(ctx,1),[32,50,99])
    assert c.cflag[8]==pron*5+2

@pytest.mark.parametrize("text,error",[("漢",-1),("あア",-2),("あいうえお",-3),("😀"*6,-3)])
def test_error_wait_then_retry(ctx,text,error):
    from eragvt.game.input_request import TextInputRequest
    g=sc.selfcall_gen(ctx,1); next(g); g.send(22); g.send("星")
    assert isinstance(g.send(text),TextInputRequest)
    assert ctx.state.result[0]==error
    previous=ctx.state.results[0]
    g.send("")
    assert ctx.state.result[0]==error and ctx.state.results[0]==previous
    g.send("ほし")
    with pytest.raises(StopIteration): g.send(99)
    assert ctx.state.charas[1].cflag[8]==(55+22*1000)*100+99

@pytest.mark.parametrize("name,reading,code",[("あい",None,200199),("星","ほし",2205599)])
def test_character_name(ctx,name,reading,code):
    ctx.state.charas[1].callname=name
    drive(sc.selfcall_gen(ctx,1),[21]+([reading] if reading else [])+[99])
    assert ctx.state.charas[1].cstr[4]==name and ctx.state.charas[1].cflag[8]==code

@pytest.mark.parametrize("invalid",[-1,9,20,23,33,999])
def test_invalid_menu_enters_reading_without_header(ctx,invalid):
    from eragvt.game.input_request import TextInputRequest
    g=sc.selfcall_gen(ctx,1); next(g)
    assert isinstance(g.send(invalid),TextInputRequest)
    assert not any("読みを入力" in line.text for line in ctx.out.lines)
    g.send("あ")
    with pytest.raises(StopIteration): g.send(99)
    # :1490 跳至讀音輸入但不改 CALL_VAR，最終仍存原本的標準稱呼。
    assert (ctx.state.charas[1].cflag[8],ctx.state.charas[1].cstr[4])==(0,"私")

@pytest.mark.parametrize("cancel",["","99"])
def test_cancel_display_and_reading(ctx,cancel):
    drive(sc.selfcall_gen(ctx,1),[22,cancel,"",99])
    assert ctx.state.charas[1].cstr[4]=="私"
    g=sc.selfcall_gen(ctx,1);next(g);g.send(22);g.send("星");g.send(cancel);g.send("")
    assert g.send(99) is None  # 讀音已清空，確認不接受，不自行恢復上一組。
    with pytest.raises(StopIteration): g.send(98)
    assert ctx.state.charas[1].cstr[4]=="私"


def test_list_results_and_static(ctx):
    g=sc.selfcall_gen(ctx,1);next(g);g.send(22);g.send("星");g.send("98")
    assert any("リェ" in line.text for line in ctx.out.lines)
    ctx.state.result[8]=71; ctx.state.results[8]="殘值"
    g.send("きゃ")
    with pytest.raises(StopIteration): g.send(98)
    assert ctx.state.result[0]==98 and ctx.state.results[0]=="ゃ"
    assert ctx.state.result[8]==71 and ctx.state.results[8]=="殘值"
    assert ctx.state.temp.locals[("FIRSTSETTING_CHARA_SELFCALL:PRN_VAR",0)]==126
    # 跨呼叫保留，入口不清除；讀檔則清暫存。
    g=sc.selfcall_gen(ctx,1);next(g)
    assert ctx.state.temp.locals[("FIRSTSETTING_CHARA_SELFCALL:PRN_VAR",0)]==126
    g.close()
    from eragvt.state.savefile import dump_save,load_save
    loaded,_=load_save(dump_save(ctx.state))
    assert not loaded.temp.locals


@pytest.mark.parametrize("packed,kind,display",[(22031086,0,"私"),(22031086,1,"ワタシ"),(4003002001,0,"あいうえ"),(104130128126,1,"キャキュキョイェ"),(111,0,"ヴぁ"),(114,0,"ヴぇ")])
def test_reenter_custom_preserves_packed_code(ctx,packed,kind,display):
    # S48：:1469–1475自訂編碼；SELF_CALL_SUBSTRING:161–165直接取高位，不從顯示字串反推。
    c=ctx.state.charas[1]; code=packed*100+99-kind
    c.cflag[8]=code; c.cstr[4]=display
    for _ in range(3):
        assert drive(sc.selfcall_gen(ctx,1),[99])==99
        assert (c.cflag[8],c.cstr[4])==(code,display)


def test_reading_six_codes_and_catalog_static(ctx):
    # LENGTH:293–295 固定文字18碼→6；SUBSTRING:124–125重新設6而不是4。
    c=ctx.state.charas[1]; c.cflag[8]=(1+2*1000+3*1000**2+4*1000**3+5*1000**4+86*1000**5)*100+99
    assert sc._reading(ctx,1)=="あいうえおわ"
    c.cflag[8]=35
    ctx.state.temp.narr[(("SELF_CALL_SUBSTRING","CAL_VAR"),(0,))]=13060
    assert sc._reading(ctx,1)=="ぼく"
    assert sc._reading(ctx,1)==""


def test_web_status_wait_save(data,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path,narration=None);client=TestClient(app)
    def send(v): return client.post("/api/input",json={"value":v}).json()
    for v in (0,1, 1000,1,0,1,110,12): send(v)
    session=app.state.session
    assert "一人称を設定" in client.get("/").text
    send(22);send("<星>");send("漢")
    assert session.input_kind=="text"
    assert "按 Enter" in client.get("/").text
    client.post("/input",data={"value":""})
    send("ほし");send(99)
    assert "&lt;星&gt;" in client.get("/").text
    assert session.state.charas[1].cstr[4]=="<星>"
    # 真實狀態畫面返回SHOP，再經Web存讀檔。
    for v in (999,200,0,300,0):send(v)
    assert session.state.charas[1].cstr[4]=="<星>"

@pytest.mark.parametrize("pron,reading",list(enumerate(("わたし","わたくし","あたし","あたい","わらわ","ぼく","おれ","",""))))
@pytest.mark.parametrize("style",range(3))
def test_read_existing_presets(ctx,pron,reading,style):
    # SELF_CALL_SUBSTRING:140–165沒有7/8分支；字形2改成片假名。
    ctx.state.charas[1].cflag[8]=pron*5+style
    expected="".join(chr(ord(c)+0x60) for c in reading) if style==2 else reading
    assert sc._reading(ctx,1)==expected

@pytest.mark.parametrize("packed,kind,expected",[(1+2*1000+3*1000**2+4*1000**3,0,"あいうえ"),
    (126+128*1000+130*1000**2+104*1000**3,1,"キャキュキョイェ"),
    (111,0,"ゔぁ"),(112,0,"ヴぃ"),(114,0,"ゔ"),(115,1,"ヴォ")])
def test_read_existing_custom(ctx,packed,kind,expected):
    # CHAR_LIB:700–704的C_ROW直接索引保留原作，112保留原表片假名ヴ，114因索引6超界只剩ゔ。
    ctx.state.charas[1].cflag[8]=packed*100+99-kind
    assert sc._reading(ctx,1)==expected


def test_default_after_custom_resets_style(ctx):
    drive(sc.selfcall_gen(ctx,1),[22,"キャ",50,99])
    assert ctx.state.charas[1].cflag[8]%5==0

@pytest.mark.parametrize("suffix",[98,99])
@pytest.mark.parametrize("talents,pron,display",[((),0,"私"),(("かるい性格",),2,"私"),(("古風","かるい性格"),4,"妾"),(("オトコ",),5,"僕"),(("オトコ","乱暴者","古風"),6,"俺")])
def test_reentered_custom_default_matches_fresh_custom(ctx,suffix,talents,pron,display):
    # :1324–1326／:1399–1400首次自訂將種類設21/22；:1304–1322切回性格預設重設字形0。
    c=ctx.state.charas[1]
    for name in ("オトコ","乱暴者","古風","かるい性格"): c.talent[ctx.data.index_of("TALENT",name)]=int(name in talents)
    c.cflag[8]=126*100+suffix; c.cstr[4]="キャ"
    drive(sc.selfcall_gen(ctx,1),[50,99])
    assert (c.cflag[8],c.cstr[4])==(pron*5,display)

@pytest.mark.parametrize("values,expected",[([98],(12698,"キャ")),([50,98],(12698,"キャ")),([6,99],(30,"俺")),([31,99],(1,"わたし")),([22,"あい",99],(200199,"あい")),([21,99],(2205599,"ほし")),([22,"99","",99],(12698,"キャ"))])
def test_reentry_choice_or_cancel(ctx,values,expected):
    c=ctx.state.charas[1];c.cflag[8]=12698;c.cstr[4]="キャ";c.callname="ほし"
    drive(sc.selfcall_gen(ctx,1),values)
    assert (c.cflag[8],c.cstr[4])==expected


def test_web_reentry_and_saved_reentry(data,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path,narration=None);client=TestClient(app)
    def send(v): return client.post("/api/input",json={"value":v}).json()
    for v in (0,1, 1000,1,0,1,110,12,22,"星","キャキュキョイェ",99): send(v)
    session=app.state.session;code=104130128126*100+98
    assert session.state.charas[1].cflag[8]==code
    for v in (12,99,999,200,0,300,0,110,12,99):send(v)
    assert (session.state.charas[1].cflag[8],session.state.charas[1].cstr[4])==(code,"星")
    c=session.state.charas[1]
    for name in ("オトコ","乱暴者","古風","かるい性格"):c.talent[data.index_of("TALENT",name)]=0
    for v in (12,50,99):send(v)
    assert (c.cflag[8],c.cstr[4])==(0,"私")
