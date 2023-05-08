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