# Python 端：狀態模型設計決策

程式：`src/eragvt/state/`、`src/eragvt/text/`。測試：`tests/test_state_*.py`、`tests/test_text_output.py`。

## 稀疏陣列（`state/sparse.py`）

- `IntArray`／`StrArray` 只存非預設值：讀未設定索引 → 0／`""`；**寫入預設值 = 刪除該鍵**。
  因此同一內容只有一種內部表示，`==` 與存檔位元組都可直接比較。
- 索引：非負 `int`，或 2 維 `(int, int)`（CDFLAG、MOB_FLAG、MOB_GLOBAL）。JSON 鍵寫成 `"5"`／`"1:300"`。
- 值型別嚴格：`IntArray` 只收 `int`（含 IntEnum，存成純 int；`bool`、`float` 會 TypeError），避免 `True`／`1.0` 混入存檔。
- **不檢查陣列上限**（era 會對超出 `VariableSize.csv` 的索引報錯）。目前沒有需要；若之後要抓 bug 再加。
- `get_bit`／`set_bit` 對應 `GETBIT`／`SETBIT`／`CLEARBIT`；`clear()` 對應 `VARSET 變數`。

## `GameState`（`state/game_state.py`）

| 欄位 | era | 備註 |
|---|---|---|
| `day` `time` `money` | DAY TIME MONEY | TIME 0 晝、1 夜 |
| `target` `assi` | TARGET ASSI | 角色列表的 index；MASTER 固定為 index 0 |
| `flag` `tflag` `item` `savestr` | 同名 | ITEM = 衣裝持有 |
| `shield` `mob_flag` | `#DIM SAVEDATA SHIELD`／`MOB_FLAG` | `ERB/DIM.ERH`:155、169 |
| `charas` | 角色列表 | `list[Character]` |
| `temp` | 非 SAVEDATA 的 `#DIM` | **不存檔**：`ターン上限`、`MAX_PALAM`、`COMMON_PALAM`、`特殊戦闘シチュエーション` |
| `rng` | RAND | **不存檔**；建構時注入 `GameRng(seed)`，測試用 `FixedRng` |

- `GameState.new(data)`：角色列表只有 MASTER（`GameBase.csv` 最初からいるキャラ = 999）。
  原作 `@EVENTFIRST` 用 `SWAPCHARA 0,1`／`DELCHARA 1` 達成同樣結果，這裡直接建成結果狀態。
- `add_chara(data, no)` = `ADDCHARA`（尾端追加）、`del_chara(i)` = `DELCHARA`（後面往前補，
  TARGET／ASSI 不自動調整）、`swap_chara(a, b)` = `SWAPCHARA`。MASTER 不可刪。
- 不存在的 era 內建變數（PALAMLV、EXPLV、BOUGHT、ITEMSALES…）**沒有建模**：本作沒用到或尚未需要。

## `Character`（`state/character.py`）

- 欄位＝era 角色變數小寫：`base maxbase abl talent exp mark palam juel ex nowex stain cflag cdflag equip relation tcvarn cstr`，
  加上 `no name callname nickname mastername`。
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
{"comment": "…", "format": "eragvt-save", "state": {...}, "version": 1}
```

- `json.dumps(sort_keys=True, ensure_ascii=False, indent=1)` + 結尾換行，UTF-8、LF。
  存→讀→存**逐位元組一致**（`tests/test_state_game.py::test_roundtrip_bytes_identical`）。
- `load_save` 檢查 `format`、`version`（非 int、< 1、比程式新 → `SaveFormatError`）；
  舊版本依 `SAVE_MIGRATIONS[舊版]` 逐版升級（目前空）。**改存檔結構時：`SAVE_VERSION += 1` 並加 migration。**
- `Character.from_json` 容許缺欄位（新增欄位時舊存檔讀得進來）。
- 全域資料另一檔：`{"format": "eragvt-global", "version": 1, "global": {global, globals, mob_global}}`；
  `load_global_file` 檔案不存在 → 空 `GlobalState`（對應 LOADGLOBAL 失敗 = 真正初次啟動）。
- `comment` 對應原作 `@SAVEINFO`（`オープニング処理.ERB`:583）產生的存檔說明。

## 文字輸出（`text/output.py`）

- `TextOutput` 累積 `Line`；`Line` = `segments`（`Segment(text, color, bold, button)`）+ `kind`（`text`／`drawline`）+ `wait`。
- `print`（不換行）／`printl`／`printw`（換行+等待）／`drawline`／`wait`／`clearline(n)`／`button`／`print_plain`；
  顏色一律 `#rrggbb`（`set_color((r,g,b))` 或字串）。
- `drain()` 交出已完成行給 Web；未換行的部分保留到下次。
- **自動按鈕**：`print` 會把 `[n]` 轉成按鈕，範圍到下一個 `[n]` 或字串尾（`split_buttons`）。
  這是 Emuera 規則的簡化版（Emuera 以整行、含 PRINTC 欄位判定），足夠應付主選單寫法；不符時改用 `button()`／`print_plain()`。

## 敘事（`text/narration.py`）

`NarrationService.narrate(kojo_no, code, seikaku) -> str | None`，對應 `KOJO_ROOT(CFLAG:6, 代碼)`；
`None` = 沒有這段口上，呼叫端照原作回落地の文。預設實作 `NullNarrationService` 永遠回 `None`。
