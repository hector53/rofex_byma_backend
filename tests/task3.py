import asyncio

class Cola:
    def __init__(self):
        self.tareas = []
    
    def agregar_tarea(self, tarea):
        self.tareas.append(tarea)
    
    async def obtener_tarea(self):
        print("entrando a obtener tarea", self.tareas)
        if self.tareas:
            return self.tareas.pop(0)
        return None
    
    async def marcar_completada(self, tarea):
        if tarea in self.tareas:
            self.tareas.remove(tarea)


class TaskManager:
    def __init__(self):
        self.tasks_queue = Cola()
        self.loop = asyncio.get_event_loop()
        self.tasks = set()
        self.processTask = self.loop.create_task(self._process_tasks())

    async def _process_tasks(self):
        while True:
            task = await self.tasks_queue.obtener_tarea()
            if task: 
                print("si hay tareas", task)
                self.loop.create_task(self.async_task(task))
            await asyncio.sleep(1)
            # Procesar la tarea en un nuevo hilo en paralelo

           # await self.async_task(1)
            # Marcar la tarea como completa

    async def async_task(self,id):
        print("Tarea asíncrona", id)
        await asyncio.sleep(2)
        print("saliendo de tarea ", id)

    def add_task(self, task):
        print("agregamos la tarea")
        self.tasks_queue.agregar_tarea(task)

    async def wait_all_tasks(self):
        await asyncio.gather(*self.tasks)



async def main():
    task_manager = TaskManager()
    print("ya iniciamos el taskManager")
    task_manager.add_task(1)
    task_manager.add_task(2)
    await asyncio.sleep(6)
    task_manager.processTask.cancel()

asyncio.run(main())
#el task 3 funciono debo probarlo , comn una nueva orden para ver cuanto dura, este me va servir para 
#la orden operada # pero ya sigo el lunes