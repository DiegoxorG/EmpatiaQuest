import json
import os
import sys
import pygame

DEFAULT_SCALE = 1.6
MAX_SCALE = 8.0
DEFAULT_HITBOX_WIDTH_RATIO = 0.20
DEFAULT_HITBOX_HEIGHT_RATIO = 0.12
DEFAULT_HITBOX_OFFSET_X_RATIO = (1.0 - DEFAULT_HITBOX_WIDTH_RATIO) / 2.0
DEFAULT_HITBOX_OFFSET_Y_RATIO = 0.86

CONFIG_NAME = os.path.join("Hitboxes", "personaje_config.json")
SPRITE_FILE = os.path.join("Imagenes", "Personajes", "personaje_main", "idle_down.png")


def choose_image_from_console(project_root):
    print("Ruta de imagen del personaje (enter = usar Imagenes/Personajes/personaje_main/idle_down.png):")
    user = input().strip().strip('"')
    if user:
        return user
    for root, _, files in os.walk(os.path.join(project_root, "Imagenes")):
        for name in files:
            if name.lower() == "idle_down.png":
                return os.path.join(root, name)
    for root, _, files in os.walk(os.path.join(project_root, "Imagenes")):
        for name in files:
            if name.lower() == "parado_skin1.png":
                return os.path.join(root, name)
    return os.path.join(project_root, SPRITE_FILE)


def clamp01(value):
    return max(0.0, min(1.0, value))


