"""
GrabarManager — Minijuego tipo 6: "Grabar".

Mecanica:
- El jugador apunta una "camara" (punto de mira) hacia zonas del evento
  que se destacan en pantalla.
- Debe mantener el enfoque sobre cada zona durante suficiente tiempo para
  capturarla (barra de captura por zona).
- La bateria del dispositivo baja lentamente y no se recarga.
- Ganar: capturar >= CAPTURAS_WIN zonas antes de quedarse sin bateria.
- Perder: bateria agotada con menos capturas de las requeridas.

Este minijuego representa la participacion pasiva/espectadora: grabar
sin intervenir directamente.

Integracion estandar (GameplayBase):
    mgr = GrabarManager(sw, sh, audio)
    mgr.handle_event(event); mgr.update(dt_ms); mgr.draw(screen, fonts)
    if mgr.result: ...   # {"gano": bool, "tipo": "grabar"}
"""
from __future__ import annotations
import math
import random
import pygame
from gameplay_base import GameplayBase

# ── Configuracion ─────────────────────────────────────────────────────────────
_BATERIA_MAX   = 100.0
_BATERIA_DECAY = 4.0          # %/s
_CAPTURA_SPEED = 55.0         # %/s al estar sobre la zona
_CAPTURA_DECAY = 20.0         # %/s al salir de la zona
_CAPTURA_WIN   = 100.0        # % para considerar zona capturada
_CAPTURAS_WIN  = 5            # zonas a capturar para ganar
_ZONA_R        = 55           # radio de zona objetivo
_SPAWN_EVERY   = 3500         # ms entre nuevas zonas
_MAX_ZONAS     = 3
_CURSOR_R      = 18

_BG_COL        = (10, 10, 20)
_ZONA_COL      = (255, 200, 60, 120)
_ZONA_CAP      = (80, 200, 130)
_CURSOR_COL    = (240, 240, 255)
_BAT_OK        = (80,  210, 100)
_BAT_WARN      = (255, 180,  40)
_BAT_CRIT      = (220,  50,  50)
_REC_COL       = (220,  40,  40)


class _Zona:
    def __init__(self, x: int, y: int) -> None:
        self.x         = x
        self.y         = y
        self.captura   = 0.0      # 0.0 → 100.0
        self.captured  = False
        self.pulse     = random.uniform(0, math.pi * 2)  # fase para animacion

    def update_pulse(self, dt: float) -> None:
        self.pulse = (self.pulse + dt * 2.8) % (math.pi * 2)


