"""
GameplayBase — clase base abstracta para todos los minijuegos de EmpatiaQuest.

Interfaz publica estandar (igual que dia5_pelea_manager.py):
    mgr.handle_event(event)       → procesa input del jugador
    mgr.update(dt_ms)             → actualiza logica cada frame
    mgr.draw(screen, fonts)       → renderiza el minijuego
    mgr.result                    → None mientras juega; dict al terminar:
                                    {"gano": bool, "tipo": str}

Subclases deben implementar:
    tipo          (str)  — identificador del minijuego
    _intro_lines  ()     → list[str]  — texto de la pantalla de intro
    _update_playing(dt_ms)           — logica de juego
    _draw_playing(screen)            — render del estado jugando

Helpers disponibles para subclases:
    _draw_timer_bar(screen, elapsed_ms, total_ms, x, y, w, h)
    _draw_hp_hearts(screen, hp, max_hp, x, y)
    _draw_key_hint(screen, text, x, y)
    _end_win()   — llama cuando el jugador gana
    _end_lose()  — llama cuando el jugador pierde
"""
from __future__ import annotations
import pygame

# ── Colores del sistema de HUD compartido ─────────────────────────────────────
_HP_COLOR    = (255,  60,  80)
_TIMER_OK    = (100, 200, 100)
_TIMER_WARN  = (255, 160,  40)
_TIMER_CRIT  = (220,  60,  60)
_WIN_COLOR   = (100, 255, 130)
_LOSE_COLOR  = (255,  80,  80)
_PANEL_BG    = (10,   14,  22, 215)
_HINT_COLOR  = (170, 170, 180)

# Tiempo (ms) que el jugador ve la pantalla de resultado antes del auto-avance
_RESULT_SHOW_MS = 3800


