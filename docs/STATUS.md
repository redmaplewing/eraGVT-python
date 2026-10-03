# 現況（唯一真相，≤120 行）

更新：2026-10-03（S28c1）

## 已完成（各階段細節見 git log 與 wiki）

- 基線：`source/earGVP/`（原作，唯讀）、`reference/emuera-1824/`（引擎原始碼，查證用）。
- **S01** 原作分析 wiki（`docs/wiki/era/`）＋骨架、CSV 載入器。**S02** 狀態模型（`docs/wiki/python/state.md`）、JSON 存讀檔、文字輸出層。
- **S03** 引擎規格查證、新遊戲、SHOP Web（`python -m eragvt`）、存讀檔（0–19＋自動 99）。
- **S04** 行動（休憩・鍛錬・出撃）與 TURNEND／EVENTSHOP（`docs/wiki/era/actions.md`）。**S05** 戰鬥核心。**S06** 拘束・性攻擊・敗北 → 幽閉。
- **S07** 口上／地の文 catalog（`eragvt.narration`，`docs/wiki/python/narration.md`）。**S08** 幽閉（`docs/wiki/era/prison.md`）。
- **S09** 身體資料（`docs/wiki/era/body-profile.md`）。**S10** 開局改回原作預設路徑（`docs/wiki/era/flow.md` §1）。
- **S11** 拡張度・いちゃラブ（`docs/wiki/era/gaping.md`）、模擬腳本 `tools/sim.py`。**S12** ゲームオーバーモード（`flow.md` §9）。
- **S13** 妊娠・出産・子供（`docs/wiki/era/pregnancy.md`）。**S14** 動画流出＋動画サイト視窗（catalog INPUTS／GOTO）。
- **S15** 戰後レイプ・自慰系。**S16** ＳＰ変身・バースト。**S17** 寄生。**S18** 強制發生事件（脅迫・夜這い・子触手）。
- **S19** 悪堕ちキャラ（`docs/wiki/era/akuoti.md`）：淫謀・洗脳／悪堕ちキャラ戰。**S20** 襲撃／救援イベント戰（`game.raid`）＋裁決修正 6 項＋斜體。
- **S21** 共用 RESULT＋触手拘束具＋悪堕ち容姿＋防衛力負數裁決（`docs/wiki/python/result.md`、`eragvt.game.corruption`）。
- **S22** 共用 RESULTS（`docs/wiki/python/result.md`）：不存檔、名乗り改竄讀 RESULTS:2、BATTLE_COM_AFTER:1159 同步。
- **S23** [反撃]スタイル（`battle/hangeki.py`，`--style 反撃` 人工模擬）。
- **S24** 設定畫面／開局プリセット／GLOBAL（`eragvt.game.config`，`docs/wiki/era/flow.md` §10）。
- **S25** ステータス畫面（`eragvt.game.status_screen`／`status_talent`／`colorbar`／`export_csv`；5 頁＋頁內指令，入口 SHOP [110]・戰鬥 [800]・HEROINE_PRESET [20]〜；控えメンバー一覧 SHOP_SHOW_STATUS_RESERVE_LIST は未實作表示）。
- **S26** FLASHNEWS（`eragvt.game.flashnews`，SHOP_FLASHNEWS.ERB 全體）。**S26b** 事件戰ニュースの前回 RESULTS:0 を照原作、3003／3004 MISSION_CHECKER の括弧修正。
- **S27** ラスボス（Ｋ触手）＋結局（`docs/wiki/era/lastboss.md`；模擬：預設 249 上限＋1 HATUJOU、敗北後 192.92）。
- **S28a** 拠点防衛・戦闘支援・情報収集・スケジュール（SHOP [160]）・戦闘基礎 Lv5 變身能力・拉致監禁表示・ACTION_MAIN 終端（下節）。

- **S28b** 特別活動（`eragvt.game.seisan`：ACTION_SEISAN＋特別活動/ 全部、地の文 catalog；下節）。
- **S28c1** 自由行動（`eragvt.game.pastime`／`pastime_school`：ACTION_PASTIME＋一般自由行動事件 12 檔；下節）。

## S28a〜S28c1 內容（`docs/wiki/era/actions.md`「S28a／S28b／S28c1 補足」）

- S28a：`action.guard`／`support`、`eragvt.game.gather`（情報収集 4 種＋ACTION_TRANSFORMATION_SELECT）、`eragvt.game.schedule`（CFLAG:110〜113）、
  SENGIUP Lv5、SHOP_SHOW_SITUATION_LIST:126、`Step.FALLTHROUGH`、`Ctx.globals`。DEVIATION D4（:142 SQRT 負→0）。
- S28b：`seisan.seisan`（選單・CFLAG:111 スケジュール・週末ライブ）、`calc_seisan`（係数表・LOSEBASE・共用 RESULT:0〜1）、9 活動
  （アルバイト 4 種〜ライブ公演）、AFTER_PILL／NINSIN_HANTEI、CFLAG:282／281／283／285／400／825・SAVESTR:21〜26（FLASHNEWS の AV／写真集）・FLAG:853。
  catalog：VARSIZE（ERH CONST）・`__INT_MAX__`・hook（`SEISAN_HOOK_LINES`：FLAG:900／TARGET／EXP）・REF 引数の読み出し → 地の文 58 函式全部可執行。
