"""中性瀏覽器驗收：真實 Web 模板／JS／GameSession 握手，不進入遊戲流程。

python tools/preview_generic_input.py --port 8871
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.input_request import WaitInputRequest, input_number, inputs
from eragvt.web import create_app


def build_app(save_dir):
    app = create_app(load_game_data(default_csv_dir()), Path(save_dir), narration=None)
    session = app.state.session
    ctx = SimpleNamespace(state=SimpleNamespace(result={0: 73}, results={0: "kept"}), out=session.out)
    session.out.drain()
    def flow():
        try:
            session.out.printw("中性驗收：按 Enter 確認第一段。")
            yield WaitInputRequest()
            session.out.printw("第二段：按確認按鈕；舊頁面不可重複推進。")
            yield WaitInputRequest()
            session.out.printl("請輸入數字；空字不應送出。")
            number = yield from input_number(ctx)
            session.out.printl(f"收到數字：{number}；請輸入文字（允許空字及空白）。")
            text = yield from inputs(ctx)
            session.out.printl(f"收到文字：{text!r}")
            for n in range(60): session.out.printl(f"中性長內容 {n + 1}")
            session.out.printw("長內容尾端：焦點應在確認按鈕；可用返回標題測試清理。")
            yield WaitInputRequest()
        finally:
            app.state.preview_closed = True
    app.state.preview_closed = False
    session._run_gen(flow(), session.begin_title)
    return app


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8871)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="eragvt-neutral-input-") as directory:
        app = build_app(directory)
        try:
            uvicorn.run(app, host="127.0.0.1", port=args.port)
        finally:
            app.state.session.close()
