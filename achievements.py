"""
Achievement framework for EmpatiaQuest.

The public class ``Lista_Logros`` is kept as a compatibility alias for the old
code, but internally it now works as a complete achievement manager with:
definitions, progress, global persistence, event tracking and popup queue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from typing import Any, Callable


SAVE_FILE = os.path.join(os.path.dirname(__file__), "Partidas_Guardadas", "logros_globales.json")
SAVE_VERSION = 1

LEGACY_ACHIEVEMENT_IDS = {
    "primera_empatia": "alguien_escucho",
    "defensor": "alguien_escucho",
    "mediador": "alguien_escucho",
    "digital_empathy": "alguien_escucho",
    "inclusion": "alguien_escucho",
    "salud_mental": "no_estabas_solo",
    "nunca_ignores": "alguien_escucho",
    "final_positivo": "una_esperanza",
    "empatia_pura": "alguien_escucho",
    "comprensivo": "entre_los_dos_lados",
    "valiente": "alguien_escucho",
    "rey_de_los_bullies": "no_me_afecta",
    "irrefutable": "no_me_afecta",
}

RARITY_COLORS = {
    "comun": (90, 190, 255),
    "raro": (120, 220, 140),
    "epico": (190, 120, 255),
    "oculto": (255, 185, 60),
}


@dataclass(frozen=True)
class AchievementData:
    id: str
    nombre: str
    descripcion: str
    categoria: str
    rareza: str = "comun"
    objetivo: int = 1
    secreto: bool = False
    icono: str = ""
    condition: Callable[["AchievementTracker", Any], bool] | None = None
    progress: Callable[["AchievementTracker", Any], int] | None = None


@dataclass
class Logro:
    id: str
    nombre: str
    descripcion: str
    categoria: str = "General"
    rareza: str = "comun"
    objetivo: int = 1
    secreto: bool = False
    icono: str = ""
    completo: bool = False
    progreso: int = 0
    unlocked_at: int = 0
    _data: AchievementData | None = field(default=None, repr=False)

    @property
    def porcentaje(self) -> int:
        if self.completo:
            return 100
        return int(min(100, (self.progreso / max(1, self.objetivo)) * 100))

    @property
    def descripcion_visible(self) -> str:
        if self.secreto and not self.completo:
            return "Logro secreto. Se revelara al desbloquearlo."
        return self.descripcion

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "completo": self.completo,
            "progreso": self.progreso,
            "unlocked_at": self.unlocked_at,
        }

    @classmethod
    def from_data(cls, data: AchievementData) -> "Logro":
        return cls(
            id=data.id,
            nombre=data.nombre,
            descripcion=data.descripcion,
            categoria=data.categoria,
            rareza=data.rareza,
            objetivo=data.objetivo,
            secreto=data.secreto,
            icono=data.icono,
            _data=data,
        )


class AchievementTracker:
    """Tracks normalized facts used by achievement conditions."""

    IMPORTANT_AREAS = {
        "habdia", "habnoche", "habtarde", "salondia", "salontarde",
        "patiodia", "patiotarde", "cafeteriadia", "cafeteriatarde",
        "bibdia", "bibtarde", "banodia", "azoteadia", "atrastarde",
        "pasillo1dia", "pasillo2dia", "pasillodia", "piscinadia",
    }

    OPTIONAL_EVENTS_BY_DAY = {
        1: {"primer_dia_asiento", "dia1_pupitre_rayado"},
        2: {"dia2_chat", "dia2_lucas"},
        3: {"dia3_piscina", "dia3_cafeteria", "dia3_pelea"},
        4: {"dia4_broma", "dia4_biblioteca", "dia4_rumores"},
        5: {"dia5_pasillo", "dia5_sara", "dia5_diego"},
    }

    EMPATHIC_CHOICES = {
        "sara", "borrar", "profesor", "defender", "reportar", "psicologo",
        "consolar", "preguntar", "negarse", "detener", "ayuda", "separar",
        "acompanar", "incluir", "escuchar",
    }
    HARMFUL_CHOICES = {
        "ignorar", "reenviar", "minimizar", "participar", "apoyar",
        "foto", "reirse", "compartir", "juzgar", "irse",
    }
    HELP_CHOICES = {"borrar", "profesor", "defender", "reportar", "consolar", "preguntar", "detener", "ayuda", "separar", "acompanar", "incluir", "escuchar"}
    BULLY_CHOICES = {"reenviar", "participar", "apoyar", "reirse", "compartir", "juzgar"}
    IGNORE_CHOICES = {"ignorar", "irse", "minimizar"}

    def __init__(self) -> None:
        self.events_seen: set[str] = set()
        self.choices_by_event: dict[str, str] = {}
        self.areas_seen: set[str] = set()
        self.minigame_results: list[dict[str, Any]] = []
        self.endings_seen: set[str] = set()
        self.best_f: int = 0
        self.best_r: int = 0
        self.high_f_days: set[int] = set()

    def to_dict(self) -> dict[str, Any]:
        return {
            "events_seen": sorted(self.events_seen),
            "choices_by_event": dict(self.choices_by_event),
            "areas_seen": sorted(self.areas_seen),
            "minigame_results": list(self.minigame_results),
            "endings_seen": sorted(self.endings_seen),
            "best_f": self.best_f,
            "best_r": self.best_r,
            "high_f_days": sorted(self.high_f_days),
        }

    def load(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        self.events_seen = set(data.get("events_seen", []))
        self.choices_by_event = dict(data.get("choices_by_event", {}))
        self.areas_seen = set(data.get("areas_seen", []))
        self.minigame_results = [r for r in data.get("minigame_results", []) if isinstance(r, dict)]
        self.endings_seen = set(data.get("endings_seen", []))
        self.best_f = int(data.get("best_f", 0))
        self.best_r = int(data.get("best_r", 0))
        self.high_f_days = set(int(d) for d in data.get("high_f_days", []))

    def ingest_game(self, game: Any) -> None:
        self.best_f = max(self.best_f, int(getattr(game, "story_felicidad", 0)))
        self.best_r = max(self.best_r, int(getattr(game, "story_reputacion", 0)))
        if int(getattr(game, "story_felicidad", 0)) >= 70:
            self.high_f_days.add(int(getattr(game, "current_day", 1)))

        final_key = str(getattr(game, "story_final_key", "")).lower()
        if final_key:
            self.endings_seen.add(final_key)

        fondo = getattr(game, "aventura_fondo", None)
        ruta = str(getattr(fondo, "ruta_imagen", "")) if fondo is not None else ""
        area = self._normalize_area(os.path.basename(ruta))
        if area:
            self.areas_seen.add(area)

        for item in getattr(game, "decision_history", []) or []:
            self.register_decision(item)

    def register_decision(self, decision: dict[str, Any]) -> None:
        event_id = str(decision.get("event_id", ""))
        if not event_id:
            return
        choice = str(decision.get("choice", "") or decision.get("option_label", "")).lower()
        self.events_seen.add(event_id)
        if choice:
            self.choices_by_event[event_id] = choice
        if event_id.startswith("minijuego_") and not any(r.get("_key") == self._minigame_key(decision) for r in self.minigame_results):
            result = dict(decision)
            result["_key"] = self._minigame_key(decision)
            result["tipo"] = event_id.replace("minijuego_", "", 1)
            self.minigame_results.append(result)

    def register_minigame(self, result: dict[str, Any], context: str = "") -> None:
        stored = dict(result)
        stored["context"] = context
        stored["_key"] = self._minigame_key(stored)
        if not any(r.get("_key") == stored["_key"] for r in self.minigame_results):
            self.minigame_results.append(stored)

    def count_choices(self, choices: set[str]) -> int:
        return sum(1 for choice in self.choices_by_event.values() if choice in choices)

    def count_help(self) -> int:
        return self.count_choices(self.HELP_CHOICES)

    def count_empathy(self) -> int:
        return self.count_choices(self.EMPATHIC_CHOICES)

    def count_harmful(self) -> int:
        return self.count_choices(self.HARMFUL_CHOICES)

    def count_minigames_no_damage(self) -> int:
        return sum(1 for r in self.minigame_results if bool(r.get("gano")) and self._no_damage(r))

    def day_optional_complete(self, day: int) -> bool:
        required = self.OPTIONAL_EVENTS_BY_DAY.get(day, set())
        return bool(required) and required.issubset(self.events_seen)

    def _normalize_area(self, filename: str) -> str:
        raw = filename.lower().replace(".png", "").replace(".jpeg", "").replace(".webp", "")
        replacements = str.maketrans("áéíóúñü ", "aeiounu_")
        raw = raw.translate(replacements).replace("_", "").replace("(", "").replace(")", "").replace("1", "").replace("2", "").replace("3", "")
        for area in self.IMPORTANT_AREAS:
            if area in raw:
                return area
        return raw

    def _minigame_key(self, result: dict[str, Any]) -> str:
        return "|".join(str(result.get(k, "")) for k in ("event_id", "tipo", "context", "goles", "puntos", "gano"))

    def _no_damage(self, result: dict[str, Any]) -> bool:
        if "vidas_restantes" in result and "vidas_max" in result:
            return int(result["vidas_restantes"]) >= int(result["vidas_max"])
        if "vidas" in result and "max_vidas" in result:
            return int(result["vidas"]) >= int(result["max_vidas"])
        if "golpes" in result:
            return int(result["golpes"]) <= 0
        return False


def _choice(event_id: str, expected: str) -> Callable[[AchievementTracker, Any], bool]:
    return lambda t, _g: t.choices_by_event.get(event_id) == expected


def _ending(key: str) -> Callable[[AchievementTracker, Any], bool]:
    return lambda t, _g: key.lower() in t.endings_seen


ACHIEVEMENTS: tuple[AchievementData, ...] = (
    AchievementData("su_primer_amigo", "SU PRIMER AMIGO", "Elegiste escuchar a Sara hasta el final.", "Narrativo", "raro", condition=_choice("dia5_sara", "escuchar")),
    AchievementData("no_estabas_solo", "NO ESTABAS SOLO", "Consolaste correctamente a Lucas.", "Narrativo", "comun", condition=lambda t, g: t.choices_by_event.get("dia2_lucas") in {"consolar", "preguntar"}),
    AchievementData("alguien_hizo_algo", "ALGUIEN HIZO ALGO", "Obtuviste el final positivo.", "Narrativo", "epico", condition=_ending("positivo")),
    AchievementData("no_basta_con_mirar", "NO BASTA CON MIRAR", "Obtuviste el final neutral.", "Narrativo", "raro", condition=_ending("neutral")),
    AchievementData("todos_miraron", "TODOS MIRARON", "Obtuviste el final negativo.", "Narrativo", "raro", condition=_ending("negativo")),
    AchievementData("entre_los_dos_lados", "ENTRE LOS DOS LADOS", "Elegiste ayudar a Diego.", "Narrativo", "raro", condition=lambda t, g: t.choices_by_event.get("dia5_pasillo") == "diego" or t.choices_by_event.get("dia5_diego") in {"detener", "ayuda"}),
    AchievementData("punteria_perfecta", "PUNTERIA PERFECTA", "Anotaste todos los goles posibles en penaltis.", "Minijuegos", "epico", condition=lambda t, g: any(r.get("tipo") == "penaltis" and int(r.get("goles", 0)) >= 4 for r in t.minigame_results)),
    AchievementData("imparable", "IMPARABLE", "Ganaste penaltis sin fallar ningun intento.", "Minijuegos", "epico", condition=lambda t, g: any(r.get("tipo") == "penaltis" and bool(r.get("gano")) and int(r.get("goles", 0)) >= 4 for r in t.minigame_results)),
    AchievementData("estabilidad_emocional", "ESTABILIDAD EMOCIONAL", "Conseguiste 200 puntos en Atrapa Emociones.", "Minijuegos", "raro", 200, progress=lambda t, g: max([int(r.get("puntos", 0)) for r in t.minigame_results if r.get("tipo") == "atrapa_emociones"] or [0])),
    AchievementData("intocable", "INTOCABLE", "Terminaste Atrapa Emociones sin tocar emociones negativas.", "Minijuegos", "epico", condition=lambda t, g: any(r.get("tipo") == "atrapa_emociones" and bool(r.get("gano")) and int(r.get("vidas_restantes", 0)) >= int(r.get("vidas_max", 3)) for r in t.minigame_results)),
    AchievementData("no_me_afecta", "NO ME AFECTA", "Completaste un minijuego de esquivar sin recibir dano.", "Minijuegos", "epico", condition=lambda t, g: t.count_minigames_no_damage() >= 1),
    AchievementData("respirar_y_resistir", "RESPIRAR Y RESISTIR", "Superaste el minijuego final de Diego.", "Minijuegos", "raro", condition=lambda t, g: any(r.get("tipo") == "pelea_palabras" and bool(r.get("gano")) for r in t.minigame_results)),
    AchievementData("no_mas", "NO MAS", "Borraste el 100% de insultos antes del limite.", "Minijuegos", "comun", condition=lambda t, g: t.choices_by_event.get("dia1_pupitre_rayado") == "borrar" or any(r.get("tipo") == "borrar_insultos" and int(r.get("borrados", 0)) >= int(r.get("total", 1)) and not bool(r.get("tiempo_agotado", False)) for r in t.minigame_results)),
    AchievementData("curioso", "CURIOSO", "Interactuaste con todos los eventos importantes.", "Exploracion", "raro", 12, progress=lambda t, g: len(t.events_seen.intersection(set().union(*AchievementTracker.OPTIONAL_EVENTS_BY_DAY.values())))),
    AchievementData("siempre_observando", "SIEMPRE OBSERVANDO", "Leiste todos los dialogos opcionales de un dia.", "Exploracion", "raro", condition=lambda t, g: any(t.day_optional_complete(d) for d in t.OPTIONAL_EVENTS_BY_DAY)),
    AchievementData("de_paso", "DE PASO", "Entraste a todas las areas importantes del colegio.", "Exploracion", "epico", len(AchievementTracker.IMPORTANT_AREAS), progress=lambda t, g: len(t.areas_seen.intersection(AchievementTracker.IMPORTANT_AREAS))),
    AchievementData("el_espectador", "EL ESPECTADOR", "Ignoraste multiples situaciones importantes.", "Decisiones", "raro", 3, progress=lambda t, g: t.count_choices(AchievementTracker.IGNORE_CHOICES)),
    AchievementData("uno_mas_del_grupo", "UNO MAS DEL GRUPO", "Participaste en burlas repetidamente.", "Decisiones", "raro", 3, progress=lambda t, g: t.count_choices(AchievementTracker.BULLY_CHOICES)),
    AchievementData("alguien_escucho", "ALGUIEN ESCUCHO", "Escogiste opciones empaticas constantemente.", "Decisiones", "epico", 5, progress=lambda t, g: t.count_empathy()),
    AchievementData("popularidad_vacia", "POPULARIDAD VACIA", "Conseguiste alta reputacion con baja felicidad.", "Decisiones", "raro", condition=lambda t, g: int(getattr(g, "story_reputacion", 0)) >= 65 and int(getattr(g, "story_felicidad", 100)) <= 35),
    AchievementData("un_buen_ambiente", "UN BUEN AMBIENTE", "Mantuviste F alta durante varios dias.", "Decisiones", "epico", 3, progress=lambda t, g: len(t.high_f_days)),
    AchievementData("y_si_hablabas", "Y SI HABLABAS?", "No dijiste nada durante un evento clave.", "Secretos", "oculto", secreto=True, condition=lambda t, g: t.choices_by_event.get("dia5_diego") == "ignorar" or t.choices_by_event.get("dia5_sara") == "irse"),
    AchievementData("todo_cambia", "TODO CAMBIA", "Cambiaste completamente tu relacion con Sara.", "Secretos", "oculto", secreto=True, condition=lambda t, g: t.choices_by_event.get("primer_dia_asiento") != "sara" and t.choices_by_event.get("dia5_sara") == "escuchar"),
    AchievementData("repetir_la_historia", "REPETIR LA HISTORIA", "Tomaste malas decisiones de forma consistente.", "Secretos", "oculto", 5, secreto=True, progress=lambda t, g: t.count_harmful()),
    AchievementData("una_esperanza", "UNA ESPERANZA", "Viste el final positivo.", "Finales", "epico", condition=_ending("positivo")),
    AchievementData("no_fue_suficiente", "NO FUE SUFICIENTE", "Viste el final neutral.", "Finales", "raro", condition=_ending("neutral")),
    AchievementData("silencio", "SILENCIO", "Viste el final negativo.", "Finales", "raro", condition=_ending("negativo")),
)


class AchievementManager:
    def __init__(self, save_file: str = SAVE_FILE) -> None:
        self.save_file = save_file
        self.definitions = {data.id: data for data in ACHIEVEMENTS}
        self.logros = {data.id: Logro.from_data(data) for data in ACHIEVEMENTS}
        self.tracker = AchievementTracker()
        self._cola_popup: list[Logro] = []
        self._dirty = False
        self.load_global()

    def update_from_game(self, game: Any) -> None:
        before = self.tracker.to_dict()
        self.tracker.ingest_game(game)
        for logro in self.logros.values():
            data = logro._data
            if data is None or logro.completo:
                continue
            progress = data.progress(self.tracker, game) if data.progress else (data.objetivo if data.condition and data.condition(self.tracker, game) else 0)
            self.set_progress(logro.id, progress, save=False)
        if self.tracker.to_dict() != before or self._dirty:
            self.save_global()

    def register_minigame_result(self, result: dict[str, Any], context: str = "") -> None:
        self.tracker.register_minigame(result, context)
        self._dirty = True

    def set_progress(self, logro_id: str, value: int, save: bool = True) -> bool:
        logro = self.logros.get(logro_id)
        if logro is None:
            return False
        new_value = max(logro.progreso, min(int(value), logro.objetivo))
        if new_value != logro.progreso:
            logro.progreso = new_value
            self._dirty = True
        if logro.progreso >= logro.objetivo:
            return self.desbloquear(logro_id, save=save)
        if save and self._dirty:
            self.save_global()
        return False

    def desbloquear(self, logro_id: str, save: bool = True) -> bool:
        logro = self.logros.get(logro_id)
        if logro is None or logro.completo:
            return False
        logro.completo = True
        logro.progreso = logro.objetivo
        logro.unlocked_at = logro.unlocked_at or len(self.completados()) + 1
        self._cola_popup.append(logro)
        self._dirty = True
        if save:
            self.save_global()
        return True

    def desbloquear_por_evento(self, event_id: str, option_idx: int) -> None:
        for logro_id in LOGRO_TRIGGERS.get((event_id, option_idx), []):
            self.desbloquear(logro_id)

    def desbloquear_final_positivo(self) -> None:
        self.desbloquear("alguien_hizo_algo")
        self.desbloquear("una_esperanza")

    def verificar_nunca_ignoraste(self, decision_history: list[dict[str, Any]]) -> None:
        if decision_history and all(d.get("dF", 0) > -8 for d in decision_history):
            self.desbloquear("alguien_escucho")

    def verificar_empatia_pura(self, decision_history: list[dict[str, Any]]) -> None:
        if decision_history and all(d.get("dF", 0) > 0 for d in decision_history):
            self.desbloquear("alguien_escucho")

    def consumir_popup(self) -> Logro | None:
        return self._cola_popup.pop(0) if self._cola_popup else None

    def to_list(self) -> list[dict[str, Any]]:
        return [logro.to_dict() for logro in self.logros.values()]

    def load_from_list(self, data: list[dict[str, Any]]) -> None:
        if not isinstance(data, list):
            return
        for item in data:
            if isinstance(item, dict):
                raw_id = str(item.get("id", ""))
                logro = self.logros.get(raw_id) or self.logros.get(LEGACY_ACHIEVEMENT_IDS.get(raw_id, ""))
                if logro is not None:
                    logro.completo = logro.completo or bool(item.get("completo", False))
                    logro.progreso = max(logro.progreso, int(item.get("progreso", 0)))
        self.save_global()

    def load_global(self) -> None:
        try:
            with open(self.save_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, dict):
            return
        self.tracker.load(data.get("tracker", {}))
        for item in data.get("logros", []):
            if isinstance(item, dict):
                logro = self.logros.get(str(item.get("id", "")))
                if logro is not None:
                    logro.completo = bool(item.get("completo", False))
                    logro.progreso = int(item.get("progreso", 0))
                    logro.unlocked_at = int(item.get("unlocked_at", 0))

    def save_global(self) -> None:
        os.makedirs(os.path.dirname(self.save_file), exist_ok=True)
        payload = {
            "save_version": SAVE_VERSION,
            "logros": self.to_list(),
            "tracker": self.tracker.to_dict(),
        }
        try:
            with open(self.save_file, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=True, indent=2)
            self._dirty = False
        except OSError:
            pass

    def completados(self) -> list[Logro]:
        return [l for l in self.logros.values() if l.completo]

    def todos(self) -> list[Logro]:
        return list(self.logros.values())

    def porcentaje(self) -> int:
        total = len(self.logros)
        return int((len(self.completados()) / total) * 100) if total else 0

    def mostrar_logros(self) -> None:
        for logro in self.todos():
            estado = "[X]" if logro.completo else "[ ]"
            print(f"{estado} {logro.nombre}: {logro.descripcion_visible}")


class AchievementUI:
    """Small UI helper namespace used by renderers."""

    @staticmethod
    def rarity_color(rareza: str) -> tuple[int, int, int]:
        return RARITY_COLORS.get(rareza, RARITY_COLORS["comun"])


class Lista_Logros(AchievementManager):
    """Backward-compatible name used by the existing codebase."""


LOGRO_TRIGGERS: dict[tuple[str, int], list[str]] = {
    ("primer_dia", 0): ["alguien_escucho"],
    ("primer_dia", 2): ["alguien_escucho"],
}
