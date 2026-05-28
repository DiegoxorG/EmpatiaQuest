"""
BorrarInsultosManager — Minijuego tipo 4: "Borrar insultos".

Mecanica:
- Aparecen insultos escritos en la pantalla (como si estuvieran en una pared
  o pantalla de redes sociales).
- El jugador usa el MOUSE para "borrar" los textos pasando el cursor sobre
  ellos mientras mantiene el boton izquierdo presionado.
- Nuevos insultos aparecen periodicamente con efecto de "escritura".
- Porcentaje borrado visible en todo momento.
- Ganar: borrar >= LIMPIEZA_WIN% antes del tiempo limite.
- Perder: tiempo agotado con menos del porcentaje requerido.

Feedback visual: partículas de borrado al pasar el cursor.

Integracion estandar (GameplayBase):
    mgr = BorrarInsultosManager(sw, sh, audio)
    mgr.handle_event(event); mgr.update(dt_ms); mgr.draw(screen, fonts)
    if mgr.result: ...   # {"gano": bool, "tipo": "borrar_insultos"}
"""
from __future__ import annotations
import math
import random
import pygame
from gameplay_base import GameplayBase

# ── Configuracion ─────────────────────────────────────────────────────────────
_TIME_MS       = 25_000
_LIMPIEZA_WIN  = 80          # % borrado necesario para ganar
_BORRADOR_R    = 28          # radio del cursor-borrador
_SPAWN_EVERY   = 4000        # ms entre oleadas de nuevos insultos
_MAX_INSULTOS  = 10
_PARTICULAS_PER_ERASE = 3

_INSULTOS_POOL = [
    "Nadie te quiere",  "Eres un fraude", "Callate",
    "No vales nada",    "Rindete",        "Eres raro/a",
    "Todo es tu culpa", "Nadie te cree",  "Eres inferior",
    "Ignorado/a",       "Fuera de aqui",  "Patético/a",
    "No encajas",       "Eres lo peor",   "Sin amigos",
]

_BG_COL      = (14, 12, 24)
_INSULT_COL  = (220,  70,  70)
_ERASED_COL  = (40,   42,  58)
_CURSOR_COL  = (245, 245, 245, 160)
_PARTICLE_COLS = [
    (255, 255, 255), (200, 210, 240), (160, 180, 255), (240, 200, 200),
]


class _Insulto:
    def __init__(self, text: str, x: int, y: int) -> None:
        self.text       = text
        self.x          = x
        self.y          = y
        self.erased_pct = 0.0       # 0.0 → 1.0
        self.appearing  = True
        self.appear_ms  = 0.0
        self.appear_dur = 600.0     # ms de animacion de entrada
        self.rect: pygame.Rect | None = None


class _Particle:
    def __init__(self, x: int, y: int) -> None:
        self.x   = float(x)
        self.y   = float(y)
        self.vx  = random.uniform(-120, 120)
        self.vy  = random.uniform(-180, -60)
        self.life = random.uniform(0.25, 0.55)
        self.col  = random.choice(_PARTICLE_COLS)

    def update(self, dt: float) -> bool:
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy += 260 * dt   # gravedad
        self.life -= dt
        return self.life > 0


