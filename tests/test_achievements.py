"""S57：預期取自 ERB/インターミッション画面/SHOP_TROPHY.ERB。"""
import threading
import pytest
from test_clothing_menu import data, ctx
from eragvt.game.achievements import get_state_trophy, show_trophy
from eragvt.game.battle.core import unlock_achievement
from eragvt.game.wait_bridge import with_achievement_wait
from eragvt.state.constants import GameOption
from eragvt.state.savefile import GlobalStore


@pytest.mark.parametrize("old,disabled,expected", [(0,False,1),(1,False,1),(2,False,2),(0,True,0)])
def test_unlock(ctx,old,disabled,expected):
    """@UNLOCK_ACHIEVEMENT:10–19；非零既有值不能覆寫。"""
    ctx.globals.mem.global_[220]=old
    ctx.globals.mem.global_[88]=123
    ctx.state.flag.set_bit(0,int(GameOption.NO_ACHIEVEMENT_END),disabled)
    unlock_achievement(ctx,220,"腕力自慢")
    assert ctx.globals.mem.global_[220]==expected
    assert ctx.globals.exists() == (old==0 and not disabled)
    assert ctx.globals.mem.global_[88]==123


@pytest.mark.parametrize("value,expected", [(499,()),(500,(220,)),(999,(220,)),(1000,(220,221))])
def test_attack_boundaries(ctx,value,expected):
    """@GET_STATE_TROPHY:399–404，等於門檻也取得。"""
    c=ctx.state.charas[1]
    c.maxbase.clear(); c.abl.clear()
    c.maxbase[ctx.data.index_of("BASE","攻撃")]=value
    get_state_trophy(ctx,1)
    assert tuple(n for n in (220,221) if ctx.globals.mem.global_[n])==expected


def _obtain(ctx):
    unlock_achievement(ctx,220,"腕力自慢")
    yield "after"


@pytest.mark.parametrize("abort", [False,True])
def test_wait_before_save_and_close(ctx,tmp_path,abort):
    """@UNLOCK_ACHIEVEMENT:15–19；PRINTW 確認前既不改GLOBAL也不寫檔。"""
    ctx.globals=GlobalStore.in_dir(tmp_path)
    ctx.globals.mem.global_[88]=123
    ctx.globals.mem.globals_[9]="保留"
    ctx.globals.mem.mob_global[5]=42
    g=with_achievement_wait(_obtain(ctx),ctx.out)
    assert next(g) is None
    assert ctx.globals.mem.global_[220]==0
    assert not ctx.globals.exists()
    if not abort:
        assert g.send(0)=="after"
        restored=GlobalStore.in_dir(tmp_path)
        assert restored.load()
        assert restored.mem.global_[220]==1
        assert restored.mem.global_[88]==123
        assert restored.mem.globals_[9]=="保留"
        assert restored.mem.mob_global[5]==42
    g.close()
    assert getattr(ctx.out,"achievement_wait",None) is None
    assert not any(t.name=="eragvt-achievement-wait" for t in threading.enumerate())
    assert ctx.globals.exists() == (not abort)


def test_pages_wrap_toggle_return(ctx):
    """@SHOW_TROPHY:322–352；模式0兩頁／模式1四頁，換模式回第1頁。"""
    gen=show_trophy(ctx)
    next(gen)
    gen.send(100)
    assert "PAGE < 2/2 >" in "\n".join(l.text for l in ctx.out.lines)
    gen.send(1000)
    assert "PAGE < 1/4 >" in "\n".join(l.text for l in ctx.out.lines)
    assert "腕力自慢" not in "\n".join(l.text for l in ctx.out.lines)
    ctx.globals.mem.global_[220]=1
    gen.send(200); gen.send(100)
    assert "腕力自慢" in "\n".join(l.text for l in ctx.out.lines)
    with pytest.raises(StopIteration):
        gen.send(999)


def test_trophy_mode_retained_until_load(ctx):
    """@SHOW_TROPHY:25–28：MODE為靜態DIM，重入只重設LOCAL頁碼。"""
    from eragvt.text import TextOutput
    from eragvt.state.savefile import dump_save,load_save
    gen=show_trophy(ctx)
    next(gen); gen.send(1000); gen.send(200)
    with pytest.raises(StopIteration): gen.send(999)
    ctx.out=TextOutput()
    gen=show_trophy(ctx)
    next(gen)
    assert 'PAGE < 1/4 >' in '\n'.join(l.text for l in ctx.out.lines)
    gen.close()
    ctx.state,_=load_save(dump_save(ctx.state))
    ctx.out=TextOutput()
    gen=show_trophy(ctx)
    next(gen)
    assert 'PAGE < 1/2 >' in '\n'.join(l.text for l in ctx.out.lines)
    gen.close()


