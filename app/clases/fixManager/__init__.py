import asyncio
from app.clases.class_main import MainTask, FixMsgQueue
import logging
import queue
import threading
import gc
class fixManager2:
    def __init__(self):
        self.tasks = queue.Queue()
        self.main_tasks = {}  # Diccionario para mantener un registro de los objetos MainTask
        self.log = logging.getLogger("fixManager")

    def add_task(self, task):
        self.tasks.put(task)
        thread = threading.Thread(target=task.run)
        thread.daemon=True
        thread.start()
        if isinstance(task, MainTask):
            # Agregar el objeto MainTask al diccionario
            self.main_tasks[task.user] = task
        elif isinstance(task, FixMsgQueue):
            self.log.info(f"task msg: {task}")
            self.main_tasks[task.id] = task

    def remove_task(self, task):
        self.tasks.remove(task)

    def stop_task(self, task):
        task.stop()

    def stop_all_tasks(self):
        print("entrando a detener todas")
        while not self.tasks.empty():
            print("obtener tarea a deteber")
            task = self.tasks.get()
            print(f"tarea: {task}")
            task.stop()

    def get_fixTask_by_id_user(self, user):
        taskReturn = None
        if user in self.main_tasks: 
            return self.main_tasks.get(user, None)
        return taskReturn
class fixManager:
    def __init__(self):
        self.tasks = asyncio.Queue()
        self.main_tasks = {}  # Diccionario para mantener un registro de los objetos MainTask
        self.log = logging.getLogger("fixManager")

    async def add_task(self, task):
        await self.tasks.put(task)
        task.taskToCancel = asyncio.create_task(task.run())
        
        if isinstance(task, MainTask):
            # Agregar el objeto MainTask al diccionario
            self.main_tasks[task.user] = task
            
      

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

    async def stop_task_by_id(self, user):
        while not self.tasks.empty():
            task = await self.tasks.get()
            if task.user == user:
                task.taskToCancel.cancel()
                del self.main_tasks[user]
                gc.collect()
                self.log.info(f"se borro la tarea correctamente")
        self.log.info("se salio del ciclo de borrar tarea")
            
        

    async def get_fixTask_by_id_user(self, user):
        taskReturn = None
        if user in self.main_tasks: 
            return self.main_tasks[user]
        return taskReturn

