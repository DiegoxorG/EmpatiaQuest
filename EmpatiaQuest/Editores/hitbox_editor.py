import json
import os
import sys
import pygame
import math
import copy

def load_image(path):
    # No usamos convert_alpha aqui porque requiere que ya exista un video mode.
    img = pygame.image.load(path)
    return img


def clamp_rect_to_image(rect, img_rect):
    x1 = max(img_rect.left, min(rect.left, img_rect.right))
    y1 = max(img_rect.top, min(rect.top, img_rect.bottom))
    x2 = max(img_rect.left, min(rect.right, img_rect.right))
    y2 = max(img_rect.top, min(rect.bottom, img_rect.bottom))
    left = min(x1, x2)
    top = min(y1, y2)
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    return pygame.Rect(left, top, width, height)


def normalize_rect(rect, img_rect):
    return {
        "rx": (rect.x - img_rect.x) / img_rect.width,
        "ry": (rect.y - img_rect.y) / img_rect.height,
        "rw": rect.width / img_rect.width,
        "rh": rect.height / img_rect.height,
    }


def denormalize_rect(data, img_rect):
    return pygame.Rect(
        img_rect.x + int(data["rx"] * img_rect.width),
        img_rect.y + int(data["ry"] * img_rect.height),
        int(data["rw"] * img_rect.width),
        int(data["rh"] * img_rect.height),
    )


def point_to_line_distance(point, line_start, line_end):
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
    t = max(0, min(1, t))
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    return math.hypot(px - closest_x, py - closest_y)

def line_thickness_px(hitbox, img_rect, default_px=8):
    thickness_norm = hitbox.get("thickness", default_px / img_rect.width)
    return max(1, int(thickness_norm * img_rect.width))