- S28c1：`pastime.pastime`（編入・變身選擇「気晴らし」・選單・CFLAG:113 排程・派發・PASTIME_REST・魅了經驗）、街／遠出／運動／學校、告白、
  悪堕ち遭遇（D4）、淫気応急＋CALC_INKIOKYU；S28c2 的前段（NANPA／SAKE_NANPA 判定、PASTIME_CHIKAN 乘車〜抵抗）也已翻，本編停止。
  本文中心的 25 函式走 catalog（hook `PASTIME_HOOK_LINES` 41 行）。`seisan._dot_after` 訂正為 RESULT 不變（DOT_AFTER は `RETURN RESULT`）。
- 測試共 1745 個（S28c1：`tests/test_pastime.py` 61）。

### 模擬（seed 0–249，`--max-shop 200`，4 並列分批）

- 基準（`--actions` 既定 101–103）：預設 249 上限＋1 HATUJOU、敗北後 192.92／GO 後 187.51 ＝ S27／S28a と同一。
- S28a `--actions 101,102,103,105,106,107`：預設 247 上限・2 HATUJOU・1 タイトル復帰；初期セット 250 上限。
- S28b `--actions 101,102,103,104,105,106,107`：預設 249 上限・1 HATUJOU（敗北後 189.40／GO 後 180.87）；初期セット 248 上限・2 タイトル復帰
  （ENDING_3）。新停止 0、佔位 0。特別活動次數（預設／初期セット）：アルバイト 303／324、研究 313／305、雑魚触手退治 313／257、
  アイドル活動 303／286（全部レベル 0〜1）、援助交際 6／9、公衆便所 0／1、AV・枕営業・ライブ 0（ランダム方針では欲望・魅了経験が育たない）。
- `--actions 104 --seisan-unlock`（人工：欲望 3・露出癖 2・マゾっ気 2・魅了経験 100、預設 100 局 `--max-shop 100`）：AV 536、公衆便所 534、
  援助交際 566、枕営業 539、ライブ 106、アイドル 452、妊娠判定 547（受精 57）；停止は既存の HATUJOU 1 のみ、佔位 0。

- S28c1 `--actions 101〜108`：預設 95 上限・120 ナンパ・18 痴漢・16 酒ナンパ（S28c2 停止）・1 タイトル復帰；初期セット 142 上限・97 ナンパ・
  9 痴漢・2 酒ナンパ。新停止は S28c2 本編のみ、佔位 0、例外 0。次數（預設／初期セット）：街 221／281、遠出 226／268、運動 220／261、
  學校開始 92／0（完了 59）、淫気応急 90／134（處女喪失 20／24）、悪堕ち遭遇判定 58／75（發生 0：悪堕ちキャラ無し）、KOKURARE 43／66（交際 0）、
  部活選択 80／0、人気投票 14、写真 16、ナンパ判定 →1 137／109、痴漢乘車 318／268。`--actions 101〜107` 再跑 ＝ S28b と同一。

### 狀態畫面內仍會停止

P1 [11]→[1] 呼び名手入力（INPUTS）、[12] 一人称設定畫面、[13] 各項的手入力／ランダム命名；P3 [0] 武器カスタマイズ；
P4 父親 CFLAG:9 指向不存在的ボス／ラスボス／モブ；HEROINE_PRESET [20]〜[29] 的不存在角色（原作也報錯）；色指定 R//G//B 的 16 進・指數表記。

### 設定項打開後會碰到未移植系統（S24，`flow.md` §10；預設 config 1 全 OFF）

[34] 雑魚戦（802 bit4）→ MOB_TENTACLE_BATTLE 停止；[78] 裏プロフィール（805 bit6）→ MAKESEXUALPROFILE 停止；[11]／[15]〜[17] 調教ステータス表示
（801 bit1／5〜7）→ 戰鬥中停止；[54] 返り血（803 bit4）→ SUPART_BLOOD 停止；[72] 触手の子種からも娘 → 命名 INPUTS 停止；
[35] クズ市民・[55] ラスボス強化 無作用（所在系統未移植）。[10]／[14] 素質表示 S25 起、[79] 有害ブログ S26 起生效。
`--config-preset 2／3` 模擬（S24）：250 局全部停止於雑魚戦。

## 下一步

