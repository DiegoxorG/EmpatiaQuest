"""
ConsolacionManager — Minijuego tipo 5: "Consolar".

Mecanica:
- En pantalla aparece un personaje con una barra de estado emocional
  (estabilidad) que baja lentamente.
- Aparecen "momentos de apoyo": ventanas de tiempo en las que el jugador
  debe presionar la tecla correcta (A/B/C/D) para responder con empatia.
- Cada respuesta correcta sube la estabilidad; la incorrecta no hace nada
  (no penaliza, porque consolar nunca es "equivocarse gravemente").
- Ganar: llevar la estabilidad a ESTABILIDAD_MAX antes de que caiga a 0.
- Perder: estabilidad llega a 0.

Tono: musica suave, colores calidos, sin efectos agresivos.

Integracion estandar (GameplayBase):
    mgr = ConsolacionManager(sw, sh, audio)
    mgr.handle_event(event); mgr.update(dt_ms); mgr.draw(screen, fonts)
    if mgr.result: ...   # {"gano": bool, "tipo": "consolar"}
"""
from __future__ import annotations
import math
import random
import pygame
from gameplay_base import GameplayBase

# ── Configuracion ─────────────────────────────────────────────────────────────
_ESTAB_MAX    = 100.0
_ESTAB_INIT   = 30.0
_ESTAB_DECAY  = 2.8         # puntos/s que baja sola
_ESTAB_GAIN   = 28.0        # puntos que sube con respuesta correcta
_WIN_THRESH   = 95.0
_WINDOW_MS    = 3200        # ms que dura cada ventana de respuesta
_GAP_MS_MIN   = 1200        # tiempo minimo entre ventanas
_GAP_MS_MAX   = 2200
_NUM_PROMPTS  = 8           # cuantas ventanas deben aparecer para poder ganar

# Respuestas posibles (clave → texto mostrado)
_OPTIONS: list[tuple[str, str]] = [
    ("A", "Estoy aqui contigo"),
    ("B", "Te escucho"),
    ("C", "Tienes razon en sentirte asi"),
    ("D", "No estas solo/a"),
]
_KEY_MAP = {
    pygame.K_a: "A",
    pygame.K_b: "B",
    pygame.K_c: "C",
    pygame.K_d: "D",
}

# Colores
_BG_COL     = (20, 16, 32)
_ESTAB_OK   = (100, 200, 140)
_ESTAB_WARN = (255, 190,  50)
_ESTAB_CRIT = (220,  60,  60)
_CHAR_COL   = (200, 160, 240)
_WINDOW_COL = (60,  70,  90, 210)
_CORRECT_FX = (140, 240, 160)
_PANEL_W    = 540
_PANEL_H    = 360


