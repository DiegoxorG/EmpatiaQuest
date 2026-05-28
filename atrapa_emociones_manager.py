"""
AtrapaEmocionesManager — Minijuego "Atrapa Emociones" integrado en EmpatiaQuest.

Mecánica:
  · Duración: 30 segundos con dificultad progresiva (3 niveles).
  · Emociones buenas y malas caen desde la parte superior.
  · ← → / A / D para mover al personaje horizontalmente.
  · Atrapar emoción buena: +10 puntos.
  · Atrapar emoción mala:  -1 vida (máximo 3 vidas).
  · Termina cuando se acaba el tiempo (victoria) o las vidas (derrota).
  · Retorna {"gano": bool, "tipo": "atrapa_emociones", "puntos": int}.

# 🎵 ASSET_BGM: Audio/BGM/minijuego_emociones.ogg  | música suave y emotiva
# 🎵 ASSET_SFX: Audio/SFX/emocion_buena.ogg        | tono positivo al atrapar buena
# 🎵 ASSET_SFX: Audio/SFX/emocion_mala.ogg         | sonido negativo al atrapar mala
"""

import math
import os
import random

import pygame

BASE_DIR   = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(
    BASE_DIR, "Imagenes", "Minijuegos", "atrapa_emociones", "imagenes_atrapa")

DURACION_MS   = 30_000   # 30 segundos
MAX_VIDAS     = 3
ALTURA_OBJ    = 64       # px base para emociones
TAM_JUGADOR   = 80       # px (cuadrado) para el sprite del jugador

# Mejor puntuación compartida durante la sesión
_session_best: dict = {"score": 0}


