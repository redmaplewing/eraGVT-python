"""catalog：`source/earGVP/ERB` 全體的函式索引＋依需要（lazy）抽取節點樹。

- 檔案順序照 `reference/emuera-1824/Emuera/Config/Config.cs@getFiles`:345–379（子資料夾先、依名稱不分大小寫排序，
  emuera.config「読み込み順をファイル名順にソートする:YES」「サブディレクトリを検索する:YES」）；拡張子が `.ERB` のみ
  （`.ERB.org` は含まない）。
- 同名函式以先定義者為準（`GameProc/LabelDictionary.cs@SortLabels`:58–77、`LogicalLine.cs@CompareTo`:274–282）。
- 函式名不分大小寫（ラベルは ToUpper：`LogicalLineParser.cs`:307–308、呼び出しも ToUpper：`Instraction.Child.cs`:2310）。
- 產生物不落地：啟動時只建索引（label 與 `#FUNCTION` 旗標），函式本體第一次用到時才解析並快取在記憶體。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import nodes as N
from .extract import ExtractContext, parse_function, read_logical_lines, scan_labels
from .hooks import match_hook
from .runtime_support import PY_FUNCTIONS, unsupported_reasons_static
from .symbols import UserVar, load_erh

NARRATION_DIRS = ("口上/", "地の文/")


def list_erb_files(root: Path, ext: str = ".ERB") -> list[Path]:
    def walk(d: Path) -> list[Path]:
        out: list[Path] = []
        for sub in sorted((p for p in d.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
            out.extend(walk(sub))
        files = [p for p in d.iterdir() if p.is_file() and p.suffix.upper() == ext]
        out.extend(sorted(files, key=lambda p: p.name.lower()))
        return out

    return walk(root)


@dataclass
class _Entry:
    rel: str
    start: int
    end: int
    kind: str  # proc / int / str


class Catalog:
    def __init__(self, erb_dir: Path, csv_names: dict[str, dict[int, str]]) -> None:
        self.erb_dir = erb_dir
        self._lines: dict[str, list[tuple[int, str]]] = {}
        self.index: dict[str, _Entry] = {}
        self.files: list[str] = []
        texts: dict[str, bytes] = {}
        for p in list_erb_files(erb_dir):
            rel = p.relative_to(erb_dir).as_posix()
            raw = p.read_bytes()
            texts[rel] = raw
            lines = read_logical_lines(raw)
            self.files.append(rel)
            if rel.startswith(NARRATION_DIRS):
                self._lines[rel] = lines
            for name, s, e in scan_labels(lines):
                if name in self.index:
                    continue
                kind = "proc"
                for _, t in lines[s + 1 : e]:
                    if not t.startswith("#"):
                        break
                    w = t[1:].strip().upper()
                    if w == "FUNCTION":
                        kind = "int"
                    elif w == "FUNCTIONS":
                        kind = "str"
                self.index[name] = _Entry(rel, s, e, kind)
        erh = []
        for p in list_erb_files(erb_dir, ".ERH"):
            rel = p.relative_to(erb_dir).as_posix()
            erh.append((rel, read_logical_lines(p.read_bytes())))
        self.user_vars: dict[str, UserVar] = load_erh(erh)
        self._mark_narration_owned(texts)
        names = {k: set(v.values()) for k, v in csv_names.items()}
        self.ctx = ExtractContext(self.user_vars, names, self.is_user_method, match_hook)
        self._parsed: dict[str, N.FuncDef] = {}
        self._support: dict[str, Optional[str]] = {}

    def _mark_narration_owned(self, texts: dict[str, bytes]) -> None:
        """口上／地の文の ERH で宣言され、口上／地の文以外の ERB から一切参照されない非 SAVEDATA 変数は
        「口上内部の状態」とみなし代入を許す（Emuera では非 SAVEDATA の #DIM は存檔されない：
        UserDefinedVariable.cs:150–152）。"""
        others = b"\n".join(v for k, v in texts.items() if not k.startswith(NARRATION_DIRS))
        for uv in self.user_vars.values():
            uv.narration_owned = False  # type: ignore[attr-defined]
            if uv.const or uv.save or uv.glob or uv.chara:
                continue
            if not uv.source.startswith(NARRATION_DIRS):
                continue
            if uv.name.encode("utf-8") in others.upper():
                continue
            uv.narration_owned = True  # type: ignore[attr-defined]

    # --- 索引 ---
    def exists(self, name: str) -> bool:
        return name.upper() in self.index

    def is_user_method(self, name: str) -> bool:
        e = self.index.get(name.upper())
        return e is not None and e.kind != "proc"

    def lines_of(self, rel: str) -> list[tuple[int, str]]:
        if rel not in self._lines:
            self._lines[rel] = read_logical_lines((self.erb_dir / rel).read_bytes())
        return self._lines[rel]

    def get(self, name: str) -> Optional[N.FuncDef]:
        up = name.upper()
        if up in self._parsed:
            return self._parsed[up]
        e = self.index.get(up)
        if e is None:
            return None
        lines = self.lines_of(e.rel)[e.start : e.end]
        fd = parse_function(self.ctx, e.rel, lines)
        self._parsed[up] = fd
        return fd

    # --- 可執行性 ---
    def unsupported_reason(self, name: str, _stack: Optional[set] = None) -> Optional[str]:
        """None = 可執行。否則回傳第一個原因（「関数名:行 原因」）。呼叫先（静的）も再帰的に確認する。"""
        up = name.upper()
        if up in PY_FUNCTIONS:
            return None
        if up in self._support:
            return self._support[up]
        stack = _stack if _stack is not None else set()
        if up in stack:
            return None  # 再帰：他の経路で判定される
        fd = self.get(up)
        if fd is None:
            return f"{up}: 関数が存在しません"
        stack.add(up)
        reason = self._own_reason(fd)
        if reason is None:
            for callee in sorted(fd.calls):
                if callee in PY_FUNCTIONS:
                    continue
                if not self.exists(callee):
                    continue  # TRYCALL 先が無い／実行時に判定
                r = self.unsupported_reason(callee, stack)
                if r is not None:
                    reason = r if r.startswith(callee + ":") or ":" in r else f"{callee}: {r}"
                    break
        stack.discard(up)
        self._support[up] = reason
        return reason

    def _own_reason(self, fd: N.FuncDef) -> Optional[str]:
        if fd.unsupported:
            line, why = fd.unsupported[0]
            return f"{fd.name}:{line} {why}"
        r = unsupported_reasons_static(fd, self)
        if r:
            return f"{fd.name}:{r[0][0]} {r[0][1]}"
        return None

    # --- 報告 ---
    def narration_functions(self) -> list[str]:
        return [n for n, e in self.index.items() if e.rel.startswith(NARRATION_DIRS)]

    def report(self) -> dict:
        """覆蓋率：函式數・可執行數・unsupported 原因（第一原因）的前 10 名・檔案別。"""
        per_file: dict[str, list[int]] = {}
        reasons: dict[str, int] = {}
        total = ok = 0
        for name in self.narration_functions():
            e = self.index[name]
            total += 1
            r = self.unsupported_reason(name)
            pf = per_file.setdefault(e.rel, [0, 0])
            pf[0] += 1
            if r is None:
                ok += 1
                pf[1] += 1
            else:
                key = _reason_key(r)
                reasons[key] = reasons.get(key, 0) + 1
        top = sorted(reasons.items(), key=lambda kv: -kv[1])
        return {"total": total, "ok": ok, "reasons": top, "files": per_file}


def _reason_key(r: str) -> str:
    """「FUNC:行 原因」→ 原因の種類（固有名・行番号を落とす）。"""
    m = re.match(r"^[^ ]+ (.*)$", r)
    why = m.group(1) if m else r
    why = re.sub(r"命令 (\S+)（.*?）", r"命令 \1", why)
    why = re.sub(r"(変数|関数) \S+", lambda mm: mm.group(0), why)
    return why

