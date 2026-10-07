"""素質の表示：`ヒロイン関連/TALENT_INFO.ERB@TALENT_INFO`:5–526（説明文）と `ヒロイン関連/CHARA_STATUS.ERB`
`@SHOW_STATUS_TALENT`:251–953（素質一覧）・`@PRINT_TALENT_CATEGORY`:968–1152。路徑相對 `source/earGVP/ERB/`。

表示のみ（RAND なし；代入は関数の静的変数と RESULTS:0〔SEIKAKU_CHECK "STRING"：模型化しない〕だけ）。
TALENT_INFO の表は ERB の SELECTCASE（`CASE n`／`CASE a TO b` → `RETURNF "…"`）から機械的に抽出したもの（行番号付き）。
"""

from __future__ import annotations

from .counting import count_loop

from .action import Ctx, config_check_screen
from .battle.core import is_girly
from .battle.ninsin import check_pregnant
from .chara_common import is_female, is_male, seikaku_check, talent

# --- TALENT_INFO.ERB ------------------------------------------------------------------------

_TALENT_INFO: dict[int, str] = {
    -999: "人工的な子宮を持っている",  # :10
    -11: "子育てを行っている。束の間の休息",  # :13
    -10: "出産に備えて入院中",  # :16
    -9: "生還が絶望視されるため、ＫＩＡ扱いとなった",  # :19
    -5: "メンタルダウンして自室に引きこもっている",  # :22
    -4: "クズ市民に誘拐されて行方不明中",  # :25
    -3: "敵に心酔し寝返っている",  # :28
    -2: "敵に操られている",  # :31
    -1: "敵に捕まって行方不明、いわゆるＭＩＡ",  # :34
    0: "乙女の証。清純度が好評価になるが、失った場合は苦痛が伴う",  # :37
    1: "母乳を分泌する体質",  # :40
    2: "失禁してしまいやすい",  # :43
    3: "恥辱が溜まりやすい",  # :46
    4: "妊娠できない",  # :49
    5: "エッチなことに耐性ができない",  # :52
    10: "後方支援もできる万能型だが恐怖に弱い。気力△、敏捷○、知性◎。倒錯しにくい",  # :55
    11: "人一倍シャイなタイプ。最も敏捷が伸びやすい高機動型。性耐△、防御○、敏捷◎。倒錯しにくい",  # :58
    12: "恐怖にも苦痛にも屈さないアタッカーだが、前のめりでガードが甘い。攻撃◎、防御×。怒りやすい",  # :61
    13: "体力に優れるぶん、休憩回数が少なくて済む。作戦を考えるのは苦手。体力◎、知性×。諦観しにくい",  # :64
    14: "後方支援もこなせる防御型。多少のことでは動じない。防御◎、敏捷性×、知性◎。消沈しにくい",  # :67
    15: "何事もそつなくこなす。足りないのは根性。体力△、気力△、攻撃○、防御○、敏捷○、知性△。動揺しにくい",  # :70
    16: "最後まで諦めない耐久型だが、エッチなことには弱い。気力◎、性耐×、知性○。冷静になりやすい",  # :73
    17: "エッチなことに対する耐性が非常に高い。性耐◎、攻撃△。消沈しにくい。刻印で怯みにくい",  # :76
    18: "能力や耐性は悪くないが、すぐに諦めるのが珠にキズ。体力○、気力×、防御○、知性○。倒錯しにくい",  # :79
    19: "扱いやすい性能をしているが、知性は伸びにくい。体力○、気力○、性耐○、知性△。高揚しやすい",  # :82
    20: "苦痛に対して非常に高い耐性を持つが、羞恥心は強い。気力○、性耐△。怒りやすい",  # :85
    21: "弱点がなく、精神面が非常にタフで随一の耐性を持つ。能力補正なし。諦観しにくい",  # :88
    22: "耐久力と知性を両立しており苦痛に強い。気力○、性耐○、防御△、知性○。冷静になりやすい",  # :91
    23: "敏捷が伸びるので便利だが、普段の余裕の態度は実は強がり。体力○、敏捷○。高揚しやすい",  # :94
    24: "正面からぶつかって相手を捩じ伏せるアタッカー。性耐×、攻撃○、防御○。動揺しにくい",  # :97
    25: "アタッカーとして優秀だが耐久力の低さがネック。体力×、気力△、性耐○、攻撃○、敏捷○。高揚しやすい",  # :100
    26: "根性は十分。エッチなことにも強いが、実は苦痛に最も弱い。気力○、性耐○。諦観しにくい",  # :103
    27: "非常に高い攻撃補正を持つが、心の内に弱さを抱えている。体力○、攻撃◎、敏捷△、知性△。怒りやすい",  # :106
    100: "PALAM:快Ｃが上がりやすい",  # :109
    101: "PALAM:快Ｃが上がりにくい",  # :112
    102: "PALAM:快Ｖが上がりやすい",  # :115
    103: "PALAM:快Ｖが上がりにくい",  # :118
    104: "PALAM:快Ａが上がりやすい",  # :121
    105: "PALAM:快Ａが上がりにくい",  # :124
    106: "PALAM:快Ｂが上がりやすい",  # :127
    107: "PALAM:快Ｂが上がりにくい",  # :130
    110: "胸で与える快感が少ないが、快Ｂが上がりにくい",  # :134
    111: "胸で与える快感が多いが、快Ｂが上がりやすい",  # :137
    112: "PALAM:潤滑が上がりやすい",  # :140
    113: "PALAM:潤滑が上がりにくい",  # :143
    114: "回復量が増えるが、鍛錬効率が少し落ちる",  # :146
    115: "回復量が減るが、鍛錬効率が少し上昇する",  # :149
    116: "敏捷にプラス補正。攻撃と振りほどきにマイナス補正",  # :152
    117: "攻撃にプラス補正。敏捷と振りほどきにマイナス補正",  # :155
    150: "恭順、欲情、屈服に補正。戦闘中に体が竦んで行動できなくなることがある",  # :158
    151: "潤滑、欲情、恥情に補正",  # :161
    152: "（未実装）",  # :164
    153: "PALAM:快Ｃが上がりやすい。夜這いイベントが発生するようになる",  # :167
    154: "PALAM:快Ｖが上がりやすい。夜這いイベントが発生するようになる",  # :170
    155: "PALAM:快Ａが上がりやすい。夜這いイベントが発生するようになる",  # :173
    156: "PALAM:快Ｂが上がりやすい。夜這いイベントが発生するようになる",  # :176
    159: "妊娠している。胎児が大きくなると出撃が出来なくなる",  # :179
    160: "触手に寄生された状態。戦闘中に体が竦んで行動できなくなることがある",  # :182
    161: "触手の苗床と化した状態。出産しやすくなり、産む触手の数も増える",  # :185
    162: "身も心も触手に屈服した状態。敗北すると即座に寝返る",  # :188
    180: "近距離での戦闘力が上昇し、近距離技能が成長しやすくなる。近距離以外が若干苦手になる",  # :191
    181: "近距離での戦闘力が低下し、近距離技能が成長しにくくなる。近距離以外が若干得意になる",  # :194
    182: "中距離での戦闘力が上昇し、中距離技能が成長しやすくなる。中距離以外が若干苦手になる",  # :197
    183: "中距離での戦闘力が低下し、中距離技能が成長しにくくなる。中距離以外が若干得意になる",  # :200
    184: "遠距離での戦闘力が上昇し、遠距離技能が成長しやすくなる。遠距離以外が若干苦手になる",  # :203
    185: "遠距離での戦闘力が低下し、遠距離技能が成長しにくくなる。遠距離以外が若干得意になる",  # :206
    186: "エアストライク使用時に攻撃の直撃率がアップし、空中戦技Lvも一段階上昇する",  # :209
    187: "エアストライク使用時に攻撃の直撃率がダウンし、空中戦技Lvも一段階低下してしまう",  # :212
    200: "変身能力があるかどうか",  # :220
    300: "女性なのにペニスが生えている",  # :228
    301: "正義のヒロインの証！一部コマンドが使用不可になる代わりに人気度が上がりやすくなる。純潔度評価もアップ",  # :232
    302: "肉体が幼いまま性徴しない",  # :236
    303: "性耐性が残っている限り触手の精液による妊娠を防ぐ",  # :240
    304: "妙にエッチな目に合ってる気がする・・・",  # :243
    400: "男性であることを示す素質",  # :247
    401: "変身すると性別が逆転する",  # :251
    403: "自分が女性であることを受け入れてしまった状態",  # :255
    404: "変身時にふたなりになる",  # :259
    405: "オトコでありながら女の子にしか見えない",  # :263
    406: "変身時に男の娘になる",  # :267
    507: "手足のない人豚、ほとんどの行動を実行できない",  # :271
    508: "理性を失った植物状態、全ての行動を実行できない",  # :275
    600: "経験値効率がアップ、情報収集の効率がダウン",  # :280
    601: "情報収集の効率がアップ、不審人物に狙われやすい",  # :284
    602: "経験値効率がアップ、戦闘支援を受けたときの効果ダウン",  # :288
    603: "戦闘支援の効果アップ、戦闘支援を行ったときの消費アップ",  # :292
    604: "屈服が上昇しやすいが、不審人物に狙われにくい",  # :296
    605: "屈服が上昇しにくいが、屈服刻印がLv3以上になると…",  # :300
    606: "習得が上昇しにくいが、性行為で消耗しにくくなる",  # :304
    607: "習得が上昇しやすいが、性行為で消耗しやすくなる",  # :308
    608: "攻撃を直撃させると気力が回復するが、同時に欲情も増加",  # :312
    609: "マゾっ気が成長しやすい",  # :316
    610: "理性強度-2　苦痛が上昇しにくいが、恭順が上昇しやすい",  # :320
    611: "理性強度+2　屈服が上昇しやすいが、欲情が上昇しにくい",  # :324
    612: "戦意強度-2　屈服が上昇しにくいが、恐怖が上昇しやすい",  # :328
    613: "戦意強度+2　恐怖が上昇しにくいが、欲情が上昇しやすい",  # :332
    614: "恭順が上昇しにくいが、恥情が上昇しやすい",  # :336
    615: "恥情が上昇しにくいが、欲情が上昇しやすい",  # :340
    616: "夜這いが発生しにくくなる",  # :344
    617: "男性が相手でも女性が相手でも平気で夜這いができる",  # :348
    618: "男性に対して夜這いが発生しにくくなる",  # :352
    619: "女性に対して夜這いが発生しにくくなる",  # :356
    620: "人気度が上昇しやすいが、恭順も上昇しやすい",  # :360
    621: "人気度が上昇しやすいが、屈服も上昇しやすい",  # :364
    622: "人気度が上昇しやすいが、苦痛も上昇しやすい",  # :368
    623: "人気度が上昇しやすいが、恥情も上昇しやすい",  # :372
    624: "人気度が上昇しやすいが、恐怖も上昇しやすい",  # :376
    625: "欲情、屈服が上昇しにくいが、恥情と恐怖がとても上昇しやすい",  # :379
    800: "交際している相手",  # :382
    801: "学校に通う学生の身分",  # :386
    810: "キャラの家族関係",  # :390
    811: "キャラの細かい特徴",  # :394
    812: "キャラの外見の特徴",  # :398
    999: "原作ありキャラの判定用",  # :402
    1100: "拘束された際に油断させやすい/魅了経験が上昇しにくい",  # :406
    1101: "出撃時にボス触手が出現しやすい/襲撃イベントのターゲットにされやすく、観衆が出現しやすい",  # :410
    1102: "攻撃の直撃率が6%上昇/拘束された際に油断させにくい",  # :414
    1103: "戦闘開始時にEXゲージが２つ溜まる/休憩時の回復量が少し低下",  # :418
    1104: "戦闘中に一度だけ絶対回避/攻撃-5",  # :422
    1105: "攻撃,防御,敏捷+5/性耐性-10,洗脳、悪堕ちしやすくなる",  # :426
    1106: "攻撃+10/性耐性-5,洗脳、悪堕ちしやすくなる",  # :430
    1107: "戦闘中と休憩時の回復量が上昇/知性-5",  # :434
    1108: "先制率上昇,知性+10/攻撃,防御,敏捷-5",  # :438
    1109: "クリティカル率+6%/知性-10,妊娠しやすい",  # :442
    1110: "全能力+10,昼間の回復量アップ/昼間に行動制限",  # :446
    1200: "ピンチで直撃率とクリティカル率+12%/攻撃,防御,敏捷,知性ボーナス-5",  # :450
    1201: "特別活動と情報収集の効率アップ/攻撃,防御,敏捷,知性ボーナス-5",  # :454
    1202: "クリティカル被弾防止,気絶防止/特別活動と戦闘支援に参加不能",  # :458
    1203: "攻撃+5,「振り解く」の成功率アップ/「振り解く」使用時に疲労蓄積",  # :462
    1204: "防御+5,空中ダッシュゲージが１つ増加/着地時に疲労蓄積",  # :466
    1205: "空中ダッシュを使用しても疲労が蓄積しない/移動系コマンド実行時に疲労蓄積",  # :470
    1206: "敏捷+5,着地ペナルティ無効/「振り解く」の成功率ダウン",  # :474
    1207: "常にバースト攻撃が使用可能/バースト攻撃使用時に追加で疲労蓄積",  # :478
    1208: "バースト攻撃の威力アップ/バースト攻撃使用時に追加で疲労蓄積",  # :482
    1209: "状態異常耐性/粘液,波動ダメージ増大,妊娠しやすい",  # :486
    1210: "消耗しても行動成功率が低下しにくい/EXゲージが増加しにくい",  # :490
    1211: "疲労しても回復量が低下しにくい/EXゲージが増加しにくい",  # :494
    1212: "時間経過で疲労回復/休憩時の回復量が少し低下,妊娠しにくい",  # :498
    1213: "知性+10/体力,気力,性耐性-5",  # :502
    1214: "先制率上昇,雑魚撃破時の探索度上昇量アップ/知性-5",  # :506
    1215: "直撃率とクリティカル率+3%/防御,敏捷-5",  # :510
    1216: "人気度と魅了経験が上昇しやすい/襲撃イベントのターゲットにされやすく、観衆が出現しやすい",  # :514
    1217: "搾精攻撃で与えるダメージアップ/戦闘や幽閉時に獲得する珠の量が増加",  # :518
    1218: "空中での回避率+25%/空中ダッシュ使用時に疲労蓄積",  # :522
}
_TALENT_INFO_RANGES: tuple[tuple[int, int, str], ...] = (
    (190, 193, "対応する部位への性的な接触を防ぐ結界"),  # :216
    (201, 249, "キャラの種族を示す素質"),  # :224
)


