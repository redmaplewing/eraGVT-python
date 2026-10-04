"""衣裝自訂保存運算（原生 Python，並非 ERB 執行器）。

依據 ERB/武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB、
CLOTHDATAアウター_特殊.ERB、CLOTHDATAインナー.ERB 各
@CLOTH_CUSTOMIZE_OPTION_{ID} 的 SAVE 之後運算。
各數值是原作運算值，不採用選單說明中的效果文字。
逐衣裝的精確函式起始行見 clothing_text.MENUS[cid]["source"]；
保存低位共通處理：CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_CUSTOMIZE_OPTION_SAVE:561–572。
"""


def encode_custom(cid: int, custom: list[int]) -> int:
    """保存低位外觀與高位補正；不正規化超過9的補正（原作直接加算）。"""
    c = list(custom) + [0] * (9 - len(custom))

    def v(i, *values):
        return values[c[i]] if 0 <= c[i] < len(values) else 0

    w = down = up = noinner = oil_down = oil_up = 0
    if cid == 101:
        w = v(1, 0, -1, -2) + v(2, 0, 1, 1) + v(3, 0, 2, -2, -1) + (c[4] == 4)
        down, up = v(3, 0, 0, 2, 1), 2 * (c[3] == 1) + (c[4] == 4)
    elif cid == 102:
        w = -2 * (c[0] == 1) + v(2, 0, -1, -1, -2, -5, 1, 2, -1) - (c[3] == 1) + v(4, 0, -1, -2, 2, -4) + (c[5] == 4)
        down, up = v(4, 0, 1, 2, 0, 4), 2 * (c[4] == 3) + (c[5] == 4)
    elif cid == 103:
        w = v(1, 0, -1, -1, -2, 1) + v(3, 0, -1, -4, 1, 2) + (c[4] == 4)
        down, up = 4 * (c[3] == 2), 2 * (c[3] == 4) + (c[4] == 4)
    elif cid == 104:
        w = v(1, 0, -1, -2, -3) + v(2, 0, 1, -1) + v(3, 0, -1, -2) + (c[4] in (4, 5))
        down, up = (c[1] == 3) + v(3, 0, 1, 2), int(c[4] in (4, 5, 6))
    elif cid == 105:
        w = v(1, 0, -1, -1, -2) + v(2, 0, 1, -1) + v(3, 0, 1, -2) + (c[4] in (4, 5))
        down, up = 2 * (c[3] == 2), (c[3] == 1) + int(c[4] in (4, 5, 6))
    elif cid == 106:
        w = v(1, 0, 1, 2, 1) - (c[2] == 1) - (c[3] in (2, 3)) + v(4, 0, -1, -1, -2, 0, -1, -2)
        down, up, noinner = v(4, 0, 0, 1, 0, 1, 2, 3), int(c[1] == 3), int(c[4] == 3)
    elif cid == 107:
        w = (c[1] == 1) + v(2, 0, 2, -1) + v(3, 0, 1, 2) + (c[4] in (4, 5))
        up = v(3, 0, 1, 2) + (c[4] in (4, 5))
    elif cid in (108, 139):
        w = v(1, 0, -1, -2, 1, 2) if cid == 108 else v(1, 0, -1, -2)
        w += v(2, 0, 1, 2) + v(3, 0, -2, -1, 0, -2) + (c[4] == 4)
        down, up = v(3, 0, 2, 1, 0, 2), int(c[4] == 4)
    elif cid in (109, 121, 132):
        w = v(0, 0, -2, -1) if cid == 132 else -2 * (c[0] == 1)
        w += v(1, 0, -1, -1, -2, -5, -2)
        if cid != 121:
            w += v(3, 0, -1, -2) + (c[4] == 4)
            down, up = v(3, 0, 1, 2), int(c[4] == 4)
    elif cid == 110:
        w = (c[0] == 2) + int(c[1] == 1) + v(2, 0, 1, 2) + (c[4] in (3, 4))
        up = (c[1] == 1) + int(c[3] == 1)
    elif cid == 111:
        w = v(1, 0, 0, -1, -3) + (c[2] == 1) + (c[4] in (4, 5))
        up = int(c[4] in (4, 5))
    elif cid == 112:
        w = v(1, 0, -1, -1, -2, -2, -3) + v(3, 0, -1, -2) + (c[4] == 4)
        down, up = v(3, 0, 1, 2), int(c[4] == 4)
    elif cid == 113:
        w = v(1, 0, -1, 1, 2) + v(3, 0, -1, -2) + (c[4] == 4)
        down, up = v(3, 0, 1, 2), int(c[4] == 4)
    elif cid == 114:
        w = v(2, 0, 1, -1, -1, -2, -6) + v(3, 0, -1, -2, -3) - (c[4] in (2, 3)) + v(5, 0, -2, -1, -2, -3, -1, -2, -3, -3) + (c[6] == 4)
        down, up = v(5, 0, 2, 1, 2, 3, 1, 2, 3, 3), (c[2] == 5) + int(c[6] == 4)
    elif cid == 115:
        w = v(1, 0, -1, -2, -3, 0, -1, -1, -2) + v(2, 0, 1, -1) + v(3, 0, -1, -2, -3, -2)
        down, noinner = v(3, 0, 1, 2, 3), int(c[3] == 4)
    elif cid == 116:
        w = (c[0] == 1) - int(c[1] == 1) + v(3, 0, -1, -1, -2, 1) + (c[4] == 4)
        down, up = v(3, 0, 1, 1, 2), (c[0] == 1) + int(c[3] == 4) + (c[4] == 4)
    elif cid == 117:
        w = -(c[1] == 1) + v(2, 0, 1, 0, -1) + v(3, 0, -1, 1, -1)
        down, up, noinner = int(c[3] == 1), 2 * (c[3] == 2), int(c[3] == 3)
    elif cid == 119:
        w = v(2, 0, -1, -1, -2, 1, -1, -2, -2, -3) + (c[3] == 1) + v(4, 0, 2, 2, 0, -1) + (c[5] == 3)
        down, up = int(c[4] == 4), 2 * (c[4] in (1, 2)) + (c[5] == 3)
    elif cid == 120:
        w = v(1, 0, 0, 0, -1, -1, -2) + v(2, 0, 0, 1, -1, -2, -2) + v(3, 0, -1, -1, -2) + v(4, 0, 1, -1) + v(5, 0, 0, 1, -1, -2) + (c[6] in (4, 5))
        down, up = v(5, 0, 0, 0, 1, 2), (c[5] in (1, 2)) + int(c[6] in (4, 5))
    elif cid == 122:
        w = -(c[1] == 1) + v(2, 0, 1, -1) + v(3, 0, 2, 1, -1) + (c[4] in (4, 5))
        down, up = int(c[3] == 3), v(3, 0, 2, 1) + (c[4] in (4, 5))
    elif cid == 123:
        w = v(1, 0, -1, -2) + v(2, 0, 1, -1) + v(3, 0, 1, 0, -1, -2) + (c[4] == 5)
        down, up = v(3, 0, 0, 0, 1, 2), (c[3] == 1) + int(c[4] == 5)
    elif cid == 124:
        w = v(3, 0, -1, -2) + v(4, 0, 1, -1) + v(5, 0, -1, -2) + v(6, 0, -1, 1)
        down, up = v(5, 0, 1, 2) + (c[6] == 1), int(c[6] == 2)
    elif cid == 125:
        w = (c[2] == 1) - 2 * (c[3] == 1) + (c[4] in (4, 5))
        down, up = 2 * (c[3] == 1), int(c[4] in (4, 5, 6))
    elif cid in (130, 143, 144):
        w = v(1, 0, -1, -2) + (c[4] == 4)
        if cid != 144:
            w -= c[3] == 1
        up = int(c[4] == 4)
    elif cid == 131:
        w = -2 * (c[3] == 1) + (c[4] == 4)
        down, up = 2 * (c[3] == 1), int(c[4] == 4)
    elif cid == 137:
        w = v(1, 0, 1, -2, -3) + v(2, 0, 1, 2) + v(3, 0, -2, -1, -2, -3) + (c[4] == 4)
        down, up = v(3, 0, 2, 1, 2, 3), int(c[4] == 4)
    elif cid == 138:
        w = v(1, 0, -2, -4) + (c[2] == 1) + v(3, 0, -2, -3)
        down = v(3, 0, 2, 3)
    elif cid == 140:
        w = v(1, 0, -1, -2) + v(3, 0, 1, -1, -2) + (c[4] == 5)
        down, up = v(3, 0, 0, 1, 2), (c[3] == 1) + int(c[4] == 5)
    elif cid == 141:
        w = v(1, 0, -1, -2, -4) + v(2, 0, 1, 2) + v(3, 0, -2, -1, -4) + (c[4] == 4)
        down, up = v(3, 0, 2, 1, 3), int(c[4] == 4)
    elif cid == 142:
        w = v(1, 0, -1, -2) + v(2, 0, 1, 2) + v(3, 0, -1, -2) + (c[4] == 4)
        down, up = v(3, 0, 1, 2), int(c[4] == 4)
    elif cid == 145:
        w = (c[2] == 1) + v(3, 0, -1, -2)
        down = v(3, 0, 1, 2)
    elif cid == 146:
        w = v(2, 0, 1, 2, -1) + v(3, 0, -1, -2, -3) + v(4, 0, -1, -2) + v(5, 0, 1, -1) + v(6, 0, 1, -1, -2, -3) + (c[7] in (4, 5))
        down, up = v(6, 0, 0, 1, 2, 3), (c[6] == 1) + int(c[7] in (4, 5, 6))
    elif cid == 147:
        w = v(0, 0, 1, 0, -1) + (c[1] in (2, 3)) + v(2, 0, -1, -2, -3) + v(3, 0, 1, -1) + v(4, 0, -1, -2) + v(5, 0, 1, -1, -2) + (c[6] in (5, 6))
        down, up = v(5, 0, 0, 1, 2), (c[5] == 1) + int(c[6] in (5, 6))
    elif cid == 148:
        w = v(1, 0, -1, -1, -2) + v(2, 0, -1, -2) + v(3, 0, 1, -1, 0, -1, -2) + (c[4] in (4, 5))
        down, up = int(c[3] == 3), v(3, 0, 2, 1) + (c[4] in (4, 5))
    elif cid == 149:
        w = v(1, 0, -1, -2, 1) + v(2, 0, 1, 2) + v(3, 0, 1, -1, -2)
        down, up = v(3, 0, 0, 1, 2), int(c[3] == 1)
    elif cid == 150:
        w = v(1, 0, -1, -2, -3) + v(2, 0, 1, -1) + v(3, 0, 1, -1, -2) + (c[4] in (4, 5))
        down, up = v(3, 0, 0, 1, 2), (c[3] == 1) + int(c[4] in (4, 5))
    elif cid == 151:
        w = v(1, 0, -1, 1, 1) + v(2, 0, 0, 1, 2, -1) + v(3, 0, -1, -1, -2, -3, 1, 2)
        down, up = v(3, 0, 1, 2, 3, 4, 0, 0, 1), v(3, 0, 0, 0, 0, 0, 1, 2)
    elif cid in (152, 196):
        w = int(c[2] in (1, 2, 3, 4)) + int(c[3] in ((1, 2, 3) if cid == 196 else (1, 2)))
        w += (-1 if cid == 196 else 1) * (c[4] == 4)
        up = int(c[4] == 4)
    elif cid == 153:
        # :8723 的 CUSTOM:1 <= 3 && >= 7 永不成立，照原作保留。
        w = (c[1] == 2) + v(2, 0, -1, -1, -3) + v(3, 0, -1, -2) + v(4, 0, -1, -2, -2, -1, -1, -3)
        down, up = v(4, 0, 2, 3, 0, 1, 0, 4), int(c[5] in (5, 6))
        noinner = int(c[2] == 3 or c[4] in (3, 5))
    elif cid in (301, 302, 303, 304, 310):
        w = v(3, 0, 0, 0, -1, -1, 1, -2, -1)
        down, up = v(3, 0, 0, 0, 1, 2, 0, 3, 4), 2 * (c[3] == 5)
        oil_down = 2 * (c[3] == 5)
        if cid != 303:
            oil_up = v(1, 0, 2, 2, 2, 2, 2, 2 if cid in (302, 310) else 1, 1, 1, 1)
        oil_up += int(c[2] in ((1, 2) if cid == 304 else (1,))) + (c[4] == 1)
        oil_up += v(3, 0, 0, 0, 1, 2, 0, 2, 1) if cid == 304 else v(3, 0, 0, 0, 1, 2, 0, 3, 4)
    elif cid == 305:
        # インナー:1058–1061，同一條件 CUSTOM:2==1 連續加1及2。
        w = 3 * (c[2] == 1) + v(4, 0, 0, 0, -1, 1, -1, -1, -3, -4, -1) + (c[6] == 1)
        down, up = v(4, 0, 0, 0, 1, 0, 2, 2, 3, 4, 4), 2 * (c[4] == 4) + (c[6] == 1)
        oil_down = 2 * (c[4] == 4)
        oil_up = int(1 <= c[1] <= 7) + (c[3] == 1) + v(4, 0, 0, 0, 1, 0, 3, 3, 3, 5, 4) + (c[5] in (1, 2))
    elif cid == 312:
        w = -3 * (c[3] == 6) + v(4, 0, 0, 1, -1, -2, 1, 1, 1)
        down, up = v(4, 0, 0, 0, 1, 2), v(4, 0, 0, 1, 0, 0, 2, 1, 1)
        oil_down = 2 * (c[3] == 6) + 2 * (c[4] == 5)
        oil_up = v(1, 0, 1, 1, 1, 2, 2, 1, 1, 1, 1) + (c[2] == 1) + (c[3] in (3, 4, 5)) + v(4, 0, 0, 0, 1, 2) + (c[5] == 1)
    elif cid == 313:
        w = v(3, 0, 0, -1, 1, 1)
        down, up = int(c[3] == 2), 2 * (c[3] in (3, 4))
        oil_down = 2 * (c[2] == 1) + 2 * (c[3] in (3, 4))
        oil_up = v(1, 0, 0, 2, 1, 1, 1, 1) + (c[3] == 2)
    elif cid not in (199, 306, 309, 314):
        raise ValueError(f"不存在自訂保存函式：{cid}")
    return (sum(x * 10**i for i, x in enumerate(custom))
            + max(-w, 0) * 10**9 + max(w, 0) * 10**10
            + down * 10**11 + up * 10**12 + (noinner + oil_down) * 10**13 + oil_up * 10**14)


