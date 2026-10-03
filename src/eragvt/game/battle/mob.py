"""雜魚遭遇及敵資料的手工翻寫。

原作路徑相對 source/earGVP/ERB/ゲーム内_戦闘処理/。
敵資料均出自 触手データ/雑魚敵/TENTACLE_MOB_{編號}_*.ERB 的同名函式；
文字由 catalog 讀取，條件與狀態變化在此以 Python 執行。
"""

from ..action import Ctx
from ..config import MOB_CATEGORY, MOB_NAMES, mob_getname
from ..chara_common import charatalent, is_female, is_male
from ..era import div
from . import core


# 各檔 @_HP～@_HOLD：1/3/301:25–103；2:22–96；101/201/601/801/901:24–98；
# 102/701/702/802:23–97；501:26–105；803:83–157；902:92–170。
# HP 基值、射精基值、搾精、油斷、攻、防、敏、知、近、中、遠、拘束。
STATS = {
    1: (1500,480,200,500,50,25,150,60,120,120,120,120),
    2: (1250,980,150,500,150,50,50,50,200,200,200,50),
    3: (1500,480,200,500,50,25,150,60,120,120,120,150),
    101: (800,480,200,500,100,200,50,50,150,150,150,150),
    102: (800,480,200,500,100,200,50,50,150,150,150,150),
    201: (2000,480,100,500,100,50,25,50,200,200,200,200),
    301: (1500,480,200,500,50,50,100,60,100,100,100,150),
    501: (1500,500,30,100,25,200,150,10,120,120,120,180),
    601: (800,480,30,300,50,50,80,10,50,50,50,10),
    701: (750,480,100,250,200,35,225,50,100,85,85,50),
    702: (800,480,100,500,70,200,50,40,100,100,100,150),
    801: (1500,280,25,500,150,150,100,50,100,100,100,250),
    802: (750,480,50,250,200,35,225,50,100,85,85,50),
    803: (3000,1000,20,500,100,100,50,40,150,150,150,150),
    901: (1000,1000,150,500,50,50,200,100,300,200,100,100),
    902: (1500,450,120,500,50,30,200,60,120,120,120,80),
}

# @_PALAM_HOSEI：1/3/301:107–133；2:100–126；101/201/601/801:102–128；
# 102/701/702/802:101–127；501:109–135；803:159–185；901:102–115；902:174–200。
_BASE_PALAM = (100,100,100,100,50,50,50,50,50,50,50,50)
PALAM = {n: _BASE_PALAM for n in STATS}
for _n in (2,102,201,801):
    PALAM[_n] = (100,100,100,100,50,50,50,40,25,50,50,25)
PALAM.update({
    3: (80,80,80,200,50,50,50,50,50,50,50,50),
    301: (200,80,80,80,50,50,50,50,50,50,50,50),
    601: (50,100,50,50,50,50,50,50,50,50,50,50),
    701: (75,75,75,75,25,150,25,25,25,50,125,125),
    702: (50,50,200,50,50,50,50,40,60,60,50,25),
    802: (75,75,75,75,25,150,25,25,25,50,125,125),
    803: (30,30,30,30,50,150,30,30,150,30,200,200),
})


def access(ctx: Ctx, key: str):
    st = ctx.state
    n = st.flag[11]
    row = STATS[n]
    if key in ("NAME", "GETNAME"):
        value = mob_getname(st, n)
        st.results[0] = value
        if key == "NAME":
            ctx.out.print(value)
            return ""
        return value
    if key == "HP":
        value = row[0]
        if n in (1,3,301,902):
            value += st.rng.rand(500)
            for _ in range(2):
                if st.rng.rand(2) == 0:
                    value += st.rng.rand(500)
        elif n == 501:
            for _ in range(3):
                if st.rng.rand(2) == 0:
                    value += 750
        return core.tentacle_status_hosei(st, value, 500)
    if key == "SYASEI":
        return row[1] + (0 if n == 501 else core.tentacle_level(st) * 5)
    if key in ("KOUGEKI", "BOUGYO", "BINSYOU", "CHISEI"):
        return core.tentacle_status_hosei(st, row[("KOUGEKI", "BOUGYO", "BINSYOU", "CHISEI").index(key)+4],
                                          10 if key == "CHISEI" else 100)
    if key in ("SAKUSEI", "YUDAN", "SHORT", "MIDDLE", "LONG", "HOLD"):
        return row[{"SAKUSEI":2,"YUDAN":3,"SHORT":8,"MIDDLE":9,"LONG":10,"HOLD":11}[key]]
    if key == "ATTACK_ROUTINE":
        return attack_routine(ctx)
    raise KeyError(key)