def talent_info(arg: int) -> str:
    """`@TALENT_INFO(ARG)`（#FUNCTIONS）：該当 CASE が無ければ ""（RETURNF なしで終端）。"""
    if arg in _TALENT_INFO:
        return _TALENT_INFO[arg]
    for lo, hi, text in _TALENT_INFO_RANGES:
        if lo <= arg <= hi:
            return text
    return ""


# --- CHARA_STATUS.ERB@SHOW_STATUS_TALENT --------------------------------------------------------

_STATE_TAGS = {  # :275–322 CFLAG:0 → (HTML 表示, PRINT 表示, TALENT_INFO の番号)
    1: ("[幽閉中]", "[幽閉中]", -1),
    2: ("[洗脳]", "[洗脳]", -2),
    3: ("[悪堕ち]", "[悪堕ち]", -3),
    4: ("[誘拐中]", "[誘拐監禁中]", -4),
    5: ("[憂鬱中]", "[憂鬱中]", -5),
    9: ("[死亡]", "[死亡]", -9),
    10: ("[入院中]", "[入院中]", -10),
    11: ("[育児中]", "[育児中]", -10),  # :319（育児中も -10 の説明：原作どおり）
}
_BREAST_SMALL = {2: "[絶壁]"}  # :353–365 それ以外は [貧乳]
_BREAST_BIG = {5: "[奇乳]", 4: "[魔乳]", 3: "[超乳]", 2: "[爆乳]"}  # :366–396 それ以外は [巨乳]
_FUTANARI = {3: "[天然ふたなり]", 2: "[寄生ふたなり]"}  # :412–436 それ以外は [ふたなり]
_KOUSAI = {1: "片思い", 2: "彼氏持ち", 3: "婚約", 4: "人妻", 5: "未亡人"}
_GAKUSEI = {1: "小学生", 2: "中学生", 3: "高校生", 4: "大学生"}
_KAZOKU = {1: "弟持ち", 2: "妹持ち", 3: "兄持ち", 4: "姉持ち", 5: "幼い息子", 6: "幼い娘", 7: "年頃の息子", 8: "年頃の娘"}
_ACCESSORY = {1: "メガネっ娘", 2: "アホ毛", 3: "お嬢様"}
_GAIKEN = {1: "安産型", 2: "むちむち", 3: "イカ腹", 4: "スレンダー", 5: "巨尻", 6: "爆尻"}
_SEIBETSU = {1: "完全女体化", 10: "封印男体化", 11: "強制女体化"}


