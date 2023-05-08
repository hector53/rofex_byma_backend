from app import mongo
from bson import json_util

class AccountModel:
    @staticmethod
    def get_all(username):
        cuentas_cursor = mongo.db.cuentas_fix.find({'username': username})
        cuentas_json = json_util.dumps(list(cuentas_cursor))
        cuentas = json_util.loads(cuentas_json)
        for cuenta in cuentas:
            cuenta['id'] = str(cuenta['_id'])
            del cuenta['_id']
        response = {
        "status": "success", 
        "cuentas": cuentas
        }
      #  print("response controler", response)
        return response

