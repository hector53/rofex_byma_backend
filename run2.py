import pymongo
from datetime import datetime
# Conecta a la base de datos de MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")

# Selecciona la base de datos y la colección
db = client["rofex"]
collection = db["ordenes"]
"""
buscar = collection.find_one({
       "clOrdId": "arxegffk", 
                "orderId": "1683648646948724", 
                "id_bot": "645a440f1ecdb05059e15fb4", 
                "cuenta": "REM7659", 
                "active": True
})

print("buscar", buscar)
"""


editar = collection.update_one({
                "clOrdId": "arxegffk", 
                "orderId": "1683648646948724", 
                "id_bot": "645a440f1ecdb05059e15fb4", 
                "cuenta": "REM7659",
                "active": True
            }, {'$set': {'active': False }})

print("editar", editar)
