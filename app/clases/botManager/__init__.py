import asyncio
import logging
import gc
class botManager:
    def __init__(self):
        self.tasks = asyncio.Queue()
        self.main_tasks = {}  # Diccionario para mantener un registro de los objetos MainTask
        self.log = logging.getLogger("botManager")

    async def add_task(self, task):
        self.main_tasks[task.id] = task

        self.log.info(f"entrando a addtask del botManager: {task}, ya lo agregue al maintask: {self.main_tasks}")
        await self.tasks.put(task)
        task.taskToCancel = asyncio.create_task(task.run())
        

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

    async def get_fixTask_by_id_user(self, user):
        taskReturn = None
        if user in self.main_tasks: 
            return self.main_tasks.get(user, None)
        return taskReturn
    
    async def stop_task_by_id(self, id):
        while not self.tasks.empty():
            task = await self.tasks.get()
            if task.id == id:
                task.taskToCancel.cancel()
                del self.main_tasks[id]
                gc.collect()
                self.log.info(f"se borro la tarea correctamente")
        self.log.info("se salio del ciclo de borrar tarea")
