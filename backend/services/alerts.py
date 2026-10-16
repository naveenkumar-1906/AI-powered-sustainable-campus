
import asyncio
from fastapi import WebSocket


class AlertManager:
    def __init__(self):
        self.connections: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

        async with self.lock:
            self.connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            self.connections.discard(websocket)

    async def broadcast(self, event: dict):
        async with self.lock:
            connections = list(self.connections)

        stale_connections = []

        for websocket in connections:
            try:
                await websocket.send_json(event)
            except Exception:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            await self.disconnect(websocket)


alert_manager = AlertManager()
