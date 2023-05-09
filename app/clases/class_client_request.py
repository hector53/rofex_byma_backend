from app import ObjectId
import logging
import time
from datetime import datetime
import random
from app.fix_application.application import Application
import string
from datetime import datetime
from app.ticks import ticks
from app.clases.class_cola import Cola
import asyncio
import threading
import concurrent.futures
from flask_pymongo import PyMongo

class client_request():
    def __init__(self, fix: Application,  id_bot, cuenta, mongo:PyMongo) -> None:
        self.fix = fix
        self.rest = fix.rest
        self.log = logging.getLogger(f"client_request_{id_bot}")
        self.mongo = mongo
       # self.log.setLevel(logging.INFO)
      #  self.log.addHandler(log.handlers[0])
      #  self.log.propagate = False
        self.id_bot = id_bot
        self.cuenta = cuenta
        self.TiempoExcedido = 15
        self.ticks = ticks
        self.lastOrderID = 0
        self.lastBotID = 0
        self.cola = Cola()
        self.colaOperadas = Cola()
        self.clOrdIdEsperar = {}
        self.codigoSuscribir = ""

    def round05(self, number):
        numero_redondeado = round(number*2)/2
        return numero_redondeado

    # genera un string aleatorio, x default de 10 caracteres
    def randomString(self, stringLength=10):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(stringLength))

    async def esperar_orden_operada(self):
        self.log.info("orden operada en proceso, esperamos.....")
        while True:
            await asyncio.sleep(0.1)
            if len(self.colaOperadas.tareas) == 0:
                break
        self.log.info("ya se proceso la orden operada, continuamos....")
        return

    async def save_or_update_order(self, details):
        try:
            clientOrderID = details["clOrdId"]
            details["ordenBot"] = 0
            details["id_bot"] = self.id_bot
            details["cuenta"] = self.cuenta
            self.log.info(f"entrando a save or update orde r")
            if len(clientOrderID) > 8:
                self.log.info("es ordenBot 1 xq tiene mas de 8 caracteres")
                details["ordenBot"] = 1
            updateOrNew = self.mongo.db.ordenes.find_one_and_replace(
                filter={"clOrdId": details["clOrdId"],
                        "orderId": details["orderId"]},
                replacement=details,
                upsert=True
            )
            if updateOrNew:
                self.log.info("se guardo todo bien")
            else:
                self.log.info("no se guardo bien")
        except Exception as e:
            self.log.error(f"error guardando o actualziadno: {e}")

    async def update_response(self, details, type):
        """
        type:
        0 order new
        1 modify order
        2 cancel orde
        3 filled order
        4 order cancel rejec
        5 order reject message
        """
        clientOrderID = details["clOrdId"]
        await self.save_or_update_order(details)
        if clientOrderID in self.clOrdIdEsperar:
            self.clOrdIdEsperar[clientOrderID]["msg"] = "llego la respuesta"
            self.clOrdIdEsperar[clientOrderID]["data"] = details
            if type < 3:
                self.clOrdIdEsperar[clientOrderID]["status"] = 1

            elif type == 4 or type == 5:
                self.clOrdIdEsperar[clientOrderID]["status"] = 2
                self.log.error(f"error en la orden: {details}")
                self.fix.server_md.broadcast(str(
                    {"msg": f"error en la orden: {str(details['text'])} ", "data": details, "type": "error"}))
            else:
                self.clOrdIdEsperar[clientOrderID]["status"] = 4
        else:
            self.log.info(f"es otro tipod e orden q no estaba esperando ")


    async def tarea_asincrona(self, details):
        self.log.info(f"ejecutando operada como hilo")
        await self.fix.triangulos[self.cuenta][self.id_bot].verificar_orden_operada(details) 

    def ejecutar_tarea(self, details):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.tarea_asincrona(details))
        loop.close()

    async def decode_message_fix(self, details, type):
        self.log.info(
            f"entrando a decode_message_fix: type: {type}, details: {details}")
        if type == 3:
            self.log.info(f"llego order filled o part ")
           # self.colaOperadas.agregar_tarea(details)
            # Crear un nuevo hilo y ejecutar la tarea asincrónica en él
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self.ejecutar_tarea, details)
            # guardar o actualizar en dado caso

            await self.update_response(details, type)
        else:
            await self.update_response(details, type)

    async def getNextOrderID(self, cuenta, id_bot):

        self.lastOrderID += 1
        clOrdId = self.randomString(8)
        self.fix.OrdersIds[clOrdId] = {
            "id_bot": id_bot,
            "cuenta": cuenta,
            "typeOrder": "N",
            "lastOrderID": self.lastOrderID
        }
        return clOrdId

    async def getNextOrderBotID(self, cuenta, id_bot, parent):
        self.lastBotID += 1
        clOrdId = self.randomString(10)
        self.fix.OrdersIds[clOrdId] = {
            "id_bot": id_bot,
            "cuenta": cuenta,
            "typeOrder": "B",
            "lastOrderID": self.lastBotID,
            "parentId": parent
        }
        return clOrdId

    

    async def suscribir_mercado(self, symbols):  # suscribe a mercado
        status = {"status": False}
        self.log.info(f"Suscribir mercado {symbols}, de: {self.id_bot}")
        # necesito un codigo unico para identificar cuando llegue la notificacion de esto
        codigo = str(self.cuenta)+"-"+str(self.id_bot) + \
            "-"+self.randomString(4)
        status = await self.fix.marketDataRequest(entries=[0, 1], symbols=symbols, subscription=1,
                                    depth=5, updateType=0, uniqueID=codigo,id_bot=self.id_bot)
        self.codigoSuscribir = codigo
        return status
       

    async def get_order_limit_by_symbol_side(self, symbol, side, ordStatus="NEW", ordenBot=0):
        try:
            self.log.info(f"symbol: {symbol}, side: {side}")
            parametrosBusqueda = {
                "symbol": symbol,
                "side": side,
                "ordStatus": ordStatus,
                "ordenBot": ordenBot,
                "id_bot": self.id_bot,
                "cuenta": self.cuenta
            }
            query = {
                "$and": [
                    {"ordenBot": ordenBot},
                    {"symbol": symbol},
                    {"side": side},
                    {"id_bot": self.id_bot},
                    {"cuenta": self.cuenta},
                    {"active": True},
                    {
                        "$or": [
                            {"ordStatus": "NEW"},
                            {
                                "$and": [
                                    {"ordStatus": "PARTIALLY FILLED"},
                                    {"leavesQty": {"$gt":0}}
                                ]
                            }
                        ]
                    }
                ]
            }
            self.log.info(f"parametrosBusqueda: {parametrosBusqueda}")
            orden = self.mongo.db.ordenes.find_one(query, {"_id": 0})

            if orden is not None:
                self.log.info("si existe la orden")
                self.log.info(f"la orden es esta: {orden}")
                return {"status": True, "data": orden}
            else:
                self.log.info("no existe orden con esos parametros ")
                return {"status": False, "msg": "no hay orden limit con esos parametros"}
        except Exception as e:
            self.log.error(f"error en get_order_limit_by_symbol_side: {e} ")
            return {"status": False}

    async def es_orden_mia(self, orden, futuro, side, type_order="NEW", orderBot=0):
        response = {"status": False}
        try:
            sideDb = "Buy"
            if side == "OF":
                sideDb = "Sell"
            parametros = {
                "price": orden["price"],
                "leavesQty": orden["size"],
                "symbol": futuro,
                "side": sideDb,
                "ordStatus": type_order,
                "id_bot": self.id_bot,
                "cuenta": self.cuenta
            }
            query = {
                "$and": [
                    {"price": orden["price"]},
                    {"symbol": futuro},
                    {"side": sideDb},
                    {"id_bot": self.id_bot},
                    {"cuenta": self.cuenta},
                    {"active": True},
                    {
                        "$or": [
                            {"ordStatus": "NEW"},
                            {
                                "$and": [
                                    {"ordStatus": "PARTIALLY FILLED"},
                                    {"leavesQty": orden["size"]}
                                ]
                            }
                        ]
                    }
                ]
            }
            self.log.info(f"verificar si esta orden es mia: {parametros}")
            resultado = self.mongo.db.ordenes.find_one(query, {"_id": 0})

            if resultado:
                response = {"status": True, "orden": resultado}
        except Exception as e:
            self.log.error(f"error en es_orden_mia: {e} ")
        return response

    async def esperarRespuesta(self, clOrdId):
        response = {"status": False}
        try:
            self.log.info("esperando respuesta de new order")
            inicio = time.time()
            self.log.info(
                f"self.clOrdIdEsperar[clOrdId]: {self.clOrdIdEsperar[clOrdId]}")
            while True:
                asyncio.sleep(0.1)
                if self.clOrdIdEsperar[clOrdId]["status"] > 0:
                    if self.clOrdIdEsperar[clOrdId]["type"] == 0:
                        self.log.info("llego respuesta de new order")
                    if self.clOrdIdEsperar[clOrdId]["type"] == 1:
                        self.log.info("llego respuesta de modify order")
                    if self.clOrdIdEsperar[clOrdId]["type"] == 2:
                        self.log.info("llego respuesta de cancelar order")
                    response = self.clOrdIdEsperar[clOrdId]
                    del self.clOrdIdEsperar[clOrdId]
                    break
                fin = time.time()
                tiempoEsperado = fin-inicio
                if tiempoEsperado > self.TiempoExcedido:
                    self.log.info("tiempo excedido de new order")
                    response = {
                        "status": 0, "msg": "tiempo excedido, no llego respuesta o algo mas paso"}
                    break
        except Exception as e:
            self.log.error(f"error en esperarRespuesta: {e}")
        return response

    async def esperarRespuestaModify(self, clOrdId):
        try:
            self.log.info("esperando respuesta de modificacion")
            inicio = time.time()
            response = {}
            while True:
                if self.fix.responseModify[clOrdId]["status"] > 0:
                    self.log.info("llego respuesta de modificacion")
                    response = self.fix.responseModify[clOrdId]
                    del self.fix.responseModify[clOrdId]
                    break
                fin = time.time()
                tiempoEsperado = fin-inicio
                if tiempoEsperado > self.TiempoExcedido:
                    self.log.info("tiempo excedido de modificacion")
                    response = {
                        "status": 0, "msg": "tiempo excedido, no llego respuesta o algo mas paso"}
                    break
        except Exception as e:
            self.log.error(f"error en esperarRespuestaModify: {e}")
        return response

    async def modificar_orden_rest(self, orderId, origClOrdId, side, orderType, symbol, quantity, price):
        self.log.info(
            f"modify orden to app {orderId, origClOrdId, side, orderType, symbol, quantity, price, self.id_bot }")
        sideRest = pyRofex.Side.BUY
        if side == 2:
            sideRest = pyRofex.Side.SELL
        # primero necesito cancelar la orden vieja y luego crear una nueva
        # cancelar la orden vieja
        try:
            cancelarVieja = pyRofex.cancel_order(client_order_id=origClOrdId)
            self.log.info(f"cancelarVieja {cancelarVieja}")
            response = {"status": 0, "msg": "no se pudo cancelar la orden"}
            if cancelarVieja["status"] == "OK":
                self.log.info(f"se cancelo la orden vieja")
                self.log.info("actualizar en db la orden vieja")
                updateOrden = await self.update_orden_vieja_db(2, orderId, origClOrdId)
                self.log.info("ahora a crear la nueva orden")
                # crear la nueva orden
                order = pyRofex.send_order(ticker=symbol,  side=sideRest, size=quantity,
                                           price=price,    order_type=pyRofex.OrderType.LIMIT)
                self.log.info(f"nueva_orden_rest to app {order}")
                if order["status"] == "OK":
                    self.log.info(
                        f"se creo la orden, ahora consultar status para guardar en db")
                    statusOrder = pyRofex.get_order_status(
                        order["order"]["clientId"])
                    self.log.info(f"statusOrder {statusOrder}")
                    if statusOrder["status"] == "OK":
                        self.log.info(f"status ok continuamos")
                        if statusOrder["order"]["status"] == "FILLED":
                            self.log.info(f"status filled")
                            response = {
                                "status": 3, "msg": "se cancelo la orden vieja y se creo la nueva y se fue filled"}
                            guardarNew = await self.guardar_orden_nueva_in_db(statusOrder["order"], 3, 0)
                        elif statusOrder["order"]["status"] == "NEW":
                            self.log.info(f"status new")
                            response = {
                                "status": 1, "msg": "se cancelo la orden vieja y se creo la nueva y se quedo en new"}
                            guardarNew = await self.guardar_orden_nueva_in_db(statusOrder["order"], 0, 0)
                        elif statusOrder["order"]["status"] == "REJECTED":
                            self.log.info(f"status rejected")
                            guardarNew = await self.guardar_orden_nueva_in_db(statusOrder["order"], 2, 0)
                            response = {
                                "status": 2, "msg": "se cancelo la orden vieja y se creo la nueva y se quedo en rejected"}
                else:
                    response = {"status": 2,
                                "msg": "no se pudo crear la nueva orden"}
            else:
                response = {"status": 2, "msg": "no se pudo cancelar la orden"}
        except Exception() as e:
            self.log.error(f"error modificar_orden_rest: {e} ")
            response = {"status": 3, "msg": f"error en la api: {e}"}
        return response

    async def get_posiciones(self, cuenta):
        try:
            self.log.info(f"get_posiciones {cuenta}")
            posiciones = self.rest.get_positions(cuenta)
            self.log.info(f"posiciones {posiciones}")
            return posiciones["positions"]
        except Exception as e:
            self.log.error(f"error en get_posiciones: {e}")
            return []

    async def guardar_datos_bb_intradia(self, datos):
        self.log.info("entrando a guardar_datos_bb_intradia")
        response = True
        try:
            fecha_actual = datetime.now()
            datos = self.mongo.db.intradia.insert_one({"id_bot": self.id_bot, "fecha": fecha_actual,
                                                  "book": datos["book"],
                                                  "dataBB": datos["dataBB"],
                                                  "limitsPuntas": datos["limitsPuntas"],
                                                  "bb_ci": datos["bb_ci"],
                                                  "bb_48": datos["bb_48"],
                                                  })
            self.log.info("datos guardados correctamente ")
        except Exception as e:
            self.log.error(f"error guardando los datos intradia: {e}")
            response = False
        return response

    async def get_trades_manual(self, market_id, symbol, desde, hasta):
        try:
            self.log.info("get trades manual")
            trades = self.rest.get_historical_trades(
                market_id, symbol, desde, hasta)
            self.log.info(f"trades {trades}")
            return trades["trades"]
        except Exception as e:
            self.log.error(f"error en get_trades_manual: {e}")
            return []

    async def get_balance(self, account=""):
        try:
            self.log.info(f"get balance {account} ")
            balance = self.rest.get_balance(account)
            self.log.info(f"balance {balance}")
            return balance["accountData"]
        except Exception as e:
            self.log.error(f"error solicitando balance: {e}")
            return 0

    async def update_balance_general(self, cuenta=""):
        if cuenta == "":
            cuenta = self.cuenta
        self.log.info("primero pedir el balance actual")
        balance = await self.get_balance(cuenta)
        self.log.info(f"balance {balance}")
        if balance != 0:
            try:
                self.log.info(f"ahora actualizar la variable ")
                if "balance" in self.fix.triangulos[cuenta]:
                    self.fix.triangulos[cuenta]["balance"] = balance["detailedAccountReports"][
                        "0"]["currencyBalance"]["detailedCurrencyBalance"]
                else:
                    self.fix.triangulos[cuenta]["balance"] = balance["detailedAccountReports"][
                        "0"]["currencyBalance"]["detailedCurrencyBalance"]
                self.log.info(
                    f"nuevo balance es: {self.fix.triangulos[cuenta]['balance']}")
            except Exception as e:
                self.log.error(f"error actualizando balance: {e}")
        else:
            self.log.error("error consultando balance")

    async def get_factor_value(self, symbol, factor=1):
        try:
            self.log.info("get get_factor_value")
            query = {"data.symbol": symbol,   "account_type": "demo"}
            unwind = {"$unwind": "$data"}
            match = {"$match": query}
            proyeccion = {"$replaceRoot": {"newRoot": "$data"}}
            resultados = self.mongo.db.securitys.aggregate(
                [unwind, match, proyeccion])
            symbolResult = list(resultados)
            self.log.info(f"factor result: {symbolResult}")
            if len(symbolResult) > 0:
                factor = symbolResult[0]["factor"]
                self.log.info(f"factor: {factor}")
        except Exception as e:
            self.log.error(f"error en factor: {e}")
        return factor

    async def get_min_increment(self, symbol, min_increment=0.50):
        try:
            self.log.info("get min increment")
            query = {"data.symbol": symbol,   "account_type": "demo"}
            unwind = {"$unwind": "$data"}
            match = {"$match": query}
            proyeccion = {"$replaceRoot": {"newRoot": "$data"}}
            resultados = self.mongo.db.securitys.aggregate(
                [unwind, match, proyeccion])
            symbolResult = list(resultados)
            minIncrement = min_increment
            if len(symbolResult) > 0:
                minIncrement = symbolResult[0]["minPriceIncrement"]
            self.log.info(f"minIncrement: {minIncrement}")
            return minIncrement
        except Exception as e:
            self.log.error(f"error en get_min_increment: {e}")

    async def get_saldo_disponible(self, simbolo):
        self.log.info(f"consultando saldo para el simbolo: {simbolo}")
        # aqui voy a verificar dependiendo del simbolo pero despues
        moneda = "ARS"
        if str(simbolo).endswith("D"):
            moneda = "USD D"
        try:
            saldo = self.fix.balance[self.cuenta][moneda]["available"]
            self.log.info(f"el saldo disponible es: {saldo}")
            return saldo
        except Exception as e:
            self.log.error(
                f"error consultando el saldo disponible arrojamos 0: {e}")
            return 0

    async def get_news_order_db(self):
        arrayOrdenes = []
        try:
            ordenes = self.self.mongo.db.ordenes.find({
                "ordStatus": "NEW",
                "ordenBot": 0,
                "id_bot": self.id_bot,
                "cuenta": self.cuenta
            }, {"_id": 0})
            arrayOrdenes = []
            # [cibi, ciof, 48bi, 48of]
            if ordenes:
                self.log.info("si existen las ordenes limits ")
                ordenes = list(ordenes)
                self.log.info(f"ordenes: {ordenes}")
                ordenCiBi = {}
                ordenCiOf = {}
                orden48Bi = {}
                orden48Of = {}
                for x in ordenes:
                    self.log.info(f"x: {x}")
                    if "ci" in str(x["symbol"]).lower() and x["side"] == "Buy":
                        ordenCiBi = x
                    if "ci" in str(x["symbol"]).lower() and x["side"] == "Sell":
                        ordenCiOf = x
                    if "48" in str(x["symbol"]).lower() and x["side"] == "Buy":
                        orden48Bi = x
                    if "48" in str(x["symbol"]).lower() and x["side"] == "Sell":
                        orden48Of = x
                arrayOrdenes = [ordenCiBi, ordenCiOf, orden48Bi, orden48Of]
        except Exception as e:
            self.log.error(f"error en get_news_order_db: {e}")
        return arrayOrdenes

    async def modificar_orden_manual(self,  orderId, origClOrdId, side, orderType, symbol, quantity, price, sizeViejo):
        try:
            self.log.info(
                f"modify orden to app {orderId, origClOrdId, side, orderType, symbol, quantity, price, self.id_bot }")
        # self.f.responseModify = None
            await self.cancelar_orden_manual(orderId, origClOrdId, side, sizeViejo, symbol)
            response = await self.nueva_orden_manual(symbol, side, quantity, price, orderType)
        except Exception as e:
            self.log.error(f"error en modificar_orden_manual: {e}")
            response = {"status": 4}
        return response

    async def modificar_orden_manual_2(self,  orderId, origClOrdId, side, orderType, symbol, quantity, price):
        try:
            self.log.info(
                f"modify orden to app {orderId, origClOrdId, side, orderType, symbol, quantity, price, self.id_bot }")
        # self.f.responseModify = None
            clOrdId = self.fix.getNextOrderID(self.cuenta, self.id_bot)
            self.fix.responseModify[clOrdId] = {
                "status": 0, "msg": "en espera de respuesta modify"}
            self.fix.orderCancelReplaceRequest(
                clOrdId, orderId, origClOrdId, side, orderType, symbol, quantity, price, self.id_bot)
            response = await self.esperarRespuestaModify(clOrdId)
        except Exception as e:
            self.log.error(f"error en modificar_orden_manual2: {e}")
            response = {"status": 4}
        return response

    async def eliminar_orden_vieja(self, orderId, origClOrdId):
        try:
            self.mongo.db.ordenes.delete_one(
                {"orderId": orderId, "clOrdId": origClOrdId})
            return True
        except Exception as e:
            self.log.error(f"error al eliminar orden vieja: {e}")
            return False

    async def add_new_order_wait(self, symbol, side, quantity,  price, orderType, clOrdId, ordenBot, typeOrderWait):
        details = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "orderType": orderType,
            "ordenBot": ordenBot,
            "clOrdId": clOrdId
        }
        if typeOrderWait == 0:
            self.log.info("es una orden nueva a esperar")
            self.clOrdIdEsperar[clOrdId] = {
                "type": 0, "details": details, "status": 0, "msg": "en espera de respuesta"}

        if typeOrderWait == 1:
            self.log.info("es una orden modify a esperar")
            self.clOrdIdEsperar[clOrdId] = {
                "type": 1, "details": details, "status": 0, "msg": "en espera de respuesta"}

        if typeOrderWait == 2:
            self.log.info("es una orden cancelar a esperar")
            self.clOrdIdEsperar[clOrdId] = {
                "type": 2, "details": details, "status": 0, "msg": "en espera de respuesta"}

        self.log.info(
            f"self.clOrdIdEsperar[clOrdId]: {self.clOrdIdEsperar[clOrdId]}")

    async def nueva_orden_contraria(self, symbol, side, quantity,  price, orderType, clOrdId="", ordenBot=0):
        self.log.info(
            f"nueva_orden to app {symbol, side, quantity,  price, orderType}")
        try:
            # status 0=en espera 1=llego bien respeusta 2=error 3=filled
            if clOrdId == "":
                clOrdId = await self.getNextOrderID(self.cuenta, self.id_bot)
            print("clOrdId", clOrdId)
            self.log.info(f"clOrdId: {clOrdId}")

            await self.add_new_order_wait(symbol, side, quantity,  price, orderType, clOrdId, ordenBot, 0)
            self.fix.newOrderSingle(
                clOrdId, symbol, side, quantity,  price, orderType, self.id_bot, self.cuenta)
            response = await self.esperarRespuesta(clOrdId)
        except Exception as e:
            self.log.error(f"error en nueva_orden: {e}")
        return response
    
    async def nueva_orden(self, symbol, side, quantity,  price, orderType, clOrdId="", ordenBot=0):
        self.log.info(
            f"nueva_orden to app {symbol, side, quantity,  price, orderType}")
        try: 
            if clOrdId == "":
                clOrdId = await self.getNextOrderID(self.cuenta, self.id_bot)
            print("clOrdId", clOrdId)
            self.log.info(f"clOrdId: {clOrdId}")
            order = await self.fix.newOrderSingle(clOrdId, symbol, side, quantity, 
                                                  price, orderType,cuenta=self.cuenta )
            self.log.info(f"order new: {order}")
            if order["llegoRespuesta"]==True:
                self.log.info(f"llego respuesta de nuevaOrden, vamos a validar carias cositas")
                if order["data"]["typeFilled"]==1:
                    self.log.info(f"es una orden filled, osea una rden q se ejecuto market, entonces no la guardo por aqui")
                elif order["data"]["typeFilled"]==0 and order["data"]["reject"]=='true':
                    self.log.info(f"no se creo la orden, arriba dira el motivo")
                else:
                    #no es filled ni tampoco reject, entonces es normal osea se cumplio bien
                    self.log.info(f"no es filled ni tampoco reject, entonces es normal osea se cumplio bien, entonces guardo")
                    await self.save_order_details(order["data"], True)
            else: 
                self.log.info(f"llego respuesta de tiempo limite excedido")
            return order
        except Exception as e: 
            self.log.error(f"error en nueva_orden: {e}")
            response = {"llegoRespuesta": False}
        

    async def save_order_details(self, details, active=False):
        try:
            clientOrderID = details["clOrdId"]
            details["ordenBot"] = 0
            details["id_bot"] = self.id_bot
            details["cuenta"] = self.cuenta
            details["active"] = active
            self.log.info(f"save_order_details")
            if len(clientOrderID) > 8:
                self.log.info("es ordenBot 1 xq tiene mas de 8 caracteres")
                details["ordenBot"] = 1
            saveOrder = self.mongo.db.ordenes.insert_one(
               details
            )
            if saveOrder:
                self.log.info("se guardo todo bien")
            else:
                self.log.info("no se guardo bien")
        except Exception as e:
            self.log.error(f"error guardando o actualziadno: {e}")

    async def nueva_orden_vieja(self, symbol, side, quantity,  price, orderType, clOrdId="", ordenBot=0):
        self.log.info(
            f"nueva_orden to app {symbol, side, quantity,  price, orderType}")
        try:
            # status 0=en espera 1=llego bien respeusta 2=error 3=filled
            if clOrdId == "":
                clOrdId = await self.getNextOrderID(self.cuenta, self.id_bot)
            print("clOrdId", clOrdId)
            self.log.info(f"clOrdId: {clOrdId}")

            await self.add_new_order_wait(symbol, side, quantity,  price, orderType, clOrdId, ordenBot, 0)
            await self.esperar_orden_operada()
            self.fix.newOrderSingle(
                clOrdId, symbol, side, quantity,  price, orderType, self.id_bot, self.cuenta)
            response = await self.esperarRespuesta(clOrdId)
        except Exception as e:
            self.log.error(f"error en nueva_orden: {e}")
            response = {"status": False}
        return response

    async def modificar_orden_size(self, orderId, origClOrdId, side, orderType, symbol, quantity, price):
        self.log.info(
            f"modify orden size to app {orderId, origClOrdId, side, orderType, symbol, quantity, price, self.id_bot }")
       # self.f.responseModify = None
        try:
            clOrdId = await self.getNextOrderID(self.cuenta, self.id_bot)
            order = await self.fix.orderCancelReplaceRequest(
                clOrdId, orderId, origClOrdId, side, orderType, symbol, quantity, price, self.id_bot, self.cuenta)
            if order["llegoRespuesta"] == True:
                self.log.info(f"llego respuesta de modifyOrden, vamos a validar carias cositas")
                if order["data"]["typeFilled"]==1:
                    self.log.info(f"es una orden filled, osea una rden q se ejecuto market, entonces no la guardo por aqui")
                    self.log.info(f"pero si vamos a deshabilitar la vieja")
                    await self.disable_order_status(orderId, origClOrdId)
                elif order["data"]["typeFilled"]==0 and order["data"]["reject"]=='true':
                    self.log.info(f"no se modifico la orden, arriba dira el motivo")
                else:
                    #no es filled ni tampoco reject, entonces es normal osea se cumplio bien
                    self.log.info(f"no es filled ni tampoco reject, entonces es normal osea se cumplio bien, entonces guardo")
                    self.log.info(f"desactivar anterior")
                    await self.disable_order_status(orderId, origClOrdId)
                    await self.save_order_details(order["data"], True)
            response = order
        except Exception as e:
            self.log.error(f"error en modificar: {e}")
            response = {"llegoRespuesta": False}
        return response

    async def modificar_orden(self, orderId, origClOrdId, side, orderType, symbol, quantity, price):
        self.log.info(
            f"entrando a modificar orden pero la que omodifica y cancela {orderId, origClOrdId, side, orderType, symbol, quantity, price, self.id_bot, self.cuenta }")
        try:
            response = await self.cancelar_orden(orderId, origClOrdId, side, quantity,
                                                 symbol)
            if response["llegoRespuesta"] == True:
                response = await self.nueva_orden(symbol, side, quantity, price, orderType)
                return response
        except Exception as e:
            self.log.error(f"error al modificar la orden: {e} ")
            response = {"llegoRespuesta": False}
        return response

    async def esperarRespuestaCancelar(self, clOrdId):
        self.log.info("esperando respuesta de cancelacion")
        inicio = time.time()
        response = {}
        try:

            while True:
                if self.fix.responseCancel[clOrdId]["status"] > 0:
                    self.log.info("llego respuesta de cancelacion")
                    response = self.fix.responseCancel[clOrdId]
                    del self.fix.responseCancel[clOrdId]
                    break
                fin = time.time()
                tiempoEsperado = fin-inicio
                if tiempoEsperado > self.TiempoExcedido:
                    self.log.info("tiempo excedido de cancelacion")
                    response = {
                        "status": 0, "msg": "tiempo excedido, no llego respuesta o algo mas paso"}
                    break
        except Exception as e:
            self.log.error(f"error en esperarRespuestaCancelar: {e}")
        return response

    async def cancelar_orden_rest(self, orderID, OrigClOrdID, side, quantity, symbol):
        try:
            cancel_order = pyRofex.cancel_order(OrigClOrdID)
            self.log.info(f"cancel_order {cancel_order}")
            if cancel_order["status"] == "OK":
                self.log.info(f"se cancelo la orden, ahora actualizar DB")
                cancelarOrdenDb = await self.update_orden_vieja_db(2, orderID, OrigClOrdID)
                response = {"status": 1, "msg": "se cancelo la orden"}
            else:
                response = {"status": 2, "msg": "no se pudo cancelar la orden"}
        except Exception() as e:
            self.log.error(f"error en cancelar_orden_rest: {e}")
            response = {"status": 3, "msg": f"error en la api: {e}"}
        return response

    async def cancelar_orden_manual(self, orderID, OrigClOrdID, side, quantity, symbol):
        try:
            self.log.info(
                f"cancelar orden to app {orderID, OrigClOrdID, side, quantity, symbol, self.id_bot}")
            clOrdId = await self.getNextOrderID(self.cuenta, self.id_bot)
            self.fix.responseCancel[clOrdId] = {
                "status": 0, "msg": "en espera de respuesta"}
            self.fix.orderCancelRequest(
                clOrdId, OrigClOrdID, side, quantity, symbol, self.id_bot, self.cuenta)
            response = await self.esperarRespuestaCancelar(clOrdId)
        except Exception as e:
            self.log.error(f"error en cancelar_orden_manual: {e}")
            response = {"status": 4}
        return response

    async def get_intradia_hoy(self):
        arrayIntradia = []
        try:
            hoy = datetime.today()
            # Obtener la hora de inicio y fin del día de hoy
            hora_inicio = datetime(hoy.year, hoy.month, hoy.day, 0, 0, 0)
            hora_fin = datetime(hoy.year, hoy.month, hoy.day, 23, 59, 59)
            # Buscar documentos por fecha de hoy
            arrayIntradia = list(self.mongo.db.intradia.find(
                {"fecha": {"$gte": hora_inicio, "$lt": hora_fin}, "id_bot": self.id_bot},
                
                ))
        except Exception as e:
            self.log.info(f"error consultando intradia : {e}")
        return arrayIntradia
    
    async def cancelar_orden(self, orderID, OrigClOrdID, side, quantity, symbol):
        self.log.info(
            f"cancelar orden to app {orderID, OrigClOrdID, side, quantity, symbol, self.id_bot, self.cuenta}")
        try: 
            clOrdId = await self.getNextOrderID(self.cuenta, self.id_bot)
            order = await self.fix.orderCancelRequest(
                clOrdId, OrigClOrdID, side, quantity, symbol, self.id_bot, self.cuenta)
            self.log.info(f"order cancel: {order}")
            if order["llegoRespuesta"]==True:
                self.log.info(f"llego respuesta de cancelOrder, vamos a validar carias cositas")
                if order["data"]["reject"]=='true':
                    self.log.info(f"no se cancelo la orden, arriba dira el motivo")
                else:
                    #no es reject, entonces es normal osea se cumplio bien
                    self.log.info(f"no es reject, entonces es normal osea se cumplio bien, entonces guardo")
                    self.log.info(f"desactivar anterior")
                    await self.disable_order_status(orderID, OrigClOrdID)
                    await self.save_order_details(order["data"], False)
            response = order
        except Exception as e: 
            response = {"llegoRespuesta": False}
            self.log.error(f"error cancelando orden: {e}")
        return response
    
    async def disable_order_status(self, orderId, clOrdId):
        try:
            self.log.info(f"entrando a disable order status: {orderId}, {clOrdId}")
            self.mongo.db.ordenes.update_one({
                "clOrdId": clOrdId, 
                "orderId": orderId, 
                "id_bot": self.id_bot, 
                "cuenta": self.cuenta
            }, {'$set': {'active': False }})
            return True
        except Exception as e: 
            self.log.error(f"error en disable order status de orderID: {orderId} clOrdId: {clOrdId}, error: {e}")
            return False

    async def cancelar_orden_vieja(self, orderID, OrigClOrdID, side, quantity, symbol):
        self.log.info(
            f"cancelar orden to app {orderID, OrigClOrdID, side, quantity, symbol, self.id_bot, self.cuenta}")
        try:
            clOrdId = await self.getNextOrderID(self.cuenta, self.id_bot)
            await self.add_new_order_wait(symbol, side, quantity,  0, 2, clOrdId, 0, 2)
            await self.esperar_orden_operada()
            self.fix.orderCancelRequest(
                clOrdId, OrigClOrdID, side, quantity, symbol, self.id_bot, self.cuenta)
            response = await self.esperarRespuesta(clOrdId)
            if response["status"] == 1:
                # borrar vieja
                self.log.info(f"borrar orden vieja ")
                ordenVieja = await self.eliminar_orden_vieja(orderID, OrigClOrdID)
        except Exception as e:
            response = {"status": False}
            self.log.error(f"error cancelando orden: {e}")

        return response

   # async def buscar_orden_book(orderID, OrigClOrdID):

    async def cancelar_orden_haberla(self, futuro, side):
        self.log.info(f"cancelar orden haberla {futuro, side}")
        response = {"status": False}
        try:
            sideDb = "Buy"
            if side == 2:
                sideDb = "Sell"
            xa = self.mongo.db.ordenes.find_one({
                "ordStatus": "NEW",
                "ordenBot": 0,
                "symbol": futuro,
                "side": sideDb,
                "id_bot": self.id_bot,
                "cuenta": self.cuenta, 
                "active": True
            }, {"_id": 0})
            if xa:
                self.log.info(f"cancelar orden haberla {xa}")
                cancelarOrden = await self.cancelar_orden(orderID=xa["orderId"], OrigClOrdID=xa["clOrdId"], side=side, quantity=xa["leavesQty"], symbol=futuro)
                self.log.info(f"cancelar orden haberla {cancelarOrden}")
                response = {"status": True, "response": cancelarOrden}
        except Exception as e:
            self.log.error(f"error en cancelar_orden_haberla: {e}")
        return response

    async def nueva_orden_rest(self, symbol, side, quantity,  price, orderType):
        self.log.info(
            f"nueva_orden_rest to app {symbol, side, quantity,  price, orderType}")
        sideRest = pyRofex.Side.BUY
        if side == 2:
            sideRest = pyRofex.Side.SELL
        clOrdId = await self.getNextOrderID(self.cuenta, self.id_bot)
        try:
            order = pyRofex.send_order(ticker=symbol,  side=sideRest, size=quantity,
                                       price=price,    order_type=pyRofex.OrderType.LIMIT,)
            self.log.info(f"nueva_orden_rest to app {order}")
            response = {"status": 0, "msg": "en espera de respuesta"}
            if order["status"] == "OK":
                self.log.info(
                    f"se creo la orden, ahora consultar status para guardar en db")
                statusOrder = pyRofex.get_order_status(
                    order["order"]["clientId"])
                self.log.info(f"statusOrder {statusOrder}")
                if statusOrder["status"] == "OK":
                    response = {"status": 1, "msg": "se creo la orden",
                                "order": statusOrder["order"]}
                    self.log.info(f"status ok continuamos")
                    if statusOrder["order"]["status"] == "FILLED":
                        self.log.info(f"status filled")
                        guardarNew = await self.guardar_orden_nueva_in_db(statusOrder["order"], 3, 0)
                    elif statusOrder["order"]["status"] == "NEW":
                        self.log.info(f"status new")
                        guardarNew = await self.guardar_orden_nueva_in_db(statusOrder["order"], 0, 0)
                    elif statusOrder["order"]["status"] == "REJECTED":
                        self.log.info(f"status rejected")
                        guardarNew = await self.guardar_orden_nueva_in_db(statusOrder["order"], 2, 0)
            else:
                response = {"status": 2, "msg": "no se pudo crear la orden"}
        except Exception() as e:
            self.log.error(f"error en nueva_orden_rest: {e}")
            response = {"status": 3, "msg": f"error en la api: {e}"}
        return response

    async def mass_cancel_request(self, marketSegment):
        try:
            self.log.info(f"mass_cancel_request to app")
            self.fix.orderMassCancelRequest(marketSegment=marketSegment)
            time.sleep(5)
            return {"status": True}
        except Exception as e:
            return {"status": False}

    async def mass_status_request(self, securityStatus, MassStatusReqType=7, account=""):
        response = {"status": False}
        try:
            self.fix.massStatusArray = []
            self.fix.massStatusArrayReal = []
            self.log.info(
                f"mass_status_request to app {securityStatus, MassStatusReqType}")
            self.fix.orderMassStatusRequest(
                securityStatus, MassStatusReqType, account)
            response = await self.esperarRespuestaMassStatus()
            print("response mass status", response)
            self.fix.responseMassStatus = None
        except Exception as e:
            self.log.error(f"error en mass status requests: {e}")
        return response

    async def esperarRespuestaMassStatus(self):
        response = {"status": False}
        try:
            self.log.info(f"esperarRespuestaMassStatus")
            inicio = time.time()

            while True:
                if self.fix.responseMassStatus != None:
                    self.log.info("llego respuesta de mass status")
                    response = self.fix.responseMassStatus
                    break
                fin = time.time()
                tiempoEsperado = fin-inicio
                if len(self.fix.massStatusArray) == 0 and tiempoEsperado > 3:
                    self.log.info("tiempo excedido de mass status ")
                    response = {
                        "status": False, "msg": "tiempo excedido, no llego respuesta o algo mas paso"}
                    break
        except Exception as e:
            self.log.error(f"error en esperarRespuestaMassStatus: {e} ")
        return response

    async def nueva_orden_manual(self, symbol, side, quantity,  price, orderType):
        self.log.info(
            f"nueva_orden manual to app {symbol, side, quantity,  price, orderType}")
        try:
            clOrdId = await self.getNextOrderID(self.cuenta, self.id_bot)
            self.fix.responseNewOrder[clOrdId] = {
                "status": 0, "msg": "en espera de respuesta"}
            self.fix.newOrderSingle(
                clOrdId, symbol, side, quantity,  price, orderType, self.id_bot, self.cuenta)
            response = await self.esperarRespuestaNeworder(clOrdId)
            if response["status"] == 2:
                self.log.error(
                    f"error en nueva orden: {response['data']['text']}")
        except Exception as e:
            self.log.error(f"error en nueva_orden_manual: {e}")
            response = {"status": 4}
        return response

    async def get_order_pendiente_by_clOrdId(self, clOrdId):
        self.log.info(f"get_order_pendiente_by_clOrdId")
        try:
            x = self.mongo.db.ordenes.find_one({
                "clOrdId": clOrdId,
                "ordStatus": "NEW",
                "id_bot": self.id_bot,
                "cuenta": self.cuenta
            }, {"_id": 0})
            self.log.info(f"get_order_pendiente_by_clOrdId {clOrdId}")
            if x:
                self.log.info("si existe la orden")
                self.log.info(f"la orden es esta: {x}")
                return {"status": True, "data": x}
            else:
                return {"status": False, "msg": "no hay orden limit con esos parametros"}
        except Exception as e:
            self.log.error(f"error en get_order_pendiente_by_clOrdId {e} ")
            return {"status": False}

    async def guardar_orden_nueva_in_db(self, orden, statusOrder, ordenBot):
        self.log.info(
            f"guardar orden nueva in db {orden, statusOrder, ordenBot, self.id_bot}")

        ordenGuardar = orden
        ordenGuardar["ordenBot"] = ordenBot
        ordenGuardar["id_bot"] = self.id_bot
        ordenGuardar["cuenta"] = self.cuenta
        try:
            ordenNew = self.mongo.db.ordenes.insert_one(ordenGuardar)
            if ordenNew.acknowledged:
                self.log.info(f"se guardo la orden nueva {ordenNew}")
                return {"status": True, "id": str(ordenNew.inserted_id)}
            else:
                self.log.info(f"no se guardo la orden nueva {ordenNew}")
                self.log.info("no se guardo la orden ")
                return {"status": False}
        except Exception as e:
            self.log.error(f"error al guardar la nueva orden: {e}")
            return {"status": False}

    async def verificar_ordenes_futuro(self, futuro, side, book):
        # con esto voy a saber si puedo operar en este futuro, para eso necesito el valor del primero del book
        # o el valor que puedo usar que no sea mi propia orden
        # si la posicion 0 del book no es mia , entonces necesito eso, por lo tanto guardo indice y retorno True

        """
        estoy validando de esta manera horita con lo nuevo q estoy creando 
        estoy en ci bi 
        response = {
                "indiceBookUsar": None, 
                "primeraOrden": False, 
                "puedoOperar": False,
            }
        verifico 48 bi 
        recorro book 
             si estoy de primero paso primeraOrden a true y rompo ciclo
             else sigo recorriendo , si hay mas ordenes coloco el indice a usar y rompo ciclo 
             entonces ahi tengo mis dos opciones 
             puedoOperar sera true cuando no este de primero y tenga ordenes del book q pueda comer 

        """
        response = {
            "indiceBookUsar": None,
            "primeraOrden": False,
            "puedoOperar": False,
        }
        self.log.info(
            f"Verificando órdenes en futuro {futuro} con side {side}")
        try:
            if not book:
                self.log.info(
                    "No hay órdenes en este futuro, retornando False")
                return response
            ordenes_book = book
            ordenesMias = 0

            for i in range(len(ordenes_book)):
                self.log.info(
                    f"i={i}, verificar si : {ordenes_book[i]}, es ,mia")
                mia = await self.es_orden_mia(ordenes_book[i], futuro, side)
                if mia["status"] == True:
                    if i == 0:
                        response["primeraOrden"] = True
                        break
                    self.log.info(f"es mia")
                    if mia["orden"] == 1:
                        self.log.info(f"es mia y es ordenBot pegada")
                        ordenesMias += 1
                    else:
                        self.log.info(f"es mia y es orden limit normal")
                        ordenesMias += 1
                else:
                    self.log.info(f"no es mia, guardando indice")
                    self.log.info(
                        f"Guardando índice para futuro {futuro} y side {side}, indice: {i}")
                    response["puedoOperar"] = True
                    response["indiceBookUsar"] = i
                    break

        except Exception as e:
            self.log.error(f"error en verificar_ordenes_futuro: {e}")

        return response

