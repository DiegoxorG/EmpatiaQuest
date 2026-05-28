"""
Mixin de manejo de eventos para EmpatiaQuestUI.
Contiene todos los _handle_*_events y la lógica de navegación entre pantallas.
"""

import os
import pygame
from config import DEFAULT_CONTROLS
import screens.historia as historia_screen
import screens.progreso as progreso_screen
import screens.tutorial as tutorial_screen
import screens.creditos as creditos_screen
from minigame_manager import MinigameManager
from penaltis_manager import PenaltisManager
from atrapa_emociones_manager import AtrapaEmocionesManager
from scene_manager import (
    get_scene_pupitre_borrar_gracias,
    get_scene_pupitre_foto,
    get_scene_pupitre_profesor,
)


class ScreenHandlersMixin:
    """Todos los manejadores de eventos de EmpatiaQuestUI."""

    def _play_hover_once(self, target):
        if getattr(self, "_last_hover_target", None) == target:
            return
        self._last_hover_target = target
        audio = getattr(self, "audio", None)
        if audio is not None:
            audio.sfx_hover()

    def _play_nav_sfx(self):
        audio = getattr(self, "audio", None)
        if audio is not None:
            audio.sfx_hover()

    # ──────────────────────────────────────────────────────────────────────────
    # Acción central — abre pantallas
    # ──────────────────────────────────────────────────────────────────────────

    def _open_action(self, action):
        audio = getattr(self, "audio", None)
        transitions = getattr(self, "transitions", None)

        if audio is not None:
            audio.sfx_click()

        if action == "salir":
            self.running = False
            return
        if action == "jugar":
            self._transition_to("jugar", transitions)
            return
        if action == "partida_nueva":
            self.nombre_input_text = ""
            self.nombre_input_cursor_visible = True
            self.nombre_input_cursor_timer = 0
            self._transition_to("nombre_input", transitions)
            return
        if action == "cargar_partida":
            self.save_slot_selected = 0
            self.pause_overwrite_pending = False
            self.pause_pending_slot = None
            self.message = "Selecciona un slot para cargar o borrar."
            self._transition_to("load_slots", transitions)
            return
        if action == "simulacion":
            self._init_simulacion()
            self._transition_to("simulacion", transitions)
            return
        if action == "pause_guardar":
            self.save_slot_selected = 0
            self.pause_overwrite_pending = False
            self.pause_pending_slot = None
            self.current_screen = "pause_guardar"
            return
        if action == "pause_salir_menu":
            self._transition_to("menu", transitions)
            return
        if action == "volver_menu":
            self._transition_to("menu", transitions)
            return
        if action == "configuracion":
            self.previous_screen = self.current_screen
            self.current_screen = "configuracion"
            return
        if action == "progreso":
            self._transition_to("progreso", transitions)
            return
        if action == "historia":
            self._transition_to("historia", transitions)
            return
        if action == "tutorial":
            self._transition_to("tutorial", transitions)
            return
        if action == "creditos":
            self._transition_to("creditos", transitions)
            return
        # Fallback genérico
        self._transition_to(action, transitions)
        self.message = f"Pantalla {action} abierta"

    def _transition_to(self, screen_name, transitions=None):
        """Cambia de pantalla con fade si el TransitionManager está disponible."""
        if transitions is not None and transitions.is_idle():
            transitions.request(self, screen_name)
        else:
            self.current_screen = screen_name
        audio = getattr(self, "audio", None)
        if audio is not None:
            audio.play_bgm_for_screen(screen_name)

    # ──────────────────────────────────────────────────────────────────────────
    # Menú principal
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_menu_events(self, event):
        if event.type == pygame.MOUSEMOTION:
            for i, button in enumerate(self.buttons):
                if button.contains(event.pos):
                    self._play_hover_once(("menu", i))
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
                self._play_nav_sfx()
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % len(self.buttons)
                self._play_nav_sfx()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._open_action(self.buttons[self.selected_index].action)

    # ──────────────────────────────────────────────────────────────────────────
    # Pausa
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_pause_events(self, event):
        if event.type == pygame.MOUSEMOTION:
            for i, button in enumerate(self.pause_buttons):
                if button.contains(event.pos):
                    self._play_hover_once(("pause", i))
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
                self._play_nav_sfx()
            elif event.key == pygame.K_UP:
                self.pause_selected_index = (self.pause_selected_index - 1) % len(self.pause_buttons)
                self._play_nav_sfx()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._open_action(self.pause_buttons[self.pause_selected_index].action)

    # ──────────────────────────────────────────────────────────────────────────
    # Guardar / Cargar slots
    # ──────────────────────────────────────────────────────────────────────────

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
                self._play_nav_sfx()
                return
            elif event.key == pygame.K_UP:
                self.save_slot_selected = (self.save_slot_selected - 1) % 5
                self._play_nav_sfx()
                return
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.save_slot_selected < 4:
                    if self._save_slot_exists(self.save_slot_selected):
                        self.pause_overwrite_pending = True
                        self.pause_pending_slot = self.save_slot_selected
                        self.message = f"Slot {self.save_slot_selected + 1} ya existe. ENTER para sobrescribir."
                    else:
                        saved = self._save_to_slot(self.save_slot_selected)
                        if saved:
                            audio = getattr(self, "audio", None)
                            if audio is not None:
                                audio.sfx_guardar()
                        self.message = (
                            f"Guardado en Slot {self.save_slot_selected + 1}."
                            if saved else "No se pudo guardar la partida."
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
                        if saved:
                            audio = getattr(self, "audio", None)
                            if audio is not None:
                                audio.sfx_guardar()
                        self.message = (
                            f"Guardado en Slot {i + 1}."
                            if saved else "No se pudo guardar la partida."
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
        self.message = (
            f"Slot {self.pause_pending_slot + 1} sobrescrito."
            if saved else "No se pudo guardar la partida."
        )
        self.pause_overwrite_pending = False
        self.pause_pending_slot = None
        audio = getattr(self, "audio", None)
        if audio is not None:
            audio.sfx_guardar()

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
                self._play_nav_sfx()
                return
            elif event.key == pygame.K_UP:
                self.save_slot_selected = (self.save_slot_selected - 1) % 5
                self._play_nav_sfx()
                return
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.save_slot_selected < 4:
                    if self._save_slot_exists(self.save_slot_selected):
                        if self._load_slot(self.save_slot_selected):
                            self.current_screen = "aventura"
                            self.message = f"Slot {self.save_slot_selected + 1} cargado."
                            audio = getattr(self, "audio", None)
                            if audio is not None:
                                audio.sfx_decision()
                                if getattr(self, "aventura_fondo", None) is not None:
                                    audio.play_ambience_for_map(self.aventura_fondo.ruta_imagen)
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
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_error() if not deleted else audio.sfx_decision()
                    self.message = (
                        f"Slot {self.save_slot_selected + 1} borrado."
                        if deleted else "No se pudo borrar el slot."
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
                            audio = getattr(self, "audio", None)
                            if audio is not None:
                                audio.sfx_decision()
                                if getattr(self, "aventura_fondo", None) is not None:
                                    audio.play_ambience_for_map(self.aventura_fondo.ruta_imagen)
                        else:
                            self.message = "No se pudo cargar la partida."
                    else:
                        self.message = "Slot vacio. Usa ENTER para cargar otro slot."
                    return
            back_rect = pygame.Rect(panel.x + panel.width // 2 - 120, panel.bottom - 90, 240, 52)
            if back_rect.collidepoint(event.pos):
                self.current_screen = "menu"
                return

    # ──────────────────────────────────────────────────────────────────────────
    # Pantalla Jugar
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_play_events(self, event):
        if event.type == pygame.MOUSEMOTION:
            for i, button in enumerate(self.play_buttons):
                if button.contains(event.pos):
                    self._play_hover_once(("jugar", i))
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
                self._play_nav_sfx()
            elif event.key == pygame.K_UP:
                self.selected_play_index = (self.selected_play_index - 1) % len(self.play_buttons)
                self._play_nav_sfx()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._open_action(self.play_buttons[self.selected_play_index].action)

    # ──────────────────────────────────────────────────────────────────────────
    # CAMBIO 1 — Ingreso de nombre
    # ──────────────────────────────────────────────────────────────────────────

    def _update_nombre_cursor(self, dt_ms):
        self.nombre_input_cursor_timer += dt_ms
        if self.nombre_input_cursor_timer >= 530:
            self.nombre_input_cursor_timer = 0
            self.nombre_input_cursor_visible = not self.nombre_input_cursor_visible

    def _handle_nombre_input_events(self, event):
        if event.type == pygame.KEYDOWN:
            text = getattr(self, "nombre_input_text", "")
            if event.key == pygame.K_BACKSPACE:
                self.nombre_input_text = text[:-1]
                audio = getattr(self, "audio", None)
                if audio is not None:
                    audio.sfx_error()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                name = text.strip()
                if name:
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
                    self.player_name = name
                    self._start_adventure()
                    transitions = getattr(self, "transitions", None)
                    self._transition_to("prologo", transitions)
            elif event.key == pygame.K_ESCAPE:
                transitions = getattr(self, "transitions", None)
                self._transition_to("jugar", transitions)
            # Caracteres: manejados SOLO por TEXTINPUT para evitar duplicados
        if event.type == pygame.TEXTINPUT:
            text = getattr(self, "nombre_input_text", "")
            for char in event.text:
                if (char.isalpha() or char.isspace() or char.isdigit()) and len(text) < 20:
                    text += char
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_dialogo()
            self.nombre_input_text = text

    # ──────────────────────────────────────────────────────────────────────────
    # Creador de personaje
    # ──────────────────────────────────────────────────────────────────────────

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
                    self._play_nav_sfx()
                    return
            for idx, color in enumerate(self.palette_colors):
                r = idx // palette_cols
                c = idx % palette_cols
                x = left_x + c * (sw + gap)
                y = palette_top + r * (sw + gap)
                rect = pygame.Rect(x, y, sw, sw)
                if rect.collidepoint(event.pos):
                    self.character_colors[self._selected_part()] = color
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
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
                    self._play_nav_sfx()
                    return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_custom_index = (self.selected_custom_index + 1) % len(self.custom_parts)
                self._play_nav_sfx()
            elif event.key == pygame.K_UP:
                self.selected_custom_index = (self.selected_custom_index - 1) % len(self.custom_parts)
                self._play_nav_sfx()
            elif event.key == pygame.K_a:
                self._change_part_style(-1)
                self._play_nav_sfx()
            elif event.key == pygame.K_d:
                self._change_part_style(1)
                self._play_nav_sfx()
            elif event.key == pygame.K_TAB:
                self.selected_slider = (self.selected_slider + 1) % 3
                self._play_nav_sfx()
            elif event.key == pygame.K_LEFT:
                self._change_selected_color_channel(self.selected_slider, -5)
                self._play_nav_sfx()
            elif event.key == pygame.K_RIGHT:
                self._change_selected_color_channel(self.selected_slider, 5)
                self._play_nav_sfx()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.message = "Personaje guardado. Listo para comenzar."
                audio = getattr(self, "audio", None)
                if audio is not None:
                    audio.sfx_decision()
                self._start_adventure()
                self.current_screen = "prologo"

    # ──────────────────────────────────────────────────────────────────────────
    # Prólogo
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_prologo_events(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            audio = getattr(self, "audio", None)
            if audio is not None:
                audio.sfx_dialogo()
            # Save current frame as the one to fade out from
            frames = getattr(self, "prologo_frames", [])
            if frames:
                cur_idx = min(self.prologo_paso, len(frames) - 1)
                self.prologo_frame_from = frames[cur_idx]
                self.prologo_fade_start_ms = pygame.time.get_ticks()
            self.prologo_paso += 1
            if self.prologo_paso >= len(self.prologo_textos):
                self.prologo_activo = False
                transitions = getattr(self, "transitions", None)
                def _after_fade():
                    if audio is not None:
                        audio.play_bgm_for_screen("aventura")
                        if hasattr(self, "_sync_scene_audio"):
                            self._sync_scene_audio()
                if transitions is not None and transitions.is_idle():
                    transitions.request(self, "aventura",
                                        callback=_after_fade,
                                        duration_ms=1400)
                else:
                    _after_fade()
                    self.current_screen = "aventura"

    # ──────────────────────────────────────────────────────────────────────────
    # Aventura (movimiento + decisiones + TAB)
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_adventure_events(self, event):
        # ── Intro cinematográfica: bloquea todo input hasta que el jugador avance ──
        intro_step = getattr(self, "day1_intro_step", 2)
        if intro_step < 2:
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER
            ):
                self.day1_intro_step = intro_step + 1
                audio = getattr(self, "audio", None)
                if audio is not None:
                    audio.sfx_dialogo()
            return

        # ── Day 5: dodge minigame intercepts all input ───────────────────────
        if getattr(self, "day5_pelea_active", False):
            mgr5 = getattr(self, "day5_pelea_mgr", None)
            if mgr5 is not None:
                mgr5.handle_event(event)
            return

        # ── SceneManager: interceptar eventos cuando hay escena activa ─────────
        if getattr(self, "escena_activa", None) is not None:
            sm = getattr(self, "scene_manager", None)
            if sm is not None:
                if sm.handle_input(event):
                    return
                # Bloquear la tecla E (interactuar) durante DialogBeats
                if (event.type == pygame.KEYDOWN
                        and event.key == self.controls.get("interactuar", pygame.K_e)
                        and sm.is_blocking_interaction):
                    return
            # Bloquear el avance del viejo day1_seq_step mientras la escena está activa
            if event.type == pygame.KEYDOWN:
                seq = getattr(self, "day1_seq_step", 0)
                if seq in (1, 2) and event.key in (
                    pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER,
                    self.controls.get("continuar", pygame.K_RETURN),
                ):
                    return

        # ── Borrador: solo activo si el jugador presionó A primero ───────────
        if (getattr(self, "day1_pupitre_zoom_active", False)
                and getattr(self, "day1_pupitre_step", 0) == 2
                and getattr(self, "day1_pupitre_erase_mode", False)):
            erase_surf = getattr(self, "day1_pupitre_erase_surface", None)
            if erase_surf is not None and pygame.mouse.get_pressed()[0]:
                mx, my = pygame.mouse.get_pos()
                pygame.draw.circle(erase_surf, (0, 0, 0, 0), (mx, my), 28)
                audio = getattr(self, "audio", None)
                if audio is not None:
                    audio.sfx_borrar()
                # Calcular progreso: muestrear puntos para estimar área borrada
                sample_step = 40
                total = 0
                erased = 0
                try:
                    pix = pygame.PixelArray(erase_surf)
                    for sx in range(0, erase_surf.get_width(), sample_step):
                        for sy in range(0, erase_surf.get_height(), sample_step):
                            total += 1
                            alpha = erase_surf.get_at((sx, sy))[3]
                            if alpha < 10:
                                erased += 1
                    del pix
                except Exception:
                    pass
                if total > 0:
                    self.day1_pupitre_erase_progress = erased / total
                # Si 100% borrado → cerrar borrador, restaurar cursor y lanzar escena
                if self.day1_pupitre_erase_progress >= 1.0:
                    self.day1_pupitre_erase_mode  = False
                    pygame.mouse.set_visible(True)
                    pname = getattr(self, "player_name", "") or "Protagonista"
                    self.story_thought = f"{pname}: Listo, ya no se ven esos mensajes."
                    self.story_felicidad = max(0, min(100, self.story_felicidad + 1))
                    self.day1_pupitre_zoom_active = False
                    self.day1_pupitre_step = 3
                    self.day1_pupitre_result = "borrar"
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
                    # ── Lanzar escena de agradecimiento de Sara ──────────────
                    self.scene_manager = get_scene_pupitre_borrar_gracias(pname)
                    self.escena_activa = "pupitre_borrar_gracias"
                    self.player_can_move = True

        if event.type == pygame.KEYDOWN:
            if getattr(self, "day3_choice_menu_active", False):
                context = getattr(self, "day3_choice_context", "")
                mappings = {
                    "piscina": {
                        pygame.K_a: "participar",
                        pygame.K_b: "negarse",
                        pygame.K_c: "detener",
                        pygame.K_d: "irse",
                    },
                    "cafeteria": {
                        pygame.K_a: "defender",
                        pygame.K_b: "ignorar",
                        pygame.K_c: "apoyar",
                        pygame.K_d: "ayuda",
                    },
                    "pelea": {
                        pygame.K_a: "separar",
                        pygame.K_b: "profesor",
                        pygame.K_c: "foto",
                        pygame.K_d: "ignorar",
                    },
                }
                choice = mappings.get(context, {}).get(event.key)
                if choice is not None:
                    self.day3_choice = choice
                    self.day3_choice_menu_active = False
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
                    return

            if getattr(self, "day4_choice_menu_active", False):
                context = getattr(self, "day4_choice_context", "")
                mappings = {
                    "azotea": {
                        pygame.K_a: "defender",
                        pygame.K_b: "diego",
                        pygame.K_c: "ignorar",
                        pygame.K_d: "reirse",
                    },
                    "biblioteca": {
                        pygame.K_a: "sara",
                        pygame.K_b: "diego",
                        pygame.K_c: "incluir",
                    },
                    "rumores": {
                        pygame.K_a: "acompanar",
                        pygame.K_b: "defender",
                        pygame.K_c: "compartir",
                        pygame.K_d: "juzgar",
                    },
                }
                choice = mappings.get(context, {}).get(event.key)
                if choice is not None:
                    self.day4_choice = choice
                    self.day4_choice_menu_active = False
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
                    return

            if getattr(self, "day5_choice_menu_active", False):
                context = getattr(self, "day5_choice_context", "")
                mappings = {
                    "pasillo_dia5": {
                        pygame.K_a: "sara",
                        pygame.K_b: "diego",
                    },
                    "sara_azotea": {
                        pygame.K_a: "escuchar",
                        pygame.K_b: "ayuda",
                        pygame.K_c: "minimizar",
                        pygame.K_d: "irse",
                    },
                    "diego_trasera": {
                        pygame.K_a: "detener",
                        pygame.K_b: "enfrentar",
                        pygame.K_c: "ayuda",
                        pygame.K_d: "ignorar",
                    },
                }
                choice = mappings.get(context, {}).get(event.key)
                if choice is not None:
                    self.day5_choice = choice
                    self.day5_choice_menu_active = False
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
                    return

            if getattr(self, "day2_chat_choice_menu_active", False):
                mapping = {
                    pygame.K_1: ("defender", "ME.Defender.png"),
                    pygame.K_2: ("reportar", "M3-Reportar.png"),
                    pygame.K_3: ("ignorar", "Me-CerrarChat.png"),
                    pygame.K_4: ("reenviar", "M3-reenviar.png"),
                    pygame.K_5: ("psicologo", "M3-Psicologo.png"),
                }
                choice_data = mapping.get(event.key)
                if choice_data is not None:
                    choice, overlay_name = choice_data
                    self.day2_chat_pending_choice = choice
                    self.day2_chat_choice = ""
                    overlay_path = self._resolve_image_path(overlay_name)
                    self.day2_chat_overlay_image = overlay_path if os.path.exists(overlay_path) else None
                    self.day2_chat_overlay_until_ms = 1500
                    self.day2_chat_choice_menu_active = False
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
                    return

            if getattr(self, "day2_lucas_choice_menu_active", False):
                mapping = {
                    pygame.K_a: "consolar",
                    pygame.K_b: "preguntar",
                    pygame.K_c: "ignorar",
                    pygame.K_d: "minimizar",
                }
                choice = mapping.get(event.key)
                if choice is not None:
                    self.day2_lucas_choice = choice
                    self.day2_lucas_choice_menu_active = False
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
                    return

            # ── Confirmación de minijuego (S = jugar, N = no jugar) ──────────
            if getattr(self, "minijuego_confirm_active", False):
                if event.key == pygame.K_s:
                    self.minijuego_confirm = "si"
                    self.minijuego_confirm_active = False
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
                    return
                elif event.key == pygame.K_n:
                    self.minijuego_confirm = "no"
                    self.minijuego_confirm_active = False
                    return

            # ── CAMBIO 3: Avance de diálogos Día 1 ───────────────────────────
            seq = getattr(self, "day1_seq_step", 0)
            if seq in (1, 2):
                if event.key in (self.controls.get("continuar", pygame.K_RETURN),
                                 pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    self.day1_seq_step = seq + 1
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_dialogo()
                    return

            # ── CAMBIO 4: pupitre paso 1 → zoom con E ────────────────────────
            pupitre_step = getattr(self, "day1_pupitre_step", 0)
            if pupitre_step == 1:
                if event.key == self.controls.get("interactuar", pygame.K_e):
                    self.day1_pupitre_step = 2
                    self.day1_pupitre_zoom_active = True
                    # Crear superficie borradora con los rayones
                    erase_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                    scratch_img_path = self._resolve_image_path("letras.png")
                    # 🖼️ ASSET_IMG: Imagenes/Interactuables/PupitreRayones.png | 1280x720 | Capa PNG con insultos encima del pupitre
                    try:
                        raw = pygame.image.load(scratch_img_path).convert_alpha()
                        erase_surf.blit(pygame.transform.scale(raw, (self.width, self.height)), (0, 0))
                    except (OSError, pygame.error):
                        erase_surf.fill((80, 40, 40, 160))
                    self.day1_pupitre_erase_surface  = erase_surf
                    self.day1_pupitre_erase_progress = 0.0
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.play_decision_bgm()
                        audio.play_sfx("pupitre_alerta")
                    return

            # ── CAMBIO 4: teclas A/B/C/D en zoom pupitre ─────────────────────
            if getattr(self, "day1_pupitre_zoom_active", False) and pupitre_step == 2:
                pname = getattr(self, "player_name", "") or "Protagonista"
                if event.key == pygame.K_a:
                    # [A] Activar modo borrador — el cursor cambia a Borradortab.png
                    if not getattr(self, "day1_pupitre_erase_mode", False):
                        self.day1_pupitre_erase_mode = True
                        self.story_thought = f"{pname}: Voy a borrar esto."
                        pygame.mouse.set_visible(False)   # ocultamos el cursor del sistema
                        audio = getattr(self, "audio", None)
                        if audio is not None:
                            audio.sfx_borrar()
                    return
                elif event.key == pygame.K_b:
                    # [B] Ignorar — F-3, R+0
                    self.story_thought = f"{pname}: Mejor no meterme en esto."
                    self.story_felicidad = max(0, min(100, self.story_felicidad - 3))
                    self.day1_pupitre_erase_mode  = False   # restaurar cursor
                    pygame.mouse.set_visible(True)
                    self.day1_pupitre_zoom_active  = False
                    self.day1_pupitre_step         = 3
                    self.day1_pupitre_result       = "ignorar"
                    self.pupitre_rayado_completado = True
                    self.current_mission           = "Volver a casa"
                    self.decision_history.append({
                        "event_id":     "dia1_pupitre_rayado",
                        "option_label": "ignorar",
                        "dF": -3, "dR": 0,
                        "thought": "Ignoré los insultos en el pupitre de Sara.",
                    })
                    self.player_can_move = True
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_error()
                    return
                elif event.key == pygame.K_c:
                    # [C] Tomar foto — F-5, R+1
                    self.story_thought = f"{pname}: Voy a documentar esto."
                    self.story_felicidad  = max(0, min(100, self.story_felicidad  - 5))
                    self.story_reputacion = max(0, min(100, self.story_reputacion + 1))
                    self.day1_pupitre_erase_mode  = False   # restaurar cursor
                    pygame.mouse.set_visible(True)
                    self.day1_pupitre_zoom_active  = False
                    self.day1_pupitre_step         = 3
                    self.day1_pupitre_result       = "foto"
                    self.pupitre_rayado_foto_active = True
                    self.pupitre_rayado_foto_timer  = 800   # ms de flash blanco
                    # Bug-8: mostrar Mision3-TomarFoto.png a pantalla completa (1800ms)
                    self.mision3_foto_overlay_active = True
                    self.mision3_foto_overlay_ms     = 1800
                    # 🎵 ASSET_SFX: Audio/SFX/camara_foto.ogg | Sonido de shutter de cámara
                    audio = getattr(self, "audio", None)
                    if audio:
                        audio.sfx_camara()
                    # ── Lanzar escena de reacción de Sara ────────────────────
                    self.scene_manager = get_scene_pupitre_foto(pname)
                    self.escena_activa = "pupitre_foto"
                    self.player_can_move = True
                    return
                elif event.key == pygame.K_d:
                    # [D] Llamar a la profesora — F+2, R+1
                    self.story_thought = f"{pname}: ¡Profe, venga a ver esto!"
                    self.story_felicidad  = max(0, min(100, self.story_felicidad  + 2))
                    self.story_reputacion = max(0, min(100, self.story_reputacion + 1))
                    self.day1_pupitre_erase_mode = False    # restaurar cursor
                    pygame.mouse.set_visible(True)
                    self.day1_pupitre_zoom_active = False
                    self.day1_pupitre_step        = 3
                    self.day1_pupitre_result      = "profesor"
                    # Bug-9: mostrar Mision3-Llamarprofe.png durante TODA la conversación.
                    # ms=0 → sin timer automático; la escena lo apaga en beat_completar.
                    self.mision3_llamar_profe_active = True
                    self.mision3_llamar_profe_ms     = 0
                    # ── Lanzar escena del profesor ───────────────────────────
                    self.scene_manager = get_scene_pupitre_profesor(pname)
                    self.escena_activa = "pupitre_profesor"
                    self.player_can_move = True
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_decision()
                    return
                elif event.key == pygame.K_ESCAPE:
                    # ESC = ignorar (fallback, mismos efectos que [B])
                    self.story_thought = f"{pname}: Mejor no meterme en esto."
                    self.story_felicidad = max(0, min(100, self.story_felicidad - 3))
                    self.day1_pupitre_erase_mode  = False   # restaurar cursor
                    pygame.mouse.set_visible(True)
                    self.day1_pupitre_zoom_active  = False
                    self.day1_pupitre_step         = 3
                    self.day1_pupitre_result       = "ignorar"
                    self.pupitre_rayado_completado = True
                    self.current_mission           = "Volver a casa"
                    self.decision_history.append({
                        "event_id":     "dia1_pupitre_rayado",
                        "option_label": "ignorar",
                        "dF": -3, "dR": 0,
                        "thought": "Ignoré los insultos en el pupitre de Sara.",
                    })
                    self.player_can_move = True
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_error()
                    return

            # TAB — panel de habilidades
            if event.key == pygame.K_TAB:
                self.show_skills_inventory = not getattr(self, "show_skills_inventory", False)
                self._play_nav_sfx()
                return

            if event.key == self.controls["interactuar"] and not self.story_pending_end:
                if self.story_is_seated:
                    self._toggle_seat_state(None)
                    return
                interactable = self._get_player_interactable()
                if interactable is not None:
                    self._execute_interactable_action(interactable)
                else:
                    self.story_interaction_text = "No hay nada interactuable aqui."
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_error()
                return

            if event.key == self.controls["guardar"]:
                audio = getattr(self, "audio", None)
                ok = self._save_game()
                if ok and audio is not None:
                    audio.sfx_guardar()
                self.message = "Partida guardada." if ok else "No se pudo guardar la partida."
                return

            if self.story_pending_end:
                if event.key in (self.controls["continuar"], pygame.K_SPACE, pygame.K_KP_ENTER):
                    transitions = getattr(self, "transitions", None)
                    self._transition_to("menu", transitions)
                return


    # ──────────────────────────────────────────────────────────────────────────
    # Configuración
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_settings_events(self, event):
        panel, row_h, row_x, row_w, start_y, _ = self._settings_layout()

        volume_keys = ("Musica", "Efectos de sonido")

        def volume_bar_rect(key=None):
            if key is None:
                key = self.setting_keys[self.selected_setting_index]
            idx = self.setting_keys.index(key)
            row = pygame.Rect(row_x, start_y + idx * row_h, row_w, 50)
            bar_w = 260
            bar_h = 16
            bar_x = row.right - bar_w - 24
            bar_y = row.centery - bar_h // 2
            return pygame.Rect(bar_x, bar_y, bar_w, bar_h)

        def set_volume_from_x(mouse_x, key=None):
            if key is None:
                key = getattr(self, "dragging_volume_key", None) or self.setting_keys[self.selected_setting_index]
            if key not in volume_keys:
                return
            bar = volume_bar_rect(key)
            rel_x = max(0, min(bar.width, mouse_x - bar.x))
            self.settings[key] = int((rel_x / bar.width) * 100)
            audio = getattr(self, "audio", None)
            if audio is not None:
                if key == "Musica":
                    audio.apply_music_volume(self.settings[key])
                else:
                    audio.apply_sfx_volume(self.settings[key])

        if event.type == pygame.MOUSEMOTION:
            for i in range(len(self.setting_keys)):
                row = pygame.Rect(row_x, start_y + i * row_h, row_w, 50)
                if row.collidepoint(event.pos):
                    self._play_hover_once(("settings", i))
                    self.selected_setting_index = i
                    break
            if self.dragging_volume:
                set_volume_from_x(event.pos[0])

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key in volume_keys:
                if key in self.setting_keys and volume_bar_rect(key).collidepoint(event.pos):
                    self.selected_setting_index = self.setting_keys.index(key)
                    self.dragging_volume = True
                    self.dragging_volume_key = key
                    set_volume_from_x(event.pos[0], key)
                    return
            controls_row = pygame.Rect(row_x, start_y + len(self.setting_keys) * row_h, row_w, 50)
            if controls_row.collidepoint(event.pos):
                self.current_screen = "controles"
                self.selected_control_index = 0
                self.waiting_control_action = None
                audio = getattr(self, "audio", None)
                if audio is not None:
                    audio.sfx_click()
                return
            for i in range(len(self.setting_keys)):
                row = pygame.Rect(row_x, start_y + i * row_h, row_w, 50)
                if row.collidepoint(event.pos):
                    self.selected_setting_index = i
                    self._change_setting(1)
                    return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_volume = False
            self.dragging_volume_key = None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_setting_index = (self.selected_setting_index + 1) % len(self.setting_keys)
                self._play_nav_sfx()
            elif event.key == pygame.K_UP:
                self.selected_setting_index = (self.selected_setting_index - 1) % len(self.setting_keys)
                self._play_nav_sfx()
            elif event.key == pygame.K_LEFT:
                self._change_setting(-1)
            elif event.key == pygame.K_RIGHT:
                self._change_setting(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._change_setting(1)

    # ──────────────────────────────────────────────────────────────────────────
    # Controles (reasignación de teclas)
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_controls_events(self, event):
        panel, row_h, row_x, row_w, start_y, list_bottom = self._controls_layout()
        self._clamp_controls_scroll()

        if self.waiting_control_action is not None and event.type == pygame.KEYDOWN:
            self._rebind_control(self.waiting_control_action, event.key)
            audio = getattr(self, "audio", None)
            if audio is not None:
                audio.sfx_decision()
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
                    self._play_hover_once(("controls", i))
                    self.selected_control_index = i
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._controls_reset_button_rect().collidepoint(event.pos):
                self.controls = self._build_default_controls()
                self.waiting_control_action = None
                audio = getattr(self, "audio", None)
                if audio is not None:
                    audio.sfx_decision()
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
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_click()
                    return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_control_index = (self.selected_control_index + 1) % len(self.control_labels)
                self._ensure_selected_control_visible()
                self._play_nav_sfx()
            elif event.key == pygame.K_UP:
                self.selected_control_index = (self.selected_control_index - 1) % len(self.control_labels)
                self._ensure_selected_control_visible()
                self._play_nav_sfx()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                _, action = self.control_labels[self.selected_control_index]
                self.waiting_control_action = action
                audio = getattr(self, "audio", None)
                if audio is not None:
                    audio.sfx_click()

    # ──────────────────────────────────────────────────────────────────────────
    # Simulación
    # ──────────────────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────────────────
    # Loop principal de eventos
    # ──────────────────────────────────────────────────────────────────────────

    def _dispatch_event(self, event):
        """Despacha un evento al handler correcto según current_screen."""
        if event.type == pygame.QUIT:
            self.running = False
            return

        # ESC global
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._handle_escape()
            return

        # F4 — debug day-select menu
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
            self._toggle_debug_day_menu()
            return

        # Debug day-select menu intercepts navigation when active
        if getattr(self, "debug_day_menu_active", False) and event.type == pygame.KEYDOWN:
            _days = [1, 2, 3, 4, 5]
            if event.key in (pygame.K_UP, pygame.K_w):
                self.debug_day_cursor = (self.debug_day_cursor - 1) % len(_days)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.debug_day_cursor = (self.debug_day_cursor + 1) % len(_days)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                day = _days[self.debug_day_cursor]
                self.debug_day_menu_active = False
                self._debug_jump_to_day(day)
            return


        screen = self.current_screen
        if screen == "menu":
            self._handle_menu_events(event)
        elif screen == "jugar":
            self._handle_play_events(event)
        elif screen == "nombre_input":
            self._handle_nombre_input_events(event)
        elif screen == "creador":
            self._handle_creator_events(event)
        elif screen == "prologo":
            self._handle_prologo_events(event)
        elif screen == "configuracion":
            self._handle_settings_events(event)
        elif screen == "controles":
            self._handle_controls_events(event)
        elif screen == "pause":
            self._handle_pause_events(event)
        elif screen == "pause_guardar":
            self._handle_pause_save_events(event)
        elif screen == "load_slots":
            self._handle_load_events(event)
        elif screen == "simulacion":
            self._handle_simulacion_events(event)
        elif screen == "aventura":
            self._handle_adventure_events(event)
        elif screen == "minijuego":
            self._handle_minijuego_events(event)
        elif screen == "historia":
            historia_screen.handle_event(self, event)
        elif screen == "progreso":
            progreso_screen.handle_event(self, event)
        elif screen == "tutorial":
            tutorial_screen.handle_event(self, event)
        elif screen == "creditos":
            creditos_screen.handle_event(self, event)

    # ──────────────────────────────────────────────────────────────────────────
    # Minijuego estilo Undertale
    # ──────────────────────────────────────────────────────────────────────────

    # Opciones del menú de pausa del minijuego
    _MINIJUEGO_PAUSE_OPTIONS = [
        "Continuar",
        "Ver hitboxes: OFF",
        "Configuracion",
        "Volver a la historia",
    ]

    def _trigger_minijuego(self, tipo: str):
        """
        Inicia el minijuego del tipo dado.
        Tipos soportados:
          "agresivo"        → MinigameManager (Undertale — puñetazos)
          "pacifico"        → MinigameManager (Undertale — mensajes)
          "penaltis"        → PenaltisManager (minijuego de penaltis)
          "atrapa_emociones"→ AtrapaEmocionesManager (minijuego de emociones)
        """
        audio = getattr(self, "audio", None)

        if tipo == "penaltis":
            self.minijuego_manager = PenaltisManager(
                self.width, self.height, audio)
            bgm = "minijuego_penaltis"
            sfx = "balon_disparo"
        elif tipo == "atrapa_emociones":
            self.minijuego_manager = AtrapaEmocionesManager(
                self.width, self.height, audio)
            bgm = "minijuego_emociones"
            sfx = "decision_tomada"
        else:
            # Undertale-style (agresivo / pacifico)
            self.minijuego_manager = MinigameManager(
                tipo, self.width, self.height, audio)
            bgm = "minijuego_batalla"
            sfx = "oleada"

        self.minijuego_pending_tipo  = tipo
        self.minijuego_paused        = False
        self.minijuego_pause_idx     = 0
        self.minijuego_show_hitboxes = False
        self.current_screen          = "minijuego"

        if audio is not None and hasattr(audio, "play_bgm"):
            try:
                audio.play_bgm(bgm)
                audio.stop_ambience()
                audio.play_sfx(sfx)
            except Exception:
                pass

    def _minijuego_pause_options(self):
        """Devuelve la lista de opciones con el estado actual de hitboxes."""
        hb_state = "ON" if getattr(self, "minijuego_show_hitboxes", False) else "OFF"
        return [
            "Continuar",
            f"Ver hitboxes: {hb_state}",
            "Configuracion",
            "Volver a la historia",
        ]

    def _handle_minijuego_events(self, event):
        """Delega eventos al MinigameManager activo o al menú de pausa."""
        mgr = getattr(self, "minijuego_manager", None)
        if mgr is None:
            return

        paused = getattr(self, "minijuego_paused", False)

        if event.type == pygame.KEYDOWN:
            if paused:
                opts = self._minijuego_pause_options()
                idx  = getattr(self, "minijuego_pause_idx", 0)

                if event.key in (pygame.K_UP, pygame.K_w):
                    self.minijuego_pause_idx = (idx - 1) % len(opts)
                    self._play_nav_sfx()
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.minijuego_pause_idx = (idx + 1) % len(opts)
                    self._play_nav_sfx()
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_click()
                    self._minijuego_pause_select(idx)
            else:
                mgr.handle_event(event)

    def _minijuego_pause_select(self, idx: int):
        """Ejecuta la opción seleccionada en el menú de pausa del minijuego."""
        mgr = getattr(self, "minijuego_manager", None)

        if idx == 0:  # Continuar
            self.minijuego_paused = False
            audio = getattr(self, "audio", None)
            if audio is not None:
                audio.sfx_pausa()

        elif idx == 1:  # Ver hitboxes toggle
            self.minijuego_show_hitboxes = not getattr(self, "minijuego_show_hitboxes", False)
            audio = getattr(self, "audio", None)
            if audio is not None:
                audio.sfx_decision()

        elif idx == 2:  # Configuracion
            self.minijuego_paused = False
            self.previous_screen = "minijuego"
            self.current_screen = "configuracion"

        elif idx == 3:  # Volver a la historia
            tipo = getattr(self, "minijuego_pending_tipo", "agresivo")
            if mgr is not None:
                self._handle_minijuego_result({"gano": False, "tipo": tipo})

    def _update_minijuego(self, dt_ms: int):
        """
        Llamado cada frame desde main.run().
        Actualiza el minijuego y, si terminó, aplica efectos y logros.
        Congela la lógica cuando está en pausa.
        """
        if self.current_screen != "minijuego":
            return
        if getattr(self, "minijuego_paused", False):
            return  # lógica congelada durante pausa
        mgr = getattr(self, "minijuego_manager", None)
        if mgr is None:
            self.current_screen = "aventura"
            return

        result = mgr.update(dt_ms)
        if result is not None:
            self._handle_minijuego_result(result)

    def _handle_minijuego_result(self, result: dict):
        """Aplica stats, desbloquea logros y regresa a aventura."""
        mgr = getattr(self, "minijuego_manager", None)
        if mgr is not None:
            if "vidas_restantes" not in result and hasattr(mgr, "vidas"):
                result["vidas_restantes"] = getattr(mgr, "vidas", 0)
            if "vidas_max" not in result:
                if hasattr(mgr, "max_lives"):
                    result["vidas_max"] = getattr(mgr, "max_lives", 0)
                elif hasattr(mgr, "vidas"):
                    result["vidas_max"] = 3
            if "goles" not in result and hasattr(mgr, "goles"):
                result["goles"] = getattr(mgr, "goles", 0)
            if "puntos" not in result and hasattr(mgr, "puntos"):
                result["puntos"] = getattr(mgr, "puntos", 0)
        gano  = result.get("gano", result.get("ganó", False))
        tipo  = result.get("tipo", getattr(self, "minijuego_pending_tipo", "agresivo"))
        lista = getattr(self, "lista_logros", None)
        if lista is not None and hasattr(lista, "register_minigame_result"):
            context = (
                getattr(self, "day3_pending_minigame_context", "")
                or getattr(self, "day4_pending_minigame_context", "")
                or getattr(self, "minijuego_pending_tipo", "")
            )
            normalized = dict(result)
            normalized["gano"] = bool(gano)
            normalized["tipo"] = tipo
            lista.register_minigame_result(normalized, context)

        if getattr(self, "day3_pending_minigame_context", ""):
            self.day3_minigame_result = {"gano": bool(gano), "tipo": tipo}
            self.day3_pending_minigame_context = ""
            if bool(gano) and tipo == "pacifico":
                lista = getattr(self, "lista_logros", None)
                if lista is not None:
                    lista.desbloquear("irrefutable")
                    if getattr(self, "popup_logro_timer", 0) <= 0:
                        siguiente = lista.consumir_popup()
                        if siguiente is not None:
                            self.popup_logro_actual = siguiente
                            self.popup_logro_timer = 3500
                            audio = getattr(self, "audio", None)
                            if audio is not None:
                                audio.sfx_logro()
            self.minijuego_manager = None
            transitions = getattr(self, "transitions", None)
            audio = getattr(self, "audio", None)
            if audio is not None and hasattr(self, "_sync_scene_audio"):
                self._sync_scene_audio()
            self._transition_to("aventura", transitions)
            return

        # ── Deltas de stats según tipo de minijuego ──────────────────────────
        if getattr(self, "day4_pending_minigame_context", ""):
            self.day4_minigame_result = {"gano": bool(gano), "tipo": tipo}
            self.day4_pending_minigame_context = ""
            self.minijuego_manager = None
            transitions = getattr(self, "transitions", None)
            audio = getattr(self, "audio", None)
            if audio is not None and hasattr(self, "_sync_scene_audio"):
                self._sync_scene_audio()
            self._transition_to("aventura", transitions)
            return

        if tipo == "agresivo":
            df, dr = +1, -2
            label  = "Defender agresivamente"
        elif tipo == "pacifico":
            df, dr = +4, -3
            label  = "Defender pacificamente"
        elif tipo == "penaltis":
            # Jugar = siempre +felicidad; ganar = también +reputación
            goles = result.get("goles", 0)
            df    = +3 if gano else +1
            dr    = +2 if gano else 0
            label = f"Jugar penaltis (goles: {goles})"
        elif tipo == "atrapa_emociones":
            # Entrenar empatía = siempre algo de felicidad
            puntos = result.get("puntos", 0)
            df     = +4 if gano else +1
            dr     = +1 if gano else 0
            label  = f"Atrapar emociones (puntos: {puntos})"
        else:
            df, dr = +1, 0
            label  = f"Minijuego: {tipo}"

        self.story_felicidad   = max(0, min(100, self.story_felicidad   + df))
        self.story_reputacion  = max(0, min(100, self.story_reputacion  + dr))

        self.decision_history.append({
            "event_id":    f"minijuego_{tipo}",
            "option_label": label,
            "gano":        gano,
            "dF":          df,
            "dR":          dr,
        })

        # Logros (solo si ganó)
        lista = getattr(self, "lista_logros", None)
        if lista is not None and gano:
            if tipo == "agresivo":
                lista.desbloquear("rey_de_los_bullies")
            elif tipo == "pacifico":
                lista.desbloquear("irrefutable")
            # Mostrar popup si hay logro recién desbloqueado
            if getattr(self, "popup_logro_timer", 0) <= 0:
                siguiente = lista.consumir_popup()
                if siguiente is not None:
                    self.popup_logro_actual = siguiente
                    self.popup_logro_timer  = 3500
                    audio = getattr(self, "audio", None)
                    if audio is not None:
                        audio.sfx_logro()

        # Incrementar contador de decisiones completadas
        self.story_completed += 1
        if self.story_completed >= getattr(self, "story_goal", 10):
            self._resolve_ending()

        # Limpiar y volver a la aventura
        self.minijuego_manager = None
        transitions = getattr(self, "transitions", None)
        audio = getattr(self, "audio", None)
        if audio is not None and hasattr(self, "_sync_scene_audio"):
            self._sync_scene_audio()
        self._transition_to("aventura", transitions)


    def _handle_escape(self):
        """Lógica de ESC por pantalla."""
        if getattr(self, "debug_day_menu_active", False):
            self.debug_day_menu_active = False
            return
        screen = self.current_screen
        if screen == "menu":
            self.running = False
        elif screen == "aventura":
            self.previous_screen = "aventura"
            self.current_screen = "pause"
            self.show_skills_inventory = False
        elif screen == "pause":
            self.current_screen = "aventura"
            self.pause_overwrite_pending = False
            self.pause_pending_slot = None
        elif screen == "pause_guardar":
            if self.pause_overwrite_pending:
                self.pause_overwrite_pending = False
                self.pause_pending_slot = None
            else:
                self.current_screen = "pause"
        elif screen == "nombre_input":
            transitions = getattr(self, "transitions", None)
            self._transition_to("jugar", transitions)
        elif screen == "configuracion":
            self.current_screen = self.previous_screen or "menu"
            self.previous_screen = None
        elif screen == "controles":
            if self.waiting_control_action is not None:
                self.waiting_control_action = None
            else:
                self.current_screen = "configuracion"
        elif screen == "minijuego":
            # ESC en minijuego: abre/cierra el menú de pausa
            if getattr(self, "minijuego_paused", False):
                self.minijuego_paused = False   # ESC de nuevo cierra la pausa
            else:
                self.minijuego_paused = True
                self.minijuego_pause_idx = 0
            audio = getattr(self, "audio", None)
            if audio is not None:
                audio.sfx_pausa()
        else:
            # historia, progreso, tutorial, creditos → menu
            transitions = getattr(self, "transitions", None)
            self._transition_to("menu", transitions)

