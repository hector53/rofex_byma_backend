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

async def main():
    task_manager = TaskManager()

    # Agrega tareas de forma dinámica
    while True:
        # Agrega 2 tareas cada 5 segundos
        for i in range(10):
            task = Task(i)
            await task_manager.add_task(task)

        await asyncio.sleep(5)
        break

    # Espera a que todas las tareas se completen
    await task_manager.stop_all_tasks()

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

asyncio.run(main())