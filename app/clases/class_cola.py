class Cola:
    def __init__(self):
        self.tareas = []
    
    async def agregar_tarea(self, tarea):
        self.tareas.append(tarea)
    
    async def obtener_tarea(self):
        if self.tareas:
            return self.tareas.pop(0)
        return None
    
    async def marcar_completada(self, tarea):
        if tarea in self.tareas:
            self.tareas.remove(tarea)