"""era 陣列變數的稀疏表示。

era 的陣列（FLAG、BASE、CSTR…）大小固定、未設定的元素為 0／空字串。
這裡只存「非預設值」的元素：讀取未設定的索引回傳預設值，寫入預設值等於刪除。
因此同一內容只有一種表示，存檔可以逐位元組重現（見 `docs/wiki/python/state.md`）。
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Generic, TypeVar, Union

Key = Union[int, tuple[int, int]]
V = TypeVar("V", int, str)


def _key_to_json(key: Key) -> str:
    if isinstance(key, tuple):
        return f"{key[0]}:{key[1]}"
    return str(key)


def _key_from_json(text: str) -> Key:
    if ":" in text:
        a, b = text.split(":", 1)
        return (int(a), int(b))
    return int(text)


def _sort_key(key: Key) -> tuple[int, int]:
    return key if isinstance(key, tuple) else (key, 0)


class _Sparse(Generic[V]):
    _default: V
    _value_type: type

    def __init__(self, data: dict[Key, V] | None = None) -> None:
        self._data: dict[Key, V] = {}
        if data:
            for k, v in data.items():
                self[k] = v

    def __getitem__(self, key: Key) -> V:
        return self._data.get(self._check_key(key), self._default)

    def __setitem__(self, key: Key, value: V) -> None:
        key = self._check_key(key)
        # bool 是 int 的子類，但 era 沒有 bool；明確擋掉以免 True 混進存檔。
        # IntEnum 等子類則轉成純 int 存（存檔與 == 比較才穩定）。
        if not isinstance(value, self._value_type) or isinstance(value, bool):
            raise TypeError(f"{type(self).__name__} 只接受 {self._value_type.__name__}：{value!r}")
        value = self._value_type(value)
        if value == self._default:
            self._data.pop(key, None)
        else:
            self._data[key] = value

    def __delitem__(self, key: Key) -> None:
        self._data.pop(self._check_key(key), None)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[Key]:
        return iter(sorted(self._data, key=_sort_key))

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and self._data == other._data  # type: ignore[attr-defined]

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self.items())!r})"

    def items(self) -> list[tuple[Key, V]]:
        return [(k, self._data[k]) for k in self]

    def is_set(self, key: Key) -> bool:
        """是否為非預設值。"""
        return self._check_key(key) in self._data

    def clear(self) -> None:
        """對應 era 的 `VARSET 變數`（全部回到預設值）。"""
        self._data.clear()

    def copy(self):
        new = type(self)()
        new._data = dict(self._data)
        return new

    def to_json(self) -> dict[str, V]:
        return {_key_to_json(k): v for k, v in self.items()}

    @classmethod
    def from_json(cls, obj: dict[str, V]):
        return cls({_key_from_json(k): v for k, v in obj.items()})

    @staticmethod
    def _check_key(key: Key) -> Key:
        if isinstance(key, tuple):
            if len(key) != 2 or any(type(k) is not int or k < 0 for k in key):
                raise IndexError(f"索引不合法：{key!r}")
            return key
        if type(key) is not int or key < 0:
            raise IndexError(f"索引不合法：{key!r}")
        return key


class IntArray(_Sparse[int]):
    """整數陣列（FLAG、BASE、CFLAG…），未設定為 0。"""

    _default = 0
    _value_type = int

    def get_bit(self, key: Key, bit: int) -> bool:
        """era `GETBIT(變數:key, bit)`。"""
        return bool((self[key] >> bit) & 1)

    def set_bit(self, key: Key, bit: int, on: bool = True) -> None:
        """era `SETBIT`／`CLEARBIT`。"""
        value = self[key]
        self[key] = value | (1 << bit) if on else value & ~(1 << bit)


class StrArray(_Sparse[str]):
    """字串陣列（SAVESTR、CSTR…），未設定為空字串。"""

    _default = ""
    _value_type = str
