#aqui creamos tareas
import asyncio

from aiocat import get_cat_fact

async def main():
    get_fact_task = asyncio.create_task(get_cat_fact())
    result = await get_fact_task
    print(result)

asyncio.run(main())