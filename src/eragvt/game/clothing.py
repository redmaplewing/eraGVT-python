"""SHOP 衣裝設定。原作：ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB。

INPUT／INPUTS 使用 input_request 的已查證共用 RESULT 通道。
"""
from .battle.cloth import cloth_hosei, customize_commonparts_cal, figure_split
from .clothing_text import DESCRIPTIONS, MENUS, BONDAGE_TEXT
from .clothing_custom import encode_custom, category_blocked, choice_blocked, change_custom
from .input_request import input_number, inputs


def _name(ctx, cid):
    item = ctx.data.items.get(cid)
    return item.name if item else ""


def description(ctx, cid):
    """CLOTHDATA*.ERB@CLOTH_DESCRIPTION_* 的原文靜態文字。"""
    for text in DESCRIPTIONS.get(cid, ()):
        ctx.out.printl(text)


def _undo_spats(c):
    """CLOTH_WEAR.ERB@CLOTH_SETTING_INNER:481–564：換掉308撤除體操服的下半身設定。"""
    for eid in (103, 3):
        eq = c.equip[eid]
        d = lambda n: figure_split(eq, n)
        if d(4) != 2:
            continue
        weight = -int(d(2) in (1, 2)) - 2 * int(d(2) == 3)
        weight -= int(d(4) == 1) + 4 * int(d(4) == 2)
        weight += int(d(2) == 4) + int(d(4) == 3)
        weight += 2 * int(d(4) == 4) + int(d(5) == 4)
        if weight < 0:
            eq += weight * 10**9
        if weight > 0:
            eq -= weight * 10**10
        if d(4) == 2:
            eq -= 4 * 10**11
        if d(4) == 4:
            eq -= 2 * 10**12
        if d(5) == 4:
            eq -= 10**12
        c.equip[eid] = eq - 2000


def clothing_setting_gen(ctx, who, slot):
    """@CLOTH_SETTING_OUTER:251／OUTER2:326／INNER:425／MISC:581。

    只選持有值恰等於1的物品。選取與確認分開；卸下不清自訂或名稱。
    """
    st, out = ctx.state, ctx.out
    c = st.charas[who]
    check = c.cflag[slot]
    lo, hi, label = {
        40: (100, 200, "アウター"),
        41: (100, 300, "アウター（変身後）"),
        42: (300, 400, "インナー"),
        43: (500, 600, "その他装備品"),
    }[slot]
    fallen = lambda: c.exp[ctx.data.index_of("EXP", "陥落経験")] > 0
    transform = lambda: c.talent[ctx.data.index_of("TALENT", "変身能力")]
    while True:
        out.printl()
        out.printl(f"{label}を選んでください")
        out.drawline()
        if slot != 43 and ((lo <= check < hi and st.item[check] == 1) or (slot == 41 and check == 401)):
            out.printl(_name(ctx, check))
            description(ctx, check)
            out.drawline()
        for cid in range(lo, hi):
            if slot == 41 and cid == 197:
                continue
            if st.item[cid] == 1 and _name(ctx, cid):
                out.printl(f"[{cid}]{_name(ctx, cid)}")
        if slot == 41 and fallen():
            out.printl(f"[401]{_name(ctx, 401)}")
        out.drawline()
        out.printl("[0]変更しないで戻る")
        out.printl("[1]変更する")
        out.printl(f"[2]{label}を設定しない")
        r = yield from input_number(ctx)
        if lo <= r < hi and st.item[r] == 1:
            check = r
        elif slot == 41 and r == 401 and fallen():
            check = r
        elif r == 0:
            return
        elif r == 2:
            c.cflag[slot] = 0
            out.printl(f"{label}を設定しませんでした")
            out.printw()
            return
        elif r == 1:
            if slot in (40, 41) and check == 197 and st.item[check] == 1 and transform() != -1:
                out.printw("このアウターは非戦闘員専用です")
            elif slot == 41 and check == 401 and not fallen():
                out.printw("このアウターは陥落経験が無いと付けられません")
            elif (lo <= check < hi and st.item[check] == 1) or (slot == 41 and check == 401):
                if slot == 41 and c.cflag[41] != check:
                    for eid in range(600, 700):
                        c.equip[eid] = 0
                c.cflag[slot] = check
                out.printl(f"{label}を{_name(ctx, check)}に変更しました")
                out.printw()
                if slot == 42:
                    if check == 399:
                        c.cflag[42] = 400
                        from .action import print_callname
                        out.printw()
                        for text in BONDAGE_TEXT:
                            out.printl(text.replace("%PRINT_CALLNAME(ARG)%", print_callname(st, who)).replace("%ITEMNAME:399%", _name(ctx,399)))
                        out.printw()
                    if c.cflag[42] != 308:
                        _undo_spats(c)
                return
            else:
                out.printw("正しい値を入力してください")
        else:
            out.printw("正しい値を入力してください")


