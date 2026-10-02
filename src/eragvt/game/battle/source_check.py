"""`ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:2–1326：コマンド実行後の処理（勝敗・敵の行動・時間切れ）。

路徑相對 `source/earGVP/ERB/`。`BEGIN AFTERTRAIN` は `BeginAfterTrain` 例外で表す。
"""

from __future__ import annotations

from collections.abc import Generator

from ..action import Ctx, config_check_maniac, kojo_root, print_callname, print_transcallname
from ..chara_common import is_male
from ..era import div
from ..opening import game_option
from ...state.constants import GameOption
from ..tentacle import enemy_type_check, get_lastboss_phase
from .func import state_change_kizetu
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
    BeginTurnend,
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
    msg_other,
    print_enemy_prefix,
    run_chinobun,
    unlock_achievement,
)
from .enemy import enemy_action, select_enemy_action, select_tentacle_action
from .palam import palam_cal


def _fatigue_line(ctx: Ctx) -> None:
    """疲労の蓄積表示（:17–21 等）。RESULTS = {TFLAG:99} を TOFULL（全角化）。"""
    st = ctx.state
    full = str(st.tflag[99]).translate(str.maketrans("0123456789-", "０１２３４５６７８９－"))
    ctx.out.printl(f"{print_callname(st, st.target)}の身体の底に疲労が蓄積した……（＋{full}）")


