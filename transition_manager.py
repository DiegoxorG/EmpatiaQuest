"""
Gestor de transiciones de pantalla para EmpatiaQuest.
Aplica un fade-out de 300 ms seguido de un fade-in al cambiar de pantalla.
Si no hay surface disponible, falla silenciosamente.
"""

import pygame
from config import TRANSITION_DURATION_MS


class TransitionManager:
    """
    Aplica fade-out → cambio de pantalla → fade-in en TRANSITION_DURATION_MS ms.

    Uso:
        # Solicitar un cambio con transición:
        game.transitions.request(game, "aventura")

        # En el loop principal, antes de flip():
        game.transitions.update(dt_ms)
        game.transitions.draw(game.screen)
    """

    def __init__(self):
        self._phase = "idle"      # idle | fade_out | fade_in
        self._elapsed = 0
        self._pending_screen = None
        self._pending_callback = None
        self._overlay = None      # pygame.Surface creada bajo demanda

    # ── API pública ───────────────────────────────────────────────────────────

    @property
    def active(self):
        return self._phase != "idle"

    def is_idle(self):
        return self._phase == "idle"

    def request(self, game, new_screen, callback=None):
        """
        Solicita una transición hacia new_screen.
        callback opcional se llama justo al completar el fade-out (antes del fade-in).
        Si ya hay una transición activa, la ignora.
        """
        if self._phase != "idle":
            return
        self._pending_screen = new_screen
        self._pending_callback = callback
        self._phase = "fade_out"
        self._elapsed = 0

    def update(self, game, dt_ms):
        """Avanza la transición. Debe llamarse cada frame."""
        if self._phase == "idle":
            return

        self._elapsed += dt_ms
        dur = TRANSITION_DURATION_MS

        if self._phase == "fade_out" and self._elapsed >= dur:
            # Momento de cambio de pantalla
            if self._pending_screen is not None:
                game.current_screen = self._pending_screen
            if self._pending_callback:
                self._pending_callback()
            self._phase = "fade_in"
            self._elapsed = 0

        elif self._phase == "fade_in" and self._elapsed >= dur:
            self._phase = "idle"
            self._elapsed = 0
            self._pending_screen = None
            self._pending_callback = None

    def draw(self, screen):
        """
        Dibuja el overlay de transición sobre el screen ya renderizado.
        Debe llamarse justo antes de pygame.display.flip().

        # 🎨 ASSET_UI: Imagenes/UI/transition_overlay.png | 1280x720 | Overlay negro para transición
        """
        if self._phase == "idle":
            return

        dur = TRANSITION_DURATION_MS
        progress = min(1.0, self._elapsed / max(1, dur))

        if self._phase == "fade_out":
            alpha = int(255 * progress)
        else:  # fade_in
            alpha = int(255 * (1.0 - progress))

        w, h = screen.get_size()
        if self._overlay is None or self._overlay.get_size() != (w, h):
            self._overlay = pygame.Surface((w, h))
            self._overlay.fill((0, 0, 0))

        self._overlay.set_alpha(alpha)
        screen.blit(self._overlay, (0, 0))
