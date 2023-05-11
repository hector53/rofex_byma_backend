from app.fix_application.application import Application
import quickfix as fix
from threading import Thread
import asyncio
from app.clases.botManager import botManager
from app.fix_application.fixMsgManager import fixMsgManager
import queue
import logging
import gc
from threading import Thread

class FixMsgQueue:
    def __init__(self, id):
        self.id = id
        self.message_queue = asyncio.Queue()
        self.log = logging.getLogger(id)
        self.log.info(f"id: {self.id}")
        self.task = None

    async def start(self):
        self.log.info(f"estoy en el ciclo start")
        try:
            while True:
                self.log.info("ciclo infinito")
                if not self.message_queue.empty():
                    task = await self.message_queue.get()
                    message = task["message"]
                    session = task["session"]
                    await self.process_message(message, session)
                    self.message_queue.task_done()
                await asyncio.sleep(0.1)
        except Exception as e:
            # Manejar la excepción adecuadamente
            self.log.info(f"Se ha producido una excepción: {e}")
        finally: 
            self.log.error(f"se cerro el ciclo")

    async def run(self):
        try:
            task = asyncio.create_task(self.start())
            # Esperar a que la tarea asincrónica termine y devuelva su resultado
            response = await task
            return response
        except Exception as e:
            self.log.error("error en run")
        finally:
            self.log.error("error se cerro aqui")

    def stop(self):
        # Detener la tarea creada
        if self.task:
            self.task.cancel()
            self.task = None
    
    async def process_message(self, message, session):
        self.log.info("aqui vamos a procesar el mensaje de fix ")
        # Decode the message here
       # decoded_message = decode_message(message)
        # Send the decoded message to another class
       # other_class.send_message(decoded_message)
        # Delete the decoded message to free up memory
       # del decoded_message
        #gc.collect() # Run the garbage collector to free up memory     

