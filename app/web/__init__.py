"""Telegram Mini App backend — aiohttp web server.

Bot polling bilan bir vaqtda ishlaydi (asyncio loop'i baham ko'riladi).
"""
from app.web.server import create_web_app, run_web_server

__all__ = ["create_web_app", "run_web_server"]
