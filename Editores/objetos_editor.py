import json
import os
import sys
import pygame
import math
import copy

def load_image(path):
    """Carga una imagen sin converter_alpha (requiere que ya exista un video mode)."""
    img = pygame.image.load(path)
    return img


def choose_image_from_console(project_root):
    """Permite elegir un fondo desde consola."""
    print("Ruta de imagen del fondo (enter = usar Imagenes/Fondos/Salon(1).jpg):")
    user = input().strip().strip('"')
    if user:
        return user
    for root, _, files in os.walk(os.path.join(project_root, "Imagenes", "Fondos")):
        for name in files:
            if name.lower() == "salon(1).jpg":
                return os.path.relpath(os.path.join(root, name), project_root)
    return os.path.join("Imagenes", "Fondos", "Salon(1).jpg")


def save_objects(out_path, objects, world_rect, image_path):
    """Guarda los objetos en JSON."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    abs_image_path = os.path.abspath(image_path)
    abs_images_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Imagenes"))
    
    if abs_image_path.startswith(abs_images_root):
        image_rel = os.path.relpath(abs_image_path, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    else:
        image_rel = os.path.join("Imagenes", "Fondos", os.path.basename(image_path))
    
    payload = {
        "image": image_rel,
        "image_size": [world_rect.width, world_rect.height],
        "objects": objects,
    }
    
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def load_objects(in_path):
    """Carga los objetos desde JSON."""
    with open(in_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    objects = payload.get("objects", [])
    return objects, payload.get("image", "")


def choose_image_gui(scan_dir, title="Elegir imagen"):
    """Selector visual de fondos con thumbnails. Devuelve ruta absoluta o None."""
    valid_ext = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    entries = []
    if os.path.isdir(scan_dir):
        for root, _, files in os.walk(scan_dir):
            for f in sorted(files):
                if os.path.splitext(f)[1].lower() in valid_ext:
                    fp = os.path.join(root, f)
                    entries.append((os.path.relpath(fp, scan_dir), fp))
    entries.sort(key=lambda x: x[0].lower())
    if not entries:
        return None

    THUMB_W, THUMB_H = 200, 130
    LABEL_H, GAP, PADDING, SEARCH_H = 34, 10, 14, 48
    CELL_W = THUMB_W + GAP
    CELL_H = THUMB_H + LABEL_H + GAP

    di = pygame.display.Info()
    WIN_W = min(1400, di.current_w)
    WIN_H = min(900, di.current_h)
    cols = max(1, (WIN_W - PADDING * 2) // CELL_W)
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption(title)
    pick_clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 15)
    big_font = pygame.font.SysFont("consolas", 20, bold=True)
    thumb_cache = {}

    def get_thumb(fp):
        if fp in thumb_cache:
            return thumb_cache[fp]
        try:
            img = pygame.image.load(fp)
            iw, ih = img.get_size()
            s = min(THUMB_W / iw, THUMB_H / ih, 1.0)
            thumb_cache[fp] = pygame.transform.smoothscale(
                img, (max(1, int(iw * s)), max(1, int(ih * s))))
        except Exception:
            thumb_cache[fp] = None
        return thumb_cache[fp]

    filter_text, scroll_y, selected_idx = "", 0, 0
    grid_top = SEARCH_H + 4
    running, result = True, None

    while running:
        ft = filter_text.lower()
        images = [(r, fp) for r, fp in entries if not ft or ft in r.lower()]
        rows = math.ceil(len(images) / cols) if images else 0
        grid_area_h = WIN_H - grid_top
        max_scroll = max(0, rows * CELL_H + PADDING - grid_area_h)
        scroll_y = min(scroll_y, max_scroll)
        if images and 0 <= selected_idx < len(images):
            sr = selected_idx // cols
            if sr * CELL_H < scroll_y:
                scroll_y = sr * CELL_H
            elif (sr + 1) * CELL_H > scroll_y + grid_area_h:
                scroll_y = (sr + 1) * CELL_H - grid_area_h

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEWHEEL:
                scroll_y = max(0, min(scroll_y - event.y * 40, max_scroll))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if my >= grid_top and images:
                    ci = (mx - PADDING) // CELL_W
                    ri = (my - grid_top + scroll_y) // CELL_H
                    if 0 <= ci < cols:
                        idx = ri * cols + ci
                        if 0 <= idx < len(images):
                            if idx == selected_idx:
                                result = images[idx][1]; running = False
                            else:
                                selected_idx = idx
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if images and 0 <= selected_idx < len(images):
                        result = images[selected_idx][1]; running = False
                elif event.key == pygame.K_BACKSPACE:
                    filter_text = filter_text[:-1]; selected_idx = 0; scroll_y = 0
                elif event.key == pygame.K_RIGHT:
                    selected_idx = min(len(images) - 1, selected_idx + 1)
                elif event.key == pygame.K_LEFT:
                    selected_idx = max(0, selected_idx - 1)
                elif event.key == pygame.K_DOWN:
                    selected_idx = min(len(images) - 1, selected_idx + cols)
                elif event.key == pygame.K_UP:
                    selected_idx = max(0, selected_idx - cols)
                elif event.unicode and event.unicode.isprintable():
                    filter_text += event.unicode; selected_idx = 0; scroll_y = 0

        screen.fill((22, 22, 32))
        pygame.draw.rect(screen, (35, 36, 52), pygame.Rect(0, 0, WIN_W, SEARCH_H))
        screen.blit(big_font.render(title, True, (210, 215, 240)), (PADDING, 8))
        screen.blit(font.render(
            f"  Filtro: {filter_text}_   {len(images)} fondos  |  "
            "Flechas=navegar  Enter/DblClick=abrir  Escribe=filtrar  ESC=salir",
            True, (140, 200, 160)), (PADDING + big_font.size(title)[0] + 12, 14))
        pygame.draw.line(screen, (55, 58, 78), (0, SEARCH_H), (WIN_W, SEARCH_H), 1)

        screen.set_clip(pygame.Rect(0, grid_top, WIN_W, grid_area_h))
        for i, (rel, fp) in enumerate(images):
            ci, ri = i % cols, i // cols
            cx = PADDING + ci * CELL_W
            cy = grid_top + ri * CELL_H - scroll_y + GAP // 2
            if cy + CELL_H < grid_top or cy > WIN_H:
                continue
            is_sel = (i == selected_idx)
            cr = pygame.Rect(cx, cy, CELL_W - GAP, CELL_H - GAP)
            pygame.draw.rect(screen, (52, 58, 82) if is_sel else (34, 36, 50), cr, border_radius=6)
            pygame.draw.rect(screen, (100, 150, 255) if is_sel else (50, 54, 72),
                             cr, 2 if is_sel else 1, border_radius=6)
            thumb = get_thumb(fp)
            if thumb:
                tw, th = thumb.get_size()
                screen.blit(thumb, (cx + 2 + (THUMB_W - 4 - tw) // 2,
                                    cy + 2 + (THUMB_H - 4 - th) // 2))
            else:
                pygame.draw.rect(screen, (44, 46, 64),
                                 pygame.Rect(cx + 2, cy + 2, THUMB_W - 4, THUMB_H - 4), border_radius=4)
            name = os.path.basename(rel)
            if font.size(name)[0] > CELL_W - GAP - 8:
                while font.size(name + "…")[0] > CELL_W - GAP - 8 and name:
                    name = name[:-1]
                name += "…"
            lbl = font.render(name, True, (230, 235, 255) if is_sel else (150, 155, 180))
            screen.blit(lbl, (cx + (CELL_W - GAP - lbl.get_width()) // 2, cy + THUMB_H + 6))
        screen.set_clip(None)

        if max_scroll > 0:
            sb_h = max(20, int(grid_area_h * grid_area_h / max(rows * CELL_H + PADDING, 1)))
            sb_y = grid_top + int(scroll_y / max_scroll * (grid_area_h - sb_h)) if max_scroll else grid_top
            pygame.draw.rect(screen, (90, 100, 140),
                             pygame.Rect(WIN_W - 8, sb_y, 6, sb_h), border_radius=3)

        pygame.display.flip()
        pick_clock.tick(60)

    return result


def main():
    pygame.init()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if not os.path.isabs(image_path):
            image_path = os.path.join(project_root, image_path)
    else:
        backgrounds_dir = os.path.join(project_root, "Imagenes", "Fondos")
        image_path = choose_image_gui(backgrounds_dir,
                                      "Elegir fondo — Editor de Objetos  (doble clic o Enter)")
        if image_path is None:
            pygame.quit()
            return

    if not os.path.isabs(image_path):
        image_path = os.path.join(project_root, image_path)

    if not os.path.exists(image_path):
        print(f"No existe la imagen: {image_path}")
        return

    # Cargar imagen de fondo
    image = load_image(image_path)
    iw, ih = image.get_size()

    # Ajustar a pantalla
    max_w, max_h = 1600, 950
    scale = min(max_w / iw, max_h / ih, 1.0)
    view_w = int(iw * scale)
    view_h = int(ih * scale)
    zoom_factor = 1.35
    world_w = max(view_w, int(view_w * zoom_factor))
    world_h = max(view_h, int(view_h * zoom_factor))
    image_view = pygame.transform.smoothscale(image, (world_w, world_h))

    # Configuración de pantalla
    padding = 20
    ui_h = 210
    display_info = pygame.display.Info()
    win_w = display_info.current_w
    win_h = display_info.current_h

    screen = pygame.display.set_mode((win_w, win_h), pygame.NOFRAME)
    pygame.display.set_caption("Editor de Objetos Interactuables")
    image = image.convert_alpha()

    # Fuentes
    font = pygame.font.SysFont("consolas", 20)
    small = pygame.font.SysFont("consolas", 16)

    def draw_wrapped_text(surface, text, font_obj, color, x, y, max_width, line_gap=4):
        """Dibuja texto envuelto en múltiples líneas."""
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

    # Viewport
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
        """Convierte coordenadas de pantalla a mundo."""
        sx, sy = pos
        if not viewport_rect.collidepoint(sx, sy):
            return None
        wx = sx - viewport_rect.x + camera_x
        wy = sy - viewport_rect.y + camera_y
        return (wx, wy)

    def world_to_screen(pos):
        """Convierte coordenadas de mundo a pantalla."""
        wx, wy = pos
        sx = wx - camera_x + viewport_rect.x
        sy = wy - camera_y + viewport_rect.y
        return (sx, sy)

    # Cargar objetos interactuables disponibles
    interactables_dir = os.path.join(project_root, "Imagenes", "Interactuables")
    valid_ext = {".png", ".jpg", ".jpeg"}
    available_objects = []

    if os.path.isdir(interactables_dir):
        for f in os.listdir(interactables_dir):
            if os.path.splitext(f)[1].lower() in valid_ext:
                available_objects.append(f)

    available_objects.sort()

    if not available_objects:
        print("No hay objetos interactuables disponibles en Imagenes/Interactuables/")
        return

    # Cargar objetos de fondo disponibles
    backgrounds_dir = os.path.join(project_root, "Imagenes", "Fondos")
    available_backgrounds = []

    if os.path.isdir(backgrounds_dir):
        for f in os.listdir(backgrounds_dir):
            if os.path.splitext(f)[1].lower() in valid_ext:
                available_backgrounds.append(f)

    available_backgrounds.sort()

    if not available_backgrounds:
        available_backgrounds = [os.path.basename(image_path)]

    # Variables de estado
    objects = []  # Lista de objetos colocados: [{"name": "...", "x": rx, "y": ry, "w": rw, "h": rh}, ...]
    history = [copy.deepcopy(objects)]
    history_index = 0
    
    current_object_idx = 0  # Objeto seleccionado para colocar
    current_object_image = None  # Imagen cacheada del objeto actual
    current_object_rect = None  # Rect del objeto para preview
    placement_sizes = {}

    dragging = False
    moving_object = None  # Índice del objeto que se está moviendo
    move_offset = (0, 0)
    move_mode = False
    start_pos = (0, 0)
    crop_mode = False
    crop_dragging = False
    crop_start_pos = None
    crop_current_pos = None
    
    selected_object_idx = None  # Objeto seleccionado para editar
    scale_step = 1.18
    min_object_size = 1
    initial_object_max_size = 96
    max_object_size = max(world_rect.width, world_rect.height) * 20
    button_size = 38
    button_gap = 8
    minus_button_rect = pygame.Rect(
        win_w - padding - (button_size * 2) - button_gap,
        viewport_rect.bottom + 12,
        button_size,
        button_size,
    )
    plus_button_rect = pygame.Rect(
        win_w - padding - button_size,
        viewport_rect.bottom + 12,
        button_size,
        button_size,
    )

    object_cache = {}  # Cache de imágenes de objetos

    def load_object_image(obj_name):
        """Carga y cachea la imagen de un objeto."""
        if obj_name in object_cache:
            return object_cache[obj_name]
        
        obj_path = os.path.join(interactables_dir, obj_name)
        try:
            img = pygame.image.load(obj_path).convert_alpha()
            object_cache[obj_name] = img
            return img
        except (OSError, pygame.error):
            return None

    def get_object_crop_rect(obj, obj_img):
        crop = obj.get("crop")
        iw, ih = obj_img.get_size()
        if not isinstance(crop, dict):
            return pygame.Rect(0, 0, iw, ih)
        try:
            cx = float(crop.get("x", 0.0))
            cy = float(crop.get("y", 0.0))
            cw = float(crop.get("w", 1.0))
            ch = float(crop.get("h", 1.0))
        except (TypeError, ValueError):
            return pygame.Rect(0, 0, iw, ih)

        x = max(0, min(iw - 1, int(cx * iw)))
        y = max(0, min(ih - 1, int(cy * ih)))
        w = max(1, min(iw - x, int(cw * iw)))
        h = max(1, min(ih - y, int(ch * ih)))
        return pygame.Rect(x, y, w, h)

    def get_cropped_object_image(obj, obj_img):
        crop_rect = get_object_crop_rect(obj, obj_img)
        if crop_rect.size == obj_img.get_size() and crop_rect.topleft == (0, 0):
            return obj_img
        return obj_img.subsurface(crop_rect)

    def get_object_world_rect(obj):
        """Convierte un objeto normalizado a rect en coordenadas de mundo."""
        return pygame.Rect(
            int(obj["x"] * world_rect.width),
            int(obj["y"] * world_rect.height),
            int(obj["w"] * world_rect.width),
            int(obj["h"] * world_rect.height),
        )

    def normalize_object(x, y, w, h):
        """Normaliza las coordenadas de un objeto."""
        return {
            "x": x / world_rect.width,
            "y": y / world_rect.height,
            "w": w / world_rect.width,
            "h": h / world_rect.height,
        }

    def denormalize_object(obj):
        """Desnormaliza las coordenadas de un objeto."""
        return {
            "x": int(obj["x"] * world_rect.width),
            "y": int(obj["y"] * world_rect.height),
            "w": int(obj["w"] * world_rect.width),
            "h": int(obj["h"] * world_rect.height),
        }

    def clamp_object_dimensions(w, h):
        w = max(min_object_size, int(w))
        h = max(min_object_size, int(h))
        scale = min(max_object_size / max(1, w), max_object_size / max(1, h), 1.0)
        return max(min_object_size, int(w * scale)), max(min_object_size, int(h * scale))

    def get_initial_object_size(obj_img):
        w = max(min_object_size, int(obj_img.get_width()))
        h = max(min_object_size, int(obj_img.get_height()))
        scale = min(initial_object_max_size / max(w, h), 1.0)
        return max(min_object_size, int(w * scale)), max(min_object_size, int(h * scale))

    def get_current_object_name():
        return available_objects[current_object_idx]

    def get_placement_size(obj_name, obj_img):
        if obj_name not in placement_sizes:
            placement_sizes[obj_name] = get_initial_object_size(obj_img)
        return placement_sizes[obj_name]

    def clamp_saved_object(obj):
        x = int(obj.get("x", 0) * world_rect.width)
        y = int(obj.get("y", 0) * world_rect.height)
        w = int(obj.get("w", 0) * world_rect.width)
        h = int(obj.get("h", 0) * world_rect.height)
        w, h = clamp_object_dimensions(w, h)
        obj.update(normalize_object(x, y, w, h))
        crop = obj.get("crop")
        if isinstance(crop, dict):
            try:
                cx = max(0.0, min(1.0, float(crop.get("x", 0.0))))
                cy = max(0.0, min(1.0, float(crop.get("y", 0.0))))
                cw = max(0.001, min(1.0 - cx, float(crop.get("w", 1.0))))
                ch = max(0.001, min(1.0 - cy, float(crop.get("h", 1.0))))
                obj["crop"] = {"x": cx, "y": cy, "w": cw, "h": ch}
            except (TypeError, ValueError):
                obj.pop("crop", None)

    def find_object_at(world_pos):
        """Encuentra el objeto en la posición del mundo."""
        for idx in range(len(objects) - 1, -1, -1):
            obj_rect = get_object_world_rect(objects[idx])
            if obj_rect.collidepoint(world_pos):
                return idx
        return None

    def get_object_display_size(obj_img):
        return get_placement_size(get_current_object_name(), obj_img)

    def clamp_object_position(x, y, w, h):
        if w <= world_rect.width:
            x = max(0, min(x, world_rect.width - w))
        else:
            x = max(world_rect.width - w, min(x, 0))

        if h <= world_rect.height:
            y = max(0, min(y, world_rect.height - h))
        else:
            y = max(world_rect.height - h, min(y, 0))

        return x, y

    def scale_selected_object(factor):
        nonlocal selected_object_idx
        if selected_object_idx is None or not (0 <= selected_object_idx < len(objects)):
            if not objects:
                return
            selected_object_idx = len(objects) - 1

        obj = objects[selected_object_idx]
        obj_rect = get_object_world_rect(obj)
        scaled_w = int(obj_rect.width * factor) if factor < 1 else round(obj_rect.width * factor)
        scaled_h = int(obj_rect.height * factor) if factor < 1 else round(obj_rect.height * factor)
        new_w, new_h = clamp_object_dimensions(
            max(min_object_size, scaled_w),
            max(min_object_size, scaled_h),
        )
        center_x, center_y = obj_rect.center
        new_x = int(center_x - new_w / 2)
        new_y = int(center_y - new_h / 2)
        new_x, new_y = clamp_object_position(new_x, new_y, new_w, new_h)

        obj.update(normalize_object(new_x, new_y, new_w, new_h))
        push_history()

    def scale_current_placement_object(factor):
        obj_name = get_current_object_name()
        obj_img = load_object_image(obj_name)
        if obj_img is None:
            return

        current_w, current_h = get_placement_size(obj_name, obj_img)
        scaled_w = int(current_w * factor) if factor < 1 else round(current_w * factor)
        scaled_h = int(current_h * factor) if factor < 1 else round(current_h * factor)
        placement_sizes[obj_name] = clamp_object_dimensions(
            max(min_object_size, scaled_w),
            max(min_object_size, scaled_h),
        )

    def scale_active_size(factor):
        if not move_mode and not crop_mode:
            scale_current_placement_object(factor)
        else:
            scale_selected_object(factor)

    def has_selected_object():
        return selected_object_idx is not None and 0 <= selected_object_idx < len(objects)

    def can_scale_object():
        return (not move_mode and not crop_mode) or has_selected_object() or bool(objects)

    def make_crop_rect_from_points(start, end):
        left = min(start[0], end[0])
        top = min(start[1], end[1])
        width = abs(end[0] - start[0])
        height = abs(end[1] - start[1])
        return pygame.Rect(left, top, width, height)

    def apply_crop_to_selected(crop_world_rect):
        if not has_selected_object():
            return

        obj = objects[selected_object_idx]
        obj_img = load_object_image(obj["name"])
        if obj_img is None:
            return

        obj_rect = get_object_world_rect(obj)
        crop_rect = crop_world_rect.clip(obj_rect)
        if crop_rect.width < 2 or crop_rect.height < 2:
            return

        old_crop = get_object_crop_rect(obj, obj_img)
        rel_x = (crop_rect.x - obj_rect.x) / max(1, obj_rect.width)
        rel_y = (crop_rect.y - obj_rect.y) / max(1, obj_rect.height)
        rel_w = crop_rect.width / max(1, obj_rect.width)
        rel_h = crop_rect.height / max(1, obj_rect.height)

        iw, ih = obj_img.get_size()
        new_x = old_crop.x + int(old_crop.width * rel_x)
        new_y = old_crop.y + int(old_crop.height * rel_y)
        new_w = max(1, int(old_crop.width * rel_w))
        new_h = max(1, int(old_crop.height * rel_h))
        new_x = max(0, min(new_x, iw - 1))
        new_y = max(0, min(new_y, ih - 1))
        new_w = max(1, min(new_w, iw - new_x))
        new_h = max(1, min(new_h, ih - new_y))

        obj["crop"] = {
            "x": new_x / iw,
            "y": new_y / ih,
            "w": new_w / iw,
            "h": new_h / ih,
        }
        obj.update(normalize_object(crop_rect.x, crop_rect.y, crop_rect.width, crop_rect.height))
        push_history()

    def reset_selected_crop():
        if not has_selected_object():
            return
        objects[selected_object_idx].pop("crop", None)
        push_history()

    current_file_name = os.path.basename(image_path)
    if current_file_name in available_backgrounds:
        current_background_idx = available_backgrounds.index(current_file_name)
    else:
        current_background_idx = 0

    # Ruta de guardado
    if current_file_name in available_backgrounds:
        current_background_idx = available_backgrounds.index(current_file_name)
    else:
        current_background_idx = 0

    # Ruta de guardado
    image_name = os.path.splitext(current_file_name)[0]
    out_path = os.path.join(project_root, "Objetos", f"{image_name}_objetos.json")
    clipboard_path = os.path.join(project_root, "Objetos", "_clipboard.json")
    selected_clipboard_path = os.path.join(project_root, "Objetos", "_clipboard_selected.json")

    # Cargar objetos automáticamente si existe el archivo
    try:
        if os.path.exists(out_path):
            objects, _ = load_objects(out_path)
            for obj in objects:
                clamp_saved_object(obj)
            history = [copy.deepcopy(objects)]
            history_index = 0
            print(f"Objetos cargados automáticamente desde: {out_path}")
    except Exception as e:
        print(f"Error cargando objetos: {e}")
        objects = []
        history = [copy.deepcopy(objects)]
        history_index = 0

    def push_history():
        nonlocal history, history_index, objects
        history = history[: history_index + 1]
        history.append(copy.deepcopy(objects))
        history_index += 1

    def copy_all_objects():
        try:
            os.makedirs(os.path.dirname(clipboard_path), exist_ok=True)
            with open(clipboard_path, "w", encoding="utf-8") as fh:
                json.dump(copy.deepcopy(objects), fh, indent=2)
            print(f"{len(objects)} objetos copiados.")
        except Exception as e:
            print(f"Error copiando objetos: {e}")

    def paste_all_objects():
        nonlocal selected_object_idx
        if not os.path.exists(clipboard_path):
            print("No existe clipboard de objetos.")
            return
        try:
            with open(clipboard_path, "r", encoding="utf-8") as fh:
                pasted = json.load(fh)
            if not isinstance(pasted, list):
                print("Clipboard de objetos invalido.")
                return
            start_idx = len(objects)
            for obj in pasted:
                if isinstance(obj, dict) and "name" in obj and all(k in obj for k in ("x", "y", "w", "h")):
                    copied = copy.deepcopy(obj)
                    clamp_saved_object(copied)
                    objects.append(copied)
            if len(objects) > start_idx:
                selected_object_idx = len(objects) - 1
                push_history()
            print(f"{len(objects) - start_idx} objetos pegados.")
        except Exception as e:
            print(f"Error pegando objetos: {e}")

    def copy_selected_object():
        if not has_selected_object():
            print("No hay objeto seleccionado para copiar.")
            return
        try:
            os.makedirs(os.path.dirname(selected_clipboard_path), exist_ok=True)
            with open(selected_clipboard_path, "w", encoding="utf-8") as fh:
                json.dump(copy.deepcopy(objects[selected_object_idx]), fh, indent=2)
            print(f"Objeto seleccionado copiado: {objects[selected_object_idx]['name']}")
        except Exception as e:
            print(f"Error copiando objeto seleccionado: {e}")

    def paste_selected_object():
        nonlocal selected_object_idx
        if not os.path.exists(selected_clipboard_path):
            print("No existe clipboard de objeto seleccionado.")
            return
        try:
            with open(selected_clipboard_path, "r", encoding="utf-8") as fh:
                pasted = json.load(fh)
            if not isinstance(pasted, dict) or "name" not in pasted or not all(k in pasted for k in ("x", "y", "w", "h")):
                print("Clipboard de objeto seleccionado invalido.")
                return
            copied = copy.deepcopy(pasted)
            rect = get_object_world_rect(copied)
            offset = 18
            new_x, new_y = clamp_object_position(rect.x + offset, rect.y + offset, rect.width, rect.height)
            copied.update(normalize_object(new_x, new_y, rect.width, rect.height))
            clamp_saved_object(copied)
            objects.append(copied)
            selected_object_idx = len(objects) - 1
            push_history()
            print(f"Objeto seleccionado pegado: {copied['name']}")
        except Exception as e:
            print(f"Error pegando objeto seleccionado: {e}")

    # Loop principal
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                world_pos = screen_to_world(event.pos)

                if event.button == 1 and minus_button_rect.collidepoint(mouse_pos):
                    scale_active_size(1 / scale_step)
                    continue

                if event.button == 1 and plus_button_rect.collidepoint(mouse_pos):
                    scale_active_size(scale_step)
                    continue

                if event.button == 1 and crop_mode and has_selected_object() and world_pos is not None:
                    selected_rect = get_object_world_rect(objects[selected_object_idx])
                    if selected_rect.collidepoint(world_pos):
                        crop_dragging = True
                        crop_start_pos = world_pos
                        crop_current_pos = world_pos
                        continue

                if event.button == 1 and world_pos is not None:
                    clicked_idx = find_object_at(world_pos)
                    if clicked_idx is not None:
                        obj_rect = get_object_world_rect(objects[clicked_idx])
                        selected_object_idx = clicked_idx
                        print(f"Objeto seleccionado: {objects[clicked_idx]['name']}")
                        if move_mode:
                            moving_object = clicked_idx
                            move_offset = (
                                world_pos[0] - obj_rect.x,
                                world_pos[1] - obj_rect.y,
                            )
                        continue
                    
                    selected_object_idx = None
                    if crop_mode:
                        continue
                    if not move_mode:
                        # Modo crear: colocar nuevo objeto
                        current_object_name = get_current_object_name()
                        obj_img = load_object_image(current_object_name)
                        
                        if obj_img:
                            obj_w, obj_h = get_placement_size(current_object_name, obj_img)
                            
                            # Centrar en el click
                            obj_x = int(world_pos[0] - obj_w / 2)
                            obj_y = int(world_pos[1] - obj_h / 2)
                            
                            # Clamping
                            obj_x, obj_y = clamp_object_position(obj_x, obj_y, obj_w, obj_h)
                            
                            new_obj = {
                                "name": current_object_name,
                                **normalize_object(obj_x, obj_y, obj_w, obj_h),
                            }
                            objects.append(new_obj)
                            selected_object_idx = len(objects) - 1
                            push_history()
                            print(f"Objeto colocado: {current_object_name}")

                elif event.button == 3 and world_pos is not None:  # Click derecho: borrar
                    for idx in range(len(objects) - 1, -1, -1):
                        obj = objects[idx]
                        obj_rect = get_object_world_rect(obj)
                        if obj_rect.collidepoint(world_pos):
                            objects.pop(idx)
                            push_history()
                            if selected_object_idx == idx:
                                selected_object_idx = None
                            elif selected_object_idx is not None and selected_object_idx > idx:
                                selected_object_idx -= 1
                            print(f"Objeto eliminado")
                            break

            elif event.type == pygame.MOUSEMOTION and moving_object is not None:
                world_pos = screen_to_world(event.pos)
                if world_pos is not None:
                    obj = objects[moving_object]
                    obj_rect = get_object_world_rect(obj)
                    
                    new_x = world_pos[0] - move_offset[0]
                    new_y = world_pos[1] - move_offset[1]
                    
                    # Clamping
                    new_x, new_y = clamp_object_position(new_x, new_y, obj_rect.width, obj_rect.height)
                    
                    obj.update(normalize_object(new_x, new_y, obj_rect.width, obj_rect.height))

            elif event.type == pygame.MOUSEMOTION and crop_dragging:
                world_pos = screen_to_world(event.pos)
                if world_pos is not None:
                    crop_current_pos = world_pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and moving_object is not None:
                    moving_object = None
                    push_history()
                if event.button == 1 and crop_dragging:
                    if crop_start_pos is not None and crop_current_pos is not None:
                        apply_crop_to_selected(make_crop_rect_from_points(crop_start_pos, crop_current_pos))
                    crop_dragging = False
                    crop_start_pos = None
                    crop_current_pos = None

            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                ctrl_pressed = bool(mods & pygame.KMOD_CTRL)
                shift_pressed = bool(mods & pygame.KMOD_SHIFT)

                if event.key == pygame.K_z and ctrl_pressed:
                    # Deshacer
                    if history_index > 0:
                        history_index -= 1
                        objects = copy.deepcopy(history[history_index])
                        if selected_object_idx is not None and selected_object_idx >= len(objects):
                            selected_object_idx = None

                elif event.key == pygame.K_y and ctrl_pressed:
                    # Rehacer
                    if history_index < len(history) - 1:
                        history_index += 1
                        objects = copy.deepcopy(history[history_index])
                        if selected_object_idx is not None and selected_object_idx >= len(objects):
                            selected_object_idx = None

                elif event.key == pygame.K_c and ctrl_pressed:
                    if move_mode:
                        copy_selected_object()
                    else:
                        copy_all_objects()

                elif event.key == pygame.K_v and ctrl_pressed:
                    if move_mode:
                        paste_selected_object()
                    else:
                        paste_all_objects()

                elif event.key == pygame.K_RETURN:
                    # Guardar
                    save_objects(out_path, objects, world_rect, image_path)
                    print(f"Guardado en: {out_path}")

                elif event.key == pygame.K_l:
                    # Cargar
                    if os.path.exists(out_path):
                        objects, _ = load_objects(out_path)
                        for obj in objects:
                            clamp_saved_object(obj)
                        selected_object_idx = None
                        history = [copy.deepcopy(objects)]
                        history_index = 0
                        print(f"Cargado desde: {out_path}")

                elif event.key == pygame.K_c:
                    # Limpiar
                    objects = []
                    selected_object_idx = None
                    push_history()

                elif event.key == pygame.K_j:
                    # Siguiente objeto
                    current_object_idx = (current_object_idx + 1) % len(available_objects)
                    selected_object_idx = None
                    print(f"Objeto seleccionado: {available_objects[current_object_idx]}")

                elif event.key == pygame.K_h:
                    # Objeto anterior
                    current_object_idx = (current_object_idx - 1) % len(available_objects)
                    selected_object_idx = None
                    print(f"Objeto seleccionado: {available_objects[current_object_idx]}")

                elif event.key == pygame.K_m:
                    # Alternar modo mover
                    move_mode = not move_mode
                    if move_mode:
                        print("MODO MOVER ACTIVADO")
                    else:
                        print("MODO MOVER DESACTIVADO")

                elif event.key == pygame.K_r:
                    if shift_pressed:
                        reset_selected_crop()
                        print("Recorte reiniciado")
                    else:
                        crop_mode = not crop_mode
                        crop_dragging = False
                        crop_start_pos = None
                        crop_current_pos = None
                        print("MODO RECORTE ACTIVADO" if crop_mode else "MODO RECORTE DESACTIVADO")

                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    scale_active_size(scale_step)

                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    scale_active_size(1 / scale_step)

                elif event.key == pygame.K_ESCAPE:
                    running = False

        # Movimiento de cámara
        keys = pygame.key.get_pressed()
        camera_speed = 10
        camera_x += ((1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)) * camera_speed
        camera_y += ((1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)) * camera_speed
        clamp_camera()

        # Renderizado
        screen.fill((28, 28, 34))
        camera_view = pygame.Rect(camera_x, camera_y, viewport_rect.width, viewport_rect.height)
        screen.blit(image_view, viewport_rect.topleft, area=camera_view)

        pygame.draw.rect(screen, (235, 235, 235), viewport_rect, 2)

        # Dibujar objetos
        for i, obj in enumerate(objects, start=1):
            obj_img = load_object_image(obj["name"])
            if obj_img:
                obj_rect = get_object_world_rect(obj)
                display_w, display_h = clamp_object_dimensions(obj_rect.width, obj_rect.height)
                screen_pos = world_to_screen((obj_rect.x, obj_rect.y))
                source_img = get_cropped_object_image(obj, obj_img)
                scaled_img = pygame.transform.smoothscale(source_img, (display_w, display_h))
                screen.blit(scaled_img, (screen_pos[0], screen_pos[1]))
                
                # Dibuja borde y número
                screen_rect = pygame.Rect(screen_pos[0], screen_pos[1], display_w, display_h)
                border_color = (255, 235, 120) if selected_object_idx == i - 1 else (100, 200, 255)
                pygame.draw.rect(screen, border_color, screen_rect, 3 if selected_object_idx == i - 1 else 2)
                
                label = small.render(str(i), True, (160, 210, 255))
                screen.blit(label, (screen_pos[0] + 4, screen_pos[1] + 2))
                
                # Nombre del objeto
                name_label = small.render(obj["name"], True, (180, 240, 180))
                screen.blit(name_label, (screen_pos[0] + 4, screen_pos[1] + display_h + 2))

        if crop_dragging and crop_start_pos is not None and crop_current_pos is not None:
            crop_preview = make_crop_rect_from_points(crop_start_pos, crop_current_pos)
            if has_selected_object():
                crop_preview = crop_preview.clip(get_object_world_rect(objects[selected_object_idx]))
            crop_preview = crop_preview.move(-camera_x + viewport_rect.x, -camera_y + viewport_rect.y)
            if crop_preview.width > 0 and crop_preview.height > 0:
                dim = pygame.Surface((crop_preview.width, crop_preview.height), pygame.SRCALPHA)
                dim.fill((255, 235, 120, 50))
                screen.blit(dim, crop_preview.topleft)
                pygame.draw.rect(screen, (255, 235, 120), crop_preview, 2)

        # Preview del objeto a colocar (en modo crear)
        if not move_mode and not crop_mode:
            current_object_name = get_current_object_name()
            obj_img = load_object_image(current_object_name)
            if obj_img:
                mouse_pos = pygame.mouse.get_pos()
                world_mouse = screen_to_world(mouse_pos)
                if world_mouse and viewport_rect.collidepoint(mouse_pos):
                    obj_w, obj_h = get_object_display_size(obj_img)
                    
                    preview_x = int(world_mouse[0] - obj_w / 2)
                    preview_y = int(world_mouse[1] - obj_h / 2)
                    
                    preview_x, preview_y = clamp_object_position(preview_x, preview_y, obj_w, obj_h)
                    
                    screen_pos = world_to_screen((preview_x, preview_y))
                    scaled_preview = pygame.transform.smoothscale(obj_img, (obj_w, obj_h))
                    preview_surf = scaled_preview.copy()
                    preview_surf.set_alpha(100)
                    screen.blit(preview_surf, (screen_pos[0], screen_pos[1]))

        # UI
        ui_y = viewport_rect.bottom + 12
        selected_info = f" | Seleccionado: {objects[selected_object_idx]['name']}" if has_selected_object() else ""
        line1 = f"Click izq: colocar/seleccionar | +/-: en CREAR cambia el objeto nuevo, en MOVER/RECORTE cambia el seleccionado | R: recortar | Shift+R: quitar recorte | Click der: borrar | WASD: mover cámara | J/H: cambiar objeto | M: mover | ENTER: guardar | ESC: salir"
        line_shortcuts = "Portapapeles: Ctrl+C/V copia/pega todos los objetos | En modo MOVER, Ctrl+C/V copia/pega solo el objeto seleccionado."
        active_mode = "RECORTE" if crop_mode else ("MOVER" if move_mode else "CREAR")
        current_object_name = get_current_object_name()
        current_obj_img = load_object_image(current_object_name)
        placement_info = ""
        if current_obj_img:
            place_w, place_h = get_placement_size(current_object_name, current_obj_img)
            placement_info = f" | Tamaño nuevo: {place_w}x{place_h}"
        line2 = f"Objeto actual: {current_object_name}{placement_info}{selected_info} | Objetos colocados: {len(objects)} | Modo: {active_mode} | Archivo: {os.path.basename(out_path)}"

        text_x = padding + 18
        max_text_w = max(120, minus_button_rect.x - text_x - 18)
        y1 = draw_wrapped_text(screen, line1, small, (235, 235, 235), text_x, ui_y, max_text_w)
        y2 = draw_wrapped_text(screen, line_shortcuts, small, (255, 235, 150), text_x, y1, max_text_w)
        draw_wrapped_text(screen, line2, small, (170, 220, 170), text_x, y2, max_text_w)

        button_enabled = can_scale_object()
        button_fill = (70, 80, 95) if button_enabled else (45, 48, 55)
        button_border = (180, 220, 255) if button_enabled else (95, 100, 110)
        text_color = (245, 245, 245) if button_enabled else (135, 140, 150)
        for rect, label in ((minus_button_rect, "-"), (plus_button_rect, "+")):
            pygame.draw.rect(screen, button_fill, rect, border_radius=6)
            pygame.draw.rect(screen, button_border, rect, 2, border_radius=6)
            label_surf = font.render(label, True, text_color)
            screen.blit(label_surf, label_surf.get_rect(center=rect.center))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
