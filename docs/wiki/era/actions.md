# 行動（CFLAG:100）的執行與影響範圍

路徑相對 `source/earGVP/ERB/`。入口 `ゲーム内_行動実行処理/ACTION.ERB@ACTION_MAIN`:6–175，一次處理一名角色
（`FLAG:799` = 目前輪到的 index），`BEGIN TURNEND` → `@EVENTTURNEND`:15 若還有人沒行動就 `JUMP ACTION_MAIN`。
Python：`eragvt.game.action`（ACTION_MAIN／REST／TRAINING）、`eragvt.game.turnend`（TURNEND／EVENTSHOP）。

## ACTION_MAIN 共通處理（每名角色）

- `FLAG:799 == 0` 時記下 `FLAG:798 = TARGET`（回合結束後 TARGET 回到這裡）並印「行動開始！」。
- `FLAG:43` = 預約「支援」且可行動的人數（≥ `CHARANUM_ACTIVE` 則 0）；`FLAG:10/11/45/48` 清 0。
- `CFLAG:0 != 0`（非無事）→ 直接 TURNEND；控え（`CFLAG:999 == 0`）→ 無聲 `REST`；無預約 → 改為休憩。
- `IS_ACTION_INCAPABLE` 成立 → `ACTION_NGREASON` 訊息 + `REST`。

## 各行動（S04 狀態）

| 行動 | 函式 | 對狀態的影響（摘要） | S04 |
|---|---|---|---|
| 出撃 101 | `ENCOUNT`／`MOB_TENTACLE_ENCOUNT` | `FLAG:41++`；遭遇 → `BEGIN TRAIN`（戰鬥），未遭遇 → TURNEND | S05 |
| 鍛錬 102 | `ACTION_TRAINING.ERB@TRAINING` | INPUT 選 0–10；體力 −`TRAINING_DOWNTAIRYOKU`、`BASEUP`（BASE 基礎值＋LEVELSTATUS）、戰技 EXP＋`SENGIUP`、`GET_EXP`（JUEL:50，升級）、`GET_SYUREN`（JUEL:20）、`CFLAG:101` = 選項 | 已翻 |
| 休憩 103 | `ACTION_REST.ERB@REST` | 體力／氣力回復（設施 FLAG:51、素質、疲勞 CFLAG:99 修正）、性耐性全滿、疲勞減少、`CFLAG:101 = -1` | 已翻 |
| 活動 104 | `ACTION_SEISAN.ERB@SEISAN` → `特別活動/SEISAN_0..8` | 變身選擇（GLOBAL:51–53）→ INPUT 選 9 種（CFLAG:111 スケジュール）→ 各活動（`CALC_SEISAN`：體力・氣力・性耐性減少、MONEY、性經驗）、JUEL、`_ABLUP 1`、變身解除；CFLAG:282／281／283／285／400／825・SAVESTR:21〜26・FLAG:853（人気度） | S28b `eragvt.game.seisan` |
| 防衛 105 | `ACTION_GUARD.ERB@GUARD` | `FLAG:41++`；`ENCOUNT`（ENCOUNT_BOSS:164–177 防衛時はボス遭遇なし → 只有洗脳／悪堕ちキャラ）＋ MOB_TENTACLE_ENCOUNT（雜魚戰 OFF 時文章のみ・探索度半分）；RESULT ≠ 0 → TRAIN；RESULT == 0：體力・氣力 −12%（SYOUHI_KEIGEN）、`FLAG:852 += 125 + Lv*2 + RAND:26` | S28a `action.guard` |
| 支援 106 | `ACTION_SUPPORT.ERB@SUPPORT` | 前線 0 人且 `FLAG:41 == 0` → 改休憩、FLAG:43−1；否則體力・氣力 ×0.24／0.18（FLAG:43 = 1／2，3 以上は MAXBASE 全量：原作どおり）×献身的 1.1、修練P 15–25、`GET_EXP((TENTACLE_LEVEL−3)/Lv*10+RAND:5)`、知性基礎 +0–2 | S28a `action.support` |
| 情報 107 | `ACTION_GATHER_INFORMATION.ERB` | 變身選擇（GLOBAL:54–56）→ 4 種（噂話／事件の捜査／情報を買う／仲間の捜索，CFLAG:112 スケジュール）→ `_ABLUP 1` → 變身解除；探索度、魅了経験、知性、`CFLAG:120–122`（コネ）、MONEY、カラダ（EXP・JUEL・處女・NINSIN_HANTEI）、CFLAG:71（拉致監禁救出）・CFLAG:23（遭遇率）；市民戰 → TRAIN（S36） | S28a `eragvt.game.gather` |
| 自由 108 | `ACTION_PASTIME.ERB@PASTIME` | 編入（DAY%30）→ 變身選擇（GLOBAL:57–59）→ 學校／街／遠出／運動（INPUT 或排程 `CFLAG:113`）、CFLAG:101（5〜20）・270・310・330〜357、TALENT:学生／交際相手／処女、EXP、FLAG:111；PASTIME_REST、魅了經驗、`_ABLUP 1`；`FLAG:73 > 0` 時 TRAIN | S28c1 `eragvt.game.pastime`（ナンパ・酒ナンパ・痴漢本編は S28c2 `eragvt.game.pastime_nanpa`） |

