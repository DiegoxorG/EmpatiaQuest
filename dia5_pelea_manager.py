"""
Día 5 — Minijuego: "Sostén la calma"

Estilo Undertale: el jugador controla un corazón y debe esquivar
frases/insultos que vuelan por la pantalla desde todas direcciones.

Controles : ↑ ↓ ← →  (también W A S D)
Ganas     : sobrevive WIN_SECONDS segundos sin agotar la vida
Pierdes   : HP llega a 0

Integración:
    mgr = Dia5PeleaManager(screen_w, screen_h, audio)
    mgr.handle_event(pygame.event)   # en el loop de eventos
    mgr.update(dt_ms)                # cada frame
    mgr.draw(screen, fonts)          # en el renderer
    if mgr.result is not None:       # {"gano": bool, "tipo": "pelea_palabras"}
        ...
"""

from __future__ import annotations
import pygame
import random
import math


# ── Frases proyectil ──────────────────────────────────────────────────────────

_INSULTS: list[str] = [
    "No te metas",
    "El empezo",
    "Siempre arruinan todo",
    "Nadie te pidio ayuda",
    "Dejalo pelear",
    "No es tu problema",
    "Hazte a un lado",
    "No puedes ayudar",
    "No cambias nada",
    "Eres igual que ellos",
    "Sigues metiendo la pata",
    "Nadie te escucha",
]

_BULLET_COLORS: list[tuple] = [
    (255, 90, 90),
    (255, 190, 50),
    (120, 200, 255),
    (200, 110, 255),
    (255, 140, 80),
]

_BG_COLOR  = (12,  8,  22)
_BOX_COLOR = (18, 14, 32)
_BOX_BORDER = (255, 255, 255)
_HP_COLOR  = (255, 60, 80)
_HEART_COLOR = (220, 40, 60)
_TIMER_COLOR = (180, 180, 200)
_WIN_COLOR   = (100, 255, 130)
_LOSE_COLOR  = (255, 80, 80)


# ── Bullet ────────────────────────────────────────────────────────────────────

class _Bullet:
    def __init__(self, arena: pygame.Rect, font: pygame.font.Font,
                 difficulty: float) -> None:
        self.font  = font
        self.text  = random.choice(_INSULTS)
        self.color = random.choice(_BULLET_COLORS)

        base_speed = 130 + 80 * difficulty          # faster as time passes
        speed = random.uniform(base_speed, base_speed + 60)

        direction = random.choice(("left", "right", "top", "bottom"))
        spread = 40 + 20 * difficulty

        if direction == "left":
            self.x  = float(arena.left - 220)
            self.y  = random.uniform(arena.top, arena.bottom)
            self.vx = speed
            self.vy = random.uniform(-spread, spread)
        elif direction == "right":
            self.x  = float(arena.right + 220)
            self.y  = random.uniform(arena.top, arena.bottom)
            self.vx = -speed
            self.vy = random.uniform(-spread, spread)
        elif direction == "top":
            self.x  = random.uniform(arena.left, arena.right)
            self.y  = float(arena.top - 120)
            self.vx = random.uniform(-spread, spread)
            self.vy = speed
        else:
            self.x  = random.uniform(arena.left, arena.right)
            self.y  = float(arena.bottom + 120)
            self.vx = random.uniform(-spread, spread)
            self.vy = -speed

        self.surf = font.render(self.text, True, self.color)
        self.rect = self.surf.get_rect(center=(int(self.x), int(self.y)))

    def update(self, dt_ms: float) -> None:
        dt = dt_ms / 1000.0
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.center = (int(self.x), int(self.y))

    def is_offscreen(self, bounds: pygame.Rect) -> bool:
        return not bounds.colliderect(self.rect)


# ── Manager ───────────────────────────────────────────────────────────────────

