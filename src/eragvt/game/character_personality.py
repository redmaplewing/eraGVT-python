"""ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_SEIKAKU.ERB 手翻。"""
from .action import seikaku_hosei
from .chara_common import baseup_cal_shield, is_female, seikaku_check, talent
from .character_personality_text import TEXT, GROUP_LABELS
from .input_request import input_number
from .status_talent import talent_info


BASE_SLOTS=(0,1,2,10,11,12,13)
# @FIRSTSETTING_CHARA_SEIKAKU:245–414：各組由左到右循環，最後回無。
TRAIT_GROUPS=((600,601),(602,603),(604,605),(606,607),(608,609),
              (610,611),(612,613),(614,615,625),(616,617,618,619),
              (620,621,622,623,624))


def _clear_traits(c):
    for i in range(600,700):c.talent[i]=0


def _select_personality(c, selected):
    for i in range(10,29):c.talent[i]=int(i==selected)
    if c.talent[28]>0:_clear_traits(c)


def _kojo_color(ctx,who,person):
    """@SHOW_KOJO_EXIST:446–454／@RAND_CHOOSE_KOJO_SEIKAKU:463。

    TRYCCALLFORM會執行色函式而非只查存在：
    reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2297–2332。
    """
    name=f"KOJO_{talent(ctx.data,ctx.state.charas[who],'オトコ')}_COLOR_{person}"
    ok=ctx.narration.run_function(ctx,name)
    catalog=getattr(ctx.narration,'catalog',None)
    if not ok and catalog is not None and catalog.exists(name):
        raise RuntimeError(f'{name} 存在但無法執行')
    return ok


def _draw(ctx,who,have):
    """@FIRSTSETTING_CHARA_SEIKAKU:39–197，保留顯示呼叫的RESULT副作用。"""
    from .character_editor import _resist
    out,st,data=ctx.out,ctx.state,ctx.data;c=st.charas[who]
    out.printl(f'{who}人目のキャラ 『{c.name}』 の性格を設定してください')
    out.drawline();out.printl(TEXT[41])
    for person in range(10,29):
        if c.talent[person]>0:out.set_color('#00ffb4')
        out.print(f'　　[{person-10:2}]'+data.names['TALENT'].get(person,'').ljust(20))
        out.reset_color();out.print('　')
        # ヒロイン関連/CHARA_SEIKAKU.ERB@SHOW_SEIKAKUHOSEI:1026–1050。
        for slot in BASE_SLOTS:
            value=seikaku_hosei(person,slot,100)
            mark,color=next((m,col) for limit,m,col in ((90,'×','#003cfa'),(100,'▽','#7878fa'),(110,'－','#808080'),(120,'○','#fab400'),(float('inf'),'◎','#fa3c00')) if value<limit)
            out.set_color(color);out.print(mark+'  ');out.reset_color()
            if slot==2:out.print('　')
        st.result[0]=0
        out.print('　');_resist(ctx,who,person,compact=True);out.print('　')
        ok=_kojo_color(ctx,who,person)
        out.reset_color()
        if not ok:out.set_color('#696969')
        out.print('有' if ok else '無');out.reset_color();st.result[0]=0
        if c.talent[person]>0:out.set_color('#00ffb4');out.print(' ＜')
        out.reset_color();out.printl()
    out.printl(TEXT[60]);out.printl(TEXT[61]);out.drawline()
    out.printl(f' 精神素質({have}/4)　※素質名にマウスオーバーすると説明が表示されます')
    for pair in range(0,10,2):
        if c.talent[28]>0:out.set_color('#808080')
        for group in range(pair,pair+2):
            selected=next((i for i in TRAIT_GROUPS[group] if c.talent[i]>0),None)
            title=talent_info(selected) if selected is not None else None
            label=data.names['TALENT'].get(selected,'') if selected is not None else '─'
            out.print(GROUP_LABELS[group])
            out.button(f'[{100+group}]　　{label}',100+group,title=title)
        out.printl();out.reset_color()
    out.drawline()
    if have>4:out.set_color('#696969')
    out.printl(TEXT[194]);out.reset_color();out.printl(TEXT[196]);out.printl(TEXT[197])


