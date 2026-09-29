"""FastAPI + Jinja2 的 Web 介面。後端持有遊戲狀態，前端只負責顯示與輸入。"""

from .app import create_app

__all__ = ["create_app"]
