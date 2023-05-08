import asyncio
import time
class Task:
    def __init__(self, id):
        self.id = id
        self.stop_event = asyncio.Event()

    async def run(self):
        while not self.stop_event.is_set():
            print(f"Task {self.id} running...")
            await asyncio.sleep(1)
            if self.id==1: 
                self.stop()
        print(f"Task {self.id} stopped.")

    def stop(self):
        self.stop_event.set()

class TaskManager:
    def __init__(self, max_workers):
        self.max_workers = max_workers
        self.tasks = asyncio.Queue()
        self.workers = []

    async def add_task(self, task):
        await self.tasks.put(task)

    def start(self):
        loop = asyncio.get_running_loop()
        for i in range(self.max_workers):
            self.workers.append(loop.create_task(self.worker()))

    async def worker(self):
        while True:
            task = await self.tasks.get()
            await asyncio.create_task(task.run())

    async def stop(self):
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)

async def main():
    task_manager = TaskManager(max_workers=2)
    start_time = time.monotonic()  # Inicia el temporizador 
    tasks = []
    for i in range(5):
        task = Task(i)
        tasks.append(task)
        await task_manager.add_task(task)
    task_manager.start()
    await asyncio.sleep(5)
    await task_manager.stop()
    end_time = time.monotonic()  # Detiene el temporizador
    elapsed_time = end_time - start_time  # Calcula el tiempo transcurrido
    print(
        f"Todas las tareas han sido detenidas. Tiempo total transcurrido: {elapsed_time:.2f} segundos.")

asyncio.run(main())