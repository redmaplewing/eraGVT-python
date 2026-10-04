# 數值格式：色碼與年齡指定（S50）

## 範圍與呼叫者

`game.numeric.read_numeric` 是原生 Python 數值轉換，供 `chara_make.toint` 與
`colorbar.isnumeric` 共用；不執行 ERB，也不改 catalog、衣裝及視窗各自的解析器。

- `ERB/汎用関数/SETCOLOR_BY_STR.ERB@SETCOLOR_BY_STR:48–55`：以 `//` 切為三段，依序短路檢查
  `ISNUMERIC`，再用 `TOINT` 指定 RGB；格式無效回 -1、不改色，合法回 0。
- `ERB/汎用関数/SETCOLOR_BY_STR.ERB@COLORCHIP:64–73`：色塊印完後還原原文字色。
- `ERB/ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE5.ERB@SHOW_STATUS_CHARA_APPERANCE:195、233、243、294`
  是既有 P5 色碼顯示入口；目前沒有手動色彩選單。S50 驗收以存檔內 CSTR 色碼經 Web P5 顯示。
- `ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_AGE_SETTING:1408–1444`：
  CSTR:204–206 中字串 `"0"` 設零歲，其他正整數設該年齡；非正值或無效字串仍走原作 `RANDOM_AGE_F`。
- 轉換函式本身不改 `RESULT`／`RESULTS`；既有呼叫流程、存檔格式與 RNG 次序不變。

## 引擎查證

下列路徑均以 `reference/emuera-1824/Emuera/` 為根：

| 規則 | 依據 |
|---|---|
| `TOINT` 無效格式回 0，`ISNUMERIC` 回 0；合法零值仍屬數字 | `GameData/Function/Creator.Method.cs:2357–2387、2540–2569` |
| 前後空白不略過；開頭只能是數字，或正負號緊接數字 | 同上 `:2366–2369、2548–2551` |
| 只在字串起首辨識 `0x`／`0b`；不採八進位 | `Sub/LexicalAnalyzer.cs:141–162` |
| 前綴後無數字可先回 0，因此 `0x`、`0b`、`0x.5` 合法；其他殘留字元仍判無效 | 同上 `:163–169`；`Creator.Method.cs:2371–2385` |
| 尾端 `.數字列` 被略去，可為空；不是浮點尾數 | `Creator.Method.cs:2373–2382、2555–2564` |
| `e` 乘十的冪、`p` 乘二的冪，大小寫皆可；指數與尾數使用同進位 | `Sub/LexicalAnalyzer.cs:170–178` |
| 指數先讀 Int64，再 unchecked 轉 Int32；零指數不經浮點轉換 | 同上 `:178–188` |
| 非零指數以 double 計算後向零截斷；NaN、無限大與超界報錯 | 同上 `:184–187` |
| 十／二／十六進位掃描規則與 Convert.ToInt64；非法二進位數字、缺數字、溢位報錯 | 同上 `:192–263` |
| RGB 超出 0–255 報錯，沒有裁切 | `GameProc/Process.ScriptProc.cs:381–406` |
| 日本語採 Encoding(932)，寬字元判定比較 UTF-16 長度與 CP932 位元組數 | `Config/Config.cs:134`、`_Library/LangManager.cs:12–20`、`Creator.Method.cs:2363、2545` |

`0x+10` 是 16，但 `+0x10` 無效。`0x1e2` 是十六進位 482（e 已是數字）；
`0x1p10` 是 65536，`0b1e10` 是 100。負號放在二／十六進位前綴後會由 .NET 拋錯。
二／十六進位的 64 位高位採二補數，例如 `0xFFFFFFFFFFFFFFFF` 是 -1。
溢位與詞法錯誤以 `OverflowError`／`ValueError` 保留，不改成 0 或重新詢問。

## .NET Framework 補充實測與重現

引擎專案 `Emuera.csproj:18` 指定 .NET Framework 4.5。S50 使用 Windows PowerShell 5.1 的
.NET Framework CLR `4.0.30319.42000`，將上述 `ReadInt64`／`readDigits` 及 `StringStream.cs:11–99`
原碼節錄編譯，外加 `Creator.Method.cs:2363–2386` 的呼叫順序；1000 組固定種子格式的值／錯誤與 Python 一致。
原始探測產物保留於本機 `tmp/s50/`，不作執行期依賴。

可在 **Windows PowerShell（powershell.exe，並非 pwsh）** 重現關鍵邊界：

```powershell
Add-Type 'public static class NumericBoundary {
  public static long Cast(double d) { return unchecked((long)d); }
}'
[Environment]::Version.ToString()
[NumericBoundary]::Cast([Math]::Pow(2, 63))
[Convert]::ToInt64('FFFFFFFFFFFFFFFF', 16)
[Text.Encoding]::GetEncoding(932).GetByteCount([char]::ConvertFromUtf32(0x1F4AB))
```

依序得到 CLR 版本、Int64.MinValue、-1、2。原引擎超界比較時 Int64.MaxValue 先轉成 double，
恰等於 2**63；因此 `1p63` 通過比較後轉成 Int64.MinValue，照此保留，不替原作修正。

完整 BMP 查證可重現：

```powershell
$enc = [Text.Encoding]::GetEncoding(932)
$rows = for ($n = 0; $n -lt 65536; $n++) {
  "$n,$($enc.GetByteCount(([char]$n).ToString())),$([int][char]::IsDigit([char]$n))"
}
$rows | Set-Content -Encoding ascii numeric-bmp.csv
```

再由 Python 比對每列 `len(chr(n).encode("cp932", errors="replace"))` 與 `chr(n).isdecimal()`。
Python 3.10 的 BMP 數字分類全部相同；CP932 長度有以下 10 字差異，數值閘門明確修正：

| 字元 | .NET 位元組數 | Python 位元組數 |
|---|---:|---:|
| `« ¯ µ · ¸ » ゔ` | 2 | 1 |
| `‖ − 〜` | 1 | 2 |

其他無法編碼的 BMP 字元替代為 1 byte，非 BMP 則兩個 UTF-16 代理字元各 1 byte。
`char.IsDigit` 判定單一 UTF-16 字元：非 BMP 數字不通過；BMP 非 ASCII 數字雖可能通過掃描，
`Convert.ToInt64` 仍不接受（例如阿拉伯數字），但小數點後只做分類檢查而不轉換。

## 驗收

`tests/test_numeric_color.py` 涵蓋進位、符號、空白、小數尾綴、指數寬度、溢位、Unicode、色碼短路與色彩還原，
並驗證年齡指定殘值、Web 狀態 P5 與存讀檔。沒有新增手動色彩 UI、UNVERIFIED 或 DEVIATION。
