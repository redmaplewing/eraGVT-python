# S31：口上選單的等待與續行

## 裁決與範圍
- 使用者於 2026-10-04 裁決：口上遇到 INPUT 依原作顯示選項，等待選擇後續行。
- 接通 TURNEND 與 SHOP 的口上輸入；保持原作選項、驗證、亂數與狀態更新順序。
- 延用既有 catalog 及事件等待機制，不重放輸入前的副作用。
- 本規格限於通用選單輸入；不包含 HATUJOU_TO_HAIRAN。

## 依據與測試
- 查原作 KOJO_ROOT、MESSAGE、SHOP、SHOP_TURNEND 與兩種設定選單。
- 查 reference/emuera-1824 的 INPUT 等待、RESULT 寫入與續行位置。
- 先寫失敗測試：選項、無效輸入、確認後續行、不重複初始化、沒有口上時的回傳值。
- 測試 expected 由 ERB 推導；亂數使用注入的 RNG。
- 少量 session 邊界測試確認等待時輸入不會誤送 SHOP。
- Web API 測試確認選單續行及回標題時關閉舊等待流程。

## 驗收與收尾
- 完整 pytest 全綠；執行預設／tokusou 各 seed 0–249、max-shop 200、actions 101–108 模擬。
- 模擬前景分批執行，停止原因與 S30 對照。
- 更新 STATUS（≤120 行）、相關 wiki 與裁決紀錄；未查證／偏離另記。
- 核對 source/、reference/ 未動及 LF／UTF-8 無 BOM。
- 只加入本次路徑，commit 並推上 main。

## 驗收結果
- `1846 passed, 1 warning in 321.58s`；新增 13 項測試，包含 Web API 的等待、續行與回標題清理。
- 兩組各 250 局的 seed 集合均等於 0–249，沒有重複；上限與行動參數同上。

| 開局 | SHOP 上限 | 回標題 | HATUJOU_TO_HAIRAN | 與 S30 比較 |
|---|---:|---:|---:|---|
| 預設 | 243 | 4 | 3 | 相同 |
| 初期セット | 250 | 0 | 0 | 相同 |

- catalog 執行失敗：兩組皆 0；S30 的病嬌 5,399 次、豹變 31／74 次失敗解除。
- 實際觸發設定：病嬌預設 34 局；豹變預設 1 局、初期セット 2 局。
- 既有未實作停止：預設 seed 52／124／240。未新增 UNVERIFIED／DEVIATION。
