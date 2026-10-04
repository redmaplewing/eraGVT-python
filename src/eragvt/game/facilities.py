"""ERB/インターミッション画面/SHOP_ENHANCING.ERB@HOME_ENHANCING的原生翻寫。"""
import re

from .facilities_text import TEXT
from .input_request import TextInputRequest, input_number
from .shop import lb


# :159–182、186–281；(按鈕, bit, 前置bit, 費用, 選單文字行, 完成文字行)。
# bit依ERB/DIM.ERH:173–184；同按鈕依原作ELSEIF次序選第一個符合項。
_RELAX=(
    (0,1,0,500,160,190),(0,512,1,4500,162,198),
    (0,1024,512,8500,164,206),(0,2048,1024,100000,166,214),
    (1,2,0,12000,168,222),(1,4,2,95000,170,230),
    (2,8,0,25800,172,238),(3,16,0,50000,174,246),
    (4,32,0,100000,176,254),(5,64,0,200000,178,262),
    (5,128,64,500000,180,270),(6,256,0,1500000,182,278),
)


def _say(ctx,*lines):
    """固定欄位插值；不執行ERB條件或運算式。"""
    st=ctx.state
    values={'{MONEY}':str(st.money),'{FLAG:200}':str(st.flag[200])}
    for slot,unit in ((50,5000),(51,1000),(52,10000),(54,5)):
        values[f'{{{unit} * FLAG:{slot} + {unit}}}']=str(unit*(st.flag[slot]+1))
        values[f'\\@FLAG:{slot} > 4 ? MAX # {{FLAG:{slot}}}\\@']='MAX' if st.flag[slot]>4 else str(st.flag[slot])
    # 單次替換，角色／文字若含標記也不再次求值。
    pattern=re.compile('|'.join(re.escape(k) for k in values))
    for line in lines:
        command,text=TEXT[line]
        text=pattern.sub(lambda m:values[m[0]],text)
        (ctx.out.printw if command.endswith('W') else ctx.out.printl)(text)


def _short(out):
    """ERB/汎用関数/PRINT_LINE.ERB@SHORTLINE:3–7。"""
    out.printl('――――――――――――――――――――――――――――')


def _number(ctx):
    """reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:701–737：輸入後顯示該值。"""
    value=yield from input_number(ctx)
    ctx.out.printl(str(value))
    return value


def _wait(ctx):
    """PRINTW的Enter等待；不寫RESULT(S)，依EmueraConsole.cs:497–508、701–734。"""
    ctx.out.printl('（按 Enter 繼續）')
    yield TextInputRequest()
    ctx.out.clearline(1)  # 移除本介面額外提示，不計入原作CLEARLINE。


def _error(ctx,line,clear):
    _say(ctx,line)
    yield from _wait(ctx)
    # DEVIATION: 沿用共用CLEARLINE僅刪已完成行，詳見deviations.md的顯示簡化。
    ctx.out.clearline(clear)


def _available(mask,row):
    return not mask&row[1] and (not row[2] or bool(mask&row[2]))


def _main(ctx):
    st,out=ctx.state,ctx.out
    _say(ctx,8); out.drawline(); _say(ctx,10,11); _short(out)
    if st.flag[53]!=0:
        _say(ctx,14); _short(out)
        for bit,line,hide in ((1,17,0),(512,19,0),(1024,21,0),(2048,23,0),(2,25,4),(4,27,0),
                              (8,29,0),(16,31,0),(32,33,0),(64,35,128),(128,37,0),(256,39,0)):
            if st.flag[53]&bit and not st.flag[53]&hide: _say(ctx,line)
    else: _say(ctx,41)
    _short(out); _say(ctx,44,45,46,47,48,49)


def facilities_gen(ctx):
    """@HOME_ENHANCING:3–331；999結束，內層99返回，購買/升級後重繪。"""
    st,out=ctx.state,ctx.out; lb(out)
    while True:
        _main(ctx)
        while True:
            choice=yield from _number(ctx)
            if choice==999:
                # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
                st.result[0]=0
                return
            if choice==3:
                yield from _relax_gen(ctx)
                break
            if choice not in (0,1,2,4):
                yield from _error(ctx,328,2)
                continue
            slot,unit,start=(50,5000,55) if choice==0 else (51,1000,86) if choice==1 else (52,10000,117) if choice==2 else (54,5,297)
            if st.flag[slot]>=5:
                yield from _error(ctx,start,2)
                continue
            if choice==4: _say(ctx,301,302,303,304,306,307)
            else: _say(ctx,start+4,start+5,start+6,start+8,start+9)
            while True:
                confirm=yield from _number(ctx)
                if confirm in (0,1): break
                yield from _error(ctx,320 if choice==4 else start+22,2)
            if confirm==0:
                cost=unit*(st.flag[slot]+1)
                resource=st.flag[200] if choice==4 else st.money
                if resource<cost:
                    line=312 if choice==4 else start+14
                else:
                    if choice==4: st.flag[200]-=cost
                    else: st.money-=cost
                    st.flag[slot]+=1
                    line=316 if choice==4 else start+18
                _say(ctx,line)
                if TEXT[line][0].endswith('W'): yield from _wait(ctx)
            _say(ctx,325 if choice==4 else start+27)
            break


def _relax_gen(ctx):
    """@HOME_ENHANCING:147–294：成功回目錄，失敗只重讀INPUT；不額外確認。"""
    st,out=ctx.state,ctx.out
    while True:
        if st.flag[53]==4095:
            _say(ctx,149); yield from _wait(ctx)
            return
        _say(ctx,153); out.drawline(); _say(ctx,155,156); _short(out)
        for row in _RELAX:
            if _available(st.flag[53],row): _say(ctx,row[4])
        _say(ctx,183)
        while True:
            choice=yield from _number(ctx)
            if choice==99: return
            row=next((r for r in _RELAX if r[0]==choice and _available(st.flag[53],r)),None)
            if row is None:
                yield from _error(ctx,285,2)
                continue
            if st.money<row[3]:
                _say(ctx,289); yield from _error(ctx,292,3)
                continue
            st.money-=row[3]; st.flag[53]|=row[1]
            _say(ctx,row[5],row[5]+1); yield from _wait(ctx)
            break
