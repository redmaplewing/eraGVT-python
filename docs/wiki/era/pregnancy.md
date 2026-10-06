# 妊娠・出産・子供（S13）

路徑相對 `source/earGVP/ERB/`。Python：`eragvt.game.battle.ninsin`（受精）、`eragvt.game.pregnancy`（進行・出産）、
`eragvt.game.child`（娘の出産・子供の加入・性徴・救出）、`eragvt.game.firstsetting`（子供のキャラ設定部品）、
`eragvt.game.relation`（相関関係）。CFLAG の意味は `●開発者向け資料/●GVTフラグ一覧.txt`:272–316（以下「一覧」）。

## 素質 妊娠（TALENT:妊娠）の値

| 値 | 意味 | 設定元 |
|---:|---|---|
| 0 | 妊娠していない | 出産で 0 |
| 1 | 触手の幼体を妊娠 | NINSIN_FLAG:227–242（幽閉中・戦闘外で即時）、NINSIN_CHECK_AFTER:171–186（戦闘後）、Ｈ触手＋排卵:150–161 |
| 2 | 触手の子種で受精（戦闘中：まだ判明していない） | NINSIN_FLAG:209／220／224 |
| 3 | 触手の子種による娘（育児機能 `CONFIG_CHECK_OTHER_F(0)` ON のみ） | 同上（RAND:100 < 50〔苗床化 75〕が外れたとき） |
| 4 | 人間（一般人・仲間）の子、無自覚 | NINSIN_FLAG:206／217（寄生されていれば 2） |
| 5 | 人間の子、自覚済み | BIRTH_HANTEI:336–344（CFLAG:222 >= 20） |

`CHECK_PREGNANT_F`（:813–820）＝ 1・3、または 5 で CFLAG:222 >= 11。出撃・防衛不可（SET_PARTYMEMBER:12–19、S08 移植済み）、
SHOP の行動制限・表示（`shop.check_pregnant`）はこれを使う。既定コンフィグ（FLAG:805 = 2：オープニング処理の CONFIG_INIT）では
育児機能 OFF なので 3 は発生せず、触手の子は 2 → 1 だけ。

## CFLAG 對照（一覧:272–316）

| CFLAG | 意味 | 主な更新 |
|---:|---|---|
| 204 | 初めて出産した | ABL_UP_BIRTH:549 |
| 219 | 愛する人（-3）の子を出産した回数 | BIRTH_DAUGHTER_HUMAN_ORIGIN:23–25／116–118 |
| 220 | 幽閉中に産んだ子触手の数 | BIRTH_TENTACLES:438（幽閉の子触手イベントが読む） |
| 221 | 前回出産（受精）からの膣出し累計 | NINSIN_HANTEI:69 加算、:144 受精で 0、出産で 0 |
| 222 | 妊娠日数×2（ターンごと +1） | BIRTH_HANTEI（苗床化 +3、幽閉中さらに +2） |
| 223 | 出産後の子触手日齢（幽閉中の出産で 1） | BIRTH_TENTACLES:436 |
| 224 | 育児日数 | GROW_HANTEI:11 |
| 225 | 子供の日齢（性徴） | ADD_CHILD:921 = 1、GROW_HANTEI:16–25 |
| 226 | 次に生まれる子の性別（1 = 男） | MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN:731／734（hook） |
| 227 | 産む触手の数 | NUM_CHILD_TENTACLE |
| 228 | 腹囲の最大増分（mm） | PREGNANT_RANDOM_SIZE |
| 230 | 父親 ID（1–99 ボス、100–198 ラスボス、200– 雑魚、-1〜-4 一般人、-101〜 仲間 = −固有番号−100） | NINSIN_HANTEI:148 |
| 231 | 子供：親（母）の種族素質番号 | ADD_CHILD:523–526 |
| 232／233 | 膣出し累計（触手／人間）＝妊娠確率の元 | NINSIN_HANTEI:72–96 |
| 241 | 避妊ピル | CHECK_HININ_F、AFTER_PILL |
| 7／9 | 子供：母親の固有番号／父親 ID | ADD_CHILD:310／701、CHECK_ALL_RELATION:961–982 |

## 狀態機

