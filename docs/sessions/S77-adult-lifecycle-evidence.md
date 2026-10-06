# S77 連續鏈驗收依據

- 新增兩案 `tests/test_adult_lifecycle.py`；人工前態共用 `tests/_adult_lifecycle.py`，瀏覽器入口 `tmp/s77/browser_fixture.py`。STATUS／PLAN最終驗收由主代理收口。
- `fresh-adult-25-v1`，三位新建人工成年甲／乙／丙與管理員，建立起四年齡欄皆25；一般及另一形態預先設定。共用編輯、FINALIZE、TRANSFORM、TS、戰後／幽閉／戰鬥／救出、SHOP、存讀本體皆原生執行。
- Null敘事；數字輸出保留原按鈕值，另保留狀況列表的人工角色狀態行。沒有敘事全文、出生或新角色生成，也不擴張W02[8]、W05失去角色發現／返り血。
- 人工邊界依序為：已有三名角色的共用編輯入口；編輯確認後的敗北／敵方前態（妊娠路另設既有待結算狀態2）；救出戰的BOSS血量1；戰後FLAG45=1事件收尾前態。最後一項走原作隊伍重算後立即回SHOP分支，避免進入出生判定；不宣稱自然遭遇、自然救援事件或完整B05／B07。
- 人工GLOBAL預設已取得200–399成就以聚焦狀態等待；原取得函式仍執行，不驗成就提示。結界前態阻止額外妊娠來源；注入FixedRng，無效重試不消耗已完成的亂數。

## 操作與預期

1. 各啟動一次：`python tmp/s77/browser_fixture.py --mode prison --port 8790`；`--mode pregnancy --port 8791`。臨時存檔自動隔離。
2. 共用編輯按6→12→12→99→99。第一次12改另一形態外貌，第二次才切換TS；第一個99確認身體，第二個99確認角色並執行FINALIZE，接本模式原生流程。
3. 取得`/fixture/state`等待快照；輸入9無效，state_digest／rng_digest相同、result0=9。digest僅排除RESULT:0，因引擎INPUT本來就會覆寫該格。
4. 等待時甲的幽閉回數31=0。prison路TARGET=3、220=0（已換位與進首次事件）；pregnancy路TARGET=1、220=9、妊娠=1（仍在EVENTEND，尚未進幽閉）。四個外貌選擇依序0→1→0→1，回SHOP。
5. SHOP角色順序乙／丙／甲；甲索引3、狀態1、999=0、31=1，TS=-1、性別変化=1。選3不能切換TARGET；按130列表顯示甲幽閉0日目。隊列關係欄同步換位：乙[20,22,23,21]、丙[30,32,33,31]、甲[10,12,13,11]。
6. 瀏覽器開`/fixture/control`，按「開始人工救出戰」表單。`POST /fixture/rescue`只建立人工戰鬥前態並導回首頁。輸入998無效，state_digest／rng_digest不變。用原生戰鬥輸入1攻擊，BOSS殲滅→原生救出→EVENTEND→TURNEND，回SHOP。
7. 兩路甲皆維持索引3、形態0、計畫103；幽閉欄20／21／30／31／220皆0，TS=-1、性別変化=1、TARGET=1。prison路甲狀態0／999=1；pregnancy路狀態10／999=0／妊娠1。按130，前者不再列幽閉，後者列特別病棟。
8. 按200→1存手動槽1；取快照的characters_digest與狀態。按頁面原有重新開始（POST /restart），標題按1→槽1。new_session=true、phase=shop、characters_digest與存檔前相同；不重新套用fixture資料。
9. 讀回後按3：prison路TARGET=3，pregnancy路仍1。再按2→103→130，兩路均可原生選丙、設定休憩及看列表，TARGET=2，角色狀態／形態／隊列不變。停在SHOP，不推進下一日夜或出生。

## 來源

- 編輯：`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:1533–1606`；確認：`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_FINALIZE:221–487`。
- 轉換：`ERB/ヒロイン関連/TRANS_SEX.ERB@TS_MtoF:8–50`；首次呼叫：`ERB/地の文/MESSAGE_PRISON.ERB@MESSAGE_PRISON_PRISENTENCE_FIRST:65–113`（只核對分派與CALL，未摘錄本文）。
- 妊娠結算：`ERB/ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@NINSIN_CHECK_AFTER:171–189`；`ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:393`。FLAG805=0走妊娠1及TS等待。
- 隊列：`ERB/ヒロイン関連/SET_PARTYMEMBER.ERB@SET_PARTYMEMBER:22–26`、`@SHIFTBACK_CHARA:34–43`；首次及回數：`ERB/ゲーム内_イベント発生/敗北幽閉中イベント/PRISON.ERB@PRISON_EVENT:64–104、164–168`。
- BOSS救出：`ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:240–259`；恢復：`ERB/インターミッション画面/SHOP_TURNEND.ERB@RECALC_PARTYMEMBER:233–241`；事件收尾：同檔`@EVENTTURNEND:55–63`。
- 兩種隊列結果：`ERB/ヒロイン関連/AFTER_RESCUED.ERB@AFTER_RESCUED:14–16、32–36、58–61`與`ERB/ヒロイン関連/RECOVER_TO_PARTY.ERB@RECOVER_TO_PARTY:3–6`；列表：`ERB/インターミッション画面/SHOP_SHOW_SITUATION_LIST.ERB@SHOP_SHOW_SITUATION_LIST:44–108`。
- 引擎：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1165–1174`（換位不調整TARGET）；`reference/emuera-1824/Emuera/GameProc/Process.cs:249–252`（INPUT寫RESULT）；`reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs:757–780`（EVENTLOAD後SHOW_SHOP）。
- 角色／變數存讀：`reference/emuera-1824/Emuera/GameData/Variable/CharacterData.cs:289–312`與`reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs:663–686`；JSON沿既定規格。新案比對全部角色序列化欄位，未宣稱RNG或.sav位元相容。

## W03 完成條件核對

- 編輯後進戰鬥：沿用S76已驗的真共用編輯→SHOP→戰鬥，本次另補編輯TS→生命週期→救出戰。
- 妊娠／幽閉／救出能續行：兩個定向連續鏈已以Web邊界測試通過，真瀏覽器由主代理獨立執行；妊娠停在原作病棟及可操作SHOP範圍，不含W02出生。
- 裝備效果與顯示、對應停止定向案例：沿用S70–S76既有原文／測試／瀏覽器證據；本次不重建全部分支。
- 沒有產品流程改動，正式500沿用S76基線並明記未重跑；沒有新增UNVERIFIED／DEVIATION。W02既有阻塞及W05／W09矩陣仍保留，不能將本次鏈冒充整列完成。

## 主代理驗收
- 全pytest：`5021 passed, 1 warning in 160.53s (0:02:40)`；兩路真瀏覽器依上列操作完成，所有角色保存內容digest一致，console錯誤0，頁籤／伺服器已關。
- 證據：tmp/s77/browser-{prison,pregnancy}-*.json、prison-complete.png、pregnancy-complete.png。UI觸發列表且輸出正確；列表立即回SHOP，其停留／等待仍屬W07，不宣稱畫面持續顯示通過。
- W03範圍完成；不含W02完整出生、W05自然救援及整列B矩陣。沒有產品改動，沿用S76正式500而未重跑。
