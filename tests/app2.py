import asyncio

from aiocat import get_cat_fact

async def main():
    print("enviar tarea 1")
    print(await get_cat_fact())
    print("enviar tarea 2")
    print(await get_cat_fact())
    print("enviar tarea 3")
    print(await get_cat_fact())

asyncio.run(main())