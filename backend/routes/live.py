
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.alerts import alert_manager

router = APIRouter(tags=["Live Alerts"])


@router.websocket("/ws/alerts")
async def live_alerts(websocket: WebSocket):
    await alert_manager.connect(websocket)

    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to CleanO Campus live alerts",
        })

        while True:
            # Keep the connection open and detect disconnects.
            await websocket.receive_text()

    except WebSocketDisconnect:
        await alert_manager.disconnect(websocket)
    except Exception:
        await alert_manager.disconnect(websocket)
