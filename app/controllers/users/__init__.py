from app import jsonify, request, abort, make_response
from app import  jwt_required,get_jwt_identity, unset_jwt_cookies, create_access_token
from app import  mongo, logging
log = logging.getLogger(__name__)
class UserController:
    @staticmethod

    @jwt_required()
    def checkToken():
        print("checktoken ")
        user = get_jwt_identity()
        print("user", user)
        return jsonify({
            "status": "success",
            "user": user
        })
    
    @jwt_required()
    def logout():
        body = request.get_json()
        print("logout ")
        token = get_jwt_identity()
        # Eliminar las cookies de JWT para remover el token del cliente
        response = jsonify({'message': 'Logout exitoso', 'status': "success"})
        unset_jwt_cookies(response)
        return response, 200
    
    def login():
        body = request.get_json()
        print(body)
        try: 
            username = body["username"]
            password = body["password"]
            user = mongo.db.users.find_one({'username': username, 'password': password})
            user["_id"] = str(user["_id"])
            if user:
                print("user", user)
            # El usuario existe
                print('El usuario existe')  
                access_token = create_access_token(identity=user)
                response = {
                    'status': True,
                    'message': 'Login successful',
                    'token': access_token,
                }
                return jsonify(response)
            else:
            # El usuario no existe
                abort(make_response(jsonify(message="el usuario no existe"), 401))
        except Exception as e: 
            log.error(f"error en login: {e}")
            abort(make_response(jsonify(message=f"error: {e}"), 401))