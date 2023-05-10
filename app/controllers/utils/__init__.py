import gc
from app import mongo, sesionesFix, ObjectId
from app.models import DbUtils
from app import time, logging, asyncio
import os
import json
from app.clases.botManager import botManager
log = logging.getLogger(__name__)


class UtilsController:
    @staticmethod
    async def iniciar_bot_ci_48_bb(botM: botManager, id_fix, id_bot, cuenta, symbols, opciones, soloEscucharMercado, fix):
        from app.clases.botManager.bots.bot_bb import botBB
        # en este punto sabemos que la sesion fix esta iniciada y todo bien
        # ahora tenemos que entrar al bot manager y iniciar este bot como tarea

        log.info(
            f"id_fix : {id_fix}, id_bot: {id_bot}, symbols: {symbols}, opciones: {opciones}")
        log.info(
            f"minRate: {opciones['minRate']}, maxRate: {opciones['maxRate']}, sizeMax: {opciones['sizeMax']}")
        log.info(f"symbols: {symbols[0]}, {symbols[1]}")
        response = {"status": False}
        try:
            bot_bb = botBB(symbols[0], symbols[1], float(opciones["minRate"]), float(
                opciones["maxRate"]), fix.application, id_bot, cuenta, mongo)
            bot_bb.botData["sizeMax"] = int(opciones["sizeMax"])
            bot_bb.botData["type_side"] = int(opciones["type_side"])
            bot_bb.botData["soloEscucharMercado"] = soloEscucharMercado
            bot_bb.botData["ruedaA"]["sizeDisponible"] = int(
                opciones["sizeMax"])
            bot_bb.botData["ruedaB"]["sizeDisponible"] = int(
                opciones["sizeMax"])
            # agregar con el bot manager
            log.info(f"botM: {botM}")
            log.info(f"voy a iniciar la tarea en el botManager")
            taskBotManager = await botM.add_task(bot_bb)
            # response = UtilsController.esperar_bot_iniciado(id_fix, id_bot, cuenta)
            # await asyncio.sleep(4)
         #   if response["status"]==True:
            await asyncio.sleep(4)
            log.info("el bot ha sido iniciado")
            # actualizar el status del bot
            status = 1
            if soloEscucharMercado == True:
                status = 2
            await DbUtils.update_bot_ejecutandose(id_bot, status)
            response = {"status": True, "statusBot": status}

        except Exception as e:
            response = {"status": False, "error": str(e)}
            log.info(f"error: {str(e)}")
        return response

    async def iniciar_bot_ci_48(botM: botManager, id_fix, id_bot, cuenta, symbols, opciones, soloEscucharMercado, fix):
        from app.clases.botManager.bots.bot_ci_48 import botCi48
        # en este punto sabemos que la sesion fix esta iniciada y todo bien
        # ahora tenemos que entrar al bot manager y iniciar este bot como tarea

        log.info(
            f"id_fix : {id_fix}, id_bot: {id_bot}, symbols: {symbols}, opciones: {opciones}")
        log.info(
            f"minRate: {opciones['minRate']}, maxRate: {opciones['maxRate']}, sizeMax: {opciones['sizeMax']}")
        log.info(f"symbols: {symbols[0]}, {symbols[1]}")
        response = {"status": False}
        try:
            bot_bb = botCi48(symbols[0], symbols[1], float(opciones["minRate"]), float(
                opciones["maxRate"]), fix.application, id_bot, cuenta, mongo)
            bot_bb.botData["sizeMax"] = int(opciones["sizeMax"])
            bot_bb.botData["soloEscucharMercado"] = soloEscucharMercado
            bot_bb.botData["ruedaA"]["sizeDisponible"] = int(
                opciones["sizeMax"])
            bot_bb.botData["ruedaB"]["sizeDisponible"] = int(
                opciones["sizeMax"])
            # agregar con el bot manager
            log.info(f"botM: {botM}")
            log.info(f"voy a iniciar la tarea en el botManager")
            taskBotManager = await botM.add_task(bot_bb)
            # response = UtilsController.esperar_bot_iniciado(id_fix, id_bot, cuenta)
            # await asyncio.sleep(4)
         #   if response["status"]==True:
            await asyncio.sleep(4)
            log.info("el bot ha sido iniciado")
            # actualizar el status del bot
            status = 1
            if soloEscucharMercado == True:
                status = 2
            await DbUtils.update_bot_ejecutandose(id_bot, status)
            response = {"status": True, "statusBot": status}

        except Exception as e:
            response = {"status": False, "error": str(e)}
            log.info(f"error: {str(e)}")
        return response

    def iniciar_bot_ci_ci(id_fix, id_bot, cuenta,  symbols, opciones, soloEscucharMercado):
        log.info(
            f"id_fix : {id_fix}, id_bot: {id_bot}, symbols: {symbols}, opciones: {opciones}")
        log.info(
            f"minRate: {opciones['minRate']}, maxRate: {opciones['maxRate']}, sizeMax: {opciones['sizeMax']}")
        log.info(f"symbols: {symbols[0]}, {symbols[1]}")
        response = {"status": False}
        try:
            log.info("entrando a try")
            sesionesFix[id_fix].application.triangulos[cuenta] = {
                id_bot: botCiCi(symbols[0], symbols[1], float(opciones["minRate"]), float(
                    opciones["maxRate"]), sesionesFix[id_fix].application, id_bot, cuenta)
            }
            log.info("segunda linea")
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["sizeMax"] = int(
                opciones["sizeMax"])
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["soloEscucharMercado"] = soloEscucharMercado
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["ruedaA"]["sizeDisponible"] = int(
                opciones["sizeMax"])
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["ruedaB"]["sizeDisponible"] = int(
                opciones["sizeMax"])
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].daemon = True
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].start()
            time.sleep(4)
            log.info("esperar bot iniciado ")
            response = UtilsController.esperar_bot_iniciado(
                id_fix, id_bot, cuenta)
            if response["status"] == True:
                log.info("el bot ha sido iniciado")
                # actualizar el status del bot
                status = 1
                if soloEscucharMercado == True:
                    status = 2
                DbUtils.update_bot_ejecutandose(id_bot, status)
                response = {"status": True, "statusBot": status}

        except Exception as e:
            response = {"status": False, "error": str(e)}
            log.info(f"error: {str(e)}")
        return response

    def iniciar_bot_triangulo(id_fix, id_bot, cuenta, symbols, opciones, soloEscucharMercado):
        response = {"status": False}
        try:

            log.info(
                f"iniciar bot triangulo: {sesionesFix[id_fix].application.triangulos} ")
            sesionesFix[id_fix].application.triangulos[cuenta] = {
                id_bot: botLento(symbols[0], symbols[1], symbols[2],
                                 sesionesFix[id_fix].application, id_bot, cuenta)
            }
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["sizeMax"] = opciones["sizeMax"]
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["soloEscucharMercado"] = soloEscucharMercado
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].daemon = True
            sesionesFix[id_fix].application.triangulos[cuenta][id_bot].start()
            time.sleep(4)
            response = UtilsController.esperar_bot_iniciado(
                id_fix, id_bot, cuenta)

            if response["status"] == True:
                log.info("el bot ha sido iniciado")
                # actualizar el status del bot
                status = 1
                if soloEscucharMercado == True:
                    status = 2

            #  update_status_bot(id_bot, status)
        except Exception as e:
            response = {"status": False, "error": str(e)}
            log.info(f"error: {e}")
        return response

    def esperar_bot_iniciado(id_fix, id_bot, cuenta):
        response = {"status": False}
        try:
            inicio = time.time()  # inicio contador de tiempo de espera
            while True:
                if sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["botIniciado"] != None:
                    if sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["botIniciado"] == True:
                        response = {"status": True}
                        break
                    else:
                        break
                fin = time.time()
                tiempoEsperado = fin-inicio
                if tiempoEsperado > 30:  # si paso mas de 30 segundos, no llego la respuesta
                    response = {
                        "status": False, "msg": "tiempo excedido, no llego respuesta o algo mas paso"}
                    break
                time.sleep(0.1)
        except Exception as e:
            log.error(f"error en esperar_bot_iniciado: {e}")
        return response

    async def detener_bot_by_id(fix, id_bot):
        from app import fixM
        from app.clases.class_main import MainTask
        log.info(f"entrando a detener bot byid: {id_bot} ")
        response = {"status": False}
        id_fix = fix["user"]
        cuenta = fix["account"]
        log.info(f"fixM: {fixM}")
        getFixTask:MainTask = await fixM.get_fixTask_by_id_user(id_fix)
        if getFixTask:
            log.info(f"si existe a session: {id_fix}")
            try:
                
                if id_bot in getFixTask.botManager.main_tasks:
                    log.info(f"borrar ordenes del bot")
                    log.info(f"si existe a bot: {id_bot}")
                    # buscar en db las ordenes de este bot y cancelarlas
                    log.info("pausar y detener cola del bot")
                    await getFixTask.botManager.main_tasks[id_bot].pause()
                    await getFixTask.botManager.main_tasks[id_bot].detenerBot() 
                    ordenes = mongo.db.ordenes.find({"active": True, "id_bot": id_bot, "cuenta": cuenta}, {"_id": 0})

                    if ordenes:
                        ordenesBorrar = list(ordenes)
                        log.info(f"ordenes: {ordenesBorrar}")
                        log.info(f"hay {len(ordenesBorrar)} ordenes")
                        contadorOrdenesCanceladas = 0

                        for x in ordenesBorrar:
                            log.info(f"borrar orden: {x}")
                            result = await UtilsController.cancelar_orden_async(
                                id_fix, id_bot, x["orderId"], x["clOrdId"], x["side"], x["leavesQty"], x["symbol"], cuenta)
                            if result["llegoRespuesta"] == True:
                                contadorOrdenesCanceladas += 1
                        log.info(
                            f"se cancelaron: {contadorOrdenesCanceladas} ordenes")
                        
                    log.info(f"botManager Yasks: {getFixTask.botManager.tasks}")
                    codigoSuscribir = getFixTask.botManager.main_tasks[id_bot].clientR.codigoSuscribir
                    log.info(f"codigo suscribir del bot q voy a detener: {codigoSuscribir}")
                    if codigoSuscribir in fixM.main_tasks[id_fix].application.suscripcionId:
                        log.info(f"borrar suscripcion : {fixM.main_tasks[id_fix].application.suscripcionId} ")
                        del fixM.main_tasks[id_fix].application.suscripcionId[codigoSuscribir]
                    log.info(f"suscripcion borrada : {fixM.main_tasks[id_fix].application.suscripcionId} ")
                    #ahora quitar suscripcion via fix 
                    symbolsBot = getFixTask.botManager.main_tasks[id_bot].botData["symbols2"]
                    respSusOff = await getFixTask.botManager.main_tasks[id_bot].clientR.suscribir_mercado_off(symbolsBot,codigoSuscribir)
                    await getFixTask.botManager.stop_task_by_id(id_bot)
                    log.info(f"botManager Yasks: {getFixTask.botManager.tasks}")
                await DbUtils.update_status_bot_ejecuntadose(id_bot, 0)
                log.info(f"fixM: {fixM}")
                response = {"status": True}
            except Exception as e:
                log.info(
                    f"error en: {e}")
                response = {"status": False}
        else:
            log.info(f"no existe la session en: {sesionesFix}")
            response = {"status": True}
        return response

    def editar_bot_triangulo(id_bot, fix, opciones):
        response = {"status": False}
        id_fix = fix["user"]
        cuenta = fix["account"]
        try:
            if id_fix in sesionesFix and id_bot in sesionesFix[id_fix].application.triangulos[cuenta]:
                sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["sizeMax"] = int(
                    opciones["sizeMax"])
                sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["varGan"] = float(
                    opciones["spreadMin"])
                sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["editandoBot"] = True
                time.sleep(1)
            # ahora guardar los datos en db
            result = mongo.db.bots_ejecutandose.update_one(
                {'_id': ObjectId(id_bot)}, {'$set': {'opciones': opciones}})
            response = {"status": True}
        except Exception as e:
            response = {"status": False, "error": str(e)}
            log.error(f"error: {str(e)}")
        return response

    async def editar_bot_ci_48(id_bot, fix, opciones):
        from app import fixM
        response = {"status": False}
        id_fix = fix["user"]
        cuenta = fix["account"]
        try:
            if id_fix in fixM.main_tasks and id_bot in fixM.main_tasks[id_fix].botManager.main_tasks:
                fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].minimum_arbitrage_rate = float(
                    opciones["minRate"])
                fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].maximum_arbitrage_rate = float(
                    opciones["maxRate"])
                fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].botData["type_side"] = int(
                    opciones["type_side"])
                task = {"type":0}
                await fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].add_task(task)
            # ahora guardar los datos en db
            result = mongo.db.bots_ejecutandose.update_one(
                {'_id': ObjectId(id_bot)}, {'$set': {'opciones': opciones}})
            response = {"status": True}
            
        except Exception as e:
            response = {"status": False, "error": str(e)}
            log.error(f"error: {str(e)}")
        return response

    async def editar_bot_ci_ci(id_bot, fix, opciones):
        response = {"status": False}
        id_fix = fix["user"]
        cuenta = fix["account"]
        try:
            if id_fix in sesionesFix and id_bot in sesionesFix[id_fix].application.triangulos[cuenta]:
                sesionesFix[id_fix].application.triangulos[cuenta][id_bot].minimum_arbitrage_rate = float(
                    opciones["minRate"])
                sesionesFix[id_fix].application.triangulos[cuenta][id_bot].maximum_arbitrage_rate = float(
                    opciones["maxRate"])
                sesionesFix[id_fix].application.triangulos[cuenta][id_bot].botData["editandoBot"] = True
                time.sleep(1)
            # ahora guardar los datos en db
            result = mongo.db.bots_ejecutandose.update_one(
                {'_id': ObjectId(id_bot)}, {'$set': {'opciones': opciones}})
            response = {"status": True}
        except Exception as e:
            response = {"status": False, "error": str(e)}
            log.error(f"error: {str(e)}")
        return response

    async def editar_bot_ci_48_bb(id_bot, fix, opciones):
        from app import fixM
        response = {"status": False}
        id_fix = fix["user"]
        cuenta = fix["account"]
        try:
            if id_fix in fixM.main_tasks and id_bot in fixM.main_tasks[id_fix].botManager.main_tasks:
                fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].minimum_arbitrage_rate = float(
                    opciones["minRate"])
                fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].maximum_arbitrage_rate = float(
                    opciones["maxRate"])
                fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].botData["type_side"] = int(
                    opciones["type_side"])
                fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].botData["editandoBot"] = True
                task = {"type":0}
                await fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].add_task(task)
            # ahora guardar los datos en db
            result = mongo.db.bots_ejecutandose.update_one(
                {'_id': ObjectId(id_bot)}, {'$set': {'opciones': opciones}})
            response = {"status": True}
            
        except Exception as e:
            response = {"status": False, "error": str(e)}
            log.error(f"error: {str(e)}")
        return response

    def get_tenencias_bot(posiciones):
        log.info(f"entrando a get tenencias bot: {posiciones}")
        arrayTenencias = []
        try:
            for x in posiciones:
                log.info(f"tenencia: {posiciones[x]}")
                symbol = x
                tenencia = int(posiciones[x]["BI"]) - int(posiciones[x]["OF"])
                objTenencia = {
                    "symbol": symbol,
                    "tenencia": tenencia
                }
                arrayTenencias.append(objTenencia)
        except Exception as e:
            log.error(f"error en get tenencias bot: {e}")
        return arrayTenencias

    async def cancelar_orden_async(id_fix, id_bot, orderID, OrigClOrdID, side, quantity, symbol, cuenta):
        from app import fixM
        log.info("entrando a cancelar orden async")
        response = {"llegoRespuesta":False}
        try:
            sideFix = 1
            if side == "Sell":
                sideFix = 2
            response = await fixM.main_tasks[id_fix].botManager.main_tasks[id_bot].clientR.cancelar_orden(
                orderID, OrigClOrdID, sideFix, quantity, symbol)
        except Exception as e:
            log.error(f"error en cancelar_orden_async: {e}")
        return response

    def guardar_security_in_fix(data, id_fix):
        for x in data:
            sesionesFix[id_fix].application.securitysList[x["symbol"]] = x
        return True

    def fetch_securitys_data(id_fix):
        log.info("fetch_securitys_data")
        lista = sesionesFix[id_fix].application.securitysList
        arraySecuritys = []
        for x in lista:
            arraySecuritys.append(lista[x])
        log.info(f"lista de securitys {len(arraySecuritys)} ")
        for security in arraySecuritys:
            securityDesc = security['securityDesc']
            securityDescUnicode = securityDesc.encode(
                'ascii', 'ignore').decode('utf-8')
            security['securityDesc'] = securityDescUnicode

        return arraySecuritys

    def get_precios_bonos():
        ruta_archivo = os.path.join(os.getcwd(), "app/dataJson/precios.json")
        with open(ruta_archivo) as archivo:
            json_data = json.load(archivo)
        return json_data