class Dia5PeleaManager:
    ARENA_W        = 440
    ARENA_H        = 290
    HEART_SIZE     = 13      # pixel radius
    HEART_SPEED    = 210     # px / sec
    MAX_HP         = 5
    WIN_SECONDS    = 20
    SPAWN_BASE_MS  = 1300    # ms between bullet spawns (decreases over time)
    SPAWN_MIN_MS   = 400
    INVINCIBLE_MS  = 900     # ms of invincibility after being hit

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.audio    = audio

        self.arena = pygame.Rect(
            (screen_w - self.ARENA_W) // 2,
            (screen_h - self.ARENA_H) // 2 + 10,
            self.ARENA_W,
            self.ARENA_H,
        )

        self.heart_x = float(self.arena.centerx)
        self.heart_y = float(self.arena.centery)

        self.hp             = self.MAX_HP
        self.survived_ms    = 0
        self.spawn_timer_ms = 0
        self.bullets: list[_Bullet] = []
        self.invincible_ms  = 0
        self._keys: set[int] = set()

        self.phase          = "intro"   # "intro" | "playing" | "win" | "lose"
        self.intro_ms       = 2000
        self.result: dict | None = None
        self.result_delay_ms = 0

        self._font_sm: pygame.font.Font | None = None
        self._font_md: pygame.font.Font | None = None

    # ── Font helpers ─────────────────────────────────────────────────────────

    def _get_fonts(self, fonts: dict) -> tuple[pygame.font.Font, pygame.font.Font]:
        if self._font_sm is None:
            try:
                self._font_sm = fonts.get("small") or pygame.font.SysFont("monospace", 13)
                self._font_md = fonts.get("medium") or pygame.font.SysFont("monospace", 20)
            except Exception:
                self._font_sm = pygame.font.Font(None, 15)
                self._font_md = pygame.font.Font(None, 22)
        return self._font_sm, self._font_md

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._keys.add(event.key)
            if self.phase in ("win", "lose") and event.key in (
                pygame.K_RETURN, pygame.K_e, pygame.K_SPACE
            ):
                self._finalize()
        elif event.type == pygame.KEYUP:
            self._keys.discard(event.key)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt_ms: float) -> None:
        if self.phase == "intro":
            self.intro_ms -= dt_ms
            if self.intro_ms <= 0:
                self.phase = "playing"
        elif self.phase == "playing":
            self._update_playing(dt_ms)
        elif self.phase in ("win", "lose"):
            self.result_delay_ms -= dt_ms
            if self.result_delay_ms <= 0:
                self._finalize()

    def _update_playing(self, dt_ms: float) -> None:
        dt = dt_ms / 1000.0
        self.survived_ms += dt_ms

        # Move heart
        vx, vy = 0.0, 0.0
        if pygame.K_LEFT  in self._keys or pygame.K_a in self._keys:
            vx -= self.HEART_SPEED
        if pygame.K_RIGHT in self._keys or pygame.K_d in self._keys:
            vx += self.HEART_SPEED
        if pygame.K_UP    in self._keys or pygame.K_w in self._keys:
            vy -= self.HEART_SPEED
        if pygame.K_DOWN  in self._keys or pygame.K_s in self._keys:
            vy += self.HEART_SPEED

        margin = self.HEART_SIZE
        self.heart_x = max(
            float(self.arena.left  + margin),
            min(float(self.arena.right  - margin), self.heart_x + vx * dt),
        )
        self.heart_y = max(
            float(self.arena.top   + margin),
            min(float(self.arena.bottom - margin), self.heart_y + vy * dt),
        )

        # Spawn bullets
        self.spawn_timer_ms -= dt_ms
        if self.spawn_timer_ms <= 0:
            difficulty = min(1.0, self.survived_ms / (self.WIN_SECONDS * 1000))
            interval = max(
                self.SPAWN_MIN_MS,
                self.SPAWN_BASE_MS - int(difficulty * (self.SPAWN_BASE_MS - self.SPAWN_MIN_MS)),
            )
            self.spawn_timer_ms = interval
            count = 1 + int(difficulty * 2)     # 1–3 bullets
            font = self._font_sm or pygame.font.SysFont("monospace", 13)
            for _ in range(count):
                self.bullets.append(_Bullet(self.arena, font, difficulty))

        # Update bullets
        dead_zone = self.arena.inflate(500, 500)
        for b in self.bullets:
            b.update(dt_ms)
        self.bullets = [b for b in self.bullets if not b.is_offscreen(dead_zone)]

        # Collision
        if self.invincible_ms <= 0:
            hx, hy = int(self.heart_x), int(self.heart_y)
            hbox = pygame.Rect(
                hx - self.HEART_SIZE // 2,
                hy - self.HEART_SIZE // 2,
                self.HEART_SIZE,
                self.HEART_SIZE,
            )
            for b in self.bullets:
                if hbox.colliderect(b.rect):
                    self.hp -= 1
                    self.invincible_ms = self.INVINCIBLE_MS
                    if self.audio:
                        try:
                            self.audio.play_sfx("golpe")
                        except Exception:
                            pass
                    if self.hp <= 0:
                        self.phase = "lose"
                        self.result_delay_ms = 3200
                    break
        else:
            self.invincible_ms -= dt_ms

        # Win check
        if self.survived_ms >= self.WIN_SECONDS * 1000:
            self.phase = "win"
            self.result_delay_ms = 3200

    def _finalize(self) -> None:
        if self.result is None:
            self.result = {"gano": self.phase == "win", "tipo": "pelea_palabras"}

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface, fonts: dict) -> None:
        font_sm, font_md = self._get_fonts(fonts)

        # Dark full-screen overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        # Arena background
        arena_surf = pygame.Surface((self.ARENA_W, self.ARENA_H))
        arena_surf.fill(_BOX_COLOR)
        screen.blit(arena_surf, self.arena.topleft)
        pygame.draw.rect(screen, _BOX_BORDER, self.arena, 3)

        if self.phase == "intro":
            self._draw_intro(screen, font_sm, font_md)
            return

        # Bullets
        for b in self.bullets:
            screen.blit(b.surf, b.rect)

        # Heart (blink during invincibility)
        if self.invincible_ms <= 0 or (pygame.time.get_ticks() // 70) % 2 == 0:
            self._draw_heart(screen)

        # HUD
        self._draw_hud(screen, font_sm)

        # Phase overlays
        if self.phase == "win":
            self._draw_result(screen, font_sm, font_md, won=True)
        elif self.phase == "lose":
            self._draw_result(screen, font_sm, font_md, won=False)

    def _draw_intro(self, screen: pygame.Surface,
                    font_sm: pygame.font.Font,
                    font_md: pygame.font.Font) -> None:
        lines = [
            "¡Sostén la calma!",
            "",
            "Esquiva las palabras con  ↑ ↓ ← →",
            f"Sobrevive {self.WIN_SECONDS} segundos para ganar.",
        ]
        y = self.arena.centery - len(lines) * 16
        for line in lines:
            surf = (font_md if line and "!" in line else font_sm).render(
                line, True, (230, 230, 230)
            )
            screen.blit(surf, (self.arena.centerx - surf.get_width() // 2, y))
            y += 30

    def _draw_heart(self, screen: pygame.Surface) -> None:
        hx = int(self.heart_x) - self.HEART_SIZE // 2
        hy = int(self.heart_y) - self.HEART_SIZE // 2
        hw = self.HEART_SIZE
        pygame.draw.rect(screen, _HEART_COLOR, (hx, hy, hw, hw))

    def _draw_hud(self, screen: pygame.Surface,
                  font_sm: pygame.font.Font) -> None:
        # HP hearts
        full  = "♥"
        empty = "♡"
        hp_str = (full * self.hp) + (empty * (self.MAX_HP - self.hp))
        hp_surf = font_sm.render(hp_str, True, _HP_COLOR)
        screen.blit(hp_surf, (self.arena.left, self.arena.bottom + 8))

        # Timer
        remaining = max(0.0, (self.WIN_SECONDS * 1000 - self.survived_ms) / 1000)
        timer_str = f"Sostén: {remaining:.1f}s"
        timer_surf = font_sm.render(timer_str, True, _TIMER_COLOR)
        screen.blit(
            timer_surf,
            (self.arena.right - timer_surf.get_width(), self.arena.bottom + 8),
        )

        # Timer bar
        bar_w = self.ARENA_W
        bar_h = 5
        bar_x = self.arena.left
        bar_y = self.arena.bottom + 28
        ratio = max(0.0, min(1.0, 1.0 - self.survived_ms / (self.WIN_SECONDS * 1000)))
        pygame.draw.rect(screen, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h))
        if ratio > 0:
            fill_color = (100, 200, 100) if ratio > 0.3 else (255, 160, 40)
            pygame.draw.rect(screen, fill_color, (bar_x, bar_y, int(bar_w * ratio), bar_h))

    def _draw_result(self, screen: pygame.Surface,
                     font_sm: pygame.font.Font,
                     font_md: pygame.font.Font,
                     won: bool) -> None:
        # Semi-transparent panel
        panel = pygame.Surface((self.ARENA_W, 80), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        screen.blit(panel, (self.arena.left, self.arena.centery - 40))

        color = _WIN_COLOR if won else _LOSE_COLOR
        msg   = "¡Lo lograste!" if won else "La pelea continúa..."
        surf  = font_md.render(msg, True, color)
        screen.blit(
            surf,
            (self.arena.centerx - surf.get_width() // 2,
             self.arena.centery - surf.get_height() // 2 - 10),
        )
        hint = font_sm.render("Presiona E / ENTER para continuar", True, (180, 180, 180))
        screen.blit(
            hint,
            (self.arena.centerx - hint.get_width() // 2,
             self.arena.centery + surf.get_height() // 2),
        )
