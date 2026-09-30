"""キャラの相関関係：`SYSTEM/キャラメイキング関連/CHARA_RELATION.ERB` の `@GET_RELATION`:5–181、
`@CHECK_ALL_RELATION`:562–984、`@TOSHIUE_F`:986–995。路徑相對 `source/earGVP/ERB/`。

RELATION:A:B は A の RELATION 配列の要素 B（B は登録 index）。ビット番号は `DIM.ERH`:219–242 の定数。
SETBIT／CLEARBIT／GETBIT は Int64 のビット操作（reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs
の SETBIT／CLEARBIT、GameData/Function/Creator.Method.cs の GETBIT）。
"""

from __future__ import annotations

from ..state import GameState
from .action import Ctx
from .chara_common import is_female, is_male, talent

# DIM.ERH:219–242
IKIWAKARE, SHITASHII, SOEN, AISURU, ZOUO, GIRI = 1, 2, 3, 4, 5, 6
OYAKO, KYOUDAI, SOFUBO, OJIOBA, OIMEI, ITOKO = 20, 21, 22, 23, 24, 25
YUUJIN, KATAOMOI, KOIBITO, KONYAKU, HAIGUUSHA = 30, 31, 32, 33, 34
SHUJIN, JUUSHA, DOREI = 40, 41, 42


def _gb(st: GameState, a: int, b: int, bit: int) -> bool:
    return (st.charas[a].relation[b] >> bit) & 1 == 1


def _sb(st: GameState, a: int, b: int, bit: int) -> None:
    st.charas[a].relation[b] = st.charas[a].relation[b] | (1 << bit)


def _cb(st: GameState, a: int, b: int, bit: int) -> None:
    st.charas[a].relation[b] = st.charas[a].relation[b] & ~(1 << bit)


def toshiue(st: GameState, a: int, b: int) -> int:
    """`@TOSHIUE_F(ARG:0, ARG:1)`：実年齢（BASE:40）が上、同じなら固有番号（CFLAG:240）が小さい方が年上。"""
    ca, cb = st.charas[a], st.charas[b]
    if ca.base[40] > cb.base[40]:
        return 1
    if ca.base[40] == cb.base[40] and ca.cflag[240] < cb.cflag[240]:
        return 1
    return 0


def get_relation(ctx: Ctx, a: int, b: int) -> str:
    """`@GET_RELATION, ARG:0, ARG:1`:5–181（RESULTS に入る文字列）。"""
    st, data = ctx.state, ctx.data
    g = lambda bit: _gb(st, a, b, bit)  # noqa: E731
    male = is_male(data, st.charas[b])
    s = ""
    if st.charas[a].relation[b] < 2**20:  # :10–23 印象系のみ
        if g(SOEN) and g(SHITASHII):
            s += "微妙な距離感の知人"
        elif g(SHITASHII):
            s += "親しい間柄"
        elif g(SOEN):
            s += "顔見知り"
        elif g(AISURU) and g(ZOUO):
            s += "複雑な関係"
        elif g(AISURU):
            s += "大事な人"
        elif g(ZOUO):
            s += "仇敵"
    else:  # :24–43
        if g(IKIWAKARE):
            s += "生き別れの"
        if g(SOEN) and g(SHITASHII):
            s += "微妙な距離感の"
        elif g(SHITASHII) and not g(YUUJIN):
            s += "親しい"
        elif g(SOEN):
            s += "疎遠な"
        if g(AISURU) and g(ZOUO):
            s += "愛憎渦巻く"
        elif g(AISURU):
            s += "愛する"
        elif g(ZOUO):
            s += "憎悪する"
        if g(GIRI):
            s += "義理の"
    local = 0  # :47–178
    if g(OYAKO):
        if toshiue(st, a, b) > 0:
            s += "息子" if male else "娘"
        else:
            s += "父親" if male else "母親"
        local += 1
        if g(KYOUDAI) or g(SOFUBO) or g(OJIOBA) or g(OIMEI) or g(ITOKO):
            s += "/"
    if g(KYOUDAI):
        if toshiue(st, a, b):
            s += "弟" if male else "妹"
        else:
            s += "兄" if male else "姉"
        local += 1
        if g(SOFUBO) or g(OJIOBA) or g(OIMEI) or g(ITOKO):
            s += "/"
    if g(SOFUBO):
        if toshiue(st, a, b):
            s += "孫"
        else:
            s += "祖父" if male else "祖母"
        local += 1
        if g(OJIOBA) or g(OIMEI) or g(ITOKO):
            s += "/"
    if g(OJIOBA):
        s += "おじ" if male else "おば"
        local += 1
        if g(ITOKO):
            s += "/"
    if g(OIMEI):
        s += "甥" if male else "姪"
        local += 1
        if g(ITOKO):
            s += "/"
    if g(ITOKO):
        s += "いとこ"
        local += 1
    if local and (g(YUUJIN) or g(KATAOMOI) or g(KOIBITO) or g(KONYAKU) or g(HAIGUUSHA)):
        s += "かつ"
    lovers = lambda: g(KATAOMOI) or g(KOIBITO) or g(KONYAKU) or g(HAIGUUSHA)  # noqa: E731
    if g(SHITASHII) and not g(SOEN) and g(YUUJIN):
        s += "親友"
        local += 1
        if local and lovers():
            s += "で"
    elif g(YUUJIN):
        s += "友人"
        local += 1
        if local and lovers():
            s += "で"
    if g(KATAOMOI):
        s += "片思いの相手"
        local += 1
    if g(KOIBITO):
        s += "恋人"
        local += 1
    if g(KONYAKU):
        s += "婚約者"
        local += 1
    if g(HAIGUUSHA):
        s += "夫" if male else "妻"
        local += 1
    if local and (g(SHUJIN) or g(JUUSHA) or g(DOREI)):
        s += "かつ"
    if g(SHUJIN):
        s += "主人"
    if g(JUUSHA):
        s += "従者"
    if g(DOREI):
        s += "奴隷"
    return s


