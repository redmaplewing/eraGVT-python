# S18：強制發生事件（クズ市民の脅迫・夜這い・深夜の子触手襲来）

## 背景
`ゲーム内_イベント発生/強制発生イベント/` 中尚未移植、且不需要新戰鬥種類的三個事件。悪堕ちキャラの淫謀（AKUOTI_EVENT）
會進入悪堕ちキャラ戰（戰鬥內約 15 個停止點），另排 S19；襲撃／救援的戰鬥另排之後。路徑相對 `source/earGVP/ERB/`。

目前狀態：
- `turnend.py:124／126`：INTIMIDATION_EVENT、KIDNAPPING 遇到即停止（需設定「クズ市民による幽閉」ON，`CONFIG_CHECK_PRISON_F(10)`）。
- `turnend.py:465`：YOBAI_EVENT 遇到即停止（`CONFIG_CHECK_EVENT_F(2)` 的設定）。
- `turnend.py:780／782`：子触手襲来**被跳過**（deviations.md「襲撃／救援、子触手襲来 會被跳過」）——這是會改變遊戲內容的偏離，本階段解除子触手的部分。

## 範圍
1. **クズ市民の脅迫**：`FORCE_クズ市民の脅迫.ERB` 全體——INTIMIDATION_EVENT（:4）、KIDNAPPING（:444）、INTIMIDATION_RAPE（:676）；
   CFLAG:286／320／321 與 `状態_誘拐`（CharaState.KIDNAPPED）的讀寫；S15 起已會增加 CFLAG:286。
2. **夜這い**：`FORCE_夜這い.ERB` 全體——YOBAI（:8，已移植的判定部分對照確認）、YOBAI_EVENT（:105）、YOBAI_SELECT_PLAY、YOBAI_ACTION、
   YOBAI_HOUSHI_1〜5。S17 的 SYNBIOSIS_YOBAI 若有呼叫夜這い本體的部分，一併接上。
3. **深夜の子触手襲来**：`FORCE_深夜の子触手襲来.ERB` 全體——SMALL_TENTACLE_HANTEI（已移植判定部分對照確認）、SMALL_TENTACLE_ATTACK（:81）、
   SMALL_PRISON_EVENT（:116）、SMALL_PRISON_COM（:168），以及地の文 `地の文/MESSAGE_RAID.ERB@MESSAGE_SMALL_PRISON_COM_0〜6`。
   移除 `_skip_event` 對子触手的跳過；更新 deviations.md 該條（只剩襲撃／救援）。
4. 文字：地の文檔案中的走 S07 catalog（狀態變化以 hooks 表）；事件檔案內與狀態變化交錯的本文照 S15／S17 慣例直接寫在 Python。
   需要玩家輸入的選單照既有 generator／輸入模式接 Web。
5. 需要未移植系統（悪堕ち戰、襲撃戰鬥、角色製作 UI 等）的分岐，照慣例停止並記錄。

## 查證要點
- 相關 CFLAG／TALENT、`状態_*` 常數、CONFIG 旗標的意義與預設值照 `●開発者向け資料/●GVTフラグ一覧.txt`、`CSV定数定義/`、`CONFIG_初期設定.ERB`。
- 引擎行為附 `reference/emuera-1824/...cs:行號`（已查證者引用既有註解即可）。

## 測試（table-driven，expected 由 ERB 推導）
- 三個事件各自的觸發條件、主要分岐、狀態變化（FixedRng）。
- 子触手襲来：發生 → 幽閉 → SMALL_PRISON_COM 各分岐 → 解除。
- 整合：設定 ON 時脅迫／夜這い各走一次並回到 SHOP；子触手襲来在預設設定下發生並回到 SHOP；存讀檔往返。

## 模擬
`tools/sim.py` 跑預設開局與初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因與各事件實際觸發次數，與 S17 對照寫進 STATUS。
若預設設定下脅迫／夜這い不會觸發，另跑一組把相關 CONFIG 打開的模擬（腳本加參數即可）。

## 完成條件
pytest 全綠；STATUS、deviations、unresolved 更新；wiki 只在必要時新增（< 300 行）。結束時務必送出三段報告。