# -------------operada ------------------#

    async def update_size_orden_vieja(self, id, ordenNueva):
        try:

            updateOrden = self.mongo.db.ordenes.update_one(
                {'_id': ObjectId(id)}, {'$set': {'leavesQty': ordenNueva["leavesQty"],
                                                 "cumQty": ordenNueva["cumQty"],
                                                 "lastQty": ordenNueva["lastQty"]
                                                 }})
            return updateOrden
        except Exception as e:
            self.log.error(f"error en update_size_orden_vieja: {e}")
            return None

    async def get_tick_value(self, symbol):
        try:
            symbol = str(symbol).replace(" ", "")
            symbol = symbol.split("-")
            symbolOnly = symbol[2]
            return self.ticks[symbolOnly]
        except Exception as e:
            self.log.error(f"error en tick: {e}")
            minIncrement = await self.get_min_increment(symbol)
            return minIncrement

    async def actualizar_order_by_change(self, orderID, ordenNueva, ordenBot=0):
        time.sleep(1)
        self.log.info(f"actualizar_order_by_change: {ordenNueva}")
        try:
            # entonces si llega una filled
            # cmparo con lastqty y verifico si la cantidad es la misma entonces la paso la padre a filled completa
            # guardo esta orden para log y actualizo la padre
            # buscar orden vieja en db
            orderVieja = self.mongo.db.ordenes.find_one({
                "orderId": orderID,
                "id_bot": self.id_bot,
                "cuenta": self.cuenta
            })
            leavesQtyNueva = ordenNueva["leavesQty"]
            if orderVieja:
                orderVieja["_id"] = str(orderVieja["_id"])
                leavesQtyVieja = orderVieja["leavesQty"]

                cumQtyNueva = ordenNueva["lastQty"]
                orderBot = orderVieja["ordenBot"]
                # si la orden es del bot
                newOrder = await self.guardar_orden_nueva_in_db(ordenNueva, 1, orderBot)
                if leavesQtyNueva == 0:
                    del self.fix.OrdersIds[ordenNueva["clOrdId"]]
                    self.log.info("la orden se ejecuto en su totalidad  ")
                    ordenVieja = await self.eliminar_orden_vieja(orderID, orderVieja["clOrdId"])
                    self.log.info(
                        "guardamos orden nueva como filled y vieja borrada")
                else:
                    # actualizar size orden vieja
                    ordenVieja = await self.update_size_orden_vieja(orderVieja["_id"], ordenNueva)

            else:
                self.log.info(
                    "es una orden nueva q se ejecuto market guardar como nueva ")
                if leavesQtyNueva == 0:
                    del self.fix.OrdersIds[ordenNueva["clOrdId"]]
                newOrder = await self.guardar_orden_nueva_in_db(ordenNueva, 1, ordenBot)
        except Exception as e:
            self.log.error(f"error actualizar_order_by_change: {e}")
        return 1
