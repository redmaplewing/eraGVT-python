"""S33：依 ENCOUNT 及各 TENTACLE_MOB 原文推導的固定案例。"""
from _gen_driver import as_generator, run_no_input

import pytest

from test_narration_s30 import ctx, data, svc
from eragvt.state import FixedRng
from eragvt.game.battle import core, mob


@pytest.mark.parametrize("number,hp,attack,defense,speed,intellect", [
    (1, 1500, 50, 25, 150, 60), (2, 1250, 150, 50, 50, 50),
    (3, 1500, 50, 25, 150, 60), (101, 800, 100, 200, 50, 50),
    (102, 800, 100, 200, 50, 50), (201, 2000, 100, 50, 25, 50),
    (301, 1500, 50, 50, 100, 60), (501, 1500, 25, 200, 150, 10),
    (601, 800, 50, 50, 80, 10), (701, 750, 200, 35, 225, 50),
    (702, 800, 70, 200, 50, 40), (801, 1500, 150, 150, 100, 50),
    (802, 750, 200, 35, 225, 50), (803, 3000, 100, 100, 50, 40),
    (901, 1000, 50, 50, 200, 100), (902, 1500, 50, 30, 200, 60),
])
def test_stats(ctx, monkeypatch, number, hp, attack, defense, speed, intellect):
    """触手データ/雑魚敵/TENTACLE_MOB_*@*_HP～*_CHISEI；COMMON_TENTACLE_DATA.ERB@TENTACLE_STATUS_HOSEI:348–352。

    固定等級 1；群體 HP 第一次加 0、兩次附加判定不成立；501 三次判定皆不成立。
    """
    monkeypatch.setattr(core, "tentacle_level", lambda st: 1)
    ctx.state.flag[10], ctx.state.flag[11], ctx.state.savestr[13] = 2, number, "MOB"
    ctx.state.rng = FixedRng([1, 1, 1] if number == 501 else [0, 1, 1])
    assert core.tentacle_access(ctx, "HP") == hp * 105 // 100 + 500
    for key, value, bonus in (("KOUGEKI", attack, 100), ("BOUGYO", defense, 100),
                              ("BINSYOU", speed, 100), ("CHISEI", intellect, 10)):
        assert core.tentacle_access(ctx, key) == value * 105 // 100 + bonus


def test_no_candidate(ctx):
    """ENCOUNT.ERB@MOB_TENTACLE_BATTLE:533–552。"""
    ctx.state.mob_flag.clear()
    ctx.state.flag[11] = 0
    ctx.state.rng = FixedRng([77])
    assert mob.mob_tentacle_battle(ctx) == -1
    assert ctx.state.rng.rand(100) == 77


@pytest.mark.parametrize("roll,expected", [(0, 101), (1, 101), (2, 601)])
def test_weighted_encounter(ctx, roll, expected):
    """ENCOUNT.ERB@MOB_TENTACLE_BATTLE:539–543、552、587–600。"""
    st = ctx.state
    st.mob_flag.clear()
    st.mob_flag[(1, 1)], st.mob_flag[(6, 1)] = 2, 1
    st.flag[11] = 0
    st.rng = FixedRng([roll, 71])
    assert mob.mob_tentacle_battle(ctx) == expected
    assert st.flag[10] == 2 and st.flag[11] == expected
    assert st.flag[12] == st.flag[13] and st.flag[15] == st.flag[17] == 0
    assert st.flag[22] == -1
    assert st.rng.rand(100) == 71


@pytest.mark.parametrize("number,roll,expected", [(101,0,3),(101,5,2),(101,40,0),
    (601,0,3),(601,50,2),(601,90,8),(201,0,0),(201,20,2),(201,40,4),
    (201,60,6),(201,80,11),(3,0,7),(3,30,6),(3,80,11),
    (301,0,1),(301,40,0),(301,80,10),(702,0,5),(702,30,4)])
