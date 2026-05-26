import sys
import random
import json
import os
import pygame
from Movimiento.Personaje import Personaje
from Movimiento.Fondo import Fondo
from Movimiento.Animacion import Animacion
from config import (
    DEFAULT_FPS, BG_DARK, BG_MID, GRID, CARD, CARD_HOVER, CARD_BORDER,
    TEXT_MAIN, TEXT_SOFT, PIXEL_CYAN, PIXEL_PINK, PALETTE_COLORS,
    CUSTOM_PARTS, PART_STYLES, DEFAULT_CHARACTER_COLORS, DEFAULT_SETTINGS, DEFAULT_CONTROLS, SAVE_VERSION
)
from ui_components import Button
from story import build_story_events, pick_next_event, PROLOGO_RAZON_CHOICES


class EmpatiaQuestUI:
    def __init__(self):
        pygame.init()
        display_info = pygame.display.Info()
        self.display_width = display_info.current_w
        self.display_height = display_info.current_h
        self.windowed_size = (
            min(1920, self.display_width),
            min(1200, self.display_height),
        )
        self.width, self.height = self.windowed_size
        self.screen = pygame.display.set_mode(self.windowed_size)
        pygame.display.set_caption("Empatia Quest")
        self.clock = pygame.time.Clock()

        self.base_fonts = self._build_fonts()
        self.pixel_scale = {
            "title": 1,
            "subtitle": 1,
            "button": 1,
            "body": 1,
            "small": 1,
        }

        self.running = True
        self.current_screen = "menu"
        self.selected_index = 0
        self.selected_play_index = 0
        self.message = ""
        self.button_width = min(460, int(self.width * 0.34))
        self.button_height = 64
        self.button_gap = 18

        self.buttons = self._build_menu_buttons()
        self.play_buttons = self._build_play_buttons()
        self.pause_buttons = self._build_pause_buttons()
        self.pause_selected_index = 0
        self.save_slot_selected = 0
        self.pause_overwrite_pending = False
        self.pause_pending_slot = None
        self.previous_screen = None
        self.custom_parts = CUSTOM_PARTS
        self.part_styles = PART_STYLES
        self.current_style = {k: 0 for k in self.part_styles}
        self.selected_custom_index = 0
        self.selected_slider = 0
        self.settings = DEFAULT_SETTINGS.copy()
        self.setting_keys = list(self.settings.keys())
        self.selected_setting_index = 0
        self.dragging_volume = False
        self.controls = self._build_default_controls()
        self.control_labels = [
            ("Mover arriba", "mover_arriba"),
            ("Mover abajo", "mover_abajo"),
            ("Mover izquierda", "mover_izquierda"),
            ("Mover derecha", "mover_derecha"),
            ("Interactuar", "interactuar"),
            ("Guardar partida", "guardar"),
            ("Continuar dialogo", "continuar"),
            ("Elegir opcion 1", "opcion_1"),
            ("Elegir opcion 2", "opcion_2"),
            ("Elegir opcion 3", "opcion_3"),
            ("Elegir opcion 4", "opcion_4"),
            ("Elegir opcion 5", "opcion_5"),
        ]
        self.selected_control_index = 0
        self.waiting_control_action = None
        self.controls_scroll = 0
        self.palette_colors = PALETTE_COLORS
        self.character_colors = DEFAULT_CHARACTER_COLORS.copy()
        self.empathy_points = 0
        self.skills_inventory = {
            "Escucha activa": {"nivel": 1, "descripcion": "Prestar atencion sin interrumpir."},
            "Comunicacion asertiva": {"nivel": 1, "descripcion": "Hablar con respeto y claridad."},
            "Mediacion": {"nivel": 0, "descripcion": "Ayudar a resolver conflictos."},
        }
        self.show_skills_inventory = False
        save_dir = os.path.join(os.path.dirname(__file__), "Partidas_Guardadas")
        os.makedirs(save_dir, exist_ok=True)
        self.save_file = os.path.join(save_dir, "partida_guardada.json")
        self.save_slot_files = [os.path.join(save_dir, f"partida_slot_{i+1}.json") for i in range(4)]
        self.player_rect = pygame.Rect(self.width // 2 - 10, self.height // 2 - 10, 20, 20)
        self.player_speed = 4
        self.npc_positions = []
        self.next_random_event_ms = 0
        self.simulacion_activa = False
        self.simulacion_personaje = None
        self.simulacion_fondo = None
        self.simulacion_animacion = None
        self.simulacion_pared1 = None
        self.simulacion_pared2 = None
        self.simulacion_aviso = None
        self.simulacion_mostrar_aviso = False
        self.prologo_activo = False
        self.prologo_paso = 0
        self.prologo_razon = ""
        self.prologo_textos = []
        self.story_walls = []
        self.story_object_image_cache = {}
        self.story_interaction_text = ""
        self.story_spawn_world = None
        self.story_spawn_by_origin = {}
        self.story_previous_map_name = None
        self.story_zoom = 1.35
        self.story_spawn_offset_x = -180
        self.story_spawn_offset_y = -120
        self.story_world_width = self.width
        self.story_world_height = self.height
        self.story_camera_x = 0
        self.story_camera_y = 0
        self.story_interaction_margin = 42
        self.story_interact_prompt_img = None
        self.story_interact_prompt_scaled = None
        self.story_seated_sprite = None
        self.story_is_seated = False
        self.story_seated_hitbox = None
        self.story_clock_day = 1
        self.story_clock_hour = 7
        self.story_clock_minute = 30
        self.story_clock_accumulator_ms = 0
        self.story_npc_sara_frames = []
        self.story_npc_diego_frames = []
        self.story_npc_sara_index = 0
        self.story_npc_diego_index = 0
        self.story_npc_anim_timer = 0
        self.story_npc_positions = {}
        self.story_npc_hitbox_cache = {}
        self.cached_background_scaled = None
        self.cached_background_size = None
        self.cached_background_source = None
        self._load_story_interact_prompt()
        self._load_story_seated_sprite()
        self._load_story_event_npc_sprites()
        self._apply_display_mode()

    def _apply_display_mode(self):
        if self.settings["Pantalla completa"]:
            self.screen = pygame.display.set_mode((self.display_width, self.display_height), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.windowed_size)
        self.width, self.height = self.screen.get_size()
        self.cached_background_scaled = None
        self.cached_background_size = None
        self.cached_background_source = None
        if self.current_screen == "aventura":
            self._rebuild_story_world(keep_player=True)
            self.story_walls = self._build_story_wall_hitboxes(
                self.aventura_fondo.ruta_imagen if getattr(self, "aventura_fondo", None) else None
            )
        self.button_width = min(460, int(self.width * 0.34))
        self.buttons = self._build_menu_buttons()
        self.play_buttons = self._build_play_buttons()
        self.pause_buttons = self._build_pause_buttons()

    def _rebuild_story_world(self, keep_player=True):
        old_w = max(1, getattr(self, "story_world_width", self.width))
        old_h = max(1, getattr(self, "story_world_height", self.height))

        self.story_world_width = max(self.width, int(self.width * self.story_zoom))
        self.story_world_height = max(self.height, int(self.height * self.story_zoom))
        self.story_map_rect = pygame.Rect(0, 0, self.story_world_width, self.story_world_height)

        if keep_player and hasattr(self, "player_rect"):
            old_cx = self.player_rect.centerx
            old_cy = self.player_rect.centery
            ratio_x = old_cx / old_w
            ratio_y = old_cy / old_h
            self.player_rect.centerx = int(ratio_x * self.story_world_width)
            self.player_rect.centery = int(ratio_y * self.story_world_height)
            self.player_rect.clamp_ip(self.story_map_rect)
        elif hasattr(self, "player_rect"):
            self.player_rect.center = (self.story_world_width // 2, self.story_world_height // 2)
            self.player_rect.clamp_ip(self.story_map_rect)

    def _update_story_camera(self):
        # Centra la camara en el jugador y la detiene en los bordes del mundo.
        target_x = self.player_rect.centerx - (self.width // 2)
        target_y = self.player_rect.centery - (self.height // 2)
        max_x = max(0, self.story_world_width - self.width)
        max_y = max(0, self.story_world_height - self.height)
        self.story_camera_x = max(0, min(target_x, max_x))
        self.story_camera_y = max(0, min(target_y, max_y))

    def _pick_readable_font(self):
        candidates = [
            "determination mono web",
            "determinationmonoweb",
            "segoeui",
            "arial",
            "verdana",
            "tahoma",
            "calibri",
        ]
        for name in candidates:
            if pygame.font.match_font(name):
                return name
        return None

    def _build_fonts(self):
        custom_font_path = self._find_custom_font_path()
        if custom_font_path:
            return {
                "title": pygame.font.Font(custom_font_path, 56),
                "subtitle": pygame.font.Font(custom_font_path, 28),
                "button": pygame.font.Font(custom_font_path, 30),
                "body": pygame.font.Font(custom_font_path, 26),
                "small": pygame.font.Font(custom_font_path, 22),
            }

        font_name = self._pick_readable_font()
        return {
            "title": pygame.font.SysFont(font_name, 56, bold=True),
            "subtitle": pygame.font.SysFont(font_name, 28, bold=True),
            "button": pygame.font.SysFont(font_name, 30, bold=True),
            "body": pygame.font.SysFont(font_name, 26, bold=False),
            "small": pygame.font.SysFont(font_name, 22, bold=False),
        }

    def _find_custom_font_path(self):
        base_dir = os.path.dirname(__file__)
        font_candidates = [
            os.path.join(base_dir, "Fuentes", "DeterminationMonoWebRegular-Z5oq.ttf"),
            os.path.join(base_dir, "Fuentes", "DeterminationMonoWeb.ttf"),
            os.path.join(base_dir, "Fonts", "DeterminationMonoWeb.ttf"),
        ]
        for path in font_candidates:
            if os.path.exists(path):
                return path
        return None

    def _load_story_interact_prompt(self):
        prompt_path = self._resolve_image_path("INTERACTUAR.webp")
        try:
            self.story_interact_prompt_img = pygame.image.load(prompt_path).convert_alpha()
            base_w = max(22, int(self.story_interact_prompt_img.get_width() * 0.24))
            base_h = max(22, int(self.story_interact_prompt_img.get_height() * 0.24))
            self.story_interact_prompt_scaled = pygame.transform.smoothscale(
                self.story_interact_prompt_img,
                (base_w, base_h),
            )
        except (OSError, pygame.error):
            self.story_interact_prompt_img = None
            self.story_interact_prompt_scaled = None

    def _load_story_seated_sprite(self):
        seated_path = self._resolve_image_path("seated.png")
        try:
            raw = pygame.image.load(seated_path).convert_alpha()
            self.story_seated_sprite = pygame.transform.smoothscale(
                raw,
                (
                    max(24, int(raw.get_width() * 2.8)),
                    max(24, int(raw.get_height() * 2.8)),
                ),
            )
        except (OSError, pygame.error):
            self.story_seated_sprite = None

    def _load_story_event_npc_sprites(self):
        base_dir = os.path.join(os.path.dirname(__file__), "Imagenes", "Personajes")
        sara_sheet = os.path.join(base_dir, "Sara", "Sara_dibujando.png")
        diego_sheet = os.path.join(base_dir, "Diego", "Diego_hablando.png")
        self.story_npc_sara_frames = self._load_sprite_sheet_frames(sara_sheet)
        self.story_npc_diego_frames = self._load_sprite_sheet_frames(diego_sheet)

    def _load_sprite_sheet_frames(self, path):
        frames = []
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except (OSError, pygame.error):
            return frames

        sw, sh = sheet.get_size()
        file_name = os.path.basename(str(path)).lower()
        is_static_anim = any(token in file_name for token in ("sentado", "parado", "idle", "stand"))
        frame_count = 1 if is_static_anim else (4 if sw >= 4 else 1)
        frame_w = max(1, sw // frame_count)
        for i in range(frame_count):
            rect = pygame.Rect(i * frame_w, 0, frame_w, sh)
            frame = sheet.subsurface(rect).copy()
            h = max(76, int(frame.get_height() * 0.82))
            w = max(42, int(frame.get_width() * (h / max(1, frame.get_height()))))
            frames.append(pygame.transform.smoothscale(frame, (w, h)))
        return frames

    def _load_npc_animation_frames(self, character_name, animation_file):
        key = (str(character_name), str(animation_file))
        if key in self.story_npc_hitbox_cache:
            return self.story_npc_hitbox_cache[key]
        npc_path = os.path.join(
            os.path.dirname(__file__),
            "Imagenes",
            "Personajes",
            str(character_name),
            str(animation_file),
        )
        frames = self._load_sprite_sheet_frames(npc_path)
        self.story_npc_hitbox_cache[key] = frames
        return frames

    def _is_first_day_classroom_context(self):
        event_id = self.story_current_event.get("id") if isinstance(self.story_current_event, dict) else None
        if event_id != "primer_dia":
            return False
        if self.aventura_fondo is None:
            return False
        map_name = os.path.basename(self.aventura_fondo.ruta_imagen).lower()
        return "salon" in map_name

    def _resolve_image_path(self, image_ref):
        images_dir = os.path.join(os.path.dirname(__file__), "Imagenes")
        if not image_ref:
            image_ref = "HabDía.png"

        normalized = os.path.normpath(str(image_ref).strip())
        direct_candidate = normalized if os.path.isabs(normalized) else os.path.join(os.path.dirname(__file__), normalized)
        if os.path.exists(direct_candidate):
            return direct_candidate

        file_name = os.path.basename(normalized)
        by_name = os.path.join(images_dir, file_name)
        if os.path.exists(by_name):
            return by_name

        file_name_lower = file_name.lower()
        try:
            for root, _, files in os.walk(images_dir):
                for name in files:
                    if name.lower() == file_name_lower:
                        return os.path.join(root, name)
        except OSError:
            pass

        return by_name

    def draw_pixel_text(self, text, x, y, style, color, center=True):
        base = self.base_fonts[style].render(text, True, color)
        scale = self.pixel_scale[style]
        if scale == 1:
            pixel_text = base
        else:
            pixel_text = pygame.transform.scale(
                base, (base.get_width() * scale, base.get_height() * scale)
            )
        rect = pixel_text.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(pixel_text, rect)
        return rect

    def _build_menu_buttons(self):
        labels = [
            ("Jugar", "jugar"),
            ("Configuracion", "configuracion"),
            ("Progreso", "progreso"),
            ("Salir", "salir"),
        ]
        buttons = []
        total_height = len(labels) * self.button_height + (len(labels) - 1) * self.button_gap
        center_y = self.height // 2 + 70
        start_y = center_y - total_height // 2
        for i, (text, action) in enumerate(labels):
            y = start_y + i * (self.button_height + self.button_gap)
            buttons.append(
                Button(
                    (
                        self.width // 2 - self.button_width // 2,
                        y,
                        self.button_width,
                        self.button_height,
                    ),
                    text,
                    action,
                )
            )
        return buttons

    def _build_play_buttons(self):
        labels = [
            ("Partida nueva", "partida_nueva"),
            ("Cargar partida", "cargar_partida"),
            ("Volver", "volver_menu"),
        ]
        buttons = []
        bw = min(380, int(self.width * 0.3))
        bh = 58
        gap = 14
        total_height = len(labels) * bh + (len(labels) - 1) * gap
        start_y = self.height // 2 - total_height // 2 + 40
        for i, (text, action) in enumerate(labels):
            y = start_y + i * (bh + gap)
            buttons.append(Button((self.width // 2 - bw // 2, y, bw, bh), text, action))
        return buttons

    def _build_pause_buttons(self):
        labels = [
            ("Guardar", "pause_guardar"),
            ("Configuracion", "configuracion"),
            ("Salir al menu", "pause_salir_menu"),
        ]
        buttons = []
        total_height = len(labels) * self.button_height + (len(labels) - 1) * self.button_gap
        center_y = self.height // 2 + 70
        start_y = center_y - total_height // 2
        for i, (text, action) in enumerate(labels):
            y = start_y + i * (self.button_height + self.button_gap)
            buttons.append(
                Button(
                    (
                        self.width // 2 - self.button_width // 2,
                        y,
                        self.button_width,
                        self.button_height,
                    ),
                    text,
                    action,
                )
            )
        return buttons

    def _save_slot_exists(self, slot):
        return os.path.exists(self.save_slot_files[slot])

    def _build_save_data(self):
        return {
            "save_version": SAVE_VERSION,
            "story_felicidad": self.story_felicidad,
            "story_reputacion": self.story_reputacion,
            "story_completed": self.story_completed,
            "story_event_pool": self.story_event_pool,
            "story_current_event": self.story_current_event,
            "story_thought": self.story_thought,
            "story_pending_end": self.story_pending_end,
            "story_final_key": self.story_final_key,
            "story_final_text": self.story_final_text,
            "character_colors": self.character_colors,
            "current_style": self.current_style,
            "settings": self.settings,
            "controls": self._serialize_controls(),
        }

    def _migrate_save_data(self, data):
        if not isinstance(data, dict):
            return {"save_version": SAVE_VERSION}
        migrated = dict(data)
        version = int(migrated.get("save_version", 1))

        if version < 2:
            migrated.setdefault("character_colors", self.character_colors.copy())
            migrated.setdefault("current_style", self.current_style.copy())
            migrated.setdefault("settings", self.settings.copy())
            migrated.setdefault("controls", self._serialize_controls())

        migrated["save_version"] = SAVE_VERSION
        return migrated

    def _apply_loaded_save_data(self, data):
        data = self._migrate_save_data(data)
        self._start_adventure()
        self.story_felicidad = int(data.get("story_felicidad", 50))
        self.story_reputacion = int(data.get("story_reputacion", 50))
        self.story_completed = int(data.get("story_completed", 0))
        self.story_event_pool = data.get("story_event_pool", self.story_event_pool)
        self.story_current_event = data.get("story_current_event", self.story_current_event)
        self.story_thought = data.get("story_thought", "")
        self.story_pending_end = bool(data.get("story_pending_end", False))
        self.story_final_key = data.get("story_final_key", "")
        self.story_final_text = data.get("story_final_text", "")
        loaded_colors = data.get("character_colors", {})
        if isinstance(loaded_colors, dict):
            for part, color in loaded_colors.items():
                if part in self.character_colors and isinstance(color, (list, tuple)) and len(color) == 3:
                    self.character_colors[part] = tuple(max(0, min(255, int(v))) for v in color)
        loaded_style = data.get("current_style", {})
        if isinstance(loaded_style, dict):
            for part, idx in loaded_style.items():
                if part in self.current_style:
                    max_idx = len(self.part_styles[part]) - 1
                    self.current_style[part] = max(0, min(max_idx, int(idx)))
        loaded_settings = data.get("settings", {})
        if isinstance(loaded_settings, dict):
            previous_fullscreen = bool(self.settings.get("Pantalla completa", False))
            for key in self.settings:
                if key in loaded_settings:
                    self.settings[key] = loaded_settings[key]
            if bool(self.settings.get("Pantalla completa", False)) != previous_fullscreen:
                self._apply_display_mode()
        loaded_controls = data.get("controls", {})
        self._apply_loaded_controls(loaded_controls)

    def _build_default_controls(self):
        controls = {}
        for action, key_name in DEFAULT_CONTROLS.items():
            try:
                key_value = pygame.key.key_code(key_name)
                controls[action] = key_value
            except ValueError:
                continue
        return controls

    def _serialize_controls(self):
        return {action: pygame.key.name(key) for action, key in self.controls.items()}

    def _apply_loaded_controls(self, loaded_controls):
        self.controls = self._build_default_controls()
        if not isinstance(loaded_controls, dict):
            return
        for action, key_name in loaded_controls.items():
            if action not in self.controls or not isinstance(key_name, str):
                continue
            try:
                key_value = pygame.key.key_code(key_name)
                self.controls[action] = key_value
            except ValueError:
                continue

    def _control_name(self, action):
        key = self.controls.get(action)
        if key is None:
            return "-"
        key_name = pygame.key.name(key).upper()
        if key_name == "RETURN":
            return "ENTER"
        return key_name

    def _rebind_control(self, action, new_key):
        if action not in self.controls:
            return
        if new_key == pygame.K_ESCAPE:
            self.waiting_control_action = None
            return
        for other_action, other_key in self.controls.items():
            if other_action != action and other_key == new_key:
                self.controls[other_action] = self.controls[action]
                break
        self.controls[action] = new_key
        self.waiting_control_action = None

    def _save_to_slot(self, slot):
        data = self._build_save_data()
        try:
            with open(self.save_slot_files[slot], "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=True, indent=2)
            return True
        except OSError:
            return False

    def _draw_pixel_background(self):
        self.screen.fill(BG_DARK)

        tile = 24
        for y in range(0, self.height, tile):
            for x in range(0, self.width, tile):
                if (x // tile + y // tile) % 2 == 0:
                    pygame.draw.rect(self.screen, BG_MID, (x, y, tile, tile))

        for x in range(0, self.width, 48):
            pygame.draw.line(self.screen, GRID, (x, 0), (x, self.height), 1)
        for y in range(0, self.height, 48):
            pygame.draw.line(self.screen, GRID, (0, y), (self.width, y), 1)

        if self.settings["Animaciones"]:
            for y in range(0, self.height, 3):
                pygame.draw.line(self.screen, (15, 13, 29), (0, y), (self.width, y), 1)

        pygame.draw.rect(self.screen, PIXEL_CYAN, (58, 58, 40, 40))
        pygame.draw.rect(self.screen, PIXEL_PINK, (self.width - 100, 88, 28, 28))
        pygame.draw.rect(self.screen, PIXEL_CYAN, (self.width - 118, self.height - 130, 44, 44))

    def _draw_menu(self):
        self._draw_pixel_background()

        first_button_y = self.buttons[0].rect.y
        title_y = first_button_y - 130
        subtitle_y = first_button_y - 72
        self.draw_pixel_text("EMPATIA QUEST", self.width // 2 + 4, title_y + 3, "title", (14, 15, 25), True)
        self.draw_pixel_text("EMPATIA QUEST", self.width // 2, title_y, "title", (245, 247, 255), True)
        self.draw_pixel_text(
            "La empatia tambien salva partidas", self.width // 2, subtitle_y, "subtitle", (198, 220, 255), True
        )

        mouse_pos = pygame.mouse.get_pos()
        for i, button in enumerate(self.buttons):
            hover = button.contains(mouse_pos) or i == self.selected_index
            button.draw(self.screen, self, hover=hover)

        hint = (
            "Mouse o flechas + Enter. ESC vuelve al menu."
        )
        self.draw_pixel_text(hint, self.width // 2, self.height - 40, "small", (194, 216, 248), True)

    def _draw_pause_screen(self):
        self._draw_adventure_screen()
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((10, 10, 16, 190))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(self.width // 2 - 360, self.height // 2 - 250, 720, 500)
        shadow = panel.move(6, 6)
        pygame.draw.rect(self.screen, (13, 12, 24), shadow)
        pygame.draw.rect(self.screen, CARD, panel)
        pygame.draw.rect(self.screen, CARD_BORDER, panel, width=5)

        self.draw_pixel_text("PAUSA", self.width // 2, panel.y + 56, "title", TEXT_MAIN, True)
        self.draw_pixel_text("Escoge una opcion", self.width // 2, panel.y + 108, "small", TEXT_SOFT, True)

        mouse_pos = pygame.mouse.get_pos()
        for i, button in enumerate(self.pause_buttons):
            hover = button.contains(mouse_pos) or i == self.pause_selected_index
            button.draw(self.screen, self, hover=hover)
            if button.contains(mouse_pos):
                self.pause_selected_index = i

        self.draw_pixel_text(
            "ESC: volver al juego | ENTER: seleccionar",
            self.width // 2,
            panel.bottom - 28,
            "small",
            TEXT_SOFT,
            True,
        )

    def _draw_pause_save_screen(self):
        self._draw_pixel_background()
        panel = pygame.Rect(self.width // 2 - 560, self.height // 2 - 280, 1120, 560)
        shadow = panel.move(6, 6)
        pygame.draw.rect(self.screen, (13, 12, 24), shadow)
        pygame.draw.rect(self.screen, CARD, panel)
        pygame.draw.rect(self.screen, CARD_BORDER, panel, width=5)

        self.draw_pixel_text("GUARDAR PARTIDA", self.width // 2, panel.y + 56, "title", TEXT_MAIN, True)
        self.draw_pixel_text("Selecciona una casilla para guardar.", self.width // 2, panel.y + 104, "small", TEXT_SOFT, True)

        mouse_pos = pygame.mouse.get_pos()
        row_height = 76
        for i in range(4):
            row = pygame.Rect(panel.x + 40, panel.y + 130 + i * row_height, panel.width - 80, 58)
            occupied = self._save_slot_exists(i)
            selected = i == self.save_slot_selected
            bg = CARD_HOVER if selected else (208, 216, 196)
            pygame.draw.rect(self.screen, bg, row)
            pygame.draw.rect(self.screen, CARD_BORDER, row, 3)
            status_text = "Ocupado" if occupied else "Vacio"
            self.draw_pixel_text(
                f"Slot {i+1} - {status_text}",
                row.x + 24,
                row.centery,
                "body",
                TEXT_MAIN,
                False,
            )
            detail_text = "ENTER para sobrescribir" if occupied else "ENTER para guardar"
            self.draw_pixel_text(
                detail_text,
                row.right - 300,
                row.centery,
                "small",
                TEXT_SOFT,
                False,
            )
            if row.collidepoint(mouse_pos):
                self.save_slot_selected = i

        back_rect = pygame.Rect(panel.x + panel.width // 2 - 120, panel.bottom - 90, 240, 52)
        pygame.draw.rect(self.screen, CARD_HOVER, back_rect)
        pygame.draw.rect(self.screen, CARD_BORDER, back_rect, 3)
        self.draw_pixel_text("Volver", back_rect.centerx, back_rect.centery, "button", TEXT_MAIN, True)

        if self.pause_overwrite_pending and self.pause_pending_slot is not None:
            confirm = pygame.Rect(self.width // 2 - 320, self.height // 2 - 80, 640, 170)
            pygame.draw.rect(self.screen, CARD, confirm)
            pygame.draw.rect(self.screen, CARD_BORDER, confirm, 4)
            self.draw_pixel_text(
                f"Slot {self.pause_pending_slot + 1} ya contiene una partida.",
                self.width // 2,
                confirm.y + 46,
                "small",
                TEXT_MAIN,
                True,
            )
            self.draw_pixel_text(
                "ENTER para sobrescribir | ESC para cancelar",
                self.width // 2,
                confirm.y + 108,
                "small",
                TEXT_SOFT,
                True,
            )

        self.draw_pixel_text(
            "Flechas para cambiar, ENTER para seleccionar, D borrar, ESC volver.",
            self.width // 2,
            panel.bottom - 24,
            "small",
            TEXT_SOFT,
            True,
        )

    def _draw_load_screen(self):
        self._draw_pixel_background()
        panel = pygame.Rect(self.width // 2 - 560, self.height // 2 - 280, 1120, 560)
        shadow = panel.move(6, 6)
        pygame.draw.rect(self.screen, (13, 12, 24), shadow)
        pygame.draw.rect(self.screen, CARD, panel)
        pygame.draw.rect(self.screen, CARD_BORDER, panel, width=5)

        self.draw_pixel_text("CARGAR PARTIDA", self.width // 2, panel.y + 56, "title", TEXT_MAIN, True)
        self.draw_pixel_text("Selecciona un slot para cargar o borrar.", self.width // 2, panel.y + 104, "small", TEXT_SOFT, True)

        mouse_pos = pygame.mouse.get_pos()
        row_height = 76
        for i in range(4):
            row = pygame.Rect(panel.x + 40, panel.y + 130 + i * row_height, panel.width - 80, 58)
            occupied = self._save_slot_exists(i)
            selected = i == self.save_slot_selected
            bg = CARD_HOVER if selected else (208, 216, 196)
            pygame.draw.rect(self.screen, bg, row)
            pygame.draw.rect(self.screen, CARD_BORDER, row, 3)
            status_text = "Ocupado" if occupied else "Vacio"
            self.draw_pixel_text(
                f"Slot {i+1} - {status_text}",
                row.x + 24,
                row.centery,
                "body",
                TEXT_MAIN,
                False,
            )
            detail_text = "ENTER para cargar" if occupied else "VACIO"
            self.draw_pixel_text(
                detail_text,
                row.right - 260,
                row.centery,
                "small",
                TEXT_SOFT,
                False,
            )
            if row.collidepoint(mouse_pos):
                self.save_slot_selected = i

        back_rect = pygame.Rect(panel.x + panel.width // 2 - 120, panel.bottom - 90, 240, 52)
        pygame.draw.rect(self.screen, CARD_HOVER, back_rect)
        pygame.draw.rect(self.screen, CARD_BORDER, back_rect, 3)
        self.draw_pixel_text("Volver", back_rect.centerx, back_rect.centery, "button", TEXT_MAIN, True)

        self.draw_pixel_text(
            "Flechas para cambiar, ENTER cargar, BACKSPACE borrar, ESC volver.",
            self.width // 2,
            panel.bottom - 24,
            "small",
            TEXT_SOFT,
            True,
        )

    def _load_slot(self, slot):
        if not self._save_slot_exists(slot):
            return False
        try:
            with open(self.save_slot_files[slot], "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return False
        self._apply_loaded_save_data(data)
        return True

    def _delete_slot(self, slot):
        if not self._save_slot_exists(slot):
            return False
        try:
            os.remove(self.save_slot_files[slot])
            return True
        except OSError:
            return False

    def _draw_panel_screen(self, title, lines):
        self._draw_pixel_background()
        panel = pygame.Rect(self.width // 2 - 340, self.height // 2 - 185, 680, 370)
        shadow = panel.move(6, 6)
        pygame.draw.rect(self.screen, (13, 12, 24), shadow)
        pygame.draw.rect(self.screen, CARD, panel)
        pygame.draw.rect(self.screen, CARD_BORDER, panel, width=5)

        self.draw_pixel_text(title, self.width // 2, panel.y + 45, "title", TEXT_MAIN, True)

        y = panel.y + 130
        for line in lines:
            self.draw_pixel_text(line, self.width // 2, y, "body", TEXT_SOFT, True)
            y += 42

        self.draw_pixel_text(
            "Presiona ESC para volver al menu", self.width // 2, panel.y + panel.height - 50, "small", (62, 74, 98), True
        )

    def _open_action(self, action):
        if action == "salir":
            self.running = False
            return
        if action == "jugar":
            self.current_screen = "jugar"
            return
        if action == "partida_nueva":
            self.current_screen = "creador"
            return
        if action == "cargar_partida":
            self.current_screen = "load_slots"
            self.save_slot_selected = 0
            self.pause_overwrite_pending = False
            self.pause_pending_slot = None
            self.message = "Selecciona un slot para cargar o borrar."
            return
        if action == "simulacion":
            self._init_simulacion()
            self.current_screen = "simulacion"
            return
        if action == "pause_guardar":
            self.current_screen = "pause_guardar"
            self.save_slot_selected = 0
            self.pause_overwrite_pending = False
            self.pause_pending_slot = None
            return
        if action == "pause_salir_menu":
            self.current_screen = "menu"
            return
        if action == "volver_menu":
            self.current_screen = "menu"
            return
        if action == "configuracion":
            self.previous_screen = self.current_screen
            self.current_screen = "configuracion"
            return
        self.current_screen = action
        self.message = f"Pantalla {action} abierta"

    def _handle_menu_events(self, event):
        if event.type == pygame.MOUSEMOTION:
            for i, button in enumerate(self.buttons):
                if button.contains(event.pos):
                    self.selected_index = i
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.contains(event.pos):
                    self._open_action(button.action)
                    return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.buttons)
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._open_action(self.buttons[self.selected_index].action)

    def _handle_pause_events(self, event):
        if event.type == pygame.MOUSEMOTION:
            for i, button in enumerate(self.pause_buttons):
                if button.contains(event.pos):
                    self.pause_selected_index = i
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.pause_buttons:
                if button.contains(event.pos):
                    self._open_action(button.action)
                    return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.pause_selected_index = (self.pause_selected_index + 1) % len(self.pause_buttons)
            elif event.key == pygame.K_UP:
                self.pause_selected_index = (self.pause_selected_index - 1) % len(self.pause_buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._open_action(self.pause_buttons[self.pause_selected_index].action)

    def _handle_pause_save_events(self, event):
        if event.type != pygame.KEYDOWN and event.type != pygame.MOUSEBUTTONDOWN:
            return

        if self.pause_overwrite_pending and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_save_slot()
            elif event.key == pygame.K_ESCAPE:
                self.pause_overwrite_pending = False
                self.pause_pending_slot = None
                self.message = "Guardado cancelado."
            return

        if event.type == pygame.MOUSEMOTION:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.save_slot_selected = (self.save_slot_selected + 1) % 5
                return
            elif event.key == pygame.K_UP:
                self.save_slot_selected = (self.save_slot_selected - 1) % 5
                return
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.save_slot_selected < 4:
                    if self._save_slot_exists(self.save_slot_selected):
                        self.pause_overwrite_pending = True
                        self.pause_pending_slot = self.save_slot_selected
                        self.message = f"Slot {self.save_slot_selected + 1} ya existe. ENTER para sobrescribir."
                    else:
                        saved = self._save_to_slot(self.save_slot_selected)
                        self.message = (
                            f"Guardado en Slot {self.save_slot_selected + 1}."
                            if saved
                            else "No se pudo guardar la partida."
                        )
                else:
                    self.current_screen = "pause"
                return
            elif event.key == pygame.K_ESCAPE:
                self.current_screen = "pause"
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            panel = pygame.Rect(self.width // 2 - 560, self.height // 2 - 280, 1120, 560)
            row_height = 76
            for i in range(4):
                row = pygame.Rect(panel.x + 40, panel.y + 130 + i * row_height, panel.width - 80, 58)
                if row.collidepoint(event.pos):
                    self.save_slot_selected = i
                    if self._save_slot_exists(i):
                        self.pause_overwrite_pending = True
                        self.pause_pending_slot = i
                        self.message = f"Slot {i + 1} ya existe. ENTER para sobrescribir."
                    else:
                        saved = self._save_to_slot(i)
                        self.message = (
                            f"Guardado en Slot {i + 1}."
                            if saved
                            else "No se pudo guardar la partida."
                        )
                    return
            back_rect = pygame.Rect(panel.x + panel.width // 2 - 120, panel.bottom - 90, 240, 52)
            if back_rect.collidepoint(event.pos):
                self.current_screen = "pause"
                return

    def _confirm_save_slot(self):
        if self.pause_pending_slot is None:
            return
        saved = self._save_to_slot(self.pause_pending_slot)
        if saved:
            self.message = f"Slot {self.pause_pending_slot + 1} sobrescrito."
        else:
            self.message = "No se pudo guardar la partida."
        self.pause_overwrite_pending = False
        self.pause_pending_slot = None

    def _handle_load_events(self, event):
        if event.type != pygame.KEYDOWN and event.type != pygame.MOUSEBUTTONDOWN:
            return

        if self.pause_overwrite_pending and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm_save_slot()
            elif event.key == pygame.K_ESCAPE:
                self.pause_overwrite_pending = False
                self.pause_pending_slot = None
                self.message = "Operacion cancelada."
            return

        if event.type == pygame.MOUSEMOTION:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.save_slot_selected = (self.save_slot_selected + 1) % 5
                return
            elif event.key == pygame.K_UP:
                self.save_slot_selected = (self.save_slot_selected - 1) % 5
                return
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.save_slot_selected < 4:
                    if self._save_slot_exists(self.save_slot_selected):
                        if self._load_slot(self.save_slot_selected):
                            self.current_screen = "aventura"
                            self.message = f"Slot {self.save_slot_selected + 1} cargado."
                        else:
                            self.message = "No se pudo cargar la partida."
                    else:
                        self.message = "Slot vacio. Elige otro slot."
                else:
                    self.current_screen = "menu"
                return
            elif event.key == pygame.K_BACKSPACE:
                if self.save_slot_selected < 4 and self._save_slot_exists(self.save_slot_selected):
                    deleted = self._delete_slot(self.save_slot_selected)
                    self.message = (
                        f"Slot {self.save_slot_selected + 1} borrado." if deleted else "No se pudo borrar el slot."
                    )
                else:
                    self.message = "No hay partida en ese slot para borrar."
                return
            elif event.key == pygame.K_ESCAPE:
                self.current_screen = "menu"
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            panel = pygame.Rect(self.width // 2 - 560, self.height // 2 - 280, 1120, 560)
            row_height = 76
            for i in range(4):
                row = pygame.Rect(panel.x + 40, panel.y + 130 + i * row_height, panel.width - 80, 58)
                if row.collidepoint(event.pos):
                    self.save_slot_selected = i
                    if self._save_slot_exists(i):
                        if self._load_slot(i):
                            self.current_screen = "aventura"
                            self.message = f"Slot {i + 1} cargado."
                        else:
                            self.message = "No se pudo cargar la partida."
                    else:
                        self.message = "Slot vacio. Usa ENTER para cargar otro slot."
                    return
            back_rect = pygame.Rect(panel.x + panel.width // 2 - 120, panel.bottom - 90, 240, 52)
            if back_rect.collidepoint(event.pos):
                self.current_screen = "menu"
                return

    def _handle_play_events(self, event):
        if event.type == pygame.MOUSEMOTION:
            for i, button in enumerate(self.play_buttons):
                if button.contains(event.pos):
                    self.selected_play_index = i
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.play_buttons:
                if button.contains(event.pos):
                    self._open_action(button.action)
                    return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_play_index = (self.selected_play_index + 1) % len(self.play_buttons)
            elif event.key == pygame.K_UP:
                self.selected_play_index = (self.selected_play_index - 1) % len(self.play_buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._open_action(self.play_buttons[self.selected_play_index].action)

    def _init_simulacion(self):
        if self.simulacion_activa:
            return
        
        base_path = os.path.dirname(__file__)
        ruta_imagenes = os.path.join(base_path, "Imagenes", "Personajes", "personaje_main")
        self.simulacion_fondo = Fondo(self._resolve_image_path("Salon(1).jpg"), 0, 0)
        self.simulacion_personaje = Personaje(600, 280, ruta_imagenes, velocidad=4, fps_animacion=8, color=self.character_colors["Piel"])
        self.simulacion_animacion = Animacion(
            self._resolve_image_path("Caminar.png"),
            5,
            fps_animacion=5,
            x=800,
            y=400,
        )
        self.simulacion_animacion.velocidad = 3
        self.simulacion_animacion.mover_lateral(100, 700)
        self.simulacion_aviso = pygame.image.load(self._resolve_image_path("INTERACTUAR.webp")).convert_alpha()
        self.simulacion_pared1 = pygame.Rect(290, 290, 100, 100)
        self.simulacion_pared2 = pygame.Rect(500, 290, 100, 100)
        self.simulacion_mostrar_aviso = False
        self.simulacion_activa = True

    def _update_simulacion(self):
        if self.current_screen != "simulacion" or not self.simulacion_activa:
            return

        x_anterior = self.simulacion_personaje.x
        y_anterior = self.simulacion_personaje.y
        self.simulacion_personaje.actualizar()

        if self.simulacion_personaje.hitbox.colliderect(self.simulacion_pared1) or self.simulacion_personaje.hitbox.colliderect(self.simulacion_pared2):
            self.simulacion_personaje.x = x_anterior
            self.simulacion_personaje.y = y_anterior
            self.simulacion_personaje.hitbox.x = x_anterior
            self.simulacion_personaje.hitbox.y = y_anterior

        self.simulacion_mostrar_aviso = self.simulacion_personaje.hitbox.colliderect(self.simulacion_pared2)
        self.simulacion_animacion.actualizar()
        self.simulacion_animacion.mover_lateral(100, 700)

    def _draw_simulacion_screen(self):
        if not self.simulacion_activa:
            self._draw_panel_screen("SIMULACION", ["No se pudo cargar la simulacion."])
            return

        self.simulacion_fondo.dibujar(self.screen)
        if self.settings.get("Mostrar hitboxes", False):
            pygame.draw.rect(self.screen, (180, 50, 50), self.simulacion_pared1, 2)
            pygame.draw.rect(self.screen, (180, 50, 50), self.simulacion_pared2, 2)
            pygame.draw.rect(self.screen, (255, 0, 0), self.simulacion_personaje.hitbox, 2)
            pygame.draw.rect(self.screen, (255, 220, 0), self.simulacion_personaje.interactable_hitbox, 2)
        self.simulacion_personaje.dibujar(self.screen)
        self.simulacion_animacion.dibujar(self.screen)
        if self.simulacion_mostrar_aviso:
            self.screen.blit(self.simulacion_aviso, (self.simulacion_pared2.x - 30, self.simulacion_pared2.y - 50))
        color = self.character_colors["Piel"]
        self.draw_pixel_text(f"Color de piel: R{color[0]} G{color[1]} B{color[2]}", self.width // 2, 50, "small", (255, 255, 255), True)
        self.draw_pixel_text("Flechas: cambiar R/G, Q/W: cambiar B, ENTER: guardar", self.width // 2, 80, "small", (255, 255, 255), True)
        self.draw_pixel_text("ESC: menu", self.width // 2, self.height - 32, "small", (255, 255, 255), True)

    def _handle_simulacion_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.current_screen = "jugar"
            elif event.key == pygame.K_LEFT:
                self._change_selected_color_channel(0, -10)
                self._reinit_simulacion_personaje()
            elif event.key == pygame.K_RIGHT:
                self._change_selected_color_channel(0, 10)
                self._reinit_simulacion_personaje()
            elif event.key == pygame.K_DOWN:
                self._change_selected_color_channel(1, -10)
                self._reinit_simulacion_personaje()
            elif event.key == pygame.K_UP:
                self._change_selected_color_channel(1, 10)
                self._reinit_simulacion_personaje()
            elif event.key == pygame.K_q:
                self._change_selected_color_channel(2, -10)
                self._reinit_simulacion_personaje()
            elif event.key == pygame.K_w:
                self._change_selected_color_channel(2, 10)
                self._reinit_simulacion_personaje()
            elif event.key == pygame.K_RETURN:
                self.message = "Personaje guardado. Listo para comenzar."
                self.current_screen = "jugar"

    def _reinit_simulacion_personaje(self):
        base_path = os.path.dirname(__file__)
        ruta_imagenes = os.path.join(base_path, "Imagenes", "Personajes", "personaje_main")
        self.simulacion_personaje = Personaje(600, 280, ruta_imagenes, velocidad=4, fps_animacion=8, color=self.character_colors["Piel"])
    def _selected_part(self):
        return self.custom_parts[self.selected_custom_index]

    def _change_selected_color_channel(self, channel_index, delta):
        part = self._selected_part()
        color = list(self.character_colors[part])
        color[channel_index] = max(0, min(255, color[channel_index] + delta))
        self.character_colors[part] = tuple(color)

    def _change_part_style(self, delta):
        part = self._selected_part()
        styles = self.part_styles[part]
        self.current_style[part] = (self.current_style[part] + delta) % len(styles)

    def _handle_creator_events(self, event):
        panel = pygame.Rect(self.width // 2 - 520, self.height // 2 - 280, 1040, 560)
        left_x = panel.x + 40
        list_top = panel.y + 110
        list_row_h = 44
        palette_top = panel.y + 448
        palette_cols = 6
        sw = 44
        gap = 12
        sliders_x = panel.x + 420
        sliders_top = panel.y + 160
        slider_w = 420

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(self.custom_parts)):
                row = pygame.Rect(left_x, list_top + i * list_row_h, 280, list_row_h - 4)
                if row.collidepoint(event.pos):
                    self.selected_custom_index = i
                    return

            for idx, color in enumerate(self.palette_colors):
                r = idx // palette_cols
                c = idx % palette_cols
                x = left_x + c * (sw + gap)
                y = palette_top + r * (sw + gap)
                rect = pygame.Rect(x, y, sw, sw)
                if rect.collidepoint(event.pos):
                    self.character_colors[self._selected_part()] = color
                    return

            for s in range(3):
                bar_rect = pygame.Rect(sliders_x, sliders_top + s * 82, slider_w, 16)
                if bar_rect.collidepoint(event.pos):
                    rel_x = max(0, min(slider_w, event.pos[0] - sliders_x))
                    value = int((rel_x / slider_w) * 255)
                    part = self._selected_part()
                    col = list(self.character_colors[part])
                    col[s] = value
                    self.character_colors[part] = tuple(col)
                    self.selected_slider = s
                    return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_custom_index = (self.selected_custom_index + 1) % len(self.custom_parts)
            elif event.key == pygame.K_UP:
                self.selected_custom_index = (self.selected_custom_index - 1) % len(self.custom_parts)
            elif event.key == pygame.K_a:
                self._change_part_style(-1)
            elif event.key == pygame.K_d:
                self._change_part_style(1)
            elif event.key == pygame.K_TAB:
                self.selected_slider = (self.selected_slider + 1) % 3
            elif event.key == pygame.K_LEFT:
                self._change_selected_color_channel(self.selected_slider, -5)
            elif event.key == pygame.K_RIGHT:
                self._change_selected_color_channel(self.selected_slider, 5)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.message = "Personaje guardado. Listo para comenzar."
                self._start_adventure()
                self.current_screen = "prologo"

    def _build_story_events(self):
        return build_story_events()

    def _condition_ok(self, condition):
        # Conservado para compatibilidad interna; la logica real vive en story.py.
        if condition is None:
            return True
        if condition == "f_40_49":
            return 40 <= self.story_felicidad < 50
        if condition == "f_25_39":
            return 25 <= self.story_felicidad < 40
        return False

    def _pick_next_event(self):
        return pick_next_event(self.story_event_pool, self.story_felicidad)

    def _start_adventure(self):
        self.story_felicidad = 50
        self.story_reputacion = 50
        all_events = self._build_story_events()
        first = next(e for e in all_events if e["id"] == "primer_dia")
        self.story_event_pool = []
        self.story_current_event = first
        self.story_completed = 0
        self.story_goal = 1
        self.story_thought = ""
        self.story_interaction_text = ""
        self.story_previous_map_name = None
        self.story_show_support = False
        self.story_pending_end = False
        self.story_final_key = ""
        self.story_final_text = ""
        self.story_is_seated = False
        self.story_seated_hitbox = None
        self.story_clock_day = 1
        self.story_clock_hour = 7
        self.story_clock_minute = 30
        self.story_clock_accumulator_ms = 0
        self.story_npc_sara_index = 0
        self.story_npc_diego_index = 0
        self.story_npc_anim_timer = 0
        self.story_npc_positions = {}
        self.story_npc_hitbox_cache = {}
        self.player_rect = pygame.Rect(0, 0, 28, 28)
        self._rebuild_story_world(keep_player=False)
        self.story_walls = []
        self._init_prologo()
        self.aventura_fondo = None
        self.aventura_personaje = None
        ruta_imagenes = os.path.join(os.path.dirname(__file__), "Imagenes", "Personajes", "personaje_main")
        try:
            self.aventura_fondo = Fondo(self._resolve_image_path("HabDía.png"), 0, 0)
        except (OSError, pygame.error):
            self.aventura_fondo = None
        self.story_walls = self._build_story_wall_hitboxes(self.aventura_fondo.ruta_imagen if self.aventura_fondo else None)
        spawn_x, spawn_y = self._get_spawn_position_for_current_map()
        try:
            self.aventura_personaje = Personaje(
                0,
                0,
                ruta_imagenes,
                velocidad=self.player_speed,
                fps_animacion=8,
                color=self.character_colors["Piel"],
            )
            self.aventura_personaje.hitbox.x = spawn_x
            self.aventura_personaje.hitbox.y = spawn_y
            self.aventura_personaje.sync_sprite_from_hitbox()
            self.player_rect = self.aventura_personaje.hitbox.copy()
        except (OSError, pygame.error, FileNotFoundError):
            self.aventura_personaje = None
        self.player_rect.clamp_ip(self.story_map_rect)
        self._update_story_camera()
        self.cached_background_scaled = None
        self.cached_background_size = None
        self.cached_background_source = None

    def _build_story_wall_hitboxes(self, image_path=None):
        # Prioriza hitboxes personalizadas exportadas desde hitbox_editor.py.
        # La imagen del fondo se escala a pantalla completa, por eso usamos el
        # tamaño real de la ventana al reescalar las coordenadas normalizadas.
        mx, my, mw, mh = 0, 0, self.width, self.height

        if image_path:
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            export_path = os.path.join(os.path.dirname(__file__), "Hitboxes", f"{image_name}_hitboxes.json")
            objects_path = os.path.join(os.path.dirname(__file__), "Objetos", f"{image_name}_objetos.json")
        else:
            export_path = os.path.join(os.path.dirname(__file__), "Hitboxes", "hitboxes_export.json")
            objects_path = None
        object_hitboxes = self._load_story_object_hitboxes(objects_path)
        try:
            with open(export_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            boxes = payload.get("hitboxes", [])
            spawn_data = payload.get("spawn", {})
            npc_positions = payload.get("npc_positions", {})
            self.story_spawn_world = None
            self.story_spawn_by_origin = {}
            self.story_npc_positions = {}
            if isinstance(npc_positions, dict):
                cleaned_positions = {}
                for npc_name, ndata in npc_positions.items():
                    if isinstance(ndata, dict) and "rx" in ndata and "ry" in ndata:
                        cleaned_positions[str(npc_name).lower()] = {
                            "rx": float(ndata.get("rx", 0.5)),
                            "ry": float(ndata.get("ry", 0.5)),
                            "rw": float(ndata.get("rw", 96 / max(1, self.story_world_width))),
                            "rh": float(ndata.get("rh", 96 / max(1, self.story_world_height))),
                        }
                self.story_npc_positions = cleaned_positions
            if isinstance(spawn_data, dict):
                # New format
                if "default" in spawn_data or "by_origin" in spawn_data:
                    default_spawn = spawn_data.get("default")
                    if isinstance(default_spawn, dict) and "rx" in default_spawn and "ry" in default_spawn:
                        sx = int(float(default_spawn.get("rx", 0.5)) * self.story_world_width)
                        sy = int(float(default_spawn.get("ry", 0.5)) * self.story_world_height)
                        self.story_spawn_world = (sx, sy)
                    by_origin = spawn_data.get("by_origin", {})
                    if isinstance(by_origin, dict):
                        for origin_name, sdata in by_origin.items():
                            if isinstance(sdata, dict) and "rx" in sdata and "ry" in sdata:
                                ox = int(float(sdata.get("rx", 0.5)) * self.story_world_width)
                                oy = int(float(sdata.get("ry", 0.5)) * self.story_world_height)
                                self.story_spawn_by_origin[str(origin_name)] = (ox, oy)
                # Old format
                elif "rx" in spawn_data and "ry" in spawn_data:
                    sx = int(float(spawn_data.get("rx", 0.5)) * self.story_world_width)
                    sy = int(float(spawn_data.get("ry", 0.5)) * self.story_world_height)
                    self.story_spawn_world = (sx, sy)
            # Backward compatibility
            for h in boxes:
                if "type" not in h:
                    h["type"] = "rect"
                if "role" not in h:
                    h["role"] = "wall"
                if h["role"] == "interactable" and "action" not in h:
                    h["action"] = "puerta"
                if h["role"] == "interactable" and "target_image" not in h:
                    h["target_image"] = ""
            return boxes + object_hitboxes
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

        # Fallback: sin hitboxes si no hay export.
        self.story_spawn_world = None
        self.story_spawn_by_origin = {}
        self.story_npc_positions = {}
        return object_hitboxes

    def _load_story_object_hitboxes(self, objects_path):
        if not objects_path:
            return []
        try:
            with open(objects_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            objects = payload.get("objects", [])
        except (OSError, json.JSONDecodeError, TypeError):
            return []

        hitboxes = []
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            try:
                hitbox = {
                    "type": "rect",
                    "role": "interactable",
                    "action": "objeto",
                    "blocking": True,
                    "object_name": str(obj.get("name", "")),
                    "rx": float(obj["x"]),
                    "ry": float(obj["y"]),
                    "rw": float(obj["w"]),
                    "rh": float(obj["h"]),
                }
                crop = obj.get("crop")
                if isinstance(crop, dict):
                    try:
                        hitbox["crop"] = {
                            "x": float(crop.get("x", 0.0)),
                            "y": float(crop.get("y", 0.0)),
                            "w": float(crop.get("w", 1.0)),
                            "h": float(crop.get("h", 1.0)),
                        }
                    except (TypeError, ValueError):
                        pass
                hitboxes.append(hitbox)
            except (KeyError, TypeError, ValueError):
                continue
        return hitboxes

    def _get_spawn_position_for_current_map(self):
        if self.story_previous_map_name:
            by_origin_spawn = self.story_spawn_by_origin.get(self.story_previous_map_name)
            if by_origin_spawn is not None:
                sx, sy = by_origin_spawn
                sx = max(0, min(self.story_world_width, sx))
                sy = max(0, min(self.story_world_height, sy))
                return sx, sy
        if self.story_spawn_world is not None:
            sx, sy = self.story_spawn_world
            sx = max(0, min(self.story_world_width, sx))
            sy = max(0, min(self.story_world_height, sy))
            return sx, sy
        sx = max(0, min(self.story_world_width, (self.story_world_width // 2) + self.story_spawn_offset_x))
        sy = max(0, min(self.story_world_height, (self.story_world_height // 2) + self.story_spawn_offset_y))
        return sx, sy

    def _collides_with_hitbox(self, personaje_rect, h):
        mx, my, mw, mh = 0, 0, self.story_world_width, self.story_world_height
        if h["type"] == "rect":
            r = pygame.Rect(
                mx + int(mw * h["rx"]),
                my + int(mh * h["ry"]),
                max(8, int(mw * h["rw"])),
                max(8, int(mh * h["rh"])),
            )
            return personaje_rect.colliderect(r)
        elif h["type"] == "circle":
            cx = mx + int(mw * h["cx"])
            cy = my + int(mh * h["cy"])
            radius = max(8, int(mw * h["r"]))
            nearest_x = max(personaje_rect.left, min(cx, personaje_rect.right))
            nearest_y = max(personaje_rect.top, min(cy, personaje_rect.bottom))
            dx = cx - nearest_x
            dy = cy - nearest_y
            return (dx * dx + dy * dy) <= (radius * radius)
        elif h["type"] == "line":
            x1 = mx + int(mw * h["x1"])
            y1 = my + int(mh * h["y1"])
            x2 = mx + int(mw * h["x2"])
            y2 = my + int(mh * h["y2"])

            steps = max(1, int(max(abs(x2 - x1), abs(y2 - y1)) / 4))
            thickness_norm = float(h.get("thickness", 8 / max(1, self.story_world_width)))
            thickness_px = max(1, int(thickness_norm * self.story_world_width))
            probe_radius = max(2, thickness_px // 2)
            probe_diameter = probe_radius * 2
            for i in range(steps + 1):
                t = i / steps
                px = int(x1 + (x2 - x1) * t)
                py = int(y1 + (y2 - y1) * t)
                probe = pygame.Rect(px - probe_radius, py - probe_radius, probe_diameter, probe_diameter)
                if personaje_rect.colliderect(probe):
                    return True
            return False
        return False

    def _is_blocking_hitbox(self, h):
        return h.get("role", "wall") != "interactable" or bool(h.get("blocking", False))

    def _collides_with_interaction_area(self, personaje_rect, h):
        margin = int(getattr(self, "story_interaction_margin", 42))
        mx, my, mw, mh = 0, 0, self.story_world_width, self.story_world_height
        if h.get("type") == "rect":
            rect = pygame.Rect(
                mx + int(mw * h["rx"]),
                my + int(mh * h["ry"]),
                max(8, int(mw * h["rw"])),
                max(8, int(mh * h["rh"])),
            )
            return personaje_rect.colliderect(rect.inflate(margin * 2, margin * 2))
        if h.get("type") == "circle":
            probe = personaje_rect.inflate(margin * 2, margin * 2)
            return self._collides_with_hitbox(probe, h)
        if h.get("type") == "line":
            probe = personaje_rect.inflate(margin * 2, margin * 2)
            return self._collides_with_hitbox(probe, h)
        return self._collides_with_hitbox(personaje_rect, h)

    def _get_player_interactable(self):
        probe_rect = self.player_rect
        if self.aventura_personaje is not None:
            probe_rect = self.aventura_personaje.interactable_hitbox
        for h in self.story_walls:
            if h.get("role", "wall") == "interactable" and self._collides_with_interaction_area(probe_rect, h):
                return h
        return None

    def _should_show_interactable_prompt(self):
        interactable = self._get_player_interactable()
        if interactable is None:
            return False
        return interactable.get("action", "puerta") != "npc"

    def _interactable_center(self, h):
        mx, my, mw, mh = 0, 0, self.story_world_width, self.story_world_height
        if h["type"] == "rect":
            r = pygame.Rect(
                mx + int(mw * h["rx"]),
                my + int(mh * h["ry"]),
                max(8, int(mw * h["rw"])),
                max(8, int(mh * h["rh"])),
            )
            return r.center
        if h["type"] == "circle":
            cx = mx + int(mw * h["cx"])
            cy = my + int(mh * h["cy"])
            return (cx, cy)
        if h["type"] == "line":
            x1 = mx + int(mw * h["x1"])
            y1 = my + int(mh * h["y1"])
            x2 = mx + int(mw * h["x2"])
            y2 = my + int(mh * h["y2"])
            return ((x1 + x2) // 2, (y1 + y2) // 2)
        return self.player_rect.center

    def _set_player_center(self, center):
        self.player_rect.center = center
        self.player_rect.clamp_ip(self.story_map_rect)
        if self.aventura_personaje is not None:
            self.aventura_personaje.hitbox.x = self.player_rect.x
            self.aventura_personaje.hitbox.y = self.player_rect.y
            self.aventura_personaje.sync_sprite_from_hitbox()

    def _toggle_seat_state(self, interactable):
        if self.story_is_seated:
            self.story_is_seated = False
            self.story_seated_hitbox = None
            self.story_thought = "Te levantaste de la silla."
            self.story_interaction_text = "Ya no estas sentado."
            return
        center = self._interactable_center(interactable)
        self._set_player_center(center)
        self.story_is_seated = True
        self.story_seated_hitbox = interactable
        self.story_thought = "Te sentaste."
        self.story_interaction_text = "Estas sentado. Presiona E para levantarte."
        if (
            self.story_current_event is not None
            and self.story_current_event.get("id") == "primer_dia"
            and self._is_first_day_classroom_context()
            and interactable is not None
        ):
            silla_idx = None
            for i, hb in enumerate(self.story_walls, start=1):
                if hb is interactable:
                    silla_idx = i
                    break
            options = self.story_current_event.get("options", [])
            if silla_idx == 42 and len(options) >= 1:
                self._apply_story_choice(options[0])  # Sara
                self.story_interaction_text = "Elegiste sentarte con Sara."
            elif silla_idx == 43 and len(options) >= 2:
                self._apply_story_choice(options[1])  # Diego
                self.story_interaction_text = "Elegiste sentarte con Diego."

    def _change_adventure_background(self, target_image_name):
        if not target_image_name:
            self.story_interaction_text = "Esta puerta no tiene destino."
            return
        prev_name = os.path.basename(self.aventura_fondo.ruta_imagen) if self.aventura_fondo is not None else None
        target_path = self._resolve_image_path(target_image_name)
        if not os.path.exists(target_path):
            self.story_interaction_text = f"Destino no encontrado: {target_image_name}"
            return
        try:
            self.aventura_fondo = Fondo(target_path, 0, 0)
        except (OSError, pygame.error):
            self.story_interaction_text = f"No se pudo cargar: {target_image_name}"
            return

        self.cached_background_scaled = None
        self.cached_background_size = None
        self.cached_background_source = None
        self.story_previous_map_name = prev_name
        self.story_walls = self._build_story_wall_hitboxes(self.aventura_fondo.ruta_imagen)
        self._rebuild_story_world(keep_player=False)
        spawn_x, spawn_y = self._get_spawn_position_for_current_map()
        self.player_rect.x = spawn_x
        self.player_rect.y = spawn_y
        self.player_rect.clamp_ip(self.story_map_rect)
        if self.aventura_personaje is not None:
            self.aventura_personaje.hitbox.x = self.player_rect.x
            self.aventura_personaje.hitbox.y = self.player_rect.y
            self.aventura_personaje.sync_sprite_from_hitbox()
        self._update_story_camera()
        self.story_interaction_text = f"Entraste a: {target_image_name}"

    def _execute_interactable_action(self, interactable):
        action = interactable.get("action", "puerta")
        if action == "puerta":
            if self.story_is_seated:
                self.story_is_seated = False
                self.story_seated_hitbox = None
            self.story_thought = "Cruzaste una puerta."
            self._change_adventure_background(interactable.get("target_image", ""))
            return
        if action == "silla":
            self._toggle_seat_state(interactable)
            return
        if action == "npc":
            npc_name = interactable.get("npc_character", "NPC")
            self.story_interaction_text = f"{npc_name} esta ocupado/a."
            return
        if action == "objeto":
            object_name = os.path.splitext(interactable.get("object_name", "objeto"))[0]
            self.story_interaction_text = f"Interactuaste con {object_name}."
            self.story_thought = "Hay algo interesante aqui."
            return
        self.story_interaction_text = f"Accion no soportada: {action}"
        self.story_thought = "No paso nada."

    def _init_prologo(self):
        self.prologo_razon = random.choice(PROLOGO_RAZON_CHOICES)
        self.prologo_textos = [
            {"speaker": "Narrador", "text": "Escuela primaria antigua. Recreo en un patio pequeno y silencioso."},
            {"speaker": "Narrador", "text": "Un grupo de ninos empieza a burlarse del protagonista."},
            {"speaker": "Narrador", "text": "Otros estudiantes observan sin intervenir. Algunos se rien."},
            {"speaker": "Narrador", "text": "Un adulto pasa cerca, pero no nota la situacion."},
            {"speaker": "Narrador", "text": f"Esta vez las burlas empezaron por: {self.prologo_razon}."},
            {"speaker": "NPC 1", "text": "Por que eres tan raro?"},
            {"speaker": "NPC 2", "text": "Ni siquiera sabe responder."},
            {"speaker": "NPC 3", "text": "Dejalo, siempre es asi."},
            {"speaker": "Protagonista", "text": "Recuerdo pensar que alguien debia hacer algo... aunque fuera una sola persona."},
            {"speaker": "Narrador", "text": "Pantalla negra. Transicion al presente."},
        ]
        self.prologo_paso = 0
        self.prologo_activo = True

    def _save_game(self):
        data = self._build_save_data()
        try:
            with open(self.save_file, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=True, indent=2)
            return True
        except OSError:
            return False

    def _load_game(self):
        try:
            with open(self.save_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return False
        self._apply_loaded_save_data(data)
        return True

    def _apply_story_choice(self, option):
        self.story_felicidad = max(0, min(100, self.story_felicidad + option["dF"]))
        self.story_reputacion = max(0, min(100, self.story_reputacion + option["dR"]))
        self.story_thought = option["thought"]
        self.story_completed += 1
        self.story_show_support = bool(self.story_current_event.get("sensitive"))
        self.story_current_event = self._pick_next_event()
        if self.story_completed >= self.story_goal or self.story_current_event is None:
            self._resolve_ending()

    def _resolve_ending(self):
        f = self.story_felicidad
        r = self.story_reputacion
        self.story_pending_end = True
        if f >= 50 and r >= 50:
            self.story_final_key = "FINAL POSITIVO — ALGUIEN HIZO ALGO"
            self.story_final_text = "Tal vez cambiar todo era imposible, pero alguien tenia que empezar."
        elif f < 50 and r < 50:
            self.story_final_key = "FINAL NEGATIVO — TODOS MIRARON"
            self.story_final_text = "Lo peor nunca fue el ruido, fue acostumbrarse a el."
        elif f < 50:
            self.story_final_key = "FINAL NEUTRAL — FELICIDAD BAJA"
            self.story_final_text = "Ser conocido no alcanzo para que todos se sintieran seguros."
        else:
            self.story_final_key = "FINAL NEUTRAL — REPUTACION BAJA"
            self.story_final_text = "Ayudar importo, aunque no siempre fuera comprendido."

    def _move_player_with_walls(self, dx, dy):
        currently_stuck = False
        for wall in self.story_walls:
            if not self._is_blocking_hitbox(wall):
                continue
            if self._collides_with_hitbox(self.player_rect, wall):
                currently_stuck = True
                break

        prev_x = self.player_rect.x
        self.player_rect.x += dx
        self.player_rect.clamp_ip(self.story_map_rect)
        if not currently_stuck:
            for wall in self.story_walls:
                if not self._is_blocking_hitbox(wall):
                    continue
                if self._collides_with_hitbox(self.player_rect, wall):
                    self.player_rect.x = prev_x
                    break
        prev_y = self.player_rect.y
        self.player_rect.y += dy
        self.player_rect.clamp_ip(self.story_map_rect)
        if not currently_stuck:
            for wall in self.story_walls:
                if not self._is_blocking_hitbox(wall):
                    continue
                if self._collides_with_hitbox(self.player_rect, wall):
                    self.player_rect.y = prev_y
                    break

    def _update_adventure(self):
        if self.current_screen != "aventura" or self.story_pending_end:
            return
        dt_ms = self.clock.get_time()
        self.story_npc_anim_timer += dt_ms
        if self.story_npc_anim_timer >= 1000000:
            self.story_npc_anim_timer = 0
        if self._is_first_day_classroom_context():
            self.story_clock_accumulator_ms += dt_ms
            while self.story_clock_accumulator_ms >= 4000:
                self.story_clock_accumulator_ms -= 4000
                self.story_clock_minute += 1
                if self.story_clock_minute >= 60:
                    self.story_clock_minute = 0
                    self.story_clock_hour += 1
                    if self.story_clock_hour >= 24:
                        self.story_clock_hour = 0
                        self.story_clock_day += 1
            if self.story_npc_sara_frames:
                self.story_npc_sara_index = (self.story_npc_anim_timer // 220) % len(self.story_npc_sara_frames)
            if self.story_npc_diego_frames:
                self.story_npc_diego_index = (self.story_npc_anim_timer // 220) % len(self.story_npc_diego_frames)
        if self.story_is_seated:
            if self.aventura_personaje is not None:
                self.aventura_personaje.moviendose = False
                self.aventura_personaje.frame_actual = 0
                self.aventura_personaje.contador_animacion = 0
            self._update_story_camera()
            return
        keys = pygame.key.get_pressed()
        sprint_activo = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        velocidad_actual = self.player_speed * (1.8 if sprint_activo else 1.0)
        move_x = (
            (1 if keys[self.controls["mover_derecha"]] else 0)
            - (1 if keys[self.controls["mover_izquierda"]] else 0)
        ) * velocidad_actual
        move_y = (
            (1 if keys[self.controls["mover_abajo"]] else 0)
            - (1 if keys[self.controls["mover_arriba"]] else 0)
        ) * velocidad_actual
        prev_x = self.player_rect.x
        prev_y = self.player_rect.y
        self._move_player_with_walls(move_x, move_y)
        actual_dx = self.player_rect.x - prev_x
        actual_dy = self.player_rect.y - prev_y
        self._update_story_camera()
        if self.aventura_personaje is not None:
            self.aventura_personaje.hitbox.x = self.player_rect.x
            self.aventura_personaje.hitbox.y = self.player_rect.y
            self.aventura_personaje.sync_sprite_from_hitbox()
            self.aventura_personaje.moviendose = (actual_dx != 0 or actual_dy != 0)
            if move_x > 0:
                self.aventura_personaje.direccion = "right"
            elif move_x < 0:
                self.aventura_personaje.direccion = "left"
            elif move_y > 0:
                self.aventura_personaje.direccion = "down"
            elif move_y < 0:
                self.aventura_personaje.direccion = "up"
            if self.aventura_personaje.moviendose:
                self.aventura_personaje.contador_animacion += 1
                if self.aventura_personaje.contador_animacion >= self.aventura_personaje.fps_animacion:
                    self.aventura_personaje.contador_animacion = 0
                    total_frames = len(self.aventura_personaje.animaciones[self.aventura_personaje.direccion])
                    self.aventura_personaje.frame_actual = (self.aventura_personaje.frame_actual + 1) % total_frames
            else:
                self.aventura_personaje.frame_actual = 0
                self.aventura_personaje.contador_animacion = 0

    def _handle_adventure_events(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == self.controls["interactuar"] and not self.story_pending_end and not self.story_show_support:
            if self.story_is_seated:
                self._toggle_seat_state(None)
                return
            interactable = self._get_player_interactable()
            if interactable is not None:
                self._execute_interactable_action(interactable)
            else:
                self.story_interaction_text = "No hay nada interactuable aqui."
            return
        if event.key == self.controls["guardar"]:
            self.message = "Partida guardada." if self._save_game() else "No se pudo guardar la partida."
            return
        if self.story_pending_end:
            if event.key in (self.controls["continuar"], pygame.K_SPACE, pygame.K_KP_ENTER):
                self.current_screen = "menu"
            return
        if self.story_show_support:
            if event.key in (self.controls["continuar"], pygame.K_SPACE, pygame.K_KP_ENTER):
                self.story_show_support = False
            return
        if self.story_current_event is None:
            return
        if self.story_current_event.get("id") == "primer_dia":
            # Este evento se resuelve solo por sentarse en silla 42/43.
            return
        key_to_idx = {
            self.controls["opcion_1"]: 0,
            self.controls["opcion_2"]: 1,
            self.controls["opcion_3"]: 2,
            self.controls["opcion_4"]: 3,
            self.controls["opcion_5"]: 4,
            pygame.K_KP1: 0,
            pygame.K_KP2: 1,
            pygame.K_KP3: 2,
            pygame.K_KP4: 3,
            pygame.K_KP5: 4,
        }
        if event.key in key_to_idx:
            idx = key_to_idx[event.key]
            options = self.story_current_event["options"]
            if 0 <= idx < len(options):
                self._apply_story_choice(options[idx])

    def _handle_prologo_events(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            self.prologo_paso += 1
            if self.prologo_paso >= len(self.prologo_textos):
                self.prologo_activo = False
                self.current_screen = "aventura"

    def _draw_reputation_face(self, x, y):
        if self.story_reputacion > 50:
            face = ":)"
        elif self.story_reputacion < 50:
            face = ":("
        else:
            face = ":|"
        self.draw_pixel_text(face, x, y, "subtitle", TEXT_MAIN, True)

    def _draw_happiness_overlay(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        if self.story_felicidad > 50:
            strength = min(90, (self.story_felicidad - 50) * 2)
            overlay.fill((255, 180, 70, strength))
        elif self.story_felicidad < 50:
            strength = min(130, (50 - self.story_felicidad) * 3)
            overlay.fill((20, 22, 40, strength))
        else:
            overlay.fill((0, 0, 0, 0))
        self.screen.blit(overlay, (0, 0))

    def _draw_prologo_screen(self):
        self.screen.fill((30, 30, 30))
        self.draw_pixel_text("PROLOGO - FLASHBACK", self.width // 2, 34, "subtitle", (240, 240, 240), True)

        # Barra inferior estilo dialogo indie/novela visual.
        box_h = 190
        dialog_box = pygame.Rect(26, self.height - box_h - 22, self.width - 52, box_h)
        pygame.draw.rect(self.screen, (242, 242, 242), dialog_box)
        pygame.draw.rect(self.screen, (18, 18, 18), dialog_box, 4)

        entry = self.prologo_textos[self.prologo_paso] if self.prologo_textos else {"speaker": "", "text": ""}
        speaker = entry.get("speaker", "")
        text = entry.get("text", "")

        name_box = pygame.Rect(dialog_box.x + 16, dialog_box.y - 34, 220, 34)
        pygame.draw.rect(self.screen, (255, 255, 255), name_box)
        pygame.draw.rect(self.screen, (18, 18, 18), name_box, 3)
        self.draw_pixel_text(speaker, name_box.centerx, name_box.centery, "small", TEXT_MAIN, True)

        self.draw_pixel_text(text, dialog_box.x + 24, dialog_box.y + 74, "body", TEXT_MAIN, False)
        self.draw_pixel_text("ENTER/ESPACIO para continuar", dialog_box.right - 16, dialog_box.bottom - 20, "small", TEXT_SOFT, False)

    def _draw_adventure_screen(self):
        self.screen.fill((255, 255, 255))
        footer_h = 220
        self.story_map_rect = pygame.Rect(0, 0, self.story_world_width, self.story_world_height)
        self.player_rect.clamp_ip(self.story_map_rect)
        self._update_story_camera()

        if self.aventura_fondo is not None:
            source = self.aventura_fondo.ruta_imagen
            target_size = (self.story_world_width, self.story_world_height)
            needs_rebuild = (
                self.cached_background_scaled is None
                or self.cached_background_size != target_size
                or self.cached_background_source != source
            )
            if needs_rebuild:
                self.cached_background_scaled = pygame.transform.scale(self.aventura_fondo.imagen, target_size)
                self.cached_background_size = target_size
                self.cached_background_source = source
            camera_view = pygame.Rect(self.story_camera_x, self.story_camera_y, self.width, self.height)
            self.screen.blit(self.cached_background_scaled, (0, 0), area=camera_view)
        else:
            pygame.draw.rect(self.screen, (255, 255, 255), (0, 0, self.width, self.height))

        if self._is_first_day_classroom_context():
            has_npc_hitboxes = any(
                h.get("role") == "interactable" and h.get("action") == "npc"
                for h in self.story_walls
            )
            if not has_npc_hitboxes:
                self._draw_first_day_classroom_npcs()
            self._draw_story_clock_hud()

        self._draw_object_interactables_from_hitboxes()

        # Barras de estado (0-100), inicializan en 50 al comenzar partida nueva.
        bar_w = min(260, max(180, self.width // 5))
        bar_h = 20
        gap = 20
        total_w = bar_w * 2 + gap
        start_x = self.width - total_w - 24
        felicidad_y = 18
        reputacion_y = 18
        bar_x_f = start_x
        bar_x_r = start_x + bar_w + gap

        pygame.draw.rect(self.screen, (220, 220, 220), (bar_x_f, felicidad_y, bar_w, bar_h))
        pygame.draw.rect(self.screen, (30, 30, 30), (bar_x_f, felicidad_y, bar_w, bar_h), 2)
        fill_f = int((self.story_felicidad / 100) * bar_w)
        if fill_f > 0:
            pygame.draw.rect(self.screen, (245, 170, 70), (bar_x_f, felicidad_y, fill_f, bar_h))
        self.draw_pixel_text(f"F {self.story_felicidad}", bar_x_f + bar_w // 2, felicidad_y + 10, "small", TEXT_MAIN, True)

        pygame.draw.rect(self.screen, (220, 220, 220), (bar_x_r, reputacion_y, bar_w, bar_h))
        pygame.draw.rect(self.screen, (30, 30, 30), (bar_x_r, reputacion_y, bar_w, bar_h), 2)
        fill_r = int((self.story_reputacion / 100) * bar_w)
        if fill_r > 0:
            pygame.draw.rect(self.screen, (90, 190, 255), (bar_x_r, reputacion_y, fill_r, bar_h))
        self.draw_pixel_text(f"R {self.story_reputacion}", bar_x_r + bar_w // 2, reputacion_y + 10, "small", TEXT_MAIN, True)

        for wall in self.story_walls:
            if self.settings.get("Mostrar hitboxes", False):
                mx, my, mw, mh = 0, 0, self.story_world_width, self.story_world_height
                color = (90, 160, 255) if wall.get("role", "wall") == "wall" else (255, 210, 0)
                if wall["type"] == "rect":
                    r = pygame.Rect(
                        mx + int(mw * wall["rx"]) - self.story_camera_x,
                        my + int(mh * wall["ry"]) - self.story_camera_y,
                        max(8, int(mw * wall["rw"])),
                        max(8, int(mh * wall["rh"])),
                    )
                    pygame.draw.rect(self.screen, color, r, 2)
                elif wall["type"] == "circle":
                    cx = mx + int(mw * wall["cx"]) - self.story_camera_x
                    cy = my + int(mh * wall["cy"]) - self.story_camera_y
                    r = max(8, int(mw * wall["r"]))
                    pygame.draw.circle(self.screen, color, (cx, cy), r, 2)
                elif wall["type"] == "line":
                    x1 = mx + int(mw * wall["x1"]) - self.story_camera_x
                    y1 = my + int(mh * wall["y1"]) - self.story_camera_y
                    x2 = mx + int(mw * wall["x2"]) - self.story_camera_x
                    y2 = my + int(mh * wall["y2"]) - self.story_camera_y
                    thickness_norm = float(wall.get("thickness", 8 / max(1, self.story_world_width)))
                    thickness_px = max(1, int(thickness_norm * self.story_world_width))
                    pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), thickness_px)
        self._draw_npc_interactables_from_hitboxes()
        if self.aventura_personaje is not None:
            if self.story_is_seated and self.story_seated_sprite is not None:
                seat_center = self._interactable_center(self.story_seated_hitbox) if self.story_seated_hitbox else self.player_rect.center
                sprite_x = seat_center[0] - (self.story_seated_sprite.get_width() // 2) - self.story_camera_x
                sprite_y = seat_center[1] - (self.story_seated_sprite.get_height() // 2) - self.story_camera_y
                self.screen.blit(self.story_seated_sprite, (sprite_x, sprite_y))
            else:
                self.aventura_personaje.dibujar(self.screen, offset=(self.story_camera_x, self.story_camera_y))
            if (
                not self.story_is_seated
                and self._should_show_interactable_prompt()
                and self.story_interact_prompt_scaled is not None
            ):
                hitbox_view = self.aventura_personaje.hitbox.move(-self.story_camera_x, -self.story_camera_y)
                bubble_x = hitbox_view.right - 6
                bubble_y = hitbox_view.top - self.story_interact_prompt_scaled.get_height() - 18
                self.screen.blit(self.story_interact_prompt_scaled, (bubble_x, bubble_y))
            if self.settings.get("Mostrar hitboxes", False):
                hitbox_view = self.aventura_personaje.hitbox.move(-self.story_camera_x, -self.story_camera_y)
                pygame.draw.rect(self.screen, (255, 0, 0), hitbox_view, 2)
                interactable_view = self.aventura_personaje.interactable_hitbox.move(-self.story_camera_x, -self.story_camera_y)
                pygame.draw.rect(self.screen, (255, 220, 0), interactable_view, 2)
        else:
            player_view = self.player_rect.move(-self.story_camera_x, -self.story_camera_y)
            pygame.draw.rect(self.screen, PIXEL_CYAN, player_view)
            if self.settings.get("Mostrar hitboxes", False):
                pygame.draw.rect(self.screen, (255, 0, 0), player_view, 2)

        # Barra inferior estilo prologo.
        event_box = pygame.Rect(26, self.height - footer_h + 20, self.width - 52, footer_h - 28)
        overlay = pygame.Surface((event_box.width, event_box.height), pygame.SRCALPHA)
        overlay.fill((242, 242, 242, 180))
        self.screen.blit(overlay, event_box.topleft)
        pygame.draw.rect(self.screen, (18, 18, 18), event_box, 4)
        tag_box = pygame.Rect(event_box.x + 16, event_box.y - 34, 300, 34)
        tag_overlay = pygame.Surface((tag_box.width, tag_box.height), pygame.SRCALPHA)
        tag_overlay.fill((255, 255, 255, 220))
        self.screen.blit(tag_overlay, tag_box.topleft)
        pygame.draw.rect(self.screen, (18, 18, 18), tag_box, 3)
        self.draw_pixel_text("Decisiones", tag_box.centerx, tag_box.centery, "small", TEXT_MAIN, True)

        if self.story_pending_end:
            self.draw_pixel_text(self.story_final_key, self.width // 2, event_box.y + 48, "subtitle", TEXT_MAIN, True)
            self.draw_pixel_text(self.story_final_text, self.width // 2, event_box.y + 110, "body", TEXT_SOFT, True)
            self.draw_pixel_text("ENTER para volver al menu", self.width // 2, event_box.y + 186, "small", TEXT_SOFT, True)
        elif self.story_show_support:
            self.draw_pixel_text(
                "Si tu o alguien que conoces pasa por algo similar, busca ayuda profesional.",
                self.width // 2,
                event_box.y + 86,
                "body",
                TEXT_MAIN,
                True,
            )
            self.draw_pixel_text("ENTER para continuar", self.width // 2, event_box.y + 164, "small", TEXT_SOFT, True)
        elif self.story_current_event is not None:
            self.draw_pixel_text(
                f"Evento {self.story_completed + 1}/{self.story_goal}: {self.story_current_event['title']}",
                self.width // 2,
                event_box.y + 24,
                "small",
                TEXT_MAIN,
                True,
            )
            y = event_box.y + 56
            for opt in self.story_current_event["options"]:
                self.draw_pixel_text(opt["label"], event_box.x + 18, y, "small", TEXT_SOFT, False)
                y += 28
            self.draw_pixel_text(f"Pensamiento: {self.story_thought}", event_box.x + 18, event_box.bottom - 26, "small", TEXT_MAIN, False)
            if self.story_interaction_text:
                self.draw_pixel_text(self.story_interaction_text, event_box.right - 18, event_box.y + 24, "small", TEXT_MAIN, False)

        # self._draw_happiness_overlay()  # Desactivado: no cambiar el tono según felicidad.
        interactable_hint = (
            f" | {self._control_name('interactuar')} interactuar"
            if self._should_show_interactable_prompt()
            else ""
        )
        move_keys = (
            f"{self._control_name('mover_arriba')}/{self._control_name('mover_izquierda')}/"
            f"{self._control_name('mover_abajo')}/{self._control_name('mover_derecha')}"
        )
        self.draw_pixel_text(
            f"{move_keys} mover{interactable_hint} | {self._control_name('guardar')} guardar | ESC pausa",
            event_box.right - 14,
            event_box.bottom - 16,
            "small",
            TEXT_SOFT,
            False,
        )

    def _draw_first_day_classroom_npcs(self):
        def _slot_for(npc_name, fallback_rx, fallback_ry):
            data = self.story_npc_positions.get(npc_name, {})
            rx = float(data.get("rx", fallback_rx))
            ry = float(data.get("ry", fallback_ry))
            wx = int(rx * self.story_world_width)
            wy = int(ry * self.story_world_height)
            rw = max(24, int(float(data.get("rw", 96 / max(1, self.story_world_width))) * self.story_world_width))
            rh = max(24, int(float(data.get("rh", 96 / max(1, self.story_world_height))) * self.story_world_height))
            return wx - self.story_camera_x, wy - self.story_camera_y, rw, rh

        if self.story_npc_sara_frames:
            sara = self.story_npc_sara_frames[self.story_npc_sara_index % len(self.story_npc_sara_frames)]
            sx, sy, sw, sh = _slot_for("sara", 0.19, 0.23)
            sara_scaled = pygame.transform.smoothscale(sara, (sw, sh))
            self.screen.blit(sara_scaled, (sx - (sw // 2), sy - (sh // 2)))
        if self.story_npc_diego_frames:
            diego = self.story_npc_diego_frames[self.story_npc_diego_index % len(self.story_npc_diego_frames)]
            dx, dy, dw, dh = _slot_for("diego", 0.62, 0.23)
            diego_scaled = pygame.transform.smoothscale(diego, (dw, dh))
            self.screen.blit(diego_scaled, (dx - (dw // 2), dy - (dh // 2)))

    def _npc_slot_from_hitbox(self, h):
        mx, my, mw, mh = 0, 0, self.story_world_width, self.story_world_height
        if h["type"] == "rect":
            r = pygame.Rect(
                mx + int(mw * h["rx"]),
                my + int(mh * h["ry"]),
                max(8, int(mw * h["rw"])),
                max(8, int(mh * h["rh"])),
            )
            return r.centerx, r.centery, r.width, r.height
        if h["type"] == "circle":
            cx = mx + int(mw * h["cx"])
            cy = my + int(mh * h["cy"])
            radius = max(8, int(mw * h["r"]))
            d = radius * 2
            return cx, cy, d, d
        if h["type"] == "line":
            x1 = mx + int(mw * h["x1"])
            y1 = my + int(mh * h["y1"])
            x2 = mx + int(mw * h["x2"])
            y2 = my + int(mh * h["y2"])
            thickness_norm = float(h.get("thickness", 8 / max(1, self.story_world_width)))
            thickness_px = max(8, int(thickness_norm * self.story_world_width))
            return (x1 + x2) // 2, (y1 + y2) // 2, max(24, thickness_px * 3), max(24, thickness_px * 3)
        return self.player_rect.centerx, self.player_rect.centery, 96, 96

    def _draw_npc_interactables_from_hitboxes(self):
        for h in self.story_walls:
            if h.get("role") != "interactable" or h.get("action") != "npc":
                continue
            character = h.get("npc_character", "Sara")
            animation = h.get("npc_animation", "Sara_dibujando.png")
            frames = self._load_npc_animation_frames(character, animation)
            if not frames:
                continue
            frame_idx = (self.story_npc_anim_timer // 220) % len(frames)
            frame = frames[int(frame_idx)]
            cx, cy, sw, sh = self._npc_slot_from_hitbox(h)
            preview_w = max(24, sw)
            preview_h = max(24, sh)
            max_preview = 160
            if preview_w > max_preview or preview_h > max_preview:
                scale = min(max_preview / preview_w, max_preview / preview_h)
                preview_w = max(24, int(preview_w * scale))
                preview_h = max(24, int(preview_h * scale))
            scaled = pygame.transform.smoothscale(frame, (preview_w, preview_h))
            self.screen.blit(
                scaled,
                (
                    cx - (scaled.get_width() // 2) - self.story_camera_x,
                    cy - (scaled.get_height() // 2) - self.story_camera_y,
                ),
            )

    def _load_object_interactable_image(self, object_name):
        if not object_name:
            return None
        cached = self.story_object_image_cache.get(object_name)
        if cached is not None:
            return cached

        object_path = os.path.join(os.path.dirname(__file__), "Imagenes", "Interactuables", object_name)
        try:
            image = pygame.image.load(object_path).convert_alpha()
        except (OSError, pygame.error):
            image = None
        self.story_object_image_cache[object_name] = image
        return image

    def _get_cropped_object_image(self, image, crop):
        if not isinstance(crop, dict):
            return image
        iw, ih = image.get_size()
        try:
            cx = max(0.0, min(1.0, float(crop.get("x", 0.0))))
            cy = max(0.0, min(1.0, float(crop.get("y", 0.0))))
            cw = max(0.001, min(1.0 - cx, float(crop.get("w", 1.0))))
            ch = max(0.001, min(1.0 - cy, float(crop.get("h", 1.0))))
        except (TypeError, ValueError):
            return image

        rect = pygame.Rect(
            max(0, min(iw - 1, int(cx * iw))),
            max(0, min(ih - 1, int(cy * ih))),
            1,
            1,
        )
        rect.width = max(1, min(iw - rect.x, int(cw * iw)))
        rect.height = max(1, min(ih - rect.y, int(ch * ih)))
        if rect.topleft == (0, 0) and rect.size == image.get_size():
            return image
        return image.subsurface(rect)

    def _draw_object_interactables_from_hitboxes(self):
        for h in self.story_walls:
            if h.get("role") != "interactable" or h.get("action") != "objeto":
                continue
            if h.get("type") != "rect":
                continue
            object_name = h.get("object_name", "")
            image = self._load_object_interactable_image(object_name)
            if image is None:
                continue
            x = int(self.story_world_width * h["rx"]) - self.story_camera_x
            y = int(self.story_world_height * h["ry"]) - self.story_camera_y
            w = max(8, int(self.story_world_width * h["rw"]))
            h_px = max(8, int(self.story_world_height * h["rh"]))
            image = self._get_cropped_object_image(image, h.get("crop"))
            scaled = pygame.transform.smoothscale(image, (w, h_px))
            self.screen.blit(scaled, (x, y))

    def _draw_story_clock_hud(self):
        hud_text = f"Dia {self.story_clock_day}  {self.story_clock_hour:02d}:{self.story_clock_minute:02d}"
        box = pygame.Rect(20, 18, 230, 38)
        overlay = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 210))
        self.screen.blit(overlay, box.topleft)
        pygame.draw.rect(self.screen, (18, 18, 18), box, 2)
        self.draw_pixel_text(hud_text, box.x + 12, box.centery, "small", TEXT_MAIN, False)

    def _change_setting(self, direction):
        key = self.setting_keys[self.selected_setting_index]
        value = self.settings[key]

        if key == "Pantalla completa":
            self.settings[key] = not value
            self._apply_display_mode()
            return

        if key == "Volumen":
            self.settings[key] = max(0, min(100, value + (5 * direction)))
            return

        if key == "Limite FPS":
            fps_steps = [30, 60, 90, 120, 144, 165, 240]
            current_idx = fps_steps.index(value) if value in fps_steps else 1
            self.settings[key] = fps_steps[(current_idx + direction) % len(fps_steps)]
            return

        if isinstance(value, bool):
            self.settings[key] = not value
    def _settings_layout(self):
        panel = pygame.Rect(self.width // 2 - 600, self.height // 2 - 370, 1200, 740)
        row_h = 62
        row_x = panel.x + 70
        row_w = panel.width - 140
        start_y = panel.y + 138
        footer_y = panel.y + panel.height - 28
        return panel, row_h, row_x, row_w, start_y, footer_y

    def _controls_layout(self):
        panel = pygame.Rect(self.width // 2 - 600, self.height // 2 - 320, 1200, 640)
        row_h = 52
        row_x = panel.x + 70
        row_w = panel.width - 180
        start_y = panel.y + 138
        list_bottom = panel.bottom - 92
        return panel, row_h, row_x, row_w, start_y, list_bottom

    def _controls_reset_button_rect(self):
        panel, _, _, _, _, _ = self._controls_layout()
        return pygame.Rect(panel.x + 24, panel.bottom - 74, 360, 42)

    def _clamp_controls_scroll(self):
        _, row_h, _, _, start_y, list_bottom = self._controls_layout()
        visible_rows = max(1, (list_bottom - start_y) // row_h)
        max_scroll = max(0, len(self.control_labels) - visible_rows)
        self.controls_scroll = max(0, min(self.controls_scroll, max_scroll))

    def _ensure_selected_control_visible(self):
        _, row_h, _, _, start_y, list_bottom = self._controls_layout()
        visible_rows = max(1, (list_bottom - start_y) // row_h)
        if self.selected_control_index < self.controls_scroll:
            self.controls_scroll = self.selected_control_index
        elif self.selected_control_index >= self.controls_scroll + visible_rows:
            self.controls_scroll = self.selected_control_index - visible_rows + 1
        self._clamp_controls_scroll()

    def _draw_settings_screen(self):
        self._draw_pixel_background()
        panel, row_h, row_x, row_w, start_y, footer_y = self._settings_layout()
        shadow = panel.move(6, 6)
        pygame.draw.rect(self.screen, (13, 12, 24), shadow)
        pygame.draw.rect(self.screen, CARD, panel)
        pygame.draw.rect(self.screen, CARD_BORDER, panel, width=5)

        self.draw_pixel_text("CONFIGURACION", self.width // 2, panel.y + 52, "title", TEXT_MAIN, True)
        self.draw_pixel_text("Ajusta tu experiencia de juego", self.width // 2, panel.y + 96, "small", TEXT_SOFT, True)

        mouse_pos = pygame.mouse.get_pos()
        for i, key in enumerate(self.setting_keys):
            row = pygame.Rect(row_x, start_y + i * row_h, row_w, 50)
            is_selected = i == self.selected_setting_index
            is_hover = row.collidepoint(mouse_pos)
            bg = CARD_HOVER if (is_selected or is_hover) else (208, 216, 196)
            pygame.draw.rect(self.screen, bg, row)
            pygame.draw.rect(self.screen, CARD_BORDER, row, 3)

            self.draw_pixel_text(key, row.x + 24, row.centery, "body", TEXT_MAIN, False)
            value = self.settings[key]
            if key == "Volumen":
                bar_w = 260
                bar_h = 16
                bar_x = row.right - bar_w - 24
                bar_y = row.centery - bar_h // 2
                bar = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
                pygame.draw.rect(self.screen, (180, 188, 170), bar)
                pygame.draw.rect(self.screen, CARD_BORDER, bar, 3)
                fill_w = int((self.settings["Volumen"] / 100) * bar_w)
                if fill_w > 0:
                    pygame.draw.rect(self.screen, PIXEL_CYAN, (bar_x, bar_y, fill_w, bar_h))
                knob_x = bar_x + fill_w
                knob = pygame.Rect(knob_x - 8, bar_y - 8, 16, 32)
                pygame.draw.rect(self.screen, PIXEL_PINK, knob)
                pygame.draw.rect(self.screen, CARD_BORDER, knob, 3)
                self.draw_pixel_text(f"{self.settings['Volumen']}%", bar_x - 58, row.centery, "small", TEXT_MAIN, False)
            else:
                if isinstance(value, bool):
                    value_text = "ON" if value else "OFF"
                else:
                    value_text = str(value)
                self.draw_pixel_text(value_text, row.right - 70, row.centery, "body", TEXT_MAIN, False)

        controls_row = pygame.Rect(row_x, start_y + len(self.setting_keys) * row_h, row_w, 50)
        controls_hover = controls_row.collidepoint(mouse_pos)
        pygame.draw.rect(self.screen, CARD_HOVER if controls_hover else (208, 216, 196), controls_row)
        pygame.draw.rect(self.screen, CARD_BORDER, controls_row, 3)
        self.draw_pixel_text("Controles", controls_row.x + 24, controls_row.centery, "body", TEXT_MAIN, False)
        self.draw_pixel_text("Editar >", controls_row.right - 120, controls_row.centery, "small", TEXT_MAIN, False)

        if self.settings["Ayuda en pantalla"]:
            help_bg = pygame.Rect(panel.x + 40, footer_y - 20, panel.width - 80, 36)
            pygame.draw.rect(self.screen, (208, 216, 196), help_bg)
            pygame.draw.rect(self.screen, CARD_BORDER, help_bg, 2)
            self.draw_pixel_text(
                "Flechas seleccionar/cambiar | Click y arrastra volumen | Enter alternar | ESC volver",
                self.width // 2,
                footer_y,
                "small",
                TEXT_SOFT,
                True,
            )

    def _draw_controls_screen(self):
        self._draw_pixel_background()
        panel, row_h, row_x, row_w, start_y, list_bottom = self._controls_layout()
        self._clamp_controls_scroll()
        shadow = panel.move(6, 6)
        pygame.draw.rect(self.screen, (13, 12, 24), shadow)
        pygame.draw.rect(self.screen, CARD, panel)
        pygame.draw.rect(self.screen, CARD_BORDER, panel, width=5)
        self.draw_pixel_text("CONTROLES", self.width // 2, panel.y + 52, "title", TEXT_MAIN, True)
        self.draw_pixel_text(
            "Haz click en una accion y luego presiona la tecla nueva",
            self.width // 2,
            panel.y + 96,
            "small",
            TEXT_SOFT,
            True,
        )

        mouse_pos = pygame.mouse.get_pos()
        visible_rows = max(1, (list_bottom - start_y) // row_h)
        start_idx = self.controls_scroll
        end_idx = min(len(self.control_labels), start_idx + visible_rows)
        for i in range(start_idx, end_idx):
            label, action = self.control_labels[i]
            visual_i = i - start_idx
            row = pygame.Rect(row_x, start_y + visual_i * row_h, row_w, row_h - 8)
            active = i == self.selected_control_index
            hover = row.collidepoint(mouse_pos)
            waiting = self.waiting_control_action == action
            bg = CARD_HOVER if (active or hover or waiting) else (208, 216, 196)
            pygame.draw.rect(self.screen, bg, row)
            pygame.draw.rect(self.screen, CARD_BORDER, row, 3)
            text_y = row.y + max(10, (row.height - 22) // 2)
            self.draw_pixel_text(label, row.x + 18, text_y, "small", TEXT_MAIN, False)
            bind_text = "Presiona una tecla..." if waiting else self._control_name(action)
            self.draw_pixel_text(bind_text, row.right - 220, text_y, "small", TEXT_MAIN, False)

        if len(self.control_labels) > visible_rows:
            track = pygame.Rect(row_x + row_w + 18, start_y, 22, list_bottom - start_y)
            pygame.draw.rect(self.screen, (190, 198, 178), track)
            pygame.draw.rect(self.screen, CARD_BORDER, track, 3)
            thumb_h = max(36, int((visible_rows / len(self.control_labels)) * track.height))
            max_scroll = max(1, len(self.control_labels) - visible_rows)
            travel = max(0, track.height - thumb_h)
            thumb_y = track.y + int((self.controls_scroll / max_scroll) * travel)
            thumb = pygame.Rect(track.x + 3, thumb_y + 3, track.width - 6, thumb_h - 6)
            pygame.draw.rect(self.screen, PIXEL_CYAN, thumb)
            pygame.draw.rect(self.screen, CARD_BORDER, thumb, 2)

        reset_btn = self._controls_reset_button_rect()
        reset_hover = reset_btn.collidepoint(mouse_pos)
        pygame.draw.rect(self.screen, CARD_HOVER if reset_hover else (208, 216, 196), reset_btn)
        pygame.draw.rect(self.screen, CARD_BORDER, reset_btn, 3)
        self.draw_pixel_text("Restablecer predeterminados", reset_btn.centerx, reset_btn.centery, "small", TEXT_MAIN, True)

        self.draw_pixel_text(
            "Rueda: desplazar | Click: seleccionar | Enter: cambiar tecla | ESC: volver",
            panel.x + 24,
            panel.bottom - 34,
            "small",
            TEXT_SOFT,
            False,
        )

    def _handle_settings_events(self, event):
        panel, row_h, row_x, row_w, start_y, _ = self._settings_layout()

        def volume_bar_rect():
            idx = self.setting_keys.index("Volumen")
            row = pygame.Rect(row_x, start_y + idx * row_h, row_w, 50)
            bar_w = 260
            bar_h = 16
            bar_x = row.right - bar_w - 24
            bar_y = row.centery - bar_h // 2
            return pygame.Rect(bar_x, bar_y, bar_w, bar_h)

        def set_volume_from_x(mouse_x):
            bar = volume_bar_rect()
            rel_x = max(0, min(bar.width, mouse_x - bar.x))
            self.settings["Volumen"] = int((rel_x / bar.width) * 100)

        if event.type == pygame.MOUSEMOTION:
            for i in range(len(self.setting_keys)):
                row = pygame.Rect(row_x, start_y + i * row_h, row_w, 50)
                if row.collidepoint(event.pos):
                    self.selected_setting_index = i
                    break
            if self.dragging_volume:
                set_volume_from_x(event.pos[0])

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if volume_bar_rect().collidepoint(event.pos):
                self.selected_setting_index = self.setting_keys.index("Volumen")
                self.dragging_volume = True
                set_volume_from_x(event.pos[0])
                return
            controls_row = pygame.Rect(row_x, start_y + len(self.setting_keys) * row_h, row_w, 50)
            if controls_row.collidepoint(event.pos):
                self.current_screen = "controles"
                self.selected_control_index = 0
                self.waiting_control_action = None
                return
            for i in range(len(self.setting_keys)):
                row = pygame.Rect(row_x, start_y + i * row_h, row_w, 50)
                if row.collidepoint(event.pos):
                    self.selected_setting_index = i
                    self._change_setting(1)
                    return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_volume = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_setting_index = (self.selected_setting_index + 1) % len(self.setting_keys)
            elif event.key == pygame.K_UP:
                self.selected_setting_index = (self.selected_setting_index - 1) % len(self.setting_keys)
            elif event.key == pygame.K_LEFT:
                self._change_setting(-1)
            elif event.key == pygame.K_RIGHT:
                self._change_setting(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._change_setting(1)

    def _handle_controls_events(self, event):
        panel, row_h, row_x, row_w, start_y, list_bottom = self._controls_layout()
        self._clamp_controls_scroll()

        if self.waiting_control_action is not None and event.type == pygame.KEYDOWN:
            self._rebind_control(self.waiting_control_action, event.key)
            return

        if event.type == pygame.MOUSEWHEEL:
            self.controls_scroll -= event.y
            self._clamp_controls_scroll()
            return

        if event.type == pygame.MOUSEMOTION:
            visible_rows = max(1, (list_bottom - start_y) // row_h)
            start_idx = self.controls_scroll
            end_idx = min(len(self.control_labels), start_idx + visible_rows)
            for i in range(start_idx, end_idx):
                visual_i = i - start_idx
                row = pygame.Rect(row_x, start_y + visual_i * row_h, row_w, row_h - 8)
                if row.collidepoint(event.pos):
                    self.selected_control_index = i
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._controls_reset_button_rect().collidepoint(event.pos):
                self.controls = self._build_default_controls()
                self.waiting_control_action = None
                return
            visible_rows = max(1, (list_bottom - start_y) // row_h)
            start_idx = self.controls_scroll
            end_idx = min(len(self.control_labels), start_idx + visible_rows)
            for i in range(start_idx, end_idx):
                _, action = self.control_labels[i]
                visual_i = i - start_idx
                row = pygame.Rect(row_x, start_y + visual_i * row_h, row_w, row_h - 8)
                if row.collidepoint(event.pos):
                    self.selected_control_index = i
                    self.waiting_control_action = action
                    return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_control_index = (self.selected_control_index + 1) % len(self.control_labels)
                self._ensure_selected_control_visible()
            elif event.key == pygame.K_UP:
                self.selected_control_index = (self.selected_control_index - 1) % len(self.control_labels)
                self._ensure_selected_control_visible()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                _, action = self.control_labels[self.selected_control_index]
                self.waiting_control_action = action

    def _draw_character_preview(self, x, y, scale=6):
        c = self.character_colors
        px = scale
        # Cabeza
        pygame.draw.rect(self.screen, c["Piel"], (x + 7 * px, y + 2 * px, 10 * px, 9 * px))
        # Cabello
        hair_style = self.part_styles["Cabello"][self.current_style["Cabello"]]
        if hair_style == "Corto":
            pygame.draw.rect(self.screen, c["Cabello"], (x + 6 * px, y + 1 * px, 12 * px, 4 * px))
        elif hair_style == "Largo":
            pygame.draw.rect(self.screen, c["Cabello"], (x + 6 * px, y + 1 * px, 12 * px, 4 * px))
            pygame.draw.rect(self.screen, c["Cabello"], (x + 6 * px, y + 4 * px, 2 * px, 7 * px))
            pygame.draw.rect(self.screen, c["Cabello"], (x + 16 * px, y + 4 * px, 2 * px, 7 * px))
        elif hair_style == "Rizado":
            pygame.draw.rect(self.screen, c["Cabello"], (x + 6 * px, y + 1 * px, 12 * px, 4 * px))
            pygame.draw.rect(self.screen, c["Cabello"], (x + 5 * px, y + 2 * px, 1 * px, 2 * px))
            pygame.draw.rect(self.screen, c["Cabello"], (x + 18 * px, y + 2 * px, 1 * px, 2 * px))
        elif hair_style == "Afro":
            pygame.draw.rect(self.screen, c["Cabello"], (x + 5 * px, y + 0 * px, 14 * px, 6 * px))
        elif hair_style == "Coleta":
            pygame.draw.rect(self.screen, c["Cabello"], (x + 6 * px, y + 1 * px, 12 * px, 4 * px))
            pygame.draw.rect(self.screen, c["Cabello"], (x + 17 * px, y + 4 * px, 2 * px, 3 * px))
        # Ojos
        eye_style = self.part_styles["Ojos"][self.current_style["Ojos"]]
        eye_w = 2 * px if eye_style == "Grandes" else px
        pygame.draw.rect(self.screen, c["Ojos"], (x + 9 * px, y + 6 * px, eye_w, px))
        pygame.draw.rect(self.screen, c["Ojos"], (x + 14 * px, y + 6 * px, eye_w, px))
        # Sueter
        sweater_style = self.part_styles["Sueter"][self.current_style["Sueter"]]
        if sweater_style == "Hoodie":
            pygame.draw.rect(self.screen, c["Sueter"], (x + 5 * px, y + 11 * px, 14 * px, 8 * px))
            pygame.draw.rect(self.screen, c["Sueter"], (x + 9 * px, y + 10 * px, 6 * px, 2 * px))
        elif sweater_style == "Chaqueta":
            pygame.draw.rect(self.screen, c["Sueter"], (x + 5 * px, y + 11 * px, 14 * px, 8 * px))
            pygame.draw.rect(self.screen, (40, 40, 55), (x + 11 * px, y + 11 * px, 2 * px, 8 * px))
        # Camisa
        shirt_style = self.part_styles["Camisa"][self.current_style["Camisa"]]
        if shirt_style == "Camiseta":
            pygame.draw.rect(self.screen, c["Camisa"], (x + 8 * px, y + 12 * px, 8 * px, 7 * px))
        elif shirt_style == "Flanelilla":
            pygame.draw.rect(self.screen, c["Camisa"], (x + 9 * px, y + 12 * px, 6 * px, 7 * px))
        elif shirt_style == "Polo":
            pygame.draw.rect(self.screen, c["Camisa"], (x + 8 * px, y + 12 * px, 8 * px, 7 * px))
            pygame.draw.rect(self.screen, (230, 230, 230), (x + 11 * px, y + 12 * px, 2 * px, 2 * px))
        # Pantalones
        pants_style = self.part_styles["Pantalones"][self.current_style["Pantalones"]]
        if pants_style == "Jeans":
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 7 * px, y + 19 * px, 4 * px, 7 * px))
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 13 * px, y + 19 * px, 4 * px, 7 * px))
        elif pants_style == "Jogger":
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 7 * px, y + 19 * px, 5 * px, 6 * px))
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 12 * px, y + 19 * px, 5 * px, 6 * px))
        elif pants_style == "Short":
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 7 * px, y + 19 * px, 10 * px, 3 * px))
        # Zapatos
        shoe_style = self.part_styles["Zapatos"][self.current_style["Zapatos"]]
        if shoe_style == "Tenis":
            pygame.draw.rect(self.screen, c["Zapatos"], (x + 6 * px, y + 26 * px, 6 * px, 2 * px))
            pygame.draw.rect(self.screen, c["Zapatos"], (x + 12 * px, y + 26 * px, 6 * px, 2 * px))
        elif shoe_style == "Botas":
            pygame.draw.rect(self.screen, c["Zapatos"], (x + 6 * px, y + 24 * px, 6 * px, 4 * px))
            pygame.draw.rect(self.screen, c["Zapatos"], (x + 12 * px, y + 24 * px, 6 * px, 4 * px))
        elif shoe_style == "Casuales":
            pygame.draw.rect(self.screen, c["Zapatos"], (x + 6 * px, y + 25 * px, 5 * px, 3 * px))
            pygame.draw.rect(self.screen, c["Zapatos"], (x + 13 * px, y + 25 * px, 5 * px, 3 * px))
        # Contorno
        pygame.draw.rect(self.screen, (20, 20, 30), (x + 4 * px, y + 0 * px, 16 * px, 28 * px), 2)

    def _draw_character_creator(self):
        self._draw_pixel_background()
        panel = pygame.Rect(self.width // 2 - 520, self.height // 2 - 280, 1040, 560)
        shadow = panel.move(6, 6)
        pygame.draw.rect(self.screen, (13, 12, 24), shadow)
        pygame.draw.rect(self.screen, CARD, panel)
        pygame.draw.rect(self.screen, CARD_BORDER, panel, width=5)

        self.draw_pixel_text("PARTIDA NUEVA - CREADOR", self.width // 2, panel.y + 50, "title", TEXT_MAIN, True)
        self.draw_pixel_text("Selecciona rasgo y color", panel.x + 180, panel.y + 90, "small", TEXT_SOFT, True)

        left_x = panel.x + 40
        list_top = panel.y + 110
        list_row_h = 44
        for i, part in enumerate(self.custom_parts):
            row = pygame.Rect(left_x, list_top + i * list_row_h, 280, list_row_h - 4)
            active = i == self.selected_custom_index
            pygame.draw.rect(self.screen, CARD_HOVER if active else (208, 216, 196), row)
            pygame.draw.rect(self.screen, CARD_BORDER, row, 3)
            style_name = self.part_styles[part][self.current_style[part]]
            self.draw_pixel_text(f"{part}: {style_name}", row.centerx, row.centery, "small", TEXT_MAIN, True)

        part_now = self._selected_part()
        self.draw_pixel_text("A/D cambia diseno", left_x + 140, panel.y + 360, "small", TEXT_SOFT, True)
        self.draw_pixel_text(
            f"Actual: {self.part_styles[part_now][self.current_style[part_now]]}",
            left_x + 140,
            panel.y + 396,
            "small",
            TEXT_SOFT,
            True,
        )

        self.draw_pixel_text("Paleta", left_x + 140, panel.y + 430, "small", TEXT_SOFT, True)
        palette_top = panel.y + 420
        palette_cols = 6
        sw = 44
        gap = 12
        selected_color = self.character_colors[self._selected_part()]
        for idx, color in enumerate(self.palette_colors):
            r = idx // palette_cols
            c = idx % palette_cols
            x = left_x + c * (sw + gap)
            y = palette_top + r * (sw + gap)
            rect = pygame.Rect(x, y, sw, sw)
            pygame.draw.rect(self.screen, color, rect)
            border = PIXEL_CYAN if color == selected_color else CARD_BORDER
            pygame.draw.rect(self.screen, border, rect, 3)

        sliders_x = panel.x + 420
        sliders_top = panel.y + 160
        slider_w = 420
        names = ["R", "G", "B"]
        current = self.character_colors[self._selected_part()]
        for i, ch in enumerate(names):
            y = sliders_top + i * 82
            self.draw_pixel_text(f"{ch}: {current[i]}", sliders_x + 40, y - 20, "small", TEXT_SOFT, False)
            bar_rect = pygame.Rect(sliders_x, y, slider_w, 16)
            pygame.draw.rect(self.screen, (180, 188, 170), bar_rect)
            pygame.draw.rect(self.screen, CARD_BORDER, bar_rect, 3)
            knob_x = sliders_x + int((current[i] / 255) * slider_w)
            knob = pygame.Rect(knob_x - 8, y - 8, 16, 32)
            pygame.draw.rect(self.screen, CARD_HOVER if i == self.selected_slider else PIXEL_PINK, knob)
            pygame.draw.rect(self.screen, CARD_BORDER, knob, 3)

        preview_box = pygame.Rect(panel.x + 700, panel.y + 150, 280, 310)
        pygame.draw.rect(self.screen, (208, 216, 196), preview_box)
        pygame.draw.rect(self.screen, CARD_BORDER, preview_box, 4)
        self.draw_pixel_text("Vista previa", preview_box.centerx, preview_box.y + 26, "small", TEXT_SOFT, True)
        self._draw_character_preview(preview_box.x + 72, preview_box.y + 60, scale=7)

        self.draw_pixel_text(
            "Flechas: rasgo/color | A/D: diseno | TAB: RGB | ENTER: guardar | ESC: volver",
            self.width // 2,
            panel.y + panel.height - 28,
            "small",
            TEXT_SOFT,
            True,
        )

    def _render_current_screen(self):
        if self.current_screen == "menu":
            self._draw_menu()
        elif self.current_screen == "jugar":
            self._draw_pixel_background()
            panel = pygame.Rect(self.width // 2 - 380, self.height // 2 - 220, 760, 440)
            shadow = panel.move(6, 6)
            pygame.draw.rect(self.screen, (13, 12, 24), shadow)
            pygame.draw.rect(self.screen, CARD, panel)
            pygame.draw.rect(self.screen, CARD_BORDER, panel, width=5)

            self.draw_pixel_text("JUGAR", self.width // 2, panel.y + 55, "title", TEXT_MAIN, True)
            self.draw_pixel_text(
                "Elige una opcion para continuar", self.width // 2, panel.y + 110, "small", TEXT_SOFT, True
            )
            mouse_pos = pygame.mouse.get_pos()
            for i, button in enumerate(self.play_buttons):
                hover = button.contains(mouse_pos) or i == self.selected_play_index
                button.draw(self.screen, self, hover=hover)
        elif self.current_screen == "historia":
            self._draw_panel_screen(
                "HISTORIA",
                [
                    "Eres estudiante y apoyas casos de acoso.",
                    "Esta vista puede mostrar capitulos y dialogos.",
                ],
            )
        elif self.current_screen == "configuracion":
            self._draw_settings_screen()
        elif self.current_screen == "controles":
            self._draw_controls_screen()
        elif self.current_screen == "progreso":
            self._draw_panel_screen(
                "PROGRESO",
                [
                    "Muestra estadisticas, empatia y avances.",
                    "Tambien logros o historial de decisiones.",
                ],
            )
        elif self.current_screen == "tutorial":
            self._draw_panel_screen(
                "TUTORIAL",
                [
                    "Explica mecanicas basicas del juego.",
                    "Incluye ejemplos de buenas decisiones.",
                ],
            )
        elif self.current_screen == "creador":
            self._draw_character_creator()
        elif self.current_screen == "prologo":
            self._draw_prologo_screen()
        elif self.current_screen == "aventura":
            self._draw_adventure_screen()
        elif self.current_screen == "pause":
            self._draw_pause_screen()
        elif self.current_screen == "pause_guardar":
            self._draw_pause_save_screen()
        elif self.current_screen == "load_slots":
            self._draw_load_screen()
        elif self.current_screen == "simulacion":
            self._draw_simulacion_screen()
        if self.settings["Mostrar FPS"]:
            self.draw_pixel_text(f"FPS {int(self.clock.get_fps())}", 20, 16, "small", (210, 230, 255), False)

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.current_screen == "menu":
                        self.running = False
                    elif self.current_screen == "aventura":
                        self.previous_screen = "aventura"
                        self.current_screen = "pause"
                    elif self.current_screen == "pause":
                        self.current_screen = "aventura"
                        self.pause_overwrite_pending = False
                        self.pause_pending_slot = None
                    elif self.current_screen == "pause_guardar":
                        if self.pause_overwrite_pending:
                            self.pause_overwrite_pending = False
                            self.pause_pending_slot = None
                        else:
                            self.current_screen = "pause"
                    elif self.current_screen == "configuracion":
                        self.current_screen = self.previous_screen or "menu"
                        self.previous_screen = None
                    elif self.current_screen == "controles":
                        if self.waiting_control_action is not None:
                            self.waiting_control_action = None
                        else:
                            self.current_screen = "configuracion"
                    else:
                        self.current_screen = "menu"
                elif self.current_screen == "menu":
                    self._handle_menu_events(event)
                elif self.current_screen == "jugar":
                    self._handle_play_events(event)
                elif self.current_screen == "creador":
                    self._handle_creator_events(event)
                elif self.current_screen == "prologo":
                    self._handle_prologo_events(event)
                elif self.current_screen == "configuracion":
                    self._handle_settings_events(event)
                elif self.current_screen == "controles":
                    self._handle_controls_events(event)
                elif self.current_screen == "pause":
                    self._handle_pause_events(event)
                elif self.current_screen == "pause_guardar":
                    self._handle_pause_save_events(event)
                elif self.current_screen == "load_slots":
                    self._handle_load_events(event)
                elif self.current_screen == "simulacion":
                    self._handle_simulacion_events(event)
                elif self.current_screen == "aventura":
                    self._handle_adventure_events(event)

            self._update_adventure()
            self._update_simulacion()
            self._render_current_screen()
            pygame.display.flip()
            self.clock.tick(self.settings["Limite FPS"])

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    app = EmpatiaQuestUI()
    app.run()



















