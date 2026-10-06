"""S78 expected 直接由各初期セット@SHOKISET_SELECT 原文推導。"""
import pytest
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.creation_menu import preset_menu
from eragvt.state import GameRng, GameState
from eragvt.state.savefile import GlobalStore
from eragvt.text import TextOutput, NullNarrationService
from tools.sim_adult import adult_data

# 0:18–32、1:18–32、2:18–30、3:21–33、4:19–37、5:20–34、
# 6:169–183、7:172–186、8:186–200、9:19–37、10:22–54、11:19–34、14:18–32。
CASES = [
 (0,(301,302,303),'特装戦隊','特命特捜!'),
 (1,(311,312,313),'マジカルハンター','セットアップ!'),
 (2,(321,322,323),'地球防衛クラブ',None),
 (3,(331,332,333),'侍女式自動人形',None),
 (4,(341,342,343,344,345,346),'ＫＪガールズ',None),
 (5,(351,352,353,354),'TEAM "RWBY"',None),
 (6,(1701,1702,1703),'リリカルハンター','セットアップ!'),
 (7,(1711,1712,1713),'リリカルハンター','セットアップ!'),
 (8,(1741,1742,1743),'リリカルハンター','セットアップ!'),
 (9,(1501,1502,1503,1504,1505),'人妻戦隊','サイガーイン！'),
 (10,(361,362,363,364,365,366),'髙橋退魔団',None),
 (11,(371,372,373,374),'JSKチーム',None),
 (14,(3081,3080,3082,3083),'LGロネスネス',None),
]

@pytest.fixture(scope='module')
def data():return adult_data(load_game_data(default_csv_dir()))

@pytest.fixture
def ctx(data):
 st=GameState.new(data,GameRng(78));st.swap_chara(0,1);st.del_chara(1)
 for _ in range(3):st.add_chara(data,0)
 st.flag[8]=3;st.target=2
 return Ctx(st,data,TextOutput(),NullNarrationService(),GlobalStore())

@pytest.mark.parametrize('preset,ids,title,call',[c for c in CASES if c[0]!=10])
def test_confirm_cancel_and_load(ctx,preset,ids,title,call):
 st=ctx.state;old=st.charas[1:];st.flag[7]=9;st.savestr[12]='保留';st.results[0]='殘值'
 g=preset_menu(ctx);next(g)
 buttons={v for line in ctx.out.lines for _,v in line.buttons}
 assert buttons=={*range(12),14,99}
 # SHOKISET:16–41：不存在／越界重選，否決後不改角色，99返回-1。
 for invalid in (-1,12,13,98,100):g.send(invalid)
 g.send(preset);g.send(-1);g.send(0)
 assert st.charas[1:]==old
 g.send(preset)
 with pytest.raises(StopIteration) as done:g.send(1)
 assert done.value.value==0 and st.result[0]==0
 assert tuple(c.no for c in st.charas[1:])==ids
 assert st.flag[8]==len(ids) and st.target==2
 assert st.flag[5]==1 and st.savestr[10]==title
 assert (st.flag[7],st.savestr[12])==((9,'保留') if call is None else (1,call))
 assert st.results[0]=='殘值'
 assert all(c.abl[ctx.data.index_of('ABL','レベル')]>=1 for c in st.charas[1:])
 before=st.to_json();g=preset_menu(ctx);next(g)
 with pytest.raises(StopIteration) as done:g.send(99)
 assert done.value.value==-1 and st.result[0]==-1
 before['result']['0']=-1
 assert st.to_json()==before

@pytest.mark.parametrize('preset', [6,7,8])
@pytest.mark.parametrize('roll',range(4))
def test_dynamic_description_rng_font_and_cancel(ctx,preset,roll):
 # 各 SETUMEI:8 RAND:4；每 CASE SETFONT→AA→SETFONT→標題；取消重入重抽。
 class Rng:
  calls=[]
  def rand(self,n):self.calls.append(n);return roll
 rng=Rng();ctx.state.rng=rng
 g=preset_menu(ctx);next(g);start=len(ctx.out.lines);g.send(preset)
 assert rng.calls==[4]
 lines=ctx.out.lines[start+1:]
 captions={6:('【三人娘】','【八神はやてJS】','【フェイト・テスタロッサJS】','【高町なのはJS】'),
           7:('【フェイト＆はやて】','【八神はやてJD】','【フェイト・テスタロッサJD】','【高町なのはJD】'),
           8:('【オリヴィエ・ゼーゲプレヒト】','【アインハルト・ストラトス（変身後）】','【高町ヴィヴィオ（変身後）】','【ヴィヴィオ＆アインハルト（変身前）】')}
 assert [l.text for l in lines if l.text.startswith('【')]==[captions[preset][roll]]
 # 原文AA的PRINTL行數，SETFONT省略引數後的標題不帶AA字型。
 counts={6:(31,39,27,35),7:(28,31,38,38),8:(30,34,43,41)}
 assert sum(any(s.font for p in l.parts for s in p.segments) for l in lines)==counts[preset][roll]
 assert any(s.font=='ＭＳ Ｐゴシック' for l in lines for p in l.parts for s in p.segments)
 assert all(s.font is None for l in lines[-3:] for p in l.parts for s in p.segments)
 g.send(0);g.send(preset)
 assert rng.calls==[4,4]


