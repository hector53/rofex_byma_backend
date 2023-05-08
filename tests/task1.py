import asyncio
import cProfile
import time
class botManager:
    def __init__(self):
        self.tasks = asyncio.Queue()

    async def add_task(self, task, type_run=1):
        if type_run==1:
            taskM = asyncio.create_task(task.run())
        elif type_run==2:
            taskM = asyncio.create_task(task)

        await self.tasks.put(taskM)

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
            task.cancel()
            print("task cancelada: ", task)




class taskSeqManager(asyncio.Queue):
    def __init__(self):
        super().__init__()
        self.paused = asyncio.Event()
        self.paused.set()
        self.pause_flag = False
      #  self.runBB = asyncio.create_task(self.run_bb())  
        # Crear una tarea asincrónica para ejecutar run_bb() en segundo plano

    async def add_task(self, task):
        await self.put(task)

    async def run(self):
        while True:
            await self.paused.wait()
            if not self.empty():
                task = await self.get()
                await self.execute_task(task)
            else:
                await asyncio.sleep(1)

    async def execute_task(self, task):
        # Do something with the task
        print(f"Executing task: {task}")
        if task==22:
            await self.nueva_orden(task)
        await asyncio.sleep(1)
    """    async def contador(self):
        print("entamos a contador")
        contador=0
        while True: 
            if self.pause_flag:
                await self.paused.wait()
            contador+=1
            print(f"contador = {contador} ")
            if contador==5: 
                print(f"llegamos a {contador} entonces salimos de la tarea")
                break
            await asyncio.sleep(1)
        print("saliendo de la tarea")

    async def contar3(self):
        print("entamos a contar3")
        self.pause()
        self.pause_flag = True
        contador=0
        while True: 
            contador+=1
            print(f"contar3 = {contador} ")
            if contador==3: 
                print(f"llegamos a {contador} entonces salimos de la tarea")
                break
            await asyncio.sleep(1)
        print("saliendo de la tarea reanundando")
        self.resume()
        self.pause_flag = False
    """
    def pause(self):
        self.paused.clear()

    def resume(self):
        self.paused.set()


class botBB(taskSeqManager):
    def __init__(self, id):
        super().__init__() 
        self.id = id

    async def calculate_bb(self):
        print("entrando a calcular bb")
        print("calculando bb")
        await asyncio.sleep(2)
        print("bb calculada")

    async def calculate_bb_every_ten_sec(self):
        while True:
            await asyncio.sleep(5)  # Esperar 5 segundos
            if self.pause_flag:
                await self.paused.wait()
            await self.calculate_bb()

    async def run_bb(self):
        print("iniciamos run bb en un hilo nuevo")
        task = asyncio.create_task(self.calculate_bb_every_ten_sec())
        print("run bb iniciada")
        # Esperar a que la tarea asincrónica termine y devuelva su resultado
        return task
    
    async def esperarRespuesta(self, orden):
        print(f"entrando a esperar respuesta de nueva orden: {orden}")
        print("esperando.....")
        await asyncio.sleep(4)
        print(f"llego respuesta de nueva orden {orden}")
        return True

    async def nueva_orden(self, orden):
        print(f"entrando a crear nueva orden: {orden} ")
        print("enviando orden....")
        task = asyncio.create_task(self.esperarRespuesta(orden))
        # Esperar a que la tarea asincrónica termine y devuelva su resultado
        response = await task
        print(f"orden {orden} procesada correctamente ")
        return response

async def ejecutar():
    
    print("primero instancio botManager")
    botManag = botManager()
    print("ahora agrego al primer bot como tarea, para que se ejecute en un hilo nuevo ")
    taskM = botBB(1)
    await botManag.add_task(taskM.run_bb(),2)
    await botManag.add_task(taskM,1)
    print("ya tenemos el bot corriendo como hilo del botManager")
    print("ahora le vamos a agregar una tarea para crear una nueva orden")
    await taskM.add_task(22)
    print("ya agregamos la tarea, mandamos a esperar 2seg ")
    await asyncio.sleep(2)
    print("ahora vamos a mandar otra nueva orden pero directa")
    await taskM.nueva_orden(23)
    print("ahora mandamos a esperar 5seg para q ocurra todo")
    await asyncio.sleep(5)
    print("ahora mandamos a pausar")
    taskM.pause()
    print("ahora mandamos a reanudar pero primero esperamos 2seg")
    await asyncio.sleep(2)
    taskM.resume()
    print("ahora esperamos 3 y cancelamos")
    await asyncio.sleep(3)
    await botManag.stop_all_tasks()
    print("cancelamos el worker")
    

async def main():
    start_time = time.monotonic()  # Inicia el temporizador
    await ejecutar()
    end_time = time.monotonic()  # Detiene el temporizador
    elapsed_time = end_time - start_time  # Calcula el tiempo transcurrido
    print(
        f"Todas las tareas han sido detenidas. Tiempo total transcurrido: {elapsed_time:.2f} segundos.")
    


asyncio.run(main())