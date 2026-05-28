"""
ParticiparManager — Minijuego tipo 7: "Participar" (en bullying).

Mecanica:
- Aparecen en pantalla mensajes/burlas que el grupo esta compartiendo.
- El jugador debe RECHAZARLOS presionando la tecla correcta (X/SPACE)
  cuando el mensaje esta resaltado, o IGNORARLOS (no hacer nada).
- Pero algunos mensajes son "trampa": aceptarlos sumaria puntos de presion
  social. El jugador debe discriminar: rechazar los daninos, dejar pasar
  los neutrales.
- Presion social: sube si el jugador no rechaza mensajes daninos o si
  rechaza mensajes neutros (por torpeza).
- Ganar: sobrevivir el tiempo sin que la presion social llegue al maximo.
- Perder: presion social al maximo.

Representa la tension de participar o resistir la presion del grupo.

Integracion estandar (GameplayBase):
    mgr = ParticiparManager(sw, sh, audio)
    mgr.handle_event(event); mgr.update(dt_ms); mgr.draw(screen, fonts)
    if mgr.result: ...   # {"gano": bool, "tipo": "participar"}
"""
from __future__ import annotations
import math
import random
import pygame
from gameplay_base import GameplayBase

# ── Configuracion ─────────────────────────────────────────────────────────────
_TIME_MS       = 22_000
_PRESION_MAX   = 100.0
_PRESION_DECAY = 1.2        # baja sola con el tiempo
_PRESION_FAIL  = 100.0      # perder si llega aqui
_WIN_SURVIVE   = True       # ganar = sobrevivir el tiempo

_MSG_WINDOW_MS   = 2400     # ms que el jugador tiene para reaccionar
_MSG_INTERVAL_MS = 2200     # ms entre mensajes

# Mensajes daninos → rechazar
_DANINOS = [
    "¡Miralo!", "Que asco", "Mandalo a...", "Enviarle foto",
    "Riete", "Comparte esto", "Siguelo", "Insultalo",
]
# Mensajes neutros → ignorar (NO rechazar)
_NEUTROS = [
    "¿Que haces?", "Hasta luego", "Ok", "Nos vemos",
    "Enviame el apunte", "¿Vienes mañana?",
]

_BG_COL       = (12, 10, 22)
_MSG_DAN_COL  = (220,  60,  60)
_MSG_NEU_COL  = (140, 160, 200)
_PRESION_COL  = (220,  50,  50)
_PRESION_OK   = (100, 200, 100)
_FX_RESIST    = (100, 220, 140)
_FX_FAIL      = (220,  80,  80)

_PANEL_W, _PANEL_H = 480, 200


class _Mensaje:
    def __init__(self, text: str, danino: bool) -> None:
        self.text      = text
        self.danino    = danino
        self.window_ms = _MSG_WINDOW_MS
        self.reacted   = False


