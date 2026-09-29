# 翻寫計畫

## 原作規模（`source/earGVP/ERB`，約 33.2 萬行）

| 區塊 | 行數 | 處理方式 |
|---|---:|---|
| `口上/` | 148K | **抽取**成文字 catalog + 條件表，不手翻邏輯 |
| `地の文/` | 24K | 同上（地の文 catalog） |
| `ゲーム内_戦闘処理/` | 42K | 手翻（核心，最難） |
| `ゲーム内_イベント発生/` | 35K | 手翻（開場、強制事件、結局、幽閉） |
| `武器と衣装/` | 22K | 資料抽取 + 手翻規則 |
| `SYSTEM/` | 15K | 手翻（角色製作、設定） |
| `ヒロイン関連/` | 15K | 手翻（狀態、墮落、懷孕等） |
| `ゲーム内_行動実行処理/` | 6K | 手翻 |
| `インターミッション画面/` | 6K | 手翻（SHOP 主選單） |
| `汎用関数/` | 4K | 依需要翻成工具函式 |
| `CSV/` | 21K 行 | 抽取成資料檔 |

主流程（`ERB/※ゲーム開始からのフロー.txt`）：

```
@EVENTFIRST(新遊戲) / @EVENTLOAD(讀檔)          ゲーム内_イベント発生/オープニング処理.ERB
  → SHOP：@SHOW_SHOP / @USERSHOP 預約行動       インターミッション画面/SHOP.ERB
  → 執行行動（+追加事件 / 開戰 → TRAIN）         ゲーム内_行動実行処理/, ゲーム内_イベント発生/
  → 戰鬥 = era 標準 TRAIN                        ゲーム内_戦闘処理/BATTLE_*.ERB
       @EVENTTRAIN @SHOW_STATUS @SHOW_USERCOM @USERCOM @EVENTCOM @EVENTCOMEND @EVENTEND
  → 回合結束 @EVENTTURNEND / @EVENTSHOP         インターミッション画面/SHOP_TURNEND.ERB
       強制事件/襲擊 → TRAIN、結局判定、日期變更、flag 重置
  → 回到 SHOP
```

注意：沒有 `@SYSTEM_TITLE`（用 Emuera 預設標題）。

## 階段

「模型」欄是建議：**O** = Opus 5.5（effort high），**S** = Sonnet 5。

| # | 階段 | 成果 | 模型 |
|---|---|---|---|
| S01 | 原作分析 + 專案骨架 | era 事實 wiki（變數、CSV、流程）、`src/eragvt` 骨架、CSV 載入器與測試 | O |
| S02 | 核心狀態模型 | 全域/角色變數模型（稀疏 dict + 常數 Enum）、由 `CharaDef` 建角色（MASTER=Chara999）、JSON 存讀檔（只存 SAVEDATA/CHARADATA）、文字輸出層、`NarrationService` 介面佔位（細項見 STATUS） | O |
| S03 | 新遊戲 + SHOP | EVENTFIRST 最小路徑（預設角色、跳過完整角色製作）、SHOP 主選單 Web UI | O |
| S04 | 行動執行 + 回合結束 | ACTION 各類、TURNEND（日期、flag 重置）、結局判定骨架 | O |
| S05 | 戰鬥核心 | 遭遇、行動順序、指令選擇/判定、PALAM 計算、戰後處理 | O |
| S06 | 戰鬥補完 | 敵方行動、連擊、反擊、報告；**垂直切片完成：可玩一整回合含一場戰鬥並存讀檔** | O |
| S07 | 口上/地の文抽取管線 | 抽取工具 → catalog + 條件表，接上 NarrationService 回落 | O 設計 → S 大量執行 |
| S08+ | 橫向擴充 | 其餘行動、事件、衣裝、墮落/幽閉、角色製作完整版、設定畫面 | S（遇難題切 O） |

S01–S06 是「需要判斷力」的部分，建議用雲端額度（Opus）優先完成；
S08 以後是照樣板擴寫，可用本機訂閱額度或 Sonnet 慢慢做。

## 額度估算（$100 雲端額度，2026-11-05 15:59 GMT+8 到期）

- Opus 5.5：$4 / $20 每百萬 token（讀快取 $0.20）。一個完整 session 粗估 $10–20。
- Sonnet 5：約 Opus 5.5 的一半。
- 預估 S01–S06 用 Opus 約 $60–90。**每個 session 結束後看額度頁實際扣款，校正後續規劃。**
- 實測：S01 花 **$7**（$100→$93）。依此校正，S02–S06 預估約 $40–60，額度可能夠做到 S07 的抽取管線設計。
- 省錢守則：session 開場只讀 AGENTS → STATUS → 本次規格；讀原作用 grep；不要重複跑整包分析。
