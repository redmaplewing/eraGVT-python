"""角色強化：ERB/インターミッション画面/SHOP_CHARA_POWERUP.ERB@CHARA_POWERUP。

分配暫存留在等待中的 generator；確認時才修改角色。輸入及返回共用 RESULT。
"""
from .battle.core import seikaku_hosei_palam
from .chara_common import (baseup_cal_shield, cal_shield, charatalent, feat_bonus,
                           level_status, levelstatus_up, seikaku_check)
from .colorbar import color_bar, percent_cal
from .era import div, format_curly, format_percent, limit
from .gather import chara_list
from .input_request import input_number


_BASE = (0, 1, 2, 10, 11, 12, 13)
_RAW = (50, 51, 52, 10, 11, 12, 13)
_MAG = (50, 50, 5, 5, 5, 5, 5)
_MARK_PALAM = (13, 16, 14, 17, 15)


def _preview(ctx, c, bonuses):
    """@CHARA_POWERUP:543–561，成長項以加點後基礎值計算。"""
    values = []
    lv = c.abl[ctx.data.index_of('ABL', 'レベル')]
    for i, slot in enumerate(_RAW):
        raw = c.base[slot] + bonuses[i] * _MAG[i]
        level, growth, cap = lv, 50, 9999
        if i < 2:
            growth, cap = 400 + div(raw - 1000, 5), 99999
        elif i == 2:
            level, growth = div(lv, 3) + 1, 10 + div(raw - 100, 2)
        values.append(levelstatus_up(raw + feat_bonus(ctx.data, c, i), level, growth, cap))
    return values


def _button(out, text, blocked=False, selected=False, owned=False):
    out.set_color((80,255,80) if owned else (255,255,0) if selected else
                  (128,128,128) if blocked else (240,240,255))
    out.print(text)
    out.reset_color()


