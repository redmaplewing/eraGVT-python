"""`ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:2–1326：コマンド実行後の処理（勝敗・敵の行動・時間切れ）。

路徑相對 `source/earGVP/ERB/`。`BEGIN AFTERTRAIN` は `BeginAfterTrain` 例外で表す。
"""

from __future__ import annotations

from ..action import Ctx, config_check_maniac, kojo_root, print_callname, print_transcallname
from ..chara_common import is_male
from ..era import div
from ..opening import game_option
from ...state.constants import GameOption
from ..tentacle import enemy_type_check
from .cloth import cloth_battle_damage, cloth_battle_hosei, cloth_check, refresh_cloth_data
from .core import (
    BETOBETO,
    HATUJOU,
    KIZETU,
    KOSHIKUDAKE,
    KOUKOTSU,
    KYOUKOUSOKU,
    MAHI,
    P_ABARE_CRIT,
    P_ABARE_FAIL,
    P_ABARE_GUARD,
    P_EX_HANGEKI,
    P_GUARD,
    P_HANGEKI,
    P_HANGEKI_OK,
    P_NORMAL,
    BeginAfterTrain,
    abl,
    config_check_balance,
    get_battle_situation,
    is_girly,
    is_penis,
    percent_cal,
    shinkyou_change,
    t,
    tc,
    tentacle_access,
    unlock_achievement,
)
from .enemy import enemy_action, select_tentacle_action
from .palam import palam_cal


def _fatigue_line(ctx: Ctx) -> None:
    """疲労の蓄積表示（:17–21 等）。RESULTS = {TFLAG:99} を TOFULL（全角化）。"""
    st = ctx.state
    full = str(st.tflag[99]).translate(str.maketrans("0123456789-", "０１２３４５６７８９－"))
    ctx.out.printl(f"{print_callname(st, st.target)}の身体の底に疲労が蓄積した……（＋{full}）")


