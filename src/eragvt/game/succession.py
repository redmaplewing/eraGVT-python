"""通關繼承：ERB/ゲーム内_イベント発生/エンディング/SUCCESSION.ERB@SUCCESSION。

逐欄保留／重置，沒有 RESETDATA；BEGIN SHOP 亦不清空狀態
（reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs:614–640）。
"""

from .counting import count_loop
from dataclasses import dataclass, field

from ..state.constants import GameMode, GameOption, PARTY_MAX
from ..state.sparse import IntArray
from .action import Ctx, Step, kojo_root_gen, seikaku_hosei
from .chara_common import talent, seikaku_check, baseup_cal_shield
from .era import div, mod
from .opening import (BOSS_ERB_NUM, game_option,
                      research_quota, set_limit_day)
from .shop import game_mode_check, lb


_COST = {11:4,12:15,13:30,14:8,18:4,19:6,20:6,
         21:8,22:6,23:6,24:3,25:8,26:30,27:2,28:2,29:3,30:2,31:0}
_OPPOSITE = {22:27,27:22,23:28,28:23,25:30,30:25}
_LABELS = {
    11:"性成長引き継ぎ",12:"娘引き継ぎ",13:"レベル引き継ぎ",14:"戦技引き継ぎ",
    15:"資金引き継ぎ",16:"基礎値ボーナス増加",17:"初期防衛力増加",
    18:"触手の欠片＆研究Lv引き継ぎ",19:"衣装引き継ぎ",20:"魅了経験引き継ぎ",
    21:"夜間自動回復アップ",22:"絡みつく選択率ダウン",23:"振り解く強化",
    24:"洗脳/悪堕ちしやすい",25:"刻印怯み無効",26:"日数制限解除",
    27:"絡みつく選択率アップ",28:"振り解く弱化",29:"妊娠確率アップ",
    30:"刻印怯み率２倍",31:"人気度リセット",
}


def points(ctx: Ctx, rank: int, show: bool = False) -> int:
    """原文 :31–268；GLOBAL:115 僅讀取，不寫回。"""
    st, g = ctx.state, ctx.globals.mem.global_
    loops = st.flag[854]-1
    mode=game_mode_check(st)
    mode_points={GameMode.SOLO:2,GameMode.NORMAL:5,GameMode.HARDCORE:7,GameMode.INSTANT:5}.get(mode,2)
    rows=[("周回数累計(引き継ぎ回数)",loops),
          ({1:"ノーマル",2:"ソロ",3:"ハードコア",7:"インスタント"}.get(mode,"")+"クリア",mode_points)]
    if rank in range(1,7):
        rows.append(("総合"+"ＥＤＣＢＡＳ"[rank-1]+"ランク",{1:0,2:1,3:2,4:3,5:5,6:8}[rank]))
    rows.extend((label,5) for i,label in ((211,"覇者の証"),(212,"へっぽこ大魔王"),(213,"eraGVTマスター")) if g[i])
    if g[114]>=8:
        rows.append(("ENDLESS撃破数ボーナス",next(v for n,v in ((60,12),(50,8),(40,6),(30,4),(20,2),(8,1)) if g[114]>=n)))
    multiplier=3 if loops>=6 else 2 if loops>=3 else 1
    subtotal=sum(value for _,value in rows)*multiplier
    achievements = {i:10 for i in (*range(220,234), *range(240,248), *range(250,275))}
    achievements.update({i:20 for i in (228,229,230,243,244,245,246,247,253,262,266,270)})
    achievements.update({240:15,242:15,269:5,271:5,272:5,273:5,274:5})
    achievement_total=sum(v for i,v in achievements.items() if g[i])
    total=subtotal+div(achievement_total,10)
    if show:
        out=ctx.out
        for dots in ("…","……","………"):
            out.printw(dots)
        lb(out)
        out.printl("+-+-+☆★☆　周回ポイントの獲得　☆★☆+-+-+")
        out.drawline()
        for label,value in rows:
            out.printl(f"{label}　+{value}")
        out.printl(f"周回数によるポイントボーナス(実績は除く)　×{multiplier}")
        out.drawline()
        out.printl(f"小合計:　{subtotal}pts")
        out.drawline()
        out.printl(f"実績による追加周回ボーナス　　　　　　　　+{achievement_total}*0.1")
        out.drawline()
        out.printl(f"合計　　　　　　　　　　　　　　　　　　　{total}pts.　(歴代最高{max(total,g[115])}pts.)")
        out.printl()
        out.printw("[PRESS ENTER]")
        out.clearline(1)
    return max(total,g[115])


