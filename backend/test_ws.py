import asyncio
import websockets
import json
import requests

async def test_ws():
    async with websockets.connect("ws://127.0.0.1:8000/ws/telemetry") as websocket:
        print("Connected.")
        
        # Trigger spike
        r = requests.post("http://127.0.0.1:8000/api/trigger_spike")
        print("Trigger spike response:", r.status_code)
        
        for _ in range(5):
            msg = await websocket.recv()
            data = json.loads(msg)
            print(f"Recv: {data}")

asyncio.run(test_ws())