def test_web_restart_cancels_wait(data,tmp_path):
    """真實 /restart 呼叫 close；確認前放棄不能保存或改新局。"""
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path)
    with TestClient(app) as client:
        for value in (0,0,1000,1):
            client.post('/api/input',json={'value':value})
        old=app.state.session
        old._run_gen(_obtain(old._ctx()),old._show_shop)
        assert old.globals.mem.global_[220]==0
        client.post('/restart')
        assert app.state.session is not old
        assert old._turn is None
        assert app.state.session.globals.mem.global_[220]==0
        assert not any(t.name=='eragvt-achievement-wait' for t in threading.enumerate())


def source_thresholds():
    """測試直接讀原作條件，無依賴 Python 的資料表或結果。"""
    import re
    from eragvt.data import default_csv_dir
    path=default_csv_dir().parent/'ERB'/'インターミッション画面'/'SHOP_TROPHY.ERB'
    source=path.read_text(encoding='utf-8-sig')
    found=[]
    for fn in ('GET_STATE_TROPHY','GET_STATE_ABLUP','GET_STATE_EXPUP'):
        body=source.split('@'+fn+',ARG')[1].split('\n@')[0]
        for array,name,threshold,num in re.findall(r'IF (MAXBASE|ABL|EXP):ARG:([^\s]+) >= (\d+)\s+CALL UNLOCK_ACHIEVEMENT\((\d+),',body):
            for delta in (-1,0,1):
                found.append((fn,array,name,int(threshold),int(num),delta))
    return found


@pytest.mark.parametrize('fn,array,name,threshold,num,delta',source_thresholds())
def test_all_source_thresholds(ctx,fn,array,name,threshold,num,delta):
    from eragvt.game import achievements
    c=ctx.state.charas[1]
    c.maxbase.clear(); c.abl.clear(); c.exp.clear()
    getattr(c,array.lower())[ctx.data.index_of('BASE' if array=='MAXBASE' else array,name)]=threshold+delta
    getattr(achievements,fn.lower())(ctx,1)
    assert ctx.globals.mem.global_[num] == int(delta>=0)


@pytest.mark.parametrize('version,retained',[(0,0),(408,1)])
def test_original_global_version_migration(ctx,version,retained):
    """ERB/バージョン間互換処理.ERB@UPDATE_GLOBAL:44–53；不擅修首次存檔版本0。"""
    from eragvt.game.config import update
    ctx.globals.mem.global_[3]=version
    unlock_achievement(ctx,220,'腕力自慢')
    update(ctx.state,ctx.globals,ctx.out,408)
    assert ctx.globals.mem.global_[220]==retained
    assert ctx.globals.mem.global_[3]==408


def test_catalog_save_is_not_rolled_back(ctx):
    from eragvt.narration.service import CatalogNarrationService
    from eragvt.narration.pyfuncs import py_unlock_achievement
    from eragvt.narration.runtime import NotSupported
    from eragvt.data import default_csv_dir
    svc=CatalogNarrationService(default_csv_dir().parent/'ERB',ctx.data)
    ctx.narration=svc
    def run(it):
        py_unlock_achievement(it,[220,'腕力自慢'])
        raise NotSupported('定向測試後續不支援')
    with pytest.raises(NotImplementedError):
        svc._run(ctx,run,'test')
    assert ctx.globals.mem.global_[220]==1
    assert ctx.globals.exists()
    assert svc.journal.depth==0


def test_nested_catalog_web_restart(data,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    from eragvt.narration.service import CatalogNarrationService
    from eragvt.narration.pyfuncs import py_unlock_achievement
    from eragvt.data import default_csv_dir
    app=create_app(data,tmp_path)
    with TestClient(app) as client:
        for value in (0,0,1000,1):
            client.post('/api/input',json={'value':value})
        s=app.state.session
        ctx=s._ctx()
        svc=CatalogNarrationService(default_csv_dir().parent/'ERB',data)
        ctx.narration=svc
        gen=svc._run_waiting(lambda: svc._run(ctx,lambda it: py_unlock_achievement(it,[220,'腕力自慢']),'test'),'s57-test')
        s._run_gen(gen,s._show_shop)
        assert s.globals.mem.global_[220]==0
        client.post('/restart')
        assert s.globals.mem.global_[220]==0
        assert svc.journal.depth==0
        assert not any(t.name in ('eragvt-achievement-wait','erb-event-s57-test') for t in threading.enumerate())
