from multiprocessing import Process, Value, Array
import time
from threading import Thread

class process():
    def __init__(self, id):
        self.id = id
        self.x = 0

    def run(self):
        x=Thread(target=self.run2)
        x.start()

    def run2(self):
        while True: 
            self.x+=1
            print(f"estamos en el proceso con id: {self.id}, x=: {self.x}") 
            time.sleep(1)

class processManager():
    def __init__(self):
        self.main_process = {}  
        self.contador = 0

    def add_process(self, process):
         id_processor = f"processor_{process.id}"
         p = Process(target=process.run)
         self.main_process[id_processor] = process
         p.start()

if __name__ == "__main__":
    pM = processManager()
    p1 = process(1)
    p2 = process(2)
    p3 = process(3)
    pM.add_process(p1)
    pM.add_process(p2)
    pM.add_process(p3)

    try:
        while True: 
            print("x en 1 : ", pM.main_process["processor_1"].x)
            time.sleep(2)
    except Exception as e: 
        print("error: ", e)