# 衣裝設定（S39）

## 入口與範圍

`ERB/インターミッション画面/SHOP.ERB@USERSHOP:257–259`：非遊戲結束模式且有活動角色時呼叫衣裝設定。
Python 入口為 `GameSession → clothing.cloth_wear_gen`。本階段不開放 SHOP [120] 購買入口。

`ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB@CLOTH_WEAR:3–245`：

- 只有一名角色時直接選1；多人時呼叫 `ERB/汎用関数/コモン関数.ERB@CHARA_LIST:303–355`。
- 選角僅允許 `CFLAG:999 != 0` 且 `CFLAG:0 == 0`；一人直接進入時沒有這個選角檢查。
- 外衣／變身外衣／內衣／其他裝備對應 `CFLAG:40/41/42/43`。
- 改名寫 `CSTR:8/9`，INPUTS 空字串也接受；換裝與卸下不清名稱。
- 內衣自訂按鈕的內層條件失敗時會落出函式，而非一律返回同一選單。

## 換裝與部件

`ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB`：

| 函式 | 行號 | 行為 |
|---|---:|---|
| `@CLOTH_SETTING_OUTER` | 251–322 | 100–199；持有值恰為1；197限非戰鬥員 |
| `@CLOTH_SETTING_OUTER2` | 326–421 | 100–299；列表略過197但仍可手動輸入；401需陥落経験 |
| `@CLOTH_SETTING_INNER` | 425–576 | 300–399；399確定後變400；非308清體操服相依設定 |
| `@CLOTH_SETTING_MISC` | 581–632 | 500–599；持有值恰為1 |
| `@CLOTH_RESETTING_TENTACLECLOTH` | 637–663 | 拆400消耗一片FLAG:200，不足時重問 |
| `@CLOTH_CUSTOMIZE_OUTER2` | 941–1290 | 600–699部件槽、身體／衣裝限制、同類互斥；輸入判斷含700 |

選取物品先暫存，只有[1]確定才換；[0]取消，[2]卸下。
變身外衣真的改成另一件才清 `EQUIP:600–699`；相同衣裝與卸下均不清部件。
部件替換先移除同類別，再算剩餘槽；因此滿槽仍可替換。

## 57種自訂

遊戲規則在 `clothing_custom.py` 手寫：保存編碼、類別／子選項可用性、研究門檻、連動修正。
原文文字常數由 `tools/extract_clothing_text.py` 抽至 `clothing_text.py`，
`MENUS[衣裝ID]["source"]` 記錄每個原作檔案、函式與起始行；不存放可執行ERB條件。
描述抽取器遇非註解／非PRINTL語句立即報錯，避免靜默丟失動態文案。

保存共通低位依據：
`ERB/武器と衣装/衣装関連/CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_CUSTOMIZE_OPTION_SAVE:561–572`。
第1–9位為外觀，第10／11位為輕／重裝，第12／13位為保護下降／上升；
第14位在部分外衣表示內衣兼用、在內衣表示油斷下降，第15位為內衣油斷上升。
高位直接相加，不額外限制為單一十進位數字。

已保留原作怪處：

- `ERB/武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB@CLOTH_CUSTOMIZE_OPTION_153:8634`：`CUSTOM:1 <= 3 && >= 7`永不成立。
- `ERB/武器と衣装/衣装関連/CLOTHDATAインナー.ERB@CLOTH_CUSTOMIZE_OPTION_305:968`：同一 `CUSTOM:2 == 1` 條件連續加重量1與2。
- `ERB/武器と衣装/衣装関連/CLOTHDATAインナー.ERB@CLOTH_CUSTOMIZE_OPTION_304:750`：保存運算和選項效果文字不同，兩者各自照原文。
- `ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB@CLOTH_CUSTOMIZE_OUTER:668–937` 與 `@CLOTH_CUSTOMIZE_INNER:1293–1533`：不還原TARGET，返回時清CFLAG:1。
- `ERB/武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB@CLOTH_CUSTOMIZE_OPTION_104:789`：COMMON顯示5類，但第6類[50]與追加裝備[60]的輸入仍照原作接受。

## 戰鬥補正與瀏覽

`ERB/武器と衣装/衣装関連/CLOTHDATAカスタム.ERB@CLOTH_CUSTOMIZE_COMMONPARTS_CAL:9–18`：
TARGET的非零部件逐一加上該模式常數，沒有對應函式則略過，不看ITEM持有。
補齊衣裝106／115／117／153的內衣兼用與保護分岐、199個別強化、397外衣未裝時回避。

`ERB/武器と衣装/衣装関連/CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_HOSEI:132–147`：
EQUIP未指定角色，讀TARGET；基礎變身分岐仍讀ARG。此處修正先前Python誤讀ARG。

`ERB/インターミッション画面/SHOP_CLOTH.ERB@SHOW_CLOTH:13–252` 的持有品模式：
分類、單件／目錄／簡易顯示、翻頁、19種交集篩選、返回。
`@LIST_CLOTH_HAVE:616–642` 接受任何非零持有值；
`@FILTER_CLOTH_HOSEI:678–759` 對部件只檢查函式存在，因此負補正也可能被篩出。
[98]僅清FILTER，不重設PAGE／選取位置，照原作。

## 引擎依據與驗證

- INPUT／INPUTS共用變數：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`；只改第0格。
- 字串長度／截取：`reference/emuera-1824/Emuera/_Library/LangManager.cs:17–20、40–84`；名稱表長度與截斷以cp932位元組。
- TIMES：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:893–916`；沿用 `era.times` 的Decimal乘算。
- 定向測試 `tests/test_clothing_menu.py`：212項通過；含57件非零編碼矩陣、57個選單來回、相依修正、條件、部件、GameSession與瀏覽。
- 主代理獨立完整 pytest：2491 passed, 1 warning；500 局標準模擬 default 246 上限＋4 標題返回、tokusou 250 上限，catalog_failure 0。
- 10 批前景程序 exit=0；逐 seed 完整結果與 S38 相同，log／JSONL／exit／audit 留在 `tmp/s39/`。抽取器重跑前後 clothing_text.py SHA256 相同。
