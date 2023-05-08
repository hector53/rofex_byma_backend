from app import logging
from app.controllers.utils import UtilsController
from app.clases.calculadoraBonos import CalculadoraFinanciera
from app import datetime, jsonify
import re
log = logging.getLogger(__name__)
class BonosController:
    @staticmethod
    def get_bonos():
        precios = UtilsController.get_precios_bonos()
        calculadora = CalculadoraFinanciera()
        arrayData = []
        for x in precios:
            year = "20"+re.sub(r'\D', '', x)
            calculadora.year = year
            calculadora.simboloP = precios[x]["precioP"]
            calculadora.simboloD = precios[x]["precioD"]
            fecha1_obj = datetime.strptime(str(datetime.strptime( calculadora.proxima_fecha(), "%Y-%m-%d %H:%M:%S").date()), '%Y-%m-%d')
            fecha2_obj = datetime.strptime(str(calculadora.fecha_hoy()), '%Y-%m-%d')
            print("fecha1 ", fecha1_obj)
            print("fecha2 ", fecha2_obj)
            diferencia = fecha1_obj - fecha2_obj
            indice = "AL"
            if "GD" in x:
                indice = "LNY"
            objeto = {
                "symbol": x,
                "data": {
                    "indice": indice,
                    "precio": calculadora.simboloP,
                    "porcentaje": 0,
                    "tir": calculadora.tir(),
                    "md": calculadora.mod_duration(),
                    "vol": 0,
                    "paridad": calculadora.paridad(),
                    "vt": calculadora.valor_tecnico(),
                    "dq":str(diferencia.days)  ,
                    "pq": 0,
                    "qp": 0
                }
            }
            arrayData.append(objeto)
        return jsonify({
            "status": "success",
            "data": arrayData
        })