S28c1 起 101〜108 全部已翻（`action_main` 的最後 `NotImplementedError` 只剩不存在的預約值）。

## S28a 補足

- **BEGIN 只回一層**：`BEGIN` = SetBegin＋Return(0)（`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs@BEGIN_Instruction`:1681–1689、
  `GameProc/Process.State.cs@SetBegin`:203–228），呼叫端繼續執行，函式堆疊清空時才以最後設定的 BEGIN 轉移（`@Return`:414–421 → `@Begin`:263–311）。
  所以 GATHER_INFORMATION:88 的 BEGIN TURNEND 會被 ACTION.ERB:151–155 覆寫（FLAG:73 > 0 → TRAIN）。
- **ACTION_MAIN 終端（RESULT < 0，雜魚戰候補なし）**：JUMP 的被呼叫端結束 → JUMP 元也立即返回（`Process.State.cs@Return`:368–377）。
  USERSHOP 經由 → @USERSHOP 結束 → @SHOW_SHOP（無 EVENTSHOP；`Step.FALLTHROUGH`）；EVENTTURNEND 經由 → 原作 CodeEE「予期しないスクリプト終端」（停止）。
  雜魚戰未移植，目前到達不了（測試以 monkeypatch 確認）。
- **スケジュール**（`eragvt.game.schedule`）：SHOP [160] `@SCHEDULE`（CFLAG:110〜113 = 實行番號×10^18 + Σ項目×100^k，負值 = OFF）、
  `@RES_SCHEDULE`（STRLENFORM 位數：`Instraction.Child.cs`:504–528）。鍛錬 CFLAG:110、情報収集 CFLAG:112 使用；鍛錬的不正值判定看 CFLAG:111（原作）。
- **SENGIUP 戦闘基礎 Lv5**：非戰鬥員取得變身能力（INPUT 有 → `sengiup`／`hangeki_to_tentacle` 改為 generator）；變身後名設定 [1] 停止（FIRSTSETTING_CHARA_TRANSAFTERNAME 未移植）。
- **SHOP_SHOW_SITUATION_LIST:126** 拉致監禁中的名字用直前的 RESULT:0：USERSHOP 輸入 130 → LB 原樣返回 → ボス／ラスボス迴圈跑過則 0、
  悪堕ちキャラ幽閉表示則支配者番號；兩迴圈都沒跑（FLAG:110 = 1 等）→ 130 → 原作也添字範圍外（停止）。
- 不在範圍：`ACTIONsub_DRUG_PREPARATION`（SHOP [113]）、`TSUIKAYOUSEI_NORMAL`（SHOP INSTANT 模式）、`ACTIONsub_CHARA_POWERUP`（空檔）——都不是行動呼叫。

## S28b 補足（特別活動 `eragvt.game.seisan`）

