import asyncio

async def my_coroutine():
    print("before sleeping")
    await asyncio.sleep(1)
    print("after sleeping")

asyncio.run(my_coroutine())
print("after event loop")