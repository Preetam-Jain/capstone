import random

def generate_data():
    data = []
    for i in range(50):
        data.append(random.randint(1, 100))

    return data

import asyncio
import websockets

async def handle_client(websocket, path):
    print("Client connected")
    try:
        async for message in websocket:
            print(f"Received from client: {message}")
            response = f"Server received: {message}"
            await websocket.send(response)
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    server = await websockets.serve(handle_client, "localhost", 8765)
    print("WebSocket Server started on ws://localhost:8765")
    await server.wait_closed()

asyncio.run(main())


