"""雜魚特殊指令：原作 触手データ/雑魚敵/TENTACLE_MOB_SPCOM.ERB 的原生 Python 翻寫。"""

from ..action import Ctx
from ..era import div, times
from . import core, mob, sexcom


def create_com(ctx: Ctx, a: list[int]):
    """TENTACLE_MOB_SPCOM.ERB@MOB_CREATE_COM:34–332；a 對應 ARG:0～18。"""
    from .cloth import cloth_battle_damage
    from .syasei import tentacle_syasei_up

    st,c = ctx.state,core.tc(ctx)
    abl = lambda name: core.abl(ctx,c,name)
    base = lambda name: c.base[ctx.data.index_of("BASE",name)]
    ex = lambda name: core.exp(ctx,c,name)
    add = lambda name,value: core.add_exp(ctx,c,name,value)
    sexcom._random(ctx,a[2],a[1])  # :39–41
    if core.t(ctx,c,"清純派") > 0 and c.tcvarn[2] != 100 and a[8] > 0:
        yield from sexcom.auto_v_defence(ctx,st.target)
    if a[4] > 0: st.tflag[4] = a[4]
    if a[3] > 0: st.tflag[3] += a[3]
    if a[5] > 0: tentacle_syasei_up(ctx,a[5])
    sexcom._size(ctx,a[0])
    mob.message(ctx,f"MESSAGE_MOB_{st.flag[11]}_COM{a[0]}",[st.temp.ex_com,st.temp.sh_com])
    if a[6] > 0: cloth_battle_damage(ctx,a[6])
    L = [0]*13
    can_v = base("Ｖ結界耐久力") <= 0 and (c.tcvarn[2] != core.P_V_GUARD or a[9]&1)
    if a[8] in (1,2) and core.t(ctx,c,"処女") > 0 and can_v:
        L[10] = 10000
        if a[8] == 1:
            sexcom.lostvirgin(ctx)
        else:
            c.talent[ctx.data.index_of("TALENT","処女")] = -1
            c.cflag[206],c.tcvarn[1] = 2,1
    strength = a[7]
    factor,constant = (60,100) if strength == 0 else (150,80) if strength == 1 else (300,200)
    sense = [abl(p+"感覚") for p in "ＣＶＡＢ"]
    shield = [int(base(p+"結界耐久力") > 0) for p in "ＣＶＡＢ"]
    for i in range(4):
        if a[10+i] > 0:
            L[i] = min(sense[i]*sense[i],25)*a[10+i]*factor + a[10+i]*constant
    if a[10] > 0:
        if core.is_manly(ctx) or core.t(ctx,c,"ふたなり") > 0:
            L[0] += 500*(strength+1)
        if sense[0] < 3:
            pain = div(strength*strength*a[10]*40,sense[0]+1)
            L[10] += pain*(1-shield[0])
            L[11] += pain
    typ = mob.sex_type(st.flag[11],a[0],0)
    lub = c.palam[ctx.data.index_of("PALAM","潤滑")]
    if a[11] > 0:
        add("Ｖ経験",1)
        # :130–136 的分母是Ｃ感覺，照原文保留。
        for condition in (sense[1] < 3,lub < 2000):
            if condition:
                pain = div(strength*strength*a[11]*20,sense[0]+1)
                L[10] += pain*(1-shield[1])
                L[11] += div(pain,1+shield[1])
        if c.tcvarn[2] == core.P_V_GUARD and not a[9]&1:
            L[1] = div(L[1],4)
        if typ&2:
            L[10] += (5000 if lub < 1000 else 1000 if lub < 2000 else 0)*(1-shield[1])
            if can_v:
                add("Ｖ経験",1)
                if a[9]&2:
                    add("Ｖ拡張経験",1)
                    add("Ｖ経験",3)
    if a[12] > 0:
        add("Ａ経験",1)
        if sense[2] < 3:
            # :203–204 故意保留 ARG:11 及Ｖ結界分母。
            pain = div(strength*strength*a[11]*50,sense[2]+1)
            L[10] += pain*(1-shield[2])
            L[11] += div(pain,1+shield[1])
        L[8] += (min(sense[2]*sense[2],25)*120+100+(sense[2]*100+1400 if sense[2]>=5 else 0))*(1 if strength==0 else 2)
        if typ&2 and not shield[2]:
            add("Ａ経験",1)
            if a[9]&2:
                add("Ａ拡張経験",1)
                add("Ａ経験",3)
    for i,part in ((1,"Ｖ"),(2,"Ａ")):
        if a[10+i] > 0 and a[9]&2:
            e = ex(part+"拡張経験")
            tier = 0 if e < 3 else 1 if e < 5 else 2 if e < 8 else 3
            L[i] = times(L[i],("0.10","0.50","0.80","1.00")[tier])
            for j,values in ((8,(400,800,1600,4000)),(9,(40,80,160,400)),(10,(800,640,320,80)),(11,(1600,1280,640,160))):
                value = a[10+i]*values[tier]
                L[j] += value*(1-shield[i]) if j==10 else div(value,1+shield[i])
    maso,sub,service = abl("マゾっ気"),abl("従順"),abl("奉仕精神")
    if a[14] > 0:
        L[8] += min(maso*maso,25)*a[14]*150+a[14]*100
        L[11] += a[14]*(2000 if sub<4 and maso<4 else 200 if sub<4 or maso<4 else 20)
        add("苦痛快楽経験",1)
    if a[15] > 0: L[5] += min(sub*sub,25)*a[15]*15+a[15]*40
    if a[16] > 0: L[6] += div(min(service*service,25)*a[16]*15,2)+a[16]*4
    if a[17] > 0:
        L[7] += min(service*service,25)*a[17]*15+a[17]*10
        L[9] += min(abl("露出癖"),5)*a[17]*100+a[17]*400
        L[11] += min((5-service)*(5-service),25)*a[17]*15+a[17]*10
        add("露出快楽経験",1)
    if a[18] > 0:
        L[8] += min(sub*sub,25)*a[18]*40+a[18]*20
        if service >= 3:
            bonus = (500,200) if service<4 else (1000,500) if service<5 else (2000,1000)
            L[5] += bonus[0]
            L[6] += bonus[1]
        add("奉仕快楽経験",1)
    sexcom._comex(ctx,L,a[2],strength)
    st.set_result_x(*L)
    return L


