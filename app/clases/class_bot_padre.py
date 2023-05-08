import datetime
import asyncio
from collections import defaultdict
from typing import DefaultDict,  Dict
from threading import Thread
from app.clases.class_client_request import client_request
import logging
import time
import pyRofex

class botPadre(Thread):
    def __init__(self, symbols, f, id_bot):#f=instancia de fix, id_bot= id del bot que se está ejecutando
        Thread.__init__(self)
        self.clientR = client_request(f, id_bot) #instancia de la clase client_request
        self._tickers: DefaultDict[str, Dict[str, float]] = defaultdict(dict) #diccionario de diccionarios donde estaran los datos del book suscritos
        self.log = logging.getLogger(f"tasa_inversa_bot_{id_bot}")#log para el bot
        self.botData = {#diccionario con las variables q el bot usará 
                        "id_bot": id_bot,#lo uso para guardar el id en db y asi poder seguir las ordenes de cada bot
                        "detener": False,#la uso para detener el bot
                        "botIniciado": None,#la uso para en el dashboard saber q el bot ya inicio correctamente o no
                        "ordenOperada": False, #la uso para saber si ya se opero una orden
                        "llegoTickers": False, #la uso para saber si ya llegaron los tickers
                        "bookChangeTime": None,#la uso para marcar el tiempo despues de un cambio de mercado, 
                        "editandoBot": False,
                        "symbols2": [symbols],
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