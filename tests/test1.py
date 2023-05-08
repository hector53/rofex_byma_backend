import asyncio


async def task():
    print("entrando a tarea")
    await asyncio.sleep(2)
    print("saliendo de tarea")

async def main():
    task2 = asyncio.create_task(task())
    await asyncio.sleep(3)


asyncio.run(main())