@dataclass
class Selection:
    remaining: int
    values: IntArray = field(default_factory=IntArray)
    page: int = 1

    def toggle(self, index: int) -> bool:
        v, price = self.values, _COST[index]
        other = _OPPOSITE.get(index)
        refund = _COST[other] if other and v[other] else 0
        if v[index]:
            v[index] = 0
            self.remaining += price
        elif self.remaining + refund >= price:
            if other:
                v[other] = 0
            v[index] = 1
            self.remaining += refund-price
        else:
            return False
        return True

    def money_choice(self, choice: int) -> bool:
        """:674–747：選5的原作退款有 *4 與固定16混用，刻意保留。"""
        old = self.values[15]
        if choice == 0:
            self.remaining += old*4
            self.values[15] = 0
        elif choice in range(1,6) and (old==choice or self.remaining+old*4 >= min(choice,4)*4):
            if old==choice:
                self.values[15] = 0
                self.remaining += min(choice,4)*4
            elif old in (4,5) and choice in (4,5):
                self.values[15] = choice
            else:
                self.remaining += old*4-min(choice,4)*4
                self.values[15] = choice
        else:
            return False
        return True


def facility_value(st) -> int:
    from .ending import _FACILITY_REFUND
    return (sum(5000*i+5000 for i in count_loop(st, st.flag[50]) if i != 0)
            +sum(1000*i+1000 for i in count_loop(st, st.flag[51]) if i != 0)
            +sum(10000*i+10000 for i in count_loop(st, st.flag[52]))
            +sum(amount for bit,amount in _FACILITY_REFUND if st.flag[53]&bit))


