"""
DefenderAgresivoManager — Minijuego tipo 3: "Defender agresivamente".

Mecanica similar a dia5_pelea_manager (tipo 2 - calma) pero mas intenso:
- El jugador controla un corazon y esquiva proyectiles fisicos (pugños).
- Los proyectiles son mas rapidos, mas grandes y con patrones mas agresivos.
- Camara con efecto de shake al recibir golpe.
- Barra de vida de 3 HP (menos tolerante que la version calmada).
- Tiempo de supervivencia mas corto pero dificultad mayor.
- Ganar: sobrevivir WIN_SECONDS segundos.
- Perder: HP llega a 0.

Representa confrontar agresivamente — funciona pero tiene mayor costo.

Integracion estandar (GameplayBase):
    mgr = DefenderAgresivoManager(sw, sh, audio)
    mgr.handle_event(event); mgr.update(dt_ms); mgr.draw(screen, fonts)
    if mgr.result: ...   # {"gano": bool, "tipo": "defender_agresivo"}
"""
from __future__ import annotations
import math
import random
import pygame
from gameplay_base import GameplayBase

# ── Configuracion ─────────────────────────────────────────────────────────────
_ARENA_W      = 460
_ARENA_H      = 300
_HEART_SIZE   = 14
_HEART_SPEED  = 220
_MAX_HP       = 3
_WIN_SECONDS  = 16
_SPAWN_BASE   = 900
_SPAWN_MIN    = 280
_INVINCIBLE   = 700
_SHAKE_MS     = 320
_SHAKE_PIXELS = 6

_FRASES = [
    "PUNO",  "GOLPE",  "EMPUJON", "PATADA",
    "AGARRE", "CHOQUE", "IMPACTO", "FUERZA",
]
_FRASE_COLS = [
    (255,  70,  50), (255, 100,  30), (220,  50,  50),
    (200,  40,  80), (255,  80,  60),
]

_BG_COL     = (16,  8,  18)
_BOX_COL    = (24, 12,  26)
_BORDER_COL = (220,  60,  60)
_HEART_COL  = (220,  40,  60)
_HIT_FLASH  = (255,  40,  40)


class _Proyectil:
    def __init__(self, arena: pygame.Rect, difficulty: float, big: bool = False) -> None:
        self.text  = random.choice(_FRASES)
        self.color = random.choice(_FRASE_COLS)
        self.big   = big
        size_m = 1.6 if big else 1.0

        base_spd = 200 + 120 * difficulty
        spd = random.uniform(base_spd, base_spd + 80) * size_m
        spread = 60 + 30 * difficulty

        direction = random.choice(("left", "right", "top", "bottom"))
        if direction == "left":
            self.x, self.y = float(arena.left - 240), random.uniform(arena.top, arena.bottom)
            self.vx, self.vy = spd, random.uniform(-spread, spread)
        elif direction == "right":
            self.x, self.y = float(arena.right + 240), random.uniform(arena.top, arena.bottom)
            self.vx, self.vy = -spd, random.uniform(-spread, spread)
        elif direction == "top":
            self.x, self.y = random.uniform(arena.left, arena.right), float(arena.top - 130)
            self.vx, self.vy = random.uniform(-spread, spread), spd
        else:
            self.x, self.y = random.uniform(arena.left, arena.right), float(arena.bottom + 130)
            self.vx, self.vy = random.uniform(-spread, spread), -spd

        self._font: pygame.font.Font | None = None
        self._surf: pygame.Surface | None = None

    def get_surf(self, font: pygame.font.Font) -> pygame.Surface:
        if self._surf is None or self._font is not font:
            self._font = font
            size = 2 if self.big else 1
            txt  = self.text if not self.big else f">> {self.text} <<"
            self._surf = font.render(txt, True, self.color)
        return self._surf

    def update(self, dt_ms: float) -> None:
        dt = dt_ms / 1000.0
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def rect(self) -> pygame.Rect:
        if self._surf:
            return self._surf.get_rect(center=(int(self.x), int(self.y)))
        return pygame.Rect(int(self.x) - 40, int(self.y) - 10, 80, 20)

    def off(self, bounds: pygame.Rect) -> bool:
        return not bounds.colliderect(self.rect)


