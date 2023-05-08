
@app.route('/api/delete_bot_from_grupo', methods=['POST'])
def delete_bot_from_grupo():
    req_obj = request.get_json()
    id_bot = req_obj['id_bot']
    id_grupo = req_obj['id_grupo']
    sql = f"""
    DELETE FROM `grupos_bots` WHERE id_bot = %s and id_grupo = %s
    """
    tupla = (id_bot, id_grupo)
    updateData(sql, tupla)
    return jsonify({"status": True})

@app.route('/api/add_bot_to_grupo', methods=['POST'])
def add_bot_to_grupo():
    req_obj = request.get_json()
    id_bot = req_obj['id_bot']
    id_grupo = req_obj['id_grupo']
    sql = f"""
    INSERT INTO grupos_bots (id_bot, id_grupo, created) VALUES (%s, %s, %s)
    """
    tupla = (id_bot, id_grupo, datetime.now())
    insert_data(sql, tupla)
    return jsonify({"status": True})


@app.route('/api/get_ordenes_bot_by_id/<id>', methods=['GET'])
def get_ordenes_bot_by_id(id):
    sql = f"""
    SELECT * FROM bots where id = %s
    """
    tupla = (id)
    x = getDataOne(sql, tupla)
    arrayBot = []
    if x: 
        typeBot = x[1]
        status = x[3]
        #tambien necesito las ordenes activas de este bot
        sql = f"""
        SELECT * FROM ordenes where type_order=%s and id_bot=%s
        """
        tupla = (0, id)
        arrayOrdenes = []
        ordenes = getData(sql, tupla)
        for y in ordenes:
            objOrden = {
            "id": y[0],
            "symbol": y[4],
            "side": y[5], 
            "size": y[10], 
            "price": y[8]
            }
            arrayOrdenes.append(objOrden)
        objBot = {
        "id": id,
        "type": typeBot,
        "status": status,
        "ordenes": arrayOrdenes
        }
        arrayBot.append(objBot)
    return jsonify(arrayBot)

@app.route('/api/get_bots_list_by_grupo/<id>', methods=['GET'])
def get_bots_list_by_grupo(id):
    sql = f"""
    SELECT * FROM bots WHERE id NOT IN ( SELECT id_bot FROM grupos_bots where id_grupo = %s );
    """
    tupla = (id)
    bots = getData(sql, tupla)
    arrayBots = []
    for x in bots:
        typeBot = "Triangulo"
        if x[1]==1:
            typeBot = "CI-48"
        id_bot = x[0]
        objBot = {
        "id": id_bot,
        "type": typeBot,
        "symbols": x[2]
        }
        arrayBots.append(objBot)
    return jsonify(arrayBots)



@app.route('/api/getEvents', methods=['GET'])
def getEvents():
    #traer datos de la tabla events
    """
    tabla events
    `id` INT AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(255) NOT NULL,
  `start` DATETIME NOT NULL,
  `end` DATETIME,
  `all_day` BOOLEAN NOT NULL,
  `color` VARCHAR(50) NOT NULL DEFAULT 'info',
  `tipo` VARCHAR(255),
  `simbolo` VARCHAR(255),
  `dato` FLOAT
    """
    sql = f"""
    SELECT * FROM events
    """
    arrayEvents = []
    events = getData(sql, None)
    for y in events:
        objEvent = {
        "id": y[0],
        "title": y[1],
        "start": str(y[2]),
        "end": str(y[3]),
        "all_day": y[4],
        "color": y[5],
        "tipo": y[6],
        "simbolo": y[7],
        "dato": y[8]
        }
        arrayEvents.append(objEvent)
    response = {
        "success": True, 
        "events": arrayEvents
    }
    return jsonify(response)


@app.route('/api/saveEvent', methods=['POST'])
def saveEvent():
    req_obj = request.get_json()
    #debo insertar en la tabla events un nuevo registro, de la variable req_obj me vienen todos los campos 
    #para insertar en la tabla events
    sql = f"""
    INSERT INTO events ( title, start, end, all_day,  tipo, simbolo, dato) 
    VALUES
    (%s, %s, %s, %s, %s, %s, %s)
    """
    tupla = (req_obj["title"], req_obj["start"], req_obj["end"], req_obj["allDay"],  req_obj["tipo"], req_obj["simbolo"], req_obj["dato"])
    inserEvent = insert_data(sql, tupla)
    response = {
        "success": True
    }
    return jsonify(response)

    


@app.route('/api/estadistica_bcra/<endpoint>', methods=['GET'])
def estadistica_bcra(endpoint):
    app.logger.info(f"get estadistica_bcra: {endpoint}")
    sql = f"""
    SELECT * from estadistica_bcra where endpoint = %s
    """
    tupla = (endpoint)
    data = getData(sql, tupla)
    arrayData = []
    if data: 
        for x in data: 
            fecha = datetime.strptime(str(x[0]), '%Y-%m-%d %H:%M:%S')
            fecha_formateada = fecha.strftime('%Y-%m-%d')
            arrayData.append({
                "d": fecha_formateada, 
                "v": float(x[1])
            })
    return jsonify(arrayData)


