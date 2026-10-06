"""既有同步測試轉為generator介面的driver；任何INPUT都必須由測試明確回答。"""
from functools import wraps


def run_no_input(gen):
    """只接受沒有INPUT的路徑；第一次yield即失敗，不消耗／代答。"""
    try:
        request = next(gen)
    except StopIteration as exc:
        return exc.value
    gen.close()
    raise AssertionError(f"未預期的INPUT：{request!r}；需在測試提供明確回答")


def as_generator(fn):
    """保留既有mock回傳／副作用，只配合被mock函式的generator介面。"""
    @wraps(fn)
    def invoke(*args, **kwargs):
        yield from ()
        return fn(*args, **kwargs)
    return invoke
