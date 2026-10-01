# 現況（唯一真相，≤150 行）

更新：2026-10-01（S16）

## 已完成

- 建立 repo，`source/earGVP/` 原作基線入庫（唯讀）；`reference/emuera-1824/` 引擎原始碼（查證用）。
- **S01** 原作分析 wiki（`docs/wiki/era/`）＋骨架、CSV 載入器。**S02** 狀態模型（`docs/wiki/python/state.md`）、JSON 存讀檔、文字輸出層。
- **S03** 引擎規格查證、新遊戲、SHOP Web（`python -m eragvt`）、存讀檔（0–19＋自動 99）。**S04** 行動（休憩・鍛錬・出撃）與
  TURNEND／EVENTSHOP（`docs/wiki/era/actions.md`）。**S05** 戰鬥核心（`eragvt.game.battle`）。**S06** 拘束・性攻擊・敗北 → 幽閉。
- **S07** 口上／地の文 catalog（`eragvt.narration`，`docs/wiki/python/narration.md`；狀態變化行走 `narration/hooks.py`）。
  覆蓋率 13384 函式中可執行 12814（95.7%），`python -m eragvt --narration-report`。
- **S08** 幽閉（`docs/wiki/era/prison.md`）：PRISON_EVENT、救出、洗脳・悪堕ち、全滅／ソロ結局本文（S12 起接ゲームオーバーモード）。
- **S09** 身體資料（`eragvt.game.body`，`docs/wiki/era/body-profile.md`）：初期セット角色原作也不生成（NO ≠ 0）→ 敏捷 0・攻擊 2 倍是原作行為。
- **S10** 開局改回原作預設路徑（`eragvt.game.chara_make`，`docs/wiki/era/flow.md` §1）：標題 `[0]` 後 2 択「[0] おまかせ（汎用キャラ 3 名）／
  [1] 初期セット『特装戦隊』」。`event_first(state, data, preset=None)` 為預設；既有測試明確指定 `preset=PRESET_TOKUSOU`。
- **S11** 拡張度與いちゃラブセックス（設計與照原作的怪處：`docs/wiki/era/gaping.md`）。
  - `battle.gaping`：V_GAPING／A_GAPING／GET_V・A_GAPING_EXP（CFLAG:34 ≠ 0）、GAPING_RANK_STR、PRINT_TENTACLE_SIZE、PRINTFORM_GAPING_NOW；
    `PALAM_CALC_GAPING`・`PRISON_GAPING` 的停止點解除（PRISON_GAPING 的 GET_*_EXP 改為 OPTION 1，照原作）。
    `TextOutput.html_print`（HTML_PRINT；`<nonbutton title>` → Web tooltip）。
  - 新模組 `eragvt.game.lovesex`：LOVESEX_NIGHT／LOVESEX_KIND／SEX_V／SEX_A／SEX_V_CONDOM（INPUT）；`ninsin.after_pill`（INPUT）、
    NINSIN_HANTEI 的一般人父親分岐（`愛する人 = -3`）。`turnend.event_turnend` 改為 generator。地の文 4 函式走 catalog，
    `MESSAGE_KATAOMOI_NIGHT` 的 TALENT 代入 2 行進 `hooks.LOVESEX_HOOK_LINES`。
  - `MESSAGE_SEX_SPCOM7` 的 INPUTS（CFLAG:34 > 0）接上（generator），輸入 "1" 的動画サイト視窗 S14 移植。
  - 模擬腳本 `tools/sim.py`（之後各階段共用）。測試共 646 個（新增 `tests/test_gaping.py` 52、`tests/test_lovesex.py` 34）。

- **S12** ゲームオーバーモード（`docs/wiki/era/flow.md` §9）：`shop.change_gameover_mode`（FLAG:0 = 0、DAY:2 = DAY*2+TIME）、
  ENDING_1／4／5 不再停止（FLAG:999 = -998 → FORCEWAIT → 回到 EVENTEND／PRISON，下一次 PRISON 歸 0）。之後每回合 PRISON 對
  全員（CFLAG:0 2／3／9 也）執行，SHOP 隱藏選單。`GAME_MODE_CHECK`（FLAG:906 版，SAVEINFO 用）、USERSHOP [110]〜[160] 的原作條件、
  `AKUOTI_ATTACK` 的候補抽選（候補有才停止）。CHECK_GAMEOVER_F 的其餘分岐 S04〜S08 已移植，本階段逐一加測試。
  `tools/sim.py` 新增ゲームオーバーモード統計（並改為停止前先記錄敗北／進入）。測試共 705 個（新增 `tests/test_gameover.py` 59）。

