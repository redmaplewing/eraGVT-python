"""キャラクターデータの書き出し：`SYSTEM/キャラメイキング関連/EXPORT_CSV.ERB@EXPORT_CSV`:2–582（路徑相對 `source/earGVP/ERB/`）。

ステータス画面 PAGE2 の [0]（`SHOW_STATUS_CHARA_SELECT_PAGE2.ERB`:53–56：TARGET = ARG の後に呼ぶ）からのみ呼ばれる（全域 grep）。
TARGET のキャラ CSV 相当の文字列を画面に印字するだけ（代入は関数の LOCAL／RELATION_LIST、RAND なし）。
ログ全消去（CLEARLINE LINECOUNT）の後に出力し、最後に WAIT。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state import GameState
from .action import Ctx, config_check_maniac, seikaku_hosei
from .battle.core import fstyle_name, t
from .chara_common import seikaku_check
from .era import mod
from .relation import get_relation

Gen = Generator[None, int, None]

_KOUSAI = {1: "片思い", 2: "彼氏持ち", 3: "婚約", 4: "人妻", 5: "未亡人"}
_GAKUSEI = {1: "小学生", 2: "中学生", 3: "高校生", 4: "大学生"}
_KAZOKU = {1: "弟持ち", 2: "妹持ち", 3: "兄持ち", 4: "姉持ち", 5: "幼い息子", 6: "幼い娘", 7: "年頃の息子", 8: "年頃の娘"}
_ACCESSORY = {1: "メガネっ娘", 2: "アホ毛", 3: "お嬢様"}
_GAIKEN = {1: "安産型", 2: "むちむち", 3: "イカ腹", 4: "スレンダー", 5: "巨尻", 6: "爆尻"}
_SUBNAMES = {800: _KOUSAI, 801: _GAKUSEI, 810: _KAZOKU, 811: _ACCESSORY, 812: _GAIKEN}  # :127–193
_BODY_MOD = (11, 31, 59, 15, 16, 13, 23, 7, 53)  # :523–576 TALENT:280〜288 が 0 なら CFLAG:33 % n + 1


def exist_csv(ctx: Ctx, no: int) -> int:
    """`EXISTCSV(no, 0)`（reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs@ExistCsvMethod:320–327 →
    GameData/Variable/VariableEvaluator.cs@ExistCsv:1326–1334）：その番号のキャラ CSV があれば 1。"""
    return 1 if no in ctx.data.charas else 0


def csvbase(ctx: Ctx, no: int, idx: int) -> int:
    """`CSVBASE no, idx`（`CSVBASE_F`、コモン関数.ERB:966–969 → VariableEvaluator.cs@GetCharacterIntfromCSVData:1383–1396：
    CSV の「基礎」= Maxbase。未定義キャラは CodeEE）。"""
    d = ctx.data.charas.get(no)
    if d is None:
        raise NotImplementedError(f"CSVBASE：キャラ番号 {no} の CSV が無い（原作でもエラー）")
    return d.base.get(idx, 0)


def _item(ctx: Ctx, i: int) -> str:
    it = ctx.data.items.get(i)
    return it.name if it is not None else ""


def export_csv(ctx: Ctx) -> Gen:
    """`@EXPORT_CSV`（対象は TARGET）。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.target_chara
    names = data.names
    T = lambda n: t(ctx, c, n)  # noqa: E731
    ix = data.index_of
    out.printl("注意：本機能はCSVからキャラクターデータを自作・改造できる人向けです。")  # :9–16
    out.printl()
    out.printl("現在のキャラクターのステータスをCSVに対応した書式で出力します。")
    out.printl("データが表示されたらEMUERAの機能から「ログをクリップボードにコピー」を選択し、")
    out.printl("空のCSVファイルにコピーペーストしてください。")
    out.printl("一部保存されない情報もあります（修練Pやレベルの端数、妊娠状況など）。")
    out.printl("また、履歴ログが5000行以上あると失敗しますのでご注意ください。")
    out.printl()
    out.printl("重複しないキャラクター番号を検索します。")
    out.printl("（連続してキャラクターデータを作製している場合、CSVの再読み込みが必要です）")
    no = 0
    for k in range(200):  # :20–35
        no = k + 101
        if exist_csv(ctx, no) != 1:
            out.printl(f"キャラクター番号を「{no}」で出力します。")
            break
        if no == 300:
            out.printl("101〜300番の間に空いているキャラクター番号がないようです。")
            out.printl("キャラクター番号を「101」で出力しますが、重複しているので後から変更をしてください。")
            no = 101
            break
    out.printl()
    keep = 0  # LOCAL:2
    while True:  # $INPUT_LOOP（:38–69）
        out.printl("[0] 実行する")
        out.print("[1] 調教状況の保存範囲を変更する　現在の設定：")
        out.printl(("感度・経験なども0にしてリセット", "感度・経験のみ保存", "感度・経験・刻印・珠を保存")[keep])
        out.printl(f"[2] キャラクター番号を手動で変更する　現在の番号：{no}")
        out.printl("[999] やめる")
        r = yield
        if r == 999:
            return
        if r == 1:
            keep = (keep + 1) % 3
        elif r == 2:
            out.printl("100〜998の数値を入力してください")
            no = yield
            if exist_csv(ctx, no) == 1:
                out.printw("注意：そのキャラクター番号のキャラはすでに設定されています")
        elif r == 0:
            break
    out.clearline(out.linecount)  # :72 CLEARLINE LINECOUNT
    pl = out.printl
    pl(f"番号,{no},")  # :76–
    pl(f"名前,{c.name},")
    pl(f"呼び名,{c.callname},")
    if c.cstr[10] != "":
        pl(f"CSTR,10,{c.cstr[10]},;　苗字")
    if c.cstr[4] != "":
        pl(f"CSTR,4,{c.cstr[4]},;　一人称")
    if c.cflag[8] > 0:
        pl(f"フラグ,8,{c.cflag[8]},;　一人称設定")
    pl()
    if c.cstr[204] != "" or c.cstr[205] != "" or c.cstr[206] != "":  # :88–102
        pl(";-------年齢指定----------------")
        for k, label in ((204, "実年齢指定"), (205, "年齢指定"), (206, "変身時年齢指定")):
            if c.cstr[k] != "":
                pl(f"CSTR,{k},{c.cstr[k]},;{label}")
        pl()
    elif c.cflag[34] > 0:
        pl(";-------年齢指定----------------")
        pl(f"CSTR,204,{c.base[ix('BASE', '実年齢')]},;実年齢指定")
        pl(f"CSTR,205,{c.base[ix('BASE', '年齢')]},;年齢指定")
        pl(f"CSTR,206,{c.maxbase[ix('BASE', '年齢')]},;変身時年齢指定")
        pl()
    pl(";-------初期ステータス----------")  # :103–116
    pl(";ステータスにおける基礎値")
    sk = seikaku_check(data, c)
    for name, k in (("体力", 0), ("気力", 1), ("性耐性", 2), ("攻撃", 10), ("防御", 11), ("敏捷", 12), ("知性", 13)):
        pl(f"基礎,{name},{seikaku_hosei(sk, k, csvbase(ctx, c.no, k))},")
    pl(f"基礎,射精,{c.maxbase[ix('BASE', '射精')]},")
    pl(f"基礎,噴乳,{c.maxbase[ix('BASE', '噴乳')]},")
    pl(f"能力,レベル,{c.abl[ix('ABL', 'レベル')]},")
    pl(f"基礎,空中ダッシュ,{c.maxbase[ix('BASE', '空中ダッシュ')] + T('空中苦手') - T('空中得意')},")
    pl()
    n0 = out.linecount  # :118 LOCAL:3 = LINECOUNT
    for name in ("近距離", "中距離", "遠距離", "戦闘基礎"):
        if c.abl[ix("ABL", name)] > 0:
            pl(f"能力,{name},{c.abl[ix('ABL', name)]},")
    if out.linecount > n0:
        pl()
    pl(";-------素質--------------------")  # :129–200
    for i in range(1000):
        v = c.talent[i]
        if v != 0 and i != 200 and i < 900 and (i < 250 or i > 299):
            out.print(f"素質,{names['TALENT'].get(i, '')},{v},")
            sub = _SUBNAMES.get(i)
            if sub is not None and v in sub:
                out.print(f";　{sub[v]}")
            pl()
    pl(";-------FEAT--------------------")
    for i in range(1000, 1300):
        if c.talent[i] > 0:
            pl(f"素質,{names['TALENT'].get(i, '')},{c.talent[i]},")
    if keep >= 1:  # :207–229
        pl()
        pl(";-------感覚など----------------")
        for i in range(25):
            if c.abl[i] >= 1:
                pl(f"能力,{names['ABL'].get(i, '')},{c.abl[i]},")
        pl()
        pl(";-------経験--------------------")
        for i in range(60):
            if c.exp[i] >= 1:
                pl(f"経験,{names['EXP'].get(i, '')},{c.exp[i]},")
        if config_check_maniac(st, 16) == 1:
            for k in (35, 36):
                head = names["ABL"].get(k - 34, "")[:1]  # SUBSTRINGU ABLNAME:(COUNT - 34), 0, 1
                pl(f"フラグ,{k},{c.cflag[k]},;　{head}拡張度")
    if keep >= 2:  # :231–245
        pl()
        pl(";-------刻印--------------------")
        for i in range(100):
            if c.mark[i] >= 1:
                pl(f"MARK,{i},{c.mark[i]},")
        pl()
        pl(";-------珠----------------------")
        for i in range(20):
            if c.juel[i] >= 1:
                pl(f"JUEL,{i},{c.juel[i]},")
    pl()
    pl(";-------衣装--------------------")  # :247–280
    for k, label in ((40, "アウターなし"), (41, "アウター（変身後）なし"), (42, "インナーなし")):
        if c.cflag[k]:
            pl(f"フラグ,{k},{c.cflag[k]},;　{_item(ctx, c.cflag[k])}")
        else:
            pl(f"フラグ,{k},-1,;　{label}")
    if c.cflag[43]:
        pl(f"フラグ,43,{c.cflag[43]},;　{_item(ctx, c.cflag[43])}")
    if c.cstr[8] != "":
        pl(f"CSTR,8,{c.cstr[8]},;　アウターの名称")
    if c.cstr[9] != "":
        pl(f"CSTR,9,{c.cstr[9]},;　アウター（変身後）の名称")
    for i in range(1, 500):
        if c.equip[i] > 0:
            if i < 100:
                pl(f"EQUIP,{i},{c.equip[i]},;　{_item(ctx, i + 100)}のカスタマイズ")
            elif i < 200:
                pl(f"EQUIP,{i},{c.equip[i]},;　{_item(ctx, i)}（変身後）のカスタマイズ")
            else:
                pl(f"EQUIP,{i},{c.equip[i]},;　{_item(ctx, i)}のカスタマイズ")
    for i in range(600, 700):
        if c.equip[i] > 0:
            pl(f"EQUIP,{i},{c.equip[i]},;　{_item(ctx, i)}")
    pl()
    pl(";-------髪型--------------------")  # :282–
    for k in (12, 13, 14):
        pl(f"CSTR,{k},{c.cstr[k]},")
    pl()
    pl(";-------目つき--------------------")
    pl(f"CSTR,18,{c.cstr[18]},")
    pl()
    pl(";-------プロフィール-------------")
    trans = T("変身能力") != 0
    pl(";髪の色")
    pl(f"CSTR,30,{c.cstr[30]},")
    pl(";変身時の髪の色")
    pl(f"CSTR,31,{c.cstr[31] if trans else c.cstr[30]},")
    pl(";右目の色")
    pl(f"CSTR,32,{c.cstr[32]},")
    pl(";左目の色")
    pl(f"CSTR,33,{c.cstr[33]},")
    pl(";変身時の右目の色")
    pl(f"CSTR,34,{c.cstr[34] if trans else c.cstr[32]},")
    pl(";変身時の左目の色")
    pl(f"CSTR,35,{c.cstr[35] if trans else c.cstr[33]},")
    pl(";肌の色")
    pl(f"CSTR,36,{c.cstr[36]},")
    pl(";変身時の肌の色")
    pl(f"CSTR,37,{c.cstr[37] if trans else c.cstr[36]},")
    pl()
    pl(";-------武器定義-----------------")  # :330–336
    for k in (1, 2, 3):
        pl(f"CSTR,{14 + k},{c.cstr[4 + k]}// //{fstyle_name(ctx, st.target, k)},")
    pl()
    pl(";-------キャラフラグ------------")  # :338–343
    out.print(f"フラグ,10,{c.cflag[10]},")
    pl(";　変身能力のあるキャラの変身前の能力(デフォルトは25%)")
    out.print(f"フラグ,11,{c.cflag[11]},")
    pl(";　変身能力のあるキャラのSP変身後の能力(デフォルトは110%)")
    pl()
    # :345–358 IF GLOBAL:262 > 0（トロフィー『陰鬱ハネムーン』）：成就は未移植で GLOBAL:262 は常に 0
    # （deviations「全域資料（GLOBAL）：成就・歷代紀錄不讀不寫」）→ この節は出力されない
    if T("変身能力") == 1:  # :359–388
        pl(";-------変身能力関連------------")
        pl("素質,変身能力,1,;　変身能力あり")
        for k, label in ((2, "変身後の名前"), (3, "変身後の呼び名"), (4, "変身時のかけ声"), (5, "変身時の名乗り")):
            if c.cflag[k] > 0:
                pl()
                pl(f";{label}")
                pl(f"CSTR,{k - 2},{c.cstr[k - 2]},")
                pl(f"フラグ,{k},1,")
        pl()
    elif T("変身能力") == -1:
        pl(";-------変身能力関連------------")
        pl("素質,変身能力,-1,;　非戦闘員")
        pl()
    if T("固有キャラ") != 0:  # :389–393
        pl(";-------固有キャラ----------")
        pl(f"素質,固有キャラ,{T('固有キャラ')},")
        pl()
    rel_list: dict[int, int] = {}  # :395–418 RELATION_LIST（添字 = NO）
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        if st.charas[i].no > 0 and c.relation[i] > 0:
            rel_list[st.charas[i].no] = c.relation[i]
    if rel_list:
        pl(";-------相関関係----------")
        for i in range(st.charanum):
            if i == GameState.MASTER:
                continue
            o = st.charas[i]
            if o.no > 0 and c.relation[i] > 0:
                pl(f"相性,{o.no},{rel_list[o.no]},;{get_relation(ctx, st.target, i)}")
        pl()
    if c.cstr[40] != "" or c.cstr[41] != "" or c.cstr[42] != "":  # :419–426
        pl(";-------パーソナリティ----------")
        for k in (40, 41, 42):
            if c.cstr[k] != "":
                pl(f"CSTR,{k},{c.cstr[k]},")
        pl()
    labels = ("体力", "気力", "性耐性", "攻撃", "防御", "敏捷", "知性")
    for base, title in ((50, "キャラメイクボーナス"), (60, "遺伝ボーナス")):  # :427–460
        if any(c.cflag[base + k] for k in range(7)):
            pl(f";-------{title}----------")
            for k in range(7):
                if c.cflag[base + k]:
                    pl(f"フラグ,{base + k},{c.cflag[base + k]},;{labels[k]}")
            pl()
    if any(c.talent[i] != 0 for i in range(250, 260)):  # :461–473（PRINTL なしで終わる：原作どおり）
        pl(";-------オプション系素質----------")
        for i in range(250, 260):
            if c.talent[i] != 0:
                pl(f"素質,{names['TALENT'].get(i, '')},{c.talent[i]},")
    if any(c.talent[i] != 0 for i in range(260, 272)):  # :474–487
        pl(";-------体型数値指定----------")
        for i in range(260, 272):
            if c.talent[i] != 0:
                pl(f"素質,{names['TALENT'].get(i, '')},{c.talent[i]},")
        pl()
    if c.cflag[34] > 0:  # :488–578
        if T("体型乱数値指定") == 0 or T("体型成長曲線指定") == 0:
            pl(";-------現在の体型乱数----------")
            if T("体型乱数値指定") == 0:
                pl(f"素質,体型乱数値指定,{c.cflag[33]},")
            if T("体型成長曲線指定") == 0:
                pl(f"素質,体型成長曲線指定,{c.cflag[34]},")
            pl()
        pl(";キャラの体型をCSVに記述する場合は上記２つあればＯＫだが、")
        pl(";以下の乱数指定を利用することもできる")
        pl(";不要であれば削除すること")
        pl(";-------体型乱数指定----------")
        for k, m in enumerate(_BODY_MOD):
            i = 280 + k
            v = c.talent[i] if c.talent[i] > 0 else mod(c.cflag[33], m) + 1
            pl(f"素質,{names['TALENT'].get(i, '')},{v},")
        pl()
    elif any(c.talent[i] != 0 for i in range(280, 289)):
        pl(";-------体型乱数指定----------")
        for i in range(280, 289):
            if c.talent[i] != 0:
                pl(f"素質,{names['TALENT'].get(i, '')},{c.talent[i]},")
        pl()
    pl(";" + "-" * 85)
    pl(";EXPORT VER 0.390")
    pl(";生成終了" + "=" * 77)
    out.wait()  # :581 WAIT（表示上の待ちのみ：他の移植と同じく入力を消費しない）