def test_sex_routine_boundaries(ctx, number, roll, expected):
    """各檔 @_SEX_ROUTINE 的閾值（101/601:145–164、201:157–198、3/301:160–182、702:146–164）。"""
    st, c = ctx.state, ctx.state.target_chara
    st.flag[11] = number
    st.tflag[20] = -1
    c.talent[ctx.data.index_of("TALENT", "オトコ")] = 0
    c.talent[ctx.data.index_of("TALENT", "清純派")] = 0
    st.temp.cloth[1], st.temp.cloth[3], st.temp.cloth[4] = 0, 0, 100
    st.rng = FixedRng([roll, 73])
    assert mob.sex_routine(ctx) == expected
    assert st.rng.rand(100) == 73


@pytest.mark.parametrize("number,arg,expected", [(1,1,3),(1,3,11),(2,1,-1),(3,2,0),
    (101,3,-1),(102,1,5),(201,3,11),(301,3,0),(501,2,3),(601,1,3),
    (701,3,-1),(702,2,5),(801,3,11),(802,1,-1),(901,7,0),(902,1,3)])
def test_reaction_reference(ctx, number, arg, expected):
    """各檔 @TENTACLE_MOB_*_REACTION_REF 的 RETURN；901 無條件回傳 0。"""
    ctx.state.flag[11] = number
    assert mob.reaction_ref(ctx,arg) == expected


@pytest.mark.parametrize("number,command,rolls,expected", [(803,3,[],4),(902,0,[],14),
    (902,1,[0,1,0],10),(902,3,[1,0,1],4),(902,5,[0,0,0],11),
    (501,2,[1],4),(101,14,[],0),(2,1,[],-1)])
def test_additional_parts(ctx, number, command, rolls, expected):
    """各檔 @SEXCOM_OPTION_MOB_*：803 的重複 COM3 取先定義（:507–508）。"""
    ctx.state.flag[11] = number
    ctx.state.rng = FixedRng(rolls+[79])
    assert mob.sex_option(ctx,command) == expected
    assert ctx.state.rng.rand(100) == 79


@pytest.mark.parametrize("number,command,expected,scheduled", [
    (102,2000,(0,0,0,0,0,0,2000,0,4000,1000,2000,1000,50),-1),
    (803,2000,(0,0,0,0,50,0,0,0,1000,50,500,2000,200),-1),
    (901,2000,(0,0,0,0,2,0,5,5,5,5,0,1,1),-1),
    (901,2001,(0,0,0,0,2,0,5,5,5,5,0,1,1),-1),
    (901,2002,(0,0,0,0,1000,0,100,500,1000,50,100,50,100),2003),
    (901,2003,(0,0,0,0,1000,0,100,1000,1000,100,1000,50,100),-1),
    (901,2004,(0,0,0,0,1000,0,1000,100,1000,100,1000,50,100),-1),
])
def test_special_command_offsets(ctx, monkeypatch, number, command, expected, scheduled):
    """102@SEXCOM_MOB_102_COM2000:343–435；803:1198–1306；901:1169–1687。
    隔離共用計算後檢查各指令額外量、保留的非 0 RESULT 清除與行動預約。
    """
    from eragvt.game.battle import mob_special, palam
    def zero(ctx, args):
        ctx.state.set_result_x(*([0]*13))
        return [0]*13
        yield
    captured=[]
    monkeypatch.setattr(mob_special,"create_com",zero)
    monkeypatch.setattr(palam,"palam_cal",as_generator(lambda ctx,*values,losebase:captured.append((*values,losebase))))
    ctx.state.flag[11] = number
    ctx.state.result[90] = 9
    assert list(mob_special.special_command(ctx,command,0)) == []
    assert captured == [expected]
    assert ctx.state.result[90] == 0
    assert ctx.state.tflag[20] == command and ctx.state.tflag[17] == scheduled


