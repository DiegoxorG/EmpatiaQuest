"""
MinigameManager — Minijuegos estilo Undertale para EmpatiaQuest.

Dos modos:
  "agresivo" → proyectil Puño.png, oleadas de boxeo
  "pacifico" → proyectiles Mensaje_X.png, oleadas de insultos

Retorna al terminar: {"ganó": bool, "tipo": "agresivo"|"pacifico"}

# 🎵 ASSET_SFX: Audio/SFX/hit_corazon.ogg | golpe recibido por el corazón
# 🎵 ASSET_SFX: Audio/SFX/minijuego_ganar.ogg | fanfare de victoria
# 🎵 ASSET_SFX: Audio/SFX/minijuego_perder.ogg | derrota
# 🎶 ASSET_BGM: Audio/BGM/minijuego_batalla.ogg | música tensa 60 segundos
"""

import json
import math
import os
import random

import pygame

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "Imagenes", "Minijuegos", "Undertale")
MINIJUEGO_CONFIG_PATH = os.path.join(BASE_DIR, "Hitboxes", "minijuego_config.json")

HUD_MARGIN = 90         # px por encima del área de batalla (vidas + barra)
BATTLE_W   = 1260
BATTLE_H   = 610
HEART_SPEED = 8         # px por frame (≈ 480 px/s @ 60 FPS)
MAX_LIVES = 3
DURATION_MS = 60_000    # 60 segundos
INVINCIBILITY_MS = 1_500
FLASH_FRAMES = 3
SHAKE_MS = 300
# Hitboxes rectangulares + escala por defecto (editables en Editores/personaje_editor.py → minijuego_config.json)
MINI_HITBOX_DEFAULTS = {
    "heart":   {"w_ratio": 0.50, "h_ratio": 0.50, "offset_x_ratio": 0.25, "offset_y_ratio": 0.25, "scale": 4.0},
    "fist":    {"w_ratio": 0.50, "h_ratio": 0.50, "offset_x_ratio": 0.25, "offset_y_ratio": 0.25, "scale": 4.0},
    "message": {"w_ratio": 0.70, "h_ratio": 0.60, "offset_x_ratio": 0.15, "offset_y_ratio": 0.20, "scale": 3.0},
}

# Intervalos de aparición de proyectiles (en ms) por oleada
AGRESIVO_SPAWN_INTERVALS = [2200, 2800, 1800, 1200]  # oleadas 0-3
PACIFICO_SPAWN_INTERVALS  = [3000, 0, 0, 0]           # solo oleada 0 usa timer

CUSTOM_TEXT_VARIANTS = {
    "insultos_sara": {
        "base": "pacifico",
        "duration_ms": 45_000,
        "max_lives": 4,
        "phrases": [
            "Metete en tus asuntos",
            "Ahora eres su heroe?",
            "Que ridiculo",
            "Nadie te pidio ayuda",
            "Dejala sola",
            "Solo es una broma",
            "No deberias meterte",
        ],
        "pre": [("Grupo", "Si vas a defenderla, aguanta lo que digan.")],
        "win": [("Grupo", "Ya... ya estuvo.")],
        "lose": [("Grupo", "Viste? Mejor no te metas.")],
    },
    "rumores_valeria": {
        "base": "pacifico",
        "duration_ms": 40_000,
        "max_lives": 3,
        "phrases": [
            "Dicen que fue por ella",
            "Seguro exagera",
            "Todos ya lo saben",
            "Que drama",
            "No la defiendas",
            "Algo habra hecho",
            "Mira como camina",
        ],
        "pre": [("Pasillo", "Los rumores vienen de todos lados.")],
        "win": [("Pasillo", "Las voces empiezan a apagarse.")],
        "lose": [("Pasillo", "El ruido pesa demasiado.")],
    },
}

PRE_DIALOGS = {
    "agresivo": [("Bully", "¿Quieres pelear? ¡Muy bien!")],
    "pacifico": [("Bully", "¿Crees que puedes defenderlo? ¡Inténtalo!")],
}
POST_DIALOGS_WIN = {
    "agresivo": [("Bully", "Agh, vale... me has ganado esta vez.")],
    "pacifico": [("Bully", "¿Ah sí? Pues... ¡Agh, cállate!")],
}
POST_DIALOGS_LOSE = {
    "agresivo": [("Bully", "Eres otro fracasado igual que él.")],
    "pacifico": [("Bully", "¿Ves? No tienes razón en nada.\nMejor te hubieras quedado callado.")],
}


