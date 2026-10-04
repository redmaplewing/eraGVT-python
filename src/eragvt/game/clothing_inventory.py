"""所持衣裝瀏覽；ERB/インターミッション画面/SHOP_CLOTH.ERB@SHOW_CLOTH:13–252。"""
from .battle.cloth import cloth_hosei
from .clothing_text import PARTS
from .input_request import input_number

MODES = ("KOUGEKI", "BOUGYO", "BINSYOU", "CHISEI", "TAIRYOKU", "KIRYOKU", "SEITAISEI", "YUDAN", "HIT", "AVOID", "CRITICAL", "LIQUID", "WAVE", "SHYNESS", "ANTIBUP", "ANTICUP", "HEALUP", "EXBOOST", "AIRPLUS")
LABELS = ("攻", "防", "敏", "知", "体", "気", "性", "油", "撃", "避", "ク", "粘", "邪", "羞", "Ｂ", "Ｃ", "癒", "EX", "空")
CATEGORIES = ("アウター", "カスタマイズパーツ", "インナー", "その他")
RANGES = ((100,300),(600,700),(300,400),(500,600))
COUNTS = (44,1,4,22)


def inventory_items(ctx, category, filters):
    """@LIST_CLOTH_HAVE:616–642、@FILTER_CLOTH_HOSEI:678–759：所有篩選必須同時符合。"""
    result = []
    for cid in range(*RANGES[category]):
        if not ctx.state.item[cid]:
            continue
        accepted = True
        for i, mode in enumerate(MODES):
            if not (filters & (1 << i)):
                continue
            if category in (0,2):
                from .clothing import _hosei
                value = _hosei(ctx,0,cid,mode,1)
                if value == -99999 or (value >= 100 if mode in ("TAIRYOKU","KIRYOKU","SEITAISEI") else value <= 0):
                    accepted = False
                    break
            elif category == 1 and mode not in PARTS.get(cid,{}):
                accepted = False
                break
        if accepted:
            result.append(cid)
    return result


def _marks(ctx, cid, category):
    """@SHOW_CLOTH_LIST:489–556／@SHOW_CLOTH_HOSEI_MARK:786–818。"""
    out, st = ctx.out, ctx.state
    keep = st.target_chara.cflag[1]
    for i, mode in enumerate(MODES):
        if cid <= 499:
            st.target_chara.cflag[1] = 1
            from .clothing import _hosei
            value = _hosei(ctx,st.target,cid,mode)
        elif mode in PARTS.get(cid,{}) and category == 1:
            value = PARTS[cid][mode]
            st.target_chara.cflag[1] = 1
        else:
            out.print("　|")
            continue
        if category in (0,2):
            if i in (0,1,2,3,7):
                threshold = 100
            elif i in (8,9,10,14,15,16,17,18):
                threshold = 0
            elif (category == 0 and i in (4,5)) or (category == 2 and i == 6):
                threshold = -95
            else:
                threshold = -100
        elif category == 1:
            threshold = -100 if i in (4,5,11,12) else 0
        else:
            threshold = 0
        diff = abs(threshold) - value if threshold < 0 else value - threshold
        if diff:
            out.set_color((96,96,255) if diff > 0 else (255,96,96))
            out.print("▲" if diff > 0 else "▼")
            out.reset_color()
        else:
            out.print("　")
        out.print("|")
    st.target_chara.cflag[1] = keep


def inventory_gen(ctx):
    """@SHOW_CLOTH:13–252，限定原入口的 SHOW_TYPE=表示画面，不包含購買。"""
    from .clothing import _name, description

    st, out = ctx.state, ctx.out
    category = page = selected = filters = kind = 0
    catalog = simple = False
    while True:
        items = inventory_items(ctx,category,filters)
        maximum = max(len(items)-1,0)//COUNTS[kind]
        out.drawline()
        out.printl("所持衣装一覧")
        out.drawline()
        if kind == 3:
            out.printl("　|"+"|".join(LABELS)+"|")
        if not items:
            out.printl("未所持")
        for cid in items[page*COUNTS[kind]:(page+1)*COUNTS[kind]]:
            if kind in (0,3):
                out.print(f"[{cid}] {_name(ctx,cid)}")
                if kind == 3:
                    out.print("|")
                    _marks(ctx,cid,category)
                out.printl()
            else:
                out.printl(_name(ctx,cid))
                description(ctx,cid)
                out.drawline()
        if maximum:
            out.printl("[90]前へ　　[91]次へ")
        else:
            out.set_color((128,128,128))
            out.print_plain("[90]前へ　　[91]次へ")
            out.reset_color()
            out.printl()
        if kind in (0,3):
            out.drawline()
            for i,label in enumerate(LABELS):
                if filters & (1 << i):
                    out.set_color((0,255,0))
                out.print(f"[{50+i}]{label}　")
                out.reset_color()
            out.printl()
        out.drawline()
        for i,label in enumerate(CATEGORIES):
            if i == category:
                out.set_color((255,255,0))
            out.print(f"[{i}]{label}　")
            out.reset_color()
        out.printl()
        out.printl("[10]カタログ表示　[11]リスト表示")
        out.printl("[98]フィルタをリセット")
        out.printl("[99]戻る")
        st.result[0] = 1  # @SHOW_CLOTH_FOOTER:395 RETURN 1
        r = yield from input_number(ctx)
        if r == 99:
            if kind in (0,3):
                st.result[0] = 1
                return
            kind, page, selected = (3 if simple else 0), 0, 0
        elif r in (90,91):
            if r == 90:
                page = maximum if page == 0 else page-1
                if kind == 1:
                    selected = selected-1 if selected > 0 else len(items)-1
                elif kind == 2:
                    selected = selected-4 if selected-4 > 0 else len(items)-1
            else:
                page = page+1 if maximum-page > 0 else 0
                if kind == 1:
                    selected = selected+1 if selected < len(items) else 0
                elif kind == 2:
                    selected = selected+4 if selected+4 < len(items) else (0 if selected == len(items)-1 else len(items)-1)
        elif 0 <= r <= 3:
            category, page, selected = r, 0, 0
            kind = 3 if simple else 0
            if not simple:
                catalog = False
        elif r == 10:
            catalog = not catalog
            if catalog:
                simple = False
            kind = 2 if catalog else 0
            page = max(selected,0)//COUNTS[kind] if items else 0
        elif r == 11:
            simple = not simple
            if simple:
                catalog = False
            kind = 3 if simple else 0
            page = max(selected,0)//COUNTS[kind] if items else 0
        elif 50 <= r <= 68 and kind in (0,3):
            filters ^= 1 << (r-50)
            page = selected = 0
        elif 100 <= r <= 1000:
            if r in items:
                selected = items.index(r)
                if kind in (0,3):
                    kind = 2 if catalog else 1
                    simple = False
                    page = selected//COUNTS[kind]
        elif r == 98:
            filters = 0
        else:
            out.printw("想定外の値が入力されました")
