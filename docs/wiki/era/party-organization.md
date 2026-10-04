# SHOP 隊伍編成（S46）

入口 `game.session`，原生實作 `game.party_organization`；共用列表仍在 `game.shop`。
原文文字由 `tools/extract_party_organization_text.py` 抽取至 `party_organization_text.py`，不執行 ERB 規則。
以下原作路徑相對 `source/earGVP/ERB/`，引擎路徑相對 `reference/emuera-1824/Emuera/`。

## 入口與操作

- `インターミッション画面/SHOP.ERB@USERSHOP:208–213`：[50] 僅在 `CHARANUM > 2 && CHARANUM_SAFE() > 0` 進入，先設 `TARGET = 0`。
- `SHOP_ORGANIZE_PARTY.ERB@SHOP_ORGANIZE_PARTY:5–98`：重畫首領資訊、出場／候補列表、資源表頭、選擇說明，再等待 INPUT。
  本函式沒有 PRINTW；輸入前保持實際畫面，不被一般 SHOP 重畫蓋掉。
- 同函式 `:127–149`：輸入角色索引，未選時選擇、同一角色取消、另一角色交換。
  幽閉／洗腦／惡墮／死亡（1/2/3/9）拒絕並保留原選擇；出產前／育兒（10/11）拒絕且清除選擇。
- 同函式 `:112–124`：[100] 僅接受非 MASTER 且狀態為 0 的角色。候補在 `CHARANUM_ACTIVE() < 6` 時加入；出場角色退出並將行動改為休憩（103）。
  候補滿員時不加入，仍清除選擇。無效目標則直接重畫，不清除既有目標。
- 同函式 `:102–109`：[50] 完成；未選角色時由注入 RNG 在 1 至 `CHARANUM - 1` 任選目標，無資格篩選。
  沒有候補時清 `FLAG:61`，`RETURN 0` 只寫 RESULT:0，尾格與 RESULTS 保留。
- `汎用関数/CHARANUM.ERB@CHARANUM_ACTIVE:124–131`、`@CHARANUM_PARTYCHECK:135–142`、`@CHARANUM_RESERVE:146–153`：
  沿用既有人數計算。出場總數只排除 CFLAG:999 = 0；候補計數只排除值 = 1，未將其他非零值正規化。

## 交換順序

`SHOP_ORGANIZE_PARTY.ERB@SHOP_ORGANIZE_PARTY:152–164`：

1. 對每個非 MASTER 角色交換 RELATION 的兩個角色索引欄位。
2. 交換兩個角色的 CFLAG:999，再交換角色本體。因此出場／候補位置保留，角色移到新位置。
3. 對交換後兩個位置，若 CFLAG:999 = 0，行動改為休憩；最後清 TARGET。

`GameData/Variable/VariableEvaluator.cs@SwapChara:1165–1174` 僅交換角色清單兩元素，不追蹤 ASSI／MASTER 或其他索引變數。
`GameProc/Process.ScriptProc.cs:341–366` 的 SWAP 先確定兩個變數引用再交換值；`:61–67` 為函式自然結束時 RESULT:0 = 0。
測試驗證雙向交換、RELATION 完整矩陣與 MASTER 列不動、ASSI／FLAG:798 不動、不同出場旗標組合。

## 顯示與已查證怪處

- `SHOP_SHOW_STATUS_LIST.ERB@SHOP_SHOW_STATUS_PARTY_LIST:9–42`：出場只顯示狀態 0；`@SHOP_SHOW_STATUS_RESERVE_LIST:52–86` 顯示候補狀態 0/10/11。
  兩者共用編成模式參數，選中標記與姓名為金色；平時為綠色。一括設定 FLAG:9 != 0 不顯示選中標記。
- `SHOP_PRINT_ACTIONPLAN.ERB@SHOP_PRINT_ACTIONPLAN:5–29` 在行動文字後 RESETCOLOR；簡化數值列末也回預設色，避免選色外溢。
- 候補列表同時接回一般 SHOP 的 FLAG:61 顯示入口。欄寬、數值條與狀態標記仍沿用既有 SHOW_SHOP 顯示簡化，登記於 `bridge/deviations.md`。
- 原作編成警告 `:80–81` 在出場人數 **小於** 上限時宣稱已滿，與 `:27–28`／`:117–118` 相反。本階段保留原文字與條件，不修正。
- 數字輸入限制 `:129` 沒有列出拉致狀態 4；雖然列表不顯示，手打仍可選擇／交換，照原作保留。
- 出產前／育兒的拒絕說明 `:133–142` 輸出後立即 RESTART，下一輪 LB 清畫面；沒有擅加等待選項。

## 驗收

- 先紅：尚無模組時匯入失敗；定向及 SHOP 回歸 `92 passed, 1 warning in 3.46s`（新增 79 案）。
- 覆蓋人數邊界、特殊狀態／拒絕順序、RNG、RESULT 尾格、GameSession.screen、Web 按鈕、存讀檔與候補顯示開關。
- 主代理獨立完整 pytest：`3058 passed, 1 warning in 369.66s (0:06:09)`，既有 Starlette/httpx 警告。
- 標準 500 局：預設 246 局上限／4 局回標題；初期セット 250 局上限，catalog 失敗 0，逐 seed 完整記錄與 S45 一致。
- `tmp/s46/` 對照 `tmp/s45/`：每組 5 批、每批 50 局前景，10 批 exit = 0；audit 確認 seed 全集、log／JSONL 一致。
- 無新增 UNVERIFIED；反向警告屬已查證原作行為，沒有新增待裁決修正。
