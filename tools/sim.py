"""隨機方針模擬（S11 起各階段共用）：`python tools/sim.py --preset default --seeds 0-249`。

每一場：新遊戲（`--preset default` = 標題 [0]→[0] おまかせ；`tokusou` = [0]→[1] 初期セット）→ 每次 SHOP 時
對全員隨機預約 101–103（休憩・鍛錬・出撃）後 [100] 確認；其他畫面從最近輸出的按鈕中隨機選一個（沒有按鈕就送 0）。
遊戲 RNG = `GameRng(seed)`，方針 RNG = `random.Random(seed)`（兩者獨立）。口上／地の文用 catalog（Web 預設）。

停止條件：Web「停止」（未移植 → NotImplementedError 的訊息）、SHOP 次數達 `--max-shop`、輸入步數達 `--max-steps`、
其他例外（記為「例外: 型別」）。

輸出：停止原因頻度、停止前經過的 SHOP 次數（平均／最多）、敗北局數（曾有人幽閉 CFLAG:0 == 1）與敗北後 SHOP 平均、
ゲームオーバーモード（FLAG:0 == 0，S12）進入局數與進入後 SHOP 平均（＝再走幾回合）及其停止原因。
停止原因以訊息的前 `--key-len` 字歸類。

S18：各強制發生事件的實際觸發次數（`install_event_counters`：包裝模組函式計數，不改變遊戲行為）。
`--enable-intimidation` 在開局後把 FLAG:804 bit10（`CONFIG_CHECK_PRISON_F(10)`「クズ市民による幽閉」）打開
（基本セットは OFF：脅迫イベントは起きない）。

S19：`--enable-akuoti` は開局後に FLAG:804 bit1（`CONFIG_CHECK_PRISON_F(1)`：陥落時に洗脳／悪堕ち）と bit9
（`CONFIG_CHECK_PRISON_F(9)`：洗脳ではなく悪堕ち）を打開（PRISON.ERB:335–357；基本セットは FLAG:804 = 1 で両方 OFF、
陥落しても悪堕ちキャラは生まれない）。悪堕ちキャラの淫謀・洗脳／悪堕ちキャラ戦の次数も数える。

S20：襲撃／救援イベント戦の次数（RAID_RESCUE／RAID_ATTACK 呼出、EXEC_n、救援見送り、ミッション成否と TFLAG:98）。

S23：[反撃]スタイルの路徑次数（HANGEKI_TO_TENTACLE 呼出・成功、COM4 のＥＸ反撃、反撃準備、[反撃]の完全防御文、過剰蓄積）。
`--style 反撃` は開局直後に全キャラ・全距離の CDFLAG:戦闘スタイル を 10（[反撃]）にする**人工的な状態**
（原作では初期セット 0／汎用キャラとも 通常：武器カスタマイズ〔未移植〕か一部固有キャラの CSV／口上でしか [反撃] にならない）。

S24：`--config-preset N`（0〜3，既定 1）＝開局の HEROINE_PRESET で押す番号（`オープニング処理.ERB`:643–649：
0 グローバル引き継ぎ・1 基本セット・2 淫獄セット・3 クズ市民セット）。`--preset`（キャラの開局経路）とは別。
模擬は毎回空の一時ディレクトリで行うので GLOBAL は無い（真の初回起動）：0 は FLAG:800 = 1、FLAG:801〜805 = 0（全 OFF）。
`--clear-bit 802:4`（複数可）は開局直後に FLAG の bit を消す**人工的な操作**（SHOP [700] で切り替えたのと同じ状態。停止点の先を見る用）。

S27：ラスボス・結局の次数（ラスボス出現・遭遇・勝敗、完全殲滅、ENDING_2／3、SCORE 総合評価）。ENDING_3 後にタイトルへ戻ったら
「タイトル復帰」で終了。`--bosses-cleared` は開局直後に FLAG:100 = 0・FLAG:101 = 1（全ボス撃破済みでラスボス出現中）にする
**人工的な状態**（撃破までの経緯〔経験・ボス経験・蓄積ダメージ等〕は通らない）。

S28a：`--actions 101,102,103,105,106,107`（既定は従来どおり 101,102,103）で SHOP の行動予約の候補を変える。拠点防衛・戦闘支援・
情報収集（4 種の内訳、情報屋／コネ獲得、変身選択）・戦闘基礎 Lv5 の変身能力獲得・スケジュールの次数を数える。

S28b：`--actions` に 104（特別活動）を入れると、活動別（アルバイト〜ライブ公演）・地の文別の次数（catalog で実行できず佔位になったものは
「（佔位）」）・特別活動中の妊娠判定を数える。変身選択の次数は「{行動} 変身して行動」。`--seisan-unlock` は開局直後に全キャラの
欲望 3・露出癖 2・マゾっ気 2・魅了経験 100 にする**人工的な状態**（援助交際〜枕営業・ライブ公演の分岐を通すため）。

S28c1：`--actions` に 108（自由行動）を入れると、行き先（CFLAG:101）・本文関数（catalog 実行、佔位は「（佔位）」）・学校・告白・
淫気応急・悪堕ち遭遇・ナンパ／酒ナンパ判定・痴漢判定（乗車）の次数を数える。S28c2：本編（ナンパ・酒ナンパ・痴漢）と
catalog の中で呼ばれた子関数（デート・お持ち帰り・レイプ・泥酔レイプ・変態プレイ）・本編中の処女喪失・痴漢お持ち帰りの次数。

S29：口上／地の文の GameState 書き込み（変数別「S29 書き込み 口上 CFLAG」等、hook 行は「（hook 行）」、函式別）、口上からの
状態変更函式 hook（LEVELSTATUS／TRANSFORM／PERFORM_CHEERS_HATE）、ジャーナルで戻した回数を数える。

S30：ループ内 $ラベルへの GOTO の再開（ラベル別：KOJO_AEGI の ＭＡＸ１／ＭＡＸ２ 等）、STRDATA（函式別）、`narration.pyfuncs`
（RANDCHOOSE 系・UNLOCK_ACHIEVEMENT）、口上の CORRUPTTION_GET_* hook、ロストキャラの発見（catalog 実行）の次数。

S32：記錄 HATUJOU_TO_HAIRAN 的成功次數（原文 RETURN 1），確認既有停止 seed 通過實際觸發路徑。

S25：戦闘中の [800] でステータス画面（5 ページ・EXPORT_CSV 含む）に入るようになった（ランダム方針のまま。SHOP [110] は押さない）。
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eragvt.data import default_csv_dir, load_game_data  # noqa: E402
from eragvt.game.session import GameSession, Phase  # noqa: E402
from eragvt.narration.service import CatalogNarrationService  # noqa: E402
from eragvt.state import GameRng  # noqa: E402

HALT_PREFIX = "（未實作のため停止しました："


def _parse_seeds(text: str) -> list[int]:
    out: list[int] = []
    for part in text.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def install_event_counters() -> Counter:
    """S18：強制發生事件的函式呼叫／狀態變化を数える（モジュール属性を包む。呼び出しは全てモジュールの大域名経由）。"""
    from eragvt.game import intimidation, small_tentacle, turnend, yobai

    counts: Counter = Counter()

    def wrap(mod, name, before=None, after=None):
        orig = getattr(mod, name)

        def w(ctx, *a, **k):
            snap = before(ctx, *a) if before else None
            r = yield from orig(ctx, *a, **k)
            if after:
                after(ctx, snap, *a)
            return r

        setattr(mod, name, w)

    def intim_before(ctx):
        c = ctx.state.target_chara
        return (c.cflag[290], c.cflag[0])

    def intim_after(ctx, snap):
        c = ctx.state.target_chara
        if c.cflag[290] != snap[0]:
            counts["脅迫（発生）"] += 1
        if c.cflag[0] == 4 and snap[1] != 4:
            counts["脅迫→拉致監禁"] += 1

    def kid_after(ctx, snap):
        counts["拉致監禁（KIDNAPPING 呼出）"] += 1
        if ctx.state.charas[snap].cflag[0] != 4:
            counts["拉致監禁→救出／解放"] += 1

    wrap(turnend, "intimidation_event", intim_before, intim_after)
    wrap(turnend, "kidnapping", lambda ctx: ctx.state.target, kid_after)
    wrap(yobai, "yobai_event", after=lambda ctx, snap: counts.update(["夜這い（YOBAI_EVENT）"]))
    wrap(yobai, "yobai_action", after=lambda ctx, snap, arg, *a: counts.update([f"夜這い実行 ARG={arg}"]))
    wrap(small_tentacle, "small_tentacle_attack", after=lambda ctx, snap: counts.update(["子触手襲来（ATTACK）"]))
    wrap(small_tentacle, "small_prison_event", after=lambda ctx, snap: counts.update(["子触手襲来（成功）"]))
    wrap(small_tentacle, "small_prison_com", after=lambda ctx, snap, arg: counts.update([f"子触手 SMALL_PRISON_COM {arg}"]))

    # S19：悪堕ちキャラ関連（いずれも通常の関数）
    from eragvt.game import akuoti
    from eragvt.game.battle import encount, source_check

    def wrap_plain(mod, name, after):
        orig = getattr(mod, name)

        def w(ctx, *a, **k):
            r = orig(ctx, *a, **k)
            after(ctx, r)
            return r

        setattr(mod, name, w)

    def enc_after(ctx, r):
        if r:
            kind = {2: "洗脳", 3: "悪堕ち"}.get(ctx.state.charas[ctx.state.flag[111]].cflag[0], "?")
            counts[f"{kind}キャラ戦（ENCOUNT_ENEMY）"] += 1

    wrap_plain(akuoti, "akuoti_event", lambda ctx, r: counts.update(["悪堕ちキャラの淫謀（AKUOTI_EVENT）"]))
    wrap_plain(encount, "encount_enemy", enc_after)
    wrap_plain(source_check, "_victory_akuoti", lambda ctx, r: counts.update(["洗脳／悪堕ちキャラ戦 勝利"]))
    orig_lose = source_check._battle_lose

    def lose(ctx, *a, **k):
        if ctx.state.flag[110] > 0:  # 敗北処理は BEGIN AFTERTRAIN（例外）で抜けるので先に数える
            counts["洗脳／悪堕ちキャラ戦 敗北"] += 1
        return orig_lose(ctx, *a, **k)

    source_check._battle_lose = lose

    # S20：襲撃／救援イベント戦（raid の関数はすべてモジュール大域名経由で呼ばれる）
    from eragvt.game import raid

    wrap(raid, "raid_rescue", after=lambda ctx, snap: counts.update(["救援（RAID_RESCUE 呼出）"]))
    wrap(raid, "raid_attack", after=lambda ctx, snap: counts.update(["襲撃（RAID_ATTACK 呼出）"]))

    def exec_after(ctx, snap):
        counts[f"イベント戦 EXEC_{snap}"] += 1

    wrap(raid, "_exec", before=lambda ctx: ctx.state.flag[45], after=exec_after)
    orig_abandon = raid._abandon

    def abandon(ctx):
        counts[f"救援 見送り（ABANDON_{ctx.state.flag[45]}）"] += 1
        return orig_abandon(ctx)

    raid._abandon = abandon
    for name, label in (("raid_mission_success", "成功"), ("raid_mission_failure", "失敗")):
        orig_m = getattr(raid, name)

        def m(ctx, _orig=orig_m, _label=label):
            counts[f"イベント戦 {ctx.state.flag[45]} ミッション{_label}（TFLAG:98={ctx.state.tflag[98]}）"] += 1
            return _orig(ctx)

        setattr(raid, name, m)

    # S23：[反撃]スタイル（enemy／commands のモジュール大域名を包む：呼び出しは大域名経由）
    from eragvt.game.battle import commands, enemy

    orig_hangeki = enemy.hangeki_to_tentacle

    def hangeki(ctx, a, b, d):
        ex0 = ctx.state.target_chara.ex[99]
        r = yield from orig_hangeki(ctx, a, b, d)
        counts["反撃 HANGEKI_TO_TENTACLE 呼出"] += 1
        if ctx.state.target_chara.ex[99] >= ex0 + 2:  # 成功時のみ EX:行動ポイント += 2（HANGEKI_STYLE.ERB:91）
            counts[f"反撃 成功（敵行動 {a}・判定 {b}）"] += 1
        return r

    enemy.hangeki_to_tentacle = hangeki
    orig_chinobun = commands.run_chinobun
    labels = {"MESSAGE_BATTLE_CHARA_HANGEKI_EX": "反撃 COM4 ＥＸ反撃体勢", "MESSAGE_BATTLE_CHARA_HANGEKI": "反撃 反撃準備（攻撃後）",
              "MESSAGE_BATTLE_TENTACLE_ATTACK_OVERCHARGE": "反撃 バースト過剰蓄積"}

    def chinobun(ctx, func, *a, **k):
        if func in labels:
            counts[labels[func]] += 1
        return orig_chinobun(ctx, func, *a, **k)

    commands.run_chinobun = chinobun
    orig_pg = enemy.msg_perfect_guard

    def perfect_guard(ctx):
        from eragvt.game.battle.core import fstyle_name, tc

        if fstyle_name(ctx, ctx.state.target, tc(ctx).tcvarn[0]) == "反撃":
            counts["反撃 完全防御文（PRINTDATAL）"] += 1
        return orig_pg(ctx)

    enemy.msg_perfect_guard = perfect_guard

    # S27：ラスボス・結局
    from eragvt.game import ending as ending_mod

    def enc_boss_after(ctx, r):
        if r and ctx.state.flag[10] == 1:
            counts["ラスボス遭遇（ENCOUNT_BOSS）"] += 1

    wrap_plain(encount, "encount_boss", enc_boss_after)
    wrap_plain(source_check, "_victory_lastboss", lambda ctx, r: counts.update(["ラスボス撃破"]))
    orig_all = source_check._all_bosses_cleared

    def all_cleared(ctx):
        key = "完全殲滅（BEGIN TURNEND）" if ctx.state.flag[64] == -1 else "ボス全滅→ラスボス出現"
        counts[key] += 1
        return orig_all(ctx)

    source_check._all_bosses_cleared = all_cleared
    orig_lose2 = source_check._battle_lose

    def lose2(ctx, *a, **k):
        if ctx.state.flag[10] == 1 and ctx.state.flag[110] == 0:
            counts["ラスボス戦 敗北"] += 1
        return orig_lose2(ctx, *a, **k)

    source_check._battle_lose = lose2
    for name in ("ending_2", "ending_3"):
        orig_e = getattr(ending_mod, name)

        def e(ctx, _orig=orig_e, _name=name):
            counts[_name.upper()] += 1
            return _orig(ctx)

        setattr(ending_mod, name, e)
    orig_score = ending_mod.score

    def sc(ctx):
        r = orig_score(ctx)
        counts[f"SCORE 総合 {r}"] += 1
        return r

    ending_mod.score = sc

    # S28a：拠点防衛・戦闘支援・情報収集
    from eragvt.game import action as action_mod, gather

    orig_guard = action_mod.guard

    def guard(ctx):
        r = orig_guard(ctx)
        counts["拠点防衛（GUARD）" + ("→戦闘" if r else "：遭遇なし")] += 1
        return r

    action_mod.guard = guard
    wrap_plain(action_mod, "support", lambda ctx, r: counts.update(["戦闘支援（SUPPORT）"]))
    names = {0: "噂話の聞き込み", 1: "事件の捜査", 2: "情報を買う", 3: "仲間の捜索"}
    wrap(gather, "message_gather_information", after=lambda ctx, snap, arg: counts.update([f"情報収集 {names.get(arg, arg)}"]))

    def tf_after(ctx, snap, arg, args):
        if ctx.state.charas[arg].cflag[1] > 0:
            counts[f"{args} 変身して行動"] += 1

    wrap(gather, "action_transformation_select", after=tf_after)
    wrap(gather, "_informant", before=lambda ctx, *a: ctx.state.target_chara.cflag[122],
         after=lambda ctx, snap, *a: counts.update(["情報屋 出現" + ("→コネ獲得" if ctx.state.target_chara.cflag[122] != snap else "")]))
    orig_inv = gather._investigate

    def inv(ctx):
        c = ctx.state.target_chara
        before = c.cflag[121]
        r = yield from orig_inv(ctx)
        if c.cflag[121] != before:
            counts[f"コネ 警察（CFLAG:121 = {c.cflag[121]}）"] += 1
        return r

    gather._investigate = inv
    wrap(action_mod, "_sengiup_henshin", after=lambda ctx, snap, who: counts.update(["戦闘基礎 Lv5 変身能力獲得"]))

    # S28b：特別活動（活動別・地の文別の次数、catalog で実行できず佔位になった地の文、スケジュール）
    from eragvt.game import seisan as seisan_mod

    for name, label in (("research", "研究"), ("idol_activity", "アイドル活動"), ("idol_live", "ライブ公演"),
                        ("part_time", "アルバイト")):
        wrap_plain(seisan_mod, name, lambda ctx, r, _l=label: counts.update([f"特別活動 {_l}"]))
    for name, label in (("pest_control", "雑魚触手退治"), ("prostitution", "援助交際"), ("porn_video", "AV出演"),
                        ("toilet", "公衆便所"), ("idol_prostitution", "枕営業")):
        wrap(seisan_mod, name, after=lambda ctx, snap, _l=label: counts.update([f"特別活動 {_l}"]))
    orig_msg = seisan_mod._msg

    def smsg(ctx, func, *a, **k):
        ok = orig_msg(ctx, func, *a, **k)
        short = func.replace("MESSAGE_SEISAN_", "").replace("MESSAGE_", "")
        counts[f"特別活動 地の文 {short}" + ("" if ok else "（佔位）")] += 1
        return ok

    seisan_mod._msg = smsg
    orig_ninsin = seisan_mod._ninsin

    def sninsin(ctx, *a):
        # S71：等待實際返回值，不能用尚未執行的 generator 判斷成功。
        r = yield from orig_ninsin(ctx, *a)
        counts["特別活動 妊娠判定" + ("→受精" if r else "")] += 1
        return r

    seisan_mod._ninsin = sninsin

    # S28c1：自由行動（行き先・本文関数・各イベント・ナンパ／痴漢の判定）
    from eragvt.game import pastime as pt
    from eragvt.game import pastime_school as pts

    cur = {"kind": None}
    for name, label in (("machi", "街"), ("toode", "遠出"), ("undou", "運動")):
        orig_g = getattr(pt, name)

        def g(ctx, *a, _o=orig_g, _l=label, **k):
            cur["kind"] = _l
            return (yield from _o(ctx, *a, **k))

        setattr(pt, name, g)
    orig_dot = pt._dot_after

    def dot(ctx, *a):
        if cur["kind"] is not None:
            counts[f"自由行動 行き先 {cur['kind']} CFLAG:101={ctx.state.target_chara.cflag[101]}"] += 1
            cur["kind"] = None
        return orig_dot(ctx, *a)

    pt._dot_after = dot
    orig_chino = pt._chinobun

    def chino(ctx, func, *a, **k):
        n0 = len(ctx.out.lines)
        ok = orig_chino(ctx, func, *a, **k)
        counts[f"自由行動 本文 {func}" + ("" if ok else "（佔位）")] += 1
        if func == "Message_School_Lunchbreak" and any("【秘密のオナペット】" in ln.text for ln in ctx.out.lines[n0:]):
            counts["自由行動 本文 PASTIME_SHASHIN（昼休みの中）"] += 1
        return ok

    pt._chinobun = chino
    pts._chinobun = chino
    wrap(pts, "pastime_school", after=lambda ctx, snap, *a: counts.update(["自由行動 学校（完了）"]))
    orig_school = pts.pastime_school

    def school(ctx, *a, **k):
        counts["自由行動 学校（開始）"] += 1
        return (yield from orig_school(ctx, *a, **k))

    pts.pastime_school = school
    wrap(pts, "select_club", after=lambda ctx, snap: counts.update(["自由行動 部活選択"]))
    wrap(pt, "select_school", after=lambda ctx, snap: counts.update(["自由行動 学校途中編入"]))

    def koku_before(ctx):
        return ctx.state.target_chara.talent[ctx.data.index_of("TALENT", "交際相手")]

    wrap(pt, "kokurare", before=koku_before,
         after=lambda ctx, snap: counts.update(["自由行動 告白→交際" if koku_before(ctx) != snap else "自由行動 KOKURARE 呼出"]))

    def ink_before(ctx, *a):
        return ctx.state.target_chara.talent[ctx.data.index_of("TALENT", "処女")]

    wrap(pt, "inkioukyu", before=ink_before,
         after=lambda ctx, snap, *a: counts.update(["自由行動 淫気応急" + ("（処女喪失）" if ink_before(ctx) != snap else "")]))
    orig_aku = pt.akuoti_encounter

    def aku(ctx):
        f111 = ctx.state.flag[111]
        n0 = len(ctx.out.lines)
        orig_aku(ctx)
        hit = any("逢魔の休日" in ln.text for ln in ctx.out.lines[n0:])
        counts["自由行動 悪堕ち遭遇" + ("（発生）" if hit else "（判定のみ）")] += 1
        _ = f111

    pt.akuoti_encounter = aku
    for name, label in (("pastime_nanpa", "ナンパ判定"), ("pastime_sake_nanpa", "酒ナンパ判定")):
        orig_n = getattr(pt, name)

        def nf(ctx, _o=orig_n, _l=label):
            r = _o(ctx)
            counts[f"自由行動 {_l}→{r}"] += 1
            return r

        setattr(pt, name, nf)
        setattr(pts, name, nf)
    orig_ch = pt.pastime_chikan

    def ch(ctx, *a):
        counts["自由行動 痴漢判定（乗車）"] += 1
        return (yield from orig_ch(ctx, *a))

    pt.pastime_chikan = ch
    pts.pastime_chikan = ch

    # S28c2：本編（ナンパ・酒ナンパ・痴漢）の次数、catalog の中で呼ばれた子関数（デート・お持ち帰り・レイプ）、処女喪失
    from eragvt.game import pastime_nanpa as pn
    from eragvt.narration.runtime import Interp

    sub = {"PASTIME_NANPA_DATE", "PASTIME_NANPA_TAKEOUT", "PASTIME_NANPA_RAPE", "PASTIME_SAKE_NANPA_DATE",
           "PASTIME_SAKE_NANPA_TAKEOUT", "PASTIME_SAKE_NANPA_RAPE", "PASTIME_SAKE_NANPA_DEISUI_RAPE", "PASTIME_CHIKAN_TAKEOUT",
           "MESSAGE_CITIZEN_TRAIN_PIG", "MESSAGE_CITIZEN_TRAIN_DOG", "MESSAGE_CITIZEN_TRAIN_KANCHO"}
    orig_call = Interp.call

    def icall(self, name, args, as_method=False):
        if name.upper() in sub:
            counts[f"自由行動 本編 子関数 {name.upper()}"] += 1
        return orig_call(self, name, args, as_method)

    Interp.call = icall
    for name, label in (("message_pastime_nanpa", "ナンパ本編"), ("message_pastime_sake_nanpa", "酒ナンパ本編"),
                        ("message_pastime_chikan", "痴漢本編")):
        orig_m2 = getattr(pn, name)

        def mf(ctx, *a, _o=orig_m2, _l=label):
            sj = ctx.data.index_of("TALENT", "処女")
            v0 = ctx.state.target_chara.talent[sj]
            r = yield from _o(ctx, *a)
            counts[f"自由行動 {_l}"] += 1
            if v0 > 0 and ctx.state.target_chara.talent[sj] < 0:
                counts[f"自由行動 {_l}（処女喪失）"] += 1
            if _l == "痴漢本編" and r:
                counts["自由行動 痴漢本編（お持ち帰り RETURN 1）"] += 1
            return r

        setattr(pt, name, mf)
        if hasattr(pts, name):
            setattr(pts, name, mf)

    # S29：口上／地の文の中の GameState 書き込み（変数別・函式数）、口上からの状態変更函式 hook、失敗回復
    from eragvt.game import kojo_calls
    from eragvt.narration import service as nsvc

    orig_set = Interp._state_set

    def sset(self, v, value, fr):
        d = fr.fd.file.split("/", 1)[0] + ("（hook 行）" if getattr(self, "_state_write", False) else "")
        counts[f"S29 書き込み {d} {v.name}"] += 1
        counts[f"S29 書き込み函式 {fr.fd.name}"] += 1  # 種類数は --load の結果から数える
        return orig_set(self, v, value, fr)

    Interp._state_set = sset
    for fname in ("hook_levelstatus", "hook_transform", "hook_perform_cheers_hate",
                  "hook_corruption_get_theme", "hook_corruption_get_nanori_final"):
        orig_k = getattr(kojo_calls, fname)

        def kf(ctx, *a, _o=orig_k, _n=fname):
            counts[f"S29 口上 hook {_n}"] += 1
            return _o(ctx, *a)

        setattr(kojo_calls, fname, kf)
    orig_rb = nsvc._Tx.rollback

    def rb(self):
        if not self.closed and len(self.journal.entries) > self.mark[0]:
            counts["S29 ジャーナルで戻した（失敗回復・INPUT 再実行）"] += 1
        return orig_rb(self)

    nsvc._Tx.rollback = rb

    # S30：ループ内ラベルへの GOTO（函式別）・STRDATA・narration.pyfuncs・ロストキャラの発見（catalog）
    orig_goto = Interp._goto_path

    def gp(self, stmts, name):
        counts[f"S30 GOTO 再開 ${name}"] += 1
        return orig_goto(self, stmts, name)

    Interp._goto_path = gp
    orig_sd = Interp._strdata

    def sd(self, s, fr):
        counts[f"S30 STRDATA {fr.fd.name}"] += 1
        return orig_sd(self, s, fr)

    Interp._strdata = sd
    from eragvt.narration import pyfuncs

    for key, fn in list(pyfuncs.PY_FUNCS.items()):
        def pf(it, args, _o=fn, _k=key):
            counts[f"S30 pyfunc {_k}"] += 1
            return _o(it, args)

        pyfuncs.PY_FUNCS[key] = pf
    from eragvt.game.battle import source_check as sc

    orig_rd = sc._rescue_deadnum

    def rd(ctx):
        n0 = len(ctx.out.lines)
        orig_rd(ctx)
        counts["S30 MESSAGE_BATTLE_END_RESCUE_DEADNUM"] += 1
        if any("【肉体回収】" in ln.text for ln in ctx.out.lines[n0:]):
            counts["S30 ロストキャラの発見（肉体回収）"] += 1

    sc._rescue_deadnum = rd
    wrap_plain(sc, "_hatujou_to_hairan", lambda ctx, r: (
        counts.update(["S32 HATUJOU_TO_HAIRAN 成功"]) if ctx.state.result[0] == 1 else None
    ))
    return counts


_STYLES = {"連続": 1, "装甲": 2, "撹乱": 3, "重撃": 4, "広範": 5, "全力": 6, "知略": 7, "設置": 8, "使役": 9, "反撃": 10}


def _set_style(state, data, style: str) -> None:
    """`--style`（テスト用の人工的な初期状態）：全キャラの CDFLAG:i:距離:戦闘スタイル（距離 1〜3）を設定する。"""
    idx = data.index_of("CDFLAG2", "戦闘スタイル")
    for i in range(1, state.charanum):
        for dist in (1, 2, 3):
            state.charas[i].cdflag[(dist, idx)] = _STYLES[style]


def _bosses_cleared(state) -> None:
    """`--bosses-cleared`（人工状態）：全ボスのビットを寝かせ、ラスボス（Ｋ触手）出現中にする
    （BATTLE_COM_AFTER.ERB:266–276 の FLAG:101 = 1 と同じ値。メッセージ・経験等は通らない）。"""
    state.flag[100] = 0
    state.flag[101] = 1


def _seisan_unlock(state, data) -> None:
    """`--seisan-unlock`（S28b、人工状態）：全キャラの欲望 3・露出癖 2・マゾっ気 2・魅了経験 100 にして特別活動の全項目を解放する
    （ACTION_SEISAN.ERB:23–42 の条件。調教・アイドル下積み等の経緯は通らない）。"""
    for i in range(1, state.charanum):
        c = state.charas[i]
        c.abl[data.index_of("ABL", "欲望")] = 3
        c.abl[data.index_of("ABL", "露出癖")] = 2
        c.abl[data.index_of("ABL", "マゾっ気")] = 2
        c.exp[data.index_of("EXP", "魅了経験")] = 100


def _corrupt(state, data, who: int) -> None:
    """`--corrupt N`（テスト用の初期状態）：キャラ N を開局時点で悪堕ち（CFLAG:0 = 3）にする。支配者はボス 1
    （CFLAG:20 = 0〔ボス〕、CFLAG:21 = 1：PRISON.ERB:335–388 の陥落と同じ持ち方）、陥落経験 +1、CFLAG:23 = 0。
    口上・容姿変更・経験値付与などの陥落時演出は通さない（原作の途中経過ではない人工的な状態）。"""
    c = state.charas[who]
    c.cflag[0] = 3
    c.cflag[20] = 0
    c.cflag[21] = 1
    c.cflag[23] = 0
    c.exp[data.index_of("EXP", "陥落経験")] += 1


def _input_choice(session, policy, buttons):
    """成就 PRINTW 僅確認；不得以舊選項額外消耗策略 RNG。"""
    if getattr(session.out, "achievement_wait", None) is not None:
        session.input(0)
    else:
        session.input(policy.choice(buttons) if buttons else 0)


def run_one(data, narration, seed: int, preset: str, max_shop: int, max_steps: int, save_dir: Path,
            enable_intimidation: bool = False, setup=None, enable_akuoti: bool = False, corrupt: int = 0,
            style: str = "", config_preset: int = 1, clear_bits: tuple = (), actions: tuple = (101, 102, 103)) -> dict:
    """`setup(state)`：開局直後に状態を変える（テスト用）。"""
    policy = random.Random(seed)
    s = GameSession(data, save_dir, rng=GameRng(seed), narration=narration)
    s.input(0)
    s.input(0 if preset == "default" else 1)
    s.input(1000)  # CHARA_MAKE_MAIN：不改設定、直接完成。
    s.input(config_preset)  # HEROINE_PRESET（S24）
    for f, b in clear_bits:
        s.state.flag.set_bit(f, b, False)
    if enable_intimidation:
        s.state.flag[804] |= 1 << 10
    if enable_akuoti:
        s.state.flag[804] |= (1 << 1) | (1 << 9)
    if corrupt:
        _corrupt(s.state, data, corrupt)
    if style:
        _set_style(s.state, data, style)
    if setup is not None:
        setup(s.state)
    shops = 0
    defeated_at: int | None = None
    gameover_at: int | None = None
    reason = "上限"
    steps = 0
    mark = len(s.out.lines)
    while steps < max_steps:
        steps += 1
        st = s.state
        if st is not None and defeated_at is None and any(st.charas[i].cflag[0] == 1 for i in range(1, st.charanum)):
            defeated_at = shops
        if st is not None and gameover_at is None and st.flag[0] == 0:  # CHANGE_GAMEOVER_MODE 後
            gameover_at = shops
        if s.phase == Phase.TITLE and steps > 1:  # S27：ENDING_3 → RESETDATA → BEGIN TITLE
            reason = "タイトル復帰"
            break
        if s.phase == Phase.HALTED:
            text = next((ln.text for ln in reversed(s.out.lines) if ln.text.startswith(HALT_PREFIX)), "")
            reason = text[len(HALT_PREFIX):].rstrip("）")
            break
        try:
            if s.phase == Phase.SHOP:
                shops += 1
                if shops > max_shop:
                    reason = "上限"
                    break
                for i in range(1, st.charanum):
                    s.input(i)
                    s.input(policy.choice(actions))
                mark = len(s.out.lines)
                s.input(100)
                continue
            new = s.out.lines[mark:] if len(s.out.lines) >= mark else s.out.lines[-40:]
            buttons = [v for ln in new for (_, v) in ln.buttons]
            if not buttons:
                buttons = [v for ln in s.out.lines[-40:] for (_, v) in ln.buttons]
            mark = len(s.out.lines)
            _input_choice(s, policy, buttons)
        except Exception as exc:  # noqa: BLE001（例外も停止原因として集計）
            reason = f"例外: {type(exc).__name__}: {exc}"
            break
    else:
        reason = "步數上限"
    return {"seed": seed, "reason": reason, "shops": shops, "defeated_at": defeated_at, "gameover_at": gameover_at}


def summarize(results: list[dict], preset: str, key_len: int = 40) -> None:
    """停止原因・SHOP 次數・事件次數の集計を表示（`--load` で分割実行の結果を合算するときも使う）。"""
    counts: Counter = Counter()
    games_with: Counter = Counter()
    for r in results:
        counts.update(r.get("events", {}))
        games_with.update(r.get("events", {}).keys())
    n = len(results)
    shops = [r["shops"] for r in results]
    lost = [r for r in results if r["defeated_at"] is not None]
    print(f"preset={preset} games={n}")
    print(f"SHOP 次數：平均 {sum(shops) / n:.2f}／最多 {max(shops)}")
    after = [r["shops"] - r["defeated_at"] for r in lost]
    print(f"敗北局 {len(lost)}" + (f"／敗北後 SHOP 平均 {sum(after) / len(after):.2f}" if after else ""))
    go = [r for r in results if r["gameover_at"] is not None]
    go_after = [r["shops"] - r["gameover_at"] for r in go]
    print(f"ゲームオーバーモード進入 {len(go)}" + (f"／進入後 SHOP 平均 {sum(go_after) / len(go_after):.2f}／最多 {max(go_after)}" if go else ""))
    print("停止原因：")
    for k, v in Counter(r["reason"][: key_len] for r in results).most_common():
        print(f"  {v:4d}  {k}")
    print("強制發生事件（總次數／發生局數）：" if counts else "強制發生事件：なし")
    for k in sorted(counts):
        print(f"  {counts[k]:5d}／{games_with[k]:3d}  {k}")
    if go:
        print("停止原因（ゲームオーバーモード進入局）：")
        for k, v in Counter(r["reason"][: key_len] for r in go).most_common():
            print(f"  {v:4d}  {k}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--preset", choices=("default", "tokusou"), default="default")
    p.add_argument("--config-preset", type=int, choices=(0, 1, 2, 3), default=1,
                   help="HEROINE_PRESET の選択（0 引き継ぎ・1 基本・2 淫獄・3 クズ市民）")
    p.add_argument("--clear-bit", action="append", default=[], help="開局直後に消す FLAG の bit（例 802:4）")
    p.add_argument("--seeds", default="0-249")
    p.add_argument("--max-shop", type=int, default=200)
    p.add_argument("--max-steps", type=int, default=100000)
    p.add_argument("--key-len", type=int, default=40)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--enable-intimidation", action="store_true")
    p.add_argument("--enable-akuoti", action="store_true")
    p.add_argument("--dump", help="各局の結果を JSON Lines で書き出す（分割実行用）")
    p.add_argument("--load", nargs="+", help="--dump の出力を読んで合算表示だけする")
    p.add_argument("--corrupt", type=int, default=0, help="開局時に悪堕ちにするキャラ番号（テスト用）")
    p.add_argument("--bosses-cleared", action="store_true", help="開局直後に FLAG:100 = 0・FLAG:101 = 1（人工状態）")
    p.add_argument("--style", choices=tuple(_STYLES), default="", help="開局時に全キャラ・全距離の戦闘スタイルを設定（テスト用）")
    p.add_argument("--actions", default="101,102,103", help="SHOP で各キャラに予約する行動の候補（S28a）")
    p.add_argument("--seisan-unlock", action="store_true", help="開局直後に特別活動の全項目を解放する（人工状態：S28b）")
    a = p.parse_args(argv)
    if a.load:
        results = []
        for path in a.load:
            with open(path, encoding="utf-8") as fp:
                results.extend(json.loads(line) for line in fp if line.strip())
        summarize(results, f"(--load {len(a.load)} 件)", a.key_len)
        return 0
    counts = install_event_counters()
    games_with: Counter = Counter()
    data = load_game_data(default_csv_dir())
    narration = CatalogNarrationService(default_csv_dir().parent / "ERB", data)
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for seed in _parse_seeds(a.seeds):
            before = Counter(counts)
            nfail = len(narration.failures)
            r = run_one(data, narration, seed, a.preset, a.max_shop, a.max_steps, Path(tmp) / str(seed), a.enable_intimidation,
                        enable_akuoti=a.enable_akuoti, corrupt=a.corrupt, style=a.style,
                        config_preset=a.config_preset,
                        setup=(_bosses_cleared if a.bosses_cleared
                               else (lambda st: _seisan_unlock(st, data)) if a.seisan_unlock else None),
                        clear_bits=tuple(tuple(int(x) for x in t.split(":")) for t in a.clear_bit),
                        actions=tuple(int(x) for x in a.actions.split(",")))
            for msg in narration.failures[nfail:]:  # S29：catalog の実行時失敗（回復して「見つからない」扱い）
                counts[f"catalog 実行時失敗 {msg[:60]}"] += 1
            r["events"] = dict(counts - before)
            games_with.update(r["events"].keys())
            results.append(r)
            if a.verbose:
                print(r, flush=True)
    if a.dump:
        with open(a.dump, "w", encoding="utf-8", newline="\n") as fp:
            for r in results:
                fp.write(json.dumps(r, ensure_ascii=False) + "\n")
    summarize(results, f"{a.preset} config={a.config_preset}", a.key_len)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
