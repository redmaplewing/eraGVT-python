"""戦闘終了処理：`ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND`:2–536（路徑相對 `source/earGVP/ERB/`）。

TFLAG:98 は戦闘の結果（0＝時間切れ／撤退、1＝勝利、2＝敗北）。設定箇所は BATTLE_COM_AFTER.ERB:129（勝利）、
:852／:973（敗北）のみ。
"""

from __future__ import annotations

from collections.abc import Generator

from ...state.constants import ActionPlan, GameOption
from ..action import (
    Ctx,
    Step,
    _shortline,
    config_check_event,
    config_check_prison,
    get_exp,
    get_syuren,
    print_callname,
    print_transcallname,
)
from ..era import div, limit
from ..opening import game_option
from ..shop import charanum_safe, check_gameover
from ..tentacle import enemy_type_check, tentacle_survive_num
from .ablup import ablup
from .cloth import cloth_battle_hosei, cloth_battle_sethp, refresh_cloth_data
from .core import PALAM_END, config_check_balance, get_battle_situation, mark, percent_cal, t, tc, tentacle_level
from .encount import get_exp_battle, get_kakera, get_money, research_progress, support_heal
from .func import transform
from .ninsin import ninsin_check_after  # ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@NINSIN_CHECK_AFTER:169–190
from .rape import after_train_rape  # 戦闘イベント.ERB@AFTER_TRAIN_RAPE:962–1334（S15）
from .self_kind import self_battleend  # FORCE_夜間自慰.ERB（S15）


def mission_check(ctx: Ctx, default: int) -> None:
    """イベント戦の特殊ミッション判定（S20：`raid.mission_check`）。"""
    from ..raid import mission_check as _mc

    _mc(ctx, default)

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
        self_battleend(ctx, st.target)  # :13（FORCE_夜間自慰.ERB@SELF_BATTLEEND:65–72）


