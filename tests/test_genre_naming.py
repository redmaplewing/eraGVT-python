"""S53：expected 由 FIRSTSETTING_RANDOMNAMING:450–507、DEFAULT:169–210／919–960 推導。"""
from pathlib import Path
from copy import deepcopy
import pytest
from eragvt.data import default_csv_dir, load_game_data
from eragvt.state import GameState, GameRng, FixedRng
from eragvt.game.genre_naming import random_naming_from_genre, genre_name_tail

@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())

class Rolls(FixedRng):
    def __init__(self, values):
        super().__init__(values)
        self.bounds = []
    def rand(self, n):
        self.bounds.append(n)
        return super().rand(n)

@pytest.mark.parametrize("genre,expected", [(1,"マジカル"),(2,"サン"),(3,"レッド"),(4,"ピーチ"),
    (5,"メロディ"),(6,"ガーネット"),(7,"ガール"),(8,"ブレイド")])
@pytest.mark.parametrize("random_genre", [False, True])
def test_all_genres_and_empty_redraw(data, genre, expected, random_genre):
    # 各組 49 均空：先空字重抽，不能壓縮為有效名稱表後抽取。
    st=GameState.new(data, Rolls(([genre-1] if random_genre else [])+[49,0]))
    st.result[0],st.result[1]=98,76
    st.results[0],st.results[1]="舊值","保留"
    assert random_naming_from_genre(st,data,9 if random_genre else genre)==expected
    assert st.rng.bounds==([8] if random_genre else [])+[50,50]
    assert st.rng.snapshot()==[]
    assert (st.result[0],st.result[1],st.results[0],st.results[1])==(0,76,expected,"保留")

@pytest.mark.parametrize("raw,expected", [("コレクター・","コレクター"),("前・中・","前・中"),
    ("末尾・・","末尾・"),("・",""),("末尾・\n","末尾\n"),("末尾・\r\n","末尾・\r\n")])
def test_replace_regex_and_static_local(data,raw,expected):
    # REPLACE "・$" 只刪一個結尾符號；LOCALS 保留刪除前字串，非 RESULTS 殘值。
    data=deepcopy(data);data.str_defaults[500]=raw
    st=GameState.new(data,Rolls([0]))
    assert random_naming_from_genre(st,data,1)==expected
    st.results[0]="不同殘值"
    assert random_naming_from_genre(st,data,10)==expected
    assert st.rng.bounds==[50]

@pytest.mark.parametrize("genre", [-1,0,10,999])
def test_unknown_genre_initial_local_empty(data,genre):
    st=GameState.new(data,Rolls([]));st.results[0]="殘值"
    assert random_naming_from_genre(st,data,genre)==""
    assert st.rng.bounds==[]

@pytest.mark.parametrize("generic", [False,True])
@pytest.mark.parametrize("rolls,expected", [([0,1],"トランス"),([0]*11,"マジカル")])
def test_duplicate_retry_limit_and_fields(data,generic,rolls,expected):
    st=GameState.new(data,Rolls(rolls));st.add_chara(data,0);st.add_chara(data,0)
    st.flag[820]=1;st.savestr[11]="冠"
    st.charas[2].cstr[0]="冠マジカル"
    st.charas[3].cstr[0]="冠マジカル"
    c=st.charas[1];c.cstr[201]="原上";c.cstr[202]="原下"
    assert genre_name_tail(st,data,1,generic=generic)==expected
    assert c.cstr[0]=="冠"+expected
    assert (c.cstr[201],c.cstr[202])==(("冠",expected) if generic else ("原上","原下"))
    assert st.rng.bounds==[50]*len(rolls) and st.rng.snapshot()==[]

@pytest.mark.parametrize("generic", [False,True])
def test_duplicate_ignores_master_and_self(data,generic):
    st=GameState.new(data,Rolls([0]));st.flag[820]=1
    st.charas[0].cstr[0]="マジカル"
    st.charas[1].cstr[0]="マジカル"
    assert genre_name_tail(st,data,1,generic=generic)=="マジカル"
    assert st.rng.snapshot()==[]

def test_csv_existing_extraction(data):
    # 直接由原作 CSV 重讀全部 8 × 50 格，比對既有 CSV 載入結果，不維護重複名字表。
    rows={}
    for line in (default_csv_dir()/"Str.csv").read_text(encoding="utf-8-sig").splitlines():
        key,sep,value=line.partition(",")
        if key.isdecimal(): rows[int(key)]=value
    for base in range(500,1201,100):
        for offset in range(50):
            assert data.str_defaults.get(base+offset,"")==rows.get(base+offset,"")

