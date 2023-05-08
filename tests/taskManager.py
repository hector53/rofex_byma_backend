import asyncio

class TaskManager:
    def __init__(self):
        self.tasks = asyncio.Queue()
        self.loop = asyncio.get_event_loop()

    async def add_task(self, task):
        await self.tasks.put(task)
        asyncio.create_task(task.run())

    async def remove_task(self, task):
        self.tasks.remove(task)

    def stop_task(self, task):
        task.stop()

    async def stop_all_tasks(self):
        while not self.tasks.empty():
            task = await self.tasks.get()
            task.stop()
        print("todas las tareas han sido detenidas")

class Task:
    def __init__(self, id):
        self.stop_event = asyncio.Event()
        self.id = id

    async def run(self):
        while not self.stop_event.is_set():
            print(f"Task {self.id} running...")
            await asyncio.sleep(1)

    def stop(self):
        self.stop_event.set()

# Ejemplo de uso
async def main():
    task_manager = TaskManager()
    task1 = Task(1)
    task2 = Task(2)

    await asyncio.gather(
        task_manager.add_task(task1),
        task_manager.add_task(task2)
    )

    await asyncio.sleep(5)

    await task_manager.stop_all_tasks()

asyncio.run(main())