def reset_character(ctx: Ctx, who: int, selection: Selection) -> int:
    """原文 :1104–1373。CSV*_F 會改 RESULT:0（コモン関数.ERB@CSVBASE_F:966 等）。"""
    from .battle.func import transform
    from .body import generate_char_size
    st, data, v = ctx.state, ctx.data, selection.values
    c = st.charas[who]
    d = data.charas[c.no]
    def csv(field, index):
        value = getattr(d,field).get(index,0)
        st.result[0] = value
        return value
    def reset(field, indices):
        for i in indices:
            getattr(c,field)[i] = csv(field,i)
    def ti(n):
        return data.index_of("TALENT",n)
    def t(n):
        return c.talent[ti(n)]
    def put(n,value):
        c.talent[ti(n)] = value
    put("初期経験設定不可",1)
    if not v[11]:
        reset("abl",range(25))
        reset("exp",range(10,58))
        reset("mark",(*range(5),*range(90,95)))
        reset("cflag",(*range(30,33),*range(35,40),*range(200,239),*range(250,999)))
        reset("talent",(1,2,*range(150,157),*range(159,165)))
        if t("固有キャラ")>0:
            put("未熟",csv("talent",4))
            put("ふたなり",csv("talent",300))
        elif t("ふたなり") not in (3,-3):
            put("ふたなり",csv("talent",300))
        c.maxbase[20] = csv("base",20)
        c.maxbase[21] = csv("base",21)
        for n in ("Ｖ敏感","Ａ敏感","Ｂ敏感","Ｃ敏感"):
            if t(n)>9:
                put(n,t(n)-10)
        for n in ("Ｖ鈍感","Ａ鈍感","Ｂ鈍感","Ｃ鈍感"):
            if t(n)<-8:
                put(n,t(n)+10)
        for n in ("処女","清純派"):
            if t(n)==-1:
                put(n,1)
        put("変身時非処女",0)
        b = lambda n: data.index_of("BASE",n)
        size = c.base[b("体格基本値")]
        if size:
            put("小柄" if size<0 else "長身",1)
        bust = c.base[b("胸サイズ基本値")]
        if bust in (-2,-1,1,2,3):
            put("貧乳" if bust<0 else "巨乳",abs(bust))
        for tn,bn in (("変身時体格変動","体格基本値"),("変身時胸サイズ変動","胸サイズ基本値"),("変身時外見","外見基本値")):
            put(tn,c.maxbase[b(bn)])
        put("外見",c.base[b("外見基本値")])
        for ar,prefix in ((c.base,""),(c.maxbase,"変身時")):
            if ar[b("性別基本値")]==2:
                put(prefix+"ふたなり",3)
            if ar[b("性別基本値")]==3:
                put(prefix+"男の娘",1)
        if mod(t("性別変化"),10)==1:
            put("オトコ",1)
            for n in ("処女","母乳体質","パイパン","Ｖ敏感","Ｖ鈍感","濡れやすい","濡れにくい","苗床化","ふたなり","アクセサリ","外見"):
                put(n,0)
            if t("交際相手") in (2,4,5):
                put("交際相手",0)
            generate_char_size(data,c,0,st.result)
            for i,n in enumerate(("身長","体重","胸囲","胴囲","腰囲","胸の重量"),2):
                c.base[b(n)] = st.result[i]
        if div(t("性別変化"),10)==1:
            generate_char_size(data,c,1,st.result)
            for i,n in enumerate(("身長","体重","胸囲","胴囲","腰囲","胸の重量"),2):
                c.maxbase[b(n)] = st.result[i]
        if t("変身時ＴＳ")==-1:
            put("変身時ＴＳ",1)
        put("性別変化",0)
        if t("女体受容")>0:
            # :1264：原文省略角色索引，交換的是 TARGET，並非 CCOUNT。
            ar = st.target_chara.talent
            a,z = ti("男性苦手"),ti("女性苦手")
            ar[a],ar[z] = ar[z],ar[a]
        put("女体受容",0)
        put("初期経験設定不可",0)
    if not v[13]:
        c.abl[50] = csv("abl",50)
        reset("cflag",range(120,124))
    if not v[14]:
        reset("abl",range(30,34))
        reset("exp",range(5,8))
    if not v[19]:
        reset("cflag",range(40,44))
        reset("equip",range(600,700))
    else:
        for i in (40,41,42):
            if c.cflag[i]==0:
                c.cflag[i]=-1
    if not v[20]:
        c.exp[58]=csv("cflag",58)
    elif c.exp[58]>100:
        c.exp[58]=100+div(c.exp[58]-100,4)
    for i in range(53):
        if i in (20,21) or 40<=i<48:
            continue
        c.base[i]=csv("base",i)
        c.maxbase[i]=c.base[i]
    reset("exp",range(3))
    reset("juel",range(51))
    reset("cflag",(0,*range(20,32),*range(99,119)))
    reset("mark",range(90,95))
    c.cflag[999]=0
    if c.cflag[231]:
        for bi,ci in ((0,60),(1,61),(2,62),(50,60),(51,61),(52,62),(10,63),(11,64),(12,65),(13,66)):
            c.base[bi]+=c.cflag[ci]
    if c.no==0:
        personality=seikaku_check(data,c)
        st.result[0]=personality
        for i in (0,1,2,10,11,12,13):
            c.base[i]=seikaku_hosei(personality,i,c.base[i])
            c.maxbase[i]=c.base[i]
    st.result[0]=transform(ctx,0,who)
    c.base[20]=c.base[21]=0
    return personality if c.no==0 else 95  # :1336 FOR LOCAL,90,95 的末值或 :1357 性格。


