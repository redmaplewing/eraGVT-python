"""稀疏陣列的 era 語意：未設定讀為預設值、寫入預設值等於刪除。"""

import pytest

from eragvt.state import IntArray, StrArray


@pytest.mark.parametrize(
    ("ops", "reads"),
    [
        ([], {0: 0, 999: 0}),
        ([(5, 3)], {5: 3, 4: 0}),
        ([(5, 3), (5, 0)], {5: 0}),
        ([(0, -1)], {0: -1}),  # 素質処女_処女喪失 = -1（TALENT.ERH:14）
        ([((1, 300), 7)], {(1, 300): 7, (1, 301): 0}),  # CDFLAG 2 維
    ],
)
def test_int_array_reads(ops, reads):
    a = IntArray()
    for k, v in ops:
        a[k] = v
    for k, v in reads.items():
        assert a[k] == v


def test_writing_default_removes_key():
    a = IntArray({1: 5})
    a[1] = 0
    assert len(a) == 0 and not a.is_set(1)


def test_str_array_default_empty():
    s = StrArray()
    assert s[10] == ""
    s[10] = "赤羽"
    s[10] = ""
    assert len(s) == 0


@pytest.mark.parametrize("bad", [True, 1.5, "1", None])
def test_int_array_rejects_non_int(bad):
    with pytest.raises(TypeError):
        IntArray()[0] = bad


@pytest.mark.parametrize("key", [-1, (1, -1), "0", 1.0, (1, 2, 3)])
def test_invalid_keys(key):
    with pytest.raises(IndexError):
        IntArray()[key]


def test_bits():
    a = IntArray()
    a.set_bit(100, 0)
    a.set_bit(100, 5)
    assert a[100] == 0b100001
    assert a.get_bit(100, 5) and not a.get_bit(100, 1)
    a.set_bit(100, 0, False)
    assert a[100] == 0b100000


def test_iteration_is_sorted_and_json_roundtrip():
    a = IntArray({(2, 1): 4, 10: 1, 2: 9, (1, 5): 3})
    assert list(a) == [(1, 5), 2, (2, 1), 10]
    j = a.to_json()
    assert j == {"1:5": 3, "2": 9, "2:1": 4, "10": 1}
    assert IntArray.from_json(j) == a


def test_clear_is_varset():
    a = IntArray({1: 1, 2: 2})
    a.clear()
    assert len(a) == 0