def message(ctx: Ctx, name: str, args: list | None = None) -> bool:
    """原作 TRYCALL 的缺函式無作用；已存在的文字不可執行時明確停止。"""
    catalog = getattr(ctx.narration,"catalog",None)
    if catalog is None:
        raise NotImplementedError("雜魚戰需要原文 catalog")
    if not catalog.exists(name):
        return False
    if not ctx.narration.run_function(ctx,name,args or []):
        raise NotImplementedError(f"雜魚原文函式不可執行：{name}")
    return True


def message_gen(ctx: Ctx, name: str, args: list | None = None):
    """701／802@MESSAGE_MOB_*_COM10 呼叫影片視窗，沿既有等待通道接收 INPUTS。"""
    catalog = getattr(ctx.narration,"catalog",None)
    if catalog is None:
        raise NotImplementedError("雜魚戰需要原文 catalog")
    if not catalog.exists(name):
        return False
    if not (yield from ctx.narration.run_event_gen(ctx,name,args or [])):
        raise NotImplementedError(f"雜魚原文函式不可執行：{name}")
    return True


def mob_tentacle_battle(ctx: Ctx) -> int:
    """ENCOUNT.ERB@MOB_TENTACLE_BATTLE:528–602；亂數池沿用 RANDCHOOSE.ERB。"""
    st, f = ctx.state, ctx.state.flag
    core.clear_randchoose(st)
    if f[11] == 0:
        for cat in range(MOB_CATEGORY):
            for num in range(100):
                for _ in range(max(0, st.mob_flag[(cat, num)])):
                    core.add_randchoose(st, cat * 100 + num)
        if core.choicecount(st) == 0:
            st.result[0] = -1
            return -1
        number = core.randchoose_f(st)
        if number > 0 and f[999] == 1 and f[45] == 0:
            raise NotImplementedError("雜魚遭遇的除錯輸入尚未移植")
        if number == 0:
            st.result[0] = 0
            return 0
        f[10], f[11] = 2, number
    else:
        number = f[11]
    st.savestr[13] = "MOB"
    if number not in MOB_NAMES:
        ctx.out.printl(f"【エラー：TENTACLE_MOB_{number}は定義されていない番号です】")
        f[10] = f[11] = 0
        st.savestr[13] = ""
        st.result[0] = 0
        return 0
    mob_getname(st, number)  # :575；901 的 GETNAME 有狀態變化。
    f[10], f[11] = 2, number
    f[12] = f[13] = int(access(ctx, "HP"))
    f[14], f[15] = int(access(ctx, "SYASEI")), 0
    f[16], f[17] = int(access(ctx, "YUDAN")) + core.tentacle_level(st)*10, 0
    f[22] = -1
    st.result[0] = number
    return number


