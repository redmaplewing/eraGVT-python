"""SHOP引退；ERB/ヒロイン関連/INTAI.ERB、INTAI_CHARA_LIST.ERB。"""
from .action import config_check_screen
from .era import div, format_percent
from .input_request import TextInputRequest, input_number
from .opening import game_option
from .retirement_text import TEXT
from .shop import lb
from ..state.constants import GameOption


def retirement_allowed(state, menu):
    """ERB/インターミッション画面/SHOP.ERB@USERSHOP:289–292。"""
    return game_option(state,GameOption.JOIN_RETIRE) and (menu==169 or menu==170 and state.charanum>1)


def _say(ctx,*lines,file='INTAI.ERB',who=None):
    """抽取文字的固定欄位替換，不求值ERB表達式。"""
    st=ctx.state; index=st.target if who is None else who; c=st.charas[index]
    replacements={
        '%CALLNAME%':c.callname,'%STR:2500%':ctx.data.str_defaults.get(2500,''),
        '{CFLAG:31 / 2}':str(div(c.cflag[31],2)),
        '{CFLAG:70 / 2}':str(div(c.cflag[70],2)),
        '{LCOUNT}':str(index),'%CALLNAME:LCOUNT,24,LEFT%':format_percent(c.callname,24,True),
        **{f'{{FLAG:{i}}}':str(st.flag[i]) for i in range(251,256)},
    }
    for line in lines:
        command,text=TEXT[file,line]
        for old,new in replacements.items(): text=text.replace(old,new)
        if command.endswith('W'): ctx.out.printw(text)
        elif command.endswith('L'): ctx.out.printl(text)
        else: ctx.out.print(text)


def retirement_list(ctx):
    """非互動呼叫端略過純顯示等待，沒有代選選項。"""
    for request in retirement_list_gen(ctx):
        assert isinstance(request,TextInputRequest)


def _wait(ctx):
    """PRINTW的Enter等待，不是INPUTS，不寫RESULT或RESULTS。

    reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、701–734。
    借用既有文字通道讓Web空白Enter可送出；附加文字只屬操作提示。
    """
    ctx.out.printl('（按 Enter 繼續）')
    yield TextInputRequest()


def retirement_list_gen(ctx):
    """INTAI.ERB@CHAR_INTAI_LIST:344–361；HTML紀錄沒有分頁／截斷。"""
    st,out=ctx.state,ctx.out; lb(out)
    if st.savestr[50]=='':
        _say(ctx,347,348); yield from _wait(ctx); lb(out)
    else:
        _say(ctx,351); out.drawline(); _say(ctx,353); out.drawline(); _say(ctx,355)
        out.html_print(st.savestr[50]); _say(ctx,357); out.drawline(); _say(ctx,359,360)
        yield from _wait(ctx)
    # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67：函式末端RESULT=0。
    st.result[0]=0


def retirement_gen(ctx):
    """INTAI.ERB@CHARA_INTAI:1–22；INTAI_CHARA_LIST.ERB@INTAI_CHARA_LIST:7–48。"""
    st,out=ctx.state,ctx.out
    _say(ctx,9,file='INTAI_CHARA_LIST.ERB')
    labels={1:18,4:24,9:29,10:31,11:33}
    for who,c in enumerate(st.charas):
        if who==st.MASTER or c.cflag[0] in (2,3): continue
        _say(ctx,16,file='INTAI_CHARA_LIST.ERB',who=who)
        if c.cflag[0] in labels: _say(ctx,labels[c.cflag[0]],file='INTAI_CHARA_LIST.ERB',who=who)
        _say(ctx,34,file='INTAI_CHARA_LIST.ERB',who=who)
    _say(ctx,36,file='INTAI_CHARA_LIST.ERB')
    while True:
        who=yield from input_number(ctx)
        if who==999:
            st.result[0]=0
            return
        if 1<=who<st.charanum and st.charas[who].cflag[0] not in (2,3): break
        _say(ctx,42,file='INTAI_CHARA_LIST.ERB')
    st.target=who; _say(ctx,7,8,9,10,11)
    first=yield from _confirmation(ctx)
    if first==0:
        _say(ctx,14,15,16)
        if (yield from _confirmation(ctx))==1:
            yield from _retirement_report_gen(ctx)
            st.flag[251]+=1
            # reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1061–1067：
            # DELCHARA只RemoveAt，不修ASSI／角色內索引；INTAI.ERB@OLD_GIRL:37另設TARGET=0。
            st.del_chara(st.target)
            st.target=0
    st.result[0]=0


def _confirmation(ctx):
    """INTAI.ERB@INPUT_ROOP:41–49；上界包含2，雖然只顯示0/1。"""
    while True:
        value=yield from input_number(ctx)
        if 0<=value<=2: return value


def retirement_report(ctx):
    """非互動呼叫端略過純顯示等待，沒有代選選項。"""
    for request in _retirement_report_gen(ctx):
        assert isinstance(request,TextInputRequest)