def _load_minijuego_config():
    try:
        with open(MINIJUEGO_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


class MinigameManager:
    """Gestiona un minijuego completo (pre-diálogo → juego → resultado)."""

    def __init__(self, tipo: str, screen_w: int, screen_h: int, audio=None):
        self.variant = tipo
        self.variant_cfg = CUSTOM_TEXT_VARIANTS.get(tipo, {})
        self.tipo = self.variant_cfg.get("base", tipo)
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.audio = audio
        self.result = None  # None mientras corre; dict al terminar
        self.max_lives = int(self.variant_cfg.get("max_lives", MAX_LIVES))
        self.duration_ms = int(self.variant_cfg.get("duration_ms", DURATION_MS))

        # Área de batalla: ancho centrado, altura fijada con margen superior para HUD
        self.battle_rect = pygame.Rect(
            screen_w // 2 - BATTLE_W // 2,
            HUD_MARGIN,
            BATTLE_W, BATTLE_H,
        )

        # Corazón
        self.heart_x = float(self.battle_rect.centerx)
        self.heart_y = float(self.battle_rect.centery)
        self.lives = self.max_lives
        self.invincible_ms = 0
        self.blink_visible = True
        self.blink_acc_ms = 0

        # Tiempo y oleadas
        self.elapsed_ms = 0
        self.wave = -1
        self.spawn_timer_ms = 0
        self.wave_initialized = False

        # Proyectiles y avisos
        self.projectiles = []
        self.warnings = []

        # Efectos visuales
        self.flash_frames = 0
        self.shake_ms = 0
        self.shake_offset = (0, 0)

        # Fases: "pre_dialog" → "playing" → "ending_flash" → "post_dialog" → done
        self.phase = "pre_dialog"
        self.dialog_step = 0
        self.ending_won = False
        self.ending_flash_ms = 0
        self.post_dialog_step = 0

        # Cargar config ANTES de _load_assets (necesita scale y ratios)
        cfg = _load_minijuego_config()
        self.hitbox_cfg = {}
        for key, defaults in MINI_HITBOX_DEFAULTS.items():
            stored = cfg.get(key, {})
            self.hitbox_cfg[key] = {k: float(stored.get(k, defaults[k])) for k in defaults}

        self._load_assets()  # usa self.hitbox_cfg["*"]["scale"] para tamaño de sprites

    # ── Carga de assets ───────────────────────────────────────────────────────

    def _load_img(self, filename: str):
        path = os.path.join(ASSETS_DIR, filename)
        try:
            return pygame.image.load(path).convert_alpha()
        except (OSError, pygame.error):
            return None

    def _load_assets(self):
        raw_heart = self._load_img("Corazon.png")
        raw_fondo = self._load_img("Fondo.png")

        if raw_fondo:
            self.fondo_img = pygame.transform.smoothscale(raw_fondo, (BATTLE_W, BATTLE_H))
        else:
            self.fondo_img = None

        # Corazón — tamaño definido por scale del editor
        heart_scale = self.hitbox_cfg["heart"]["scale"]
        if raw_heart:
            rw, rh = raw_heart.get_size()
            tw = max(1, int(rw * heart_scale))
            th = max(1, int(rh * heart_scale))
            self.heart_img = pygame.transform.smoothscale(raw_heart, (tw, th))
            self.heart_w, self.heart_h = tw, th
        else:
            self.heart_img = None
            self.heart_w = self.heart_h = int(80 * heart_scale / 4.0)  # fallback proporcional

        # Proyectiles
        if self.tipo == "agresivo":
            raw = self._load_img("Puño.png")
            fist_scale = self.hitbox_cfg["fist"]["scale"]
            if raw:
                rw, rh = raw.get_size()
                tw = max(1, int(rw * fist_scale))
                th = max(1, int(rh * fist_scale))
                self.proj_imgs = [pygame.transform.smoothscale(raw, (tw, th))]
            else:
                self.proj_imgs = [None]
        else:
            self.proj_imgs = []
            msg_scale = self.hitbox_cfg["message"]["scale"]
            for i in range(2, 9):
                img = self._load_img(f"Mensaje_{i}.png") or self._load_img(f"Mensaje_ {i}.png")
                if img:
                    rw, rh = img.get_size()
                    tw = max(1, int(rw * msg_scale))
                    th = max(1, int(rh * msg_scale))
                    img = pygame.transform.smoothscale(img, (tw, th))
                self.proj_imgs.append(img)

    # ── API pública ───────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key not in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            return

        if self.phase == "pre_dialog":
            if self.audio is not None:
                self.audio.sfx_dialogo()
            self.dialog_step += 1
            if self.dialog_step >= len(self._pre_dialogs()):
                self.phase = "playing"
                self.wave = -1
                self.elapsed_ms = 0
                if self.audio is not None:
                    self.audio.play_sfx("oleada")

        elif self.phase == "post_dialog":
            if self.audio is not None:
                self.audio.sfx_dialogo()
            self.post_dialog_step += 1
            post = self._post_dialogs()
            if self.post_dialog_step >= len(post):
                self.result = {"ganó": self.ending_won, "tipo": self.tipo}

            if self.result is not None:
                self.result["tipo"] = self.variant

    def update(self, dt_ms: int):
        if self.result is not None:
            return self.result

        dt_ms = max(1, dt_ms)

        if self.flash_frames > 0:
            self.flash_frames -= 1

        if self.shake_ms > 0:
            self.shake_ms -= dt_ms
            mag = 8
            self.shake_offset = (random.randint(-mag, mag), random.randint(-mag, mag))
        else:
            self.shake_offset = (0, 0)

        if self.phase == "pre_dialog":
            return None

        if self.phase == "playing":
            self._update_playing(dt_ms)
        elif self.phase == "ending_flash":
            self.ending_flash_ms += dt_ms
            if self.ending_flash_ms >= 2000:
                self.phase = "post_dialog"
                self.post_dialog_step = 0
        elif self.phase == "post_dialog":
            pass

        return self.result

    def draw(self, screen: pygame.Surface, base_fonts: dict, show_hitboxes: bool = False):
        screen.fill((10, 10, 16))

        if self.phase == "pre_dialog":
            dialog = self._pre_dialogs()
            step = min(self.dialog_step, len(dialog) - 1)
            self._draw_dialog_box(screen, base_fonts, *dialog[step])
            return

        sx, sy = self.shake_offset
        br = self.battle_rect.move(sx, sy)

        if self.fondo_img:
            screen.blit(self.fondo_img, br.topleft)
        else:
            pygame.draw.rect(screen, (30, 28, 50), br)
        pygame.draw.rect(screen, (255, 255, 255), br, 5)

        for w in self.warnings:
            self._draw_warning(screen, w, sx, sy)
        for p in self.projectiles:
            self._draw_projectile(screen, p, sx, sy)

        if self.phase == "playing":
            if self.blink_visible:
                self._draw_heart(screen, int(self.heart_x) + sx, int(self.heart_y) + sy)
        else:
            self._draw_heart(screen, int(self.heart_x) + sx, int(self.heart_y) + sy)

        # Hitboxes de depuración
        if show_hitboxes:
            self._draw_hitboxes(screen, sx, sy)

        if self.flash_frames > 0:
            alpha = int((self.flash_frames / FLASH_FRAMES) * 120)
            surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            surf.fill((255, 0, 0, alpha))
            screen.blit(surf, (0, 0))

        self._draw_lives(screen, sx, sy)
        self._draw_time_bar(screen, sx, sy)

        if self.phase == "ending_flash":
            self._draw_ending_flash(screen, base_fonts)
        elif self.phase == "post_dialog":
            self._draw_ending_flash(screen, base_fonts)
            post = self._post_dialogs()
            step = min(self.post_dialog_step, len(post) - 1)
            self._draw_dialog_box(screen, base_fonts, *post[step])

    # ── Lógica de juego ───────────────────────────────────────────────────────

    def _update_playing(self, dt_ms: int):
        self.elapsed_ms += dt_ms

        new_wave = min(3, self.elapsed_ms // 15_000)
        if new_wave != self.wave:
            self.wave = new_wave
            self._on_wave_start()

        if self.invincible_ms > 0:
            self.invincible_ms -= dt_ms
            self.blink_acc_ms += dt_ms
            if self.blink_acc_ms >= 100:
                self.blink_acc_ms = 0
                self.blink_visible = not self.blink_visible
        else:
            self.blink_visible = True

        keys = pygame.key.get_pressed()
        dx = ((1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0)
              - (1 if keys[pygame.K_a] or keys[pygame.K_LEFT]  else 0)) * HEART_SPEED
        dy = ((1 if keys[pygame.K_s] or keys[pygame.K_DOWN]  else 0)
              - (1 if keys[pygame.K_w] or keys[pygame.K_UP]   else 0)) * HEART_SPEED
        hw2, hh2 = self.heart_w // 2, self.heart_h // 2
        self.heart_x = max(self.battle_rect.left  + hw2,
                           min(self.battle_rect.right  - hw2, self.heart_x + dx))
        self.heart_y = max(self.battle_rect.top   + hh2,
                           min(self.battle_rect.bottom - hh2, self.heart_y + dy))

        use_timer = (self.tipo == "agresivo") or (self.tipo == "pacifico" and self.wave == 0)
        if use_timer:
            interval = (AGRESIVO_SPAWN_INTERVALS[self.wave]
                        if self.tipo == "agresivo"
                        else PACIFICO_SPAWN_INTERVALS[self.wave])
            if interval > 0:
                self.spawn_timer_ms += dt_ms
                if self.spawn_timer_ms >= interval:
                    self.spawn_timer_ms = 0
                    self._spawn_wave_pattern()

        new_warnings = []
        for w in self.warnings:
            w["timer_ms"] -= dt_ms
            if w["timer_ms"] > 0:
                new_warnings.append(w)
            else:
                self._spawn_from_warning(w)
        self.warnings = new_warnings

        alive = []
        hit_this_frame = False
        for p in self.projectiles:
            self._move_projectile(p)
            in_bounds = self._proj_in_bounds(p)
            bouncing = p.get("ptype") == "bouncing"
            if not in_bounds and not bouncing:
                continue
            if not hit_this_frame and self.invincible_ms <= 0 and self._hits_heart(p):
                self._take_hit()
                hit_this_frame = True
                if not bouncing:
                    continue
            alive.append(p)
        self.projectiles = alive

        if self.elapsed_ms >= self.duration_ms:
            self._start_ending(won=True)
        elif self.lives <= 0:
            self._start_ending(won=False)

    def _on_wave_start(self):
        self.spawn_timer_ms = 0
        self.wave_initialized = False
        if self.audio is not None and self.wave >= 0:
            self.audio.play_sfx("oleada", 0.8)

        if self.tipo == "pacifico":
            if self.wave == 1:
                self.projectiles = []
                self.warnings = []
                self._spawn_pacifico_wave1_init()
                self.wave_initialized = True
            elif self.wave == 2:
                self.projectiles = []
                self.warnings = []
                self._spawn_pacifico_wave2_init()
                self.wave_initialized = True
            elif self.wave == 3:
                self.projectiles = []
                self.warnings = []
                self._spawn_pacifico_wave3_init()
                self.wave_initialized = True
        elif self.tipo == "agresivo":
            self.projectiles = []
            self.warnings = []

    # ── Helpers de spawn ──────────────────────────────────────────────────────

    def _rand_size_scale(self) -> float:
        if random.random() < 0.4:
            return random.uniform(0.5, 1.8)
        return 1.0

    def _mk_agresivo_spawn(self, x: float, y: float, vx: float, vy: float) -> dict:
        angle = math.degrees(math.atan2(vy, vx)) + 180.0 if (vx or vy) else 180.0
        return {
            "x": float(x), "y": float(y), "vx": float(vx), "vy": float(vy),
            "img_idx": 0,
            "angle": angle,
            "ptype": "straight",
            "orient_to_velocity": True,
            "size_scale": self._rand_size_scale(),
        }

    def _rand_msg_idx(self) -> int:
        return random.randint(0, max(0, len(self.proj_imgs) - 1))

    def _rand_phrase(self) -> str:
        phrases = self.variant_cfg.get("phrases") or []
        return random.choice(phrases) if phrases else ""

    def _pre_dialogs(self):
        return self.variant_cfg.get("pre") or PRE_DIALOGS[self.tipo]

    def _post_dialogs(self):
        if self.ending_won:
            return self.variant_cfg.get("win") or POST_DIALOGS_WIN[self.tipo]
        return self.variant_cfg.get("lose") or POST_DIALOGS_LOSE[self.tipo]

    # ── Spawning agresivo ─────────────────────────────────────────────────────

    def _spawn_wave_pattern(self):
        if self.tipo == "agresivo":
            self._spawn_agresivo()
        else:
            self._spawn_pacifico_wave0()

    def _spawn_agresivo(self):
        br = self.battle_rect
        wave = self.wave

        if wave == 0:
            for side in range(2):
                y = float(random.randint(br.top + 30, br.bottom - 30))
                if side == 0:
                    x, vx = float(br.left - 50), 4.0
                else:
                    x, vx = float(br.right + 50), -4.0
                self.warnings.append({
                    "timer_ms": 500, "orig_timer_ms": 500,
                    "wtype": "h_line",
                    "y": y,
                    "spawn": self._mk_agresivo_spawn(x, y, vx, 0.0),
                })

        elif wave == 1:
            corners = [
                (float(br.left - 50),  float(br.top - 50),     5.0,  5.0),
                (float(br.right + 50), float(br.top - 50),    -5.0,  5.0),
                (float(br.left - 50),  float(br.bottom + 50),  5.0, -5.0),
                (float(br.right + 50), float(br.bottom + 50), -5.0, -5.0),
            ]
            for cx, cy, vx, vy in random.sample(corners, 3):
                self.warnings.append({
                    "timer_ms": 500, "orig_timer_ms": 500,
                    "wtype": "corner",
                    "x": cx, "y": cy,
                    "spawn": self._mk_agresivo_spawn(cx, cy, vx, vy),
                })

        elif wave == 2:
            for _ in range(5):
                x = float(random.randint(br.left + 20, br.right - 20))
                y = float(br.top - 50)
                self.warnings.append({
                    "timer_ms": 400, "orig_timer_ms": 400,
                    "wtype": "v_marker",
                    "x": x,
                    "spawn": self._mk_agresivo_spawn(x, y, 0.0, 6.0),
                })

        elif wave == 3:
            pattern = random.randint(0, 2)
            if pattern == 0:
                for side in range(2):
                    y = float(random.randint(br.top + 30, br.bottom - 30))
                    x  = float(br.left - 50) if side == 0 else float(br.right + 50)
                    vx = 8.0 if side == 0 else -8.0
                    self.projectiles.append(self._mk_agresivo_spawn(x, y, vx, 0.0))
            elif pattern == 1:
                cx, cy, vx, vy = random.choice([
                    (float(br.left - 50),  float(br.top - 50),     8.0,  8.0),
                    (float(br.right + 50), float(br.top - 50),    -8.0,  8.0),
                    (float(br.left - 50),  float(br.bottom + 50),  8.0, -8.0),
                    (float(br.right + 50), float(br.bottom + 50), -8.0, -8.0),
                ])
                self.projectiles.append(self._mk_agresivo_spawn(cx, cy, vx, vy))
            else:
                x = float(random.randint(br.left + 20, br.right - 20))
                self.projectiles.append(self._mk_agresivo_spawn(x, float(br.top - 50), 0.0, 8.0))

    # ── Spawning pacífico ─────────────────────────────────────────────────────

    def _spawn_pacifico_wave0(self):
        br = self.battle_rect
        for _ in range(2):
            y = float(random.randint(br.top + 40, br.bottom - 40))
            amp = random.choice([-90.0, 90.0])
            img_idx = self._rand_msg_idx()
            spawn = {
                "x": float(br.left - 50), "y": y,
                "vx": 3.5, "vy": 0.0,
                "img_idx": img_idx, "angle": 0.0,
                "ptype": "arc",
                "arc_amp": amp,
                "arc_origin_y": y,
                "arc_total_x": float(br.width + 100),
                "arc_x0": float(br.left - 50),
                "size_scale": self._rand_size_scale(),
                "text": self._rand_phrase(),
            }
            self.warnings.append({
                "timer_ms": 600, "orig_timer_ms": 600,
                "wtype": "ghost",
                "x": float(br.left - 50), "y": y,
                "img_idx": img_idx,
                "spawn": spawn,
            })

    def _spawn_pacifico_wave1_init(self):
        br = self.battle_rect
        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            self.projectiles.append({
                "x": float(br.centerx + random.randint(-100, 100)),
                "y": float(br.centery + random.randint(-80, 80)),
                "vx": 4.0 * math.cos(angle),
                "vy": 4.0 * math.sin(angle),
                "img_idx": self._rand_msg_idx(),
                "angle": 0.0,
                "ptype": "bouncing",
                "size_scale": self._rand_size_scale(),
                "text": self._rand_phrase(),
            })

    def _spawn_pacifico_wave2_init(self):
        br = self.battle_rect
        for i in range(4):
            start_angle = i * 90.0
            self.projectiles.append({
                "x": float(br.centerx),
                "y": float(br.centery),
                "vx": 0.0, "vy": 0.0,
                "img_idx": self._rand_msg_idx(),
                "angle": start_angle,
                "ptype": "spiral",
                "spiral_angle": start_angle,
                "spiral_r": 0.0,
                "spiral_dr": 0.8,
                "size_scale": self._rand_size_scale(),
                "text": self._rand_phrase(),
            })

    def _spawn_pacifico_wave3_init(self):
        br = self.battle_rect
        n = min(7, max(1, len(self.proj_imgs)))
        for i in range(n):
            angle = random.uniform(0, 2 * math.pi)
            vx = 5.0 * math.cos(angle)
            vy = 5.0 * math.sin(angle)
            side = random.randint(0, 3)
            if side == 0:
                x, y = float(br.left - 50), float(random.randint(br.top, br.bottom))
            elif side == 1:
                x, y = float(br.right + 50), float(random.randint(br.top, br.bottom))
            elif side == 2:
                x, y = float(random.randint(br.left, br.right)), float(br.top - 50)
            else:
                x, y = float(random.randint(br.left, br.right)), float(br.bottom + 50)
            self.projectiles.append({
                "x": x, "y": y, "vx": vx, "vy": vy,
                "img_idx": i % len(self.proj_imgs),
                "angle": 0.0, "ptype": "straight",
                "size_scale": self._rand_size_scale(),
                "text": self._rand_phrase(),
            })

    def _spawn_from_warning(self, w: dict):
        if "spawn" in w:
            self.projectiles.append(dict(w["spawn"]))
            if self.audio is not None:
                self.audio.play_sfx("aviso_ataque", 0.45)

    # ── Movimiento de proyectiles ─────────────────────────────────────────────

    def _move_projectile(self, p: dict):
        ptype = p.get("ptype", "straight")

        if ptype == "straight":
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p.get("orient_to_velocity") and (p["vx"] != 0.0 or p["vy"] != 0.0):
                # Orienta el sprite en la dirección de movimiento
                p["angle"] = math.degrees(math.atan2(p["vy"], p["vx"])) + 180.0
            else:
                p["angle"] = (p.get("angle", 0.0) + 3.0) % 360.0

        elif ptype == "bouncing":
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            br = self.battle_rect
            img_idx = p.get("img_idx", 0)
            img = None if p.get("text") else (
                self.proj_imgs[img_idx] if 0 <= img_idx < len(self.proj_imgs) else None
            )
            sc = p.get("size_scale", 1.0)
            hw = int((img.get_width()  // 2) * sc) if img else 30
            hh = int((img.get_height() // 2) * sc) if img else 20
            if p["x"] - hw <= br.left or p["x"] + hw >= br.right:
                p["vx"] *= -1
                p["x"] = max(br.left + hw, min(br.right - hw, p["x"]))
            if p["y"] - hh <= br.top or p["y"] + hh >= br.bottom:
                p["vy"] *= -1
                p["y"] = max(br.top + hh, min(br.bottom - hh, p["y"]))
            p["angle"] = (p.get("angle", 0.0) + 2.0) % 360.0

        elif ptype == "spiral":
            p["spiral_r"] += p["spiral_dr"]
            p["spiral_angle"] = (p["spiral_angle"] + 2.0) % 360.0
            rad = math.radians(p["spiral_angle"])
            r = p["spiral_r"]
            p["x"] = self.battle_rect.centerx + r * math.cos(rad)
            p["y"] = self.battle_rect.centery  + r * math.sin(rad)
            p["angle"] = p["spiral_angle"]

        elif ptype == "arc":
            p["x"] += p["vx"]
            traveled = p["x"] - p["arc_x0"]
            total = p.get("arc_total_x", float(BATTLE_W + 100))
            t = traveled / max(1.0, total)
            amp = p.get("arc_amp", 0.0)
            p["y"] = p["arc_origin_y"] + amp * 4.0 * t * (1.0 - t)

    # ── Colisiones ────────────────────────────────────────────────────────────

    def _proj_in_bounds(self, p: dict) -> bool:
        br = self.battle_rect
        margin = 200
        return (br.left - margin <= p["x"] <= br.right  + margin and
                br.top  - margin <= p["y"] <= br.bottom + margin)

    def _get_heart_rect(self) -> pygame.Rect:
        """Hitbox rectangular del corazón según ratios del editor."""
        hcfg = self.hitbox_cfg["heart"]
        iw, ih = self.heart_w, self.heart_h
        x = self.heart_x - iw // 2 + iw * hcfg["offset_x_ratio"]
        y = self.heart_y - ih // 2 + ih * hcfg["offset_y_ratio"]
        return pygame.Rect(int(x), int(y),
                           max(4, int(iw * hcfg["w_ratio"])),
                           max(4, int(ih * hcfg["h_ratio"])))

    def _get_proj_obb(self, p: dict) -> tuple:
        """OBB del proyectil (cx, cy, half_w, half_h, cos_a, sin_a), rotado igual que el sprite.

        La rotación visual es pygame.transform.rotate(img, -angle) = CW por angle grados.
        CW en pantalla: (local_x, local_y) → (x·cos + y·sin, −x·sin + y·cos).
        """
        sc = p.get("size_scale", 1.0)
        pkey = "fist" if self.tipo == "agresivo" else "message"
        pcfg = self.hitbox_cfg[pkey]
        img_idx = p.get("img_idx", 0)
        img = None if p.get("text") else (self.proj_imgs[img_idx] if 0 <= img_idx < len(self.proj_imgs) else None)
        if img:
            iw = max(1, int(img.get_width()  * sc))
            ih = max(1, int(img.get_height() * sc))
        elif p.get("text"):
            iw = max(110, int(18 * len(str(p.get("text", ""))) * sc))
            ih = max(42, int(48 * sc))
        else:
            iw = ih = max(1, int(80 * sc))
        half_w = max(2, int(iw * pcfg["w_ratio"])  // 2)
        half_h = max(2, int(ih * pcfg["h_ratio"])   // 2)
        # Centro de la hitbox en espacio local (relativo al centro del sprite)
        local_x = iw * (pcfg["offset_x_ratio"] + pcfg["w_ratio"]  / 2 - 0.5)
        local_y = ih * (pcfg["offset_y_ratio"] + pcfg["h_ratio"] / 2 - 0.5)
        # Rotación CW en pantalla = pygame.transform.rotate(img, -angle)
        # En coords de pantalla (y abajo): x' = x·cosθ − y·sinθ, y' = x·sinθ + y·cosθ
        angle_rad = math.radians(p.get("angle", 0.0))
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        world_cx = p["x"] + local_x * cos_a - local_y * sin_a
        world_cy = p["y"] + local_x * sin_a + local_y * cos_a
        return world_cx, world_cy, half_w, half_h, cos_a, sin_a

    def _obb_vs_aabb(self, obb: tuple, rect: pygame.Rect) -> bool:
        """SAT: OBB (cx, cy, hw, hh, cos_a, sin_a) contra AABB pygame.Rect."""
        cx, cy, hw, hh, cos_a, sin_a = obb
        ux, uy =  cos_a,  sin_a   # eje local +x del OBB tras rotación CW
        vx, vy = -sin_a,  cos_a   # eje local +y del OBB tras rotación CW
        obb_c = [
            (cx + hw*ux + hh*vx, cy + hw*uy + hh*vy),
            (cx + hw*ux - hh*vx, cy + hw*uy - hh*vy),
            (cx - hw*ux + hh*vx, cy - hw*uy + hh*vy),
            (cx - hw*ux - hh*vx, cy - hw*uy - hh*vy),
        ]
        l, r, t, b = rect.left, rect.right, rect.top, rect.bottom
        aabb_c = [(l,t),(r,t),(r,b),(l,b)]
        for ax, ay in [(1,0),(0,1),(ux,uy),(vx,vy)]:
            op = [ax*px+ay*py for px,py in obb_c]
            ap = [ax*px+ay*py for px,py in aabb_c]
            if max(op) < min(ap) or max(ap) < min(op):
                return False
        return True

    def _get_spawn_hitbox_size(self, spawn: dict) -> tuple:
        """Devuelve (w_hitbox, h_hitbox) en px para un descriptor de spawn (sin rotar)."""
        sc = spawn.get("size_scale", 1.0)
        pkey = "fist" if self.tipo == "agresivo" else "message"
        pcfg = self.hitbox_cfg[pkey]
        img_idx = spawn.get("img_idx", 0)
        img = None if spawn.get("text") else (self.proj_imgs[img_idx] if 0 <= img_idx < len(self.proj_imgs) else None)
        if img:
            iw = max(1, int(img.get_width()  * sc))
            ih = max(1, int(img.get_height() * sc))
        elif spawn.get("text"):
            iw = max(110, int(18 * len(str(spawn.get("text", ""))) * sc))
            ih = max(42, int(48 * sc))
        else:
            iw = ih = max(1, int(80 * sc))
        return max(4, int(iw * pcfg["w_ratio"])), max(4, int(ih * pcfg["h_ratio"]))

    def _hits_heart(self, p: dict) -> bool:
        return self._obb_vs_aabb(self._get_proj_obb(p), self._get_heart_rect())

    def _take_hit(self):
        self.lives -= 1
        self.invincible_ms = INVINCIBILITY_MS
        self.blink_acc_ms = 0
        self.blink_visible = True
        self.flash_frames = FLASH_FRAMES
        self.shake_ms = SHAKE_MS
        if self.audio is not None:
            self.audio.play_sfx("hit_corazon")
        # 🎵 ASSET_SFX: Audio/SFX/hit_corazon.ogg | golpe recibido por el corazón

    def _start_ending(self, won: bool):
        self.ending_won = won
        self.phase = "ending_flash"
        self.ending_flash_ms = 0
        self.projectiles.clear()
        self.warnings.clear()
        if self.audio is not None:
            self.audio.play_sfx("minijuego_ganar" if won else "minijuego_perder")
        # 🎵 ASSET_SFX: Audio/SFX/minijuego_ganar.ogg | fanfare de victoria (si won)
        # 🎵 ASSET_SFX: Audio/SFX/minijuego_perder.ogg | derrota (si not won)

    # ── Dibujo ────────────────────────────────────────────────────────────────

    def _draw_heart(self, screen: pygame.Surface, x: int, y: int):
        if self.heart_img:
            screen.blit(self.heart_img, (x - self.heart_w // 2, y - self.heart_h // 2))
        else:
            size = max(28, self.heart_h // 2)
            pygame.draw.polygon(screen, (220, 30, 50), [
                (x, y - size),
                (x - size, y + size // 2),
                (x + size, y + size // 2),
            ])
            pygame.draw.polygon(screen, (255, 80, 80), [
                (x, y - size),
                (x - size, y + size // 2),
                (x + size, y + size // 2),
            ], 2)

    def _draw_lives(self, screen: pygame.Surface, sx: int, sy: int):
        br = self.battle_rect
        life_h = 68  # altura fija de cada corazón de vida
        # ancho proporcional al sprite real para no aplastarlo
        if self.heart_img:
            ratio  = self.heart_w / max(1, self.heart_h)
            life_w = max(life_h, int(life_h * ratio))
        else:
            life_w = life_h
        gap = 16
        start_x = br.left + sx
        y = br.top - life_h - 6 + sy
        for i in range(self.max_lives):
            x = start_x + i * (life_w + gap)
            if i < self.lives:
                if self.heart_img:
                    small = pygame.transform.smoothscale(self.heart_img, (life_w, life_h))
                    screen.blit(small, (x, y))
                else:
                    pygame.draw.polygon(screen, (220, 30, 50), [
                        (x + life_w // 2, y),
                        (x, y + life_h),
                        (x + life_w, y + life_h),
                    ])
            else:
                pygame.draw.rect(screen, (60, 60, 80), (x, y, life_w, life_h), 2)

    def _draw_time_bar(self, screen: pygame.Surface, sx: int, sy: int):
        br = self.battle_rect
        bx = br.left + sx
        by = br.top - 28 + sy
        bw = br.width
        bh = 22

        elapsed = min(self.elapsed_ms, self.duration_ms)
        remaining = 1.0 - elapsed / self.duration_ms

        pygame.draw.rect(screen, (50, 50, 70), (bx, by, bw, bh))
        fill_w = max(0, int(remaining * bw))
        if fill_w > 0:
            if remaining > 0.5:
                color = (80, 210, 80)
            elif remaining > 0.25:
                color = (220, 180, 30)
            else:
                color = (220, 50, 50)
            pygame.draw.rect(screen, color, (bx, by, fill_w, bh))
        pygame.draw.rect(screen, (150, 160, 180), (bx, by, bw, bh), 2)

    def _draw_warning(self, screen: pygame.Surface, w: dict, sx: int, sy: int):
        br = self.battle_rect
        wtype = w.get("wtype", "")
        orig = w.get("orig_timer_ms") or max(1, w["timer_ms"] + 1)
        progress = 1.0 - w["timer_ms"] / orig
        alpha = max(30, min(180, int(progress * 180)))

        if wtype == "h_line":
            y = int(w["y"]) + sy
            # banda del alto de la hitbox del proyectil, alargada hasta los bordes
            _, band_h = self._get_spawn_hitbox_size(w.get("spawn", {}))
            band_h = max(6, band_h)
            surf = pygame.Surface((br.width, band_h), pygame.SRCALPHA)
            surf.fill((255, 30, 30, alpha))
            screen.blit(surf, (br.left + sx, y - band_h // 2))

        elif wtype == "v_marker":
            x = int(w["x"]) + sx
            # banda del ancho de la hitbox rotada (ih*h_ratio se convierte en ancho de pantalla)
            _, band_w = self._get_spawn_hitbox_size(w.get("spawn", {}))
            band_w = max(6, band_w)
            surf = pygame.Surface((band_w, br.height), pygame.SRCALPHA)
            surf.fill((255, 30, 30, alpha))
            screen.blit(surf, (x - band_w // 2, br.top + sy))

        elif wtype == "corner":
            x = int(w["x"]) + sx
            y = int(w["y"]) + sy
            pygame.draw.circle(screen, (255, 60, 30), (x, y), 16)

        elif wtype == "ghost":
            x = int(w["x"]) + sx
            y = int(w["y"]) + sy
            img_idx = w.get("img_idx", 0)
            img = (self.proj_imgs[img_idx]
                   if 0 <= img_idx < len(self.proj_imgs) else None)
            if img:
                ghost = img.copy()
                ghost.set_alpha(70)
                screen.blit(ghost, (x - img.get_width() // 2,
                                    y - img.get_height() // 2))
            else:
                surf = pygame.Surface((100, 50), pygame.SRCALPHA)
                surf.fill((220, 200, 50, 70))
                screen.blit(surf, (x - 50, y - 25))

    def _draw_projectile(self, screen: pygame.Surface, p: dict, sx: int, sy: int):
        x = int(p["x"]) + sx
        y = int(p["y"]) + sy
        img_idx = p.get("img_idx", 0)
        img = None if p.get("text") else (
            self.proj_imgs[img_idx] if 0 <= img_idx < len(self.proj_imgs) else None
        )
        size_scale = p.get("size_scale", 1.0)

        if p.get("text"):
            text = str(p.get("text", ""))
            font = pygame.font.Font(None, max(24, int(30 * size_scale)))
            label = font.render(text, True, (20, 20, 26))
            pad_x, pad_y = 16, 8
            rw = label.get_width() + pad_x * 2
            rh = label.get_height() + pad_y * 2
            bubble = pygame.Surface((rw, rh), pygame.SRCALPHA)
            bubble.fill((246, 241, 210, 235))
            pygame.draw.rect(bubble, (25, 25, 30), bubble.get_rect(), 3)
            bubble.blit(label, (pad_x, pad_y))
            angle = p.get("angle", 0.0)
            rotated = pygame.transform.rotate(bubble, -angle) if angle != 0.0 else bubble
            screen.blit(rotated, (x - rotated.get_width() // 2,
                                  y - rotated.get_height() // 2))
        elif img:
            angle = p.get("angle", 0.0)
            rotated = pygame.transform.rotate(img, -angle) if angle != 0.0 else img
            if abs(size_scale - 1.0) > 0.02:
                rw, rh = rotated.get_size()
                rotated = pygame.transform.smoothscale(
                    rotated, (max(1, int(rw * size_scale)), max(1, int(rh * size_scale))))
            screen.blit(rotated, (x - rotated.get_width()  // 2,
                                  y - rotated.get_height() // 2))
        else:
            if self.tipo == "agresivo":
                r = max(10, int(60 * size_scale))
                pygame.draw.circle(screen, (255, 120, 30), (x, y), r)
                pygame.draw.circle(screen, (200, 80, 10), (x, y), r, 3)
            else:
                rw = max(10, int(180 * size_scale))
                rh = max(6,  int(70  * size_scale))
                pygame.draw.rect(screen, (220, 200, 50),
                                 (x - rw // 2, y - rh // 2, rw, rh))
                pygame.draw.rect(screen, (150, 130, 20),
                                 (x - rw // 2, y - rh // 2, rw, rh), 2)

    def _draw_hitboxes(self, screen: pygame.Surface, sx: int, sy: int):
        """Dibuja hitboxes: AABB para corazón, OBB rotado para proyectiles (modo debug)."""
        # Corazón (AABB, no rota)
        hr = self._get_heart_rect().move(sx, sy)
        hsurf = pygame.Surface((hr.w, hr.h), pygame.SRCALPHA)
        hsurf.fill((255, 80, 80, 70))
        screen.blit(hsurf, (hr.x, hr.y))
        pygame.draw.rect(screen, (255, 80, 80), hr, 2)

        # Proyectiles (OBB, rota con el sprite)
        proj_col = (255, 140, 30) if self.tipo == "agresivo" else (60, 180, 255)
        for p in self.projectiles:
            cx, cy, hw, hh, cos_a, sin_a = self._get_proj_obb(p)
            cx += sx; cy += sy
            ux, uy =  cos_a,  sin_a
            vx, vy = -sin_a,  cos_a
            corners = [
                (int(cx + hw*ux + hh*vx), int(cy + hw*uy + hh*vy)),
                (int(cx + hw*ux - hh*vx), int(cy + hw*uy - hh*vy)),
                (int(cx - hw*ux - hh*vx), int(cy - hw*uy - hh*vy)),
                (int(cx - hw*ux + hh*vx), int(cy - hw*uy + hh*vy)),
            ]
            if len(set(corners)) >= 3:
                pygame.draw.polygon(screen, proj_col, corners, 2)

    def _draw_ending_flash(self, screen: pygame.Surface, base_fonts: dict):
        if self.ending_won:
            progress = min(1.0, self.ending_flash_ms / 2000.0)
            alpha = int(200 * (1.0 - abs(progress - 0.5) * 2))
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, max(0, alpha)))
            screen.blit(overlay, (0, 0))
            text  = "¡SOBREVIVISTE!"
            color = (20, 20, 30)
        else:
            alpha = min(160, int(self.ending_flash_ms / 2000.0 * 160))
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((160, 10, 10, alpha))
            screen.blit(overlay, (0, 0))
            text  = "CAÍSTE..."
            color = (255, 255, 255)

        font = base_fonts.get("subtitle") or base_fonts.get("title")
        if font:
            surf = font.render(text, True, color)
            screen.blit(surf, (screen.get_width()  // 2 - surf.get_width()  // 2,
                               screen.get_height() // 2 - surf.get_height() // 2))

    def _draw_dialog_box(self, screen: pygame.Surface, base_fonts: dict,
                         speaker: str, text: str):
        w = screen.get_width()
        h = screen.get_height()
        box_h = 140
        box = pygame.Rect(26, h - box_h - 22, w - 52, box_h)
        pygame.draw.rect(screen, (242, 242, 242), box)
        pygame.draw.rect(screen, (18, 18, 18), box, 4)

        name_w = max(120, len(speaker) * 14 + 24)
        name_box = pygame.Rect(box.x + 16, box.y - 34, name_w, 34)
        pygame.draw.rect(screen, (255, 255, 255), name_box)
        pygame.draw.rect(screen, (18, 18, 18), name_box, 3)

        f_small = base_fonts.get("small")
        f_body  = base_fonts.get("body") or f_small

        def blit_centered(font, txt, cx, cy, color=(20, 20, 30)):
            if not font:
                return
            s = font.render(txt, True, color)
            screen.blit(s, (cx - s.get_width() // 2, cy - s.get_height() // 2))

        def blit_left(font, txt, lx, ty, color=(20, 20, 30)):
            if not font:
                return
            s = font.render(txt, True, color)
            screen.blit(s, (lx, ty))

        blit_centered(f_small, speaker, name_box.centerx, name_box.centery)

        lines = text.split("\n")
        ty = box.y + 42
        for line in lines:
            blit_left(f_body, line, box.x + 24, ty)
            ty += (f_body.get_height() + 4) if f_body else 24

        blit_left(f_small, "ENTER / ESPACIO para continuar",
                  box.right - 280, box.bottom - 22, (100, 110, 130))
