from app import jsonify, request
from app import  jwt_required,get_jwt_identity
from app import ObjectId, mongo, logging
from app.models import AccountModel
log = logging.getLogger(__name__)
class CuentasFixController:
    @staticmethod
    @jwt_required()
    def index():
        user = get_jwt_identity()
        cuentas = AccountModel.get_all(user["username"])
        return jsonify(cuentas)
    
    @jwt_required()
    def insert():
        user = get_jwt_identity()
        body = request.get_json()
        try: 
            body["username"]= user["username"]
            body["active"]=0
            body["selected"]=False
            print("add_cuenta_fix ", body)
            resultado = mongo.db.cuentas_fix.insert_one(body)
            print(f"Insertado usuario con ID: {resultado.inserted_id}")
            response = {
            "status": "success",
            "message": "Cuenta FIX agregada exitosamente", 
            "id": str(resultado.inserted_id)
                }
        except Exception as e: 
            response = {
            "status": "error",
            "message": f"error: {e}", 
                }
        return jsonify(response)

    @jwt_required()
    def delete(id):
        print("delete cuenta fix", id)
        id_cuenta = id
        try: 
            filtro = {'_id': ObjectId(id_cuenta)}
            resultado = mongo.db.cuentas_fix.delete_one(filtro)
            print(f"Documentos eliminados: {resultado.deleted_count}")
            response = {
                 "status": "success",
                "message": "Cuenta FIX eliminada exitosamente"
            }   
        except Exception as e: 
            response = {
                "status": "error", 
                "message": f"algo paso al eliminar: {e}"
            }
        return jsonify(response)

    @jwt_required()
    def update():
        body = request.get_json()
        try:
            id_cuenta = body["id"]
            filtro = {'_id': ObjectId(id_cuenta)}
            del body["id"]
            nuevos_valores = {'$set': body}
            resultado = mongo.db.cuentas_fix.update_one(filtro, nuevos_valores)
            print(f"Documentos modificados: {resultado.modified_count}")
            response = {
            "status": "success",
            "message": "Cuenta FIX editada exitosamente"
            }
        except Exception as e: 
            response = {
                "status": "error", 
                "message": f"error al actualizar: {e}"
            }
        return jsonify(response)
    
    @jwt_required()
    def select_cuenta():
        body = request.get_json()
        try: 
            id_user = body["id_user"]
            cuentaVieja = body["cuentaVieja"]
            cuentaNueva = body["cuentaNueva"]
            if cuentaVieja!=None: 
                filtro = {'_id': ObjectId(id_user), "cuentas.cuenta": cuentaVieja}
                nuevos_valores = {'$set': {"cuentas.$.active": 0}}
                resultado = mongo.db.cuentas_fix.update_one(filtro, nuevos_valores)
                print(f"Documentos modificados: {resultado.modified_count}")
            filtro = {'_id': ObjectId(id_user), "cuentas.cuenta": cuentaNueva}
            nuevos_valores = {'$set': {"cuentas.$.active": 1}}
            resultado = mongo.db.cuentas_fix.update_one(filtro, nuevos_valores)
            print(f"Documentos modificados: {resultado.modified_count}")
            response = {
                    "status": "success",
                    "message": "Cuenta FIX editada exitosamente"
            }
        except Exception as e: 
            response = {
                    "status": "error",
                    "message": f"error: {e}"
            }
        return jsonify(response)
    
    @jwt_required()
    def userFix_select():
        body = request.get_json()
        try: 
            id_nueva = body["id"]
            id_vieja = body["id_vieja"]
            if id_vieja!=None:
                filtro = {'_id': ObjectId(id_vieja)}
                nuevos_valores = {'$set': {"selected": False}}
                resultado = mongo.db.cuentas_fix.update_one(filtro, nuevos_valores)
                print(f"Documentos modificados: {resultado.modified_count}")
            filtro = {'_id': ObjectId(id_nueva)}
            nuevos_valores = {'$set': {"selected": True}}
            resultado = mongo.db.cuentas_fix.update_one(filtro, nuevos_valores)
            print(f"Documentos modificados: {resultado.modified_count}")
            response = {
            "status": "success",
            "message": "Cuenta FIX editada exitosamente"
            }
        except Exception as e: 
            response = {
            "status": "error",
            "message": f"error: {e}"
            }
        return jsonify(response)
     


 