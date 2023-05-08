import asyncio

paused = asyncio.Event()

if not paused.is_set():
    print("paused esta activo ")