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


MAIN_THEME = "cambiar_el_mundo"


BGM_MAP = {
    "menu": MAIN_THEME,
    "jugar": MAIN_THEME,
    "creador": MAIN_THEME,
    "configuracion": MAIN_THEME,
    "controles": MAIN_THEME,
    "historia": MAIN_THEME,
    "progreso": MAIN_THEME,
    "tutorial": MAIN_THEME,
    "creditos": MAIN_THEME,
    "prologo": MAIN_THEME,
    "aventura": MAIN_THEME,
    "pause": MAIN_THEME,
    "pause_guardar": MAIN_THEME,
    "load_slots": MAIN_THEME,
    "simulacion": MAIN_THEME,
    "minijuego": MAIN_THEME,
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
        self._current_detail_name = None
        self._volume = 0.7
        self._sfx_cache = {}
        self._generated_cache = {}
        self._ambience_cache = {}
        self._detail_cache = {}
        self._bgm_fallback_cache = {}
        self._last_step_ms = 0
        self._last_named_sfx_ms = {}
        self._step_toggle = False
        self._try_init()
        if self._initialized:
            try:
                pygame.mixer.set_num_channels(max(16, pygame.mixer.get_num_channels()))
                self._ambience_channel = pygame.mixer.Channel(5)
                self._detail_channel = pygame.mixer.Channel(6)
                self._bgm_fallback_channel = pygame.mixer.Channel(7)
            except Exception:
                self._ambience_channel = None
                self._detail_channel = None
                self._bgm_fallback_channel = None
        else:
            self._ambience_channel = None
            self._detail_channel = None
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

    def _main_theme_loop(self):
        """Tema esperanzador y sobrio: tension social + impulso de cambio."""
        duration = 12.8
        n = max(1, int(_SAMPLE_RATE * duration))
        samples = array("h")
        chords = [
            (220.00, 261.63, 329.63),  # A menor
            (174.61, 261.63, 329.63),  # F maj7 sin quinta
            (196.00, 246.94, 293.66),  # G suspendido
            (164.81, 246.94, 329.63),  # E menor abierto
        ]
        motif = [440.00, 493.88, 523.25, 659.25, 587.33, 523.25, 493.88, 392.00]
        for i in range(n):
            t = i / _SAMPLE_RATE
            bar = int(t / 3.2) % len(chords)
            beat_pos = (t % 3.2) / 3.2
            chord = chords[bar]
            pad = 0.0
            for freq in chord:
                pad += math.sin(2 * math.pi * freq * t) * 0.18
                pad += math.sin(2 * math.pi * freq * 2.0 * t) * 0.035
            bass_freq = chord[0] / 2.0
            bass_pulse = 0.55 + 0.45 * math.sin(2 * math.pi * 0.625 * t)
            bass = math.sin(2 * math.pi * bass_freq * t) * 0.36 * bass_pulse
            step = int((t * 2.5) % len(motif))
            note_env = max(0.0, 1.0 - ((t * 2.5) % 1.0) * 2.4)
            melody = math.sin(2 * math.pi * motif[step] * t) * 0.16 * note_env
            resolve = math.sin(2 * math.pi * 880.0 * t) * 0.035 if beat_pos > 0.78 else 0.0
            breath = random.uniform(-1.0, 1.0) * 0.008
            env = min(1.0, t / 0.7, (duration - t) / 0.7)
            v = (pad + bass + melody + resolve + breath) * env
            left = _clamp_sample(v * 0.90 * _MAX_I16)
            right = _clamp_sample((v * 0.82 + melody * 0.22) * _MAX_I16)
            samples.append(left)
            samples.append(right)
        return self._make_sound(samples)

    def _texture_loop(self, name):
        duration = 4.0
        n = max(1, int(_SAMPLE_RATE * duration))
        samples = array("h")
        car_events = [0.35, 1.9, 3.15]
        bird_events = [0.7, 2.55, 3.55]
        bell_events = [1.2]
        for i in range(n):
            t = i / _SAMPLE_RATE
            v = 0.0
            if name == "calle":
                low = math.sin(2 * math.pi * 45 * t) * 0.10
                roll = math.sin(2 * math.pi * (65 + 10 * math.sin(t * 1.7)) * t) * 0.07
                v += low + roll + random.uniform(-1.0, 1.0) * 0.018
                for ev in car_events:
                    d = abs((t - ev + duration / 2) % duration - duration / 2)
                    if d < 0.42:
                        v += math.sin(2 * math.pi * (80 + 160 * d) * t) * (0.16 * (1.0 - d / 0.42))
                for ev in bird_events:
                    d = abs((t - ev + duration / 2) % duration - duration / 2)
                    if d < 0.09:
                        chirp_freq = 2100 + 900 * math.sin(80 * d)
                        v += math.sin(2 * math.pi * chirp_freq * t) * (0.12 * (1.0 - d / 0.09))
            elif name == "estudiantes":
                murmur = 0.0
                for freq in (180, 230, 310, 370, 460, 520):
                    murmur += math.sin(2 * math.pi * (freq + 6 * math.sin(t * 2.0)) * t)
                v += murmur * 0.018 + random.uniform(-1.0, 1.0) * 0.035
                for ev in bell_events:
                    d = abs((t - ev + duration / 2) % duration - duration / 2)
                    if d < 0.18:
                        v += math.sin(2 * math.pi * 880 * t) * 0.06 * (1.0 - d / 0.18)
            elif name == "cafeteria_detalle":
                v += random.uniform(-1.0, 1.0) * 0.045
                v += math.sin(2 * math.pi * 620 * t) * 0.018 * (1.0 if int(t * 4) % 5 == 0 else 0.0)
            elif name == "biblioteca_detalle":
                v += random.uniform(-1.0, 1.0) * 0.012
                if int(t * 1.5) % 5 == 0:
                    v += math.sin(2 * math.pi * 140 * t) * 0.018
            else:
                v += random.uniform(-1.0, 1.0) * 0.01
            env = min(1.0, t / 0.3, (duration - t) / 0.3)
            s = _clamp_sample(v * env * _MAX_I16)
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
            if nombre == MAIN_THEME:
                sound = self._main_theme_loop()
            else:
                sound = self._main_theme_loop()
            self._bgm_fallback_cache[nombre] = sound
        if sound is None:
            return
        try:
            sound.set_volume(self._volume * 0.36)
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
        self.play_bgm(MAIN_THEME)
        self.play_sfx("decision_tension", 0.7)

    def play_ending_bgm(self, final_key):
        self.play_bgm(MAIN_THEME)
        self.play_sfx("final_luz" if "POSITIVO" in final_key else "final_sombra", 0.85)

    # Ambientes por mapa

    def ambience_name_for_map(self, map_name):
        base = os.path.basename(str(map_name)).lower()
        if "calle" in base:
            return "calle"
        if any(k in base for k in ("patio", "azotea", "atras", "atr", "piscina")):
            return "exterior_colegio"
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

    def detail_name_for_map(self, map_name, has_students=False):
        ambience = self.ambience_name_for_map(map_name)
        if ambience == "calle":
            return "calle"
        if ambience in ("colegio", "exterior_colegio") and has_students:
            return "estudiantes"
        if ambience == "cafeteria":
            return "cafeteria_detalle"
        if ambience == "biblioteca":
            return "biblioteca_detalle"
        return None

    def play_ambience_for_map(self, map_name, has_students=False):
        name = self.ambience_name_for_map(map_name)
        if not self._initialized or self._current_ambience_name == name:
            self._play_detail_for_map(map_name, has_students)
            return
        if self._ambience_channel is None:
            return
        sound = self._ambience_cache.get(name)
        if sound is None:
            if name == "calle":
                sound = self._noise_loop(duration=3.2, volume=0.09, tone=72)
            elif name == "exterior_colegio":
                sound = self._noise_loop(duration=3.0, volume=0.075, tone=118)
            elif name == "cafeteria":
                sound = self._noise_loop(duration=2.6, volume=0.105, tone=90)
            elif name == "bano":
                sound = self._noise_loop(duration=2.8, volume=0.07, tone=180)
            elif name == "biblioteca":
                sound = self._noise_loop(duration=3.4, volume=0.045, tone=75)
            elif name == "habitacion_noche":
                sound = self._noise_loop(duration=3.4, volume=0.035, tone=55)
            elif name == "habitacion":
                sound = self._noise_loop(duration=3.2, volume=0.045, tone=70)
            else:
                sound = self._noise_loop(duration=2.8, volume=0.055 if not has_students else 0.07, tone=100)
            self._ambience_cache[name] = sound
        if sound is None:
            return
        try:
            sound.set_volume(self._volume * 0.35)
            self._ambience_channel.play(sound, -1, 0, 500)
            self._current_ambience_name = name
        except Exception:
            pass
        self._play_detail_for_map(map_name, has_students)

    def _play_detail_for_map(self, map_name, has_students=False):
        detail = self.detail_name_for_map(map_name, has_students)
        if detail == self._current_detail_name:
            return
        if self._detail_channel is None:
            self._current_detail_name = detail
            return
        if detail is None:
            try:
                self._detail_channel.fadeout(350)
            except Exception:
                pass
            self._current_detail_name = None
            return
        sound = self._detail_cache.get(detail)
        if sound is None:
            sound = self._texture_loop(detail)
            self._detail_cache[detail] = sound
        if sound is None:
            return
        try:
            sound.set_volume(self._volume * (0.26 if detail == "estudiantes" else 0.30))
            self._detail_channel.play(sound, -1, 0, 500)
            self._current_detail_name = detail
        except Exception:
            pass

    def stop_ambience(self, fade_ms=350):
        if self._ambience_channel is not None:
            try:
                self._ambience_channel.fadeout(fade_ms)
            except Exception:
                pass
        if self._detail_channel is not None:
            try:
                self._detail_channel.fadeout(fade_ms)
            except Exception:
                pass
        self._current_ambience_name = None
        self._current_detail_name = None

    # SFX

    def _generate_sfx(self, nombre):
        if nombre in self._generated_cache:
            return self._generated_cache[nombre]
        specs = {
            "click_boton": lambda: self._tone([680, 920], 0.055, 0.28, "square"),
            "hover_boton": lambda: self._tone(880, 0.035, 0.16, "sine"),
            "guardar_partida": lambda: self._sweep(520, 980, 0.22, 0.32),
            "decision_tomada": lambda: self._tone([330, 494, 659], 0.22, 0.28, "triangle"),
            "decision_tension": lambda: self._tone([196, 233, 294], 0.40, 0.20, "triangle", noise=0.04),
            "final_luz": lambda: self._tone([392, 523, 659, 784], 0.70, 0.26, "sine"),
            "final_sombra": lambda: self._sweep(196, 110, 0.70, 0.22, noise=0.08),
            "logro_desbloqueado": lambda: self._tone([523, 659, 784], 0.45, 0.30, "sine"),
            "paso_suave": lambda: self._tone(105, 0.06, 0.13, "triangle", noise=0.50),
            "paso_firme": lambda: self._tone(86, 0.07, 0.17, "triangle", noise=0.55),
            "paso_exterior": lambda: self._tone(72, 0.075, 0.14, "triangle", noise=0.72),
            "paso_madera": lambda: self._tone(132, 0.065, 0.14, "triangle", noise=0.40),
            "puerta": lambda: self._sweep(140, 70, 0.36, 0.24, noise=0.42),
            "interactuar": lambda: self._tone([392, 587], 0.11, 0.18, "sine"),
            "sentarse": lambda: self._sweep(180, 90, 0.20, 0.20, noise=0.35),
            "dialogo_avanzar": lambda: self._tone(640, 0.035, 0.10, "triangle"),
            "error": lambda: self._sweep(220, 105, 0.18, 0.20, noise=0.18),
            "camara_foto": lambda: self._tone(980, 0.05, 0.30, "square", noise=0.72),
            "borrar": lambda: self._tone(180, 0.10, 0.18, "triangle", noise=0.75),
            "ropa_movimiento": lambda: self._tone(95, 0.06, 0.08, "triangle", noise=0.85),
            "lapiz": lambda: self._tone(240, 0.08, 0.10, "triangle", noise=0.80),
            "madera": lambda: self._tone(165, 0.09, 0.18, "triangle", noise=0.48),
            "armario": lambda: self._sweep(125, 75, 0.28, 0.24, noise=0.38),
            "tela": lambda: self._tone(78, 0.12, 0.12, "triangle", noise=0.82),
            "balon": lambda: self._sweep(110, 70, 0.12, 0.30, noise=0.18),
            "maquina": lambda: self._tone([220, 440], 0.22, 0.20, "square", noise=0.20),
            "npc": lambda: self._tone([360, 480], 0.10, 0.12, "triangle"),
            "burla": lambda: self._sweep(700, 460, 0.22, 0.15),
            "pupitre_alerta": lambda: self._tone([196, 247, 294], 0.40, 0.20, "triangle"),
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

    def play_sfx(self, nombre, volume_scale=1.0, cooldown_ms=0):
        if cooldown_ms > 0:
            now = pygame.time.get_ticks()
            last = self._last_named_sfx_ms.get(nombre, -cooldown_ms)
            if now - last < cooldown_ms:
                return
            self._last_named_sfx_ms[nombre] = now
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
        if ambience in ("calle", "exterior_colegio"):
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
            if self._detail_channel is not None:
                self._detail_channel.set_volume(self._volume * 0.28)
            if self._bgm_fallback_channel is not None:
                self._bgm_fallback_channel.set_volume(self._volume * 0.36)
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

    def sfx_animation(self, animation_name):
        lowered = str(animation_name).lower()
        if "dibuj" in lowered or "write" in lowered:
            self.play_sfx("lapiz", 0.55, cooldown_ms=260)
        elif "walk" in lowered or "camin" in lowered or "run" in lowered:
            self.play_sfx("ropa_movimiento", 0.45, cooldown_ms=260)
        elif "sent" in lowered or "seat" in lowered:
            self.play_sfx("sentarse", 0.7, cooldown_ms=450)
        else:
            self.play_sfx("ropa_movimiento", 0.35, cooldown_ms=320)

    def sfx_object(self, object_name):
        lowered = str(object_name).lower()
        for key, sfx_name in SFX_ALIASES.items():
            if key in lowered:
                self.play_sfx(sfx_name)
                return
        self.sfx_interactuar()
