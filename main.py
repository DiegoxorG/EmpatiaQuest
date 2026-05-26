
import sys
import os
import pygame

from config import (
    DEFAULT_FPS, CUSTOM_PARTS, PART_STYLES, DEFAULT_CHARACTER_COLORS,
    DEFAULT_SETTINGS, PALETTE_COLORS, STORY_GOAL,
)
from game_state import GameStateMixin
from renderer import RendererMixin
from screen_handlers import ScreenHandlersMixin
from audio_manager import AudioManager
from transition_manager import TransitionManager


class EmpatiaQuestUI(GameStateMixin, RendererMixin, ScreenHandlersMixin):
    """
    Punto de entrada del juego.
    GameStateMixin  — toda la lógica de datos, guardado, historia, habilidades, logros.
    RendererMixin   — todos los métodos _draw_* y _render_current_screen.
    ScreenHandlersMixin — todos los _handle_*_events y _dispatch_event.
    """

    def __init__(self):
        pygame.init()

        # ── Pantalla ──────────────────────────────────────────────────────────
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

        # ── Fuentes ───────────────────────────────────────────────────────────
        self.base_fonts = self._build_fonts()
        self.pixel_scale = {"title": 1, "subtitle": 1, "button": 1, "body": 1, "small": 1}

        # ── Estado de navegación ──────────────────────────────────────────────
        self.running = True
        self.current_screen = "menu"
        self.previous_screen = None
        self.selected_index = 0
        self.selected_play_index = 0
        self.message = ""

        # ── Botones ───────────────────────────────────────────────────────────
        self.button_width = min(460, int(self.width * 0.34))
        self.button_height = 64
        self.button_gap = 18
        self.buttons = self._build_menu_buttons()
        self.play_buttons = self._build_play_buttons()
        self.pause_buttons = self._build_pause_buttons()

        # ── Pausa / guardado ──────────────────────────────────────────────────
        self.pause_selected_index = 0
        self.save_slot_selected = 0
        self.pause_overwrite_pending = False
        self.pause_pending_slot = None

        # ── Personaje y paleta ────────────────────────────────────────────────
        self.custom_parts = CUSTOM_PARTS
        self.part_styles = PART_STYLES
        self.current_style = {k: 0 for k in self.part_styles}
        self.selected_custom_index = 0
        self.selected_slider = 0
        self.palette_colors = PALETTE_COLORS
        self.character_colors = DEFAULT_CHARACTER_COLORS.copy()

        # ── Configuración ─────────────────────────────────────────────────────
        self.settings = DEFAULT_SETTINGS.copy()
        self.setting_keys = list(self.settings.keys())
        self.selected_setting_index = 0
        self.dragging_volume = False

        # ── Controles ─────────────────────────────────────────────────────────
        self.controls = self._build_default_controls()
        self.control_labels = [
            ("Mover arriba",        "mover_arriba"),
            ("Mover abajo",         "mover_abajo"),
            ("Mover izquierda",     "mover_izquierda"),
            ("Mover derecha",       "mover_derecha"),
            ("Interactuar",         "interactuar"),
            ("Guardar partida",     "guardar"),
            ("Continuar dialogo",   "continuar"),
            ("Elegir opcion 1",     "opcion_1"),
            ("Elegir opcion 2",     "opcion_2"),
            ("Elegir opcion 3",     "opcion_3"),
            ("Elegir opcion 4",     "opcion_4"),
            ("Elegir opcion 5",     "opcion_5"),
        ]
        self.selected_control_index = 0
        self.waiting_control_action = None
        self.controls_scroll = 0

        # ── Historia / aventura ───────────────────────────────────────────────
        self.empathy_points = 0
        self.skills_inventory = {}          # relleno en _start_adventure
        self.show_skills_inventory = False
        self.lista_logros = None            # Lista_Logros, creada en _start_adventure
        self.decision_history = []
        self.popup_logro_actual = None
        self.popup_logro_timer = 0
        self.story_felicidad = 50
        self.story_reputacion = 50
        self.story_completed = 0
        self.story_goal = STORY_GOAL
        self.story_thought = ""
        self.story_interaction_text = ""
        self.story_pending_end = False
        self.story_final_key = ""
        self.story_final_text = ""
        self.story_walls = []
        self.story_object_image_cache = {}
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

        # ── Cache de fondo ────────────────────────────────────────────────────
        self.cached_background_scaled = None
        self.cached_background_size = None
        self.cached_background_source = None

        # ── Prólogo ───────────────────────────────────────────────────────────
        self.prologo_activo = False
        self.prologo_paso = 0
        self.prologo_razon = ""
        self.prologo_textos = []

        # ── Ingreso de nombre ─────────────────────────────────────────────────
        self.player_name = ""
        self.nombre_input_text = ""
        self.nombre_input_cursor_visible = True
        self.nombre_input_cursor_timer = 0

        # ── Estado Día 1 ──────────────────────────────────────────────────────
        self.current_day = 1
        self.day1_guide_active = True
        self.day1_salon_entered = False
        self.day1_seq_step = 0          # 0=inactivo 1=pensamiento 2=diego 3=esperar_silla
        self.day1_seating_result = ""   # sentó_con_sara / sentó_con_diego / sentó_solo
        self.day1_in_tarde = False
        self.day1_pupitre_step = 0      # 0=inactivo 1=pensamiento 2=zoom 3=done
        self.day1_pupitre_zoom_active = False
        self.day1_pupitre_erase_surface = None
        self.day1_pupitre_erase_progress = 0.0
        self.day1_pupitre_result = ""
        self.day1_completed = False
        self.day1_end_timer = 0         # ms countdown para "Fin del Día 1"
        self.day1_sara_npc_warned = False
        self.day1_seq_dialog_done = False
        self.day1_intro_step = 0        # 0=primer mensaje 1=segundo mensaje 2=listo
        self.current_mission = ""

        # ── Simulación ────────────────────────────────────────────────────────
        self.simulacion_activa = False
        self.simulacion_personaje = None
        self.simulacion_fondo = None
        self.simulacion_animacion = None
        self.simulacion_pared1 = None
        self.simulacion_pared2 = None
        self.simulacion_aviso = None
        self.simulacion_mostrar_aviso = False

        # ── Archivos de guardado ──────────────────────────────────────────────
        save_dir = os.path.join(os.path.dirname(__file__), "Partidas_Guardadas")
        os.makedirs(save_dir, exist_ok=True)
        self.save_file = os.path.join(save_dir, "partida_guardada.json")
        self.save_slot_files = [
            os.path.join(save_dir, f"partida_slot_{i+1}.json") for i in range(4)
        ]

        # ── Player rect (mundo) ───────────────────────────────────────────────
        self.player_rect = pygame.Rect(self.width // 2 - 10, self.height // 2 - 10, 20, 20)
        self.player_speed = 4
        self.npc_positions = []

        # ── Aventura ──────────────────────────────────────────────────────────
        self.aventura_fondo = None
        self.aventura_personaje = None
        self.next_random_event_ms = 0

        # ── Sistemas nuevos ───────────────────────────────────────────────────
        self.audio = AudioManager()
        self.transitions = TransitionManager()

        # Minijuego Undertale
        self.minijuego_manager = None   # MinigameManager activo, o None

        # ── Carga diferida de assets ──────────────────────────────────────────
        self._load_story_interact_prompt()
        self._load_story_seated_sprite()
        self._load_story_event_npc_sprites()
        self._apply_display_mode()

    # ── Configuración de pantalla (necesita self.screen ya creado) ────────────

    def _apply_display_mode(self):
        if self.settings["Pantalla completa"]:
            self.screen = pygame.display.set_mode(
                (self.display_width, self.display_height), pygame.FULLSCREEN
            )
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

    # ── Loop principal ────────────────────────────────────────────────────────

    def run(self):
        while self.running:
            dt_ms = self.clock.get_time()

            for event in pygame.event.get():
                self._dispatch_event(event)

            # Actualizar lógica de juego
            self._update_adventure()
            self._update_simulacion()
            self._update_minijuego(dt_ms)
            if self.current_screen == "nombre_input":
                self._update_nombre_cursor(dt_ms)

            # Actualizar transición y popup de logro
            self.transitions.update(self, dt_ms)
            self._update_popup_logro(dt_ms)

            # Renderizar
            self._render_current_screen()
            pygame.display.flip()
            self.clock.tick(self.settings["Limite FPS"])

        pygame.quit()
        sys.exit()

    def _update_popup_logro(self, dt_ms):
        """Consume la cola de popups de logros y decrementa el timer."""
        if self.popup_logro_timer > 0:
            self.popup_logro_timer -= dt_ms
            if self.popup_logro_timer <= 0:
                self.popup_logro_timer = 0
                self.popup_logro_actual = None
                # Consumir el siguiente logro de la cola si existe
                lista = getattr(self, "lista_logros", None)
                if lista is not None:
                    siguiente = lista.consumir_popup()
                    if siguiente is not None:
                        self.popup_logro_actual = siguiente
                        self.popup_logro_timer = 3500


if __name__ == "__main__":
    app = EmpatiaQuestUI()
    app.run()
