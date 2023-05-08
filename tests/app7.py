#lo mismo pero le damos nombre a la tarea y podemos consultarlo 
import asyncio

from aiocat import get_cat_fact

async def main():
    get_fact_task = asyncio.create_task(get_cat_fact())
    get_fact_task.set_name('Task to get a random fact about cats')
    result = await get_fact_task
    print(f'Finished running task: {get_fact_task.get_name()}')
    print(result)

asyncio.run(main())