from __future__ import annotations

import asyncio
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.profile_manager import ProfileManager

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.active.discard(ws)


def get_connections(websocket: WebSocket):
    return websocket.app.state.connections


def get_manager(websocket: WebSocket) -> ProfileManager:
    return websocket.app.state.manager


@router.websocket("/api/ws")
async def ws_endpoint(websocket: WebSocket):
    manager: ProfileManager = get_manager(websocket)
    connections: ConnectionManager = get_connections(websocket)
    await connections.connect(websocket)
    try:
        # Send initial state so a (re)connecting client is immediately in sync.
        await websocket.send_json(
            {
                "type": "init",
                "monitor": manager.monitor_status(),
                "profiles": [p.to_summary() for p in manager.list_profiles()],
            }
        )
        while True:
            # Keep the connection alive; client messages are ignored.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await connections.disconnect(websocket)
    except Exception:  # noqa: BLE001
        await connections.disconnect(websocket)
