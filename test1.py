from multiprocessing import Process
import time
# Declara una función que representa una tarea
def do_task(n):
    start = time.time()
    print(f"Doing task {n}")
    end = time.time()
    print(f"Task {n} took {end-start} seconds")

# Envolve el código principal dentro de esta condición   
if __name__ == "__main__":
    
    # Crea una lista de tareas     
    tasks = [do_task for _ in range(10)]
        
    # Crea los procesos      
    processes = [Process(target=task, args=(i,)) for i, task in enumerate(tasks)]

    # Inicia los procesos     
    for process in processes:
        process.start()
        
    # Espera a que terminen los procesos      
    for process in processes:
        process.join()
        
    # Tareas realizadas      
    print("All tasks done!")