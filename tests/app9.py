import asyncio

from aiocat import real_get_cat_fact_with_errors

def check_task_status(task: asyncio.Task):
    # check if task is done and print results
    if task.done():
        if task.exception() is not None:
            print(f'Task #{task.get_name()} failed')
            return True
        print(f'Task #{task.get_name()} complete, result - {task.result()}')
        return True
    return False
    # else task is in progress

async def main():
    # create array of tasks with numbered names
    tasks = [asyncio.create_task(real_get_cat_fact_with_errors(), name=str(i+1)) for i in range(5)]

    while tasks:
      #  # check status of tasks and remove those that are finished
        tasks = [task for task in tasks if not check_task_status(task)]
        """  esto es lo mismo q arriba pero mas detallado para que se entienda
            taskNew = []
        for task in tasks: 
            if check_task_status(task)==False:
                taskNew.append(task)
        tasks = taskNew
        """
       # print("tasks quedan: ", len(tasks))
        await asyncio.sleep(0.1)
   # print("tasks final quedan: ", len(tasks))

asyncio.run(main())