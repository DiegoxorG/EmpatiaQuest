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


class ScreenHandlersMixin:
    """Todos los manejadores de eventos de EmpatiaQuestUI."""

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
            self._transition_to("creador", transitions)
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

    # ──────────────────────────────────────────────────────────────────────────
    # Pausa
    # ──────────────────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────────────────
    # Prólogo
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_prologo_events(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            self.prologo_paso += 1
            if self.prologo_paso >= len(self.prologo_textos):
                self.prologo_activo = False
                audio = getattr(self, "audio", None)
                if audio is not None:
                    audio.play_bgm_for_screen("aventura")
                self.current_screen = "aventura"

    # ──────────────────────────────────────────────────────────────────────────
    # Aventura (movimiento + decisiones + TAB)
    # ──────────────────────────────────────────────────────────────────────────

    def _handle_adventure_events(self, event):
        if event.type == pygame.KEYDOWN:
            # TAB — panel de habilidades
            if event.key == pygame.K_TAB:
                self.show_skills_inventory = not getattr(self, "show_skills_inventory", False)
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

            if self.story_show_support:
                if event.key in (self.controls["continuar"], pygame.K_SPACE, pygame.K_KP_ENTER):
                    self.story_show_support = False
                return

            if self.story_current_event is None:
                return

            if self.story_current_event.get("id") == "primer_dia":
                return

            key_to_idx = {
                self.controls["opcion_1"]: 0,
                self.controls["opcion_2"]: 1,
                self.controls["opcion_3"]: 2,
                self.controls["opcion_4"]: 3,
                self.controls["opcion_5"]: 4,
                pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2,
                pygame.K_KP4: 3, pygame.K_KP5: 4,
            }
            if event.key in key_to_idx:
                idx = key_to_idx[event.key]
                options = self.story_current_event["options"]
                if 0 <= idx < len(options):
                    self._apply_story_choice(options[idx], option_idx=idx)

    # ──────────────────────────────────────────────────────────────────────────
    # Configuración
    # ──────────────────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────────────────
    # Controles (reasignación de teclas)
    # ──────────────────────────────────────────────────────────────────────────

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

        screen = self.current_screen
        if screen == "menu":
            self._handle_menu_events(event)
        elif screen == "jugar":
            self._handle_play_events(event)
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
        elif screen == "historia":
            historia_screen.handle_event(self, event)
        elif screen == "progreso":
            progreso_screen.handle_event(self, event)
        elif screen == "tutorial":
            tutorial_screen.handle_event(self, event)
        elif screen == "creditos":
            creditos_screen.handle_event(self, event)

    def _handle_escape(self):
        """Lógica de ESC por pantalla."""
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
        elif screen == "configuracion":
            self.current_screen = self.previous_screen or "menu"
            self.previous_screen = None
        elif screen == "controles":
            if self.waiting_control_action is not None:
                self.waiting_control_action = None
            else:
                self.current_screen = "configuracion"
        else:
            # historia, progreso, tutorial, creditos → menu
            transitions = getattr(self, "transitions", None)
            self._transition_to("menu", transitions)