- **選單**（ACTION_SEISAN.ERB:14–45）：援助交際＝欲望 > 0、AV＝欲望＋露出癖 ≥ 5 或 CFLAG:283 ≥ 10、公衆便所＝欲望＋マゾっ気 ≥ 5（皆需 ISHOLE）、
  魅了経験 > 99 で枕営業、さらに週末（DAY % 7 が 0／6）は [6] の代わりに [8]★ライブ公演（入力 6 も 8 に読み替え：:138–140）。
  CFLAG:111 スケジュールで実行不能 → 手入力（:70–129 の GOTO INPUT_LOOP）。SHOP の予約・`IS_ACTION_INCAPABLE` は既存のまま。
- **CALC_SEISAN**（:15–137）：係数表（SEISAN_CALC.ERH:157–197）を SEISAN_INIT の順で `EARN_TABLE` に。LOSEBASE 経由で體力・氣力に
  SYOUHI_KEIGEN、性耐性は係数 > 0 のときだけ。客数＝體力減少量（活動別の補正）、稼ぎ＝共通式（IS_PROFITABLE かつ IS_NORMAL_EARN）、
  RETURN 客数, 稼ぎ → 共用 RESULT:0〜1（`docs/wiki/python/result.md`）。
- **原作どおりの怪處**（そのまま移植）：SEISAN_INIT:8 アルバイト「失敗」に成功の係数；研究所助手・路上ライブの表示額（知性倍率・+200）は
  MONEY に入らない；公衆便所（野良犬）は表示 0＄でも CALC:85 の 1＋… が MONEY に入る；路地裏放置の経験（SEISAN_5:79–91）と
  雑魚触手退治の妊娠判定（SEISAN_2:70）は AFTER_PILL／NINSIN_HANTEI 後の RESULT:0 を読む；路地裏放置の LOST_VIRGIN は常に 0；
  ライブ公演の CHARM_BASE 等は静的変数で失敗時は前回値（初回 0）；AV タイトルの `\@変身能力 == 1?#…\@` は変身能力 1 で空。
- **他系統への書き込み**：AV → CFLAG:282（種類）・281（サンプル確認）・SAVESTR:(20+TARGET)・CFLAG:285（75%）；写真集 → SAVESTR:(23+TARGET)
  （FLASHNEWS:529–547 は 21〜25 を読む）；枕営業 → CFLAG:283（露見度）・285；公衆便所・援助交際 → CFLAG:285／825；ライブ → CFLAG:400；
  人気度 FLAG:853。CFLAG:284（動画流出）・287 は特別活動からは書かれない（grep）。UNLOCK_ACHIEVEMENT・GET_STATE_EXPUP は実績のみ（何もしない）。
- **地の文**：`MESSAGE_SEISAN_*`（58 函式）と `MESSAGE_CITIZEN_TRAIN_{KANCHO,PIG,DOG}` は catalog で全部実行可能（`narration/hooks.py`
  `SEISAN_HOOK_LINES`：FLAG:900・`TARGET=ARG`・犬プレイの EXP）。写真集タイトルは `#DIMS REF BOOK_TITLE` を実行後に読む。
- INPUT：変身選択、活動選択、生ハメの回答（SEISAN_3:304–334、想定外は黙って再入力）、AFTER_PILL、AV サンプル（:96–120、想定外は 1 回だけ警告）。

## S28c1 補足（自由行動 `eragvt.game.pastime`／`pastime_school`）

路徑 `自由/` = `ゲーム内_イベント発生/自由行動中イベント/`。
- **分工**：INPUT・派發・狀態變化為主的函式手翻（PASTIME、PASTIME_REST、SelectSchool、街に出る、遠出する、運動する、SportsPark、KOKURARE、
  悪堕ち遭遇、淫気応急＋CALC_INKIOKYU、學校本體・Afterschool・SelectClub）；本文中心、無 INPUT 的函式當地の文用 catalog 執行
  （`pastime._chinobun`）：FASHION、Fitness／Massage／Pool、遠出 8 處、AKUOTI_EVENT、改造制服 4 個、授業（CL／PE）・昼休み（含写真）・部活・
  ClubString、人気投票。狀態變化行 41 行列在 `narration/hooks.py` 的 `PASTIME_HOOK_LINES`。catalog 不可時（Null）佔位＋`_FALLBACKS`
  （FASHION／Fitness／Massage／部活可決定；Pool 的淫乱分岐與授業的狀態變化依本文亂數 → `NotImplementedError`）。