def load_config(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def draw_text(surface, text, x, y, font, color=(240, 240, 240)):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        rendered = font.render(line, True, color)
        surface.blit(rendered, (x, y + i * (rendered.get_height() + 4)))


def read_hitbox(config, key_prefix, defaults):
    return {
        "w_ratio": float(config.get(f"{key_prefix}_w_ratio", defaults["w_ratio"])),
        "h_ratio": float(config.get(f"{key_prefix}_h_ratio", defaults["h_ratio"])),
        "offset_x_ratio": float(config.get(f"{key_prefix}_offset_x_ratio", defaults["offset_x_ratio"])),
        "offset_y_ratio": float(config.get(f"{key_prefix}_offset_y_ratio", defaults["offset_y_ratio"])),
    }


def main():
    pygame.init()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    config_path = os.path.join(project_root, CONFIG_NAME)
    
    if len(sys.argv) > 1:
        sprite_path = sys.argv[1]
    else:
        sprite_path = choose_image_from_console(project_root)

    if not os.path.isabs(sprite_path):
        sprite_path = os.path.join(project_root, sprite_path)

    if not os.path.exists(sprite_path):
        print(f"No se encontro sprite: {sprite_path}")
        return

    screen_w, screen_h = 1200, 820
    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption("Editor de personaje")
    clock = pygame.time.Clock()

    image = pygame.image.load(sprite_path).convert_alpha()
    iw, ih = image.get_size()

    font = pygame.font.SysFont("consolas", 18)
    title_font = pygame.font.SysFont("consolas", 24, bold=True)

    config = load_config(config_path)
    scale = float(config.get("scale", DEFAULT_SCALE))
    default_hitbox = {
        "w_ratio": DEFAULT_HITBOX_WIDTH_RATIO,
        "h_ratio": DEFAULT_HITBOX_HEIGHT_RATIO,
        "offset_x_ratio": DEFAULT_HITBOX_OFFSET_X_RATIO,
        "offset_y_ratio": DEFAULT_HITBOX_OFFSET_Y_RATIO,
    }
    hitboxes = {
        "collision": read_hitbox(config, "hitbox", default_hitbox),
        "interactable": read_hitbox(config, "interactable_hitbox", default_hitbox),
    }
    active_hitbox = "collision"

    history = [
        {
            "scale": scale,
            "hitboxes": {
                "collision": dict(hitboxes["collision"]),
                "interactable": dict(hitboxes["interactable"]),
            },
            "active_hitbox": active_hitbox,
        }
    ]
    history_index = 0

    def push_history():
        nonlocal history, history_index, scale, hitboxes, active_hitbox
        history = history[: history_index + 1 ]
        history.append({
            "scale": scale,
            "hitboxes": {
                "collision": dict(hitboxes["collision"]),
                "interactable": dict(hitboxes["interactable"]),
            },
            "active_hitbox": active_hitbox,
        })
        history_index += 1

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_q:
                    scale = max(0.5, scale - 0.05)
                    push_history()
                elif event.key == pygame.K_e:
                    scale = min(MAX_SCALE, scale + 0.05)
                    push_history()
                elif event.key == pygame.K_a:
                    hitboxes[active_hitbox]["w_ratio"] = clamp01(hitboxes[active_hitbox]["w_ratio"] - 0.01)
                    push_history()
                elif event.key == pygame.K_d:
                    hitboxes[active_hitbox]["w_ratio"] = clamp01(hitboxes[active_hitbox]["w_ratio"] + 0.01)
                    push_history()
                elif event.key == pygame.K_w:
                    hitboxes[active_hitbox]["h_ratio"] = clamp01(hitboxes[active_hitbox]["h_ratio"] - 0.01)
                    push_history()
                elif event.key == pygame.K_s:
                    hitboxes[active_hitbox]["h_ratio"] = clamp01(hitboxes[active_hitbox]["h_ratio"] + 0.01)
                    push_history()
                elif event.key == pygame.K_LEFT:
                    hitboxes[active_hitbox]["offset_x_ratio"] = clamp01(hitboxes[active_hitbox]["offset_x_ratio"] - 0.01)
                    push_history()
                elif event.key == pygame.K_RIGHT:
                    hitboxes[active_hitbox]["offset_x_ratio"] = clamp01(hitboxes[active_hitbox]["offset_x_ratio"] + 0.01)
                    push_history()
                elif event.key == pygame.K_UP:
                    hitboxes[active_hitbox]["offset_y_ratio"] = clamp01(hitboxes[active_hitbox]["offset_y_ratio"] - 0.01)
                    push_history()
                elif event.key == pygame.K_DOWN:
                    hitboxes[active_hitbox]["offset_y_ratio"] = clamp01(hitboxes[active_hitbox]["offset_y_ratio"] + 0.01)
                    push_history()
                elif event.key == pygame.K_i:
                    active_hitbox = "interactable" if active_hitbox == "collision" else "collision"
                    push_history()
                elif event.key == pygame.K_r:
                    scale = DEFAULT_SCALE
                    hitboxes["collision"] = dict(default_hitbox)
                    hitboxes["interactable"] = dict(default_hitbox)
                    push_history()
                elif event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL:
                    if history_index > 0:
                        history_index -= 1
                        state = history[history_index]
                        scale = state["scale"]
                        hitboxes = {
                            "collision": dict(state["hitboxes"]["collision"]),
                            "interactable": dict(state["hitboxes"]["interactable"]),
                        }
                        active_hitbox = state.get("active_hitbox", active_hitbox)
                elif event.key == pygame.K_y and event.mod & pygame.KMOD_CTRL:
                    if history_index < len(history) - 1:
                        history_index += 1
                        state = history[history_index]
                        scale = state["scale"]
                        hitboxes = {
                            "collision": dict(state["hitboxes"]["collision"]),
                            "interactable": dict(state["hitboxes"]["interactable"]),
                        }
                        active_hitbox = state.get("active_hitbox", active_hitbox)
                elif event.key == pygame.K_l:
                    config = load_config(config_path)
                    scale = float(config.get("scale", scale))
                    hitboxes["collision"] = read_hitbox(config, "hitbox", hitboxes["collision"])
                    hitboxes["interactable"] = read_hitbox(config, "interactable_hitbox", hitboxes["interactable"])
                    push_history()
                elif event.key == pygame.K_RETURN:
                    save_data = {
                        "scale": scale,
                        # Compatibilidad con codigo existente de colisiones.
                        "hitbox_w_ratio": hitboxes["collision"]["w_ratio"],
                        "hitbox_h_ratio": hitboxes["collision"]["h_ratio"],
                        "hitbox_offset_x_ratio": hitboxes["collision"]["offset_x_ratio"],
                        "hitbox_offset_y_ratio": hitboxes["collision"]["offset_y_ratio"],
                        "interactable_hitbox_w_ratio": hitboxes["interactable"]["w_ratio"],
                        "interactable_hitbox_h_ratio": hitboxes["interactable"]["h_ratio"],
                        "interactable_hitbox_offset_x_ratio": hitboxes["interactable"]["offset_x_ratio"],
                        "interactable_hitbox_offset_y_ratio": hitboxes["interactable"]["offset_y_ratio"],
                    }
                    save_config(config_path, save_data)
                    print(f"Guardado en {config_path}")

        screen.fill((30, 30, 40))

        preview_x = 120
        preview_y = 120
        scaled_w = max(1, int(iw * scale))
        scaled_h = max(1, int(ih * scale))
        sprite = pygame.transform.smoothscale(image, (scaled_w, scaled_h))
        sprite_rect = sprite.get_rect(center=(preview_x + 240, preview_y + 220))

        pygame.draw.rect(screen, (40, 42, 58), (preview_x - 20, preview_y - 20, 520, 500), border_radius=12)
        info_x = preview_x + 560
        pygame.draw.rect(screen, (40, 42, 58), (info_x - 20, preview_y - 20, 520, 360), border_radius=12)
        title = title_font.render("Editor de personaje", True, (255, 255, 255))
        screen.blit(title, (preview_x, preview_y - 48))

        screen.blit(sprite, sprite_rect.topleft)

        collision = hitboxes["collision"]
        interactable = hitboxes["interactable"]

        collision_rect = pygame.Rect(
            sprite_rect.left + int(scaled_w * collision["offset_x_ratio"]),
            sprite_rect.top + int(scaled_h * collision["offset_y_ratio"]),
            max(4, int(scaled_w * collision["w_ratio"])),
            max(4, int(scaled_h * collision["h_ratio"])),
        )
        interactable_rect = pygame.Rect(
            sprite_rect.left + int(scaled_w * interactable["offset_x_ratio"]),
            sprite_rect.top + int(scaled_h * interactable["offset_y_ratio"]),
            max(4, int(scaled_w * interactable["w_ratio"])),
            max(4, int(scaled_h * interactable["h_ratio"])),
        )

        collision_width = 3 if active_hitbox == "collision" else 2
        interactable_width = 3 if active_hitbox == "interactable" else 2

        pygame.draw.rect(screen, (255, 0, 0), collision_rect, collision_width)
        pygame.draw.line(screen, (255, 0, 0), (sprite_rect.left, collision_rect.top), (sprite_rect.right, collision_rect.top), 1)
        pygame.draw.line(screen, (255, 0, 0), (sprite_rect.left, collision_rect.bottom), (sprite_rect.right, collision_rect.bottom), 1)

        pygame.draw.rect(screen, (255, 220, 0), interactable_rect, interactable_width)
        pygame.draw.line(screen, (255, 220, 0), (sprite_rect.left, interactable_rect.top), (sprite_rect.right, interactable_rect.top), 1)
        pygame.draw.line(screen, (255, 220, 0), (sprite_rect.left, interactable_rect.bottom), (sprite_rect.right, interactable_rect.bottom), 1)

        active_label = "ROJA (colision)" if active_hitbox == "collision" else "AMARILLA (interactuable)"
        active = hitboxes[active_hitbox]

        info = [
            f"Scale: {scale:.2f}  (Q/E, max {MAX_SCALE:.1f})",
            f"Editando: {active_label}  (I para alternar)",
            f"Anchura hitbox activa: {active['w_ratio']:.2f}  (A/D)",
            f"Altura hitbox activa: {active['h_ratio']:.2f}  (W/S)",
            f"Offset X activa: {active['offset_x_ratio']:.2f}  (LEFT/RIGHT)",
            f"Offset Y activa: {active['offset_y_ratio']:.2f}  (UP/DOWN)",
            "ENTER: guardar, L: cargar,",
            "R: reset, Ctrl+Z: deshacer, Ctrl+Y: rehacer",
            "ESC: salir",
        ]
        draw_text(screen, "\n".join(info), info_x, preview_y, font)

        note = (
            "Guarda para que el juego cargue el valor desde Hitboxes/personaje_config.json.\n"
            "Roja = colisiones, amarilla = interactuable."
        )
        draw_text(screen, note, preview_x, preview_y + 540, font, color=(200, 200, 200))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()

