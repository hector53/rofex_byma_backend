import asyncio
import logging
from logging.handlers import RotatingFileHandler
# Configurar el registro de eventos
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler('taskReport.log')
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(name)s  %(levelname)s  %(message)s  %(lineno)d')
handler.setFormatter(formatter)

logger.addHandler(handler)
async def task1():
    logging.info("Tarea 1 iniciada")
    while True:
        logging.info("Tarea 1 en ejecución")
        await asyncio.sleep(1)

async def task2():
    logging.info("Tarea 2 iniciada")
    while True:
        logging.info("Tarea 2 en ejecución")
        await asyncio.sleep(1)

async def task3():
    logging.info("Tarea 3 iniciada")
    while True:
        await asyncio.sleep(3)
        logging.info("Tarea 3 en ejecución")

async def main():
    task_list = [asyncio.create_task(task1()), asyncio.create_task(task2())]
    await asyncio.gather(*task_list)

if __name__ == "__main__":
    asyncio.run(main())