#class main para quickfix 
class MainTask():
    def __init__(self, config_file, market, user, passwd, account, target, server_md, accountFixId):
        self.target = target
        self.market = market
        self.user = user
        self.passwd = passwd
        self.account = account
        self.accountFixId = accountFixId
        self.settings = config_file
        self.threadFix = None
        self.message_queue = asyncio.Queue()
        self.application = Application(self.market, self.user, self.passwd, self.account, self.message_queue)
        self.botManager = botManager()
        self.log = logging.getLogger("MainFix")
        self.application.server_md = server_md
        self.storefactory = fix.FileStoreFactory(config_file)
        self.logfactory = fix.FileLogFactory(config_file)
        self.initiator = fix.SocketInitiator(self.application, self.storefactory, self.settings, self.logfactory)
        self.threadCola = None
        self.stopCola = asyncio.Event()
        self.taskToCancel = None
        self.threadBalance = None
    
    async def checkLoggedOn(self):
        self.log.info(f"entrando a checklogon in hilo")
        while self.application.sessions[self.target]['connected']==None:
            await asyncio.sleep(0.1)
        self.log.info(f"saliendo a checklogon")
        return self.application.sessions[self.target]['connected']

    async def check_logged_on(self):
        task = asyncio.create_task(self.checkLoggedOn())
        # Esperar a que la tarea asincrónica termine y devuelva su resultado
        response = await task
        return response
    
    async def run(self):
        try:
            self.threadFix = Thread(target=self.initiator.start)
            self.threadFix.start()
            self.threadCola = Thread(target=self.startCola)
            self.threadCola.start()
            self.threadBalance = Thread(target=self.startLoopBalance)
            self.threadBalance.start()
        finally:
            self.log.error("se cerro el run d ela tarea main task")
        
    def startLoopBalance(self):
        loop = asyncio.new_event_loop()# creo un nuevo evento para asyncio y asi ejecutar todo de aqui en adelante con async await 
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.run_forever_balance())#ejecuto la funcion q quiero
        loop.close()
    
    def startCola(self):
        loop3 = asyncio.new_event_loop()# creo un nuevo evento para asyncio y asi ejecutar todo de aqui en adelante con async await 
        asyncio.set_event_loop(loop3)
        loop3.run_until_complete(self.run_forever())#ejecuto la funcion q quiero
        loop3.close()

    async def run_forever_balance(self):
        self.log.info(f"estoy en el ciclo run_forever_balance")
        try:
            while not self.stopCola.is_set():
                await self.consultar_balances_en_cuentas()
                await asyncio.sleep(60)
        except Exception as e:
            # Manejar la excepción adecuadamente
            self.log.info(f"Se ha producido una excepción: {e}")
        finally: 
            self.log.error(f"se cerro el ciclo del balance")

    async def consultar_balances_en_cuentas(self):
        from app import mongo
        from bson import ObjectId
        self.log.info("consultar balances ")
         #primero necesito las cuentas activas 
        try: 
            cuentas = []
            #mejor las traigo de la db 
            cuentasFix = mongo.db.cuentas_fix.find_one({'_id': ObjectId(self.accountFixId)})
            if cuentasFix:
                self.log.info("si tengo cuentas en este user ")
                cuentas = cuentasFix["cuentas"]
            if len(cuentas)>0:
                self.log.info(f"si hay cuentas: {cuentas}")
                for cuenta in cuentas:
                    self.log.info(f"consultando balance en cuenta: {cuenta['cuenta']}  ")
                    await self.update_balance_general(cuenta["cuenta"])
        except Exception as e: 
            self.log.error(f"error al actualizar balance de cuentas: {e}")

    async def update_balance_general(self, cuenta=""):
        if cuenta == "":
            cuenta = self.cuenta
        self.log.info("primero pedir el balance actual")
        balance = await self.get_balance(cuenta)
        self.log.info(f"balance {balance}")
        if balance != 0:
            try:
                self.log.info(f"ahora actualizar la variable ")
                self.application.balance[cuenta] =  balance["detailedAccountReports"][
                        "0"]["currencyBalance"]["detailedCurrencyBalance"]
                self.log.info(
                    f"nuevo balance es: {self.application.balance[cuenta]}")
            except Exception as e:
                self.log.error(f"error actualizando balance: {e}")
        else:
            self.log.error("error consultando balance")

    async def run_forever(self):
        self.log.info(f"estoy en el ciclo start")
        try:
            while not self.stopCola.is_set():
             #   self.log.info("ciclo infinito")
                if not self.message_queue.empty():
                    task = await self.message_queue.get()
                    asyncio.create_task(self.process_message(task))
                    self.message_queue.task_done()
                await asyncio.sleep(0.01)
        except Exception as e:
            # Manejar la excepción adecuadamente
            self.log.info(f"Se ha producido una excepción: {e}")
        finally: 
            self.log.error(f"se cerro el ciclo de cola en main task")

    async def stopColaFix(self):
        self.stopCola.set()

    async def update_tickers_bot(self, task):
        id_bot = task["id_bot"]
        self.log.info(f"""procesando tarea de enviar actualizacion de book al id_bot: {id_bot}, 
        aqui agregamos tarea a la cola del bot para verificar puntas, pero primero actualizamos tickers en el bot """)
        #task = {"type": 0, "symbolTicker": symbolTicker, "marketData": data["marketData"], 
                    #   "id_bot": self.suscripcionId[MDReqID]["id_bot"] }
        self.log.info(f"bot data: {self.botManager.main_tasks[id_bot].botData}")
        self.log.info(f"self.botManager.tasks: {self.botManager.tasks}")
        self.log.info(f"self.botManager.main_tasks: {self.botManager.main_tasks}")            
        symbolTicker = task["symbolTicker"]
        marketData = task["marketData"]
        if id_bot in self.botManager.main_tasks:
            self.log.info(f"tickers antes: {self.botManager.main_tasks[id_bot]._tickers[symbolTicker]}")
            self.botManager.main_tasks[id_bot]._tickers[symbolTicker] = marketData
            self.log.info(f"tickers despues: {self.botManager.main_tasks[id_bot]._tickers[symbolTicker]}")
            self.log.info(f"ahora si agregamos tarea al bot para verificar puntas")
            if self.botManager.main_tasks[id_bot].botData["botIniciado"]==True and self.botManager.main_tasks[id_bot].botData["soloEscucharMercado"]==False:
                await self.botManager.main_tasks[id_bot].add_task(task)
            self.log.info(f"listo tarea agregada al bot")
            self.log.info(f"self.botManager.tasks: {self.botManager.tasks}")
            self.log.info(f"self.botManager.main_tasks: {self.botManager.main_tasks}") 
        else:
            self.log.error("el bot no esta en el botManager quizas ya se detuvo")
       # await asyncio.sleep(0.1)

    async def process_message(self, task):
        self.log.info(f"procesando mensaje de fix .....: {task}")
        if task["type"]==0:
            await self.update_tickers_bot(task)

        if task["type"]==1: 
            self.log.info(f"procesando task orden filled {task}")
            #task = {"type": 1,  "id_bot": id_bot, "typeOrder": typeOrder, "cuenta": accountFixMsg, "details": details }
            #es una orden filled o partial
            #pausar cola de bot
            id_bot = task["id_bot"]
            details = task["details"]
            typeOrder = task["typeOrder"]
            lastOrderID = task["lastOrderID"]
            if typeOrder == "N":
                self.log.info(f"pausar cola del bot :{self.botManager.main_tasks[id_bot].paused}")
                self.log.info(f"contadorOperada: {self.botManager.main_tasks[id_bot].contadorOperada}")
                if self.botManager.main_tasks[id_bot].contadorOperada == 0:
                    self.log.info(f"contador = 0, pongo pausa")
                    await self.botManager.main_tasks[id_bot].pause()
                self.botManager.main_tasks[id_bot].contadorOperada+=1
                self.log.info(f"paused:{self.botManager.main_tasks[id_bot].paused}")
                self.log.info(f"mandar a verificar orden para q opere contraria, hacerlo en nueva hilo")
                taskOperada = asyncio.create_task(self.botManager.main_tasks[id_bot].verificar_orden_operada(details,typeOrder, lastOrderID))
                response = await taskOperada
                self.log.info(f"luego q termino de verificar la operada y operar la contraria quito el pause")
                self.log.info(f"paused:{self.botManager.main_tasks[id_bot].paused}")
                self.botManager.main_tasks[id_bot].contadorOperada-=1
                self.log.info(f"contadorOperada: {self.botManager.main_tasks[id_bot].contadorOperada}")
                if self.botManager.main_tasks[id_bot].contadorOperada == 0:
                    self.log.info(f"contador = 0, pongo resume")
                    await self.botManager.main_tasks[id_bot].resume()
                self.log.info(f"paused:{self.botManager.main_tasks[id_bot].paused}")
            elif typeOrder == "B":
                self.log.info(f"esta es una contraria, aqui ya denbe estar en pause solo mando a verificar en un nuevo hilo")
                taskOperada = asyncio.create_task(self.botManager.main_tasks[id_bot].verificar_orden_operada(details,typeOrder, lastOrderID))
                self.log.info(f"listo aqui ya se verifico la contraria ")
                response = await taskOperada



      #  await asyncio.sleep(1)

    async def get_balance(self, account=""):
        try:
            self.log.info(f"get balance {account} ")
            balance = self.application.rest.get_balance(account)
            self.log.info(f"balance {balance}")
            return balance["accountData"]
        except Exception as e:
            self.log.error(f"error solicitando balance: {e}")
            return 0