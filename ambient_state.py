"""
AmbientStateManager — sistema de ambiente dinamico basado en Felicidad (F).

5 estados segun el rango de F:
    SERENO   F >= 70   calido, vivo, esperanzador
    ESTABLE  50 <= F   escuela normal, sin efectos
    LEVE     40 <= F   silencioso, grisaceo, leve incomodidad
    CRISIS   25 <= F   tenso, frio, lluvia, luces parpadeantes
    GRAVE    F < 25    oscuro, niebla, abandono, silencio pesado

Integracion minima:
    mgr = AmbientStateManager()
    # en _update_adventure():
    mgr.update(self.story_felicidad, dt_ms, self.width, self.height)
    # en _draw_adventure_screen() (despues del mundo, antes del HUD):
    mgr.draw(screen)
    # para audio:
    audio.set_felicidad_context(self.story_felicidad)
"""
from __future__ import annotations

import math
import random
import pygame

# ── Umbrales publicos (usados tambien en otros modulos) ───────────────────────
F_SERENO  = 70
F_ESTABLE = 50
F_LEVE    = 40
F_CRISIS  = 25


def get_ambient_state(f: int) -> str:
    """Retorna el nombre del estado ambiental para un valor de F dado."""
    if f >= F_SERENO:  return "SERENO"
    if f >= F_ESTABLE: return "ESTABLE"
    if f >= F_LEVE:    return "LEVE"
    if f >= F_CRISIS:  return "CRISIS"
    return "GRAVE"


# ── Parametros por estado ─────────────────────────────────────────────────────

# Overlay de tinte: (R, G, B, alpha_max) — None = sin overlay
_OVERLAY: dict[str, tuple | None] = {
    "SERENO":  (255, 210, 120, 38),   # dorado calido, sutil
    "ESTABLE": None,
    "LEVE":    (70,  82,  110, 42),   # gris-azulado suave
    "CRISIS":  (28,  34,   68, 80),   # azul-oscuro frio
    "GRAVE":   (10,  12,   28, 115),  # casi negro, muy frio
}

# Multiplicador de densidad NPC 0.0–1.0
_NPC_DENSITY: dict[str, float] = {
    "SERENO":  1.0,
    "ESTABLE": 0.85,
    "LEVE":    0.60,
    "CRISIS":  0.35,
    "GRAVE":   0.15,
}

# Escala de volumen del ambiente (relativo al volumen base)
_AMBIENCE_VOL: dict[str, float] = {
    "SERENO":  1.10,
    "ESTABLE": 1.00,
    "LEVE":    0.80,
    "CRISIS":  0.55,
    "GRAVE":   0.22,
}

_RAIN_STATES = {"CRISIS"}
_FOG_STATES  = {"GRAVE"}

# Velocidad de transicion de alpha en unidades/ms (aprox 1 unidad/frame a 60fps)
_ALPHA_SPEED = 0.058


