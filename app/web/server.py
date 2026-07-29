"""aiohttp web server — bot polling bilan bir loop'da ishlaydi."""
from __future__ import annotations

from aiohttp import web

from app.core.config import get_settings
from app.core.logger import logger
from app.web.api import setup_api_routes


def _cors_origin(request: web.Request) -> str:
    """So'rov origin'iga qarab ruxsat etilgan CORS origin qiymatini qaytaradi."""
    allowed = get_settings().cors_origins_list
    origin = request.headers.get("Origin", "")
    if allowed == ["*"]:
        return origin or "*"
    return origin if origin in allowed else allowed[0]


@web.middleware
async def cors_middleware(request: web.Request, handler) -> web.Response:
    """CORS sarlavhalarini qo'shadi — frontend GitHub Pages'da bo'lgani uchun.

    OPTIONS (preflight) so'rovlariga darhol 200 qaytaradi.
    """
    if request.method == "OPTIONS":
        resp = web.Response(status=200)
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = _cors_origin(request)
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Telegram-Init-Data"
    resp.headers["Vary"] = "Origin"
    return resp


async def serve_webapp_index(request: web.Request) -> web.Response:
    """GET / → static/webapp/index.html."""
    settings = get_settings()
    index_path = settings.base_dir / "static" / "webapp" / "index.html"
    if not index_path.exists():
        return web.Response(text="WebApp index.html topilmadi", status=404)
    return web.FileResponse(index_path)


def create_web_app() -> web.Application:
    """aiohttp Application yasash — bot bilan asyncio loop baham."""
    settings = get_settings()
    app = web.Application(middlewares=[cors_middleware])

    # 1. API routelar
    setup_api_routes(app)

    # 2. Static fayllar (CSS, JS, rasmlar)
    webapp_static = settings.base_dir / "static" / "webapp"
    if webapp_static.exists():
        app.router.add_static("/static/", path=webapp_static, name="static")

    # 3. 3D emoji PNG (Microsoft Fluent UI) — bot va WebApp baham
    emojis_dir = settings.base_dir / "static" / "emojis"
    if emojis_dir.exists():
        app.router.add_static("/emojis/", path=emojis_dir, name="emojis")

    # 4. Asosiy sahifa
    app.router.add_get("/", serve_webapp_index)
    app.router.add_get("/webapp", serve_webapp_index)

    return app


async def run_web_server(app: web.Application, port: int) -> web.AppRunner:
    """Web server'ni ishga tushirish va `AppRunner` ni qaytarish (shutdown uchun)."""
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("🌐 Web server: http://localhost:{}", port)
    return runner


__all__ = ["create_web_app", "run_web_server"]
