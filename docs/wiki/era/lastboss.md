# ラスボス（Ｋ触手）と結局（S27）

路徑相對 `source/earGVP/ERB/`；引擎相對 `reference/emuera-1824/Emuera/`。Python：`eragvt.game.battle.*`、`eragvt.game.ending`。

## 旗標

| 變數 | 意義 | 出處 |
|---|---|---|
| FLAG:100 | 生存ボス的 bit（1〜7） | `オープニング処理.ERB`:90–105 |
| FLAG:101 | 生存ラスボス的 bit（1 = Ｋ触手、2 = 天使の樹）；`GET_LASTBOSS_PHASE_F` = 1（==1）、1+FLAG:21（==2）、否則 0 | `汎用関数/コモン関数.ERB`:1345–1353 |
| FLAG:4 | ラスボス總數（開局 1） | 同上 :90–105 |
| FLAG:10 | 戰鬥對手種別（0 ボス、1 ラスボス、2 雑魚） | `ENEMY_TYPE_CHECK_F`（コモン関数.ERB:1356–1371） |
| FLAG:401〜／601〜 | ラスボス的蓄積ダメージ（×100）／解析度 | `BATTLE_TRAIN_AFTER.ERB`:432–439 |
| FLAG:64 | -1 = 完全殲滅（ENDING 待ち）、1〜6 = クリア済み（SCORE 總合評價） | `BATTLE_COM_AFTER.ERB`:186–188、`ENDING.ERB`:15 |
| FLAG:854 | 周回數（SCORE:749 +1；只有引き継ぎ能帶到下一周） | |
| FLAG:999 | -999 → 回標題、-997 → スコアへ（エンドレス）、-998 → ゲームオーバーモード | `ENDING.ERB` |

## 流程

1. **出現**：最後一隻ボス撃破（`BATTLE_COM_AFTER.ERB`:266–276）→ FLAG:101 = 1、`MESSAGE_BATTLE_END_LASTBOSSAPPEAR`。
2. **遭遇**：`ENCOUNT.ERB@ENCOUNT_BOSS`:309–421。探索度 ≥ ノルマ且非撃破直後（FLAG:49）時，昼 70％／夜 80％（×FLAG:47/FLAG:46），
   襲來事件 100％。候補以 GET_BOSS_ERB_NUM（7）迴圈，但 FLAG:100 = 0 所以 TENTACLE_SURVIVE_CHECK 看 FLAG:101。
   FLAG:10 = 1、HP ×LASTBOSS_KYOUKA_F（[55] 強化 ON 時 5 倍）、蓄積ダメージ（FLAG:400+n）、FLAG:16 += Lv×10、EXP:ラスボス経験 +1。
3. **戰鬥**：`TENTACLE_ACCESS`（COMMON_TENTACLE_DATA.ERB:202）在 `GET_LASTBOSS_PHASE_F() != 0` 且非雑魚／市民時一律走
   `TENTACLE_LASTBOSS_{FLAG:11}_*`（不看 FLAG:10）。Ｋ触手的資料、ATTACK_ROUTINE（防御 > 200 的對手多吐粘液、油斷時拉開距離）、
   SEX_ROUTINE（SP 性攻撃 1000〜1007／1015）、REACTION_REF、TENTACLE_SIZE（GAPING.ERB:1131–1135 的ラスボス係數）見
   `TENTACLE_LASTBOSS_1_Ｋ触手.ERB`。REACTION_REF 的呼叫端：COMABLE:996、COMF100:55、COMF103:194（ENEMY_TYPE_CHECK）、
   BATTLE_COM_AFTER:1154（GET_LASTBOSS_PHASE_F）。
4. **敗北**：幽閉 CFLAG:20 = 1、CFLAG:21 = 1。`TENTACLE_ACCESS_PRISON`:329–342：PRISON_ROUTINE 是Ｋ触手的，PALAM_HOSEI 卻是
   `TENTACLE_BOSS_1`（Ｃ触手）的（原作照搬）。未擊敗時保存蓄積ダメージ（BATTLE_TRAIN_AFTER:432–439）。
