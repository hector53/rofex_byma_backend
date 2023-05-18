import asyncio
from app.modulos_db import insert_data, updateData, updateTable, getData, getDataOne, getDataOnly
from collections import defaultdict
from typing import DefaultDict,   Dict, Tuple, Optional
import time
from threading import Thread
from datetime import datetime
import logging
from app.clases.class_client_request import client_request
from app.clases.botManager.taskSeqManager import taskSeqManager
class botTriangulo(taskSeqManager):
    def  __init__(self, futuro1, futuro2, pase, f, id_bot, cuenta, mongo) -> None:
        super().__init__()
        self.fix = f
        self.name = f"bot_{id_bot}"
        self.id = id_bot
        self.clientR = client_request(f, id_bot, cuenta,mongo)
        self.threadCola = None
        self.contadorOperada = 0
        self.botData = {
            "id_bot": id_bot,
            "cuenta": cuenta, 
            "futuro1": futuro1,
            "futuro2": futuro2,
            "paseFuturos": pase,
            "posiciones": {futuro1: {"BI": 0, "OF": 0}, futuro2: {"BI": 0, "OF": 0}},
            "idTriangulos": 0,
            "symbols": [futuro1, futuro2, pase],
            "symbols2": [futuro1, futuro2, pase],
            "llegoTickers": False,
            "pegados": [],
            "ordenOperada": False,
            "inicioTime": time.time(),
            "ordenesPrimarias": [],
            "vueltas": 0,
            "ordenesBot": [],
            "triangulosPegados": False,
            "onlySize1": True,
            "indices_futuros":{},#aqui almaceno el indice de la posicion que puedo usar para operar de cada simbolo bi y of
            "minMax": {},
            "varGan": 0.1,
            "sizeMax": 1,
            "market": False,
            "detener": False,#la uso para detener el bot
            "editandoBot": False,#la uso para saber si estoy editando el bot
            "botIniciado": None,#la uso para en el dashboard saber q el bot ya inicio correctamente o no
            "soloEscucharMercado": False,
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
        self._tickers: DefaultDict[str, Dict[str, float]] = defaultdict(dict)
        self.log = logging.getLogger(f"botLento_{id_bot}")
      #  self.suscribir_mercado()
        #funciones bot rapido 
    async def detenerBot(self):
        await self.stopCola()
        self.threadCola = None
        self.threadBB = None

    async def  calcular_limit_futuro1_ask(self, verificarFuturo1):
        self.log.info("entrando a calcular_limit_futuro1_ask")
        if len(self._tickers[self.botData["futuro2"]]["OF"])<(self.botData["indices_futuros"][self.botData["futuro2"]]["OF"]+1):
            self.log.info("en futuro2 ask hay una orden y es mia, o esta vacia ")
            return 0
        if len(self._tickers[self.botData["paseFuturos"]]["BI"])==0:
            self.log.info("en paseFuturos bid esta vacio")
            #si pase en este momento es 0 entonces me salgo 
            return 0
        #voy a guardar los indices q necesito en variables
        indicePaseBid = self.botData["indices_futuros"][self.botData["paseFuturos"]]["BI"]
        indiceFuturo2Ask = self.botData["indices_futuros"][self.botData["futuro2"]]["OF"]
        indiceFuturo1Ask = self.botData["indices_futuros"][self.botData["futuro1"]]["OF"]
        futuro2Ask = self._tickers[self.botData["futuro2"]]["OF"][indiceFuturo2Ask]["price"]
        paseFuturosBid = self._tickers[self.botData["paseFuturos"]]["BI"][indicePaseBid]["price"]
        precioMaxGanAskFuturo1 = futuro2Ask - paseFuturosBid
        futuro2AskSize = self._tickers[self.botData["futuro2"]]["OF"][indiceFuturo2Ask]["size"]
        self.log.info(f"futuro2Ask:{futuro2Ask}, paseFuturosBid: {paseFuturosBid}, precioMaxGanAskFuturo1: {precioMaxGanAskFuturo1} ")
        futuro1Ask = 0
        if verificarFuturo1["puedoOperar"]==True:
            futuro1Ask = self._tickers[self.botData["futuro1"]]["OF"][indiceFuturo1Ask]["price"]
        limitAskFuturo1 = 0
        if futuro1Ask > 0 and futuro1Ask > precioMaxGanAskFuturo1 and (futuro1Ask-precioMaxGanAskFuturo1)>0.11:
            limitAskFuturo1 = futuro1Ask-self.botData["varGan"]
            #verificar lo del spread 
            #necesito el bid
            self.log.info("voy a comprobar lo del spread")
            verificarFuturo1x =  await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "BI", self._tickers[self.botData["futuro1"]]["BI"]) 
            if verificarFuturo1x["puedoOperar"]==True:
                indiceFuturo1Bid = verificarFuturo1x["indiceBookUsar"]
                bookContrario = self._tickers[self.botData["futuro1"]]["BI"][indiceFuturo1Bid]["price"]
                if float(bookContrario) - float(futuro1Ask) >=0:
                    self.log.info("tengo spread 0 o 0.1")
                    limitAskFuturo1 = futuro1Ask
            else:
                self.log.info("no hay bid en el futuro1")
        elif (futuro1Ask-precioMaxGanAskFuturo1)==0.10 and futuro1Ask >0:
            self.log.info("tengo spread 0.1")
            limitAskFuturo1 = self.futuro1Ask
        elif futuro1Ask ==0:
            self.log.info("no hay ask en el futuro1")
            limitAskFuturo1 = (futuro2Ask + paseFuturosBid) + self.botData["varGan"]
        else:
            self.log.info("no hay spread")
            limitTrue =  futuro1Ask-self.botData["varGan"]
            limitTrueMax = float(self.botData["minMax"][self.botData["futuro1"]]["highLimitPrice"])
            limitTrueMin = float(self.botData["minMax"][self.botData["futuro1"]]["lowLimitPrice"])
            self.log.info(f"limitTrue: {limitTrue}, limitTrueMax:{limitTrueMax}, limitTrueMin:{limitTrueMin}")
            limitAskFuturo1 = precioMaxGanAskFuturo1+self.botData["varGan"]
            self.log.info(f"limitAskFuturo1:{limitAskFuturo1}")
            if futuro1Ask != 0: 
                if limitAskFuturo1 <=limitTrueMin or limitAskFuturo1>=limitTrueMax:
                    self.log.info("no estoy en los valores de limites maximos y minimos :D ")
                    return 0
        limitAskFuturo1 = round(limitAskFuturo1,1)
        self.log.info(f"futuro1Ask:{futuro1Ask},limitAskFuturo1:{limitAskFuturo1}")
        self.update_limits("CI", limitAskFuturo1, "OF")
        return limitAskFuturo1
    
    async def  calcular_limit_futuro1_bid(self, verificarFuturo1):
        #en este putno ya tengo valores en pase of y futuro2 bid
        self.log.info("entrando a calcular_limit_futuro1_bid")
        if len(self._tickers[self.botData["futuro2"]]["BI"])<(self.botData["indices_futuros"][self.botData["futuro2"]]["BI"]+1):
            self.log.info("en futuro2 bid hay una orden y es mia, o esta vacia ")
            return 0
        if len(self._tickers[self.botData["paseFuturos"]]["OF"])==0:
            self.log.info("no hay pase en of")
            #si pase en este momento es 0 entonces me salgo 
            return 0
        #voy a guardar los indices q necesito en variables
        indicePaseAsk = self.botData["indices_futuros"][self.botData["paseFuturos"]]["OF"]
        indiceFuturo2Bid = self.botData["indices_futuros"][self.botData["futuro2"]]["BI"]
        indiceFuturo1Bid = self.botData["indices_futuros"][self.botData["futuro1"]]["BI"]
        #voy a guardar los precios que necesito en variables
        futuro2Bid = self._tickers[self.botData["futuro2"]]["BI"][indiceFuturo2Bid]["price"]
        paseFuturosAsk = self._tickers[self.botData["paseFuturos"]]["OF"][indicePaseAsk]["price"]
        #voy a calcular el precio maximo de ganancia
        precioMaxGanBidFuturo1 = futuro2Bid - paseFuturosAsk
        #voy a guardar el size de las orden del futuro2 bid
        futuro2BidSize = self._tickers[self.botData["futuro2"]]["BI"][indiceFuturo2Bid]["size"]
        self.log.info(f"futuro2Bid:{futuro2Bid}, paseFuturosAsk: {paseFuturosAsk}, precioMaxGanBidFuturo1: {precioMaxGanBidFuturo1} ")
        self.log.info("ahora le voy a poner el valor del futuro1 bid a la variable y crear el precio del limit a la orden")
        futuro1Bid = 0
        self.log.info("verificar si el bid1 esta vacio o si hay una sola orden mia")
        if verificarFuturo1["puedoOperar"]==True:
            futuro1Bid = self._tickers[self.botData["futuro1"]]["BI"][indiceFuturo1Bid]["price"]
        limitBidFuturo1 = 0
        if futuro1Bid>0 and futuro1Bid < precioMaxGanBidFuturo1 and (precioMaxGanBidFuturo1-futuro1Bid)>0.11 : #true
            limitBidFuturo1 = futuro1Bid+self.botData["varGan"]
            #entonces lo del spread va aqui
            self.log.info("voy a comprobar lo del spread")
            verificarFuturo1x = await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "OF", self._tickers[self.botData["futuro1"]]["OF"]) 
            if verificarFuturo1x["puedoOperar"]==True:
                bookContrario = self._tickers[self.botData["futuro1"]]["OF"][verificarFuturo1x["indiceBookUsar"]]["price"]
                if float(bookContrario) - float(futuro1Bid) <=0.1:
                    self.log.info("tengo spread 0 o 0.1 por lo tanto poner el limit a lo mismo del bidfuturo1")
                    limitBidFuturo1 = futuro1Bid
            else:
                self.log.info("fuuturo1 ask no disponible ")
        elif (precioMaxGanBidFuturo1-futuro1Bid)  == 0.10 and futuro1Bid>0: #true igualo bid1
            self.log.info("el spread es 0.1 y el bid1 es mayor a 0")
            limitBidFuturo1 = futuro1Bid
        elif futuro1Bid==0:
            self.log.info("el bid1 es 0")
            limitBidFuturo1 = (futuro2Bid - paseFuturosAsk) + self.botData["varGan"]
        else:
            self.log.info("el bid1 es mayor al precio maximo de ganancia")
            limitBidFuturo1 = precioMaxGanBidFuturo1-self.botData["varGan"]
            limitTrue =  futuro1Bid+self.botData["varGan"]
            limitTrueMax = float(self.botData["minMax"][self.botData["futuro1"]]["highLimitPrice"])
            limitTrueMin = float(self.botData["minMax"][self.botData["futuro1"]]["lowLimitPrice"])
            self.log.info(f"limitTrue: {limitTrue}, limitTrueMax:{limitTrueMax}, limitTrueMin:{limitTrueMin}")
            limitBidFuturo1 = precioMaxGanBidFuturo1-self.botData["varGan"]
            self.log.info(f"limitBidFuturo1:{limitBidFuturo1}")
            if futuro1Bid != 0: 
                if limitBidFuturo1 <=limitTrueMin or limitBidFuturo1>=limitTrueMax:
                    self.log.info("no estoy en los valores de limites maximos y minimos :D ")
                    return 0
        self.log.info(f"futuro1Bid:{futuro1Bid},limitBidFuturo1:{limitBidFuturo1}")
        limitBidFuturo1 = round(limitBidFuturo1,1)
        self.update_limits("CI", limitBidFuturo1, "BI")
        return limitBidFuturo1
    
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


    async def  calcular_limit_futuro2_bid(self, verificarFuturo1 ):
        self.log.info("entrando a calcular_limit_futuro2_bid")
        if len(self._tickers[self.botData["futuro1"]]["BI"])<(self.botData["indices_futuros"][self.botData["futuro1"]]["BI"]+1):
            self.log.info("en futuro2 bid hay una orden y es mia, o esta vacia ")
            return 0
        if len(self._tickers[self.botData["paseFuturos"]]["BI"])==0:
            #si pase en este momento es 0 entonces me salgo 
            return 0
        indiceFuturo1Bid = self.botData["indices_futuros"][self.botData["futuro1"]]["BI"]
        indiceFuturo2Bid = self.botData["indices_futuros"][self.botData["futuro2"]]["BI"]
        indicePaseBid = self.botData["indices_futuros"][self.botData["paseFuturos"]]["BI"]
        futuro1Bid = self._tickers[self.botData["futuro1"]]["BI"][indiceFuturo1Bid]["price"]
        paseFuturosBid = self._tickers[self.botData["paseFuturos"]]["BI"][indicePaseBid]["price"] 
        precioMaxGanBidFuturo2 = futuro1Bid + paseFuturosBid
        self.log.info(f"futuro1Bid:{futuro1Bid}, paseFuturosBid: {paseFuturosBid}, precioMaxGanBidFuturo2: {precioMaxGanBidFuturo2} ")
        self.futuro1BidSize = self._tickers[self.botData["futuro1"]]["BI"][indiceFuturo1Bid]["size"]
        self.log.info("ahora le voy a poner el valor del futuro2 bid a la variable y crear el precio del limit a la orden")
        futuro2Bid = 0
        self.log.info("verificar si el bid2 esta vacio o si hay una sola orden mia")
       
        if verificarFuturo1["puedoOperar"]==True:
            futuro2Bid = self._tickers[self.botData["futuro2"]]["BI"][indiceFuturo2Bid]["price"]
        #self.limitBidFuturo2 = futuro2Bid+self.botData["varGan"] if futuro2Bid < self.precioMaxGanBidFuturo2 else self.precioMaxGanBidFuturo2-self.botData["varGan"]
        limitBidFuturo2 = 0
        self.log.info(f"futuro2Bid {futuro2Bid}")
        if futuro2Bid> 0 and futuro2Bid < precioMaxGanBidFuturo2 and (precioMaxGanBidFuturo2-futuro2Bid)>0.11:
            self.log.info("el spread es mayor a 0.1 y el bid2 es menor al precio maximo de ganancia")
            limitBidFuturo2 = futuro2Bid+self.botData["varGan"] #336.3
            #verificar lo del spread 
            #necesito el ask 
            self.log.info("voy a comprobar lo del spread")
            verificarFuturo1x = await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "OF",self._tickers[self.botData["futuro2"]]["OF"]) 
            if verificarFuturo1x["puedoOperar"]==True:
                bookContrario = self._tickers[self.botData["futuro2"]]["OF"][verificarFuturo1x["indiceBookUsar"]]["price"]
                if float(bookContrario) - float(futuro2Bid) <=0.1:
                    self.log.info("tengo spread 0 o 1 por lo tanto poner el limit a lo mismo del bidfuturo1")
                    limitBidFuturo2 = futuro2Bid
            else:
                self.log.info("fuuturo2 ask no disponible ")
        elif futuro2Bid > 0 and (precioMaxGanBidFuturo2-futuro2Bid)==0.10:
            self.log.info("el spread es igual a 0.1 y el bid2 es menor al precio maximo de ganancia")
            limitBidFuturo2 = futuro2Bid
        elif futuro2Bid==0:
            self.log.info("el bid2 es 0")
            limitBidFuturo2 = (futuro1Bid - paseFuturosBid) + self.botData["varGan"]
        else:
            self.log.info("el bid2 es mayor al precio maximo de ganancia")
            limitTrue = futuro2Bid+self.botData["varGan"] #336.3
            limitTrueMax = float(self.botData["minMax"][self.botData["futuro2"]]["highLimitPrice"])
            limitTrueMin = float(self.botData["minMax"][self.botData["futuro2"]]["lowLimitPrice"])
            self.log.info(f"limitTrue: {limitTrue}, limitTrueMax:{limitTrueMax}, limitTrueMin:{limitTrueMin}")
            limitBidFuturo2 = precioMaxGanBidFuturo2-self.botData["varGan"] #333.7
            self.log.info(f"limitBidFuturo2:{limitBidFuturo2}")
            if futuro2Bid != 0: 
                if limitBidFuturo2 <=limitTrueMin or limitBidFuturo2>=limitTrueMax:
                    self.log.info("no estoy en los valores de limites maximos y minimos :D ")
                    return 0
        limitBidFuturo2 = round(limitBidFuturo2,1)
        self.log.info(f"futuro2Bid:{futuro2Bid},limitBidFuturo2:{limitBidFuturo2}")
        self.update_limits("48", limitBidFuturo2, "BI")
        return limitBidFuturo2


    async def  calcular_limit_futuro2_ask(self, verificarFuturo1):
        self.log.info("calcular limit futuro2 ask")
        if len(self._tickers[self.botData["futuro1"]]["OF"])<(self.botData["indices_futuros"][self.botData["futuro1"]]["OF"]+1):
            self.log.info("en futuro2 bid hay una orden y es mia, o esta vacia ")
            return 0
        if len(self._tickers[self.botData["paseFuturos"]]["OF"])==0:
            #si pase en este momento es 0 entonces me salgo 
            return 0

        indiceFuturo1Ask = self.botData["indices_futuros"][self.botData["futuro1"]]["OF"]
        indiceFuturo2Ask = self.botData["indices_futuros"][self.botData["futuro2"]]["OF"]
        indicePaseAsk = self.botData["indices_futuros"][self.botData["paseFuturos"]]["OF"]

        
        futuro1Ask = self._tickers[self.botData["futuro1"]]["OF"][indiceFuturo1Ask]["price"]
        paseFuturosAsk = self._tickers[self.botData["paseFuturos"]]["OF"][indicePaseAsk]["price"] 
        precioMaxGanAskFuturo2 = futuro1Ask + paseFuturosAsk
        self.log.info(f"futuro1Ask:{futuro1Ask}, paseFuturosAsk: {paseFuturosAsk}, precioMaxGanAskFuturo2: {precioMaxGanAskFuturo2} ")
        futuro2Ask = 0
        self.log.info("verificar si el ask2 esta vacio o si hay una sola orden mia")
        if verificarFuturo1["puedoOperar"]==True:
            futuro2Ask = self._tickers[self.botData["futuro2"]]["OF"][indiceFuturo2Ask]["price"]
        self.log.info("ahora le voy a poner el valor del futuro2 bid a la variable y crear el precio del limit a la orden")
        #self.limitBidFuturo2 = futuro2Bid+self.botData["varGan"] if futuro2Bid < self.precioMaxGanBidFuturo2 else self.precioMaxGanBidFuturo2-self.botData["varGan"]
        limitAskFuturo2 = 0
        if futuro2Ask>0 and futuro2Ask > precioMaxGanAskFuturo2 and (futuro2Ask-precioMaxGanAskFuturo2)>0.11: #true
            self.log.info("el ask2 es mayor al precio maximo de ganancia y el spread es mayor a 0.1")
            limitAskFuturo2 = futuro2Ask-self.botData["varGan"]
            #verificar lo del spread 
            #necesito el ask 
            self.log.info("voy a comprobar lo del spread")
            verificarFuturo1x = await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "BI", self._tickers[self.botData["futuro2"]]["BI"]) 
            if verificarFuturo1x["puedoOperar"]==True:
                bookContrario = self._tickers[self.botData["futuro2"]]["BI"][verificarFuturo1x["indiceBookUsar"]]["price"]
                if float(bookContrario) - float(futuro2Ask) >=0:
                    self.log.info("tengo spread 0 o 1 por lo tanto poner el limit a lo mismo del bidfuturo1")
                    limitAskFuturo2 = futuro2Ask
            else:
                self.log.info("fuuturo2 ask no disponible ")
        elif  futuro2Ask>0 and (futuro2Ask-precioMaxGanAskFuturo2)==0.10:
            self.log.info("el ask2 es mayor al precio maximo de ganancia y el spread es igual a 0.1")
            limitAskFuturo2 = futuro2Ask
        elif  futuro2Ask==0:
            self.log.info("el ask2 es igual a 0")
            limitAskFuturo2 = (futuro1Ask + paseFuturosAsk) + self.botData["varGan"]
        else:
            self.log.info("el ask2 es menor al precio maximo de ganancia")
            limitTrue =  futuro2Ask-self.botData["varGan"]
            limitTrueMax = float(self.botData["minMax"][self.botData["futuro2"]]["highLimitPrice"])
            limitTrueMin = float(self.botData["minMax"][self.botData["futuro2"]]["lowLimitPrice"])
            self.log.info(f"limitTrue: {limitTrue}, limitTrueMax:{limitTrueMax}, limitTrueMin:{limitTrueMin}")
            limitAskFuturo2 = precioMaxGanAskFuturo2+self.botData["varGan"]
            self.log.info(f"limitAskFuturo2:{limitAskFuturo2}")
            if futuro2Ask != 0: 
                if limitAskFuturo2 <=limitTrueMin or limitAskFuturo2>=limitTrueMax:
                    self.log.info("no estoy en los valores de limites maximos y minimos :D ")
                    return 0
        limitAskFuturo2 = round(limitAskFuturo2,1)
        self.log.info(f"futuro2Ask:{futuro2Ask},limitBidFuturo2:{limitAskFuturo2}")
        self.update_limits("48", limitAskFuturo2, "OF")
        return limitAskFuturo2
    

    async def  verificar_futuro1_bid(self):
        self.log.info("verificar futuro1 bid")
        verificarOrdenCreada = await self.clientR.get_order_limit_by_symbol_side(self.botData["futuro1"], "Buy" ) 
        if verificarOrdenCreada["status"]==True:
            self.log.info("tengo orden creada")
            orden =  verificarOrdenCreada["data"]
            #es true osea q si tengo orden 
            #aqui debo verificar primnero q la orden de futuro1 bid no sea mia 
            verificarFuturo1 =  await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "BI", self._tickers[self.botData["futuro1"]]["BI"] )
            if verificarFuturo1["puedoOperar"]==True: 
                self.log.info("puedo usar futuro 1 bid ")
                verificarFuturo2 = await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "BI", self._tickers[self.botData["futuro2"]]["BI"]) 
                verificarPase =  await self.clientR.verificar_ordenes_futuro(self.botData["paseFuturos"], "OF", self._tickers[self.botData["paseFuturos"]]["OF"]) 
                if verificarFuturo2["puedoOperar"]==True and verificarPase["puedoOperar"]==True:
                    self.log.info("tengo orden creada y el bid1 es mio y tengo el bid2 y el ask del pase")
                    self.botData["indices_futuros"][self.botData["futuro1"]] = {"BI": verificarFuturo1["indiceBookUsar"]}
                    self.botData["indices_futuros"][self.botData["paseFuturos"]] = {"OF": verificarPase["indiceBookUsar"]}
                    self.botData["indices_futuros"][self.botData["futuro2"]] = {"BI": verificarFuturo2["indiceBookUsar"]}
                    calcularLimit = await self.calcular_limit_futuro1_bid(verificarFuturo1)
                    if calcularLimit>0:
                        self.log.info("calcular limit es mayor a 0")
                        sizeOrder = await self.get_size_order(self.botData["futuro1"], "BI")
                        limitBidFuturo1 = calcularLimit
                        self.log.info(f"precio mio {round(orden['price'],1) }")
                        self.log.info(f"limitBidFuturo1 {round(limitBidFuturo1,1)}")
                        self.log.info(f"size mio: {orden['leavesQty']}")
                        if orden['leavesQty']==0:
                            self.log.info("leavesQty es 0")
                            return False
                        self.log.info(f"size a poner : {sizeOrder}")
                        if round(orden['price'],1) != round(limitBidFuturo1,1) or orden['leavesQty'] != sizeOrder:
                        #modificar orden
                            self.log.info("es diferente entonces mando a actualizar")
                            if not self.paused.is_set():
                                self.log.warning(f"paused esta activo")
                                return
                            self.log.info(f"orden operada = false, enviar a modificar orden")
                            if orden['leavesQty'] != sizeOrder:
                                modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'],1, 2, 
                                                        self.botData["futuro1"], sizeOrder, limitBidFuturo1)
                            else:
                                sizeOrder = orden['orderQty']
                                modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'],1, 2, 
                                                        self.botData["futuro1"], sizeOrder, limitBidFuturo1)
                            self.log.info(f"orden modificada {modificarOrden}")
                        else:
                            self.log.info("es lo mismo asi q no actuaklizo ")
                else:
                    self.log.info("debo borrar xq no hay futuro2 o pase ask ")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    self.log.info(f"orden operada = false, enviar a cancelar orden")
                    borrarOrden = await self.clientR.cancelar_orden(orden['orderId'], orden['clOrdId'], 1, orden['orderQty'], self.botData["futuro1"])
                    self.log.info(f"orden borrada: {borrarOrden}")
            else:
                self.log.info("o es mi una orden y es mia o no hay ordenes, por ende borro el futuro2bid, pero no lo hare")
                if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro2"], 1 )
        else: 
            #no tengo orden la creo 
            self.log.info("no tengo orden la creo")
            verificarFuturo1 =  await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "BI", self._tickers[self.botData["futuro1"]]["BI"])
            verificarFuturo2 = await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "BI", self._tickers[self.botData["futuro2"]]["BI"]) 
            verificarPase =  await self.clientR.verificar_ordenes_futuro(self.botData["paseFuturos"], "OF", self._tickers[self.botData["paseFuturos"]]["OF"]) 
            if verificarFuturo2["puedoOperar"]==True and verificarPase["puedoOperar"]==True:
                self.botData["indices_futuros"][self.botData["futuro1"]] = {"BI": verificarPase["indiceBookUsar"]}
                self.botData["indices_futuros"][self.botData["paseFuturos"]] = {"OF": verificarPase["indiceBookUsar"]}
                self.botData["indices_futuros"][self.botData["futuro2"]] = {"BI": verificarFuturo2["indiceBookUsar"]}
                self.log.info("si puedo crear orden en futuro1 bid")
                calcularLimit = await self.calcular_limit_futuro1_bid(verificarFuturo1)
                if calcularLimit>0:
                    sizeOrder = await self.get_size_order(self.botData["futuro1"], "BI")
                    limitBidFuturo1 = calcularLimit
                    self.log.info(f"enviando a crear orden futuro1 bid, side 1, quantity:{sizeOrder}, price: {limitBidFuturo1}   ")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    self.log.info(f"orden operada = false, enviar a crear orden")
                    ordenNueva = await self.clientR.nueva_orden(self.botData["futuro1"], 1, sizeOrder, limitBidFuturo1, 2)
                    self.log.info(f"orden nueva {ordenNueva}")
            else:
                self.log.info("no puedo crearla xq no hay futuro o pase necesario")
                if verificarFuturo1["puedoOperar"]==False:
                    self.log.info("voy a boorar bid1 xq no hay nada en bid2 o es mia la orden")
                    borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro2"], 1 )

    async def get_size_order(self, symbol, side):
        sizeReturn = 0
        self.log.info("entrando a get_size_order")
        if symbol==self.botData["futuro1"]:
            if side=="BI":
                indicePaseAsk = self.botData["indices_futuros"][self.botData["paseFuturos"]]["OF"]
                indiceFuturo2Bid = self.botData["indices_futuros"][self.botData["futuro2"]]["BI"]
                futuro2BidSize = self._tickers[self.botData["futuro2"]]["BI"][indiceFuturo2Bid]["size"]
                paseFuturosAskSize = self._tickers[self.botData["paseFuturos"]]["OF"][indicePaseAsk]["size"]
                sizeBidFuturo1 = futuro2BidSize if futuro2BidSize<paseFuturosAskSize else paseFuturosAskSize
                sizeReturn = sizeBidFuturo1
            else:#OF
                indiceFuturo2Ask = self.botData["indices_futuros"][self.botData["futuro2"]]["OF"]
                indiceFuturoPaseBid = self.botData["indices_futuros"][self.botData["paseFuturos"]]["BI"]
                futuro2AskSize = self._tickers[self.botData["futuro2"]]["OF"][indiceFuturo2Ask]["size"]
                paseFuturosBidSize = self._tickers[self.botData["paseFuturos"]]["BI"][indiceFuturoPaseBid]["size"]
                sizeAskFuturo1 = futuro2AskSize if futuro2AskSize<paseFuturosBidSize else paseFuturosBidSize
                sizeReturn = sizeAskFuturo1
        else:#futuro2
            if side=="BI":
                indiceFuturo1Bid = self.botData["indices_futuros"][self.botData["futuro1"]]["BI"]
                indiceFuturoPaseBid = self.botData["indices_futuros"][self.botData["paseFuturos"]]["BI"]
                futuro1BidSize = self._tickers[self.botData["futuro1"]]["BI"][indiceFuturo1Bid]["size"]
                paseFuturosBidSize = self._tickers[self.botData["paseFuturos"]]["BI"][indiceFuturoPaseBid]["size"]
                sizeBidFuturo2 = futuro1BidSize if futuro1BidSize<paseFuturosBidSize else paseFuturosBidSize
                sizeReturn = sizeBidFuturo2
            else:#OF
                indiceFuturo1Ask = self.botData["indices_futuros"][self.botData["futuro1"]]["OF"]
                indiceFuturoPaseAsk = self.botData["indices_futuros"][self.botData["paseFuturos"]]["OF"]
                futuro1AskSize = self._tickers[self.botData["futuro1"]]["OF"][indiceFuturo1Ask]["size"]
                paseFuturosAskSize = self._tickers[self.botData["paseFuturos"]]["OF"][indiceFuturoPaseAsk]["size"]
                sizeAskFuturo2 = futuro1AskSize if futuro1AskSize<paseFuturosAskSize else paseFuturosAskSize
                sizeReturn = sizeAskFuturo2
        self.log.info(f"sizeReturn {sizeReturn}")
        if sizeReturn>self.botData["sizeMax"]:
            return self.botData["sizeMax"]
        return sizeReturn
                
    async def  verificar_futuro1_ask(self):
        self.log.info("entrando a verificar_futuro1_ask")
        verificarOrdenCreada = await self.clientR.get_order_limit_by_symbol_side(self.botData["futuro1"], "Sell" ) 
        if verificarOrdenCreada["status"]==True:
            orden =  verificarOrdenCreada["data"]
            #es true osea q si tengo orden 
            #aqui debo verificar primnero q la orden de futuro1 OF no sea mia 
            verificarFuturo1 =  await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "OF", self._tickers[self.botData["futuro1"]]["OF"] )
            if verificarFuturo1["puedoOperar"]==True: 
                self.log.info("tengo orden creada en ask1")
                verificarFuturo2 = await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "OF", self._tickers[self.botData["futuro2"]]["OF"]) 
                verificarPase =  await self.clientR.verificar_ordenes_futuro(self.botData["paseFuturos"], "BI", self._tickers[self.botData["paseFuturos"]]["BI"]) 
                if verificarFuturo2["puedoOperar"]==True and verificarPase["puedoOperar"]==True:
                    self.log.info("tengo el ask2 y el bid del pase")
                    self.botData["indices_futuros"][self.botData["futuro1"]] = {"OF": verificarFuturo1["indiceBookUsar"]}
                    self.botData["indices_futuros"][self.botData["paseFuturos"]] = {"BI": verificarPase["indiceBookUsar"]}
                    self.botData["indices_futuros"][self.botData["futuro2"]] = {"OF": verificarFuturo2["indiceBookUsar"]}
                    calcularLimit = await self.calcular_limit_futuro1_ask(verificarFuturo1)
                    if calcularLimit>0:
                        self.log.info("calcular limit es mayor a 0")
                        sizeOrder = await self.get_size_order(self.botData["futuro1"], "OF")
                        limitAskFuturo1 = calcularLimit
                        self.log.info(f"precio mio {round(orden['price'],1) }")
                        self.log.info(f"limitAskFuturo1 {round(limitAskFuturo1,1)}")
                        self.log.info(f"size mio: {orden['leavesQty']}")
                        if orden['leavesQty']==0:
                            return False
                        self.log.info(f"size a poner : {sizeOrder}")
                        if round(orden['price'],1) != round(limitAskFuturo1,1) or orden['leavesQty'] != sizeOrder:
                            self.log.info("es diferente entonces mando a actualizar")
                            if not self.paused.is_set():
                                self.log.warning(f"paused esta activo")
                                return
                            if orden['leavesQty'] != sizeOrder:
                                modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'],2, 2, self.botData["futuro1"], sizeOrder, limitAskFuturo1)
                                self.log.info(f"orden modificada {modificarOrden}")
                            else:
                                sizeOrder = orden['orderQty']
                                modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'],2, 2, self.botData["futuro1"], sizeOrder, limitAskFuturo1)
                                self.log.info(f"orden modificada {modificarOrden}")
                        else:
                            self.log.info("es lo mismo asi q no actuaklizo ")
                else:
                    self.log.info("debo borrar xq no hay futuro2 o pase ask ")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    borrarOrden = await  self.clientR.cancelar_orden(orderId = orden['orderId'], clOrdId=orden['clOrdId'], side=2, quantity=orden['leavesQty'], symbol=self.botData["futuro1"])
                    self.log.info("borrar orden", borrarOrden)
            else:
                self.log.info("o es mi una orden y es mia o no hay ordenes, por ende borro el futuro2 ask, pero no lo hare")
                if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro2"], 2)
        else: 
            #no tengo orden la creo 
            self.log.info("no tengo orden la creo")
            verificarFuturo1 =  await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "OF", self._tickers[self.botData["futuro1"]]["OF"] )
            verificarFuturo2 = await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "OF", self._tickers[self.botData["futuro2"]]["OF"]) 
            verificarPase =  await self.clientR.verificar_ordenes_futuro(self.botData["paseFuturos"], "BI", self._tickers[self.botData["paseFuturos"]]["BI"]) 
            if verificarFuturo2["puedoOperar"]==True and verificarPase["puedoOperar"]==True:
                self.botData["indices_futuros"][self.botData["futuro1"]] = {"OF": verificarFuturo1["indiceBookUsar"]}
                self.botData["indices_futuros"][self.botData["paseFuturos"]] = {"BI": verificarPase["indiceBookUsar"]}
                self.botData["indices_futuros"][self.botData["futuro2"]] = {"OF": verificarFuturo2["indiceBookUsar"]}
                self.log.info("si puedo crear orden en futuro1 ask")
                calcularLimit = await self.calcular_limit_futuro1_ask(verificarFuturo1)
                if calcularLimit>0:
                    sizeOrder = await self.get_size_order(self.botData["futuro1"], "OF")
                    limitAskFuturo1 = calcularLimit
                    self.log.info(f"enviando a crear orden futuro1 ask, side 2, quantity:{sizeOrder}, price: {limitAskFuturo1}   ")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    self.log.info(f"orden operada = false, enviar a cancelar orden")
                    ordenNueva = await self.clientR.nueva_orden(self.botData["futuro1"], 2, sizeOrder, limitAskFuturo1, 2)
                    self.log.info("orden nueva ", ordenNueva)
                    #estas ordenes nueva debo ponerles al id_origen el id de la orden q se acaba de guardar 
            else:
                self.log.info("no puedo crearla xq no hay futuro o pase necesario")
                if verificarFuturo1["status"]==False:
                    self.log.info("voy a borrar ask2 xq no hay nada en ask1 o hay una y es mia ")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro2"], 2)
                    self.log.info("borrar orden", borrarOrden)

    async def  verificar_futuro2_bid(self):
        self.log.info("-----------------entrando a verificar_futuro2_bid--------------------")
        verificarOrdenCreada = await self.clientR.get_order_limit_by_symbol_side(self.botData["futuro2"], "Buy" ) 
        if verificarOrdenCreada["status"]==True:
            self.log.info("tengo orden creada")
            orden =  verificarOrdenCreada["data"]
            #es true osea q si tengo orden 
            #aqui debo verificar primnero q la orden de futuro2 bid no sea mia 
            verificarFuturo1 =  await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "BI", self._tickers[self.botData["futuro2"]]["BI"] )
            if verificarFuturo1["puedoOperar"]==True: 
                self.log.info("entonces puedo continuar ")
                verificarFuturo2 = await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "BI", self._tickers[self.botData["futuro1"]]["BI"]) 
                verificarPase =  await self.clientR.verificar_ordenes_futuro(self.botData["paseFuturos"], "BI", self._tickers[self.botData["paseFuturos"]]["BI"]) 
                if verificarFuturo2["puedoOperar"]==True and verificarPase["puedoOperar"]==True:
                    self.botData["indices_futuros"][self.botData["futuro2"]] = {"BI": verificarFuturo1["indiceBookUsar"]}
                    self.botData["indices_futuros"][self.botData["paseFuturos"]] = {"BI": verificarPase["indiceBookUsar"]}
                    self.botData["indices_futuros"][self.botData["futuro1"]] = {"BI": verificarFuturo2["indiceBookUsar"]}
                    calcularLimit = await self.calcular_limit_futuro2_bid(verificarFuturo1)
                    if calcularLimit>0:
                        self.log.info("moficicar")
                        sizeOrder = await self.get_size_order(self.botData["futuro2"], "BI")
                        limitBidFuturo2 = calcularLimit
                        self.log.info(f"precio mio {round(orden['price'],1) }")
                        self.log.info(f"limitBidFuturo2 {round(limitBidFuturo2,1)}")
                        self.log.info(f"size mio: {orden['leavesQty']}")
                        if orden['leavesQty']==0:
                            return False
                        self.log.info(f"size a poner : {sizeOrder}")
                        if round(orden['price'],1) != round(limitBidFuturo2,1) or orden['leavesQty'] != sizeOrder:
                        #modificar orden
                            if not self.paused.is_set():
                                self.log.warning(f"paused esta activo")
                                return
                            self.log.info(f"orden operada = false, enviar a modificar orden")
                            self.log.info("es diferente entonces mando a actualizar")
                            if orden['leavesQty'] != sizeOrder:
                                modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'],1, 2, self.botData["futuro2"],sizeOrder, limitBidFuturo2)
                            else:
                                sizeOrder = orden['orderQty']
                                modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'],1, 2, self.botData["futuro2"],sizeOrder, limitBidFuturo2)
                            self.log.info(f"orden modificada {modificarOrden}")
                        else:
                            self.log.info("es lo mismo asi q no actuaklizo ")    
                else:
                    self.log.info("debo borrar xq no hay futuro2 o pase ask ")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    borrarOrden = await self.clientR.cancelar_orden(orden['orderId'], orden['clOrdId'],1,orden['leavesQty'], self.botData["futuro2"])
                    self.log.info("borrar orden", borrarOrden)
            else:
                self.log.info("o es mi una orden y es mia o no hay ordenes, cancelar futuro1bid")
                if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro1"], 1)
        else: 
            self.log.info("no tengo orden la creo")
            #no tengo orden la creo 
            verificarFuturo1 =  await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "BI", self._tickers[self.botData["futuro2"]]["BI"] )
            verificarFuturo2 = await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "BI", self._tickers[self.botData["futuro2"]]["BI"]) 
            verificarPase =  await self.clientR.verificar_ordenes_futuro(self.botData["paseFuturos"], "BI", self._tickers[self.botData["paseFuturos"]]["OF"]) 
            if verificarFuturo2["puedoOperar"]==True and verificarPase["puedoOperar"]==True:
                self.botData["indices_futuros"][self.botData["futuro2"]] = {"BI": verificarPase["indiceBookUsar"]}
                self.botData["indices_futuros"][self.botData["paseFuturos"]] = {"BI": verificarPase["indiceBookUsar"]}
                self.botData["indices_futuros"][self.botData["futuro1"]] = {"BI": verificarFuturo2["indiceBookUsar"]}
                self.log.info("si puedo crear orden en futuro2 bid")
                calcularLimit = await self.calcular_limit_futuro2_bid(verificarFuturo1)
                if calcularLimit>0:
                    sizeOrder = await self.get_size_order(self.botData["futuro2"], "BI")
                    limitBidFuturo2 = calcularLimit
                    self.log.info(f"enviando a crear orden futuro2 bid, side 1, quantity:{sizeOrder}, price: {limitBidFuturo2}   ")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    self.log.info(f"orden operada = false, enviar a cancelar orden")
                    ordenNueva = await self.clientR.nueva_orden(self.botData["futuro2"], 1, sizeOrder, limitBidFuturo2, 2)
                    self.log.info(f"orden nueva {ordenNueva}")
                    
            else:
                self.log.info("no puedo crearla xq no hay futuro o pase necesario")
                if verificarFuturo1["status"]==False:
                    self.log.info("voy a borrar la orden de futuro1 bid xq no hay nada en futuro2 bid o hay una sola orden y es mia")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro1"], 1)


    async def  verificar_futuro2_ask(self): 
        self.log.info("entrando a verificar_futuro2_ask")
        verificarOrdenCreada = await self.clientR.get_order_limit_by_symbol_side(self.botData["futuro2"], "Sell" ) 
        if verificarOrdenCreada["status"]==True:
            self.log.info("tengo orden creada")
            orden =  verificarOrdenCreada["data"]
            #es true osea q si tengo orden 
            #aqui debo verificar primnero q la orden de futuro1 bid no sea mia 
            self.log.info("voy a verificar futuro2 of")
            verificarFuturo1 =  await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "OF", self._tickers[self.botData["futuro2"]]["OF"] )
            if verificarFuturo1["puedoOperar"]==True: 
                self.log.info("verificado status true")
                self.log.info("entonces puedo continuar ")
                verificarFuturo2 = await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "OF", self._tickers[self.botData["futuro1"]]["OF"]) 
                verificarPase =  await self.clientR.verificar_ordenes_futuro(self.botData["paseFuturos"], "OF", self._tickers[self.botData["paseFuturos"]]["OF"]) 
                if verificarFuturo2["status"]==True and verificarPase["status"]==True:
                    self.botData["indices_futuros"][self.botData["futuro2"]] = {"OF": verificarFuturo1["indiceBookUsar"]}
                    self.botData["indices_futuros"][self.botData["paseFuturos"]] = {"OF": verificarPase["indiceBookUsar"]}
                    self.botData["indices_futuros"][self.botData["futuro1"]] = {"OF": verificarFuturo2["indiceBookUsar"]}
                    calcularLimit = await self.calcular_limit_futuro2_ask(verificarFuturo1)
                    if calcularLimit>0:
                        self.log.info("moficicar")
                        sizeOrder = await self.get_size_order(self.botData["futuro2"], "OF")
                        limitAskFuturo2 = calcularLimit
                        self.log.info(f"precio mio {round(orden['price'],1) }")
                        self.log.info(f"limitAskFuturo2 {round(limitAskFuturo2,1)}")
                        self.log.info(f"size mio: {orden['leavesQty']}")
                        if orden['leavesQty']==0:
                            return False
                        self.log.info(f"size a poner : {sizeOrder}")
                        if round(orden['price'],1) != round(limitAskFuturo2,1) or orden['leavesQty'] != sizeOrder :
                            #modificar orden
                            self.log.info("es diferente entonces mando a actualizar")
                            if not self.paused.is_set():
                                self.log.warning(f"paused esta activo")
                                return
                            self.log.info(f"orden operada = false, enviar a modificar orden")
                            if orden['leavesQty'] != sizeOrder:
                                modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'], 2, 2, self.botData["futuro2"], sizeOrder, limitAskFuturo2)
                            else:
                                 sizeOrder = orden['orderQty']
                                 modificarOrden = await self.clientR.modificar_orden_size(orden['orderId'], orden['clOrdId'], 2, 2, self.botData["futuro2"], sizeOrder, limitAskFuturo2)
                            self.log.info(f"orden modificada {modificarOrden}")
                        else:
                            self.log.info("es lo mismo asi q no actuaklizo ")
                else:
                    self.log.info("debo borrar xq no hay futuro2 o pase ask ")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    borrarOrden = await self.clientR.cancelar_orden(orden['orderId'], orden['clOrdId'], 2,orden['leavesQty'], self.botData["futuro2"])
                    self.log.info(f"borrar orden {borrarOrden}")
            else:
                self.log.info("o es mi una orden y es mia o no hay ordenes, cancelar futuro1ask ")
                if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro1"], 2)
        else: 
            #no tengo orden la creo 
            self.log.info("no tengoorden la creo")
            verificarFuturo1 =  await self.clientR.verificar_ordenes_futuro(self.botData["futuro2"], "OF", self._tickers[self.botData["futuro2"]]["OF"] )
            verificarFuturo2 = await self.clientR.verificar_ordenes_futuro(self.botData["futuro1"], "OF", self._tickers[self.botData["futuro1"]]["OF"]) 
            verificarPase =  await self.clientR.verificar_ordenes_futuro(self.botData["paseFuturos"], "OF", self._tickers[self.botData["paseFuturos"]]["OF"]) 
            if  verificarFuturo2["puedoOperar"]==True and verificarPase["puedoOperar"]==True:
                self.botData["indices_futuros"][self.botData["futuro2"]] = {"OF": verificarPase["indiceBookUsar"]}
                self.botData["indices_futuros"][self.botData["paseFuturos"]] = {"OF": verificarPase["indiceBookUsar"]}
                self.botData["indices_futuros"][self.botData["futuro1"]] = {"OF": verificarFuturo2["indiceBookUsar"]}
                self.log.info("si puedo crear orden en futuro2 ask")
                calcularLimit = await self.calcular_limit_futuro2_ask(verificarFuturo1)
                if calcularLimit>0:
                    sizeOrder = await self.get_size_order(self.botData["futuro2"], "OF")
                    limitAskFuturo2 = calcularLimit
                    self.log.info(f"enviando a crear orden futuro2 ask, side 2, quantity:{sizeOrder}, price: {limitAskFuturo2}   ")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    self.log.info(f"orden operada = false, enviar a modificar orden")
                    ordenNueva = await self.clientR.nueva_orden(self.botData["futuro2"], 2, sizeOrder, limitAskFuturo2, 2)
                    self.log.info(f"orden nueva {ordenNueva}")
                 
            else:
                self.log.info("no puedo crearla xq no hay futuro o pase necesario")
                if verificarFuturo1["status"]==False:
                    self.log.info("voy a borrar ask1 xq no hay nada en ask2 o hay una sola y es mia")
                    if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
                    borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro2"], 2)
   
    async def  verificar_pases(self):
        self.log.info(f"vamos a verificar los pases del triangulo: {self.botData['id_bot']}, pase: {self._tickers[self.botData['paseFuturos']]} ")
        
        if len(self._tickers[self.botData["paseFuturos"]]["BI"])==0:
            self.log.info("no hay nada en pase bid, entonces cancelar ordenes en bid2 y ask1")
            if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
            borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro2"], 1)
            if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
            borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro1"], 2)
        if len(self._tickers[self.botData["paseFuturos"]]["OF"])==0:
            self.log.info("no hay nada en pase bid, entonces cancelar ordenes en ask2 y bid1")
            if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
            borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro2"], 2)
            if not self.paused.is_set():
                        self.log.warning(f"paused esta activo")
                        return
            borrarOrden = await self.clientR.cancelar_orden_haberla(self.botData["futuro1"], 1)

    async def  verificar_ordenes(self):
        await self.verificar_futuro1_bid()
        self.log.info("fin verificar futuro1 bid")
        await self.verificar_futuro1_ask()
        self.log.info("fin verificar futuro1 ask")
        await self.verificar_futuro2_bid()
        self.log.info("fin verificar futuro2 bid")
        await self.verificar_futuro2_ask()
        self.log.info("fin verificar futuro2 ask")
        await self.verificar_pases()
        self.log.info("fin verificar pases")

    async def guardar_posiciones(self):
        try:
            posiciones = await self.clientR.get_posiciones(self.botData["cuenta"])
            self.log.info("voy a guardar posiciones")
            for posicion in posiciones:
                if posicion["tradingSymbol"] == self.botData["futuro1"]:
                    self.botData["posiciones"][self.botData["futuro1"]
                                               ]["BI"] = posicion["buySize"]
                    self.botData["posiciones"][self.botData["futuro1"]
                                               ]["OF"] = posicion["sellSize"]
                    if posicion["tradingSymbol"] == self.botData["futuro2"]:
                        self.botData["posiciones"][self.botData["futuro2"]
                                                   ]["BI"] = posicion["buySize"]
                        self.botData["posiciones"][self.botData["futuro2"]
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
            self.botData["minPriceIncrement"] = await self.clientR.get_tick_value(self.botData["futuro1"])
            self.botData["factor"] = await self.clientR.get_factor_value(self.botData["futuro1"])
            self.log.info(f"ahora los limits max y min de cada simbolo")
            self.botData["minMax"][self.botData["futuro1"]] = await self.clientR.getMinMax(self.botData["futuro1"])
            self.botData["minMax"][self.botData["futuro2"]] = await self.clientR.getMinMax(self.botData["futuro2"])
            
            self.log.info(f"tercero suscribir al mercado ")
            suscribir = await self.clientR.suscribir_mercado(self.botData["symbols2"])
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


    async def run_forever(self):
        try:
            if await self.tareas_de_inicio() == False:
                return
            self.log.info(f"iniciando ciclo de tareas con el bot: {self.id}")
            while not self.stop.is_set():
                #   self.log.info("estoy en el ciclo inifito del bot")
                if self.paused.is_set():
                    if self.botData["soloEscucharMercado"] == False:
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

    async def execute_task(self, task):
        # Do something with the task
        self.log.info(f"Executing task: {task}, en bot: {self.id}")
        if task["type"] == 0:
            self.log.info(f"aqui si verificamos puntas")
            await self.verificar_ordenes()

    def startCola(self):
        # creo un nuevo evento para asyncio y asi ejecutar todo de aqui en adelante con async await
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # ejecuto la funcion q quiero
        loop.run_until_complete(self.run_forever())
        loop.close()
            
    async def run(self):
        try:
            self.threadCola = Thread(target=self.startCola)
            self.threadCola.start()
        finally:
            self.log.info(
                "saliendo de la tarea iniciada en el botmanager pero queda la thread")
      

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
                await self.clientR.disable_order_status(orderId, clOrdId)
                await self.clientR.save_order_details(details, activeOrder)
                order = await self.operar_orden(details, lastOrderID)
                self.log.info(
                    f"llego respuesta de ordenes contrarias operadas: {order}")
                if order["ordenNew"]["llegoRespuesta"] == True:
                        #verificar si es colgada 
                        if order["ordenNew"]["data"]["ordStatus"]=="NEW":
                            #es colgada enviar notificacion 
                            dataMd = {"type": "colgada", "details": order["ordenNew"]["data"]}
                            self.fix.server_md.broadcast(str(dataMd))
                if order["ordenPase"]["llegoRespuesta"] == True:
                        #verificar si es colgada 
                        if order["ordenPase"]["data"]["ordStatus"]=="NEW":
                            #es colgada enviar notificacion 
                            dataMd = {"type": "colgada", "details": order["ordenPase"]["data"]}
                            self.fix.server_md.broadcast(str(dataMd))

            elif typeOrder == "B":
                self.log.info("es una orden B osea contraria")
                await self.clientR.disable_order_status(orderId, clOrdId)
                await self.clientR.save_order_details(details, activeOrder)
            response = True
        except Exception as e:
            self.log.error(f"error verificando orden operada: {e}")
        return response

    async def operar_orden(self, orden, id_order):
        self.log.info(f"entrando a operar orden")
        response = {"ordenNew": {}, "ordenPase": {} }
        try:
            if orden["symbol"] == self.botData["futuro1"]:
                self.log.info("futuro1")
                if orden["side"] == "Buy":
                    self.log.info("Buy")
                    self.log.info("ahora operar la contraria pero en futuro2 OF ")
                    response = await self.operar_orden_contraria(orden, self.botData["futuro2"], "BI", id_order, 2)
                else:
                    # es sell
                    self.log.info("Sell")
                    self.log.info("ahora operar la contraria pero en futuro2 BI ")
                    response = await self.operar_orden_contraria(orden, self.botData["futuro2"], "OF", id_order, 1)
            else:
                # es byma48h
                self.log.info("futuro2")
                if orden["side"] == "Buy":
                    self.log.info("Buy")
                    self.log.info("ahora operar la contraria pero en futuro1 OF ")
                    response = await self.operar_orden_contraria(orden, self.botData["futuro1"], "BI", id_order, 2)
                else:
                    # es sell
                    self.log.info("Sell")
                    self.log.info("ahora operar la contraria pero en futuro1 BI ")
                    response = await self.operar_orden_contraria(orden, self.botData["futuro1"], "OF", id_order, 1)
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
            if self.botData["market"]==True:
                self.log.info(f"esta market mando a crear orden nueva y cancelar orden haberla en 2 hilos ")
                size = orden["lastQty"]
                clOrdId = await self.clientR.getNextOrderBotID(self.botData["cuenta"], self.botData["id_bot"], id_order)
                task1 = asyncio.create_task(self.clientR.nueva_orden(symbolCheck, sideOrder, size,1, 1, clOrdId, 1))
                task2 = asyncio.create_task(self.clientR.nueva_orden(self.botData["paseFuturos"], sideOrder, size,1, 1, clOrdId, 1))
                ordenNew = await task1
                ordenPase = await task2
                self.log.info(f"llegaron respuestas, ordennew: {ordenNew}, ordenPase: {ordenPase}")
                response = {"ordenNew": ordenNew, "ordenPase": ordenPase }
            else:
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
                    task1 = asyncio.create_task(self.clientR.nueva_orden(symbolCheck, sideOrder, size, priceOrder, 2, clOrdId, 1))
                    #necesito el precio del pase 
                    precioPase = self._tickers[self.botData["paseFuturos"]][sideCheck][0]["price"]
                    task2 = asyncio.create_task(self.clientR.nueva_orden(self.botData["paseFuturos"], sideOrder, size, precioPase, 2, clOrdId, 1))
                   
                    ordenNew = await task1
                    ordenPase = await task2
                    self.log.info(f"llegaron respuestas, ordennew: {ordenNew}, ordenPase: {ordenPase}")
                    
                    response = {"ordenNew": ordenNew, "ordenPase": ordenPase }

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
                    task2 = asyncio.create_task(self.clientR.cancelar_orden_haberla(symbolCheck, sideOrder))
                    precioPase = self._tickers[self.botData["paseFuturos"]][sideCheck][0]["price"]
                    task2 = asyncio.create_task(self.clientR.nueva_orden(self.botData["paseFuturos"], sideOrder, size, precioPase, 2, clOrdId, 1))
                    ordenNew = await task1
                    ordenPase = await task2
                    self.log.info(f"llegaron respuestas, ordennew: {ordenNew}, ordenPase: {ordenPase}")
                    response = {"ordenNew": ordenNew, "ordenPase": ordenPase }
        except Exception as e:
            self.log.error(f"error operando orden contraria: {e}")
        return response

                        
    async def  guardar_orden_pegada(self,details, idPrincipal, idPegada ):
        self.log.info("guardar_orden_pegada")
        #quiero guardar el id de la orden operada principal , y los datos de la orden pegada 
        self.botData["idTriangulos"] +=1
        self.botData["pegados"].append({
            "id": self.botData["idTriangulos"],
            "idPrincipal": idPrincipal, 
            "idPegada":idPegada,
            "ordenPegada": details, 
            "ordenCierre1":{}, 
            "ordenCierre2": {}, 
            "status": 1
        })
        self.botData["triangulosPegados"] = True
    
    
    async def  verificar_cerrar_triangulo(self, details, typeOrder, clOrderID):
        self.log.info("entrando a verificar, cerrar triangulo")
        self.log.info("recorrer los triangulos a ver si mi orden me sirve para cerrar el triangulo viejo")
        symbolNueva = details["symbol"]
        sideNueva = details["side"]
        response = False
        for i in range(len(self.botData["pegados"])):
            response = await self.verificar_triangulo_pase(i, symbolNueva, sideNueva, typeOrder, details, clOrderID)
            if response == True:
                return response 
        return response 

    async def  verificar_triangulo_pase(self, i, symbolNueva, sideNueva, typeOrder, details, clOrderID):
        response = False
        if self.botData["pegados"][i]["ordenPegada"]["symbol"]==self.botData["paseFuturos"] and self.botData["pegados"][i]["ordenPegada"]["side"]=="Buy":
            self.log.info("es un pase buy pegado , x lo tanto necesito un futuro2 bid o futuro1 ask ")
            self.log.info("pero primero vamos a revisar q yo este de primero en el book ")
            if self._tickers[self.botData["paseFuturos"]]["BI"][0]["price"]==self.botData["pegados"][i]["ordenPegada"]["price"]:
                self.log.info("si estoy de primero en el book entonces esta orden me sirve para cerrar la orden vieja ")
                if symbolNueva==self.botData["futuro2"] and sideNueva=="Buy" or symbolNueva==self.botData["futuro1"] and sideNueva=="Sell":
                    self.log.info("si es un futuro q me sirve para cerrar el circulo viejo, bid2, ask1 ")
                    if typeOrder=="N":
                        self.log.info("enviar siguiente orden ")  
                        clOrdIdC = self.clientR.fix.getNextOrderBotIDC(clOrderID, self.botData["pegados"][i]["idPegada"], self.botData["pegados"][i]["idPrincipal"]  )
                        operarFuturo = await self.operar_futuro(details, "BI", clOrdIdC)
                        response = True
            else: 
                self.log.info("no estoy de primero en el book entonces no me sirve para cerrar la orden vieja ")
        
        if self.botData["pegados"][i]["ordenPegada"]["symbol"]==self.botData["paseFuturos"] and self.botData["pegados"][i]["ordenPegada"]["side"]=="Sell":
            self.log.info("es un pase sell pegado , x lo tanto necesito un futuro2 ask o futuro1 bid ")
            self.log.info("pero primero vamos a revisar q yo este de primero en el book ")
            if self._tickers[self.botData["paseFuturos"]]["OF"][0]["price"]==self.botData["pegados"][i]["ordenPegada"]["price"]:
                self.log.info("si estoy de primero en el book entonces esta orden me sirve para cerrar la orden vieja ")
                if symbolNueva==self.botData["futuro2"] and sideNueva=="Sell" or symbolNueva==self.botData["futuro1"] and sideNueva=="Buy":
                    self.log.info("si es un futuro q me sirve para cerrar el circulo viejo, bid1, ask2 ")
                    if typeOrder=="N":
                        self.log.info("enviar siguiente orden ")  
                        clOrdIdC = self.clientR.fix.getNextOrderBotIDC(clOrderID, self.botData["pegados"][i]["idPegada"], self.botData["pegados"][i]["idPrincipal"]  )
                        operarFuturo = await self.operar_futuro(details, "OF", clOrdIdC)
                        response = True
            else: 
                self.log.info("no estoy de primero en el book entonces no me sirve para cerrar la orden vieja ")
            #---futuros-------
        if self.botData["pegados"][i]["ordenPegada"]["symbol"]==self.botData["futuro1"] and self.botData["pegados"][i]["ordenPegada"]["side"]=="Buy":
            self.log.info("es bid1 pegado, necesito q me tomen bid2")
            if symbolNueva==self.botData["futuro2"] and sideNueva=="Buy": #es bid2
                self.log.info("es bid 2 la orden filled")
                if typeOrder=="N":
                    #ahora necesito q los sizes coincidan 
                    self.log.info("ahora necesito q los sizes coincidan")
                    if self.botData["pegados"][i]["ordenPegada"]["leavesQty"]==details["lastQty"]:
                        self.log.info("si es el mismo size entonces si puedo operar, en este caso ejecuto el pase necesario")
                        precioPase = self._tickers[self.botData["paseFuturos"]]["BI"][0]["price"]
                        clOrdIdC = self.clientR.fix.getNextOrderBotIDC(clOrderID, self.botData["pegados"][i]["idPegada"], self.botData["pegados"][i]["idPrincipal"]  )
                        ordenFuturo = self.clientR.fix.newOrderSingle(clOrdIdC,self.botData["paseFuturos"], 2, details["lastQty"], precioPase, 2 )
                        response = True

        if self.botData["pegados"][i]["ordenPegada"]["symbol"]==self.botData["futuro1"] and self.botData["pegados"][i]["ordenPegada"]["side"]=="Sell":
            self.log.info("es ask1 pegado, necesito q me tomen ask2")
            if symbolNueva==self.botData["futuro2"] and sideNueva=="Sell": #es ask2
                self.log.info("es bid 2 la orden filled")
                if typeOrder=="N":
                    #ahora necesito q los sizes coincidan 
                    self.log.info("ahora necesito q los sizes coincidan")
                    if self.botData["pegados"][i]["ordenPegada"]["leavesQty"]==details["lastQty"]:
                        self.log.info("si es el mismo size entonces si puedo operar, en este caso ejecuto el pase necesario")
                        precioPase = self._tickers[self.botData["paseFuturos"]]["OF"][0]["price"]
                        clOrdIdC = self.clientR.fix.getNextOrderBotIDC(clOrderID, self.botData["pegados"][i]["idPegada"], self.botData["pegados"][i]["idPrincipal"]  )
                        ordenFuturo = await self.clientR.fix.newOrderSingle(clOrdIdC,self.botData["paseFuturos"], 1, details["lastQty"], precioPase, 2 )
                        response = True

        if self.botData["pegados"][i]["ordenPegada"]["symbol"]==self.botData["futuro2"] and self.botData["pegados"][i]["ordenPegada"]["side"]=="Buy":
            self.log.info("es bid2 pegado, necesito q me tomen bid1")
            if symbolNueva==self.botData["futuro1"] and sideNueva=="Sell": #es bid1
                self.log.info("es bid 1 la orden filled")
                if typeOrder=="N":
                    #ahora necesito q los sizes coincidan 
                    self.log.info("ahora necesito q los sizes coincidan")
                    if self.botData["pegados"][i]["ordenPegada"]["leavesQty"]==details["lastQty"]:
                        self.log.info("si es el mismo size entonces si puedo operar, en este caso ejecuto el pase necesario")
                        precioPase = self._tickers[self.botData["paseFuturos"]]["OF"][0]["price"]
                        clOrdIdC = self.clientR.fix.getNextOrderBotIDC(clOrderID, self.botData["pegados"][i]["idPegada"], self.botData["pegados"][i]["idPrincipal"]  )
                        ordenFuturo = self.clientR.fix.newOrderSingle(clOrdIdC,self.botData["paseFuturos"], 1, details["lastQty"], precioPase, 2 )
                        response = True
        
        if self.botData["pegados"][i]["ordenPegada"]["symbol"]==self.botData["futuro2"] and self.botData["pegados"][i]["ordenPegada"]["side"]=="Sell":
            self.log.info("es ask2 pegado, necesito q me tomen ask1")
            if symbolNueva==self.botData["futuro1"] and sideNueva=="Sell": #es ask1
                self.log.info("es ask1  la orden filled")
                if typeOrder=="N":
                    #ahora necesito q los sizes coincidan 
                    self.log.info("ahora necesito q los sizes coincidan")
                    if self.botData["pegados"][i]["ordenPegada"]["leavesQty"]==details["lastQty"]:
                        self.log.info("si es el mismo size entonces si puedo operar, en este caso ejecuto el pase necesario")
                        precioPase = self._tickers[self.botData["paseFuturos"]]["BI"][0]["price"]
                        clOrdIdC = self.clientR.fix.getNextOrderBotIDC(clOrderID, self.botData["pegados"][i]["idPegada"], self.botData["pegados"][i]["idPrincipal"]  )
                        ordenFuturo = self.clientR.fix.newOrderSingle(clOrdIdC,self.botData["paseFuturos"], 2, details["lastQty"], precioPase, 2 )
                        response = True
   
        return response 
    
    async def  operar_futuro(self, orden, sidePase, clOrdIdC):
        if orden["symbol"]==self.botData["futuro2"]:
            self.log.info("es futuro 2")
            if orden["side"]=="Buy":
                self.log.info("es una orden buy ")
                ordenNew = await self.ejecutar_futuro(self.botData["futuro1"], "BI",   orden, sidePase, clOrdIdC )

            if orden["side"]=="Sell":
                self.log.info("es una orden sell ")
                ordenNew = await self.ejecutar_futuro(self.botData["futuro1"], "OF",   orden, sidePase, clOrdIdC )

        if orden["symbol"]==self.botData["futuro1"]:
            self.log.info("es futuro1")
            if orden["side"]=="Buy":
                self.log.info("es una orden buy ")
                ordenNew = await self.ejecutar_futuro(self.botData["futuro2"], "BI",   orden, sidePase, clOrdIdC )
                
            if orden["side"]=="Sell":
                self.log.info("es una orden sell ")
                ordenNew = await self.ejecutar_futuro(self.botData["futuro2"], "OF",   orden, sidePase, clOrdIdC )

    async def  ejecutar_futuro(self, futuro, sideF,  orden, sidePase, clOrdIdC ):
        self.log.info("hola ejecutar futuro  ")
        #ejemplo me tomaron futuro1 sell 
        self.log.info("verificar futuro ")
        verifyF = await self.clientR.verificar_ordenes_futuro(futuro, sideF, self._tickers[futuro][sideF])
        if verifyF["status"]==True:
            self.log.info("si tengo futuro ")
            size = orden["lastQty"]
            sideOrden = 2 #necesito hacer un buy limit con el precio del offer, entonces necesito el indice del offer
            indiceFuturo = verifyF["indiceBookUsar"]
            if sideF=="OF":
                sideOrden = 1
            priceFuturo = self._tickers[futuro][sideF][indiceFuturo]["price"]
            self.log.info(f"priceFuturo: {priceFuturo}")
            self.log.info("si tengo pase ")
            indicePase = 0
            precioPase = self._tickers[self.botData["paseFuturos"]][sidePase][indicePase]["price"]
            self.log.info(f"precioPase {precioPase}")
            #calculo el precio limit para la orden de futuro 
            precioLimit = ( float(orden["price"]) - float(precioPase) ) + self.botData["varGan"] #futuro2 buy
            if orden["side"]=="Sell":
                precioLimit = ( float(orden["price"]) - float(precioPase) ) - self.botData["varGan"] #futuro2 Sell
            if priceFuturo >= precioLimit:
                    precioLimit = priceFuturo

            if orden["symbol"]==self.botData["futuro1"]:
                precioLimit = ( float(orden["price"]) + float(precioPase) ) - self.botData["varGan"] #futuro1 sell 
                if orden["side"]=="Buy":
                    precioLimit = ( float(orden["price"]) + float(precioPase) ) + self.botData["varGan"] #futuro1 buy 
                if priceFuturo <= precioLimit:
                    precioLimit = priceFuturo
            #314 <= 314.3 #entonces hago el limit a precio de futuro 
     
            self.botData["ordenesBot"].append({"idOperada":clOrdIdC, "clOrdId": clOrdIdC, "size": size })
            ordenFuturo = self.clientR.fix.newOrderSingle(clOrdIdC,futuro, sideOrden, size, precioLimit, 2 )
 

    async def  borrar_triangulo_pegado(self, idPrincipal):
        index = -1
        for i in range(len(self.botData['pegados'])):
            if self.botData['pegados'][i]["idPrincipal"]==idPrincipal:
                index = i 
        if index!=-1:
            self.botData['pegados'].pop(index)
    async def verify_orden_pegada(self, details): 
        self.log.info("verify_orden_pegada", details)
        self.log.info("triangulos", self.botData['pegados'])
        response = {"status": False}
        for i in range(len(self.botData['pegados'])):
            if self.botData['pegados'][i]["ordenPegada"]["clOrdId"]==details["clOrdId"]:
                return {"status": True, "index": i}
        return response
    async def  cancelar_orden_pegada(self, idPegada):
        self.log.info(f"cancelar orden pegada {idPegada}")
        self.log.info(f"triangulos {self.botData['pegados']}")
        for i in range(len(self.botData['pegados'])):
            if self.botData['pegados'][i]["idPegada"]==idPegada:
              #  self.log.info("actualizar status a 0 , para desde le bot lento cancelar la orden")
             #   self.botData["pegados"][i]["status"] = 0
                sideOrder = 1 
                if self.botData['pegados'][i]["ordenPegada"]["side"]=="Sell":
                    sideOrder=2
                clOrdId = self.clientR.fix.getNextOrderID()
                self.clientR.fix.orderCancelRequest(clOrdId, self.botData['pegados'][i]["ordenPegada"]["clOrdId"], sideOrder, self.botData['pegados'][i]["ordenPegada"]["leavesQty"], self.botData['pegados'][i]["ordenPegada"]["symbol"])