def check_all_relation(ctx: Ctx) -> None:
    """`@CHECK_ALL_RELATION`:562–984：親子関係から兄弟・祖父母・おじおば・いとこを推移的に設定し、双方向化・表示、
    子や孫を持つキャラの処女消去、両親 ID（CFLAG:7 母／CFLAG:9 父）の設定。

    FOR の終端は開始時の CHARANUM（Instraction.Child.cs:1731–1743）。:593 の PRINTL（空行）は「親が居る」組ごとに出る（原作どおり）。
    """
    st, data, out = ctx.state, ctx.data, ctx.out
    if st.charanum < 3:  # :568–569
        return
    n = st.charanum
    M = GameState.MASTER
    cf = lambda i, k: st.charas[i].cflag[k]  # noqa: E731
    ts = lambda a, b: toshiue(st, a, b)  # noqa: E731
    gb = lambda a, b, bit: _gb(st, a, b, bit)  # noqa: E731
    for ch in range(n):  # :571
        if ch == M:
            continue
        if cf(ch, 9) <= -100 or cf(ch, 7) > 0:  # :576–588 両親が仲間に居る
            for se in range(n):
                if se == M or se == ch:
                    continue
                if (cf(ch, 9) <= -100 and cf(se, 240) == cf(ch, 9) * -1 - 100) or (cf(ch, 7) > 0 and cf(se, 240) == cf(ch, 7)):
                    _sb(st, ch, se, OYAKO)
                    _sb(st, se, ch, OYAKO)
        for se in range(n):  # :591
            if se == M or se == ch:
                continue
            w = [0, 0]

            def both(bit_cs: int, bit_sc: int, giri_from: int | None = None) -> None:
                """「SIF GETBIT(ch,se) == 0 → W0++ / SETBIT ch,se / SIF GETBIT(se,ch) == 0 → W1++ / SETBIT se,ch」＋義理の。"""
                if not gb(ch, se, bit_cs):
                    w[0] += 1
                _sb(st, ch, se, bit_cs)
                if not gb(se, ch, bit_sc):
                    w[1] += 1
                _sb(st, se, ch, bit_sc)
                if giri_from is not None and gb(ch, giri_from, GIRI):
                    _sb(st, ch, se, GIRI)
                    _sb(st, se, ch, GIRI)

            for re in range(n):  # :603–669 自分に親か子が居る
                if re == M or re == ch:
                    continue
                if gb(ch, re, OYAKO) and ts(re, ch) > 0:  # 親が居る
                    out.printl()
                    if gb(se, re, OYAKO) and ts(re, se) > 0:
                        both(KYOUDAI, KYOUDAI, re)
                    if gb(re, se, OYAKO) and ts(se, re) > 0:
                        if ts(se, ch) > 0:
                            both(SOFUBO, SOFUBO, re)
                    if gb(re, se, KYOUDAI):
                        both(OJIOBA, OIMEI, re)
                if gb(ch, re, OYAKO) and ts(ch, re) > 0:  # 子が居る
                    if gb(re, se, OYAKO) and ts(re, se) > 0:
                        if ts(ch, se) > 0:
                            both(SOFUBO, SOFUBO, re)
                    if gb(re, se, SOFUBO) and ts(se, re) > 0:
                        if ts(se, ch) > 0:
                            both(OYAKO, OYAKO, re)
            for re in range(n):  # :681–735 兄弟姉妹
                if re == M or re == ch:
                    continue
                if gb(ch, re, KYOUDAI):
                    if gb(re, se, KYOUDAI):
                        both(KYOUDAI, KYOUDAI)
                    if gb(re, se, OYAKO) and ts(se, re) > 0:
                        if ts(se, ch) > 0:
                            both(OYAKO, OYAKO)
                    if gb(re, se, SOFUBO) and ts(se, re) > 0:
                        if ts(se, ch) > 0:
                            both(SOFUBO, SOFUBO)
                    if gb(re, se, OYAKO) and ts(re, se) > 0:
                        both(OIMEI, OJIOBA)
            for re in range(n):  # :737–777 祖父母・孫
                if re == M or re == ch:
                    continue
                if gb(ch, re, SOFUBO) and ts(re, ch) > 0:
                    if gb(re, se, OYAKO) and ts(re, se) > 0 and not gb(ch, se, OYAKO):
                        both(OJIOBA, OIMEI, re)
                if gb(ch, re, SOFUBO) and ts(ch, re) > 0:
                    if gb(re, se, OYAKO) and ts(se, re) > 0:
                        if ts(ch, se) > 0:
                            both(OYAKO, OYAKO)
            for re in range(n):  # :779–798 おじおば
                if re == M or re == ch:
                    continue
                if gb(ch, re, OJIOBA):
                    if gb(re, se, OYAKO) and ts(re, se) > 0:
                        both(ITOKO, ITOKO, re)
            for re in range(n):  # :800–820 いとこ
                if re == M or re == ch:
                    continue
                if gb(ch, re, ITOKO):
                    if gb(re, se, OYAKO) and ts(se, re) > 0:
                        both(OJIOBA, OIMEI, re)
            # :822–934 関係の双方向化（se→ch 側を ch→se に合わせる）
            for bit_cs, bit_sc in (
                (IKIWAKARE, IKIWAKARE), (GIRI, GIRI), (OYAKO, OYAKO), (KYOUDAI, KYOUDAI), (SOFUBO, SOFUBO),
                (OJIOBA, OIMEI), (OIMEI, OJIOBA), (ITOKO, ITOKO), (KOIBITO, KOIBITO), (KONYAKU, KONYAKU),
                (HAIGUUSHA, HAIGUUSHA),
            ):
                if gb(ch, se, bit_cs):
                    if not gb(se, ch, bit_sc):
                        w[1] += 1
                    _sb(st, se, ch, bit_sc)
                else:
                    if gb(se, ch, bit_sc):
                        w[1] += 1
                    _cb(st, se, ch, bit_sc)
            if not any(gb(ch, se, b) for b in (OYAKO, KYOUDAI, SOFUBO, OJIOBA, OIMEI)):  # :928–933
                if gb(se, ch, IKIWAKARE) or gb(se, ch, GIRI):
                    w[1] += 1
                _cb(st, se, ch, IKIWAKARE)
                _cb(st, se, ch, GIRI)
            cn = lambda i: st.charas[i].callname  # noqa: E731
            if st.charas[ch].relation[se] > 0 and w[0] > 0:  # :935–946
                out.printl(f"『{cn(ch)}』にとって『{cn(se)}』は【{get_relation(ctx, ch, se)}】になりました。")
            elif w[0] > 0:
                out.printl(f"『{cn(ch)}』と『{cn(se)}』の相関関係は無くなりました。")
            if st.charas[se].relation[ch] > 0 and w[1] > 0:
                out.printl(f"『{cn(se)}』にとって『{cn(ch)}』は【{get_relation(ctx, se, ch)}】になりました。")
            elif w[1] > 0:
                out.printl(f"『{cn(se)}』と『{cn(ch)}』の相関関係は無くなりました。")
            if w[0] or w[1]:
                out.printl()
            # :950–958 子供か孫を持つキャラは処女を失う
            if not gb(ch, se, GIRI) and (gb(ch, se, OYAKO) or gb(ch, se, SOFUBO)):
                if ts(ch, se) > 0:
                    c = st.charas[ch]
                    if talent(data, c, "処女") > 0:
                        c.talent[data.index_of("TALENT", "処女")] = 0
                        out.printl(f"　　関係の変化により『{cn(ch)}』の処女を消去しました")
                        out.printl()
    # :961–982 両親 ID
    for ch in range(n):
        if ch == M:
            continue
        for se in range(n):
            if se == M or se == ch:
                continue
            s = st.charas[se]
            if (
                gb(ch, se, OYAKO) and not gb(ch, se, GIRI) and ts(se, ch) > 0
                and (is_male(data, s) or talent(data, s, "ふたなり") > 0)
                and cf(ch, 7) != cf(se, 240) and cf(ch, 9) == 0
            ):
                st.charas[ch].cflag[9] = cf(se, 240) * -1 - 100
        for se in range(n):
            if se == M or se == ch:
                continue
            s = st.charas[se]
            if (
                gb(ch, se, OYAKO) and not gb(ch, se, GIRI) and ts(se, ch) > 0 and is_female(data, s)
                and cf(ch, 9) * -1 - 100 != cf(se, 240) and cf(ch, 7) == 0
            ):
                st.charas[ch].cflag[7] = cf(se, 240)
