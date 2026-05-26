"""
Sistema de audio para EmpatiaQuest.

Usa archivos en Audio/BGM y Audio/SFX cuando existan. Si no existen, genera
musica/ambientes/efectos procedurales para que el juego tenga sonido sin
depender de assets externos. Cualquier fallo de pygame.mixer se ignora para no
interrumpir la partida.
"""

import math
import os
import random
from array import array

import pygame


_AUDIO_BASE = os.path.join(os.path.dirname(__file__), "Audio")
_SAMPLE_RATE = 44100
_MAX_I16 = 32767


BGM_MAP = {
    "menu": "menu_principal",
    "jugar": "menu_principal",
    "creador": "menu_principal",
    "configuracion": "menu_principal",
    "controles": "menu_principal",
    "historia": "menu_principal",
    "progreso": "menu_principal",
    "tutorial": "menu_principal",
    "creditos": "menu_principal",
    "prologo": "prologo",
    "aventura": "exploracion",
    "pause": "exploracion",
    "pause_guardar": "exploracion",
    "load_slots": "menu_principal",
    "simulacion": "exploracion",
    "minijuego": "minijuego_batalla",
}


SFX_ALIASES = {
    "pupitre": "madera",
    "escritorio": "madera",
    "armario": "armario",
    "cama": "tela",
    "mesa": "madera",
    "mesita": "madera",
    "borrador": "borrar",
    "balon": "balon",
    "maquina": "maquina",
}


def _clamp_sample(value):
    return max(-_MAX_I16, min(_MAX_I16, int(value)))


def _adsr(t, duration, attack=0.01, release=0.05):
    if duration <= 0:
        return 0.0
    if t < attack:
        return t / max(0.001, attack)
    if t > duration - release:
        return max(0.0, (duration - t) / max(0.001, release))
    return 1.0