def collides_rect_with_hitbox(rect, h, img_rect):
    if h["type"] == "rect":
        return rect.colliderect(denormalize_rect(h, img_rect))
    if h["type"] == "circle":
        cx = img_rect.x + int(h["cx"] * img_rect.width)
        cy = img_rect.y + int(h["cy"] * img_rect.height)
        r = max(4, int(h["r"] * img_rect.width))
        nearest_x = max(rect.left, min(cx, rect.right))
        nearest_y = max(rect.top, min(cy, rect.bottom))
        dx = cx - nearest_x
        dy = cy - nearest_y
        return (dx * dx + dy * dy) <= (r * r)
    if h["type"] == "line":
        x1 = img_rect.x + h["x1"] * img_rect.width
        y1 = img_rect.y + h["y1"] * img_rect.height
        x2 = img_rect.x + h["x2"] * img_rect.width
        y2 = img_rect.y + h["y2"] * img_rect.height
        thickness = line_thickness_px(h, img_rect)
        steps = max(1, int(max(abs(x2 - x1), abs(y2 - y1)) / 3))
        radius = max(2, thickness // 2)
        for i in range(steps + 1):
            t = i / steps
            px = int(x1 + (x2 - x1) * t)
            py = int(y1 + (y2 - y1) * t)
            probe = pygame.Rect(px - radius, py - radius, radius * 2, radius * 2)
            if rect.colliderect(probe):
                return True
        return False
    return False


def collides_with_any_hitbox(rect, hitboxes, img_rect):
    for h in hitboxes:
        if collides_rect_with_hitbox(rect, h, img_rect):
            return True
    return False

def save_hitboxes(out_path, hitboxes, img_rect, image_path, spawn_data=None, npc_positions=None):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    abs_image_path = os.path.abspath(image_path)
    abs_images_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Imagenes"))
    if abs_image_path.startswith(abs_images_root):
        image_rel = os.path.relpath(abs_image_path, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    else:
        image_rel = os.path.join("Imagenes", os.path.basename(image_path))
    payload = {
        "image": image_rel,
        "image_size": [img_rect.width, img_rect.height],
        "hitboxes": hitboxes,
        "spawn": spawn_data or {},
        "npc_positions": npc_positions or {},
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def load_hitboxes(in_path):
    with open(in_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    hitboxes = payload.get("hitboxes", [])
    # Backward compatibility: if no "type", assume "rect"
    for h in hitboxes:
        if "type" not in h:
            h["type"] = "rect"
        if "role" not in h:
            h["role"] = "wall"
        if h["role"] == "interactable" and "action" not in h:
            h["action"] = "puerta"
        if h["role"] == "interactable" and "target_image" not in h:
            h["target_image"] = ""
        if h["role"] == "interactable" and h.get("action") == "npc":
            if "npc_character" not in h:
                h["npc_character"] = "Sara"
            if "npc_animation" not in h:
                h["npc_animation"] = "Sara_dibujando.png"
    return hitboxes, payload.get("spawn", {}), payload.get("npc_positions", {})


def choose_image_from_console(project_root):
    print("Ruta de imagen del fondo (enter = usar Imagenes/Salon(1).jpg):")
    user = input().strip().strip('"')
    if user:
        return user
    for root, _, files in os.walk(os.path.join(project_root, "Imagenes")):
        for name in files:
            if name.lower() == "salon(1).jpg":
                return os.path.relpath(os.path.join(root, name), project_root)
    return os.path.join("Imagenes", "Salon(1).jpg")


def build_dummy_from_game_logic(project_root, img_rect):
    default = pygame.Rect(img_rect.centerx - 14, img_rect.centery - 14, 28, 28)
    try:
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from Movimiento.Personaje import Personaje

        rutas = os.path.join(project_root, "Imagenes", "Personajes", "personaje_main")
        # Replica _start_adventure de main.py para el spawn base.
        sprite_spawn_x = img_rect.width // 2 - 14
        sprite_spawn_y = img_rect.height // 2 - 14
        personaje = Personaje(sprite_spawn_x, sprite_spawn_y, rutas, velocidad=4, fps_animacion=8)
        hb = personaje.hitbox.copy()
        hb.x += img_rect.x
        hb.y += img_rect.y
        hb.clamp_ip(img_rect)
        return hb
    except Exception:
        return default


def main():
    pygame.init()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = choose_image_from_console(project_root)

    if not os.path.isabs(image_path):
        image_path = os.path.join(project_root, image_path)

    if not os.path.exists(image_path):
        print(f"No existe la imagen: {image_path}")
        return

    image = load_image(image_path)
    iw, ih = image.get_size()

    max_w, max_h = 1600, 950
    scale = min(max_w / iw, max_h / ih, 1.0)
    view_w = int(iw * scale)
    view_h = int(ih * scale)
    zoom_factor = 1.35
    world_w = max(view_w, int(view_w * zoom_factor))
    world_h = max(view_h, int(view_h * zoom_factor))
    image_view = pygame.transform.smoothscale(image, (world_w, world_h))

    padding = 20
    ui_h = 210
    display_info = pygame.display.Info()
    win_w = display_info.current_w
    win_h = display_info.current_h

    screen = pygame.display.set_mode((win_w, win_h), pygame.NOFRAME)
    pygame.display.set_caption("Editor de Hitboxes")
    # Ahora que ya existe ventana, convertimos para acelerar blit.
    image = image.convert_alpha()

    font = pygame.font.SysFont("consolas", 20)
    small = pygame.font.SysFont("consolas", 16)

    def draw_wrapped_text(surface, text, font_obj, color, x, y, max_width, line_gap=4):
        words = text.split(" ")
        line = ""
        yy = y
        for word in words:
            test = f"{line} {word}".strip()
            if font_obj.size(test)[0] <= max_width:
                line = test
            else:
                surface.blit(font_obj.render(line, True, color), (x, yy))
                yy += font_obj.get_height() + line_gap
                line = word
        if line:
            surface.blit(font_obj.render(line, True, color), (x, yy))
            yy += font_obj.get_height() + line_gap
        return yy

    viewport_w = max(100, win_w - (padding * 2))
    viewport_h = max(100, win_h - (padding * 2) - ui_h)
    viewport_rect = pygame.Rect(padding, padding, viewport_w, viewport_h)
    world_rect = pygame.Rect(0, 0, world_w, world_h)
    camera_x = 0
    camera_y = 0

    def clamp_camera():
        nonlocal camera_x, camera_y
        max_x = max(0, world_rect.width - viewport_rect.width)
        max_y = max(0, world_rect.height - viewport_rect.height)
        camera_x = max(0, min(camera_x, max_x))
        camera_y = max(0, min(camera_y, max_y))

    def center_camera_on_rect(rect):
        nonlocal camera_x, camera_y
        camera_x = rect.centerx - (viewport_rect.width // 2)
        camera_y = rect.centery - (viewport_rect.height // 2)
        clamp_camera()

    def screen_to_world(pos):
        sx, sy = pos
        if not viewport_rect.collidepoint(sx, sy):
            return None
        wx = sx - viewport_rect.x + camera_x
        wy = sy - viewport_rect.y + camera_y
        return (wx, wy)

    def world_to_screen(pos):
        wx, wy = pos
        sx = wx - camera_x + viewport_rect.x
        sy = wy - camera_y + viewport_rect.y
        return (sx, sy)

    images_dir = os.path.join(project_root, "Imagenes", "Fondos")
    valid_ext = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

    available_backgrounds = []

    if os.path.isdir(images_dir):
        for root, _, files in os.walk(images_dir):
            for f in files:
                if os.path.splitext(f)[1].lower() in valid_ext:

                    rel_path = os.path.relpath(
                        os.path.join(root, f),
                        images_dir
                    )

                    available_backgrounds.append(rel_path)

    available_backgrounds.sort()

    if not available_backgrounds:
        available_backgrounds = [os.path.basename(image_path)]

    hitboxes = []
    history = [copy.deepcopy(hitboxes)]
    history_index = 0
    dragging = False
    moving_hitbox = None
    selected_hitbox_idx = None
    move_offset = (0, 0)
    move_mode = False   
    start_pos = (0, 0)
    current_rect = None
    current_shape = "rect"
    current_role = "wall"
    interactable_actions = ["puerta", "silla", "npc"]
    current_interactable_action = "puerta"
    current_target_bg_idx = 0
    current_file_name = os.path.basename(image_path)
    if current_file_name in available_backgrounds:
        current_target_bg_idx = available_backgrounds.index(current_file_name)
    current_line_thickness_px = 8
    test_mode = False
    test_speed = 4
    test_player = pygame.Rect(0, 0, 28, 28)

    hb_template = build_dummy_from_game_logic(project_root, world_rect)
    spawn_rect = hb_template.copy()
    spawn_rules = {
        "default": None,
        "by_origin": {},
    }
    spawn_modal_active = False
    spawn_modal_options = ["Cualquier fondo"] + available_backgrounds
    spawn_modal_selected = 0
    spawn_status_message = ""
    spawn_status_timer = 0
    pending_spawn_rect = None
    active_spawn_label = "Cualquier fondo"
    npc_positions = {}
    selected_npc_name = "sara"
    npc_default_site_w = 96
    npc_default_site_h = 96

    personajes_dir = os.path.join(project_root, "Imagenes", "Personajes")
    npc_character_options = []
    if os.path.isdir(personajes_dir):
        for entry in os.listdir(personajes_dir):
            full = os.path.join(personajes_dir, entry)
            if os.path.isdir(full):
                npc_character_options.append(entry)
    npc_character_options.sort()
    if not npc_character_options:
        npc_character_options = ["Sara", "Diego"]
    current_npc_character_idx = 0

    def _animations_for_character(char_name):
        char_dir = os.path.join(personajes_dir, char_name)
        options = []
        if os.path.isdir(char_dir):
            for fn in os.listdir(char_dir):
                if fn.lower().endswith(".png"):
                    options.append(fn)
        options.sort()
        if not options:
            options = ["idle_down.png"]
        return options

    current_npc_animation_options = _animations_for_character(npc_character_options[current_npc_character_idx])
    current_npc_animation_idx = 0
    npc_preview_cache = {}

    def _load_npc_preview_frames(character_name, animation_file):
        key = (str(character_name), str(animation_file))
        cached = npc_preview_cache.get(key)
        if cached is not None:
            return cached
        anim_path = os.path.join(personajes_dir, str(character_name), str(animation_file))
        frames = []
        try:
            sheet = pygame.image.load(anim_path).convert_alpha()
            sw, sh = sheet.get_size()
            file_name = str(animation_file).lower()
            is_static_anim = any(token in file_name for token in ("sentado", "parado", "idle", "stand"))
            frame_count = 1 if is_static_anim else (4 if sw >= 4 else 1)
            frame_w = max(1, sw // frame_count)
            for i in range(frame_count):
                frame = sheet.subsurface(pygame.Rect(i * frame_w, 0, frame_w, sh)).copy()
                frames.append(frame)
        except (OSError, pygame.error):
            frames = []
        npc_preview_cache[key] = frames
        return frames

    def clamp_spawn_rect():
        nonlocal spawn_rect
        spawn_rect.width = hb_template.width
        spawn_rect.height = hb_template.height
        spawn_rect.clamp_ip(world_rect)

    def reset_test_player_to_spawn():
        spawn = spawn_rect.copy()
        spawn.clamp_ip(world_rect)
        test_player.x = spawn.x
        test_player.y = spawn.y
        test_player.width = spawn_rect.width
        test_player.height = spawn_rect.height

    def _resolve_to_nearest_free(base_rect):
        candidate = base_rect.copy()
        candidate.clamp_ip(world_rect)
        if not collides_with_any_hitbox(candidate, hitboxes, world_rect):
            return candidate
        step = 8
        max_radius = max(world_rect.width, world_rect.height)
        for radius in range(step, max_radius + step, step):
            for dx, dy in (
                (radius, 0), (-radius, 0), (0, radius), (0, -radius),
                (radius, radius), (radius, -radius), (-radius, radius), (-radius, -radius),
            ):
                probe = base_rect.copy()
                probe.x += dx
                probe.y += dy
                probe.clamp_ip(world_rect)
                if not collides_with_any_hitbox(probe, hitboxes, world_rect):
                    return probe
        return None

    def set_spawn_to_mouse(mouse_pos):
        nonlocal pending_spawn_rect
        world_pos = screen_to_world(mouse_pos)
        if world_pos is None:
            return
        base = spawn_rect.copy()
        base.center = world_pos
        base.clamp_ip(world_rect)
        pending_spawn_rect = base

    def _serialize_spawn_rect(rect):
        return {
            "rx": rect.x / world_rect.width,
            "ry": rect.y / world_rect.height,
            "rw": rect.width / world_rect.width,
            "rh": rect.height / world_rect.height,
        }

    def _apply_loaded_spawn(spawn_payload):
        nonlocal spawn_rules, spawn_rect
        nonlocal active_spawn_label
        spawn_rules = {"default": None, "by_origin": {}}
        active_spawn_label = "Cualquier fondo"
        if not isinstance(spawn_payload, dict):
            return

        # New format: {"default": {...}, "by_origin": {...}}
        if "default" in spawn_payload or "by_origin" in spawn_payload:
            default_spawn = spawn_payload.get("default")
            if isinstance(default_spawn, dict):
                spawn_rules["default"] = default_spawn
                spawn_rect.x = int(default_spawn.get("rx", 0.5) * world_rect.width)
                spawn_rect.y = int(default_spawn.get("ry", 0.5) * world_rect.height)
            by_origin = spawn_payload.get("by_origin", {})
            if isinstance(by_origin, dict):
                cleaned = {}
                for k, v in by_origin.items():
                    if isinstance(v, dict) and "rx" in v and "ry" in v:
                        cleaned[str(k)] = v
                spawn_rules["by_origin"] = cleaned
            clamp_spawn_rect()
            reset_test_player_to_spawn()
            return

        # Backward compatibility: old single spawn dict
        if "rx" in spawn_payload and "ry" in spawn_payload:
            spawn_rules["default"] = spawn_payload
            spawn_rect.x = int(spawn_payload.get("rx", 0.5) * world_rect.width)
            spawn_rect.y = int(spawn_payload.get("ry", 0.5) * world_rect.height)
            clamp_spawn_rect()
            reset_test_player_to_spawn()

    def _spawn_rect_from_data(sdata):
        return pygame.Rect(
            int(float(sdata.get("rx", 0.5)) * world_rect.width),
            int(float(sdata.get("ry", 0.5)) * world_rect.height),
            spawn_rect.width,
            spawn_rect.height,
        )

    def _delete_spawn_at_world_pos(world_pos):
        nonlocal spawn_status_message, spawn_status_timer
        # Primero intenta borrar spawns por procedencia (mas especificos).
        for origin_name in list(spawn_rules.get("by_origin", {}).keys()):
            sdata = spawn_rules["by_origin"].get(origin_name)
            if not isinstance(sdata, dict):
                continue
            if _spawn_rect_from_data(sdata).collidepoint(world_pos):
                del spawn_rules["by_origin"][origin_name]
                spawn_status_message = f"Spawn eliminado: '{origin_name}'."
                spawn_status_timer = 180
                return True
        # Luego intenta borrar el default.
        default_data = spawn_rules.get("default")
        if isinstance(default_data, dict) and _spawn_rect_from_data(default_data).collidepoint(world_pos):
            spawn_rules["default"] = None
            spawn_status_message = "Spawn por defecto eliminado."
            spawn_status_timer = 180
            return True
        return False

    def _serialize_world_point(world_pos):
        return {
            "rx": (world_pos[0] - world_rect.x) / world_rect.width,
            "ry": (world_pos[1] - world_rect.y) / world_rect.height,
        }

    def _denormalize_world_point(data):
        return (
            int(world_rect.x + float(data.get("rx", 0.5)) * world_rect.width),
            int(world_rect.y + float(data.get("ry", 0.5)) * world_rect.height),
        )

    def _set_npc_at_mouse(npc_name, mouse_pos):
        nonlocal spawn_status_message, spawn_status_timer
        world_pos = screen_to_world(mouse_pos)
        if world_pos is None:
            return
        point = _serialize_world_point(world_pos)
        point["rw"] = npc_default_site_w / world_rect.width
        point["rh"] = npc_default_site_h / world_rect.height
        npc_positions[npc_name] = point
        spawn_status_message = f"{npc_name.capitalize()} ubicado."
        spawn_status_timer = 180

    def _change_npc_site_size(npc_name, delta):
        nonlocal spawn_status_message, spawn_status_timer
        data = npc_positions.get(npc_name)
        if not isinstance(data, dict):
            spawn_status_message = f"Primero ubica {npc_name} (Shift+1/Shift+2)."
            spawn_status_timer = 180
            return
        cur_w = max(24, int(float(data.get("rw", npc_default_site_w / world_rect.width)) * world_rect.width))
        cur_h = max(24, int(float(data.get("rh", npc_default_site_h / world_rect.height)) * world_rect.height))
        new_w = max(24, min(320, cur_w + delta))
        new_h = max(24, min(320, cur_h + delta))
        data["rw"] = new_w / world_rect.width
        data["rh"] = new_h / world_rect.height
        spawn_status_message = f"Tamano de {npc_name}: {new_w}x{new_h}px."
        spawn_status_timer = 180

    def _delete_npc_at_world_pos(world_pos):
        nonlocal spawn_status_message, spawn_status_timer
        for npc_name, data in list(npc_positions.items()):
            if not isinstance(data, dict):
                continue
            nx, ny = _denormalize_world_point(data)
            if math.hypot(world_pos[0] - nx, world_pos[1] - ny) <= 24:
                del npc_positions[npc_name]
                spawn_status_message = f"{npc_name.capitalize()} eliminado."
                spawn_status_timer = 180
                return True
        return False

    # Definir out_path basado en el nombre de la imagen
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    out_path = os.path.join(project_root, "Hitboxes", f"{image_name}_hitboxes.json")
    clipboard_path = os.path.join(project_root, "Hitboxes", "_clipboard.json")
    selected_clipboard_path = os.path.join(project_root, "Hitboxes", "_clipboard_selected.json")

    # Cargar hitboxes automáticamente si existe el archivo
    try:
        if os.path.exists(out_path):
            hitboxes, loaded_spawn, loaded_npcs = load_hitboxes(out_path)
            _apply_loaded_spawn(loaded_spawn)
            if isinstance(loaded_npcs, dict):
                npc_positions = {k: v for k, v in loaded_npcs.items() if isinstance(v, dict)}
            history = [copy.deepcopy(hitboxes)]
            history_index = 0
            print(f"Hitboxes cargadas automáticamente desde: {out_path}")
    except Exception as e:
        print(f"Error cargando hitboxes: {e}")
        hitboxes = []
        history = [copy.deepcopy(hitboxes)]
        history_index = 0

    reset_test_player_to_spawn()

    def push_history():
        nonlocal history, history_index, hitboxes
        history = history[: history_index + 1]
        history.append(copy.deepcopy(hitboxes))
        history_index += 1


    def copy_hitboxes():
        copied = []

        for h in hitboxes:
            # SOLO copiar paredes
            if h.get("role") == "wall":
                copied.append(copy.deepcopy(h))

        return copied

    def copy_selected_hitbox():
        if selected_hitbox_idx is None or not (0 <= selected_hitbox_idx < len(hitboxes)):
            print("No hay hitbox seleccionada para copiar.")
            return None
        return copy.deepcopy(hitboxes[selected_hitbox_idx])

    def paste_hitboxes():
        nonlocal hitboxes

        if not os.path.exists(clipboard_path):
            print("No existe clipboard.")
            return

        try:
            with open(clipboard_path, "r", encoding="utf-8") as fh:
                pasted = json.load(fh)

            if not isinstance(pasted, list):
                print("Clipboard invalido.")
                return

            hitboxes.extend(copy.deepcopy(pasted))

            push_history()

            print(f"{len(pasted)} hitboxes pared pegadas.")

        except Exception as e:
            print(f"Error pegando hitboxes: {e}")

    def paste_selected_hitbox():
        nonlocal hitboxes, selected_hitbox_idx

        if not os.path.exists(selected_clipboard_path):
            print("No existe clipboard de hitbox seleccionada.")
            return

        try:
            with open(selected_clipboard_path, "r", encoding="utf-8") as fh:
                pasted = json.load(fh)

            if not isinstance(pasted, dict) or "type" not in pasted:
                print("Clipboard seleccionado invalido.")
                return

            hitboxes.append(copy.deepcopy(pasted))
            selected_hitbox_idx = len(hitboxes) - 1
            push_history()
            print("Hitbox seleccionada pegada.")

        except Exception as e:
            print(f"Error pegando hitbox seleccionada: {e}")


    def _build_hitbox_payload(shape_data):
        payload = {"role": current_role, **shape_data}

        if current_role == "interactable":
            payload["action"] = current_interactable_action
            if current_interactable_action == "puerta":
                payload["target_image"] = available_backgrounds[current_target_bg_idx]
            elif current_interactable_action == "npc":
                payload["npc_character"] = npc_character_options[current_npc_character_idx]
                payload["npc_animation"] = current_npc_animation_options[current_npc_animation_idx]

        return payload

    def _interactable_label(action):
        if str(action).lower() == "silla":
            return "Silla"
        if str(action).lower() == "npc":
            return "NPC"
        return "Puerta"

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if spawn_modal_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        spawn_modal_selected = (spawn_modal_selected - 1) % len(spawn_modal_options)
                    elif event.key == pygame.K_DOWN:
                        spawn_modal_selected = (spawn_modal_selected + 1) % len(spawn_modal_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if pending_spawn_rect is None:
                            spawn_status_message = "Primero marca una posicion con Shift+P."
                            spawn_status_timer = 180
                            continue
                        selected = spawn_modal_options[spawn_modal_selected]
                        spawn_data = _serialize_spawn_rect(pending_spawn_rect)
                        if selected == "Cualquier fondo":
                            if spawn_rules.get("default") is not None:
                                spawn_status_message = (
                                    "Ya existe spawn para 'Cualquier fondo'. "
                                    "Elige una procedencia especifica."
                                )
                                spawn_status_timer = 240
                                continue
                            spawn_rules["default"] = spawn_data
                            spawn_rect = pending_spawn_rect.copy()
                            active_spawn_label = "Cualquier fondo"
                            clamp_spawn_rect()
                            reset_test_player_to_spawn()
                            spawn_status_message = "Spawn por defecto creado."
                            spawn_status_timer = 180
                        else:
                            if selected in spawn_rules["by_origin"]:
                                spawn_status_message = (
                                    f"Ya existe un spawn para '{selected}'. "
                                    "Elige otra procedencia."
                                )
                                spawn_status_timer = 240
                                continue
                            else:
                                spawn_rules["by_origin"][selected] = spawn_data
                                spawn_rect = pending_spawn_rect.copy()
                                active_spawn_label = selected
                                clamp_spawn_rect()
                                reset_test_player_to_spawn()
                                spawn_status_message = f"Spawn creado para '{selected}'."
                                spawn_status_timer = 180
                        pending_spawn_rect = None
                        spawn_modal_active = False
                    elif event.key == pygame.K_ESCAPE:
                        pending_spawn_rect = None
                        spawn_modal_active = False
                continue

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if test_mode:
                    continue
                world_pos = screen_to_world(event.pos)
                if event.button == 1 and world_pos is not None:

                    # MODO MOVER
                    if move_mode:
                        for idx in range(len(hitboxes) - 1, -1, -1):

                            h = hitboxes[idx]

                            # =========================
                            # RECT
                            # =========================
                            if h["type"] == "rect":

                                r = denormalize_rect(h, world_rect)

                                if r.collidepoint(world_pos):

                                    moving_hitbox = idx
                                    selected_hitbox_idx = idx

                                    move_offset = (
                                        world_pos[0] - r.x,
                                        world_pos[1] - r.y
                                    )

                                    print("Moviendo RECT")

                                    break

                            # =========================
                            # CIRCLE
                            # =========================
                            elif h["type"] == "circle":

                                cx = world_rect.x + h["cx"] * world_rect.width
                                cy = world_rect.y + h["cy"] * world_rect.height
                                radius = h["r"] * world_rect.width

                                dist = math.hypot(
                                    world_pos[0] - cx,
                                    world_pos[1] - cy
                                )

                                if dist <= radius:

                                    moving_hitbox = idx
                                    selected_hitbox_idx = idx

                                    move_offset = (
                                        world_pos[0] - cx,
                                        world_pos[1] - cy
                                    )

                                    print("Moviendo CIRCLE")

                                    break

                            # =========================
                            # LINE
                            # =========================
                            elif h["type"] == "line":

                                x1 = world_rect.x + h["x1"] * world_rect.width
                                y1 = world_rect.y + h["y1"] * world_rect.height

                                x2 = world_rect.x + h["x2"] * world_rect.width
                                y2 = world_rect.y + h["y2"] * world_rect.height

                                dist = point_to_line_distance(
                                    world_pos,
                                    (x1, y1),
                                    (x2, y2)
                                )

                                thickness = line_thickness_px(h, world_rect)

                                if dist <= thickness:

                                    moving_hitbox = idx
                                    selected_hitbox_idx = idx

                                    move_offset = (
                                        world_pos[0] - x1,
                                        world_pos[1] - y1
                                    )

                                    print("Moviendo LINE")

                                    break

                    # MODO CREAR
                    else:
                        dragging = True
                        start_pos = world_pos

                        if current_shape == "rect":
                            current_rect = pygame.Rect(
                                world_pos[0],
                                world_pos[1],
                                0,
                                0
                            )
                    if current_shape == "rect":
                        current_rect = pygame.Rect(world_pos[0], world_pos[1], 0, 0)
                elif event.button == 3 and world_pos is not None:
                    if _delete_npc_at_world_pos(world_pos):
                        continue
                    if _delete_spawn_at_world_pos(world_pos):
                        continue
                    for idx in range(len(hitboxes) - 1, -1, -1):
                        h = hitboxes[idx]
                        if h["type"] == "rect":
                            r = denormalize_rect(h, world_rect)
                            if r.collidepoint(world_pos):
                                hitboxes.pop(idx)
                                if selected_hitbox_idx == idx:
                                    selected_hitbox_idx = None
                                elif selected_hitbox_idx is not None and selected_hitbox_idx > idx:
                                    selected_hitbox_idx -= 1
                                push_history()
                                break
                        elif h["type"] == "circle":
                            cx = world_rect.x + h["cx"] * world_rect.width
                            cy = world_rect.y + h["cy"] * world_rect.height
                            r = h["r"] * world_rect.width
                            dist = math.hypot(world_pos[0] - cx, world_pos[1] - cy)
                            if dist <= r:
                                hitboxes.pop(idx)
                                if selected_hitbox_idx == idx:
                                    selected_hitbox_idx = None
                                elif selected_hitbox_idx is not None and selected_hitbox_idx > idx:
                                    selected_hitbox_idx -= 1
                                push_history()
                                break
                        elif h["type"] == "line":
                            x1 = world_rect.x + h["x1"] * world_rect.width
                            y1 = world_rect.y + h["y1"] * world_rect.height
                            x2 = world_rect.x + h["x2"] * world_rect.width
                            y2 = world_rect.y + h["y2"] * world_rect.height
                            dist = point_to_line_distance(world_pos, (x1, y1), (x2, y2))
                            if dist <= (line_thickness_px(h, world_rect) / 2 + 4):
                                hitboxes.pop(idx)
                                if selected_hitbox_idx == idx:
                                    selected_hitbox_idx = None
                                elif selected_hitbox_idx is not None and selected_hitbox_idx > idx:
                                    selected_hitbox_idx -= 1
                                push_history()
                                break
            elif event.type == pygame.MOUSEMOTION and moving_hitbox is not None:

                world_pos = screen_to_world(event.pos)

                if world_pos is not None:

                    h = hitboxes[moving_hitbox]

                    # =========================
                    # RECT
                    # =========================
                    if h["type"] == "rect":

                        r = denormalize_rect(h, world_rect)

                        r.x = world_pos[0] - move_offset[0]
                        r.y = world_pos[1] - move_offset[1]

                        r.clamp_ip(world_rect)

                        hitboxes[moving_hitbox].update(
                            normalize_rect(r, world_rect)
                        )

                    # =========================
                    # CIRCLE
                    # =========================
                    elif h["type"] == "circle":

                        radius_px = h["r"] * world_rect.width

                        cx = world_pos[0] - move_offset[0]
                        cy = world_pos[1] - move_offset[1]

                        cx = max(
                            world_rect.left + radius_px,
                            min(cx, world_rect.right - radius_px)
                        )

                        cy = max(
                            world_rect.top + radius_px,
                            min(cy, world_rect.bottom - radius_px)
                        )

                        h["cx"] = (cx - world_rect.x) / world_rect.width
                        h["cy"] = (cy - world_rect.y) / world_rect.height

                    # =========================
                    # LINE
                    # =========================
                    elif h["type"] == "line":

                        x1 = world_rect.x + h["x1"] * world_rect.width
                        y1 = world_rect.y + h["y1"] * world_rect.height

                        x2 = world_rect.x + h["x2"] * world_rect.width
                        y2 = world_rect.y + h["y2"] * world_rect.height

                        dx = world_pos[0] - move_offset[0] - x1
                        dy = world_pos[1] - move_offset[1] - y1

                        x1 += dx
                        y1 += dy
                        x2 += dx
                        y2 += dy

                        line_min_x = min(x1, x2)
                        line_max_x = max(x1, x2)

                        line_min_y = min(y1, y2)
                        line_max_y = max(y1, y2)

                        if line_min_x < world_rect.left:
                            offset = world_rect.left - line_min_x
                            x1 += offset
                            x2 += offset

                        if line_max_x > world_rect.right:
                            offset = line_max_x - world_rect.right
                            x1 -= offset
                            x2 -= offset

                        if line_min_y < world_rect.top:
                            offset = world_rect.top - line_min_y
                            y1 += offset
                            y2 += offset

                        if line_max_y > world_rect.bottom:
                            offset = line_max_y - world_rect.bottom
                            y1 -= offset
                            y2 -= offset

                        h["x1"] = (x1 - world_rect.x) / world_rect.width
                        h["y1"] = (y1 - world_rect.y) / world_rect.height

                        h["x2"] = (x2 - world_rect.x) / world_rect.width
                        h["y2"] = (y2 - world_rect.y) / world_rect.height
            elif event.type == pygame.MOUSEMOTION and dragging:
                if current_shape == "rect":
                    world_pos = screen_to_world(event.pos)
                    if world_pos is None:
                        continue
                    x1, y1 = start_pos
                    x2, y2 = world_pos
                    current_rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and moving_hitbox is not None:
                    moving_hitbox = None
                    push_history()
                if event.button == 1 and dragging:
                    world_pos = screen_to_world(event.pos)
                    if world_pos is None:
                        dragging = False
                        current_rect = None
                        continue
                    if current_shape == "rect" and current_rect is not None:
                        fixed = clamp_rect_to_image(current_rect, world_rect)
                        if fixed.width > 6 and fixed.height > 6:
                            hitboxes.append(_build_hitbox_payload({"type": "rect", **normalize_rect(fixed, world_rect)}))
                            selected_hitbox_idx = len(hitboxes) - 1
                            push_history()
                    elif current_shape == "circle":
                        dx = world_pos[0] - start_pos[0]
                        dy = world_pos[1] - start_pos[1]
                        r = math.hypot(dx, dy)
                        if r > 3:
                            cx = start_pos[0]
                            cy = start_pos[1]
                            hitboxes.append(_build_hitbox_payload({
                                "type": "circle",
                                "cx": (cx - world_rect.x) / world_rect.width,
                                "cy": (cy - world_rect.y) / world_rect.height,
                                "r": r / world_rect.width
                            }))
                            selected_hitbox_idx = len(hitboxes) - 1
                            push_history()
                    elif current_shape == "line":
                        dx = abs(world_pos[0] - start_pos[0])
                        dy = abs(world_pos[1] - start_pos[1])
                        if dx > 3 or dy > 3:
                            x1 = start_pos[0]
                            y1 = start_pos[1]
                            x2 = world_pos[0]
                            y2 = world_pos[1]
                            hitboxes.append(_build_hitbox_payload({
                                "type": "line",
                                "x1": (x1 - world_rect.x) / world_rect.width,
                                "y1": (y1 - world_rect.y) / world_rect.height,
                                "x2": (x2 - world_rect.x) / world_rect.width,
                                "y2": (y2 - world_rect.y) / world_rect.height,
                                "thickness": current_line_thickness_px / world_rect.width,
                            }))
                            selected_hitbox_idx = len(hitboxes) - 1
                            push_history()
                    dragging = False
                    current_rect = None

            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                ctrl_pressed = bool(mods & pygame.KMOD_CTRL)
                shift_pressed = bool(mods & pygame.KMOD_SHIFT)

                if event.key == pygame.K_z and ctrl_pressed:
                    if history_index > 0:
                        history_index -= 1
                        hitboxes = copy.deepcopy(history[history_index])
                        if selected_hitbox_idx is not None and selected_hitbox_idx >= len(hitboxes):
                            selected_hitbox_idx = None
                elif event.key == pygame.K_y and ctrl_pressed:
                    if history_index < len(history) - 1:
                        history_index += 1
                        hitboxes = copy.deepcopy(history[history_index])
                        if selected_hitbox_idx is not None and selected_hitbox_idx >= len(hitboxes):
                            selected_hitbox_idx = None
                elif event.key == pygame.K_c and ctrl_pressed and shift_pressed:
                    clipboard_hitbox = copy_selected_hitbox()

                    if clipboard_hitbox is not None:
                        try:
                            with open(selected_clipboard_path, "w", encoding="utf-8") as fh:
                                json.dump(clipboard_hitbox, fh, indent=2)

                            print("Hitbox seleccionada copiada.")

                        except Exception as e:
                            print(f"Error copiando hitbox seleccionada: {e}")
                elif event.key == pygame.K_c and ctrl_pressed:
                    clipboard_hitboxes = copy_hitboxes()

                    try:
                        with open(clipboard_path, "w", encoding="utf-8") as fh:
                            json.dump(clipboard_hitboxes, fh, indent=2)

                        print(f"{len(clipboard_hitboxes)} hitboxes pared copiadas.")

                    except Exception as e:
                        print(f"Error copiando hitboxes: {e}")

                elif event.key == pygame.K_v and ctrl_pressed:
                    if shift_pressed:
                        paste_selected_hitbox()
                    else:
                        paste_hitboxes()

                elif event.key == pygame.K_c:
                    hitboxes = []
                    selected_hitbox_idx = None
                    push_history()
                elif event.key == pygame.K_RETURN:
                    spawn_data = {
                        "default": spawn_rules.get("default"),
                        "by_origin": spawn_rules.get("by_origin", {}),
                    }
                    save_hitboxes(
                        out_path,
                        hitboxes,
                        world_rect,
                        image_path,
                        spawn_data=spawn_data,
                        npc_positions=npc_positions,
                    )
                    print(f"Guardado en: {out_path}")
                elif event.key == pygame.K_l:
                    if os.path.exists(out_path):
                        hitboxes, loaded_spawn, loaded_npcs = load_hitboxes(out_path)
                        _apply_loaded_spawn(loaded_spawn)
                        if isinstance(loaded_npcs, dict):
                            npc_positions = {k: v for k, v in loaded_npcs.items() if isinstance(v, dict)}
                        selected_hitbox_idx = None
                        push_history()
                        print(f"Cargado desde: {out_path}")
                elif event.key == pygame.K_f:
                    if current_shape == "rect":
                        current_shape = "circle"
                    elif current_shape == "circle":
                        current_shape = "line"
                    else:
                        current_shape = "rect"
                elif event.key == pygame.K_i:
                    current_role = "interactable" if current_role == "wall" else "wall"
                elif event.key == pygame.K_j:
                    current_target_bg_idx = (current_target_bg_idx + 1) % len(available_backgrounds)
                elif event.key == pygame.K_h:
                    current_target_bg_idx = (
                        current_target_bg_idx - 1
                    ) % len(available_backgrounds)
                elif event.key == pygame.K_k:
                    idx = interactable_actions.index(current_interactable_action)
                    current_interactable_action = interactable_actions[(idx + 1) % len(interactable_actions)]
                elif event.key == pygame.K_n:
                    current_npc_character_idx = (current_npc_character_idx + 1) % len(npc_character_options)
                    current_npc_animation_options = _animations_for_character(npc_character_options[current_npc_character_idx])
                    current_npc_animation_idx = 0
                elif event.key == pygame.K_b:
                    if current_npc_animation_options:
                        current_npc_animation_idx = (current_npc_animation_idx + 1) % len(current_npc_animation_options)
                elif event.key == pygame.K_m:
                    move_mode = not move_mode      
                    if move_mode:
                        print("MODO MOVER ACTIVADO")
                    else:
                        print("MODO MOVER DESACTIVADO")         
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_t:
                    test_mode = not test_mode
                    if test_mode:
                        reset_test_player_to_spawn()
                        center_camera_on_rect(test_player)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    current_line_thickness_px = min(64, current_line_thickness_px + 1)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    current_line_thickness_px = max(1, current_line_thickness_px - 1)
                elif event.key == pygame.K_p:
                    if event.mod & pygame.KMOD_SHIFT:
                        set_spawn_to_mouse(pygame.mouse.get_pos())
                        # Evita sobrescribir por accidente el spawn por defecto:
                        # selecciona de entrada la primera procedencia sin spawn.
                        spawn_modal_selected = 0
                        for idx, opt in enumerate(spawn_modal_options):
                            if opt == "Cualquier fondo":
                                continue
                            if opt not in spawn_rules.get("by_origin", {}):
                                spawn_modal_selected = idx
                                break
                        spawn_modal_active = True
                    else:
                        reset_test_player_to_spawn()
                        center_camera_on_rect(test_player)
                elif event.key == pygame.K_1 and event.mod & pygame.KMOD_SHIFT:
                    _set_npc_at_mouse("sara", pygame.mouse.get_pos())
                elif event.key == pygame.K_2 and event.mod & pygame.KMOD_SHIFT:
                    _set_npc_at_mouse("diego", pygame.mouse.get_pos())
                elif event.key == pygame.K_1:
                    selected_npc_name = "sara"
                    spawn_status_message = "NPC seleccionado: Sara."
                    spawn_status_timer = 120
                elif event.key == pygame.K_2:
                    selected_npc_name = "diego"
                    spawn_status_message = "NPC seleccionado: Diego."
                    spawn_status_timer = 120
                elif event.key in (pygame.K_LEFTBRACKET, pygame.K_KP_MINUS):
                    _change_npc_site_size(selected_npc_name, -8)
                elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_KP_PLUS):
                    _change_npc_site_size(selected_npc_name, 8)

        if test_mode:
            keys = pygame.key.get_pressed()
            move_x = ((1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)) * test_speed
            move_y = ((1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)) * test_speed
            prev_x = test_player.x
            test_player.x += move_x
            test_player.clamp_ip(world_rect)
            for h in hitboxes:
                if h.get("role", "wall") == "interactable":
                    continue
                if collides_rect_with_hitbox(test_player, h, world_rect):
                    test_player.x = prev_x
                    break
            prev_y = test_player.y
            test_player.y += move_y
            test_player.clamp_ip(world_rect)
            for h in hitboxes:
                if h.get("role", "wall") == "interactable":
                    continue
                if collides_rect_with_hitbox(test_player, h, world_rect):
                    test_player.y = prev_y
                    break
            # En modo test, la camara sigue siempre al dummy.
            center_camera_on_rect(test_player)
        else:
            keys = pygame.key.get_pressed()
            camera_speed = 10
            camera_x += ((1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)) * camera_speed
            camera_y += ((1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)) * camera_speed
            clamp_camera()

        screen.fill((28, 28, 34))
        camera_view = pygame.Rect(camera_x, camera_y, viewport_rect.width, viewport_rect.height)
        screen.blit(image_view, viewport_rect.topleft, area=camera_view)

        pygame.draw.rect(screen, (235, 235, 235), viewport_rect, 2)

        for i, h in enumerate(hitboxes, start=1):
            role = h.get("role", "wall")
            color = (90, 160, 255) if role == "wall" else (255, 210, 80)
            label_color = (160, 210, 255) if role == "wall" else (255, 235, 150)
            if h["type"] == "rect":
                r = denormalize_rect(h, world_rect)
                r = r.move(-camera_x + viewport_rect.x, -camera_y + viewport_rect.y)
                pygame.draw.rect(screen, color, r, 2)
                if selected_hitbox_idx == i - 1:
                    pygame.draw.rect(screen, (255, 255, 255), r, 4)
                label = small.render(str(i), True, label_color)
                screen.blit(label, (r.x + 4, r.y + 2))
                if role == "interactable":
                    action_lbl = _interactable_label(h.get("action", "puerta"))
                    door_lbl = small.render(action_lbl, True, (255, 245, 180))
                    door_rect = door_lbl.get_rect(center=r.center)
                    screen.blit(door_lbl, door_rect)
                    if h.get("action") == "npc":
                        frames = _load_npc_preview_frames(h.get("npc_character", "Sara"), h.get("npc_animation", ""))
                        if frames:
                            idx_anim = (pygame.time.get_ticks() // 180) % len(frames)
                            frame = frames[int(idx_anim)]
                            max_preview = 160
                            target_w = min(max(12, r.width), max_preview)
                            target_h = min(max(12, r.height), max_preview)
                            frame_w, frame_h = frame.get_size()
                            scale = min(target_w / frame_w, target_h / frame_h, 1.0)
                            scaled_w = max(12, int(frame_w * scale))
                            scaled_h = max(12, int(frame_h * scale))
                            scaled = pygame.transform.smoothscale(frame, (scaled_w, scaled_h))
                            screen.blit(scaled, scaled.get_rect(center=r.center))
                        npc_info = f"{h.get('npc_character', 'NPC')} | {h.get('npc_animation', '')}"
                        npc_lbl = small.render(npc_info, True, (255, 205, 150))
                        screen.blit(npc_lbl, (r.x + 4, r.bottom + 2))
            elif h["type"] == "circle":
                cx = world_rect.x + h["cx"] * world_rect.width
                cy = world_rect.y + h["cy"] * world_rect.height
                r = h["r"] * world_rect.width
                sx, sy = world_to_screen((cx, cy))
                pygame.draw.circle(screen, color, (int(sx), int(sy)), int(r), 2)
                if selected_hitbox_idx == i - 1:
                    pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), int(r), 4)
                label = small.render(str(i), True, label_color)
                screen.blit(label, (sx - 10, sy - 10))
                if role == "interactable":
                    action_lbl = _interactable_label(h.get("action", "puerta"))
                    door_lbl = small.render(action_lbl, True, (255, 245, 180))
                    door_rect = door_lbl.get_rect(center=(int(sx), int(sy)))
                    screen.blit(door_lbl, door_rect)
                    if h.get("action") == "npc":
                        frames = _load_npc_preview_frames(h.get("npc_character", "Sara"), h.get("npc_animation", ""))
                        if frames:
                            idx_anim = (pygame.time.get_ticks() // 180) % len(frames)
                            frame = frames[int(idx_anim)]
                            diam = max(12, int(r * 2))
                            diam = min(diam, 160)
                            frame_w, frame_h = frame.get_size()
                            scale = min(diam / frame_w, diam / frame_h, 1.0)
                            scaled_w = max(12, int(frame_w * scale))
                            scaled_h = max(12, int(frame_h * scale))
                            scaled = pygame.transform.smoothscale(frame, (scaled_w, scaled_h))
                            screen.blit(scaled, scaled.get_rect(center=(int(sx), int(sy))))
                        npc_info = f"{h.get('npc_character', 'NPC')} | {h.get('npc_animation', '')}"
                        npc_lbl = small.render(npc_info, True, (255, 205, 150))
                        screen.blit(npc_lbl, (int(sx) + 8, int(sy) + 12))
            elif h["type"] == "line":
                x1 = world_rect.x + h["x1"] * world_rect.width
                y1 = world_rect.y + h["y1"] * world_rect.height
                x2 = world_rect.x + h["x2"] * world_rect.width
                y2 = world_rect.y + h["y2"] * world_rect.height
                sx1, sy1 = world_to_screen((x1, y1))
                sx2, sy2 = world_to_screen((x2, y2))
                thickness = line_thickness_px(h, world_rect)
                pygame.draw.line(screen, color, (sx1, sy1), (sx2, sy2), thickness)
                if selected_hitbox_idx == i - 1:
                    pygame.draw.line(screen, (255, 255, 255), (sx1, sy1), (sx2, sy2), max(thickness + 4, 5))
                label = small.render(str(i), True, label_color)
                screen.blit(label, ((sx1 + sx2) / 2 - 10, (sy1 + sy2) / 2 - 10))
                if role == "interactable":
                    midx = int((sx1 + sx2) / 2)
                    midy = int((sy1 + sy2) / 2)
                    action_lbl = _interactable_label(h.get("action", "puerta"))
                    door_lbl = small.render(action_lbl, True, (255, 245, 180))
                    door_rect = door_lbl.get_rect(center=(midx, midy - 14))
                    screen.blit(door_lbl, door_rect)
                    if h.get("action") == "npc":
                        frames = _load_npc_preview_frames(h.get("npc_character", "Sara"), h.get("npc_animation", ""))
                        if frames:
                            idx_anim = (pygame.time.get_ticks() // 180) % len(frames)
                            frame = frames[int(idx_anim)]
                            size = max(24, thickness * 3)
                            size = min(size, 160)
                            frame_w, frame_h = frame.get_size()
                            scale = min(size / frame_w, size / frame_h, 1.0)
                            scaled_w = max(24, int(frame_w * scale))
                            scaled_h = max(24, int(frame_h * scale))
                            scaled = pygame.transform.smoothscale(frame, (scaled_w, scaled_h))
                            screen.blit(scaled, scaled.get_rect(center=(midx, midy)))
                        npc_info = f"{h.get('npc_character', 'NPC')} | {h.get('npc_animation', '')}"
                        npc_lbl = small.render(npc_info, True, (255, 205, 150))
                        screen.blit(npc_lbl, (midx + 8, midy + 2))

        if current_rect is not None:
            preview = clamp_rect_to_image(current_rect, world_rect)
            preview = preview.move(-camera_x + viewport_rect.x, -camera_y + viewport_rect.y)
            pygame.draw.rect(screen, (120, 200, 255), preview, 2)
        elif dragging and current_shape == "circle":
            mouse_world = screen_to_world(pygame.mouse.get_pos())
            if mouse_world is not None:
                dx = mouse_world[0] - start_pos[0]
                dy = mouse_world[1] - start_pos[1]
                r = math.hypot(dx, dy)
                screen_start = world_to_screen(start_pos)
                pygame.draw.circle(screen, (120, 200, 255), (int(screen_start[0]), int(screen_start[1])), int(r), 2)
        elif dragging and current_shape == "line":
            mouse_world = screen_to_world(pygame.mouse.get_pos())
            if mouse_world is not None:
                screen_start = world_to_screen(start_pos)
                screen_mouse = world_to_screen(mouse_world)
                pygame.draw.line(screen, (120, 200, 255), screen_start, screen_mouse, current_line_thickness_px)

        if test_mode:
            test_view = test_player.move(-camera_x + viewport_rect.x, -camera_y + viewport_rect.y)
            pygame.draw.rect(screen, (255, 190, 90), test_view, 2)
        # Dibuja todos los spawns guardados para evitar confusion visual.
        if isinstance(spawn_rules.get("default"), dict):
            d = spawn_rules["default"]
            d_rect = pygame.Rect(
                int(d.get("rx", 0.5) * world_rect.width),
                int(d.get("ry", 0.5) * world_rect.height),
                spawn_rect.width,
                spawn_rect.height,
            )
            d_rect = d_rect.move(-camera_x + viewport_rect.x, -camera_y + viewport_rect.y)
            pygame.draw.rect(screen, (255, 90, 90), d_rect, 2)
            d_lbl = small.render("Spawn: default", True, (255, 120, 120))
            screen.blit(d_lbl, (d_rect.x, d_rect.y - 16))
        for origin_name, sdata in spawn_rules.get("by_origin", {}).items():
            if not isinstance(sdata, dict):
                continue
            s_rect = pygame.Rect(
                int(sdata.get("rx", 0.5) * world_rect.width),
                int(sdata.get("ry", 0.5) * world_rect.height),
                spawn_rect.width,
                spawn_rect.height,
            )
            s_rect = s_rect.move(-camera_x + viewport_rect.x, -camera_y + viewport_rect.y)
            pygame.draw.rect(screen, (255, 180, 70), s_rect, 2)
            s_lbl = small.render(f"Spawn: {origin_name}", True, (255, 210, 120))
            screen.blit(s_lbl, (s_rect.x, s_rect.y - 16))

        for npc_name, data in npc_positions.items():
            if not isinstance(data, dict):
                continue
            nx, ny = _denormalize_world_point(data)
            site_w = max(24, int(float(data.get("rw", npc_default_site_w / world_rect.width)) * world_rect.width))
            site_h = max(24, int(float(data.get("rh", npc_default_site_h / world_rect.height)) * world_rect.height))
            sx, sy = world_to_screen((nx, ny))
            site_rect = pygame.Rect(0, 0, site_w, site_h)
            site_rect.center = (int(sx), int(sy))
            pygame.draw.rect(screen, (255, 120, 200), site_rect, 1)
            pygame.draw.circle(screen, (255, 80, 170), (int(sx), int(sy)), 10, 2)
            pygame.draw.line(screen, (255, 80, 170), (int(sx) - 7, int(sy)), (int(sx) + 7, int(sy)), 2)
            pygame.draw.line(screen, (255, 80, 170), (int(sx), int(sy) - 7), (int(sx), int(sy) + 7), 2)
            npc_lbl = small.render(f"NPC: {npc_name}", True, (255, 180, 220))
            screen.blit(npc_lbl, (int(sx) + 12, int(sy) - 12))

        # Preview del spawn que se esta ubicando antes de confirmar.
        if pending_spawn_rect is not None:
            p_view = pending_spawn_rect.move(-camera_x + viewport_rect.x, -camera_y + viewport_rect.y)
            pygame.draw.rect(screen, (255, 255, 0), p_view, 2)
            p_lbl = small.render("Nuevo spawn (pendiente)", True, (255, 255, 140))
            screen.blit(p_lbl, (p_view.x, p_view.y - 16))

        if spawn_modal_active:
            modal_w = min(760, win_w - 120)
            modal_h = min(520, win_h - 120)
            modal = pygame.Rect((win_w - modal_w) // 2, (win_h - modal_h) // 2, modal_w, modal_h)
            dim = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 140))
            screen.blit(dim, (0, 0))
            pygame.draw.rect(screen, (245, 245, 245), modal, border_radius=10)
            pygame.draw.rect(screen, (20, 20, 20), modal, 3, border_radius=10)
            title_surf = font.render("Este es el spawn si el jugador proviene de:", True, (20, 20, 20))
            help_surf = small.render(
                "(UP/DOWN para elegir, ENTER para confirmar, ESC para cancelar)",
                True,
                (70, 70, 70),
            )
            screen.blit(title_surf, (modal.x + 20, modal.y + 20))
            screen.blit(help_surf, (modal.x + 20, modal.y + 54))
            list_y = modal.y + 96
            max_rows = max(1, (modal.height - 130) // 26)
            start = 0
            if spawn_modal_selected >= max_rows:
                start = spawn_modal_selected - max_rows + 1
            end = min(len(spawn_modal_options), start + max_rows)
            for idx in range(start, end):
                txt = spawn_modal_options[idx]
                row_rect = pygame.Rect(modal.x + 20, list_y + (idx - start) * 26, modal.width - 40, 24)
                if idx == spawn_modal_selected:
                    pygame.draw.rect(screen, (210, 230, 255), row_rect, border_radius=4)
                option_label = txt
                if txt != "Cualquier fondo" and txt in spawn_rules.get("by_origin", {}):
                    option_label = f"{txt} [YA TIENE SPAWN]"
                option_surf = small.render(option_label, True, (20, 20, 20))
                screen.blit(option_surf, (row_rect.x + 8, row_rect.y + 2))

        if spawn_status_timer > 0 and spawn_status_message:
            spawn_status_timer -= 1
            msg_color = (255, 180, 120) if "Ya existe" in spawn_status_message else (180, 255, 180)
            status_surf = small.render(spawn_status_message, True, msg_color)
            status_rect = status_surf.get_rect(midtop=(win_w // 2, viewport_rect.bottom - 26))
            screen.blit(status_surf, status_rect)

        ui_y = viewport_rect.bottom + 8
        line1 = "Rect/Circ: arrastra click izq. Linea: click inicio, suelta fin."
        line2 = "WASD: mover camara | F: forma | I: wall/interactable | J/H: destino | K: accion | N/B: NPC | +/-: grosor linea | T: test | P: spawn | Shift+P: fijar spawn | click derecho: borrar | C: limpiar | ENTER: guardar | L: cargar | ESC: salir."
        line_shortcuts = "Portapapeles: Ctrl+C copia paredes | Ctrl+V pega paredes | Ctrl+Shift+C copia seleccionada | Ctrl+Shift+V pega seleccionada | Ctrl+Z/Y deshacer/rehacer."
        line3 = (
            f"Archivo: {os.path.basename(image_path)} | Hitboxes: {len(hitboxes)} | "
            f"Forma: {current_shape} | Tipo nuevo: {current_role} | "
            f"Accion: {current_interactable_action} | Destino: {available_backgrounds[current_target_bg_idx]} | "
            f"Grosor linea: {current_line_thickness_px}px | "
            f"Test: {'ON' if test_mode else 'OFF'} | Dummy: {test_player.width}x{test_player.height} | "
            f"Cam: ({camera_x}, {camera_y}) | Zoom: {zoom_factor:.2f}x | NPCs legacy: {len(npc_positions)} | NPC seleccionado legacy: {selected_npc_name} | "
            f"NPC hitbox: {npc_character_options[current_npc_character_idx]} / {current_npc_animation_options[current_npc_animation_idx]} | Export: {os.path.basename(out_path)}."
            f"MoveMode: {'ON' if move_mode else 'OFF'} | Seleccionada: {selected_hitbox_idx + 1 if selected_hitbox_idx is not None and selected_hitbox_idx < len(hitboxes) else 'ninguna'} | "
        )

        text_x = padding + 18
        max_text_w = win_w - text_x - padding
        y2 = draw_wrapped_text(screen, line1, font, (235, 235, 235), text_x, ui_y, max_text_w)
        y3 = draw_wrapped_text(screen, line2, small, (210, 210, 220), text_x, y2, max_text_w)
        y4 = draw_wrapped_text(screen, line_shortcuts, small, (255, 235, 150), text_x, y3, max_text_w)
        draw_wrapped_text(screen, line3, small, (170, 220, 170), text_x, y4, max_text_w)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