def remove_tentacle_cloth_gen(ctx, who):
    """@CLOTH_RESETTING_TENTACLECLOTH:637–663。"""
    st, out = ctx.state, ctx.out
    while True:
        name = _name(ctx, 400)
        out.printl(f"{name}を取り外すには触手の欠片が1個必要です（現在の所持数：{st.flag[200]}個）")
        out.printl(f"{name}を取り外しますか？")
        out.printl("[0]いいえ")
        out.printl("[1]はい")
        r = yield from input_number(ctx)
        if r == 0:
            return
        if r == 1:
            if st.flag[200] < 1:
                out.printl("触手の欠片が足りません")
                out.printw()
            else:
                st.flag[200] -= 1
                st.charas[who].cflag[42] = 0
                out.printl(f"{name}を取り外しました")
                out.printw()
                return
        else:
            out.printw("正しい値を入力してください")


def _hosei(ctx, who, cid, mode, shopr=0):
    value = cloth_hosei(ctx, who, cid, mode, shopr)
    # 共通処理@CLOTH_HOSEI:63–90：SUBSTRING 寫 RESULTS:0；未找到與 ! 分岐不寫。
    text = ctx.state.savestr[0]
    start = text.find(mode)
    if start >= 0:
        start += len(mode)
        if text[start:start+1] != "!":
            end = text.find(",", start)
            at = text.find("@", start)
            if at >= 0 and at <= end:
                if ctx.state.charas[who].cflag[1] > 0:
                    start = at+1
                else:
                    end = at
            ctx.state.results[0] = text[start:end] if end >= 0 else text[start:]
    ctx.state.result[0] = value
    return value


def _choice_text(fragments, blocked=False):
    if not fragments:
        return ""
    if len(fragments) == 1:
        return fragments[0]
    return fragments[0] + (fragments[1] if blocked else fragments[2])


def _performance(ctx, who, cid, slot, parts=False):
    """CLOTH_WEAR.ERB@CLOTH_CUSTOMIZE_OUTER:706–918、OUTER2:978–1119、INNER:1320–1514。"""
    from .era import div, mod

    c = ctx.state.charas[who]
    inner = slot == 42
    eid = cid-100 if cid < 200 and c.cflag[1] == 0 else cid
    weight = figure_split(c.equip[eid],11)-figure_split(c.equip[eid],10)
    words = []

    def get(mode):
        value = _hosei(ctx,who,cid,mode)
        return customize_commonparts_cal(ctx,value,mode) if parts else value

    def ratio(value):
        return f"{div(value,100)}.{div(mod(value,100),10)}" + (str(mod(value,10)) if mod(value,10) else "")

    for mode,label in (("KOUGEKI","攻撃"),("BOUGYO","防御"),("BINSYOU","敏捷"),("CHISEI","知性")):
        value = get(mode)
        if value != 100:
            words.append(f"{label}{ratio(value)}倍")
    for mode,label in (("TAIRYOKU","体力"),("KIRYOKU","気力")):
        base = _hosei(ctx,who,cid,mode)
        value = customize_commonparts_cal(ctx,base,mode) if parts else base
        value += (100-base) if parts else (10 if cid>199 and not inner else 5)
        if value != 100:
            words.append(f"戦闘中の{label}の減少量{ratio(value)}倍")
    if not parts:
        value = get("SEITAISEI")
        if value != (95 if inner else 100):
            words.append(f"戦闘中の性耐性の減少量{ratio(value+(5 if inner else 0))}倍")
        value = get("YUDAN")
        if inner:
            other = c.equip[cid-100]  # :1403 原作本欄特意/誤用ID-100，照原文。
            value += figure_split(other,15)-figure_split(other,14)
        if value != 100:
            words.append(f"触手の油断度の上昇量{ratio(value)}倍")
    value = get("CRITICAL")
    if value:
        words.append(f"クリティカル補正 +{value}％")
    if not parts:
        if not inner:
            value = get("HIT") + weight
            if value:
                words.append(f"命中率補正 {value:+}％")
        value = get("AVOID")
        if value:
            words.append(f"回避率補正 +{value}％")
    for mode,label in (("EXBOOST","EXゲージ増幅"),("AIRPLUS","空中性能強化")):
        if get(mode)>0:
            words.append(label)
    for mode,label in (("LIQUID","粘液"),("WAVE","邪気")):
        value = get(mode)
        if value <= 90:
            words.append(f"{label}ダメージ軽減（{'大' if value<=70 else '中' if value<=80 else '小'}）")
    if not parts:
        if inner and get("ANTICUP")>0:
            words.append("快Ｃ自動増加防止")
        if not inner and get("HEALUP")>0:
            words.append("支援時の回復効果増幅")
        if not inner and get("NOINNER")>0:
            words.append("インナー兼用")
        value = get("SHYNESS")
        if inner and value<=80:
            words.append(f"露出軽減（{'大' if value<=20 else '中' if value<=60 else '小'}）")
        elif not inner and value>100:
            words.append(f"露出度が高い（{'大' if value>130 else '中' if value>115 else '小'}）")
        if inner and get("HEALUP")>0:
            words.append("支援時の回復効果増幅")
    ctx.out.printl("【 基本 】"+"　".join(words))
    if not parts:
        words = []
        if inner:
            oil = figure_split(c.equip[eid],15)-figure_split(c.equip[eid],14)
            if oil:
                words.append(f"触手の油断度{oil:+}％")
        elif weight:
            words.append(f"命中{-weight:+}％")
        protection = figure_split(c.equip[eid],13)-figure_split(c.equip[eid],12)
        if protection:
            label = "挿入抵抗" if inner or _hosei(ctx,who,cid,"NOINNER") else "下着保護"
            words.append(f"{label}{5*protection:+}％")
        ctx.out.printl("【 補正 】"+"　".join(words))


