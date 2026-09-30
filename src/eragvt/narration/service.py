"""catalog 版 `NarrationService`：口上派發（`KOJO_ROOT`）與地の文函式的執行。

- `call_kojo`：`口上/口上システム関係/KOJO_ROOT.ERB@KOJO_ROOT`:46–90（気絶・結界の判定 :16–43 は
  `eragvt.game.action.kojo_root_full` 側）。汎用口上（C_NO = キャラ口上_女性汎用 0／オトコ汎用 1：
  `CSV定数定義/CFLAG.ERH`:79–80）は `KOJO_{C_NO}_%CODE%_{SEIKAKU_CHECK_F(TARGET)}`、`OTHER_` を含む code は
  FLAG:62 = 1 で `SEIKAKU_CHECK_F(FLAG:111)`。見つからなければ RESETCOLOR・FLAG:900 = 0・RETURN -1。
  見つかれば実行後 RESETCOLOR・FLAG:900 = 0、RESULT == 999 ならそのまま、それ以外は出力行数。
- `run_function`：地の文など任意の ERB 函式を実行（可執行なら True）。INPUTS を含む（呼び出し先も含む）函式は False。
- `run_function_gen`（S14）：同上のジェネレータ版。INPUTS に達したら `yield` で入力を受け取り、出力・亂數・LOCAL を開始時に
  戻して入力列を足して最初から再実行する（同じ入力列なら同じ結果になる：亂數は注入 RNG のスナップショットで戻す）。
  入力待ちより前に状態変化（hook・KOJO_ROOT）があった場合は再実行できないので NotImplementedError。
- `CALL WINDOW_*`（汎用関数/WindowDrawer.ERB）は `narration.windowlib` の Python 移植を呼ぶ（実行ごとに新しいウィンドウ管理）。
- 實行時才發現不可執行（動態呼叫先が unsupported、引擎會報錯的狀況）→ 輸出・亂數・LOCAL を開始前に戻し、
  口上は「見つからない」（-1）、地の文は False（呼び出し側が佔位を出す）。
  DEVIATION: 引擎では実行時エラーで停止する箇所も「見つからない」扱いになる（deviations.md「口上 catalog」）。
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable, Optional

from .catalog import Catalog
from .runtime import Env, ErbRuntimeError, Interp, NeedInput, NotSupported
from .windowlib import WindowManager
from .windowlib import py_functions as window_py_functions


class _Tx:
    """輸出・亂數・LOCAL 的快照（失敗時回復）。"""

    def __init__(self, ctx) -> None:
        out = ctx.out
        st = ctx.state
        d = dict(out.__dict__)
        d["_lines"] = list(out._lines)
        if d["_lines"]:
            d["_lines"][-1] = copy.copy(d["_lines"][-1])
            d["_lines"][-1].parts = list(d["_lines"][-1].parts)
        d["_parts"] = list(out._parts)
        d["_pending"] = list(out._pending)
        self.out_state = d
        self.rng = st.rng.snapshot()
        self.locals = dict(st.temp.locals)
        self.narr = dict(st.temp.narr)
        self.ctx = ctx

    def rollback(self) -> None:
        out = self.ctx.out
        out.__dict__.clear()
        out.__dict__.update(self.out_state)
        st = self.ctx.state
        st.rng.restore(self.rng)
        st.temp.locals = self.locals
        st.temp.narr = self.narr


class CatalogNarrationService:
    """`source/earGVP/ERB` から lazily 抽取した catalog で口上・地の文を実行する。"""

    def __init__(self, erb_dir: Path, data) -> None:
        self.catalog = Catalog(erb_dir, data.names)
        self.data = data
        self.failures: list[str] = []  # 実行時に不可執行と判明したもの（診断用）

    @classmethod
    def from_csv_dir(cls, csv_dir: Path, data) -> Optional["CatalogNarrationService"]:
        erb = csv_dir.parent / "ERB"
        return cls(erb, data) if erb.is_dir() else None

    # --- 共通 ---
    def _interp(self, ctx, hooks: Optional[dict] = None, inputs: Optional[list] = None) -> Interp:
        from ..game.action import kojo_root_full

        def py_kojo_root(it: Interp, args: list) -> int:
            c_no = args[0] if args and args[0] is not None else 0
            code = args[1] if len(args) > 1 and args[1] is not None else ""
            force = args[2] if len(args) > 2 and args[2] is not None else 0
            it.side_effects += 1  # FLAG:62／FLAG:900 を書く
            r = kojo_root_full(ctx, c_no, code, force)
            it._set_result([r])
            return r

        py = {"KOJO_ROOT": py_kojo_root}
        py.update(window_py_functions(WindowManager(), ctx.out))
        env = Env(ctx.state, ctx.data, ctx.out, py, hooks or {}, ctx, inputs)
        return Interp(self.catalog, env)

    def _run(self, ctx, fn: Callable[[Interp], Any], what: str, hooks: Optional[dict] = None):
        tx = _Tx(ctx)
        it = self._interp(ctx, hooks)
        try:
            return True, fn(it)
        except (NotSupported, ErbRuntimeError) as e:
            if it.hooks_fired:
                # 状態変化（hook）の後に失敗したものは戻せない
                raise NotImplementedError(f"{what}：状態変化の後で実行できなくなりました（{e}）") from e
            tx.rollback()
            self.failures.append(f"{what}: {e}")
            return False, None

    def can_run(self, name: str) -> bool:
        return self.catalog.unsupported_reason(name) is None

    # --- KOJO_ROOT:46–90 ---
    def call_kojo(self, ctx, c_no: int, code: str) -> int:
        from ..game.chara_common import seikaku_check

        st = ctx.state
        out = ctx.out
        before = out.linecount
        other = "OTHER_" in code
        cat = self.catalog
        if c_no in (0, 1):
            who = st.charas[st.flag[111]] if other else st.target_chara
            seikaku = seikaku_check(ctx.data, who)
            color = f"KOJO_{c_no}_OTHER_COLOR_{seikaku}" if other else f"KOJO_{c_no}_COLOR_{seikaku}"
            st.flag[62] = 1 if other else 0
            name = f"KOJO_{c_no}_{code}_{seikaku}"
            ok = self._try_color(ctx, color)
        else:
            color = f"KOJO_{c_no}_OTHER_COLOR" if other else f"KOJO_{c_no}_COLOR"
            ok = self._try_color(ctx, color)
            st.flag[62] = 1 if other else 0
            name = f"KOJO_{c_no}_{code}"
        if not ok or not cat.exists(name):
            out.reset_color()
            st.flag[900] = 0
            return -1
        done, result = self._run(ctx, lambda it: (it.call(name, []), it._get_narr("RESULT", 0, 0))[1], name)
        if not done:
            out.reset_color()
            st.flag[900] = 0
            return -1
        out.reset_color()
        st.flag[900] = 0
        if result == 999:
            return 999
        return out.linecount - before

    def _try_color(self, ctx, name: str) -> bool:
        """TRYCALLFORM（見つからなければ何もしない）。不可執行なら False（口上ごと見つからない扱い）。"""
        if not self.catalog.exists(name):
            return True
        done, _ = self._run(ctx, lambda it: it.call(name, []), name)
        return done

    # --- 地の文 ---
    def run_function(self, ctx, name: str, args: Optional[list] = None, hooks: Optional[dict] = None) -> bool:
        if not self.catalog.exists(name):
            return False
        if self.catalog.unsupported_reason(name) is not None:
            return False
        if self.catalog.needs_input(name):
            return False
        done, _ = self._run(ctx, lambda it: it.call(name, list(args or [])), name, hooks)
        return done

    def run_function_gen(self, ctx, name: str, args: Optional[list] = None, hooks: Optional[dict] = None):
        """ジェネレータ版（`ok = yield from service.run_function_gen(...)`）。入力は `str(送られた値)`。
        DEVIATION: Web の入力は整数のみ（deviations.md「INPUTS 只能輸入整數」）。"""
        if not self.catalog.exists(name) or self.catalog.unsupported_reason(name) is not None:
            return False
        inputs: list[str] = []
        while True:
            tx = _Tx(ctx)
            it = self._interp(ctx, hooks, inputs)
            try:
                it.call(name, list(args or []))
                return True
            except NeedInput:
                if it.hooks_fired or it.side_effects:
                    raise NotImplementedError(f"{name}：入力待ちより前に状態変化があるため再実行できません") from None
                value = yield
                tx.rollback()
                inputs.append(str(value))
            except (NotSupported, ErbRuntimeError) as e:
                if it.hooks_fired:  # `_run` と同じ扱い
                    raise NotImplementedError(f"{name}：状態変化の後で実行できなくなりました（{e}）") from e
                tx.rollback()
                self.failures.append(f"{name}: {e}")
                return False