def _retirement_report_gen(ctx):
    """INTAI.ERB@MASSAGE_INTAI:51–342；依原作次序選文字與紀錄，不新增敘事。"""
    st,out,data=ctx.state,ctx.out,ctx.data; c=st.charas[st.target]
    def t(name): return c.talent[data.index_of('TALENT',name)]
    def a(name): return c.abl[data.index_of('ABL',name)]
    def b(name): return c.base[data.index_of('BASE',name)]
    local0=1; local1=0
    for trait,line in (('近距離得意',66),('中距離得意',68),('遠距離得意',70)):
        if t(trait):
            _say(ctx,line,72); break
    else: _say(ctx,74)
    if t('繁殖袋'): _say(ctx,82)
    if t('四肢欠損'): _say(ctx,84)
    points=div(b('体力基礎')+b('気力基礎'),10)+sum(b(n) for n in ('性耐性基礎','攻撃','防御','敏捷','知性'))
    if t('繁殖袋') or t('四肢欠損'): _say(ctx,86)
    elif points>746: _say(ctx,88)
    else:
        for threshold,line,score in ((580,91,1),(480,94,2),(380,97,3),(280,100,4),(180,103,5),(80,106,5)):
            if points>=threshold:
                _say(ctx,line); local1=score; break
        else: _say(ctx,109); local1=6
    for name,line in (('体力基礎',114),('気力基礎',116),('性耐性基礎',118)):
        if b(name)<=0: _say(ctx,line)
    _say(ctx,119)
    for name,line in (('攻撃',121),('防御',123),('敏捷',125),('知性',127)):
        if b(name)<=0: _say(ctx,line)
    _say(ctx,128); yield from _wait(ctx)
    senses=[a(n) for n in ('Ｃ感覚','Ｖ感覚','Ａ感覚','Ｂ感覚')]
    if t('完堕ち'): _say(ctx,132)
    elif min(senses)==5: _say(ctx,135)
    elif sum(senses)>14: _say(ctx,138)
    elif max(senses)==5:
        _say(ctx,141)
        for name,line in (('Ａ感覚',143),('Ｖ感覚',145),('Ｂ感覚',147),('Ｃ感覚',149)):
            if a(name)==5: _say(ctx,line); break
    elif max(senses)>2:
        _say(ctx,152)
        for name,line in (('Ａ感覚',154),('Ｖ感覚',156),('Ｂ感覚',158),('Ｃ感覚',160)):
            if a(name)>2: _say(ctx,line); break
    else: local0+=1
    if local0==0: _say(ctx,167)
    elif t('完堕ち'): _say(ctx,169)
    elif max(a(n) for n in ('従順','欲望','奉仕精神','マゾっ気'))>3: _say(ctx,171)
    for name,line in (('従順',175),('欲望',177),('奉仕精神',180),('マゾっ気',184)):
        if a(name)>3: _say(ctx,line); break
    else: local0+=2
    if any(a(n) for n in ('触手中毒','自慰中毒','精液中毒')):
        if local0>=3: _say(ctx,192)
        elif local0==2: _say(ctx,194)
        elif local0==1: _say(ctx,196)
        else: _say(ctx,198,199)
    for name,line in (('触手中毒',205),('自慰中毒',207),('精液中毒',209),('噴乳中毒',211),('射精中毒',213)):
        if a(name): _say(ctx,line); break
    else: local0+=4
    _say(ctx,218)
    # ERB/汎用関数/PRINT_LINE.ERB@DOT_AFTER:43–55；此處保留每個PRINTW等待。
    for text in ('・','・・','・・・'):
        if text=='・・・' or config_check_screen(st,3)==0:
            out.printw(text); yield from _wait(ctx)
        else: out.printl(text)
    # :222–332的先後順序與計數器差異照原作，含缺肢分支未加分類計數。
    if c.cflag[0]==9:
        if t('毀滅倒計時')==-10:
            _say(ctx,224,225,226,227,228); reason,current='生贄虐殺','死亡'
        elif t('毀滅倒計時')==-11:
            _say(ctx,232,233,234,235); reason,current='残虐処刑','死亡'
        elif t('苗床化'):
            _say(ctx,239,240,241,242,243,244,245); reason,current='触手吸収','苗床'
        else:
            _say(ctx,249,250,251,252,253,254,255); reason,current='触手喰食','死亡'
        st.flag[255]+=1
    elif c.cflag[0]==1:
        _say(ctx,261,262,263,264,265,266,267,268); reason,current='敗北幽閉','推定死亡'
        st.flag[255]+=1
    elif c.cflag[0]==4:
        if t('四肢欠損'):
            _say(ctx,274,275,276,277,278,279,280,281); reason,current='残虐拷問','推定死亡'
        else:
            _say(ctx,285,286,287,288,289,290,291,292); reason,current='拉致監禁','失踪'
        st.flag[255]+=1; _say(ctx,297); yield from _wait(ctx)
    elif t('四肢欠損')>0 and t('繁殖袋')<1:
        _say(ctx,310); reason,current='廃品除隊','存命'
    elif t('繁殖袋'):
        _say(ctx,314); reason,current='人格破滅','存命'; st.flag[254]+=1
    elif local0>6 and local1<3:
        _say(ctx,319); reason,current='自主除隊','存命'; st.flag[252]+=1
    elif local0>3 or local1<5:
        _say(ctx,324); reason,current='後勤引退','存命'; st.flag[253]+=1
    else:
        _say(ctx,329); reason,current='長期療養','存命'; st.flag[254]+=1
    # reference/emuera-1824/Emuera/GameData/StrForm.cs:248–263：%字串,寬度,方向%不截斷。
    record='　　'+format_percent(c.name,30,True)+' '+format_percent(reason,8,False)+' '+format_percent(current,20,False)+' <br> <br>'
    _say(ctx,335); yield from _wait(ctx)
    out.drawline(); _say(ctx,337,338)
    out.html_print(record); out.drawline(); st.savestr[50]+=record; _say(ctx,342)
    yield from _wait(ctx)
    st.result[0]=0
