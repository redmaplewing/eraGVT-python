# S22：共用 RESULTS（字串回傳值）陣列，照原作

使用者裁決（2026-10-02）：`CORRPUTION.ERB@CORRUPTTION_GET_NANORI_FINAL`:786–791 讀前一次 RESULTS:2 的殘值，**照原作**。
S21 已建立共用整數 RESULT 陣列（`docs/wiki/python/result.md`）；本階段以相同方式處理字串 RESULTS。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **查證引擎**：RESULTS 的大小、是否存檔、新遊戲／BEGIN／讀檔時是否清除；多值 RETURNF／`RETURN` 字串、`RESULTS:n =` 代入、
   會寫 RESULTS 的內建命令（SPLIT 不算，SPLIT 寫指定變數；STRDATA、PRINTDATA 等逐一確認；式中関数當命令用時結果進 RESULTS:0）——
   全部附 `reference/emuera-1824/...cs:行號`。
2. 在遊戲狀態加共用 RESULTS 陣列；若原作存檔包含，存檔版本升 3 並保留舊版相容（舊檔讀入時 RESULTS 為空字串）。
3. **寫入來源清單**：用精確 pattern 全域 grep（先看總筆數），列出原作中寫 RESULTS:1 以後的所有位置（口上以外約 66 行含讀取，需區分讀寫），
   以及寫 RESULTS:0 而之後有人讀「呼叫前 RESULTS」的位置。已移植者讓 Python 同步寫入；清單寫進 `docs/wiki/python/result.md`。
4. catalog（narration runtime）目前的 RESULTS 暫存改用共用陣列，catalog 執行失敗回復時一併還原。
5. `CORRUPTTION_GET_NANORI_FINAL`:786–791 改讀共用 RESULTS:2，解除停止點；unresolved.md 該條結案。
6. 同時檢查 deviations.md「口上 catalog 的顯示簡化」中 RESULT:0 未全面模型化的部分：若 RESULT:0 的「讀呼叫前值」在已移植流程中有實際到達的位置，
   一併改為同步；沒有則維持並寫明理由。

## 測試（table-driven，expected 由 ERB 推導）
- 字串多值 RETURN 後殘值保留；存讀檔往返（若存檔包含）；舊版存檔相容。
- 名乗り改竄：名乗り中找不到變身後名時，讀到前一次 RESULTS:2 的代表路徑。

## 模擬
`tools/sim.py` 預設、初期セット、`--enable-akuoti`、`--corrupt 3` 各 250 場（seed 0–249，`--max-shop 200`；可分批）：確認無新停止、與 S21 對照。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved、wiki 更新。結束時務必送出三段報告。
