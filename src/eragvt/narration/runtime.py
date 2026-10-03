"""執行器：對 `nodes` 的節點樹求值，輸出到 `TextOutput`，亂數一律用注入的 `GameRng`（依 ERB 的求值順序）。

引擎語意的依據（路徑相對 `reference/emuera-1824/Emuera/`）：
- 二項演算：`GameData/Expression/OperatorMethod.cs`（`&&`／`||` は短絡:524–555、`/`・`%` は右辺→左辺の順:298–330、
  C# の整数除算は 0 方向への切り捨て、剰余の符号は被除数）、三項:795–822。
- FORM：`GameData/StrForm.cs`（`%式,幅,LEFT%` は cp932 バイト幅で埋める:248–266、`{}`:233–246、`\\@`:268–274）。
- PRINT：`GameView/EmueraConsole.Print.cs@Print`:311–330（文字列中の `\\n` で改行）。
- PRINTDATA：`GameProc/Function/Instraction.Child.cs`:190–235（`RAND(件数)` で 1 件、DATALIST の行間は改行、
  L／W で最後に改行）。
- CALL／TRYCALL／TRYCCALL：同:2294–2320（見つからないとき TRY なら CATCH へ）、CATCH:2034–2038。
- RETURN：同:1997–2025（RESULT:0.. に代入）、関数末尾まで流れ落ちると RESULT = 0（`GameProc/Process.ScriptProc.cs`:61–67）。
- 関数引数：省略時は 0／""（`GameProc/ErbLoader.cs`:582–590）、LOCAL・#DIM は静的（`UserDefinedVariable.cs`:27）。
- FOR：`Instraction.Child.cs`:1731–1744、WHILE:1754–1760。
- GOTO：同名の `$ラベル` の次の行へ（`Instraction.Child.cs@GOTO_Instruction`:2366–2406、ラベル名は ToUpper：
  `GameProc/LogicalLineParser.cs`:305–320）。FOR／REPEAT 等はスタックを持たない線形ジャンプなので、関数本体トップレベルの
  ラベルへはどの入れ子からでも「本体をラベル位置から再開」で等価。S28c2：IF／SELECTCASE の中のラベルへも、ELSEIF／ELSE／CASE は
  ENDIF／ENDSELECT へ飛ぶだけ・ENDIF は何もしない（`Instraction.Child.cs@ELSEIF_Instruction`:1805–1821、`ENDIF_Instruction`:1822–1832、
  `FunctionIdentifier.cs`:231–237）ので「ラベル以降の残り → 外側の入れ子文の次 → …」で等価。S30：ループの中のラベルへも
  （実行中の FOR／REPEAT はそのループ自身が受けて同じ周回を続ける、WHILE／DO は状態なし：`Interp._exec_path`）。
- INPUTS：入力文字列を RESULTS:0 に（`GameProc/Process.cs@InputString`:257–260）。`Env.inputs` が None（通常の呼び出し）なら
  unsupported。ジェネレータ呼び出しでは、まだ無い入力に達したら `NeedInput` で中断し、入力を足して最初から再実行する
  （`service.CatalogNarrationService.run_function_gen`：出力・亂數・LOCAL は開始時に戻すので再実行結果は同一）。
- DRAWLINEFORM：`Process.ScriptProc.cs`:159–172（空文字列ならエラー：`EmueraConsole.Print.cs@printCustomBar`:526–531）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from . import nodes as N
from .expr import Binary, Call, Form, Lit, Ternary, Unary, Var
from .runtime_support import (
    CHARA_ATTR,
    CHARA_STR_ATTR,
    CLOTH_INDEX,
    GLOBAL_ARRAY_ATTR,
    NAME_TABLE_OF,
    NARRATION_DIRS,
    STATE_SAVEDATA_ATTR,
    STATE_WRITABLE,
    TEMP_ARRAY_ATTR,
    TEMP_SCALAR_ATTR,
    var_length,
)
from .symbols import CSV_NAME_TABLE


class ErbRuntimeError(Exception):
    """引擎會報錯停止的狀況（除以 0、範圍外等）。"""


class NotSupported(Exception):
    """執行中才發現的子集外（動態 CALLFORM 的呼叫先不可執行等）。"""


class NeedInput(Exception):
    """ジェネレータ呼び出しで、まだ与えられていない INPUTS に達した。"""


class _Goto(Exception):
    def __init__(self, name: str) -> None:
        self.name = name


class _Return(Exception):
    def __init__(self, value: Any = None) -> None:
        self.value = value


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


def cp932_len(s: str) -> int:
    """`LangManager.GetStrlenLang`（_Library/LangManager.cs:17–20）：Shift-JIS のバイト数。"""
    return len(s.encode("cp932", errors="replace"))


def _trunc_div(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _trunc_mod(a: int, b: int) -> int:
    return a - _trunc_div(a, b) * b


class StateJournal:
    """S29：catalog が GameState に書いた変更の記録（失敗時に完全に戻すため）。

    `begin()` で区間を開き（入れ子可）、`rollback(mark)` はその区間の書き込みを新しい順に元へ戻す。区間が 1 つも開いていない
    ときは記録しない（外側に戻す人がいない）。最外の区間が閉じたら記録を捨てる。Python 移植を呼ぶ hook（`HOOK_CALLS`）の
    状態変化は記録できないので `irreversible` を数え、区間内でそれが増えていたら戻せない（`can_rollback`）。"""

    def __init__(self) -> None:
        self.entries: list = []
        self.depth = 0
        self.irreversible = 0

    def begin(self) -> tuple[int, int]:
        self.depth += 1
        return (len(self.entries), self.irreversible)

    def _close(self) -> None:
        self.depth -= 1
        if self.depth <= 0:
            self.depth = 0
            self.entries.clear()

    def commit(self, mark: tuple[int, int]) -> None:
        self._close()

    def can_rollback(self, mark: tuple[int, int]) -> bool:
        return self.irreversible == mark[1]

    def rollback(self, mark: tuple[int, int]) -> None:
        start = mark[0]
        for kind, obj, key, old in reversed(self.entries[start:]):
            if kind == "item":
                obj[key] = old
            else:
                setattr(obj, key, old)
        del self.entries[start:]
        self._close()

    def touch_item(self, arr: Any, key: Any) -> None:
        """これから Python 側が書く要素の現在値を記録する（KOJO_ROOT の FLAG:62／FLAG:900 等）。"""
        if self.depth:
            self.entries.append(("item", arr, key, arr[key]))

    def set_item(self, arr: Any, key: Any, value: Any) -> None:
        if self.depth:
            self.entries.append(("item", arr, key, arr[key]))
        arr[key] = value

    def set_attr(self, obj: Any, name: str, value: Any) -> None:
        if self.depth:
            self.entries.append(("attr", obj, name, getattr(obj, name)))
        setattr(obj, name, value)


@dataclass
class Frame:
    fd: N.FuncDef
    name: str
    in_method: bool = False


@dataclass
class Env:
    """執行環境。py_functions: 名稱 → f(interp, args) → 回傳值；hooks: key → f(interp, frame, hook)。"""

    state: Any
    data: Any
    out: Any
    py_functions: dict = field(default_factory=dict)
    hooks: dict = field(default_factory=dict)
    ctx: Any = None  # action.Ctx（hook／KOJO_ROOT 用）
    inputs: Optional[list] = None  # INPUTS に与える入力（None = INPUTS 不可）
    input_fn: Optional[Callable] = None  # S28c2 run_event_gen：f(yield する値) → 入力値（中断して待つ）
    journal: Optional[StateJournal] = None  # S29：状態書き込みの記録（None なら記録しない新しいジャーナル）


class Interp:
    MAX_DEPTH = 200

    def __init__(self, catalog, env: Env) -> None:
        self.cat = catalog
        self.env = env
        self.st = env.state
        self.data = env.data
        self.out = env.out
        self.depth = 0
        self.hooks_fired = 0
        self.side_effects = 0  # py_functions による状態変化（KOJO_ROOT）の回数
        self.input_pos = 0
        self.gotos = 0  # GOTO の回数（無限ループ検出：MAX_GOTO）
        if env.journal is None:
            env.journal = StateJournal()
        self.journal = env.journal

    # --- 呼び出し ------------------------------------------------------------------
    def call(self, name: str, args: list, as_method: bool = False) -> Any:
        """ユーザー関数を呼ぶ。as_method: 式中関数として（RETURNF の値を返す）。"""
        up = name.upper()
        if up in self.env.py_functions:
            return self.env.py_functions[up](self, args)
        fd = self.cat.get(up)
        if fd is None:
            raise ErbRuntimeError(f"関数 {up} が見つかりません")
        reason = self.cat.unsupported_reason(up)
        if reason is not None:
            raise NotSupported(reason)
        if as_method and fd.kind == "proc":
            raise ErbRuntimeError(f"{up} は式中関数ではありません")
        if not as_method and fd.kind != "proc":
            # CALL で #FUNCTION を呼ぶのは引擎ではエラー（CALLF を使う）
            pass
        if len(args) > len(fd.params):
            raise ErbRuntimeError(f"@{up} の引数が多すぎます")
        self.depth += 1
        if self.depth > self.MAX_DEPTH:
            raise ErbRuntimeError("呼び出しが深すぎます")
        fr = Frame(fd, up, fd.kind != "proc")
        try:
            for i, (pv, default) in enumerate(fd.params):
                value = args[i] if i < len(args) and args[i] is not None else None
                if value is None:
                    is_str = self._is_str_var(fr, pv.name)
                    value = default if default is not None else ("" if is_str else 0)
                self._assign_var(fr, pv, value)
            try:
                self._exec_body(fd, fr)
            except _Return as r:
                return r.value
            # 末尾まで流れ落ちた
            if fd.kind == "proc":
                self._set_result([0])
                return 0
            return "" if fd.kind == "str" else 0
        except (_Break, _Continue) as e:
            raise ErbRuntimeError("ループ外の BREAK/CONTINUE") from e
        finally:
            self.depth -= 1

    MAX_GOTO = 100000

    def _exec_body(self, fd: N.FuncDef, fr: Frame) -> None:
        """関数本体。GOTO は $ラベルの次から再開する（実行中のループの中のラベルはそのループ自身が受ける：`_for` 等）。"""
        body = fd.body
        path: Optional[list] = None
        while True:
            try:
                if path is None:
                    self.exec_block(body, fr)
                else:
                    self._exec_path(path, fr)
                return
            except _Goto as g:
                path = self._goto_path(body, g.name)

    def _goto_path(self, stmts: list, name: str) -> list:
        path = N.label_path(stmts, name, loops=True)
        if path is None:
            raise NotSupported(f"GOTO 先 ${name} が見つからない") from None
        self.gotos += 1
        if self.gotos > self.MAX_GOTO:
            raise ErbRuntimeError("GOTO の繰り返しが多すぎます（無限ループ）") from None
        return path

    def _exec_path(self, path: list, fr: Frame) -> None:
        """GOTO 後の再開：path[0] の文リストの path[0] 位置の入れ子文に入り（最後はラベル自身）、内側を終えたら
        その文リストの残りを実行する。引擎はラベルの次の行から線形に進むだけ（`Process.ScriptProc.cs`:20–21 ShiftNextLine、
        `$ラベル`行は何もしない:73–74）なので：
        - IF／SELECTCASE：ELSEIF／ELSE／CASE／CASEELSE は ENDIF／ENDSELECT へ飛ぶだけ・ENDIF は何もしない
          （`Instraction.Child.cs@ELSEIF_Instruction`:1805–1821、`ENDIF_Instruction`:1822–1832、`FunctionIdentifier.cs`:231–237）
          → 枝の残りを終えたらその入れ子文は終わり。
        - WHILE：WEND は WHILE の条件を再評価して真なら WHILE の次へ（:2163–2176）→ 本体の残りの後は通常のループ継続。
        - DO：LOOP は条件が真なら DO の次へ（:2178–2192、DO は ENDIF_Instruction：`FunctionIdentifier.cs`:245）→ 同上。
        - FOR／REPEAT：実行中のもの（GOTO を含むもの）は `_for`／Repeat 自身が _Goto を受けて再開する。ここに来るのは
          実行中でないものだけ（前回の FOR の値で回る）→ unsupported（静的にも `unsupported_reasons_static` で弾く）。"""
        stmts, i = path[0]
        if len(path) > 1:
            s = stmts[i]
            rest = path[1:]
            t = type(s)
            if t is N.If or t is N.Select:
                self._exec_path(rest, fr)
            elif t is N.While:
                self._while(s, fr, rest)
            elif t is N.Loop:
                self._do(s, fr, rest)
            else:
                raise NotSupported(f"GOTO 先 ${self._label_name(path)} が実行中でない FOR／REPEAT の中")
        for s in stmts[i + 1:]:
            self.exec(s, fr)

    @staticmethod
    def _label_name(path: list) -> str:
        stmts, i = path[-1]
        return stmts[i].name

    # --- 文 --------------------------------------------------------------------------
    def exec_block(self, stmts: list, fr: Frame) -> None:
        for s in stmts:
            self.exec(s, fr)

    def exec(self, s: N.Stmt, fr: Frame) -> None:
        t = type(s)
        if t is N.Print:
            self._print(s, fr)
        elif t is N.If:
            for cond, body in s.branches:
                if self._int(cond, fr) != 0:
                    self.exec_block(body, fr)
                    return
            if s.orelse is not None:
                self.exec_block(s.orelse, fr)
        elif t is N.Select:
            self._select(s, fr)
        elif t is N.Sif:
            if self._int(s.cond, fr) != 0 and s.body is not None:
                self.exec(s.body, fr)
        elif t is N.PrintData:
            self._printdata(s, fr)
        elif t is N.StrData:
            self._strdata(s, fr)
        elif t is N.CallStmt:
            self._callstmt(s, fr)
        elif t is N.Style:
            self._style(s, fr)
        elif t is N.Assign:
            self._assign(s, fr)
        elif t is N.BitOp:
            v = self._int(s.target, fr)
            for b in s.bits:
                bit = self._int(b, fr)
                if bit < 0 or bit > 63:
                    raise ErbRuntimeError("ビット位置が範囲外")
                if s.mode == 1:
                    v |= 1 << bit
                elif s.mode == 0:
                    v &= ~(1 << bit)
                else:
                    v ^= 1 << bit
            self._assign_var(fr, s.target, v)
        elif t is N.StrLen:
            text = self._text(s.kind, s.arg, fr)
            self._set_result([len(text) if s.unicode else cp932_len(text)])
        elif t is N.Split:
            self._split(s, fr)
        elif t is N.Times:
            self._times(s, fr)
        elif t is N.VarSet:
            self._varset(s, fr)
        elif t is N.Return:
            vals = [self._int(v, fr) for v in s.values] or [0]
            if fr.in_method:
                raise _Return(None)
            self._set_result(vals)
            raise _Return(vals[0])
        elif t is N.ReturnF:
            if not fr.in_method:
                raise ErbRuntimeError("RETURNF は式中関数でのみ使えます")
            v = self.eval(s.value, fr) if s.value is not None else ("" if fr.fd.kind == "str" else 0)
            raise _Return(v)
        elif t is N.ClearLine:
            self.out.clearline(self._int(s.count, fr))
        elif t is N.DrawLine:
            if s.form is not None:
                bar = self.eval(s.form, fr)
                if not bar:
                    raise ErbRuntimeError("空文字列によるDRAWLINEが行われました")
            # DEVIATION（表示のみ）：DRAWLINEFORM の線の文字列（画面幅まで繰り返し：EmueraConsole.Print.cs@getStBar:543–560）は
            # 反映せず、DRAWLINE と同じ区切り線を出す（deviations.md「口上 catalog の表示」）
            self.out.drawline()
        elif t is N.Label:
            pass
        elif t is N.Goto:
            raise _Goto(s.name)
        elif t is N.Input:
            value = self._input()
            if s.kind == "I":
                # INPUT：整数 → RESULT:0（GameProc/Process.cs@InputInteger:249–252）
                self._set_result([int(value)])
            else:
                self.st.results[0] = str(value)  # RESULTS は共用（GameState.results、S22）
        elif t is N.Wait:
            self.out.wait()
        elif t is N.For:
            self._for(s, fr)
        elif t is N.While:
            self._while(s, fr)
        elif t is N.Loop:
            self._do(s, fr)
        elif t is N.Repeat:
            self._repeat(s, fr)
        elif t is N.Break:
            raise _Break()
        elif t is N.Continue:
            raise _Continue()
        elif t is N.MethodStmt:
            v = self._method(s.name, s.args, fr)
            if isinstance(v, str):
                self.st.results[0] = v  # Instraction.Child.cs@METHOD_Instruction:398–404
            else:
                self._set_result([v])
        elif t is N.Hook:
            self._hook(s, fr)
        elif t is N.Unsupported:
            raise NotSupported(s.reason)
        else:  # pragma: no cover
            raise NotSupported(f"文 {t.__name__}")

    def _input(self) -> Any:
        """入力 1 つ。`Env.input_fn`（S28c2 `run_event_gen`：本当に中断して待つ）か、`Env.inputs`（再実行方式）。"""
        if self.env.input_fn is not None:
            return self.env.input_fn(None)
        inputs = self.env.inputs
        if inputs is None:
            raise NotSupported("INPUT／INPUTS（ジェネレータ呼び出しのみ対応）")
        if self.input_pos >= len(inputs):
            raise NeedInput()
        v = inputs[self.input_pos]
        self.input_pos += 1
        return v

    def _hook(self, s: N.Hook, fr: Frame) -> None:
        """hooks.py の状態変化行：CALL は既存の Python 移植へ、代入は状態書き込みを許可して実行。"""
        import importlib
        import inspect

        from .hooks import HOOK_CALLS

        if self.env.ctx is None:
            raise NotSupported("hook の実行に ctx が必要")
        inner = s.args[0]
        self.hooks_fired += 1
        if isinstance(inner, N.CallStmt):
            mod, fn = HOOK_CALLS[inner.name]
            self.journal.irreversible += 1  # Python 移植の状態変化は記録できない（S29：失敗しても戻せない）
            args = [self.eval(a, fr) for a in inner.args if a is not None]
            r = getattr(importlib.import_module(mod), fn)(self.env.ctx, *args)
            if inspect.isgenerator(r):
                # S28c2：INPUT を yield する Python 移植（AFTER_PILL・CALC_GANGBANG）は `Env.input_fn` 経由で駆動する
                if self.env.input_fn is None:
                    raise NotSupported(f"hook {inner.name} は入力を待つ（run_event_gen のみ対応）")
                try:
                    y = next(r)
                    while True:
                        y = r.send(self.env.input_fn(y))
                except StopIteration:
                    pass
            return
        self._state_write = True
        try:
            self.exec(inner, fr)
        finally:
            self._state_write = False

    # --- ループ（S30：GOTO で本体の途中から再開できる） ---
    # 本体の実行中に _Goto が来て、ラベルがそのループの本体にあれば「本体のラベル位置から」同じ周回を続ける
    # （引擎は線形ジャンプ。NEXT／REND／WEND／LOOP に達すれば通常どおり：`_exec_path` の docstring）。
    # BREAK：FOR／REPEAT はカウンタを 1 歩進めてから抜ける（`Instraction.Child.cs@BREAK_Instruction`:2054–2077
    # 「eramakerではBREAK時にCOUNTが回る」、WHILE・DO は進めない）。CONTINUE：カウンタを進めて判定（:2079–2133）。
    def _loop_body(self, s, fr: Frame, pending: Optional[list]) -> Optional[str]:
        """本体を 1 周（pending があればその経路から）。戻り値 "break"／"goto"（self._pending に経路）／None。"""
        try:
            if pending is None:
                self.exec_block(s.body, fr)
            else:
                self._exec_path(pending, fr)
        except _Break:
            return "break"
        except _Continue:
            return None
        except _Goto as g:
            if N.label_path(s.body, g.name, loops=True) is None:
                raise
            self._pending = self._goto_path(s.body, g.name)
            return "goto"
        return None

    def _for(self, s: N.For, fr: Frame) -> None:
        # FOR：Instraction.Child.cs@REPEAT_Instruction:1731–1744（開始値代入→終値・步進を評価→判定）
        self._assign_var(fr, s.var, self._int(s.start, fr))
        end = self._int(s.end, fr)
        step = self._int(s.step, fr) if s.step is not None else 1
        pending = None
        while True:
            if pending is None:
                cur = self._int(s.var, fr)
                if not ((step > 0 and end > cur) or (step < 0 and end < cur)):
                    break
            r = self._loop_body(s, fr, pending)
            pending = None
            if r == "goto":
                pending = self._pending
                continue
            # NEXT（REND_Instruction:2135–2161）／BREAK／CONTINUE：カウンタ += 步進
            self._assign_var(fr, s.var, self._int(s.var, fr) + step)
            if r == "break":
                break

    def _repeat(self, s: N.Repeat, fr: Frame) -> None:
        # REPEAT：カウンタ COUNT:0、開始 0、步進 1（FOR と同じ REPEAT_Instruction）
        n = self._int(s.count, fr)
        self._set_narr("COUNT", 0, 0)
        pending = None
        while True:
            if pending is None and not self._get_narr("COUNT", 0, 0) < n:
                break
            r = self._loop_body(s, fr, pending)
            pending = None
            if r == "goto":
                pending = self._pending
                continue
            self._set_narr("COUNT", 0, self._get_narr("COUNT", 0, 0) + 1)
            if r == "break":
                break

    def _while(self, s: N.While, fr: Frame, pending: Optional[list] = None) -> None:
        # WHILE：条件が偽なら WEND の次へ（:1747–1761）、WEND は条件を再評価（:2163–2176）
        while True:
            if pending is None and self._int(s.cond, fr) == 0:
                break
            r = self._loop_body(s, fr, pending)
            pending = None
            if r == "goto":
                pending = self._pending
                continue
            if r == "break":
                break

    def _do(self, s: N.Loop, fr: Frame, pending: Optional[list] = None) -> None:
        # DO … LOOP 条件：DO は何もしない（FunctionIdentifier.cs:245）、LOOP は条件が真なら DO の次へ（:2178–2192）。
        # CONTINUE は LOOP の条件で判定（:2118–2129）
        while True:
            r = self._loop_body(s, fr, pending)
            pending = None
            if r == "goto":
                pending = self._pending
                continue
            if r == "break" or self._int(s.cond, fr) == 0:
                break

    def _select(self, s: N.Select, fr: Frame) -> None:
        v = self.eval(s.expr, fr)
        for conds, body in s.cases:
            for c in conds:
                if self._case_match(v, c, fr):
                    self.exec_block(body, fr)
                    return
        if s.orelse is not None:
            self.exec_block(s.orelse, fr)

    def _case_match(self, v: Any, c: N.CaseCond, fr: Frame) -> bool:
        if c.kind == "eq":
            return v == self.eval(c.a, fr)
        if c.kind == "to":
            a = self.eval(c.a, fr)
            b = self.eval(c.b, fr)
            return a <= v <= b
        return bool(self._binop(c.op, v, self.eval(c.a, fr)))

    # --- PRINT ---
    def _text(self, kind: str, arg: Any, fr: Frame) -> str:
        if kind == "raw":
            return arg
        v = self.eval(arg, fr)
        return v if isinstance(v, str) else str(v)

    def _emit(self, text: str) -> None:
        parts = text.split("\n")
        for i, p in enumerate(parts):
            if i > 0:
                self.out.printl("")  # NewLine（EmueraConsole.Print.cs:315–326）
            self.out.print(p)

    def _print(self, s: N.Print, fr: Frame) -> None:
        text = self._text(s.kind, s.arg, fr)
        saved = None
        if s.dflag:
            saved = self.out._color
            self.out._color = None
        try:
            if s.plain:
                self.out.print_plain(text)
            else:
                self._emit(text)
            if s.wait:
                self.out.printw("")
            elif s.newline:
                self.out.printl("")
        finally:
            if s.dflag:
                self.out._color = saved

    def _printdata(self, s: N.PrintData, fr: Frame) -> None:
        if not s.items:
            return
        choice = self.st.rng.rand(len(s.items))
        if s.var is not None:
            self._assign_var(fr, s.var, choice)
        saved = None
        if s.dflag:
            saved = self.out._color
            self.out._color = None
        try:
            item = s.items[choice]
            for i, (kind, a, _lno) in enumerate(item):
                self._emit(self._text(kind, a, fr))
                if i + 1 < len(item):
                    self.out.printl("")
            if s.wait:
                self.out.printw("")
            elif s.newline:
                self.out.printl("")
        finally:
            if s.dflag:
                self.out._color = saved

    def _strdata(self, s: N.StrData, fr: Frame) -> None:
        """S30：STRDATA（Process.ScriptProc.cs:730–760）。空なら何もしない、`GetNextRand(件数)` で 1 件選び、
        その行（DATALIST なら複数行を "\n" で連結）の文字列を変数に代入する。PRINTDATA と違い選択番号は返さない。"""
        if not s.items:
            return
        item = s.items[self.st.rng.rand(len(s.items))]
        text = "\n".join(self._text(kind, a, fr) for kind, a, _lno in item)
        self._assign_var(fr, s.var, text)

    def _style(self, s: N.Style, fr: Frame) -> None:
        w = s.what
        if w == "SETCOLOR":
            vals = [self._int(a, fr) for a in s.args]
            if len(vals) == 3:
                self.out.set_color(tuple(max(0, min(255, x)) for x in vals))
            elif len(vals) == 1:
                c = vals[0]
                self.out.set_color(((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF))
            else:
                raise ErbRuntimeError("SETCOLOR の引数")
        elif w == "RESETCOLOR":
            self.out.reset_color()
        elif w == "FONTBOLD":
            self.out.set_bold(True)
        elif w == "FONTREGULAR":
            self.out.set_bold(False)
        elif w == "FONTITALIC":
            self.out.set_italic(True)
        elif w == "SETFONT":
            if s.args and s.args[0] is not None:
                self.eval(s.args[0], fr)
            # DEVIATION（表示のみ）：フォント名は反映しない
        elif w == "ALIGNMENT":
            a = s.args[0]
            if a not in ("LEFT", "CENTER", "RIGHT"):
                raise ErbRuntimeError("ALIGNMENT の引数")
            self.out.set_align(a.lower())

    def _callstmt(self, s: N.CallStmt, fr: Frame) -> None:
        name = s.name if isinstance(s.name, str) else str(self.eval(s.name, fr)).upper()
        args = [self.eval(a, fr) if a is not None else None for a in s.args]
        exists = name in self.env.py_functions or self.cat.exists(name)
        if not exists:
            if not s.try_:
                raise ErbRuntimeError(f"関数 @{name} が見つかりません")
            if s.catch is not None:
                self.exec_block(s.catch, fr)
            return
        if s.callf:
            self.call(name, args, as_method=True)
        else:
            self.call(name, args)
        if s.success:
            self.exec_block(s.success, fr)

    def _varset(self, s: N.VarSet, fr: Frame) -> None:
        tgt = s.target
        is_str = self._is_str_var(fr, tgt.name)
        value = self.eval(s.value, fr) if s.value is not None else ("" if is_str else 0)
        if s.start is None and s.end is None and not tgt.args:
            default = "" if is_str else 0
            if value != default:
                raise NotSupported("VARSET の配列全体への非既定値代入")
            if tgt.name == "LOCAL":
                for k in [k for k in self.st.temp.locals if k[0] == fr.name]:
                    del self.st.temp.locals[k]
                return
            d = self._narr()
            if tgt.name in ("ARG", "LOCALS", "ARGS") or tgt.name in fr.fd.private:
                key0 = (fr.name, tgt.name)
            elif tgt.name == "RESULT":
                self.st.result.clear()  # 共用 RESULT（GameState.result）全體を 0 に
                return
            elif tgt.name == "RESULTS":
                self.st.results.clear()  # 共用 RESULTS（GameState.results、S22）全體を "" に
                return
            elif tgt.name == "COUNT" or getattr(self.cat.user_vars.get(tgt.name), "narration_owned", False):
                key0 = tgt.name
            else:
                raise NotSupported(f"{tgt.name} への VARSET")
            for k in [k for k in d if k[0] == key0]:
                del d[k]
            return
        if tgt.args:
            raise NotSupported("添字付き VARSET")
        start = self._int(s.start, fr) if s.start is not None else 0
        if s.end is None:
            raise NotSupported("終了位置なしの VARSET")
        end = self._int(s.end, fr)
        for i in range(start, end):
            self._assign_var(fr, Var(tgt.name, [Lit(i)]), value)

    # --- 代入 ---
    def _assign(self, s: N.Assign, fr: Frame) -> None:
        op = s.op
        tgt = s.target
        if op in ("++", "--"):
            self._assign_var(fr, tgt, self._int(tgt, fr) + (1 if op == "++" else -1))
            return
        if op == "=" and len(s.values) > 1:
            # 配列への一括代入：最後の添字から連続して（SpSetArrayArgument）
            base_args = list(tgt.args)
            if not base_args:
                raise NotSupported("添字なしの配列一括代入")
            start = self._int(base_args[-1], fr)
            for k, v in enumerate(s.values):
                val = self.eval(v, fr)
                self._assign_var(fr, Var(tgt.name, base_args[:-1] + [Lit(start + k)]), val)
            return
        val = self.eval(s.values[0], fr)
        if op in ("=", "'="):
            self._assign_var(fr, tgt, val)
            return
        cur = self.eval(tgt, fr)
        self._assign_var(fr, tgt, self._binop(op[:-1], cur, val))

    # --- 式 --------------------------------------------------------------------------
    def _int(self, e, fr: Frame) -> int:
        v = self.eval(e, fr)
        if not isinstance(v, int):
            raise ErbRuntimeError("整数が必要です")
        return v

    def eval(self, e, fr: Frame) -> Any:
        t = type(e)
        if t is Lit:
            return e.value
        if t is Var:
            return self._get_var(fr, e)
        if t is Binary:
            op = e.op
            if op == "&&":
                return 1 if (self._int(e.left, fr) != 0 and self._int(e.right, fr) != 0) else 0
            if op == "||":
                return 1 if (self._int(e.left, fr) != 0 or self._int(e.right, fr) != 0) else 0
            if op in ("/", "%"):
                r = self.eval(e.right, fr)
                lv = self.eval(e.left, fr)
                return self._binop(op, lv, r)
            lv = self.eval(e.left, fr)
            r = self.eval(e.right, fr)
            return self._binop(op, lv, r)
        if t is Unary:
            v = self._int(e.x, fr)
            return {"-": -v, "+": v, "~": ~v, "!": 1 if v == 0 else 0}[e.op]
        if t is Ternary:
            return self.eval(e.yes, fr) if self._int(e.cond, fr) != 0 else self.eval(e.no, fr)
        if t is Form:
            return self._form(e, fr)
        if t is Call:
            return self._method(e.name, e.args, fr)
        raise NotSupported(f"式 {t.__name__}")  # pragma: no cover

    def _binop(self, op: str, a: Any, b: Any) -> Any:
        if op == "+":
            if type(a) is not type(b):
                raise ErbRuntimeError("型が一致しません")
            return a + b
        if op == "*":
            if isinstance(a, str):
                return a * max(0, b)
            return a * b
        if op in ("==", "!=", "<", ">", "<=", ">="):
            r = {"==": a == b, "!=": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
            return 1 if r else 0
        if not isinstance(a, int) or not isinstance(b, int):
            raise ErbRuntimeError("整数演算に文字列")
        if op == "-":
            return a - b
        if op == "/":
            if b == 0:
                raise ErbRuntimeError("0による除算")
            return _trunc_div(a, b)
        if op == "%":
            if b == 0:
                raise ErbRuntimeError("0による除算")
            return _trunc_mod(a, b)
        if op == "&":
            return a & b
        if op == "|":
            return a | b
        if op == "^":
            return a ^ b
        if op == "<<":
            return a << b
        if op == ">>":
            return a >> b
        if op == "^^":
            return 1 if ((a != 0) != (b != 0)) else 0
        if op == "!&":
            return 0 if (a != 0 and b != 0) else 1
        if op == "!|":
            return 0 if (a != 0 or b != 0) else 1
        raise ErbRuntimeError(f"演算子 {op}")

    def _form(self, f: Form, fr: Frame) -> str:
        out = [f.strs[0]]
        for i, p in enumerate(f.parts):
            if p.kind == "@":
                out.append(self._form(p.yes, fr) if self._int(p.expr, fr) != 0 else self._form(p.no, fr))
            elif p.kind == "{":
                s = str(self._int(p.expr, fr))
                if p.width is not None:
                    w = self._int(p.width, fr)
                    s = s.ljust(w) if p.left else s.rjust(w)
                out.append(s)
            else:
                v = self.eval(p.expr, fr)
                s = v if isinstance(v, str) else str(v)
                if p.width is not None:
                    total = self._int(p.width, fr)
                    total -= cp932_len(s) - len(s)
                    if total >= len(s):
                        s = s.ljust(total) if p.left else s.rjust(total)
                out.append(s)
            out.append(f.strs[i + 1])
        return "".join(out)

    # --- 式中関数 ---
    def _method(self, name: str, arg_exprs: list, fr: Frame) -> Any:
        from .builtins import BUILTINS

        if name in BUILTINS:
            return BUILTINS[name](self, arg_exprs, fr)
        args = [self.eval(a, fr) if a is not None else None for a in arg_exprs]
        return self.call(name, args, as_method=True)

    # --- 変数 --------------------------------------------------------------------------
    def _is_str_var(self, fr: Frame, name: str) -> bool:
        if name in fr.fd.private:
            return fr.fd.private[name]
        from .symbols import BUILTIN_STR

        if name in BUILTIN_STR:
            return True
        uv = self.cat.user_vars.get(name)
        return bool(uv and uv.is_str)

    def _idx(self, v: Any, var: str) -> int:
        if isinstance(v, str):
            table = CSV_NAME_TABLE.get(var)
            if table is None:
                raise ErbRuntimeError(f"{var} の添字に文字列")
            try:
                return self.data.index_of(table, v)
            except KeyError as e:
                raise ErbRuntimeError(str(e)) from e
        return v

    def _results_idx(self, i: Any) -> int:
        """RESULTS の添字（大きさ 100：ConstantData.cs:154–155。範囲外は引擎エラー）。"""
        if not isinstance(i, int) or not 0 <= i < self.st.RESULTS_SIZE:
            raise ErbRuntimeError(f"RESULTS の添字 {i!r} が範囲外")
        return i

    def _chara(self, i: int):
        if not isinstance(i, int) or i < 0 or i >= self.st.charanum:
            raise ErbRuntimeError(f"キャラ番号 {i} が範囲外")
        return self.st.charas[i]

    def _narr(self) -> dict:
        d = getattr(self.st.temp, "narr", None)
        if d is None:
            d = {}
            self.st.temp.narr = d
        return d

    def _get_narr(self, name: str, key: Any, default: Any) -> Any:
        return self._narr().get((name, key), default)

    def _set_narr(self, name: str, key: Any, value: Any) -> None:
        self._narr()[(name, key)] = value

    def _split(self, s: N.Split, fr: Frame) -> None:
        """SPLIT（Process.ScriptProc.cs:522–538）：`target.Split(new string[]{区切り}, StringSplitOptions.None)`、
        個数変数（省略時 RESULT:0、ArgumentBuilder.cs:1509）に分割数、配列長を超えた分は切り捨てて先頭から代入。"""
        src = self.eval(s.src, fr)
        sep = self.eval(s.sep, fr)
        if not isinstance(src, str) or not isinstance(sep, str):
            raise ErbRuntimeError("SPLIT の引数の型")
        if sep == "":
            raise NotSupported("SPLIT の区切りが空文字列（.NET は空白区切り扱い）")
        if s.target.args:
            raise NotSupported("SPLIT の配列に添字")
        name = s.target.name
        if name in fr.fd.sizes:
            size = fr.fd.sizes[name]
        elif name in ("LOCALS", "ARGS"):
            size = 100  # 既定の要素数（GameData/ConstantData.cs:153–154、VariableData.cs:332–335）
        else:
            size = None
        if size is None:
            raise NotSupported(f"SPLIT 先 {name} の要素数が不明")
        parts = src.split(sep)
        if s.num is None:
            self.st.result[0] = len(parts)
        else:
            self._assign_var(fr, s.num, len(parts))
        for i, p in enumerate(parts[:size]):
            self._assign_var(fr, Var(name, [Lit(i)]), p)

    def _times(self, s: "N.Times", fr: Frame) -> None:
        """TIMES（config「TIMESの計算をeramakerにあわせる:NO」：`source/earGVP/emuera.config`:65）：
        `decimal d = 値 * (decimal)実数` を Int64 へ切り捨て（`Instraction.Child.cs@TIMES_Instruction`:905–916）。
        実数は `LexicalAnalyzer.ReadDouble` で double になってから `(decimal)` 変換される。"""
        from decimal import Decimal

        # UNVERIFIED: .NET の double→decimal 変換（有効数字 15 桁に丸める）は reference に無い .NET 実行時の仕様。
        # 15 桁以下のリテラルなら原文の Decimal と同じ値になる前提（`game.era.times` と同じ）。本作の口上は 0.5／0.20 のみ。

        if len(s.factor.replace(".", "").lstrip("0")) > 15:
            raise NotSupported("TIMES の実数が有効数字 15 桁を超える")
        d = Decimal(self._int(s.target, fr)) * Decimal(s.factor)
        if not (-(2**63) <= d <= 2**63 - 1):
            raise NotSupported("TIMES の結果が Int64 の範囲外（引擎は double 経由で丸める）")
        self._assign_var(fr, s.target, int(d))

    def _set_result(self, vals: list) -> None:
        """RESULT:0〜 に代入（多値 RETURN 等）。RESULT は Python 移植部分と共用の `GameState.result`（S21）。"""
        self.st.set_result_x(*vals)

    def _get_result(self, i: int = 0) -> int:
        return self.st.result[i]

    def _args(self, fr: Frame, v: Var) -> list:
        return [self.eval(a, fr) for a in v.args]

    def _get_var(self, fr: Frame, v: Var) -> Any:
        name = v.name
        fd = fr.fd
        if name in fd.consts:
            args = self._args(fr, v)
            i = args[0] if args else 0
            return fd.consts[name][i]
        if name == "LOCAL" or name in ("ARG", "LOCALS", "ARGS") or name in fd.private:
            return self._private_get(fr, v)
        if name == "RAND":
            args = self._args(fr, v)
            n = args[0] if args else 0
            if n <= 0:
                raise ErbRuntimeError("RAND の引数が 0 以下")
            return self.st.rng.rand(n)
        args = self._args(fr, v)
        st = self.st
        if name in CHARA_ATTR:
            if len(args) == 0:
                c, i = st.target, 0
            elif len(args) == 1:
                c, i = st.target, args[0]
            else:
                c, i = args[0], args[1]
            return getattr(self._chara(c), CHARA_ATTR[name])[self._idx(i, name)]
        if name in CHARA_STR_ATTR:
            c = args[0] if args else st.target
            return getattr(self._chara(c), CHARA_STR_ATTR[name])
        if name == "CSTR":
            if len(args) <= 1:
                c, i = st.target, (args[0] if args else 0)
            else:
                c, i = args[0], args[1]
            return self._chara(c).cstr[i]
        if name == "NO":
            return self._chara(args[0] if args else st.target).no
        if name == "CDFLAG":
            if len(args) != 3:
                raise NotSupported("CDFLAG の引数は 3 つ")
            return self._chara(args[0]).cdflag[self._cdflag_key(args)]
        if name == "TCVAR":
            # 常に 0（runtime_support.READ_ONLY_SPECIAL の注記）。添字の検査だけ行う
            c, i = (st.target, args[0] if args else 0) if len(args) <= 1 else (args[0], args[1])
            self._chara(c)
            self._check_index("TCVAR", [i])
            return 0
        if name in GLOBAL_ARRAY_ATTR:
            return getattr(st, GLOBAL_ARRAY_ATTR[name])[self._idx(args[0], name) if args else 0]
        if name in ("TIME", "MONEY", "TARGET", "ASSI", "MASTER"):
            if args and args[0] != 0:
                raise NotSupported(f"{name}:{args[0]}")
            return {"TIME": st.time, "MONEY": st.money, "TARGET": st.target, "ASSI": st.assi, "MASTER": 0}[name]
        if name in ("SELECTCOM", "PREVCOM", "NEXTCOM"):
            return getattr(st.temp, name.lower())
        if name == "CHARANUM":
            return st.charanum
        if name == "LINECOUNT":
            return self.out.linecount
        if name == "RESULT":
            return self.st.result[self._idx(args[0], name) if args else 0]
        if name == "COUNT":
            return self._get_narr(name, args[0] if args else 0, 0)
        if name == "RESULTS":
            return self.st.results[self._results_idx(args[0] if args else 0)]
        if name in TEMP_ARRAY_ATTR:
            arr = getattr(st.temp, TEMP_ARRAY_ATTR[name])
            if len(args) >= 2:
                return arr[(args[0], args[1])]
            return arr[self._idx(args[0], name) if args else 0]
        if name in TEMP_SCALAR_ATTR:
            return getattr(st.temp, TEMP_SCALAR_ATTR[name])
        if name in CLOTH_INDEX:
            return st.temp.cloth[CLOTH_INDEX[name]]
        if name == "特殊戦闘シチュエーション":
            return st.temp.battle_situation
        if name in STATE_SAVEDATA_ATTR:
            arr = getattr(st, STATE_SAVEDATA_ATTR[name])
            return arr[(args[0], args[1])] if len(args) >= 2 else arr[args[0] if args else 0]
        if name == "SAVESTR":
            return st.savestr[args[0] if args else 0]
        if name == "STR":
            return self.data.str_defaults.get(args[0] if args else 0, "")
        if name in NAME_TABLE_OF:
            return self.data.names.get(NAME_TABLE_OF[name], {}).get(args[0] if args else 0, "")
        if name.endswith("NAME"):
            return ""  # 対応する CSV が本作に無い（flag.csv 等）→ 名前は空
        uv = self.cat.user_vars.get(name)
        if uv is not None:
            if uv.const:
                i = args[0] if args else 0
                if len(uv.dims) > 1 and len(args) > 1:
                    raise NotSupported("多次元 CONST")
                return uv.values[i]
            if getattr(uv, "narration_owned", False):
                key = tuple(args) if args else (0,)
                return self._get_narr(name, key, "" if uv.is_str else 0)
        raise NotSupported(f"変数 {name}")

    def _private_key(self, fr: Frame, v: Var) -> tuple:
        args = self._args(fr, v)
        return tuple(args) if args else (0,)

    def _private_get(self, fr: Frame, v: Var) -> Any:
        name = v.name
        key = self._private_key(fr, v)
        if name == "LOCAL":
            return self.st.temp.locals.get((fr.name, key[0]), 0)
        default = "" if self._is_str_var(fr, name) else 0
        return self._get_narr((fr.name, name), key, default)

    def _assign_var(self, fr: Frame, v: Var, value: Any) -> None:
        name = v.name
        is_str = self._is_str_var(fr, name)
        if is_str != isinstance(value, str):
            raise ErbRuntimeError(f"{name} への型の異なる代入")
        if name == "LOCAL":
            key = self._private_key(fr, v)
            if value == 0:
                self.st.temp.locals.pop((fr.name, key[0]), None)
            else:
                self.st.temp.locals[(fr.name, key[0])] = value
            return
        if name in ("ARG", "LOCALS", "ARGS") or name in fr.fd.private:
            if name in fr.fd.consts:
                raise ErbRuntimeError("CONST への代入")
            self._set_narr((fr.name, name), self._private_key(fr, v), value)
            return
        if name == "RESULT":
            args = self._args(fr, v)
            self.st.result[self._idx(args[0], name) if args else 0] = value
            return
        if name == "RESULTS":
            args = self._args(fr, v)
            self.st.results[self._results_idx(args[0] if args else 0)] = value
            return
        if name == "COUNT":
            args = self._args(fr, v)
            self._set_narr(name, args[0] if args else 0, value)
            return
        uv = self.cat.user_vars.get(name)
        if uv is not None and getattr(uv, "narration_owned", False):
            args = self._args(fr, v)
            self._set_narr(name, tuple(args) if args else (0,), value)
            return
        if getattr(self, "_state_write", False) or (fr.fd.file.startswith(NARRATION_DIRS) and name in STATE_WRITABLE):
            self._state_set(v, value, fr)
            return
        raise NotSupported(f"{name} への代入")

    def _check_index(self, name: str, idx: list) -> None:
        """範囲外の添字は引擎エラー（キャラ変数：`GameData/Variable/VariableToken.cs@CharaVariableToken.CheckElement`:275–283、
        一般の配列も同様に CodeEE）。要素数は `runtime_support.var_length`。"""
        sizes = var_length(name, self.data, self.cat)
        for k, i in enumerate(idx):
            if k < len(sizes) and (not isinstance(i, int) or not 0 <= i < sizes[k]):
                raise ErbRuntimeError(f"配列変数 {name} の第{k + 1}添字 {i!r} は範囲外")

    def _cdflag_key(self, args: list) -> tuple:
        """CDFLAG:キャラ:a:b。文字列の添字は a が CDFLAG1、b が CDFLAG2 の名前（`GameData/ConstantData.cs`:826–844）。"""
        a, b = args[1], args[2]
        try:
            if isinstance(a, str):
                a = self.data.index_of("CDFLAG1", a)
            if isinstance(b, str):
                b = self.data.index_of("CDFLAG2", b)
        except KeyError as e:
            raise ErbRuntimeError(str(e)) from e
        self._check_index("CDFLAG", [a, b])
        return (a, b)

    def _state_set(self, v: Var, value: Any, fr: Frame) -> None:
        """GameState への書き込み（S29：口上／地の文の函式内の代入すべて、および hook 行）。

        キャラ変数の添字を 1 つ省略すると TARGET（`GameData/Variable/VariableParser.cs`:104–135）。書き込みは単なる配列要素への
        代入で、BASE と MAXBASE の連動などはない（`VariableToken.cs@CharaInt1DVariableToken.SetValue`:1066–1070、
        `CharaStrVariableToken.SetValue`:1121–1125、`CharaStr1DVariableToken.SetValue`:1150–1154、
        `CharaInt2DVariableToken.SetValue`:1196–1200）。変更は `StateJournal` に記録し、失敗時に戻す。"""
        st = self.st
        name = v.name
        args = self._args(fr, v)
        j = self.journal
        if name in GLOBAL_ARRAY_ATTR:
            if len(args) > 1:
                raise ErbRuntimeError(f"{name} の引数が多すぎます")
            i = self._idx(args[0], name) if args else 0
            self._check_index(name, [i])
            j.set_item(getattr(st, GLOBAL_ARRAY_ATTR[name]), i, value)
        elif name in CHARA_ATTR:
            if len(args) > 2:
                raise ErbRuntimeError(f"キャラクタ変数 {name} の引数が多すぎます")
            c, i = (st.target, args[0] if args else 0) if len(args) <= 1 else (args[0], args[1])
            ch = self._chara(c)
            i = self._idx(i, name)
            self._check_index(name, [i])
            j.set_item(getattr(ch, CHARA_ATTR[name]), i, value)
        elif name in CHARA_STR_ATTR:
            if len(args) > 1:
                raise ErbRuntimeError(f"キャラクタ変数 {name} の引数が多すぎます")
            j.set_attr(self._chara(args[0] if args else st.target), CHARA_STR_ATTR[name], value)
        elif name == "CSTR":
            if len(args) > 2:
                raise ErbRuntimeError("キャラクタ変数 CSTR の引数が多すぎます")
            c, i = (st.target, args[0] if args else 0) if len(args) <= 1 else (args[0], args[1])
            ch = self._chara(c)
            self._check_index(name, [i])
            j.set_item(ch.cstr, i, value)
        elif name == "CDFLAG":
            if len(args) != 3:
                raise ErbRuntimeError("キャラクタ二次元配列変数 CDFLAG の引数は省略できません")
            ch = self._chara(args[0])
            j.set_item(ch.cdflag, self._cdflag_key(args), value)
        elif name == "TENTACLE_SIZE" and len(args) == 2:
            self._check_index(name, args)
            j.set_item(st.temp.tentacle_size, (args[0], args[1]), value)
        elif name == "TARGET" and not args:  # S28b：`MESSAGE_CITIZEN_TRAIN.ERB`:191／:419 `TARGET=ARG`
            j.set_attr(st, "target", value)
        else:
            raise NotSupported(f"{name} への代入")


Hook = Callable[[Interp, Frame, N.Hook], None]
