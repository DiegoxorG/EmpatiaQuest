"""
Mixin de estado del juego para EmpatiaQuestUI.
Contiene toda la l?gica de datos: guardado, carga, exploraci?n, historia,
habilidades, logros y eventos.
"""

import os
import json
import random
import unicodedata

import pygame
from Movimiento.Personaje import Personaje
from npc_ai import NPCAIManager
from Movimiento.Fondo import Fondo
from Movimiento.Animacion import Animacion
from config import (
    DEFAULT_CONTROLS, SAVE_VERSION, SPAWN_OFFSET_X, SPAWN_OFFSET_Y,
    STORY_GOAL, DEFAULT_CHARACTER_COLORS, DEFAULT_SETTINGS,
    CUSTOM_PARTS, PART_STYLES, PROLOGO_RAZON_CHOICES,
)
from achievements import Lista_Logros, LOGRO_TRIGGERS
from scene_manager import (
    get_scene_dia1_salon,
    get_scene_pupitre_rayado_intro,
    get_scene_pupitre_borrar_gracias,
    get_scene_pupitre_foto,
    get_scene_pupitre_profesor,
    get_scene_patio_penaltis,
    get_scene_callejon_emociones,
    get_scene_bedroom_intro,
    get_scene_cama_dormir,
    get_scene_dia2_chat,
    get_scene_dia2_lucas_bano,
    get_scene_dia3_piscina,
    get_scene_dia3_cafeteria,
    get_scene_dia3_cafeteria_profesor,
    get_scene_dia3_pelea,
    get_scene_dia3_pelea_profesor,
    get_scene_dia3_buscar_profesor,
    get_scene_dia3_fin,
)


# â”€â”€â”€ Habilidades disponibles y sus triggers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DEFAULT_SKILLS = {
    "Escucha Activa": {
        "nivel": 0, "max_nivel": 3,
        "descripcion": "Prestar atencion sin interrumpir.",
    },
    "Intervencion Pacifica": {
        "nivel": 0, "max_nivel": 3,
        "descripcion": "Actuar para detener el dano sin escalar la violencia.",
    },
    "Empatia Digital": {
        "nivel": 0, "max_nivel": 3,
        "descripcion": "Manejar situaciones de ciberbullying de forma correcta.",
    },
    "Valentia Social": {
        "nivel": 0, "max_nivel": 3,
        "descripcion": "Decir no cuando es lo correcto, aunque cueste.",
    },
    "Mediacion de Conflictos": {
        "nivel": 0, "max_nivel": 3,
        "descripcion": "Ayudar a resolver conflictos de forma dialogada.",
    },
}