def attack_routine(ctx: Ctx) -> int:
    """各 @_ATTACK_ROUTINE：1:140–157；3/301:140–154；201:135–150；
    803:191–215、901:121–145、902:204–233；其餘約 :133–150。"""
    st, c = ctx.state, core.tc(ctx)
    n, rand = st.flag[11], st.rng.rand
    if n in (102,702):
        # @_ATTACK_ROUTINE:133–138 沒有 LOCAL 賦值，保留該函式的初始／殘值。
        return 2 if core.get_local(st, f"TENTACLE_MOB_{n}_ATTACK_ROUTINE", 0) < 45 else 0
    if n not in (803,901,902):
        roll = rand(100)
        core.set_local(st, f"TENTACLE_MOB_{n}_ATTACK_ROUTINE", 0, roll)
        if n in (1,3,201,301):
            for bit in (1,2,4):
                if rand(4) == 0:
                    st.tflag[11] |= bit
        if n == 601:
            return 2 if roll < 65 and is_female(ctx.data,c) else 1
        return 2 if roll < (55 if n in (3,301) else 60 if n == 801 else 45) else 0
    if n == 901:
        if st.flag[13] < div(st.flag[12],5) and rand(10) == 0:
            return 4
        if c.tcvarn[10] == 0 or core.t(ctx,c,"変身能力") == 0:
            return 2 if rand(3) == 0 else 6 if rand(6) == 0 else 1
        if rand(3) == 0:
            return 2
        ct = lambda form,name: charatalent(ctx.data,c,form,name)
        if ct(1,"オトコ") != 1 and ct(1,"ふたなり") != 1 and (ct(2,"オトコ") == 1 or ct(2,"ふたなり") == 1):
            return 1
        return 6 if rand(4) == 0 else 1
    if n == 902:
        for bit in (1,2,4):
            if rand(4) == 0:
                st.tflag[11] |= bit
    if c.tcvarn[12] & (core.KIZETU | core.KOSHIKUDAKE) and c.tcvarn[0] in (1,2,3):
        st.tflag[11] |= 1 << (c.tcvarn[0]-1)
    if st.flag[13] < rand(st.flag[12]):
        return 4
    if rand(3) == 0:
        return 6 if n == 902 else 3 if rand(2) == 0 else 6
    return 1 if rand(2) == 0 else 2


