"""一人稱設定：ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_SELFCALL:1203–1493。

讀音分析手翻 ERB/口上/口上システム関係/SELF_CALL.ERB@SELF_CALL_ANALYSIS:299–356、@CHECK_SINGLE_SOUND:360–428、@CHECK_DIPHTHONG:432–505；固定字表由原文抽取。
"""
from collections.abc import Generator

from ..state.character import Character
from .action import Ctx
from .akuoti import self_call
from .era import div
from .firstsetting import self_call_list
from .input_request import TextInputRequest, input_number, inputs
from .self_call_text import TEXT, SOUND_ROWS


def _result(ctx: Ctx, *values: int) -> int:
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023：RETURN 僅改指定格。
    for i,v in enumerate(values):
        ctx.state.result[i]=v
    return values[0]


def _single(ctx: Ctx, char: str) -> int:
    # SELF_CALL.ERB@CHECK_SINGLE_SOUND:360–428，STRFINDU 找不到也先寫 RESULT=-1。
    if char=="　":
        return _result(ctx,-1)
    for kind,lines in enumerate(((368,370,372,374,376),(396,398,400,402,404))):
        for row,line in enumerate(lines):
            pos=SOUND_ROWS[line].find(char)
            if pos>=0:
                return _result(ctx,pos+row*20+1,1,kind)
        for line,start in ((384 if kind==0 else 412,6),(389 if kind==0 else 417,76)):
            pos=SOUND_ROWS[line].find(char)
            if pos>=0:
                return _result(ctx,pos+start,0,kind)
    if char in ("ヴ","ー"):
        return _result(ctx,94 if char=="ヴ" else 95,1,2)
    return _result(ctx,-1)