def _option_gen(ctx, options, current, blocked, inner=False):
    """共通処理@CLOTH_CUSTOMIZE_OPTION_PRINT:277–392／INNER:400–515。"""
    for i, text in enumerate(options):
        flavor, _, effect = text.partition("@")
        if effect.startswith("!!"):
            effect = effect[2:]
        for level in range(1,7):
            effect = effect.replace(f"軽{level}", f"耐久-{5*level} " + ("" if inner else f"命中+{level} "))
            effect = effect.replace(f"重{level}", f"耐久+{5*level} " + ("" if inner else f"命中-{level} "))
            effect = effect.replace(f"油{level}", f"油断度+{level} ") if inner else effect
            effect = effect.replace(f"油-{level}", f"油断度-{level} ") if inner else effect
            effect = effect.replace(f"護{level}", f"{'挿入抵抗' if inner else '下着保護'}+{5*level}")
            effect = effect.replace(f"晒{level}", f"{'挿入抵抗' if inner else '下着保護'}-{5*level}")
        ctx.state.results[0] = effect  # 共通処理:285–383／408–505 REPLACE的最後結果。
        if blocked[i]:
            ctx.out.set_color((105, 105, 105))
        elif i == current:
            ctx.out.set_color((120, 250, 0))
        ctx.out.printl(f" [{i}]{flavor}　{effect}")
        ctx.out.reset_color()
    while True:
        r = yield from input_number(ctx)
        if 0 <= r < len(options) and not blocked[r]:
            return r


def _read_custom(ctx, value, number):
    """各CLOTH_CUSTOMIZE_OPTION_*及共通処理@COPY91:538–545的REPEAT。

    FIGURE_SPLIT使用LOCAL，不改COUNT；仍於CALL前設定、CALL後以共享COUNT
    寫入及步進（reference/emuera-1824/Emuera/GameProc/Function/
    Instraction.Child.cs:2054–2161）。
    """
    st = ctx.state
    custom = [0] * number
    st.count[0] = 0
    while st.count[0] < number:
        custom[st.count[0]] = figure_split(value, st.count[0] + 1)
        st.count[0] += 1
    return custom


