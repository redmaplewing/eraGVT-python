"""Emuera のシステム処理（タイトル、SHOP ループ、SAVEGAME／LOADGAME、オートセーブ）に相当する状態機械。

依據：`reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs`（以下「SystemProc」）。
Web（`eragvt.web`）はこのクラスに数値入力を渡し、`screen()` を描画するだけ。
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..data.csv_loader import GameData
from ..state import GameRng, GameState
from ..state.savefile import (
    GameIdentity,
    GlobalStore,
    SaveFormatError,
    load_from_file,
    read_save_comment,
    save_to_file,
)
from ..text import Line, NarrationService, NullNarrationService, TextOutput
from . import shop
from .action import Ctx
from .config import config_gen, update
from .era import limit
from .input_request import TextInputRequest
from .opening import event_first_gen
from .turnend import run_turn

AUTOSAVE_INDEX = 99  # SystemProc:805
SAVE_DATA_NOS = 20  # emuera.config「表示するセーブデータ数:20」
# emuera.config「オートセーブを行なう:YES」
AUTOSAVE = True


class Phase(str, Enum):
    TITLE = "title"
    NEW_GAME = "new_game"  # @EVENTFIRST 中の INPUT 待ち（開局経路の 2 択・HEROINE_PRESET・コンフィグ）
    SHOP = "shop"
    ACTION_CONFIRM = "action_confirm"
    TURN = "turn"  # ACTION_MAIN〜TURNEND・@EVENTSHOP 中の INPUT 待ち
    HALTED = "halted"  # 未移植の処理に到達して停止（タイトルに戻るしかない）
    SAVE_SELECT = "save_select"
    SAVE_OVERWRITE = "save_overwrite"
    LOAD_SELECT = "load_select"


class GameSession:
    def __init__(
        self,
        data: GameData,
        save_dir: Path,
        rng: GameRng | None = None,
        narration: NarrationService | None = None,
        now: Callable[[], datetime] = datetime.now,
        global_store: GlobalStore | None = None,
    ) -> None:
        self.data = data
        self.save_dir = save_dir
        self.rng = rng or GameRng()
        self.narration = narration or NullNarrationService()
        self.now = now
        self.identity = GameIdentity.from_data(data)
        # グローバル変数（メモリ）と global.json。Emuera ではタイトルに戻ってもメモリは消えない（ResetData は GLOBAL を
        # 初期化しない：VariableEvaluator.cs@ResetData:1132–1141）ので、Web はアプリ単位の store を渡す。
        self.globals = global_store or GlobalStore.in_dir(save_dir, self.identity)
        self.out = TextOutput()
        self.state: GameState | None = None
        self.phase = Phase.TITLE
        self.input_kind = "number"
        self._confirm_kind = ""
        self._save_target = -1
        self._load_from_title = False
        self._turn: Generator[None, int, None] | None = None
        self._turn_done: Callable[[], None] = lambda: None
        self._gen_phase = Phase.TURN
        self._gen_result: object = None
        # SAVEGAME（ジェネレータ内）から戻る先。None なら SHOP の [200]（loadPrevState → @SHOW_SHOP）
        self._save_return: Callable[[], None] | None = None
        self.begin_title()

    # --- 画面 -------------------------------------------------------------------

    def screen(self) -> list[Line]:
        """最後の @LB（50 行の空行）以降の行。Emuera は画面を流すだけなので、ここで切り詰めて返す。"""
        lines = self.out.lines
        run = 0
        start = 0
        for i, line in enumerate(lines):
            if line.kind == "text" and line.text == "" and not line.wait:
                run += 1
                if run >= 50:
                    start = i + 1
            else:
                run = 0
        return lines[start:]

    def input(self, value: int | str) -> None:
        if self.input_kind == "text":
            value = str(value)
        else:
            try:
                value = int(value)
            except (ValueError, TypeError):
                return
        handler = {
            Phase.TITLE: self._title_input,
            Phase.NEW_GAME: self._turn_input,
            Phase.SHOP: self._shop_input,
            Phase.ACTION_CONFIRM: self._action_confirm_input,
            Phase.TURN: self._turn_input,
            Phase.HALTED: self._halted_input,
            Phase.SAVE_SELECT: self._save_select_input,
            Phase.SAVE_OVERWRITE: self._save_overwrite_input,
            Phase.LOAD_SELECT: self._load_select_input,
        }[self.phase]
        handler(value)

    # --- タイトル（SystemProc@beginTitle:133–188、@endOpenning:197–231）----------

    def close(self) -> None:
        """放棄目前輸入流程，關閉等待執行緒及其狀態交易區間。"""
        if self._turn is not None:
            self._turn.close()
            self._turn = None

    def begin_title(self) -> None:
        self.input_kind = "number"
        gb = self.data.game_base
        out = self.out
        out.drawline()
        out.set_align("center")
        out.printl(gb.get("タイトル", ""))
        ver = self.identity.version
        if ver != 0:
            # GameBase.cs@ScriptVersionText:26–38
            minor = f"{ver % 1000:03d}" if ver % 10 != 0 else f"{ver % 1000 // 10:02d}"
            out.printl(f"{ver // 1000}.{minor}")
        out.printl(gb.get("作者", ""))
        out.printl(f"({gb.get('製作年', '')})")
        out.printl()
        out.printl(gb.get("追加情報", ""))
        out.set_align("left")
        out.drawline()
        out.printl("[0] 最初からはじめる")  # ConfigData.cs:131 システムメニュー0
        out.printl("[1] ロードしてはじめる")  # :132
        self.phase = Phase.TITLE

    def _title_input(self, value: int) -> None:
        if value == 0:
            # SystemProc@endOpenning:197–209 → @beginFirst:233–242（@EVENTFIRST）
            self.state = GameState.new(self.data, rng=self.rng)
            self.out.drawline()
            self.out.printl()
            gen = event_first_gen(self.state, self.data, self.out, self.globals)
            self._run_gen(gen, self._after_event_first, phase=Phase.NEW_GAME)
        elif value == 1:
            self._load_from_title = True
            self.begin_load_game()
        else:
            self.out.clearline(1)
            self.out.printl("無効な値です")

    def _after_event_first(self) -> None:
        if self._gen_result is False:  # MODE_SELECT [100]：RESETDATA → BEGIN TITLE（オープニング処理.ERB:82–85）
            self.state = None
            self.begin_title()
            return
        self.begin_shop(called_when_normal=True)  # オープニング処理.ERB:292 BEGIN SHOP

    # --- SHOP（SystemProc@beginShop:614–628、@endCallEventShop:630–640、@endAutoSave:670–680）

    def begin_shop(self, called_when_normal: bool) -> None:
        """@EVENTSHOP はジェネレータ（S17：寄生触手のイベントが INPUT を使う）。INPUT 待ちの間は Phase.TURN。"""
        assert self.state is not None
        try:
            gen = shop.event_shop_gen(self.state, self.data, self.out, self.narration)
        except NotImplementedError as exc:  # @EVENTSHOP 内の未移植イベント
            self._halt(exc)
            return
        self._run_gen(gen, lambda: self._after_event_shop(called_when_normal))

    def _after_event_shop(self, called_when_normal: bool) -> None:
        if AUTOSAVE and called_when_normal:
            self._autosave()
        self._show_shop()

    def _autosave(self) -> None:
        """SystemProc@beginAutoSave:642–654：SAVEDATA_TEXT = 日時 + " " + @SAVEINFO の PUTFORM、99 番へ。"""
        assert self.state is not None
        now = self.now()
        text = now.strftime("%Y/%m/%d %H:%M:%S") + " " + shop.save_info(self.state, self.data, now)
        save_to_file(self._save_path(AUTOSAVE_INDEX), self.state, text, self.identity)

    def _show_shop(self) -> None:
        assert self.state is not None
        self._run_gen(
            shop.show_shop_gen(self.state, self.data, self.out, self.narration), self._after_show_shop
        )

    def _after_show_shop(self) -> None:
        self.phase = Phase.SHOP

    def _shop_input(self, value: int) -> None:
        """SystemProc@shopWaitInput:691–735：販売アイテム数 0（_Replace.csv）なので常に @USERSHOP。"""
        assert self.state is not None
        st, out = self.state, self.out
        if 1 <= value <= st.charanum - 1:
            shop.select_target(st, out, value)
        elif value == 50:
            out.printl("（未實作：パーティ編成 SHOP_ORGANIZE_PARTY）")
        elif value == 60:
            shop.toggle_party_view(st, out)
        elif value == 90:
            shop.multi_set(st, out)
        elif value == 100:
            kind = shop.action_confirm_prompt(st, self.data, out)
            if kind == "begin":
                self._begin_action_main()
            else:
                self._confirm_kind = kind
                self.phase = Phase.ACTION_CONFIRM
            return
        elif 101 <= value <= 108:
            shop.usershop_set_action(st, self.data, out, value, st.flag[9])
        elif value == 200:
            self.begin_save_game()
            return
        elif value == 300:
            self._load_from_title = False
            self.begin_load_game()
            return
        elif value == 130:  # SHOP.ERB:271–273
            shop.shop_show_situation_list(st, self.data, out, self.narration)
        elif value == 110:  # SHOP.ERB:246–249 TARGET = LIMIT(TARGET, 1, CHARANUM-1) → CALL SHOW_STATUS_CHARA_SELECT
            from .status_screen import show_status_chara_select

            st.target = limit(st.target, 1, st.charanum - 1)
            self._run_gen(show_status_chara_select(self._ctx(), st.target), self._show_shop)
            return
        elif value == 112:  # SHOP.ERB@USERSHOP:257–259
            if shop.usershop_calls_submenu(st, value):
                from .clothing import cloth_wear_gen
                self._run_gen(cloth_wear_gen(self._ctx()), self._show_shop)
                return
        elif value == 120:  # SHOP.ERB@USERSHOP:267–269
            if shop.usershop_calls_submenu(st, value):
                from .clothing_inventory import inventory_gen
                self._run_gen(inventory_gen(self._ctx(), purchase=True), self._show_shop)
                return
        elif value == 111:  # SHOP.ERB@USERSHOP:251–254
            if shop.usershop_calls_submenu(st, value):
                from .character_powerup import character_powerup_gen
                self._run_gen(character_powerup_gen(self._ctx()), self._show_shop)
                return
        elif value == 113:  # SHOP.ERB@USERSHOP:261–264
            if shop.usershop_calls_submenu(st, value):
                from .drug_preparation import drug_preparation_gen
                self._run_gen(drug_preparation_gen(self._ctx()), self._show_shop)
                return
        elif value == 150:  # SHOP.ERB:275–278
            if shop.usershop_calls_submenu(st, value):
                out.printl(f"（未實作：[{value}]）")
        elif value == 160:  # SHOP.ERB:281–285
            if shop.schedule_selectable(st):
                from .schedule import schedule_gen

                self._run_gen(schedule_gen(self._ctx()), self._show_shop)  # CALL SCHEDULE → @USERSHOP 終了 → @SHOW_SHOP
                return
            out.printw("スケジュールを設定するキャラクターが選択されていません")
        elif value == 700:  # SHOP.ERB:302–303 CALL CONFIG（FROM = ""）→ @USERSHOP 終了 → @SHOW_SHOP
            self._run_gen(config_gen(st, self.data, out, self.globals), self._show_shop)
            return
        elif value in (169, 170, 180, 800):
            out.printl(f"（未實作：[{value}]）")
        # @USERSHOP 終了 → SystemProc@endCallEventBuy:737–755 → endAutoSave → @SHOW_SHOP
        self._show_shop()

    def _action_confirm_input(self, value: int) -> None:
        assert self.state is not None
        if shop.action_confirm_answer(self.state, self.data, self._confirm_kind, value):
            self._begin_action_main()
        else:
            self._show_shop()  # RETURN 0 → @USERSHOP 終了 → @SHOW_SHOP

    def _begin_action_main(self) -> None:
        """JUMP ACTION_MAIN（SHOP.ERB:557）→ 各キャラの行動 → @EVENTTURNEND → BEGIN SHOP。"""
        assert self.state is not None
        # BEGIN SHOP（EVENTTURNEND 実行中の SystemState は Normal：SystemProc@beginTurnend:609–611）
        # → calledWhenNormal = true（Process.State.cs@Begin:271–273）→ オートセーブあり（SystemProc:633）
        self._run_gen(run_turn(self._ctx()), self._after_turn)

    def _ctx(self) -> Ctx:
        assert self.state is not None
        return Ctx(self.state, self.data, self.out, self.narration, self.globals)

    def _after_turn(self) -> None:
        from .action import Step

        if self._gen_result == Step.TITLE:  # SHOP_TURNEND.ERB:44–47 RESETDATA → BEGIN TITLE（S27：ENDING_3）
            self.state = None
            self.begin_title()
            return
        if self._gen_result == Step.FALLTHROUGH:  # S28a：最初の ACTION_MAIN が BEGIN なしで終了 → @USERSHOP 終了 → @SHOW_SHOP
            self._show_shop()
            return
        self.begin_shop(called_when_normal=True)

    def _run_gen(self, gen: Generator[None, int, object], done: Callable[[], None], phase: Phase = Phase.TURN) -> None:
        """INPUT を yield するジェネレータを駆動する。終了したら戻り値を `_gen_result` に入れて `done`。"""
        self._turn = gen
        self._turn_done = done
        self._gen_phase = phase
        self._gen_result = None
        self._advance_turn(None)

    def _turn_input(self, value: int | str) -> None:
        self._advance_turn(value)

    def _advance_turn(self, value: int | str | None) -> None:
        assert self._turn is not None
        from .ending import SaveGameRequest

        self.input_kind = "number"
        try:
            if value is None:
                y = next(self._turn)
            else:
                y = self._turn.send(value)
        except StopIteration as stop:
            self._turn = None
            self._gen_result = stop.value
            self._turn_done()
            return
        except NotImplementedError as exc:
            self._turn = None
            self._halt(exc)
            return
        self.input_kind = "text" if isinstance(y, TextInputRequest) else "number"
        if isinstance(y, SaveGameRequest):
            # S27：ジェネレータ内の SAVEGAME（ENDING.ERB:22）→ セーブ画面、終わったら（キャンセル含む）続きから
            # （SystemProc@saveGameWaitInput:865–869／@endCallSaveInfo:926–934 の loadPrevState）
            self._save_return = lambda: self._advance_turn(None)
            self.begin_save_game()
            return
        self.phase = self._gen_phase

    def _halt(self, exc: NotImplementedError) -> None:
        self.out.printl()
        self.out.printl(f"（未實作のため停止しました：{exc}）")
        self.phase = Phase.HALTED

    def _halted_input(self, value: int) -> None:
        self.out.printl("（未實作のため停止中。「タイトルに戻る」で再開してください）")

    # --- SAVEGAME / LOADGAME（SystemProc:782–990）-------------------------------

    def _save_path(self, index: int) -> Path:
        return self.save_dir / f"save{index:02d}.json"

    def _print_save_list(self, include_auto: bool) -> list[bool]:
        """SystemProc@printSaveDataText:807–859（1 ページ 20 件、SAVE_DATA_NOS = 20 なのでページ切替なし）。"""
        available = []
        for i in range(SAVE_DATA_NOS):
            comment = read_save_comment(self._save_path(i))
            self.out.printl(f"[{i:2d}] " + (comment if comment is not None else "----"))
            available.append(comment is not None)
        if include_auto:
            comment = read_save_comment(self._save_path(AUTOSAVE_INDEX))
            self.out.printl(f"[{AUTOSAVE_INDEX:2d}] " + (comment if comment is not None else "----"))
            available.append(comment is not None)
        self.out.printl("[100] 戻る")
        return available

    def begin_save_game(self) -> None:
        self.out.printl("何番にセーブしますか？")
        self._print_save_list(include_auto=False)
        self.phase = Phase.SAVE_SELECT

    def _save_select_input(self, value: int) -> None:
        """SystemProc@saveGameWaitInput:863–903。"""
        if value == 100:
            self._after_save()  # loadPrevState → @USERSHOP の続き → @SHOW_SHOP（SAVEGAME 命令なら命令の次）
            return
        if not 0 <= value < SAVE_DATA_NOS:
            self.out.clearline(1)
            self.out.printl("無効な値です")
            return
        self._save_target = value
        if read_save_comment(self._save_path(value)) is not None:
            self.out.printl("既にデータが存在します。上書きしますか？")
            self.out.print("[0] はい")
            self.out.print("[1] いいえ")
            self.out.printl()
            self.phase = Phase.SAVE_OVERWRITE
            return
        self._save_overwrite_input(0)

    def _save_overwrite_input(self, value: int) -> None:
        """SystemProc@saveGameWaitInputOverwrite:905–924、@endCallSaveInfo:926–934。"""
        assert self.state is not None
        if value == 1:
            self.begin_save_game()
            return
        if value != 0:
            self.out.clearline(1)
            self.out.printl("無効な値です")
            return
        now = self.now()
        text = now.strftime("%Y/%m/%d %H:%M:%S") + " " + shop.save_info(self.state, self.data, now)
        save_to_file(self._save_path(self._save_target), self.state, text, self.identity)
        self._after_save()

    def _after_save(self) -> None:
        ret, self._save_return = self._save_return, None
        if ret is not None:
            ret()
        else:
            self._show_shop()

    def begin_load_game(self) -> None:
        self.out.printl("何番をロードしますか？")
        self._print_save_list(include_auto=True)
        self.phase = Phase.LOAD_SELECT

    def _load_select_input(self, value: int) -> None:
        """SystemProc@loadGameWaitInput:936–990、@beginDataLoaded:757–780。"""
        if value == 100:
            if self._load_from_title:
                self.begin_title()
            else:
                self._show_shop()
            return
        if not (0 <= value < SAVE_DATA_NOS or value == AUTOSAVE_INDEX):
            self.out.clearline(1)
            self.out.printl("無効な値です")
            return
        path = self._save_path(value)
        if read_save_comment(path) is None:
            self.out.printl(str(value))
            self.out.printl("データがありません")
            self.begin_load_game()
            return
        try:
            state, _ = load_from_file(path, rng=self.rng, identity=self.identity)
        except SaveFormatError as exc:
            self.out.printl(str(exc))
            self.begin_load_game()
            return
        self.state = state
        self._event_load()

    def _event_load(self) -> None:
        """`ゲーム内_イベント発生/オープニング処理.ERB@EVENTLOAD`:4–15。"""
        assert self.state is not None
        try:
            # :7 CALL UPDATE（バージョン間互換処理.ERB:95–846）：LOADGLOBAL 成功時は GLOBAL を反映
            update(self.state, self.globals, self.out, self.identity.version)
        except NotImplementedError as exc:
            self._halt(exc)
            return
        # オープニング処理.ERB@EVENTLOAD:8–12。
        if self.state.flag[999] == 1:
            self.out.set_bgcolor((0,0,40))
        else:
            self.out.reset_bgcolor()
        if self.state.flag[64] > 0:  # :13–14 JUMP ENDING（S27：クリアデータ → $START_SUCCESSION → 引き継ぎ選單）
            from .ending import ending_gen

            self._run_gen(ending_gen(self._ctx()), self._after_turn)
            return
        # BEGIN なしで終了 → SystemProc@endEventLoad:775–780 → endAutoSave → @SHOW_SHOP（オートセーブなし）
        self._show_shop()
