# reference/ — 唯讀參考資料

## emuera-1824/

Emuera 1.824 原版 C# 原始碼（引擎）。用來**查證** Emuera 內建行為，不是要移植的對象。

- 出處：<https://github.com/0x00000FF/Emuera> commit `85db4cb`（"Upload Source Code of Emuera 1824"，未修改的原版上傳）。
  原始發布：OSDN `emuera` 專案 `src1824.zip`。
- 授權：`emuera-1824/LICENSE.txt`（MinorShift 等；允許改作與再頒布，**不得刪改該授權聲明**）。
- 本作實際附的是 `source/earGVP/Emuera1824+v10.exe`（1.824 的派生版）。派生版可能有差異；
  若原始碼行為與原作表現明顯矛盾，記入 `docs/wiki/bridge/unresolved.md` 並標明「可能是 +v10 差異」。

### 常用查詢位置

| 想知道 | 看哪裡 |
|---|---|
| 系統流程（TITLE/FIRST/SHOP/TRAIN/TURNEND/SAVE/LOAD 的呼叫順序） | `Emuera/GameProc/Process.SystemProc.cs` |
| BEGIN TRAIN 時重置哪些變數、SOURCE 何時清空 | `Emuera/GameData/Variable/VariableEvaluator.cs`（`UpdateInBeginTrain`、`UpdateAfterSourceCheck` 等） |
| 變數種類、是否存檔（`__SAVE_EXTENDED__` 等旗標） | `Emuera/GameData/Variable/VariableCode.cs` |
| 存讀檔實際寫了什麼 | `Emuera/GameData/Variable/VariableData.cs`、`CharacterData.cs` |
| CSV 解析（省略值、數字格式、錯誤處理） | `Emuera/GameData/ConstantData.cs`、`CharacterData.cs` |
| 各 ERB 命令的語意 | `Emuera/GameData/Function/`、`Emuera/GameProc/Function/` |
| PRINT／按鈕／文字顯示 | `Emuera/GameView/` |