def _skip_talent(i: int) -> bool:
    """:325 個別表示しない番号（性格・変身能力〜種族・オプション・オトコ・性格系 600〜799・社交 800〜899・900 以降）。"""
    return (10 <= i <= 27 or 200 <= i <= 206 or 250 <= i <= 299 or i == 400 or 600 <= i <= 799 or 800 <= i <= 899
            or i >= 900)


def show_status_talent(ctx: Ctx, who: int, arg1: int = 0, arg2: int = 0) -> None:
    """`@SHOW_STATUS_TALENT, ARG, ARG:1 = 0, ARG:2 = 0`:251–953。ARG:1：0 = ステータス画面、1 = 鍛錬、2 = キャラメイク。
    ARG:2 ≠ 0 なら HTML_PRINT の title（説明のポップアップ）付き。CONFIG_CHECK_SCREEN_F(0)（FLAG:801 bit0）で 2 形式。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[who]
    names = data.names["TALENT"]
    T = lambda n: talent(data, c, n)  # noqa: E731
    if config_check_screen(st, 0) == 0 or arg1 == 2:
        _show_talent_list(ctx, who, arg1, arg2)
        return
    # :642–953 カテゴリ別表示
    out.printl("◆素質" if arg1 == 0 else "素質")
    s = ("" if arg1 else "　") + "基本："  # :657 `\@ARG:1?#　\@基本：`
    if is_male(data, c):
        s += f"<nonbutton title='{talent_info(400)}'>[オトコ]</nonbutton>"
    elif T("ふたなり") in (3, 2, 1):
        s += f"<nonbutton title='{talent_info(300)}'>{_FUTANARI.get(T('ふたなり'), '[ふたなり]')}</nonbutton>"
    else:
        s += "<nonbutton title='女性であることを示す素質'>[女]</nonbutton>"
    if T("男の娘") == 1:
        s += f"<nonbutton title='{talent_info(405)}'>[男の娘]</nonbutton>"
    if T("処女") == 2 and is_female(data, c):
        s += f"<nonbutton title='{talent_info(0)}'>[聖処女]</nonbutton>"
    elif T("処女") == 1 and is_female(data, c):
        s += f"<nonbutton title='{talent_info(0)}'>[処女]</nonbutton>"
    if T("初心") == 1:
        s += f"<nonbutton title='{talent_info(5)}'>[初心]</nonbutton>"
    if T("変身時ＴＳ") > 0:
        s += f"<nonbutton title='{talent_info(401)}'>[変身時ＴＳ]</nonbutton>"
    if T("変身時ふたなり") > 0 and T("変身能力") > 0 and c.cflag[1] == 0:
        s += f"<nonbutton title='{talent_info(404)}'>[変身時ふたなり]</nonbutton>"
    if T("女体受容") > 0:
        s += f"<nonbutton title='{talent_info(403)}'>[女体受容]</nonbutton>"
    if T("変身時男の娘") == 1:
        s += f"<nonbutton title='{talent_info(406)}'>[変身時男の娘]</nonbutton>"
    for i in count_loop(ctx.state, 250, 201):  # :691–694 種族
        if c.talent[i] > 0:
            s += f"<nonbutton title='{talent_info(i)}'>[{names.get(i, '')}]</nonbutton>"
    if arg1 == 0:  # :695–698 SEIKAKU_CHECK "STRING"（該当なしは「ランダム」）
        k = seikaku_check(data, c)
        s += "[" + (names.get(k, "") if k else "ランダム") + "]"
    out.html_print(s)

    def cat(category: str, tv: int = 0, sub: int = 0) -> None:
        _print_talent_category(ctx, category, arg1, arg2, tv, sub)

    if T("清純派") == 1:
        cat("精神", 301)
    for i in range(600, 650):
        if c.talent[i] > 0:
            cat("精神", i)
    for i in range(1, 4):
        if c.talent[i] > 0:
            cat("肉体", i)
    if T("ロボっ子") > 0 and T("未熟") != 2 and is_female(data, c):  # :748–749
        cat("肉体", -999)
    if T("未熟") > 0:
        cat("肉体", 4, 2 if is_male(data, c) else T("未熟") - 1)
    elif T("未熟") == -1:
        cat("肉体", 4, -2 if is_male(data, c) else -1)
    if T("嬲られ体質") > 0 and is_girly(ctx, who):  # :765–766
        cat("肉体", 304)
    for i in range(112, 116):
        if c.talent[i] > 0:
            cat("肉体", i)
    if T("アクセサリ") in (1, 2):
        cat("肉体", 811, T("アクセサリ"))
    for i in (110, 111):
        if c.talent[i] > 0:
            cat("肉体", i, c.talent[i])
    for i in (116, 117):
        if c.talent[i] > 0:
            cat("肉体", i)
    if c.cflag[1] > 0 and T("変身時外見") > 0:  # :795–799
        cat("肉体", 812, T("変身時外見"))
    elif T("外見") > 0:
        cat("肉体", 812, T("外見"))
    if T("性別変化") in (1, 10, 11):
        cat("肉体", 900, T("性別変化"))
    for i in list(range(100, 108)) + list(range(150, 157)):  # 性癖
        if c.talent[i] > 0:
            cat("性癖", i)
    for i in range(180, 200):  # 戦闘
        if c.talent[i] > 0:
            cat("戦闘", i)
    if T("避妊結界") > 0:
        cat("戦闘", 303)
    cat("状態", -998, c.cflag[0])  # :861
    if check_pregnant(ctx, who) > 0:  # :864–868
        cat("状態", 159, 0)
    elif T("妊娠") == 5 and c.cflag[222] < 11:
        cat("状態", 159, 1)
    for i in range(160, 180):
        if c.talent[i] > 0:
            cat("状態", i)
    for i in range(350, 400):  # :882–885 社交
        if c.talent[i] > 0:
            cat("社交", i)
    for name, n in (("交際相手", 800), ("学生", 801), ("家族関係", 810)):
        if T(name) > 0:
            cat("社交", n, T(name))
    if T("アクセサリ") == 3:
        cat("社交", 811, 3)
    for i in range(500, 550):  # :910–913 負傷
        if c.talent[i] > 0:
            cat("負傷", i)
    for i in range(1100, 1300):  # :946–949 FEAT
        if c.talent[i] > 0:
            cat("FEAT", i)
    cat("")  # :952 終了処理


def _show_talent_list(ctx: Ctx, who: int, arg1: int, arg2: int) -> None:
    """:255–641（CONFIG_CHECK_SCREEN_F(0) == 0 か キャラメイク）：素質を [名前] で並べる。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[who]
    names = data.names["TALENT"]
    T = lambda n: talent(data, c, n)  # noqa: E731
    female = is_female(data, c)
    male = is_male(data, c)
    buf = ["◆素質" if arg1 == 0 else "　　所持素質：" if arg1 == 2 else "素質"]  # :256–262（`LOCALS = 素質    ` は代入の trim で末尾空白なし）

    def add(text: str, title: str) -> None:
        if arg2:
            buf[0] += f"<nonbutton title='{title}'>{text}</nonbutton>"
        else:
            out.print(text)

    if arg2:  # :263–270
        buf[0] += "<br>"
    else:
        out.print(buf[0])
        buf[0] = ""
        if arg1 != 1:
            out.printl()
    if arg1 == 2:
        out.print("　　　　　　 ")  # :273
    tag = _STATE_TAGS.get(c.cflag[0])  # :275–322
    if tag is not None:
        if arg2:
            buf[0] += f"<nonbutton title='{talent_info(tag[2])}'>{tag[0]}</nonbutton>"
        else:
            out.print(tag[1])
    for i in count_loop(ctx.state, 1000):  # :324–473
        v = c.talent[i]
        if v > 0:
            if _skip_talent(i):
                pass
            elif i == 3 and male:
                add("[生えてない]", talent_info(i))
            elif i == 4:
                if T("未熟") == 1:
                    if T("ロボっ子") > 0 and female:
                        add("[人工子宮]", talent_info(-999))
                    add("[未熟]", "射精できない" if male else talent_info(i))
                elif T("未熟") == 2:
                    add("[不妊]", talent_info(i))
            elif i == 110:
                add(_BREAST_SMALL.get(T("貧乳"), "[貧乳]"), talent_info(i))
            elif i == 111:
                add(_BREAST_BIG.get(T("巨乳"), "[巨乳]"), talent_info(i))
            elif i == 159:
                if check_pregnant(ctx, who) > 0:
                    add("[妊娠]", talent_info(i))
                elif T("妊娠") == 5 and c.cflag[222] < 11:
                    add("[着床]", talent_info(i))
            elif i == 300:
                add(_FUTANARI.get(T("ふたなり"), "[ふたなり]"), talent_info(i))
            elif i == 402 and T("変身時ＴＳ") == 0:
                pass
            elif i == 404 and (T("変身能力") < 1 or c.cflag[1] > 0):
                pass
            else:
                add(f"[{names.get(i, '')}]", talent_info(i))
        elif i == 4:  # :445–472
            if v == 0 and T("ロボっ子") > 0 and female:
                add("[人工子宮]", talent_info(-999))
            if T("未熟") == -1 and config_check_screen(st, 4) > 0:
                if T("ロボっ子") > 0 and female:
                    add("[人工子宮]", talent_info(-999))
                add("[性徴促進]", "薬品によって精通を迎えた" if male else "薬品によって初潮を迎えた")
    if arg2:  # :474–478
        buf[0] += "<br>"
    else:
        out.printl()
    if arg1 == 2:
        out.print("　　　　　")  # :480
    has600 = sum(c.talent[i] > 0 and 600 <= i <= 699 for i in count_loop(ctx.state, 1000)) > 0  # :482–486
    if arg1 != 1 and has600:
        if arg2:
            buf[0] += "<shape type='space' param='150'>"
        else:
            out.print("   ")  # :491
        for i in count_loop(ctx.state, 1000):
            if 600 <= i <= 699 and c.talent[i] > 0:
                add(f"[{names.get(i, '')}]", talent_info(i))
    has800 = sum(c.talent[i] > 0 and 800 <= i <= 899 for i in count_loop(ctx.state, 1000)) > 0  # :504–508
    if arg1 != 1 and has800:
        if arg2 and not has600:
            buf[0] += f"<shape type='space' param='150'><nonbutton title='{talent_info(800)}'>"
        elif arg2:
            buf[0] += f"<nonbutton title='{talent_info(800)}'>"
        elif not has600:
            buf[0] += "   "
        if T("交際相手") in _KOUSAI:
            buf[0] += f"[{_KOUSAI[T('交際相手')]}]"
        if arg2:
            buf[0] += f"</nonbutton><nonbutton title='{talent_info(801)}'>"
        if T("学生") in _GAKUSEI:
            buf[0] += f"[{_GAKUSEI[T('学生')]}]"
        if arg2:
            buf[0] += f"</nonbutton><nonbutton title='{talent_info(810)}'>"
        if T("家族関係") in _KAZOKU:
            buf[0] += f"[{_KAZOKU[T('家族関係')]}]"
        if arg2:
            buf[0] += f"</nonbutton><nonbutton title='{talent_info(811)}'>"
        if T("アクセサリ") in _ACCESSORY:
            buf[0] += f"[{_ACCESSORY[T('アクセサリ')]}]"
        if arg2:
            buf[0] += f"</nonbutton><nonbutton title='{talent_info(812)}'>"
        g = T("変身時外見") if c.cflag[1] > 0 else T("外見")  # :569–597
        if g in _GAIKEN:
            buf[0] += f"[{_GAIKEN[g]}]"
        if arg2:
            buf[0] += "</nonbutton><br>"
        else:
            out.printl(buf[0])
    elif arg2:  # :604–609
        buf[0] += "<br>"
    else:
        out.printl()
    if arg1 == 2:
        out.print("　　　　　　 ")  # :612
    has_feat = sum(c.talent[1000 + i] > 0 and 100 <= i <= 299 for i in count_loop(ctx.state, 299)) > 0  # :614–618（REPEAT 299：COUNT 0〜298）
    if arg1 != 1 and has_feat:
        if arg2:
            buf[0] += "<shape type='space' param='300'>"
        else:
            out.print("      ")  # :623
        for i in count_loop(ctx.state, 299):
            if 100 <= i <= 299 and c.talent[1000 + i] > 0:
                add(f"[{names.get(1000 + i, '')}]", talent_info(1000 + i))
    if arg2:  # :634–639
        buf[0] += "<br>"
    else:
        out.printl()
    if arg2:
        out.html_print(buf[0])


