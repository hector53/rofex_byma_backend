#devolucion de llamada de una tarea
import asyncio

from aiocat import real_get_cat_fact_with_errors

def check_task_status(task: asyncio.Task):
    if task.done():
        if task.exception() is not None:
            print(f'Task #{task.get_name()} failed')
            return
        print(f'Task #{task.get_name()} complete, result - {task.result()}')

async def main():
    tasks = []
    for i in range(5):
        task = asyncio.create_task(real_get_cat_fact_with_errors())
        task.set_name(str(i + 1))
        task.add_done_callback(check_task_status)
        tasks.append(task)
    await asyncio.gather(*tasks, return_exceptions=True)

asyncio.run(main())