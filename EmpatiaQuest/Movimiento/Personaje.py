import os
import json
import pygame


REQUIRED_IDLE_SPRITES = (
    "idle_down.png",
    "idle_up.png",
    "idle_left.png",
    "idle_right.png",
)

RUN_SPRITES = (
    "run_down.png",
    "run_up.png",
    "run_left.png",
    "run_right.png",
)

WALK_SPRITES = (
    "walk_down.png",
    "walk_up.png",
    "walk_left.png",
    "walk_right.png",
)


def _resolve_sprite_pack_path(ruta_pack):
    if not os.path.isdir(ruta_pack):
        return ruta_pack

    for root, _, files in os.walk(ruta_pack):
        lowered = {name.lower() for name in files}
        has_idle = all(sprite in lowered for sprite in REQUIRED_IDLE_SPRITES)
        has_run = all(sprite in lowered for sprite in RUN_SPRITES)
        has_walk = all(sprite in lowered for sprite in WALK_SPRITES)
        if has_idle and (has_run or has_walk):
            return root
    for root, _, files in os.walk(ruta_pack):
        lowered = {name.lower() for name in files}
        if "parado_skin1.png" in lowered:
            return root
    return ruta_pack


def _load_sequence_frames(ruta_pack, prefix):
    found = []
    lower_prefix = prefix.lower()
    try:
        for name in os.listdir(ruta_pack):
            lname = name.lower()
            if lname.startswith(lower_prefix) and lname.endswith(".png"):
                found.append(name)
    except OSError:
        return []
    found.sort()
    frames = []
    for name in found:
        img = pygame.image.load(os.path.join(ruta_pack, name)).convert_alpha()
        frames.append(_normalize_frame(_trim_transparent(img)))
    return frames


