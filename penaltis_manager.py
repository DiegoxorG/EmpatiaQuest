"""
PenaltisManager — Minijuego de Penaltis integrado en EmpatiaQuest.

Mecánica:
  · Intento 1 (entrenamiento): barra que se mueve automáticamente L↔R.
    ESPACIO / E para detener la barra y disparar el balón.
  · Intentos 2-5: la portería tiene obstáculos (paredes negras).
    ← → / A / D para mover el cursor de apuntado.
    ESPACIO / E para disparar.
  · 5 intentos totales (1 entrenamiento + 4 normales).
  · Retorna {"gano": bool, "tipo": "penaltis", "goles": int} al terminar.

# 🎵 ASSET_BGM: Audio/BGM/minijuego_penaltis.ogg  | música arcade rápida de penaltis
# 🎵 ASSET_SFX: Audio/SFX/gol_marcado.ogg         | fanfare breve al marcar gol
# 🎵 ASSET_SFX: Audio/SFX/balon_disparo.ogg       | sonido de patear el balón
# 🎵 ASSET_SFX: Audio/SFX/balon_bloqueado.ogg     | tiro bloqueado o fuera
"""

import math
import os
import random

import pygame

BASE_DIR   = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "Imagenes", "Minijuegos", "penaltis", "imagenes_penaltis")

MAX_INTENTOS  = 5    # 1 entrenamiento + 4 normales
WIN_THRESHOLD = 1    # ≥ 1 gol = minijuego superado (accesible/casual)
BALL_SPEED    = 14.0 # px por frame