def sex_routine(ctx: Ctx) -> int:
    """各 @_SEX_ROUTINE：1:165–206、2:147–202、3/301:160–182、101/601:145–164、
    102:146–198、201:157–198、501:156–211、701:147–198、702:146–164、
    801:148–220、802:147–194、803:220–253、901:150–192、902:238–263。
    保留原作短路、RAND 順序及多值 RETURN。
    """
    from .sexcom import check_holyvirgin
    st, c = ctx.state, core.tc(ctx)
    n, rand = st.flag[11], st.rng.rand
    cl = st.temp.cloth
    outer, outer_def, inner, inner_def = cl[1], cl[2], cl[3], cl[4]
    covered = outer > 90 or inner >= inner_def
    male, female, hole = is_male(ctx.data,c), is_female(ctx.data,c), core.is_hole(ctx)
    holy = lambda: check_holyvirgin(ctx)
    ct = lambda form,name: charatalent(ctx.data,c,form,name)
    base = lambda name: c.base[ctx.data.index_of("BASE",name)]
    if n == 901:
        kiss = lambda: 2001 if ct(0,"オトコ") == 0 and ct(1,"オトコ") > 0 and core.t(ctx,c,"妊娠") > 0 else 2000
        if c.tcvarn[10] == 0:
            return kiss()
        if inner < inner_def:
            if core.is_penis(ctx):
                return 2004
            if all(ct(f,t) != 1 for f in (0,1) for t in ("オトコ","ふたなり")) and (st.tflag[20] == 1 or st.tflag[0] in (13,14)):
                return 2002
            return 0  # 原作此分支不成立即到函式終端。
        if ct(0,"オトコ") != 1 and ct(0,"ふたなり") != 1 and (ct(1,"オトコ") == 1 or ct(1,"ふたなり") == 1) and (c.cflag[1] == 0 or c.base[1] < div(c.maxbase[1],10)):
            return kiss()
        if ((ct(0,"オトコ") == 1 or ct(0,"ふたなり") == 1) or (ct(1,"オトコ") != 1 and ct(1,"ふたなり") != 1)) and rand(4) == 0:
            return 2001
        if rand(6) == 0 and c.base[0] < div(c.maxbase[0],10):
            return 8
        return (0,2,4,6,1)[rand(5)]
    if n == 902:
        if rand(4) == 0:
            if rand(3) == 0 and not holy():
                return 3
            return 5 if rand(2) == 0 else 11
        if rand(3) == 0:
            return 1 if rand(2) == 0 else 7
        if rand(2) == 0:
            return 14 if rand(3) == 0 else 8 if rand(3) == 0 else 9
        return 0
    if n == 803:
        if rand(3) == 0 and outer >= outer_def and inner >= inner_def:
            return 14
        if rand(2) == 0 and outer < outer_def and inner < inner_def and hole:
            if base("Ｖ結界耐久力") > 0 or base("Ａ結界耐久力") > 0:
                return 2000
            return 3 if female and not holy() else 4
        if rand(4) == 0 and hole:
            return 12
        return 8 if rand(2) == 0 else 9
    if n == 102 and st.flag[15] > div(st.flag[14]*3,4) and st.flag[13] < div(st.flag[12],10):
        if outer > 90 or inner >= div(inner_def,4):
            return 14
        return 1 if not hole else 5 if c.cflag[41] == 299 and c.cflag[1] > 0 else 2000
    if n == 701 and outer < 90 and inner < inner_def:
        return 3 if c.tcvarn[12] & core.KIZETU else 9
    if n == 802 and st.flag[72] == 1 and rand(5) == 0:
        return 10
    if n == 2 and male:
        choices = (0,6,4,11) if hole else (0,6,11)
        return choices[rand(len(choices))]
    if n == 801 and (not hole or male):
        # 原作 CASE 2 缺漏，落到 RETURN 1。
        return {0:0,1:2,3:11,4:1,5:9,6:8,7:5}.get(rand(8 if hole else 7),1)
    roll = rand(110 if n == 801 else 100)
    core.set_local(st, f"TENTACLE_MOB_{n}_SEX_ROUTINE", 0, roll)
    if n in (101,601):
        if (roll < (5 if n == 101 else 50) or (st.tflag[20] == 2 and roll < 90)) and female and not holy():
            return 14 if covered else 3
        if roll < (40 if n == 101 else 90) and female:
            return 2
        return 0 if n == 101 else 8
    if n in (3,301):
        strong, weak, final, bound = (7,6,11,30) if n == 3 else (1,0,10,40)
        if roll < bound or (st.tflag[20] == strong and roll < 80):
            return 14 if covered else strong
        return (14 if covered else weak) if roll < 80 else final
    if n in (102,702):
        if roll < (20 if n == 102 else 30) + int(male)*20 or (st.tflag[20] == 5 and roll < 80):
            return 14 if covered else 1 if n == 102 and not hole else 5
        if n == 102 and roll < 50:
            return 0
        if n == 102 and not hole:
            return 1
        st.set_result_x(4,n,1)
        return 4
    if n in (1,501):
        if n == 1 and (roll < 15 or (st.tflag[20] == 3 and roll < 90) or c.tcvarn[12] & core.HAIRAN) and not holy():
            return 14 if covered else 1 if male else 3
        if roll < (40 if n == 1 else 15) and core.t(ctx,c,"母乳体質"):
            return 14 if covered else 1 if not hole else 7
        if roll < (70 if n == 1 else 20):
            return 0
        if roll < (80 if n == 1 else 40):
            return 14 if covered else 1
        if n == 1 or roll < 60:
            return 1 if not hole else 11
        if roll < 80:
            return 14 if covered else 1 if male else 2
        # 501:198 用 TCVAR:12（非 TCVARn），引擎未寫入，值為 0。
        if (roll < 95 or (st.tflag[20] == 3 and roll < 90)) and not holy():
            return 14 if covered else 1 if male else 3
        return 9
    if n in (2,201,701):
        final = 10 if n == 701 else 11
        if roll < 20:
            return 0
        if roll < 40:
            return (0,4,6,final)[rand(4)] if male else 2
        return 4 if roll < 60 else 6 if roll < 80 else final
    if n == 802:
        return 0 if roll < 13 else (0 if male else 2) if roll < 25 else 4 if roll < 37 else 6 if roll < 70 else 10
    if n == 801:
        if roll < 20: return 0
        if roll < 40: return 2
        if roll < 60: return 11
        if roll < 70: return 1
        if roll < 80 and not holy(): return 3
        if roll < 90: return 5
        return 9 if roll < 95 else 8
    raise KeyError(n)