def custom_clothing_gen(ctx, who, slot):
    """CLOTH_WEAR.ERB@CLOTH_CUSTOMIZE_OUTER:668–937／INNER:1293–1533。

    原作雖保存 KEEPTARGET，這兩個函式不還原 TARGET；返回99時CFLAG:1清零。
    """
    st, out = ctx.state, ctx.out
    c = st.charas[who]
    cid = c.cflag[slot]
    if slot == 41 and c.talent[ctx.data.index_of("TALENT", "変身能力")] > 0:
        c.cflag[1] = 1
    st.target = who
    if cid not in MENUS:
        # 原作 TRYCALLFORM 無同名函式時直接落到函式末端。
        st.result[0] = 0
        return
    menu = MENUS[cid]
    eid = cid - 100 if cid < 200 and c.cflag[1] == 0 else cid
    while True:
        out.printl("カスタマイズ項目を選んでください" + ("（変身時）" if slot == 41 else ""))
        out.drawline()
        out.printl(_name(ctx, cid))
        _performance(ctx,who,cid,slot)
        custom = _read_custom(ctx, c.equip[eid], menu["count"])
        for field, variants in menu["choices"].items():
            variant = 0 if cid != 115 or 4 <= custom[1] <= 7 else len(variants)-1
            choices = variants[variant]
            if field < len(custom) and 0 <= custom[field] < len(choices):
                fragments = choices[custom[field]]
                text = _choice_text(fragments)
                if not text and menu["local_text"]:
                    text = menu["local_text"][1]
                out.print(f"[{text.partition('@')[0]}]")
        if c.cflag[1] > 0 and menu["extra"]:
            extra = c.cflag[900+eid]
            if 0 <= extra < len(menu["extra"]):
                out.print(f"[{_choice_text(menu['extra'][extra])}]")
        out.printl()
        hp = _hosei(ctx, who, cid, "HP")
        if hp != -1 and slot != 42:
            hp = customize_commonparts_cal(ctx, hp, "HP")
        out.printl(f"【耐久力】{hp if hp > 0 else '─'}")
        disabled = []
        for i, fragments in enumerate(menu["categories"]):
            off = not fragments[0] or category_blocked(cid, i, custom, st.flag[54])
            disabled.append(off)
            if fragments[0]:
                if off:
                    out.set_color((105, 105, 105))
                text = _choice_text(fragments, off)
                if off and len(fragments) > 3 and ((cid==102 and i==3 and custom[2]==7)
                    or (cid==104 and i==2 and custom[1]==3) or (cid==120 and i==4 and custom[2]==5)
                    or (cid==132 and i==2 and custom[1]==5)):
                    text = fragments[0]+fragments[3]
                if off and "!!" in text:
                    st.results[0] = ""
                out.printl(f" [{i*10}]{text.replace('!!', '　')}")
                out.reset_color()
        if 0 <= eid <= 199 and c.cflag[1] > 0:
            out.printl(f" [{len(menu['categories'])*10}]追加装備")
        out.printl(" [90]初期化")
        same = c.cflag[40] == c.cflag[41]
        if (eid < 300 or eid > 400) and same:
            other = "変身前" if c.cflag[1] > 0 else "変身後"
            out.printl(f" [91]{other}のカスタマイズをコピー")
            out.printl(f" [92]{other}のカスタマイズにペースト")
        out.printl(" [99]戻る")
        st.result[0] = 0
        while True:
            r = yield from input_number(ctx)
            if r >= 0 and r % 10 == 0 and r // 10 < len(disabled) and disabled[r//10]:
                continue
            if r == 99:
                c.cflag[1] = 0
                st.result[0] = 0
                return
            if r == 90:
                c.equip[eid] = 0
                if c.cflag[1] > 0:
                    c.cflag[900 + eid] = 0
                custom = [0] * menu["count"]
                break
            if r == 91 and same and cid < 300:
                other = eid - 100 if c.cflag[1] > 0 else eid + 100
                custom = _read_custom(ctx, c.equip[other], menu["count"])
                break
            if r == 92 and same and cid < 300:
                other = eid - 100 if c.cflag[1] > 0 else eid + 100
                c.equip[other] = c.equip[eid]
                break
            if r == menu.get("extra_input") and c.cflag[1] > 0:
                values = [_choice_text(f) for f in menu["extra"]]
                c.cflag[900 + eid] = yield from _option_gen(ctx, values, c.cflag[900+eid], [False]*len(values))
                break
            field = r // 10
            if r < 0 or r % 10 or field not in menu["choices"]:
                continue
            variants = menu["choices"][field]
            variant = 0 if cid != 115 or 4 <= custom[1] <= 7 else len(variants)-1
            fragments = variants[variant]
            blocked = [choice_blocked(cid, field, i, custom, c.cflag[42], st.flag[54]) for i in range(len(fragments))]
            values = [_choice_text(f, blocked[i]) for i, f in enumerate(fragments)]
            for i, text in enumerate(values):
                if not text:
                    values[i] = menu["local_text"][0 if blocked[i] else 1]
            choice = yield from _option_gen(ctx, values, custom[field], blocked, cid >= 300)
            change_custom(cid, field, choice, custom)
            break
        if r != 92:
            c.equip[eid] = encode_custom(cid, custom, state=st)
        st.result[0] = -1


