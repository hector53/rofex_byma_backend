from app import mongo
from bson import json_util

class BotsModel:
    @staticmethod
    def get_all(id_user, fix):
        user_fix = fix["user"]
        cuenta = fix["account"]
        arrayBots=[]
        try:
            print("consultando ")
            count = mongo.db.bots.count_documents({})
            print("len bots", count)
            if count>0:
                bots = mongo.db.bots.find({"id_user": id_user})
                for doc in bots:
                    doc['_id'] = str(doc['_id'])
                    #ahora quiero el listado no, el status del bot que debe estar ejecutandose siempre y cuando haya uno
                    ejecutandose = mongo.db.bots_ejecutandose.find_one({"id_bot": doc['_id'], 
                                                                        "user_fix": user_fix, 
                                                                        "cuenta":cuenta
                                                                        })
                    if ejecutandose: 
                        print("si tiene documentos ")
                        doc["status"] = ejecutandose["status"]
                        doc["id_ejecutandose"] = str(ejecutandose["_id"])
                    else: 
                        doc['status'] = 0
                    arrayBots.append(doc)
                response = {"arrayBots": arrayBots, "status": True}
            else:
                response = {"arrayBots": arrayBots, "status": False}
        except Exception as e: 
            print("error ", e)
            response = {"arrayBots": arrayBots, "status": False, "msg": e}
        return response
    
    