class AtrapaEmocionesManager:
    """Gestiona el minijuego de atrapa emociones completo."""

    def __init__(self, screen_w: int, screen_h: int, audio=None):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.audio    = audio
        self.result   = None   # None mientras corre; dict al terminar

        # ── Escala respecto a 1280×720 ────────────────────────────────────────
        self._sx = screen_w / 1280
        self._sy = screen_h / 720
        self._obj_h = max(40, int(ALTURA_OBJ * self._sy))
        self._jug_h = max(60, int(TAM_JUGADOR * self._sy))

        # ── Jugador ───────────────────────────────────────────────────────────
        self.jug_x   = float(screen_w // 2 - self._jug_h // 2)
        self.jug_y   = int(screen_h * 0.80)
        self.jug_spd = max(6, int(8 * self._sx))
        self._dir    = "frente"   # "frente" | "izq" | "der"

        # ── Estado ────────────────────────────────────────────────────────────
        self.puntos       = 0
        self.vidas        = MAX_VIDAS
        self.elapsed_ms   = 0
        self.spawn_acc    = 0
        self.spawn_period = 38   # frames entre spawns (disminuye con dificultad)
        self.obj_speed    = 3.0  # px/frame (aumenta con dificultad)
        self.objetos: list = []

        # Fase: "playing" | "result"
        self.phase    = "playing"
        self.blink_ms = 0
        self._gano    = False

        # ── Efectos visuales (splash al atrapar) ─────────────────────────────
        self.fx: list = []

        # ── Parpadeo de vida perdida ──────────────────────────────────────────
        self._vida_hit_ms = 0     # ms de efecto rojo en pantalla al perder vida

        # ── Carga de assets ───────────────────────────────────────────────────
        self._load_assets()

    # =========================================================================
    # Assets
    # =========================================================================

    def _load_img(self, fname: str):
        path = os.path.join(ASSETS_DIR, fname)
        try:
            img = pygame.image.load(path)
            ext = os.path.splitext(fname)[1].lower()
            return img.convert_alpha() if ext == ".png" else img.convert()
        except (OSError, pygame.error):
            return None

    def _scale_obj(self, img):
        if img is None:
            return None
        ow, oh = img.get_size()
        nw = max(1, int(ow * self._obj_h / oh))
        return pygame.transform.smoothscale(img, (nw, self._obj_h))

    def _scale_player(self, img):
        if img is None:
            return None
        return pygame.transform.smoothscale(img, (self._jug_h, self._jug_h))

    def _load_assets(self):
        # Fondo
        raw_bg = self._load_img("atras.jpeg")
        self.fondo = (
            pygame.transform.smoothscale(raw_bg, (self.screen_w, self.screen_h))
            if raw_bg else None
        )

        # Personaje (3 direcciones)
        self.img_frente = self._scale_player(self._load_img("frente.png"))
        self.img_izq    = self._scale_player(self._load_img("izquierda.png"))
        self.img_der    = self._scale_player(self._load_img("derecha.png"))

        # Corazón HUD — más ancho que alto
        heart_h = max(32, int(48 * self._sy))
        heart_w = max(46, int(74 * self._sx))
        raw_heart = self._load_img("corazon.png")
        if raw_heart:
            self.img_corazon       = pygame.transform.smoothscale(raw_heart, (heart_w, heart_h))
            self.img_corazon_vacio  = self.img_corazon.copy()
            self.img_corazon_vacio.set_alpha(55)
        else:
            self.img_corazon       = None
            self.img_corazon_vacio = None
        self._heart_sz = heart_w   # ancho usado para espaciado

        # Emociones buenas
        buenas_files = [
            "abrazo.png", "empatia.png", "feliz.png",
            "sol.png", "solidaridad.png", "corazon.png",
        ]
        self.imgs_buenas = [
            self._scale_obj(self._load_img(f)) for f in buenas_files
        ]
        self.imgs_buenas = [i for i in self.imgs_buenas if i is not None]

        # Emociones malas
        malas_files = [
            "burbujainsultos.png", "llorar.png", "notainsultos.png",
            "ira.png", "pelea.png",
        ]
        self.imgs_malas = [
            self._scale_obj(self._load_img(f)) for f in malas_files
        ]
        self.imgs_malas = [i for i in self.imgs_malas if i is not None]

    # =========================================================================
    # Spawn helpers
    # =========================================================================

    def _spawn_objeto(self):
        # 55 % bueno, 45 % malo
        tipo = "bueno" if random.random() < 0.55 else "malo"
        imgs = self.imgs_buenas if tipo == "bueno" else self.imgs_malas

        if imgs:
            img = random.choice(imgs)
            w   = img.get_width()
        else:
            img = None
            w   = self._obj_h

        x = random.randint(0, max(0, self.screen_w - w))
        self.objetos.append({
            "tipo": tipo,
            "img":  img,
            "x":    float(x),
            "y":    float(-self._obj_h - 10),
            "w":    w,
            "h":    self._obj_h,
            "spd":  self.obj_speed + random.uniform(-0.6, 0.6),
        })

    # =========================================================================
    # FX (splash de colores al atrapar)
    # =========================================================================

    def _add_fx(self, cx: int, cy: int, tipo: str):
        color_base = (80, 220, 80) if tipo == "bueno" else (220, 60, 60)
        for _ in range(14):
            a = random.uniform(0, math.tau)
            s = random.uniform(2, 8)
            self.fx.append({
                "x":    float(cx),
                "y":    float(cy),
                "vx":   math.cos(a) * s,
                "vy":   math.sin(a) * s,
                "life": random.randint(14, 22),
                "color": color_base,
            })

    def _update_fx(self):
        for f in self.fx[:]:
            f["x"] += f["vx"]
            f["y"] += f["vy"]
            f["life"] -= 1
            if f["life"] <= 0:
                self.fx.remove(f)

    # =========================================================================
    # Audio
    # =========================================================================

    def _sfx(self, name: str):
        if self.audio is not None:
            try:
                self.audio.play_sfx(name)
            except Exception:
                pass

    # =========================================================================
    # update() — llamado cada frame desde screen_handlers
    # =========================================================================

    def update(self, dt_ms: int):
        if self.result is not None:
            return self.result

        if self.phase == "result":
            self.blink_ms = (self.blink_ms + dt_ms) % 1200
            return None

        # Temporizador hit-rojo
        if self._vida_hit_ms > 0:
            self._vida_hit_ms -= dt_ms

        self.elapsed_ms += dt_ms
        self._update_fx()

        # ── Dificultad progresiva cada 10 s ──────────────────────────────────
        level = min(3, self.elapsed_ms // 10_000)
        self.obj_speed    = 3.0 + level * 1.5
        self.spawn_period = max(14, 38 - level * 7)

        # ── Movimiento del jugador ────────────────────────────────────────────
        keys = pygame.key.get_pressed()
        moviendo = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.jug_x = max(0.0, self.jug_x - self.jug_spd)
            self._dir  = "izq"
            moviendo   = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.jug_x = min(float(self.screen_w - self._jug_h),
                             self.jug_x + self.jug_spd)
            self._dir  = "der"
            moviendo   = True
        if not moviendo:
            self._dir = "frente"

        # ── Spawn ─────────────────────────────────────────────────────────────
        self.spawn_acc += 1
        if self.spawn_acc >= self.spawn_period:
            self._spawn_objeto()
            self.spawn_acc = 0

        # ── Mover objetos + colisiones ────────────────────────────────────────
        jug_rect    = pygame.Rect(int(self.jug_x), self.jug_y,
                                  self._jug_h, self._jug_h)
        hitbox_jug  = jug_rect.inflate(-22, -18)

        for obj in self.objetos[:]:
            obj["y"] += obj["spd"]
            obj_rect    = pygame.Rect(int(obj["x"]), int(obj["y"]),
                                      obj["w"], obj["h"])
            hitbox_obj  = obj_rect.inflate(-14, -14)

            if hitbox_jug.colliderect(hitbox_obj):
                cx = int(obj["x"] + obj["w"] / 2)
                cy = int(obj["y"] + obj["h"] / 2)
                if obj["tipo"] == "bueno":
                    self.puntos += 10
                    self._sfx("emocion_buena")
                else:
                    self.vidas -= 1
                    self._vida_hit_ms = 300
                    self._sfx("emocion_mala")
                self._add_fx(cx, cy, obj["tipo"])
                self.objetos.remove(obj)
                if self.vidas <= 0:
                    self._end_game(gano=False)
                    return None
                continue

            # Eliminar si sale por abajo
            if obj["y"] > self.screen_h + 30:
                self.objetos.remove(obj)

        # ── Fin de tiempo ─────────────────────────────────────────────────────
        if self.elapsed_ms >= DURACION_MS:
            self._end_game(gano=True)

        return None

    def _end_game(self, gano: bool):
        global _session_best
        self._gano = gano
        if self.puntos > _session_best["score"]:
            _session_best["score"] = self.puntos
        self.phase    = "result"
        self.blink_ms = 0

    # =========================================================================
    # handle_event() — llamado desde screen_handlers
    # =========================================================================

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN:
            return
        if self.phase == "result":
            CONFIRM = (pygame.K_RETURN, pygame.K_SPACE,
                       pygame.K_KP_ENTER, pygame.K_e)
            if event.key in CONFIRM:
                self.result = {
                    "gano":   self._gano,
                    "tipo":   "atrapa_emociones",
                    "puntos": self.puntos,
                }
            elif event.key == pygame.K_r:
                self._full_reset()

    def _full_reset(self):
        global _session_best
        self.puntos       = 0
        self.vidas        = MAX_VIDAS
        self.elapsed_ms   = 0
        self.spawn_acc    = 0
        self.spawn_period = 38
        self.obj_speed    = 3.0
        self.objetos      = []
        self.fx           = []
        self.phase        = "playing"
        self._gano        = False
        self._vida_hit_ms = 0
        self.jug_x        = float(self.screen_w // 2 - self._jug_h // 2)
        self._dir         = "frente"

    # =========================================================================
    # draw() — llamado cada frame desde renderer
    # =========================================================================

    def draw(self, screen: pygame.Surface, fonts: dict, **kwargs):
        W, H = self.screen_w, self.screen_h

        # ── Fondo ─────────────────────────────────────────────────────────────
        if self.fondo:
            screen.blit(self.fondo, (0, 0))
        else:
            screen.fill((15, 15, 35))
            # Farolillos procedurales como decoración
            for i in range(5):
                cx = int(W * (i + 0.5) / 5)
                pygame.draw.circle(screen, (60, 40, 100), (cx, H // 3), 30)
                pygame.draw.circle(screen, (120, 80, 180), (cx, H // 3), 26)

        # ── Objetos cayendo ───────────────────────────────────────────────────
        for obj in self.objetos:
            ox, oy = int(obj["x"]), int(obj["y"])
            if obj["img"]:
                screen.blit(obj["img"], (ox, oy))
            else:
                # Fallback: rectángulo con borde de color
                col    = (60, 200, 60) if obj["tipo"] == "bueno" else (200, 55, 55)
                brd    = (100, 255, 100) if obj["tipo"] == "bueno" else (255, 100, 100)
                pygame.draw.rect(screen, col,
                                 (ox, oy, obj["w"], obj["h"]),
                                 border_radius=10)
                pygame.draw.rect(screen, brd,
                                 (ox, oy, obj["w"], obj["h"]),
                                 2, border_radius=10)
                # Símbolo interior
                sym = "♥" if obj["tipo"] == "bueno" else "✕"
                fn_s = fonts.get("small")
                if fn_s:
                    s = fn_s.render(sym, True, (255, 255, 255))
                    screen.blit(s, (ox + obj["w"] // 2 - s.get_width() // 2,
                                    oy + obj["h"] // 2 - s.get_height() // 2))

        # ── Personaje ─────────────────────────────────────────────────────────
        px, py = int(self.jug_x), self.jug_y
        img_map = {"frente": self.img_frente, "izq": self.img_izq, "der": self.img_der}
        img_p   = img_map.get(self._dir)
        if img_p:
            screen.blit(img_p, (px, py))
        else:
            # Fallback: silueta rectangular
            pygame.draw.rect(screen, (80, 140, 230),
                             (px, py, self._jug_h, self._jug_h),
                             border_radius=12)
            pygame.draw.rect(screen, (160, 200, 255),
                             (px, py, self._jug_h, self._jug_h),
                             3, border_radius=12)
            fn_s = fonts.get("small")
            if fn_s:
                s = fn_s.render("★", True, (255, 255, 255))
                screen.blit(s, (px + self._jug_h // 2 - s.get_width() // 2,
                                py + self._jug_h // 2 - s.get_height() // 2))

        # ── FX de captura ──────────────────────────────────────────────────────
        for f in self.fx:
            r, g, b = f["color"]
            frac  = max(0.0, f["life"] / 22)
            alpha = int(200 * frac)
            ps = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(ps, (r, g, b, alpha), (4, 4), 4)
            screen.blit(ps, (int(f["x"]) - 4, int(f["y"]) - 4))

        # ── Flash rojo al perder vida ──────────────────────────────────────────
        if self._vida_hit_ms > 0:
            frac   = self._vida_hit_ms / 300
            alpha  = int(90 * frac)
            flash  = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((200, 0, 0, alpha))
            screen.blit(flash, (0, 0))

        # ── HUD ───────────────────────────────────────────────────────────────
        self._draw_hud(screen, fonts)

        # ── Pantalla de resultado ─────────────────────────────────────────────
        if self.phase == "result":
            self._draw_result(screen, fonts)

    # ── Sub-dibujos ───────────────────────────────────────────────────────────

    def _draw_hud(self, screen, fonts):
        W = self.screen_w
        hud = pygame.Surface((W, 64), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 170))
        screen.blit(hud, (0, 0))

        fn = fonts.get("body") or fonts.get("small")
        if not fn:
            return

        # Tiempo restante
        rem    = max(0, DURACION_MS - self.elapsed_ms)
        segs   = rem // 1000
        cents  = (rem % 1000) // 10
        t_txt  = f"{segs:02d}.{cents:02d}s"
        t_surf = fn.render(t_txt, True, (255, 230, 60))
        screen.blit(t_surf, (16, 16))

        # Puntos (centrado)
        p_surf = fn.render(f"Puntos: {self.puntos}", True, (100, 255, 120))
        screen.blit(p_surf, (W // 2 - p_surf.get_width() // 2, 16))

        # Vidas (derecha) — corazones imagen
        hsz = self._heart_sz
        hh  = self.img_corazon.get_height() if self.img_corazon else hsz
        gap = max(6, int(10 * self._sx))
        total_w = MAX_VIDAS * hsz + (MAX_VIDAS - 1) * gap
        hx = W - total_w - 16
        hy = (64 - hh) // 2
        for i in range(MAX_VIDAS):
            img = self.img_corazon if i < self.vidas else self.img_corazon_vacio
            if img:
                screen.blit(img, (hx + i * (hsz + gap), hy))
            else:
                col = (255, 80, 80) if i < self.vidas else (80, 40, 40)
                pygame.draw.rect(screen, col, (hx + i * (hsz + gap), hy, hsz, hsz), border_radius=4)

    def _draw_result(self, screen, fonts):
        W, H = self.screen_w, self.screen_h
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 190))
        screen.blit(ov, (0, 0))

        fn_t = fonts.get("title") or fonts.get("body")
        fn_b = fonts.get("body") or fonts.get("small")
        if not fn_t:
            return

        gano   = self._gano
        titulo = "¡LO LOGRASTE!" if gano else "¡SE ACABÓ!"
        col_t  = (80, 255, 120) if gano else (220, 80, 80)

        self._blit(screen, fn_t, titulo,
                   (W // 2, H // 2 - 120), col_t, cx=True)

        if fn_b:
            best = _session_best["score"]
            self._blit(screen, fn_b,
                       f"Puntos obtenidos: {self.puntos}",
                       (W // 2, H // 2 - 48), (255, 255, 255), cx=True)
            self._blit(screen, fn_b,
                       f"Mejor puntuación (sesión): {best}",
                       (W // 2, H // 2 + 6), (200, 200, 100), cx=True)

            # Hint parpadeante
            if self.blink_ms < 700:
                self._blit(screen, fn_b,
                           "ESPACIO / E  para salir       R  para reintentar",
                           (W // 2, H // 2 + 66), (180, 180, 180), cx=True)

    @staticmethod
    def _blit(screen, font, text, pos, color, cx=False):
        surf = font.render(text, True, color)
        x, y = pos
        if cx:
            x -= surf.get_width() // 2
        screen.blit(surf, (x, y))
