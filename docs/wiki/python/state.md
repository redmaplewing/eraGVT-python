# Python 端：狀態模型設計決策

程式：`src/eragvt/state/`、`src/eragvt/text/`。測試：`tests/test_state_*.py`、`tests/test_text_output.py`。

## 稀疏陣列（`state/sparse.py`）

- `IntArray`／`StrArray` 只存非預設值：讀未設定索引 → 0／`""`；**寫入預設值 = 刪除該鍵**。
  因此同一內容只有一種內部表示，`==` 與存檔位元組都可直接比較。
- 索引：非負 `int`，或 2 維 `(int, int)`（CDFLAG、MOB_FLAG、MOB_GLOBAL）。JSON 鍵寫成 `"5"`／`"1:300"`。
- 值型別嚴格：`IntArray` 只收 `int`（含 IntEnum，存成純 int；`bool`、`float` 會 TypeError），避免 `True`／`1.0` 混入存檔。
  索引也接受 IntEnum（`chara.base[Base.HP]`），內部轉成純 int。
- **不檢查陣列上限**（era 會對超出 `VariableSize.csv` 的索引報錯）。目前沒有需要；若之後要抓 bug 再加。
- `get_bit`／`set_bit` 對應 `GETBIT`／`SETBIT`／`CLEARBIT`；`clear()` 對應 `VARSET 變數`。

## `GameState`（`state/game_state.py`）

| 欄位 | era | 備註 |
|---|---|---|
| `day` `time` `money` | DAY TIME MONEY | `day` 是 `IntArray`（DAY:0 日數、DAY:1 延長日數、DAY:2 半日通算）；TIME 0 晝、1 夜 |
| `target` `assi` | TARGET ASSI | 角色列表的 index；MASTER 固定為 index 0。初始值 TARGET=1、ASSI=-1（`reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs`:644–647） |
| `flag` `tflag` `item` `savestr` | 同名 | ITEM = 衣裝持有 |
| `shield` `mob_flag` | `#DIM SAVEDATA SHIELD`／`MOB_FLAG` | `ERB/DIM.ERH`:155、169 |
| `result` | RESULT | S21：跨函式共用、存檔（SAVE_VERSION 2）。`set_result_x(*v)` = 多值 RETURN。寫入來源一覽：`docs/wiki/python/result.md` |
| `results` | RESULTS | S22：跨函式共用、**不存檔**（讀檔／新遊戲為空，compare=False）、大小 100。`set_results_array` = VARSET＋ARRAYCOPY。`result.md` |
| `charas` | 角色列表 | `list[Character]` |
| `temp` | 非 SAVEDATA 的 `#DIM` | **不存檔**：`ターン上限`、`MAX_PALAM`、`COMMON_PALAM`、`特殊戦闘シチュエーション`，以及 `last_load_version`（LASTLOAD_VERSION：新遊戲 -1、讀檔後 = 存檔的遊戲版本） |
| `rng` | RAND | **不存檔**；建構時注入 `GameRng(seed)`，測試用 `FixedRng` |

- `GameState.new(data)`：標題「最初からはじめる」後、`@EVENTFIRST` 前的狀態＝[角色 0（依檔名番號）, 999]
  （SystemProc@endOpenning:197–209）。開局流程在 `eragvt.game.opening.event_first`（含 `SWAPCHARA 0,1`／`DELCHARA 1`）。
- `add_chara(data, no)` = `ADDCHARA`（依 `番号`）、`add_chara_from_csv_no` = 引擎內部的依檔名番號加入、
  `del_chara(i)` = `DELCHARA`（後面往前補，TARGET／ASSI 不自動調整）、`swap_chara(a, b)` = `SWAPCHARA`。MASTER 不可刪。
- 不存在的 era 內建變數（PALAMLV、EXPLV、BOUGHT、ITEMSALES…）**沒有建模**：本作沒用到或尚未需要。

## `Character`（`state/character.py`）

- 欄位＝era 角色變數小寫：`base maxbase abl talent exp mark palam juel ex nowex stain cflag cdflag equip relation tcvarn cstr`，
  加上 `no name callname nickname mastername`。`tcvarn` **不存檔**（`Character.NOT_SAVED`；讀檔後為 0）。
- `Character.from_def(CharaDef)` = ADDCHARA 的 CSV 初期化：「基礎」同時設 BASE／MAXBASE。
  **不做**原作 `CHARA_MAKE_FINALIZE` 的補完（CFLAG:240 固有番號、MAXBASE 射精／噴乳 < 1 修正等）——那是 S03 開局流程。
- RELATION 保持 CSV 原樣（索引 = 對方 CSV 番号），轉換見 unresolved。
- `CharaDef` 與 `Character` 不共享物件：改角色不影響載入的 CSV 資料。