def reset_data(ctx: Ctx, selection: Selection) -> None:
    """原文 :1043–1442；未列出的全域及角色暫存全部保留。"""
    st,v=ctx.state,selection.values
    refund=facility_value(st)
    st.day[0]=st.day[1]=st.time=0
    for i in (*range(250,256),*range(1,5),*range(9,22),*range(65,112),*range(300,800),*range(900,999)):
        st.flag[i]=0
    for i in range(41,64):
        if (v[15]!=5 or i<50 or i>53) and (not v[18] or i!=54):
            st.flag[i]=0
    for i in range(21,31):
        st.flag[880+i]=v[i]
    if st.flag[906]:
        st.flag.set_bit(0,GameOption.NO_TIME_LIMIT)
    if v[15]!=5:
        st.flag[50]=st.flag[51]=1
        st.flag[52]=st.flag[53]=0
    st.result[0]=st.flag[3]=BOSS_ERB_NUM
    st.flag[4]=1
    st.flag[100]=0
    for i in count_loop(st, st.flag[3]):
        st.flag[100] |= 1 << i
    st.flag[101]=0
    who=1
    local=31  # :1072 FOR LOCAL,21,31 的末值。
    while who<st.charanum:
        if st.charas[who].cflag[0]==999:
            local=reset_character(ctx,who,selection)
            who+=1
        else:
            # SWAPCHARA／DELCHARA 不修正 TARGET、RELATION：
            # reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1061–1066,1165–1174。
            # :1383 的 SIF LOCAL==MASTER 指的是先前 LOCAL 殘值，非 CCOUNT:2。
            for i in range(who,st.charanum-1):
                st.swap_chara(i,i+1)
                for c in st.charas:
                    if local!=st.MASTER:
                        c.relation[i],c.relation[i+1]=c.relation[i+1],c.relation[i]
            for i in range(1,st.charanum):
                st.charas[-1].relation[i]=0
                st.charas[i].relation[st.charanum-1]=0
            st.del_chara(st.charanum-1)
    st.money = st.money-refund+1000 if v[15]==5 else div(st.money*25*v[15],100)+1000
    st.flag[852]=5000+v[17]*500
    if not v[18]:
        st.flag[200]=st.flag[54]=0
    if not v[19]:
        for i in (*range(101,200),*range(301,400),*range(401,700)):
            st.item[i]=0
    if v[31]:
        st.flag[853]=0


def _input(ctx):
    value=yield
    ctx.state.result[0]=value
    return value


def _show(ctx,s):
    out=ctx.out
    out.printl(f"データ引き継ぎ　のこり周回ポイント ({s.remaining}pts.)")
    out.drawline()
    out.printl("入手した周回ポイントを消費して次の周回にデータを引き継ぐことができます。")
    out.printl("名前や種族など、ゲーム開始時にキャラが持っていたデータは自動で引き継がれます。")
    out.printl("引き継ぐ項目を選んでください。")
    out.printl()
    out.printl(f"[0] 引き継ぎキャラ選択　現在 {s.values[10]}人" if s.page==1 else "[0] このページの項目をすべて解除")
    out.printl()
    for i in (range(11,21) if s.page==1 else range(21,31) if s.page==2 else (31,)):
        disabled=False
        label=_LABELS[i]
        v=s.values
        if i==15:
            value=("なし","25％","50％","75％","100％","100％＋施設そのまま")[v[i]]
        elif i in (16,17):
            value=f"{v[i]*(500 if i==17 else 1):5} ポイント" if v[i] else "なし"
        elif i==13 and not ctx.globals.mem.global_[213]:
            label,value,disabled="？？？","",True
        else:
            value="(選択済み)" if v[i] else "消費なし" if i==31 else f"-{_COST[i]}"
            price=_COST[i]
            if i in (22,23,25) and v[_OPPOSITE[i]]:
                price={22:4,23:1,25:6}[i]  # :442 顯示門檻1，實際購買門檻4。
            if i in (27,28,30) and v[_OPPOSITE[i]]:
                price=0
            if i==31:
                price=8  # 免費仍按8點變灰，照原作 :507。
            disabled=not v[i] and (s.remaining<price or i==12 and not any(c.cflag[231] for c in ctx.state.charas[1:]) or i==18 and not ctx.state.flag[200])
        if disabled:
            out.set_color((105,105,105))
        out.printl(f"[{i-10}] {label}　　　　　　　　　　{value}")
        out.reset_color()
    out.drawline()
    if s.page>1:
        out.printl("[100] 前のページへ")
    out.printl(f"PAGE < {s.page}/3 >")
    if s.page<3:
        out.printl("[200] 次のページへ")
    out.printl("[999] 引き継ぎ開始")


