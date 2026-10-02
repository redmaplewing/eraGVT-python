# S21：共用 RESULT 陣列（照原作的殘值）＋触手拘束具＋悪堕ち容姿

使用者裁決（2026-10-02）：悪堕ちキャラ幽閉的 PALAM_HOSEI 殘值**照原作**；本階段一次完成触手拘束具與悪堕ち容姿。路徑相對 `source/earGVP/ERB/`。

## Part A：共用 RESULT 陣列（照原作）
背景：`COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS_PRISON`:314–343 在 CFLAG:20 == 2 時沒有分岐 → 函式結束只把 RESULT:0 設 0
（`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs`:61–67），`EVENT_PALAM_UP.ERB`:134–140 讀到的 RESULT:1–11 是殘值
（S20 調查結論見 `docs/wiki/bridge/unresolved.md`）。目前 `prison/event.py:125` 停止。
1. 在遊戲狀態加一個共用的整數 RESULT 陣列（大小照引擎定義，查 reference 並附行號）。**先查證**：存檔是否包含 RESULT、讀檔／BEGIN 時是否重設，
   據此決定是否存檔與何時清除。
2. 列出原作中會寫 RESULT:1 以後的所有來源（用精確 pattern 全域 grep，先看總筆數）：多值 RETURN（口上以外 84 處、口上 10 處）、
   `RESULT:n =` 的直接代入、會寫多格 RESULT 的內建命令（逐一查 reference 確認）。對其中**已移植**的函式／位置，讓 Python 實作同步寫入共用陣列
   （寫入順序、格數與原作一致；未寫到的格子保留）。清單與對應 Python 位置寫進 wiki（`docs/wiki/python/state.md` 或新頁）。
3. `TENTACLE_ACCESS_PRISON` 的 PALAM_HOSEI 在 CFLAG:20 == 2 時：RESULT:0 = 0、讀共用陣列的 1–11，解除停止點；unresolved.md 該條結案。
4. 也一併檢查已登記為「讀前一次 RESULT」的既有處（例：deviations.md S19「TENTACLE_SAKUSEI 用前一次的 RESULT」），若目前是用局部推導實作，
   確認與共用陣列一致或改為讀共用陣列。

## Part B：触手拘束具
停止點：`battle/source_check.py:805`（強制裝着 `MESSAGE_SUBEVENT_BATTLE_SETTENTACLECLOTH`，事件戰時間到後 23%）、`source_check.py:106`
（拘束具による被姦 `SUBEVENT_BATTLE_ACTTENTACLECLOTH`）、`restraint.py:1327`（COMF103:160–175 素股焦らし失敗文）。
照原文移植裝着條件、裝着後的衣裝狀態（`武器と衣装/衣装関連/CLOTH_WEAR.ERB`、`CLOTHDATAインナー.ERB` 的相關部分）、每回合／戰鬥中的效果、
解除方式，以及其他已移植檔案中讀觸手拘束具的分岐（全域搜尋確認）。

## Part C：悪堕ち容姿
停止點：`prison/event.py:480`（CORRUPT_CHANGE_LOOKS_MAIN）、`opening.py:121`、`party.py:126`（RECOVER_CORRUPTION）。
`ヒロイン関連/悪堕ち/CORRPUTION.ERB` 全體與 `CORRUPTION_RECOVER.ERB`、地の文 `地の文/MESSAGE_AKUOTI.ERB` 的 CORRUPT／STAIN 系（走 S07 catalog）。
依賴的プロフィール系統：只移植容姿變化與回復實際用到的部分；有 UI 的地方照「跳過 UI 走原作預設路徑」。

## 測試（table-driven，expected 由 ERB 推導）
- 共用 RESULT：多值 RETURN 後殘值保留、函式結束 RESULT:0 = 0；PALAM_HOSEI 悪堕ち分岐讀到正確殘值（重現 S20 調查中的代表路徑）。
- 触手拘束具：裝着條件、效果、解除；悪堕ち容姿：變化與回復的狀態差異。

## 模擬
`tools/sim.py` 預設、初期セット、`--enable-akuoti`、`--corrupt 3` 各 250 場（seed 0–249，`--max-shop 200`；可分批）：
停止原因與 S20／S19 對照（含 S20 未重跑的悪堕ち系，確認 SQRT 停止已消失），寫進 STATUS。

## 完成條件
pytest 全綠；**先把 STATUS 壓縮到 ≤120 行**（已完成階段各一行）再更新；deviations、unresolved 更新。結束時務必送出三段報告。