class AudioManager:
    """Gestiona BGM, ambientes y SFX con fallback procedural."""

    def __init__(self):
        self._initialized = False
        self._current_bgm_name = None
        self._current_ambience_name = None
        self._volume = 0.7
        self._sfx_cache = {}
        self._generated_cache = {}
        self._ambience_cache = {}
        self._bgm_fallback_cache = {}
        self._last_step_ms = 0
        self._step_toggle = False
        self._try_init()
        if self._initialized:
            try:
                pygame.mixer.set_num_channels(max(16, pygame.mixer.get_num_channels()))
                self._ambience_channel = pygame.mixer.Channel(6)
                self._bgm_fallback_channel = pygame.mixer.Channel(7)
            except Exception:
                self._ambience_channel = None
                self._bgm_fallback_channel = None
        else:
            self._ambience_channel = None
            self._bgm_fallback_channel = None

    def _try_init(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=512)
            self._initialized = True
        except Exception:
            self._initialized = False

    def _bgm_path(self, nombre):
        return os.path.join(_AUDIO_BASE, "BGM", f"{nombre}.ogg")

    def _sfx_path(self, nombre):
        for ext in ("ogg", "wav", "mp3"):
            path = os.path.join(_AUDIO_BASE, "SFX", f"{nombre}.{ext}")
            if os.path.exists(path):
                return path
        return os.path.join(_AUDIO_BASE, "SFX", f"{nombre}.ogg")

    def _make_sound(self, samples):
        if not self._initialized:
            return None
        try:
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except Exception:
            return None

    def _tone(self, freqs, duration=0.18, volume=0.35, wave="sine", noise=0.0):
        n = max(1, int(_SAMPLE_RATE * duration))
        samples = array("h")
        if not isinstance(freqs, (list, tuple)):
            freqs = [freqs]
        for i in range(n):
            t = i / _SAMPLE_RATE
            env = _adsr(t, duration)
            v = 0.0
            for freq in freqs:
                phase = 2.0 * math.pi * freq * t
                if wave == "square":
                    v += 1.0 if math.sin(phase) >= 0 else -1.0
                elif wave == "triangle":
                    v += 2.0 * abs(2.0 * ((freq * t) % 1.0) - 1.0) - 1.0
                else:
                    v += math.sin(phase)
            v /= max(1, len(freqs))
            if noise:
                v = (v * (1.0 - noise)) + (random.uniform(-1.0, 1.0) * noise)
            s = _clamp_sample(v * env * volume * _MAX_I16)
            samples.append(s)
            samples.append(s)
        return self._make_sound(samples)

    def _sweep(self, start_freq, end_freq, duration=0.25, volume=0.35, noise=0.0):
        n = max(1, int(_SAMPLE_RATE * duration))
        samples = array("h")
        phase = 0.0
        for i in range(n):
            t = i / _SAMPLE_RATE
            p = i / max(1, n - 1)
            freq = start_freq + (end_freq - start_freq) * p
            phase += 2.0 * math.pi * freq / _SAMPLE_RATE
            env = _adsr(t, duration)
            v = math.sin(phase)
            if noise:
                v = (v * (1.0 - noise)) + (random.uniform(-1.0, 1.0) * noise)
            s = _clamp_sample(v * env * volume * _MAX_I16)
            samples.append(s)
            samples.append(s)
        return self._make_sound(samples)

    def _rhythm_loop(self, base_freqs, duration=3.2, volume=0.18, noise=0.0):
        n = max(1, int(_SAMPLE_RATE * duration))
        samples = array("h")
        for i in range(n):
            t = i / _SAMPLE_RATE
            beat = int(t * 2) % max(1, len(base_freqs))
            freq = base_freqs[beat]
            pulse = 0.55 + 0.45 * math.sin(2 * math.pi * 0.5 * t)
            v = math.sin(2 * math.pi * freq * t) * pulse
            v += math.sin(2 * math.pi * freq * 2.01 * t) * 0.18
            if noise:
                v += random.uniform(-1.0, 1.0) * noise
            env = min(1.0, t / 0.25, (duration - t) / 0.25)
            s = _clamp_sample(v * env * volume * _MAX_I16)
            samples.append(s)
            samples.append(s)
        return self._make_sound(samples)

    def _noise_loop(self, duration=2.4, volume=0.12, tone=0.0):
        n = max(1, int(_SAMPLE_RATE * duration))
        samples = array("h")
        last = 0.0
        for i in range(n):
            t = i / _SAMPLE_RATE
            last = (last * 0.96) + (random.uniform(-1.0, 1.0) * 0.04)
            hum = math.sin(2 * math.pi * tone * t) * 0.12 if tone else 0.0
            env = min(1.0, t / 0.25, (duration - t) / 0.25)
            s = _clamp_sample((last + hum) * env * volume * _MAX_I16)
            samples.append(s)
            samples.append(s)
        return self._make_sound(samples)

    # BGM

    def play_bgm(self, nombre, loop=True):
        if not self._initialized or self._current_bgm_name == nombre:
            return
        self.stop_bgm(fade_ms=250)
        path = self._bgm_path(nombre)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self._volume)
                pygame.mixer.music.play(-1 if loop else 0)
                self._current_bgm_name = nombre
                return
            except Exception:
                pass
        self._play_generated_bgm(nombre, loop)

    def _play_generated_bgm(self, nombre, loop=True):
        if self._bgm_fallback_channel is None:
            return
        sound = self._bgm_fallback_cache.get(nombre)
        if sound is None:
            if nombre == "prologo":
                sound = self._rhythm_loop([220, 196, 174, 196], duration=4.0, volume=0.11, noise=0.01)
            elif nombre == "decision":
                sound = self._rhythm_loop([110, 116, 110, 123], duration=2.4, volume=0.13, noise=0.02)
            elif nombre == "minijuego_batalla":
                sound = self._rhythm_loop([330, 392, 440, 523], duration=1.6, volume=0.14, noise=0.01)
            elif nombre == "final_positivo":
                sound = self._rhythm_loop([392, 494, 587, 659], duration=4.0, volume=0.15)
            elif nombre == "final_negativo":
                sound = self._rhythm_loop([146, 138, 130, 123], duration=4.0, volume=0.12, noise=0.01)
            elif nombre == "final_neutral":
                sound = self._rhythm_loop([196, 247, 220, 174], duration=4.0, volume=0.12)
            elif nombre == "exploracion":
                sound = self._rhythm_loop([262, 330, 392, 330], duration=4.0, volume=0.10)
            else:
                sound = self._rhythm_loop([330, 392, 440, 392], duration=3.2, volume=0.10)
            self._bgm_fallback_cache[nombre] = sound
        if sound is None:
            return
        try:
            sound.set_volume(self._volume * 0.45)
            self._bgm_fallback_channel.play(sound, -1 if loop else 0, 0, 250)
            self._current_bgm_name = nombre
        except Exception:
            pass

    def play_bgm_for_screen(self, screen_name):
        nombre = BGM_MAP.get(screen_name)
        if nombre:
            self.play_bgm(nombre)

    def stop_bgm(self, fade_ms=0):
        if not self._initialized:
            return
        try:
            pygame.mixer.music.fadeout(fade_ms) if fade_ms else pygame.mixer.music.stop()
            if self._bgm_fallback_channel is not None:
                self._bgm_fallback_channel.fadeout(fade_ms) if fade_ms else self._bgm_fallback_channel.stop()
            self._current_bgm_name = None
        except Exception:
            pass

    def fade_bgm(self, ms=800):
        self.stop_bgm(fade_ms=ms)

    def play_decision_bgm(self):
        self.play_bgm("decision")

    def play_ending_bgm(self, final_key):
        if "POSITIVO" in final_key:
            self.play_bgm("final_positivo", loop=False)
        elif "NEGATIVO" in final_key:
            self.play_bgm("final_negativo", loop=False)
        else:
            self.play_bgm("final_neutral", loop=False)

    # Ambientes por mapa

    def ambience_name_for_map(self, map_name):
        base = os.path.basename(str(map_name)).lower()
        if any(k in base for k in ("patio", "calle", "azotea", "atras", "atr", "piscina")):
            return "exterior"
        if "cafeteria" in base:
            return "cafeteria"
        if any(k in base for k in ("bano", "baño")):
            return "bano"
        if any(k in base for k in ("bib", "biblioteca")):
            return "biblioteca"
        if any(k in base for k in ("hab", "noche")):
            return "habitacion_noche" if "noche" in base else "habitacion"
        if any(k in base for k in ("salon", "salón", "pasillo")):
            return "colegio"
        return "colegio"

    def play_ambience_for_map(self, map_name):
        name = self.ambience_name_for_map(map_name)
        if not self._initialized or self._current_ambience_name == name:
            return
        if self._ambience_channel is None:
            return
        sound = self._ambience_cache.get(name)
        if sound is None:
            if name == "exterior":
                sound = self._noise_loop(duration=2.8, volume=0.10, tone=120)
            elif name == "cafeteria":
                sound = self._noise_loop(duration=2.2, volume=0.13, tone=90)
            elif name == "bano":
                sound = self._noise_loop(duration=2.6, volume=0.08, tone=180)
            elif name == "biblioteca":
                sound = self._noise_loop(duration=3.0, volume=0.055, tone=75)
            elif name == "habitacion_noche":
                sound = self._noise_loop(duration=3.2, volume=0.045, tone=55)
            elif name == "habitacion":
                sound = self._noise_loop(duration=3.2, volume=0.06, tone=70)
            else:
                sound = self._noise_loop(duration=2.6, volume=0.08, tone=100)
            self._ambience_cache[name] = sound
        if sound is None:
            return
        try:
            sound.set_volume(self._volume * 0.35)
            self._ambience_channel.play(sound, -1, 0, 500)
            self._current_ambience_name = name
        except Exception:
            pass

    def stop_ambience(self, fade_ms=350):
        if self._ambience_channel is not None:
            try:
                self._ambience_channel.fadeout(fade_ms)
            except Exception:
                pass
        self._current_ambience_name = None

    # SFX

    def _generate_sfx(self, nombre):
        if nombre in self._generated_cache:
            return self._generated_cache[nombre]
        specs = {
            "click_boton": lambda: self._tone([680, 920], 0.055, 0.28, "square"),
            "hover_boton": lambda: self._tone(880, 0.035, 0.16, "sine"),
            "guardar_partida": lambda: self._sweep(520, 980, 0.22, 0.32),
            "decision_tomada": lambda: self._tone([330, 494, 659], 0.22, 0.28, "triangle"),
            "logro_desbloqueado": lambda: self._tone([523, 659, 784], 0.45, 0.30, "sine"),
            "paso_suave": lambda: self._tone(120, 0.065, 0.20, "triangle", noise=0.35),
            "paso_firme": lambda: self._tone(95, 0.075, 0.24, "triangle", noise=0.45),
            "paso_exterior": lambda: self._tone(80, 0.08, 0.22, "triangle", noise=0.55),
            "paso_madera": lambda: self._tone(150, 0.07, 0.20, "triangle", noise=0.25),
            "puerta": lambda: self._sweep(180, 95, 0.28, 0.34, noise=0.25),
            "interactuar": lambda: self._tone([440, 660], 0.12, 0.26, "sine"),
            "sentarse": lambda: self._sweep(210, 120, 0.18, 0.28, noise=0.25),
            "dialogo_avanzar": lambda: self._tone(720, 0.045, 0.18, "square"),
            "error": lambda: self._sweep(260, 120, 0.16, 0.26, noise=0.12),
            "camara_foto": lambda: self._tone(1000, 0.055, 0.34, "square", noise=0.60),
            "borrar": lambda: self._tone(180, 0.10, 0.18, "triangle", noise=0.75),
            "madera": lambda: self._tone(180, 0.08, 0.24, "triangle", noise=0.35),
            "armario": lambda: self._sweep(140, 90, 0.22, 0.30, noise=0.28),
            "tela": lambda: self._tone(90, 0.10, 0.16, "triangle", noise=0.70),
            "balon": lambda: self._sweep(110, 70, 0.12, 0.30, noise=0.18),
            "maquina": lambda: self._tone([220, 440], 0.22, 0.20, "square", noise=0.20),
            "npc": lambda: self._tone([390, 520], 0.10, 0.18, "triangle"),
            "burla": lambda: self._sweep(760, 520, 0.20, 0.20),
            "pupitre_alerta": lambda: self._tone([220, 277, 330], 0.35, 0.25, "triangle"),
            "hit_corazon": lambda: self._tone(72, 0.20, 0.40, "square", noise=0.35),
            "minijuego_ganar": lambda: self._tone([523, 659, 784, 1046], 0.55, 0.34, "sine"),
            "minijuego_perder": lambda: self._sweep(220, 80, 0.55, 0.34, noise=0.12),
            "aviso_ataque": lambda: self._tone(980, 0.08, 0.24, "square"),
            "oleada": lambda: self._sweep(300, 520, 0.22, 0.22, noise=0.05),
            "pausa": lambda: self._tone([260, 196], 0.12, 0.22, "triangle"),
        }
        factory = specs.get(nombre, specs["interactuar"])
        sound = factory()
        if sound is not None:
            try:
                sound.set_volume(self._volume * 0.85)
            except Exception:
                pass
        self._generated_cache[nombre] = sound
        return sound

    def _load_sfx(self, nombre):
        if nombre in self._sfx_cache:
            return self._sfx_cache[nombre]
        if not self._initialized:
            self._sfx_cache[nombre] = None
            return None
        path = self._sfx_path(nombre)
        if os.path.exists(path):
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(self._volume * 0.85)
                self._sfx_cache[nombre] = sound
                return sound
            except Exception:
                pass
        sound = self._generate_sfx(nombre)
        self._sfx_cache[nombre] = sound
        return sound

    def play_sfx(self, nombre, volume_scale=1.0):
        sound = self._load_sfx(nombre)
        if sound is None:
            return
        try:
            sound.set_volume(self._volume * 0.85 * volume_scale)
            sound.play()
        except Exception:
            pass

    def update_player_motion(self, moving, sprint=False, map_name=""):
        if not moving:
            return
        now = pygame.time.get_ticks()
        interval = 230 if sprint else 310
        if now - self._last_step_ms < interval:
            return
        self._last_step_ms = now
        ambience = self.ambience_name_for_map(map_name)
        if ambience == "exterior":
            name = "paso_exterior"
        elif ambience in ("habitacion", "habitacion_noche", "biblioteca"):
            name = "paso_madera"
        else:
            name = "paso_firme" if sprint else "paso_suave"
        self._step_toggle = not self._step_toggle
        self.play_sfx(name, 0.95 if self._step_toggle else 0.75)

    def apply_volume(self, valor_0_a_100):
        self._volume = max(0.0, min(1.0, valor_0_a_100 / 100.0))
        if not self._initialized:
            return
        try:
            pygame.mixer.music.set_volume(self._volume)
        except Exception:
            pass
        for sound in list(self._sfx_cache.values()) + list(self._generated_cache.values()):
            if sound is not None:
                try:
                    sound.set_volume(self._volume * 0.85)
                except Exception:
                    pass
        try:
            if self._ambience_channel is not None:
                self._ambience_channel.set_volume(self._volume * 0.35)
            if self._bgm_fallback_channel is not None:
                self._bgm_fallback_channel.set_volume(self._volume * 0.45)
        except Exception:
            pass

    # Atajos semanticos

    def sfx_click(self): self.play_sfx("click_boton")
    def sfx_hover(self): self.play_sfx("hover_boton", 0.75)
    def sfx_guardar(self): self.play_sfx("guardar_partida")
    def sfx_decision(self): self.play_sfx("decision_tomada")
    def sfx_logro(self): self.play_sfx("logro_desbloqueado")
    def sfx_puerta(self): self.play_sfx("puerta")
    def sfx_interactuar(self): self.play_sfx("interactuar")
    def sfx_sentarse(self): self.play_sfx("sentarse")
    def sfx_dialogo(self): self.play_sfx("dialogo_avanzar", 0.8)
    def sfx_error(self): self.play_sfx("error")
    def sfx_camara(self): self.play_sfx("camara_foto")
    def sfx_borrar(self): self.play_sfx("borrar", 0.75)
    def sfx_npc(self): self.play_sfx("npc")
    def sfx_burla(self): self.play_sfx("burla")
    def sfx_pausa(self): self.play_sfx("pausa")

    def sfx_object(self, object_name):
        lowered = str(object_name).lower()
        for key, sfx_name in SFX_ALIASES.items():
            if key in lowered:
                self.play_sfx(sfx_name)
                return
        self.sfx_interactuar()
