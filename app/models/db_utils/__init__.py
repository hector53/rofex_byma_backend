from app import mongo, datetime
from bson import ObjectId
import logging
log = logging.getLogger(__name__)

class DbUtils:
    @staticmethod

    def get_bot_activo(id):
        bot = mongo.db.bots_ejecutandose.find_one({
        "_id": ObjectId(id)
        })
        if bot:
            bot["_id"] = str(bot["_id"])
            log.info(f"existe el bot ejecutandose en la db ")
            return bot
        else:
            return False
    async def update_bot_ejecutandose(id_bot, status):
        result = mongo.db.bots_ejecutandose.update_one({'_id': ObjectId(id_bot)}, {'$set': {'status': status}})
        return True

    async def update_status_bot_ejecuntadose(id_bot, status):
        result = mongo.db.bots_ejecutandose.update_one({ "_id": ObjectId(id_bot)}, 
                                                    {'$set': {'status': status}})
        return True
    
    
    async def update_fix_session_mongo(id, status): 
        try: 
            filtro = {'_id': ObjectId(id)}
            nuevos_valores = {'$set': {"active": status}}
            resultado = mongo.db.cuentas_fix.update_one(filtro, nuevos_valores)
            #tambien vamos a actualizar todos los bots q se estan ejecutando 
            print(f"Documentos modificados: {resultado.modified_count}")
            return True 
        except Exception as e: 
            log.error(f"error update fix sesion mongo: {e}")
            return False
        
    def get_bot_ejecutandose( id_fix, id_bot, cuenta, symbols="", opciones=[], status="", type_bot=""):
        try: 
            bot = mongo.db.bots_ejecutandose.find_one({
                "user_fix": id_fix, 
                "id_bot": id_bot, 
                "cuenta": cuenta
            })
            if bot:
                bot["_id"] = str(bot["_id"])
                log.info(f"existe el bot ejecutandose en la db ")
                return bot
            else:
                log.info(f"no existe por lo tanto lo creo ")
                objetoAInsertar = {
                "user_fix": id_fix, 
                "cuenta": cuenta, 
                "id_bot": id_bot, 
                "symbols": symbols, 
                "opciones": opciones, 
                "type_bot": type_bot,
                "status": status
                }
                result = mongo.db.bots_ejecutandose.insert_one(objetoAInsertar)
                objetoAInsertar["_id"] = result.inserted_id
                return objetoAInsertar
        except Exception as e: 
            log.error(f"error en get_bot_ejecutandose: {e} ")
            return None
        

    def get_data_bb_intradia_hoy(id_bot): 
        array_dataBB = []
        try: 
            hoy = datetime.today()
            # Obtener la hora de inicio y fin del día de hoy
            hora_inicio = datetime(hoy.year, hoy.month, hoy.day, 0, 0, 0)
            hora_fin = datetime(hoy.year, hoy.month, hoy.day, 23, 59, 59)
            # Buscar documentos por fecha de hoy
            documentos_hoy = list(mongo.db.intradia.find({"id_bot": id_bot,
                                            "fecha": {"$gte": hora_inicio, "$lt": hora_fin}}))
            array_dataBB = [documento["dataBB"] for documento in documentos_hoy]
        except Exception as e: 
            log.error(f"error filtrando data intradia hoy: {e}")
        return array_dataBB