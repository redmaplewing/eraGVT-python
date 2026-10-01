"""ヒロインの戦闘コマンド：`ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/`（COMABLE.ERB、COMF*.ERB、
COM_ATTACK_COMMON.ERB、MOVESELECT.ERB、PRINT_COMNAME.ERB）。

路徑相對 `source/earGVP/ERB/`。S05 で実行できるのは 変身（0、201–203）・近／中／遠距離攻撃（1–3）・防御（4）・
距離をとる（5）・ギブアップ（99）。他のコマンドは表示のみで、選ぶと停止する。
COMn はジェネレータ（INPUT を含むのは COM0 の変身方法選択のみ）で、戻り値は RESULT。
"""

from __future__ import annotations

from collections.abc import Generator

from ..action import Ctx, config_check_other, kojo_root, print_transcallname, sengiup
from ..chara_common import charatalent
from ..era import div, format_percent, isqrt, limit, times
from ..shop import check_pregnant
from ..tentacle import enemy_type_check
from .cheers import perform_cheers_hate
from .cloth import cloth_battle_hosei
from .core import (
    BETOBETO,
    KIZETU,
    KOSHIKUDAKE,
    KOUKOTSU,
    P_GUARD,
    P_HANGEKI_OK,
    P_NOTHING,
    add_battle_situation,
    fstyle_name,
    get_battle_situation,
    percent_cal,
    print_distance,
    run_chinobun,
    shinkyou_change,
    shinkyou_check,
    t,
    tc,
    tentacle_access,
    unlock_achievement,
)
from .func import (
    act_limit,
    attack_air_flag,
    get_air_strike,
    get_brave_hit,
    get_chain_hit,
    get_counter_attack,
    get_evader_atk,
    get_evader_crt,
    transform,
)
from .hantei import act_hantei_chara_to_tentacle, act_hantei_chara_to_tentacle_guard, damage

ComGen = Generator[None, int, int]

# 拘束中専用のコマンド（非拘束時は COM_ABLE が必ず 0 を返す：COMABLE.ERB の各関数冒頭の条件）
_RESTRAINT_ONLY = (8, 9, 10, 12, 13, 14, 15, 40, 44, 45, 46, 100, 101, 102, 103, 104)


def _no_attack(ctx: Ctx) -> bool:
    """`GETBATTLESITUATION("攻撃不可")==1 || (GETBATTLESITUATION("身バレ不可") && FLAG:70+FLAG:71 > 0)`。"""
    st = ctx.state
    return get_battle_situation(st, "攻撃不可") == 1 or (
        get_battle_situation(st, "身バレ不可") == 1 and st.flag[70] + st.flag[71] > 0
    )


def com_able(ctx: Ctx, n: int) -> tuple[int, tuple[int, int, int] | None]:
    """`COMABLE.ERB@COM_ABLE{n}`：(RESULT, SETCOLOR で指定された色)。

    `TCVARn:8 < 10` の判定は呼び出し側（SHOW_USERCOM／USERCOM）で +10 している前提で行う。
    """
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    guard = v[8] >= 10
    tt = lambda name: t(ctx, c, name)  # noqa: E731
    color: tuple[int, int, int] | None = None
    if n == 0:  # :3–32
        if v[0] == 0 or tt("変身能力") != 1 or c.cflag[1] != 0:
            return 0, None
        if (
            charatalent(ctx.data, c, 0, "オトコ") == 0
            and charatalent(ctx.data, c, 1, "オトコ") > 0
            and check_pregnant(ctx.data, st, st.target)
        ):
            return 0, None
        if div(c.base[1] * 100, c.maxbase[1]) < 10:
            return 0, None
        if v[12] & KIZETU:
            return 0, None
        if get_battle_situation(st, "変身不可") == 1 or _no_attack(ctx):
            return 0, None
        return (1 if guard else 0), None
    if n in (1, 2, 3):  # :38–100
        if v[0] == 0 or (v[12] & KIZETU):
            return 0, None
        if (v[12] & KOSHIKUDAKE) and v[0] != n:
            return 0, None
        if _no_attack(ctx):
            return 0, None
        if n == 3 and get_battle_situation(st, "遠距離不可") == 1:
            return 0, None
        return (1 if guard else 0), None
    if n == 4:  # :104–114
        if v[0] == 0 or (v[12] & KIZETU):
            return 0, None
        return (1 if guard else 0), None
    if n in (5, 6, 7):  # :118–186
        if st.temp.prevcom == n or v[0] == 0 or c.cflag[99] >= 50 or (v[12] & KIZETU) or (v[12] & KOSHIKUDAKE):
            return 0, None
        if n == 5 and get_battle_situation(st, "遠距離不可") == 1:
            return 0, None
        return (1 if guard else 0), None
    if n in _RESTRAINT_ONLY or n in (11, 47, 70):  # 拘束中専用（COM11／70 は気絶・非拘束時の分岐も含む）
        from .restraint import com_able_restraint

        return com_able_restraint(ctx, n)
    if n == 16:  # :390–419
        if v.get_bit(216, 0):
            color = (255, 255, 0)
        if v[0] == 0 or c.base[22] == 0 or (tt("変身能力") and c.cflag[1] == 0) or c.cflag[99] >= 50:
            return 0, color
        if (v[12] & KIZETU) or (v[12] & KOUKOTSU) or _no_attack(ctx):
            return 0, color
        if get_battle_situation(st, "空中不可") == 1:
            return 0, color
        return (1 if guard else 0), color
    if n == 17:  # :423–453
        if v.get_bit(217, 0):
            color = (255, 255, 0)
        if v[0] == 0:
            return 0, color
        if v[4] < 200 and c.cflag[1] < 2 and tt("ホットスタート") == 0:
            return 0, color
        if (tt("変身能力") and c.cflag[1] == 0) or c.cflag[99] >= 50:
            return 0, color
        if (v[12] & KIZETU) or (v[12] & KOUKOTSU) or _no_attack(ctx):
            return 0, color
        return (1 if guard else 0), color
    if n == 69:  # :742–760
        if v[0] == 0 or not guard:
            return 0, None
        if v[12] & KIZETU:
            r, _ = com_able(ctx, 11)
            if r == 1:
                return 0, None
        return 1, None
    if n in (71, 72):  # :802–871
        bit = 0 if n == 71 else 1
        if not v.get_bit(3, bit):
            if v[4] + v[6] < 100 and c.cflag[1] < 2:
                return 0, None
            if tt("変身能力") and c.cflag[1] == 0:
                return 0, None
        else:
            color = (255, 255, 0)
        if (v[12] & KIZETU) or (v[12] & KOUKOTSU) or _no_attack(ctx):
            return 0, color
        if get_battle_situation(st, "EX不可") == 1:
            return 0, color
        return (1 if guard else 0), color
    if n == 73:  # :875–921
        if v[0] == 0 or v[4] + v[6] < 200 or tt("変身能力") < 1:
            return 0, None
        if (tt("変身能力") > 0 and c.cflag[1] == 0) or c.cflag[1] == 2:
            return 0, None
        if (v[12] & KIZETU) or (v[12] & KOUKOTSU):
            return 0, None
        if get_battle_situation(st, "変身不可") == 1 or _no_attack(ctx) or get_battle_situation(st, "EX不可") == 1:
            return 0, None
        return (1 if guard else 0), None
    if n == 74:  # :925–963
        if v[0] == 0:
            return 0, None
        if tt("変身能力") == 0 and v[4] < 500:
            return 0, None
        if tt("変身能力") and c.cflag[1] < 2:
            return 0, None
        if (v[12] & KIZETU) or (v[12] & KOUKOTSU) or _no_attack(ctx):
            return 0, None
        if get_battle_situation(st, "EX不可") == 1:
            return 0, None
        return (1 if guard else 0), None
    if n == 99:  # :967–975
        if st.flag[999] < 1 and config_check_other(st, 1) == 0:
            return 0, None
        return (1 if guard else 0), None
    if n in (201, 202, 203):  # :1123–1200
        if v[0] < 1 or v.get_bit(216, 1):
            return 0, None
        v[8] += 10
        local = sum(com_able(ctx, k)[0] for k in (5, 6, 7))
        v[8] -= 10
        if local < 3:
            return 0, None
        return com_able(ctx, 0)
    return 0, None


