from multiprocessing import Process, Pipe

def worker(conn):
    conn.send('Hola')
    conn.send('Mundo')
    conn.send('!')
    conn.close()

if __name__ == '__main__':
    parent_conn, child_conn = Pipe()
    p = Process(target=worker, args=(child_conn,))
    p.start()

    while True:
        try:
            item = parent_conn.recv()
        except EOFError:
            break
        print(item)

    p.join()