def _normalize_frame(frame):
    frame = _extract_by_nonblack_segments(frame)
    # Si el frame viene "doble" (dos personajes lado a lado), nos quedamos
    # con la mitad izquierda y recortamos de nuevo.
    w, h = frame.get_size()
    # Para este pack, un solo personaje queda aprox cercano a cuadrado/rectangulo
    # moderado; si queda demasiado ancho, sigue siendo un frame doble.
    if w >= int(h * 1.35):
        frame = frame.subsurface(pygame.Rect(0, 0, w // 2, h)).copy()
        frame = _trim_transparent(frame)

    # Evita sprites gigantes en pantalla.
    target_h = 96
    w, h = frame.get_size()
    if h > target_h:
        nw = max(1, int(w * (target_h / h)))
        frame = pygame.transform.scale(frame, (nw, target_h))
    return frame


def _extract_by_nonblack_segments(image, dark_threshold=24):
    # Detecta segmentos por columnas con pixeles "no negros".
    # Este pack usa fondo negro opaco, asi que separar por alpha no funciona.
    w, h = image.get_size()
    if w <= 1 or h <= 1:
        return image

    segments = []
    in_run = False
    start = 0
    for x in range(w):
        has_fg = False
        for y in range(h):
            px = image.get_at((x, y))
            if px.r > dark_threshold or px.g > dark_threshold or px.b > dark_threshold:
                has_fg = True
                break
        if has_fg and not in_run:
            in_run = True
            start = x
        elif not has_fg and in_run:
            segments.append((start, x - 1))
            in_run = False
    if in_run:
        segments.append((start, w - 1))

    if len(segments) <= 1:
        return image

    segments.sort(key=lambda s: (-(s[1] - s[0] + 1), s[0]))
    x1, x2 = segments[0]
    return image.subsurface(pygame.Rect(x1, 0, x2 - x1 + 1, h)).copy()


def _trim_transparent(image):
    # Recorta el canvas al contenido visible para evitar sprites gigantes
    # cuando los PNG tienen mucho espacio transparente.
    rect = image.get_bounding_rect(min_alpha=1)
    if rect.width <= 0 or rect.height <= 0:
        return _extract_single_sprite(_trim_by_background_color(image))

    # Si todo el canvas tiene alpha > 0, no hay transparencia util.
    # En ese caso recortamos por color de fondo.
    full_alpha = (
        rect.x == 0
        and rect.y == 0
        and rect.width == image.get_width()
        and rect.height == image.get_height()
    )
    if full_alpha:
        return _extract_single_sprite(_trim_by_background_color(image))

    cropped = image.subsurface(rect).copy()
    return _extract_single_sprite(cropped)


def _extract_single_sprite(image):
    # Algunos packs traen dos personajes en el mismo frame separados por
    # transparencia. Detectamos columnas con pixeles visibles y nos quedamos
    # con un solo bloque (el mas ancho; si empatan, el de la izquierda).
    w, h = image.get_size()
    if w <= 1 or h <= 1:
        return image

    columns = []
    in_run = False
    start = 0
    for x in range(w):
        has_visible = False
        for y in range(h):
            if image.get_at((x, y)).a > 0:
                has_visible = True
                break
        if has_visible and not in_run:
            in_run = True
            start = x
        elif not has_visible and in_run:
            columns.append((start, x - 1))
            in_run = False
    if in_run:
        columns.append((start, w - 1))

    if len(columns) <= 1:
        return image

    columns.sort(key=lambda r: (-(r[1] - r[0] + 1), r[0]))
    x1, x2 = columns[0]
    part = image.subsurface(pygame.Rect(x1, 0, x2 - x1 + 1, h)).copy()
    rect = part.get_bounding_rect(min_alpha=1)
    if rect.width <= 0 or rect.height <= 0:
        return part
    return part.subsurface(rect).copy()


def _trim_by_background_color(image, tolerance=12):
    # Fallback para sprites sin transparencia: recorta bordes del color
    # dominante del pixel superior-izquierdo.
    w, h = image.get_size()
    if w <= 1 or h <= 1:
        return image

    bg = image.get_at((0, 0))
    min_x, min_y = w, h
    max_x, max_y = -1, -1

    for y in range(h):
        for x in range(w):
            px = image.get_at((x, y))
            if (
                abs(px.r - bg.r) > tolerance
                or abs(px.g - bg.g) > tolerance
                or abs(px.b - bg.b) > tolerance
            ):
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y

    if max_x < min_x or max_y < min_y:
        return image

    rect = pygame.Rect(min_x, min_y, (max_x - min_x + 1), (max_y - min_y + 1))
    return image.subsurface(rect).copy()


def cortar_spritesheet_auto(ruta, cantidad_frames):
    imagen = pygame.image.load(ruta).convert_alpha()
    frames = []
    ancho_imagen, alto_imagen = imagen.get_size()
    ancho_frame = ancho_imagen // cantidad_frames

    for i in range(cantidad_frames):
        x = i * ancho_frame
        frame = imagen.subsurface((x, 0, ancho_frame, alto_imagen))
        frame = _trim_transparent(frame)
        frames.append(frame)
    return frames


def cargar_animaciones(ruta_pack, escala=1.0):
    has_idle_sheet = all(
        os.path.exists(os.path.join(ruta_pack, sprite))
        for sprite in REQUIRED_IDLE_SPRITES
    )
    has_run_sheet = all(
        os.path.exists(os.path.join(ruta_pack, sprite))
        for sprite in RUN_SPRITES
    )
    has_walk_sheet = all(
        os.path.exists(os.path.join(ruta_pack, sprite))
        for sprite in WALK_SPRITES
    )

    if has_idle_sheet and (has_run_sheet or has_walk_sheet):
        move_prefix = "run" if has_run_sheet else "walk"
        animaciones = {
            "down": cortar_spritesheet_auto(os.path.join(ruta_pack, f"{move_prefix}_down.png"), 8),
            "up": cortar_spritesheet_auto(os.path.join(ruta_pack, f"{move_prefix}_up.png"), 8),
            "left": cortar_spritesheet_auto(os.path.join(ruta_pack, f"{move_prefix}_left.png"), 8),
            "right": cortar_spritesheet_auto(os.path.join(ruta_pack, f"{move_prefix}_right.png"), 8),
            "idle_down": cortar_spritesheet_auto(os.path.join(ruta_pack, "idle_down.png"), 1),
            "idle_up": cortar_spritesheet_auto(os.path.join(ruta_pack, "idle_up.png"), 1),
            "idle_left": cortar_spritesheet_auto(os.path.join(ruta_pack, "idle_left.png"), 1),
            "idle_right": cortar_spritesheet_auto(os.path.join(ruta_pack, "idle_right.png"), 1),
        }
    else:
        walk_frames = _load_sequence_frames(ruta_pack, "Caminando_skin1")
        run_frames = _load_sequence_frames(ruta_pack, "Corriendo_skin1")
        idle_legacy_frames = _load_sequence_frames(ruta_pack, "Parado_skin1")
        if not walk_frames and not run_frames:
            raise FileNotFoundError(f"No se encontraron sprites compatibles en: {ruta_pack}")

        # Este pack trae 4 imagenes que representan direcciones, no frames
        # temporales de una sola direccion.
        if len(walk_frames) >= 4 or len(run_frames) >= 4:
            base = walk_frames if len(walk_frames) >= 4 else run_frames
            alt = run_frames if len(run_frames) >= 4 else walk_frames

            down_a, up_a, left_a, right_a = base[0], base[1], base[2], base[3]
            down_b, up_b, left_b, right_b = alt[0], alt[1], alt[2], alt[3]
            if len(idle_legacy_frames) >= 4:
                idle_down, idle_up, idle_left, idle_right = (
                    idle_legacy_frames[0],
                    idle_legacy_frames[1],
                    idle_legacy_frames[2],
                    idle_legacy_frames[3],
                )
            elif len(idle_legacy_frames) >= 1:
                idle_down = idle_up = idle_left = idle_right = idle_legacy_frames[0]
            else:
                idle_down, idle_up, idle_left, idle_right = down_a, up_a, left_a, right_a
            animaciones = {
                "down": [down_a, down_b],
                "up": [up_a, up_b],
                "left": [left_a, left_b],
                "right": [right_a, right_b],
                "idle_down": [idle_down],
                "idle_up": [idle_up],
                "idle_left": [idle_left],
                "idle_right": [idle_right],
            }
        else:
            idle_frame = idle_legacy_frames[0] if idle_legacy_frames else walk_frames[0]
            animaciones = {
                "down": walk_frames,
                "up": walk_frames,
                "left": walk_frames,
                "right": walk_frames,
                "idle_down": [idle_frame],
                "idle_up": [idle_frame],
                "idle_left": [idle_frame],
                "idle_right": [idle_frame],
            }

    if escala != 1.0:
        for k, frames in animaciones.items():
            scaled = []
            for frame in frames:
                w = max(1, int(frame.get_width() * escala))
                h = max(1, int(frame.get_height() * escala))
                scaled.append(pygame.transform.scale(frame, (w, h)))
            animaciones[k] = scaled
    return animaciones


class Personaje:
    def __init__(self, x, y, ruta_pack, velocidad=3, fps_animacion=8, escala=1.6, color=None):
        self.x = x
        self.y = y
        self.velocidad = velocidad
        self.sprint_multiplier = 1.8
        self.scale = escala
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config = self._load_config(project_root)
        self.scale = float(config.get("scale", self.scale))
        ruta_pack_resuelta = _resolve_sprite_pack_path(ruta_pack)
        self.animaciones = cargar_animaciones(ruta_pack_resuelta, escala=self.scale)
        self.direccion = "down"
        self.frame_actual = 0
        self.contador_animacion = 0
        self.fps_animacion = fps_animacion
        base = self.animaciones["idle_down"][0]
        self.sprite_w = base.get_width()
        self.sprite_h = base.get_height()

        default_width_ratio = 0.20
        default_height_ratio = 0.12
        default_offset_x_ratio = (1.0 - default_width_ratio) / 2.0
        default_offset_y_ratio = 1.0 - default_height_ratio - 0.025

        self.hitbox_w_ratio = float(config.get("hitbox_w_ratio", default_width_ratio))
        self.hitbox_h_ratio = float(config.get("hitbox_h_ratio", default_height_ratio))
        self.hitbox_offset_x_ratio = float(config.get("hitbox_offset_x_ratio", default_offset_x_ratio))
        self.hitbox_offset_y_ratio = float(config.get("hitbox_offset_y_ratio", default_offset_y_ratio))
        self.interactable_hitbox_w_ratio = float(config.get("interactable_hitbox_w_ratio", self.hitbox_w_ratio))
        self.interactable_hitbox_h_ratio = float(config.get("interactable_hitbox_h_ratio", self.hitbox_h_ratio))
        self.interactable_hitbox_offset_x_ratio = float(config.get("interactable_hitbox_offset_x_ratio", self.hitbox_offset_x_ratio))
        self.interactable_hitbox_offset_y_ratio = float(config.get("interactable_hitbox_offset_y_ratio", self.hitbox_offset_y_ratio))

        self.hitbox_w = max(14, int(self.sprite_w * self.hitbox_w_ratio))
        self.hitbox_h = max(8, int(self.sprite_h * self.hitbox_h_ratio))
        self.hitbox_offset_x = int(self.sprite_w * self.hitbox_offset_x_ratio)
        self.hitbox_offset_y = int(self.sprite_h * self.hitbox_offset_y_ratio)
        self.interactable_hitbox_w = max(14, int(self.sprite_w * self.interactable_hitbox_w_ratio))
        self.interactable_hitbox_h = max(8, int(self.sprite_h * self.interactable_hitbox_h_ratio))
        self.interactable_hitbox_offset_x = int(self.sprite_w * self.interactable_hitbox_offset_x_ratio)
        self.interactable_hitbox_offset_y = int(self.sprite_h * self.interactable_hitbox_offset_y_ratio)
        self.hitbox = pygame.Rect(
            self.x + self.hitbox_offset_x,
            self.y + self.hitbox_offset_y,
            self.hitbox_w,
            self.hitbox_h,
        )
        self.interactable_hitbox = pygame.Rect(
            self.x + self.interactable_hitbox_offset_x,
            self.y + self.interactable_hitbox_offset_y,
            self.interactable_hitbox_w,
            self.interactable_hitbox_h,
        )

    def _load_config(self, root_dir):
        candidate_paths = [
            os.path.join(root_dir, "Hitboxes", "personaje_config.json"),
            os.path.join(root_dir, "personaje_config.json"),
        ]
        for config_path in candidate_paths:
            try:
                with open(config_path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
        return {}

    def sync_hitbox_from_sprite(self):
        self.hitbox.x = self.x + self.hitbox_offset_x
        self.hitbox.y = self.y + self.hitbox_offset_y
        self.interactable_hitbox.x = self.x + self.interactable_hitbox_offset_x
        self.interactable_hitbox.y = self.y + self.interactable_hitbox_offset_y

    def sync_sprite_from_hitbox(self):
        self.x = self.hitbox.x - self.hitbox_offset_x
        self.y = self.hitbox.y - self.hitbox_offset_y
        self.interactable_hitbox.x = self.x + self.interactable_hitbox_offset_x
        self.interactable_hitbox.y = self.y + self.interactable_hitbox_offset_y

    def actualizar(self):
        teclas = pygame.key.get_pressed()
        self.moviendose = False
        sprint_activo = teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT]
        velocidad_actual = self.velocidad * self.sprint_multiplier if sprint_activo else self.velocidad

        if teclas[pygame.K_UP] or teclas[pygame.K_w]:
            self.y -= velocidad_actual
            self.direccion = "up"
            self.moviendose = True
        elif teclas[pygame.K_DOWN] or teclas[pygame.K_s]:
            self.y += velocidad_actual
            self.direccion = "down"
            self.moviendose = True
        elif teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
            self.x -= velocidad_actual
            self.direccion = "left"
            self.moviendose = True
        elif teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
            self.x += velocidad_actual
            self.direccion = "right"
            self.moviendose = True

        if self.moviendose:
            self.contador_animacion += 1
            if self.contador_animacion >= self.fps_animacion:
                self.contador_animacion = 0
                total_frames = len(self.animaciones[self.direccion])
                self.frame_actual = (self.frame_actual + 1) % total_frames
        else:
            self.frame_actual = 0
            self.contador_animacion = 0

        self.sync_hitbox_from_sprite()

    def dibujar(self, pantalla, offset=(0, 0)):
        if self.moviendose:
            imagen_actual = self.animaciones[self.direccion][self.frame_actual]
        else:
            imagen_actual = self.animaciones[f"idle_{self.direccion}"][0]

        pantalla.blit(imagen_actual, (self.x - offset[0], self.y - offset[1]))
