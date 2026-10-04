# S49：武器自訂

## 目標
- 接通狀態畫面 P3 [0] 的 WEAPON_CUSTOMIZE，消除未移植停止點。
- 原作：`ERB/武器と衣装/武器カスタマイズ関連/WEAPON_CUSTOMIZE.ERB`。
- 入口：`ERB/ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE3.ERB`。

## 範圍
- 近／中／遠距離武器顯示、SETTING_WEAPON_NAME、SETTING_FSTYLE 及各自返回／取消。
- 原選單可達的手動與隨機命名、附加字串等依原作完整接通，優先重用既有命名工具。
- 風格條件、資源消耗或限制、旗標與名稱資料寫入，逐項查原文，不假定只影響顯示。
- FSTYLE_ATTACK／SET_FSTYLE_INFO／FSTYLE_NAME_F 等優先核對既有實作並重用。
- 驗證自訂後實際戰鬥呼叫者讀取新設定，不做無呼叫者模組。
- 固定資料與文字抽取，遊戲邏輯手翻；亂數只走注入 RNG。
- INPUT／INPUTS／PRINTW 與 RESULT／RESULTS 殘值依引擎確認並附行號。
- 不擴充整套角色製作 UI，不改其他已裁決規則；新疑義先列證據。

## 驗收
- 原文推導 table-driven 預期，先紅後綠。
- 覆蓋三種距離、選項條件、無效輸入、取消、命名與風格資料、RNG、戰鬥效果。
- 少量 GameSession／Web／存讀檔邊界測試，確認畫面真正在輸入位置等待。
- 主代理完整 pytest，全綠後確認 source／reference 無修改及 LF／UTF-8 無 BOM。
- 預設與 tokusou 各 seed 0–249、max-shop 200、actions 101–108，每批 50 局前景執行。
- 與 S48 逐 seed 對照完整記錄，回報停止原因及 catalog 失敗。
- 更新 STATUS（≤120 行）及相關 wiki；有新偏離／未決才登記對應文件。
- 主代理驗收後 commit、push main，完成本階段即停止。

## 驗收結果
- 先紅：新增模組尚未建立，定向測試收集 `1 error in 0.51s`；實作後通過。
- 主代理完整：`3313 passed, 1 warning in 280.23s (0:04:40)`；其後新增2案獨立驗證 `2 passed, 127 deselected in 0.37s`，共3315案。
- 詞庫167／205候選、47詞群、80文字片段，抽取器重跑雜湊一致。
- 標準500局：default246上限／4回標題、tokusou250上限；catalog失敗0，逐seed與S48完整結果一致。
- 10批exit=0、seed全集、log／JSONL一致；紀錄與audit在`tmp/s49/`。
- source／reference未動，所有變更為UTF-8無BOM／LF；無新增未決與偏離。
