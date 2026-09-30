"""戦闘終了処理：`ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND`:2–536（路徑相對 `source/earGVP/ERB/`）。

TFLAG:98 は戦闘の結果（0＝時間切れ／撤退、1＝勝利、2＝敗北）。設定箇所は BATTLE_COM_AFTER.ERB:129（勝利）、
:852／:973（敗北）のみ。
"""

from __future__ import annotations

from ...state.constants import ActionPlan, GameOption
from ..action import Ctx, Step, config_check_event, config_check_prison, get_exp, get_syuren, print_callname, print_transcallname
from ..era import div, limit, times
from ..opening import game_option
from ..shop import charanum_safe, check_gameover
from ..tentacle import enemy_type_check, tentacle_survive_num
from .ablup import ablup
from .cloth import cloth_battle_hosei, cloth_battle_sethp, refresh_cloth_data
from .core import PALAM_END, config_check_balance, get_battle_situation, is_hole, mark, percent_cal, t, tc, tentacle_level
from .encount import get_exp_battle, get_kakera, get_money, research_progress, support_heal
from .func import transform
from .ninsin import ninsin_check_after  # ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@NINSIN_CHECK_AFTER:169–190

# :13–120 刻印：(PALAM 名, MARK 名, 防止 MARK 名, 1 段目の閾値, 防止 1 あたりの加算)
_MARKS = (
    ("欲情", "快楽刻印", "快楽刻印防止", 40000, 1000),
    ("苦痛", "苦痛刻印", "苦痛刻印防止", 30000, 750),
    ("屈服", "屈服刻印", "屈服刻印防止", 20000, 500),
    ("恐怖", "恐怖刻印", "恐怖刻印防止", 20000, 500),
    ("恥情", "恥辱刻印", "恥辱刻印防止", 20000, 500),
)