@pytest.mark.parametrize("strength,senses,weights,shields,lub,expected", [
    (2,(3,1,2),(3,5),(0,0),2500,(1500,7000,1160,260,260)),
    (2,(3,1,2),(3,5),(1,0),2500,(1500,7000,1160,200,130)),
    (2,(3,1,2),(0,5),(0,0),2500,(0,7000,1160,0,0)),
    (1,(1,2,1),(3,0),(0,0),1000,(2040,0,0,60,60)),
    (1,(1,2,1),(3,0),(1,0),1000,(2040,0,0,0,30)),
])
def test_create_com_formulas(ctx, monkeypatch, strength, senses, weights, shields, lub, expected):
    """TENTACLE_MOB_SPCOM.ERB@MOB_CREATE_COM:119–136、192–216。

    第一例：Ｖ值 = 1²×3×300+3×200 = 1500；Ａ值 = 2²×5×300+5×200 = 7000。
    Ｖ苦痛 = 2²×3×20/(Ｃ感覺3+1) = 60；Ａ苦痛 = 2²×ARG:11(3)×50/(2+1) = 200。
    第二例的Ｖ結界讓恐怖成為 60/2+200/2 = 130；第三例確認 ARG:12 不代替 ARG:11。
    """
    from eragvt.game.battle import mob_special, sexcom
    c = ctx.state.target_chara
    for name,value in zip("ＣＶＡ",senses):
        c.abl[ctx.data.index_of("ABL",name+"感覚")] = value
    for name,value in zip("ＶＡ",shields):
        c.base[ctx.data.index_of("BASE",name+"結界耐久力")] = value
    c.palam[ctx.data.index_of("PALAM","潤滑")] = lub
    monkeypatch.setattr(sexcom,"_random",lambda *args:None)
    monkeypatch.setattr(sexcom,"_size",lambda *args:None)
    monkeypatch.setattr(sexcom,"_comex",lambda *args:None)
    monkeypatch.setattr(mob,"message",lambda *args:False)
    monkeypatch.setattr(mob,"sex_type",lambda *args:0)
    args = [0]*19
    args[7],args[11],args[12] = strength,*weights
    assert list(mob_special.create_com(ctx,args)) == []
    assert tuple(ctx.state.result[i] for i in (1,2,8,10,11)) == expected


@pytest.mark.parametrize("action,hunter,roll,expected", [(101,0,0,8),(102,0,4,6),(101,1,4,19),(102,1,1,11)])
def test_mob_victory_research(ctx, monkeypatch, action, hunter, roll, expected):
    """ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:417–435。"""
    from eragvt.game.battle import source_check
    from eragvt.game.battle import encount as actions
    st,c = ctx.state,ctx.state.target_chara
    st.flag[10],st.flag[11] = 2,1
    c.cflag[100] = action
    c.talent[ctx.data.index_of("TALENT","狩人の勘")] = hunter
    st.rng = FixedRng([roll])
    values=[]
    monkeypatch.setattr(actions,"research_progress",lambda ctx,value:values.append(value))
    monkeypatch.setattr(mob,"message",lambda *args:True)
    with pytest.raises(source_check.BeginAfterTrain):
        next(source_check._victory(ctx))
    assert st.tflag[98] == 1
    assert values == [expected]


@pytest.mark.parametrize("function,suffix", [("msg_tentacle_attack","TENTACLE_ATTACK"),("msg_karamituku","KARAMITUKU"),("msg_taieki","TENTACLE_TAIEKI"),("msg_hadou","TENTACLE_HADOU")])
def test_mob_messages_dispatch(ctx, monkeypatch, function, suffix):
    """地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_*:1083、1258、1339、1471：存在即取專用函式。"""
    from eragvt.game.battle import enemy
    ctx.state.flag[10],ctx.state.flag[11] = 2,901
    called=[]
    monkeypatch.setattr(mob,"message",lambda ctx,name:called.append(name) or True)
    getattr(enemy,function)(ctx)
    assert called == [f"MESSAGE_BATTLE_MOB_901_{suffix}"]