def category_blocked(cid, field, custom, research):
    """各 @CLOTH_CUSTOMIZE_OPTION_* 的 COMMON 引數與分岐限制。"""
    c = custom + [0] * (9 - len(custom))
    if cid == 199:
        return research == 0
    if cid == 102:
        return (field in (0, 3) and c[2] == 4) or (field in (1, 3) and c[2] == 7)
    if cid == 104:
        return field == 2 and c[1] in (2, 3)
    if cid == 106:
        return field == 2 and c[1] == 2
    if cid in (109, 121, 132):
        return (field == 0 and c[1] == 4) or (field == 2 and ((cid == 121 and c[1] == 5) or (cid == 132 and c[1] in (4, 5))))
    if cid == 111:
        return field == 2 and c[1] >= 3
    if cid == 114:
        return field in (3, 4, 5, 6) and c[2] == 5
    if cid == 119:
        return field == 3 and c[2] in (5, 6, 7, 8)
    if cid == 120:
        return (field == 3 and c[2] == 4) or (field == 4 and c[2] in (3, 4, 5))
    if cid == 123:
        return (field == 2 and c[1] == 2) or (field == 4 and c[3] == 1)
    if cid in (130, 143, 144):
        return field == 2 and c[1] == 0
    if cid == 140:
        return field == 4 and c[3] == 1
    if cid == 149:
        return field == 2 and c[1] == 2
    if cid == 153:
        return field == 3 and c[2] == 3
    return False


