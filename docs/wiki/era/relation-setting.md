# 開局角色關係設定（S51）

實作：`game/relation_setting.py`；固定文字由 `tools/extract_relation_setting.py` 擷取。
原作路徑相對 `source/earGVP/`；引擎路徑相對 `reference/emuera-1824/Emuera/`。

## 開局入口與轉換

- `ERB/ゲーム内_イベント発生/オープニング処理.ERB@HEROINE_PRESET:659–752`：
  `[30]` 先呼叫 `CONVERT_RELATION`，再選本人／對方；本人 `[99]` 呼叫 `CHECK_ALL_RELATION` 後回開局畫面。
  對方 `[99]` 只回角色列表；本人與對方不可相同，其他非法值留在同一輸入點。
- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CONVERTCSV.ERB@CONVERT_RELATION:3–24`：
  每個非 MASTER 角色先複製 RELATION 的 0–9998 格，再以對方 NO 查快照，正值才複製到對方登錄索引。
  舊 NO 格不清除、零值／負值不覆蓋、同一輪不讀自己的新寫入；每次重入 `[30]` 都再執行。
  上限來自 `ERB/DIM.ERH:23`。一般直接開始遊戲仍不轉換。
- 角色列表顯示姓名、CFLAG:34 打開時的實際年齡、性別與初始狀態；通用未設定角色另顯示未設定。
  依據：同 `HEROINE_PRESET:666–695、702–736`，`ERB/CSV定数定義/CFLAG.ERH:13–22`。

## 選擇與確認

以下皆為 `ERB/SYSTEM/キャラメイキング関連/CHARA_RELATION.ERB@SET_RELATION`。

- `:195–200` 由目前 RELATION 載入 64 個暫存位元；每次呼叫重新載入，取消不回寫。
- `:208–285` 打開的選項以 RGB(255,60,220) 顯示。位元定義在 `ERB/DIM.ERH:219–242`。
- `:290–337` 無任何親屬位元 20–25 時，不接受生き別れ／義理の。
  非義理的親子／祖父祖母孫，若年長者為女性且有処女：固有角色不許確認；其餘角色確認時清該素質。
  年長判斷使用既有 `TOSHIUE_F`：實際年齡相同時 CFLAG:240 較小者年長（同檔 `@TOSHIUE_F:986–995`）。
- `:338–350` 禁止確認時按鈕灰色，但仍依輸入再次檢查，不靠前端禁用。
  可確認時先將正向 RELATION 清零，再回寫位元 1–63；位元 0 丟棄，其餘未列在選單上的位元仍保存。
- `:508–553` `[999]` 取消；互斥群組為 23／24、31–34、40–42。
  點到群組中一項時先切換該位元，再清群組其他位元；即使把該項關閉也會清其他項。
  親子／兄弟姉妹／祖父祖母孫並未互斥；親しい／疎遠な及愛する／憎悪する也可並存。

## 雙向關係

`@SET_RELATION:361–489`：先完成正向資料，再依表新增或移除反向資料；未列入的反向位元保留。

| 正向位元 | 反向位元 |
|---|---|
| 1、6、20、21、22、25、32、33、34 | 同一位元 |
| 23 おじおば | 24 甥姪 |
| 24 甥姪 | 23 おじおば |
| 40 主人 | 依子選單 41 従者／42 奴隷 |
| 41 従者／42 奴隷 | 40 主人 |

印象 2–5、友人 30、片思い 31 為單向。主人不存在時清反向 41／42；正向 41／42 都不存在時清反向 40。
`@SET_RELATION:492–507` 顯示正向關係；只有反向改動時另顯示反向結果，最後 PRINTW 等待後返回。
`CHECK_ALL_RELATION` 只在退出角色列表時呼叫，會推導親屬並設定父母 ID；確認一組關係時尚不推導。
既有實作同步補上 `@CHECK_ALL_RELATION:931、937` 的 `CALL GET_RELATION`：寫入 RESULTS:0，其他格保留。

## 保留的原作邊界

- `HEROINE_PRESET:699、740` 使用 `<= CHARANUM`，所以手動輸入 CHARANUM 後選另一角色，仍在存取不存在角色時報錯；不自行改成忽略。
- `SET_RELATION:510` 接受位元 25 いとこ，但 `:208–285` 沒有其按鈕；仍可手動輸入。
- `SET_RELATION:461` 是 OR：反向已有従者或奴隷其中一種時仍詢問，選另一種會保留兩種；已有兩種時才跳過詢問。
- `CHECK_ALL_RELATION:923–927` 的無親屬檢查沒包含いとこ，可能清除對方的義理の／生き別れ；沿用原作既有實作。

以上皆有明文依據，未當作 bug 擅改；無新增 UNVERIFIED／DEVIATION。

## 引擎與驗收

- PRINTFORM 只展開原樣板，插入的角色名字串不重解讀：`GameData/StrForm.cs:205–216`。
- INPUT 只寫 RESULT:0：`GameProc/Process.cs:249–252`；無效值是否重畫由 ERB 決定。
- RETURN 無引數只清 RESULT:0：`GameProc/Function/Instraction.Child.cs:2008–2012`；
  自然函式終端同樣清 0：`GameProc/Process.ScriptProc.cs:61–67`。
- SETBIT 的位元 63 是 Int64 符號位：`GameProc/Function/Instraction.Child.cs:546–557`；不轉成 Python 正的大整數。
- CLEARLINE 使用給定數目刪行：`GameProc/Function/Instraction.Child.cs:488–500`。
  `SET_RELATION:201、344–345` 記住呼叫前 LINECOUNT，非 200 輸入清到原位置；無效確認 200 留下畫面再追加。
- WAIT 等 Enter，不寫 RESULT／RESULTS：`GameView/EmueraConsole.cs:497–508、701–734`；沿用既有 Web 等待標記。
- `tests/test_relation_setting.py` 覆蓋方向、刪除、互斥、限制、取消、重入、快照、符號位、殘值、顯示與 Web 存讀檔。
  `tests/test_config.py` 的原 `[30]` 停止測試改成實際開局進出。

標準500局不選開局 [30]，用來檢查既有流程及 CHECK_ALL_RELATION 的回歸；新選單與最後的字串顯示修正由定向及完整 pytest 驗證。
