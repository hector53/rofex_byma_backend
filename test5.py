from multiprocessing import Process, Queue
import time

class MyClass():
    def __init__(self, id):
        self.id = id
        self.x = 0

    def run(self, queue):
        while True:
            self.x += 1
            print(f"estamos en la instancia con id: {self.id}, x: {self.x}")
            queue.put({'id': self.id, 'x': self.x})
            time.sleep(1)

if __name__ == "__main__":
    queue = Queue()
    my_classes = [MyClass(1), MyClass(2), MyClass(3)]
    processes = []

    for my_class in my_classes:
        p = Process(target=my_class.run, args=(queue,))
        processes.append(p)
        p.start()

    while True:
        if not queue.empty():
            data = queue.get()
            print(f"Proceso con id {data['id']} reporta x: {data['x']}")
        time.sleep(0.1)