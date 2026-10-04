"""SHOP追加招募；ERB/ゲーム内_行動実行処理/ACTIONsub_TSUIKAYOUSEI_NORMAL.ERB。"""
from .akuoti import dot_after
from .action import print_callname
from .body import set_profile
from .character_defaults import confirm_default_character
from .chara_common import syuzoku_check
from .firstsetting import feat_select_ui, set_feat_default
from .input_request import input_number
from .opening import chara_make_finalize, game_option
from .recruitment_text import TEXT
from .shop import lb, charanum_safe_partycheck
from ..state.constants import GameOption


def recruitment_allowed(state):
    """ERB/インターミッション画面/SHOP.ERB@USERSHOP:293；ERB/DIM.ERH:25。"""
    return state.charanum <= 29 and game_option(state, GameOption.JOIN_RETIRE)


def _say(ctx, *lines):
    """抽取文字的固定欄位替換，不求值ERB表達式。"""
    st=ctx.state
    c=st.charas[st.target] if 0<=st.target<st.charanum else None
    replacements={'{FLAG:250}':str(st.flag[250]), '{TARGET}':str(st.target),
                  '%CALLNAME%':c.callname if c else '',
                  '%PRINT_CALLNAME(TARGET)%':print_callname(st,st.target) if c else ''}
    for line in lines:
        command,text=TEXT[line]
        for old,new in replacements.items(): text=text.replace(old,new)
        (ctx.out.printw if command.endswith('W') else ctx.out.printl)(text)


def recruitment_gen(ctx):
    """@TSUIKAYOUSEI_NORMAL:4–161：無費用、無引退子選單。"""
    st,out,data=ctx.state,ctx.out,ctx.data
    lb(out); _say(ctx,10,11,12,13,14,15,16,17)
    while True:
        choice=yield from input_number(ctx)
        if choice==99:
            # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67：函式末端RESULT=0。
            st.result[0]=0
            _say(ctx,160,161)
            return
        if choice in (0,1,2): break
    st.flag[250]+=1
    _say(ctx,22); lb(out); dot_after(ctx); _say(ctx,25)
    target=st.target
    c=st.add_chara(data,0); who=st.charanum-1; st.target=who
    if choice!=2:
        _say(ctx,30)
        if choice==1:
            c.talent[data.index_of('TALENT','オトコ')]=1
            c.name='汎用キャラ(♂)'
        # DEVIATION: 沿用既有角色製作UI暫略；只走不改設定直接[99]確認。
        confirm_default_character(ctx,who)
    # :39–40；[2]尚未INITIALIZE，race可能是0，不能提前生成種族。
    race=syuzoku_check(c); st.result[0]=race
    _say(ctx,45,46,47,48)
    while True:
        answer=yield from input_number(ctx)
        if answer==0:
            yield from feat_select_ui(ctx,who,race)
            break
        if answer==1:
            _say(ctx,128,129)
            break
        if answer==2:
            set_feat_default(ctx,who,race)
            set_profile(data,c,st.result)
            _say(ctx,135,136)
            break
    lb(out); dot_after(ctx); _say(ctx,143,144)
    if charanum_safe_partycheck(st)>=6: _say(ctx,146)
    else: c.cflag[999]=1
    chara_make_finalize(st,data,who)
    st.result[0]=0
    _say(ctx,153)
    st.target=target
    _say(ctx,160,161)