- **自主推進（使用者指定 2026-10-02，依序）**：~~S22 RESULTS 共用~~ → ~~S23 [反撃]スタイル~~ → ~~S24 設定畫面／プリセット~~ → ~~S25 狀態畫面~~
  → ~~S26 FLASHNEWS~~ → ~~S26b RESULTS:0 殘值~~ → ~~S27 ラスボス～結局~~ → S28 未移植行動（~~S28a 防衛・支援・情報収集等~~ → ~~S28b 特別活動 SEISAN~~ → ~~S28c1 自由行動＋一般事件~~ → **S28c2 ナンパ・酒ナンパ・痴漢本編**）。
  其他候選：引き継ぎ（SUCCESSION.ERB，クリア後の停止點）、天使の樹（引き継ぎ後のみ）、ランダム命名畫面、SHOP [112] 衣裝設定、
  SHOP 子選單（[111] CHARA_POWERUP：SHOP.ERB:253、[113] DRUG_PREPARATION：:264、[180] TSUIKAYOUSEI_NORMAL（加入引退有り）：:294）。
- 已裁決（2026-10-02）：名乗り改竄的 RESULTS:2 殘值照原作（S22 實作）；開局デフォルト悪堕ち的輸出丟棄維持現況。
- 已裁決（2026-10-02）：PALAM_HOSEI 殘值照原作、防衛力負數 D1〜D4（S21 實作）。已裁決（2026-10-01）：S20 的 DEVIATION 6 項＋斜體。
- 已裁決（2026-09-30）：拡張度初期值照原作；S13 苗床出産的 static LOSEDEF 等怪處照原作。
- 口上 catalog 待擴充：改狀態的口上（hook 化）、入れ子內 $ラベル 的 GOTO（`KOJO_AEGI.ERB` $ＭＡＸ２，199 函式）、STRDATA、未實作式中関数。
- deviations.md 需裁決：振り解く `LOCAL:O` と同類の SCORE:150 `O`（S27）、口上的狀態副作用、口上 catalog 實行時失敗的回復、S08 以後新增項、S28c1 的 2 項（夜間排程早送り、Null 時停止）。

## 仍會停止的分岐（`NotImplementedError` → Web 停止）

S23 模擬（含 [反撃] 人工設定）皆無停止。登記但罕見：
- 悪堕ち：悪堕ち戰中 TENTACLE_ACCESS 的數值鍵（安全網）。
- 襲撃／救援：生存ラスボス 0 での襲来（原作無限ループ）、RAID_HANTEI のデバッグ入力、原作でも CodeEE になるエラー路。
- ラスボス・結局（S27）：クリア後の引き継ぎ（SUCCESSION）、天使の樹（裏ボス：遭遇・形態變化・攻撃・幽閉・表示）、ENDING 後の JUMP SHOW_SHOP（原作もエラー）。
- 幽閉：TS 性別變化。
- 妊娠・子供：TS 変身キャラ妊娠時的女體化、子供名字等的手入力（INPUTS）與ランダム命名畫面、デバッグモード的妊娠確率輸入。
- 情報収集（S28a）：クズ市民戰（事件の捜査 config 802 bit5／仲間の捜索で監禁場所特定）、デバッグ入力；SENGIUP Lv5 的變身後名設定 [1]。
- ACTION_MAIN 由 EVENTTURNEND 經 JUMP 而終端（雜魚戰候補なし：原作也錯誤，目前無法到達）。
- 自由行動（S28c1）：ナンパ／酒ナンパ／痴漢本編（MESSAGE_PASTIME_NANPA／SAKE_NANPA／CHIKAN：S28c2）。
- 夜這い：TS キャラ的 `_ABLUP` 女体受容取得、`%CALLNAME:ARG%` 指向不存在角色（原作也報錯）。
- 開局：HEROINE_PRESET 的 [30]（相関関係）、2 択畫面的 [300]（ゲームの説明）。狀態畫面內的停止見上節。設定項造成的停止見上表。
- 戰鬥 PALAM 表示（FLAG:801 bit 5）、觸手服（ACTTENTACLESUIT・運動快感）、雜魚／クズ市民／事件戰／エンドレス、
  ボスの返り血（SUPART_BLOOD）、デバッグ模式、`HATUJOU_TO_HAIRAN` 地の文。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（整體「暫時維持」，S06 以後新增項待裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局：預設（NORMAL＋汎用キャラ 3 名おまかせ）與初期セット「特装戦隊」，HEROINE_PRESET 可選 0〜3；其他初期セット／キャラメイク畫面的手動設定未移植。
- 可玩範圍：休憩・鍛錬（含スケジュール）・出撃・拠点防衛・戦闘支援・情報収集・特別活動・自由行動（ナンパ等本編除外；含拘束戰鬥、拡張度、敗北後幽閉與救出、戰後レイプ、襲撃／救援イベント戰）、夜間いちゃラブ・自慰、
  妊娠・出産・子供、全滅後的ゲームオーバーモード、ラスボス戰～ENDING_2（引き継ぎで停止）、日數超過 ENDING_3（回標題）。
- 初期セット選項的角色身體資料為 0（原作同樣不生成），戰鬥中女性敏捷 0・攻擊 2 倍（原作行為，是否偏離待決定）。
- COUNT 仍未與 Python 共用（catalog 專用暫存，deviations「口上 catalog 的顯示簡化」）；RESULT／RESULTS 已共用。
