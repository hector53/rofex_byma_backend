import pymongo
from datetime import datetime
# Conecta a la base de datos de MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")

# Selecciona la base de datos y la colección
db = client["rofex"]
collection = db["ordenes"]

editar = collection.update_one({
                "clOrdId": "uyajesqs", 
                "orderId": "1683291400765572", 
                "id_bot": "6452c6113604978abd67aee6", 
                "cuenta": "REM7659"
            }, {'$set': {'active': False }})

print("editar", editar)