def choice_blocked(cid, field, value, custom, inner, research):
    """各自訂子選單 OPTION_PRINT 之 !! 條件。"""
    c = custom + [0] * (9 - len(custom))
    if cid == 102:
        return field == 2 and value == 4 and c[0] == 1
    if cid in (109, 121, 132):
        return field == 1 and value == 4 and c[0] == 1
    if cid == 103:
        return field == 3 and value == 2 and inner != 308
    if cid == 104:
        return field == 3 and value == 0 and c[1] in (2, 3)
    if cid == 115:
        return field == 3 and value == 4 and c[1] not in (0, 1)
    if cid == 117:
        return field == 2 and value == 2 and c[1] != 0
    if cid == 120:
        return field == 4 and value == 2 and c[2] in (3, 4, 5)
    if cid == 153:
        return field == 4 and value in (3, 5) and c[2] == 3
    if cid == 199:
        if field == 1:
            return research < value
        if field == 2:
            return value > 0 and research < 3
        if field == 3:
            return research < (0, 2, 4, 3, 5)[value]
    return False


def change_custom(cid, field, value, custom):
    """原作每次選取後的相依欄位修正；僅在該選項確定時執行。"""
    c = custom
    c[field] = value
    if cid == 102:
        if field == 0 and value == 1 and c[2] == 4:
            c[2] = 0
        if field == 2 and value == 7:
            c[1] = c[3] = 0
    elif cid == 104 and field == 1:
        if value == 2:
            c[2] = 0
        elif value == 3:
            c[2] = 2
            if c[3] == 0:
                c[3] = 1
    elif cid == 106 and field == 1 and value == 2:
        c[2] = 0
    elif cid == 111 and field == 1 and value == 3:
        c[2] = 1
    elif cid == 114 and field == 2 and value == 5:
        c[3:7] = [0] * 4
    elif cid == 115 and field == 1 and value in (2, 3) and c[3] == 4:
        c[3] = 0
    elif cid == 117 and field == 1 and value == 1 and c[2] == 2:
        c[2] = 0
    elif cid == 119 and field == 2 and value in (5, 6, 7, 8):
        c[3] = 0
    elif cid == 120 and field == 2:
        if value == 4:
            c[3] = 0
        if value in (3, 4) and c[4] == 2:
            c[4] = 0
        if value == 5:
            c[4] = 0
    elif cid == 121 and field == 1 and value == 5:
        c[2] = 0
    elif cid in (123, 140):
        if field == 1 and value == 2:
            c[2] = 2
        if field == 3 and value == 1:
            c[4] = 0
    elif cid == 130 and field == 1 and value == 0:
        c[2] = 0
    elif cid == 132 and field == 0 and value == 1 and c[1] == 4:
        c[1] = 0
    elif cid == 149 and field == 1 and value == 2:
        c[2] = 0
    elif cid == 153 and field == 2 and value == 3:
        c[3] = 2
        if c[4] == 3:
            c[4] = 0
        if c[4] == 5:
            c[4] = 4