def _battle_marks(ctx: Ctx) -> None:
    """:12–120。段 n（1–5）の閾値は 1 段目 × 2^(n-1)、2 段目以降は現在の刻印が n-1 であることが条件。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    for palam_name, mark_name, guard_name, base, per in _MARKS:
        p = c.palam[data.index_of("PALAM", palam_name)]
        g = mark(ctx, c, guard_name)
        cur = mark(ctx, c, mark_name)
        local = 0
        if p >= base + g * per:
            local = 1
        for n in (2, 3, 4, 5):
            k = 2 ** (n - 1)
            if p >= base * k + g * per * k and cur == n - 1:
                local = n
        if local > cur:
            idx = data.index_of("MARK", mark_name)
            c.mark[idx] = local
            out.print(f"{print_transcallname(st, st.target)}は")
            out.set_bold(True)
            out.print(f"{data.names['MARK'].get(idx, '')}{local}")
            out.set_bold(False)
            out.printl("を取得した")
            out.printl()


def event_battle_reset_costume(ctx: Ctx, num: int) -> None:
    """`イベントから派生する特殊戦闘/特殊シチュエーション.ERB@EVENT_BATTLE_RESET_COSTUME(num)`:101–114。"""
    c = ctx.state.charas[num]
    if c.cflag[544] == 0:
        return
    for i in (40, 41, 42, 43):
        c.cflag[i] = c.cflag[500 + i]
    c.cflag[544] = 0
    cloth_battle_sethp(ctx)
    refresh_cloth_data(ctx)


def _transform_enemy_off(ctx: Ctx) -> None:
    """`SIF TALENT:(FLAG:111):変身能力 > 0 && CFLAG:(FLAG:111):1 > 0 / CALL TRANSFORM, 0, FLAG:111`。"""
    st = ctx.state
    e = st.charas[st.flag[111]]
    if t(ctx, e, "変身能力") > 0 and e.cflag[1] > 0:
        transform(ctx, 0, st.flag[111])


def self_check(ctx: Ctx, who: int) -> int:
    """`ゲーム内_イベント発生/強制発生イベント/FORCE_夜間自慰.ERB@SELF_CHECK, ARG`:77–178。"""
    st, data = ctx.state, ctx.data
    c = st.charas[who]
    p = c.palam[data.index_of("PALAM", "欲情")]
    if p == 0:
        local = 0
    else:
        for bound, val in ((100, 1), (300, 2), (600, 4), (1500, 6), (3000, 8), (6000, 10), (10000, 12), (30000, 15),
                           (60000, 18), (150000, 21), (300000, 25)):
            if p < bound:
                local = val
                break
        else:
            local = 30
    a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    step = ("0.25", "0.50", "0.75", "1.00", "1.25", "1.50")
    if a("欲望") >= 0:  # :114–126（負の値はどの分岐にも当たらない）
        local = times(local, step[min(a("欲望"), 5)])
    if a("露出癖") >= 0:  # :129–141
        local = times(local, step[min(a("露出癖"), 5)])
    onani = a("自慰中毒")  # :144–154
    if onani >= 1:
        local = times(local, {1: "1.25", 2: "1.50", 3: "2.00", 4: "2.50"}.get(onani, "4.00"))
    if t(ctx, c, "淫乱") == 1:  # :157–158
        local = times(local, "2.00")
    r = st.rng.rand(100)  # :161–172
    for bound, fac in ((20, "0.80"), (40, "0.90"), (60, "1.00"), (80, "1.10")):
        if r < bound:
            local = times(local, fac)
            break
    else:
        local = times(local, "1.20")
    return 1 if local >= 15 else 0


def subevent_release_ecstasy(ctx: Ctx) -> None:
    """`SUBEVENT_BATTLEE.ERB@SUBEVENT_RELEASE_ECSTASY`:163–226。"""
    from .palam import calc_ecstasy, message_sex_ecstasy_single

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    if c.tcvarn[40] <= 0:
        return
    c.nowex.clear()  # :169 VARSET NOWEX
    for i in range(4):  # :170–173 FOR LCOUNT, 0, 感覚数（DIM.ERH:154 感覚数 = 4）
        c.nowex[i] = calc_ecstasy(ctx, i, 0)
    local = sum(1 for i in range(4) if c.nowex[i] > 0)  # :176–180
    zecchou = data.index_of("EXP", "絶頂経験")
    for i in range(4):  # :181–188 JUEL:快Ｃ〜快Ｂ = 0〜3
        c.exp[zecchou] += c.nowex[i] * local
        c.juel[i] += 1000 * c.nowex[i] * local
    c.exp[data.index_of("EXP", "露出快楽経験")] += local  # :190
    if c.nowex[0] + c.nowex[1] + c.nowex[2] + c.nowex[3]:  # :192–223
        out.printl()
        if st.tflag[98] != 2:  # 地の文/MESSAGE_SUBEVENT.ERB@MESSAGE_SUBEVENT_BATTLE_RELEASE_ECSTASY:174–181
            out.set_bold(True)
            out.printl("絶頂解放")
            out.set_bold(False)
            out.printl(f"医療班に回収された{print_transcallname(st, st.target)}は、絶頂を阻害している成分を中和する薬を投与され、")
            out.printl("医師や看護師たちに見られる中で望まぬ絶頂を迎えた・・・")
            out.printl()
        for i in range(4):
            if c.nowex[i] >= 1:
                message_sex_ecstasy_single(ctx, i, c.nowex[i])
    c.tcvarn[40] = 0  # :224


def subevent_battleend(ctx: Ctx) -> None:
    """`SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLEEND`:6–13。"""
    st = ctx.state
    if tc(ctx).tcvarn[40] > 0:
        subevent_release_ecstasy(ctx)
    if st.tflag[98] in (0, 1):
        # SELF_BATTLEEND（FORCE_夜間自慰.ERB:65–72）
        if self_check(ctx, st.target) == 1:
            raise NotImplementedError("戦闘後自慰（MESSAGE_SELF_BATTLEEND／SELF_KIND）は未移植")


def after_train_rape(ctx: Ctx, arg: int) -> int:
    """`ゲーム内_イベント発生/戦闘イベント.ERB@AFTER_TRAIN_RAPE, ARG`:962–。襲われる場合は未移植で停止。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    if c.cflag[0] != 0:  # :970–971
        return 0
    if not is_hole(ctx):  # :973–974（ISHOLE()：ARG 省略 = -1 → TARGET）
        return 0
    local = min(div(5000 - st.flag[852], 100), 50) + min(c.cflag[285] * 2, 50) + (t(ctx, c, "嬲られ体質") > 0) * 10
    if st.flag[72] == 0:
        local = div(local, 2)
    if get_battle_situation(st, "レイプ確定") == 0 and st.rng.rand(100) >= local:  # :982–983
        return 0
    out.drawline()  # :986–990
    out.printl("――")
    out.printl("――――")
    out.printw("――――――")
    out.printl()
    # :992 分母の最後は MAXBASE ではなく BASE:性耐性 * 10（原作どおり）
    l1 = percent_cal(c.base[0] + c.base[1] + c.base[2] * 10, c.maxbase[0] + c.maxbase[1] + c.base[2] * 10)
    out.printl()
    if get_battle_situation(st, "レイプ確定") == 0 and st.rng.rand(100) < (
        div(l1 * 3, 4) + (st.tflag[98] == 1) * 6 - (st.time == 1) * 12 - (t(ctx, c, "嬲られ体質") > 0) * 12
    ):
        name = print_transcallname(st, st.target)
        if local < 25 or st.rng.rand(2) == 0:
            out.printl(f"{name}は誰かに尾けられているような気がしたが、")
            out.printl("どうやら気のせいだったようだ・・・")
        else:
            out.printl(f"{name}は誰かに尾けられているような気がしたが、")
            out.printl("うまく撒くことができたようだ・・・")
        out.printw()
        return 0
    raise NotImplementedError("戦闘終了後のレイプ（AFTER_TRAIN_RAPE:1007–）は未移植")