def douga_ryusutu(ctx: Ctx, arg: int) -> None:
    """`ゲーム内_イベント発生/戦闘イベント.ERB@DOUGA_RYUSUTU, ARG`:1338–1478（S14）。

    TFLAG:21 は「キャラの凌辱目撃フラグ」（`●開発者向け資料/●GVTフラグ一覧.txt`:480–490：1 動画配信された、2 愛撫、
    4 口、8 挿入、16 膣内射精、32 アナル射精、64 ぶっかけ、128 嬲りもの、256 絶頂、512 自分から）。bit 0 は撮影中
    （FLAG:71 か 常時撮影）の性攻撃地の文と PERFORM_CHEERS_TENTACLE_SEX_HANTEI（:771–774）で立つ。
    CFLAG:284 = 触手凌辱映像流出フラグ、CFLAG:285 = ストーカーフラグ（同 :348–349）。いずれも TARGET のもの。
    ARG = AFTER_TRAIN_RAPE の戻り値（BATTLE_TRAIN_AFTER.ERB:498–504；1 は戦闘後レイプが成立した場合＝:1334 RETURN 1）。
    """
    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    f = st.tflag[21]
    if (f & 1) and arg == 0:  # :1342
        _shortline(out)  # :1343 CALL SHORTLINE
        out.printl()
        out.printl("どうやら撮影された動画がネットに放流されたようだ。")
        out.printl()
        out.print(f"そこには{print_transcallname(st, st.target)}が")
        out.print("触手" if enemy_type_check(st, "AKUOTI") == 0 else "悪の手先")  # :1348–1352
        out.printl("に捕まり、")

        def b(m: int) -> bool:
            return (f & m) != 0

        oral_etc = b(2) or b(4) or b(64)
        if b(2):  # :1355–1362
            out.print("全身を愛撫されて快楽に")
            out.print("喘いでいる" if f == 3 else "喘ぎながら")
        if b(4):  # :1363–1370
            out.print("口で奉仕させられ")
            if b(64) or (not b(2) and b(8)):
                out.print("た上に")
            elif f == 13:
                out.printl("、")
        if b(64):  # :1371–1372
            out.print("精液をぶっかけられ")
        if f in (65, 113):  # :1373–1377
            out.print("ている")
        elif b(2) and b(4) and b(64) and b(128):
            out.printl("、")
        if b(4) or b(64):  # :1379–1382
            if not b(8) and not b(16) and not b(32) and not b(128) and not b(256):
                out.print("ている")
        if oral_etc:  # :1384–1390
            if b(8) or b(256):
                out.printl("、")
                if (b(128) or b(256)) and not b(8):
                    out.print("それだけでなく")
        if b(8):  # :1392–1415
            if b(128):
                out.print("ボロボロに犯され")
            else:
                out.print("挿入")
                if oral_etc:
                    out.print("まで")
                out.print("され")
            if b(16) or b(32):
                out.print("て")
            if b(16) and b(32):
                out.print("前後の穴に子種を注ぎ込まれ")
            elif b(16):
                out.print("膣内射精を受け止め")
            elif b(32):
                out.print("アナルに射精を受け止め")
            if b(256):
                out.printl("、")
            else:
                out.print("ている")
        if b(256):  # :1417–1426
            out.print("絶頂")
            if b(128) and not b(8):
                out.print("させられた挙句に")
            else:
                if oral_etc and not b(8):
                    out.print("まで")
                out.print("させられている")
        if b(128) and not b(8):  # :1428–1433
            out.print("玩具のように嬲られて")
            if b(2) or b(256):
                out.printl("、")
            out.print("拷問でボロボロになっていく")
        if f == 1:  # :1435–1437
            out.print("あわや犯されそうになっている際どい")
        out.printl("映像が映し出されていた。")  # :1439–1440
        out.printl()
        if b(8):  # :1442–1443
            out.printl("股間にモザイクも掛けられておらず、結合部が丸見えになっている。")
        charm = c.exp[data.index_of("EXP", "魅了経験")] >= 150
        # :1444–1462（ELSEIF の RAND は前の条件が偽のときだけ評価される）
        if st.rng.rand(4) == 0:
            out.printl("幸運なことに顔はしっかりと映っていないが、")
            out.printl("どんなところから身元を特定されてしまうか分かったものではない。")
        elif st.rng.rand(3) == 0:
            out.printl("不幸中の幸いと言うべきか、顔にはモザイクが掛かっていたが、")
            out.printl("見る人が見れば容易に身元を特定されてしまうだろう。")
            if charm:
                c.cflag[285] += 1
        elif st.rng.rand(2) == 0:
            out.printl("顔の映りは不鮮明だが、見る人が見れば容易に身元を特定されてしまうだろう。")
            c.cflag[285] += 1
            if charm:
                c.cflag[285] += 1
        else:
            out.printl("顔がはっきり映されてしまっており、ネット上で身元を特定されるのも時間の問題だろう。")
            c.cflag[285] += 2
            if charm:
                c.cflag[285] += 1
        out.printl("動画が削除されるまでの間、再生数は伸び続けた・・・")  # :1463–1464
        out.printw()
    elif arg == 1:  # :1465–1477
        _shortline(out)
        out.printl()
        out.printl("男たちは襲われたことを他言しなければ動画を公開しないと言っていたが、")
        if t(ctx, c, "主観視点") > 0:
            out.printl(
                "初めから約束を守る気など無かったのか、あの後すぐにレイプの一部始終を捉えた動画をネット上にアップロードしたようだ。"
            )
        else:
            out.printl("初めから約束を守る気など無かったのか、すぐにレイプ動画をネット上にアップロードした。")
        out.printl(f"後になって{print_transcallname(st, st.target)}が気付いた時には既に遅く、")
        out.printl("動画が多数の人間の目に触れてしまった後だった・・・")
        out.printw()
        c.cflag[284] += 4 + st.rng.rand(5)  # :1477


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
    if st.flag[45] > 0:  # :379–390（CATCH：無指定なら敗北時はミッション失敗）
        mission_check(ctx, 0)
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


def event_end(ctx: Ctx) -> Generator[None, int, Step]:
    """`@EVENTEND`:2–536。`BEGIN TURNEND` を返す。AFTER_TRAIN_RAPE → CALC_GANGBANG → AFTER_PILL（INPUT）のため
    ジェネレータ（S15）。"""
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
        if st.flag[45] > 0:  # :187–198（CATCH：無指定なら敗北時以外はミッション達成）
            mission_check(ctx, 1)
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
        get_exp_battle(ctx)
        tentacle_survive_num(st)
        get_syuren(ctx,10+ex99()*2)
        get_money(ctx,(25+st.rng.rand(11))*(5+st.rng.rand(5)))
        local = st.rng.rand(50)+div(tentacle_level(st),2)+50
        st.flag[852] = max(st.flag[852]+local,0)
        out.printl(f"防衛力が{abs(local)}"+("低下した" if local<0 else "上昇した"))
        out.printl()
        ninsin_check_after(ctx)
        transform(ctx,0)
        _transform_enemy_off(ctx)
        event_battle_reset_costume(ctx,st.target)
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
        if st.flag[45] > 0:  # :286–297
            mission_check(ctx, 1)
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
    elif enemy_type_check(st, "LASTBOSS") >= 1 and st.tflag[98] != 1:  # :432–439（S27：:434 の重複代入も同値）
        n = st.flag[11]
        result = div(st.flag[13] * 1000000, st.flag[12])
        st.flag[400 + n] = (1000000 - result) * 100
        if (st.flag[13] * 1000000) % st.flag[12]:
            st.flag[400 + n] += 1
        st.flag[600 + n] = st.flag[20]
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
            result = yield from after_train_rape(ctx, st.tflag[98])
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