def custom_parts_gen(ctx, who, slot=41):
    """CLOTH_WEAR.ERB@CLOTH_CUSTOMIZE_OUTER2:941–1290。"""
    st, out = ctx.state, ctx.out
    c = st.charas[who]
    keep = st.target
    st.target = who
    cid = c.cflag[slot]
    while True:
        maximum = _hosei(ctx, who, cid, "SLOT")
        used = sum(c.equip[i] > 0 for i in range(600, 700))
        out.printl("カスタマイズ項目を選んでください")
        out.printl(_name(ctx, cid))
        if cid == 200:
            out.printl("下着へのダメージ軽減")
        if cid == 299:
            out.printl("避妊効果")
        if _hosei(ctx,who,cid,"NOINNER") > 0:
            out.printl("インナー兼用")
        # CLOTH_WEAR.ERB@CLOTH_CUSTOMIZE_OUTER2:983–989：先兩個REPEAT，
        # 再CALL各補正；零／負上限的第二輪也先把COUNT清零。
        out.print("スロット数：")
        st.count[0] = 0
        while st.count[0] < used:
            out.print("●")
            st.count[0] += 1
        st.count[0] = 0
        while st.count[0] < maximum - used:
            out.print("〇")
            st.count[0] += 1
        out.printl()
        _performance(ctx,who,cid,slot,True)
        hp = _hosei(ctx,who,cid,"HP")
        if hp != -1:
            hp = customize_commonparts_cal(ctx,hp,"HP")
        out.printl(f"【耐久力】{hp if hp>0 else '─'}")
        blocked = set()
        for label, lo, hi in (("汎用",600,660),("羽織",660,670),("胸部",670,680),("腕部",680,690),("脚部",690,700)):
            out.printl(f"【{label}】")
            for part in range(lo, hi):
                if st.item[part] != 1:
                    continue
                off = ((part == 672 and c.talent[ctx.data.index_of("TALENT", "貧乳")] > 0)
                       or (part == 673 and c.talent[ctx.data.index_of("TALENT", "巨乳")] > 0)
                       or (690 <= part < 700 and cid in (200, 299)))
                if off:
                    blocked.add(part)
                    out.set_color((105, 105, 105))
                elif c.equip[part] > 0:
                    out.set_color((120, 255, 0))
                out.printl(f"[{part}]{_name(ctx,part)}")
                out.reset_color()
        out.printl("[999]決定")
        r = yield from input_number(ctx)
        if r == 999:
            st.target = keep
            st.result[0] = 0
            return
        if 600 <= r <= 700 and st.item[r] > 0:
            if c.equip[r] > 0:
                if r not in blocked:
                    c.equip[r] = 0
            elif c.equip[r] == 0:
                if r not in blocked:
                    if 660 <= r < 700:
                        base = r // 10 * 10
                        for part in range(base, base+10):
                            if c.equip[part] > 0:
                                c.equip[part] = 0
                                used -= 1
                    if maximum - used > 0:
                        c.equip[r] = 1
                out.printl(_name(ctx,r))
                description(ctx,r)