def special_command(ctx: Ctx, command: int, option: int):
    """102@SEXCOM_MOB_102_COM2000:343–435；803:1198–1306；901:1169–1687。"""
    from .palam import palam_cal
    st,c = ctx.state,core.tc(ctx)
    n = st.flag[11]
    # ARG:2～18 與 RESULT:4/6/7/8/9/10/11/12 的固定額外值。
    if n == 102 and command == 2000:
        body = [4,100,4,2000,2,2,0,2,0,0,5,0,0,0,5,0,0]
        extra = (0,2000,0,4000,1000,2000,1000,50)
    elif n == 803 and command == 2000:
        local = core.get_local(st,"SEXCOM_MOB_803_COM2000",3)+10
        core.set_local(st,"SEXCOM_MOB_803_COM2000",3,local)
        bits = sum(1<<i for i in range(4) if c.base[30+i] > 0)
        body = [bits,local,(8 if bits&8 else 0)+(64 if bits&7 else 0),10,
                st.rng.rand(11)+st.rng.rand(11)+10,1,0,0,2,2,2,2,6,0,1,1,2]
        extra = (50,0,0,1000,50,500,2000,200)
    elif n == 901 and command in (2000,2001):
        body = [0,30,0,20,0,0,0,0,0,0,0,0,1,0,6,3,4]
        extra = (2,5,5,5,5,0,1,1)
        core.add_exp(ctx,c,"フェラ経験",1)
    elif n == 901 and command == 2002:
        body = [1,30,0,0,0,0,0,0,6,0,0,0,0,0,0,3,0]
        extra = (1000,100,500,1000,50,100,50,100)
    elif n == 901 and command == 2003:
        st.flag[13] = 5
        c.talent[ctx.data.index_of("TALENT","ふたなり")] = 2
        index = ctx.data.index_of("BASE","射精")
        c.base[index] += c.maxbase[index]*5
        c.nowex[ctx.data.index_of("EX","Ｃ絶頂")] += 1
        body = [1,100,0,5000,0,2,0,0,8,8,8,8,2,0,0,3,0]
        extra = (1000,100,1000,1000,100,1000,50,100)
    elif n == 901 and command == 2004:
        body = [1,30,0,50,0,2,0,0,5,2,2,2,5,0,3,3,0]
        extra = (1000,1000,100,1000,100,1000,50,100)
    else:
        return  # SEX_COMABLE:590 的 TRYCALLFORM 不存在時無作用。
    st.result.clear()
    yield from create_com(ctx,[command,option,*body])
    st.tflag[20],st.tflag[17] = command,2003 if n==901 and command==2002 else -1
    for index,value in zip((4,6,7,8,9,10,11,12),extra):
        st.result[index] += value
    palam_cal(ctx,*[st.result[i] for i in range(12)],losebase=st.result[12])