def _show(ctx, c, bonuses, costs, price, preview, digits, left, right):
    """@CHARA_POWERUP:91–331；灰色僅顯示，實際允許條件另依輸入分支。"""
    st, out, data = ctx.state, ctx.out, ctx.data
    points = c.juel[data.index_of('JUEL','修練P')]
    total = sum(costs) + 30 * bonuses[12:16].count(1)
    out.printl()
    out.printl(f'{c.callname}の{data.names["PALAM"][20]}  {points}P')
    out.drawline()
    out.printl('　　 '+'\u2000'*div(digits,2)+'強化後 '+'\u2000'*digits+'基礎値　 消費修練P')
    for i, slot in enumerate(_BASE):
        raw = c.base[_RAW[i]] + feat_bonus(data,c,i)
        out.print(format_percent(data.names['BASE'][slot],6,True)+'：')
        if preview[i] > c.maxbase[slot]: out.set_color((255,255,0))
        # reference/emuera-1824/Emuera/GameData/StrForm.cs:233–244：數值以字元數補空白；最後留下知性。
        st.results[0] = format_curly(preview[i],min(digits,5))
        out.print(format_percent(st.results[0],7,True)); out.reset_color()
        out.print(f'{raw:>{digits}} → {raw+bonuses[i]*_MAG[i]:>{digits}}（{costs[i]:4}）')
        out.print_plain(' ')
        for delta, blocked in ((-2,bonuses[i]<2),(-1,bonuses[i]<1),(1,total+50>points),(2,total+100>points)):
            cmd = i*10 + {-2:0,-1:1,1:2,2:3}[delta]
            _button(out,f'[{cmd:2}]{delta*_MAG[i]:+4}',blocked)
            if delta!=2:
                out.print_plain('  　 ')
        out.printl()
        if i==2: out.printl()
    out.printl()
    marks=[]
    personality=seikaku_check(data,c)
    for i,palam in enumerate(_MARK_PALAM):
        remaining=c.mark[i]-bonuses[i+7]
        cost=seikaku_hosei_palam(personality,palam,seikaku_hosei_palam(personality,palam,remaining*100))
        marks.append(cost)
        out.print(('刻印　：　' if i==0 else '　　　　　')+data.names['MARK'][i]+'　')
        if bonuses[i+7]: out.set_color((255,255,0))
        out.print('['+'*'*remaining+'.'*(5-remaining)+']'); out.reset_color()
        out.print(f'（{costs[i+7]:4}）')
        out.print_plain(' ')
        _button(out,f'[{70+i}] {remaining} → {limit(remaining-1,0,5)}　　+{cost:4}',
                c.mark[i]==0 or remaining==0 or total+cost>points)
        if i==4: _button(out,'　　　　　　　　[79]解除',not any(bonuses[7:12]))
        out.printl()
    if sum(c.talent[i] for i in range(190,194)):
        out.printl()
        for i in range(4):
            if not c.talent[190+i]: continue
            mode=bonuses[12+i]
            out.print(f'{data.names["TALENT"][190+i]}の再構築 （{30 if mode==1 else 0:2}）')
            out.print_plain(' ')
            _button(out,f'[{80+i}]',c.base[30+i]==c.maxbase[30+i] or total+30>points or mode==2,mode==1)
            st.result[0]=percent_cal(c.base[30+i],c.maxbase[30+i])
            p=st.result[0]
            red=limit(255-div(p*p*4,200),0,255)
            green=limit(-215-div(p*p,100)+p*5,0,255)
            if mode: red=green=255
            if c.base[30+i]>0:
                st.result[0]=color_bar(out,c.base[30+i],c.maxbase[30+i],20,red,green,20,-160,6,32,20,1,'▮','▮')
            else:
                out.set_color((128,40,40)); out.print('　　　崩　壊　　　　'); out.reset_color()
            money=c.abl[data.index_of('ABL','レベル')]*625
            _button(out,f'[{85+i}] ${money:5}',c.base[30+i]==c.maxbase[30+i] or mode==1 or price+money>st.money,mode==2)
            # 原文:262–270 的最後一行計算有一位差，照原文保留。
            last=next(k for k in range(4) if c.talent[193-k])
            if i==4-last: _button(out,'  [89]解除',not any(bonuses[12:16]))
            out.printl()
    selected=bonuses[16]
    count=sum(bool(selected & (1<<i) or c.talent[190+i]) for i in range(4))
    count+=bool(selected & 16 or c.talent[303]>0)
    out.printl(); out.print(f'          結界の獲得 （{costs[12]:4}')
    out.print_plain('） ')
    for i in range(5):
        tid=190+i if i<4 else 303
        blocked=count>2 or (i==1 and (selected&16 or c.talent[303]>0)) or (i==4 and (selected&2 or c.talent[191]>0))
        _button(out,f'[{90+i}]{data.names["TALENT"][tid]}　',blocked,bool(selected&(1<<i)),bool(c.talent[tid]) and not bool(selected&(1<<i)))
    out.printl(); out.drawline()
    out.print('[100]決定　')
    out.print_plain('　　　　　　')
    out.printl(f'合 計{total:5} / {points:5}　　　　　資 金{price:5} / {st.money}')
    out.print('[200]全て解除')
    out.print_plain('　　　　　')
    out.print('[300]前のキャラ' if left else '               ')
    out.print_plain('　　　　　　 ')
    if right:
        out.print('[500]次のキャラ')
    out.printl()
    out.printl('[999]戻る')
    return total, marks