class PenaltisManager:
    """Gestiona el minijuego de penaltis completo."""

    def __init__(self, screen_w: int, screen_h: int, audio=None):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.audio    = audio
        self.result   = None  # None mientras corre; dict al terminar

        # ── Portería (escalada desde base 1280×720) ──────────────────────────
        sx = screen_w / 1280
        sy = screen_h / 720
        self.arco_x1 = int(457 * sx)
        self.arco_x2 = int(766 * sx)
        self.arco_y  = int(220 * sy)
        self.arco_h  = int(116 * sy)
        self.arco_w  = self.arco_x2 - self.arco_x1

        # ── Posición inicial del balón ────────────────────────────────────────
        self._bsx = screen_w // 2 - 25
        self._bsy = int(560 * sy)
        self._reset_ball()

        # ── Barra de entrenamiento ────────────────────────────────────────────
        self.bar_w     = max(50, int(90 * sx))
        self.bar_h     = max(12, int(16 * sy))
        self.bar_x     = float(self.arco_x1)
        self.bar_speed = max(3, int(4 * sx))
        self.bar_dir   = 1

        # ── Cursor de apuntado (intentos 2-5) ────────────────────────────────
        self.aim_x   = float((self.arco_x1 + self.arco_x2) // 2)
        self.aim_spd = max(3, int(4 * sx))

        # ── Estado del partido ────────────────────────────────────────────────
        self.intento  = 0   # 0 = entrenamiento, 1-4 = normales
        self.goles    = 0
        self.espacios : list = []   # pygame.Rect huecos abiertos en portería
        self.bloqueos : list = []   # pygame.Rect zonas bloqueadas (derivadas)

        # Fases: "training" | "playing" | "pending" | "result"
        self.phase         = "training"
        self.pending_ms    = 0
        self.pending_scored = False

        # ── Mensajes y timers ─────────────────────────────────────────────────
        self.mensaje   = ""
        self.msg_timer = 0

        # ── Partículas de gol ─────────────────────────────────────────────────
        self.particles: list = []

        # ── Pantalla de resultado ─────────────────────────────────────────────
        self.blink_ms = 0

        # ── Carga de assets ───────────────────────────────────────────────────
        self._load_assets()
        self._generate_spaces()

    # =========================================================================
    # Assets
    # =========================================================================

    def _load_img(self, filename: str):
        path = os.path.join(ASSETS_DIR, filename)
        try:
            img = pygame.image.load(path)
            return (img.convert_alpha() if filename.lower().endswith(".png")
                    else img.convert())
        except (OSError, pygame.error):
            return None

    def _load_assets(self):
        raw_fondo = self._load_img("cancha.jpeg")
        self.fondo = (
            pygame.transform.smoothscale(raw_fondo, (self.screen_w, self.screen_h))
            if raw_fondo else None
        )
        self.balon_orig = self._load_img("balon.png")

    # =========================================================================
    # Generación de portería
    # =========================================================================

    def _generate_spaces(self):
        """Genera los huecos abiertos para el intento actual."""
        self.espacios = []
        if self.intento == 0:
            # Entrenamiento: portería completamente libre
            self.espacios.append(
                pygame.Rect(self.arco_x1, self.arco_y, self.arco_w, self.arco_h))
        else:
            # Tamaños decrecientes por ronda
            base_sizes = [54, 46, 40, 34]
            sz = int(base_sizes[min(self.intento - 1, 3)] * (self.screen_w / 1280))
            sz = max(20, sz)

            # Esquinas siempre accesibles
            self.espacios.append(
                pygame.Rect(self.arco_x1 + 4, self.arco_y, sz, self.arco_h))
            self.espacios.append(
                pygame.Rect(self.arco_x2 - sz - 4, self.arco_y, sz, self.arco_h))

            # Hueco central aleatorio a partir del intento 3
            if self.intento >= 3:
                margin = sz + 14
                lo = self.arco_x1 + margin
                hi = self.arco_x2 - margin - sz
                if lo < hi:
                    xr = random.randint(lo, hi)
                    self.espacios.append(
                        pygame.Rect(xr, self.arco_y, sz, self.arco_h))

        self._compute_bloqueos()

    def _compute_bloqueos(self):
        """Deriva los rectángulos bloqueados a partir de los huecos abiertos."""
        self.bloqueos = []
        sorted_sp = sorted(self.espacios, key=lambda r: r.x)
        x_cur = self.arco_x1
        for sp in sorted_sp:
            if sp.x > x_cur:
                self.bloqueos.append(
                    pygame.Rect(x_cur, self.arco_y, sp.x - x_cur, self.arco_h))
            x_cur = sp.right
        if x_cur < self.arco_x2:
            self.bloqueos.append(
                pygame.Rect(x_cur, self.arco_y, self.arco_x2 - x_cur, self.arco_h))

    # =========================================================================
    # Balón helpers
    # =========================================================================

    def _reset_ball(self):
        self.ball_x    = float(self._bsx)
        self.ball_y    = float(self._bsy)
        self.ball_size = 50
        self.vel_x     = 0.0
        self.vel_y     = 0.0
        self.shot      = False
        self.trajectory: list = []

    def _shoot(self, target_x: float, target_y: float):
        cx = self.ball_x + self.ball_size / 2
        cy = self.ball_y + self.ball_size / 2
        dx, dy = target_x - cx, target_y - cy
        dist = math.hypot(dx, dy) or 1.0
        self.vel_x = dx / dist * BALL_SPEED
        self.vel_y = dy / dist * BALL_SPEED
        self.shot  = True
        self.mensaje = ""
        self._sfx("balon_disparo")

    def _move_ball(self):
        self.ball_x += self.vel_x
        self.ball_y += self.vel_y
        self.trajectory.append(
            (int(self.ball_x + self.ball_size / 2),
             int(self.ball_y + self.ball_size / 2)))
        # Encogimiento perspectivo
        if self.ball_size > 18:
            self.ball_size -= 1

    # =========================================================================
    # Audio & partículas
    # =========================================================================

    def _sfx(self, name: str):
        if self.audio is not None:
            try:
                self.audio.play_sfx(name)
            except Exception:
                pass

    def _spawn_particles(self):
        cx = int(self.ball_x + self.ball_size / 2)
        cy = int(self.ball_y + self.ball_size / 2)
        for _ in range(30):
            a = random.uniform(0, math.tau)
            s = random.uniform(4, 12)
            self.particles.append({
                "x": float(cx), "y": float(cy),
                "vx": math.cos(a) * s,
                "vy": math.sin(a) * s,
                "life": random.randint(26, 44),
                "color": random.choice([
                    (255, 210, 0), (255, 140, 0), (255, 255, 80),
                    (80, 220, 255), (120, 255, 120),
                ]),
            })

    def _update_particles(self):
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.35
            p["life"] -= 1
            if p["life"] <= 0:
                self.particles.remove(p)

    # =========================================================================
    # Avance de intento
    # =========================================================================

    def _end_attempt(self, scored: bool, msg: str):
        """Registra resultado del intento y activa pausa breve."""
        self.mensaje       = msg
        self.msg_timer     = 2200
        self.pending_scored = scored
        self.pending_ms    = 900
        self.phase         = "pending"
        if scored:
            self._sfx("gol_marcado")
            self._spawn_particles()
        else:
            self._sfx("balon_bloqueado")

    def _resolve_pending(self):
        """Ejecuta el avance después de la pausa."""
        if self.pending_scored:
            self.goles += 1
        self._reset_ball()
        self.intento += 1

        if self.intento >= MAX_INTENTOS:
            self.phase    = "result"
            self.blink_ms = 0
        elif self.intento == 1:
            # Entrenamiento completado → modo normal
            self.phase = "playing"
            self._generate_spaces()
            self.aim_x = float((self.arco_x1 + self.arco_x2) // 2)
        else:
            self.phase = "playing"
            self._generate_spaces()

    # =========================================================================
    # update() — llamado cada frame desde screen_handlers
    # =========================================================================

    def update(self, dt_ms: int):
        if self.result is not None:
            return self.result

        self._update_particles()

        if self.msg_timer > 0:
            self.msg_timer -= dt_ms
            if self.msg_timer <= 0:
                self.mensaje = ""

        if self.phase == "pending":
            self.pending_ms -= dt_ms
            if self.pending_ms <= 0:
                self._resolve_pending()
            return None

        if self.phase == "training":
            self._tick_training()
        elif self.phase == "playing":
            self._tick_playing()
        elif self.phase == "result":
            self.blink_ms = (self.blink_ms + dt_ms) % 1200

        return None

    # ── tick_training ─────────────────────────────────────────────────────────

    def _tick_training(self):
        # Mover barra (solo cuando no se ha disparado aún)
        if not self.shot:
            self.bar_x += self.bar_speed * self.bar_dir
            if self.bar_x + self.bar_w >= self.arco_x2:
                self.bar_dir = -1
            if self.bar_x <= self.arco_x1:
                self.bar_dir = 1
            return  # sin disparo → nada más que hacer

        # Balón en vuelo
        self._move_ball()
        bx, by = int(self.ball_x), int(self.ball_y)
        sz = self.ball_size
        cx, cy = bx + sz // 2, by + sz // 2

        bRect  = pygame.Rect(bx, by, sz, sz)
        barRct = pygame.Rect(int(self.bar_x), self.arco_y, self.bar_w, self.bar_h)

        # Colisión con portero (barra)
        if bRect.colliderect(barRct):
            self._end_attempt(False, "¡ATAJADO!")
            return

        # Balón dentro de la zona de portería
        if cy <= self.arco_y + self.arco_h and cy >= self.arco_y - sz:
            if self.arco_x1 <= cx <= self.arco_x2:
                self._end_attempt(True, "¡GOOOOL! ⚽")
            else:
                self._end_attempt(False, "¡FALLASTE!")
            return

        # Balón sale de la pantalla sin llegar
        if by + sz < 0:
            self._end_attempt(False, "¡FALLASTE!")

    # ── tick_playing ──────────────────────────────────────────────────────────

    def _tick_playing(self):
        # Mover cursor con teclas (solo cuando no se ha disparado)
        if not self.shot:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.aim_x = max(float(self.arco_x1 + 4),
                                 self.aim_x - self.aim_spd)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.aim_x = min(float(self.arco_x2 - 4),
                                 self.aim_x + self.aim_spd)
            return

        # Balón en vuelo
        self._move_ball()
        bx, by = int(self.ball_x), int(self.ball_y)
        sz = self.ball_size
        cx, cy = bx + sz // 2, by + sz // 2
        bRect = pygame.Rect(bx, by, sz, sz)

        # Colisión con bloqueos
        for blq in self.bloqueos:
            if bRect.colliderect(blq):
                self._end_attempt(False, "¡BLOQUEADO!")
                return

        # Balón en zona de portería
        if cy <= self.arco_y + self.arco_h and cy >= self.arco_y - sz:
            if self.arco_x1 <= cx <= self.arco_x2:
                gol = any(sp.left <= cx <= sp.right for sp in self.espacios)
                if gol:
                    self._end_attempt(True, "¡GOOOOL! ⚽")
                else:
                    self._end_attempt(False, "¡BLOQUEADO!")
            else:
                self._end_attempt(False, "¡FALLASTE!")
            return

        # Fuera de pantalla
        if by + sz < 0 or bx > self.screen_w + 100 or bx + sz < -100:
            self._end_attempt(False, "¡FALLASTE!")

    # =========================================================================
    # handle_event() — llamado desde screen_handlers
    # =========================================================================

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN:
            return

        CONFIRM = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER,
                   pygame.K_e)

        # Pantalla de resultado
        if self.phase == "result":
            if event.key in CONFIRM:
                gano = self.goles >= WIN_THRESHOLD
                self.result = {
                    "gano":   gano,
                    "tipo":   "penaltis",
                    "goles":  self.goles,
                }
            elif event.key == pygame.K_r:
                self._full_reset()
            return

        # Durante pausa breve entre intentos: ignorar input
        if self.phase == "pending":
            return

        # Entrenamiento: ESPACIO/E dispara hacia la posición de la barra
        if self.phase == "training" and not self.shot:
            if event.key in CONFIRM:
                tx = self.bar_x + self.bar_w / 2
                ty = float(self.arco_y + self.arco_h // 2)
                self._shoot(tx, ty)

        # Normal: ESPACIO/E dispara hacia el cursor de apuntado
        elif self.phase == "playing" and not self.shot:
            if event.key in CONFIRM:
                ty = float(self.arco_y + self.arco_h // 2)
                self._shoot(self.aim_x, ty)

    def _full_reset(self):
        self.intento      = 0
        self.goles        = 0
        self.phase        = "training"
        self.mensaje      = ""
        self.msg_timer    = 0
        self.pending_ms   = 0
        self.particles    = []
        self.bar_x        = float(self.arco_x1)
        self.bar_dir      = 1
        self.aim_x        = float((self.arco_x1 + self.arco_x2) // 2)
        self._reset_ball()
        self._generate_spaces()

    # =========================================================================
    # draw() — llamado cada frame desde renderer
    # =========================================================================

    def draw(self, screen: pygame.Surface, fonts: dict, **kwargs):
        W, H = self.screen_w, self.screen_h

        # ── Fondo ─────────────────────────────────────────────────────────────
        if self.fondo:
            screen.blit(self.fondo, (0, 0))
        else:
            # Fallback: campo verde con líneas blancas
            screen.fill((20, 110, 45))
            pygame.draw.rect(screen, (255, 255, 255),
                             (W // 4, H // 4, W // 2, H // 2), 4)
            pygame.draw.circle(screen, (255, 255, 255),
                               (W // 2, H // 2), H // 8, 3)

        # ── Bloqueos de portería (modo normal) ────────────────────────────────
        if self.phase in ("playing", "pending") and self.intento >= 1:
            for blq in self.bloqueos:
                pygame.draw.rect(screen, (18, 18, 18), blq)
                pygame.draw.rect(screen, (160, 30, 30), blq, 2)

        # ── Barra del portero (entrenamiento) ─────────────────────────────────
        if self.phase == "training" and not self.shot:
            bar_rect = pygame.Rect(int(self.bar_x), self.arco_y,
                                   self.bar_w, self.bar_h)
            pygame.draw.rect(screen, (220, 30, 30), bar_rect)
            pygame.draw.rect(screen, (255, 160, 0), bar_rect, 2)
            fn_s = fonts.get("small")
            if fn_s:
                lbl = fn_s.render("PORTERO", True, (255, 255, 80))
                screen.blit(lbl, (int(self.bar_x), self.arco_y - lbl.get_height() - 2))

        # ── Cursor de apuntado (modo normal, sin disparo) ─────────────────────
        if self.phase == "playing" and not self.shot:
            ax = int(self.aim_x)
            ay_top = self.arco_y - 16
            ay_bot = self.arco_y + self.arco_h + 8
            pygame.draw.line(screen, (255, 230, 0), (ax, ay_bot), (ax, ay_top), 3)
            pygame.draw.polygon(screen, (255, 230, 0), [
                (ax - 8, ay_top + 8),
                (ax + 8, ay_top + 8),
                (ax,     ay_top - 4),
            ])

        # ── Trayectoria ────────────────────────────────────────────────────────
        if len(self.trajectory) > 1:
            pygame.draw.lines(screen, (255, 255, 255), False,
                              self.trajectory, 2)

        # ── Balón ─────────────────────────────────────────────────────────────
        bx, by = int(self.ball_x), int(self.ball_y)
        sz = self.ball_size
        if self.balon_orig:
            bsurf = pygame.transform.scale(self.balon_orig, (sz, sz))
            screen.blit(bsurf, (bx, by))
        else:
            pygame.draw.circle(screen, (240, 240, 240),
                               (bx + sz // 2, by + sz // 2), sz // 2)
            pygame.draw.circle(screen, (60, 60, 60),
                               (bx + sz // 2, by + sz // 2), sz // 2, 2)
            # Pentagono central
            r = sz // 4
            pygame.draw.polygon(screen, (30, 30, 30), [
                (bx + sz // 2 + int(r * math.cos(math.tau * i / 5 - math.pi / 2)),
                 by + sz // 2 + int(r * math.sin(math.tau * i / 5 - math.pi / 2)))
                for i in range(5)
            ])

        # ── Partículas de gol ─────────────────────────────────────────────────
        for p in self.particles:
            r, g, b = p["color"]
            frac = max(0.0, p["life"] / 44)
            alpha = int(220 * frac)
            ps = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(ps, (r, g, b, alpha), (4, 4), 4)
            screen.blit(ps, (int(p["x"]) - 4, int(p["y"]) - 4))

        # ── HUD ───────────────────────────────────────────────────────────────
        self._draw_hud(screen, fonts)

        # ── Mensaje flash ─────────────────────────────────────────────────────
        if self.mensaje:
            self._draw_mensaje(screen, fonts)

        # ── Pantalla de resultado ─────────────────────────────────────────────
        if self.phase == "result":
            self._draw_result(screen, fonts)

    # ── Sub-dibujos ───────────────────────────────────────────────────────────

    def _draw_hud(self, screen, fonts):
        W = self.screen_w
        hud = pygame.Surface((W, 60), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 165))
        screen.blit(hud, (0, 0))

        fn = fonts.get("body") or fonts.get("small")
        if not fn:
            return

        if self.phase == "training":
            label = "ENTRENAMIENTO  —  ESPACIO / E para disparar"
            col_l = (255, 235, 80)
        elif self.phase == "playing":
            att_n = self.intento
            label = f"INTENTO {att_n}/{MAX_INTENTOS - 1}   ←→ apuntar   ESPACIO / E disparar"
            col_l = (210, 210, 210)
        elif self.phase == "pending":
            label = ""
            col_l = (200, 200, 200)
        else:
            label = "RESULTADO FINAL"
            col_l = (255, 220, 0)

        goles_surf = fn.render(f"⚽ Goles: {self.goles}", True, (100, 255, 100))
        screen.blit(goles_surf, (W - goles_surf.get_width() - 16, 14))
        if label:
            lbl_surf = fn.render(label, True, col_l)
            screen.blit(lbl_surf, (16, 14))

    def _draw_mensaje(self, screen, fonts):
        W, H = self.screen_w, self.screen_h
        fn = fonts.get("title") or fonts.get("body")
        if not fn:
            return
        colors = {
            "¡GOOOOL! ⚽":  (255, 230, 0),
            "¡ATAJADO!":    (255, 80, 80),
            "¡FALLASTE!":   (220, 80, 80),
            "¡BLOQUEADO!":  (220, 80, 80),
        }
        col = colors.get(self.mensaje, (255, 255, 255))
        sh  = fn.render(self.mensaje, True, (0, 0, 0))
        sf  = fn.render(self.mensaje, True, col)
        x   = W // 2 - sf.get_width() // 2
        y   = H // 2 - 70
        screen.blit(sh, (x + 3, y + 3))
        screen.blit(sf, (x, y))

    def _draw_result(self, screen, fonts):
        W, H = self.screen_w, self.screen_h
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 185))
        screen.blit(ov, (0, 0))

        fn_t = fonts.get("title") or fonts.get("body")
        fn_b = fonts.get("body") or fonts.get("small")
        if not fn_t:
            return

        gano   = self.goles >= WIN_THRESHOLD
        titulo = "¡VICTORIA!" if gano else "FIN DEL PARTIDO"
        col_t  = (255, 225, 0) if gano else (220, 80, 80)

        self._blit(screen, fn_t, titulo,
                   (W // 2, H // 2 - 110), col_t, cx=True)
        if fn_b:
            self._blit(screen, fn_b,
                       f"Goles: {self.goles}  de  {MAX_INTENTOS - 1}",
                       (W // 2, H // 2 - 40), (255, 255, 255), cx=True)
            if self.blink_ms < 700:
                self._blit(screen, fn_b,
                           "ESPACIO / E  para salir       R  para reintentar",
                           (W // 2, H // 2 + 36), (180, 180, 180), cx=True)

    @staticmethod
    def _blit(screen, font, text, pos, color, cx=False):
        surf = font.render(text, True, color)
        x, y = pos
        if cx:
            x -= surf.get_width() // 2
        screen.blit(surf, (x, y))