class AmbientStateManager:
    """
    Gestiona el estado visual/ambiental del mundo segun el valor de F.

    El estado cambia suavemente mediante interpolacion lineal, evitando
    cambios bruscos entre umbrales.
    """

    def __init__(self) -> None:
        self._state     : str   = "ESTABLE"
        self._overlay_a : float = 0.0   # alpha actual del tinte base
        self._rain_a    : float = 0.0   # alpha lluvia  (objetivo: 75 en CRISIS)
        self._fog_a     : float = 0.0   # alpha niebla  (objetivo: 90 en GRAVE)
        self._flicker_cd: int   = 0     # ms hasta proximo parpadeo (CRISIS)
        self._drops     : list  = []    # gotas de lluvia activas
        self._fog_phase : float = 0.0   # fase de oscilacion de la niebla
        self._ready     : bool  = False

    # ── Consultas publicas ────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    def get_npc_density(self) -> float:
        """Multiplicador 0.0–1.0 para controlar cuantos NPCs aparecen."""
        return _NPC_DENSITY.get(self._state, 1.0)

    def get_ambience_volume_scale(self) -> float:
        """Escala de volumen para el sistema de audio ambiental."""
        return _AMBIENCE_VOL.get(self._state, 1.0)

    # ── Actualizacion (llamar cada frame) ─────────────────────────────────────

    def update(self, felicidad: int, dt_ms: float,
               screen_w: int, screen_h: int) -> None:
        self._state = get_ambient_state(felicidad)
        step = _ALPHA_SPEED * dt_ms

        # Tinte base
        target_a = self._target_overlay_alpha(felicidad)
        self._overlay_a = _lerp(self._overlay_a, target_a, step)

        # Lluvia (transicion mas lenta para suavidad)
        rain_t = 75.0 if self._state in _RAIN_STATES else 0.0
        self._rain_a = _lerp(self._rain_a, rain_t, step * 0.35)

        # Niebla (transicion aun mas lenta — efecto dramatico gradual)
        fog_t = 90.0 if self._state in _FOG_STATES else 0.0
        self._fog_a = _lerp(self._fog_a, fog_t, step * 0.20)

        # Particulas de lluvia
        if self._rain_a > 3:
            self._update_drops(dt_ms, screen_w, screen_h)
        elif self._drops:
            self._drops.clear()

        # Fase de la niebla (oscilacion lenta)
        self._fog_phase = (self._fog_phase + dt_ms * 0.00022) % (2 * math.pi)

        # Contador de parpadeo (solo en CRISIS)
        if self._state == "CRISIS":
            self._flicker_cd = max(0, self._flicker_cd - int(dt_ms))
        else:
            self._flicker_cd = 999

        self._ready = True

    def _target_overlay_alpha(self, f: int) -> float:
        """Calcula el alpha objetivo del tinte segun posicion dentro del estado."""
        p = _OVERLAY.get(self._state)
        if p is None:
            return 0.0
        max_a = float(p[3])
        if self._state == "SERENO":
            # Mas calido a medida que F sube de 70 a 100
            ratio = (f - F_SERENO) / max(1, 100 - F_SERENO)
        elif self._state == "LEVE":
            # Mas intenso cuanto mas cerca de 40
            ratio = 1.0 - (f - F_LEVE) / max(1, F_ESTABLE - F_LEVE)
        elif self._state == "CRISIS":
            # Mas intenso cuanto mas cerca de 25
            ratio = 1.0 - (f - F_CRISIS) / max(1, F_LEVE - F_CRISIS)
        elif self._state == "GRAVE":
            # Mas intenso cuanto mas cerca de 0
            ratio = 1.0 - f / max(1, F_CRISIS)
        else:
            return 0.0
        return max_a * max(0.0, min(1.0, ratio))

    # ── Lluvia ────────────────────────────────────────────────────────────────

    def _update_drops(self, dt_ms: float, sw: int, sh: int) -> None:
        density = max(15, int(55 * self._rain_a / 75.0))
        # Agregar gotas nuevas hasta alcanzar densidad
        while len(self._drops) < density:
            self._drops.append({
                "x":   float(random.randint(0, sw)),
                "y":   float(random.randint(-sh // 2, sh)),
                "spd": random.uniform(260, 440),
                "ln":  random.randint(5, 13),
                "a":   random.randint(65, 150),
            })
        # Mover gotas y eliminar las que salieron de pantalla
        dt = dt_ms / 1000.0
        kept = []
        for d in self._drops:
            d["x"] -= d["spd"] * 0.11 * dt
            d["y"] += d["spd"] * dt
            if d["y"] < sh + 20:
                kept.append(d)
        self._drops = kept

    # ── Dibujo (llamar despues del mundo, antes del HUD) ──────────────────────

    def draw(self, screen: pygame.Surface) -> None:
        """Dibuja los efectos de ambiente sobre el mundo ya renderizado."""
        if not self._ready:
            return
        w, h = screen.get_size()

        # 1. Overlay de tinte (calido/frio)
        if self._overlay_a > 0.5:
            p = _OVERLAY.get(self._state)
            if p:
                surf = pygame.Surface((w, h), pygame.SRCALPHA)
                surf.fill((p[0], p[1], p[2], int(self._overlay_a)))
                screen.blit(surf, (0, 0))

        # 2. Gotas de lluvia (CRISIS)
        if self._rain_a > 2 and self._drops:
            rs = pygame.Surface((w, h), pygame.SRCALPHA)
            scale = self._rain_a / 75.0
            for d in self._drops:
                a = int(d["a"] * scale)
                if a < 8:
                    continue
                x1, y1 = int(d["x"]), int(d["y"])
                pygame.draw.line(
                    rs, (175, 205, 255, a),
                    (x1, y1), (x1 - 1, y1 + d["ln"]), 1,
                )
            screen.blit(rs, (0, 0))

        # 3. Niebla en capas (GRAVE)
        if self._fog_a > 2:
            self._draw_fog(screen, w, h)

        # 4. Parpadeo electrico ocasional (CRISIS)
        if self._state == "CRISIS" and self._flicker_cd == 0:
            if random.random() < 0.004:
                fs = pygame.Surface((w, h), pygame.SRCALPHA)
                fs.fill((0, 0, 0, random.randint(22, 58)))
                screen.blit(fs, (0, 0))
                self._flicker_cd = random.randint(700, 2800)

    def _draw_fog(self, screen: pygame.Surface, w: int, h: int) -> None:
        """Dibuja capas de niebla en la parte inferior con oscilacion suave."""
        fs = pygame.Surface((w, h), pygame.SRCALPHA)
        a  = int(self._fog_a)
        for layer in range(4):
            band_h = int(h * 0.20)
            osc    = int(math.sin(self._fog_phase + layer * 1.1) * 5)
            base_y = h - band_h * (layer + 1) + osc
            band_a = max(0, a - layer * 20)
            if band_a < 2:
                continue
            fs.fill(
                (192, 202, 212, band_a),
                pygame.Rect(0, base_y, w, band_h + 4),
            )
        screen.blit(fs, (0, 0))


# ── Helpers privados del modulo ───────────────────────────────────────────────

def _lerp(current: float, target: float, step: float) -> float:
    """Interpolacion lineal con paso fijo (no overshoot)."""
    if current < target:
        return min(target, current + step)
    return max(target, current - step)
