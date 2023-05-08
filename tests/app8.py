#verificar estados de la tarea 
import asyncio

from aiocat import get_cat_fact

async def main():
    task1 = asyncio.create_task(get_cat_fact())
    task2 = asyncio.create_task(get_cat_fact())
    print(f'Task 1: done: {task1.done()}, cancelled: {task1.cancelled()}')
    print(f'Task 2: done: {task2.done()}, cancelled: {task2.cancelled()}')

    task1.cancel() # cancel first task
    await task2 # wait until second task is done
    print(f'Task 1: done: {task1.done()}, cancelled: {task1.cancelled()}')
    print(f'Task 2: done: {task2.done()}, cancelled: {task2.cancelled()}')

asyncio.run(main())