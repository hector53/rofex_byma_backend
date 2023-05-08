import asyncio
from concurrent.futures import ProcessPoolExecutor
import threading
import time
def tareaAsync(id):
    print("entrando a tarea async", id)
    time.sleep(2)
    print("saliendo de tarea async", id)
    return




def main():
    executor = ProcessPoolExecutor()
    executor.submit(tareaAsync, 1)
    executor.submit(tareaAsync, 2)
    print("despus de las tareas")
if __name__ == '__main__':
    main()