"""
BuscarDocenteManager — Minijuego tipo 1: "Buscar al docente".

Mecanica:
- El jugador controla un corazon (igual que dia5_pelea_manager) dentro de
  un pasillo simplificado de la escuela.
- Debe llegar hasta el icono del docente antes de que expire el tiempo.
- La musica se acelera conforme pasa el tiempo.
- Una flecha guia apunta siempre hacia el docente.

Controles: flechas / WASD para moverse.
Ganar:     alcanzar la zona del docente a tiempo.
Perder:    tiempo agotado.

Integracion estandar (GameplayBase):
    mgr = BuscarDocenteManager(sw, sh, audio)
    mgr.handle_event(event)
    mgr.update(dt_ms)
    mgr.draw(screen, fonts)
    if mgr.result: ...   # {"gano": bool, "tipo": "buscar_docente"}
"""
from __future__ import annotations
import math
import random
import pygame
from gameplay_base import GameplayBase

# ── Configuracion ─────────────────────────────────────────────────────────────
_ARENA_W    = 500
_ARENA_H    = 320
_PLAYER_SPD = 195       # px/s
_PLAYER_R   = 10        # radio del corazon jugador
_DOC_R      = 22        # radio zona de llegada del docente
_TIME_MS    = 18_000    # 18 segundos para llegar

_BG_COLOR   = (18, 14, 32)
_WALL_COLOR = (42, 44, 66)
_PLAYER_COL = (220, 40,  60)
_DOC_COL    = (90, 200, 130)
_DOC_ICON   = (220, 240, 220)
_GUIDE_COL  = (255, 220, 80)
_TIMER_WARN = 6_000     # ms restantes para cambio de color