def random_mental_traits(ctx,who,count):
    """CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_STATUS_TALENT_SEIKAKU:1237–1331。

    保留連續條件RAND的次序，使用共用RANDCHOOSE陣列，不以抽樣API代替。
    """
    from .battle.core import add_randchoose,clear_randchoose,clear_specific_choose,randchoose_f
    st=ctx.state;c=st.charas[who]
    if count<1 or c.talent[28]>0:st.result[0]=0;return
    count=min(count,10);clear_randchoose(st)
    for start in range(600,616,2):add_randchoose(st,start+int(st.rng.rand(2)!=0))
    # :1296–1304與:1306–1318每個ELSEIF各抽一次，不能RAND:4／RAND:6一次代替。
    for start,n in ((616,4),(620,6)):
        selected=start+n-1
        for offset in range(n-1):
            if st.rng.rand(n-offset)==0:selected=start+offset;break
        add_randchoose(st,selected)
    while True:
        selected=randchoose_f(st);c.talent[selected]=1;clear_specific_choose(st,selected)
        if sum(c.talent[i]>0 for i in range(600,700))>=count:break
    st.result[0]=0


def personality_setting(ctx,who):
    """@FIRSTSETTING_CHARA_SEIKAKU:4–444；200確認，98／99為亂數而非取消。"""
    from .shop import lb
    st,data,out=ctx.state,ctx.data,ctx.out;c=st.charas[who]
    lb(out);start=out.linecount
    while True:
        # CSVBASE缺欄為0、缺角色是錯誤：
        # reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1383–1418。
        template=data.charas[c.no]
        for slot in BASE_SLOTS:
            st.result[0]=c.base[slot]=c.maxbase[slot]=template.base.get(slot,0)
        st.result[0]=seikaku_check(data,c)
        if st.result[0]==0:
            c.talent[10+st.rng.rand(19)]=1
            if c.talent[28]>0:_clear_traits(c)
        have=sum(c.talent[i]>0 for i in range(600,700))
        _draw(ctx,who,have)
        choice=yield from input_number(ctx)
        if choice==200 and have<=4:break
        out.clearline(out.linecount-start)
        if choice==98:
            candidates=[]
            # DEVIATION: 共用COUNT尚未模型化，沿W07既有COUNT項；此處局部FOR終值19。
            for person in range(10,29):
                if _kojo_color(ctx,who,person) and not c.talent[person]:candidates.append(person)
            out.reset_color()
            # 空集合RAND:0照引擎停止，不發明後備性格。
            # reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:960–970。
            st.result[0]=st.rng.rand(len(candidates))
            _select_personality(c,candidates[st.result[0]])
        elif choice==99:_select_personality(c,10+st.rng.rand(19))
        elif 0<=choice<=18:_select_personality(c,10+choice)
        elif choice==300:_clear_traits(c)
        elif choice==999:
            _clear_traits(c);random_mental_traits(ctx,who,st.rng.rand(3)+1)
        elif 100<=choice<=109 and c.talent[28]==0:
            slots=TRAIT_GROUPS[choice-100]
            active=next((i for i,slot in enumerate(slots) if c.talent[slot]>0),-1)
            selected=active+1
            for i,slot in enumerate(slots):c.talent[slot]=int(i==selected)
    out.printl()
    person=seikaku_check(data,c);st.result[0]=person
    for slot in BASE_SLOTS:c.base[slot]=c.maxbase[slot]=seikaku_hosei(person,slot,c.base[slot])
    if not c.cstr[4] and is_female(data,c):
        if talent(data,c,'古風'):c.cflag[8]=20
        elif talent(data,c,'かるい性格'):c.cflag[8]=11
    baseup_cal_shield(data,st,who)
    # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67：自然終端。
    st.result[0]=0
