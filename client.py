import asyncio
import websockets

async def client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        while True:
            message = input("Enter message to send (or 'exit' to quit): ")
            if message.lower() == "exit":
                break
            
            await websocket.send(message)
            response = await websocket.recv()
            print(f"Received from server: {response}")

asyncio.run(client())
