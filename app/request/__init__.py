from app import app

#controllers 
from app.controllers import *

#rutas con controladores 

###FIX###
app.add_url_rule('/api/iniciar_fix/new', view_func=FixController.iniciar_fix_new, methods=['POST'] )
app.add_url_rule('/api/detener_fix/new', view_func=FixController.detener_fix_new, methods=['POST'] )
app.add_url_rule('/api/get_securitys', view_func=FixController.get_securitys, methods=['POST'] )
app.add_url_rule('/api/new_order_manual', view_func=FixController.newOrderTest, methods=['POST'] )
app.add_url_rule('/api/initC', view_func=FixController.initC, methods=['POST'] )
app.add_url_rule('/api/stopC', view_func=FixController.stopC, methods=['POST'] ) 
####BOTS####
app.add_url_rule('/api/get_bots/<string:user_id>/<string:fix>', view_func=BotsController.show_all )
app.add_url_rule('/api/startBot', view_func=BotsController.start_bot_new, methods=['POST'] )
app.add_url_rule('/api/detenerBot', view_func=BotsController.detener_bot, methods=['POST'] )
app.add_url_rule('/api/add_bot', view_func=BotsController.add_bot, methods=['POST'] )
app.add_url_rule('/api/editBot', view_func=BotsController.edit_bot, methods=['POST'] )
app.add_url_rule('/api/deleteBot', view_func=BotsController.deleteBot, methods=['POST'] )
app.add_url_rule('/api/bot_data_charts/<string:id>', view_func=BotsController.bot_data_charts, methods=['POST'] )

####CUENTAS FIX####
app.add_url_rule('/api/cuentas_fix', view_func=CuentasFixController.index)
app.add_url_rule('/api/cuenta_fix', view_func=CuentasFixController.insert,   methods=['POST'])
app.add_url_rule('/api/cuentas_fix/<string:id>', view_func=CuentasFixController.delete, methods=['DELETE'])
app.add_url_rule('/api/cuentas_fix', view_func=CuentasFixController.update,  methods=['PUT'])
app.add_url_rule('/api/cuenta_fix/select', view_func=CuentasFixController.select_cuenta,   methods=['POST'])
app.add_url_rule('/api/user_fix/select', view_func=CuentasFixController.userFix_select,   methods=['POST'])

###user####
app.add_url_rule('/api/checkToken', view_func=UserController.checkToken,   methods=['POST'])
app.add_url_rule('/api/logout', view_func=UserController.logout,   methods=['POST'])
app.add_url_rule('/api/login', view_func=UserController.login,   methods=['POST'])

###BONOS####
app.add_url_rule('/api/get_data_bonos', view_func=BonosController.get_bonos,   methods=['GET'])

###FIX MANUAL####
app.add_url_rule('/api/manual/<string:id>', view_func=FixManualController.get_fix_manual_data,   methods=['GET'])
app.add_url_rule('/api/manual/new_order', view_func=FixManualController.new_order_manual,   methods=['POST'])
app.add_url_rule('/api/manual/edit_order', view_func=FixManualController.manual_edit_order,   methods=['POST'])
app.add_url_rule('/api/manual/cancel_orden', view_func=FixManualController.manual_cancel_orden,   methods=['POST'])
app.add_url_rule('/api/manual/mass_cancel', view_func=FixManualController.manua_mass_cancel,   methods=['POST'])
app.add_url_rule('/api/manual/get_posiciones/<string:id>', view_func=FixManualController.manua_get_posiciones,   methods=['GET'])
app.add_url_rule('/api/manual/get_balance/<string:id>', view_func=FixManualController.manua_get_balance,   methods=['GET'])
app.add_url_rule('/api/manual/mass_status/<string:id>', view_func=FixManualController.manua_mass_status,   methods=['GET'])
app.add_url_rule('/api/manual/get_trades', view_func=FixManualController.manual_get_trades,   methods=['POST'])