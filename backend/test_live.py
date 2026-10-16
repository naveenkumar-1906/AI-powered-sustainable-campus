
import asyncio
import json
import websockets


async def main():
    uri = "ws://127.0.0.1:8000/ws/alerts"

    async with websockets.connect(uri) as websocket:
        print("Connected to CleanO Campus alerts!")

        # The server sends a welcome message first.
        welcome = await websocket.recv()
        print("WELCOME:", welcome)

        print("\nNow create an issue in /docs.")
        print("Waiting for a live alert...\n")

        message = await asyncio.wait_for(
            websocket.recv(),
            timeout=60,
        )

        print("LIVE ALERT RECEIVED:")
        print(json.dumps(json.loads(message), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
