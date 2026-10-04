"""角色個別編輯暫略UI時的原作[99]預設確認路徑。"""


def confirm_default_character(ctx, who):
    """ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:9–34、112–122、318–353。"""
    from .opening import chara_make_initialize, decode_weapon_data
    from .chara_common import baseup_cal_shield
    from .body import generate_char_size, top_under, cup_size
    st,data=ctx.state,ctx.data
    c=st.charas[who]
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:9–34／318–353。
    # DEVIATION: 沿用角色製作UI跳過，狀態走原作[99]預設確認；不提供手動編輯。
    items={i:st.item[i] for i in range(100,700) if i in data.items and data.items[i].name}
    for i in items: st.item[i]=1
    if c.cflag[240]==0: chara_make_initialize(st,data,who)
    for dist in (1,2,3):
        if c.cstr[14+dist]: st.result[0]=decode_weapon_data(data,st,who,dist)
        c.cstr[14+dist]=''
    # :112–122的顯示呼叫仍產生RESULT:1–7／RESULTS殘值。
    sizes=generate_char_size(data,c,0,st.result)
    if sizes[4]>0:
        difference,under=top_under(data,c,0)
        st.result[0],st.result[1]=difference,under
        st.result[0],st.results[0]=cup_size(st.result[0])
    st.result[0]=99
    baseup_cal_shield(data,st,who)
    for i in range(4): st.savestr[i]=''
    for i in range(100,700): st.item[i]=items.get(i,0)
