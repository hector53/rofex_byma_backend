# -*- coding: utf-8 -*-
"""
Created on Tue Mar 28 15:55:11 2023

@author: Hector
"""

import requests
import logging
from datetime import datetime, timedelta
class RofexAPI:
    def __init__(self, user, password, base_url="https://api.remarkets.primary.com.ar/"):
        self.user = user
        self.password = password
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.token_expiration = None
        self.log = logging.getLogger(f"api_primary")

    def _authenticate(self):
        auth_url = f"{self.base_url}/auth/getToken"
        headers = {"X-Username": self.user, "X-Password": self.password}
        response = requests.post(auth_url, headers=headers)

        if response.status_code == 200:
            self.log.info(f"response: {response.headers}", )
            self.token = response.headers["x-auth-token"]
            # Establece la fecha y hora de expiración del token en 24 horas
            self.token_expiration = datetime.now() + timedelta(hours=24)
        else:
            raise Exception("Error de autenticación")

    def _is_token_expired(self):
        if self.token_expiration:
            return datetime.now() >= self.token_expiration
        return True

    def _get_headers(self):
        if not self.token or self._is_token_expired():
            self._authenticate()
        return {"x-auth-token": self.token}

    def get_balance(self, account):
        headers = self._get_headers()
        balance_url = f"{self.base_url}/rest/risk/accountReport/{account}"
        response = requests.get(balance_url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception("Error al obtener el balance")

    def get_positions(self, account):
        headers = self._get_headers()
        positions_url = f"{self.base_url}/rest/risk/position/getPositions/{account}"
        response = requests.get(positions_url, headers=headers)
        
        if response.status_code == 200:
            self.log.info("respuesta correcta de get positi")
            return response.json()
        else:
            self.log.info("error en get positcion rest")
            raise Exception("Error al obtener las posiciones")

    def get_historical_trades(self, market_id="ROFX", symbol="DLR/DIC23", dateFrom="2023-02-08", dateTo="2023-02-09"):
        headers = self._get_headers()
        historical_trades_url = f"{self.base_url}/rest/data/getTrades?marketId={market_id}&symbol={symbol}&dateFrom={dateFrom}&dateTo={dateTo}"
        response = requests.get(historical_trades_url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception("Error al obtener los trades históricos")