def _diphthong(ctx: Ctx, pair: str) -> int:
    # @CHECK_DIPHTHONG:432–505：原字表每格三個 UTF-16 code unit。
    for start in (439,473):
        for row in range(13):
            pos=SOUND_ROWS[start+row*2].find(pair)
            if pos>=0:
                return _result(ctx,pos//3+row*10+101)
    return _result(ctx,-1)


def analyze(ctx: Ctx, value: str) -> int:
    """@SELF_CALL_ANALYSIS:299–356；維持錯誤時 RESULT 尾格及 RESULTS 的最後單字殘值。"""
    # STRLENFORMU/SUBSTRINGU 依 .NET UTF-16，不按 Python Unicode code point 計數。
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:504–526。
    raw=value.encode("utf-16-le",errors="surrogatepass")
    units=[raw[i:i+2].decode("utf-16-le",errors="surrogatepass") for i in range(0,len(raw),2)]
    _result(ctx,len(units))
    if len(units)>10:
        return _result(ctx,-3)
    codes=[0]*10
    length=0
    kind=99
    for i,char in enumerate(units):
        ctx.state.results[0]=char
        if _single(ctx,char)<0:
            return _result(ctx,-1)
        char_kind=ctx.state.result[2]
        if kind>10 and char_kind<2:
            kind=char_kind
        elif kind!=char_kind and char_kind!=2:
            return _result(ctx,-2)
        codes[length]=ctx.state.result[0]
        if i>0 and ctx.state.result[1]==0:
            if _diphthong(ctx,units[i-1]+char)>0:
                codes[length]=0
                length-=1
                codes[length]=ctx.state.result[0]
        length+=1
    if kind>10:
        kind=1
    if length>4:
        return _result(ctx,-3)
    return _result(ctx,kind,*codes[:4])


def _reading(ctx: Ctx, who: int) -> str:
    """SELF_CALL(7,0,who)：SELF_CALL.ERB:31–65、96–182、254–295、512–717。"""
    st=ctx.state
    c=st.charas[who or st.target]
    value=c.cflag[8]
    pron=div(value,5)%20
    style=value%5
    kind=int(style==2)
    constants=(22031086,22013031086,22031001,2031001,86081086,13060,84005)
    if 0<=pron<=6:
        packed=constants[pron]
        count=(3,4,3,3,3,2,2)[pron]
    else:
        # :293 的 FORM 是未插值固定文字；長度 18，LENGTH=6。
        # :124–125 再設同一 LENGTH 而非上限 4，所以實際讀六個碼。
        st.result[0]=len("CSTR:SELF_TARGET:4")
        count=6
        # :140–165 沒有 7/8 等分支；CAL_VAR 被 :254 零次 FOR 重設為 0。
        packed=div(value,100) if pron==19 else st.temp.narr.get((("SELF_CALL_SUBSTRING", "CAL_VAR"), (0,)), 0)
        if pron==19 and style==3:
            kind=1
    result=""
    for _ in range(count):
        code=packed%1000
        packed=div(packed,1000)
        if code==0:
            continue
        if code<100:
            col=div(code-1,5)
            row=(code-1)%5
            line=(587 if kind==0 else 599)+div(col,4)*2
            text=SOUND_ROWS[line][(col%4)*5+row:(col%4)*5+row+1]
            if kind==0 and col==18 and row==3:
                text="ゔ"
        else:
            col=div(code-101,5)
            row=(code-101)%5*2
            line=(643 if kind==0 else 671)+div(col,2)*2
            text=SOUND_ROWS[line][(col%2)*10+row:(col%2)*10+row+2]
            if kind==0 and col==2 and row!=2:
                # 原作 C_ROW 直接索引，包含超界空字串；保留而不修正。
                text="ゔ"+"ぁぃ　ぇぉ"[row:row+1]
        st.results[0]=text
        result+=text
    # 零次 FOR 仍設定起值：Instraction.Child.cs:1733–1743。
    st.temp.narr[(("SELF_CALL_SUBSTRING", "CAL_VAR"), (0,))]=0
    return result


def _say(ctx: Ctx, line: int, **values: object) -> None:
    command,text=TEXT[line]
    # 僅替換本畫面的已知欄位，不執行 ERB 表達式。
    for old,new in values.items():
        text=text.replace(old,str(new))
    if command.endswith(("L","W")):
        ctx.out.printl(text)
    else:
        ctx.out.print(text)


def _wait(ctx: Ctx) -> Generator[TextInputRequest, object, None]:
    # PRINTW：EmueraConsole.cs:497–508、701–734；不寫 RESULT/RESULTS。
    ctx.out.printl("（按 Enter 繼續）")
    yield TextInputRequest()


def _number(ctx: Ctx) -> Generator[None, int, int]:
    value=yield from input_number(ctx)
    ctx.out.printl(str(value))
    return value


def _default(ctx: Ctx, c: Character) -> int:
    has=lambda name: c.talent[ctx.data.index_of("TALENT",name)]!=0
    return (6 if has("乱暴者") else 5) if has("オトコ") else (4 if has("古風") else 2 if has("かるい性格") else 0)


def selfcall_gen(ctx: Ctx, who: int) -> Generator[None | TextInputRequest, int | str, int]:
    """@FIRSTSETTING_CHARA_SELFCALL:1203–1493，狀態只在 [99] 確認後寫入。"""
    st,out=ctx.state,ctx.out
    c=st.charas[who]
    # #DIM 無 DYNAMIC：reference/emuera-1824/Emuera/GameProc/UserDefinedVariable.cs:27。
    # PRN_VAR/CHR_VAR 不在入口清除，手動讀音取消及無效值跳轉會使用殘值。
    mem=st.temp.locals
    key="FIRSTSETTING_CHARA_SELFCALL:"
    # :1211–1215初始化CALL_LIST的兩層FOR，兩個COUNT元素各自留終值。
    # SELF_CALL_LIST為固定查表且不改COUNT；不能把COUNT:1當作函式區域暫存。
    call_list={}
    for i in range(21):
        st.count[0]=i
        for j in range(3):
            st.count[1]=j
            call_list[i,j]=self_call_list(i,j)
        st.count[1]=3
    st.count[0]=21
    pron=div(c.cflag[8],5)%20
    style=c.cflag[8]%5
    # DEVIATION: S48 修復自訂重入；保留原碼而非重析顯示文字（CHAR_LIB 非完全可逆）。
    # FIRSTSETTING_CHARA_SELFCALL:1216–1219、1466–1475；SELF_CALL_SUBSTRING:161–165。
    existing_custom=c.cflag[8] if pron==19 and style in (3,4) else None
    reading=_reading(ctx,who)
    display=self_call(ctx,who)
    mode="top"
    header=True
    while True:
        if mode=="top":
            _say(ctx,1223)
            _say(ctx,1224,**{"{ARG:0}":who,"%CALLNAME:ARG%":c.callname})
            _say(ctx,1225)
            for i in range(21):
                st.count[0]=i
                if not call_list[i,0]:
                    # BREAK同樣加步進：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2067–2073。
                    st.count[0]+=1
                    break
                label=f"[{i}] {call_list[i,0]}（{call_list[i,1]}）　"
                if pron==i:
                    out.set_color((120,255,0))
                    out.print_plain(label)
                    out.reset_color()
                else:
                    out.print(label)
                if i%5==4:
                    out.printl()
            else:
                st.count[0]=21
            out.printl()
            out.printl()
            if 0<=pron<=20:
                for i in range(3):
                    st.count[0]=i
                    label=f"[{i+30}] {self_call_list(pron,i)}　"
                    if style==i:
                        out.set_color((120,255,0))
                        out.print_plain(label)
                        out.reset_color()
                    else:
                        out.print(label)
                st.count[0]=3
            out.printl()
            out.printl()
            for choice,line in ((21,1258),(22,1262)):
                if pron==choice:
                    out.set_color((120,255,0))
                _say(ctx,line,**{"{一人称_最大+1}":21,"{一人称_最大+2}":22,"%CALLNAME:ARG%":c.callname})
                out.reset_color()
            _say(ctx,1264)
            _say(ctx,{6:1267,5:1269,4:1273,2:1275,0:1277}[_default(ctx,c)])
            out.printl()
            out.printl()
            out.printl(f"読み：{reading or '　-　'}　表記：{display or '　-　'}")
            out.printl()
            if not reading or not display:
                out.set_color((128,128,128))
            _say(ctx,1286)
            out.reset_color()
            _say(ctx,1288)
            mode="menu"
        if mode=="menu":
            r=yield from _number(ctx)
            if 0<=r<=8:
                existing_custom=None
                pron=r
                if style>2:
                    style=0
                reading=self_call_list(pron,1)
                display=self_call_list(pron,style)
            elif 30<=r<=32:
                existing_custom=None
                style=r-30
                if pron>8:
                    pron=0
                reading=self_call_list(pron,1)
                display=self_call_list(pron,style)
            elif r==50:
                # DEVIATION: S48 依首次自訂後切回預設的 :1304–1305 重設字形。
                if existing_custom is not None or not 0<=pron<=20:
                    style=0
                existing_custom=None
                pron=_default(ctx,c)
                # :1304–1322 原作自訂重入未重設字形而越界；上方已修復自訂碼。
                # 此處僅保留其他不合法原始字形的原作越界停止。
                # reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs:2049–2076。
                if not 0 <= style < 3:
                    raise NotImplementedError("FIRSTSETTING_CHARA_SELFCALL：原作 CALL_LIST 第二維越界（性格預設）")
                reading=self_call_list(pron,1)
                display=self_call_list(pron,style)
            elif r in (21,22):
                if r==22:
                    _say(ctx,1389)
                    _say(ctx,1390)
                    value=yield from inputs(ctx)
                    if value in ("","99"):
                        _say(ctx,1393)
                        _say(ctx,1394)
                        _say(ctx,1395)
                        yield from _wait(ctx)
                        mode="top"
                        continue
                    display=value
                else:
                    display=c.callname
                existing_custom=None
                pron=style=r
                if analyze(ctx,display)>=0:
                    reading=display
                    for i in range(4):
                        mem[key+"PRN_VAR",i]=st.result[i+1]
                    mem[key+"CHR_VAR",0]=st.result[0]
                else:
                    reading=""
                    mode="reading"
                    header=True
                    continue
            elif r==98:
                return _result(ctx,98)
            elif r==99:
                if not reading or not display:
                    out.clearline(1)
                    continue
                if existing_custom is not None:
                    c.cflag[8]=existing_custom
                elif 0<=pron<=20:
                    c.cflag[8]=pron*5+style
                else:
                    c.cflag[8]=sum(mem.get((key+"PRN_VAR",i),0)*1000**i for i in range(4))*100+99-mem.get((key+"CHR_VAR",0),0)
                c.cstr[4]=display
                out.printl()
                out.printl()
                if st.flag[999]==1:
                    out.set_color((105,105,105))
                    out.printl()
                    out.printl(f"CFLAG{c.cflag[8]} CSTR{c.cstr[4]} {self_call(ctx,who)}")
                    out.printl()
                    out.reset_color()
                return _result(ctx,99)
            else:
                # :1488–1490 刻意保留原作跳 INPUT_PRN_0（不是主選單）。
                out.clearline(1)
                mode="reading"
                header=False
                continue
            mode="top"
            continue
        if mode=="reading":
            if header:
                for line in range(1334,1341):
                    if line in TEXT:
                        _say(ctx,line,**{"{PRN_MAX}":4,"%CALL_STR:1%":display})
            value=yield from inputs(ctx)
            if value in ("","99"):
                _say(ctx,1344)
                _say(ctx,1345)
                _say(ctx,1346)
                yield from _wait(ctx)
                mode="top"
                continue
            if value=="98":
                for line in range(1349,1359):
                    _say(ctx,line)
                header=False
                continue
            analyzed=analyze(ctx,value)
            if analyzed<0:
                out.printl()
                _say(ctx,{-1:1365,-2:1370,-3:1375}[analyzed])
                out.printl()
                yield from _wait(ctx)
                header=True
                continue
            reading=value
            for i in range(4):
                mem[key+"PRN_VAR",i]=st.result[i+1]
            mem[key+"CHR_VAR",0]=st.result[0]
            mode="top"
