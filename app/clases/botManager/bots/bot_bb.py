from app.clases.botManager.taskSeqManager import taskSeqManager
import asyncio
from collections import defaultdict
from typing import DefaultDict,  Dict
import logging
from app.clases.class_client_request import client_request
from threading import Thread
import datetime
import statistics


class botBB(taskSeqManager):
    def __init__(self, bymaCI, byma48h, minimum_arbitrage_rate, maximum_arbitrage_rate, f, id_bot, cuenta, mongo):
        super().__init__()
        self.minimum_arbitrage_rate = float(minimum_arbitrage_rate)
        self.maximum_arbitrage_rate = float(maximum_arbitrage_rate)
        self.fix = f
        # diccionario de diccionarios donde estaran los datos del book suscritos
        self._tickers: DefaultDict[str, Dict[str, float]] = defaultdict(dict)
        self.name = f"bot_{id_bot}"
        self.id = id_bot
        self.log = logging.getLogger(f"botBB{id_bot}")
        # instancia de la clase client_request
        self.clientR = client_request(f, id_bot, cuenta, mongo)
        self.bb_ci = []
        self.bb_48 = []
        self.capture_datos_bb = {}
        self.bookBB = []
        self.dataBB = []
        self.limitsBB = []
        self.upperBB = None
        self.lowerBB = None
        self.threadCola = None
        self.threadBB = None
        self.contadorOperada = 0
        self.botData = {  # diccionario con las variables q el bot usará
            # lo uso para guardar el id en db y asi poder seguir las ordenes de cada bot
            "id_bot": id_bot,
            "cuenta": cuenta,
            "posiciones": {bymaCI: {"BI": 0, "OF": 0}, byma48h: {"BI": 0, "OF": 0}},
            "detener": False,  # la uso para detener el bot
            # la uso para en el dashboard saber q el bot ya inicio correctamente o no
            "botIniciado": None,
            "bymaCI": bymaCI,  # los valores de los book que se van a suscribir
            "byma48h": byma48h,  # los valores de los book que se van a suscribir
            "ordenOperada": 0,  # la uso para saber si ya se opero una orden
            "llegoTickers": False,  # la uso para saber si ya llegaron los tickers
            "bookChangeTime": None,  # la uso para marcar el tiempo despues de un cambio de mercado,
            "symbols2": [bymaCI, byma48h],
            "sizeOnly1": True,
            "pegados": [],
            "contadorTareas": 0,
            # "ordenesBot": [],
            "idPegadas": 0,
            "editandoBot": False,
            "type_side": 0,
            "sizeMax": 1,
            "soloEscucharMercado": False,
            "ruedasCompletadas": 0,
            "ruedaA": {
                "ordenes": [],
                "sizeDisponible": 0,
            },
            "ruedaB": {
                "ordenes": [],
                "sizeDisponible": 0,
            },
            "minPriceIncrement": 0.05,
            "factor": 0.1,
            "limitsBB": {
                "bi_ci": None,
                "of_ci": None,
                "bi_48": None,
                "of_48": None
            }
        }

    async def guardar_posiciones(self):
        try:
            posiciones = await self.clientR.get_posiciones(self.botData["cuenta"])
            self.log.info("voy a guardar posiciones")
            for posicion in posiciones:
                if posicion["tradingSymbol"] == self.botData["bymaCI"]:
                    self.botData["posiciones"][self.botData["bymaCI"]
                                               ]["BI"] = posicion["buySize"]
                    self.botData["posiciones"][self.botData["bymaCI"]
                                               ]["OF"] = posicion["sellSize"]
                    if posicion["tradingSymbol"] == self.botData["byma48h"]:
                        self.botData["posiciones"][self.botData["byma48h"]
                                                   ]["BI"] = posicion["buySize"]
                        self.botData["posiciones"][self.botData["byma48h"]
                                                   ]["OF"] = posicion["sellSize"]
        except Exception as e:
            self.log.error(f"error guardando posiciones: {e}")

    async def tareas_de_inicio(self):
        self.log.info(f"ejecutando bot id: {self.id} ")
        try:
            self.log.info(
                "primero voy a guardar las tenencias actuales en mi variable")
            await self.guardar_posiciones()
            self.log.info("segundo lo del minIncremente")
            self.botData["minPriceIncrement"] = await self.clientR.get_tick_value(self.botData["bymaCI"])
            self.botData["factor"] = await self.clientR.get_factor_value(self.botData["bymaCI"])
            self.log.info(f"tercero suscribir al mercado ")
            suscribir = await self.clientR.suscribir_mercado([self.botData["bymaCI"], self.botData["byma48h"]])
            if suscribir["status"] == True:
                self.log.info("suscribir mercado ok")
                self.botData["botIniciado"] = True
                self.log.info(
                    f"antes de iniciar la cola, voy a agregar 1 tarea inicial verificar puntas")
                self.log.info(
                    "bot iniciado ok, ahora si iniciamos la cola de tareas")
                await self.add_task({"type": 0})
                return True
            else:
                self.log.info("no se pudo suscribir al mercado")
                self.botData["botIniciado"] = False
                return False
        except Exception as e:
            self.log.error(f"error creando tareas iniciales: {e}")
            return False

    async def operar_con_bb(self):
        try:
            # await self.clientR.esperar_orden_operada()
            self.log.info("entrando a operar con bb")
            # necesito captura de el last q invetamos de ci y 48
            # necesito las 4 puntas del book guardarlas
            symbolCi = self.botData["bymaCI"]
            symbol48 = self.botData["byma48h"]
            price_ci_bi = self._tickers[symbolCi]["BI"][0]["price"]
            price_ci_of = self._tickers[symbolCi]["OF"][0]["price"]
            price_48_bi = self._tickers[symbol48]["BI"][0]["price"]
            price_48_of = self._tickers[symbol48]["OF"][0]["price"]
            self.log.info(f"price_ci_bi: {price_ci_bi}")
            self.log.info(f"price_ci_of: {price_ci_of}")
            self.log.info(f"price_48_bi: {price_48_bi}")
            self.log.info(f"price_48_of: {price_48_of}")

            # aqui traigo de la db estos datos
            bbDataUL = await self.clientR.get_intradia_hoy()

            if self.botData["ordenOperada"] > 0:
                return
            bb_ci_actual = (price_ci_bi + price_ci_of) / 2
            bb_48_actual = (price_48_bi + price_48_of) / 2
            self.log.info(f"bb_ci: {bb_ci_actual}")
            self.log.info(f"bb_48: {bb_48_actual}")
            bb_ci_lista = []
            bb_48_lista = []
            if len(bbDataUL) > 0:
                for x in bbDataUL:
                    bb_ci_lista.append(x["bb_ci"])
                    bb_48_lista.append(x["bb_48"])
            else:
                bb_ci_lista.append(bb_ci_actual)
                bb_48_lista.append(bb_48_actual)
            bb_ci_lista.append(bb_ci_actual)
            bb_48_lista.append(bb_48_actual)
         #   self.bb_ci.append(bb_ci_actual)
          #  self.bb_48.append(bb_48_actual)
            self.log.info(f"bb_ci_lista: {bb_ci_lista}")
            self.log.info(f"bb_48_lista: {bb_48_lista}")

            asset_price_48h = bb_48_lista[-180:]
            asset_price_CI = bb_ci_lista[-180:]
            self.log.info(f"asset_price_48h: {asset_price_48h}")
            self.log.info(f"asset_price_CI: {asset_price_CI}")
            current_date = datetime.datetime.now().date()
            self.log.info(f"current_date: {current_date}")
            next_day = self.next_business_day(current_date)
            self.log.info(f"next_day: {next_day}")
            dias_restantes = next_day
            self.log.info(f"dias_restantes: {dias_restantes}")
            close_prices = [((asset_price_48h[i] - asset_price_CI[i]) / asset_price_CI[i])
                            * 365 / (dias_restantes + 0) for i in range(len(asset_price_48h))]
            self.log.info(f"close_prices: {close_prices}")

            if len(close_prices) < 2:
                self.log.info(f"close prices < 2")
                return
            mean = statistics.mean(close_prices)
            std = statistics.stdev(close_prices)
            upper = mean + (std * self.maximum_arbitrage_rate)
            self.upperBB = upper
            lower = mean - (std * self.minimum_arbitrage_rate)
            self.lowerBB = lower
            self.log.info(f"upper: {upper}")
            self.log.info(f"lower: {lower}")
            latest_asset_price_48h = asset_price_48h[-1]
            latest_asset_price_ci = asset_price_CI[-1]
            self.log.info(f"latest_asset_price_48h: {latest_asset_price_48h}")
            self.log.info(f"latest_asset_price_ci: {latest_asset_price_ci}")
            # limit BID CI: Escuchas BID 48h y ASK CI para el calculo
            latest_limit_asset_price_CI_BID = price_48_bi - \
                (upper * (dias_restantes + 0) / 365) * price_ci_of
            # limit ASK CI: Escuchas ASK 48h y BID CI para el calculo
            latest_limit_asset_price_CI_ASK = price_48_of - \
                (lower * (dias_restantes + 0) / 365) * price_ci_bi
            self.log.info(
                f"New limit CI: BID estrategia: {latest_limit_asset_price_CI_BID}")
            self.log.info(
                f"New limit CI: ASK estrategia: {latest_limit_asset_price_CI_ASK}")
            # limit BID 48h: Escuchas BID CI y ASK 48h para el calculo. Aca no te pide 48h igualmente.
            latest_limit_asset_price_48h_BID = price_ci_bi + \
                (lower * (dias_restantes + 0) * price_ci_bi / 365)
            # limit ASK 48h: Escuchas ASK CI y BID 48h para el calculo. Aca no te pide 48h igualmente.
            latest_limit_asset_price_48h_ASK = price_ci_of + \
                (upper * (dias_restantes + 0) * price_ci_of / 365)
            self.log.info(
                f"New limit 48: BID estrategia: {latest_limit_asset_price_48h_BID}")
            self.log.info(
                f"New limit 48: ASK estrategia: {latest_limit_asset_price_48h_ASK}")
            self.log.info("----------datos para la BB----------")
            bid_estrategia = ((price_48_bi - price_ci_of) /
                              price_ci_of) * 365 / (dias_restantes + 0)
            ask_estrategia = ((price_48_of - price_ci_bi) /
                              price_ci_bi) * 365 / (dias_restantes + 0)
            """
            
            """
            self.log.info(
                f"        upper: {upper}            lower: {lower}            media: {close_prices[-1:]}            bid_estrategia: {bid_estrategia}            ask_estrategia: {ask_estrategia}          ")
            bookBB = {
                "price_ci_bi": price_ci_bi,
                "price_ci_of": price_ci_of,
                "price_48_bi": price_48_bi,
                "price_48_of": price_48_of
            }

            self.log.info(f"bookBB: {bookBB}")
            dataBB = {
                "label": str(datetime.datetime.now()),
                "upper": upper,
                "lower": lower,
                "media": close_prices[-1:][0],
                "bid_estrategia": bid_estrategia,
                "ask_estrategia": ask_estrategia,
            }
            self.log.info(f"dataBB: {dataBB}")
            limitsBB = {
                "bi_ci": latest_limit_asset_price_CI_BID,
                "of_ci": latest_limit_asset_price_CI_ASK,
                "bi_48": latest_limit_asset_price_48h_BID,
                "of_48": latest_limit_asset_price_48h_ASK
            }
            self.botData["limitsBB"] = limitsBB
            self.log.info(f"limitsBB: {limitsBB}")
            captureDatosBB = {
                "fecha": datetime.datetime.today().date(),
                "book": bookBB,
                "dataBB": dataBB,
                "limitsPuntas": limitsBB,
                "bb_ci": bb_ci_actual,
                "bb_48": bb_48_actual
            }
          #  self.capture_datos_bb = captureDatosBB
            self.log.info(f"voy a guardar datos intradia: {captureDatosBB}")
            await self.clientR.guardar_datos_bb_intradia(captureDatosBB)
            # if self.botData["soloEscucharMercado"]==True:
            dataMd = {"type": "bb", "instrumentId": {
                "symbol": self.botData["bymaCI"]}}
            self.fix.server_md.broadcast(str(dataMd))
            return

        except Exception as e:
            self.log.error(f"error en operar con bb: {e}")

    async def run_forever_bb(self):
        try:
            while not self.stop.is_set():
                self.log.info("estoy en el ciclo inifito del bot BB")
         #       await self.pausedBB.wait()
                if self.paused.is_set():
                    await self.operar_con_bb()
                await asyncio.sleep(10)
            #    self.log.info(f"sin task en la cola del bot: {self.id}")
        except Exception as e:
            self.log.error(
                f"error en el ciclo run_forever del botBB con id: {self.id} , {e}")
        finally:
            self.log.info(
                f"saliendo del ciclo run foreverBB del botBB con id: {self.id}")

    async def run_forever(self):
        try:
            if await self.tareas_de_inicio() == False:
                return
            self.log.info(f"iniciando ciclo de tareas con el bot: {self.id}")
            while not self.stop.is_set():
                #   self.log.info("estoy en el ciclo inifito del bot")
                if self.paused.is_set():
                    self.log.info(f"el bot no esta en pause")
                    task = await self.obtener_tarea()
                    if task is not None:
                        self.log.info(f"el bot tiene tareas")
                        self.log.info(f" se va ejecutar esta tarea: {task}")
                        self.marcar_completada(task)
                        await self.execute_task(task)
                        self.log.info(f"se completo la tarea: {task}")
                    else:
                        self.log.info(f"el bot no tiene tareas")
                else:
                    self.log.info(f"el bot esta en pause")
                await asyncio.sleep(0.1)
            #    self.log.info(f"sin task en la cola del bot: {self.id}")
        except Exception as e:
            self.log.error(
                f"error en el ciclo run_forever del botBB con id: {self.id} , {e}")
        finally:
            self.log.info(
                f"saliendo del ciclo run forever del botBB con id: {self.id}")

    async def run(self):
        try:
            self.threadCola = Thread(target=self.startCola)
            self.threadCola.start()
            self.threadBB = Thread(target=self.startLoopBB)
            self.threadBB.start()
        finally:
            self.log.info(
                "saliendo de la tarea iniciada en el botmanager pero queda la thread")

    def startLoopBB(self):
        # creo un nuevo evento para asyncio y asi ejecutar todo de aqui en adelante con async await
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # ejecuto la funcion q quiero
        loop.run_until_complete(self.run_forever_bb())
        loop.close()

    def startCola(self):
        # creo un nuevo evento para asyncio y asi ejecutar todo de aqui en adelante con async await
        loop3 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop3)
        # ejecuto la funcion q quiero
        loop3.run_until_complete(self.run_forever())
        loop3.close()

    async def execute_task(self, task):
        # Do something with the task
        self.log.info(f"Executing task: {task}, en bot: {self.id}")
        if task["type"] == 0:
            self.log.info(f"aqui si verificamos puntas")
            await self.verificar_puntas()


    async def detenerBot(self):
        await self.stopCola()
        self.threadCola = None
        self.threadBB = None

    def calculate_limit_asset_price_CI(self, asset_price_48h, size_48h, sideBook, market_price_ci):
        self.log.info(
            f"entrando a calculate_limit_asset_price_CI: {asset_price_48h}, {size_48h}, {sideBook}, {market_price_ci}")
        try:
            annualized_arbitrage_rate = self.lowerBB
            if annualized_arbitrage_rate == None:
                annualized_arbitrage_rate = self.minimum_arbitrage_rate
            volume = self.get_volume(size_48h)
            self.log.info(f"volume: {volume}")
            if sideBook == "BI":
                self.log.info(f"sideBook BI")
                annualized_arbitrage_rate = self.upperBB
                if annualized_arbitrage_rate == None:
                    annualized_arbitrage_rate = self.maximum_arbitrage_rate
                if volume > self.botData["ruedaA"]["sizeDisponible"]:
                    self.log.info(
                        f"volume>self.botData['ruedaA']['sizeDisponible']")
                    self.log.info(
                        f"sizeDisponible ruedaA: {self.botData['ruedaA']['sizeDisponible']}")
                    volume = self.botData["ruedaA"]["sizeDisponible"]
            else:
                self.log.info(f"sideBook OF")
                if volume > self.botData["ruedaB"]["sizeDisponible"]:
                    self.log.info(
                        f"volume>self.botData['ruedaB']['sizeDisponible']")
                    self.log.info(
                        f"sizeDisponible ruedaB: {self.botData['ruedaB']['sizeDisponible']}")
                    volume = self.botData["ruedaB"]["sizeDisponible"]

            current_date = datetime.datetime.now().date()
            self.log.info(f"current_date: {current_date}")
            next_day = self.next_business_day(current_date)
            self.log.info(f"next_day: {next_day}")
            dias_restantes = next_day  # aqui es
            self.log.info(f"dias_restantes: {dias_restantes}")
            limit_asset_price_CI = asset_price_48h - \
                (annualized_arbitrage_rate *
                 (dias_restantes + 0) / 365) * market_price_ci
            self.log.info(f"limit_asset_price_CI: {limit_asset_price_CI}")
            self.update_limits("CI", limit_asset_price_CI, sideBook)
            return round(self.redondeo_tick(limit_asset_price_CI, self.botData["minPriceIncrement"]), 2), volume
        except Exception as e:
            self.log.error(f"error calculando limit ci: {e}")
            return 0, 0

    def calculate_limit_asset_price_48h(self, asset_price_CI, size_CI, sideBook):
        self.log.info(
            f"entrando a calcular limit 48: {asset_price_CI}, {size_CI}, {sideBook}")
        try:
            annualized_arbitrage_rate = self.lowerBB
            if annualized_arbitrage_rate == None:
                annualized_arbitrage_rate = self.minimum_arbitrage_rate
            volume = size_CI  # self.get_volume(size_CI)
            self.log.info(f"volume: {volume}")
            if sideBook == "OF":
                self.log.info(f"sideBook OF")
                annualized_arbitrage_rate = self.upperBB
                if annualized_arbitrage_rate == None:
                    annualized_arbitrage_rate = self.maximum_arbitrage_rate
                if volume > self.botData["ruedaA"]["sizeDisponible"]:
                    self.log.info(
                        f"volume>self.botData['ruedaA']['sizeDisponible']")
                    self.log.info(
                        f"sizeDisponible ruedaA: {self.botData['ruedaA']['sizeDisponible']}")
                    volume = self.botData["ruedaA"]["sizeDisponible"]
            else:
                self.log.info(f"sideBook BI")
                if volume > self.botData["ruedaB"]["sizeDisponible"]:
                    self.log.info(
                        f"volume>self.botData['ruedaB']['sizeDisponible']")
                    self.log.info(
                        f"sizeDisponible ruedaB: {self.botData['ruedaB']['sizeDisponible']}")
                    volume = self.botData["ruedaB"]["sizeDisponible"]
            current_date = datetime.datetime.now().date()
            next_day = self.next_business_day(current_date)
            dias_restantes = next_day
            limit_asset_price_48h = asset_price_CI + \
                (annualized_arbitrage_rate *
                 (dias_restantes + 0) * asset_price_CI / 365)
            self.update_limits("48", limit_asset_price_48h, sideBook)

            return round(self.redondeo_tick(limit_asset_price_48h, self.botData["minPriceIncrement"]), 2), volume
        except Exception as e:
            self.log.error(f"error calculando limit 48: {e}")
            return 0, 0

    async def verificar_size_rueda(self, symbol, side):
        response = False
        if symbol == self.botData["byma48h"]:
            if side == "Buy":
                self.log.info(
                    f"es rueda b, size disponible: {self.botData['ruedaB']['sizeDisponible']}")
                if self.botData['ruedaB']['sizeDisponible'] == 0:
                    # cancelar orden haberla
                    self.log.info(f"envio a cancelar orden haberla")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(symbol, 1)
                    response = True
            else:
                self.log.info(
                    f"es rueda a, size disponible: {self.botData['ruedaA']['sizeDisponible']}")

                if self.botData['ruedaA']['sizeDisponible'] == 0:
                    self.log.info(f"envio a cancelar orden haberla")
                    # cancelar orden haberla
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(symbol, 2)
                    response = True
        else:
            if side == "Buy":
                self.log.info(
                    f"es rueda a, size disponible: {self.botData['ruedaA']['sizeDisponible']}")
                if self.botData['ruedaA']['sizeDisponible'] == 0:
                    # cancelar orden haberla
                    self.log.info(f"envio a cancelar orden haberla")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(symbol, 1)
                    response = True
            else:
                self.log.info(
                    f"es rueda b, size disponible: {self.botData['ruedaB']['sizeDisponible']}")
                if self.botData['ruedaB']['sizeDisponible'] == 0:
                    # cancelar orden haberla
                    self.log.info(f"envio a cancelar orden haberla")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(symbol, 2)
                    response = True
        return response

    async def verificar_48h(self, side):
        self.log.info(f"book: {self._tickers}")
        try:
            self.log.info(f"ver botData: {self.botData}")
            sideText = "Buy"
            sideBook = "BI"
            sideOrder = 1
            if side == "Sell":
                sideText = "Sell"
                sideBook = "OF"
                sideOrder = 2

            self.log.info(f"entrando a verificar 48h: {side}")
            # await self.clientR.esperar_orden_operada()
            # necesito verificar si tengo una orden creada , y de ser asi modificar y sino crear
            # aqui busco en db si tengo una orden limit creada en el book byma48h
            verificarOrdenCreada = await self.clientR.get_order_limit_by_symbol_side(self.botData["byma48h"], sideText)
            # esta funcion me devuelve un diccionario con status y data, la data viene de la db y es un diccionario con los datos de la orden
            if verificarOrdenCreada["status"] == True:  # si tengo orden creada
                # guardo los datos de la orden
                orden = verificarOrdenCreada["data"]
                self.log.info("tengo orden creada")
                if await self.verificar_size_rueda(self.botData["byma48h"], sideText) == True:
                    return
                # verifico si puedo operar, aqui va consultar la data del book con la data de la db y ver si puedo operar
                # me va arrojar un diccionario con status y indice, si status es True entonces puedo operar y el indice es el indice del book q puedo tomar sus valores
                # await self.clientR.esperar_orden_operada()
                verificarOperar = await self.clientR.verificar_ordenes_futuro(self.botData["bymaCI"], sideBook, self._tickers[self.botData["bymaCI"]][sideBook])
                if verificarOperar["puedoOperar"] == True:
                    self.log.info(f"puedo crear orden en 48h: {sideBook}")
                    # indice del book q puedo tomar sus valores
                    indice = verificarOperar["indiceBookUsar"]
                    # precio del book q puedo tomar sus valores
                    market_price_CI = self._tickers[self.botData["bymaCI"]
                                                    ][sideBook][indice]["price"]
                    # size del book q puedo tomar sus valores
                    size_CI = self._tickers[self.botData["bymaCI"]
                                            ][sideBook][indice]["size"]
                    limit_price_CI, volume_limit_CI = self.calculate_limit_asset_price_48h(
                        market_price_CI, size_CI, sideBook)  # calculo el precio y size de la orden
                    self.log.info(
                        f"Limit CI: {limit_price_CI}, Volume: {volume_limit_CI} ")
                    if limit_price_CI <= 0:
                        self.log.info(
                            "no hago nada xq el precio es menor o igual a 0")
                        return
                    # validar mejor con el size disponible de la rueda
                    if volume_limit_CI <= 0:
                        self.log.info(
                            "no hago nada xq el size es menor o igual a 0")
                        return
                    # verifico si el precio o size son diferentes del q tengo actualmente
                    if orden['price'] != limit_price_CI or orden['leavesQty'] != volume_limit_CI:
                        self.log.info(
                            "si el precio o size son diferentes del q tengo actualmente entonces modifico la orden")
                        # await self.clientR.esperar_orden_operada()
                        if sideBook == "BI":
                            self.log.info(
                                "aqui voy a verificar el saldo disponible en pesos  ")
                            disponible = await self.clientR.get_saldo_disponible(self.botData["byma48h"])
                            if disponible < (limit_price_CI*volume_limit_CI) * self.botData["factor"]:
                                self.log.info(
                                    f"no hay saldo disponible para operar ")
                                return
                        if self.botData["soloEscucharMercado"] == True:
                            return
                        if not self.paused.is_set():
                            self.log.warning(f"paused esta activo")
                            return
                        if orden['leavesQty'] != volume_limit_CI:
                            modificarOrden = await self.clientR.modificar_orden(orden['orderId'], orden['clOrdId'], sideOrder, 2, self.botData["byma48h"],
                                                                                volume_limit_CI, limit_price_CI)  # modifico la orden
                        else:
                            volume_limit_CI = orden['orderQty']
                            modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'], sideOrder, 2, self.botData["byma48h"],
                                                                                     volume_limit_CI, limit_price_CI)  # modifico la orden
                        self.log.info(f"orden modificada {modificarOrden}")
                    else:
                        self.log.error(
                            "no hago nada xq el precio y size son iguales al q tengo actualmente")
                else:
                    self.log.info("cancelar orden haberla todo depende :D  ")

            else:
                self.log.info("no tengo orden creada")
                self.log.info(f"posiciones: {self.botData['posiciones']}")
                posicionBymaCI = self.botData["posiciones"][self.botData["bymaCI"]
                                                            ]["BI"] - self.botData["posiciones"][self.botData["bymaCI"]]["OF"]
                if sideBook == "BI":
                    # verificar antes por una orden pegada
                    # verificar la cantidad de las posiciones en el book bymaCI
                    if posicionBymaCI == 0:
                        # x ende no puedo crear una orden de compra 48 xq no tengo nada en ci posicion
                        self.log.info("no hay nada en CI BI")
                        # por ende no me pueden tomar mi orden xq si lo hacen no puedo vender ci
                        return
                if sideBook == "OF":
                    posicion48h = (self.botData["posiciones"][self.botData["byma48h"]]["BI"] -
                                   self.botData["posiciones"][self.botData["byma48h"]]["OF"]) + posicionBymaCI
                    if posicion48h <= 0:
                        self.log.info("no hay nada en 48h BI")
                        return
                # verifico si puedo operar
                # me va arrojar un diccionario con status y indice, si status es True entonces puedo operar y el indice es el indice del book q puedo tomar sus valores
                # await self.clientR.esperar_orden_operada()
                verificarOperar = await self.clientR.verificar_ordenes_futuro(self.botData["bymaCI"], sideBook, self._tickers[self.botData["bymaCI"]][sideBook])
                if verificarOperar["puedoOperar"] == True:  # si puedo operar
                    self.log.info(f"puedo crear orden en 48h: {sideBook} ")
                    # indice del book q puedo tomar sus valores
                    indice = verificarOperar["indiceBookUsar"]
                    # precio del book q puedo tomar sus valores
                    market_price_CI = self._tickers[self.botData["bymaCI"]
                                                    ][sideBook][indice]["price"]
                    # size del book q puedo tomar sus valores
                    size_CI = self._tickers[self.botData["bymaCI"]
                                            ][sideBook][indice]["size"]
                    limit_price_CI, volume_limit_CI = self.calculate_limit_asset_price_48h(
                        market_price_CI, size_CI, sideBook)  # calculo el precio y size de la orden
                    self.log.info(
                        f"Limit CI: {limit_price_CI}, Volume: {volume_limit_CI} ")
                    if volume_limit_CI <= 0 or limit_price_CI <= 0:
                        self.log.info(
                            "no hago nada xq el size es menor o igual a 0")
                        return
                    # creo la orden: symbol, side:1=buy:2=sell, volume, price, order_type:2=limit, id_bot
                    # await self.clientR.esperar_orden_operada()
                    if posicionBymaCI >= volume_limit_CI:
                        if sideBook == "BI":
                            self.log.info(
                                "aqui voy a verificar el saldo disponible en pesos  ")
                            disponible = await self.clientR.get_saldo_disponible(self.botData["byma48h"])
                            if disponible < (limit_price_CI*volume_limit_CI) * self.botData["factor"]:
                                self.log.info(
                                    f"no hay saldo disponible para operar ")
                                return
                        if self.botData["soloEscucharMercado"] == True:
                            return
                        if not self.paused.is_set():
                            self.log.warning(f"paused esta activo")
                            return
                        # creo la orden
                        ordenNueva = await self.clientR.nueva_orden(self.botData["byma48h"], sideOrder, volume_limit_CI, limit_price_CI, 2)
                        self.log.info(f"orden nueva {ordenNueva}")
                    else:
                        self.log.error(
                            f"no puedo crear la orden xq no tengo suficiente size en ci")

                else:
                    self.log.error(
                        "no hago nada xq no tengo nada en CI BI y no tengo orden creada")
        except Exception as e:
            self.log.error(f"error verificando 48: {e}")

    async def verificar_colgadas_rueda(self):
        self.log.info(f"entrando a verificar colgadas rueda")
        ruedaA = self.botData["ruedaA"]["sizeDisponible"]  # C CI / V 48
        ruedaB = self.botData["ruedaB"]["sizeDisponible"]  # V CI / C 48
        # self.botData["byma48h"]
        # self.botData["bymaCI"]
        if ruedaA == 0:
            if not self.paused.is_set():
                self.log.warning(f"paused esta activo")
                return
            cancelHaberla = await self.clientR.cancelar_orden_haberla(self.botData["bymaCI"], 1)
            self.log.info(f"cancelHaberla: {cancelHaberla}")
            cancelHaberla = await self.clientR.cancelar_orden_haberla(self.botData["byma48h"], 2)
            self.log.info(f"cancelHaberla: {cancelHaberla}")

        if ruedaB == 0:
            if not self.paused.is_set():
                self.log.warning(f"paused esta activo")
                return
            cancelHaberla = await self.clientR.cancelar_orden_haberla(self.botData["bymaCI"], 2)
            self.log.info(f"cancelHaberla: {cancelHaberla}")
            cancelHaberla = await self.clientR.cancelar_orden_haberla(self.botData["byma48h"], 1)
            self.log.info(f"cancelHaberla: {cancelHaberla}")

    async def verificar_puntas(self):
        try:
            if self.botData["type_side"] == 0:
                # await self.clientR.esperar_orden_operada()
                # aqui voy a verificar si tengo orden abierta en ci la modifico y si no la creo
                verificar_ci = await self.verificar_ci("Buy")
                # await self.clientR.esperar_orden_operada()
                verificar_ci = await self.verificar_ci("Sell")
                # await self.clientR.esperar_orden_operada()
                # aqui voy a verificar si tengo orden abierta en 48h la modifico y si no la creo
                verificar_48h = await self.verificar_48h("Buy")
                # await self.clientR.esperar_orden_operada()
                verificar_48h = await self.verificar_48h("Sell")

                verificar_colgadas_rueda = await self.verificar_colgadas_rueda()
            elif self.botData["type_side"] == 1:
                # await self.clientR.esperar_orden_operada()
                # aqui voy a verificar si tengo orden abierta en ci la modifico y si no la creo
                verificar_ci = await self.verificar_ci("Buy")
                # await self.clientR.esperar_orden_operada()
                verificar_ci = await self.verificar_ci("Sell")

                verificar_colgadas_rueda = await self.verificar_colgadas_rueda()
            elif self.botData["type_side"] == 2:
                # await self.clientR.esperar_orden_operada()
                # aqui voy a verificar si tengo orden abierta en 48h la modifico y si no la creo
                verificar_48h = await self.verificar_48h("Buy")
                # await self.clientR.esperar_orden_operada()
                verificar_48h = await self.verificar_48h("Sell")

                verificar_colgadas_rueda = await self.verificar_colgadas_rueda()
            else:
                self.log.error(
                    f"type side desconocido: {self.botData['type_side']}")
        except Exception as e:
            self.log.error(f"error verificando puntas")

    async def verificar_ci(self, side):
        self.log.info(f"book: {self._tickers}")
        try:
            self.log.info(f"entrando a verificar ci: {side}")
            self.log.info(f"ver botData: {self.botData}")
            sideText = "Buy"
            sideBook = "BI"
            sideOrder = 1
            sideBookCI = "OF"
            if side == "Sell":
                sideText = "Sell"
                sideBook = "OF"
                sideBookCI = "BI"
                sideOrder = 2
            # necesito verificar si tengo una orden creada , y de ser asi modificar y sino crear
            # aqui busco en db si tengo una orden limit creada en el book bymaCI

            verificarOrdenCreada = await self.clientR.get_order_limit_by_symbol_side(self.botData["bymaCI"], sideText)
            # esta funcion me devuelve un diccionario con status y data, la data viene de la db y es un diccionario con los datos de la orden
            if verificarOrdenCreada["status"] == True:  # si tengo orden creada
                # guardo los datos de la orden
                orden = verificarOrdenCreada["data"]
                self.log.info("tengo orden creada")
                # verificar si el size de la rueda no es 0 , xq si es 0 entonces debo cancelar orden haberla
                if await self.verificar_size_rueda(self.botData["bymaCI"], sideText) == True:
                    return
                # verifico si puedo operar, aqui va consultar la data del book con la data de la db y ver si puedo operar
                # me va arrojar un diccionario con status y indice, si status es True entonces puedo operar y el indice es el indice del book q puedo tomar sus valores
                # await self.clientR.esperar_orden_operada()
                verificarOperar = await self.clientR.verificar_ordenes_futuro(self.botData["byma48h"], sideBook, self._tickers[self.botData["byma48h"]][sideBook])
                # verifico ci por la formula que calcula el limit de ci
                verificarCI = await self.clientR.verificar_ordenes_futuro(self.botData["bymaCI"], sideBookCI, self._tickers[self.botData["bymaCI"]][sideBookCI])
                if verificarOperar["puedoOperar"] == True and verificarCI["puedoOperar"] == True:
                    self.log.info(f"puedo crear orden en CI: {sideBook}")
                    # indice del book q puedo tomar sus valores
                    indice = verificarOperar["indiceBookUsar"]
                    incideCI = verificarCI["indiceBookUsar"]
                    # precio del book q puedo tomar sus valores
                    market_price_48h = self._tickers[self.botData["byma48h"]
                                                     ][sideBook][indice]["price"]
                    market_price_ci = self._tickers[self.botData["bymaCI"]
                                                    ][sideBookCI][incideCI]["price"]
                    # size del book q puedo tomar sus valores
                    size_48h = self._tickers[self.botData["byma48h"]
                                             ][sideBook][indice]["size"]
                    limit_price_CI, volume_limit_CI = self.calculate_limit_asset_price_CI(
                        market_price_48h, size_48h, sideBook, market_price_ci)  # calculo el precio y size de la orden
                    self.log.info(
                        f"Limit CI: {limit_price_CI}, Volume: {volume_limit_CI} ")
                    if limit_price_CI <= 0:
                        self.log.info(
                            "no hago nada xq el precio es menor o igual a 0")
                        return
                    if volume_limit_CI <= 0:
                        self.log.info(
                            "no hago nada xq el size es menor o igual a 0")
                        return
                    # verifico si el precio o size son diferentes del q tengo actualmente
                    if orden['price'] != limit_price_CI or orden['leavesQty'] != volume_limit_CI:
                        self.log.info(
                            "si el precio o size son diferentes del q tengo actualmente entonces modifico la orden")
                        # await self.clientR.esperar_orden_operada()
                        if sideBook == "BI":
                            self.log.info(
                                "aqui voy a verificar el saldo disponible en pesos  ")
                            disponible = await self.clientR.get_saldo_disponible(self.botData["bymaCI"])
                            if disponible < (limit_price_CI*volume_limit_CI) * self.botData["factor"]:
                                self.log.info(
                                    f"no hay saldo disponible para operar ")
                                return
                        if self.botData["soloEscucharMercado"] == True:
                            return
                        if not self.paused.is_set():
                            self.log.warning(f"paused esta activo")
                            return
                        if orden['leavesQty'] != volume_limit_CI:
                            modificarOrden = await self.clientR.modificar_orden(orden['orderId'], orden['clOrdId'], sideOrder, 2, self.botData["bymaCI"],
                                                                                volume_limit_CI, limit_price_CI)  # modifico la orden
                        else:
                            volume_limit_CI = orden['orderQty']
                            modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'], sideOrder, 2, self.botData["bymaCI"],
                                                                                     volume_limit_CI, limit_price_CI)  # modifico la orden
                        self.log.info(f"orden modificada {modificarOrden}")
                    else:
                        self.log.error(
                            "no hago nada xq el precio y size son iguales al q tengo actualmente")
                else:
                    if verificarOperar["primeraOrden"] == True:
                        self.log.info(
                            "cancelar orden haberla en 48 todo depende :D  ")
                        self.log.info(f"estoy en 48: {side}")
                        if not self.paused.is_set():
                            self.log.warning(f"paused esta activo")
                            return
                        cancelarHaberla = await self.clientR.cancelar_orden_haberla(self.botData["byma48h"], sideOrder)
                        self.log.info(f"cancelarHaberla: {cancelarHaberla}")

            else:
                self.log.info("no tengo orden creada")
                posicionBymaCI = self.botData["posiciones"][self.botData["bymaCI"]
                                                            ]["BI"] - self.botData["posiciones"][self.botData["bymaCI"]]["OF"]
                posicion48h = self.botData["posiciones"][self.botData["byma48h"]
                                                         ]["BI"] - self.botData["posiciones"][self.botData["byma48h"]]["OF"]
                saldoBi = posicionBymaCI + posicion48h
                if sideBook == "OF":
                    # verificar la cantidad de las posiciones en el book bymaCI
                    if saldoBi <= 0:
                        # x ende no puedo crear una orden de venta en CI
                        self.log.info(
                            "no hay nada en CI BI o esta calzado con 48")
                        return
                # verifico si puedo operar
                # me va arrojar un diccionario con status y indice, si status es True entonces puedo operar y el indice es el indice del book q puedo tomar sus valores
                # await self.clientR.esperar_orden_operada()
                verificarOperar = await self.clientR.verificar_ordenes_futuro(self.botData["byma48h"], sideBook, self._tickers[self.botData["byma48h"]][sideBook])
                verificarCI = await self.clientR.verificar_ordenes_futuro(self.botData["bymaCI"], sideBookCI, self._tickers[self.botData["bymaCI"]][sideBookCI])
                if verificarOperar["puedoOperar"] == True:
                    self.log.info(f"puedo crear orden en CI: {sideBook}")
                    # indice del book q puedo tomar sus valores
                    indice = verificarOperar["indiceBookUsar"]
                    incideCI = verificarCI["indiceBookUsar"]
                    # precio del book q puedo tomar sus valores
                    market_price_48h = self._tickers[self.botData["byma48h"]
                                                     ][sideBook][indice]["price"]
                    market_price_ci = self._tickers[self.botData["bymaCI"]
                                                    ][sideBookCI][incideCI]["price"]
                    # size del book q puedo tomar sus valores
                    size_48h = self._tickers[self.botData["byma48h"]
                                             ][sideBook][indice]["size"]
                    limit_price_CI, volume_limit_CI = self.calculate_limit_asset_price_CI(
                        market_price_48h, size_48h, sideBook, market_price_ci)  # calculo el precio y size de la orden
                    # muestro el precio y size de la orden
                    self.log.info(
                        f"Limit CI: {limit_price_CI}, Volume: {volume_limit_CI} ")
                    # creo la orden: symbol, side:1=buy:2=sell, volume, price, order_type:2=limit, id_bot
                    if volume_limit_CI <= 0 or limit_price_CI <= 0:
                        self.log.info(
                            "no hago nada xq el size es menor o igual a 0")
                        return
                    # await self.clientR.esperar_orden_operada()
                    # ahora aqui debo validar q el size q tengo en las posiciones sea mayor o igual al q voy a realizar
                    if sideBook == "OF":
                        if posicionBymaCI <= volume_limit_CI:
                            self.log.info(
                                "no hago nada xq no tengo suficiente size en las posiciones")

                            return  # no hago nada xq no tengo suficiente size en las posiciones
                    if sideBook == "BI":
                        self.log.info(
                            "aqui voy a verificar el saldo disponible en pesos  ")
                        disponible = await self.clientR.get_saldo_disponible(self.botData["bymaCI"])
                        if disponible < (limit_price_CI*volume_limit_CI) * self.botData["factor"]:
                            self.log.info(
                                f"no hay saldo disponible para operar ")
                            return
                    if self.botData["soloEscucharMercado"] == True:
                        return
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    ordenNueva = await self.clientR.nueva_orden(self.botData["bymaCI"], sideOrder, volume_limit_CI,
                                                                limit_price_CI, 2)  # creo la orden

                #   ordenNueva = await self.clientR.nueva_orden(self.botData["bymaCI"], sideOrder, volume_limit_CI,
                    #                                      limit_price_CI, 2)#creo la orden
                    self.log.info(f"orden nueva {ordenNueva}")
                else:
                    self.log.error(
                        "no hago nada xq no tengo nada en 48h  y no tengo orden creada en CI")

        except Exception as e:
            self.log.error(f"error verificando ci: {e}")

    # 250k es el máximo de volumen por operación, tiene que ser un input de otra función que revise balances de tenencias
    def get_volume(self, size, max_volume=250000):
        if size > max_volume:
            return max_volume
        else:
            return size

    def next_business_day(self, current_date):
        # Calcular el próximo día hábil a partir del día actual
        if current_date.weekday() >= 3:
            # Si es jueves o viernes, el próximo día hábil en 48h es 4 días después
            next_day = 4
        else:
            # En otro caso, el próximo día hábil es el siguiente día
            next_day = 2

        return next_day

    def update_limits(self, symbol, price, sideBook):
        self.log.info(f"entrando a updatelimits")
        try:
            if symbol == "48":
                if sideBook == "BI":
                    self.botData["limitsBB"]["bi_48"] = price
                else:
                    self.botData["limitsBB"]["of_48"] = price
            else:
                if sideBook == "BI":
                    self.botData["limitsBB"]["bi_ci"] = price
                else:
                    self.botData["limitsBB"]["of_ci"] = price
        except Exception as e:
            self.log.error(f"error update limits: {e}")

    def redondeo_tick(self, price, tick, ):
        self.log.info(f"redondeo_tick: {price}, {tick}")
        rounded_num = round(price / tick) * tick
        return rounded_num

    def calculate_current_rate(self, market_price_CI, market_price_48h):
        current_date = datetime.datetime.now().date()
        next_day = self.next_business_day(current_date)
        dias_restantes = (next_day - current_date).days
        profit_48h = (market_price_48h - market_price_CI) / market_price_48h
        annualized_arbitrage_rate_48h = profit_48h * 365 / (dias_restantes + 0)
        return annualized_arbitrage_rate_48h

    async def verificar_orden_operada(self, details, typeOrder, lastOrderID):
        self.log.info(f"entrando a verificar_orden_operada. {details}")
        response = False
        try:
            self.log.info(f"contador operadas: {self.botData['ordenOperada']}")
            await self.actualizar_posiciones(details)
            self.log.info(
                f"verificando orden operada del id_bot: {self.clientR.id_bot}")
            orderId = details["orderId"]
            clOrdId = details["clOrdId"]
            activeOrder = False
            if details["leavesQty"] > 0:
                activeOrder = True
            if typeOrder == "N":
                self.log.info("es orden normal de la estrategia ")
                self.log.info("ahora operar la contraria ")
                order = await self.operar_orden(details, lastOrderID)
                self.log.info(
                    f"llego respuesta de orden contraria operada: {order}")
                if order["llegoRespuesta"] == True:
                    if order["data"]["reject"] == False:
                        self.log.info(
                            f"es filled o colgada ahora si descuento la rueda ")
                        await self.guardar_mitad_rueda(order["data"], order["lastQty"], 1)
                await self.clientR.disable_order_status(orderId, clOrdId)

                await self.clientR.save_order_details(details, activeOrder)
            elif typeOrder == "B":
                self.log.info("es una orden B osea contraria")
                await self.clientR.disable_order_status(orderId, clOrdId)
                await self.clientR.save_order_details(details, activeOrder)
            response = True
        except Exception as e:
            self.log.error(f"error verificando orden operada: {e}")
        return response

    async def actualizar_posiciones(self, details):
        try:
            self.log.info(f"actualizando posiciones")
            size = int(details["lastQty"])
            if details["side"] == "Buy":
                self.botData["posiciones"][details["symbol"]
                                           ]["BI"] = self.botData["posiciones"][details["symbol"]]["BI"] + size
            else:
                self.botData["posiciones"][details["symbol"]
                                           ]["OF"] = self.botData["posiciones"][details["symbol"]]["OF"] + size
            self.log.info(
                f"posiciones actualizadas: {self.botData['posiciones']}")
        except Exception as e:
            self.log.error(f"error actualizando posiciones: {e}")

    async def operar_orden(self, orden, id_order):
        self.log.info(f"entrando a operar orden")
        response = {"llegoRespuesta": False}
        try:
            if orden["symbol"] == self.botData["bymaCI"]:
                self.log.info("bymaCI")
                if orden["side"] == "Buy":
                    self.log.info("Buy")
                    self.log.info("ahora operar la contraria pero en 48h OF ")
                    response = await self.operar_orden_contraria(orden, self.botData["byma48h"], "BI", id_order, 2)
                else:
                    # es sell
                    self.log.info("Sell")
                    self.log.info("ahora operar la contraria pero en 48h BI ")
                    response = await self.operar_orden_contraria(orden, self.botData["byma48h"], "OF", id_order, 1)
            else:
                # es byma48h
                self.log.info("byma48h")
                if orden["side"] == "Buy":
                    self.log.info("Buy")
                    self.log.info("ahora operar la contraria pero en CI OF ")
                    response = await self.operar_orden_contraria(orden, self.botData["bymaCI"], "BI", id_order, 2)
                else:
                    # es sell
                    self.log.info("Sell")
                    self.log.info("ahora operar la contraria pero en CI BI ")
                    response = await self.operar_orden_contraria(orden, self.botData["bymaCI"], "OF", id_order, 1)
        except Exception as e:
            self.log.error(f"error operando orden : {e}")
        return response

    async def operar_orden_contraria(self, orden, symbolCheck, sideCheck, id_order, sideOrder):
        response = {"llegoRespuesta": False}
        self.log.info(
            f"operar orden contraria del id_bot: {self.clientR.id_bot}")
        self.log.info(f"orden {orden}")
        self.log.info(f"necesito el symbol: {symbolCheck}")
        self.log.info(
            f"necesito el side: {sideCheck} para poder hacer el market del otro lado")
        self.log.info(f"id_order: {id_order}")
        self.log.info(f"sideOrder: {sideOrder}")
        try:
            verifyF = await self.clientR.verificar_ordenes_futuro(symbolCheck, sideCheck, self._tickers[symbolCheck][sideCheck])
            if verifyF["puedoOperar"] == True:
                self.log.info(
                    "si hay ordenes en el simbolo y en el side que necesito")
                size = orden["lastQty"]
                indiceBook = verifyF["indiceBookUsar"]
                priceOrder = self._tickers[symbolCheck][sideCheck][indiceBook]["price"]
                self.log.info(f"priceFuturo: {priceOrder}")
                clOrdId = await self.clientR.getNextOrderBotID(self.botData["cuenta"], self.botData["id_bot"], id_order)
            #   self.botData["ordenesBot"].append({"idOperada":id_order, "clOrdId": clOrdId, "size": size })
                ordenNew = await self.clientR.nueva_orden(symbolCheck, sideOrder, size, priceOrder, 2, clOrdId, 1)
                self.log.info(f"ordenNew: {ordenNew}")
                response = ordenNew

            else:
                size = orden["lastQty"]
                self.log.info(
                    f"no puedo operar xq no hay ordenes en el simbolo y en el side que necesito")
                sideForPrice = "BI"
                if sideCheck == "BI":
                    sideForPrice = "OF"
                limit_price, volume_limit = self.calculate_limit_asset_price_48h(
                    orden["price"], orden["lastQty"], sideForPrice)
                self.log.info(f"priceFuturo: {limit_price}")
                clOrdId = await self.clientR.getNextOrderBotID(self.botData["cuenta"], self.botData["id_bot"], id_order)
            #  self.botData["ordenesBot"].append({"idOperada":id_order, "clOrdId": clOrdId, "size": size })
                ordenNew = await self.clientR.nueva_orden(symbolCheck, sideOrder, size, limit_price, 2, clOrdId, 1)
                self.log.info(f"ordenNew: {ordenNew}")
                response = ordenNew
        except Exception as e:
            self.log.error(f"error operando orden contraria: {e}")
        return response

    async def guardar_mitad_rueda(self, details, lastQty, descontar=0, sizePendiente=0):
        self.log.info("guardar_mitad_rueda")
        try:
            # debo primero averiguar a q lado de la rueda pertenece la orden
            # para eso voy a comparar el simbolo de la orden con el simbolo de la rueda
            # si el simbolo de la orden es igual CI con el side BI entonces es de rueda A, o
            ruedaType = "ruedaA"
            ruedaContraria = "ruedaB"
            if details["symbol"] == self.botData["byma48h"] and details["side"] == "Buy":
                ruedaType = "ruedaB"
                ruedaContraria = "ruedaA"
            elif details["symbol"] == self.botData["bymaCI"] and details["side"] == "Sell":
                ruedaType = "ruedaB"
                ruedaContraria = "ruedaA"
            self.log.info(f"ruedaType: {ruedaType}")
            # guardar orden
            self.log.info("guardar orden en el lado de la rueda")
        #  self.botData[ruedaType]["ordenes"].append(details)
            self.log.info(
                f"ordenes de la rueda: {self.botData[ruedaType]['ordenes']}")
            # descontar sizedisponible
            if descontar == 1:
                self.log.info("descontar size disponible")
                size = lastQty
                self.botData[ruedaType]["sizeDisponible"] = self.botData[ruedaType]["sizeDisponible"] - size
                self.log.info(
                    f"size disponible: {self.botData[ruedaType]['sizeDisponible']}")
                self.log.info("sumar size disponible en rueda contraria")
                self.botData[ruedaContraria]["sizeDisponible"] = self.botData[ruedaContraria]["sizeDisponible"] + size
        except Exception as e:
            self.log.error(f"error guardando mitad rueda:{e}")
