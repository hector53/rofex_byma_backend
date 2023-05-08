'''
simboloP: precio del activo en pesos. Lo traigo por una API.
simboloD: Precio del activo en dolares. Lo traigo por una API. 
simboloP / Dolar Mep = simboloP / (simboloP / simboloD)
Hoy = funcion para saber que dia es hoy
Fecha Emisión = valor fijo 
Fecha Vencimiento = valor fijo
Cupon Actual = json[0][1][1]
Ultima Fecha Pago = input de valor fijo
XIRR = TIR.NO.PER( Recorrido del json[0][0][bucle valor];json[0][0][bucle keys fecha])
TIR = XIRR
TNA (YTM) = TASA.NOMINAL(TIR;2)
Precio Clean = Precio Dirty - Intereses Corridos
Intereses Corridos = 100 * Cupon Actual*dias360(Ultima fecha pago;Hoy)/360
Precio Dirty = json[0][0][0] * factorDescuento
Valor Tecnico = 100 + Intereses corridos
Paridad = 'simboloP / Dolar Mep' / Valor Tecnico
Duration = durationVariable
Mod. Duration = duration / (1+TIR/2)
Yield = Cupon Actual
'''

import datetime
import json
from scipy.optimize import newton
import os
from pyxirr import xirr as pxirr
import re
class CalculadoraFinanciera:
    def __init__(self,  ultima_fecha_pago='2023-01-09'):
        self.year = "2029"
        self.simboloP = 9077 # extraer Precio del activo en pesos. Lo traigo por una API.
        self.simboloD = 20.96 # extraer Precio del activo en dolares. Lo traigo por una API.
        self.ultima_fecha_pago = ultima_fecha_pago
        self.json_data = self.leer_json('bonos.json')
        self.cupon_actual = self.get_cupon_actual()


    def get_cupon_actual(self, fondo="Intereses Anuales"):
        return self.json_data[self.year][fondo][self.proxima_fecha()]

    def leer_json(self, nombre_archivo):
        ruta_archivo = os.path.join(os.getcwd(), nombre_archivo)
        with open(ruta_archivo) as archivo:
            json_data = json.load(archivo)
        return json_data

    # Inicio funciones base

    def fecha_hoy(self):
        return datetime.date.today()
    
    def restaFechas(self, fecha1, fecha2):
        return (fecha1.year - fecha2.year) * 360 + (fecha1.month - fecha2.month) * 30 + (fecha1.day - fecha2.day)
    
    def proxima_fecha(self):
        hoy = self.fecha_hoy()
      #  fechas = self.extraer_fechas_json("2029", "Fondo VN 100")
        fechas = [datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date() for date in self.json_data["2029"]["Fondo VN 100"].keys()]

        siguiente_fecha = None
        siguiente_indice = None
        for i, fecha in enumerate(fechas):
           # fechaSinHora = datetime.datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S').date()
            if hoy < fecha:
             #   print("hoy es menor q fechasinhora")
                if siguiente_fecha is None or fecha < siguiente_fecha:
                    siguiente_fecha = fecha
                    siguiente_indice = i

        return str(siguiente_fecha.strftime('%Y-%m-%d %H:%M:%S'))

    
    #Fin funciones base

    # Inicio funciones de calculo para JSON
    def factor_descuento(self):
        hoy = self.fecha_hoy()
        tir = self.tir()
        fechas = [datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date() for date in self.json_data["2029"]["Fondo VN 100"].keys()]

        resultado = []
        for fecha in fechas:
            dias = self.restaFechas(hoy, fecha)
            factor = 1 / (1 + tir) ** ((-1)*dias / 360)
            resultado.append(factor)

        return resultado
    
    def valor_actual(self):
        factores_descuento = self.factor_descuento()
        valores = [self.json_data["2029"]["Fondo VN 100"][key] for key in self.json_data["2029"]["Fondo VN 100"].keys()]

        resultado = []
        for valor, factor in zip(valores, factores_descuento):
            valor_actual = valor * factor
            resultado.append(valor_actual)

        return resultado

    def capital_acum(self):
        valores = [self.json_data["2029"]["Intereses En Pago"][key] for key in self.json_data["2029"]["Intereses En Pago"].keys()]
        capital_acumulado = [100]

        for valor in valores:
            capital_acumulado.append(capital_acumulado[-1] - valor * 100)

        return capital_acumulado[1:]
    
    def day_count(self):
        hoy = self.fecha_hoy()
        fechas = [datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date() for date in self.json_data["2029"]["Fondo VN 100"].keys()]

        resultado = []
        for fecha in fechas:
            dias_divididos = (-1) * self.restaFechas(hoy, fecha) / 360
            resultado.append(dias_divididos)

        return resultado

    def day_xva(self):
        day_counts = self.day_count()
        valores_actuales = self.valor_actual()

        resultado = []
        for count, valor in zip(day_counts, valores_actuales):
            xva = count * valor
            resultado.append(xva)

        return resultado

    # Fin funciones de calculo para JSON

    # Inicio funciones de calculo
    def simboloP_dolar_mep(self):
        return (self.simboloP / (self.simboloP / self.simboloD))

    def intereses_corridos(self):
        ultima_fecha_pago_date = datetime.datetime.strptime(self.ultima_fecha_pago, "%Y-%m-%d").date()
        dias = self.restaFechas(self.fecha_hoy(), ultima_fecha_pago_date)
        return 100 * self.cupon_actual * dias / 360

    def precio_dirty(self):
        valores = self.valor_actual()
        return sum(valores)

    def precio_clean(self):
        return self.precio_dirty() - self.intereses_corridos()

    def valor_tecnico(self):
        return 100 + self.intereses_corridos()

    def paridad(self):
        return self.simboloP_dolar_mep() / self.valor_tecnico()

    def xirr(self):
        # Obtener las fechas y flujos de fondos de self.json_data
        fechas = [datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date() for date in self.json_data["2029"]["Fondo VN 100"].keys()]
        flujos_de_fondos = list(self.json_data["2029"]["Fondo VN 100"].values())

        # Calcular el valor negativo a partir de simboloP_dolar_mep()
        valor_negativo = -self.simboloP_dolar_mep()

        # Insertar el valor negativo al principio del array de flujos de fondos
        flujos_de_fondos.insert(0, valor_negativo)

        # Agregar la fecha actual al principio de la lista de fechas
        fecha_actual = datetime.date.today()
        fechas.insert(0, fecha_actual)

        # Calcular el XIRR
        xirr_value = pxirr(fechas, flujos_de_fondos)

        return xirr_value


    def tir(self):
        return self.xirr()

    def tna(self, num_periodos):
        xirr = self.xirr()
        nar = ((1 + xirr) ** (1 / num_periodos)) - 1
        return nar * num_periodos

    def duration(self):
        day_xva = sum(self.day_xva())
        return day_xva / self.precio_dirty()

    def mod_duration(self):
        return self.duration() / (1 + self.tir() / 2)

    def yield_rate(self):
        return self.cupon_actual