def source_check(ctx: Ctx) -> None:
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    name = print_transcallname(st, st.target)
    cancel_lose = 0  # ターン内敗北キャンセル（:5–6）
    # :12–22 疲労
    if c.cflag[1] == 2:
        st.tflag[99] += 1
    elif st.tflag[99] > 0:
        c.cflag[99] += st.tflag[99]
        _fatigue_line(ctx)
        out.printw()
        st.tflag[99] = 0
    # :28–35 装備効果
    if c.cflag[43] in (506, 507, 509):
        raise NotImplementedError(f"装備 {c.cflag[43]} の効果（MISC_PATCH.ERB）は未移植")
    # :40–112 裏ボス形態変化
    if enemy_type_check(st, "LASTBOSS") >= 2:
        raise NotImplementedError("裏ボスの形態変化は未移植")
    # :117–436 勝利
    if st.flag[13] <= 0:
        _victory(ctx)
    if st.flag[700] == 0:  # :439–440
        return
    st.tflag[13] = st.tflag[11]  # :443
    _motion_palam(ctx)
    # :680–681 心境の自動変化
    if st.rng.rand(100) < v[11] * v[11] and (v[12] & KIZETU) == 0:
        shinkyou_change(ctx, "NORMAL")
    # :685–693 べとべとの持続（RAND は短絡評価の最後）
    if (v[12] & BETOBETO) and v[2] in (P_GUARD, P_ABARE_GUARD, P_ABARE_FAIL, P_ABARE_CRIT) and st.rng.rand(100) < max(
        75 - c.cflag[99] * 3, 25
    ):
        out.printl(f"○ {name}は纏わり付いた粘液を振り払った！")
        out.printl(f"　 {name}は[べとべと]状態から回復した！")
        out.printw()
        v[12] -= BETOBETO
    elif (v[12] & BETOBETO) and v[2] == P_GUARD:
        out.printl(f"× {name}は纏わり付いた粘液を振り払うのに失敗した！")
        out.printw()
    # :696 SUBEVENT_BATTLE_ACTTENTACLECLOTH（CFLAG:42 == 400 のときのみ）
    if c.cflag[42] == 400:
        raise NotImplementedError("触手拘束具による被姦（SUBEVENT_BATTLE_ACTTENTACLECLOTH）は S06")
    # :699 SUBEVENT_BATTLE_ACTTENTACLESUIT（触手服 199 のときのみ）
    if (c.cflag[1] == 0 and c.cflag[40] == 199) or (c.cflag[1] > 0 and c.cflag[41] == 199):
        raise NotImplementedError("触手服の処理（SUBEVENT_BATTLE_ACTTENTACLESUIT）は未移植")
    if v[0] != 0:  # :702–703
        st.tflag[20] = -999
    refresh_cloth_data(ctx)
    if st.tflag[24] > 0:  # :710–711
        st.tflag[1] = 1
    # :717–723 敵の行動
    out.printl()
    out.set_bold(True)
    out.set_color((150, 0, 255))
    out.printl("********** 敵の行動 **********")
    out.reset_color()
    out.set_bold(False)
    out.printl()
    if not v.get_bit(216, 1):
        st.tflag.set_bit(11, 3, False)
    if v[2] in (P_ABARE_GUARD, P_ABARE_FAIL, P_ABARE_CRIT):
        raise NotImplementedError("暴れる（拘束中）の追加処理は S06")
    if st.tflag[1] == 1:  # :806–830
        if v[12] & KYOUKOUSOKU:
            v[12] -= KYOUKOUSOKU
        st.tflag[1] = 0
        st.tflag[16] = -1
        st.tflag[17] = -1
        st.tflag[20] = -1
        if enemy_type_check(st, "AKUOTI") == 0:
            tentacle_access(ctx, "NAME")
        else:
            raise NotImplementedError("悪堕ちキャラ戦は未移植")
        out.printl("は体勢を立て直している・・・")
        out.printl()
        select_tentacle_action(ctx)
        palam_cal(ctx, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    else:
        enemy_action(ctx)
        if v[2] in (P_HANGEKI, P_EX_HANGEKI, P_HANGEKI_OK):
            v[2] = P_NORMAL
    if v[12] & KYOUKOUSOKU:
        cancel_lose = 1
    if st.tflag[23] == 100:
        cancel_lose = 1
    # :850–1098 敗北
    if st.flag[73] > 0 and c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0 and v[0] == 0:
        raise NotImplementedError("クズ市民戦の敗北（監禁）は未移植")
    lost = c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0 and st.flag[13] > 0 and (
        enemy_type_check(st, "MOB") == 0 and enemy_type_check(st, "CITIZEN") == 0
    )
    if lost:
        if enemy_type_check(st, "BOSS") == 1 and st.flag[11] == 6 and 0 <= st.tflag[23] < 100:
            st.tflag[23] = 100
            cancel_lose = 1
        if cancel_lose > 0:
            raise NotImplementedError("強拘束／丸飲み準備中の敗北遅延（STATE_CHANGE_KIZETU 以降）は S06")
        _battle_lose(ctx)
    # :1104–1131 時間切れ
    if c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0 and cancel_lose > 0:
        raise NotImplementedError("強拘束中の時間切れ遅延は S06")
    if (st.temp.turn_limit != -1 and st.tflag[0] >= st.temp.turn_limit) or (st.flag[73] > 0 and v[0] != 0):
        _timeup(ctx)
    st.tflag[18] = 0  # :1135
    # :1139–1143 オート振り解き
    if config_check_balance(st, 2) > 0:
        _auto_untangle(ctx)
    else:
        st.tflag[22] = 1
    _hatujou_to_hairan(ctx)
    if st.temp.selectcom == 103:
        raise NotImplementedError("素股焦らしの次ターン行動指定は S06")
    _state_turnend(ctx)
    # :1303–1310 発情による敗北
    if c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0 and st.flag[13] > 0 and (
        enemy_type_check(st, "MOB") == 0 and enemy_type_check(st, "CITIZEN") == 0
    ):
        if cancel_lose == 0:
            _battle_lose(ctx)
        raise NotImplementedError("強拘束中の敗北遅延は S06")
    # :1313–1318
    if st.tflag[24] > 0:
        st.tflag[24] -= 1
    else:
        st.tflag[0] += 1
    st.temp.ex_com = 0
    st.temp.sh_com = 0


def _victory(ctx: Ctx) -> None:
    """:117–436 勝利。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if enemy_type_check(st, "MOB") == 0 and enemy_type_check(st, "CITIZEN") == 0:
        from ..tentacle import BOSS_ERB_NUM

        for i in range(1, BOSS_ERB_NUM + 1):
            st.flag[300 + i] -= st.rng.rand(11) + 50
            if st.flag[300 + i] < 0:
                st.flag[300 + i] = 0
    st.tflag[98] = 1
    if enemy_type_check(st, "BOSS") == 1:
        # MESSAGE_BATTLE_END_WIN（地の文/MESSAGE_BATTLE.ERB:1634–1652）
        tentacle_access(ctx, "NAME")
        out.printl("は力尽きた！")
        out.printl()
        out.print("戦闘結果：勝利 - ")
        tentacle_access(ctx, "NAME")
        out.printl("の殲滅完了！")
        kojo_root(ctx, "BATTLE_END_WIN")
        # :1648 `CONFIG_CHECK_MANIAC_F(14)==1 && RAND(1) < 1`（RAND(1) は常に 0）
        if config_check_maniac(st, 14) == 1 and st.rng.rand(1) < 1:
            _rescue_deadnum(ctx)
        out.printw()
        if st.flag[18] == st.flag[11]:
            st.flag[18] = 0
        st.flag[st.flag[11] + 300] = 0
        if game_option(st, GameOption.ENDLESS) and st.flag[11] > 0:
            raise NotImplementedError("エンドレスモードのボス撃破は未移植")
        if st.flag[11] > 0:
            st.flag.set_bit(100, st.flag[11] - 1, False)
        # :165 TRYCALL SUPART_BLOOD（返り血）
        _supart_blood(ctx)
        if c.base[0] == c.maxbase[0] and c.base[1] == c.maxbase[1] and st.tflag[0] >= 10:
            unlock_achievement(ctx, 266, "パーフェクション")
        # :202 AFTER_KILLED_BOSS（COMMON_TENTACLE_DATA.ERB:446–449）
        from ..opening import research_quota

        st.flag[49] = 1
        research_quota(st)
        for i in range(1, st.charanum):
            o = st.charas[i]
            if o.cflag[0] in (1, 2) and o.cflag[20] == st.flag[10] and o.cflag[21] == st.flag[11]:
                raise NotImplementedError("撃破したボスに捕らわれていたキャラの救出は未移植")
        if st.flag[100] == 0 and st.flag[101] == 0:
            raise NotImplementedError("ボス全滅（ラスボス出現）は未移植")
    elif enemy_type_check(st, "LASTBOSS") >= 1 or enemy_type_check(st, "AKUOTI") == 1:
        raise NotImplementedError("ラスボス／悪堕ちキャラへの勝利は未移植")
    elif enemy_type_check(st, "MOB") == 1:
        raise NotImplementedError("雑魚戦の勝利は未移植（雑魚戦システムは基本セットで OFF）")
    raise BeginAfterTrain()


def _rescue_deadnum(ctx: Ctx) -> None:
    """`MESSAGE_BATTLE_END_RESCUE_DEADNUM`（MESSAGE_BATTLE.ERB:1739–1750）：取り込まれロストしたキャラの発見。"""
    from .core import add_randchoose, choicecount, clear_randchoose

    st = ctx.state
    clear_randchoose(st)
    for i in range(1, st.charanum):
        o = st.charas[i]
        if o.cflag[0] == 9 and t(ctx, o, "苗床化"):
            add_randchoose(st, i)
    if choicecount(st) == 0:
        return
    raise NotImplementedError("ロストキャラの発見（MESSAGE_BATTLE_END_RESCUE_DEADNUM）は未移植")


def _supart_blood(ctx: Ctx) -> None:
    """`ゲーム内_戦闘処理/SUPART_BLOOD.ERB@SUPART_BLOOD`:1–（CONFIG_CHECK_BALANCE_F(4)：基本セットで OFF）。"""
    if config_check_balance(ctx.state, 4) > 0 and ctx.state.flag[11] > 0:
        raise NotImplementedError("ボスの返り血（SUPART_BLOOD）は未移植")


def _motion_palam(ctx: Ctx) -> None:
    """:448–676 運動時の快感（COMMON_PALAM:0／:3）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    cp = st.temp.common_palam
    out = ctx.out
    cl_no_inner = st.temp.cloth[0]
    sel = st.temp.selectcom
    name = print_transcallname(st, st.target)
    l1 = 0
    if (c.cflag[1] == 0 and v[20] == -1) or (c.cflag[1] >= 1 and v[22] == -1):
        l1 |= 2
    if v[24] == -1 or (cl_no_inner > 0 and l1 > 0):
        l1 |= 1
    if c.cflag[40 if c.cflag[1] == 0 else 41] == 199:
        raise NotImplementedError("触手服の運動快感判定は未移植")
    # --- 快C ---
    ac = abl(ctx, c, "Ｃ感覚")
    if ac <= 2:
        local = 0
    elif ac <= 4:
        local = 4
    elif ac == 5:
        local = 8
    elif ac == 6:
        local = 12
    elif ac == 7:
        local = 20
    elif 8 <= ac < 12:
        local = div(ac * 2, 3) * 15
    else:
        local = div(ac * 2, 3) * 30
    if is_penis(ctx):
        local += 20
    r = cloth_battle_hosei(ctx, "ANTICUP")
    local -= r
    if r:
        local = div(local, 2)
    local = _motion_by_command(sel, local)
    cc = cloth_check(ctx, st.target)
    lust = c.palam[13]
    if is_penis(ctx):
        if (cc & 1) == 0 and (l1 & 1) == 0 and lust < 2000:
            local = div(local, 2)
        elif ((cc & 1) or (l1 & 1)) and lust < 2000:
            local *= 2
        elif (cc & 1) == 0 and (l1 & 1) == 0:
            local *= 8
        else:
            local *= 16
    elif (cc & 1) or (l1 & 1):
        local *= 6
    else:
        local *= 0
    if t(ctx, c, "淫核"):
        local = div(local * 175, 100)
    if local < 100:
        local = 0
    cp[0] += local
    # --- 快B ---
    ab = abl(ctx, c, "Ｂ感覚")
    if ab <= 2:
        local = 0
    elif ab <= 4:
        local = 5
    elif ab == 5:
        local = 10
    elif ab == 6:
        local = 20
    elif ab == 7:
        local = 40
    elif 8 <= ab < 12:
        local = div(ab * 2, 3) * 20
    else:
        local = div(ab * 2, 3) * 40
    if t(ctx, c, "母乳体質"):
        local += 5
    r = cloth_battle_hosei(ctx, "ANTIBUP")
    local -= r
    if r:
        local = div(local, 2)
    local = _motion_by_command(sel, local)
    clothed = (cc & 2) or (cc & 4) or (l1 & 2)
    if t(ctx, c, "貧乳") > 0 or is_male(ctx.data, c):
        local = local * 8 if clothed else 0
    elif t(ctx, c, "巨乳") > 0:
        local = local * 4 if clothed else local * 16
        if t(ctx, c, "巨乳") > 3:
            local *= 2
        if t(ctx, c, "巨乳") > 4:
            local *= 2
    else:
        local = local * 3 if clothed else local * 12
    if t(ctx, c, "淫乳"):
        local = div(local * 175, 100)
    if lust < 2000:
        local = div(local, 2)
    elif lust > 10000:
        local = div(local * 125, 100)
    if local < 100:
        local = 0
    cp[3] += local
    # :587–676 表示
    girly = is_girly(ctx)
    if cp[0] or (cp[3] and girly):
        out.printl()
    moving = sel in (1, 2, 3, 5, 6, 7, 16, 17)
    if cp[0] and c.base[30] == 0:
        out.print("抵抗しようともがく" if sel in (8, 9) else "激しい運動で" if moving else "ちょっとした動きでも")
        out.print(f"{name}の")
        if abl(ctx, c, "Ｃ感覚") >= 6 or t(ctx, c, "淫核"):
            out.print("開発されきった")
        if abl(ctx, c, "Ｃ感覚") >= 3 or t(ctx, c, "Ｃ敏感"):
            out.print("敏感な")
        if is_penis(ctx):
            if lust >= 2000:
                out.print("勃起")
            out.print("ペニスが")
        else:
            out.print("クリトリスが")
        out.printl("下着で擦れてしまい、" if (cloth_check(ctx, st.target) & 1) else "揺れてしまい、")
        p = cp[0]
        out.print("微かに疼いている・・・" if p < 250 else "感覚を刺激されて疼いてしまう・・・" if p < 500
                  else "快楽を感じてしまっている・・・" if p < 2000 else "強い快楽を感じてしまっている・・・")
        out.printl()
    if cp[3] and girly and c.base[33] == 0:
        out.print("抵抗しようともがく" if sel in (8, 9) else "激しい運動で" if moving else "ちょっとした動きでも")
        out.print(f"{name}の")
        if abl(ctx, c, "Ｂ感覚") >= 6 or t(ctx, c, "淫乳"):
            out.print("開発されきった")
        sensitive = abl(ctx, c, "Ｂ感覚") >= 3 or t(ctx, c, "Ｂ敏感")
        if t(ctx, c, "巨乳") > 0:
            out.print("豊満")
            out.print("で" if sensitive else "な")
        if sensitive:
            out.print("敏感な")
        out.print("乳首が" if is_male(ctx.data, c) else "胸が")
        cc2 = cloth_check(ctx, st.target)
        if (cc2 & 2) or (cc2 & 4):
            out.printl("服で擦れてしまい、")
        else:
            if t(ctx, c, "巨乳") > 0 and sel in (1, 2, 3, 5, 6, 7, 8, 9, 16, 17):
                out.print("大きく")
            out.printl("揺れてしまい、")
        p = cp[3]
        out.print("微かに疼いている……" if p < 250 else "感覚を刺激されて疼いてしまう……" if p < 500
                  else "快楽を感じてしまっている……" if p < 2000 else "強い快楽を感じてしまっている……")
        out.printl()
    if cp[0] or (cp[3] and girly):
        out.printw()


def _motion_by_command(sel: int, local: int) -> int:
    """:479–487／:539–547 直前の行動による補正。"""
    if sel in (8, 9):
        return local + 25
    if sel in (1, 5, 6, 7, 16, 17):
        return local + 15
    if sel in (2, 3):
        return local + 5
    return div(local, 8)


def _battle_lose(ctx: Ctx) -> None:
    """:969–1095 `$BATTLE_LOSE` 以降（敗北 → 幽閉）。"""
    # DEVIATION ではなく未移植：敗北後の幽閉（CFLAG:0 = 1 等）以降は PRISON 系の処理が未移植なので停止する。
    raise NotImplementedError("戦闘敗北（幽閉：BATTLE_COM_AFTER.ERB:969–1095）は未移植")


def _timeup(ctx: Ctx) -> None:
    """:1113–1130 時間切れ。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    # TRYCALL KYUSHUTU_TIMEUP_HANTEI（COMF15.ERB:63–65）：TFLAG:9 == 1 のときのみ地の文
    if st.tflag[9] == 1:
        raise NotImplementedError("救出の時間切れ（MESSAGE_KYUUSHUTU_TIMEUP）は未移植")
    if st.flag[73] > 0:
        raise NotImplementedError("クズ市民戦の時間切れは未移植")
    # MESSAGE_BATTLE_END_TIMEUP（地の文/MESSAGE_BATTLE.ERB:1873–1906）
    if get_battle_situation(st, "耐久戦"):
        out.printl("何とか襲撃を耐えきったようだ・・・")
    else:
        out.printl("どうやら戦闘が長引き過ぎた様だ")
    tentacle_access(ctx, "NAME")
    out.print("は")
    if c.tcvarn[0] == 0:
        out.print(f"{print_transcallname(st, st.target)}を離し、")
    if st.flag[45] == 0:
        out.printl("大きく後退してそのまま逃げ出してしまった・・・")
    else:
        out.printl("大きく後退してそのまま姿を消した・・・")
    out.printl()
    out.print("戦闘結果：タイムアップ - ")
    tentacle_access(ctx, "NAME")
    out.printl("の殲滅失敗")
    out.printl()
    kojo_root(ctx, "BATTLE_END_TIMEUP")
    out.printw()
    if enemy_type_check(st, "MOB") == 0 and enemy_type_check(st, "CITIZEN") == 0:
        _settentaclecloth(ctx)
    raise BeginAfterTrain()


def _settentaclecloth(ctx: Ctx) -> None:
    """`SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_SETTENTACLECLOTH`:71–89。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    cl = st.temp.cloth
    if c.cflag[42] == 400:
        return
    local = 0
    outer, outer_max = (21, 20) if c.cflag[1] == 0 else (23, 22)
    if (percent_cal(v[outer], v[outer_max]) < cl[2] or v[outer] == 0) and (
        percent_cal(v[25], v[24]) < cl[4] or v[25] == 0
    ):
        local = 1
    l1 = 35 - min((1 if st.flag[45] > 0 else 0) * 12, 12)
    # :85 `LOCAL == 1 && RAND(100) < LOCAL:1`（短絡：LOCAL が 1 のときだけ RAND を引く）
    if local == 1 and st.rng.rand(100) < l1:
        c.cflag[42] = 400
        raise NotImplementedError("触手拘束具の強制装着（MESSAGE_SUBEVENT_BATTLE_SETTENTACLECLOTH）は未移植")


def _auto_untangle(ctx: Ctx) -> None:
    """`SUBEVENT_BATTLEE.ERB@AUTO_UNTANGLE`:231–302（非拘束時は TFLAG:22 = 0 のみ）。"""
    st = ctx.state
    v = tc(ctx).tcvarn
    if v[12] & KIZETU:
        st.tflag[22] = 1
        return
    if v[12] & KOUKOTSU:
        st.tflag[22] = 1
        return
    if st.temp.selectcom == 69:
        st.tflag[22] = 1
        return
    if st.flag[73] > 0:
        st.tflag[22] = 1
        return
    if v[0] == 0:
        raise NotImplementedError("オート振り解き（拘束中）は S06")
    st.tflag[22] = 0


def _hatujou_to_hairan(ctx: Ctx) -> None:
    """`SUBEVENT_BATTLEE.ERB@HATUJOU_TO_HAIRAN`:513–585（ケモミミ族のみ）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    if t(ctx, c, "ケモミミ族") == 0:
        return
    if is_male(ctx.data, c) or t(ctx, c, "妊娠") > 0 or (v[12] & 2) or (v[12] & HATUJOU) == 0:
        return
    if st.rng.rand(100) >= 10:
        return
    raise NotImplementedError("発情による排卵（HATUJOU_TO_HAIRAN の地の文）は未移植")


def _state_turnend(ctx: Ctx) -> None:
    """:1165–1300 ターン終了時の状態異常処理。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    name = print_transcallname(st, st.target)
    if v[12] > 0 and v[12] != 2:
        out.printl()
        out.set_bold(True)
        out.printl("状態異常")
        out.set_bold(False)
    if v[12] & KYOUKOUSOKU:
        out.printl(f"× {name}は行動を制限されている…")
    if (v[12] & HATUJOU) and (v[12] & KIZETU) == 0:
        subjective = t(ctx, c, "主観視点") > 0
        if subjective:
            out.printl(f"× {name}の体は媚薬の効果で欲情してしまっている…")
        else:
            out.printl(f"× {name}は媚薬の効果で欲情している…")
        out.set_bold(True)
        local = 0
        if c.base[2] > 0:
            if c.maxbase[2] >= 300:
                local = st.rng.rand(8) + 3
            elif c.maxbase[2] >= 200:
                local = st.rng.rand(6) + 2
            else:
                local = st.rng.rand(4) + 1
            out.printl(f"　 性耐性が{local}減少した！")
            out.printl()
            c.base[2] = max(c.base[2] - local, 0)
        else:
            if c.base[0] > 0:
                local = max(div(c.base[0], 40), 40) + st.rng.rand(30)
                out.printl(f"　 体力が{local}減少した！")
                c.base[0] = max(c.base[0] - local, 0)
            if c.base[1] > 0:
                local = max(div(c.base[1], 20), 80) + st.rng.rand(60)
                out.printl(f"　 気力が{local}減少した！")
                c.base[1] = max(c.base[1] - local, 0)
        out.set_bold(False)
        c.palam[13] += local * 125
    if v[12] & MAHI:
        raise NotImplementedError("麻痺の持続判定は未移植")
    if v[12] & BETOBETO:
        out.printl(f"× {name}に粘液が纏わり付いて離れない…")
        if c.cflag[1] > 0 and (v[23] > 0 or v[25] > 0):
            out.printl(f"　 {name}の衣装が少しずつ溶かされていく！")
            local = st.rng.rand(5) + 1
            out.set_bold(True)
            out.printl(f"　 衣装に{local}の損傷を受けた！")
            out.set_bold(False)
            out.printl()
            cloth_battle_damage(ctx, local, 1)
        elif v[21] > 0 or v[25] > 0:
            out.printl(f"　 {name}の衣装が少しずつ溶かされていく！")
            local = st.rng.rand(5) + 1
            out.set_bold(True)
            out.printl(f"　 衣装に{local}の損傷を受けた！")
            out.set_bold(False)
            out.printl()
            cloth_battle_damage(ctx, local, 1)
    if (v[12] & KOSHIKUDAKE) and (v[12] & KIZETU) == 0:
        raise NotImplementedError("腰くだけの持続判定は S06")
    ki = percent_cal(c.base[1], c.maxbase[1])
    if (v[12] & KOUKOTSU) and (v[12] & KIZETU) == 0:
        raise NotImplementedError("恍惚の持続判定は S06")
    v[107] = 0
    _ = ki
    if v[12] & KIZETU:
        if c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0:
            out.printl(f"× {name}の意識は朦朧としている…" if t(ctx, c, "主観視点") > 0 else f"× {name}の意識が戻る気配はない…")
            v[101] += 1
        elif (v[101] > 0 and st.rng.rand(100 - 20 * (1 if c.cflag[43] == 508 else 0)) < max(35 - c.cflag[99] * 3 + v[101] * 10, 10)) or v[101] == -999:
            # :1280 `A && RAND < … || TCVARn:101 == -999`（左結合：(A && B) || C）
            if t(ctx, c, "主観視点") > 0:
                out.printl(f"○ {name}は意識を持ち直した！")
                out.printl(f"　 {name}は[朦朧]状態から回復した！\t")
            else:
                out.printl(f"○ {name}は意識を取り戻した！")
                out.printl(f"　 {name}は[気絶]状態から回復した！")
            v[12] -= KIZETU
            v[101] = 0
        else:
            out.printl(f"× {name}の意識は朦朧としている…" if t(ctx, c, "主観視点") > 0 else f"× {name}の意識が戻る気配はない…")
            v[101] += 1
    else:
        v[101] = 0
