# 悪堕ちキャラ（淫謀イベント・洗脳／悪堕ちキャラ戰）

S19。路徑相對 `source/earGVP/ERB/`。Python：`eragvt.game.akuoti`、`eragvt.game.battle.*`。照原作的怪處見
`docs/wiki/bridge/deviations.md`「原作行為」S19，未決見 `unresolved.md`。

## 角色狀態

| 變數 | 意義 |
|---|---|
| CFLAG:0 = 2／3 | 洗脳／悪堕ち（PRISON.ERB:335–357：陥落時 `CONFIG_CHECK_PRISON_F(1)` ON 才會；`触手の虜` または `F(9)` なら悪堕ち） |
| CFLAG:20／21 | 支配者：0＝ボス（21 = ボス番號）、1＝ラスボス、2＝悪堕ちキャラ（21 = その固有番號 CFLAG:240） |
| CFLAG:240 | 角色固有番號（キャラ作成時に設定） |
| FLAG:110 | 現在の敵が洗脳／悪堕ちキャラ（`ENEMY_TYPE_CHECK_F("AKUOTI")`）。勝利時のみ 0 に戻る |
| FLAG:111 | 敵（淫謀の實行者）の角色番號 |

基本セット（FLAG:804 = 1）は陥落時の洗脳／悪堕ちが OFF → 通常の遊玩では悪堕ちキャラは生まれない
（`tools/sim.py --enable-akuoti` で bit1＋bit9 を ON にできる）。

## 淫謀（`強制発生イベント/FORCE_悪堕ちキャラの淫謀.ERB`）

- `AKUOTI_ATTACK`（:5–29，`turnend.akuoti_attack`）：SHOP_TURNEND:110。候補＝CFLAG:0 = 3 かつ ISHOLE かつ
  `MIN(RAND:(SQRT(防衛力)/2+20), 100) < 昼 40／夜 20`（`&&` 短絡）。ゲームオーバーモードは防衛力 0 → 毎回合發生。
- `AKUOTI_EVENT`（:33–1711，`akuoti.akuoti_event`）：`SELECT = RAND:100` を SELECT_N:0／1（防衛力の SQRT から、:41–47）で 3 分割。
  - 市街地襲撃（DAMAGE = SQRT*20 + 防衛力*5/100）：幼稚園バス（昼のみ）／悪堕ちヒロインの狩り（×1.5）／一般女性／ロリ少女／カップル。
  - 暗躍（DAMAGE = SQRT + 防衛力*10/100）：薬品販売／動画拡散（TINPUTS は時間切れの既定路徑）／水源放流（×1.5）／ペットショップ／
    女を攫う／男を攫う。
  - 被調教系（ゲームオーバーモード以外）：TARGET＝悪堕ちキャラで PRISON_COMABLE（PRISON_EVENT の簡略版）。
  - 襲撃・暗躍は最後に TARGET を悪堕ちキャラにして COMMON_PRISON・經驗加算・`NINSIN_HANTEI, V_SEX, 20, 200`（父＝雑魚触手）。

## 洗脳／悪堕ちキャラ戰

- 遭遇 `ENCOUNT_ENEMY`（ENCOUNT.ERB:19–131）：出撃のたびに FLAG:110 = 1 にして、洗脳／悪堕ちキャラ候補がいれば
  `RAND:100 < 昼40／夜20 + 遭遇率アップ - MIN(防衛力/500, 40)`（上限 80）。HP = MAXBASE:體力 + MAXBASE:防御*(15+Lv)/2。
  變身能力持ちは變身して出てくる。
- 行動 `SELECT_ENEMY_ACTION`（ENEMY_ACTION.ERB:1073–1156）：攻撃 55／邪悪な波動 15／絡みつく 15／体液 10／距離 5（%）、
  寄生なしは絡みつく→押し倒す、体液→攻撃。性コマンドは敵の ABL を重みにした區間で選ぶ（:1172–1343）。
- 說得（COM47）：知性比 `PERCENT_CAL` で 3 段階の油断度上昇（COMF47.ERB）。入力は他の指令と同じく USERCOM 經由（unresolved.md「TRAIN の輸入」）。
- 勝利（BATTLE_COM_AFTER.ERB:312–405）：FLAG:110 = 0、悪堕ちキャラを救出（CFLAG:0 = -1）、その悪堕ちキャラに洗脳／幽閉されていた
  角色も連鎖救出（CFLAG:100 = 103）。`CONFIG_CHECK_PRISON_F(11)` ON なら連れ去られて終わり。
- 敗北（:1044–1087）：洗脳キャラ → 支配者の触手が幽閉。寄生持ち悪堕ちキャラ＋`MANIAC(13)` → 悪堕ちキャラが幽閉（CFLAG:20 = 2）。
  それ以外 → `SUBEVENT_BATTLE_RAPED_ENEMY`（屈服・恥情 2000、被姦經驗 +1）で幽閉されない。

## 觀衆（`戦闘イベント.ERB`）

悪堕ち經驗（EXP:陥落経験 > 0）があると、變身時に罵声（PERFORM_CHEERS_HATE，心境＝消沈）、被弾／回避時の觀衆反応が人気度減少側になる。