@app.route('/api/get_bots_by_grupo/<id>', methods=['GET'])
def get_bots_by_grupo(id):
    app.logger.info("get_bots_by_grupo")
    sql = f"""
    SELECT t1.id_bot, t1.id_grupo, t2.status, t2.type, t2.symbols FROM grupos_bots as t1
    INNER JOIN bots as t2 ON t1.id_bot=t2.id where id_grupo = %s;
    """
    tupla = (id)
    bots = getData(sql, tupla)
    arrayBots = []
    for x in bots:
        id_bot = x[0]
        typeBot = x[3]
        status = x[2]
        symbols = x[4]
        #tambien necesito las ordenes activas de este bot 
        sql = f"""
        SELECT * FROM ordenes where type_order=%s and id_bot=%s
        """
        tupla = (0, id_bot)
        arrayOrdenes = []
        ordenes = getData(sql, tupla)
        for y in ordenes:
            objOrden = {
            "id": y[0],
            "symbol": y[4],
            "side": y[5], 
            "size": y[10], 
            "price": y[8]
            }
            arrayOrdenes.append(objOrden)
        objBot = {
        "id": id_bot,
        "type": typeBot,
        "status": status,
        "ordenes": arrayOrdenes, 
        "symbols": json.loads(str(symbols).replace("'", '"'))
        }
        arrayBots.append(objBot)
    return jsonify(arrayBots)


@app.route('/api/get_grupos', methods=['GET'])
def get_grupos():
    app.logger.info("get_grupos")
    sql = f"""
    SELECT * FROM grupos where id_user = %s
    """
    tupla = (1)
    grupos = getData(sql, tupla)
    arrayGrupos = []
    for x in grupos:
        objGrupo = {
        "id": x[0],
        "name": x[1],
        }
        arrayGrupos.append(objGrupo)
    response = {"status": True, "grupos": arrayGrupos}
    return jsonify(response)














@app.route('/api/escuchar_mercados', methods=['POST'])
def escuchar_mercados():
    req_obj = request.get_json()
    log.info(f"req_obj: {req_obj}")
    id_fix = req_obj["id_fix"]
    response = {"status": False}
    if id_fix in sesionesFix:
        #verificar si hay bots activos en db 
        sql = f"""
        SELECT * FROM bots WHERE id_user = %s AND status = 0 
        """
        tupla = (1)
        bots = getData(sql, tupla)
        if bots: 
            for x in bots: 
                if x[0] not in sesionesFix[id_fix].application.triangulos:
                    #no existe el bot en la session
                    symbols = json.loads(str(x[2]).replace("'", '"'))
                    type_bot = x[1]
                    print("symbols", symbols)
                    opciones = {}
                    if x[6] is not None:
                        opciones =  json.loads(str(x[6]).replace("'", '"'))
                    if type_bot == 0:#triangulo
                        response = iniciar_bot_triangulo(id_fix, x[0], symbols, opciones, True)
                    if type_bot == 1:#CI-48
                        response = iniciar_bot_ci_48(id_fix, x[0], symbols, opciones, True)
                    if type_bot == 2:#CI-CI
                        response = iniciar_bot_ci_ci(id_fix, x[0], symbols, opciones, True)
                else:
                    #ya existe el bot en la session
                    log.info(f"ya existe el bot en la session: {x[0]}")
        else:
            response = {"status": True, "msg": "no hay bots inactivos"}
    else:
        response = {"status": False, "msg": "no existe la session"}
    return jsonify(response)

def get_bot_by_id(id_bot):
    try:
        bot = mongo.db.bots.find_one({'_id': ObjectId(id_bot)})
        if bot:
            bot['_id'] = str(bot['_id'])
        return bot
    except Exception as e: 
        abort(make_response(jsonify(message=f"error listando bot: {id_bot}"), 401))





@app.route('/api/delete_grupo/<id>', methods=['POST'])
def delete_grupo(id):
    req_obj = request.get_json()
    sql = f"""
    DELETE FROM grupos WHERE id=%s 
    """
    tupla = (id)
    deleteGrupo = updateData(sql, tupla)
    return {"status": True}





@app.route('/api/add_grupo', methods=['POST'])
def add_grupo():
    req_obj = request.get_json()
    print(req_obj)
    sql = f"""
    INSERT INTO grupos ( name, id_user, created) 
    VALUES
    ( %s, %s, %s)
    """
    tupla = (req_obj["name"], 1, datetime.now())
    idGrupo = insert_data(sql, tupla)
    if idGrupo["status"] == 0:
        log.info(f"no se guardo idBot {idGrupo}")
        return {"status": False}
    else: 
        log.info(f"se guardo idBot {idGrupo}")
    return {"status": True, "id": idGrupo["id"] }

