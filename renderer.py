"""
Mixin de renderizado para EmpatiaQuestUI.
Contiene todos los métodos _draw_* y _render_current_screen.

# 🎨 ASSET_UI: Imagenes/UI/popup_logro.png          | 400x100 | Banner de logro estilo Undertale (fallback: rect + texto)
# 🎨 ASSET_UI: Imagenes/UI/habilidades_panel.png    | 500x600 | Panel lateral de habilidades (fallback: rect + texto)
# 🎨 ASSET_UI: Imagenes/UI/logo_menu.png            | 800x200 | Logo EMPATIA QUEST en menu (fallback: draw_pixel_text)
"""

import os
import pygame
from config import (
    BG_DARK, BG_MID, GRID, CARD, CARD_HOVER, CARD_BORDER,
    TEXT_MAIN, TEXT_SOFT, PIXEL_CYAN, PIXEL_PINK,
    CUSTOM_PARTS, PART_STYLES,
    SEATED_OFFSET_X, SEATED_OFFSET_Y, SEATED_DESK_TOP_FRAC,
)
from ui_components import Button
import screens.historia as historia_screen
import screens.progreso as progreso_screen
import screens.tutorial as tutorial_screen
import screens.creditos as creditos_screen


class RendererMixin:
    """Todos los métodos de renderizado de EmpatiaQuestUI."""

    # ──────────────────────────────────────────────────────────────────────────
    # Texto pixel-art
    # ──────────────────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────────────────
    # Constructores de botones (dependen del tamaño de pantalla)
    # ──────────────────────────────────────────────────────────────────────────

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
                    (self.width // 2 - self.button_width // 2, y, self.button_width, self.button_height),
                    text, action,
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
                    (self.width // 2 - self.button_width // 2, y, self.button_width, self.button_height),
                    text, action,
                )
            )
        return buttons

    # ──────────────────────────────────────────────────────────────────────────
    # Fondo compartido
    # ──────────────────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────────────────
    # Pantallas principales
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_menu(self):
        self._draw_pixel_background()
        # 🎨 ASSET_UI: Imagenes/UI/logo_menu.png | 800x200 | Logo EMPATIA QUEST (fallback: texto pixel)
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
        self.draw_pixel_text(
            "Mouse o flechas + Enter. ESC vuelve al menu.",
            self.width // 2, self.height - 40, "small", (194, 216, 248), True,
        )
        self.draw_pixel_text(
            "F5: test pelea  |  F6: test palabras",
            self.width // 2, self.height - 18, "small", (90, 100, 130), True,
        )

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
            "Presiona ESC para volver al menu",
            self.width // 2, panel.y + panel.height - 50, "small", (62, 74, 98), True,
        )

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
            self.width // 2, panel.bottom - 28, "small", TEXT_SOFT, True,
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
            self.draw_pixel_text(f"Slot {i+1} - {status_text}", row.x + 24, row.centery, "body", TEXT_MAIN, False)
            detail_text = "ENTER para sobrescribir" if occupied else "ENTER para guardar"
            self.draw_pixel_text(detail_text, row.right - 300, row.centery, "small", TEXT_SOFT, False)
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
                self.width // 2, confirm.y + 46, "small", TEXT_MAIN, True,
            )
            self.draw_pixel_text(
                "ENTER para sobrescribir | ESC para cancelar",
                self.width // 2, confirm.y + 108, "small", TEXT_SOFT, True,
            )
        self.draw_pixel_text(
            "Flechas para cambiar, ENTER para seleccionar, D borrar, ESC volver.",
            self.width // 2, panel.bottom - 24, "small", TEXT_SOFT, True,
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
            self.draw_pixel_text(f"Slot {i+1} - {status_text}", row.x + 24, row.centery, "body", TEXT_MAIN, False)
            detail_text = "ENTER para cargar" if occupied else "VACIO"
            self.draw_pixel_text(detail_text, row.right - 260, row.centery, "small", TEXT_SOFT, False)
            if row.collidepoint(mouse_pos):
                self.save_slot_selected = i
        back_rect = pygame.Rect(panel.x + panel.width // 2 - 120, panel.bottom - 90, 240, 52)
        pygame.draw.rect(self.screen, CARD_HOVER, back_rect)
        pygame.draw.rect(self.screen, CARD_BORDER, back_rect, 3)
        self.draw_pixel_text("Volver", back_rect.centerx, back_rect.centery, "button", TEXT_MAIN, True)
        self.draw_pixel_text(
            "Flechas para cambiar, ENTER cargar, BACKSPACE borrar, ESC volver.",
            self.width // 2, panel.bottom - 24, "small", TEXT_SOFT, True,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Configuración y controles
    # ──────────────────────────────────────────────────────────────────────────

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
                value_text = ("ON" if value else "OFF") if isinstance(value, bool) else str(value)
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
                self.width // 2, footer_y, "small", TEXT_SOFT, True,
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
            self.width // 2, panel.y + 96, "small", TEXT_SOFT, True,
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
            panel.x + 24, panel.bottom - 34, "small", TEXT_SOFT, False,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # CAMBIO 1 — Pantalla de ingreso de nombre
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_name_input_screen(self):
        # 🎨 ASSET_UI: Imagenes/UI/fondo_nombre.png | 1280x720 | Pantalla de ingreso de nombre, estilo pixel-art escolar
        self._draw_pixel_background()
        panel = pygame.Rect(self.width // 2 - 380, self.height // 2 - 200, 760, 400)
        shadow = panel.move(6, 6)
        pygame.draw.rect(self.screen, (13, 12, 24), shadow)
        pygame.draw.rect(self.screen, CARD, panel)
        pygame.draw.rect(self.screen, CARD_BORDER, panel, width=5)
        self.draw_pixel_text("NUEVA PARTIDA", self.width // 2, panel.y + 55, "title", TEXT_MAIN, True)
        self.draw_pixel_text("¿Cuál es tu nombre?", self.width // 2, panel.y + 110, "subtitle", TEXT_SOFT, True)

        field_rect = pygame.Rect(panel.x + 80, panel.y + 155, panel.width - 160, 56)
        pygame.draw.rect(self.screen, (255, 255, 255), field_rect)
        pygame.draw.rect(self.screen, CARD_BORDER, field_rect, 3)

        text = getattr(self, "nombre_input_text", "")
        cursor_vis = getattr(self, "nombre_input_cursor_visible", True)
        display_text = text + ("|" if cursor_vis else " ")
        font_h = self.base_fonts["button"].get_height()
        text_y = field_rect.y + (field_rect.height - font_h) // 2
        self.draw_pixel_text(display_text, field_rect.x + 14, text_y, "button", TEXT_MAIN, False)

        self.draw_pixel_text(
            "Solo letras, espacios y números. Máximo 20 caracteres.",
            self.width // 2, panel.y + 240, "small", TEXT_SOFT, True,
        )
        can_confirm = len(text.strip()) > 0
        btn_color = CARD_HOVER if can_confirm else (180, 180, 180)
        btn_rect = pygame.Rect(self.width // 2 - 130, panel.y + 280, 260, 52)
        pygame.draw.rect(self.screen, btn_color, btn_rect)
        pygame.draw.rect(self.screen, CARD_BORDER, btn_rect, 3)
        self.draw_pixel_text(
            "ENTER para continuar" if can_confirm else "Escribe tu nombre",
            btn_rect.centerx, btn_rect.centery, "small", TEXT_MAIN, True,
        )
        self.draw_pixel_text("ESC para volver", self.width // 2, panel.bottom - 22, "small", TEXT_SOFT, True)

    # ──────────────────────────────────────────────────────────────────────────
    # Creador de personaje
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_character_preview(self, x, y, scale=6):
        c = self.character_colors
        px = scale
        pygame.draw.rect(self.screen, c["Piel"], (x + 7 * px, y + 2 * px, 10 * px, 9 * px))
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
        eye_style = self.part_styles["Ojos"][self.current_style["Ojos"]]
        eye_w = 2 * px if eye_style == "Grandes" else px
        pygame.draw.rect(self.screen, c["Ojos"], (x + 9 * px, y + 6 * px, eye_w, px))
        pygame.draw.rect(self.screen, c["Ojos"], (x + 14 * px, y + 6 * px, eye_w, px))
        sweater_style = self.part_styles["Sueter"][self.current_style["Sueter"]]
        if sweater_style == "Hoodie":
            pygame.draw.rect(self.screen, c["Sueter"], (x + 5 * px, y + 11 * px, 14 * px, 8 * px))
            pygame.draw.rect(self.screen, c["Sueter"], (x + 9 * px, y + 10 * px, 6 * px, 2 * px))
        elif sweater_style == "Chaqueta":
            pygame.draw.rect(self.screen, c["Sueter"], (x + 5 * px, y + 11 * px, 14 * px, 8 * px))
            pygame.draw.rect(self.screen, (40, 40, 55), (x + 11 * px, y + 11 * px, 2 * px, 8 * px))
        shirt_style = self.part_styles["Camisa"][self.current_style["Camisa"]]
        if shirt_style == "Camiseta":
            pygame.draw.rect(self.screen, c["Camisa"], (x + 8 * px, y + 12 * px, 8 * px, 7 * px))
        elif shirt_style == "Flanelilla":
            pygame.draw.rect(self.screen, c["Camisa"], (x + 9 * px, y + 12 * px, 6 * px, 7 * px))
        elif shirt_style == "Polo":
            pygame.draw.rect(self.screen, c["Camisa"], (x + 8 * px, y + 12 * px, 8 * px, 7 * px))
            pygame.draw.rect(self.screen, (230, 230, 230), (x + 11 * px, y + 12 * px, 2 * px, 2 * px))
        pants_style = self.part_styles["Pantalones"][self.current_style["Pantalones"]]
        if pants_style == "Jeans":
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 7 * px, y + 19 * px, 4 * px, 7 * px))
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 13 * px, y + 19 * px, 4 * px, 7 * px))
        elif pants_style == "Jogger":
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 7 * px, y + 19 * px, 5 * px, 6 * px))
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 12 * px, y + 19 * px, 5 * px, 6 * px))
        elif pants_style == "Short":
            pygame.draw.rect(self.screen, c["Pantalones"], (x + 7 * px, y + 19 * px, 10 * px, 3 * px))
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
            left_x + 140, panel.y + 396, "small", TEXT_SOFT, True,
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
            self.width // 2, panel.y + panel.height - 28, "small", TEXT_SOFT, True,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Prólogo
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_prologo_screen(self):
        self.screen.fill((30, 30, 30))
        self.draw_pixel_text("PROLOGO - FLASHBACK", self.width // 2, 34, "subtitle", (240, 240, 240), True)
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
        self.draw_pixel_text(
            "ENTER/ESPACIO para continuar",
            dialog_box.right - 16, dialog_box.bottom - 20, "small", TEXT_SOFT, False,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Aventura
    # ──────────────────────────────────────────────────────────────────────────

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

    def _draw_story_clock_hud(self):
        if getattr(self, "day1_intro_step", 0) < 2:
            return
        day = getattr(self, "current_day", getattr(self, "story_clock_day", 1))
        mission = getattr(self, "current_mission", "")

        def _badge(text, x, y, min_w=90):
            text_surf = self.base_fonts["small"].render(text, True, TEXT_MAIN)
            w = max(min_w, text_surf.get_width() + 24)
            box = pygame.Rect(x, y, w, 34)
            overlay = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 220))
            self.screen.blit(overlay, box.topleft)
            pygame.draw.rect(self.screen, (18, 18, 18), box, 2)
            self.draw_pixel_text(text, box.centerx, box.centery, "small", TEXT_MAIN, True)
            return box.right

        next_x = _badge(f"Dia {day}", 12, 12)
        if mission:
            _badge(f"Mision: {mission}", next_x + 8, 12, min_w=200)

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
                mx + int(mw * h["rx"]), my + int(mh * h["ry"]),
                max(8, int(mw * h["rw"])), max(8, int(mh * h["rh"])),
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
                (cx - (scaled.get_width() // 2) - self.story_camera_x,
                 cy - (scaled.get_height() // 2) - self.story_camera_y),
            )

    # _load_object_interactable_image and _get_cropped_object_image defined in GameStateMixin

    def _draw_object_interactables_from_hitboxes(self):
        seated_pupitre = getattr(self, "story_seated_pupitre", None)
        for h in self.story_walls:
            if h.get("role") != "interactable" or h.get("action") != "objeto":
                continue
            if seated_pupitre is not None and h is seated_pupitre:
                continue  # pupitre hidden while player is seated there
            if h.get("type") != "rect":
                continue
            object_name = h.get("object_name", "")
            image = self._load_object_interactable_image(object_name)
            if image is None:
                continue  # No debería ocurrir con el fallback, pero por seguridad
            x = int(self.story_world_width * h["rx"]) - self.story_camera_x
            y = int(self.story_world_height * h["ry"]) - self.story_camera_y
            w = max(8, int(self.story_world_width * h["rw"]))
            h_px = max(8, int(self.story_world_height * h["rh"]))
            image = self._get_cropped_object_image(image, h.get("crop"))
            scaled = pygame.transform.smoothscale(image, (w, h_px))
            self.screen.blit(scaled, (x, y))

    # ──────────────────────────────────────────────────────────────────────────
    # CAMBIO 2 — Flecha guía
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_guide_arrow(self):
        # 🎨 ASSET_UI: Imagenes/flecha_guia.png | 64x64 | Flecha pixel-art amarilla, se rota por código
        if not getattr(self, "day1_guide_active", False):
            return

        # Determinar el mapa siguiente en la secuencia del Día 1
        # Clave: fragmento del nombre del mapa actual → fragmento esperado en target_image del destino
        DAY1_NEXT = {
            "habdia":       "calle",
            "calledia":     "patio",
            "patiod":       "pasillo1",  # cubre patiodía y patiodia
            "pasillo1_dia": "salon",
        }
        fondo = getattr(self, "aventura_fondo", None)
        ruta = str(getattr(fondo, "ruta_imagen", "")).lower().replace("\\", "/")
        current_map = ruta.split("/")[-1]  # basename en minúsculas
        next_keyword = ""
        for key, val in DAY1_NEXT.items():
            if key in current_map:
                next_keyword = val
                break

        # Buscar la puerta cuyo target_image coincide con el siguiente mapa
        target_world = None
        for h in self.story_walls:
            if h.get("role") != "interactable" or h.get("action") != "puerta":
                continue
            if next_keyword:
                tgt = h.get("target_image", "").lower().replace("\\", "/")
                if next_keyword not in tgt:
                    continue
            mw, mh = self.story_world_width, self.story_world_height
            cx = int(mw * h["rx"]) + int(mw * h["rw"]) // 2
            cy = int(mh * h["ry"]) + int(mh * h["rh"]) // 2
            target_world = (cx, cy)
            break

        # Fallback: cualquier puerta si no encontramos la específica
        if target_world is None:
            for h in self.story_walls:
                if h.get("role") == "interactable" and h.get("action") == "puerta":
                    mw, mh = self.story_world_width, self.story_world_height
                    cx = int(mw * h["rx"]) + int(mw * h["rw"]) // 2
                    cy = int(mh * h["ry"]) + int(mh * h["rh"]) // 2
                    target_world = (cx, cy)
                    break
        if target_world is None:
            return
        # Posición de la flecha en pantalla: sobre el jugador
        player_screen_x = self.player_rect.centerx - self.story_camera_x
        player_screen_y = self.player_rect.centery - self.story_camera_y
        arrow_cx = player_screen_x
        arrow_cy = player_screen_y - 48
        # Calcular ángulo hacia el destino
        import math
        tx = target_world[0] - self.story_camera_x
        ty = target_world[1] - self.story_camera_y
        dx = tx - player_screen_x
        dy = ty - player_screen_y
        angle_rad = math.atan2(-dy, dx)  # positivo Y en pantalla va hacia abajo
        angle_deg = math.degrees(angle_rad)
        # Animación de rebote
        t = pygame.time.get_ticks() / 1000.0
        bounce = int(4 * abs(math.sin(t * 4)))
        arrow_cy -= bounce
        # Dibujar flecha procedural (triángulo amarillo)
        size = 22
        tip_x = arrow_cx + int(size * math.cos(math.radians(angle_deg)))
        tip_y = arrow_cy - int(size * math.sin(math.radians(angle_deg)))
        perp = math.radians(angle_deg + 90)
        base_x = arrow_cx - int((size * 0.5) * math.cos(math.radians(angle_deg)))
        base_y = arrow_cy + int((size * 0.5) * math.sin(math.radians(angle_deg)))
        p1 = (tip_x, tip_y)
        p2 = (int(base_x + 10 * math.cos(perp)), int(base_y - 10 * math.sin(perp)))
        p3 = (int(base_x - 10 * math.cos(perp)), int(base_y + 10 * math.sin(perp)))
        pygame.draw.polygon(self.screen, (255, 220, 30), [p1, p2, p3])
        pygame.draw.polygon(self.screen, (180, 140, 0), [p1, p2, p3], 2)

    # ──────────────────────────────────────────────────────────────────────────
    # Intro cinematográfica — mensajes al inicio de la aventura
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_day1_intro_dialog(self):
        step = getattr(self, "day1_intro_step", 2)
        pname = getattr(self, "player_name", "") or "Protagonista"
        if step == 0:
            text = "Que lindo dia, ya no puedo esperar por comenzar mi primer dia de clases!"
        else:
            text = "Tengo que ir a la escuela"
        box_h = 130
        box = pygame.Rect(26, self.height - box_h - 22, self.width - 52, box_h)
        overlay = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        overlay.fill((242, 242, 242, 220))
        self.screen.blit(overlay, box.topleft)
        pygame.draw.rect(self.screen, (18, 18, 18), box, 4)
        name_box = pygame.Rect(box.x + 16, box.y - 32, max(120, len(pname) * 14 + 24), 32)
        pygame.draw.rect(self.screen, (255, 255, 255), name_box)
        pygame.draw.rect(self.screen, (18, 18, 18), name_box, 3)
        self.draw_pixel_text(pname, name_box.centerx, name_box.centery, "small", TEXT_MAIN, True)
        self.draw_pixel_text(text, box.x + 24, box.y + 52, "body", TEXT_MAIN, False)
        self.draw_pixel_text("ENTER para continuar", box.right - 16, box.bottom - 18, "small", TEXT_SOFT, False)

    # ──────────────────────────────────────────────────────────────────────────
    # CAMBIO 3 — Caja de diálogo Día 1
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_day1_dialog(self):
        seq = getattr(self, "day1_seq_step", 0)
        if seq not in (1, 2, 3):
            return
        pname = getattr(self, "player_name", "") or "Protagonista"
        if seq == 1:
            speaker = pname
            text = "¿Dónde debería sentarme?"
            hint = "ENTER para continuar"
        elif seq == 2:
            speaker = "Diego"
            text = "Ey, acá hay puesto."
            hint = "ENTER para continuar"
        else:  # 3
            speaker = pname
            text = "Voy a elegir dónde sentarme."
            hint = "Acércate a una silla y presiona E"

        box_h = 130
        box = pygame.Rect(26, self.height - box_h - 22, self.width - 52, box_h)
        overlay = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        overlay.fill((242, 242, 242, 220))
        self.screen.blit(overlay, box.topleft)
        pygame.draw.rect(self.screen, (18, 18, 18), box, 4)
        name_box = pygame.Rect(box.x + 16, box.y - 32, max(120, len(speaker) * 14 + 24), 32)
        pygame.draw.rect(self.screen, (255, 255, 255), name_box)
        pygame.draw.rect(self.screen, (18, 18, 18), name_box, 3)
        self.draw_pixel_text(speaker, name_box.centerx, name_box.centery, "small", TEXT_MAIN, True)
        self.draw_pixel_text(text, box.x + 24, box.y + 52, "body", TEXT_MAIN, False)
        self.draw_pixel_text(hint, box.right - 16, box.bottom - 18, "small", TEXT_SOFT, False)

    # ──────────────────────────────────────────────────────────────────────────
    # CAMBIO 4 — Zoom pupitre rayado
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_pupitre_zoom(self):
        if not getattr(self, "day1_pupitre_zoom_active", False):
            return
        # Fondo zoom
        # 🖼️ ASSET_IMG: Imagenes/Interactuables/PupitreRayado_zoom.png | 1280x720 | Pupitre con insultos escritos, vista de cerca
        zoom_img = self._load_object_interactable_image("PupitreRayado_zoom.png")
        if zoom_img is not None:
            scaled = pygame.transform.scale(zoom_img, (self.width, self.height))
            self.screen.blit(scaled, (0, 0))
        else:
            placeholder = pygame.Surface((self.width, self.height))
            placeholder.fill((80, 60, 40))
            self.screen.blit(placeholder, (0, 0))
            self.draw_pixel_text("Pupitre Rayado", self.width // 2, self.height // 2 - 60, "subtitle", (255, 255, 255), True)

        # Capa de rayones borrables (si no se está borrando, mostrar overlay)
        # 🖼️ ASSET_IMG: Imagenes/Interactuables/PupitreRayones.png | 1280x720 | Capa PNG con insultos encima del pupitre
        erase_surf = getattr(self, "day1_pupitre_erase_surface", None)
        if erase_surf is not None:
            self.screen.blit(erase_surf, (0, 0))

        pname = getattr(self, "player_name", "") or "Protagonista"
        step = getattr(self, "day1_pupitre_step", 2)
        if step == 2:
            # Panel de opciones
            panel_h = 220
            panel = pygame.Rect(26, self.height - panel_h - 10, self.width - 52, panel_h)
            overlay = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
            overlay.fill((242, 242, 242, 220))
            self.screen.blit(overlay, panel.topleft)
            pygame.draw.rect(self.screen, (18, 18, 18), panel, 4)
            self.draw_pixel_text(f"{pname}: Vaya, cuántos comentarios groseros.", panel.x + 16, panel.y + 24, "body", TEXT_MAIN, False)
            opts = [
                ("A", "Borrar mensajes"),
                ("B", "Ignorar"),
                ("C", "Tomar foto"),
                ("D", "Mostrar al profesor"),
            ]
            col_w = (panel.width - 32) // 2
            for i, (key, label) in enumerate(opts):
                col = i % 2
                row = i // 2
                x = panel.x + 16 + col * col_w
                y = panel.y + 70 + row * 52
                self.draw_pixel_text(f"[{key}] {label}", x, y, "small", TEXT_MAIN, False)
            self.draw_pixel_text("ESC para volver", panel.right - 16, panel.bottom - 18, "small", TEXT_SOFT, False)

    def _draw_adventure_screen(self):
        self.screen.fill((255, 255, 255))
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

        _npc_ai_mgr = getattr(self, "npc_ai_manager", None)
        _npc_ai_on = _npc_ai_mgr is not None and _npc_ai_mgr.npc_ai_active
        if self._is_first_day_classroom_context() and not _npc_ai_on:
            has_npc_hitboxes = any(
                h.get("role") == "interactable" and h.get("action") == "npc"
                for h in self.story_walls
            )
            if not has_npc_hitboxes:
                self._draw_first_day_classroom_npcs()

        self._draw_object_interactables_from_hitboxes()

        bar_w = min(260, max(180, self.width // 5))
        bar_h = 20
        gap = 20
        total_w = bar_w * 2 + gap
        start_x = self.width - total_w - 24
        bar_y_top = 18
        bar_x_f = start_x
        bar_x_r = start_x + bar_w + gap

        pygame.draw.rect(self.screen, (220, 220, 220), (bar_x_f, bar_y_top, bar_w, bar_h))
        pygame.draw.rect(self.screen, (30, 30, 30), (bar_x_f, bar_y_top, bar_w, bar_h), 2)
        fill_f = int((self.story_felicidad / 100) * bar_w)
        if fill_f > 0:
            pygame.draw.rect(self.screen, (245, 170, 70), (bar_x_f, bar_y_top, fill_f, bar_h))
        self.draw_pixel_text(f"F {self.story_felicidad}", bar_x_f + bar_w // 2, bar_y_top + 10, "small", TEXT_MAIN, True)

        pygame.draw.rect(self.screen, (220, 220, 220), (bar_x_r, bar_y_top, bar_w, bar_h))
        pygame.draw.rect(self.screen, (30, 30, 30), (bar_x_r, bar_y_top, bar_w, bar_h), 2)
        fill_r = int((self.story_reputacion / 100) * bar_w)
        if fill_r > 0:
            pygame.draw.rect(self.screen, (90, 190, 255), (bar_x_r, bar_y_top, fill_r, bar_h))
        self.draw_pixel_text(f"R {self.story_reputacion}", bar_x_r + bar_w // 2, bar_y_top + 10, "small", TEXT_MAIN, True)

        if self.settings.get("Mostrar hitboxes", False):
            mx, my, mw, mh = 0, 0, self.story_world_width, self.story_world_height
            for wall in self.story_walls:
                color = (90, 160, 255) if wall.get("role", "wall") == "wall" else (255, 210, 0)
                if wall["type"] == "rect":
                    r = pygame.Rect(
                        mx + int(mw * wall["rx"]) - self.story_camera_x,
                        my + int(mh * wall["ry"]) - self.story_camera_y,
                        max(8, int(mw * wall["rw"])), max(8, int(mh * wall["rh"])),
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

        if not _npc_ai_on:
            self._draw_npc_interactables_from_hitboxes()

        # NPC AI draw — misma capa que los NPCs estáticos, debajo del jugador
        if _npc_ai_mgr is not None and self.aventura_fondo is not None:
            _cur_map = os.path.basename(str(getattr(self.aventura_fondo, "ruta_imagen", "")))
            _npc_ai_mgr.draw(
                self.screen,
                self.story_camera_x, self.story_camera_y,
                self.story_world_width, self.story_world_height,
                _cur_map,
            )

        if self.aventura_personaje is not None:
            if self.story_is_seated and self.story_seated_sprite is not None:
                p = getattr(self, "story_seated_pupitre", None)
                if p is not None:
                    pw_base = max(8, int(self.story_world_width * p["rw"]))
                    ph_base = max(8, int(self.story_world_height * p["rh"]))
                    # Scale sprite so its chair bottom = pupitre bottom, desk top = pupitre top
                    frac = max(0.05, min(0.95, SEATED_DESK_TOP_FRAC))
                    sw = sh = int(ph_base / (1.0 - frac))
                    # Centered on pupitre X; desk-top aligned with pupitre top Y
                    spx = int(self.story_world_width * p["rx"]) - self.story_camera_x
                    spy = int(self.story_world_height * p["ry"]) - self.story_camera_y
                    draw_x = spx + pw_base // 2 - sw // 2 + SEATED_OFFSET_X
                    draw_y = spy - int(frac * sh)          + SEATED_OFFSET_Y
                    seated_scaled = pygame.transform.smoothscale(self.story_seated_sprite, (sw, sh))
                    self.screen.blit(seated_scaled, (draw_x, draw_y))
                else:
                    seat_center = (
                        self._interactable_center(self.story_seated_hitbox)
                        if self.story_seated_hitbox else self.player_rect.center
                    )
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
                interactable_view = self.aventura_personaje.interactable_hitbox.move(
                    -self.story_camera_x, -self.story_camera_y
                )
                pygame.draw.rect(self.screen, (255, 220, 0), interactable_view, 2)
        else:
            player_view = self.player_rect.move(-self.story_camera_x, -self.story_camera_y)
            pygame.draw.rect(self.screen, PIXEL_CYAN, player_view)
            if self.settings.get("Mostrar hitboxes", False):
                pygame.draw.rect(self.screen, (255, 0, 0), player_view, 2)

        # CAMBIO 2: flecha guía
        self._draw_guide_arrow()

        # HUD de día — dibuja al frente, encima de objetos y NPCs
        self._draw_story_clock_hud()

        # CAMBIO 4: zoom pupitre (dibuja encima de todo si está activo)
        if getattr(self, "day1_pupitre_zoom_active", False):
            self._draw_pupitre_zoom()
            return  # No dibujar el event box mientras está el zoom

        # CAMBIO 5: pantalla de fin del Día 1
        if getattr(self, "day1_end_timer", 0) > 0:
            overlay_end = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay_end.fill((0, 0, 0, 200))
            self.screen.blit(overlay_end, (0, 0))
            self.draw_pixel_text("Fin del Día 1", self.width // 2, self.height // 2, "title", (245, 247, 255), True)
            return

        # Intro: bloquea el event box hasta que el jugador avance los dos mensajes
        if getattr(self, "day1_intro_step", 2) < 2:
            self._draw_day1_intro_dialog()
            return

        # Ocultar barra entera mientras el jugador camina a la escuela (después del intro)
        if not getattr(self, "day1_salon_entered", True):
            return

        # CAMBIO 3: caja de diálogo Día 1 (reemplaza event box mientras está en secuencia)
        seq_step = getattr(self, "day1_seq_step", 0)
        if seq_step in (1, 2, 3):
            self._draw_day1_dialog()
            return

        # ── Pantalla de final ────────────────────────────────────────────────────
        if self.story_pending_end:
            end_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            end_overlay.fill((0, 0, 0, 210))
            self.screen.blit(end_overlay, (0, 0))
            self.draw_pixel_text(self.story_final_key, self.width // 2, self.height // 2 - 60, "subtitle", (245, 247, 255), True)
            self.draw_pixel_text(self.story_final_text, self.width // 2, self.height // 2, "body", TEXT_SOFT, True)
            self.draw_pixel_text("ENTER para volver al menu", self.width // 2, self.height // 2 + 80, "small", TEXT_SOFT, True)
            return

        # ── Barra de estado inferior ─────────────────────────────────────────────
        status_h = 72
        status_box = pygame.Rect(26, self.height - status_h - 10, self.width - 52, status_h)
        status_surf = pygame.Surface((status_box.width, status_box.height), pygame.SRCALPHA)
        status_surf.fill((242, 242, 242, 180))
        self.screen.blit(status_surf, status_box.topleft)
        pygame.draw.rect(self.screen, (18, 18, 18), status_box, 3)

        thought = getattr(self, "story_thought", "")
        interaction = getattr(self, "story_interaction_text", "")
        if thought:
            self.draw_pixel_text(f"Pensamiento: {thought}", status_box.x + 14, status_box.y + 8, "small", TEXT_MAIN, False)
        if interaction:
            self.draw_pixel_text(interaction, status_box.x + 14, status_box.y + 34, "small", TEXT_SOFT, False)

        interactable_hint = (
            f" | {self._control_name('interactuar')} interactuar"
            if self._should_show_interactable_prompt() else ""
        )
        move_keys = (
            f"{self._control_name('mover_arriba')}/{self._control_name('mover_izquierda')}/"
            f"{self._control_name('mover_abajo')}/{self._control_name('mover_derecha')}"
        )
        self.draw_pixel_text(
            f"{move_keys} mover{interactable_hint} | {self._control_name('guardar')} guardar | ESC pausa | TAB habilidades",
            status_box.right - 14, status_box.bottom - 10, "small", TEXT_SOFT, False,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Simulación
    # ──────────────────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────────────────
    # Nuevo: popup de logro (Undertale-style)
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_achievement_popup(self):
        """
        Muestra el banner de logro desbloqueado en la esquina superior derecha.
        # 🎨 ASSET_UI: Imagenes/UI/popup_logro.png | 400x100 | Banner de logro estilo Undertale (fallback procedural)
        """
        logro = getattr(self, "popup_logro_actual", None)
        if logro is None:
            return
        pw, ph = 400, 90
        px = self.width - pw - 16
        py = 16
        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((20, 22, 38, 220))
        self.screen.blit(bg, (px, py))
        pygame.draw.rect(self.screen, PIXEL_CYAN, (px, py, pw, ph), 3)
        # Estrella pequeña (procedural)
        star_cx = px + 28
        star_cy = py + ph // 2
        pygame.draw.polygon(
            self.screen, (230, 180, 30),
            [(star_cx, star_cy - 12), (star_cx + 8, star_cy + 10),
             (star_cx - 10, star_cy - 4), (star_cx + 10, star_cy - 4),
             (star_cx - 8, star_cy + 10)],
        )
        self.draw_pixel_text("Logro desbloqueado!", px + 52, py + 22, "small", PIXEL_CYAN, False)
        nombre = logro.nombre[:38] + ".." if len(logro.nombre) > 40 else logro.nombre
        self.draw_pixel_text(nombre, px + 52, py + 50, "small", (245, 248, 255), False)

    # ──────────────────────────────────────────────────────────────────────────
    # Nuevo: panel lateral de habilidades (TAB)
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_skills_inventory_overlay(self):
        """
        Panel lateral de habilidades, activado con TAB durante la aventura.
        # 🎨 ASSET_UI: Imagenes/UI/habilidades_panel.png | 500x600 | Panel lateral de habilidades (fallback procedural)
        """
        pw = 420
        ph = min(self.height - 40, 520)
        px = self.width // 2 - pw // 2
        py = self.height // 2 - ph // 2

        panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel_surf.fill((15, 14, 30, 230))
        self.screen.blit(panel_surf, (px, py))
        pygame.draw.rect(self.screen, PIXEL_CYAN, (px, py, pw, ph), 4)

        self.draw_pixel_text("HABILIDADES", self.width // 2, py + 32, "subtitle", PIXEL_CYAN, True)
        pygame.draw.line(self.screen, CARD_BORDER, (px + 20, py + 54), (px + pw - 20, py + 54), 2)

        skills = getattr(self, "skills_inventory", {})
        item_h = 72
        item_y = py + 68
        for skill_name, skill_data in skills.items():
            nivel = skill_data.get("nivel", 0)
            max_nivel = skill_data.get("max_nivel", 3)
            desc = skill_data.get("descripcion", "")

            color_icon = PIXEL_CYAN if nivel > 0 else (80, 85, 100)
            icon_rect = pygame.Rect(px + 18, item_y + 8, 44, 44)
            pygame.draw.rect(self.screen, color_icon, icon_rect, 0, 6)
            pygame.draw.rect(self.screen, CARD_BORDER, icon_rect, 2, 6)
            self.draw_pixel_text(str(nivel), icon_rect.centerx, icon_rect.centery, "subtitle", (245, 248, 255), True)

            self.draw_pixel_text(skill_name, px + 74, item_y + 14, "small", TEXT_MAIN, False)
            short_desc = desc[:44] + ".." if len(desc) > 46 else desc
            self.draw_pixel_text(short_desc, px + 74, item_y + 36, "small", TEXT_SOFT, False)

            dot_x = px + 74
            for lvl in range(max_nivel):
                dot_rect = pygame.Rect(dot_x + lvl * 20, item_y + 54, 14, 8)
                dot_color = PIXEL_CYAN if lvl < nivel else (60, 65, 80)
                pygame.draw.rect(self.screen, dot_color, dot_rect, 0, 3)

            item_y += item_h
            if item_y + item_h > py + ph - 40:
                break

        self.draw_pixel_text("TAB para cerrar", self.width // 2, py + ph - 20, "small", (62, 74, 98), True)

    # ──────────────────────────────────────────────────────────────────────────
    # Dispatcher principal
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_minijuego_screen(self):
        """Delegado de renderizado al MinigameManager activo."""
        mgr = getattr(self, "minijuego_manager", None)
        if mgr is None:
            self.screen.fill((10, 10, 16))
            return
        show_hb = getattr(self, "minijuego_show_hitboxes", False)
        mgr.draw(self.screen, self.base_fonts, show_hitboxes=show_hb)

        if getattr(self, "minijuego_paused", False):
            self._draw_minijuego_pause_overlay()

    def _draw_minijuego_pause_overlay(self):
        """Menú de pausa sobre el minijuego (ESC)."""
        w, h = self.width, self.height

        # Fondo semitransparente
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((8, 8, 18, 200))
        self.screen.blit(overlay, (0, 0))

        # Panel central
        pw, ph = 540, 420
        panel = pygame.Rect(w // 2 - pw // 2, h // 2 - ph // 2, pw, ph)
        shadow = panel.move(6, 6)
        pygame.draw.rect(self.screen, (8, 8, 18), shadow)
        pygame.draw.rect(self.screen, CARD, panel)
        pygame.draw.rect(self.screen, CARD_BORDER, panel, width=4)

        self.draw_pixel_text("PAUSA", w // 2, panel.y + 46, "title", TEXT_MAIN, True)
        self.draw_pixel_text(
            "↑↓ navegar   ENTER seleccionar   ESC continuar",
            w // 2, panel.y + 92, "small", TEXT_SOFT, True,
        )

        # Opciones
        mgr   = getattr(self, "minijuego_manager", None)
        tipo  = getattr(self, "minijuego_pending_tipo", "agresivo")
        hb_on = getattr(self, "minijuego_show_hitboxes", False)
        opts  = [
            "Continuar",
            f"Ver hitboxes: {'ON' if hb_on else 'OFF'}",
            "Configuracion",
            "Volver a la historia",
        ]
        sel_idx   = getattr(self, "minijuego_pause_idx", 0)
        opt_start = panel.y + 130
        opt_h     = 56

        for i, label in enumerate(opts):
            opt_rect = pygame.Rect(panel.x + 28, opt_start + i * opt_h, pw - 56, opt_h - 6)
            is_sel   = i == sel_idx

            if is_sel:
                pygame.draw.rect(self.screen, CARD_HOVER, opt_rect, border_radius=6)
                pygame.draw.rect(self.screen, CARD_BORDER, opt_rect, 2, border_radius=6)
                color = TEXT_MAIN
            else:
                color = TEXT_SOFT

            self.draw_pixel_text(label, opt_rect.centerx, opt_rect.centery, "body", color, True)

        # Subtítulo con el tipo de minijuego activo
        tipo_label = "Pelea agresiva" if tipo == "agresivo" else "Defensa con palabras"
        self.draw_pixel_text(
            f"Modo: {tipo_label}",
            w // 2, panel.bottom - 26, "small", TEXT_SOFT, True,
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
                "Elige una opcion para continuar", self.width // 2, panel.y + 110, "small", TEXT_SOFT, True,
            )
            mouse_pos = pygame.mouse.get_pos()
            for i, button in enumerate(self.play_buttons):
                hover = button.contains(mouse_pos) or i == self.selected_play_index
                button.draw(self.screen, self, hover=hover)
        elif self.current_screen == "historia":
            historia_screen.draw(self)
        elif self.current_screen == "progreso":
            progreso_screen.draw(self)
        elif self.current_screen == "tutorial":
            tutorial_screen.draw(self)
        elif self.current_screen == "creditos":
            creditos_screen.draw(self)
        elif self.current_screen == "configuracion":
            self._draw_settings_screen()
        elif self.current_screen == "controles":
            self._draw_controls_screen()
        elif self.current_screen == "nombre_input":
            self._draw_name_input_screen()
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
        elif self.current_screen == "minijuego":
            self._draw_minijuego_screen()

        # Overlays globales (siempre encima de la pantalla actual)
        if getattr(self, "show_skills_inventory", False):
            self._draw_skills_inventory_overlay()

        # Popup de logro desbloqueado
        popup_timer = getattr(self, "popup_logro_timer", 0)
        if popup_timer > 0:
            self._draw_achievement_popup()

        # Transición de pantalla (fade negro)
        transitions = getattr(self, "transitions", None)
        if transitions is not None:
            transitions.draw(self.screen)

        if self.settings["Mostrar FPS"]:
            self.draw_pixel_text(f"FPS {int(self.clock.get_fps())}", 20, 16, "small", (210, 230, 255), False)
