"""讓同步成就函式沿遊戲 generator 的既有輸入通道等待。

沿用 narration.service 的雙 queue 握手；任一時間只有一側執行遊戲。
"""
import queue
import threading


class AbortWait(BaseException):
    pass


def with_achievement_wait(gen, out):
    to_main, to_worker = queue.Queue(), queue.Queue()

    def wait(request):
        to_main.put(("yield", request))
        kind, value = to_worker.get()
        if kind == "abort":
            raise AbortWait()
        return value

    def work(first, value):
        old = getattr(out, "achievement_wait", None)
        out.achievement_wait = wait
        try:
            request = next(gen) if first else gen.send(value)
            result = ("input", request)
        except StopIteration as stop:
            result = ("done", stop.value)
        except AbortWait:
            result = ("abort", None)
        except BaseException as exc:
            result = ("error", exc)
        finally:
            out.achievement_wait = old
        to_main.put(result)

    worker = None
    first, answer = True, None
    try:
        while True:
            worker = threading.Thread(target=work, args=(first,answer), name="eragvt-achievement-wait", daemon=True)
            worker.start()
            first = False
            while True:
                kind, value = to_main.get()
                if kind == "yield":
                    answer = yield value
                    to_worker.put(("value", answer))
                    continue
                worker.join()
                if kind == "input":
                    answer = yield value
                    break
                if kind == "done":
                    return value
                raise value
    finally:
        if worker is not None and worker.is_alive():
            to_worker.put(("abort", None))
            worker.join()
        gen.close()