class BorrarInsultosManager(GameplayBase):
    """Minijuego de borrado de mensajes daninos con el raton."""

    tipo = "borrar_insultos"

    def __init__(self, screen_w: int, screen_h: int, audio=None) -> None:
        super().__init__(screen_w, screen_h, audio)
        self._elapsed_ms    = 0.0
        self._spawn_timer   = 1000.0
        self._insultos      : list[_Insulto] = []
        self._particles     : list[_Particle] = []
        self._mouse_down    = False
        self._mouse_pos     = (0, 0)
        self._total_borrado = 0.0
        self._total_posible = 0.0
        self._font_insult: pygame.font.Font | None = None

    def _intro_lines(self) -> list[str]:
        return [
            "Borrar insultos",
            "",
            "Mantén el botón izquierdo del ratón presionado",
            "y pasa el cursor sobre los mensajes para borrarlos.",
            f"Borra el {_LIMPIEZA_WIN}% antes de que acabe el tiempo.",
        ]

    def _on_start(self) -> None:
        self._spawn_batch()

    def _on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._mouse_down = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_down = False
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            self._mouse_pos = pygame.mouse.get_pos()

    def _update_playing(self, dt_ms: float) -> None:
        self._elapsed_ms += dt_ms
        if self._elapsed_ms >= _TIME_MS:
            if self._limpieza_pct() >= _LIMPIEZA_WIN:
                self._end_win()
            else:
                self._end_lose()
            return

        dt = dt_ms / 1000.0
        # Actualizar particulas
        self._particles = [p for p in self._particles if p.update(dt)]

        # Animacion de aparicion
        for ins in self._insultos:
            if ins.appearing:
                ins.appear_ms += dt_ms
                if ins.appear_ms >= ins.appear_dur:
                    ins.appearing = False

        # Borrado con el raton
        if self._mouse_down:
            mx, my = self._mouse_pos
            for ins in self._insultos:
                if ins.rect is None or ins.erased_pct >= 1.0:
                    continue
                if ins.appearing:
                    continue
                expanded = ins.rect.inflate(_BORRADOR_R * 2, _BORRADOR_R * 2)
                if expanded.collidepoint(mx, my):
                    old = ins.erased_pct
                    ins.erased_pct = min(1.0, ins.erased_pct + dt * 1.8)
                    if ins.erased_pct > old:
                        for _ in range(_PARTICULAS_PER_ERASE):
                            self._particles.append(_Particle(
                                ins.rect.centerx + random.randint(-20, 20),
                                ins.rect.centery + random.randint(-10, 10),
                            ))
                        if self.audio and random.random() < 0.15:
                            try:
                                self.audio.play_sfx("borrar", 0.4)
                            except Exception:
                                pass

        # Spawn de nuevos insultos
        self._spawn_timer -= dt_ms
        if self._spawn_timer <= 0:
            self._spawn_batch()
            self._spawn_timer = _SPAWN_EVERY

        # Victoria anticipada
        if self._limpieza_pct() >= _LIMPIEZA_WIN:
            self._end_win()

    def _spawn_batch(self) -> None:
        """Agrega insultos hasta _MAX_INSULTOS si hay espacio."""
        active = [i for i in self._insultos if i.erased_pct < 1.0]
        need   = max(0, _MAX_INSULTOS // 2 - len(active))
        for _ in range(need):
            if len(self._insultos) >= _MAX_INSULTOS * 2:
                break
            text = random.choice(_INSULTOS_POOL)
            x = random.randint(80, self.screen_w - 220)
            y = random.randint(80, self.screen_h - 120)
            self._insultos.append(_Insulto(text, x, y))
        # Actualizar total posible
        self._total_posible = float(len([i for i in self._insultos]))

    def _limpieza_pct(self) -> float:
        if not self._insultos:
            return 0.0
        total = len(self._insultos)
        borrado = sum(i.erased_pct for i in self._insultos)
        return (borrado / max(1, total)) * 100.0

    # ── Render ────────────────────────────────────────────────────────────────

    def _draw_playing(self, screen: pygame.Surface) -> None:
        # Fondo oscuro
        bg = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        bg.fill((*_BG_COL, 240))
        screen.blit(bg, (0, 0))

        # Insultos
        fn = self._get_insult_font()
        for ins in self._insultos:
            if ins.erased_pct >= 1.0:
                continue
            # Progreso de aparicion
            if ins.appearing:
                ratio = min(1.0, ins.appear_ms / ins.appear_dur)
            else:
                ratio = 1.0
            # Alpha segun borrado: a menos borrado, mas visible
            visible = max(0.0, 1.0 - ins.erased_pct)
            a = int(255 * visible * ratio)
            if a < 5:
                continue
            col = (*_INSULT_COL, a)
            surf = fn.render(ins.text, True, col[:3])
            surf.set_alpha(a)
            screen.blit(surf, (ins.x, ins.y))
            ins.rect = pygame.Rect(ins.x, ins.y, surf.get_width(), surf.get_height())

            # Barra de borrado debajo del texto
            if not ins.appearing and ins.erased_pct > 0:
                bw = surf.get_width()
                fill = int(bw * ins.erased_pct)
                pygame.draw.rect(screen, (50, 55, 75),
                                 (ins.x, ins.y + surf.get_height() + 2, bw, 3))
                pygame.draw.rect(screen, (120, 200, 140),
                                 (ins.x, ins.y + surf.get_height() + 2, fill, 3))

        # Particulas
        ps = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        for p in self._particles:
            a = int(220 * max(0.0, p.life / 0.5))
            pygame.draw.circle(ps, (*p.col, a), (int(p.x), int(p.y)), 2)
        screen.blit(ps, (0, 0))

        # Cursor de borrador
        if self._mouse_down:
            mx, my = self._mouse_pos
            cur = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            pygame.draw.circle(cur, _CURSOR_COL, (mx, my), _BORRADOR_R)
            pygame.draw.circle(cur, (255, 255, 255, 200), (mx, my), _BORRADOR_R, 2)
            screen.blit(cur, (0, 0))

        # HUD
        pct = self._limpieza_pct()
        fn_sm = self._font_sm
        if fn_sm:
            col = (100, 220, 130) if pct >= _LIMPIEZA_WIN else (200, 200, 220)
            t = fn_sm.render(f"Borrado: {pct:.0f}%  (meta: {_LIMPIEZA_WIN}%)", True, col)
            screen.blit(t, (20, 20))
        self._draw_timer_bar(
            screen, self._elapsed_ms, _TIME_MS,
            20, self.screen_h - 28, self.screen_w - 40, 7,
        )
        remaining = max(0.0, (_TIME_MS - self._elapsed_ms) / 1000.0)
        if fn_sm:
            tc = (220, 80, 80) if remaining < 6 else (170, 175, 195)
            t = fn_sm.render(f"{remaining:.1f}s", True, tc)
            screen.blit(t, (self.screen_w - t.get_width() - 20, self.screen_h - 28))

    def _get_insult_font(self) -> pygame.font.Font:
        if self._font_insult is None:
            try:
                self._font_insult = pygame.font.SysFont("monospace", 18)
            except Exception:
                self._font_insult = pygame.font.Font(None, 20)
        return self._font_insult
