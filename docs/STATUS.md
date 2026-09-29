# 現況（唯一真相，≤150 行）

更新：2026-09-29

## 已完成

- 建立 repo，`source/earGVP/` 原作基線入庫（唯讀）。AGENTS.md、PLAN.md。
- **S01**：原作分析 + 專案骨架。
  - era 事實 wiki：`docs/wiki/era/flow.md`、`variables.md`、`csv.md`、`battle-overview.md`。
  - `pyproject.toml`（src layout）、`src/eragvt/`；`python -m eragvt --check-data` 載入全部原作 CSV 並列摘要。
  - `eragvt.data.load_game_data()`：12 張名稱表、Item（含價格）、Str 初期值、GameBase／VariableSize／_Replace、
    77 名角色 CSV（遞迴、BOM 有無、CRLF/LF、名稱索引、64 位元 RELATION）。
  - `tests/`：59 個 table-driven 測試，expected 由 CSV 原文手抄。
- **S02**：核心狀態模型（設計見 `docs/wiki/python/state.md`）。
  - `eragvt.state`：`IntArray`／`StrArray`（稀疏，未設定 = 0／""）、`Character.from_def`（= ADDCHARA）、
    `GameState`（MASTER = index 0 的 Chara999；`add_chara`／`del_chara`／`swap_chara`；`temp` 與 `rng` 不存檔）、
    `GlobalState`（GLOBAL 系，另一檔）、`GameRng`／`FixedRng`、主流程常數 Enum（附來源行號）。
  - 存讀檔：版本化 JSON（`eragvt-save` v1／`eragvt-global` v1），存→讀→存逐位元組一致；migration 掛點。
  - `eragvt.text`：`TextOutput`（PRINT 系列 → `Line`/`Segment`，含顏色、粗體、按鈕、等待、DRAWLINE、CLEARLINE）、
    `NarrationService` Protocol + `NullNarrationService`。
  - `--check-data` 追加「開局狀態（MASTER+301/302/303）存讀檔」檢查。測試共 127 個。

## 下一步

- **S03**：新遊戲 + SHOP（規格待寫 `docs/sessions/S03-*.md`）。建議內容：
  1. **開局最小路徑**（翻 `ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST`，跳過角色製作與序章）：
     `GameState.new` → `TIME=1`、`MONEY=5000`、`ITEM:100/200/201/202/299/300/401=1`（:48–59）；
     模式固定 NORMAL：`FLAG:0 = MODE_OPTIONS[NORMAL]`、`FLAG:852=5000`；`FLAG:50=FLAG:51=1`；
     `FLAG:3` = BOSS 數（`COMMON_TENTACLE_DATA.ERB@GET_BOSS_ERB_NUM` = `触手データ/ボス触手/TENTACLE_BOSS_n` 連號數，現為 7）、
     `FLAG:4=1`、`FLAG:100` 低 FLAG:3 位全 SETBIT；
     預設隊伍 `初期セット/0_特捜戦隊.ERB@SHOKISET_SELECT_0`（FLAG:5/7、SAVESTR:10/12、ADDCHARA 301–303、`FLAG:8+=3`）
     與 `SHOKISET.ERB@SHOKISET_CSVFIX` → `FIRSTSETTING_CHARA_CSVFIX`（需讀）；
     `CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_FINALIZE`:221 的必要部分（`CFLAG:240 = index`、MAXBASE 射精／噴乳 < 1 → 10000）；
     `CFLAG:6` 口上番號（:143–166）、`CFLAG:100 = 予定_休憩`、`SET_LIMIT_DAY`（:411，NORMAL → `FLAG:2 = 11`）、
     `CFLAG:999 = 1`（index ≤ 6）、裝備衣裝登記 ITEM（:269–283）、`FLAG:41 = 1`、`RESEARCH_QUOTA`。
     `CONFIG_INIT`／`HEROINE_PRESET`／`UPDATE` 先讀再決定是否納入。
  2. `@EVENTSHOP` 的 `DAY == 0` 分支（`SHOP_TURNEND.ERB`:147–156）→ 進 SHOP。
  3. **SHOP Web UI**：FastAPI + Jinja2；後端持有 `GameState` + `TextOutput`，`@SHOW_SHOP` 輸出成 `Line` 列表渲染，
     按鈕送回數字 → `@USERSHOP` 分派（先做：切換 TARGET、101–108 行動預約、100 確認（先停在「將執行 ACTION_MAIN」）、
     200/300 存讀檔接 `state.savefile`）。其餘選單項目顯示但標「未實作」。
  4. 相性（RELATION）轉換的調查與實作（unresolved）。

## 已知問題

- 未決事項見 `docs/wiki/bridge/unresolved.md`；最重要的是戰鬥回合數 `TFLAG:0` 的遞增處（S05 前要解）。
- 原作 CSV 有兩處瑕疵（Chara299 `100.`、Chara998 佔位符），載入器已容錯並記警告。