def douga_ryusutu(ctx: Ctx, arg: int) -> None:
    """`戦闘イベント.ERB@DOUGA_RYUSUTU, ARG`:1338–1478。撮影フラグ（TFLAG:21 bit0、性攻撃の地の文でのみ立つ）が
    無く ARG == 0 なら何もしない。"""
    st = ctx.state
    if (st.tflag[21] & 1) and arg == 0:
        raise NotImplementedError("動画流出（DOUGA_RYUSUTU:1342–1464）は未移植")
    if arg == 1:
        raise NotImplementedError("レイプ動画流出（DOUGA_RYUSUTU:1465–1477）は未移植")


def _tofull(n: int) -> str:
    return str(n).translate(str.maketrans("0123456789-", "０１２３４５６７８９－"))


def _event_end_lose(ctx: Ctx) -> None:
    """:335–422 敗北時（TFLAG:98 == 2）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    level = c.abl[data.index_of("ABL", "レベル")]
    get_syuren(ctx, 40 + c.ex[99] * 4)  # :337
    local = div(250 * tentacle_level(st), level + 2) + st.rng.rand(10)  # :339
    if st.flag[73] > 0:
        local = div(local, 8)
    get_exp(ctx, min(local, 750))  # :344
    local = (tentacle_level(st) + 65 - st.flag[52] * 5) * (st.tflag[0] - 50) - 200 - st.rng.rand(51)  # :348
    st.flag[852] += local
    if st.flag[852] < 0:
        st.flag[852] = 0
    result = abs(local)  # :352 `ABS LOCAL`：式中関数を命令として使うと RESULT に代入（Instraction.Child.cs:390–409）
    if st.flag[73] > 0:  # :355–364
        result = div(result, 8)
        for i in range(1, st.charanum):
            if st.charas[i].cflag[71] == -1:
                st.charas[i].cflag[71] = 1
        local = st.charanum  # FOR LOCAL,1,CHARANUM の終了後 LOCAL は CHARANUM（以下の IF LOCAL < 0 は偽）
    out.print(f"防衛力が{result}")  # :366–372
    out.printl("低下した" if local < 0 else "上昇した")
    out.printl()
    st.flag[853] -= 3  # :374–376（下限の補正なし：原作どおり）
    out.printl("人気度が3低下した")
    if st.flag[45] > 0:  # :379–390
        raise NotImplementedError("イベント戦の特殊ミッション判定は未移植")
    ninsin_check_after(ctx)  # :393
    if c.cflag[0] > 0:  # :397–410
        if (t(ctx, c, "変身時ＴＳ") > 0 and config_check_prison(st, 0) > 0) or st.flag[73] > 0:
            pass
        elif config_check_balance(st, 6) == 0:
            transform(ctx, 0)
    else:
        transform(ctx, 0)
        event_battle_reset_costume(ctx, st.target)
    _transform_enemy_off(ctx)  # :413–414
    if (enemy_type_check(st, "BOSS") == 1 or enemy_type_check(st, "LASTBOSS") >= 1) and st.flag[47] > st.flag[46]:
        st.flag[47] = div(st.flag[47] - st.flag[46], 4) + st.flag[46]  # :418–419
    c.cflag[23] = 0  # :421


def event_end(ctx: Ctx) -> Step:
    """`@EVENTEND`:2–536。`BEGIN TURNEND` を返す。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    ex99 = lambda: c.ex[99]  # noqa: E731  EX:行動ポイント
    st.flag[700] = 0  # :7
    st.tflag[6] = 0
    _battle_marks(ctx)  # :12–120
    mp = st.temp.max_palam
    for i in range(PALAM_END):  # :123–125 LIMIT(MAX, PALAM, MAX) = max(PALAM, MAX)（Creator.Method.cs@GetLimitMethod:1188–1197）
        c.palam[i] = limit(mp[i], c.palam[i], mp[i])
    st.temp.common_palam.clear()  # :128
    ablup(ctx, 0 if c.cflag[0] not in (1, 4) else 2)  # :131–137
    level = c.abl[data.index_of("ABL", "レベル")]
    boss_or_last = enemy_type_check(st, "BOSS") == 1 or enemy_type_check(st, "LASTBOSS") >= 1
    if st.tflag[98] == 0:  # :141–226 時間切れ／撤退
        if ex99() > 0:
            get_syuren(ctx, ex99())
        local = 100 - percent_cal(c.base[0] + c.base[1] + c.base[2] * 10, c.maxbase[0] + c.maxbase[1] + c.maxbase[2] * 10)
        local = div(div(tentacle_level(st) - 2, level) * local, 2) + st.rng.rand(10)
        if c.cflag[43] == 505:
            local = div(local * 5, 4)
        get_exp(ctx, min(local, 150))
        if st.flag[73] == 0:  # :154–177
            l1 = min(st.tflag[0] - 10, 0) ** 2
            l1 = l1 * (8 + tentacle_level(st)) + st.rng.rand(101) + max(300 - ex99() * 20, 100)
            if enemy_type_check(st, "MOB") == 1:
                l1 = div(l1, 10)
            if l1 == 0:
                l1 = 1
            if st.flag[852] > 0:
                st.flag[852] -= l1
                if st.flag[852] < 0:
                    st.flag[852] = 0
                out.printl(f"防衛力が{abs(l1)}低下した")
            elif st.rng.rand(100) < div(l1, 50):
                st.flag[853] -= 1
                if st.flag[853] < -100:
                    st.flag[853] = -100
                out.printl("人気度が1低下した")
        else:  # :179–184
            for i in range(1, st.charanum):
                if st.charas[i].cflag[71] <= -1:
                    st.charas[i].cflag[71] = 1
        if st.flag[45] > 0:  # :187–198
            raise NotImplementedError("イベント戦の特殊ミッション判定は未移植")
        ninsin_check_after(ctx)  # :204
        transform(ctx, 0)  # :206
        _transform_enemy_off(ctx)
        event_battle_reset_costume(ctx, st.target)  # :213
        if boss_or_last:  # :216–226
            if st.flag[47] > st.flag[46]:
                st.flag[47] = div(st.flag[47] - st.flag[46], 4) + st.flag[46]
            else:
                local = 6 + st.rng.rand(4)
                out.printl(f"探索度が{local}上昇した")
                research_progress(ctx, local)
                out.printl()
    elif st.savestr[13] == "MOB" and st.tflag[98] == 1:  # :228–260
        raise NotImplementedError("雑魚戦（戦闘あり）の勝利処理は未移植")
    elif st.tflag[98] == 1:  # :263–333 ボス勝利
        get_exp_battle(ctx)
        survive = tentacle_survive_num(st)
        get_syuren(ctx, 100 + ex99() * 2)
        a = 25 + st.rng.rand(8)
        get_money(ctx, a * (100 + (st.flag[3] - survive) * (25 + st.rng.rand(8))))
        get_kakera(ctx, 3)
        local = (tentacle_level(st) + 4) * 50 + 400 + st.rng.rand(101)
        st.flag[852] += local
        if st.flag[852] < 0:
            st.flag[852] = 0
        out.printl(f"防衛力が{abs(local)}上昇した")
        out.printl()
        st.flag[853] += 3  # :281–283
        out.printl("人気度が3上昇した！")
        if st.flag[45] > 0:
            raise NotImplementedError("イベント戦の特殊ミッション判定は未移植")
        ninsin_check_after(ctx)
        transform(ctx, 0)
        _transform_enemy_off(ctx)
        event_battle_reset_costume(ctx, st.target)
        if game_option(st, GameOption.ENDLESS):  # :311–333
            raise NotImplementedError("エンドレスモードの期日短縮は未移植")
    elif st.tflag[98] == 2:  # :335–422 敗北
        _event_end_lose(ctx)
    # :425–440 勝てなかったボスの蓄積ダメージと解析度を保持
    if enemy_type_check(st, "BOSS") == 1 and st.tflag[98] != 1:
        n = st.flag[11]
        result = div(st.flag[13] * 1000000, st.flag[12])
        st.flag[300 + n] = (1000000 - result) * 100
        if (st.flag[13] * 1000000) % st.flag[12]:
            st.flag[300 + n] += 1
        st.flag[500 + n] = st.flag[20]
    elif enemy_type_check(st, "LASTBOSS") >= 1 and st.tflag[98] != 1:
        raise NotImplementedError("ラスボスの蓄積ダメージ保持は未移植")
    # :443–464 戦闘支援効果で回復（CFLAG:100 が 出撃(101) か 防衛(105)）
    if st.flag[43] and c.cflag[100] in (ActionPlan.SORTIE, ActionPlan.DEFENSE) and st.tflag[98] != 2:
        support_heal(ctx)
    # :467–473
    if st.tflag[99] > 0:
        c.cflag[99] += st.tflag[99]
        out.printl(f"{print_callname(st, st.target)}の身体の底に疲労が蓄積した……（＋{_tofull(st.tflag[99])}）")
        st.tflag[99] = 0
    subevent_battleend(ctx)  # :476
    c.base[20] = 0  # :479–480
    c.base[21] = 0
    # :484–492 空中ダッシュ最大値を戻す
    if cloth_battle_hosei(ctx, "AIRPLUS", st.target) > 0:
        c.maxbase[22] -= 1
    if c.cflag[43] == 510:
        c.maxbase[22] -= 1
    if t(ctx, c, "有翼") > 0:
        c.maxbase[22] -= 1
    if st.flag[45] == 0:  # :494–495
        out.printw()
    # :498–504（AFTER_TRAIN_RAPE を呼ばない場合 RESULT は直前の値のまま。FLAG:73 == 0 の通常戦闘では必ず呼ぶ）
    if config_check_event(st, 3) > 0 and get_battle_situation(st, "レイプなし") == 0:
        result = 0
        if st.flag[73] == 0:
            result = after_train_rape(ctx, st.tflag[98])
        douga_ryusutu(ctx, result)
    if enemy_type_check(st, "MOB") == 1:  # :507–513
        st.flag[10] = 0 if st.flag[100] else 1
    # :516–524
    c.tcvarn.clear()
    st.temp.ex_com = 0
    st.temp.sh_com = 0
    st.temp.insert = 0
    st.temp.tentacle_size.clear()
    st.temp.tentacle_num.clear()
    st.flag[73] = 0
    # :527–528
    enslaved = sum(1 for ch in st.charas[1:] if ch.cflag[0] == 4)
    if (
        charanum_safe(st) + enslaved == 0
        and not game_option(st, GameOption.SOLO)
        and not game_option(st, GameOption.NO_GAMEOVER)
        and not check_gameover(st)
    ):
        from ..ending import ending_1

        ending_1(ctx)  # :528（ゲームオーバーモードに移行して戻る → :536 BEGIN TURNEND）
    # :531–532 実績のみ（deviations.md「全域資料」）
    return Step.TURNEND