@pytest.mark.parametrize("genre", range(1,10))
def test_generic_actual_opening_uses_global_genre(data,genre):
    from eragvt.game.opening import event_first
    from eragvt.state.savefile import GlobalStore
    store=GlobalStore();store.mem.global_[8]=genre
    store.mem.globals_[16]="冠"
    store.mem.global_[21]=1  # DEFAULT:12–13 指定人類，:531–534 必有變身能力。
    st=GameState.new(data,GameRng(7))
    event_first(st,data,store=store)
    # DEFAULT:934–936 三格同步；名字來源由 CSV 指定區間限定。
    bases=range(500,1201,100) if genre==9 else [400+genre*100]
    candidates={data.str_defaults.get(base+i,"").removesuffix("・") for base in bases for i in range(50)}-{ "" }
    for c in st.charas[1:]:
        if c.talent[data.index_of("TALENT","変身能力")]==1:
            assert c.cstr[202] in candidates
            assert (c.cstr[0],c.cstr[201])==("冠"+c.cstr[202],"冠")
            assert c.cstr[1]==c.cstr[0] and c.cflag[2]==c.cflag[3]==1
    assert st.temp.genre_name_local != ""

@pytest.mark.parametrize("collision", [False,True])
def test_named_character_actual_initialize(data,collision):
    from eragvt.game.opening import chara_make_initialize
    st=GameState.new(data,Rolls([0,1] if collision else [0]))
    st.add_chara(data,301);sel=st.charanum-1;c=st.charas[sel]
    st.flag[820]=1;st.savestr[11]="冠"
    c.cstr[0]="";c.cstr[1]="";c.cstr[3]="保留名乘"
    c.cstr[201]="保留上";c.cstr[202]="保留下"
    c.talent[data.index_of("TALENT","変身能力")]=1
    if collision:st.charas[1].cstr[0]="冠マジカル"
    chara_make_initialize(st,data,sel)
    expected="冠トランス" if collision else "冠マジカル"
    assert (c.cstr[0],c.cstr[1],c.cstr[3])==(expected,expected,"保留名乘")
    assert (c.cstr[201],c.cstr[202])==("保留上","保留下")
    assert st.rng.snapshot()==[]

@pytest.mark.parametrize("generic", [False,True])
def test_empty_tail_does_not_overwrite_fields(data,generic):
    st=GameState.new(data,Rolls([]));st.flag[820]=10
    c=st.charas[1];c.cstr[0]="原名";c.cstr[201]="原上";c.cstr[202]="原下"
    assert genre_name_tail(st,data,1,generic=generic)==""
    assert (c.cstr[0],c.cstr[201],c.cstr[202])==("原名","原上","原下")

def test_static_local_not_saved(data):
    from eragvt.state.savefile import dump_save,load_save
    st=GameState.new(data,Rolls([10]))
    assert random_naming_from_genre(st,data,1)=="コレクター"
    loaded,_=load_save(dump_save(st))
    assert loaded.temp.genre_name_local==""
    assert random_naming_from_genre(loaded,data,10)==""

@pytest.mark.parametrize("preset", [0,1])
def test_web_global_genre_and_save_load(data,tmp_path,preset):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    from eragvt.state.savefile import GlobalStore,GameIdentity
    store=GlobalStore.in_dir(tmp_path,GameIdentity.from_data(data))
    store.mem.global_[8]=3
    store.mem.globals_[16]="冠"
    store.mem.global_[21]=1  # DEFAULT:12–13 指定人類，:531–534 必有變身能力。
    store.save()
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(7),narration=None)
    client=TestClient(app)
    def send(value):
        response=client.post("/api/input",json={"value":value})
        assert response.status_code==200
        return response.json()
    send(0);send(preset);send(1000)
    assert send(1)["phase"]=="shop"
    st=app.state.session.state
    assert st.flag[820]==3
    names=[c.cstr[0] for c in st.charas[1:]]
    if preset==0:
        colors={data.str_defaults[700+i] for i in range(8)}
        assert all(c.cstr[202] in colors for c in st.charas[1:])
    # 初期角色的 CSTR:0 未設定，DEFAULT:171–183 使用同一主題，但不寫 201／202。
    else:
        colors={data.str_defaults[700+i] for i in range(8)}
        assert all(name in {"冠"+color for color in colors} for name in names)
    send(200);send(0);send(300)
    assert send(0)["phase"]=="shop"
    assert [c.cstr[0] for c in app.state.session.state.charas[1:]]==names
    assert app.state.session.state.temp.genre_name_local==""