def _print_talent_category(ctx: Ctx, category: str, indent: int, popup: int, tv: int = 0, sub: int = 0) -> None:
    """`@PRINT_TALENT_CATEGORY, CATEGORY_STR, INDENT_VAR, POPUP_VAR, TALENT_VAR, SUB_TALENT`:968–1152。

    `#DIM`（DYNAMIC なし）の変数は呼び出し間で保持される。PRINT_STR・COUNT_VAR・CATEGORY_STR:1 は SHOW_STATUS_TALENT が
    毎回最後に "" で呼ぶ終了処理（:952）で初期状態に戻るので、ここでは SHOW_STATUS_TALENT の 1 回ごとに持つ
    （`st.temp.locals` の "PRINT_TALENT_CATEGORY"）。SUB_STR:0 は -998（状態）で CFLAG:0 が SELECTCASE に無い値
    （-1 救出直後・5 など）のとき代入されず前回の値が残るので、呼び出しをまたいで保持する。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    mem = st.temp.locals
    key = ("PRINT_TALENT_CATEGORY", 0)
    s = mem.get(key)  # type: ignore[assignment]
    if not isinstance(s, dict):
        s = {"print": "", "count": 0, "cat": "", "sub0": ""}
        mem[key] = s  # type: ignore[assignment]
    head = "" if indent else "　"  # `\@INDENT_VAR?#　\@`

    def flush() -> None:
        if popup:
            out.html_print(s["print"])
        else:
            out.printl(s["print"])

    if category != s["cat"]:  # :979–989
        if s["count"] > 0:
            flush()
        s["count"] = 0
        s["print"] = head + category + "："
        s["cat"] = category
    if category == "":  # :993–996 VARSET CATEGORY_STR
        s["cat"] = ""
        return
    sub1 = talent_info(tv)  # :998
    sub0 = s["sub0"]
    names = data.names["TALENT"]
    screen4 = config_check_screen(st, 4) > 0
    if tv == -998:  # :1001–1020
        if sub == 0:
            s["sub0"] = ""
            return
        sub0 = {1: "幽閉中", 2: "洗脳", 3: "悪堕ち", 4: "誘拐中", 9: "死亡", 10: "入院中", 11: "育児中"}.get(sub, sub0)
    elif tv == -999:
        sub0 = "人工子宮"
    elif tv == 4 and sub == 1:
        sub0 = "不妊"
    elif tv == 4 and sub == 2:
        sub0 = names.get(4, "")
        sub1 = "射精できない"
    elif tv == 4 and sub == -1 and screen4:
        sub0, sub1 = "性徴促進", "薬品によって初潮を迎えた"
    elif tv == 4 and sub == -2 and screen4:
        sub0, sub1 = "性徴促進", "薬品によって精通を迎えた"
    elif tv == 110 and sub in (2, 1):
        sub0 = "絶壁" if sub == 2 else "貧乳"
    elif tv == 111 and sub in (5, 4, 3, 2, 1):
        sub0 = {5: "奇乳", 4: "魔乳", 3: "超乳", 2: "爆乳", 1: "巨乳"}[sub]
    elif tv == 159 and sub == 1:
        sub0 = "着床"
    elif tv == 800:
        sub0 = _KOUSAI.get(sub, sub0)
    elif tv == 801:
        sub0 = _GAKUSEI.get(sub, sub0)
    elif tv == 810:
        sub0 = _KAZOKU.get(sub, sub0)
    elif tv == 811:
        sub0 = _ACCESSORY.get(sub, sub0)
    elif tv == 812:
        sub0 = _GAIKEN.get(sub, sub0)
    elif tv == 900:
        sub0 = _SEIBETSU.get(sub, sub0)
    else:
        sub0 = names.get(tv, "")
    s["sub0"] = sub0
    if popup:  # :1136–1140
        s["print"] += f"<nonbutton title='{sub1}'>[{sub0}]</nonbutton>"
    else:
        s["print"] += f"[{sub0}]"
    s["count"] += 1
    if s["count"] > 5:  # :1143–1151
        flush()
        s["count"] = 0
        s["print"] = head + "　　　"
