# S17：寄生系統（寄生触手の暴走・共生・寄生による行動制限）

## 背景
S16 後隨機模擬 500 場中只剩 1 場停止（初期セット seed 101：「ACT_LIMIT：寄生による行動制限は未移植」）。
寄生相關的停止點共 4 處：
- `battle/func.py:193`（ACT_LIMIT 寄生分岐，`COMMON_BATTLE_FUNC.ERB@ACT_LIMIT`）
- `turnend.py:784`（PARASITE_EVENT／SYNBIOSIS_EVENT）
- `battle/ablup.py:388`（寄生ふたなりの定着／消失）
- `session.py:155` 附近 @EVENTSHOP 內的寄生触手暴走
S08 已移植 PARASITE 前半段（`FORCE_深夜の寄生触手暴走.ERB`:3–66）。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **寄生事件本體**：`ゲーム内_イベント発生/強制発生イベント/FORCE_深夜の寄生触手暴走.ERB` 全體——
   PARASITE（:3，已移植部分對照確認）、PARASITE_EVENT（:72）、PARASITE_ACTION（:108）、
   SYNBIOSIS_GET_EVENT／SYNBIOSIS_EVENT／SYNBIOSIS_SOLO_EVENT／SYNBIOSIS_OUT_OF_CONTROL_EVENT、
   SYNBIOSIS_YOBAI_EVENT／ACTION、CHECK_SYNBIOSIS_YOBAI_TARGET、PRINT_CHARA_LIST、SYNBIOSIS_ABL_UP。
   接上 TURNEND（`turnend.py:784`）與 @EVENTSHOP 的呼叫點。
2. **戰鬥中的寄生**：ACT_LIMIT 的寄生分岐與地の文 `MESSAGE_BATTLE_DISACTION_PARASITE`（`MESSAGE_BATTLE.ERB`:2023）、
   `MESSAGE_OTHER_BATTLE_DISACTION_PARASITE`（`MESSAGE_OTHER.ERB`:687）。
3. **寄生ふたなり**：`ablup.py:388` 的定着／消失（`_ABLUP` 對應行），以及它依賴的處理。
4. **寄生的其他讀寫處**：全域搜尋 `TALENT:寄生`（與相關 CFLAG）在**已移植檔案**中的分岐，逐一確認已照原文移植，缺的補上。
5. 文字一律走 S07 catalog；狀態變化以 hooks 表移植並對照測試。PRINT_CHARA_LIST 若是選擇 UI，照既有輸入模式接 Web。

## 不做
- 夜這い（FORCE_夜這い.ERB）本體：SYNBIOSIS_YOBAI 只移植寄生觸手自身的部分；若必須呼叫夜這い本體，照慣例停止並記錄。

## 查證要點
- TALENT:寄生 的值域、相關 CFLAG 的意義照 `●開発者向け資料/●GVTフラグ一覧.txt` 與 `CSV定数定義/`。
- 引擎行為附 `reference/emuera-1824/...cs:行號`（已查證者引用既有註解即可）。

## 測試（table-driven，expected 由 ERB 推導）
- PARASITE_EVENT／ACTION、SYNBIOSIS 各事件的觸發條件與狀態變化（FixedRng）。
- ACT_LIMIT 寄生分岐、寄生ふたなり的定着／消失。
- 整合：重現初期セット seed 101 的路徑（或等價的 prestate）→ 不再停止。

## 模擬
`tools/sim.py` 跑預設開局與初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因頻度、停止前 SHOP 次數，與 S16 對照寫進 STATUS；
另外統計寄生相關事件的實際觸發次數。

## 完成條件
pytest 全綠；STATUS、deviations、unresolved 更新；wiki 只在必要時新增（< 300 行）。結束時務必送出三段報告。