class ParticiparManager(GameplayBase):
    """Minijuego de resistencia a la presion social."""

    tipo = "participar"

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        super().__init__(screen_w, screen_h, audio)
        self._presion      = 30.0
        self._elapsed_ms   = 0.0
        self._next_msg_ms  = 800.0
        self._mensaje      : _Mensaje | None = None
        self._fx_timer     = 0.0
        self._fx_col       = _FX_RESIST
        self._last_feedback: str = ""

    # ── Hooks ────────────────────────────────────────────────────────────────

    def _intro_lines(self) -> list[str]:
        return [
            "Resistir la presion",
            "",
            "Aparecen mensajes del grupo.",
            "Presiona X o ESPACIO para RECHAZAR los mensajes daninos.",
            "No hagas nada ante los mensajes neutros.",
            "No dejes que la presion social llegue al maximo.",
        ]

    def _on_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key not in (pygame.K_x, pygame.K_SPACE):
            return
        if self._mensaje is None or self._mensaje.reacted:
            return
        msg = self._mensaje
        msg.reacted = True
        if msg.danino:
            # Correcto: rechazar lo danino baja la presion
            self._presion = max(0.0, self._presion - 18.0)
            self._fx_timer = 550.0
            self._fx_col   = _FX_RESIST
            self._last_feedback = "¡Bien! Rechazaste lo dañino."
            if self.audio:
                try:
                    self.audio.play_sfx("decision_tomada", 0.6)
                except Exception:
                    pass
        else:
            # Error: rechazar algo neutro genera presion social
            self._presion = min(_PRESION_MAX, self._presion + 14.0)
            self._fx_timer = 450.0
            self._fx_col   = _FX_FAIL
            self._last_feedback = "Rechazaste algo inocente..."

    def _update_playing(self, dt_ms: float) -> None:
        self._elapsed_ms += dt_ms
        dt = dt_ms / 1000.0

        # Decaimiento natural de presion
        self._presion = max(0.0, self._presion - _PRESION_DECAY * dt)

        # Victoria por tiempo
        if self._elapsed_ms >= _TIME_MS:
            self._end_win()
            return

        # Derrota por presion
        if self._presion >= _PRESION_FAIL:
            self._end_lose()
            return

        # Efecto visual
        if self._fx_timer > 0:
            self._fx_timer = max(0.0, self._fx_timer - dt_ms)

        # Mensaje activo
        if self._mensaje is not None:
            self._mensaje.window_ms -= dt_ms
            if self._mensaje.window_ms <= 0 or self._mensaje.reacted:
                # Si el mensaje danino expiro sin ser rechazado → presion sube
                if not self._mensaje.reacted and self._mensaje.danino:
                    self._presion = min(_PRESION_MAX, self._presion + 22.0)
                    self._last_feedback = "No hiciste nada..."
                self._mensaje = None

        # Siguiente mensaje
        if self._mensaje is None:
            self._next_msg_ms -= dt_ms
            if self._next_msg_ms <= 0:
                self._spawn_mensaje()
                self._next_msg_ms = _MSG_INTERVAL_MS + random.uniform(-400, 400)

    def _spawn_mensaje(self) -> None:
        danino = random.random() < 0.55   # 55% daninos
        pool   = _DANINOS if danino else _NEUTROS
        self._mensaje = _Mensaje(random.choice(pool), danino)

    # ── Render ────────────────────────────────────────────────────────────────

    def _draw_playing(self, screen: pygame.Surface) -> None:
        cx, cy = self.screen_w // 2, self.screen_h // 2

        # Fondo
        bg = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        bg.fill((*_BG_COL, 240))
        screen.blit(bg, (0, 0))

        # Efecto de flash
        if self._fx_timer > 0:
            a = int(80 * self._fx_timer / 550.0)
            fs = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            fs.fill((*self._fx_col, a))
            screen.blit(fs, (0, 0))

        # Panel del mensaje
        px, py = cx - _PANEL_W // 2, cy - _PANEL_H // 2 - 20
        panel = pygame.Surface((_PANEL_W, _PANEL_H), pygame.SRCALPHA)
        panel.fill((18, 20, 36, 230))
        screen.blit(panel, (px, py))

        if self._mensaje is not None:
            msg = self._mensaje
            # Color segun tipo
            col = _MSG_DAN_COL if msg.danino else _MSG_NEU_COL
            # Pulso de urgencia para mensajes daninos
            if msg.danino:
                pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() / 200.0)
                a = int(255 * pulse)
            else:
                a = 210
            fn = self._font_md
            if fn:
                surf = fn.render(f'"{msg.text}"', True, col)
                surf.set_alpha(a)
                screen.blit(surf, (cx - surf.get_width() // 2, py + 44))

            # Barra de tiempo de reaccion
            elapsed_w = _MSG_WINDOW_MS - msg.window_ms
            self._draw_timer_bar(
                screen, elapsed_w, _MSG_WINDOW_MS,
                px + 20, py + _PANEL_H - 30, _PANEL_W - 40, 6,
            )

            # Indicacion de accion
            fn_sm = self._font_sm
            if fn_sm:
                if msg.danino:
                    hint = "[ X ] o [ ESPACIO ] para rechazar"
                    hcol = (220, 120, 120)
                else:
                    hint = "No hagas nada (mensaje neutro)"
                    hcol = (130, 150, 190)
                ht = fn_sm.render(hint, True, hcol)
                screen.blit(ht, (cx - ht.get_width() // 2, py + _PANEL_H - 52))
        else:
            fn = self._font_sm
            if fn:
                t = fn.render("Esperando mensaje...", True, (100, 110, 140))
                screen.blit(t, (cx - t.get_width() // 2, cy - 10))

        # Feedback de ultima accion
        if self._last_feedback and self._font_sm:
            a = min(255, int(self._fx_timer * 1.5)) if self._fx_timer > 0 else 60
            surf = self._font_sm.render(self._last_feedback, True, self._fx_col)
            surf.set_alpha(a)
            screen.blit(surf, (cx - surf.get_width() // 2, py - 30))

        # HUD: barra de presion social
        fn_sm = self._font_sm
        bw, bh = 320, 16
        bx = cx - bw // 2
        by = cy + _PANEL_H // 2 + 20
        pygame.draw.rect(screen, (35, 35, 55), (bx, by, bw, bh))
        fill = int(bw * self._presion / _PRESION_MAX)
        pcol = _PRESION_OK if self._presion < 50 else (_MSG_DAN_COL if self._presion < 75 else _PRESION_COL)
        if fill > 0:
            pygame.draw.rect(screen, pcol, (bx, by, fill, bh))
        pygame.draw.rect(screen, (80, 84, 108), (bx, by, bw, bh), 1)
        if fn_sm:
            t = fn_sm.render(f"Presion social: {int(self._presion)}%", True, (190, 195, 215))
            screen.blit(t, (cx - t.get_width() // 2, by + bh + 4))

        # Temporizador
        remaining = max(0.0, (_TIME_MS - self._elapsed_ms) / 1000.0)
        self._draw_timer_bar(
            screen, self._elapsed_ms, _TIME_MS,
            20, self.screen_h - 28, self.screen_w - 40, 5,
        )
        if fn_sm:
            t = fn_sm.render(f"{remaining:.0f}s", True, (160, 165, 185))
            screen.blit(t, (self.screen_w - t.get_width() - 20, self.screen_h - 28))