def succession_gen(ctx: Ctx, rank: int):
    """原文 :16–1041、:1444–1622；選單與確認逐次等待 INPUT。"""
    from .battle.func import transform
    from .config import heroine_preset_gen
    st,out=ctx.state,ctx.out
    st.flag[64]=0
    daughter=0
    for i in range(1,st.charanum):
        daughter+=int(bool(st.charas[i].cflag[231]))
        if st.charas[i].cflag[1]>0:
            st.result[0]=transform(ctx,0,i)
    s=Selection(points(ctx,rank,show=True))
    # :316–320 先複製 FLAG:901–910 後立即 VARSET LOCAL，故全部從未選開始。
    while True:
        start_line=out.linecount
        _show(ctx,s)
        r=yield from _input(ctx)
        if r==100 and s.page>1:
            s.page-=1
        elif r==200 and s.page<3:
            s.page+=1
        elif r==0 and s.page==1:
            while True:
                s.values[10]=sum(c.cflag[0]==999 for c in st.charas[1:])
                out.printl("引き継ぎを行うキャラを選択してください。")
                for i,c in enumerate(st.charas[1:],1):
                    if c.cflag[231] and not s.values[12]:
                        out.set_color((105,105,105))
                    out.printl(f"[{i}] {c.name}　{'○引き継ぐ' if c.cflag[0]==999 else '×引き継がない'}"+('　(娘)' if c.cflag[231] else ''))
                    out.reset_color()
                out.printl("[100] 全キャラ選択")
                out.printl("[999] 選択完了")
                q=yield from _input(ctx)
                if q<0:
                    raise NotImplementedError("SUCCESSION 角色選擇負索引（原作 CFLAG:RESULT:231 亦為範圍錯誤）")
                if q==999:
                    break
                if q==100:
                    for c in st.charas[1:]:
                        if not c.cflag[231] or s.values[12]:
                            c.cflag[0]=999
                elif 0<q<st.charanum and (not st.charas[q].cflag[231] or s.values[12]):
                    c=st.charas[q]
                    c.cflag[0]=0 if c.cflag[0]==999 else 999
        elif r==0 and s.page in (2,3):
            for i in (range(21,31) if s.page==2 else (31,)):
                if s.values[i]:
                    s.toggle(i)
        elif s.page==1 and r in (5,6,7):
            while True:
                out.printl(f"{_LABELS[r+10]}　のこり周回ポイント ({s.remaining}pts.)")
                if r==5:
                    out.printl("資金の引き継ぎ金額を選んでください。")
                    for i in range(6):
                        available=s.remaining+s.values[15]*4>=min(i,4)*4
                        if not available:
                            out.set_color((105,105,105))
                        if i==0:
                            out.printl("[0] 引き継がない")
                        else:
                            amount=st.money-facility_value(st) if i==5 else div(st.money*25*i,100)
                            detail="＋施設そのまま" if i==5 else ""
                            status="(選択済み)" if s.values[15]==i else f"-{min(i,4)*4}"
                            out.printl(f"[{i}] {min(i,4)*25}％引き継ぎ　{amount:10}＄{detail}　{status}")
                        out.reset_color()
                else:
                    out.printl("キャラエディットの際に使用する基礎値ボーナスを20ポイントまで獲得できます。" if r==6 else "初期防衛力を5000ポイントまで強化できます。")
                    out.printl("周回ポイントを割り振ってください。")
                    out.printl(f"基礎値ボーナス：{s.values[16]}" if r==6 else f"防衛力強化：{s.values[17]*500}")
                    out.printl("[0] リセットする")
                    if not s.values[r+10]:
                        out.set_color((105,105,105))
                    out.printl("[1]−１" if r==6 else "[1]−５００")
                    out.reset_color()
                    if s.remaining<(2 if r==6 else 1) or s.values[r+10]>=(20 if r==6 else 10):
                        out.set_color((105,105,105))
                    out.printl("[10]＋１" if r==6 else "[10]＋５００")
                    out.reset_color()
                out.printl("[999] 選択完了")
                q=yield from _input(ctx)
                if q==999:
                    break
                if r==5:
                    if s.money_choice(q) and q==0:
                        break  # :674 分岐のみサブ選單へ戻らず MASTER_LOOP。
                else:
                    i=r+10
                    cost,maximum=(2,20) if r==6 else (1,10)
                    if q==0:
                        s.remaining+=s.values[i]*cost
                        s.values[i]=0
                    elif q==1 and s.values[i]:
                        s.values[i]-=1
                        s.remaining+=cost
                    elif q==10 and s.remaining>=cost and s.values[i]<maximum:
                        s.values[i]+=1
                        s.remaining-=cost
        elif (s.page==1 and r in (1,2,3,4,8,9,10)) or (s.page==2 and 11<=r<=20) or (s.page==3 and r==21):
            if r==2 and not daughter or r==3 and not ctx.globals.mem.global_[213] or r==8 and not st.flag[200]:
                continue
            s.toggle(r+10)
            if r==2 and not s.values[12]:
                for c in st.charas[1:]:
                    if c.cflag[0]==999 and c.cflag[231]:
                        c.cflag[0]=0
                        s.values[10]-=1
        elif r==999:
            if not s.values[10]:
                out.printl("現在の引き継ぎ人数が 0人になっています。")
                out.printl("キャラを引き継がずに次周を開始してもよろしいですか？")
                out.printl("[0] はい　[1] いいえ")
                q=yield from _input(ctx)
                while q not in (0,1):
                    q=yield from _input(ctx)
                if q==1:
                    continue
            out.printl("次周を開始するにあたって、ゲームモードを選択し直すことができます")
            from .opening import mode_select_gen
            if (yield from mode_select_gen(ctx, inherited=True, count=s.values[10])) == 999:
                continue
            break
        out.clearline(out.linecount-start_line)
    reset_data(ctx,s)
    number=1 if game_option(st,GameOption.SOLO) else max(3,s.values[10])
    if not game_option(st,GameOption.SOLO) and sum(ctx.globals.mem.global_[i] for i in (100,101,102))>0 and number<7:
        out.printl("周回クリアボーナス：ゲーム開始時の人数を増減できます")
        for q in (-1,0,1,2,3):
            if (q==-1 and s.values[10]<3) or (q>=0 and s.values[10]+q<7):
                out.printl(f"[{q}] {2 if q==-1 else number+q}人で開始")
        q=yield from _input(ctx)
        while not (0<=q<=3 and s.values[10]+q<7 or q==-1 and s.values[10]<3):
            q=yield from _input(ctx)
        number=2 if q==-1 else number+q
    if number-s.values[10] > 0:  # @SUCCESSION:1479，零人不進REPEAT。
        for _ in count_loop(st, number-s.values[10]):
            st.add_chara(ctx.data,0)
            st.flag[8]+=1
    set_limit_day(st)
    _training_points(ctx,s.values[16])
    st.target=st.charanum-1
    from .creation_menu import creation_menu
    yield from creation_menu(ctx,bonus=s.values[16])
    for i,c in enumerate(st.charas[1:],1):
        if c.cflag[6]==0 or c.cflag[6]>=100:
            c.cflag[6]=c.no
        baseup_cal_shield(ctx.data,st,i)
    for i,c in enumerate(st.charas[1:],1):
        st.target=i
        if c.cflag[0]!=0 and c.cflag[20]==0 and c.cflag[21]==0:
            c.cflag[21]=st.rng.rand(7)+1
        yield from kojo_root_gen(ctx,"FIRST")
        st.result[0]=0  # MESSAGE_FIRST 的函式終端。
        if i<=PARTY_MAX:
            c.cflag[999]=1
    for c in st.charas[1:]:
        for k in (40,41,42,43):
            if st.item[c.cflag[k]]==0:
                st.item[c.cflag[k]]=1
        for k in range(600,700):
            if c.equip[k]:
                st.item[k]=1
    yield from heroine_preset_gen(st,ctx.data,out,ctx.globals)
    st.flag[41]=1
    research_quota(st)
    st.result[0]=0  # RESEARCH_QUOTA 函式終端；Process.ScriptProc.cs:61–67。
    for i in range(20,27):
        st.savestr[i]=""
    st.flag[64]=-1
    return Step.SHOP


def _training_points(ctx,bonus):
    """原文 :1491–1550：已用修練點扣除後下限0，再加周回獎勵。"""
    ti=ctx.data.index_of("PALAM","修練P")
    costs={n:150 for n in ("近距離得意","中距離得意","遠距離得意","空中得意","回復早い","情報屋")}
    costs.update({n:50 for n in ("Ｃ結界","Ｖ結界","Ａ結界","Ｂ結界","避妊結界","噂好きの友人")})
    costs["裕福な実家"]=100
    for c in ctx.state.charas[1:]:
        cost=sum(c.cflag[i]*10 for i in range(50,57))
        cost+=sum(price for name,price in costs.items() if talent(ctx.data,c,name))
        police=talent(ctx.data,c,"警察関係者")
        cost+={1:100,2:200}.get(police,0)
        cost-=sum(50 for n in ("近距離苦手","中距離苦手","遠距離苦手","空中苦手","回復遅い") if talent(ctx.data,c,n))
        c.juel[ti]=max(0,c.juel[ti]-cost)+bonus*10