def cloth_wear_gen(ctx):
    """CLOTH_WEAR.ERB@CLOTH_WEAR:3–245。"""
    from .gather import chara_list
    from .clothing_inventory import inventory_gen
    from .era import cp932_len, format_percent

    st, out = ctx.state, ctx.out
    while True:
        out.printl("【衣装の設定】")
        if st.charanum <= 2:
            who = 1
            st.result[0] = 1
        else:
            out.printl("[変身前アウター]　[変身後アウター]　[インナー]　[その他】")
            for c in st.charas[1:]:
                names = [c.cstr[8] or _name(ctx,c.cflag[40]) or "なし",
                         c.cstr[9] or _name(ctx,c.cflag[41]) or "なし",
                         _name(ctx,c.cflag[42]) or "なし", _name(ctx,c.cflag[43]) or "なし"]
                if c.talent[ctx.data.index_of("TALENT", "変身能力")] != 1:
                    names[1] = "×"
                for i in (0,1):
                    if i == 1 and names[1] == "×":
                        continue
                    if c.cflag[40+i] == 0:
                        names[i] = "なし"
                    elif c.cstr[8+i] and cp932_len(c.cstr[8+i]) >= 21:
                        # reference/emuera-1824/Emuera/_Library/LangManager.cs:40–84。
                        text = ""
                        for ch in c.cstr[8+i]:
                            text += ch
                            if cp932_len(text) >= 18:
                                break
                        st.results[0] = text
                        names[i] = text + "…"
                out.printl(format_percent(c.name,21,True)+"".join(format_percent(n,23 if i==2 else 21,True) for i,n in enumerate(names)))
            out.drawline()
            selection = chara_list(ctx, 1, 0)
            next(selection)
            while True:
                answer = yield from input_number(ctx)
                try:
                    selection.send(answer)
                except StopIteration as done:
                    who = done.value
                    st.result[0] = who
                    break
        if who == 999:
            st.result[0] = 0
            return
        c = st.charas[who]
        while True:
            ability = c.talent[ctx.data.index_of("TALENT", "変身能力")]
            out.drawline()
            out.printl(f"◆{c.name}の衣装設定")
            for slot, label in ((40,"アウター"),(41,"アウター（変身後）"),(42,"インナー"),(43,"その他　")):
                if slot == 41 and ability != 1:
                    continue
                name = _name(ctx,c.cflag[slot]) or "なし"
                if slot in (40,41) and c.cstr[slot-32] and c.cflag[slot]:
                    name = f"{c.cstr[slot-32]}（{name}）"
                out.printl(f"【{label}】{name}")
            out.drawline()
            out.printl("どの衣装を設定しますか？")
            slots = {1:40}
            if ability in (0,-1):
                slots.update({2:42,3:43})
            elif ability == 1:
                slots.update({2:41,3:42,4:43})
            custom = {}
            labels = {40:"アウター",41:"アウター（変身後）",42:"インナー",43:"その他装備品"}
            for command, slot in slots.items():
                out.print(f"[{command}]{labels[slot]}　")
                if slot != 43:
                    custom[slot] = _hosei(ctx, who, c.cflag[slot], "SLOT")
                    if custom[slot] >= 0 or c.cflag[slot]:
                        if custom[slot] < 0:
                            out.set_color((105,105,105))
                            out.print_plain(f"[{command*10}]カスタマイズ　")
                        else:
                            out.print(f"[{command*10}]カスタマイズ　")
                        out.reset_color()
                if slot in (40,41) and c.cflag[slot]:
                    out.print(f"[{command*10+1}]名称変更　")
                    if c.cstr[slot-32]:
                        out.print(f"[{command*10+2}]消去")
                out.printl()
            out.drawline()
            out.printl("[100]所持衣装一覧")
            out.drawline()
            out.printl("[999]戻る")
            r = yield from input_number(ctx)
            if r == 999:
                if st.charanum < 3:
                    st.result[0] = 0
                    return
                break
            input_slots = dict(slots)
            if ability < 1:
                input_slots.update({2:42,3:43})
            if r in input_slots:
                slot = input_slots[r]
                if slot == 42 and c.cflag[42] == 400:
                    yield from remove_tentacle_cloth_gen(ctx, who)
                else:
                    yield from clothing_setting_gen(ctx, who, slot)
            elif r in (11,12,21,22) and (r < 20 or ability == 1):
                slot = 40 if r < 20 else 41
                if c.cflag[slot]:
                    if r % 10 == 1:
                        out.printl("名称を入力してください：")
                        c.cstr[slot-32] = yield from inputs(ctx)
                    else:
                        c.cstr[slot-32] = ""
                else:
                    out.printw("正しい値を入力してください")
            elif r in (10,20,30):
                slot = slots.get(r//10)
                if slot in custom and custom[slot] >= 0 and c.cflag[slot]:
                    if slot == 41 and custom[slot] > 0:
                        yield from custom_parts_gen(ctx,who,slot)
                    else:
                        yield from custom_clothing_gen(ctx,who,slot)
                elif r == 20 and ability < 1 or r == 30 and ability == 1:
                    # :218–222 此分岐內條件不成立時不GOTO，落到函式末端。
                    st.result[0] = 0
                    return
                else:
                    out.printw("正しい値を入力してください")
            elif r == 100:
                yield from inventory_gen(ctx)
            else:
                out.printw("正しい値を入力してください")