- **S13** 妊娠・出産・子供（`docs/wiki/era/pregnancy.md`：狀態機與 CFLAG 對照、照原作的怪處）。
  - `battle.ninsin`：NINSIN_HANTEI 全父親分岐（悪堕ちキャラ・仲間・PAPA_ID 0 的 static PREG_PER）、NINSIN_SUBMIT／NINSIN_FLAG／
    NINSIN_CHECK_AFTER／NUM_CHILD_TENTACLE／PREGNANT_RANDOM_SIZE／PREGNANCY_*_EXPAND、Ｈ触手＋排卵。ACT_LIMIT 妊娠後期。
  - 新模組 `game.pregnancy`（BIRTH_HANTEI〔generator〕、BIRTH_TENTACLES、ABL_UP_BIRTH、苗床出産）、`game.child`（BIRTH_DAUGHTER_HUMAN／
    TENTACLE_ORIGIN、GROW_HANTEI、ADD_CHILD、CHILD_GROW_1／2、RESCUE_CHILD）、`game.firstsetting`（SELFCALL／SIZE_SETTING 的
    「直接 [99] 決定」、フィート選擇・SET_FEAT_DEFAULT、変身後名等選單）、`game.relation`（CHECK_ALL_RELATION／GET_RELATION）。
    `turnend.recalc_partymember` 改為 generator（RESCUE_CHILD）。地の文 `MESSAGE_NINSIN.ERB` 走 catalog，CFLAG:226 兩行進
    `hooks.NINSIN_HOOK_LINES`。測試共 775 個（新增 `tests/test_pregnancy.py` 70）。

- **S14** 動画流出（`battle.after.douga_ryusutu`：`戦闘イベント.ERB@DOUGA_RYUSUTU`:1338–1478 全 TFLAG:21 組合、CFLAG:284／285）。
  CFLAG:284／285 的後續讀取（SHOP_TURNEND:543／751–754）已在 S04 移植，本階段補測試；FLASHNEWS 的讀取屬未移植新聞本體（deviations）。
  catalog 擴充：`$ラベル`／GOTO（最上層ラベル）、INPUTS（generator 呼叫 `run_function_gen`，以重放實作）、DRAWLINEFORM；
  `汎用関数/WindowDrawer.ERB`＋`TagSetText.ERB` 以 Python 移植（`narration/windowlib.py`）→ `MESSAGE_SEX_SPCOM7` 與動画サイト
  `MESSAGE_SEX_VIDEO_SITE_Window` 全由 catalog 執行（`docs/wiki/python/narration.md`「動画サイト」）。覆蓋率 13384 中可執行 12828
  （95.8%，其中需 INPUTS 2）。測試共 821 個（新增 `tests/test_video_leak.py` 45）。

- **S15** 戰後レイプ・自慰系。新模組 `battle.rape`：`戦闘イベント.ERB@AFTER_TRAIN_RAPE`:962–1334 全分岐（本文 Python 移植，
  SHITAGI_COLOR／KAIZOU_PANT 走 catalog）＋`CALC_GANGBANG.ERB@CALC_GANGBANG`（全シチュエーション，靜態 LOCAL 照原作），
  AFTER_PILL（INPUT）→ `after.event_end` 改為 generator；RETURN 1 → `DOUGA_RYUSUTU, 1` 動画流出接通。`battle.self_kind`：
  `FORCE_夜間自慰.ERB` 的 SELF_BATTLEEND／SELF_CHECK／SELF_KIND／SELF_N・B・A・V（靜態 `#DIM Ｖ自慰可` 照原作），接上強制自慰
  （SPCOM6）、戰後自慰（SUBEVENT_BATTLEEND）、夜間自慰（`turnend.self_night`）。地の文 MESSAGE_SELF_*／MESSAGE_OTHER_SELF_* 走
  catalog（無狀態變化）。怪處見 deviations「原作行為」S15。測試共 876 個（新增 `tests/test_rape_self.py` 55）。

- **S16** ＳＰ変身・バースト。`battle.commands`：COM73（ＳＰ変身：CFLAG:1 = 2、EX→SP ゲージ、狀態異常回復、性格別心境、アウター回復）、
  COM70（ＳＰバースト，拘束中）、COM74（ＳＰフルバースト，`ADDBATTLESITUATION("EX不可")`＝`core.add_battle_situation`，照原作是覆寫）；
  地の文 MESSAGE_BATTLE_CHARA_SP_TRANSFORMCALL／SP_BURST／SP_FBURST／TENTACLE_ATTACK_OVERCHARGE 走 catalog。バースト攻撃
  （TCVARn:217）：`COM_ATTACK_COMMON` 全分岐（連続 6 回・使役・設置 油断度〔[設置]本體也一併接上〕・撹乱 怯み・知略・クリティカル倍率・
  [反撃] 蓄積加算／過剰蓄積・反動・装甲オートガード・知略見切り）、`PRINT_COMBO` 表示、`hantei` 命中／カス当たり／回避／DAMAGE 與
  `FSTYLE_ATTACK` [反撃]。`train.status_charge_limit`（STATUS_PRINT_CHARGE 的 TCVARn:206 代入）。CFLAG:1 == 2 的既存分岐
  （CHARA_SHINKYOU／CHARA_STATE_CHANGE／HANTEI／CORRECTION_TRANS／EVENTCOMEND 的 SP ゲージと解除／PALAM_UP／ENEMY_ACTION）逐一對照，
  皆已照原文。怪處見 deviations「原作行為」S16。測試共 970 個（新增 `tests/test_sp_burst.py` 94）。