@pytest.mark.parametrize("number,command,last,expected", [(1,101,11,1),(1,101,3,0),(1,103,0,1),(2,103,0,0),(701,103,0,0)])
def test_mob_restraint_choices(ctx, monkeypatch, number, command, last, expected):
    """戦闘コマンド(ヒロイン)/COMABLE.ERB@COM_ABLE101:893–905、@COM_ABLE103:991–1020。"""
    from eragvt.game.battle import restraint
    st,c = ctx.state,ctx.state.target_chara
    st.flag[10],st.flag[11],st.tflag[20] = 2,number,last
    c.tcvarn[0],c.tcvarn[12] = 0,0
    c.talent[ctx.data.index_of("TALENT","清純派")] = 0
    c.abl[ctx.data.index_of("ABL","技巧")] = 3
    monkeypatch.setattr(restraint,"is_hole",lambda ctx:True)
    monkeypatch.setattr(restraint,"chara_sex_comable",lambda ctx,n:1)
    assert restraint._com_able_sex(ctx,command,True,(1,2,3))[0] == expected


@pytest.mark.parametrize("rolls,level,points,money,defense", [([0,0,0],1,0,125,50),([10,4,49],9,3,315,103)])
def test_mob_after_rewards(ctx, monkeypatch, rolls, level, points, money, defense):
    """ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:228–260。
    金錢 = (25+RAND:11)×(5+RAND:5)；防衛力 = RAND:50+敵等級/2+50。
    """
    from eragvt.game.battle import after
    st,c = ctx.state,ctx.state.target_chara
    st.savestr[13],st.tflag[98],c.ex[99] = "MOB",1,points
    st.rng = FixedRng(rolls)
    st.flag[852] = 0
    recorded=[]
    for name in ("_battle_marks","get_exp_battle","ninsin_check_after","_transform_enemy_off"):
        monkeypatch.setattr(after,name,as_generator(lambda *args:None) if name == "ninsin_check_after" else lambda *args:None)
    monkeypatch.setattr(after,"ablup",lambda *args:None)
    monkeypatch.setattr(after,"transform",lambda *args:None)
    monkeypatch.setattr(after,"tentacle_level",lambda st:level)
    monkeypatch.setattr(after,"get_syuren",lambda ctx,value:recorded.append(("training",value)))
    monkeypatch.setattr(after,"get_money",lambda ctx,value:recorded.append(("money",value)))
    class ReachedCleanup(Exception): pass
    def cleanup(*args): raise ReachedCleanup
    monkeypatch.setattr(after,"event_battle_reset_costume",cleanup)
    with pytest.raises(ReachedCleanup): list(after.event_end(ctx))
    assert recorded == [("training",10+points*2),("money",money)]
    assert st.flag[852] == defense


def test_mob_901_threshold(ctx, monkeypatch):
    """ゲーム内_戦闘処理/TENTACLE_SYASEI.ERB@TENTACLE_SYASEI_CHECK:90–119。"""
    from eragvt.game.battle import syasei
    st=ctx.state
    st.flag[10],st.flag[11],st.flag[14],st.flag[15] = 2,901,100,150
    st.tflag[3] = 0
    monkeypatch.setattr(syasei,"tentacle_sakusei",lambda *args:(0,0,0,0))
    assert run_no_input(syasei.tentacle_syasei_check(ctx)) == (0,0,0,0)
    assert (st.flag[15],st.tflag[3]) == (50,100)


@pytest.mark.parametrize("number", list(mob.STATS))
def test_encounter_catalog(ctx, number):
    """地の文/MESSAGE_BATTLE.ERB@MESSAGE_ENCOUNT_MOB_BATTLE:15–23；901@GETNAME:9–13。"""
    ctx.state.flag[10],ctx.state.flag[11] = 2,number
    ctx.state.savestr[13] = "MOB"
    ctx.state.tflag[17] = 3
    assert mob.message(ctx,"MESSAGE_ENCOUNT_MOB_BATTLE")
    assert ctx.state.tflag[17] == (-1 if number == 901 else 3)


@pytest.mark.parametrize("number", [701,802])
def test_mob_video_input(ctx, number):
    """701/802@MESSAGE_MOB_*_COM10 呼叫 MESSAGE_SEX_VIDEO_SITE_WINDOW:1343 的 INPUTS。"""
    ctx.state.flag[10],ctx.state.flag[11] = 2,number
    ctx.state.savestr[13] = "MOB"
    ctx.state.rng = FixedRng([5]*1000)
    gen=mob.message_gen(ctx,f"MESSAGE_MOB_{number}_COM10",[0,0])
    next(gen)
    assert any(value==99 for line in ctx.out.lines for _,value in line.buttons)
    with pytest.raises(StopIteration) as end:
        gen.send(99)
    assert end.value.value is True


