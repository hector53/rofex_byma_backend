from app import jsonify, request, abort, make_response
from app import  jwt_required,get_jwt_identity
from app import  ObjectId, mongo, logging, sesionesFix, time, server_md
from app import config_fix_settings
from app.models import DbUtils
from app.controllers.utils import UtilsController
from datetime import date, datetime
from app.clases.class_main import MainTask, FixMsgQueue
import asyncio
from threading import Thread
from app import thread 
from aiohttp import web
import gc
from app.clases.class_rest_primary import RofexAPI
log = logging.getLogger(__name__)
class FixController:

    @staticmethod
    async def newOrderTest():
        from app import fixM
      #  async def newOrderSingle(self, clOrdId, symbol, side, quantity, price, orderType, 
           #                      idTriangulo=0, cuenta=""):
        req_obj = request.get_json()
        print("req", req_obj)
        dataOrder = req_obj["dataOrder"]
        userFix = req_obj["userFix"]
        fixTask = await fixM.get_fixTask_by_id_user(userFix)
        if fixTask: 
            print("si tenemos la sesion iniciada para ese user")
            order = await fixTask.application.newOrderSingle(dataOrder["clOrdId"], dataOrder["symbol"],
                                                       dataOrder["side"], dataOrder["quantity"], 
                                                       dataOrder["price"], dataOrder["orderType"],
                                                       cuenta=dataOrder["cuenta"]
                                                        )
            return jsonify(order)
        else:
            print("no tenemos la sesion iniciada")
            abort(make_response(jsonify(message="sesion no iniciada"), 400))
        
        
    def ciclo_infinito(id):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(FixController.ciclo_infinito_coro(id))
        finally:
            loop.close()

    # Función que ejecuta el ciclo infinito utilizando asyncio
    async def ciclo_infinito_coro(id):
        try: 
            while True:
                # Aquí puedes poner el código que quieras ejecutar en el ciclo infinito
                log.info(f"estoy en el ciclo infinito con asyncio: {id}")
                await asyncio.sleep(1)
        finally:
            log.info("saliendo del ciclo")



    def initC():
        global thread
        id = len(thread)
        thread[id] = Thread(target=FixController.ciclo_infinito, args=(id,))
        thread[id].start()
        # Creamos un nuevo hilo y lo iniciamos
        return 'Ciclo infinito iniciado'
    

        
      
    def stopC():
        global thread
        if thread is not None:
            # Detenemos el hilo
            thread.stop()
            thread = None
            return 'Ciclo infinito detenido'
        else:
            return 'El ciclo infinito no está en ejecución'


    async def iniciar_fix_new():
        from app import fixM
        req_obj = request.get_json()
        print("req iniciar fix", req_obj)
        id_fix = req_obj["user"]["user"]
        accountFixId = req_obj["user"]["id"]
        BeginString = "FIXT.1.1"
        target = "ROFX"
        settings = config_fix_settings(req_obj["user"]["puerto"], BeginString, id_fix, target, id_fix)
        response = {"status": True, "id_fix": id_fix}
        log.info("voy a iniciar otro ciclo infinito antes")
        mainFix = MainTask(settings, target, id_fix, req_obj["user"]["password"], req_obj["cuenta"], target,server_md, accountFixId)
        url_rest = "https://api.remarkets.primary.com.ar/"
        if int(req_obj["user"]["live"])==1: 
            url_rest = req_obj["user"]["url_rest"]
        mainFix.application.rest = RofexAPI(user=id_fix, password=req_obj["user"]["password"], base_url=url_rest)
        log.info(f"fixM: {fixM}")
        await fixM.add_task(mainFix)
        login = await mainFix.check_logged_on()
        log.info("saliendo de checkLogOn en flask ")
        log.info(f"fixM: {fixM.tasks}")
        if login==True:
            log.info("login = true")
            
            #actualizar el status de la sesion en la tabla fix_sessions
            #ahora vamos a iniciar el bot manual en la sesion de fix 
            await DbUtils.update_fix_session_mongo(req_obj["user"]["id"], 1)
            log.info("dbultil = true")
            #pasar loop 
        #   mainFix.application.loop = asyncio.get_event_loop()
            #ahora aqui voy a crear un nuevo fixMsgManager y s elo paso a application 
            #  mainFixMsqQueue.stop()
          #  log.info(f"fixM: {fixM.tasks}")
          #  await asyncio.sleep(5)
          #  log.info(f"fixM: {fixM.tasks}")
            return jsonify(response)
        else:
          #  await asyncio.sleep(5)
            return {"status": False}
    


    @staticmethod
    async def iniciar_fix_m():
        req_obj = request.get_json()
        print("req", req_obj)
        
        id_fix = req_obj["user"]["user"]
        user_id = req_obj["user"]["id"]
        BeginString = "FIXT.1.1"
        target = "ROFX"
        settings = config_fix_settings(req_obj["user"]["puerto"], BeginString, id_fix, target, id_fix)
        response = {"status": True, "id_fix": id_fix}
        login = False
        try:
            sesionesFix[id_fix] = main(settings, target, id_fix, req_obj["user"]["password"], req_obj["cuenta"])
            sesionesFix[id_fix].daemon = True
            sesionesFix[id_fix].start()
            time.sleep(4)
            #ahora iniciar rest
            url_rest = "https://api.remarkets.primary.com.ar/"
            if int(req_obj["user"]["live"])==1: 
                url_rest = req_obj["user"]["url_rest"]
            sesionesFix[id_fix].application.rest = RofexAPI(user=id_fix, password=req_obj["user"]["password"], base_url=url_rest)

            while True: 
                if sesionesFix[id_fix].application.sessions[target]['connected']!=None:
                    print("la variable cambio de None ")
                    if sesionesFix[id_fix].application.sessions[target]['connected']==True:
                        print("la variable cambio a True")
                        sesionesFix[id_fix].application.server_md = server_md
                        log.info("sesion fix creada")
                        login = True
                        sesionesFix[id_fix].application.triangulos[0] = fixManual(sesionesFix[id_fix].application,id_fix, 0,req_obj["cuenta"], user_id)
                        sesionesFix[id_fix].application.triangulos[0].daemon = True
                        sesionesFix[id_fix].application.triangulos[0].start()
                        time.sleep(1)
                        break
                    else:
                        response = {"status": False, "id_fix": id_fix, "mgs": "datos incorrectos"}
                        sesionesFix[id_fix].application.logout()
                        sesionesFix[id_fix].initiator.stop()
                        del sesionesFix[id_fix]
                        break

        except Exception() as e: 
            log.warning(f"error al crear sesion fix: {e}")
            response = {"status": False, "id_fix": id_fix, "msg": e}
        if login==True:
            #actualizar el status de la sesion en la tabla fix_sessions
            #ahora vamos a iniciar el bot manual en la sesion de fix 
            await DbUtils.update_fix_session_mongo(req_obj["user"]["id"], 1)
            return jsonify(response)
        else:
            abort(make_response(jsonify(message="Datos de sesion incorrectos"), 401))

    async def detener_fix_new():
        from app import fixM
        req_obj = request.get_json()
        print(req_obj)
        id_fix = req_obj['user']["user"]
        id_user = req_obj['user']["id"]
        log.info(f"fixM: {fixM.tasks}")

        

        getFixTask = await fixM.get_fixTask_by_id_user(id_fix)
        if getFixTask:
            print("si existe a session")
            print("detener los bots abiertos ")
            bots = mongo.db.bots_ejecutandose.find({
                "user_fix": id_fix, "status": {"$gt": 0}
            })
            if bots: 
                print("si hay bots activos para este usuario")
                for bot in bots: 
                    await DbUtils.update_status_bot_ejecuntadose(str(bot["_id"]), 0)
                    #ahora cancelar las ordenes abiertas 
                    fix = {
                        "user": id_fix, 
                        "account": bot["cuenta"]
                    }
                    response =  await UtilsController.detener_bot_by_id(fix, bot["_id"])
            getFixTask.application.logout()
            getFixTask.initiator.stop()
            await getFixTask.stopColaFix()
            getFixTask.threadFix = None
            getFixTask.threadCola = None
            getFixTask.threadBalance = None
            await fixM.stop_task_by_id(id_fix)
            await DbUtils.update_fix_session_mongo(id_user, 0)
            log.info(f"fixM: {fixM.tasks}")
            return {"status": True}
        else:
            print("noexiste pero actualizadmos en db")
            await DbUtils.update_fix_session_mongo(id_user, 0)
            return {"status": False}
    
    def get_securitys():
        from app import fixM
        req_obj = request.get_json()
        print(req_obj)
        inicio = time.time()
        id_fix = req_obj['id_fix']
        if id_fix in fixM.main_tasks:
            #ahora necesito saber el tipo de cuenta si es demo o no 
            cuentaFix = mongo.db.cuentas_fix.find_one({"user": id_fix }, {"_id": 0})
            account_type = "demo"
            if cuentaFix["live"]==1: 
                account_type="live"
            today = date.today()
            securitys = mongo.db.securitys.find_one({"date": str(today), "account_type": account_type})
            if securitys:
                UtilsController.guardar_security_in_fix(securitys["data"], id_fix)
                response = {"securitys": str(securitys["data"]).replace("'", '"'), "date": str(datetime.now()), "status": True}
                return jsonify(response)
            fixM.main_tasks[id_fix].application.securityListRequest(symbol="")
            response = {"status": True}
            while True: 
                time.sleep(0.1)
            #   log.info(f"esperando seguridad {sesionesFix[id_fix].application.securitySegments}")
                if "DDA" in fixM.main_tasks[id_fix].application.securitySegments and "DDF" in fixM.main_tasks[id_fix].application.securitySegments and "MERV" in fixM.main_tasks[id_fix].application.securitySegments and "DUAL" in fixM.main_tasks[id_fix].application.securitySegments:
                    break
            time.sleep(1)
            securitys_data = UtilsController.fetch_securitys_data(id_fix)
            UtilsController.guardar_security_in_fix(securitys_data, id_fix)
            document = {
            "date": str(today),
            "account_type": account_type,
            "data": securitys_data
            }
            mongo.db.securitys.insert_one(document)
            response = {"securitys": str(securitys_data).replace("'", '"'), "date": str(datetime.now()), "status": True}

        else:
            response = {"status": False}
        return jsonify(response)