## S16 模擬（`tools/sim.py` 的 `run_one`，seed 0–249，`--max-shop 200`；4 行程並列；seed 0–2 與逐次執行一致）

ＳＰ変身・ＳＰバースト・ＳＰフルバースト・COM17 的停止全部消失。

| 指標 | 預設 S15 | 預設 S16 | 初期セット S15 | 初期セット S16 |
|---|---:|---:|---:|---:|
| 停止前 SHOP 次數（平均／最多） | 175.74／201 | 201.00／201 | 150.64／201 | 200.29／201 |
| ゲームオーバーモード進入局／進入後 SHOP 平均（最多） | 217／186.44（197） | 250／186.46（197） | 184／187.74（197） | 249／187.39（197） |
| 敗北局／敗北後 SHOP 平均 | 239／175.30 | 250／192.81 | 220／162.14 | 250／192.26 |

- 停止原因：預設 上限 250（全局）；初期セット 上限 249、`ACT_LIMIT：寄生による行動制限は未移植` 1（seed 101，S16 後才走到的既存停止點）。
- 新路徑實際執行次數（計數用包裝，次數／局數）：預設 COM70 14／14、COM73 12／12、COM74 3／3、バースト攻撃 7／5；
  初期セット COM70 29／29、COM73 36／35、COM74 9／9、バースト攻撃 8／7。

## 下一步

- **S17：寄生系統**（`docs/sessions/S17-parasite.md`）。之後候選：[反撃]スタイル（ＥＸ反撃・HANGEKI_TO_TENTACLE；S16 已接バースト側）、悪堕ちキャラ（AKUOTI_EVENT）、
  クズ市民の脅迫（INTIMIDATION_EVENT：S15 起 CFLAG:286 會增加，但需設定「クズ市民による幽閉」ON 才觸發）、狀態畫面、FLASHNEWS、
  ランダム命名畫面。
- 已裁決（2026-09-30）：拡張度初期值照原作不設定；初期セット身體資料問題因 S10 改回預設開局而不再需要偏離；
  S13 苗床出産的 static LOSEDEF 等怪處全部照原作。
- 口上 catalog 待擴充：改狀態的口上（hook 化）、入れ子內 $ラベル 的 GOTO（`KOJO_AEGI.ERB` $ＭＡＸ２，199 函式受影響）、SPLIT／STRDATA、未實作式中関数（覆蓋率報告）。
- deviations.md 需裁決：振り解く `LOCAL:O`、口上的狀態副作用、口上 catalog 實行時失敗的回復、S08 以後新增項。

## 仍會停止的分岐（`NotImplementedError` → Web 停止）

頻度見上方 S16 模擬。其餘登記但罕見：
- 幽閉：ラスボス／悪堕ちキャラ 的幽閉、容貌變化（設定 ON）、RECOVER_CORRUPTION、TS 性別變化、ラスボス出現後的淫紋陥落。
- 妊娠・子供（S13）：TS 変身キャラ妊娠時的女體化（TS_MtoF）、子供名字／変身後名／かけ声／名乗り的手入力（INPUTS）與ランダム命名畫面、
  デバッグモード的妊娠確率輸入。
- TURNEND：AKUOTI_EVENT（悪堕ちキャラが抽選に當選）、ENDING_1 的エンドレス分岐、寄生触手的暴走／共生取得、INTIMIDATION／KIDNAPPING。
- 指令：47 説得する、反擊（[反撃]スタイル、`HANGEKI_TO_TENTACLE`）、ACT_LIMIT 的寄生行動制限。
- ステータス PALAM 表示（FLAG:801 bit 5）、素股焦らし失敗的處女喪失、觸手服／觸手拘束具、
  悪堕ち／雜魚／クズ市民／ラスボス／事件戰／エンドレス、デバッグ模式、`HATUJOU_TO_HAIRAN` 地の文。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（整體「暫時維持」，S06 以後新增項待裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局：預設（NORMAL＋汎用キャラ 3 名おまかせ）與初期セット「特装戦隊」；其他初期セット／キャラメイク畫面的手動設定未移植。
- 可玩範圍：休憩・鍛錬・出撃（含被拘束的戰鬥、拡張度、敗北後的幽閉與救出、戰後レイプ）、夜間いちゃラブ・自慰、妊娠・出産・子供的加入、
  全滅後的ゲームオーバーモード。其他行動、11 日目夜的日數超過結局等會進入 Web「停止」畫面（deviations、上一節）。
- 初期セット選項的角色身體資料為 0（原作同樣不生成），戰鬥中女性敏捷 0・攻擊 2 倍（原作行為，是否偏離待決定）。
  預設開局的汎用キャラ會生成（體重正常）。角色製作／狀態畫面的手動生成未移植。
- 襲撃／救援（DAY ≥ 3）與子触手襲来成立時只顯示「スキップ」訊息（deviations）。
