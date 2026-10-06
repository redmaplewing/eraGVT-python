"""S59 使用者裁決；舊檔仍依 ERB/バージョン間互換処理.ERB@UPDATE_GLOBAL。"""
import pytest
from test_clothing_menu import data
from eragvt.state.savefile import GameIdentity, GlobalStore
from eragvt.game.session import GameSession
from eragvt.state import GameRng
from eragvt.text import NullNarrationService


@pytest.mark.parametrize("existing", ["missing", "broken", "old", "current"])
def test_only_new_global_gets_version(data,tmp_path,existing):
    identity=GameIdentity.from_data(data)
    path=tmp_path/"global.json"
    if existing=="broken":
        path.write_bytes(b"broken")
    elif existing in ("old","current"):
        old=GlobalStore(path,identity)
        old.mem.global_[3]=0 if existing=="old" else identity.version
        old.mem.global_[113]=5
        old.save()
    store=GlobalStore(path,identity)
    assert store.mem.global_[3]==(identity.version if existing=="missing" else 0)
    assert store.load()==(existing in ("old","current"))
    assert store.mem.global_[3]==(identity.version if existing in ("missing","current") else 0)
    assert store.mem.global_[113]==(5 if existing in ("old","current") else 0)
    assert store.mem.global_[110]==0
    assert store.mem.global_[11]==0
    assert store.mem.mob_global[(0,1)]==0


def test_clean_session_first_achievement_survives_restart(data,tmp_path):
    from eragvt.game.achievements import unlock
    from eragvt.game.action import Ctx
    from eragvt.text import TextOutput
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for value in (0,1,1000,1,0): s.input(value)
    unlock(Ctx(s.state,data,TextOutput(),NullNarrationService(),s.globals),220,"腕力自慢")
    assert s.globals.mem.global_[3]==s.identity.version
    s2=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for value in (0,1,1000,1,0): s2.input(value)
    assert s2.globals.mem.global_[220]==1
    assert s2.globals.mem.global_[3]==s2.identity.version
