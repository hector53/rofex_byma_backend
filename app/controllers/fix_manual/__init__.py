from app import mongo, sesionesFix, ObjectId, logging, datetime, jsonify, request, asyncio, abort, make_response

log = logging.getLogger(__name__)

class FixManualController:
    @staticmethod

    def get_fix_manual_data(id):
        id_fix = id
        response = {
            "status": False,
            "msg": "fix no activo",
            "isFixManualActive": False,
            "ordenes": [],
        }
        if id_fix in sesionesFix:
            #ver si bot manual esta activo 
            isFixManualActive = False 
            if 0 in sesionesFix[id_fix].application.triangulos:
                isFixManualActive = True
            #buscar todas las ordenes de fix manual
            arrayOrdenes = []
            fecha_hoy = datetime.today().date()
            fecha_formateada = fecha_hoy.strftime("%Y-%m-%d")
            #arrayOrdenes = get_ordenes_bot_manual(0, fecha_formateada)
            response = {
                "status": True,
                "msg": "fix activo",
                "isFixManualActive": isFixManualActive,
                "ordenes": arrayOrdenes
            }
        return jsonify(response)

    def new_order_manual():
        req_obj = request.get_json()
        print(req_obj)
        id_fix = req_obj['id_fix']
        order = req_obj['order']
        if 0 in sesionesFix[id_fix].application.triangulos:
            clientR = sesionesFix[id_fix].application.triangulos[0].clientR
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(clientR.nueva_orden_manual(order["symbol"], order["side"], order["size"], order["price"], order["type"]))
            loop.close()
            return response
        else:
            abort(make_response(jsonify(message="manual no activo"), 401))

    def manual_edit_order():
        req_obj = request.get_json()
        print(req_obj)
        id_fix = req_obj['id_fix']
        typeRequest = int(req_obj['typeRequest'])
        orden = req_obj['orden']
        if 0 in sesionesFix[id_fix].application.triangulos:
            sideOrder = 1 if orden["side"] == "Buy" else 2
            clientR = sesionesFix[id_fix].application.triangulos[0].clientR
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            if typeRequest == 1:
                response = loop.run_until_complete(clientR.modificar_orden_manual(orderId=orden["orderId"],
                        origClOrdId=orden["clOrdId"], side=sideOrder, orderType=2, symbol=orden["symbol"],
                        quantity=orden["size"], price=orden["price"], sizeViejo=orden["sizeViejo"]))
            elif typeRequest == 2:
                response = loop.run_until_complete(clientR.modificar_orden_manual_2(orderId=orden["orderId"],
                        origClOrdId=orden["clOrdId"], side=sideOrder, orderType=2, symbol=orden["symbol"],
                        quantity=orden["size"], price=orden["price"]))
            loop.close()
            return response
        else:
            abort(make_response(jsonify(message="manual no activo"), 401))

    def manual_cancel_orden():
        req_obj = request.get_json()
        print(req_obj)
        id_fix = req_obj['id_fix']
        orden = req_obj['orden']
        if 0 in sesionesFix[id_fix].application.triangulos:
            sideOrder = 1 if orden["side"] == "Buy" else 2
            clientR = sesionesFix[id_fix].application.triangulos[0].clientR
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(clientR.cancelar_orden_manual(orden["orderId"], orden["clOrdId"], sideOrder, orden["leavesQty"], orden["symbol"]))
            loop.close()
            return response
        else:
            abort(make_response(jsonify(message="manual no activo"), 401))

    async def manua_mass_cancel():
        from app import fixM
        req_obj = request.get_json()
        print(req_obj)
        id_fix = req_obj['id_fix']
        marketSegment = req_obj['marketSegment']
        await fixM.main_tasks[id_fix].application.orderMassCancelRequest(marketSegment=marketSegment)
        return jsonify({"status":True})

    def manua_get_posiciones(id):
        id_fix = id
        cuenta = request.args.get('cuenta', '')
        if 0 in sesionesFix[id_fix].application.triangulos:
            clientR = sesionesFix[id_fix].application.triangulos[0].clientR
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(clientR.get_posiciones(cuenta))
            loop.close()
            return jsonify(response)
        else:
            abort(make_response(jsonify(message="manual no activo"), 401))

    def manua_get_balance(id):
        id_fix = id
        print("request", request)
        cuenta = request.args.get('cuenta', '')
        print("uenta", cuenta)
        if 0 in sesionesFix[id_fix].application.triangulos:
            clientR = sesionesFix[id_fix].application.triangulos[0].clientR
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(clientR.get_balance(account=cuenta))
            loop.close()
            return jsonify(response)
        else:
            abort(make_response(jsonify(message="manual no activo"), 401))

    def manua_mass_status(id):
        id_fix = id
        cuenta = request.args.get('cuenta', '')
        if 0 in sesionesFix[id_fix].application.triangulos:
            clientR = sesionesFix[id_fix].application.triangulos[0].clientR
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(clientR.mass_status_request("1", 7, cuenta))
            loop.close()
            return response
        else:
            abort(make_response(jsonify(message="manual no activo"), 401))

    def manual_get_trades():
        req_obj = request.get_json()
        print(req_obj)
        id_fix = req_obj['id_fix']
        market_id = req_obj['market_id']
        symbol = req_obj['symbol']
        desde = req_obj['desde']
        hasta = req_obj['hasta']
        if 0 in sesionesFix[id_fix].application.triangulos:
            clientR = sesionesFix[id_fix].application.triangulos[0].clientR
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(clientR.get_trades_manual(market_id, symbol, desde, hasta))
            loop.close()
            return jsonify(response)
        else:
            abort(make_response(jsonify(message="manual no activo"), 401))