class BuscarDocenteManager(GameplayBase):
    """Minijuego de carrera con temporizador para encontrar al docente."""

    tipo = "buscar_docente"

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        super().__init__(screen_w, screen_h, audio)

        self.arena = pygame.Rect(
            (screen_w - _ARENA_W) // 2,
            (screen_h - _ARENA_H) // 2 + 10,
            _ARENA_W,
            _ARENA_H,
        )

        # Posicion inicial del jugador (esquina izquierda del arena)
        self._px = float(self.arena.left + _PLAYER_R * 3)
        self._py = float(self.arena.centery)

        # Posicion del docente (esquina opuesta, con un poco de variacion)
        margin = _DOC_R + 8
        self._dx = float(self.arena.right  - margin)
        self._dy = float(self.arena.top    + margin + random.randint(0, _ARENA_H - margin * 2))

        # Obstaculos (pupitres simplificados)
        self._walls: list[pygame.Rect] = self._gen_walls()

        self._elapsed_ms = 0.0
        self._keys: set[int] = set()
        self._found = False

    # ── Obstaculos procedurales ───────────────────────────────────────────────

    def _gen_walls(self) -> list[pygame.Rect]:
        walls = []
        cols, rows = 3, 2
        cw = _ARENA_W // (cols + 1)
        rh = _ARENA_H // (rows + 2)
        for r in range(rows):
            for c in range(cols):
                x = self.arena.left + cw * (c + 1) - 18
                y = self.arena.top  + rh * (r + 1) + 10
                rect = pygame.Rect(x, y, 36, 22)
                # No bloquear inicio ni llegada
                if rect.collidepoint(self._px, self._py):
                    continue
                if rect.collidepoint(self._dx, self._dy):
                    continue
                walls.append(rect)
        return walls

    # ── Hooks ────────────────────────────────────────────────────────────────

    def _intro_lines(self) -> list[str]:
        t = int(_TIME_MS / 1000)
        return [
            "¡Busca al docente!",
            "",
            "Corre hasta el docente antes de que acabe el tiempo.",
            f"Tienes {t} segundos.  Flechas / WASD para moverte.",
        ]

    def _on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._keys.add(event.key)
        elif event.type == pygame.KEYUP:
            self._keys.discard(event.key)

    def _update_playing(self, dt_ms: float) -> None:
        self._elapsed_ms += dt_ms
        if self._elapsed_ms >= _TIME_MS:
            self._end_lose()
            return

        dt = dt_ms / 1000.0
        vx, vy = 0.0, 0.0
        if pygame.K_LEFT  in self._keys or pygame.K_a in self._keys: vx -= _PLAYER_SPD
        if pygame.K_RIGHT in self._keys or pygame.K_d in self._keys: vx += _PLAYER_SPD
        if pygame.K_UP    in self._keys or pygame.K_w in self._keys: vy -= _PLAYER_SPD
        if pygame.K_DOWN  in self._keys or pygame.K_s in self._keys: vy += _PLAYER_SPD

        # Mover con colision contra paredes y bordes del arena
        nx = self._px + vx * dt
        ny = self._py + vy * dt

        m = _PLAYER_R
        nx = max(float(self.arena.left + m), min(float(self.arena.right - m), nx))
        ny = max(float(self.arena.top  + m), min(float(self.arena.bottom - m), ny))

        pr = pygame.Rect(int(nx) - m, int(ny) - m, m * 2, m * 2)
        for wall in self._walls:
            if pr.colliderect(wall):
                nx, ny = self._px, self._py
                break

        self._px, self._py = nx, ny

        # Victoria: llegar al docente
        dist = math.hypot(self._px - self._dx, self._py - self._dy)
        if dist <= _DOC_R + _PLAYER_R:
            self._found = True
            self._end_win()

    # ── Render ────────────────────────────────────────────────────────────────

    def _draw_playing(self, screen: pygame.Surface) -> None:
        # Fondo del arena
        arena_surf = pygame.Surface((_ARENA_W, _ARENA_H))
        arena_surf.fill(_BG_COLOR)
        screen.blit(arena_surf, self.arena.topleft)
        pygame.draw.rect(screen, (255, 255, 255), self.arena, 2)

        # Obstaculos / pupitres
        for wall in self._walls:
            pygame.draw.rect(screen, _WALL_COLOR, wall)
            pygame.draw.rect(screen, (80, 84, 110), wall, 1)

        # Docente (circulo verde con icono "D")
        dx, dy = int(self._dx), int(self._dy)
        pygame.draw.circle(screen, _DOC_COL, (dx, dy), _DOC_R)
        pygame.draw.circle(screen, _DOC_ICON, (dx, dy), _DOC_R, 2)
        fn = self._font_sm
        if fn:
            t = fn.render("DOC", True, (10, 30, 20))
            screen.blit(t, (dx - t.get_width() // 2, dy - t.get_height() // 2))

        # Flecha guia hacia el docente
        self._draw_guide_arrow(screen)

        # Jugador (corazon cuadrado, igual que dia5_pelea)
        px, py = int(self._px), int(self._py)
        pygame.draw.rect(screen, _PLAYER_COL,
                         (px - _PLAYER_R // 2, py - _PLAYER_R // 2,
                          _PLAYER_R, _PLAYER_R))

        # HUD
        remaining = max(0.0, _TIME_MS - self._elapsed_ms)
        self._draw_timer_bar(
            screen, self._elapsed_ms, _TIME_MS,
            self.arena.left, self.arena.bottom + 10,
            _ARENA_W, 7,
        )
        fn = self._font_sm
        if fn:
            color = (255, 90, 90) if remaining < _TIMER_WARN else (180, 180, 200)
            t = fn.render(f"Tiempo: {remaining / 1000:.1f}s", True, color)
            screen.blit(t, (self.arena.right - t.get_width(), self.arena.bottom + 20))

    def _draw_guide_arrow(self, screen: pygame.Surface) -> None:
        """Dibuja una flecha animada apuntando hacia el docente."""
        if self._found:
            return
        dx  = self._dx - self._px
        dy  = self._py - self._dy  # invertido porque Y crece hacia abajo
        ang = math.atan2(-dy, dx)  # angulo en radianes

        # Punta de la flecha: 40px del jugador en direccion al docente
        dist = max(1.0, math.hypot(dx, -dy))
        # Si ya estamos cerca no necesitamos flecha
        if dist < _DOC_R * 2:
            return

        offset = min(50.0, dist * 0.4)
        tip_x = int(self._px + math.cos(ang) * offset)
        tip_y = int(self._py - math.sin(ang) * offset)

        # Pulso
        pulse = 0.65 + 0.35 * math.sin(pygame.time.get_ticks() / 280.0)
        a = int(200 * pulse)
        arrow_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)

        size = 10
        perp_ang = ang + math.pi / 2
        base_x = tip_x - int(math.cos(ang) * size * 1.4)
        base_y = tip_y + int(math.sin(ang) * size * 1.4)
        p1 = (tip_x, tip_y)
        p2 = (base_x + int(math.cos(perp_ang) * size),
              base_y - int(math.sin(perp_ang) * size))
        p3 = (base_x - int(math.cos(perp_ang) * size),
              base_y + int(math.sin(perp_ang) * size))
        pygame.draw.polygon(arrow_surf, (*_GUIDE_COL, a), [p1, p2, p3])
        screen.blit(arrow_surf, (0, 0))