def character_powerup_gen(ctx):
    """@CHARA_POWERUP:4–566。所有角色寫入集中於[100]；入口更新結界照原文執行。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    out.printl(); out.printl('【キャラの強化】')
    who=1
    if st.charanum>=3:
        selection=chara_list(ctx,1,2)
        next(selection)
        while True:
            value=yield from input_number(ctx)
            try: selection.send(value)
            except StopIteration as done:
                who=done.value
                break
        if who==999:
            st.result[0]=0
            return
    bonuses=[0]*17
    costs=[0]*13
    price=0
    fresh=True
    while True:
        c=st.charas[who]
        if fresh:
            preview=[c.maxbase[i] for i in _BASE]
            digits=max(4,*(min(len(str(c.maxbase[i]+1)),100) for i in _BASE))
            fresh=False
        # :60–61 每一圈覆寫；不能改成固定的進入前 TARGET。
        old_target=st.target
        st.target=who
        out.printl(f'{c.callname}を選びました')
        baseup_cal_shield(data,st,who)
        st.result[0]=0  # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
        eligible=[i for i in range(1,st.charanum) if st.charas[i].cflag[999]!=0 and st.charas[i].cflag[0]==0]
        left=max((i for i in eligible if i<who),default=0)
        right=min((i for i in eligible if i>who),default=0)
        total,marks=_show(ctx,c,bonuses,costs,price,preview,digits,left,right)
        r=yield from input_number(ctx)
        if r==999:
            st.target=old_target
            st.result[0]=0
            return
        # DEVIATION: 沿用共用CLEARLINE僅刪已完成行；詳見deviations.md的顯示簡化。
        out.clearline(26)
        shield_lines=sum(c.talent[i] for i in range(190,194))+1
        if shield_lines>1:
            out.clearline(shield_lines)
        points=c.juel[data.index_of('JUEL','修練P')]
        money=c.abl[data.index_of('ABL','レベル')]*625
        if r==400:
            st.flag[999]^=1
            if st.flag[999]==1: out.set_bgcolor((0,0,40))
            else: out.reset_bgcolor()
            continue
        if 0<=r<70 and r%10<=3:
            i=r//10
            delta=(-2,-1,1,2)[r%10]
            if (delta<0 and bonuses[i]>=-delta) or (delta>0 and points>=total+50*delta):
                bonuses[i]+=delta; costs[i]+=50*delta
        elif 70<=r<75:
            i=r-70
            if c.mark[i]-bonuses[i+7]>0 and points>=total+marks[i]:
                bonuses[i+7]+=1; costs[i+7]+=marks[i]
        elif r==79:
            bonuses[7:12]=[0]*5; costs[7:12]=[0]*5
        elif 80<=r<84:
            i=r-80
            if bonuses[i+12]==1: bonuses[i+12]=0
            elif points>=total+30 and c.base[i+30]<c.maxbase[i+30]:
                if bonuses[i+12]==2: price-=money
                bonuses[i+12]=1
        elif 85<=r<89:
            i=r-85
            if bonuses[i+12]==2:
                bonuses[i+12]=0; price-=money
            elif st.money>=price+money and c.base[i+30]<c.maxbase[i+30]:
                bonuses[i+12]=2; price+=money
        elif r==89:
            bonuses[12:16]=[0]*4; price=0
        elif 90<=r<94 or (r==94 and c.talent[191]==0):
            i=r-90; bit=1<<i
            if bonuses[16]&bit: bonuses[16]&=~bit
            else:
                count=sum(bool(bonuses[16]&(1<<j) or c.talent[190+j]) for j in range(4))
                count+=bool(bonuses[16]&16 or c.talent[303]>0)
                maximum=3-int(any(charatalent(data,c,k,'オトコ')>0 for k in (0,1)))
                blocked=(i==1 and (bonuses[16]&16 or c.talent[303]>0)) or (i==4 and (bonuses[16]&2 or c.talent[191]>0))
                if not blocked and count<maximum and c.talent[190+i if i<4 else 303]==0 and points>=total+50:
                    bonuses[16]|=bit
            costs[12]=bonuses[16].bit_count()*50
        elif r==100:
            for i,slot in enumerate(_RAW): c.base[slot]+=bonuses[i]*_MAG[i]
            for i in range(5):
                if bonuses[i+7]>0 and c.mark[90+i]<c.mark[i]: c.mark[90+i]=c.mark[i]
                c.mark[i]-=bonuses[i+7]
            for i in range(4):
                if bonuses[i+12]: c.base[i+30]=c.maxbase[i+30]
            for i in range(4):
                if bonuses[16]&(1<<i):
                    c.talent[190+i]=1
                    c.maxbase[30+i]=cal_shield(data,c)
                    c.base[30+i]=c.maxbase[30+i]
            if bonuses[16]&16: c.talent[303]=1
            c.juel[data.index_of('JUEL','修練P')]-=total
            st.money-=price
            level_status(data,st,who)
            baseup_cal_shield(data,st,who)
            bonuses=[0]*17; costs=[0]*13; price=0
        elif r==200:
            bonuses=[0]*17; costs=[0]*13; price=0
        elif (r==300 and left) or (r==500 and right):
            bonuses=[0]*17; costs=[0]*13; price=0
            who=left if r==300 else right
            fresh=True
            continue
        preview=_preview(ctx,c,bonuses)
