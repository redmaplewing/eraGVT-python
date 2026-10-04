# 引退名簿與主動引退（S44）

入口是SHOP [169]名簿與[170]主動引退，原生實作在`eragvt.game.retirement`。
以下簡寫`INTAI`指`ERB/ヒロイン関連/INTAI.ERB`；文字由`tools/extract_retirement_text.py`抽取，未新增敘事。

## 入口、選擇與確認

- `ERB/インターミッション画面/SHOP.ERB@SHOW_SHOP:174–179、@USERSHOP:289–292`：
  兩入口都要求加入引退選項開啟；[170]另要求CHARANUM>1。[169]即使只剩MASTER仍可看紀錄。
- `ERB/ヒロイン関連/INTAI_CHARA_LIST.ERB@INTAI_CHARA_LIST:7–47`：
  列表略過MASTER及CFLAG:0為2/3的角色；狀態1/4/9/10/11附原文標記。
  999取消；輸入必須介於1與CHARANUM−1，且狀態不是2/3。只有被列出者可選，沒有費用或能力門檻。
- `INTAI@CHARA_INTAI:1–22`：選定後TARGET改為該角色，取消確認不恢復舊TARGET。
  第一問0是／1否，第二問0否／1是；僅0→1執行引退，選擇人物時999則不動TARGET。
- `INTAI@INPUT_ROOP:41–49`檢查`RESULT > ARG`，因此ARG=2時接受0/1/2；
  雖然畫面只列0/1，2仍依原作作為不執行引退的有效值，未擅自改成錯值重問。

## 紀錄與刪除

- `INTAI@OLD_GIRL:25–39`是普通函式，不是資料陣列或存檔宣告：
  呼叫MASSAGE_INTAI→FLAG:251加一→DELCHARA TARGET→TARGET=0。獎勵資金／防衛力只是註解，不執行。
- `INTAI@MASSAGE_INTAI:51–218`：LOCAL:0先設1，按原文條件加1/2/4；
  LOCAL:1先設0，體能點數由兩項基礎值總和除10，再加其餘五項基礎值。
  耗損門檻依序為>746、≥580、≥480、≥380、≥280、≥180、≥80、其餘，LOCAL:1對應0/1/2/3/4/5/5/6。
  特殊素質優先於耗損門檻，維持LOCAL:1=0；判定次序與原文顯示逐段手翻。
- `INTAI@MASSAGE_INTAI:222–332`：死亡／幽閉／市民監禁優先，FLAG:255加一；
  其餘依身體狀態、LOCAL:0及LOCAL:1分類至引退／後援／治療。
  缺肢且非繁殖袋的分支不加FLAG:252–255，只有OLD_GIRL增加總數251；照原作保留。
  `:298–308`整段已註解的特殊處置沒有啟用。
- `INTAI@MASSAGE_INTAI:334–342`：姓名寬30靠左、原因寬8靠右、現況寬20靠右，
  原HTML字串追加至SAVESTR:50（尾端` <br> <br>`），不是保存已渲染的Line。
- `INTAI@CHAR_INTAI_LIST:344–361`只有空白判斷與整段HTML_PRINT，沒有名簿容量／分頁／刪除紀錄指令。
  SAVESTR已在現有JSON模型內；舊存檔未設定索引50時讀空字串，不新增欄位或變更格式版本。
- 對正式ERB精確搜尋OLD_GIRL／MASSAGE_INTAI／CHAR_INTAI_LIST共6處，只有本檔定義、主動確認呼叫與SHOP名簿入口；
  沒有另一條自動引退呼叫鏈，因此不額外接入回合流程。

## 顯示等待與引擎依據

- `reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1061–1067`：
  DELCHARA只刪除指定角色並壓縮列表，不修TARGET、ASSI或其他角色欄位；TARGET=0是原作OLD_GIRL另做的事。
  Python沿用`GameState.del_chara`，保留ASSI、CFLAG:9與固有編號CFLAG:240，不額外重編。
- `reference/emuera-1824/Emuera/GameData/StrForm.cs:248–263`：百分比字串格式按字寬填空白，不截斷過長文字。
- `reference/emuera-1824/Emuera/GameView/HtmlManager.cs:326–331`：br建立換行。
  名簿交給既有`TextOutput.html_print`，保留空白與多列；Web不把原始br字樣顯示給玩家。
- `reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:90–93`的W設等待旗標；
  `reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、701–734`以EnterKey等待，
  只有IntValue／StrValue分支寫入數值／字串結果；PRINTW確認不寫RESULT或RESULTS。
- 本階段名簿與引退報告依原作PRINTW位置局部等待，避免下一次LB遮掉尚未看過的名簿／報告。
  借用既有TextInputRequest通道接收空白Enter，未呼叫INPUTS，附「按 Enter 繼續」操作提示，沒有新增遊戲選項。
  `ERB/汎用関数/PRINT_LINE.ERB@DOT_AFTER:43–55`保留FLAG:801 bit3決定的1／3次等待。
  最後報告PRINTFORMW確認後才增加引退總數並刪除角色。
- `reference/emuera-1824/Emuera/GameProc/Process.cs:249–252`：INPUT僅寫RESULT:0。
  `reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`：函式末端RESULT:0設0，尾格及RESULTS不變。

## 驗證

- 新模組先紅；完成後發現既有不阻塞PRINTW會被SHOP的LB遮掉，新增GameSession.screen案例先2紅，再補局部等待。
- 定向102項：資格／錯值／999、雙重確認與2、耗損門檻／分類優先序、原文分支、
  刪除索引及尾格保留、連續引退、空／多列HTML、存讀檔、實際畫面可見性、等待前不得刪除角色。
- `102 passed, 1 warning in 7.51s`。Web邊界用真實表單確認text欄位無required，空白POST可返回SHOP。
- 主代理獨立完整pytest：`2875 passed, 1 warning in 369.55s (0:06:09)`；既有Starlette/httpx警告。
- 標準500局：default246上限／4回標題、tokusou250上限，catalog失敗0；逐seed全部欄位與S43一致。
  default／tokusou各seed0–249、max-shop200、actions101–108；10個50局獨立前景批次exit=0，seed全集與log／JSONL一致。
  產物及audit留在`tmp/s44/`，主代理亦獨立核對通過；標準模擬不操作[169]/[170]，選單互動另由定向測試驗證。
- 沒有新增UNVERIFIED或原作規則偏離；既有WAIT簡化只在本階段引退畫面局部補完。