class ConsolacionManager(GameplayBase):
    """Minijuego cooperativo de apoyo emocional."""

    tipo = "consolar"

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        super().__init__(screen_w, screen_h, audio)
        self._estab       = _ESTAB_INIT
        self._next_window = 500.0   # ms hasta la primera ventana
        self._window_open = False
        self._window_ms   = 0.0     # ms restantes en la ventana actual
        self._current_opt : str | None = None
        self._correct_key : str = ""
        self._prompts_seen = 0
        self._fx_timer    = 0.0     # ms de efecto visual de acierto
        self._fx_color    = _CORRECT_FX
        self._elapsed_ms  = 0.0
        self._char_y_off  = 0.0     # oscilacion del personaje

    # ── Hooks ────────────────────────────────────────────────────────────────

    def _intro_lines(self) -> list[str]:
        return [
            "Consolar",
            "",
            "Aparecera una ventana con opciones A B C D.",
            "Elige la respuesta empatica a tiempo.",
            "Sube la estabilidad emocional para ganar.",
        ]

    def _on_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if not self._window_open:
            return
        pressed = _KEY_MAP.get(event.key)
        if pressed is None:
            return
        if pressed == self._correct_key:
            self._estab = min(_ESTAB_MAX, self._estab + _ESTAB_GAIN)
            self._fx_timer = 600.0
            self._fx_color = _CORRECT_FX
            if self.audio:
                try:
                    self.audio.play_sfx("decision_tomada", 0.6)
                except Exception:
                    pass
        # Respuesta incorrecta: sin penalizacion, solo cierra la ventana
        self._window_open = False
        self._window_ms   = 0.0

    def _update_playing(self, dt_ms: float) -> None:
        self._elapsed_ms += dt_ms
        dt = dt_ms / 1000.0

        # Decaimiento de estabilidad
        self._estab = max(0.0, self._estab - _ESTAB_DECAY * dt)
        if self._estab <= 0.0:
            self._end_lose()
            return
        if self._estab >= _WIN_THRESH and self._prompts_seen >= _NUM_PROMPTS:
            self._end_win()
            return

        # Oscilacion del personaje (respiracion)
        self._char_y_off = math.sin(self._elapsed_ms / 900.0) * 5

        # Efecto visual de acierto
        if self._fx_timer > 0:
            self._fx_timer = max(0.0, self._fx_timer - dt_ms)

        # Ventana de respuesta abierta
        if self._window_open:
            self._window_ms -= dt_ms
            if self._window_ms <= 0:
                self._window_open = False
            return

        # Contar hacia la siguiente ventana
        self._next_window -= dt_ms
        if self._next_window <= 0:
            self._open_window()
            self._next_window = random.uniform(_GAP_MS_MIN, _GAP_MS_MAX)

    def _open_window(self) -> None:
        self._window_open = True
        self._window_ms   = _WINDOW_MS
        self._prompts_seen += 1
        self._correct_key = random.choice([o[0] for o in _OPTIONS])
        # Mezclar el orden de opciones mostradas
        shuffled = _OPTIONS[:]
        random.shuffle(shuffled)
        self._current_opts = shuffled

    # ── Render ────────────────────────────────────────────────────────────────

    def _draw_playing(self, screen: pygame.Surface) -> None:
        cx = self.screen_w // 2
        cy = self.screen_h // 2

        # Panel de fondo
        pw, ph = _PANEL_W, _PANEL_H
        px, py = cx - pw // 2, cy - ph // 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((*_BG_COL, 230))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (80, 80, 120), (px, py, pw, ph), 2)

        # Personaje (circulo con colores segun estabilidad)
        char_y = int(py + 80 + self._char_y_off)
        char_col = self._estab_color()
        pygame.draw.circle(screen, char_col, (cx, char_y), 28)
        pygame.draw.circle(screen, (240, 240, 250), (cx, char_y), 28, 2)
        # Expresion
        fn = self._font_sm
        if fn:
            expr = ":)" if self._estab > 60 else (":|" if self._estab > 30 else ":(")
            t = fn.render(expr, True, (20, 20, 30))
            screen.blit(t, (cx - t.get_width() // 2, char_y - t.get_height() // 2))

        # Barra de estabilidad
        bar_w, bar_h = 280, 16
        bx = cx - bar_w // 2
        by = py + 130
        pygame.draw.rect(screen, (40, 40, 60), (bx, by, bar_w, bar_h))
        fill = int(bar_w * self._estab / _ESTAB_MAX)
        if fill > 0:
            pygame.draw.rect(screen, char_col, (bx, by, fill, bar_h))
        pygame.draw.rect(screen, (100, 100, 130), (bx, by, bar_w, bar_h), 1)
        # Marca de victoria
        win_x = bx + int(bar_w * _WIN_THRESH / _ESTAB_MAX)
        pygame.draw.line(screen, (240, 220, 80), (win_x, by - 3), (win_x, by + bar_h + 3), 2)
        if fn:
            t = fn.render(f"Estabilidad: {int(self._estab)}%", True, (200, 200, 220))
            screen.blit(t, (cx - t.get_width() // 2, by + bar_h + 6))

        # Efecto de acierto
        if self._fx_timer > 0:
            a = int(120 * self._fx_timer / 600.0)
            fx_s = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            fx_s.fill((*self._fx_color, a))
            screen.blit(fx_s, (0, 0))

        # Ventana de respuesta
        if self._window_open:
            self._draw_response_window(screen, px, py, pw)

        # Instruccion si no hay ventana
        elif fn:
            t = fn.render("Espera el momento...", True, (130, 140, 160))
            screen.blit(t, (cx - t.get_width() // 2, py + ph - 34))

    def _draw_response_window(
        self, screen: pygame.Surface,
        px: int, py: int, pw: int,
    ) -> None:
        cx = px + pw // 2
        opts = getattr(self, "_current_opts", _OPTIONS)
        # Barra de tiempo de la ventana
        remaining = max(0.0, self._window_ms / _WINDOW_MS)
        bx = px + 20
        by = py + _PANEL_H - 50
        bw = pw - 40
        self._draw_timer_bar(screen, _WINDOW_MS - self._window_ms, _WINDOW_MS,
                             bx, by, bw, 5)

        # Opciones
        fn = self._font_sm
        if fn is None:
            return
        oy = py + _PANEL_H // 2 - 10
        for key, text in opts:
            highlight = (key == self._correct_key and remaining < 0.15)
            col = (240, 220, 100) if highlight else (210, 215, 235)
            t = fn.render(f"[{key}] {text}", True, col)
            screen.blit(t, (cx - t.get_width() // 2, oy))
            oy += 26

    def _estab_color(self) -> tuple:
        if self._estab >= 60:
            return _ESTAB_OK
        if self._estab >= 30:
            return _ESTAB_WARN
        return _ESTAB_CRIT
