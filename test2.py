import multiprocessing
import time
def do_task(n):
    while True: 
        print(f"mostrando tarea: {n}")

if __name__ == "__main__":
        
    processes = []

    try:
        
        while True:
            p = multiprocessing.Process(target=do_task, args=(len(processes)+1, ))
            processes.append(p)
            p.start()
    except Exception as e:
        print(f"Error creating process: {e}")

    print(f"{len(processes)} processes created.")  