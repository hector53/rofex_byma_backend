import datetime
import asyncio
from collections import defaultdict
from typing import DefaultDict,  Dict
from threading import Thread
from app.clases.class_client_request import client_request
import logging
import time
import pyRofex
"""
limit CI ASK = 48h ASK
limit CI BI = 48h BI
limit 48h ASK = CI ASK
limit 48h BI = CI BI 
"""
class botCi48Caucion(Thread):
    def __init__(self, bymaCI, byma48h, caucion, minimum_arbitrage_rate, maximum_arbitrage_rate, f, id_bot):#f=instancia de fix, id_bot= id del bot que se está ejecutando
        Thread.__init__(self)
        self.clientR = client_request(f, id_bot) #instancia de la clase client_request
        self.minimum_arbitrage_rate = float(minimum_arbitrage_rate)
        self.maximum_arbitrage_rate = float(maximum_arbitrage_rate)
        self._tickers: DefaultDict[str, Dict[str, float]] = defaultdict(dict) #diccionario de diccionarios donde estaran los datos del book suscritos
        self.log = logging.getLogger(f"tasa_inversa_bot_{id_bot}")#log para el bot
        self.botData = {#diccionario con las variables q el bot usará 
                        "id_bot": id_bot,#lo uso para guardar el id en db y asi poder seguir las ordenes de cada bot
                        "posiciones": {bymaCI: {"BI": 0, "OF": 0}, byma48h: {"BI": 0, "OF": 0}, caucion: {"BI": 0, "OF": 0}},#diccionario con las posiciones de los book
                        "detener": False,#la uso para detener el bot
                        "botIniciado": None,#la uso para en el dashboard saber q el bot ya inicio correctamente o no
                        "bymaCI": bymaCI,#los valores de los book que se van a suscribir
                        "byma48h": byma48h,#los valores de los book que se van a suscribir
                        "caucion": caucion,#los valores de los book que se van a suscribir
                        "ordenOperada": False, #la uso para saber si ya se opero una orden
                        "llegoTickers": False, #la uso para saber si ya llegaron los tickers
                        "bookChangeTime": None,#la uso para marcar el tiempo despues de un cambio de mercado, 
                        "symbols2": [bymaCI, byma48h, caucion],#los valores de los book que se van a suscribir], 
                        "sizeOnly1": True, 
                        "pegados": [],
                       # "ordenesBot": [], 
                        "idPegadas": 0, 
                        "editandoBot": False,
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
                        } 

    async def verificar_48h(self, side):
        self.log.info(f"ver botData: {self.botData}")
        sideText = "Buy"
        sideBook = "BI"
        sideOrder = 1
        if side == "Sell":
            sideText = "Sell"
            sideBook = "OF"
            sideOrder = 2

        self.log.info(f"entrando a verificar 48h: {side}")
        #necesito verificar si tengo una orden creada , y de ser asi modificar y sino crear
        #aqui busco en db si tengo una orden limit creada en el book byma48h
        verificarOrdenCreada = await self.clientR.get_order_limit_by_symbol_side(self.botData["byma48h"], sideText, 0,0) 
        #esta funcion me devuelve un diccionario con status y data, la data viene de la db y es un diccionario con los datos de la orden
        if verificarOrdenCreada["status"]==True:#si tengo orden creada
            orden =  verificarOrdenCreada["data"] #guardo los datos de la orden
            self.log.info("tengo orden creada")
            #verificar caucion
            verificarCaucion = await self.verificarCaucion("48",sideBook)
            if verificarCaucion["status"]==False:
                self.log.info("no hay caucion suficiente, o la unica q hay es mia ")
                #cancelar ordenes en ci bi y 48h of en dado caso q sea BI el q estoy revisando
                if sideBook=="OF":
                    #cancelar ordenes en ci bi y 48h of
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(self.botData["bymaCI"], "Buy")
                    self.log.info(f"cancelar orden en CI BI: {cancelarOrden}")
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(self.botData["byma48h"], "Sell")
                    self.log.info(f"cancelar orden en 48 Sell: {cancelarOrden}")
                else:
                    #cancelar ordenes en ci of y 48h bi
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(self.botData["bymaCI"], "Sell")
                    self.log.info(f"cancelar orden en CI OF: {cancelarOrden}")
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(self.botData["byma48h"], "Buy")
                    self.log.info(f"cancelar orden en 48 BI: {cancelarOrden}")
                return
            #verifico si puedo operar, aqui va consultar la data del book con la data de la db y ver si puedo operar
            #me va arrojar un diccionario con status y indice, si status es True entonces puedo operar y el indice es el indice del book q puedo tomar sus valores
            verificarOperar =  await self.clientR.verificar_ordenes_futuro(self.botData["bymaCI"], sideBook, self._tickers[self.botData["bymaCI"]][sideBook])
            if verificarOperar["status"]==True:
                self.log.info(f"puedo crear orden en 48h: {sideBook}")
                indice = verificarOperar["indice"]  #indice del book q puedo tomar sus valores
                market_price_CI = self._tickers[self.botData["bymaCI"]][sideBook][indice]["price"] #precio del book q puedo tomar sus valores
                size_CI = self._tickers[self.botData["bymaCI"]][sideBook][indice]["size"]#size del book q puedo tomar sus valores
                limit_price_CI, volume_limit_CI = self.calculate_limit_asset_price_48h(market_price_CI,size_CI, sideBook) #calculo el precio y size de la orden
                self.log.info(f"Limit CI: {limit_price_CI}, Volume: {volume_limit_CI} ") 
                if volume_limit_CI<=0:
                    self.log.info("no hago nada xq el size es menor o igual a 0")
                    return
                if round(orden['price'],1) != round(limit_price_CI,1) or orden['leavesQty'] != volume_limit_CI:#verifico si el precio o size son diferentes del q tengo actualmente
                    self.log.info("si el precio o size son diferentes del q tengo actualmente entonces modifico la orden")
                    if self.botData["ordenOperada"] == False:#verifico si hay una orden operada en proceso
                        modificarOrden = await self.clientR.modificar_orden(orden['orderId'], orden['clOrdId'],sideOrder, 2, self.botData["byma48h"],
                                                volume_limit_CI, limit_price_CI) #modifico la orden
                        self.log.info(f"orden modificada {modificarOrden}")
                    else:
                        self.log.info(f"hay una orden operada en proceso")
                else: 
                    self.log.info("no hago nada xq el precio y size son iguales al q tengo actualmente")
            else:
                self.log.info("cancelar orden haberla todo depende :D  ")
                self.log.info(f"estoy en ci: {side}")
                if side=="Buy":
                    self.log.info("cancelar orden en 48 buy")
                    self.log.info(f"cancelar orden en 48 buy: {orden['orderId']}")
                    cancelarOrden = await self.clientR.cancelar_orden(orden['orderId'], orden['clOrdId'], 1, 2, self.botData["byma48h"])
                    self.log.info(f"cancelar orden en ci buy: {cancelarOrden}")
                else:#es sell
                    self.log.info("cancelar orden en 48 sell")
                    self.log.info(f"cancelar orden en 48 sell: {orden['orderId']}")
                    cancelarOrden = await self.clientR.cancelar_orden(orden['orderId'], orden['clOrdId'], 2, 2, self.botData["byma48h"])
                    self.log.info(f"cancelar orden en 48 sell: {cancelarOrden}")
        else:
            self.log.info("no tengo orden creada")
            verificarCaucion = await self.verificarCaucion("48",sideBook)
            if verificarCaucion["status"]==False:
                self.log.info("no hay caucion suficiente, o la unica q hay es mia ")
                return
            posicionBymaCI = self.botData["posiciones"][self.botData["bymaCI"]]["BI"] - self.botData["posiciones"][self.botData["bymaCI"]]["OF"]
            if sideBook=="BI":
                #verificar antes por una orden pegada
                #verificar la cantidad de las posiciones en el book bymaCI
                if posicionBymaCI==0:
                    self.log.info("no hay nada en CI BI")#x ende no puedo crear una orden de compra 48 xq no tengo nada en ci posicion
                    #por ende no me pueden tomar mi orden xq si lo hacen no puedo vender ci
                    return
            if sideBook=="OF":
                posicion48h = self.botData["posiciones"][self.botData["byma48h"]]["BI"] - self.botData["posiciones"][self.botData["byma48h"]]["OF"]
                if posicion48h<=0:
                    self.log.info("no hay nada en 48h BI")
                    return
                    
            #verifico si puedo operar 
            #me va arrojar un diccionario con status y indice, si status es True entonces puedo operar y el indice es el indice del book q puedo tomar sus valores
            verificarOperar =  await self.clientR.verificar_ordenes_futuro(self.botData["bymaCI"], sideBook, self._tickers[self.botData["bymaCI"]][sideBook])
            if verificarOperar["status"]==True:#si puedo operar
                self.log.info(f"puedo crear orden en 48h: {sideBook} ")
                indice = verificarOperar["indice"]  #indice del book q puedo tomar sus valores
                market_price_CI = self._tickers[self.botData["bymaCI"]][sideBook][indice]["price"] #precio del book q puedo tomar sus valores
                size_CI = self._tickers[self.botData["bymaCI"]][sideBook][indice]["size"]#size del book q puedo tomar sus valores
                limit_price_CI, volume_limit_CI = self.calculate_limit_asset_price_48h(market_price_CI,size_CI, sideBook) #calculo el precio y size de la orden
                self.log.info(f"Limit CI: {limit_price_CI}, Volume: {volume_limit_CI} ") 
                if volume_limit_CI<=0:
                    self.log.info("no hago nada xq el size es menor o igual a 0")
                    return
                #creo la orden: symbol, side:1=buy:2=sell, volume, price, order_type:2=limit, id_bot
                if self.botData["ordenOperada"] == False:#verifico si hay una orden operada en proceso
                    if posicionBymaCI>=volume_limit_CI:
                        #ordenNueva = await self.clientR.nueva_orden(self.botData["byma48h"],sideOrder, volume_limit_CI, limit_price_CI, 2)#creo la orden
                        ordenNueva = await self.clientR.nueva_orden(self.botData["byma48h"],sideOrder, volume_limit_CI, limit_price_CI, 2)#creo la orden
                        self.log.info(f"orden nueva {ordenNueva}")
                    else:
                        self.log.info(f"no puedo crear la orden xq no tengo suficiente size en ci")
                else:
                    self.log.info(f"hay una orden operada en proceso")
            else:
                self.log.info("no hago nada xq no tengo nada en CI BI y no tengo orden creada")

    async def verificar_ci(self, side):
        self.log.info(f"entrando a verificar ci: {side}")
        self.log.info(f"ver botData: {self.botData}")
        sideText = "Buy"
        sideBook = "BI"
        sideOrder = 1
        if side == "Sell":
            sideText = "Sell"
            sideBook = "OF"
            sideOrder = 2
        #necesito verificar si tengo una orden creada , y de ser asi modificar y sino crear
        #aqui busco en db si tengo una orden limit creada en el book bymaCI
        verificarOrdenCreada = await self.clientR.get_order_limit_by_symbol_side(self.botData["bymaCI"], sideText, 0,0) 
        #esta funcion me devuelve un diccionario con status y data, la data viene de la db y es un diccionario con los datos de la orden
        if verificarOrdenCreada["status"]==True:#si tengo orden creada
            orden =  verificarOrdenCreada["data"] #guardo los datos de la orden
            self.log.info("tengo orden creada")
            #verificar caucion
            verificarCaucion = await self.verificarCaucion("CI",sideBook)
            if verificarCaucion["status"]==False:
                self.log.info("no hay caucion suficiente, o la unica q hay es mia ")
                #cancelar ordenes en ci bi y 48h of en dado caso q sea BI el q estoy revisando
                if sideBook=="BI":
                    #cancelar ordenes en ci bi y 48h of
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(self.botData["bymaCI"], "Buy")
                    self.log.info(f"cancelar orden en CI BI: {cancelarOrden}")
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(self.botData["byma48h"], "Sell")
                    self.log.info(f"cancelar orden en 48 Sell: {cancelarOrden}")
                else:
                    #cancelar ordenes en ci of y 48h bi
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(self.botData["bymaCI"], "Sell")
                    self.log.info(f"cancelar orden en CI OF: {cancelarOrden}")
                    cancelarOrden = await self.clientR.cancelar_orden_haberla(self.botData["byma48h"], "Buy")
                    self.log.info(f"cancelar orden en 48 BI: {cancelarOrden}")
                return
                

            #verifico si puedo operar, aqui va consultar la data del book con la data de la db y ver si puedo operar
            #me va arrojar un diccionario con status y indice, si status es True entonces puedo operar y el indice es el indice del book q puedo tomar sus valores
            verificarOperar =  await self.clientR.verificar_ordenes_futuro(self.botData["byma48h"], sideBook, self._tickers[self.botData["byma48h"]][sideBook])
            if verificarOperar["status"]==True:
                self.log.info(f"puedo crear orden en CI: {sideBook}")
                indice = verificarOperar["indice"]  #indice del book q puedo tomar sus valores
                market_price_48h = self._tickers[self.botData["byma48h"]][sideBook][indice]["price"] #precio del book q puedo tomar sus valores
                size_48h = self._tickers[self.botData["byma48h"]][sideBook][indice]["size"]#size del book q puedo tomar sus valores
                limit_price_CI, volume_limit_CI = self.calculate_limit_asset_price_CI(market_price_48h,size_48h, sideBook ) #calculo el precio y size de la orden
                self.log.info(f"Limit CI: {limit_price_CI}, Volume: {volume_limit_CI} ") 
                if volume_limit_CI<=0:
                    self.log.info("no hago nada xq el size es menor o igual a 0")
                    return
                if round(orden['price'],1) != round(limit_price_CI,1) or orden['leavesQty'] != volume_limit_CI:#verifico si el precio o size son diferentes del q tengo actualmente
                    self.log.info("si el precio o size son diferentes del q tengo actualmente entonces modifico la orden")
                    if self.botData["ordenOperada"] == False:#verifico si hay una orden operada en proceso
                        modificarOrden = await self.clientR.modificar_orden(orden['orderId'], orden['clOrdId'],sideOrder, 2, self.botData["bymaCI"],
                                                volume_limit_CI, limit_price_CI) #modifico la orden
                        self.log.info(f"orden modificada {modificarOrden}")
                    else:
                        self.log.info(f"hay una orden operada en proceso")
                else: 
                    self.log.info("no hago nada xq el precio y size son iguales al q tengo actualmente")
            else:
                self.log.info("cancelar orden haberla todo depende :D  ")
                self.log.info(f"estoy en 48: {side}")
                if side=="Buy":
                    self.log.info("cancelar orden en ci buy")
                    self.log.info(f"cancelar orden en ci buy: {orden['orderId']}")
                    cancelarOrden = await self.clientR.cancelar_orden(orden['orderId'], orden['clOrdId'], 1, 2, self.botData["bymaCI"])
                    self.log.info(f"cancelar orden en ci buy: {cancelarOrden}")
                else:#es sell
                    self.log.info("cancelar orden en ci sell")
                    self.log.info(f"cancelar orden en ci sell: {orden['orderId']}")
                    cancelarOrden = await self.clientR.cancelar_orden(orden['orderId'], orden['clOrdId'], 2, 2, self.botData["bymaCI"])
                    self.log.info(f"cancelar orden en ci sell: {cancelarOrden}")
        else:
            self.log.info("no tengo orden creada")
            #verificar la caucion en el book a ver si hay suficiente para crear la orden
            verificarCaucion = await self.verificarCaucion("CI",sideBook)
            if verificarCaucion["status"]==False:
                self.log.info("no hay caucion suficiente, o la unica q hay es mia ")
                return
            posicionBymaCI = self.botData["posiciones"][self.botData["bymaCI"]]["BI"] - self.botData["posiciones"][self.botData["bymaCI"]]["OF"]
            posicion48h = self.botData["posiciones"][self.botData["byma48h"]]["BI"] - self.botData["posiciones"][self.botData["byma48h"]]["OF"]
            saldoBi = posicionBymaCI - posicion48h
            if sideBook=="OF":
                #verificar la cantidad de las posiciones en el book bymaCI
                if saldoBi<=0:
                    self.log.info("no hay nada en CI BI o esta calzado con 48")#x ende no puedo crear una orden de venta en CI
                    return
            
            

            #verifico si puedo operar 
            #me va arrojar un diccionario con status y indice, si status es True entonces puedo operar y el indice es el indice del book q puedo tomar sus valores
            verificarOperar =  await self.clientR.verificar_ordenes_futuro(self.botData["byma48h"], sideBook, self._tickers[self.botData["byma48h"]][sideBook])
            if verificarOperar["status"]==True:#si puedo operar
                self.log.info(f"puedo crear orden en CI: {sideBook}")
                indice = verificarOperar["indice"]  #indice del book q puedo tomar sus valores
                market_price_48h = self._tickers[self.botData["byma48h"]][sideBook][indice]["price"] #precio del book q puedo tomar sus valores
                size_48h = self._tickers[self.botData["byma48h"]][sideBook][indice]["size"]#size del book q puedo tomar sus valores
                limit_price_CI, volume_limit_CI = self.calculate_limit_asset_price_CI(market_price_48h,size_48h, sideBook)#calculo el precio y size de la orden
                self.log.info(f"Limit CI: {limit_price_CI}, Volume: {volume_limit_CI} ") #muestro el precio y size de la orden
                #creo la orden: symbol, side:1=buy:2=sell, volume, price, order_type:2=limit, id_bot
                if volume_limit_CI<=0:
                    self.log.info("no hago nada xq el size es menor o igual a 0")
                    return
                if self.botData["ordenOperada"] == False:#verifico si hay una orden operada en proceso
                    #ahora aqui debo validar q el size q tengo en las posiciones sea mayor o igual al q voy a realizar
                    if sideBook=="OF":
                        if posicionBymaCI<=volume_limit_CI: 
                            self.log.info("no hago nada xq no tengo suficiente size en las posiciones")
                            return #no hago nada xq no tengo suficiente size en las posiciones
                    ordenNueva = await self.clientR.nueva_orden(self.botData["bymaCI"], sideOrder, volume_limit_CI,
                                                                limit_price_CI, 2)#creo la orden
                 #   ordenNueva = await self.clientR.nueva_orden(self.botData["bymaCI"], sideOrder, volume_limit_CI,
                          #                                      limit_price_CI, 2)#creo la orden
                    self.log.info(f"orden nueva {ordenNueva}")
                else:
                    self.log.info(f"hay una orden operada en proceso")
            else:
                self.log.info("no hago nada xq no tengo nada en 48h OF y no tengo orden creada en CI") 

    async def verificarCaucion(self, ci48, sideBook):
        sideBookCaucion = sideBook
        if ci48=="CI":
            self.log.info("es ci")
            if sideBook=="BI":
                self.log.info("es bi")
                sideBookCaucion = "OF"
            else:
                self.log.info("es of")
                sideBookCaucion = "BI"
        verificarCaucion = await self.clientR.verificar_ordenes_futuro(self.botData["caucion"], sideBookCaucion, self._tickers[self.botData["caucion"]][sideBookCaucion])
        return verificarCaucion
                
    async def verificar_puntas(self):
        if self.botData["ordenOperada"]==False:
            verificar_ci = await self.verificar_ci("Buy") #aqui voy a verificar si tengo orden abierta en ci la modifico y si no la creo
        if self.botData["ordenOperada"]==False:
            verificar_ci = await self.verificar_ci("Sell")
        if self.botData["ordenOperada"]==False:
            verificar_48h = await self.verificar_48h("Buy") #aqui voy a verificar si tengo orden abierta en 48h la modifico y si no la creo
        if self.botData["ordenOperada"]==False:
            verificar_48h = await self.verificar_48h("Sell")

    async def guardar_posiciones(self, posiciones):
        self.log.info("voy a guardar posiciones")
        for posicion in posiciones["positions"]:
            if posicion["tradingSymbol"] == self.botData["bymaCI"]:
            #    "posiciones": {bymaCI: {"BI": 0, "OF": 0}, byma48h: {"BI": 0, "OF": 0}}
            #{"BI": posicion["buySize"], "OF": posicion["sellSize"]}
                self.botData["posiciones"][self.botData["bymaCI"]]["BI"] = posicion["buySize"]
                self.botData["posiciones"][self.botData["bymaCI"]]["OF"] = posicion["sellSize"]
            if posicion["tradingSymbol"] == self.botData["byma48h"]:
                self.botData["posiciones"][self.botData["byma48h"]]["BI"] = posicion["buySize"]
                self.botData["posiciones"][self.botData["byma48h"]]["OF"] = posicion["sellSize"]

    async def ejecutar_bot(self):
        self.log.info("voy a probar get posiciones por rest ")
        posiciones = pyRofex.get_account_position()
        self.log.info(f"posiciones: {posiciones}")
        await self.guardar_posiciones(posiciones)
        self.log.info(f"posiciones botData: {self.botData['posiciones']}")
        
        self.log.info(f"ejecutando bot id: {self.botData['id_bot']} ")
        
        self.log.info(f"primero suscribir al mercado ")
        suscribir = await self.clientR.suscribir_mercado([self.botData["bymaCI"], self.botData["byma48h"] ] )
        if suscribir["status"]==True:
            self.log.info("suscribir mercado ok")
            self.botData["botIniciado"] = True 
            self.log.info("bot iniciado ok")
            #en este punto ya tengo los tickers suscritos
            while True: 
                time.sleep(0.1)
                if self.botData["detener"] == True:
                    self.log.info("deteniendo bot")
                    #en la funcion de arriba vamos a guardar en db que el bot se detuvo
                    #pero antes vamos a ver si tenemos ordenes abiertas y cerrarlas todas
                    #tambien nos vamos a desconectar del mercado
                    #luego si actualizamos db y salir del ciclo while
                    break  
                #self.log.info(f"voy a verificar si esta activo lo de soloEscucharMercado: {self.botData['soloEscucharMercado']} ")
                if self.botData["soloEscucharMercado"]==True:
                 #   self.log.info(f"esta activo")
                    continue
                
                #continuamos 
                if self.botData["ordenOperada"]==False:#si no hay orden operada puedo continuar normal
                    if self.botData["llegoTickers"] == True:#hubo un cambio en el book, en alguno de los tickers suscritos
                        self.log.info("llego tickers")
                        await self.verificar_puntas()
                        self.botData["llegoTickers"] = False #pongo en falso para q no vuelva a entrar a este if
                        self.botData["bookChangeTime"] = time.time()#pongo el tiempo de cambio de book
                        self.log.info("terminamos de verificar por cambio de mercado")
                    else:
                        if self.botData["editandoBot"] == True:
                            self.log.info(f"actualizaron datos del bot, id: {self.clientR.id_bot}")
                            ordenes =  await self.verificar_puntas()
                            self.botData["inicioTime"] = time.time()
                            self.botData["editandoBot"] = False

                        self.log.info("no ha habido cambio de mercado")
                        #aqui ejecuto un timer de 10 seg para verificar lo mismo como si hubiese habido un cambio de mercado, x si acaso hubo un error lo corrija
                        finTimeStatus = time.time()
                        tiempoLimitStatus = finTimeStatus-self.botData["bookChangeTime"]
                        if tiempoLimitStatus>=10:
                            self.log.info("vamos a verificar ordenes por tiempo de 10 seg")
                            await self.verificar_puntas()
                            self.botData["bookChangeTime"] = time.time()
                            self.log.info("terminamos de verificar por tiempo")
                else:
                    self.log.info("orden operada en proceso")
                    #cuando la orden operada esta en proceso se va estar ejecutando otra funcion 
                    #es decir el motor de fix nos envia a la funcion (pasar_orden_operada) los datos 
        else:
            #si no se pudo suscribir al mercado, no se puede ejecutar el bot
            self.log.info("no se pudo suscribir al mercado")
            self.botIniciado = False

    def run(self):
        loop = asyncio.new_event_loop()# creo un nuevo evento para asyncio y asi ejecutar todo de aqui en adelante con async await 
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.ejecutar_bot())#ejecuto la funcion q quiero en este caso la de ejecutar_bot
        loop.close()

    def pasar_orden_operada(self, details, type=0):
            self.log.info(f"pasando orden operada, details: {details}, type: {type}")
            loop = asyncio.new_event_loop()# creo un nuevo evento para asyncio y asi ejecutar todo de aqui en adelante con async await 
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.verificar_orden_operada(details, type))#ejecuto la funcion q quiero
            loop.close()

    async def actualizar_posiciones(self, details):
        self.log.info(f"actualizando posiciones")
        size = int(details["lastQty"])
        if details["side"] == "Buy":
            self.botData["posiciones"][details["symbol"]]["BI"] = self.botData["posiciones"][details["symbol"]]["BI"] + size
        else:
            self.botData["posiciones"][details["symbol"]]["OF"] = self.botData["posiciones"][details["symbol"]]["OF"] + size
        self.log.info(f"posiciones actualizadas: {self.botData['posiciones']}")

    async def  verificar_orden_operada(self, details, type=0):
        self.log.info(f"verificando orden operada, orden: {details}, type: {type}")
        if int(type) == 0:
            self.log.info("si es 0")
            await self.actualizar_posiciones(details)
        self.log.info(f"verificando orden operada del id_bot: {self.clientR.id_bot}")
        self.log.info("primero vamos a desintegrar el client order id para guardar el id de la orden y para comprobar si es de la estrategia o del bot ")
        clOrdIdSplit = str(details["clOrdId"]).split("-")
        if len(clOrdIdSplit)>1:
            self.log.info("es una orden el bot")
            typeOrder = clOrdIdSplit[0]#"N or B" N=New order , B= order segundo paso, la market limit
            id_order = clOrdIdSplit[1]#id de la orden , N-1: id = 1
            if typeOrder == "N":
                self.log.info("es orden normal de la estrategia ")
                self.botData["ordenOperada"] = True
                self.log.info("ahora guardar los cambios en db ")
                await self.clientR.actualizar_order_by_change(details["orderId"], details)
                await self.guardar_mitad_rueda(details)
                self.log.info("ahora operar la contraria ")
                await self.operar_orden(details, id_order)
            
            elif typeOrder == "B":
                #bueno esta es una orden contraria, aqui debo verificar si es una orden parcialmente filled 
                #si lastQty < cumQty entonces es una orden parcialmente filled
                #si lastQty == cumQty entonces es una orden completamente filled
                if details["orderQty"] == details["cumQty"]:
                    self.log.info("es orden del bot completamente filled ")
                    id_contraria = clOrdIdSplit[2]
                    self.log.info("es orden del bot la orden contraria ")
                #    self.log.info("primero guardar en db ordenes ")
                #    self.log.info(f"""voy a verificar si es type 1, para ver si es una orden limit new,
                 #   q me indica q es una orden pegada y guardar y activar lo de orden pegada 
                #    """)
                    
                 #   type_order = 1
                  #  if type==1:
                   #     type_order = 0
                     #   self.log.info("si es type 1")
                      #  await self.guardar_orden_pegada(details, id_order, id_contraria )
                       # self.log.info("la orden se quedo pegada ")
                    
                  #  elif type==0:

                    #si es una orden totalmente operada, debemos averiguar si forma parte de una orden pegada o no
                    #entonces buscar por el clOrdId en la db y status 0 q es de pendiente 
                    #si no hay ninguna orden pendiente entonces es una orden normal
                    #si hay una orden pendiente entonces es una orden pegada
                    orderDb = await self.clientR.get_order_pendiente_by_clOrdId(details["clOrdId"])
                    if orderDb["status"]==True: 
                        self.log.info("es una orden pegada, entonces esa orden pegada se completo en su totalidad")
                        #necesitamos el size pendiente de la orden pegada
                        sizePendiente = int(orderDb["leavesQty"])
                        #ese size pendiente se completo por lo tanto lo vamos a reflejar en las ruedas para q aumente
                        #o disminuya el size disponible 
                        await self.guardar_mitad_rueda(details,  1, sizePendiente)
                        #ahora vamos a actualizar la orden vieja 
                        ordenVieja = await self.clientR.filled_orden_vieja(orderDb["id"])
                    else:
                        self.log.info(f"no es una orden q estaba pegada por lo tanto descuento normal de la rueda ")
                        await self.guardar_mitad_rueda(details,  1, int(details["cumQty"]))
                    self.log.info("es operada, osea q es una contraria correctamente ejecutada")
                    newOrder = await self.clientR.guardar_orden_nueva_in_db(details, 1, 1 )
                    self.botData["ordenOperada"] = False
                else:
                    self.log.info("es orden del bot parcialmente filled ")
                    orderDb = await self.clientR.get_order_pendiente_by_clOrdId(details["clOrdId"])
                    if orderDb["status"]==True: 
                        self.log.info("es una orden pegada, entonces esa orden pegada q sigue parcialmente filled ")
                        #necesitamos el size pendiente de la orden pegada
                        sizePendienteViejo = int(orderDb["leavesQty"]) #size pendiente viejo 
                        sizePendienteNuevo = int(details["leavesQty"])
                        sizePendiente = sizePendienteViejo - sizePendienteNuevo
                        #ese size pendiente se completo por lo tanto lo vamos a reflejar en las ruedas para q aumente
                        #o disminuya el size disponible 
                        await self.guardar_mitad_rueda(details,  1, sizePendiente)
                        #ahora vamos a actualizar la orden vieja 
                        ordenVieja = await self.clientR.filled_orden_vieja(orderDb["id"])
                    else:
                        self.log.info(f"no es una orden q estaba pegada por lo tanto descuento normal de la rueda ")
                        await self.guardar_mitad_rueda(details,  1, int(details["cumQty"]))
                  #  self.log.info("ahora guardar en db ordenes pegadas ")
                 #   await self.guardar_orden_pegada(details, id_order, id_contraria )
                   # self.log.info("la orden se quedo pegada ")
                    newOrder = await self.clientR.guardar_orden_nueva_in_db(details, 0, 1 )
                    self.botData["ordenOperada"] = False
                    
    async def guardar_mitad_rueda(self, details, descontar=0, sizePendiente=0):
        self.log.info("guardar_mitad_rueda")
        #debo primero averiguar a q lado de la rueda pertenece la orden 
        #para eso voy a comparar el simbolo de la orden con el simbolo de la rueda
        #si el simbolo de la orden es igual CI con el side BI entonces es de rueda A, o 
        ruedaType = "ruedaA"
        ruedaContraria = "ruedaB"
        if details["symbol"]==self.botData["byma48h"] and details["side"]=="Buy":
            ruedaType = "ruedaB"
            ruedaContraria = "ruedaA"
        elif details["symbol"]==self.botData["bymaCI"] and details["side"]=="Sell":
            ruedaType = "ruedaB"
            ruedaContraria = "ruedaA"
        self.log.info(f"ruedaType: {ruedaType}")
        #guardar orden 
        self.log.info("guardar orden en el lado de la rueda")
        self.botData[ruedaType]["ordenes"].append(details)
        self.log.info(f"ordenes de la rueda: {self.botData[ruedaType]['ordenes']}")
        #descontar sizedisponible 
        if descontar==1: 
            self.log.info("descontar size disponible")
            size = sizePendiente
            self.botData[ruedaType]["sizeDisponible"] = self.botData[ruedaType]["sizeDisponible"] - size
            self.log.info(f"size disponible: {self.botData[ruedaType]['sizeDisponible']}")
            self.log.info("sumar size disponible en rueda contraria")
            self.botData[ruedaContraria]["sizeDisponible"] = self.botData[ruedaContraria]["sizeDisponible"] + size

   
    async def  operar_orden(self, orden, id_order):
        if orden["symbol"]==self.botData["bymaCI"]:
            self.log.info("bymaCI")
            if orden["side"]=="Buy":
                self.log.info("Buy")
                self.log.info("ahora operar la contraria pero en 48h OF ")
                await self.operar_orden_contraria(orden, self.botData["byma48h"], "BI", id_order, 2)
            else:
                #es sell
                self.log.info("Sell")
                self.log.info("ahora operar la contraria pero en 48h BI ")
                await self.operar_orden_contraria(orden, self.botData["byma48h"], "OF", id_order, 1)
        else:
            #es byma48h
            self.log.info("byma48h")
            if orden["side"]=="Buy":
                self.log.info("Buy")
                self.log.info("ahora operar la contraria pero en CI OF ")
                await self.operar_orden_contraria(orden, self.botData["bymaCI"], "BI", id_order, 2)
            else:
                #es sell
                self.log.info("Sell")
                self.log.info("ahora operar la contraria pero en CI BI ")
                await self.operar_orden_contraria(orden, self.botData["bymaCI"], "OF", id_order, 1)

    async def operar_orden_contraria(self, orden, symbolCheck, sideCheck, id_order, sideOrder):
        self.log.info(f"operar orden contraria del id_bot: {self.clientR.id_bot}")
        self.log.info(f"orden {orden}")
        self.log.info(f"necesito el symbol: {symbolCheck}")
        self.log.info(f"necesito el side: {sideCheck} para poder hacer el market del otro lado")
        self.log.info(f"id_order: {id_order}")
        self.log.info(f"sideOrder: {sideOrder}")
        verifyF = await self.clientR.verificar_ordenes_futuro(symbolCheck, sideCheck, self._tickers[symbolCheck][sideCheck])
        if verifyF["status"]==True:
            self.log.info("si hay ordenes en el simbolo y en el side que necesito")
            size = orden["lastQty"]
            indiceBook = verifyF["indice"]
            priceOrder = self._tickers[symbolCheck][sideCheck][indiceBook]["price"]
            self.log.info(f"priceFuturo: {priceOrder}")
            clOrdId = self.clientR.fix.getNextOrderBotID(id_order)
         #   self.botData["ordenesBot"].append({"idOperada":id_order, "clOrdId": clOrdId, "size": size })
            ordenNew = self.clientR.fix.newOrderSingle(clOrdId,symbolCheck, sideOrder, size, priceOrder, 2 )
            self.log.info(f"ordenNew: {ordenNew}")
        else:
            size = orden["lastQty"]
            self.log.info(f"no puedo operar xq no hay ordenes en el simbolo y en el side que necesito")
            sideForPrice = "BI"
            if sideCheck=="BI":
                sideForPrice = "OF"
            limit_price, volume_limit = self.calculate_limit_asset_price_48h(orden["price"], orden["lastQty"], sideForPrice)
            self.log.info(f"priceFuturo: {limit_price}")
            clOrdId = self.clientR.fix.getNextOrderBotID(id_order)
          #  self.botData["ordenesBot"].append({"idOperada":id_order, "clOrdId": clOrdId, "size": size })
            ordenNew = self.clientR.fix.newOrderSingle(clOrdId,symbolCheck, sideOrder, volume_limit, limit_price, 2 )
            self.log.info(f"ordenNew: {ordenNew}")

        
      

    def next_business_day(self, current_date):
        # Calcular el próximo día hábil a partir del día actual
        if current_date.weekday() >= 3:
            # Si es jueves, el próximo día hábil es el lunes
            next_day = current_date + datetime.timedelta(days=(7 - current_date.weekday()))
        else:
            # En otro caso, el próximo día hábil es el siguiente día
            next_day = current_date + datetime.timedelta(days=2)
        return next_day
    
    def calculate_limit_asset_price_CI(self, asset_price_48h, size_48h, sideBook):
        annualized_arbitrage_rate = self.minimum_arbitrage_rate
        volume = self.get_volume(size_48h)
        self.log.info(f"volume: {volume}")
        if sideBook=="BI": 
            self.log.info(f"sideBook BI")
            annualized_arbitrage_rate = self.maximum_arbitrage_rate
            if volume>self.botData["ruedaA"]["sizeDisponible"]:
                self.log.info(f"volume>self.botData['ruedaA']['sizeDisponible']")
                self.log.info(f"sizeDisponible ruedaA: {self.botData['ruedaA']['sizeDisponible']}")
                volume = self.botData["ruedaA"]["sizeDisponible"]
        else:
            self.log.info(f"sideBook OF")
            if volume>self.botData["ruedaB"]["sizeDisponible"]:
                self.log.info(f"volume>self.botData['ruedaB']['sizeDisponible']")
                self.log.info(f"sizeDisponible ruedaB: {self.botData['ruedaB']['sizeDisponible']}")
                volume = self.botData["ruedaB"]["sizeDisponible"]

        current_date = datetime.datetime.now().date()
        next_day = self.next_business_day(current_date)
        dias_restantes = (next_day - current_date).days
         
        limit_asset_price_CI = asset_price_48h - (annualized_arbitrage_rate * (dias_restantes + 0) / 365) * asset_price_48h
        return round(limit_asset_price_CI, 0), volume
    
    def calculate_limit_asset_price_48h(self, asset_price_CI, size_CI, sideBook):
        annualized_arbitrage_rate = self.minimum_arbitrage_rate
        volume = size_CI #self.get_volume(size_CI)
        self.log.info(f"volume: {volume}")
        if sideBook=="OF": 
            self.log.info(f"sideBook OF")
            annualized_arbitrage_rate = self.maximum_arbitrage_rate
            if volume>self.botData["ruedaA"]["sizeDisponible"]:
                self.log.info(f"volume>self.botData['ruedaA']['sizeDisponible']")
                self.log.info(f"sizeDisponible ruedaA: {self.botData['ruedaA']['sizeDisponible']}")
                volume = self.botData["ruedaA"]["sizeDisponible"]
        else:
            self.log.info(f"sideBook BI")
            if volume>self.botData["ruedaB"]["sizeDisponible"]:
                self.log.info(f"volume>self.botData['ruedaB']['sizeDisponible']")
                self.log.info(f"sizeDisponible ruedaB: {self.botData['ruedaB']['sizeDisponible']}")
                volume = self.botData["ruedaB"]["sizeDisponible"]
        current_date = datetime.datetime.now().date()
        next_day = self.next_business_day(current_date)
        dias_restantes = (next_day - current_date).days
        limit_asset_price_48h = asset_price_CI / (1 - (annualized_arbitrage_rate * (dias_restantes + 0) / 365))
        return round(limit_asset_price_48h, 0), volume
    
    def calculate_current_rate(self, market_price_CI, market_price_48h):
        current_date = datetime.datetime.now().date()
        next_day = self.next_business_day(current_date)
        dias_restantes = (next_day - current_date).days
        profit_48h = (market_price_48h - market_price_CI) / market_price_48h
        annualized_arbitrage_rate_48h = profit_48h * 365 / (dias_restantes + 0)
        return annualized_arbitrage_rate_48h
    
    def get_volume(self, size, max_volume=250000): # 250k es el máximo de volumen por operación, tiene que ser un input de otra función que revise balances de tenencias
        if size > max_volume:
            return max_volume
        else:
            return size
