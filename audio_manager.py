"""
Sistema de audio para EmpatiaQuest.
Gestiona BGM (música de fondo) y SFX (efectos de sonido).
Si los archivos de audio no existen, todo falla silenciosamente — el juego
sigue funcionando sin sonido.
"""

import os
import pygame

_AUDIO_BASE = os.path.join(os.path.dirname(__file__), "Audio")

# ─── Mapa de BGM por pantalla ─────────────────────────────────────────────────
# 🎶 ASSET_BGM: Audio/BGM/menu_principal.ogg | Música tranquila pixel-art para menú, jugar y creator
# 🎶 ASSET_BGM: Audio/BGM/prologo.ogg        | Nostálgico y melancólico para el prólogo/flashback
# 🎶 ASSET_BGM: Audio/BGM/exploracion.ogg    | Ambiente escolar suave para exploración del mundo
# 🎶 ASSET_BGM: Audio/BGM/decision.ogg       | Tensión leve cuando aparece un evento de decisión
# 🎶 ASSET_BGM: Audio/BGM/final_positivo.ogg | Esperanzador y cálido para el final positivo
# 🎶 ASSET_BGM: Audio/BGM/final_negativo.ogg | Sombrío y melancólico para el final negativo
# 🎶 ASSET_BGM: Audio/BGM/final_neutral.ogg  | Ambiguo para los dos finales neutrales
BGM_MAP = {
    "menu":          "menu_principal",
    "jugar":         "menu_principal",
    "creador":       "menu_principal",
    "configuracion": "menu_principal",
    "controles":     "menu_principal",
    "historia":      "menu_principal",
    "progreso":      "menu_principal",
    "tutorial":      "menu_principal",
    "creditos":      "menu_principal",
    "prologo":       "prologo",
    "aventura":      "exploracion",
    "pause":         "exploracion",
    "pause_guardar": "exploracion",
    "load_slots":    "menu_principal",
    "simulacion":    "exploracion",
}

# ─── Nombres de SFX disponibles ───────────────────────────────────────────────
# 🎵 ASSET_SFX: Audio/SFX/click_boton.ogg        | Clic en un botón de menú
# 🎵 ASSET_SFX: Audio/SFX/hover_boton.ogg        | Hover sobre botón de menú
# 🎵 ASSET_SFX: Audio/SFX/guardar_partida.ogg    | Confirmación al guardar la partida
# 🎵 ASSET_SFX: Audio/SFX/decision_tomada.ogg    | Al elegir una opción de evento narrativo
# 🎵 ASSET_SFX: Audio/SFX/logro_desbloqueado.ogg | Fanfare breve al desbloquear un logro
# 🎵 ASSET_SFX: Audio/SFX/pasos.ogg              | Pasos del personaje al moverse
# 🎵 ASSET_SFX: Audio/SFX/puerta.ogg             | Al cruzar una puerta / cambio de mapa
# 🎵 ASSET_SFX: Audio/SFX/interactuar.ogg        | Al interactuar con un objeto del mundo
# 🎵 ASSET_SFX: Audio/SFX/sentarse.ogg           | Al sentarse o levantarse de una silla
# 🎵 ASSET_SFX: Audio/SFX/dialogo_avanzar.ogg    | Al avanzar texto de diálogo en prólogo