class GrabarManager(GameplayBase):
    """Minijuego de grabacion: apunta y captura zonas del evento."""

    tipo = "grabar"

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        super().__init__(screen_w, screen_h, audio)
        self._bateria       = _BATERIA_MAX
        self._zonas         : list[_Zona] = []
        self._captured_n    = 0
        self._spawn_timer   = 800.0
        self._elapsed_ms    = 0.0
        self._cursor_pos    = (screen_w // 2, screen_h // 2)
        self._recording     = True  # siempre grabando (camara activa)
        self._rec_blink_ms  = 0.0

    # ── Hooks ────────────────────────────────────────────────────────────────

    def _intro_lines(self) -> list[str]:
        return [
            "Grabar",
            "",
            "Apunta la camara (raton) hacia las zonas iluminadas.",
            "Manten el enfoque para capturarlas.",
            f"Captura {_CAPTURAS_WIN} zonas antes de quedarte sin bateria.",
        ]

    def _on_event(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            self._cursor_pos = pygame.mouse.get_pos()

    def _update_playing(self, dt_ms: float) -> None:
        self._elapsed_ms += dt_ms
        dt = dt_ms / 1000.0

        # Bateria
        self._bateria = max(0.0, self._bateria - _BATERIA_DECAY * dt)
        if self._bateria <= 0.0:
            if self._captured_n >= _CAPTURAS_WIN:
                self._end_win()
            else:
                self._end_lose()
            return

        # Blink rec
        self._rec_blink_ms += dt_ms

        # Zonas
        mx, my = self._cursor_pos
        for z in self._zonas:
            if z.captured:
                continue
            z.update_pulse(dt)
            dist = math.hypot(mx - z.x, my - z.y)
            if dist <= _ZONA_R:
                z.captura = min(_CAPTURA_WIN, z.captura + _CAPTURA_SPEED * dt)
                if z.captura >= _CAPTURA_WIN:
                    z.captured = True
                    self._captured_n += 1
                    if self.audio:
                        try:
                            self.audio.play_sfx("camara_foto", 0.5)
                        except Exception:
                            pass
                    if self._captured_n >= _CAPTURAS_WIN:
                        self._end_win()
                        return
            else:
                z.captura = max(0.0, z.captura - _CAPTURA_DECAY * dt)

        # Spawn
        self._spawn_timer -= dt_ms
        if self._spawn_timer <= 0:
            self._try_spawn()
            self._spawn_timer = _SPAWN_EVERY

    def _try_spawn(self) -> None:
        activas = [z for z in self._zonas if not z.captured]
        if len(activas) >= _MAX_ZONAS:
            return
        margin = _ZONA_R + 60
        x = random.randint(margin, self.screen_w  - margin)
        y = random.randint(margin, self.screen_h  - margin)
        self._zonas.append(_Zona(x, y))

    # ── Render ────────────────────────────────────────────────────────────────

    def _draw_playing(self, screen: pygame.Surface) -> None:
        # Fondo
        bg = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        bg.fill((*_BG_COL, 245))
        screen.blit(bg, (0, 0))

        # Visor de camara (bordes redondeados con vigneteo)
        self._draw_vignette(screen)

        # Zonas objetivo
        zs = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        for z in self._zonas:
            if z.captured:
                # Zona capturada: icono de check verde
                pygame.draw.circle(zs, (*_ZONA_CAP, 120), (z.x, z.y), _ZONA_R // 2)
                fn = self._font_sm
                if fn:
                    t = fn.render("OK", True, _ZONA_CAP)
                    zs.blit(t, (z.x - t.get_width() // 2, z.y - t.get_height() // 2))
                continue
            # Pulso: radio oscila
            pulse_r = _ZONA_R + int(math.sin(z.pulse) * 6)
            a = int(80 + 50 * math.sin(z.pulse))
            pygame.draw.circle(zs, (*_ZONA_COL[:3], a), (z.x, z.y), pulse_r)
            pygame.draw.circle(zs, (255, 220, 100, 180), (z.x, z.y), pulse_r, 2)
            # Barra de captura
            if z.captura > 0:
                arc_rect = pygame.Rect(z.x - pulse_r, z.y - pulse_r,
                                       pulse_r * 2, pulse_r * 2)
                arc_angle = int((z.captura / _CAPTURA_WIN) * 360)
                pygame.draw.arc(zs, (*_ZONA_CAP, 220), arc_rect,
                                math.radians(90), math.radians(90 + arc_angle), 4)
        screen.blit(zs, (0, 0))

        # Cursor de camara (mira)
        mx, my = self._cursor_pos
        cur = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        r = _CURSOR_R
        pygame.draw.circle(cur, (*_CURSOR_COL, 180), (mx, my), r, 1)
        pygame.draw.line(cur, (*_CURSOR_COL, 180), (mx - r - 6, my), (mx + r + 6, my), 1)
        pygame.draw.line(cur, (*_CURSOR_COL, 180), (mx, my - r - 6), (mx, my + r + 6), 1)
        screen.blit(cur, (0, 0))

        # HUD: bateria
        fn = self._font_sm
        bw, bh = 180, 16
        bx, by = self.screen_w - bw - 20, 18
        pygame.draw.rect(screen, (40, 42, 55), (bx, by, bw, bh))
        bat_fill = int(bw * self._bateria / _BATERIA_MAX)
        bat_col  = _BAT_OK if self._bateria > 50 else (_BAT_WARN if self._bateria > 25 else _BAT_CRIT)
        if bat_fill > 0:
            pygame.draw.rect(screen, bat_col, (bx, by, bat_fill, bh))
        pygame.draw.rect(screen, (100, 105, 120), (bx, by, bw, bh), 1)
        if fn:
            t = fn.render(f"Bateria: {int(self._bateria)}%", True, (200, 205, 220))
            screen.blit(t, (bx - t.get_width() - 8, by + 2))

        # HUD: capturas
        if fn:
            t = fn.render(f"Capturas: {self._captured_n}/{_CAPTURAS_WIN}", True, (200, 205, 220))
            screen.blit(t, (20, 18))

        # Indicador REC parpadeante
        rec_on = (self._rec_blink_ms // 600) % 2 == 0
        if rec_on and fn:
            rec_surf = fn.render("● REC", True, _REC_COL)
            screen.blit(rec_surf, (20, 42))

    def _draw_vignette(self, screen: pygame.Surface) -> None:
        """Efecto de visor de camara en los bordes."""
        w, h = self.screen_w, self.screen_h
        vs = pygame.Surface((w, h), pygame.SRCALPHA)
        thickness = 60
        for i in range(thickness):
            a = int(160 * (1.0 - i / thickness) ** 2)
            pygame.draw.rect(vs, (0, 0, 0, a), (i, i, w - i * 2, h - i * 2), 1)
        screen.blit(vs, (0, 0))