def test_duplicate_901_message_order(svc):
    """emuera.config:40；Config.cs:330–379；LabelDictionary.cs:58–77；LogicalLine.cs:274–282。"""
    name="MESSAGE_MOB_901_COM2"
    assert svc.catalog.get(name).file.endswith("クズ市民/CITIZEN_1.ERB")
    assert svc.catalog.unsupported_reason(name) is None


@pytest.mark.parametrize("number,rolls,expected", [(102,[],2),(702,[],2),(803,[0,0,0],3),(803,[0,0,1],6),(803,[0,1,0],1),(803,[0,1,1],2),(901,[0],2),(901,[1,0],6),(901,[1,1],1)])
def test_attack_branch_rng(ctx, number, rolls, expected):
    """102/702@*_ATTACK_ROUTINE:133–138；803:191–215；901:121–145。"""
    ctx.state.flag[11],ctx.state.flag[12],ctx.state.flag[13] = number,100,100
    ctx.state.target_chara.tcvarn[10] = 0
    ctx.state.rng=FixedRng(rolls+[97])
    assert mob.attack_routine(ctx) == expected
    assert ctx.state.rng.rand(100)==97


def test_mob_size_fallback(ctx, monkeypatch):
    """GAPING.ERB@SET_TENTACLE_SIZE:1137–1169：缺 MOB 尺寸函式，CATCH 取固定比率。
    等級 1：floor(sqrt(21×30))=25，再 floor(sqrt(25×25))=25。
    """
    from eragvt.game.battle import gaping
    monkeypatch.setattr(gaping,"tentacle_level",lambda st:1)
    ctx.state.flag[850] |= 1<<20  # CONFIG_GLOBAL_MANIAC.ERB@CONFIG_CHECK_MANIAC_F:43–47：反向位元。
    ctx.state.rng=FixedRng([0,0,0,0,97])
    gaping.set_tentacle_size(ctx,2,1,0,0,0)
    assert [ctx.state.temp.tentacle_size[(0,i)] for i in range(4)] == [7,22,22,16]
    assert [ctx.state.temp.tentacle_num[(0,i)] for i in range(4)] == [1,1,1,1]
    assert ctx.state.rng.rand(100)==97


@pytest.mark.parametrize("kind,probability,expected", [(1,20,None),(2,1,1),(7,2,2),(1,7,7)])
def test_original_extraeffect_argument_order(ctx, monkeypatch, kind, probability, expected):
    """ENEMY_ACTION.ERB@ENEMY_ACTION:251；CHARA_STATE_CHANGE.ERB@STATE_CHANGE_EXTRAEFFECT:342–359。
    ARG:1 省略為 0：reference/emuera-1824/Emuera/GameProc/ErbLoader.cs:581–590。
    """
    from eragvt.game.battle import func
    calls=[]
    for number,name in enumerate(("kizetu","hairan","hatujou","dengeki","betobeto","mahi","kizetu_damage"),1):
        monkeypatch.setattr(func,"state_change_"+name,lambda ctx,arg,n=number:calls.append((n,arg)))
    ctx.state.target_chara.tcvarn[14],ctx.state.target_chara.tcvarn[15]=kind,probability
    func.state_change_extraeffect(ctx)
    assert calls == ([] if expected is None else [(expected,0)])


def test_all_mob_message_functions_supported(svc):
    """實際呼叫到的專用顯示函式皆須可解析；遊戲規則函式不加入 catalog 可寫範圍。"""
    names=[name for name,entry in svc.catalog.index.items()
           if entry.rel.startswith("ゲーム内_戦闘処理/触手データ/雑魚敵/") and name.startswith("MESSAGE_")]
    assert len(names)==194
    for name in names:
        assert svc.catalog.unsupported_reason(name) is None,name
