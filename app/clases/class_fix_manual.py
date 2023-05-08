import asyncio
from collections import defaultdict
from typing import DefaultDict,  Dict
from threading import Thread
from app.clases.class_client_request import client_request
import logging
import time
from app import mongo
from bson import ObjectId
from app.clases.botManager.taskSeqManager import taskSeqManager


class fixManual(taskSeqManager):
    # f=instancia de fix, id_bot= id del bot que se está ejecutando
    def __init__(self, f, id_fix,  id_bot, cuenta, user_id):
        self.user_id = user_id
        self.fix = f
        self.name = f"fix_manual_{id_fix}"
        self.id_fix = id_fix
        self.log = logging.getLogger(self.name)
        # self.log.setLevel(logging.WARNING)
       # handler = logging.FileHandler(f"{self.name}.log")
      #  handler.setLevel(logging.WARNING)
      #  formatter = logging.Formatter('%(asctime)s %(name)s  %(levelname)s  %(message)s  %(lineno)d')
      #  handler.setFormatter(formatter)
      #  self.log.addHandler(handler)
        # instancia de la clase client_request
        self.clientR = client_request(f, id_bot, cuenta, mongo)
        self.threadLoop = None

    async def run(self):
        try:
            self.threadLoop = Thread(target=self.startRun)
            self.threadLoop.start()
        finally:
            self.log.info(
                "saliendo de la tarea iniciada en el botmanager pero queda la thread")

    def startRun(self):
        # creo un nuevo evento para asyncio y asi ejecutar todo de aqui en adelante con async await
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # ejecuto la funcion q quiero
        loop.run_until_complete(self.run_forever())
        loop.close()

    async def iniciar_cuentas(self):
        try:
            cuentas = []
            # mejor las traigo de la db
            cuentasFix = mongo.db.cuentas_fix.find_one(
                {'_id': ObjectId(self.user_id)})
            if cuentasFix:
                self.log.info("si tengo cuentas en este user ")
                cuentas = cuentasFix["cuentas"]
            if len(cuentas) > 0:
                self.log.info(f"si hay cuentas: {cuentas}")
                for cuenta in cuentas:
                    self.log.info(
                        f"iniciando ciuenta: {cuenta['cuenta']} en variable ")
                    self.fix.triangulos[cuenta["cuenta"]] = {}
        except Exception as e:
            self.log.error(f"error al actualizar balance de cuentas: {e}")

    async def run_forever(self):
        try:
            while not self.stop.is_set():
                #   self.log.info("estoy en el ciclo inifito del bot")
                await self.consultar_balances_en_cuentas()
                await asyncio.sleep(60)
            #    self.log.info(f"sin task en la cola del bot: {self.id}")
        except Exception as e:
            self.log.error(
                f"error en el ciclo run_forever del botManual con user_id: {self.user_id} , {e}")
        finally:
            self.log.info(
                f"saliendo del ciclo run_forever del botManual con user_id: {self.user_id}")
                
    async def consultar_balances_en_cuentas(self):
        self.log.info("consultar balances ")
         #primero necesito las cuentas activas 
        try: 
            cuentas = []
            #mejor las traigo de la db 
            cuentasFix = mongo.db.cuentas_fix.find_one({'_id': ObjectId(self.user_id)})
            if cuentasFix:
                self.log.info("si tengo cuentas en este user ")
                cuentas = cuentasFix["cuentas"]
            if len(cuentas)>0:
                self.log.info(f"si hay cuentas: {cuentas}")
                for cuenta in cuentas:
                    self.log.info(f"consultando balance en cuenta: {cuenta['cuenta']}  ")
                    await self.clientR.update_balance_general(cuenta["cuenta"])
        except Exception as e: 
            self.log.error(f"error al actualizar balance de cuentas: {e}")

