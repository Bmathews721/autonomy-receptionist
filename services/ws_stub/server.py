
import asyncio, websockets, wave, datetime, os

async def handler(websocket):
    os.makedirs("recordings", exist_ok=True)
    fname = datetime.datetime.utcnow().strftime("recordings/%Y%m%d_%H%M%S.wav")
    # This is a stub; in real use you'd handle audio frames.
    await websocket.send("ok")
    await websocket.recv()
async def main():
    async with websockets.serve(handler, "", 8765):
        await asyncio.Future()
if __name__ == "__main__":
    asyncio.run(main())