- **S28c2 的前段**：發生判定 `PASTIME_NANPA`／`PASTIME_SAKE_NANPA`、`PASTIME_CHIKAN`（乘車〜抵抗選擇，:4–465）已翻；本編
  `MESSAGE_PASTIME_NANPA`／`_SAKE_NANPA`／`_CHIKAN` 停止。街・遠出・運動・學校的結尾都呼叫 NANPA 判定，遠出・學校一定經過 CHIKAN。
- **派發**（ACTION_PASTIME:29–132）：排程 RESULT 0 學校(0)、1 隨機（晝 RAND:4 含學校／夜 1+RAND:3）、2〜4 各類隨機、5〜8 街(R-5)、9〜16 遠出(R-9)、
  17〜20 運動(R-17)、其他無事。SCHEDULE 畫面的「街：アミューズメント施設」(5) 實際是ショッピングモール（順序不同：原作どおり）。
  夜間排程到學校 → `FOR LOCAL,1,NUM_SCHEDULE_F(113)+1` 找非學校；全是學校時原作會跑 NUM_SCHEDULE_F 次（極大）後仍 0 → 夜也上學；依使用者裁決（2026-10-03）改照作者意圖：一巡找不到就隨機去處（DEVIATION）。
- **原作どおりの怪處**：PASTIME_CHIKAN 收呼叫端自己的 ARG（遠出 -1／0〜7、學校 -1／0）→ ARG == 1（遠出文）只在排程水族館、ARG == 3（通學混雑・
  CFLAG:356）只在排程植物園；`DOT_AFTER` 是 `RETURN RESULT`（RESULT 不變，S28c1 也訂正了 `seisan._dot_after`）；FitnessClub 的 `#DIM EROEVENT = 0`
  靜態 → 初次後一直 1（之後健身房不會有ナンパ）；學校 `#DIM 改造制服` 靜態不歸 0、`目的地` 在學生 0 時沿用前值；Classwork_PE 的 LOCAL（ヒップ形容）
  與 `SUIEI` 是靜態殘值；SelectClub:1579 只有輸入 0 才算歸宅；PASTIME_REST:170–172 回復遅い 的気力 +5；PASTIME_TSFLAG_OVERWRITE 無呼叫處（不移植）。
- **D4**：悪堕ち遭遇:19 `SQRT(FLAG:852)` 負數當 0（`pastime.akuoti_encounter`）。

## S28c2 補足（自由行動の本編 `eragvt.game.pastime_nanpa`）

- **範囲**：`自由/PASTIME_ナンパ.ERB@MESSAGE_PASTIME_NANPA`＋DATE／TAKEOUT／RAPE、`PASTIME_酒ナンパ.ERB@MESSAGE_PASTIME_SAKE_NANPA`＋DATE／
  TAKEOUT／RAPE／DEISUI_RAPE、`PASTIME_痴漢.ERB@MESSAGE_PASTIME_CHIKAN`＋TAKEOUT（11 関数・約 6,800 行）。
- **分工**：本文がほぼ全部で INPUT（選択肢 7 か所）と少数の状態変化が分岐の中に混ざる → 手翻せず S07 catalog で原文を実行
  （`CatalogNarrationService.run_event_gen`：INPUT で本当に中断して待つ。catalog の拡張は `docs/wiki/python/narration.md`「S28c2 追加」）。
  状態変化 72 行は `NANPA_HOOK_LINES`：代入（CFLAG:270／206／320／321／325〜328／356／825、TALENT:処女、EXP、FLAG:900）は書き込み許可で
  実行、CALL は既存の Python 移植（COMMON_PRISON・COMMON_PRISON_EXP・_ABLUP・AFTER_PILL〔INPUT〕・NINSIN_HANTEI・CALC_GANGBANG〔INPUT〕）。
  変態プレイ（`MESSAGE_CITIZEN_TRAIN_*`）・口上（KOJO_ROOT）は catalog の通常経路。catalog が無い（Null）と停止。
