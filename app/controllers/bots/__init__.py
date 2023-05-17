from flask import jsonify, request
from flask_jwt_extended import  jwt_required,get_jwt_identity
from flask import  abort, make_response, request, jsonify
from app.models import BotsModel, DbUtils
from app.controllers.utils import UtilsController
import json
from app import mongo, sesionesFix, ObjectId, logging, datetime
from datetime import timedelta
from app import fixM
log = logging.getLogger(__name__)

class BotsController:
    @staticmethod
    def show_all(user_id, fix):
       # print("botscontroler params, ", user_id, fix)
        bots = []
        try: 
            fixJson = json.loads(fix)
            print(fixJson["user"])
            if fixJson["user"]!="" and fixJson["account"]!="":
                bots = BotsModel.get_all(user_id, fixJson)
        except Exception as e: 
            log.error(f"error en show_all: {e}")
        return jsonify(bots)
    
    async def   start_bot_new(): 
        from app import fixM
        req_obj = request.get_json()
      #  print("startBot",req_obj)
        id_bot = req_obj["id"]
        fix = req_obj["fix"]
        cuenta = fix["account"]
        id_fix = fix["user"]
        soloEscucharMercado = req_obj["soloEscucharMercado"]
        response = {"status": False}
        getFixTask = await fixM.get_fixTask_by_id_user(id_fix)
        if getFixTask:
            print("si existe la sesion fix ")
            getBotEjecutando = DbUtils.get_bot_activo(id_bot)
            if getBotEjecutando==False:
                abort(make_response(jsonify(message="no existe ese bot"), 404))
            log.info(f"si existe el bot en la db asi q continuo")
            id_bot_ejecutando = getBotEjecutando["_id"]
            type_bot = getBotEjecutando["type_bot"]
            symbols = getBotEjecutando["symbols"]
            opciones = getBotEjecutando["opciones"]
            if getBotEjecutando["status"]==0:
                log.info(f"el bot esta desactivado asi q lo inicio")
                opciones = getBotEjecutando["opciones"]
                if not "market" in opciones:
                    opciones["market"] = False
                if type_bot == 0:#triangulo
                    response = await UtilsController.iniciar_bot_triangulo(getFixTask.botManager, id_fix, id_bot_ejecutando,cuenta, symbols, opciones, soloEscucharMercado, getFixTask)
                if type_bot == 1:#CI-48
                    response = await UtilsController.iniciar_bot_ci_48(getFixTask.botManager, id_fix, id_bot_ejecutando,cuenta, symbols, opciones, soloEscucharMercado, getFixTask)
                if type_bot == 2:#CI-CI
                    response = await UtilsController.iniciar_bot_ci_ci(getFixTask.botManager, id_fix, id_bot_ejecutando,cuenta, symbols, opciones, soloEscucharMercado, getFixTask)
                if type_bot == 3:#CI-48-BB
                    response = await UtilsController.iniciar_bot_ci_48_bb(getFixTask.botManager, id_fix, id_bot_ejecutando,cuenta, symbols, opciones, soloEscucharMercado, getFixTask)
            else:
                log.info(f"el bot esta en otro estado asi q lo actualizo")
                #activar bot 
                getFixTask.botManager.main_tasks[id_bot_ejecutando].botData["soloEscucharMercado"] = soloEscucharMercado
                task = {"type":0}
                await getFixTask.botManager.main_tasks[id_bot_ejecutando].add_task(task)
                status = 1
                if soloEscucharMercado==True: 
                    status = 2
                await DbUtils.update_bot_ejecutandose(id_bot_ejecutando, status)
                response = {"status": True, "msg": "el bot ya se esta ejecutando, actualizamos"}
        else:
            print("no existe la sesion")
            response = {"status": False, "error": "no existe la sesion"}
            abort(make_response(jsonify(message=response), 401))
        return response
           
    def start_bot():
        req_obj = request.get_json()
        print("startBot",req_obj)
        id_bot = req_obj["id"]
        fix = req_obj["fix"]
        cuenta = fix["account"]
        id_fix = fix["user"]
        soloEscucharMercado = req_obj["soloEscucharMercado"]
        response = {"status": False}
        if id_fix in sesionesFix:
            log.info(f"si existe a session: {id_fix}")
            print("si existe a session")
          
            getBotEjecutando = DbUtils.get_bot_activo(id_bot)
            if getBotEjecutando==False:
                abort(make_response(jsonify(message="no existe ese bot"), 404))
            id_bot_ejecutando = getBotEjecutando["_id"]
            type_bot = getBotEjecutando["type_bot"]
            symbols = getBotEjecutando["symbols"]
            opciones = getBotEjecutando["opciones"]
            if getBotEjecutando["status"]==0:
                opciones = getBotEjecutando["opciones"]
                if not "market" in opciones:
                    opciones["market"] = False
                if type_bot == 0:#triangulo
                    response = UtilsController.iniciar_bot_triangulo(id_fix, id_bot_ejecutando, cuenta, symbols, opciones, soloEscucharMercado)
                if type_bot == 1:#CI-48
                    response = UtilsController.iniciar_bot_ci_48(id_fix, id_bot_ejecutando,cuenta, symbols, opciones, soloEscucharMercado)
                if type_bot == 2:#CI-48
                    response = UtilsController.iniciar_bot_ci_ci(id_fix, id_bot_ejecutando,cuenta, symbols, opciones, soloEscucharMercado)
                if type_bot == 3:#CI-48-BB
                    response = UtilsController.iniciar_bot_ci_48_bb(id_fix, id_bot_ejecutando,cuenta, symbols, opciones, soloEscucharMercado)
        
            else:
                #activar bot 
                sesionesFix[id_fix].application.triangulos[cuenta][id_bot_ejecutando].botData["soloEscucharMercado"] = soloEscucharMercado
                sesionesFix[id_fix].application.triangulos[cuenta][id_bot_ejecutando].botData["editandoBot"] = True
                status = 1
                if soloEscucharMercado==True: 
                    status = 2
                DbUtils.update_bot_ejecutandose(id_bot_ejecutando, status)

                response = {"status": True, "msg": "el bot ya se esta ejecutando, actualizamos"}
           
        else:
            print("no existe la sesion")
            response = {"status": False, "error": "no existe la sesion"}
        return jsonify(response)
    
    async def edit_bot():
        req_obj = request.get_json()
        log.info(f"req_obj: {req_obj}")
        id_bot = req_obj["id_bot"]
        fix = req_obj["fix"]
        opciones = req_obj["opciones"]
        typeEdit = req_obj["typeEdit"]
        response = {"status": False}
        if typeEdit==0: #edit general 
            if req_obj["fix"]["active"]==0:
                try:
                    result = mongo.db.bots.update_one({'_id': ObjectId(id_bot)}, {'$set': {'opciones': opciones}})
                    response = {"status": True}
                    return jsonify(response)
                except Exception as e:
                    log.error(f"error editando bot general: {e} ")
                    response = {"status": False, "msg": e}
                    abort(make_response(jsonify(message=response), 401))
            else:
                return jsonify(1)
        else: 
            #edit bot ejecutandose 
            type_bot = int(req_obj["type_bot"])
            if type_bot == 0: 
                response = UtilsController.editar_bot_triangulo(id_bot, fix, opciones)
            if type_bot == 1: 
                response = await UtilsController.editar_bot_ci_48(id_bot, fix, opciones)
            if type_bot == 2: 
                response = await UtilsController.editar_bot_ci_ci(id_bot, fix, opciones)
            if type_bot == 3: 
                response = await UtilsController.editar_bot_ci_48_bb(id_bot, fix, opciones)
            if response["status"]==False:#retornar abort
                abort(make_response(jsonify(message=response), 401))
            return jsonify(response)

    async def detener_bot():
        req_obj = request.get_json()
        log.info(f"DETENER BOT: {req_obj}")
        id_bot = req_obj["id"]
        fix = req_obj["fix"]
        response = {"status": True}
   
        if fix["active"]==1:
            #  await DbUtils.update_status_bot_ejecuntadose(id_bot, 0)
            #ahora cancelar las ordenes abiertas 
            response = await UtilsController.detener_bot_by_id(fix, id_bot)
        else:
            log.info("fix no esta activa, entonces actualizo solo en db ")
            await DbUtils.update_status_bot_ejecuntadose(id_bot, 0)
            response = {"status": True}
        
        return jsonify(response)
    
    @jwt_required()
    def bot_data_charts(id):
        req_obj = request.get_json()
        print(req_obj)
        try: 
            fix = req_obj["fix"]
            botE = mongo.db.bots_ejecutandose.find_one({
                "user_fix": fix["user"], 
                "cuenta": fix["account"], 
                "id_bot": id
            })
            if botE: 
                log.info("el bot existe en bot ejecutandose")
            else:
                log.info("el bot no existe en bot ejecutandose ")
                log.info("necesito los datos del bot original ")
                bot = mongo.db.bots.find_one({'_id': ObjectId(id)})
                if bot:
                    bot['_id'] = str(bot['_id'])
                    log.info("ahora a crear el bot ejecutando ")
                    botE = DbUtils.get_bot_ejecutandose(fix["user"], id, fix["account"],bot["symbols"], bot["opciones"], 0, bot["type_bot"] )
                    if botE == None:
                        abort(make_response(jsonify(message="botE vacio"), 401))
                else:
                    abort(make_response(jsonify(message="no se encontro el id del bot"), 401))
            botE['_id'] = str(botE['_id'])
            botE_id = botE['_id']
            log.info(f"botE_id: {botE_id}")
            botE_cuenta = botE['cuenta']
            statusBot = botE["status"]
            if statusBot==0:
                return jsonify(botE)
            else:
                #aqui si esta activo completamente buscar todos los demas datos 
                #necesito el tipo de bot para saber q datos traer 
                if botE["type_bot"]==0: 
                    log.info("es triangulo")
                    # Obtener la fecha actual
                    fecha_actual = datetime.today()

                    # Agregar 4 horas a la fecha actual
                    fecha_actual_mas_4h = fecha_actual + timedelta(hours=4)

                    # Convertir la fecha a un formato legible
                    fecha_actual_mas_4h_str = fecha_actual_mas_4h.strftime("%Y%m%d")

                    ordenesToda = mongo.db.ordenes.find({
                        "id_bot": botE_id, 
                        "cuenta": botE_cuenta, 
                        "transactTime": {"$regex": f"^{fecha_actual_mas_4h_str}"}
                    }, {"_id": 0})
                    

                    arrayBook = fixM.main_tasks[fix["user"]].botManager.main_tasks[botE_id]._tickers
                    posiciones = fixM.main_tasks[fix["user"]].botManager.main_tasks[botE_id].botData["posiciones"]
                    posiciones = UtilsController.get_tenencias_bot(posiciones)
                    botE["limitsPuntas"] = fixM.main_tasks[fix["user"]].botManager.main_tasks[botE_id].botData["limitsBB"]
                    botE["ordenesToda"] = list(ordenesToda)
                    botE["arrayBook"] = arrayBook
                    botE["posiciones"] = posiciones
                #  log.info(f"esto es lo q voy a retornar botE: {botE}")
                    return jsonify(botE)
                elif botE["type_bot"]==1 or botE["type_bot"]==2 or botE["type_bot"]==3: 
                    log.info("es ci/48")
                    # Obtener la fecha actual
                    fecha_actual = datetime.today()

                    # Agregar 4 horas a la fecha actual
                    fecha_actual_mas_4h = fecha_actual + timedelta(hours=4)

                    # Convertir la fecha a un formato legible
                    fecha_actual_mas_4h_str = fecha_actual_mas_4h.strftime("%Y%m%d")

                    ordenesToda = mongo.db.ordenes.find({
                        "id_bot": botE_id, 
                        "cuenta": botE_cuenta, 
                        "transactTime": {"$regex": f"^{fecha_actual_mas_4h_str}"}
                    }, {"_id": 0})
                    

                    arrayBook = fixM.main_tasks[fix["user"]].botManager.main_tasks[botE_id]._tickers
                    posiciones = fixM.main_tasks[fix["user"]].botManager.main_tasks[botE_id].botData["posiciones"]
                    posiciones = UtilsController.get_tenencias_bot(posiciones)
                    ruedaA = fixM.main_tasks[fix["user"]].botManager.main_tasks[botE_id].botData["ruedaA"]
                    ruedaB = fixM.main_tasks[fix["user"]].botManager.main_tasks[botE_id].botData["ruedaB"]
                    if botE["type_bot"]==3: 
                        botE["dataBB"] = DbUtils.get_data_bb_intradia_hoy(botE_id)
                    botE["limitsPuntas"] = fixM.main_tasks[fix["user"]].botManager.main_tasks[botE_id].botData["limitsBB"]
                    botE["ordenesToda"] = list(ordenesToda)
                    botE["arrayBook"] = arrayBook
                    botE["posiciones"] = posiciones
                    botE["ruedaA"] = ruedaA
                    botE["ruedaB"] = ruedaB
                #  log.info(f"esto es lo q voy a retornar botE: {botE}")
                    return jsonify(botE)
        except Exception as e: 
            log.error(f"error en get botchar: {e}")
            abort(make_response(jsonify(message=f"botE error {e}"), 401))
    
    def deleteBot(id):
        try:
            print("delete bots",id)
            count = mongo.db.bots_ejecutandose.count_documents({"id_bot": id, "status": {"$gt": 0}})
            if count > 0:
                abort(make_response(jsonify(message="este bot esta siendo ejecutado actualmente, borrarlo seria una catastrofe jajaja"), 401))
            delete = mongo.db.bots_ejecutandose.delete_many({
                "id_bot": id
            })
            result = mongo.db.bots.delete_one({'_id': ObjectId(id)})
            return {"status": True}
        except Exception as e: 
            return {"status": False}
    
    def add_bot():
        req_obj = request.get_json()
        req_obj["status"]=0
        print(req_obj)
        try: 
            resultado = mongo.db.bots.insert_one(req_obj)
            response = {
                "status":True
            }
        except Exception() as e:
            response = {
                "status": False, 
                "msg": e
            }
        return jsonify(response)