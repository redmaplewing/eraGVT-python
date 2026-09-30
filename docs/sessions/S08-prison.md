# S08：幽閉（敗北後 → 幽閉中イベント → 脱出／救出・洗腦・悪堕ち・死亡）

## 目標
S06 的敗北後，TURNEND 在 `SET_PARTYMEMBER` 的 `SHIFTBACK_CHARA` 與之後的 `PRISON` 停止。
本階段讓「敗北 → 幽閉 → 每回合幽閉中處理 → 解除（自力脱出／救出）或轉入洗腦・悪堕ち・死亡」整條流程可玩。
路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **隊伍整理**：`ヒロイン関連/SET_PARTYMEMBER.ERB`（@SET_PARTYMEMBER、@SHIFTBACK_CHARA、@SHIFTFOWARD_CHARA），
   含 RELATION 的 SWAP 與 SWAPCHARA（S02 已有 `swap_chara`；語意查 reference 確認，含 TARGET／ASSI 等是否跟著換）。
   妊娠分岐（CHECK_PREGNANT_F）照原文移植判定；若需要的妊娠函式尚未移植，照 S06 慣例 `NotImplementedError`。
2. **幽閉本體**：`ゲーム内_イベント発生/敗北幽閉中イベント/` 全部
   （PRISON.ERB 的 @PRISON／@PRISON_EVENT／@CHECK_CONTAMINATION、COMMON_PRISON、PRISON_COMABLE、PRISON_COM*_*.ERB 17 檔）。
   以及它們呼叫的：`TENTACLE_ACCESS_PRISON`、`GET_SYUREN`、刺青系（`ヒロイン関連/CHARA_TATTOO.ERB`）、
   `TRANSFORM`（COMMON_BATTLE_FUNC.ERB:426）、`TENTACLE_LEVEL`、`GET_EXP`、`CONFIG_CHECK_PRISON_F`、
   SHOP_TURNEND.ERB:93 附近的幽閉相關判定與 :944–969 的 `MESSAGE_SHOP_PRISON`。
3. **出口**：
   - 自力脱出與救出後處理 `ヒロイン関連/AFTER_RESCUED.ERB@AFTER_RESCUED`。
   - 戰鬥指令 15「救出する」（`戦闘コマンド(ヒロイン)/COMF15.ERB` 與 COMABLE 對應條件）——若牽涉 S06 未移植的戰鬥分岐過多，
     可只做判定＋`NotImplementedError`，於報告說明。
   - 洗腦・悪堕ち：PRISON.ERB 內的轉換處理、`悪堕ち/CORRPUTION.ERB@CORRUPT_CHANGE_LOOKS_MAIN`。
   - 全滅／死亡結局 `エンディング/ENDING.ERB@ENDING_4`、`@ENDING_5`：做到遊戲結束畫面（Web 顯示結局並回標題）；
     結局文太長或牽涉未移植系統時，文字走 S07 catalog，其餘照 S06 慣例停止。
4. **文字**：`地の文/MESSAGE_PRISON.ERB`、`MESSAGE_OTHER.ERB` 的 PRISON 系、`MESSAGE_KYUUSHUTU.ERB` 一律經 S07 的
   `NarrationService.run_function` 輸出；其中的狀態變化照 S07 的 hooks 表方式移植並對照測試。
5. **Web**：幽閉中角色在 SHOP 狀態列的顯示（SHOP_SHOW_SITUATION_LIST.ERB 的幽閉部分）、幽閉中不可選為行動對象。

## 不做
- 襲撃（RAID）中的小觸手幽閉 `MESSAGE_SMALL_PRISON_*`、`CALC_GANGBANG`、自由行動／強制事件中的 PRISON 參照。
- 妊娠成立以後（下一階段）。遇到就停止並記錄。

## 查證要點
- SWAPCHARA／SWAP／VARSET LOCAL 的引擎語意（`reference/emuera-1824/...cs:行號`）。
- 幽閉判定所用 CFLAG 番號（0、30、286、320、321、999…）的意義照 CSV定数定義／原文註解，不得自行命名推測。

## 測試（table-driven，expected 由 ERB 推導）
- SHIFTBACK_CHARA：3〜4 人隊伍、各位置離脫時的順序與 RELATION。
- PRISON_EVENT：首次幽閉／第 N 日、各 PRISON_COMABLE 分岐的選擇（FixedRng）、CHECK_CONTAMINATION 閾值、
  脱出條件、洗腦／悪堕ち／死亡的轉換條件。
- 整合：敗北 → TURNEND → 幽閉 1 回 → SHOP（seed 固定）；幽閉中存讀檔往返。
- 更新 S06 的隨機方針模擬：記錄敗北後能再走多少回合、新的停止原因依頻度列進 STATUS。

## 完成條件
pytest 全綠；STATUS 更新（停止分岐清單改寫）；新 DEVIATION／UNVERIFIED 登記；
必要時 `docs/wiki/era/prison.md`（< 300 行）說明幽閉狀態機與 CFLAG 對照。