```
膣内射精 → NINSIN_HANTEI（:11–165）── 受精（RAND:1000 < PREG_PER + 100×非幽閉）
   → NINSIN_SUBMIT（屈服／恐怖の珠）→ CFLAG:230 = 父親 → NINSIN_FLAG
       戦闘中：妊娠 2 ──（戦闘終了 EVENTEND :204/:252/:300/:393）→ NINSIN_CHECK_AFTER → 妊娠 1（＋227／228）
       幽閉中（CFLAG:21 > 0）・戦闘外：その場で 妊娠 1（人間の父親なら 4）
毎ターン EVENTTURNEND:105 BIRTH_HANTEI（全キャラ、死亡 CFLAG:0 == 9 は除く）
   妊娠 1／3：CFLAG:0 == 0 かつ 222 > 9（苗床化 > 3）→ 出産直前 CFLAG:0 = 10（MESSAGE_MATANITY、SET_PARTYMEMBER）
              222 += 1（苗床化 3）、幽閉中 +2；222 > 10 で母乳体質、RAND:(30−222) == 0 かつ ≥ 10、または ≥ 15、
              または幽閉中の苗床化で RAND:2 == 0 → 出産（妊娠 3＋育児機能 → BIRTH_DAUGHTER_TENTACLE_ORIGIN、他は BIRTH_TENTACLES）
   妊娠 4：+1、6／9／12 で兆候の文、20 以上で 妊娠 5
   妊娠 5：CFLAG:0 == 0 かつ 222 > 42 → 出産直前；16 以上で母乳体質；RAND:(83−222) == 0 かつ ≥ 53、または ≥ 56 → BIRTH_DAUGHTER_HUMAN_ORIGIN
BIRTH_TENTACLES：疲労 45＋腹囲/20、出産直前なら RECOVER_TO_PARTY、幽閉中は CFLAG:220／FLAG:44 += 数（合いの子の地の文 1/4）、
   組織なら 触手の欠片（FLAG:200）+= 数 → ABL_UP_BIRTH（体力気力半減、珠、経験、初産なら体力気力の最大値 +25%、拡張度）→ _ABLUP 1
BIRTH_DAUGHTER_HUMAN_ORIGIN：病院（CFLAG:0 == 10）で $10000 あれば INPUT「[1]育てる」→ 育児中 CFLAG:0 = 11、それ以外は手放して復帰
EVENTTURNEND:107 GROW_HANTEI：育児中（11）／幽閉された娘の待ち（CFLAG:22 > 0）は 224 += 1、4 以上で RAND:2 == 0 または 10 → ADD_CHILD
ADD_CHILD：ADDCHARA 0 → 名前（INPUT）→ 一人称 → 種族（母依存）→ フィート（INPUT）→ 変身能力（人間の母なら 3/4）→
   変身後名等（INPUT）→ 素質・父親別の補正（PAPA_POWER）→ 基礎値 → 性格 → 色・髪型・年齢 6〜10・体格 → 母子とも復帰 → CHECK_ALL_RELATION
子供の性徴：CFLAG:225 = 7 で CHILD_GROW_1（未熟が取れる）、> 14 で CHILD_GROW_2（体質変化）、以降 0（止まる）
```

苗床出産（BIRTH_AUTO_RANDOM:671–746、EVENTSHOP:166）：取り込まれた（CFLAG:0 == 9）苗床化キャラが毎ターン 1/4 で子触手を産み、
防衛力（FLAG:852）が下がる。ゲームオーバーモード中も続く。

## 照原作移植的怪處

- **NUM_CHILD_TENTACLE(ARG)** は ARG を使わず TARGET の出産経験・苗床化・CFLAG:0 を読む（:579–601）。苗床出産では TARGET は
  そのとき TURNEND の TARGET（取り込まれキャラではない）。
- **BIRTH_AUTO_RANDOM の LOSEDEF は static**（`#DIM LOSEDEF,1`、VARSET LOCAL の対象外）。呼ぶたびに累積し、累積値を毎回防衛力から
  引く（2 回目以降の低下が大きくなる）。`TALENT:母乳体質 = 1`／`TALENT:膨乳改造値 += 10`（:729–732）はキャラ指定がなく TARGET に付く。
- **BIRTH_HANTEI の並べ替え**：出産直前になったキャラは SET_PARTYMEMBER で最後尾へ移る（SHIFTBACK_CHARA）が、ループは index
  （TARGET = CCOUNT）で進むので、同じ周回の日数加算は繰り上がった別キャラに行われ、移ったキャラは最後の index でもう一度処理される。
- **ABL_UP_BIRTH**：`BASE:気力 = MAX(BASE:体力/2−500, 1)` は半減後の体力から計算（:469）、`JUEL:快Ｖ／快Ｂ` は加算でなく代入（:523–524）、
  組織での ×3（CFLAG:0 == 10）は BIRTH_TENTACLES が先に RECOVER_TO_PARTY するので触手出産では起きない。
- **ADD_CHILD**：GROW_HANTEI の同じ周回の性徴処理（:16–25）は TARGET が新キャラに替わった後なので子供の CFLAG:225 が 1 → 2
  （母親の分はその周回は処理されない）。PAPA_POWER は static で「父親不明!?」分岐（CFLAG:230 が 0 や 8–99 の範囲外）は前回値を使う。
  パーソナリティの重複判定は文字列 `"CSTR:41"` 等との比較（:1059–1071、実質は空文字判定のみ）。
- **SET_FEAT_DEFAULT**：枠（FEAT_NUM）が 1 以上残れば、取得可能なフィートを **すべて** 取得する（:1767 の FOR 終端は開始時の
  候補数、候補を 1 つずつ引いて消すので全部引かれる）。
- **CHECK_ALL_RELATION**：CFLAG:7／9 からの親子設定（:576–588）は WAITFLAG を増やさないので「〜になりました」は出ない。
  母親の処女消去（:950–958）は母親の周回が子供より前なら起きない。
- **RECALC_PARTYMEMBER の RESCUE_CHILD**：施設に預けた（DELCHARA）とき `CCOUNT -= RESULT`（RESULT = −1）で 1 人余分に飛ばす。
- **PREG_PER は static**：父親 ID が 0（戦闘外・非幽閉で ARG:2 = 0）や該当する仲間がいないときは前回の確率を使う（:72–97）。

## 入口現況與剩餘停止

- TS 変身キャラの女体化（`TRANS_SEX.ERB@TS_MtoF`：NINSIN_TS_FIX:263–267、NINSIN_FLAG:248–256）。
- デバッグモードの妊娠確率入力（NINSIN_HANTEI:125–138）。
- 子供命名／變身命名／掛聲／名乗的手輸已接通；S68接`ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:515`一人稱，S69接同函式:1075–1107身體收尾，均等待真實輸入。S69只驗25歲人工尾段函式邊界，不代表完整出生／加入或B05整列，見[角色編輯](character-editor.md)。
