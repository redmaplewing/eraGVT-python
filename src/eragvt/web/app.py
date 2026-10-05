"""Web 介面：把 `GameSession` 的輸出（`Line` 列表）渲染成 HTML，把按鈕／輸入的數值交回 session。

單人本機遊玩用，session 只有一個（存在 app.state）。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from threading import RLock
from uuid import uuid4

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..data import GameData
from ..game import shop
from ..game.session import GameSession
from ..state import GameRng
from ..state.savefile import GameIdentity, GlobalStore

_HERE = Path(__file__).parent


class InputBody(BaseModel):
    value: int | str
    input_token: str | None = None


def create_app(
    data: GameData,
    save_dir: Path,
    rng_factory: Callable[[], GameRng] = GameRng,
    now: Callable[[], datetime] = datetime.now,
    narration: Any = "auto",
    csv_dir: Path | None = None,
) -> FastAPI:
    """narration="auto"：`csv_dir`（省略時は既定の CSV 目錄）旁有 `ERB/` 就用 catalog 版口上（S07），否則 Null。"""
    if narration == "auto":
        from ..data import default_csv_dir
        from ..narration.service import CatalogNarrationService

        narration = CatalogNarrationService.from_csv_dir(csv_dir or default_csv_dir(), data)
    app = FastAPI(title="eraGVT")
    templates = Jinja2Templates(directory=str(_HERE / "templates"))
    app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")

    # グローバル変数のメモリはタイトルに戻っても残る（Emuera：ResetData は GLOBAL を初期化しない）→ アプリ単位で 1 つ
    globals_store = GlobalStore.in_dir(save_dir, GameIdentity.from_data(data))

    def new_session() -> GameSession:
        return GameSession(data, save_dir, rng=rng_factory(), narration=narration, now=now, global_store=globals_store)

    app.state.session = new_session()
    input_lock = RLock()
    input_token = uuid4().hex

    def screen_json() -> dict[str, Any]:
        s: GameSession = app.state.session
        st = s.state
        # 與 GETBGCOLOR 共用實際 Console 背景，不依目前 TIME 反推。
        bg = s.out.bgcolor
        return {
            "phase": s.phase.value,
            "input_kind": s.input_kind,
            "input_token": input_token,
            "background": bg,
            "lines": [line.to_json() for line in s.screen()],
        }

    def submit(value: int | str, token: str | None) -> None:
        nonlocal input_token
        # Web 傳輸去重：舊頁面不能把一次確認送入下一個輸入點。
        # token 省略時保留既有 API／表單客戶端相容性。
        if token is not None and token != input_token:
            return
        app.state.session.input(value)
        input_token = uuid4().hex

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        with input_lock:
            return templates.TemplateResponse(request, "index.html", {"screen": screen_json()})

    @app.post("/input")
    def post_input(value: str = Form(""), input_token: str | None = Form(None)) -> RedirectResponse:
        with input_lock:
            submit(value, input_token)
        return RedirectResponse("/", status_code=303)

    @app.post("/restart")
    def restart() -> RedirectResponse:
        nonlocal input_token
        with input_lock:
            app.state.session.close()
            app.state.session = new_session()
            input_token = uuid4().hex
        return RedirectResponse("/", status_code=303)

    @app.get("/api/screen")
    def api_screen() -> JSONResponse:
        with input_lock:
            return JSONResponse(screen_json())

    @app.post("/api/input")
    def api_input(body: InputBody) -> JSONResponse:
        with input_lock:
            submit(body.value, body.input_token)
            return JSONResponse(screen_json())

    return app