def print_comname(ctx: Ctx, n: int) -> None:
    """`PRINT_COMNAME.ERB@PRINT_COMNAME(ARG)`:2–36（-1 は空欄）。"""
    out = ctx.out
    if n < 0:
        label = ""
        r = 0
    else:
        r, color = com_able(ctx, n)
        if color is not None:
            out.set_color(color)
        label = ""
        if r:
            name = ctx.data.names["TRAIN"].get(n, "")
            if name == "振り解く":  # :6–13
                from .restraint import label_hurihodoku

                label = f"{name}({label_hurihodoku(ctx)}%)[{n:3d}]"
            elif name == "引き剥がす":  # :14–24
                from .restraint import label_hikihagasu

                label = f"{name}({label_hikihagasu(ctx)}%)[{n:3d}]"
            elif n == 69 and (tc(ctx).tcvarn[12] & KIZETU):
                label = f"なすがまま[{n:3d}]"
            else:
                label = f"{name}[{n:3d}]"
    out.print(format_percent(label, 22, left=False))
    out.reset_color()


# --- 地の文（地の文/MESSAGE_BATTLE.ERB）---------------------------------------------


def _msg_transformcall(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_CHARA_TRANSFORMCALL`:145–187。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    name = print_transcallname(st, st.target)
    sel = st.temp.selectcom
    head = {201: "大きく踏み込んだ", 202: "身構える", 203: "距離を取って身構えた"}.get(sel, "身構えた")
    out.printl(f"{head}{name}の周囲を")
    if t(ctx, c, "完堕ち"):
        out.printl("妖しげな紫色の霧が包み込む…")
    elif t(ctx, c, "触手の虜"):
        out.printl("蠱惑的なピンク色の光が包み込む…")
    else:
        out.printl("眩い光が包み込む！")
    if kojo_root(ctx, "BATTLE_CHARA_TRANSFORMCALL") == -1:
        # DEVIATION: 口上色（KOJO_{n}_COLOR*）は口上側の関数なので未移植（deviations「口上」）
        out.printl()
        if c.cflag[4] == 1:
            s = c.cstr[2]
            if t(ctx, c, "完堕ち"):
                s = s.replace("！", "❤")
            elif t(ctx, c, "触手の虜"):
                s = s.replace("！", "…❤")
            out.printl(f"「{s}」")
        out.reset_color()


def _msg_nanori(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_CHARA_NANORI`:190–213。"""
    c = tc(ctx)
    out = ctx.out
    if kojo_root(ctx, "BATTLE_CHARA_NANORI") == -1:
        out.printl()
        if c.cflag[5] == 1:
            s = c.cstr[3]
            if t(ctx, c, "完堕ち"):
                s = s.replace("！", "❤❤❤")
            elif t(ctx, c, "触手の虜"):
                s = s.replace("！", "…❤")
            out.printl(f"「{s}」")
        out.reset_color()


def _msg_nanori_byousha(ctx: Ctx) -> None:
    """`@MESSAGE_BATTLE_CHARA_NANORI_BYOUSHA`:216–342（カスタムパーツ EQUIP:600–693 は未移植）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if any(c.equip[i] for i in (600, 601, 602, 603, 660, 661, 664, 672, 673, 680, 681, 690, 691, 693)):
        raise NotImplementedError("カスタムパーツを付けた変身描写は未移植")
    suits = {200: "オリジナルスーツ", 201: "可愛らしいフリルスカート", 202: "動きやすいレオタード",
             299: "薄いゴム状隠密スーツ", 401: "瘴気を帯びた禍々しいスーツ", 199: "触手細胞を利用した生体鎧"}
    cid = c.cflag[41]
    if cid in suits:
        out.print(suits[cid])
        out.printl("を纏い、")
    elif cid == 0 and c.cflag[42] == 0:
        from .core import abl

        if (t(ctx, c, "淫乱") or abl(ctx, c, "露出癖") >= 3) and t(ctx, c, "初心") < 1:
            out.printl("裸身を晒す快感に震え、")
        else:
            out.printl("裸身を晒し、")
    else:
        item = ctx.data.items.get(cid)
        out.printl(f"{item.name if item else ''}を纏い、")
    # CUSTOMIZABLE（#DIM、0）なので「光の中から」は出ない
    if c.cflag[2] == 1:
        out.printl(f"{c.cstr[0]}が現れた！")
    else:
        out.printl(f"{print_transcallname(st, st.target)}が現れた！")


# --- COM0／COM201–203 変身（COMF0.ERB）、TRANSFORM_MOVESELECT（MOVESELECT.ERB）------------------


def transform_moveselect(ctx: Ctx) -> ComGen:
    """`@TRANSFORM_MOVESELECT`（MOVESELECT.ERB:2–86）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    if st.tflag[24] > 0:
        return 0
    if v[0] < 1 or v.get_bit(216, 1):
        return 0
    v[8] += 10
    able5 = com_able(ctx, 5)[0]
    able6 = com_able(ctx, 6)[0]
    able7 = com_able(ctx, 7)[0]
    v[8] -= 10
    if able5 == 0 and able6 == 0 and able7 == 0:
        return 0
    lcount = ctx.out.linecount
    if c.cflag[12] > 0:
        result = c.cflag[12]
    elif st.temp.selectcom > 200:
        result = st.temp.selectcom - 200
    else:
        out = ctx.out
        out.printl()
        out.printl("変身方法を選択してください")
        if v[0] == 1:
            out.printl("[1]その場で変身する　　　　　（回避+20%）")
        elif able6 > 0:
            out.printl("[1]踏み込んで隙を突く　　　　（近距離に移動、EXゲージが上昇）")
        if v[0] == 2:
            out.printl("[2]その場で変身する　　　　　（回避+15%）")
        elif able7 > 0:
            out.printl("[2]敵の動きを見極める　　　　（中距離に移動、次のターン予測精度アップ）")
        if v[0] == 3:
            out.printl("[3]その場で変身する　　　　　（回避+10%）")
        elif able5 > 0:
            out.printl("[3]距離を取って態勢を整える　（遠距離に移動、体力気力が多めに回復）")
        result = yield
    while True:
        if result == v[0]:
            ctx.out.clearline(ctx.out.linecount - lcount)
            return 0
        for n, able in ((1, able6), (2, able7), (3, able5)):
            if result == n and able > 0:
                v[0] = n
                if t(ctx, c, "空中浮遊") > 0:
                    st.tflag[99] += 1
                ctx.out.clearline(ctx.out.linecount - lcount)
                return n
        result = yield  # GOTO INPUT_LOOP


def com0(ctx: Ctx) -> ComGen:
    """`COMF0.ERB@COM0`:2–114（COM201–203 も同じ：:118–126）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    if act_limit(ctx) == 1:
        return 1
    moveselect = yield from transform_moveselect(ctx)
    attack_air_flag(ctx)
    print_distance(ctx)
    out.printl()
    _msg_transformcall(ctx)
    if v[10] != 1:
        _msg_nanori(ctx)
        v[10] = 1
        _msg_nanori_byousha(ctx)
        perform_cheers_hate(ctx)
    out.printw()
    if (
        charatalent(ctx.data, c, 0, "オトコ") == 0
        and charatalent(ctx.data, c, 1, "オトコ") > 0
        and t(ctx, c, "妊娠") > 0
    ):
        out.printl()
        out.printl("しかし、なぜか男性化できない！")
        out.printw(f"{print_transcallname(st, st.target)}は無防備な体制のまま変身に失敗してしまった！")
        v[2] = P_NOTHING
        return 1
    if get_battle_situation(st, "奇襲") and t(ctx, c, "変身時ＴＳ") and st.tflag[0] < 3:
        out.printl(f"しかし、急の襲撃で身体が変身準備に入れない！（変身チャージ完了まで：{3 - st.tflag[0]}ターン）")
        out.printw(f"{print_transcallname(st, st.target)}は無防備な体制のまま変身に失敗してしまった！")
        v[2] = P_NOTHING
        return 1
    transform(ctx, 1)
    if c.cflag[41] != 0 and v[23] == 0:
        v[23] = 10
    if moveselect == 1:
        if c.cflag[99] < 5:
            v[6] += 30 + st.rng.rand(16)
        elif c.cflag[99] < 15:
            v[6] += 20 + st.rng.rand(11)
        else:
            v[6] += 10 + st.rng.rand(6)
    if moveselect == 2:
        st.tflag[25] = 1
    l0 = c.maxbase[0]
    l0 = times(l0, "0.22" if t(ctx, c, "回復早い") == 1 else "0.18" if t(ctx, c, "回復遅い") == 1 else "0.20")
    # :84 `TALENT:(FLAG:799):共生`（行動中キャラ＝TARGET）
    if st.charas[st.flag[799]].talent[ctx.data.index_of("TALENT", "共生")] == 1:
        l0 = times(l0, "1.02")
    if moveselect == 3:
        l0 = times(l0, "1.50")
    if c.base[0] + l0 >= c.maxbase[0]:
        l0 = c.maxbase[0] - c.base[0]
    if c.base[0] == 0:
        l0 = 0
    c.base[0] += l0
    l1 = c.maxbase[1]
    l1 = times(l1, "0.22" if t(ctx, c, "回復早い") == 1 else "0.18" if t(ctx, c, "回復遅い") == 1 else "0.20")
    if moveselect == 3:
        l1 = times(l1, "1.50")
    if c.base[1] + l1 >= c.maxbase[1]:
        l1 = c.maxbase[1] - c.base[1]
    c.base[1] += l1
    return 1


# --- COM1–3 攻撃（COMF1–3.ERB）、COM_ATTACK_COMMON ------------------------------------


def com_attack(ctx: Ctx, n: int) -> ComGen:
    """`COMF{1,2,3}.ERB@COM{n}`（近・中・遠距離攻撃）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    if act_limit(ctx) == 1:
        return 1
    attack_air_flag(ctx)
    # :12 べとべと中の滑り（COM1 は RAND を括弧内で先に、COM2/3 も左から評価される）
    if (v[12] & BETOBETO) and (st.rng.rand(100) < 10 and v[0] != n) and not v.get_bit(216, 1):
        print_distance(ctx)
        out.printl()
        out.printl(f"{print_transcallname(st, st.target)}は脚を滑らせてしまった！")
        out.printl("移動を伴う行動が失敗した！")
        out.printw()
        return 1
    if v[0] == n and st.tflag[30]:
        st.tflag[30] += 1
    else:
        st.tflag[30] = 1
    v[0] = n
    com_attack_common(ctx)
    exp_name, kind = {1: ("近距離戦闘経験", 0), 2: ("中距離戦闘経験", 1), 3: ("遠距離戦闘経験", 2)}[n]
    if t(ctx, c, "変身能力") != -1:
        c.exp[ctx.data.index_of("EXP", exp_name)] += st.rng.rand(5) + 1
        sengiup(ctx, st.target, kind)
    else:
        c.exp[ctx.data.index_of("EXP", "戦闘基礎経験")] += st.rng.rand(5) + 1
        sengiup(ctx, st.target, 3)
    c.ex[99] += 2
    return 1
    yield  # pragma: no cover  （ジェネレータにするため）


# COMBO_ATTACK.ERB:155–189 バースト攻撃の説明（LOCALS:2）
_BURST_DESC = {
    "連続": "6回連続攻撃",
    "装甲": "直撃率アップ＋攻撃後にオートガード",
    "撹乱": "与ダメージアップ＋怯み効果",
    "重撃": "直撃しにくい大ダメージ攻撃",
    "広範": "必中攻撃＋反動で回避不能",
    "全力": "捨て身の大ダメージ攻撃",
    "知略": "クリティカル率アップ＋見切り効果",
    "設置": "油断効果2倍",
    "使役": "直撃しにくい大ダメージ攻撃",
    "反撃": "戦闘中に反撃で蓄積させた被害を加算",
    "通常": "与ダメージアップ＋直撃率アップ",
}


def print_combo(ctx: Ctx) -> None:
    """`COMBO_ATTACK.ERB@PRINT_COMBO`:119–246。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    lens = 26

    def row(a: str, b: str, d: str) -> None:
        out.print(format_percent(a, lens - 4, left=True))
        out.print(format_percent(b, lens, left=True))
        out.print(d)
        out.printl()

    if v.get_bit(216, 1):
        airplus = cloth_battle_hosei(ctx, "AIRPLUS", st.target)
        local = (1 if t(ctx, c, "空中得意") > 0 else 0) * get_air_strike(ctx, 2) + airplus * 25 - (
            1 if t(ctx, c, "空中苦手") > 0 else 0
        ) * get_air_strike(ctx, 3)
        if local > 0:
            s2 = f"直撃率＋{local}％　回避率＋{get_air_strike(ctx, 1)}％"
        elif local < 0:
            s2 = f"直撃率?{-local}％　回避率＋{get_air_strike(ctx, 1)}％"
        else:
            s2 = f"回避率＋{get_air_strike(ctx, 1)}％"
        if t(ctx, c, "空中得意") > 0:
            s2 += "（空中得意）"
        elif t(ctx, c, "空中苦手") > 0:
            s2 += "（空中苦手）"
        if t(ctx, c, "エアマスター") > 0:
            s2 += "（エアマスター）"
        row("　＋AIR STRIKE", "空中攻撃", s2)
    if v.get_bit(217, 0):  # :152–194
        row("　＋BURST STRIKE", f"バースト攻撃：{fstyle_name(ctx, st.target, v[0])}", _BURST_DESC[fstyle_name(ctx, st.target, v[0])])
    if st.tflag[30] > 1 and st.flag[73] == 0:
        a = "　＋ BRAVE COUNTER" if fstyle_name(ctx, st.target, v[0]) == "反撃" else "　＋BRAVE HIT"
        row(a, f"同一距離連続実行({st.tflag[30] - 1})",
            f"直撃率＋{get_brave_hit(ctx, st.tflag[30] - 1, '命中') - 3}％　回避率?{get_brave_hit(ctx, st.tflag[30] - 1, '回避')}％")
    if st.tflag[31] > 0 and st.flag[73] == 0:
        row("　＋CHAIN HIT", f"連続で攻撃ヒット({st.tflag[31]})", f"与ダメージ＋{get_chain_hit(ctx, st.tflag[31]) - 100}％")
    if st.tflag[32] > 0:
        row("　＋COUNTER ATTACK", f"防御しながら攻撃({st.tflag[32]})",
            f"直撃率＋{get_counter_attack(ctx, 1)}％　被ダメージ?{get_counter_attack(ctx, 2)}％")
    if st.tflag[33] > 1:
        row("　＋EVADER", f"連続で回避成功({st.tflag[33] - 1})",
            f"与ダメージ＋{div(get_evader_atk(ctx, st.tflag[33] - 1) - 100, 2)}％　クリティカル率＋{get_evader_crt(st.tflag[33] - 1)}％")


_RANGE_TEXTS = {
    1: ("近距離攻撃", True, "の頭上から強烈な一撃を叩きこんだ！", (
        "の懐に潜り込み全力の一撃を叩き込んだ！", "に対して息もつかせぬ連続攻撃を放った！",
        "の死角から電光石火の一撃を加え、すかさず飛びずさった！", "に肉薄し、強烈な一撃を叩き込んだ！",
        "の一瞬の隙を突いて飛び掛かり、側面から攻撃を叩き込んだ！")),
    2: ("中距離攻撃", False, "は空中に飛び上がり、上空から猛攻撃を仕掛けた！", (
        "はミドルレンジから強力な攻撃を放った！", "は力を集中させ、一気に解き放って攻撃した！",
        "は付かず離れずの位置から連続攻撃を仕掛けた！", "は障害物を利用して回避しながら、付かず離れずの距離から攻撃した！",
        "は接近すると見せかけて、中距離からそのまま攻撃した！")),
    3: ("遠距離攻撃", True, "に狙いを定め、高空から遠距離攻撃を仕掛けた！", (
        "から離れた位置から遠距離攻撃を仕掛けた！", "に遠距離攻撃を放ち、ヒットアンドアウェイの要領で後退した！",
        "の射程外から照準を定め、急所を狙い撃った！", "の動きを先読みし、連続で攻撃を放った！",
        "にロングレンジから狙い澄ました一撃を加えた！")),
}


def _msg_attack_range(ctx: Ctx, dist: int) -> None:
    """`MESSAGE_BATTLE_CHARA_ATTACK_RANGE_{SHORT,MIDDLE,LONG}`（MESSAGE_BATTLE.ERB:408–487）。"""
    st = ctx.state
    out = ctx.out
    name = print_transcallname(st, st.target)
    word, with_enemy, air, texts = _RANGE_TEXTS[dist]
    out.printl(f"{name}の{word}！")
    if with_enemy:
        if enemy_type_check(st, "AKUOTI") == 1:
            raise NotImplementedError("悪堕ちキャラ戦の地の文は未移植")
        out.print(f"{name}は")
        tentacle_access(ctx, "NAME")
    else:
        out.print(name)
    if tc(ctx).tcvarn.get_bit(216, 1):
        out.printl(air)
    else:
        out.printl(texts[st.rng.rand(5)])
    code = {1: "SHORT", 2: "MIDDLE", 3: "LONG"}[dist]
    kojo_root(ctx, f"BATTLE_CHARA_ATTACK_RANGE_{code}")
    out.printw()


_RANGE_ARGS = {1: "ATTACK_RANGE_SHORT", 2: "ATTACK_RANGE_MIDDLE", 3: "ATTACK_RANGE_LONG"}


def com_attack_common(ctx: Ctx) -> int:
    """`COM_ATTACK_COMMON.ERB@COM_ATTACK_COMMON`:3–428。"""
    st, data = ctx.state, ctx.data
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    name = print_transcallname(st, st.target)
    attack_num = 0
    hit_flag = 0
    loc: dict[int, int] = {}  # VARSET LOCAL
    kojo_root(ctx, "BATTLE_CHARA_BATTLE_STYLE_CHANGE")
    style = fstyle_name(ctx, st.target, v[0])
    burst = v.get_bit(217, 0)
    if style == "連続":  # :15–16
        attack_num += 1
    if burst and style == "連続":  # :18–19 [連続]バースト
        attack_num += 4
    if not burst and style == "使役":  # :21–22
        attack_num += 1
    print_distance(ctx)
    out.print("　")
    out.set_bold(True)
    if c.cstr[v[0] + 4] != "":
        out.print(f"『{c.cstr[v[0] + 4]}』")
    out.printl(f"<<{fstyle_name(ctx, st.target, v[0])}>>")
    out.set_bold(False)
    print_combo(ctx)
    out.printl()
    if v[2] == P_HANGEKI_OK:
        raise NotImplementedError("反撃成功時の攻撃（MESSAGE_BATTLE_CHARA_ATTACK_HANGEKI）は S06")
    _msg_attack_range(ctx, v[0])
    while True:  # $ATTACK_AGAIN
        kind = _RANGE_ARGS[v[0]]
        r, _ = act_hantei_chara_to_tentacle(ctx, kind)
        if enemy_type_check(st, "LASTBOSS") >= 1 and st.flag[11] == 2 and st.flag[21] == 1 and (st.tflag[13] & v[0]) == 0:
            raise NotImplementedError("ラスボス（天使の樹）戦は未移植")
        if r == 0:
            if act_hantei_chara_to_tentacle_guard(ctx, kind):
                hit_flag = -1
                st.tflag[31] += 1
                dmg = damage(ctx, kind)
                hp = div(c.base[0] * 100, c.maxbase[0])
                if style == "広範":
                    k, a, cap, rnd = {1: (100, 20, 40, (26, 75)), 2: (200, 15, 30, (51, 50)), 3: (300, 10, 20, (76, 25))}[v[0]]
                    l1 = div(min(div(dmg * k * min(hp + a, cap), 10000) + 100, dmg) * (st.rng.rand(rnd[0]) + rnd[1]), 100)
                else:
                    k, a, cap = {1: (25, 15, 30), 2: (100, 10, 20), 3: (300, 5, 10)}[v[0]]
                    l1 = min(div(dmg * k * min(hp + a, cap), 10000) + 50, dmg)
                # :108–112 [反撃]バースト：蓄積ダメージ（TCVARn:205）の 1/4 を加算
                if burst and v[2] != P_HANGEKI_OK and style == "反撃":
                    l99 = div(v[205], 4)
                    l1 += l99
                    v[205] = v[205] - l99
                st.flag[13] -= l1
                # MESSAGE_BATTLE_CHARA_ATTACK_GUARD（MESSAGE_BATTLE.ERB:557–566）
                out.set_color((0, 255, 255))
                out.printl("GUARD...")
                out.reset_color()
                out.printl(f"{name}の攻撃は直撃しなかったようだ・・・")
                if attack_num == 0:
                    kojo_root(ctx, "BATTLE_CHARA_ATTACK_FALSE")
                out.set_bold(True)
                out.printl(f"{l1}のダメージを与えた！")
                out.set_bold(False)
                out.printw()
                if l1 >= 5000:
                    unlock_achievement(ctx, 263, "破壊神の一撃")
                loc[2] = 1
            else:
                hit_flag = 0
                st.tflag[31] = 0
                # MESSAGE_BATTLE_CHARA_ATTACK_FALSE（:546–554）
                out.set_color((255, 0, 255))
                out.printl("MISS!")
                out.reset_color()
                out.printl(f"{name}の攻撃は回避されてしまった・・・")
                if attack_num == 0:
                    kojo_root(ctx, "BATTLE_CHARA_ATTACK_FALSE")
                out.printw()
            if v[1] == 0 and attack_num == 0:
                shinkyou_change(ctx, "KOUYOU_SYOUTIN")
            l3 = 0
            if style == "設置" and loc.get(2, 0):  # :147–152
                l3 += 125
                if burst:
                    l3 += 125
            if l3 > 0:
                _yudan_up(ctx, l3)
            # :166–169 [撹乱]バーストの怯み（RAND は左から：GETBIT・スタイルが真のときだけ引く）
            if burst and style == "撹乱" and st.rng.rand(10) == 0 and hit_flag == -1:
                st.tflag[1] = 1
                out.printl("うまく相手の体勢を崩した！")
        else:
            st.tflag[31] += 1
            crit = cloth_battle_hosei(ctx, "CRITICAL")
            if t(ctx, c, "獣性の証") > 0:
                crit += 6
            hi_power = t(ctx, c, "秘められし力") > 0 and percent_cal(c.base[0] + c.base[1], c.maxbase[0] + c.maxbase[1]) <= 25
            if hi_power:
                crit += 12
            if t(ctx, c, "心眼") > 0:
                crit += 3
            if t(ctx, c, "共生") > 0:
                crit += 2
            if style == "撹乱":
                crit += 5
            if burst and style == "知略":  # :191–192
                crit += 5
            if st.tflag[33] > 1:
                crit += get_evader_crt(st.tflag[33] - 1)
            l0 = max(c.base[11] - 100, 0)
            crit += min(div(isqrt(l0) * 2, 3), 12)
            if v[0] == 1:
                crit += 3 + st.tflag[30] * 2
            if v[0] == 2:
                crit += 1
            if st.rng.rand(100) < 5 + crit:
                l0 = 15
                if burst:  # :215–216
                    l0 += 5
                # :218–221 秘められし力の RESULT 加算は直後の CALL DAMAGE で上書きされるので無効
            else:
                l0 = 10
            dmg = damage(ctx, _RANGE_ARGS[v[0]])
            l1 = div(dmg * l0, 10)
            if burst and v[2] != P_HANGEKI_OK and style == "反撃":  # :240–241
                l1 += v[205]
            st.flag[13] -= l1
            loc[2] = l1
            result = 0
            if l0 > 10:
                hit_flag = 2
                # MESSAGE_BATTLE_CHARA_ATTACK_CRITICAL_HIT（:522–532）
                out.set_color((255, 0, 0))
                out.set_bold(True)
                out.printl("CRITICAL HIT!")
                out.set_bold(False)
                out.reset_color()
                if attack_num == 0:
                    kojo_root(ctx, "BATTLE_CHARA_ATTACK_CRITICAL_HIT")
            else:
                hit_flag = 1
                out.set_color((255, 255, 0))
                out.printl("HIT!")
                out.reset_color()
                if attack_num == 0:
                    kojo_root(ctx, "BATTLE_CHARA_ATTACK_HIT")
            # :264 `FLAG:13 <= 0 && RESULT == 999`：地の文関数は RETURN 999 しない限り RESULT = 0
            if st.flag[13] <= 0 and result == 999:
                l1 *= 16
            out.set_bold(True)
            out.printl(f"{l1}のダメージを与えた！")
            out.set_bold(False)
            if st.flag[999] and hit_flag == 2:
                out.printl(f"クリティカル倍率：{l0 * 10}％")
            out.printw()
            if loc[2] >= 5000:
                unlock_achievement(ctx, 263, "破壊神の一撃")
            l3 = 0
            if style == "設置":  # :279–284
                l3 += 300
                if burst:
                    l3 += 300
            if l3 > 0:
                _yudan_up(ctx, l3)
            # :298–303 [撹乱]バーストの怯み（クリティカルなら RAND を引かない：|| の短絡評価）
            if burst and style == "撹乱":
                if hit_flag == 2 or st.rng.rand(2) == 0:
                    st.tflag[1] = 1
                    out.printl("うまく相手の体勢を崩した！")
        if attack_num:
            attack_num -= 1
            continue
        break
    if style == "全力":
        st.tflag[99] += 2
    if burst:  # :317–402 バースト攻撃の反動
        _burst_recoil(ctx, style, hit_flag)
    if t(ctx, c, "サド気質") > 0 and hit_flag > 0:
        l1 = st.rng.rand(max(div(c.maxbase[1] * hit_flag * 8, 100), 1)) + 10
        if c.base[1] + l1 >= c.maxbase[1]:
            l1 = c.maxbase[1] - c.base[1]
        c.base[1] += l1
        st.temp.common_palam[7] += l1 * 10
        if l1 > 0:
            out.printl(f"サディスティックな快楽で{data.names['BASE'].get(1, '')}が{l1}回復した")
    if style == "反撃" and v[2] != P_HANGEKI_OK and not burst:
        raise NotImplementedError("[反撃]スタイルの反撃準備は S06")
    return 1


def _yudan_up(ctx: Ctx, amount: int) -> None:
    """COM_ATTACK_COMMON.ERB:153–164／:285–296：油断度上昇の追加効果（FLAG:17 += LOCAL:3）。"""
    st = ctx.state
    out = ctx.out
    if st.flag[110] == 0:
        tentacle_access(ctx, "NAME")
    elif st.flag[110] == 1:
        out.print(print_transcallname(st, st.flag[111]))
    out.printl(f"の油断度が少し上昇した……（＋{_tofull(amount)}）")
    out.printw()
    st.flag[17] += amount


# :318–385 バースト攻撃の反動（TFLAG:99 加算量。反撃は別処理）
_BURST_RECOIL = {"連続": 2, "装甲": 2, "撹乱": 2, "重撃": 3, "広範": 3, "全力": 4, "知略": 1, "設置": 1, "使役": 3, "通常": 1}


def _burst_recoil(ctx: Ctx, style: str, hit_flag: int) -> None:
    """COM_ATTACK_COMMON.ERB:317–402。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    if style == "反撃":  # :337–382
        if v[2] != P_HANGEKI_OK:
            st.tflag[99] += 3
            if v[205] > v[206] and hit_flag != -1:
                # :346 MESSAGE_BATTLE_TENTACLE_ATTACK_OVERCHARGE（地の文/MESSAGE_BATTLE.ERB:1226–1240）
                run_chinobun(ctx, "MESSAGE_BATTLE_TENTACLE_ATTACK_OVERCHARGE")
                if enemy_type_check(st, "AKUOTI"):  # :348–349
                    raise NotImplementedError("悪堕ちキャラの地の文（MESSAGE_OTHER_BATTLE_TENTACLE_ATTACK_OVERCHARGE）は未移植")
                result = min(percent_cal(v[205], v[206]), 70)  # :353–355
                l2 = div(c.maxbase[0] * result, 100)
                out.set_bold(True)
                out.printl(f"{l2}ダメージを受けた！")
                out.set_bold(False)
                if c.base[0] - l2 <= 0:
                    l2 = c.base[0]
                c.base[0] -= l2
                # :375 `FOR RESULT, RESULT, 0, -5`：負の STEP は「終端 < カウンタ」の間くり返す
                # （reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1739–1743、NEXT:2153–2158）
                r = result
                while r > 0:
                    st.tflag[99] += 3
                    r -= 5
                v[205] = 0
    else:
        st.tflag[99] += _BURST_RECOIL[style]
    if t(ctx, c, "ホットスタート") > 0:  # :387–390
        st.tflag[99] += 1
    if t(ctx, c, "フルバースト") > 0:
        st.tflag[99] += 1
    name = print_transcallname(st, st.target)
    if style == "装甲":  # :393–396 オートガード
        v[2] = P_GUARD
        out.printl(f"{name}は防御態勢になった！")
    if style == "知略":  # :398–401 見切り
        st.tflag[25] = 1
        out.printl(f"{name}は見切り状態になった！")


# --- COM4 防御、COM5 距離をとる、COM99 ギブアップ ------------------------------------------


def com4(ctx: Ctx) -> ComGen:
    """`COMF4.ERB@COM4`:2–44。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    if act_limit(ctx) == 1:
        return 1
    if v.get_bit(216, 1):
        v[216] = 4
        if t(ctx, c, "有翼") > 0:
            st.tflag[99] += 1
    else:
        v[216] = 0
    print_distance(ctx)
    out.printl()
    if fstyle_name(ctx, st.target, v[0]) == "反撃":
        raise NotImplementedError("[反撃]スタイルのＥＸ反撃は S06")
    # MESSAGE_BATTLE_CHARA_DEFENSE（MESSAGE_BATTLE.ERB:569–574）
    out.printl(f"{print_transcallname(st, st.target)}は集中して身を固めた！")
    kojo_root(ctx, "BATTLE_CHARA_DEFENSE")
    out.printw()
    v[2] = P_GUARD
    c.ex[99] += 1
    return 1
    yield  # pragma: no cover


def com5(ctx: Ctx) -> ComGen:
    """`COMF5.ERB@COM5`:2–141。"""
    st, data = ctx.state, ctx.data
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    if act_limit(ctx) == 1:
        return 1
    attack_air_flag(ctx)
    if (v[12] & BETOBETO) and st.rng.rand(100) < 50 and not v.get_bit(216, 1):
        print_distance(ctx)
        out.printl()
        out.printl(f"{print_transcallname(st, st.target)}は脚を滑らせてしまった！")
        out.printl("移動を伴う行動が失敗した！")
        out.printw()
        return 1
    st.tflag[30] = 0
    st.tflag[31] = 0
    v[0] = 3
    print_distance(ctx)
    out.printl()
    tt = lambda n: t(ctx, c, n)  # noqa: E731
    l0 = c.maxbase[0] + div(c.base[11] * cloth_battle_hosei(ctx, "BOUGYO") * 2, 100)
    if tt("溢れる生命力") > 0:
        l0 = times(l0, "1.25")
    l0 = times(l0, "0.49" if tt("回復早い") == 1 else "0.41" if tt("回復遅い") == 1 else "0.45")
    if st.charas[st.flag[799]].talent[data.index_of("TALENT", "共生")] == 1:
        l0 = times(l0, "1.04")
    if c.base[1] == 0:
        l0 = div(l0, 2)
    for _ in range(max(c.cflag[99], 0)):
        if l0 <= 1:
            break
        l0 = times(l0, "0.985" if tt("スタミナ") > 0 else "0.97")
    if tt("スタミナ") > 0:
        if c.cflag[99] < 5:
            l0 = times(l0, "1.25")
        elif c.cflag[99] < 10:
            l0 = times(l0, "1.10")
    else:
        if c.cflag[99] == 0:
            l0 = times(l0, "1.25")
        elif c.cflag[99] < 5:
            l0 = times(l0, "1.10")
    if c.cflag[43] == 504:
        l0 += 200
    if c.base[0] + l0 >= c.maxbase[0]:
        l0 = c.maxbase[0] - c.base[0]
    if c.base[0] == 0:
        l0 = 0
    c.base[0] += l0
    l1 = c.maxbase[1] + div(c.base[11] * cloth_battle_hosei(ctx, "BOUGYO") * 4, 200)
    if tt("溢れる生命力") > 0:
        l1 = times(l1, "1.25")
    l1 = times(l1, "0.22" if tt("回復早い") == 1 else "0.18" if tt("回復遅い") == 1 else "0.20")
    if c.base[1] + l1 >= c.maxbase[1]:
        l1 = c.maxbase[1] - c.base[1]
    for _ in range(max(c.cflag[99], 0)):
        if l1 <= 1:
            break
        l1 = times(l1, "0.995" if tt("スタミナ") > 0 else "0.99")
    c.base[1] += l1
    st.tflag[99] += 1
    if tt("空中浮遊") > 0:
        st.tflag[99] += 1
    # MESSAGE_BATTLE_CHARA_TAKEAWAY（MESSAGE_BATTLE.ERB:595–600）
    out.printl(f"{print_transcallname(st, st.target)}は一度距離をとって体勢を立て直し、心を落ち着けた・・・")
    kojo_root(ctx, "BATTLE_CHARA_TAKEAWAY")
    out.printw()
    names = data.names["BASE"]
    if c.base[0]:
        out.printl(f"{names.get(0, '')}が{l0}回復した")
    else:
        out.printl(f"{names.get(0, '')}は既に尽きてしまっている……")
    out.printl(f"{names.get(1, '')}が{l1}回復した")
    if v[1] > 0 and st.rng.rand(100) < v[11] * 20:
        shinkyou_change(ctx, "NORMAL")
    else:
        v[11] += 1
    out.printl()
    return 1
    yield  # pragma: no cover


def _tofull(n: int) -> str:
    """`TOFULL`（半角→全角）。数値文字列のみ使う。"""
    return str(n).translate(str.maketrans("0123456789-", "０１２３４５６７８９－"))


def _move_prologue(ctx: Ctx) -> bool:
    """COMF6／COMF7.ERB:3–22 共通：行動制限・空中フラグ・べとべとによる失敗。True なら RETURN 1。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    if act_limit(ctx) == 1:
        return True
    attack_air_flag(ctx)
    if (v[12] & BETOBETO) and st.rng.rand(100) < 50 and not v.get_bit(216, 1):
        print_distance(ctx)
        out.printl()
        out.printl(f"{print_transcallname(st, st.target)}は脚を滑らせてしまった！")
        out.printl("移動を伴う行動が失敗した！")
        out.printw()
        return True
    st.tflag[30] = 0
    st.tflag[31] = 0
    return False


def _gauge_up(ctx: Ctx, table: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]) -> None:
    """ゲージが増加：CFLAG:99 < 5／< 15／それ以外 で (基本値, RAND 幅)。"""
    c = tc(ctx)
    k = 0 if c.cflag[99] < 5 else 1 if c.cflag[99] < 15 else 2
    c.tcvarn[6] += table[k][0] + ctx.state.rng.rand(table[k][1])


def com6(ctx: Ctx) -> ComGen:
    """`COMF6.ERB@COM6`:2–107 背後に回る。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    rand = st.rng.rand
    if _move_prologue(ctx):
        return 1
    _gauge_up(ctx, ((30, 16), (20, 11), (10, 6)))  # :27–33
    v[0] = 1  # :36 距離を近に
    print_distance(ctx)
    out.printl()
    st.tflag[99] += 1  # :42–45
    if t(ctx, c, "空中浮遊") > 0:
        st.tflag[99] += 1
    # MESSAGE_BATTLE_CHARA_STEPIN（地の文/MESSAGE_BATTLE.ERB:603–607）
    out.printl(f"{print_transcallname(st, st.target)}はあえて踏み込み、相手の背後に回った！")
    kojo_root(ctx, "BATTLE_CHARA_STEPIN")
    out.printw()
    if enemy_type_check(st, "AKUOTI") == 1:  # :50–51
        raise NotImplementedError("悪堕ちキャラの地の文（MESSAGE_OTHER_BATTLE_CHARA_STEPIN）は未移植")
    l0 = div(c.maxbase[ctx.data.index_of("BASE", "知性")] * cloth_battle_hosei(ctx, "CHISEI"), 100)  # :54–58
    l0 = shinkyou_check(ctx, "CHISEI", l0)  # :61–62
    l1 = int(tentacle_access(ctx, "CHISEI"))  # :65–70（悪堕ちキャラは上で停止済み）
    result = percent_cal(l0, l1)  # :72
    # `RAND:RESULT / 2` は (RAND:RESULT) / 2：変数の `:` 引数は単項だけを読む
    # （reference/emuera-1824/Emuera/GameData/Expression/ExpressionParser.cs@ReduceVariableArgument:192–198）
    if rand(360) + 90 < result or st.tflag[10] == 4:  # :73–80
        local = 500 + div(rand(result), 2)
        st.tflag[3] += local
        out.printl("相手は一瞬こちらを見失って取り乱した！")
        out.printl(f"油断度＋（{_tofull(local)}）")
        st.tflag[1] = 1
    elif rand(240) + 60 < result:  # :81–87
        local = 250 + div(rand(result), 2)
        st.tflag[3] += local
        out.printl("うまく相手を翻弄することができた！")
        out.printl(f"油断度＋（{_tofull(local)}）")
    elif rand(180) + 30 < result:  # :88–94
        local = 100 + div(rand(result), 4)
        st.tflag[3] += local
        out.printl("相手のペースを乱した！")
        out.printl(f"油断度＋（{_tofull(local)}）")
    else:
        out.printl("しかしうまくいかなかった・・・")
    out.printl("EXゲージが大きく溜まった！")
    if rand(100) < v[11] * v[11] or v[1] == 0:  # :100–105
        if rand(2) == 0:
            shinkyou_change(ctx, "KOUYOU")
    else:
        v[11] += 1
    out.printl()
    return 1
    yield  # pragma: no cover


def com7(ctx: Ctx) -> ComGen:
    """`COMF7.ERB@COM7`:2–154 見切り。"""
    st, data = ctx.state, ctx.data
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    if _move_prologue(ctx):
        return 1
    _gauge_up(ctx, ((20, 11), (15, 6), (5, 6)))  # :27–33
    v[0] = 2  # :36 距離を中に
    print_distance(ctx)
    out.printl()
    st.tflag[25] = 1  # :42 見切りフラグ
    tt = lambda n: t(ctx, c, n)  # noqa: E731
    l0 = c.maxbase[0] + div(c.base[11] * cloth_battle_hosei(ctx, "BOUGYO") * 2, 100)  # :50–51
    if tt("溢れる生命力") > 0:
        l0 = times(l0, "1.25")
    l0 = times(l0, "0.27" if tt("回復早い") == 1 else "0.23" if tt("回復遅い") == 1 else "0.25")
    if st.charas[st.flag[799]].talent[data.index_of("TALENT", "共生")] == 1:
        l0 = times(l0, "1.02")
    if c.base[1] == 0:
        l0 = div(l0, 2)
    for _ in range(max(c.cflag[99], 0)):  # :69–78
        if l0 <= 1:
            break
        l0 = times(l0, "0.985" if tt("スタミナ") > 0 else "0.97")
    if tt("スタミナ") > 0:  # :80–92
        if c.cflag[99] < 5:
            l0 = times(l0, "1.25")
        elif c.cflag[99] < 10:
            l0 = times(l0, "1.10")
    else:
        if c.cflag[99] == 0:
            l0 = times(l0, "1.25")
        elif c.cflag[99] < 5:
            l0 = times(l0, "1.10")
    if c.cflag[43] == 504:  # :94–95 救急スプレー
        l0 += 100
    if c.base[0] + l0 >= c.maxbase[0]:
        l0 = c.maxbase[0] - c.base[0]
    if c.base[0] == 0:
        l0 = 0
    c.base[0] += l0
    l1 = c.maxbase[1] + div(c.base[11] * cloth_battle_hosei(ctx, "BOUGYO") * 4, 200)  # :105–106
    if tt("溢れる生命力") > 0:
        l1 = times(l1, "1.25")
    l1 = times(l1, "0.11" if tt("回復早い") == 1 else "0.09" if tt("回復遅い") == 1 else "0.10")
    if c.base[1] + l1 >= c.maxbase[1]:
        l1 = c.maxbase[1] - c.base[1]
    for _ in range(max(c.cflag[99], 0)):  # :120–129
        if l1 <= 1:
            break
        l1 = times(l1, "0.995" if tt("スタミナ") > 0 else "0.99")
    c.base[1] += l1
    st.tflag[99] += 1  # :133–136
    if tt("空中浮遊") > 0:
        st.tflag[99] += 1
    # MESSAGE_BATTLE_CHARA_SEETHROUGH（地の文/MESSAGE_BATTLE.ERB:610–619）
    if tt("主観視点") > 0:
        out.printl(f"{print_transcallname(st, st.target)}は油断なく相手の動きを観察した！")
    else:
        out.printl(f"{print_transcallname(st, st.target)}は相手の動きを見切ろうとしている！")
    kojo_root(ctx, "BATTLE_CHARA_SEETHROUGH")
    out.printw()
    if enemy_type_check(st, "AKUOTI") == 1:  # :141–142
        raise NotImplementedError("悪堕ちキャラの地の文（MESSAGE_OTHER_BATTLE_CHARA_SEETHROUGH）は未移植")
    names = data.names["BASE"]
    if c.base[0]:  # :144–149
        out.printl(f"{names.get(0, '')}が{l0}回復した")
    else:
        out.printl(f"{names.get(0, '')}は既に尽きてしまっている……")
    out.printl(f"{names.get(1, '')}が{l1}回復した")
    out.printl("EXゲージが少し溜まった！")
    if st.rng.rand(100) < v[11] * v[11] or v[1] == 0:  # :152–156
        shinkyou_change(ctx, "REISEI")
    else:
        v[11] += 1
    out.printl()
    return 1
    yield  # pragma: no cover


def com99(ctx: Ctx) -> ComGen:
    """`COMF99.ERB@COM99`:2–21。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    print_distance(ctx)
    out.printl()
    c.base[0] = 0
    c.base[1] = 0
    c.base[2] = 0
    c.tcvarn[2] = P_NOTHING
    # MESSAGE_BATTLE_CHARA_NOACTION（MESSAGE_BATTLE.ERB:623–628）
    out.printl(f"{print_transcallname(st, st.target)}は何もしなかった")
    kojo_root(ctx, "BATTLE_CHARA_NOACTION")
    out.printw()
    return 1
    yield  # pragma: no cover


def com69(ctx: Ctx) -> ComGen:
    """`COMF69.ERB@COM69`:2–29 何もしない。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    if v.get_bit(216, 1):  # :5–9 滞空状態なら着地
        v[216] = 4
        if t(ctx, c, "有翼") > 0:
            st.tflag[99] += 1
    print_distance(ctx)  # :11–12
    out.printl()
    v[2] = P_NOTHING  # :15
    if v[12] & KIZETU:  # :18–20
        out.printl(f"{print_transcallname(st, st.target)}は意識を失っている…")
        out.printw()
    else:
        # MESSAGE_BATTLE_CHARA_NOACTION（地の文/MESSAGE_BATTLE.ERB:623–628）
        out.printl(f"{print_transcallname(st, st.target)}は何もしなかった")
        kojo_root(ctx, "BATTLE_CHARA_NOACTION")
        out.printw()
        if enemy_type_check(st, "AKUOTI") == 1:  # :24–25
            raise NotImplementedError("悪堕ちキャラの地の文（MESSAGE_OTHER_BATTLE_CHARA_NOACTION）は未移植")
    return 1
    yield  # pragma: no cover


def _invert_bit(v, key: int, bit: int) -> None:  # noqa: ANN001  INVERTBIT
    v.set_bit(key, bit, not v.get_bit(key, bit))


def com16(ctx: Ctx) -> ComGen:
    """`COMF16.ERB@COM16`:2–7 エアストライク：空中攻撃フラグの切り替えのみ（RETURN 0）。"""
    _invert_bit(tc(ctx).tcvarn, 216, 0)
    return 0
    yield  # pragma: no cover


def com17(ctx: Ctx) -> ComGen:
    """`COMF17.ERB@COM17`:2–7 バースト攻撃：使用フラグの切り替えのみ（RETURN 0）。"""
    _invert_bit(tc(ctx).tcvarn, 217, 0)
    return 0
    yield  # pragma: no cover


def com_ex_gauge(ctx: Ctx, n: int) -> ComGen:
    """`COMF71.ERB@COM71`／`COMF72.ERB@COM72`:2–29：ＥＸゲージの予約と返却（RETURN 0）。"""
    c = tc(ctx)
    v = c.tcvarn
    bit = 0 if n == 71 else 1
    if c.cflag[1] == 2:
        amount = 68 if v[217] else 34
    else:
        amount = 100
    v[6] += amount if v.get_bit(3, bit) else -amount
    _invert_bit(v, 3, bit)
    return 0
    yield  # pragma: no cover


# --- COM70 ＳＰバースト、COM73 ＳＰ変身、COM74 ＳＰフルバースト（COMF70／73／74.ERB）------------------


def _print_enemy_name(ctx: Ctx) -> None:
    """COMF70.ERB:48–52 等：`FLAG:110 == 0` なら TENTACLE_ACCESS "NAME"、1 なら PRINT_TRANSCALLNAME(FLAG:111)。"""
    st = ctx.state
    if st.flag[110] == 0:
        tentacle_access(ctx, "NAME")
    elif st.flag[110] == 1:
        ctx.out.print(print_transcallname(st, st.flag[111]))


def _fatigue_limit(ctx: Ctx, label: str) -> bool:
    """COMF70.ERB:9–14／COMF74.ERB:9–14：CFLAG:99 >= 100 なら使えない（True＝RETURN 0）。"""
    st = ctx.state
    c = tc(ctx)
    if c.cflag[99] < 100:
        return False
    from ..action import print_callname

    ctx.out.printl(f"{print_callname(st, st.target)}に蓄積した疲労はもう限界に達している…！")
    ctx.out.printl(f"{label}は使えない…！")
    ctx.out.printw()
    return True


def sp_burst_damage(ctx: Ctx) -> int:
    """COMF70.ERB:30–44 ＳＰバーストの固定ダメージ（RAND なし）。"""
    st, data = ctx.state, ctx.data
    c = tc(ctx)
    v = c.tcvarn
    b = lambda n: data.index_of("BASE", n)  # noqa: E731
    ex = c.ex[99]  # EX:行動ポイント
    local = div(
        max((c.maxbase[b("体力")] + c.maxbase[b("気力")] - 2000) * 2 + (c.maxbase[b("防御")] - 100) * 3, 480)
        * max(v[4] + v[5] - 200, 0) ** 2  # POWER(x, 2)：Math.Pow → long（Creator.Method.cs:1051–1062）
        * (100 + ex * 2),
        4800000,
    ) + 2500 * (1 if c.cflag[1] == 2 else 0)
    if st.temp.prevcom in (44, 45, 46, 47):  # :33–34
        local = div(local * 115, 100)
    if enemy_type_check(st, "AKUOTI") == 0 and enemy_type_check(st, "MOB") == 1:  # :36–37
        local *= 2
    rate = percent_cal(  # :39
        c.base[b("体力")] + c.base[b("気力")] + c.base[b("性耐性")] * 40,
        c.maxbase[b("体力")] + c.maxbase[b("気力")] + c.maxbase[b("性耐性")] * 40,
    )
    local = div(local * (125 - rate), 100)
    if t(ctx, c, "変身能力") < 1:  # :41–42
        local = div(local * 85, 100)
    return limit(local, 500, 99999)  # :44


def com70(ctx: Ctx) -> ComGen:
    """`COMF70.ERB@COM70`:2–76 ＳＰバースト（拘束中のみ使用可：COMABLE.ERB:676–698）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    print_distance(ctx)
    out.printl()
    if _fatigue_limit(ctx, "ＳＰバースト"):
        return 0
    v[0] = 2  # :16 拘束を吹き飛ばして中距離へ
    st.tflag[4] = 0
    v[6] += -500  # :20
    out.set_bold(True)
    out.printl("SPバースト")
    out.set_bold(False)
    run_chinobun(ctx, "MESSAGE_BATTLE_CHARA_SP_BURST", fallback=lambda: kojo_root(ctx, "BATTLE_CHARA_SP_BURST"))
    local = sp_burst_damage(ctx)
    st.flag[13] -= local  # :46
    out.set_bold(True)
    _print_enemy_name(ctx)
    out.printl(f"に{local}のダメージを与えた！")
    l0 = div(c.base[0], 4)  # :56–60 反動
    l1 = div(c.base[1], 4)
    c.base[0] -= l0
    c.base[1] -= l1
    out.printl(f"体力を{l0}、気力を{l1}消費した！")
    out.printw()
    out.set_bold(False)
    st.tflag[99] += 2 + div(max(v[4] + v[5] - 200, 0) * c.ex[99], 400)  # :65
    if c.ex[99] > 0:  # :68–69
        c.ex[99] = div(c.ex[99], 2) + 1
    st.tflag[1] = 1  # :72
    v[8] = 1  # :74
    return 1
    yield  # pragma: no cover


# COMF73.ERB:30–42 性格（SEIKAKU_CHECK "GET_TALENT_VALUE" の素質番号）→ 心境
_SP_SHINKYOU_IKARI = (15, 24, 27)  # 面倒くさがり, 古風, 乱暴者
_SP_SHINKYOU_REISEI = (10, 11, 14, 17, 18, 22)  # 臆病, 恥ずかしがり屋, おっとり, 楽天家, 悲観的, 無口


def com73(ctx: Ctx) -> ComGen:
    """`COMF73.ERB@COM73`:2–61 ＳＰ変身。"""
    from ..chara_common import seikaku_check

    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    print_distance(ctx)
    out.printl()
    run_chinobun(  # :9（CFLAG:1 を 2 にする前に呼ぶ：「再び」の分岐は CFLAG:1 == 1）
        ctx, "MESSAGE_BATTLE_CHARA_SP_TRANSFORMCALL", fallback=lambda: kojo_root(ctx, "BATTLE_CHARA_SP_TRANSFORMCALL")
    )
    c.cflag[1] = 2  # :12–14 SP モード：EX ゲージを SP ゲージに移す
    v[5] = v[4]
    v[4] = 0
    name = print_transcallname(st, st.target)
    if v[12] > 0:  # :17–21 状態異常が治る
        out.printl(f"{name}の状態異常が治った！")
        out.printl()
        v[12] = 0
    result = seikaku_check(ctx.data, c)  # :25
    out.print(f"{name}は ")  # :28
    if result in _SP_SHINKYOU_IKARI:
        v[1] = 2
        out.print("怒り")
    elif result in _SP_SHINKYOU_REISEI:
        v[1] = 4
        out.print("冷静")
    else:
        v[1] = 6
        out.print("高揚")
    out.printl("状態 になった")
    v[11] = 0  # :46
    if c.cflag[41] != 0:  # :49–50 アウター（変身後）のダメージ全回復
        v[23] = v[22]
    st.tflag[1] = 1  # :53
    st.tflag[99] += 3  # :56
    v[8] = 1  # :59
    return 1
    yield  # pragma: no cover


def sp_full_burst_damage(ctx: Ctx) -> int:
    """COMF74.ERB:32–46 ＳＰフルバーストの固定ダメージ（RAND なし）。"""
    st, data = ctx.state, ctx.data
    c = tc(ctx)
    v = c.tcvarn
    b = lambda n: data.index_of("BASE", n)  # noqa: E731
    local = div(
        max((c.maxbase[b("体力")] + c.maxbase[b("気力")] - 2000) + c.maxbase[b("攻撃")] * 10, 800)
        * (100 + c.ex[99] * 2)
        * (5000 + v[5]),
        500000,
    )
    if enemy_type_check(st, "AKUOTI") == 0 and enemy_type_check(st, "MOB") == 1:  # :38–39
        local *= 2
    rate = percent_cal(  # :41
        c.base[b("体力")] + c.base[b("気力")] + c.base[b("性耐性")] * 10,
        c.maxbase[b("体力")] + c.maxbase[b("気力")] + c.maxbase[b("性耐性")] * 10,
    )
    local = div(local * (300 - rate), 200)
    return limit(local, 500, 99999)  # :46


def com74(ctx: Ctx) -> ComGen:
    """`COMF74.ERB@COM74`:2–85 ＳＰフルバースト。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    print_distance(ctx)
    out.printl()
    if _fatigue_limit(ctx, "ＳＰフルバースト"):
        return 0
    v[0] = 2  # :16
    st.tflag[4] = 0
    v[6] = -500  # :20 全ゲージ消費
    v[3] = 0  # :22 EX：攻防を解除
    out.set_bold(True)
    out.printl("SPフルバースト")
    out.set_bold(False)
    run_chinobun(ctx, "MESSAGE_BATTLE_CHARA_SP_FBURST")  # :29（口上呼び出しはコメントアウト：MESSAGE_BATTLE.ERB:1064–1068）
    local = sp_full_burst_damage(ctx)
    st.flag[13] -= local  # :48
    out.set_bold(True)
    _print_enemy_name(ctx)
    out.printl(f"に{local}のダメージを与えた！")
    if st.flag[13] <= 0:  # :58–59 トドメならデメリットなし
        st.tflag[99] = 0
    else:
        st.tflag[99] += min(div((1000 + v[5]) * (100 + c.ex[99] * 2), 10000), 15) + st.rng.rand(2)  # :62
        l0 = div(c.base[0], 3)  # :66–70
        l1 = div(c.base[1], 3)
        c.base[0] -= l0
        c.base[1] -= l1
        out.printl(f"体力を{l0}、気力を{l1}消費した！")
    out.printw()
    out.set_bold(False)
    add_battle_situation(st, "EX不可")  # :76
    return 1
    yield  # pragma: no cover


def run_com(ctx: Ctx, n: int) -> ComGen:
    """`@COM{n}`（Process.SystemProc.cs@endEventCom:414–420 が COM{SELECTCOM} を呼ぶ）。"""
    if n in (0, 201, 202, 203):
        return (yield from com0(ctx))
    if n in (1, 2, 3):
        return (yield from com_attack(ctx, n))
    if n == 4:
        return (yield from com4(ctx))
    if n == 5:
        return (yield from com5(ctx))
    if n == 99:
        return (yield from com99(ctx))
    if n == 6:
        return (yield from com6(ctx))
    if n == 7:
        return (yield from com7(ctx))
    if n == 69:
        return (yield from com69(ctx))
    if n == 16:
        return (yield from com16(ctx))
    if n == 17:
        return (yield from com17(ctx))
    if n in (71, 72):
        return (yield from com_ex_gauge(ctx, n))
    if n == 70:
        return (yield from com70(ctx))
    if n == 73:
        return (yield from com73(ctx))
    if n == 74:
        return (yield from com74(ctx))
    from .restraint import RESTRAINT_COMS

    if n in RESTRAINT_COMS:
        return (yield from RESTRAINT_COMS[n](ctx))
    name = ctx.data.names["TRAIN"].get(n, str(n))
    # DEVIATION: 未移植のコマンド（S16 時点で 47 説得する〔悪堕ちキャラ戦〕のみ）は
    # 実行せずに停止する（deviations.md「未移植の戦闘分岐は停止」）
    raise NotImplementedError(f"戦闘コマンド「{name}」（COM{n}）は未移植")
