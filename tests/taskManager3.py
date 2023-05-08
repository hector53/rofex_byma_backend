import asyncio
from concurrent.futures import ThreadPoolExecutor
import time


class TaskManager:
    def __init__(self):
        self.tasks = asyncio.Queue()

    async def add_task(self, task):
        await self.tasks.put(task)
        asyncio.create_task(task.run())

    async def remove_task(self, task):
        self.tasks.remove(task)

    def stop_task(self, task):
        task.stop()

    async def stop_all_tasks(self):
        print("entrando a detener todas")
        while not self.tasks.empty():
            print("obtener tarea a deteber")
            task = await self.tasks.get()
            print(f"tarea: {task}")
            task.stop()


async def main():
    task_manager = TaskManager()

    start_time = time.monotonic()  # Inicia el temporizador

    # Agrega tareas de forma dinámica
    while True:
        # Agrega 2 tareas cada 5 segundos
        for i in range(4):
            task = Task(i)
            await task_manager.add_task(task)

        await asyncio.sleep(5)
        break

    # Espera a que todas las tareas se completen
    await task_manager.stop_all_tasks()

    end_time = time.monotonic()  # Detiene el temporizador
    elapsed_time = end_time - start_time  # Calcula el tiempo transcurrido
    print(
        f"Todas las tareas han sido detenidas. Tiempo total transcurrido: {elapsed_time:.2f} segundos.")


class Task:
    def __init__(self, id):
        self.stop_event = asyncio.Event()
        self.id = id
        self.descripcion = "hola soy la descripcion del bot: "+self.id

    async def run(self):
        while not self.stop_event.is_set():
            print(f"Task {self.id} running...")
            await asyncio.sleep(1)
        print(f"Task {self.id} stopped.")

    def stop(self):
        print("deteniento evento en task")
        self.stop_event.set()

asyncio.run(main())