## 常數（`state/constants.py`）

`ActionPlan`（予定_*）、`CharaState`（状態_*）、`KojoType`、`GameMode`／`GameOption`／`MODE_OPTIONS`、
`Base`、`Palam`、`Distance`、`BattleStatus`（IntFlag）、`SexPart`（IntFlag）、`Pose`；每個類別 docstring 附來源行號。
IntEnum／IntFlag 可直接寫入 `IntArray`（`chara.cflag[100] = ActionPlan.SORTIE`），存成純 `int`。

## 存讀檔（`state/savefile.py`）

```json
{"comment": "…", "format": "eragvt-save", "game_code": 891216222, "game_version": 408, "state": {...}, "version": 1}
```

- `game_code`／`game_version` = GameBase.csv 的コード／バージョン。`load_save(..., identity=GameIdentity)` 照 Emuera 檢查：
  代碼不同（且存檔代碼非 0）→「異なるゲームのセーブデータです」；版本依 `CheckVersion`（`GameData/GameBase.cs`:40–55）。

- `json.dumps(sort_keys=True, ensure_ascii=False, indent=1)` + 結尾換行，UTF-8、LF。
  存→讀→存**逐位元組一致**（`tests/test_state_game.py::test_roundtrip_bytes_identical`）。
- `load_save` 檢查 `format`、`version`（非 int、< 1、比程式新 → `SaveFormatError`）；
  舊版本依 `SAVE_MIGRATIONS[舊版]` 逐版升級（目前空）。**改存檔結構時：`SAVE_VERSION += 1` 並加 migration。**
- `Character.from_json` 容許缺欄位（新增欄位時舊存檔讀得進來）。
- 全域資料另一檔：`{"format": "eragvt-global", "version": 1, "global": {global, globals, mob_global}}`；
  `load_global_file` 檔案不存在 → 空 `GlobalState`（對應 LOADGLOBAL 失敗 = 真正初次啟動）。
- `comment` 對應原作 `@SAVEINFO`（`オープニング処理.ERB`:583）產生的存檔說明。

## 文字輸出（`text/output.py`）

- `TextOutput` 累積 `Line`；`Line` = `parts`（`Part(segments, button)`，Part 對應 Emuera 的 ConsoleButtonString）+
  `kind`（`text`／`drawline`）+ `wait` + `align`。`Segment(text, color, bold)` 是樣式段。
- `print`（不換行）／`printl`／`printw`（換行+等待）／`print_plain`／`button`／`drawline`／`wait`／`clearline(n)`／
  `set_color`（`#rrggbb` 或 `(r,g,b)`）／`set_bold`／`set_align`。`drain()` 交出已完成行。
- **自動按鈕**（照 `GameView/ButtonStringCreator.cs`）：PRINT 累積的文字在換行、`print_plain`、`button` 時
  整段交給 `split_buttons` 判定——沒有或只有一個 `[數字]` 時整段是一個單位（一個時整段可點）；兩個以上時
  依說明文字在左／右／兩側決定切點（兩側時以 2 個以上空白分隔）。樣式段依切點分割。
- 格式化：`%字串,幅,LEFT%` 以 cp932 位元組算寬度、`{數值,幅}` 以字數（`eragvt.game.era.format_percent`／`format_curly`）。

## 遊戲流程（`game/`）

- `era.py`：Emuera 內建語意（整數除法向 0 截斷、`TIMES` 的 decimal 截斷、`SQRT`、`LIMIT`、字寬）。
- `opening.py`：`@EVENTFIRST` 最小路徑（固定選擇見模組 docstring）。`shop.py`：`@EVENTSHOP` 初日、`@SHOW_SHOP`、`@USERSHOP` 各處理。
- `session.py`：`GameSession` 是 Emuera 系統流程（標題、SHOP 迴圈、SAVEGAME／LOADGAME 選單、自動存檔 99 號）的狀態機，
  `input(數值)` 推進、`screen()` 回傳最後一次 `@LB` 之後的行。未移植的 ERB 分支一律 `NotImplementedError`（不默默走錯路）。
- `web/`：FastAPI。`GET /` 渲染、`POST /input`（表單）、`GET /api/screen`／`POST /api/input`（JSON）、`POST /restart`。
  `python -m eragvt` 啟動（預設 `127.0.0.1:8000`、存檔 `./saves`）。

## 敘事（`text/narration.py`）

`NarrationService.narrate(kojo_no, code, seikaku) -> str | None`，對應 `KOJO_ROOT(CFLAG:6, 代碼)`；
`None` = 沒有這段口上，呼叫端照原作回落地の文。預設實作 `NullNarrationService` 永遠回 `None`。