class DefenderAgresivoManager(GameplayBase):
    """Minijuego de defensa agresiva: esquivar ataques fisicos."""

    tipo = "defender_agresivo"

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        super().__init__(screen_w, screen_h, audio)

        self.arena = pygame.Rect(
            (screen_w - _ARENA_W) // 2,
            (screen_h - _ARENA_H) // 2 + 8,
            _ARENA_W, _ARENA_H,
        )
        self._hx = float(self.arena.centerx)
        self._hy = float(self.arena.centery)
        self._hp = _MAX_HP
        self._survived_ms   = 0.0
        self._spawn_timer   = 0.0
        self._bullets       : list[_Proyectil] = []
        self._invincible_ms = 0.0
        self._shake_ms      = 0.0
        self._shake_ox      = 0
        self._shake_oy      = 0
        self._keys          : set[int] = set()
        self._hit_flash_ms  = 0.0

    def _intro_lines(self) -> list[str]:
        return [
            "¡Defender con fuerza!",
            "",
            "Esquiva los ataques físicos con  ↑ ↓ ← →",
            f"Aguanta {_WIN_SECONDS} segundos.  Tienes {_MAX_HP} vidas.",
            "¡Cuidado — son más rápidos y grandes!",
        ]

    def _on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._keys.add(event.key)
        elif event.type == pygame.KEYUP:
            self._keys.discard(event.key)

    def _update_playing(self, dt_ms: float) -> None:
        dt = dt_ms / 1000.0
        self._survived_ms += dt_ms

        # Mover corazon
        vx = vy = 0.0
        if pygame.K_LEFT  in self._keys or pygame.K_a in self._keys: vx -= _HEART_SPEED
        if pygame.K_RIGHT in self._keys or pygame.K_d in self._keys: vx += _HEART_SPEED
        if pygame.K_UP    in self._keys or pygame.K_w in self._keys: vy -= _HEART_SPEED
        if pygame.K_DOWN  in self._keys or pygame.K_s in self._keys: vy += _HEART_SPEED
        m = _HEART_SIZE
        self._hx = max(float(self.arena.left + m),
                       min(float(self.arena.right - m), self._hx + vx * dt))
        self._hy = max(float(self.arena.top + m),
                       min(float(self.arena.bottom - m), self._hy + vy * dt))

        # Spawn
        difficulty = min(1.0, self._survived_ms / (_WIN_SECONDS * 1000))
        self._spawn_timer -= dt_ms
        if self._spawn_timer <= 0:
            interval = max(_SPAWN_MIN, _SPAWN_BASE - int(difficulty * (_SPAWN_BASE - _SPAWN_MIN)))
            self._spawn_timer = interval
            count = 1 + int(difficulty * 3)
            fn = self._font_sm or pygame.font.SysFont("monospace", 13)
            for i in range(count):
                big = (i == 0 and difficulty > 0.5 and random.random() < 0.3)
                self._bullets.append(_Proyectil(self.arena, difficulty, big))

        # Mover proyectiles
        dead_zone = self.arena.inflate(600, 600)
        for b in self._bullets:
            b.update(dt_ms)
        self._bullets = [b for b in self._bullets if not b.off(dead_zone)]

        # Colision
        if self._invincible_ms <= 0:
            hbox = pygame.Rect(
                int(self._hx) - m // 2, int(self._hy) - m // 2, m, m
            )
            for b in self._bullets:
                if hbox.colliderect(b.rect):
                    self._hp -= 1
                    self._invincible_ms = _INVINCIBLE
                    self._shake_ms      = _SHAKE_MS
                    self._hit_flash_ms  = 280.0
                    if self.audio:
                        try: self.audio.play_sfx("hit_corazon")
                        except Exception: pass
                    if self._hp <= 0:
                        self._end_lose()
                    break
        else:
            self._invincible_ms = max(0.0, self._invincible_ms - dt_ms)

        # Shake
        if self._shake_ms > 0:
            self._shake_ms = max(0.0, self._shake_ms - dt_ms)
            self._shake_ox = random.randint(-_SHAKE_PIXELS, _SHAKE_PIXELS)
            self._shake_oy = random.randint(-_SHAKE_PIXELS, _SHAKE_PIXELS)
        else:
            self._shake_ox = self._shake_oy = 0

        # Flash de golpe
        self._hit_flash_ms = max(0.0, self._hit_flash_ms - dt_ms)

        # Victoria
        if self._survived_ms >= _WIN_SECONDS * 1000:
            self._end_win()

    def _draw_playing(self, screen: pygame.Surface) -> None:
        ox, oy = self._shake_ox, self._shake_oy

        # Fondo del arena
        arena_surf = pygame.Surface((_ARENA_W, _ARENA_H))
        arena_surf.fill(_BOX_COL)
        screen.blit(arena_surf, (self.arena.x + ox, self.arena.y + oy))
        pygame.draw.rect(screen, _BORDER_COL,
                         self.arena.move(ox, oy), 3)

        # Flash de golpe
        if self._hit_flash_ms > 0:
            a = int(120 * self._hit_flash_ms / 280.0)
            fs = pygame.Surface((_ARENA_W, _ARENA_H), pygame.SRCALPHA)
            fs.fill((*_HIT_FLASH, a))
            screen.blit(fs, (self.arena.x + ox, self.arena.y + oy))

        # Proyectiles
        fn = self._font_sm or pygame.font.Font(None, 15)
        for b in self._bullets:
            surf = b.get_surf(fn)
            r = surf.get_rect(center=(int(b.x) + ox, int(b.y) + oy))
            screen.blit(surf, r)

        # Corazon (parpadea durante invulnerabilidad)
        if self._invincible_ms <= 0 or (pygame.time.get_ticks() // 55) % 2 == 0:
            hx = int(self._hx) - _HEART_SIZE // 2 + ox
            hy = int(self._hy) - _HEART_SIZE // 2 + oy
            pygame.draw.rect(screen, _HEART_COL, (hx, hy, _HEART_SIZE, _HEART_SIZE))

        # HUD
        remaining = max(0.0, (_WIN_SECONDS * 1000 - self._survived_ms) / 1000)
        self._draw_hp_hearts(screen, self._hp, _MAX_HP,
                             self.arena.left, self.arena.bottom + 8)
        self._draw_timer_bar(screen, self._survived_ms, _WIN_SECONDS * 1000,
                             self.arena.left, self.arena.bottom + 28,
                             _ARENA_W, 5)
        fn_sm = self._font_sm
        if fn_sm:
            color = (255, 80, 80) if remaining < 5 else (170, 175, 200)
            t = fn_sm.render(f"Aguanta: {remaining:.1f}s", True, color)
            screen.blit(t, (self.arena.right - t.get_width(), self.arena.bottom + 8))