class GameplayBase:
    """
    Clase base para minijuegos. Gestiona ciclo de vida, HUD compartido
    y transicion resultado→finalizacion.

    No instanciar directamente — usar subclases concretas.
    """

    tipo: str = "base"

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.audio    = audio
        self.result: dict | None = None

        # Ciclo de vida: "intro" → "playing" → "win"/"lose" → (result set)
        self.phase        = "intro"
        self._intro_ms    = 2200    # duracion de la pantalla de intro
        self._result_ms   = _RESULT_SHOW_MS

        # Fuentes (se resuelven en la primera llamada a draw)
        self._font_sm: pygame.font.Font | None = None
        self._font_md: pygame.font.Font | None = None
        self._font_lg: pygame.font.Font | None = None

    # ── Fuentes ───────────────────────────────────────────────────────────────

    def _init_fonts(self, fonts: dict) -> None:
        if self._font_sm is not None:
            return
        try:
            self._font_sm = fonts.get("small")  or pygame.font.SysFont("monospace", 13)
            self._font_md = fonts.get("medium") or pygame.font.SysFont("monospace", 20)
            self._font_lg = fonts.get("title")  or pygame.font.SysFont("monospace", 28)
        except Exception:
            self._font_sm = pygame.font.Font(None, 15)
            self._font_md = pygame.font.Font(None, 22)
            self._font_lg = pygame.font.Font(None, 32)

    # ── Interface publica ─────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.phase in ("win", "lose"):
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN, pygame.K_e, pygame.K_SPACE
            ):
                self._finalize()
                return
        self._on_event(event)

    def update(self, dt_ms: float) -> None:
        if self.phase == "intro":
            self._intro_ms -= dt_ms
            if self._intro_ms <= 0:
                self.phase = "playing"
                self._on_start()
        elif self.phase == "playing":
            self._update_playing(dt_ms)
        elif self.phase in ("win", "lose"):
            self._result_ms -= dt_ms
            if self._result_ms <= 0:
                self._finalize()

    def draw(self, screen: pygame.Surface, fonts: dict) -> None:
        self._init_fonts(fonts)
        self._draw_base_overlay(screen)

        if self.phase == "intro":
            self._draw_intro(screen)
        elif self.phase == "playing":
            self._draw_playing(screen)
        elif self.phase in ("win", "lose"):
            self._draw_playing(screen)
            self._draw_result_banner(screen, won=(self.phase == "win"))

    # ── Hooks para subclases ──────────────────────────────────────────────────

    def _on_event(self, event: pygame.event.Event) -> None:
        """Subclases sobreescriben esto para procesar input durante 'playing'."""

    def _on_start(self) -> None:
        """Se llama una vez al pasar de 'intro' a 'playing'."""

    def _update_playing(self, dt_ms: float) -> None:
        raise NotImplementedError(f"{type(self).__name__} debe implementar _update_playing")

    def _draw_playing(self, screen: pygame.Surface) -> None:
        raise NotImplementedError(f"{type(self).__name__} debe implementar _draw_playing")

    def _intro_lines(self) -> list[str]:
        """Lineas mostradas durante la pantalla de intro. Subclases sobreescriben."""
        return ["¡Preparate!"]

    # ── Transiciones de estado ────────────────────────────────────────────────

    def _end_win(self, sfx: str = "minijuego_ganar") -> None:
        if self.phase != "playing":
            return
        self.phase = "win"
        self._result_ms = _RESULT_SHOW_MS
        if self.audio:
            try:
                self.audio.play_sfx(sfx)
            except Exception:
                pass

    def _end_lose(self, sfx: str = "minijuego_perder") -> None:
        if self.phase != "playing":
            return
        self.phase = "lose"
        self._result_ms = _RESULT_SHOW_MS
        if self.audio:
            try:
                self.audio.play_sfx(sfx)
            except Exception:
                pass

    def _finalize(self) -> None:
        if self.result is None:
            self.result = {"gano": self.phase == "win", "tipo": self.tipo}

    # ── HUD helpers compartidos ───────────────────────────────────────────────

    def _draw_base_overlay(self, screen: pygame.Surface) -> None:
        """Oscurece el fondo del mundo para dar foco al minijuego."""
        ov = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        screen.blit(ov, (0, 0))

    def _draw_intro(self, screen: pygame.Surface) -> None:
        lines = self._intro_lines()
        cx = self.screen_w // 2
        cy = self.screen_h // 2 - (len(lines) * 18)
        for i, line in enumerate(lines):
            if not line:
                cy += 14
                continue
            font = self._font_lg if i == 0 else self._font_sm
            if font is None:
                cy += 28
                continue
            color = (235, 235, 235) if i == 0 else (190, 195, 210)
            surf = font.render(line, True, color)
            screen.blit(surf, (cx - surf.get_width() // 2, cy))
            cy += surf.get_height() + 10

    def _draw_timer_bar(
        self, screen: pygame.Surface,
        elapsed_ms: float, total_ms: float,
        x: int, y: int, w: int, h: int = 7,
    ) -> None:
        """Barra de tiempo decreciente. Color cambia segun urgencia."""
        ratio = max(0.0, min(1.0, 1.0 - elapsed_ms / max(1.0, total_ms)))
        pygame.draw.rect(screen, (38, 38, 58), (x, y, w, h))
        if ratio > 0:
            color = _TIMER_OK if ratio > 0.40 else (_TIMER_WARN if ratio > 0.18 else _TIMER_CRIT)
            pygame.draw.rect(screen, color, (x, y, int(w * ratio), h))
        pygame.draw.rect(screen, (80, 80, 100), (x, y, w, h), 1)

    def _draw_hp_hearts(
        self, screen: pygame.Surface,
        hp: int, max_hp: int,
        x: int, y: int,
    ) -> None:
        fn = self._font_sm
        if fn is None:
            return
        hp_str = ("♥" * max(0, hp)) + ("♡" * max(0, max_hp - hp))
        surf = fn.render(hp_str, True, _HP_COLOR)
        screen.blit(surf, (x, y))

    def _draw_key_hint(
        self, screen: pygame.Surface,
        text: str, x: int, y: int,
        centered: bool = True,
    ) -> None:
        fn = self._font_sm
        if fn is None:
            return
        surf = fn.render(text, True, _HINT_COLOR)
        bx = x - surf.get_width() // 2 if centered else x
        screen.blit(surf, (bx, y))

    def _draw_result_banner(
        self, screen: pygame.Surface, won: bool,
        msg_win: str  = "¡Lo lograste!",
        msg_lose: str = "No fue suficiente...",
    ) -> None:
        """Panel semitransparente con mensaje de victoria/derrota."""
        pw, ph = 500, 96
        px = self.screen_w // 2 - pw // 2
        py = self.screen_h // 2 - ph // 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 185))
        screen.blit(panel, (px, py))
        color = _WIN_COLOR if won else _LOSE_COLOR
        msg   = msg_win if won else msg_lose
        if self._font_md:
            surf = self._font_md.render(msg, True, color)
            screen.blit(surf, (self.screen_w // 2 - surf.get_width() // 2, py + 16))
        if self._font_sm:
            hint = self._font_sm.render("E / ENTER para continuar", True, _HINT_COLOR)
            screen.blit(hint, (self.screen_w // 2 - hint.get_width() // 2, py + 58))
