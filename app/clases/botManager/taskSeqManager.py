import queue
import threading
import time
import asyncio
from app.fix_application.application import Application
class taskSeqManager(asyncio.Queue):
    def __init__(self):
        super().__init__()
        self.paused = asyncio.Event()
        self.paused.set()
        self.stop = asyncio.Event()
        self.pause_flag = False
        self.taskToCancel = None

    async def add_task(self, task):
        await self.put(task)

    async def stopCola(self):
        self.stop.set()

    async def pause(self):
        self.paused.clear()

    async def resume(self):
        self.paused.set()


