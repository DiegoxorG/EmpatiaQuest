"""
Sistema de logros del juego EmpatiaQuest.
Cada logro se desbloquea automáticamente según las decisiones del jugador.
"""

# ─── Definición de todos los logros ──────────────────────────────────────────
LOGROS_DEFINIDOS = [
    {
        "id": "primera_empatia",
        "nombre": "Primera Empatia",
        "descripcion": "Tomaste tu primera decision empatica.",
    },
    {
        "id": "defensor",
        "nombre": "Defensor Silencioso",
        "descripcion": "Defendiste a alguien que lo necesitaba.",
    },
    {
        "id": "mediador",
        "nombre": "Mediador",
        "descripcion": "Resolviste un conflicto con calma y sin escalar.",
    },
    {
        "id": "digital_empathy",
        "nombre": "Empatia Digital",
        "descripcion": "Manejaste correctamente un caso de ciberbullying.",
    },
    {
        "id": "antirracista",
        "nombre": "Antirracista",
        "descripcion": "Confrontaste el racismo con educacion y respeto.",
    },
    {
        "id": "inclusion",
        "nombre": "Puente de Inclusion",
        "descripcion": "Integraste a alguien que estaba siendo excluido.",
    },
    {
        "id": "salud_mental",
        "nombre": "Red de Apoyo",
        "descripcion": "Apoyaste a alguien en una crisis de salud mental.",
    },
    {
        "id": "nunca_ignores",
        "nombre": "Nunca De Espaldas",
        "descripcion": "Completaste el juego sin ignorar a nadie.",
    },
    {
        "id": "final_positivo",
        "nombre": "Heroe Silencioso",
        "descripcion": "Terminaste la historia con el final positivo.",
    },
    {
        "id": "empatia_pura",
        "nombre": "Empatia Pura",
        "descripcion": "Solo tomaste decisiones empaticas en toda la historia.",
    },
    {
        "id": "comprensivo",
        "nombre": "Comprensivo",
        "descripcion": "Intentaste entender a quien hacia dano.",
    },
    {
        "id": "valiente",
        "nombre": "Valiente",
        "descripcion": "Dijiste no cuando era lo correcto, aunque costara.",
    },
]

# ─── Disparadores: (event_id, option_idx) → lista de logro IDs ───────────────
# option_idx es el índice 0-based de la opción elegida en el evento.
LOGRO_TRIGGERS = {
    ("primer_dia", 0):        ["primera_empatia"],
    ("primer_dia", 2):        ["primera_empatia"],
    ("voces_pasillo", 0):     ["primera_empatia", "defensor"],
    ("voces_pasillo", 2):     ["primera_empatia", "mediador"],
    ("reenviado", 0):         ["primera_empatia", "digital_empathy"],
    ("reenviado", 2):         ["primera_empatia", "digital_empathy"],
    ("detras_agresor", 0):    ["mediador", "comprensivo"],
    ("encajar", 1):           ["valiente"],
    ("encajar", 2):           ["defensor", "valiente"],
    ("broma", 0):             ["defensor"],
    ("broma", 2):             ["mediador"],
    ("racismo", 1):           ["antirracista"],
    ("xenofobia", 0):         ["inclusion"],
    ("xenofobia", 1):         ["inclusion", "defensor"],
    ("no_era_flojera", 0):    ["salud_mental"],
    ("no_era_flojera", 1):    ["salud_mental"],
    ("persona_llorando", 0):  ["salud_mental"],
    ("persona_llorando", 1):  ["salud_mental"],
    ("rumores", 0):           ["mediador"],
    ("rumores", 1):           ["defensor"],
}


# ─── Clases ───────────────────────────────────────────────────────────────────

class Logro:
    """Representa un logro individual."""

    def __init__(self, logro_id, nombre, descripcion, completo=False):
        self.id = logro_id
        self.nombre = nombre
        self.descripcion = descripcion
        self.completo = completo

    def __str__(self):
        estado = "[X]" if self.completo else "[ ]"
        return f"{estado} {self.nombre}: {self.descripcion}"

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "completo": self.completo,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            d.get("id", ""),
            d.get("nombre", ""),
            d.get("descripcion", ""),
            bool(d.get("completo", False)),
        )


class Lista_Logros:
    """Gestiona el conjunto de logros del jugador."""

    def __init__(self):
        self.logros = {
            d["id"]: Logro(d["id"], d["nombre"], d["descripcion"])
            for d in LOGROS_DEFINIDOS
        }
        # Cola FIFO de logros recién desbloqueados para el popup visual.
        self._cola_popup = []

    # ── Desbloqueo ────────────────────────────────────────────────────────────

    def desbloquear(self, logro_id):
        """Desbloquea un logro. Retorna True si se desbloqueó por primera vez."""
        logro = self.logros.get(logro_id)
        if logro and not logro.completo:
            logro.completo = True
            self._cola_popup.append(logro)
            return True
        return False

    def desbloquear_por_evento(self, event_id, option_idx):
        """Desbloquea logros según el evento y el índice de opción elegida."""
        for logro_id in LOGRO_TRIGGERS.get((event_id, option_idx), []):
            self.desbloquear(logro_id)

    def desbloquear_final_positivo(self):
        self.desbloquear("final_positivo")

    def verificar_nunca_ignoraste(self, decision_history):
        """Desbloquea 'nunca_ignores' si ninguna decisión fue ignorar (dF <= -8)."""
        if not decision_history:
            return
        if all(d.get("dF", 0) > -8 for d in decision_history):
            self.desbloquear("nunca_ignores")

    def verificar_empatia_pura(self, decision_history):
        """Desbloquea 'empatia_pura' si todas las decisiones tuvieron dF > 0."""
        if not decision_history:
            return
        if all(d.get("dF", 0) > 0 for d in decision_history):
            self.desbloquear("empatia_pura")

    # ── Popup ─────────────────────────────────────────────────────────────────

    def consumir_popup(self):
        """Retorna el siguiente logro para mostrar en popup, o None."""
        return self._cola_popup.pop(0) if self._cola_popup else None

    # ── Persistencia ──────────────────────────────────────────────────────────

    def to_list(self):
        return [l.to_dict() for l in self.logros.values()]

    def load_from_list(self, data):
        if not isinstance(data, list):
            return
        for item in data:
            if isinstance(item, dict):
                lid = item.get("id", "")
                if lid in self.logros:
                    self.logros[lid].completo = bool(item.get("completo", False))

    # ── Consultas ─────────────────────────────────────────────────────────────

    def completados(self):
        return [l for l in self.logros.values() if l.completo]

    def todos(self):
        return list(self.logros.values())

    def porcentaje(self):
        total = len(self.logros)
        if total == 0:
            return 0
        return int((len(self.completados()) / total) * 100)

    def mostrar_logros(self):
        for logro in self.logros.values():
            print(f"- {logro}")