def source_check(ctx: Ctx) -> Generator[None, int, None]:
    """`@SOURCE_CHECK`。敵の行動（拘束中の AUTO_V_DEFENCE）に INPUT があるのでジェネレータ。"""
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
        _acttentaclecloth(ctx)
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
    _abareru(ctx)  # :730–802
    if st.tflag[1] == 1:  # :806–830
        if v[12] & KYOUKOUSOKU:
            v[12] -= KYOUKOUSOKU
        st.tflag[1] = 0
        st.tflag[16] = -1
        st.tflag[17] = -1
        st.tflag[20] = -1
        print_enemy_prefix(ctx)  # :815–819
        out.printl("は体勢を立て直している・・・")
        out.printl()
        if enemy_type_check(st, "AKUOTI"):  # :822–826
            select_enemy_action(ctx)
        else:
            select_tentacle_action(ctx)
        palam_cal(ctx, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    else:
        yield from enemy_action(ctx)
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
        if cancel_lose > 0:  # :963–965
            state_change_kizetu(ctx, 100)
        else:
            _battle_lose(ctx)
    # :1104–1131 時間切れ
    if c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0 and cancel_lose > 0:
        state_change_kizetu(ctx, 100)  # :1106
        st.tflag[0] -= 1  # :1108
    elif (st.temp.turn_limit != -1 and st.tflag[0] >= st.temp.turn_limit) or (st.flag[73] > 0 and v[0] != 0):
        _timeup(ctx)
    st.tflag[18] = 0  # :1135
    # :1139–1143 オート振り解き
    if config_check_balance(st, 2) > 0:
        _auto_untangle(ctx)
    else:
        st.tflag[22] = 1
    _hatujou_to_hairan(ctx)
    # :1151–1161 素股焦らしの次ターン行動指定（`SELECTCOM == 103 && TFLAG:17 < 0 && RAND:100 < 95`：短絡）
    if st.temp.selectcom == 103 and st.tflag[17] < 0 and st.rng.rand(100) < 95:
        from .core import LASTBOSS_NAMES
        from .sexcom import boss_reaction_ref, lastboss_reaction_ref

        if enemy_type_check(st, "MOB") == 1 or enemy_type_check(st, "CITIZEN") == 1:
            raise NotImplementedError("雑魚敵の REACTION_REF は未移植")
        if get_lastboss_phase(st) >= 1:  # :1154–1155（ENEMY_TYPE_CHECK ではなく GET_LASTBOSS_PHASE_F：S27）
            # ラスボス出現後の悪堕ちキャラ戦（FLAG:11 = 0）は TENTACLE_LASTBOSS_0_REACTION_REF が無く不発 → 下と同じく共用 RESULT:0
            r = lastboss_reaction_ref(ctx, st.flag[11], 1) if st.flag[11] in LASTBOSS_NAMES else st.result[0]
        elif st.flag[11] in range(1, 8):
            r = boss_reaction_ref(ctx, st.flag[11], 1)
        else:
            # S22：悪堕ちキャラ戦（FLAG:11 = 0：ACTION.ERB:38）は TENTACLE_BOSS_0_REACTION_REF が無く TRYCALLFORM 不発
            # （Instraction.Child.cs:2310–2317）→ :1159 の RESULT は直前の CALL HATUJOU_TO_HAIRAN（:1147）の RETURN 0
            # （SUBEVENT_BATTLEE.ERB:515–527。RETURN 1 の経路は未移植で停止）＝共用 RESULT:0。
            r = st.result[0]
        if r >= 0:
            st.tflag[17] = r
    _state_turnend(ctx)
    # :1303–1310 発情による敗北
    if c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0 and st.flag[13] > 0 and (
        enemy_type_check(st, "MOB") == 0 and enemy_type_check(st, "CITIZEN") == 0
    ):
        if cancel_lose == 0:  # :1304–1305 GOTO BATTLE_LOSE
            _battle_lose(ctx)
        state_change_kizetu(ctx, 100)  # :1308
    # :1313–1318
    if st.tflag[24] > 0:
        st.tflag[24] -= 1
    else:
        st.tflag[0] += 1
    st.temp.ex_com = 0
    st.temp.sh_com = 0


def source_check_jump(ctx: Ctx) -> None:
    """`PALAM_UP.ERB`:355–356 `JUMP SOURCE_CHECK`（FLAG:13 <= 0 の搾精撃破）。JUMP 先から戻ると呼び出し元も
    即 RETURN する（reference/emuera-1824/Emuera/GameProc/Process.State.cs:370–378）。FLAG:13 <= 0 なので
    SOURCE_CHECK は必ず勝利処理（:117–436）の `BEGIN AFTERTRAIN` に達し、入力待ちには到達しない。"""
    gen = source_check(ctx)
    try:
        next(gen)
    except StopIteration:
        return
    raise RuntimeError("JUMP SOURCE_CHECK が入力待ちに到達した")


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
    if enemy_type_check(st, "BOSS") == 1 or enemy_type_check(st, "LASTBOSS") >= 1:  # :136
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
        if enemy_type_check(st, "BOSS") == 1:  # :142–165
            if st.flag[18] == st.flag[11]:
                st.flag[18] = 0
            st.flag[st.flag[11] + 300] = 0
            if game_option(st, GameOption.ENDLESS) and st.flag[11] > 0:
                raise NotImplementedError("エンドレスモードのボス撃破は未移植")
            if st.flag[11] > 0:
                st.flag.set_bit(100, st.flag[11] - 1, False)
            # :165 TRYCALL SUPART_BLOOD（返り血）
            _supart_blood(ctx)
        elif enemy_type_check(st, "LASTBOSS") == 1 and get_lastboss_phase(st) >= 1:  # :167–193 ラスボス（Ｋ）／裏ボス撃破（S27）
            _victory_lastboss(ctx)
        if c.base[0] == c.maxbase[0] and c.base[1] == c.maxbase[1] and st.tflag[0] >= 10:  # :198–200
            unlock_achievement(ctx, 266, "パーフェクション")
        # :202 AFTER_KILLED_BOSS（COMMON_TENTACLE_DATA.ERB:446–449）
        from ..opening import research_quota

        st.flag[49] = 1
        research_quota(st)
        _rescue_captives(ctx)  # :204–262
        if st.flag[100] == 0 and st.flag[101] == 0:  # :266–308
            _all_bosses_cleared(ctx)
    elif enemy_type_check(st, "AKUOTI") == 1:
        _victory_akuoti(ctx)
    elif enemy_type_check(st, "MOB") == 1:
        raise NotImplementedError("雑魚戦の勝利は未移植（雑魚戦システムは基本セットで OFF）")
    raise BeginAfterTrain()


def _victory_lastboss(ctx: Ctx) -> None:
    """:167–193 ラスボス（Ｋ）撃破時のフラグ処理（S27）。実績 270 は GLOBAL のみ（deviations.md「全域資料」）。"""
    st = ctx.state
    f = st.flag
    if f[18] == f[11]:  # :169–170
        f[18] = 0
    f[400 + f[11]] = 0  # :173
    if f[854] > 0 and game_option(st, GameOption.HARDCORE) and f[101] == 1:  # :176–180 周回＆HARDCORE：裏ボス出現準備
        f[4] += 1
        f[1] += 5
        f[21] = 1
    elif f[101] == 2:  # :182–185 裏ボス撃破
        f[64] = -1
        unlock_achievement(ctx, 270, "とびっきりの最強対最強")
    else:  # :186–188
        f[64] = -1
    if f[11] > 0:  # :192–193
        f.set_bit(101, f[11] - 1, False)


def _all_bosses_cleared(ctx: Ctx) -> None:
    """:265–308 ボス全滅かつラスボス不在：ラスボス（裏ボス）出現、または完全殲滅 → `BEGIN TURNEND`（S27）。

    完全殲滅は @EVENTEND（BATTLE_TRAIN_AFTER.ERB）を通らずに @EVENTTURNEND へ行く（原作どおり：経験・報酬・FLAG:700 = 0 等なし）。
    :283–304 の実績（260／261／259／265）は GLOBAL のみ（deviations.md「全域資料」）：判定の副作用は無いので省略。"""
    st, out, data = ctx.state, ctx.out, ctx.data
    f = st.flag
    if f[64] != -1:  # :268
        if f[854] > 0 and game_option(st, GameOption.HARDCORE) and enemy_type_check(st, "LASTBOSS") == 2:  # :270–272
            f[101] = 2
            _msg_lastbossappear_2(ctx)
        elif enemy_type_check(st, "LASTBOSS") == 0:  # :274–276
            f[101] = 1
            # MESSAGE_BATTLE_END_LASTBOSSAPPEAR（地の文/MESSAGE_BATTLE.ERB:1664–1670）
            out.printl()
            out.printl(f"全ての{data.str_defaults.get(2502, '')}を殲滅しました！")
            out.printl(f"{data.str_defaults.get(2503, '')}が出現しました！")
            kojo_root(ctx, "BATTLE_END_LASTBOSSAPPEAR")
            out.printw()
        return
    # MESSAGE_BATTLE_END_PERFECT（MESSAGE_BATTLE.ERB:1673–1679）
    out.printl()
    out.printl(f"全ての{data.str_defaults.get(2500, '')}を完全殲滅しました！！")
    out.printl()
    kojo_root(ctx, "BATTLE_END_PERFECT")
    out.printw()
    raise BeginTurnend()  # :306


def _msg_lastbossappear_2(ctx: Ctx) -> None:
    """`MESSAGE_BATTLE_END_LASTBOSSAPPEAR_2`（MESSAGE_BATTLE.ERB:1682–1699）。"""
    st, out = ctx.state, ctx.out
    out.printl()
    out.printl(f"全ての{ctx.data.str_defaults.get(2500, '')}を完全殲滅しました！！")
    out.printl()
    for w in ("…", "……", "………"):
        out.printw(w)
    out.printl()
    out.printw("なにやら様子がおかしい……")
    out.printl()
    out.printl("突如大きな地響きが起こったかと思った次の瞬間、")
    out.printl("目の前の触手の巨大な屍体が弾け飛び、地中から無数の肉の柱が出現した！")
    out.printl("それらは互いに絡まり合い、巨大な一本の\"樹\"の形を成していく……")
    out.printw()
    out.printl("際限なく生長をつづける\"肉の樹\"は大地を砕き、ビルを倒壊させ、周囲を取り込んでいく。")
    out.printl(f"{print_transcallname(st, st.target)}は危ういところで身を避わし、何とか撤退に成功した……")
    out.printw()


def _victory_akuoti(ctx: Ctx) -> None:
    """:312–405 悪堕ちキャラに勝利。:314 で FLAG:110 = 0 にするので、以降の ENEMY_TYPE_CHECK_F("AKUOTI") は 0
    （MESSAGE_BATTLE_END_RESCUE_SENNOU は触手側の文になる：原作どおり。EVENTEND でもボス扱い：after.py）。
    MESSAGE_OTHER_* は FLAG:111 を見るのでそのまま呼ぶ。実績（UNLOCK_ACHIEVEMENT）は GLOBAL のみ。"""
    from ..action import config_check_prison, kojo_root_full

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    f111 = st.flag[111]
    e = st.charas[f111]
    st.flag[110] = 0  # :314
    run_chinobun(ctx, "MESSAGE_BATTLE_END_WIN_ENEMY", fallback=lambda: (kojo_root(ctx, "BATTLE_END_WIN_ENEMY"), out.printw()))
    msg_other(ctx, "BATTLE_END_WIN_ENEMY")  # :319
    if c.base[0] == c.maxbase[0] and c.base[1] == c.maxbase[1] and st.tflag[0] >= 10:  # :321–323
        unlock_achievement(ctx, 266, "パーフェクション")
    run_chinobun(ctx, "MESSAGE_BATTLE_END_RESCUE_ENEMY",  # :326
                 fallback=lambda: (kojo_root(ctx, "BATTLE_END_RESCUE_ENEMY"), out.printw()))
    l3 = e.cflag[0]  # :330 2＝洗脳 3＝悪堕ち
    if config_check_prison(st, 11) == 1 and l3 == 3:  # :333–334 悪堕ちキャラが正気に返らないオプション
        if not ctx.narration.run_function(ctx, "MESSAGE_OTHER_BATTLE_END_AKUOTI_NO_RESCUE", []):
            # MESSAGE_OTHER.ERB:714–721（SETCOLORBYNAME は catalog 外なので Python で同じ本文：Fuchsia = #FF00FF）
            out.set_bold(True)
            out.set_color("#FF00FF")
            out.printl(f"しかし周囲の蠢く触手が{print_transcallname(st, f111)}を素早く包み込み、そのまま連れ去ってしまった…！")
            out.set_bold(False)
            out.reset_color()
            out.printl()
        return
    e.cflag[0] = -1  # :336–344
    for k in (20, 21, 30, 31):
        e.cflag[k] = 0
    e.base[0] = 1
    e.base[1] = 1
    e.base[2] = 1
    unlock_achievement(ctx, 272, "正気に戻りなさい！")
    run_chinobun(ctx, "MESSAGE_OTHER_BATTLE_END_RESCUED_ENEMY",  # :347（MESSAGE_OTHER.ERB:706–711）
                 fallback=lambda: kojo_root_full(ctx, e.cflag[6], "OTHER_BATTLE_END_RESCUED_ENEMY"))
    if l3 != 3:
        return
    # :350–404 悪堕ちキャラに洗脳／幽閉されていたキャラの連鎖救出（CFLAG:21 = 悪堕ちキャラの固有番号 CFLAG:240）
    for state_no, msg, other, code, ach in (
        (2, "MESSAGE_BATTLE_END_RESCUE_SENNOU", "MESSAGE_OTHER_BATTLE_END_RESCUED_SENNOU", "BATTLE_END_RESCUE_SENNOU",
         (273, "わたくしは何を…？")),
        (1, "MESSAGE_BATTLE_END_RESCUE_AKUOTI", "MESSAGE_OTHER_BATTLE_END_RESCUED", "BATTLE_END_RESCUE_AKUOTI",
         (271, "いま助けるわ！")),
    ):
        shown = 0  # LOCAL:1
        for i in range(st.charanum):
            if i == 0:  # MASTER
                continue
            o = st.charas[i]
            if o.cflag[20] == 2 and o.cflag[21] == e.cflag[240] and o.cflag[0] == state_no:
                unlock_achievement(ctx, *ach)
                if shown == 0:
                    run_chinobun(ctx, msg, fallback=lambda cd=code: (kojo_root(ctx, cd), out.printw()))
                o.cflag[0] = -1
                for k in (20, 21, 30, 31):
                    o.cflag[k] = 0
                o.cflag[100] = 103  # :366／:398
                o.base[0] = 1
                o.base[1] = 1
                o.base[2] = 1
                o.cflag[220] = 0
                saved = st.target
                st.target = i
                run_chinobun(ctx, other, fallback=lambda: kojo_root_full(ctx, e.cflag[6], other[len("MESSAGE_"):]))
                st.target = saved
                shown = 1


def _rescue_captives(ctx: Ctx) -> None:
    """`BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:203–262：撃破したボス（FLAG:10／FLAG:11）に洗脳・幽閉されていたキャラの救出。

    実績（UNLOCK_ACHIEVEMENT 273／271）は GLOBAL のみ（deviations.md「全域資料」）。地の文は catalog。
    :214／:245 は救出状態（状態_救出直後 = -1：CSV定数定義/CFLAG.ERH:13）にするだけで、AFTER_RESCUED は
    ターン終了時の RECALC_PARTYMEMBER（SHOP_TURNEND.ERB:235–244）が行う。
    """
    from .core import run_chinobun

    st = ctx.state
    for state_no, msg, other in ((2, "MESSAGE_BATTLE_END_RESCUE_SENNOU", "MESSAGE_OTHER_BATTLE_END_RESCUED_SENNOU"),
                                 (1, "MESSAGE_BATTLE_END_RESCUE", "MESSAGE_OTHER_BATTLE_END_RESCUED")):
        shown = 0  # LOCAL:1
        for i in range(st.charanum):
            if i == 0:  # MASTER
                continue
            o = st.charas[i]
            if o.cflag[0] == state_no and o.cflag[20] == st.flag[10] and o.cflag[21] == st.flag[11]:
                if shown == 0:
                    run_chinobun(ctx, msg)
                o.cflag[0] = -1
                o.cflag[20] = 0
                o.cflag[21] = 0
                o.cflag[30] = 0
                o.cflag[31] = 0
                o.base[0] = 1  # 体力
                o.base[1] = 1  # 気力
                o.base[2] = 1  # 性耐性（:222–223 は 2 回代入）
                o.cflag[220] = 0
                saved = st.target
                st.target = i
                run_chinobun(ctx, other)
                st.target = saved
                shown = 1


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
    """:969–1095 `$BATTLE_LOSE` 以降（敗北 → 幽閉：CFLAG:0 = 1）。最後に `BEGIN AFTERTRAIN`。"""
    from ..action import config_check_prison
    from .core import is_hole, run_chinobun

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    name = print_transcallname(st, st.target)
    akuoti = enemy_type_check(st, "AKUOTI") == 1
    out.printw()  # :971
    st.tflag[98] = 2  # :973
    out.printl()
    out.print("戦闘結果：敗北 -")
    if not akuoti:  # :977–982
        tentacle_access(ctx, "NAME")
        out.printl("の殲滅失敗")
    else:
        out.printl(f"{print_transcallname(st, st.flag[111])}の解放失敗")
    out.printl()
    if t(ctx, c, "主観視点") > 0:
        out.printl(f"{name}は力尽きてしまった・・・")
    else:
        out.printl(f"{name}は力尽きた")
    out.printl()
    if not game_option(st, GameOption.ENDLESS):  # :997–998
        st.day[1] += div(c.abl[ctx.data.index_of("ABL", "レベル")], 2) + 7
    if config_check_maniac(st, 10) == 1:  # :1001–1010
        progress = div(c.cflag[32], 10000000000000000)  # CHARA_TATTOO.ERB@TATTOO_ACCESS "PROGRESS_VAR":171–172
        if progress:
            local = min(progress, 75)
            c.cflag[30] = div(_check_contamination(ctx) * local, 100)
    else:
        c.cflag[30] = 0
    exp_idx = ctx.data.index_of("EXP", "幽閉経験")
    abn_idx = ctx.data.index_of("EXP", "異常経験")
    if not is_hole(ctx, st.target) and t(ctx, c, "変身時ＴＳ") < 1 and config_check_prison(st, 0) == 0:  # :1013–1029
        c.cflag[0] = 9
        c.cflag[20] = st.flag[10]
        c.cflag[21] = st.flag[11]
        out.printl(f"オトコである{name}はそのままトドメを刺され、")
        out.printl(f"{ctx.data.str_defaults.get(2500, '')}に取り込まれていってしまった・・・")
        out.printw()
        out.printw(f"{name}はロストしました")
    elif st.flag[110] == 0:  # :1031–1043
        c.cflag[0] = 1
        c.cflag[20] = st.flag[10]
        c.cflag[21] = st.flag[11]
        _msg_end_loss(ctx)
    elif st.flag[110] == 1:  # :1044–1087
        e = st.charas[st.flag[111]]
        if e.cflag[0] == 2:  # :1046–1062 洗脳キャラに敗北：ご主人様（洗脳した触手）が幽閉する
            c.cflag[0] = 1
            c.cflag[20] = e.cflag[20]
            c.cflag[21] = e.cflag[21]
            _msg_end_loss(ctx)
            msg_other(ctx, "BATTLE_END_LOSS")
        elif e.cflag[0] == 3:  # :1064–1086
            if t(ctx, e, "寄生") == 1 and config_check_maniac(st, 13) == 1:  # 寄生持ち・悪堕ち触手アリなら幽閉
                c.cflag[0] = 1
                c.cflag[20] = 2
                c.cflag[21] = e.cflag[240]
                _msg_end_loss(ctx)
                msg_other(ctx, "BATTLE_END_LOSS")
            else:  # 犯される（幽閉されない）
                _subevent_battle_raped_enemy(ctx)
                raise_after(ctx)
                return
        else:
            # どちらでもない（FLAG:111 が洗脳／悪堕ちでない：:82 の遭遇率アップで選ばれた幽閉中キャラ等）→ 何もしない
            raise_after(ctx)
            return
    else:
        raise_after(ctx)
        return
    if c.exp[exp_idx] == 0:
        c.exp[abn_idx] += 1
    c.exp[exp_idx] += 1
    if c.cflag[0] in (1, 9, 4):  # :1091–1092
        st.flag[799] -= 1
    raise BeginAfterTrain()  # :1095


def raise_after(ctx: Ctx) -> None:
    """:1091–1095 `SIF CFLAG:0 == 1 || 9 || 4 / FLAG:799 -= 1` と `BEGIN AFTERTRAIN`。"""
    st = ctx.state
    if tc(ctx).cflag[0] in (1, 9, 4):
        st.flag[799] -= 1
    raise BeginAfterTrain()


def _msg_end_loss(ctx: Ctx) -> None:
    """MESSAGE_BATTLE_END_LOSS（地の文/MESSAGE_BATTLE.ERB:1815–1863、LOSE_SITUATION を含む。状態変化なし）。
    本文＋:1860 KOJO_ROOT＋:1861 FORCEWAIT。悪堕ちキャラ戦は :1851–1855 の文。"""
    out = ctx.out
    run_chinobun(ctx, "MESSAGE_BATTLE_END_LOSS", fallback=lambda: (kojo_root(ctx, "BATTLE_END_LOSS"), out.wait()))


def _subevent_battle_raped_enemy(ctx: Ctx) -> None:
    """`SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_RAPED_ENEMY`:24–51：悪堕ちキャラに敗北して犯される（幽閉されない）。"""
    from ..action import kojo_root_full

    st = ctx.state
    c = tc(ctx)
    loc = [0] * 12
    loc[8] = 2000  # 屈服
    loc[9] = 2000  # 恥情
    e = st.charas[st.flag[111]]
    run_chinobun(ctx, "MESSAGE_OTHER_SUBEVENT_BATTLE_RAPE_ENEMY",  # MESSAGE_OTHER.ERB:1804–1809
                 fallback=lambda: kojo_root_full(ctx, e.cflag[6], "OTHER_SUBEVENT_BATTLE_RAPE_ENEMY"))
    run_chinobun(ctx, "MESSAGE_SUBEVENT_BATTLE_RAPED_ENEMY",  # MESSAGE_SUBEVENT.ERB:5–9
                 fallback=lambda: kojo_root(ctx, "SUBEVENT_BATTLE_RAPED_ENEMY"))
    c.exp[ctx.data.index_of("EXP", "被姦経験")] += 1
    c.nowex.clear()  # SUBEVENT_BATTLE_PRECALCRESET:20 `VARSET NOWEX, 0`
    palam_cal(ctx, *loc)


def _check_contamination(ctx: Ctx) -> int:
    """`PRISON.ERB@CHECK_CONTAMINATION`:430–443（`eragvt.game.prison.event.check_contamination`）。"""
    from ..prison.event import check_contamination

    return check_contamination(ctx)


def _abareru(ctx: Ctx) -> None:
    """:730–802 暴れるの結果（体勢：暴れる防御／失敗／クリティカル）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    out = ctx.out
    name = print_transcallname(st, st.target)
    if v[2] == P_ABARE_GUARD:
        out.set_bold(True)
        out.printl("暴れる抵抗判定：成功")
        out.set_bold(False)
        out.print("拘束を振り解けなかったものの、")
        print_enemy_prefix(ctx)  # :735–739
        out.printl(f"は{name}の抵抗に虚を突かれ、体勢を崩している！")
        out.printw()
        st.tflag[1] = 1
    elif v[2] == P_ABARE_FAIL:
        out.set_bold(True)
        out.printl("暴れる抵抗判定：失敗")
        out.set_bold(False)
        rand = st.rng.rand
        if enemy_type_check(st, "BOSS") == 1 or enemy_type_check(st, "LASTBOSS") == 1:  # :750–769
            if rand(7) == 0:
                if t(ctx, c, "主観視点") > 0:
                    out.printl(f"ガッチリ巻き付いた触手はびくともせず、{name}は己の無力を突き付けられた・・・")
                else:
                    out.printl(f"ガッチリ巻き付いた触手はびくともせず、{name}は己の無力に唇を噛み占めた・・・")
            elif rand(6) == 0:
                out.printl(f"触手を引き離そうとする{name}だが、ギリギリのところで力負けしてしまった・・・")
            elif rand(5) == 0:
                out.printl(f"絡み付いた触手を引き離そうとする{name}だが、数が多すぎてきりがない・・・")
            else:
                _abare_fail_common(ctx, name)
        else:
            _abare_fail_common(ctx, name)
        out.printw()
    elif v[2] == P_ABARE_CRIT:
        out.set_bold(True)
        out.printl("暴れる抵抗判定：クリティカル")
        out.set_bold(False)
        print_enemy_prefix(ctx)  # :786–790
        out.printl(f"が思わぬ反撃に怯んだ隙に、{name}は拘束を抜け出した！")
        out.printw()
        v[0] = 2
        st.tflag[4] = 0
        st.tflag[1] = 1
        v[8] = 1


def _abare_fail_common(ctx: Ctx, name: str) -> None:
    """:761–768／:771–779 の 4 択（RAND:4 → RAND:3 → RAND:2 の順に引く）。"""
    rand = ctx.state.rng.rand
    out = ctx.out
    if rand(4) == 0:
        out.printl(f"抵抗するも、{name}は手足を抑え込まれて身動きできなくなってしまった・・・")
    elif rand(3) == 0:
        out.printl(f"{name}は必死に抵抗するが、強引に組み伏せられてしまった・・・")
    elif rand(2) == 0:
        out.printl(f"{name}は強く締め上げられて、あまりの苦痛に思わず隙を晒してしまった・・・")
    else:
        out.printl(f"{name}は突然の愛撫に不意を突かれて、抵抗する力を弱めてしまった・・・")


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
    print_enemy_prefix(ctx)  # :1879–1883
    out.print("は")
    if c.tcvarn[0] == 0:
        out.print(f"{print_transcallname(st, st.target)}を離し、")
    if enemy_type_check(st, "LASTBOSS") >= 1 and st.flag[11] == 2:  # :1887–1888
        out.printl("地響きと共に姿を消してしまった・・・")
    elif st.flag[45] == 0:
        out.printl("大きく後退してそのまま逃げ出してしまった・・・")
    else:
        out.printl("大きく後退してそのまま姿を消した・・・")
    out.printl()
    out.print("戦闘結果：タイムアップ - ")
    # :1898 は無条件の TENTACLE_ACCESS "NAME"（悪堕ちキャラ戦では FLAG:11 = 0 のエラー文字列：core.tentacle_access）
    tentacle_access(ctx, "NAME")
    out.printl("の殲滅失敗")
    out.printl()
    kojo_root(ctx, "BATTLE_END_TIMEUP")
    out.printw()
    if enemy_type_check(st, "AKUOTI") == 1:  # BATTLE_COM_AFTER.ERB:1122–1124
        msg_other(ctx, "BATTLE_END_TIMEUP")
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
        c.cflag[42] = 400  # :86 インナーが触手拘束具（CLOTH400：CLOTHDATAインナー.ERB:41–50）になる
        # :88 地の文（地の文/MESSAGE_SUBEVENT.ERB:22–48、末尾 :48 の KOJO_ROOT）
        run_chinobun(ctx, "MESSAGE_SUBEVENT_BATTLE_SETTENTACLECLOTH",
                     fallback=lambda: kojo_root(ctx, "SUBEVENT_BATTLE_SETTENTACLECLOTH"))


def _acttentaclecloth(ctx: Ctx) -> None:
    """`SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_ACTTENTACLECLOTH`:93–156（CFLAG:42 == 400 のとき毎ターン）。

    原作どおりの点：LOCAL の添字 0〜11（快Ｃ〜快Ｂ、潤滑〜恐怖）をそのまま PALAM_HOSEI_TALENT／PALAM_HOSEI_SEIKAKU の
    PALAM 番号と COMMON_PALAM の添字に使う（:130、:134、:155）→ LOCAL:4〜11 は PALAM 4〜11（潤滑〜恐怖の 10〜17 ではない）の
    補正・加算になる。触手中毒補正の判定（:142 `LCOUNT + PALAM始点 - 感覚数`）だけは 恭順・欲情・屈服（LOCAL:5／7／8）に正しく当たる。
    FOR は 0〜12（:119）だが LOCAL:12 はどこでも代入されない（静的 LOCAL、常に 0）。
    """
    from .palam import palam_hosei_pose, palam_hosei_poisoning, palam_hosei_random, palam_hosei_seitaisei, palam_hosei_talent
    from .core import seikaku_hosei_palam
    from .sexcom import sex_comex
    from ..chara_common import seikaku_check

    st, data = ctx.state, ctx.data
    c = tc(ctx)
    r = sex_comex(ctx, 0, 0, 15)  # :101 → RESULT:0〜11
    local = [div(r[i], 2) for i in range(12)] + [0]  # :102–104（LOCAL:12 は常に 0）
    if is_male(data, c):  # :105–106
        local[1] = 0
    # :109 地の文（地の文/MESSAGE_SUBEVENT.ERB:53–61、末尾 :60 KOJO_ROOT・:61 PRINTW）
    def fallback() -> None:
        kojo_root(ctx, "SUBEVENT_BATTLE_ACTTENTACLECLOTH")
        ctx.out.printw()

    run_chinobun(ctx, "MESSAGE_SUBEVENT_BATTLE_ACTTENTACLECLOTH", fallback=fallback)
    c.exp[data.index_of("EXP", "被姦経験")] += 1  # :112
    c.nowex.clear()  # :115 SUBEVENT_BATTLE_PRECALCRESET（:19–20 VARSET NOWEX, 0）
    cp = st.temp.common_palam
    for lc in range(13):  # :119–156
        v = local[lc]
        if v > 0:
            v = palam_hosei_pose(ctx, v)
            v = palam_hosei_seitaisei(ctx, v)
            v = palam_hosei_talent(ctx, lc, v)
            v = seikaku_hosei_palam(seikaku_check(data, c), lc, v)
            if lc + 10 - 4 in (11, 13, 14):  # :142 恭順・欲情・屈服
                v = palam_hosei_poisoning(ctx, v)
            v = palam_hosei_random(ctx, v)
            if v <= 0:
                v = 1
            if v > 999999 and lc >= 4:
                v = 999999
        cp[lc] += v  # :155


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
    if v[0] == 0:  # :253–299
        if st.tflag[22] > 0 or (v[12] & KYOUKOUSOKU):
            st.tflag[22] = 1
            return
        from .restraint import msg_hurihodoku, msg_hurihodoku_success
        from .hantei import act_hantei_chara_to_tentacle

        out = ctx.out
        name = print_transcallname(st, st.target)
        if act_hantei_chara_to_tentacle(ctx, "HURIHODOKU")[0] == 1:
            out.printl()
            out.set_bold(True)
            out.printl("オート振り解き")
            out.set_bold(False)
            msg_hurihodoku(ctx)
            v[0] = 2
            st.tflag[4] = 0
            msg_hurihodoku_success(ctx)
            if enemy_type_check(st, "AKUOTI") == 1:  # :276–277
                msg_other(ctx, "BATTLE_CHARA_HURIHODOKU_SUCCESS")
            v[8] = 1
            st.tflag[1] = 0
            st.tflag[16] = -1
            st.tflag[17] = -1
            st.tflag[20] = -1
            print_enemy_prefix(ctx)  # :287–291
            out.printl("は体勢を立て直している・・・")
            out.printl()
        else:
            out.printl()
            out.printl(f"{name}はがっちり拘束されて身動きできない・・・")
            out.printl()
            st.tflag[22] = 1
        return
    st.tflag[22] = 0


def _hatujou_to_hairan(ctx: Ctx) -> None:
    """`SUBEVENT_BATTLEE.ERB@HATUJOU_TO_HAIRAN`:513–585（ケモミミ族のみ）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    # :515–527 の RETURN 0 → RESULT:0 = 0（共用 RESULT。BATTLE_COM_AFTER.ERB:1159 の不発 TRYCALLFORM 後に読まれる：S22）
    st.result[0] = 0
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
    rmax = 100 - 20 * (1 if c.cflag[43] == 508 else 0)
    if v[12] & MAHI:  # :1210–1220（`(A && RAND < X) || B`：A が偽なら RAND を引かない）
        if (v[104] > 0 and st.rng.rand(rmax) < max(25 - c.cflag[99] * 5 + v[104] * 5, 15)) or v[104] == -999:
            out.printl(f"○ {name}の麻痺が治った！")
            out.printl(f"　 {name}は[麻痺]状態から回復した！")
            v[12] -= MAHI
            v[104] = 0
        else:
            out.printl(f"× {name}は身体が麻痺して敏捷性がダウンしている…")
            v[104] += 1
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
    if (v[12] & KOSHIKUDAKE) and (v[12] & KIZETU) == 0:  # :1245–1255
        if (v[106] > 1 and st.rng.rand(rmax) < 60 + v[106] * 5) or v[106] == -999:
            out.printl(f"○ {name}の脚の震えが止まった！")
            out.printl(f"　 {name}は[腰くだけ]状態から回復した！")
            v[12] -= KOSHIKUDAKE
            v[106] = 0
        else:
            out.printl(f"× {name}は脚が震えて思うように動けない…")
            v[106] += 1
    ki = percent_cal(c.base[1], c.maxbase[1])  # :1257
    if (v[12] & KOUKOTSU) and (v[12] & KIZETU) == 0:  # :1258–1270
        if (v[107] > 1 and st.rng.rand(rmax) < div(ki, 4) + 35 + v[107] * 10) or v[107] == -999:
            out.printl(f"○ {name}は気持ちを持ち直した！")
            out.printl(f"　 {name}は[恍惚]状態から回復した！")
            v[12] -= KOUKOTSU
            v[107] = 0
        else:
            out.printl(f"× {name}は絶頂の余韻で力が入らない…")
            v[107] += 1
    else:
        v[107] = 0
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
