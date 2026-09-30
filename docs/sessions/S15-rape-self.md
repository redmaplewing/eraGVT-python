# S15：戰後レイプ（AFTER_TRAIN_RAPE）與自慰系（FORCE_夜間自慰.ERB）

## 背景
S14 後預設開局最常停的兩處：強制自慰（16 場）、戰後レイプ（15 場）。停止點：
- `battle/after.py@after_train_rape`（`ゲーム内_イベント発生/戦闘イベント.ERB@AFTER_TRAIN_RAPE`:962–1337，襲われる分岐）
- `battle/self_kind.py@self_kind`（強制自慰 `MESSAGE_SEX_COMSP` SPCOM6 → `SELF_KIND`）
- `battle/after.py@subevent_battleend`（戰後自慰 `SELF_BATTLEEND` → `MESSAGE_SELF_BATTLEEND`／`SELF_KIND`）
- `turnend.py:402`（夜間自慰 `SELF_NIGHT`）
路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **戰後レイプ**：`AFTER_TRAIN_RAPE` 全體（:962–1337）與它呼叫的函式、地の文；`RETURN 1` 後由
   `BATTLE_TRAIN_AFTER.ERB`:498–504 接到 S14 已移植的 `DOUGA_RYUSUTU, 1`（レイプ動画流出），確認這條路真的走得到。
2. **自慰系**：`ゲーム内_イベント発生/強制発生イベント/FORCE_夜間自慰.ERB` 全體——
   `SELF_NIGHT`（:5）、`SELF_BATTLEEND`（:65）、`SELF_CHECK`（:77，已移植者對照原文確認）、`SELF_KIND`（:182）、
   `SELF_N`／`SELF_B`／`SELF_A`／`SELF_V`（:251–814）；地の文 `MESSAGE_SELF_BATTLEEND`（`地の文/MESSAGE_SEX.ERB`:1092）等。
   接上三個呼叫點：強制自慰（戰鬥中 SPCOM6）、戰後自慰、夜間自慰（TURNEND）。
3. **文字**：地の文一律走 S07 catalog；狀態變化以 hooks 表移植並對照測試（沿用 sexmsg／lovesex 的做法）。
   PALAM_CAL、ABLUP、NINSIN_HANTEI 等依賴已移植者重用；受精成立以後已於 S13 接上。

## 不做
- 其他強制發生事件（夜這い、クズ市民の脅迫、悪堕ちキャラの淫謀等）。

## 查證要點
- 相關 TFLAG／CFLAG／TALENT 番號照 `●開発者向け資料/●GVTフラグ一覧.txt` 與 `CSV定数定義/`。
- 引擎行為附 `reference/emuera-1824/...cs:行號`（已查證者引用既有 wiki／註解即可）。

## 測試（table-driven，expected 由 ERB 推導）
- AFTER_TRAIN_RAPE：觸發條件與各分岐、RETURN 值、狀態變化（FixedRng）；RETURN 1 → レイプ動画流出。
- SELF_CHECK／SELF_KIND 分岐；SELF_N／B／A／V 的 PALAM 與狀態變化。
- 三個呼叫點各一個整合 case（強制自慰、戰後自慰、夜間自慰）。

## 模擬
`tools/sim.py` 跑預設開局與初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因頻度、停止前 SHOP 次數，與 S14 對照寫進 STATUS。

## 完成條件
pytest 全綠；STATUS、deviations、unresolved 更新；wiki 只在必要時新增（< 300 行）。結束時務必送出三段報告。