def test_select_order_and_double_csvfix(ctx,monkeypatch):
 from eragvt.game import opening
 calls=[]
 def fix(st,data):calls.append((tuple(c.no for c in st.charas[1:]),st.flag[8],st.target))
 monkeypatch.setattr(opening,'shokiset_csvfix',fix)
 g=preset_menu(ctx);next(g);g.send(14)
 with pytest.raises(StopIteration):g.send(1)
 assert calls==[((3081,3080,3082,3083),4,2)]*2


def test_preset10_retains_explicit_stop(ctx):
 # SHOKISET:29–33已刪舊角色；未實作套組10不能偽裝為成功。
 g=preset_menu(ctx);next(g);g.send(10);g.send(0)
 assert ctx.state.charanum==4
 g.send(10)
 with pytest.raises(NotImplementedError,match='SHOKISET_SELECT_10'):g.send(1)
 assert ctx.state.charanum==1 and ctx.state.flag[8]==0

@pytest.mark.parametrize('preset,ids,title,call',[c for c in CASES if c[0]!=10])
def test_session_start_to_shop(data,tmp_path,preset,ids,title,call):
 from eragvt.game.session import GameSession
 s=GameSession(data,tmp_path,narration=NullNarrationService(),rng=GameRng(78))
 for value in (0,1,200,preset,1,1000,1,0):s.input(value)
 assert s.phase.name=='SHOP'
 assert tuple(c.no for c in s.state.charas[1:])==ids
 assert s.state.target==1
 # EVENTFIRST:263–266／DIM.ERH:24最大6人隊列；SET_LIMIT_DAY:445每增1人減1天。
 assert [c.cflag[999] for c in s.state.charas[1:]]==[1]*len(ids)
 assert s.state.flag[2]==14-len(ids)
 assert all([c.base[40],c.base[41],c.maxbase[40],c.maxbase[41]]==[25]*4 for c in s.state.charas)


def test_extraction_is_reproducible():
 import runpy
 from pathlib import Path
 root=Path(__file__).parents[1]
 extract=runpy.run_path(str(root/'tools/extract_initial_presets.py'))['extract']
 assert extract()==(root/'src/eragvt/game/initial_preset_data.py').read_text(encoding='utf-8')


def test_swap_presets_then_reenter_editor(ctx):
 from eragvt.game.creation_menu import creation_menu
 g=creation_menu(ctx);next(g)
 for preset,ids,title,call in CASES:
  if preset==10:continue
  for value in (200,preset,1):g.send(value)
  assert tuple(c.no for c in ctx.state.charas[1:])==ids
  assert ctx.state.flag[8]==len(ids)
  # FIRSTSETTING_CHARA_MAIN:234–353：選完套組仍可開個別編輯99確定。
  g.send(1);g.send(99)
  assert tuple(c.no for c in ctx.state.charas[1:])==ids


@pytest.mark.parametrize('preset,ids,title,call',[c for c in CASES if c[0]!=10])
def test_direct_preset_helper(ctx,preset,ids,title,call):
 from eragvt.game.opening import chara_make_main_preset
 chara_make_main_preset(ctx.state,ctx.data,preset,ctx=ctx)
 assert tuple(c.no for c in ctx.state.charas[1:])==ids
 assert ctx.state.flag[8]==len(ids)


def test_web_dynamic_description(data,tmp_path):
 from fastapi.testclient import TestClient
 from eragvt.web import create_app
 app=create_app(data,tmp_path,rng_factory=lambda:GameRng(78),narration=NullNarrationService())
 client=TestClient(app)
 for v in (0,1,200,6):assert client.post('/api/input',json={'value':v}).status_code==200
 html=client.get('/').text
 assert 'font-family:' in html and 'ＭＳ Ｐゴシック' in html
 for v in (0,14,1,1,99,1000,1,0):assert client.post('/api/input',json={'value':v}).status_code==200
 assert app.state.session.phase.name=='SHOP'


def test_font_survives_button_splitting_and_catalog_rollback(ctx):
 from eragvt.narration.service import _Tx
 out=ctx.out
 out.set_font('ＭＳ Ｐゴシック')
 tx=_Tx(ctx)
 out.set_font();out.printl('discard')
 tx.rollback()
 out.printl('[0] 否  [1] 是')
 assert len(out.lines[-1].parts)==2
 assert all(s.font=='ＭＳ Ｐゴシック' for p in out.lines[-1].parts for s in p.segments)
 out.set_font();out.printl('預設')
 assert out.lines[-1].parts[0].segments[0].font is None