- **S36**：`CONFIG_CHECK_EVENT_F(5) == 1` 時的 `ENCOUNT_CITIZEN(6001)` 已接通；原作規則見 [市民戰](citizen.md)。
- **戻り値**：PASTIME_CHIKAN:455–459 は本編が持ち帰り（:1097 RETURN 1）なら RETURN 1 → 遠出・学校はそこで終わる（`pastime_chikan`）。
  ナンパ・酒ナンパの本編は RESULT を返さない（呼び出し元も読まない）。
- **原作どおり**：本編の ARG は呼び出し元の ARG（街・遠出・運動・学校の予約値）なので、ナンパの場所分岐（0／1 街・遠出、2 運動、3 学校、
  他は :409 の ELSE）や DATE の `持ち帰り先`（静的 #DIM、ARG 0〜3 以外では前回値）は予約内容で決まる。学校の合コン（:352）も学校の ARG
  （S28c1 の Python は 0 を渡していたのを訂正）。NANPA_RAPE:3087 の `CFLAG:1 > 1`（他所は `> 0`）もそのまま。

## 回合結束之後（EVENTTURNEND → BEGIN SHOP → EVENTSHOP）

`SHOP_TURNEND.ERB@EVENTTURNEND`:3–139 → `BEGIN SHOP`（此時 SystemState = Normal，會自動存檔：
`reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs`:609–611、633，`Process.State.cs`:271–273）
→ `@EVENTSHOP`:158–215（晝夜切換、回復、日期、收支）→ 自動存檔 → `@SHOW_SHOP`。

開局狀態（NORMAL＋特装戦隊、config 基本セット：FLAG:801=1、802=15、804=1、805=2、850=0）下各夜間事件：

| 事件 | 開始條件 | 開局狀態 |
|---|---|---|
| INTIMIDATION／KIDNAPPING | PRISON config bit10（OFF）／CFLAG:0 == 4 | 不觸發（S18 已移植：`eragvt.game.intimidation`） |
| PRISON | CFLAG:0 == 1 或 GAMEOVER 模式 | 不觸發 |
| BIRTH_HANTEI／GROW_HANTEI | 素質「妊娠」1/3/4/5；育兒 CFLAG:0 == 11、CFLAG:22、225 | 不觸發 |
| AKUOTI_ATTACK | CFLAG:0 == 3 | 不觸發 |
| LOVESEX_NIGHT | 夜、交際相手 1–4 | 不觸發（交際相手 0） |
| SELF_NIGHT | 夜、RAND:100 < 欲望*5 + 触手中毒*2 + 自慰中毒段階 | 機率 0 |
| YOBAI | 夜、淫核等素質或感覺 ABL ≥ 3 | 不觸發（S18 已移植：`eragvt.game.yobai`） |
| RAID_HANTEI | DAY ≥ 3、有人沒出撃／防衛、依防衛力 RAND | **會觸發** → DEVIATION 跳過 |
| PARASITE | 素質「寄生」；迴圈會把 FLAG:799 覆寫成 CHARANUM-1（SHOW_SHOP:20 歸 0） | 不觸發 |
| SMALL_TENTACLE_HANTEI | 夜、FLAG:44（子触手數）> 0 | FLAG:44 > 0 後**會觸發**（S18 起照原作：`eragvt.game.small_tentacle`） |
| BIRTH_AUTO_RANDOM | 防衛力 < 10000 時 1/(防衛力/100)：FLAG:44 += 1（已翻）；苗床死亡角色出產（未翻） | 前半會觸發（已翻） |
| ENDING | 全ボス撃破（ENDING_2）、日數超過（ENDING_3：開局 NORMAL 為 11 日目夜） | 11 日目夜觸發 → NotImplemented |
