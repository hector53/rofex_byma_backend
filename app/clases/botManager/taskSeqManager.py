import queue
import threading
import time
import asyncio
from app.fix_application.application import Application
import logging
from app.clases.class_cola import Cola
class taskSeqManager(Cola):
    def __init__(self):
        super().__init__()
        self.paused = asyncio.Event()
        self.paused.set()
        self.stop = asyncio.Event()
        self.pause_flag = False
        self.taskToCancel = None
        self.log = logging.getLogger(f"taskSeqManager")

    async def add_task(self, task):
        self.log.info(f"agregando task: {task}")
        await self.agregar_tarea(task)

    async def stopCola(self):
        self.stop.set()

    async def pause(self):
        self.paused.clear()

    async def resume(self):
        self.paused.set()