class AudioManager:
    """
    Gestiona BGM y SFX con fallback gracioso.
    Si pygame.mixer no está disponible o los archivos faltan, no lanza excepciones.
    """

    def __init__(self):
        self._initialized = False
        self._current_bgm_name = None
        self._volume = 0.7          # 0.0 – 1.0
        self._sfx_cache: dict = {}
        self._try_init()

    def _try_init(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._initialized = True
        except Exception:
            self._initialized = False

    def _bgm_path(self, nombre):
        return os.path.join(_AUDIO_BASE, "BGM", f"{nombre}.ogg")

    def _sfx_path(self, nombre):
        return os.path.join(_AUDIO_BASE, "SFX", f"{nombre}.ogg")

    # ── BGM ───────────────────────────────────────────────────────────────────

    def play_bgm(self, nombre, loop=True):
        """Reproduce el BGM indicado. Si ya suena, no lo reinicia."""
        if not self._initialized or self._current_bgm_name == nombre:
            return
        path = self._bgm_path(nombre)
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._volume)
            pygame.mixer.music.play(-1 if loop else 0)
            self._current_bgm_name = nombre
        except Exception:
            pass

    def play_bgm_for_screen(self, screen_name):
        """Elige y reproduce el BGM correcto para la pantalla indicada."""
        nombre = BGM_MAP.get(screen_name)
        if nombre:
            self.play_bgm(nombre)

    def stop_bgm(self):
        if not self._initialized:
            return
        try:
            pygame.mixer.music.stop()
            self._current_bgm_name = None
        except Exception:
            pass

    def fade_bgm(self, ms=800):
        if not self._initialized:
            return
        try:
            pygame.mixer.music.fadeout(ms)
            self._current_bgm_name = None
        except Exception:
            pass

    def play_decision_bgm(self):
        """Cambia a la música de tensión para un evento de decisión."""
        # 🎶 ASSET_BGM: Audio/BGM/decision.ogg | Tensión leve al presentar opciones
        if self._current_bgm_name == "decision":
            return
        self.fade_bgm(400)
        self.play_bgm("decision")

    def play_ending_bgm(self, final_key):
        """Reproduce la música del final según el tipo."""
        if "POSITIVO" in final_key:
            # 🎶 ASSET_BGM: Audio/BGM/final_positivo.ogg | Final positivo
            self.fade_bgm(600)
            self.play_bgm("final_positivo", loop=False)
        elif "NEGATIVO" in final_key:
            # 🎶 ASSET_BGM: Audio/BGM/final_negativo.ogg | Final negativo
            self.fade_bgm(600)
            self.play_bgm("final_negativo", loop=False)
        else:
            # 🎶 ASSET_BGM: Audio/BGM/final_neutral.ogg | Final neutral
            self.fade_bgm(600)
            self.play_bgm("final_neutral", loop=False)

    # ── SFX ───────────────────────────────────────────────────────────────────

    def _load_sfx(self, nombre):
        if nombre in self._sfx_cache:
            return self._sfx_cache[nombre]
        if not self._initialized:
            self._sfx_cache[nombre] = None
            return None
        path = self._sfx_path(nombre)
        if not os.path.exists(path):
            self._sfx_cache[nombre] = None
            return None
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self._volume * 0.85)
            self._sfx_cache[nombre] = sound
            return sound
        except Exception:
            self._sfx_cache[nombre] = None
            return None

    def play_sfx(self, nombre):
        sound = self._load_sfx(nombre)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    # ── Volumen ───────────────────────────────────────────────────────────────

    def apply_volume(self, valor_0_a_100):
        """Aplica el volumen del slider (0-100) a todos los canales activos."""
        self._volume = max(0.0, min(1.0, valor_0_a_100 / 100.0))
        if not self._initialized:
            return
        try:
            pygame.mixer.music.set_volume(self._volume)
        except Exception:
            pass
        for sound in self._sfx_cache.values():
            if sound is not None:
                try:
                    sound.set_volume(self._volume * 0.85)
                except Exception:
                    pass

    # ── Atajos de SFX ─────────────────────────────────────────────────────────

    def sfx_click(self):
        self.play_sfx("click_boton")

    def sfx_hover(self):
        self.play_sfx("hover_boton")

    def sfx_guardar(self):
        self.play_sfx("guardar_partida")

    def sfx_decision(self):
        self.play_sfx("decision_tomada")

    def sfx_logro(self):
        self.play_sfx("logro_desbloqueado")

    def sfx_puerta(self):
        self.play_sfx("puerta")

    def sfx_interactuar(self):
        self.play_sfx("interactuar")

    def sfx_sentarse(self):
        self.play_sfx("sentarse")

    def sfx_dialogo(self):
        self.play_sfx("dialogo_avanzar")
