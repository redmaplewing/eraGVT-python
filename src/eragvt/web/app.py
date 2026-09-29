"""Web 介面：把 `GameSession` 的輸出（`Line` 列表）渲染成 HTML，把按鈕／輸入的數值交回 session。

單人本機遊玩用，session 只有一個（存在 app.state）。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..data import GameData
from ..game import shop
from ..game.session import GameSession
from ..state import GameRng

_HERE = Path(__file__).parent


class InputBody(BaseModel):
    value: int


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

    def new_session() -> GameSession:
        return GameSession(data, save_dir, rng=rng_factory(), narration=narration, now=now)

    app.state.session = new_session()

    def screen_json() -> dict[str, Any]:
        s: GameSession = app.state.session
        st = s.state
        # 背景色：SHOW_SHOP:26–35（FLAG:999 はデバッグ用の特別色）
        bg = None
        if st is not None:
            bg = "#000028" if st.flag[999] else shop.BG_COLORS[st.time]
        return {
            "phase": s.phase.value,
            "background": bg,
            "lines": [line.to_json() for line in s.screen()],
        }

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "index.html", {"screen": screen_json()})

    @app.post("/input")
    def post_input(value: int = Form(...)) -> RedirectResponse:
        app.state.session.input(value)
        return RedirectResponse("/", status_code=303)

    @app.post("/restart")
    def restart() -> RedirectResponse:
        app.state.session = new_session()
        return RedirectResponse("/", status_code=303)

    @app.get("/api/screen")
    def api_screen() -> JSONResponse:
        return JSONResponse(screen_json())

    @app.post("/api/input")
    def api_input(body: InputBody) -> JSONResponse:
        app.state.session.input(body.value)
        return JSONResponse(screen_json())

    return app
