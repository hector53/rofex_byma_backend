import asyncio
import quickfix as fix
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(sys.path[0]), 'model'))
__SOH__ = chr(1)
class fixMsgManager:
    def __init__(self):
        self.clOrdIdEsperar = {}
    
    async def add_task(self, type, message, session):
        if type==1:
            asyncio.create_task(self.onMessage_ExecutionReport_New(message, session))

    async def remove_task(self, task):
        self.tasks.remove(task)

    def stop_task(self, task):
        task.stop()

    async def stop_all_tasks(self):
        print("entrando a detener todas")
        while not self.tasks.empty():
            print("obtener tarea a deteber")
            task = await self.tasks.get()
            print(f"tarea: {task}")
            task.stop()

    async def get_fixTask_by_id_user(self, user):
        taskReturn = None
        if user in self.main_tasks: 
            return self.main_tasks.get(user, None)
        return taskReturn
    
    async def onMessage_ExecutionReport_New(self, message, session):
        msg = message.toString().replace(__SOH__, "|")
     #   logfix.info("R new order>> (%s)" % msg)
        """
        onMessage - Execution Report - New
        Message Type = '8', ExecType '0' = New.
        Confirm the receipt of an order.
        Fields:
            - (35) - MsgType = 8
            - (6)  - AvgPx = (float)
            - (11) - ClOrdId = (string)
            - (14) - CumQty = (int)
            - (17) - ExecID = (string)
            - (31) - LastPx = (float)
            - (32) - LastQty = (int)
            - (37) - OrderID = (string)
            - (38) - OrderQty = (int)
            - (39) - OrderStatus = 0 (New)
            - (40) - OrdType = 2 (Limit)
            - (44) - Price = (float)
            - (54) - Side = 1 (Buy) / 2 (Sell)
            - (55) - Symbol = (string)
            - (58) - Text = (string)
            - (60) - TransactTime = UTC Timestamp
            - (150) - ExecType = 0 (New)
            - (151) - LeavesQty = (int)
        """
        clientOrderID = self.getValue(message, fix.ClOrdID())
        targetCompID = session.getTargetCompID().getValue()
        senderCompID = session.getSenderCompID().getValue()
        orderID = self.getValue(message, fix.OrderID())
        accountIDMsg = self.getValue(message, fix.Account())
        
        details = {'targetCompId': targetCompID,
                   'clOrdId': clientOrderID,
                   'execId': self.getValue(message, fix.ExecID()),
                   'symbol': self.getValue(message, fix.Symbol()),
                   'side': self.getSide(self.getValue(message, fix.Side())),
                   'securityExchange': self.getValue(message, fix.SecurityExchange()),
                   'transactTime': self.getString(message, fix.TransactTime()),
                   'ordStatus': self.getOrdStatus(self.getValue(message, fix.OrdStatus())),
                   'ordType': self.getOrdType(self.getValue(message, fix.OrdType())),
                   'price': self.getValue(message, fix.Price()),
                   'avgPx': self.getValue(message, fix.AvgPx()),
                   'lastPx': self.getValue(message, fix.LastPx()),
                   'orderQty': self.getValue(message, fix.OrderQty()),
                   'leavesQty': self.getValue(message, fix.LeavesQty()),
                   'cumQty': self.getValue(message, fix.CumQty()),
                   'lastQty': self.getValue(message, fix.LastQty()),
                   'text': self.getValue(message, fix.Text()),
                   'orderId': orderID,
                   'marketLimit': False,
                   'typeFilled': 0
                   }
        data = {}
        data['type'] = 'or'
        data['senderCompID'] = senderCompID
        data['orderReport'] = {'accountId': {'id': self.account},
                               'clOrdId': details['clOrdId'],
                               'cumQty': details['cumQty'],
                               'execId': details['execId'],
                               'instrumentId': {'marketId': details['securityExchange'], 'symbol': details['symbol']},
                               'leavesQty': details['leavesQty'],
                               'ordType': details['ordType'],
                               'orderId': orderID,
                               'orderQty': details['orderQty'],
                               'price': details['price'],
                               'side': details['side'],
                               'status': details['ordStatus'],
                               'transactTime': details['transactTime'],
                               'text': details['text']
                               }
        
        #actualizamos variable en espera
        if clientOrderID in self.clOrdIdEsperar:
            self.clOrdIdEsperar[clientOrderID]["llegoRespuesta"] = True
            self.clOrdIdEsperar[clientOrderID]["data"] = details

        self.orders[orderID] = details
        self.sessions[targetCompID][clientOrderID] = orderID

        # verificar si es una orden nueva en espera y de ser asi, enviar la respuesta
        #logfix.info(f"enviar al bot new order")
            
      #  self.send_to_bot(details, accountIDMsg, 0)#0=order new 

        self.server_md.broadcast(str(data))