5. **撃破**：:167–193 FLAG:64 = -1、清 FLAG:101 bit → :279–306 `MESSAGE_BATTLE_END_PERFECT` → **`BEGIN TURNEND`**（不經 @EVENTEND）。
   @EVENTTURNEND:16 若還有未行動角色先回 ACTION_MAIN（FLAG:49 = 1 不會再遭遇），之後 :42 `CALL ENDING`。
6. **ENDING**（`ENDING.ERB@ENDING`:3–88）：FLAG:100 ≤ 0 且 FLAG:101 ≤ 0 且非ゲームオーバー → ENDING_2 → SCORE → FLAG:64 = 總合評價 →
   「クリアデータを記録しますか？」[0] → `SAVEGAME`（セーブ畫面；EVENTTURNEND 中 SystemState = Normal，含 __CAN_SAVE__：
   `GameProc/Process.State.cs`:76）→ 施設資金還元（:30–68）→ `JUMP SUCCESSION`（引き繼ぎ，**未移植 → 停止**）。
   讀取 FLAG:64 > 0 的存檔：`オープニング処理.ERB@EVENTLOAD`:13–14 `JUMP ENDING` → :4–5 直接到還元與引き繼ぎ。
7. **日數超過**（:74–85）：ボス期は `(FLAG:3 − 生存 + 1) × FLAG:2 − DAY + DAY:1 ≤ 0`、ラスボス期は `FLAG:1 − DAY + DAY:1 == 0`，
   且 TIME == 1（夜）→ ENDING_3 → FLAG:999 = -999 → SHOP_TURNEND:44–47 `CLEARLINE LINECOUNT`・`RESETDATA`・`BEGIN TITLE`。
   ゲームオーバーモード（FLAG:0 = 0）與「制限時間無し」不判定。
8. ENDING_6（クズ市民處刑）全作沒有呼叫者（原作註解：デッドコード），只移植函式。

## SCORE（`SCORE.ERB`）

生存（ソロ：幽閉經驗；否則 100 − 幽閉 60／洗腦・悪堕ち 30／死亡 90 各 ÷(CHARANUM−1)）、日數（(FLAG:1 − DAY)×100/FLAG:2；エンドレスは撃破數）、
純潔（被姦經驗：處女或清純派 ×1、否則 ×2、兩者皆有 −1）、性成長（無事角色的 15 種 ABL 加點 ÷ CHARANUM_SAFE）、人氣（FLAG:853）、
資產（MONEY×2＋施設＋FLAG:53 的 9 種設備〔ソロ ×3〕＋所持 ITEM 的 ITEMPRICE）。總合 = (生存＋日數＋max(純潔, 性成長)＋人氣＋資產/2＋3)/5。
:150 的 `O` 見 deviations.md。GLOBAL（最高評價、クリア回數、實績）不寫（deviations.md「全域資料」）。

## 未移植（停止）

- 天使の樹（`TENTACLE_LASTBOSS_2`）：只在周回（FLAG:854 > 0）且 HARDCORE 的Ｋ触手撃破後出現（:176–180、:270–272），需引き繼ぎ。
  形態變化（SOURCE_CHECK:40–112）、攻撃時的甲殻判定（COM_ATTACK_COMMON:59）、遭遇・幽閉・SHOP 顯示的 2 號都停止。
- 引き繼ぎ `SUCCESSION.ERB`（約 1640 行）。
- 襲來事件中生存ラスボス 0 的 `GOTO RAID_LOOP`（原作無限ループ）。
- ENDING 後 FLAG:64 != 0 的 `JUMP SHOW_SHOP`（原作亦為スクリプト終端錯誤：`GameProc/Process.SystemProc.cs@endNormal`:993–996）。