class GameStateMixin:
    """
    Mixin que contiene toda la l?gica de estado, guardado/carga,
    aventura, historia y habilidades de EmpatiaQuestUI.
    """

    # â”€â”€ Controles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_default_controls(self):
        controls = {}
        for action, key_name in DEFAULT_CONTROLS.items():
            try:
                controls[action] = pygame.key.key_code(key_name)
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
                self.controls[action] = pygame.key.key_code(key_name)
            except ValueError:
                continue

    def _control_name(self, action):
        key = self.controls.get(action)
        if key is None:
            return "-"
        name = pygame.key.name(key).upper()
        return "ENTER" if name == "RETURN" else name

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

    # â”€â”€ Guardado y carga â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _save_slot_exists(self, slot):
        return os.path.exists(self.save_slot_files[slot])

    def _build_save_data(self):
        return {
            "save_version": SAVE_VERSION,
            "player_name": getattr(self, "player_name", ""),
            "current_day": getattr(self, "current_day", 1),
            "story_felicidad": self.story_felicidad,
            "story_reputacion": self.story_reputacion,
            "story_completed": self.story_completed,
            "story_thought": self.story_thought,
            "story_pending_end": self.story_pending_end,
            "story_final_key": self.story_final_key,
            "story_final_text": self.story_final_text,
            "prologo_razon": self.prologo_razon,
            "decision_history": self.decision_history,
            "character_colors": self.character_colors,
            "current_style": self.current_style,
            "settings": self.settings,
            "controls": self._serialize_controls(),
            "skills_inventory": self.skills_inventory,
            "logros": self.lista_logros.to_list(),
            "escena_dia1_completada":   getattr(self, "escena_dia1_completada",   False),
            "pupitre_rayado_completado": getattr(self, "pupitre_rayado_completado", False),
            "escena_dia2_chat_completada": getattr(self, "escena_dia2_chat_completada", False),
            "escena_dia2_lucas_completada": getattr(self, "escena_dia2_lucas_completada", False),
            "decision_dia2_chat": getattr(self, "decision_dia2_chat", ""),
            "decision_dia2_lucas": getattr(self, "decision_dia2_lucas", ""),
            "day2_pasillo_prompt_done": getattr(self, "day2_pasillo_prompt_done", False),
            "escena_dia3_piscina_completada": getattr(self, "escena_dia3_piscina_completada", False),
            "escena_dia3_cafeteria_completada": getattr(self, "escena_dia3_cafeteria_completada", False),
            "escena_dia3_pelea_completada": getattr(self, "escena_dia3_pelea_completada", False),
            "decision_dia3_piscina": getattr(self, "decision_dia3_piscina", ""),
            "decision_dia3_cafeteria": getattr(self, "decision_dia3_cafeteria", ""),
            "decision_dia3_pelea": getattr(self, "decision_dia3_pelea", ""),
            "profesor1_fondo_actual": getattr(self, "profesor1_fondo_actual", ""),
            "profesor1_pos": list(getattr(self, "profesor1_pos", (0.5, 0.5))),
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

        if version < 3:
            migrated.setdefault("prologo_razon", "")
            migrated.setdefault("decision_history", [])
            migrated.setdefault("skills_inventory", {k: dict(v) for k, v in DEFAULT_SKILLS.items()})
            migrated.setdefault("logros", [])

        migrated["save_version"] = SAVE_VERSION
        return migrated

    def _apply_loaded_save_data(self, data):
        data = self._migrate_save_data(data)
        # Item-4: flag temporal para que _start_adventure() no active la intro del dormitorio
        self._loading_save = True
        self._start_adventure()
        self._loading_save = False
        self.day1_intro_step        = 2   # No mostrar intro al cargar partida
        self.escena_dia1_completada    = bool(data.get("escena_dia1_completada",   False))
        self.pupitre_rayado_completado = bool(data.get("pupitre_rayado_completado", False))
        self.escena_dia2_chat_completada = bool(data.get("escena_dia2_chat_completada", False))
        self.escena_dia2_lucas_completada = bool(data.get("escena_dia2_lucas_completada", False))
        self.decision_dia2_chat = str(data.get("decision_dia2_chat", ""))
        self.decision_dia2_lucas = str(data.get("decision_dia2_lucas", ""))
        self.day2_pasillo_prompt_done = bool(data.get("day2_pasillo_prompt_done", False))
        self.escena_dia3_piscina_completada = bool(data.get("escena_dia3_piscina_completada", False))
        self.escena_dia3_cafeteria_completada = bool(data.get("escena_dia3_cafeteria_completada", False))
        self.escena_dia3_pelea_completada = bool(data.get("escena_dia3_pelea_completada", False))
        self.decision_dia3_piscina = str(data.get("decision_dia3_piscina", ""))
        self.decision_dia3_cafeteria = str(data.get("decision_dia3_cafeteria", ""))
        self.decision_dia3_pelea = str(data.get("decision_dia3_pelea", ""))
        self.profesor1_fondo_actual = str(data.get("profesor1_fondo_actual", ""))
        pos = data.get("profesor1_pos", (0.5, 0.5))
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            self.profesor1_pos = (float(pos[0]), float(pos[1]))
        self.player_name = str(data.get("player_name", ""))
        self.current_day = int(data.get("current_day", 1))
        self.story_felicidad = int(data.get("story_felicidad", 50))
        self.story_reputacion = int(data.get("story_reputacion", 50))
        self.story_completed = int(data.get("story_completed", 0))
        self.story_thought = data.get("story_thought", "")
        self.story_pending_end = bool(data.get("story_pending_end", False))
        self.story_final_key = data.get("story_final_key", "")
        self.story_final_text = data.get("story_final_text", "")
        self.prologo_razon = data.get("prologo_razon", "")
        self.decision_history = data.get("decision_history", [])

        loaded_colors = data.get("character_colors", {})
        if isinstance(loaded_colors, dict):
            for part, color in loaded_colors.items():
                if part in self.character_colors and isinstance(color, (list, tuple)) and len(color) == 3:
                    self.character_colors[part] = tuple(max(0, min(255, int(v))) for v in color)

        loaded_style = data.get("current_style", {})
        if isinstance(loaded_style, dict):
            for part, idx in loaded_style.items():
                if part in self.current_style:
                    self.current_style[part] = max(0, min(len(self.part_styles[part]) - 1, int(idx)))

        loaded_settings = data.get("settings", {})
        if isinstance(loaded_settings, dict):
            prev_fullscreen = bool(self.settings.get("Pantalla completa", False))
            for key in self.settings:
                if key in loaded_settings:
                    self.settings[key] = loaded_settings[key]
            if bool(self.settings.get("Pantalla completa", False)) != prev_fullscreen:
                self._apply_display_mode()

        self._apply_loaded_controls(data.get("controls", {}))

        loaded_skills = data.get("skills_inventory", {})
        if isinstance(loaded_skills, dict):
            for skill_name, skill_data in loaded_skills.items():
                if skill_name in self.skills_inventory:
                    self.skills_inventory[skill_name]["nivel"] = int(
                        skill_data.get("nivel", 0)
                    )

        self.lista_logros.load_from_list(data.get("logros", []))

        if self.settings.get("Volumen") is not None:
            self.audio.apply_volume(self.settings["Volumen"])
        if getattr(self, "current_day", 1) == 3:
            self._prepare_day3_state()

    def _save_to_slot(self, slot):
        data = self._build_save_data()
        try:
            with open(self.save_slot_files[slot], "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=True, indent=2)
            return True
        except OSError:
            return False

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

    def _confirm_save_slot(self):
        if self.pause_pending_slot is None:
            return
        saved = self._save_to_slot(self.pause_pending_slot)
        if saved:
            self.message = f"Slot {self.pause_pending_slot + 1} sobrescrito."
            self.audio.sfx_guardar()
        else:
            self.message = "No se pudo guardar la partida."
        self.pause_overwrite_pending = False
        self.pause_pending_slot = None

    # â”€â”€ Settings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _change_setting(self, direction):
        key = self.setting_keys[self.selected_setting_index]
        value = self.settings[key]

        if key == "Pantalla completa":
            self.settings[key] = not value
            self._apply_display_mode()
            return

        if key == "Volumen":
            self.settings[key] = max(0, min(100, value + (5 * direction)))
            self.audio.apply_volume(self.settings[key])
            return

        if key == "Limite FPS":
            fps_steps = [30, 60, 90, 120, 144, 165, 240]
            current_idx = fps_steps.index(value) if value in fps_steps else 1
            self.settings[key] = fps_steps[(current_idx + direction) % len(fps_steps)]
            return

        if isinstance(value, bool):
            self.settings[key] = not value

    # â”€â”€ Layout helpers (compartidos con renderer y handlers) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # â”€â”€ Personaje â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # â”€â”€ Mundo y aventura â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _rebuild_story_world(self, keep_player=True):
        old_w = max(1, getattr(self, "story_world_width", self.width))
        old_h = max(1, getattr(self, "story_world_height", self.height))
        self.story_world_width = max(self.width, int(self.width * self.story_zoom))
        self.story_world_height = max(self.height, int(self.height * self.story_zoom))
        self.story_map_rect = pygame.Rect(0, 0, self.story_world_width, self.story_world_height)
        if keep_player and hasattr(self, "player_rect"):
            ratio_x = self.player_rect.centerx / old_w
            ratio_y = self.player_rect.centery / old_h
            self.player_rect.centerx = int(ratio_x * self.story_world_width)
            self.player_rect.centery = int(ratio_y * self.story_world_height)
            self.player_rect.clamp_ip(self.story_map_rect)
        elif hasattr(self, "player_rect"):
            self.player_rect.center = (self.story_world_width // 2, self.story_world_height // 2)
            self.player_rect.clamp_ip(self.story_map_rect)

    def _update_story_camera(self):
        max_x = max(0, self.story_world_width  - self.width)
        max_y = max(0, self.story_world_height - self.height)
        if getattr(self, "camera_mode", "follow_player") == "cinematic":
            target = getattr(self, "camera_target", None)
            if target is not None:
                lerp = getattr(self, "camera_lerp", 0.05)
                tx = max(0, min(target[0] - self.width  // 2, max_x))
                ty = max(0, min(target[1] - self.height // 2, max_y))
                self.story_camera_x = int(
                    self.story_camera_x + (tx - self.story_camera_x) * lerp)
                self.story_camera_y = int(
                    self.story_camera_y + (ty - self.story_camera_y) * lerp)
            return
        # follow_player (comportamiento por defecto)
        target_x = self.player_rect.centerx - (self.width  // 2)
        target_y = self.player_rect.centery - (self.height // 2)
        self.story_camera_x = max(0, min(target_x, max_x))
        self.story_camera_y = max(0, min(target_y, max_y))

    def _start_adventure(self):
        self.story_felicidad = 50
        self.story_reputacion = 50
        self.story_completed = 0
        self.story_goal = STORY_GOAL
        self.story_thought = ""
        self.story_interaction_text = ""
        self.story_previous_map_name = None
        self.story_pending_end = False
        self.story_final_key = ""
        self.story_final_text = ""
        self.story_is_seated = False
        self.story_seated_hitbox = None
        self.story_seated_pupitre = None
        self.story_clock_day = 1
        self.story_clock_hour = 7
        self.story_clock_minute = 30
        self.story_clock_accumulator_ms = 0
        self.story_npc_sara_index = 0
        self.story_npc_diego_index = 0
        self.story_npc_anim_timer = 0
        self.story_npc_positions = {}
        self.story_npc_hitbox_cache = {}
        self.decision_history = []
        self.skills_inventory = {k: dict(v) for k, v in DEFAULT_SKILLS.items()}
        self.lista_logros = Lista_Logros()
        # Reset Day 1 state
        self.current_day = 1
        self.day1_guide_active = True
        self.day1_salon_entered = False
        self.day1_seq_step = 0
        self.day1_seating_result = ""
        self.day1_in_tarde = False
        self.day1_pupitre_step = 0
        self.day1_pupitre_zoom_active = False
        self.day1_pupitre_erase_surface = None
        self.day1_pupitre_erase_progress = 0.0
        self.day1_pupitre_erase_mode = False  # True cuando el jugador presiona A
        self.day1_pupitre_result = ""
        # â”€â”€ Evento pupitre rayado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.pupitre_rayado_completado  = False
        self.pupitre_rayado_foto_active = False
        self.pupitre_rayado_foto_timer  = 0
        self.pupitre_rayado_fondo       = ""    # "" | "sara"
        self.tarde_player_seated        = False  # jugador auto-sentado en SalonTarde
        # ── Overlays Misi?n 3 (Bugs 8 y 9) ───────────────────────────────────
        self.mision3_foto_overlay_active    = False  # muestra Mision3-TomarFoto.png
        self.mision3_foto_overlay_ms        = 0
        self.mision3_llamar_profe_active    = False  # muestra Mision3-Llamarprofe.png
        self.mision3_llamar_profe_ms        = 0
        self.profe_en_sara                  = False  # profesora aparece junto a Sara tras llamarla
        self._profe_deco_name               = ""     # nombre del sprite de la profesora (cacheado)
        self.day1_completed = False
        self.day1_end_timer = 0
        self.day1_sara_npc_warned = False
        self.day1_seq_dialog_done = False
        self.day1_intro_step = 0
        self.bedroom_sleeping_active = False  # Item-4: True = mostrar overlay A_Sleeping.png
        self.day1_patio_entered = False
        self.current_mission = "Ir a la escuela"
        # Day 2 state
        self.escena_dia2_chat_completada = False
        self.escena_dia2_lucas_completada = False
        self.decision_dia2_chat = ""
        self.decision_dia2_lucas = ""
        self.day2_chat_active = False
        self.day2_chat_choice_menu_active = False
        self.day2_chat_show_ana_photo = False
        self.day2_chat_choice = ""
        self.day2_chat_pending_choice = ""
        self.day2_chat_pending_choice = ""
        self.day2_chat_overlay_image = None
        self.day2_chat_overlay_until_ms = 0
        self.day2_lucas_event_active = False
        self.day2_lucas_choice_menu_active = False
        self.day2_lucas_choice = ""
        self.day2_lucas_sprite = ""
        self.day2_guide_target = ""
        self.day2_pasillo_prompt_done = False
        self.day2_fin_active = False
        self.day2_fin_timer_ms = 0
        # Day 3 state
        self.escena_dia3_piscina_completada = False
        self.escena_dia3_cafeteria_completada = False
        self.escena_dia3_pelea_completada = False
        self.decision_dia3_piscina = ""
        self.decision_dia3_cafeteria = ""
        self.decision_dia3_pelea = ""
        self.day3_guide_target = ""
        self.day3_event_active = ""
        self.day3_choice_context = ""
        self.day3_choice = ""
        self.day3_choice_menu_active = False
        self.day3_recording_started = False
        self.day3_recording_anim_started_ms = 0
        self.day3_buscar_profesor_context = ""
        self.day3_pending_minigame_context = ""
        self.day3_minigame_result = None
        self.day3_profesor1_return_target = ""
        self.day3_foto_pelea_active = False
        self.day3_foto_pelea_timer_ms = 0
        self.day3_fin_active = False
        self.day3_fin_timer_ms = 0
        self.profesor1_fondo_actual = ""
        self.profesor1_pos = (0.5, 0.5)
        # NPC AI Manager (Evento 1)
        self.npc_ai_manager = NPCAIManager(os.path.dirname(__file__))
        # Mejora 2: set de posiciones (rx, ry) de pupitres actualmente ocupados por NPCs
        self.pupitres_ocupados: set = set()
        self.story_deco_frame_states = {}
        self.popup_logro_timer = 0
        # â”€â”€ SceneManager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.escena_dia1_completada:  bool  = False
        self.escena_activa:           object = None   # str | None
        self.scene_manager:           object = None
        self.eligiendo_asiento:       bool  = False
        self.jugador_sentado:         bool  = False
        self.decision_dia1_asiento:   str   = ""
        self._sm_dia1_result:         str   = ""
        self.player_can_move:         bool  = True
        # ── C?mara cinem?tica ─────────────────────────────────────────────────
        self.camera_mode:             str   = "follow_player"
        self.camera_target:           tuple = (0, 0)
        self.camera_lerp:             float = 0.05
        self.camera_return_after_ms:  int   = 0
        self.popup_logro_actual = None
        self.player_rect = pygame.Rect(0, 0, 28, 28)
        self._rebuild_story_world(keep_player=False)
        self.story_walls = []
        self._init_prologo()
        self.aventura_fondo = None
        self.aventura_personaje = None
        ruta_imagenes = os.path.join(os.path.dirname(__file__), "Imagenes", "Personajes", "personaje_main")
        hab_path = self._resolve_image_path("HabDía.png")
        try:
            self.aventura_fondo = Fondo(hab_path, 0, 0)
        except (OSError, pygame.error):
            placeholder = self._make_placeholder_surface(1280, 720, "HabDía.png")
            self.aventura_fondo = self._make_fondo_placeholder(hab_path, placeholder)
        audio = getattr(self, "audio", None)
        self.story_walls = self._build_story_wall_hitboxes(
            self.aventura_fondo.ruta_imagen if self.aventura_fondo else None
        )
        self._sync_scene_audio()
        spawn_x, spawn_y = self._get_spawn_position_for_current_map()
        try:
            self.aventura_personaje = Personaje(
                0, 0, ruta_imagenes,
                velocidad=self.player_speed,
                fps_animacion=8,
                color=self.character_colors["Piel"],
            )
            self.aventura_personaje.hitbox.x = spawn_x
            self.aventura_personaje.hitbox.y = spawn_y
            self.aventura_personaje.sync_sprite_from_hitbox()
            self.player_rect = self.aventura_personaje.hitbox.copy()
        except Exception as _e:
            print(f"[WARN] aventura_personaje no cargó: {_e}")
            self.aventura_personaje = None
        self.player_rect.clamp_ip(self.story_map_rect)
        self._update_story_camera()
        self.cached_background_scaled = None
        self.cached_background_size = None
        self.cached_background_source = None
        # ── Item-4: intro cinem?tica del dormitorio (solo partidas nuevas) ────
        # _loading_save=True cuando llamado desde _apply_loaded_save_data -> no lanzar intro
        if not getattr(self, "_loading_save", False):
            pname = getattr(self, "player_name", "") or "Protagonista"
            self.scene_manager   = get_scene_bedroom_intro(pname)
            self.escena_activa   = "bedroom_intro"
            self.player_can_move = False
            self.day1_intro_step = 2  # desactiva el viejo texto intro (ya no se usa)

    def _init_prologo(self):
        self.prologo_razon = random.choice(PROLOGO_RAZON_CHOICES)
        self.prologo_textos = [
            {"speaker": "Narrador", "text": "Escuela primaria antigua. Recreo en un patio pequeno y silencioso."},
            {"speaker": "Narrador", "text": "Un grupo de ninos empieza a burlarse del protagonista."},
            {"speaker": "Narrador", "text": "Otros estudiantes observan sin intervenir. Algunos se rien."},
            {"speaker": "Narrador", "text": "Un adulto pasa cerca, pero no nota la situacion."},
            {"speaker": "Narrador", "text": f"Esta vez las burlas empezaron por: {self.prologo_razon}."},
            {"speaker": "NPC 1", "text": "¿Por qué eres tan raro?"},
            {"speaker": "NPC 2", "text": "Ni siquiera sabe responder."},
            {"speaker": "NPC 3", "text": "Dejalo, siempre es asi."},
            {"speaker": self.player_name or "Protagonista", "text": "Recuerdo pensar que alguien debia hacer algo... aunque fuera una sola persona."},
            {"speaker": "Narrador", "text": "Pantalla negra. Transicion al presente."},
        ]
        self.prologo_paso = 0
        self.prologo_activo = True

    # â”€â”€ Historia y decisiones â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _resolve_ending(self):
        f = self.story_felicidad
        r = self.story_reputacion
        self.story_pending_end = True

        if f >= 50 and r >= 50:
            self.story_final_key = "FINAL POSITIVO - ALGUIEN HIZO ALGO"
            self.story_final_text = "Tal vez cambiar todo era imposible, pero alguien tenia que empezar."
            self.lista_logros.desbloquear_final_positivo()
        elif f < 50 and r < 50:
            self.story_final_key = "FINAL NEGATIVO - TODOS MIRARON"
            self.story_final_text = "Lo peor nunca fue el ruido, fue acostumbrarse a el."
        elif f < 50:
            self.story_final_key = "FINAL NEUTRAL - FELICIDAD BAJA"
            self.story_final_text = "Ser conocido no alcanzo para que todos se sintieran seguros."
        else:
            self.story_final_key = "FINAL NEUTRAL - REPUTACION BAJA"
            self.story_final_text = "Ayudar importo, aunque no siempre fuera comprendido."

        self.lista_logros.verificar_nunca_ignoraste(self.decision_history)
        self.lista_logros.verificar_empatia_pura(self.decision_history)
        self.audio.play_ending_bgm(self.story_final_key)
        self.audio.stop_ambience()

    # â”€â”€ Hitboxes de mundo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_story_wall_hitboxes(self, image_path=None):
        if image_path:
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            export_path = os.path.join(os.path.dirname(__file__), "Hitboxes", f"{image_name}_hitboxes.json")
            legacy_objects_path = os.path.join(os.path.dirname(__file__), "Objetos", f"{image_name}_objetos.json")
        else:
            export_path = os.path.join(os.path.dirname(__file__), "Hitboxes", "hitboxes_export.json")
            legacy_objects_path = None

        try:
            with open(export_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            boxes = payload.get("hitboxes", []) + payload.get("chair_zones", []) + payload.get("silla_hitboxes", [])
            spawn_data = payload.get("spawn", {})
            npc_positions = payload.get("npc_positions", {})
            self.story_spawn_world = None
            self.story_spawn_by_origin = {}
            self.story_npc_positions = {}

            if isinstance(npc_positions, dict):
                cleaned = {}
                for npc_name, ndata in npc_positions.items():
                    if isinstance(ndata, dict) and "rx" in ndata and "ry" in ndata:
                        cleaned[str(npc_name).lower()] = {
                            "rx": float(ndata.get("rx", 0.5)),
                            "ry": float(ndata.get("ry", 0.5)),
                            "rw": float(ndata.get("rw", 96 / max(1, self.story_world_width))),
                            "rh": float(ndata.get("rh", 96 / max(1, self.story_world_height))),
                        }
                self.story_npc_positions = cleaned

            if isinstance(spawn_data, dict):
                if "default" in spawn_data or "by_origin" in spawn_data:
                    default_spawn = spawn_data.get("default")
                    if isinstance(default_spawn, dict) and "rx" in default_spawn:
                        sx = int(float(default_spawn.get("rx", 0.5)) * self.story_world_width)
                        sy = int(float(default_spawn.get("ry", 0.5)) * self.story_world_height)
                        self.story_spawn_world = (sx, sy)
                    by_origin = spawn_data.get("by_origin", {})
                    if isinstance(by_origin, dict):
                        for origin_name, sdata in by_origin.items():
                            if isinstance(sdata, dict) and "rx" in sdata:
                                ox = int(float(sdata.get("rx", 0.5)) * self.story_world_width)
                                oy = int(float(sdata.get("ry", 0.5)) * self.story_world_height)
                                self.story_spawn_by_origin[str(origin_name)] = (ox, oy)
                elif "rx" in spawn_data and "ry" in spawn_data:
                    sx = int(float(spawn_data.get("rx", 0.5)) * self.story_world_width)
                    sy = int(float(spawn_data.get("ry", 0.5)) * self.story_world_height)
                    self.story_spawn_world = (sx, sy)

            for h in boxes:
                h.setdefault("type", "rect")
                h.setdefault("role", "wall")
                if h["role"] == "interactable":
                    h.setdefault("action", "puerta")
                    h.setdefault("target_image", "")

            # Prefer decoracion embedded in hitboxes JSON; fall back to legacy Objetos/*.json
            deco_list = payload.get("decoracion") or []
            if deco_list:
                object_hitboxes = self._load_story_object_hitboxes_from_list(deco_list)
            else:
                object_hitboxes = self._load_story_object_hitboxes(legacy_objects_path)

            return boxes + object_hitboxes
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

        self.story_spawn_world = None
        self.story_spawn_by_origin = {}
        self.story_npc_positions = {}
        return self._load_story_object_hitboxes(legacy_objects_path)

    def _load_story_object_hitboxes(self, objects_path):
        """Loads objects from a legacy Objetos/*_objetos.json file."""
        if not objects_path:
            return []
        try:
            with open(objects_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            return self._load_story_object_hitboxes_from_list(payload.get("objects", []))
        except (OSError, json.JSONDecodeError, TypeError):
            return []

    def _load_story_object_hitboxes_from_list(self, deco_list):
        """Converts a decoracion list (from hitboxes JSON or objetos JSON) to object hitboxes."""
        hitboxes = []
        for obj in deco_list:
            if not isinstance(obj, dict):
                continue
            try:
                hitbox = {
                    "type": "rect",
                    "role": "interactable",
                    "action": self._infer_object_action(str(obj.get("name", ""))),
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
                if obj.get("npc_owner"):
                    hitbox["npc_owner"] = str(obj["npc_owner"])
                if obj.get("npc_animation"):
                    hitbox["npc_animation"] = str(obj["npc_animation"])
                if obj.get("frames"):
                    hitbox["frames"] = int(obj["frames"])
                if obj.get("interactive_frame"):
                    hitbox["interactive_frame"] = True
                # Cachear nombre del sprite de la profesora para usarlo en _draw_profe_en_sara
                if "profesor" in hitbox["object_name"].lower() and not self._profe_deco_name:
                    self._profe_deco_name = hitbox["object_name"]
                hitboxes.append(hitbox)
            except (KeyError, TypeError, ValueError):
                continue
        return hitboxes

    def _infer_object_action(self, object_name):
        name = str(object_name).lower()
        if "cama" in name:
            return "cama"
        if "escritorio" in name:
            return "escritorio"
        return "objeto"

    def _current_scene_has_students(self):
        """Detecta si la escena actual debe tener bullicio de estudiantes."""
        if getattr(self, "story_npc_positions", None):
            return True
        for h in getattr(self, "story_walls", []):
            if h.get("role") == "interactable" and h.get("action") == "npc":
                return True
            npc_name = str(h.get("npc_character", "")).lower()
            if npc_name:
                return True
        npc_mgr = getattr(self, "npc_ai_manager", None)
        if npc_mgr is not None:
            for attr in ("npcs", "active_npcs", "event_npcs", "characters"):
                value = getattr(npc_mgr, attr, None)
                if value:
                    return True
        return False

    def _sync_scene_audio(self):
        audio = getattr(self, "audio", None)
        fondo = getattr(self, "aventura_fondo", None)
        if audio is None or fondo is None:
            return
        audio.play_bgm_for_screen("aventura")
        audio.play_ambience_for_map(
            fondo.ruta_imagen,
            has_students=self._current_scene_has_students(),
        )

    def _get_spawn_position_for_current_map(self):
        if self.story_previous_map_name:
            by_origin = self.story_spawn_by_origin.get(self.story_previous_map_name)
            if by_origin is not None:
                sx, sy = by_origin
                return (
                    max(0, min(self.story_world_width, sx)),
                    max(0, min(self.story_world_height, sy)),
                )
        if self.story_spawn_world is not None:
            sx, sy = self.story_spawn_world
            return (
                max(0, min(self.story_world_width, sx)),
                max(0, min(self.story_world_height, sy)),
            )
        sx = max(0, min(self.story_world_width, (self.story_world_width // 2) + SPAWN_OFFSET_X))
        sy = max(0, min(self.story_world_height, (self.story_world_height // 2) + SPAWN_OFFSET_Y))
        return sx, sy

    # â”€â”€ Colisiones â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _collides_with_hitbox(self, personaje_rect, h):
        mw, mh = self.story_world_width, self.story_world_height
        if h["type"] == "rect":
            r = pygame.Rect(
                int(mw * h["rx"]), int(mh * h["ry"]),
                max(8, int(mw * h["rw"])), max(8, int(mh * h["rh"])),
            )
            return personaje_rect.colliderect(r)
        elif h["type"] == "circle":
            cx = int(mw * h["cx"])
            cy = int(mh * h["cy"])
            radius = max(8, int(mw * h["r"]))
            nx = max(personaje_rect.left, min(cx, personaje_rect.right))
            ny = max(personaje_rect.top, min(cy, personaje_rect.bottom))
            return (cx - nx) ** 2 + (cy - ny) ** 2 <= radius ** 2
        elif h["type"] == "line":
            x1 = int(mw * h["x1"]); y1 = int(mh * h["y1"])
            x2 = int(mw * h["x2"]); y2 = int(mh * h["y2"])
            steps = max(1, int(max(abs(x2 - x1), abs(y2 - y1)) / 4))
            thickness_px = max(1, int(float(h.get("thickness", 8 / max(1, mw))) * mw))
            pr = max(2, thickness_px // 2)
            for i in range(steps + 1):
                t = i / steps
                px = int(x1 + (x2 - x1) * t)
                py = int(y1 + (y2 - y1) * t)
                if personaje_rect.colliderect(pygame.Rect(px - pr, py - pr, pr * 2, pr * 2)):
                    return True
        return False

    def _is_blocking_hitbox(self, h):
        return h.get("role", "wall") != "interactable" or bool(h.get("blocking", False))

    def _collides_with_interaction_area(self, personaje_rect, h):
        margin = int(getattr(self, "story_interaction_margin", 42))
        mw, mh = self.story_world_width, self.story_world_height
        if h.get("type") == "rect":
            rect = pygame.Rect(
                int(mw * h["rx"]), int(mh * h["ry"]),
                max(8, int(mw * h["rw"])), max(8, int(mh * h["rh"])),
            )
            return personaje_rect.colliderect(rect.inflate(margin * 2, margin * 2))
        probe = personaje_rect.inflate(margin * 2, margin * 2)
        return self._collides_with_hitbox(probe, h)

    def _get_player_interactable(self):
        probe = self.player_rect
        if self.aventura_personaje is not None:
            probe = self.aventura_personaje.interactable_hitbox
        candidates = []
        for h in self.story_walls:
            if h.get("role", "wall") != "interactable":
                continue
            if not self._interactable_enabled(h):
                continue
            if self._collides_with_interaction_area(probe, h):
                candidates.append(h)
        if not candidates:
            return None
        priority = {
            "cama": 0,
            "puerta": 1,
            "minijuego": 2,
            "silla": 3,
            "npc": 5,
            "objeto": 6,
        }
        return min(candidates, key=lambda h: priority.get(h.get("action", "puerta"), 4))

    def _interactable_enabled(self, h):
        if h.get("action") == "silla":
            if getattr(self, "day1_in_tarde", False) and not getattr(self, "pupitre_rayado_completado", False):
                if h.get("zone_tag") == "sara_zone":
                    return False
        if h.get("action") == "objeto":
            name = str(h.get("object_name", "")).lower()
            if "pupitre-sal" in name:
                if getattr(self, "day1_in_tarde", False) and not getattr(self, "pupitre_rayado_completado", False):
                    rx = float(h.get("rx", 0.0))
                    ry = float(h.get("ry", 0.0))
                    if abs(rx - 0.16969) < 0.03 and abs(ry - 0.68955) < 0.04:
                        return False
        return True

    def _should_show_interactable_prompt(self):
        interactable = self._get_player_interactable()
        if interactable is None:
            return False
        return interactable.get("action", "puerta") != "npc"

    def _interactable_center(self, h):
        mw, mh = self.story_world_width, self.story_world_height
        if h["type"] == "rect":
            r = pygame.Rect(
                int(mw * h["rx"]), int(mh * h["ry"]),
                max(8, int(mw * h["rw"])), max(8, int(mh * h["rh"])),
            )
            return r.center
        if h["type"] == "circle":
            return (int(mw * h["cx"]), int(mh * h["cy"]))
        if h["type"] == "line":
            x1 = int(mw * h["x1"]); y1 = int(mh * h["y1"])
            x2 = int(mw * h["x2"]); y2 = int(mh * h["y2"])
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
            # Guardar referencia al pupitre antes de limpiarla, para posicionar
            # al jugador fuera de su hitbox al levantarse.
            _prev_desk = self.story_seated_pupitre or self.story_seated_hitbox

            self.story_is_seated      = False
            self.story_seated_hitbox  = None
            self.story_seated_pupitre = None
            self.story_thought          = "Te levantaste de la silla."
            self.story_interaction_text = "Ya no estas sentado."
            self.audio.sfx_sentarse()

            # Mover al jugador justo debajo del pupitre para que no quede encima
            if _prev_desk is not None and _prev_desk.get("type") == "rect":
                _desk_cx = int(self.story_world_width  * (_prev_desk["rx"] + _prev_desk["rw"] / 2))
                _desk_by = int(self.story_world_height * (_prev_desk["ry"] + _prev_desk["rh"]))
                _stand_y = _desk_by + self.player_rect.height // 2 + 6
                self._set_player_center((_desk_cx, _stand_y))
            # â”€â”€ Tarde: el jugador se levanta -> iniciar evento pupitre rayado â”€
            if (getattr(self, "tarde_player_seated", False)
                    and getattr(self, "day1_in_tarde", False)
                    and getattr(self, "escena_dia1_completada", False)
                    and not getattr(self, "pupitre_rayado_completado", False)):
                self.tarde_player_seated    = False
                self.pupitre_rayado_fondo   = "sara"
                self.player_can_move        = False
                self.story_thought          = ""
                self.story_interaction_text = ""
                # Reposicionar al jugador junto al pupitre de Sara, no al suyo
                # (pupitre de Sara: rx=0.16969, ry=0.68955, rw=0.10240, rh=0.12793)
                _sara_cx = int(self.story_world_width  * (0.16969 + 0.10240 / 2))
                _sara_by = int(self.story_world_height * (0.68955 + 0.12793))
                if self.player_rect is not None:
                    self._set_player_center((_sara_cx, _sara_by + self.player_rect.height // 2 + 6))
                audio = getattr(self, "audio", None)
                if audio:
                    audio.play_decision_bgm()
                pname = getattr(self, "player_name", "") or "Protagonista"
                self.scene_manager  = get_scene_pupitre_rayado_intro(pname)
                self.escena_activa  = "pupitre_rayado_intro"
            return
        center = self._interactable_center(interactable)
        self._set_player_center(center)
        self.story_is_seated = True
        self.story_seated_hitbox = interactable
        self.story_thought = "Te sentaste."
        self.story_interaction_text = "Estas sentado. Presiona E para levantarte."
        self.audio.sfx_sentarse()

    def _auto_seat_player_tarde(self):
        """Sienta autom?ticamente al jugador en SalonTarde seg?n su decisi?n de asiento.
        - 'diego' -> 3.er pupitre fila inferior (rxâ‰ˆ0.4775, ryâ‰ˆ0.6864)
        - sara / ninguno -> 2.? pupitre fila inferior (rx≈0.3201, ry≈0.6911), junto a Sara
        El jugador permanece sentado hasta presionar E -> activa el evento del pupitre rayado.
        """
        choice = getattr(self, "decision_dia1_asiento", "ninguno")
        if choice == "diego":
            TARGET_RX, TARGET_RY = 0.4775, 0.6864   # 3.er pupitre fila inferior
        else:
            TARGET_RX, TARGET_RY = 0.3201, 0.6911   # 2.? pupitre fila inferior (cerca Sara)
        desk = None
        best = float("inf")
        for h in self.story_walls:
            if h.get("action") != "objeto":
                continue
            d = (h.get("rx", 0) - TARGET_RX) ** 2 + (h.get("ry", 0) - TARGET_RY) ** 2
            if d < best:
                best, desk = d, h
        if desk is None or best > 0.015:
            return
        # Sentar al jugador
        self.story_is_seated      = True
        self.story_seated_hitbox  = desk
        self.story_seated_pupitre = desk
        self.tarde_player_seated  = True
        self._set_player_center(self._interactable_center(desk))
        self.story_thought          = "Ya es tarde... todos se han ido."
        self.story_interaction_text = "Presiona E para levantarte."

    def _prepare_day3_state(self):
        npc_mgr = getattr(self, "npc_ai_manager", None)
        if npc_mgr is not None:
            fondo = getattr(self, "profesor1_fondo_actual", "") or None
            pos = getattr(self, "profesor1_pos", None)
            npc_mgr.init_day3_profesor1(self, fondo, pos)
        if (getattr(self, "day3_guide_target", "") == "profesor1"
                or getattr(self, "day3_profesor1_return_target", "")):
            return
        if not getattr(self, "escena_dia3_piscina_completada", False):
            self.day3_guide_target = "piscina"
            self.current_mission = "Ir a la piscina"
        elif not getattr(self, "escena_dia3_cafeteria_completada", False):
            self.day3_guide_target = "cafeteria"
            self.current_mission = "Ir a la cafeteria"
        elif not getattr(self, "escena_dia3_pelea_completada", False):
            self.day3_guide_target = "pasillo2"
            self.current_mission = "Ir al pasillo del segundo piso"
        else:
            self.day3_guide_target = "habtarde"
            self.current_mission = "Volver a casa"

    def _current_adventure_map_norm(self):
        fondo = getattr(self, "aventura_fondo", None)
        raw = os.path.basename(str(getattr(fondo, "ruta_imagen", ""))).lower()
        return (
            raw.replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        )

    def _change_adventure_background(self, target_image_name):
        if not target_image_name:
            self.story_interaction_text = "Esta puerta no tiene destino."
            return
        prev_name = (
            os.path.basename(self.aventura_fondo.ruta_imagen)
            if self.aventura_fondo is not None else None
        )
        target_path = self._resolve_image_path(target_image_name)
        # CAMBIO 7: si no existe, usar placeholder en lugar de abortar
        if not os.path.exists(target_path):
            placeholder = self._make_placeholder_surface(1280, 720, target_image_name)
            self.aventura_fondo = self._make_fondo_placeholder(target_path, placeholder)
        else:
            try:
                self.aventura_fondo = Fondo(target_path, 0, 0)
            except (OSError, pygame.error):
                placeholder = self._make_placeholder_surface(1280, 720, target_image_name)
                self.aventura_fondo = self._make_fondo_placeholder(target_path, placeholder)
        self.cached_background_scaled = None
        self.cached_background_size = None
        self.cached_background_source = None
        self.story_previous_map_name = prev_name
        self.story_walls = self._build_story_wall_hitboxes(self.aventura_fondo.ruta_imagen)
        if hasattr(self, "pupitres_ocupados"):
            self.pupitres_ocupados.clear()
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
        self.story_interaction_text = ""   # el cambio de mapa habla por s? solo
        self.audio.sfx_puerta()
        self._sync_scene_audio()
        # â”€â”€ NPC AI: notificar cambio de mapa â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        npc_mgr = getattr(self, "npc_ai_manager", None)
        if npc_mgr is not None:
            npc_mgr.on_map_change(os.path.basename(target_image_name), self)

        # ── Detecci?n de mapas especiales D?a 1 ───────────────────────────────
        base = os.path.basename(target_image_name).lower()
        base_norm = (
            base.replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        )
        # NPC AI: spawn en PatioDia la primera vez
        if "patiod" in base and not getattr(self, "day1_patio_entered", False):
            self.day1_patio_entered = True
            npc_mgr = getattr(self, "npc_ai_manager", None)
            if npc_mgr is not None:
                npc_mgr.init_event1_routine(self.story_world_width, self.story_world_height,
                                             getattr(self, "story_walls", []))
        if base == "salondia.png":
            if not getattr(self, "day1_salon_entered", False):
                self.day1_salon_entered = True
                self.day1_guide_active  = False
                self.current_mission    = "Elegir donde sentarse"
                if not getattr(self, "escena_dia1_completada", False):
                    # Activar escena cinem?tica del D?a 1
                    pname = getattr(self, "player_name", "") or "Protagonista"
                    self.scene_manager   = get_scene_dia1_salon(pname)
                    self.escena_activa   = "dia1_salon"
                    self.jugador_sentado = False
                    self.eligiendo_asiento = False
                    self.player_can_move = True   # beat 1 lo bloquear? al procesar
                # Si escena_dia1_completada=True -> day1_seq_step queda en 0 (sin di?logos)
        elif base in ("salontarde.png",):
            self.day1_in_tarde = True
            # NPC AI: fase saliendo cuando empieza SalonTarde
            npc_mgr = getattr(self, "npc_ai_manager", None)
            if npc_mgr is not None:
                npc_mgr.notify_phase("saliendo")
            # â”€â”€ Tarde: reloj -> 14:30 y sentar al jugador para esperar â”€â”€â”€â”€â”€â”€â”€
            if (getattr(self, "escena_dia1_completada", False)
                    and not getattr(self, "pupitre_rayado_completado", False)):
                self.story_clock_hour   = 14
                self.story_clock_minute = 30
                self._auto_seat_player_tarde()
        elif base_norm == "habtarde.png":
            if not getattr(self, "day1_completed", False) and getattr(self, "day1_in_tarde", False):
                self.day1_completed = True
            self.day1_guide_active = False
            if getattr(self, "current_mission", "") == "Volver a casa":
                self.current_mission = ""
        if getattr(self, "current_day", 1) == 2 and ("habnoche" in base):
            if not getattr(self, "escena_dia2_chat_completada", False):
                pname = getattr(self, "player_name", "") or "Protagonista"
                self.scene_manager = get_scene_dia2_chat(pname)
                self.escena_activa = "dia2_chat"
                self.player_can_move = False

        if (getattr(self, "current_day", 1) == 2
                and ("pasillo1_dia" in base_norm or "pasillo1dia" in base_norm)
                and getattr(self, "day2_guide_target", "") == "escuela"
                and not getattr(self, "day2_pasillo_prompt_done", False)):
            self.day2_pasillo_prompt_done = True
            self.story_thought = "Vaya, me dieron ganas de ir al baño."
            self.current_mission = "Ir al baño"
            self.day2_guide_target = "bano"

        is_bano = "banodia" in base_norm
        if getattr(self, "current_day", 1) == 2 and is_bano:
            if not getattr(self, "escena_dia2_lucas_completada", False):
                self.day2_guide_target = ""
                pname = getattr(self, "player_name", "") or "Protagonista"
                self.scene_manager = get_scene_dia2_lucas_bano(pname)
                self.escena_activa = "dia2_lucas"
                self.player_can_move = False

        if (getattr(self, "current_day", 1) == 2 and base_norm == "habtarde.png"
                and getattr(self, "escena_dia2_lucas_completada", False)):
            self.day2_guide_target = ""
            self.current_mission = "Dormir"

        if getattr(self, "current_day", 1) == 3:
            self._prepare_day3_state()
            returning_target = getattr(self, "day3_profesor1_return_target", "")
            if returning_target and base_norm == os.path.basename(returning_target).lower().replace("í", "i").replace("é", "e"):
                self.day3_profesor1_return_target = ""
                self.day3_guide_target = ""
                mgr = getattr(self, "npc_ai_manager", None)
                if mgr is not None:
                    mgr.place_profesor1_near_player(self)
                pname = getattr(self, "player_name", "") or "Protagonista"
                if getattr(self, "day3_buscar_profesor_context", "") == "pelea":
                    self.scene_manager = get_scene_dia3_pelea_profesor(pname)
                    self.escena_activa = "dia3_pelea_profesor"
                else:
                    self.scene_manager = get_scene_dia3_cafeteria_profesor(pname)
                    self.escena_activa = "dia3_cafeteria_profesor"
                self.player_can_move = False
            elif "piscinadia" in base_norm and not getattr(self, "escena_dia3_piscina_completada", False):
                pname = getattr(self, "player_name", "") or "Protagonista"
                self.scene_manager = get_scene_dia3_piscina(pname)
                self.escena_activa = "dia3_piscina"
                self.player_can_move = False
            elif ("cafeteria" in base_norm
                    and getattr(self, "escena_dia3_piscina_completada", False)
                    and not getattr(self, "escena_dia3_cafeteria_completada", False)
                    and not getattr(self, "day3_profesor1_return_target", "")):
                pname = getattr(self, "player_name", "") or "Protagonista"
                self.scene_manager = get_scene_dia3_cafeteria(pname)
                self.escena_activa = "dia3_cafeteria"
                self.player_can_move = False
            elif ("pasillo2dia" in base_norm
                    and getattr(self, "escena_dia3_cafeteria_completada", False)
                    and not getattr(self, "escena_dia3_pelea_completada", False)
                    and not getattr(self, "day3_profesor1_return_target", "")):
                pname = getattr(self, "player_name", "") or "Protagonista"
                self.scene_manager = get_scene_dia3_pelea(pname)
                self.escena_activa = "dia3_pelea"
                self.player_can_move = False
            elif (base_norm == "habtarde.png"
                    and getattr(self, "escena_dia3_pelea_completada", False)):
                pname = getattr(self, "player_name", "") or "Protagonista"
                self.scene_manager = get_scene_dia3_fin(pname)
                self.escena_activa = "dia3_fin"
                self.player_can_move = False

    def _execute_interactable_action(self, interactable):
        action = interactable.get("action", "puerta")
        if action == "puerta":
            if self.story_is_seated:
                self.story_is_seated = False
                self.story_seated_hitbox = None
                self.story_seated_pupitre = None
            self.story_thought = "Cruzaste una puerta."
            self._change_adventure_background(interactable.get("target_image", ""))
            return
        if action == "silla":
            # CAMBIO 3: si estamos en la secuencia del D?a 1 esperando silla
            if getattr(self, "eligiendo_asiento", False) or getattr(self, "day1_seq_step", 0) == 3:
                zone_tag = interactable.get("zone_tag", "")
                if zone_tag == "sara_zone":
                    result = "sentado_con_sara"
                    df, dr = 2, -1
                elif zone_tag == "diego_zone":
                    result = "sentado_con_diego"
                    df, dr = -3, 2
                else:
                    result = "sentado_solo"
                    df, dr = -2, 0
                self.day1_seating_result = result
                self.story_felicidad = max(0, min(100, self.story_felicidad + df))
                self.story_reputacion = max(0, min(100, self.story_reputacion + dr))
                self.decision_history.append({
                    "event_id": "primer_dia_espacial",
                    "option_label": result,
                    "dF": df, "dR": dr,
                    "thought": f"Me senté: {result}",
                })
                self.story_completed += 1
                self.day1_seq_step = 4
                self.eligiendo_asiento = False
                self.audio.sfx_decision()
                npc_mgr = getattr(self, "npc_ai_manager", None)
                if npc_mgr is not None:
                    npc_mgr.notify_phase("en_clase")
                if self.story_completed >= self.story_goal:
                    self._resolve_ending()
                self.audio.sfx_sentarse()
                # Fade y transici?n a SalonTarde
                transitions = getattr(self, "transitions", None)
                if transitions is not None and transitions.is_idle():
                    transitions.request(self, "aventura", callback=lambda: self._change_adventure_background("SalonTarde.png"))
                else:
                    self._change_adventure_background("SalonTarde.png")
                return
            self._toggle_seat_state(interactable)
            return
        if action == "npc":
            npc_name = interactable.get("npc_character", "NPC")
            self.story_interaction_text = f"{npc_name} esta ocupado/a."
            self.audio.sfx_npc()
            return
        if action == "minijuego":
            # Activar minijuego al interactuar con el objeto disparador
            tipo = interactable.get("minijuego_tipo", "penaltis")
            if not getattr(self, "player_can_move", True):
                # No iniciar durante una cinem?tica
                return
            self.story_thought = ""
            self.story_interaction_text = ""
            # Mostrar di?logo previo del NPC seg?n el tipo de minijuego
            pname = getattr(self, "player_name", "") or "Protagonista"
            if tipo == "atrapa_emociones":
                self.scene_manager = get_scene_callejon_emociones(pname, tipo)
            else:
                self.scene_manager = get_scene_patio_penaltis(pname, tipo)
            self.escena_activa   = "minijuego_intro"
            self.player_can_move = False
            return
        if action == "cama":
            if getattr(self, "player_can_move", True):
                if (getattr(self, "current_day", 1) == 2
                        and getattr(self, "escena_dia2_lucas_completada", False)):
                    # Fin del Día 2: dormir → Día 3
                    self.current_mission = ""
                    self.bedroom_sleeping_active = True
                    self.day2_fin_active = True
                    self.day2_fin_timer_ms = 3000
                    self.player_can_move = False
                else:
                    pname = getattr(self, "player_name", "") or "Protagonista"
                    self.scene_manager = get_scene_cama_dormir(pname)
                    self.escena_activa = "cama_dormir"
            return
        if action == "mensaje":
            texto = interactable.get("texto", "...")
            self.story_interaction_text = texto
            self.audio.sfx_interactuar()
            return
        if action == "escritorio":
            self.story_thought          = "Aquí habrá minijuegos más adelante."
            self.story_interaction_text = "[ Escritorio - contenido próximamente ]"
            self.audio.sfx_interactuar()
            return
        if action == "objeto":
            raw_name = interactable.get("object_name", "objeto")
            raw_name_norm = str(raw_name).lower().replace("ó", "o").replace("Ó", "o")
            if "pupitre-salon1.png" in raw_name_norm or "pupitre-saln1.png" in raw_name_norm or "pupitre-sal" in raw_name_norm:
                npc_owner = interactable.get("npc_owner", "")
                if npc_owner:
                    self.story_interaction_text = f"El pupitre de {npc_owner} está reservado."
                    self.audio.sfx_interactuar()
                    return
                # SceneManager: eligiendo asiento
                if getattr(self, "eligiendo_asiento", False) and not getattr(self, "jugador_sentado", False):
                    cx = round(float(interactable.get("rx", 0)), 4)
                    cy = round(float(interactable.get("ry", 0)), 4)
                    pup_set = getattr(self, "pupitres_ocupados", set())
                    if (cx, cy) in pup_set:
                        self.story_interaction_text = "Este pupitre ya está ocupado."
                        self.audio.sfx_interactuar()
                        return
                    self.story_is_seated      = True
                    self.story_seated_hitbox  = interactable
                    self.story_seated_pupitre = interactable
                    self.story_thought        = "Este es mi lugar."
                    self.jugador_sentado      = True
                    self.audio.sfx_sentarse()
                    return
                if self.story_is_seated and self.story_seated_pupitre is interactable:
                    self.story_is_seated = False
                    self.story_seated_hitbox = None
                    self.story_seated_pupitre = None
                    self.story_interaction_text = "Te levantaste del pupitre."
                    self.story_thought = ""
                    self.audio.sfx_sentarse()
                else:
                    self.story_is_seated = True
                    self.story_seated_hitbox = interactable
                    self.story_seated_pupitre = interactable
                    self.story_interaction_text = "Te sentaste en tu pupitre."
                    self.story_thought = "Este es mi lugar."
                    self.audio.sfx_sentarse()
                return
            if interactable.get("interactive_frame"):
                key = f"{interactable.get('object_name','')}_{interactable.get('rx',0):.4f}"
                frames = int(interactable.get("frames", 2))
                current = self.story_deco_frame_states.get(key, 0)
                self.story_deco_frame_states[key] = (current + 1) % frames
                self.audio.sfx_interactuar()
        
            elif interactable.get("toggle_object"):
                alt = interactable.get("toggle_object")
                key = f"{interactable.get('object_name','')}_{interactable.get('rx',0):.4f}"
                current = self.story_deco_frame_states.get(key, False)
                self.story_deco_frame_states[key] = not current
                self.audio.sfx_interactuar()
            return
    
        friendly = self._friendly_object_name(raw_name)
        self.story_interaction_text = f"Interactuaste con {friendly}."
        self.story_thought = "Hay algo interesante aqui."
        self.audio.sfx_object(raw_name)
        return
        # Acci?n desconocida: no mostrar texto t?cnico al jugador
        self.story_interaction_text = ""

    # â”€â”€ Nombres amigables para la UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _FRIENDLY_OBJECTS: dict = {
        "armario": "el armario",      "cama": "la cama",
        "escritorio": "el escritorio","pupitre": "el pupitre",
        "silla": "la silla",          "mochila": "la mochila",
        "ventana": "la ventana",      "pizarra": "la pizarra",
        "puerta": "la puerta",        "balon": "el balón",
        "balón": "el balón",          "mesa": "la mesa",
        "estante": "el estante",      "cartel": "el cartel",
        "poster": "el póster",        "telefono": "el teléfono",
        "lampara": "la lámpara",      "reloj": "el reloj",
        "cuadro": "el cuadro",        "libro": "el libro",
        "mapa": "el mapa",            "bolso": "el bolso",
        "bolsa": "la bolsa",          "maleta": "la maleta",
        "locker": "el casillero",     "taquilla": "la taquilla",
        "banca": "la banca",          "banco": "el banco",
        "caneca": "la caneca",        "papelera": "la papelera",
    }

    def _friendly_object_name(self, raw_name: str) -> str:
        """Convierte el nombre de archivo de un objeto en texto legible para la UI."""
        base = os.path.splitext(raw_name)[0].lower()
        for key, friendly in self._FRIENDLY_OBJECTS.items():
            if key in base:
                return friendly
        return "algo"

    def _move_player_with_walls(self, dx, dy):
        currently_stuck = any(
            self._is_blocking_hitbox(w) and self._collides_with_hitbox(self.player_rect, w)
            for w in self.story_walls
        )
        prev_x = self.player_rect.x
        self.player_rect.x += dx
        self.player_rect.clamp_ip(self.story_map_rect)
        if not currently_stuck:
            for wall in self.story_walls:
                if self._is_blocking_hitbox(wall) and self._collides_with_hitbox(self.player_rect, wall):
                    self.player_rect.x = prev_x
                    break
        prev_y = self.player_rect.y
        self.player_rect.y += dy
        self.player_rect.clamp_ip(self.story_map_rect)
        if not currently_stuck:
            for wall in self.story_walls:
                if self._is_blocking_hitbox(wall) and self._collides_with_hitbox(self.player_rect, wall):
                    self.player_rect.y = prev_y
                    break

    # â”€â”€ Culling de objetos (Tarea 9) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _get_visible_hitboxes(self):
        """Retorna solo hitboxes dentro de 2x el tamano de pantalla del jugador."""
        player_cx = self.player_rect.centerx
        player_cy = self.player_rect.centery
        threshold_x = self.width * 2
        threshold_y = self.height * 2
        mw, mh = self.story_world_width, self.story_world_height
        visible = []
        for h in self.story_walls:
            if h.get("type") == "rect":
                hx = int(mw * h.get("rx", 0)) + int(mw * h.get("rw", 0)) / 2
                hy = int(mh * h.get("ry", 0)) + int(mh * h.get("rh", 0)) / 2
            elif h.get("type") == "circle":
                hx = int(mw * h.get("cx", 0.5))
                hy = int(mh * h.get("cy", 0.5))
            else:
                hx = int(mw * h.get("x1", 0.5))
                hy = int(mh * h.get("y1", 0.5))
            if abs(hx - player_cx) <= threshold_x and abs(hy - player_cy) <= threshold_y:
                visible.append(h)
        return visible

    def _dist_to_hitbox(self, h):
        """Distancia normalizada del jugador al centro de un hitbox (en px mundo)."""
        mw, mh = self.story_world_width, self.story_world_height
        if h.get("type") == "rect":
            cx = int(mw * h["rx"]) + int(mw * h["rw"]) // 2
            cy = int(mh * h["ry"]) + int(mh * h["rh"]) // 2
        elif h.get("type") == "circle":
            cx = int(mw * h["cx"])
            cy = int(mh * h["cy"])
        else:
            cx = int(mw * h.get("x1", 0.5))
            cy = int(mh * h.get("y1", 0.5))
        dx = self.player_rect.centerx - cx
        dy = self.player_rect.centery - cy
        return (dx * dx + dy * dy) ** 0.5

    # ── Actualizaci?n de aventura ─────────────────────────────────────────────

    def _update_adventure(self):
        if self.current_screen != "aventura" or self.story_pending_end:
            return
        if getattr(self, "day1_intro_step", 2) < 2:
            if self.aventura_personaje is not None:
                self.aventura_personaje.moviendose = False
                self.aventura_personaje.frame_actual = 0
            return
        dt_ms = self.clock.get_time()

        self.story_npc_anim_timer += dt_ms
        if self.story_npc_anim_timer >= 1000000:
            self.story_npc_anim_timer = 0

        # NPC AI update
        npc_mgr = getattr(self, "npc_ai_manager", None)
        if npc_mgr is not None:
            npc_mgr.update(dt_ms, self)
        self._sync_scene_audio()

        # â”€â”€ Temporizador foto pupitre rayado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if getattr(self, "pupitre_rayado_foto_active", False):
            self.pupitre_rayado_foto_timer -= dt_ms
            if self.pupitre_rayado_foto_timer <= 0:
                self.pupitre_rayado_foto_active = False
                self.pupitre_rayado_foto_timer  = 0

        # ── Temporizadores overlays Misi?n 3 (Bugs 8, 9) ────────────────────
        # foto: timer de 1800ms - desaparece autom?ticamente
        if getattr(self, "mision3_foto_overlay_active", False):
            self.mision3_foto_overlay_ms = max(0, self.mision3_foto_overlay_ms - dt_ms)
            if self.mision3_foto_overlay_ms <= 0:
                self.mision3_foto_overlay_active = False
        # llamar_profe: si ms == 0 no hay timer; la escena lo limpia en beat_completar
        if getattr(self, "mision3_llamar_profe_active", False):
            if self.mision3_llamar_profe_ms > 0:
                self.mision3_llamar_profe_ms = max(0, self.mision3_llamar_profe_ms - dt_ms)
                if self.mision3_llamar_profe_ms <= 0:
                    self.mision3_llamar_profe_active = False

        # â”€â”€ SceneManager update â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sm = getattr(self, "scene_manager", None)
        if sm is not None and getattr(self, "escena_activa", None) is not None:
            sm.update(dt_ms, self)
            if sm.done and getattr(self, "escena_activa", None) is not None:
                # Edge case: escena termin? sin que beat8 limpiara el flag
                self.escena_activa    = None
                self.player_can_move  = True

        if getattr(self, "day2_chat_overlay_until_ms", 0) > 0:
            self.day2_chat_overlay_until_ms = max(0, self.day2_chat_overlay_until_ms - dt_ms)
            if self.day2_chat_overlay_until_ms <= 0:
                self.day2_chat_overlay_image = None
                if getattr(self, "day2_chat_pending_choice", ""):
                    self.day2_chat_choice = self.day2_chat_pending_choice
                    self.day2_chat_pending_choice = ""

        if getattr(self, "day3_foto_pelea_active", False):
            self.day3_foto_pelea_timer_ms = max(0, self.day3_foto_pelea_timer_ms - dt_ms)
            if self.day3_foto_pelea_timer_ms <= 0:
                self.day3_foto_pelea_active = False

        if (getattr(self, "current_day", 1) == 3
                and getattr(self, "day3_guide_target", "") == "profesor1"
                and getattr(self, "escena_activa", None) is None):
            prof_map = str(getattr(self, "profesor1_fondo_actual", ""))
            prof_pos = getattr(self, "profesor1_pos", (0.5, 0.5))
            current_map = os.path.basename(str(getattr(getattr(self, "aventura_fondo", None), "ruta_imagen", "")))
            if prof_map and os.path.splitext(prof_map)[0].lower() == os.path.splitext(current_map)[0].lower():
                world_w = max(1, getattr(self, "story_world_width", 1280))
                world_h = max(1, getattr(self, "story_world_height", 720))
                px = float(prof_pos[0]) * world_w
                py = float(prof_pos[1]) * world_h
                dx = self.player_rect.centerx - px
                dy = self.player_rect.centery - py
                if dx * dx + dy * dy < 120 * 120:
                    pname = getattr(self, "player_name", "") or "Protagonista"
                    context = getattr(self, "day3_buscar_profesor_context", "cafeteria")
                    self.scene_manager = get_scene_dia3_buscar_profesor(pname, context)
                    self.escena_activa = "dia3_buscar_profesor"
                    self.player_can_move = False

        if getattr(self, "day2_fin_active", False):
            self.day2_fin_timer_ms = max(0, self.day2_fin_timer_ms - dt_ms)
            if self.day2_fin_timer_ms <= 0:
                self.day2_fin_active = False
                self.bedroom_sleeping_active = False
                self.current_day = 3
                self._change_adventure_background("HabDía.png")
                self._prepare_day3_state()
                self.player_can_move = True

        # ── Temporizador retorno de c?mara ────────────────────────────────────
        if getattr(self, "camera_return_after_ms", 0) > 0:
            self.camera_return_after_ms -= dt_ms
            if self.camera_return_after_ms <= 0:
                self.camera_return_after_ms = 0
                self.camera_mode = "follow_player"

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
                old_idx = self.story_npc_sara_index
                self.story_npc_sara_index = (self.story_npc_anim_timer // 220) % len(self.story_npc_sara_frames)
                if self.story_npc_sara_index != old_idx:
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_animation("npc_walk")
            if self.story_npc_diego_frames:
                old_idx = self.story_npc_diego_index
                self.story_npc_diego_index = (self.story_npc_anim_timer // 220) % len(self.story_npc_diego_frames)
                if self.story_npc_diego_index != old_idx:
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_animation("npc_walk")

        if self.story_is_seated:
            if self.aventura_personaje is not None:
                self.aventura_personaje.moviendose = False
                self.aventura_personaje.frame_actual = 0
                self.aventura_personaje.contador_animacion = 0
            self._update_story_camera()
            return

        # ── Bloqueo de movimiento durante cinem?ticas ─────────────────────────
        if not getattr(self, "player_can_move", True):
            if self.aventura_personaje is not None:
                self.aventura_personaje.moviendose = False
                self.aventura_personaje.frame_actual = 0
                self.aventura_personaje.contador_animacion = 0
            self._update_story_camera()
            return

        keys = pygame.key.get_pressed()
        sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = self.player_speed * (1.8 if sprint else 1.0)
        move_x = (
            (1 if keys[self.controls["mover_derecha"]] else 0)
            - (1 if keys[self.controls["mover_izquierda"]] else 0)
        ) * speed
        move_y = (
            (1 if keys[self.controls["mover_abajo"]] else 0)
            - (1 if keys[self.controls["mover_arriba"]] else 0)
        ) * speed
        prev_x = self.player_rect.x
        prev_y = self.player_rect.y
        self._move_player_with_walls(move_x, move_y)
        actual_dx = self.player_rect.x - prev_x
        actual_dy = self.player_rect.y - prev_y
        self._update_story_camera()
        audio = getattr(self, "audio", None)
        if audio is not None and getattr(self, "aventura_fondo", None) is not None:
            audio.update_player_motion(
                actual_dx != 0 or actual_dy != 0,
                sprint=sprint,
                map_name=self.aventura_fondo.ruta_imagen,
            )
        # ── CAMBIO 4: Detecci?n de proximidad al pupitre rayado ──────────────
        # (s?lo activo si no hay escena autom?tica ni evento ya completado)
        if (getattr(self, "day1_in_tarde", False)
                and getattr(self, "day1_pupitre_step", 0) == 0
                and not getattr(self, "pupitre_rayado_completado", False)
                and getattr(self, "escena_activa", None) is None):
            for h in self.story_walls:
                if h.get("zone_tag") == "pupitre_rayado":
                    dist = self._dist_to_hitbox(h)
                    if dist < 150:
                        self.day1_pupitre_step = 1
                        pname = getattr(self, "player_name", "") or "Protagonista"
                        self.story_thought = f"{pname}: ¿Qué dice este pupitre todo rayado?"
                        if audio is not None:
                            audio.play_sfx("pupitre_alerta")
                        break
        # â”€â”€ CAMBIO 3: Proximidad a zona Sara durante espera de silla â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if getattr(self, "day1_seq_step", 0) == 3 and not getattr(self, "day1_sara_npc_warned", False):
            for h in self.story_walls:
                if h.get("zone_tag") == "sara_zone":
                    dist = self._dist_to_hitbox(h)
                    if dist < 150:
                        self.day1_sara_npc_warned = True
                        self.story_interaction_text = "NPC: Ella siempre anda sola."
                        if audio is not None:
                            audio.sfx_burla()
                        break

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
                    total = len(self.aventura_personaje.animaciones[self.aventura_personaje.direccion])
                    self.aventura_personaje.frame_actual = (self.aventura_personaje.frame_actual + 1) % total
            else:
                self.aventura_personaje.frame_actual = 0
                self.aventura_personaje.contador_animacion = 0

    # ── Simulaci?n ────────────────────────────────────────────────────────────

    def _init_simulacion(self):
        if self.simulacion_activa:
            return
        base_path = os.path.dirname(__file__)
        ruta_imagenes = os.path.join(base_path, "Imagenes", "Personajes", "personaje_main")
        self.simulacion_fondo = Fondo(self._resolve_image_path("HabDía.png"), 0, 0)
        self.simulacion_personaje = Personaje(
            600, 280, ruta_imagenes, velocidad=4, fps_animacion=8,
            color=self.character_colors["Piel"]
        )
        self.simulacion_animacion = Animacion(
            self._resolve_image_path("INTERACTUAR.webp"), 5, fps_animacion=5, x=800, y=400,
        )
        self.simulacion_animacion.velocidad = 3
        self.simulacion_animacion.mover_lateral(100, 700)
        try:
            self.simulacion_aviso = pygame.image.load(
                self._resolve_image_path("INTERACTUAR.webp")
            ).convert_alpha()
        except (OSError, pygame.error):
            self.simulacion_aviso = None
        self.simulacion_pared1 = pygame.Rect(290, 290, 100, 100)
        self.simulacion_pared2 = pygame.Rect(500, 290, 100, 100)
        self.simulacion_mostrar_aviso = False
        self.simulacion_activa = True

    def _update_simulacion(self):
        if self.current_screen != "simulacion" or not self.simulacion_activa:
            return
        x_prev = self.simulacion_personaje.x
        y_prev = self.simulacion_personaje.y
        self.simulacion_personaje.actualizar()
        if (
            self.simulacion_personaje.hitbox.colliderect(self.simulacion_pared1)
            or self.simulacion_personaje.hitbox.colliderect(self.simulacion_pared2)
        ):
            self.simulacion_personaje.x = x_prev
            self.simulacion_personaje.y = y_prev
            self.simulacion_personaje.hitbox.x = x_prev
            self.simulacion_personaje.hitbox.y = y_prev
        self.simulacion_mostrar_aviso = self.simulacion_personaje.hitbox.colliderect(self.simulacion_pared2)
        self.simulacion_animacion.actualizar()
        self.simulacion_animacion.mover_lateral(100, 700)

    def _reinit_simulacion_personaje(self):
        base_path = os.path.dirname(__file__)
        ruta_imagenes = os.path.join(base_path, "Imagenes", "Personajes", "personaje_main")
        self.simulacion_personaje = Personaje(
            600, 280, ruta_imagenes, velocidad=4, fps_animacion=8,
            color=self.character_colors["Piel"]
        )

    # â”€â”€ Utilidades de imagen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _make_placeholder_surface(self, w, h, path_str=""):
        """CAMBIO 7: Crea Surface de placeholder para im?genes faltantes."""
        surf = pygame.Surface((w, h))
        surf.fill((42, 42, 42))
        pygame.draw.rect(surf, (255, 68, 68), (0, 0, w, h), 3)
        try:
            font = self.base_fonts.get("body") or self.base_fonts.get("small")
            if font:
                t1 = font.render("Imagen Faltante", True, (255, 255, 255))
                surf.blit(t1, (w // 2 - t1.get_width() // 2, h // 2 - t1.get_height() - 4))
                short = str(path_str)[-60:] if len(str(path_str)) > 60 else str(path_str)
                t2 = font.render(short, True, (200, 200, 200))
                surf.blit(t2, (w // 2 - t2.get_width() // 2, h // 2 + 8))
        except Exception:
            pass
        return surf

    def _make_fondo_placeholder(self, path_str, surface):
        """Crea un objeto Fondo-compatible usando una Surface placeholder."""
        class _FondoSustituto:
            def __init__(self, ruta, img):
                self.ruta_imagen = ruta
                self.imagen = img
            def dibujar(self, pantalla):
                pantalla.blit(self.imagen, (0, 0))
        return _FondoSustituto(str(path_str), surface)

    def _resolve_image_path(self, image_ref):
        images_dir = os.path.join(os.path.dirname(__file__), "Imagenes")
        if not image_ref:
            image_ref = "HabDía.png"
        normalized = os.path.normpath(str(image_ref).strip())
        direct = normalized if os.path.isabs(normalized) else os.path.join(os.path.dirname(__file__), normalized)
        if os.path.exists(direct):
            return direct
        file_name = os.path.basename(normalized)
        event_path = os.path.join(images_dir, "Cosas_especificas_eventos", file_name)
        if os.path.exists(event_path):
            return event_path
        by_name = os.path.join(images_dir, file_name)
        if os.path.exists(by_name):
            return by_name
        def _norm_key(name: str) -> str:
            lowered = name.lower()
            decomposed = unicodedata.normalize("NFD", lowered)
            return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")

        file_name_key = _norm_key(file_name)
        try:
            for root, _, files in os.walk(images_dir):
                for name in files:
                    if _norm_key(name) == file_name_key:
                        return os.path.join(root, name)
        except OSError:
            pass
        return by_name

    def _is_first_day_classroom_context(self):
        if not getattr(self, "day1_salon_entered", False):
            return False
        # Solo activa cuando el fondo tiene NPCs definidos (estamos en el sal?n).
        return any(
            h.get("role") == "interactable" and h.get("action") == "npc"
            for h in self.story_walls
        )

    # â”€â”€ Carga de sprites NPC â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    _SPRITE_SHEET_FRAME_COUNTS: dict = {
        "npc2_burla.png": 16,
        "andres_pelear.png": 16,
        "carlos_pelear.png": 16,
        "mateo_llorando.png": 16,
        "sara_llorar.png": 16,
        "npc1_burla.png": 8,
        "npc1_chisme.png": 8,
        "npc2_chisme.png": 8,
        "npc2_grabar_animacion.png": 8,
        "npc1_grabar_animacion.png": 4,
        "samuel_llorando_animacion.png": 4,
        "npc1_grabar.png": 1,
        "npc2_grabar.png": 1,
    }

    def _load_sprite_sheet_frames(self, path):
        frames = []
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except (OSError, pygame.error):
            return frames
        sw, sh = sheet.get_size()
        file_name = os.path.basename(str(path)).lower()
        frame_count = self._SPRITE_SHEET_FRAME_COUNTS.get(file_name)
        if frame_count is None:
            is_static = any(t in file_name for t in ("sentado", "parado", "idle", "stand"))
            frame_count = 1 if is_static else (max(1, round(sw / max(1, sh))) if sw > sh * 1.5 else 1)
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
        # Tarea 8: Cargar sprite del NPC por nombre desde Imagenes/Personajes/<Nombre>/
        npc_dir = os.path.join(os.path.dirname(__file__), "Imagenes", "Personajes", str(character_name))
        # Fallback para NPC2 incompleto: usar NPC1
        # [IMG]ï¸ ASSET_IMG: Imagenes/Personajes/NPC2/parado.png   | mismas dims que NPC1 | NPC2 sprite parado
        # [IMG]ï¸ ASSET_IMG: Imagenes/Personajes/NPC2/sentado.png  | mismas dims que NPC1 | NPC2 sprite sentado
        # [IMG]ï¸ ASSET_IMG: Imagenes/Personajes/NPC2/hablando.png | mismas dims que NPC1 | NPC2 sprite hablando
        if not os.path.isdir(npc_dir):
            fallback_dir = os.path.join(os.path.dirname(__file__), "Imagenes", "Personajes", "NPC1")
            if os.path.isdir(fallback_dir):
                npc_dir = fallback_dir
        npc_path = os.path.join(npc_dir, str(animation_file))
        frames = self._load_sprite_sheet_frames(npc_path)
        self.story_npc_hitbox_cache[key] = frames
        return frames

    def _load_story_interact_prompt(self):
        prompt_path = self._resolve_image_path("INTERACTUAR.webp")
        try:
            self.story_interact_prompt_img = pygame.image.load(prompt_path).convert_alpha()
            base_w = max(22, int(self.story_interact_prompt_img.get_width() * 0.24))
            base_h = max(22, int(self.story_interact_prompt_img.get_height() * 0.24))
            self.story_interact_prompt_scaled = pygame.transform.smoothscale(
                self.story_interact_prompt_img, (base_w, base_h)
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
                (max(24, int(raw.get_width() * 2.8)), max(24, int(raw.get_height() * 2.8))),
            )
        except (OSError, pygame.error):
            self.story_seated_sprite = None

    def _load_story_event_npc_sprites(self):
        base_dir = os.path.join(os.path.dirname(__file__), "Imagenes", "Personajes")
        sara_sheet = os.path.join(base_dir, "Sara", "Sara_dibujando.png")
        diego_sheet = os.path.join(base_dir, "Diego", "Diego_hablando.png")
        self.story_npc_sara_frames = self._load_sprite_sheet_frames(sara_sheet)
        self.story_npc_diego_frames = self._load_sprite_sheet_frames(diego_sheet)

    def _load_object_interactable_image(self, object_name):
        if not object_name:
            return None
        cached = self.story_object_image_cache.get(object_name)
        if cached is not None:
            return cached
        base = os.path.dirname(__file__)
        # Ruta 1: Cosas_especificas_eventos/<nombre> (assets de escenas puntuales)
        object_path = os.path.join(base, "Imagenes", "Cosas_especificas_eventos", object_name)
        if not os.path.isfile(object_path):
            # Ruta 2: Interactuables/<nombre>  (objetos cl?sicos)
            object_path = os.path.join(base, "Imagenes", "Interactuables", object_name)
        if not os.path.isfile(object_path):
            # Ruta 3: Imagenes/<nombre>  (sprites de personajes con prefijo
            #  "Personajes/Xxx/archivo.png" puestos desde el hitbox editor)
            object_path = os.path.join(base, "Imagenes",
                                        object_name.replace("/", os.sep))
        try:
            image = pygame.image.load(object_path).convert_alpha()
        except (OSError, pygame.error):
            # CAMBIO 7: placeholder en lugar de None
            image = self._make_placeholder_surface(256, 256, object_path)
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
            1, 1,
        )
        rect.width = max(1, min(iw - rect.x, int(cw * iw)))
        rect.height = max(1, min(ih - rect.y, int(ch * ih)))
        if rect.topleft == (0, 0) and rect.size == image.get_size():
            return image
        return image.subsurface(rect)

    # â”€â”€ Fuentes y display â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _find_custom_font_path(self):
        base_dir = os.path.dirname(__file__)
        candidates = [
            os.path.join(base_dir, "Fuentes", "DeterminationMonoWebRegular-Z5oq.ttf"),
            os.path.join(base_dir, "Fuentes", "DeterminationMonoWeb.ttf"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _pick_readable_font(self):
        for name in ("determination mono web", "segoeui", "arial", "verdana", "tahoma", "calibri"):
            if pygame.font.match_font(name):
                return name
        return None

    def _build_fonts(self):
        custom = self._find_custom_font_path()
        if custom:
            return {
                "title":    pygame.font.Font(custom, 56),
                "subtitle": pygame.font.Font(custom, 28),
                "button":   pygame.font.Font(custom, 30),
                "body":     pygame.font.Font(custom, 26),
                "small":    pygame.font.Font(custom, 22),
            }
        name = self._pick_readable_font()
        return {
            "title":    pygame.font.SysFont(name, 56, bold=True),
            "subtitle": pygame.font.SysFont(name, 28, bold=True),
            "button":   pygame.font.SysFont(name, 30, bold=True),
            "body":     pygame.font.SysFont(name, 26),
            "small":    pygame.font.SysFont(name, 22),
        }

    def _debug_jump_to_day(self, day: int):
        """Debug helper: jump directly to the start of the given day (1, 2, or 3)."""
        # Ensure the adventure personaje exists (may not if jumped from main menu)
        if self.aventura_personaje is None:
            if not getattr(self, "player_name", ""):
                self.player_name = "Debug"
            self._start_adventure()
            # _start_adventure sets current_screen and triggers bedroom_intro — reset it
            self.escena_activa = None
            self.scene_manager = None
            self.player_can_move = True

        # Abort any active scene/cinematic
        self.scene_manager = None
        self.escena_activa = None
        self.player_can_move = True
        self.bedroom_sleeping_active = False
        self.day2_fin_active = False
        self.day3_fin_active = False
        self.story_interaction_text = ""
        self.story_thought = ""

        if day == 1:
            self.current_day = 1
            self.escena_dia1_completada = False
            self.day1_completed = False
            self.day1_guide_active = True
            self.day1_salon_entered = False
            self.day1_seq_step = 0
            self.day1_seating_result = ""
            self.day1_in_tarde = False
            self.day1_intro_step = 2
            self.day1_patio_entered = False
            self.pupitre_rayado_completado = False
            self.current_mission = "Ir a la escuela"
            self.current_screen = "aventura"
            self._change_adventure_background("HabDía.png")

        elif day == 2:
            self.current_day = 2
            self.escena_dia1_completada = True
            self.day1_completed = True
            self.escena_dia2_chat_completada = False
            self.escena_dia2_lucas_completada = False
            self.day2_guide_target = ""
            self.day2_pasillo_prompt_done = False
            self.day2_fin_active = False
            self.day2_fin_timer_ms = 0
            self.current_mission = "Ir a la escuela"
            self.current_screen = "aventura"
            # Entering HabNoche triggers the day2 chat scene automatically
            self._change_adventure_background("HabNoche (2).png")

        elif day == 3:
            self.current_day = 3
            self.escena_dia1_completada = True
            self.day1_completed = True
            self.escena_dia2_chat_completada = True
            self.escena_dia2_lucas_completada = True
            self.escena_dia3_piscina_completada = False
            self.escena_dia3_cafeteria_completada = False
            self.escena_dia3_pelea_completada = False
            self.day3_guide_target = ""
            self.day3_event_active = ""
            self.day3_fin_active = False
            self.day3_fin_timer_ms = 0
            self.current_screen = "aventura"
            self._change_adventure_background("HabDía.png")
            self._prepare_day3_state()

        audio = getattr(self, "audio", None)
        if audio and getattr(self, "aventura_fondo", None):
            audio.play_ambience_for_map(self.aventura_fondo.ruta_imagen)

    def _toggle_debug_day_menu(self):
        self.debug_day_menu_active = not getattr(self, "debug_day_menu_active", False)
        if not hasattr(self, "debug_day_cursor"):
            self.debug_day_cursor = 0



