from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import profiles_router, ws_router
from .api.websocket import ConnectionManager
from .config import Settings
from .services.file_watcher import FileWatcher
from .services.profile_manager import ProfileManager
from .services.semantic_mapper import load_mappings
from .services.source_mapper import SourceMapper

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    mapper = load_mappings(settings.mappings_dir)
    source_mapper = SourceMapper(mapper)
    manager = ProfileManager(settings, mapper, source_mapper)
    connections = ConnectionManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        manager.bind_loop(loop)
        manager.set_event_sink(connections.broadcast)
        scan_trigger = asyncio.Event()
        manager.set_scan_trigger(scan_trigger)

        # Initial scan (required in addition to the watcher).
        await loop.run_in_executor(None, manager.scan)

        watcher = FileWatcher(settings, manager)
        watcher.start()

        stop = asyncio.Event()

        async def rescan_loop() -> None:
            while not stop.is_set():
                try:
                    await asyncio.wait_for(
                        scan_trigger.wait(), timeout=settings.watch_interval
                    )
                except asyncio.TimeoutError:
                    pass
                scan_trigger.clear()
                await loop.run_in_executor(None, manager.scan)

        rescan_task = asyncio.create_task(rescan_loop())
        logger.info(
            "SGLang Profiler Viewer started (profile_root=%s, port=%s)",
            settings.profile_root,
            settings.port,
        )
        yield
        stop.set()
        rescan_task.cancel()
        watcher.stop()
        manager.shutdown()

    app = FastAPI(title="SGLang Profiler Viewer", lifespan=lifespan)
    app.state.settings = settings
    app.state.manager = manager
    app.state.connections = connections

    # API routes must be registered before the static mount so that /api/* wins.
    app.include_router(profiles_router)
    app.include_router(ws_router)

    frontend_dist = settings.frontend_dist
    if frontend_dist is not None and Path(frontend_dist).exists():
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_dist), html=True),
            name="frontend",
        )
    return app


app = create_app()


def run() -> None:
    settings = Settings.from_env()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()
