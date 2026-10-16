
import asyncio
import json
import websockets


async def main():
    uri = "ws://127.0.0.1:8000/ws/alerts"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to CleanO Campus alerts!")

            welcome = await websocket.recv()
            print("WELCOME:", welcome)

            print("\nNow create an issue in /docs.")
            print("Waiting up to 120 seconds for an alert...\n")

            try:
                message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=120,
                )
                print("LIVE ALERT RECEIVED:")
                print(json.dumps(json.loads(message), indent=2))

            except asyncio.TimeoutError:
                print("No alert received within 120 seconds.")

    except Exception as exc:
        print(f"Connection failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