def reaction_ref(ctx: Ctx, arg: int = 0) -> int:
    """各 @_REACTION_REF；803:261–282、902:271–283 為條件分支，其餘為固定回傳表。"""
    from .sexcom import check_holyvirgin
    st, c = ctx.state, core.tc(ctx)
    n = st.flag[11]
    if n == 901:
        return 0
    if n == 902:
        if arg == 2:
            return 3 if st.rng.rand(2) == 0 and not check_holyvirgin(ctx) else 5
        return {1:3,3:11}.get(arg,-1)
    if n == 803:
        if arg == 1: return 14
        if arg == 3: return 12
        if arg != 2: return -1
        base = lambda name: c.base[ctx.data.index_of("BASE",name)]
        if st.temp.cloth[3] >= st.temp.cloth[4]:
            v = c.tcvarn[2] != core.P_V_GUARD and is_female(ctx.data,c) and base("Ｖ結界耐久力") == 0
            if v and base("Ａ結界耐久力") == 0 and not check_holyvirgin(ctx): return 19
            if v and not check_holyvirgin(ctx): return 15
            if core.is_hole(ctx) and base("Ａ結界耐久力") == 0: return 17
        return 2000 if not (c.tcvarn[12] & core.KIZETU) and any(base(p+"結界耐久力") > 0 for p in "ＣＶＡＢ") else 9
    table = {1:(3,3,11),2:(-1,-1,11),3:(0,0,11),101:(3,3,-1),102:(5,5,-1),
             201:(-1,-1,11),301:(0,0,0),501:(3,3,11),601:(3,3,-1),701:(-1,-1,-1),
             702:(5,5,-1),801:(3,3,11),802:(-1,-1,-1)}
    return table[n][arg-1] if arg in (1,2,3) else -1


# 各檔 @SEX_TYPE_MOB_{n}_COM{command} 的存在集合；值見 DIM.ERH:221–224。
_COMMANDS = {
    1:(0,1,3,7,11,14),2:tuple(range(15)),3:(6,7,11,14),101:(0,2,3,14),102:(0,4,5,14,2000),
    201:tuple(range(15)),301:(0,1,10,14),501:(0,1,2,3,7,9,11,14),601:(2,3,8,14),
    701:(0,2,3,4,6,9,10,14),702:(4,5,14),801:tuple(range(15)),802:(0,2,3,4,6,9,10,14),
    803:(3,5,8,9,12,15,16,17,18,19,20,2000,14),901:(0,1,2,4,6,8,14,2000,2001,2002,2003,2004),
    902:(0,1,3,5,7,8,9,11,14),
}


def sex_type(number: int, command: int, default=None):
    if command not in _COMMANDS[number]:
        return default
    if number == 901 and command in (2000,2001): return 1
    if number == 102 and command == 2000: return 2
    if command in (3,5) and number not in (701,802): return 2
    if 15 <= command <= 20: return 2
    if command in (11,12): return 1
    return 0


def sex_option(ctx: Ctx, command: int) -> int:
    """各 @SEXCOM_OPTION_MOB_*；SEX_COMABLE.ERB:17–23 預先 RESULT=0，缺函式時保留 0。
    803:507 與 :637 同名，照 LabelDictionary.cs:58–77 取先定義。
    """
    st,c = ctx.state,core.tc(ctx)
    n,rand = st.flag[11],st.rng.rand
    fixed = {(1,0):15,(2,0):1,(2,1):-1,(3,11):8,(101,0):7,(101,2):1,(102,0):5,
             (102,4):1,(201,0):1,(301,10):1,(501,0):15,(701,0):1,(801,0):15,
             (801,2):15,(802,0):1,(803,3):4,(902,0):14}
    if (n,command) in fixed:
        return fixed[(n,command)]
    if n == 501 and command == 2:
        return (1,4,8)[rand(3)]  # :670–678
    if n == 902 and command in (1,3,5,7):
        return sum(bit for bit in {1:(2,4,8),3:(1,4,8),5:(1,2,8),7:(1,2,4)}[command] if rand(3) == 0)
    if n == 901:
        male = charatalent(ctx.data,c,c.cflag[1],"オトコ") == 1
        choices = None
        if command == 0: choices = (4,8) if male else (2,4,8)
        elif command == 2: choices = (1,4,8)
        elif command == 4: choices = (1,8) if male else (1,2,8)
        elif command == 6: choices = (1,4) if male else (1,2,4)
        elif command == 1:
            choices = (12,4,8) if male else (6,10,12,2,4,8) if core.t(ctx,c,"小さな体躯") == 1 else (6,2,4)
        elif command == 2004: choices = (4,8) if male else (6,2,4,8)
        elif command == 2003: return 14
        elif command in (8,14,2000,2001,2002): return -1
        if choices is not None:
            return choices[rand(len(choices))]
    return 0
