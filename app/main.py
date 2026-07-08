"""FastAPI 入口:挂载 API 路由 + WebSocket 进度 + 静态前端。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import routes_analysis, routes_books, routes_export, routes_results
from app.config import BASE_DIR
from app.db.database import init_db, reset_in_progress_chapters
from app.services.progress import progress_manager
from app.utils.logger import get_logger, setup_logging

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db()
    # 断点续传:回滚上次未完成的 analyzing 章节
    await reset_in_progress_chapters()
    logger.info("Novel Insight 启动完成")
    yield


app = FastAPI(title="Novel Insight", version="0.1.0", lifespan=lifespan)

# 本地开发:允许 Vite(5173)跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_books.router)
app.include_router(routes_analysis.router)
app.include_router(routes_results.router)
app.include_router(routes_export.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/progress/{book_id}")
async def ws_progress(websocket: WebSocket, book_id: int):
    await websocket.accept()
    await progress_manager.connect(book_id, websocket)
    try:
        while True:
            # 仅用于保活/探测断开;前端不需要主动发消息
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await progress_manager.disconnect(book_id, websocket)


# 生产构建后的前端(frontend/dist)。开发时用 Vite,无需此挂载。
_DIST = BASE_DIR / "frontend" / "dist"
if _DIST.exists():
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")
    _INDEX = _DIST / "index.html"

    # SPA history 模式:所有非 API/WS 路径回退到 index.html(API 路由已先注册,优先匹配)
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_INDEX))

    logger.info("已挂载前端静态目录: %s", _DIST)
else:
    @app.get("/")
    async def root():
        return {
            "app": "Novel Insight",
            "hint": "前端开发模式请运行 `cd frontend && npm run dev`,然后访问 http://localhost:5173",
            "api_docs": "/docs",
        }
