"""
Sistema de logros del juego.
"""


class Logro:
    """Representa un logro individual."""
    
    def __init__(self, nombre, descripcion, completo=False):
        self.nombre = nombre
        self.descripcion = descripcion
        self.completo = completo

    def __str__(self):
        return f"{self.nombre}: {self.descripcion}"


class Lista_Logros:
    """Gestiona los logros del jugador."""
    
    def __init__(self):
        self.logros = []

    def agregar_logro(self, logro):
        self.logros.append(logro)

    def mostrar_logros(self):
        if not self.logros:
            print("No has desbloqueado ningún logro aún.")
        else:
            print("Logros desbloqueados:")
            for logro in self.logros:
                print(f"- {logro}")
