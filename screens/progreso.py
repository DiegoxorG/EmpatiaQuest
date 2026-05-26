"""
Pantalla de Progreso — estadísticas, logros y completitud del juego.

# 🎨 ASSET_UI: Imagenes/UI/barra_felicidad.png       | 240x24 | Barra de felicidad estilo pixel-art
# 🎨 ASSET_UI: Imagenes/UI/barra_reputacion.png      | 240x24 | Barra de reputación estilo pixel-art
# 🎨 ASSET_UI: Imagenes/UI/icono_logro_desbloqueado.png | 36x36 | Icono de logro desbloqueado (estrella dorada)
# 🎨 ASSET_UI: Imagenes/UI/icono_logro_bloqueado.png    | 36x36 | Icono de logro bloqueado (candado gris)
"""

import pygame
from config import (
    CARD, CARD_HOVER, CARD_BORDER, TEXT_MAIN, TEXT_SOFT,
    PIXEL_CYAN, PIXEL_PINK, BG_DARK,
)

_SCROLL = 0   # Scroll del panel de logros (módulo-level para persistencia en sesión)


def _draw_stat_bar(game, label, value, max_val, x, y, bar_w, bar_h, fill_color):
    """Dibuja una barra de estadística con etiqueta y valor numérico."""
    game.draw_pixel_text(label, x, y - 26, "small", TEXT_SOFT, False)
    bg = pygame.Rect(x, y, bar_w, bar_h)
    pygame.draw.rect(game.screen, (200, 208, 192), bg)
    pygame.draw.rect(game.screen, CARD_BORDER, bg, 2)
    fill_w = max(0, int((value / max(1, max_val)) * bar_w))
    if fill_w > 0:
        pygame.draw.rect(game.screen, fill_color, (x, y, fill_w, bar_h))
    game.draw_pixel_text(
        f"{value}/{max_val}", x + bar_w + 10, y, "small", TEXT_MAIN, False
    )


def draw(game):
    """Renderiza la pantalla de Progreso."""
    global _SCROLL
    game._draw_pixel_background()

    w, h = game.screen.get_size()

    # ── Panel principal ────────────────────────────────────────────────────────
    panel = pygame.Rect(w // 2 - 520, 40, 1040, h - 80)
    shadow = panel.move(5, 5)
    pygame.draw.rect(game.screen, (13, 12, 24), shadow)
    pygame.draw.rect(game.screen, CARD, panel)
    pygame.draw.rect(game.screen, CARD_BORDER, panel, 5)

    game.draw_pixel_text("PROGRESO", w // 2, panel.y + 44, "title", TEXT_MAIN, True)
    game.draw_pixel_text(
        "Tu camino en EmpatiaQuest", w // 2, panel.y + 82, "small", TEXT_SOFT, True
    )

    # ── Estadísticas ─────────────────────────────────────────────────────────
    stats_y = panel.y + 124
    bar_w = 320
    bar_h = 22
    left_col = panel.x + 60
    right_col = panel.x + 560

    felicidad = getattr(game, "story_felicidad", 50)
    reputacion = getattr(game, "story_reputacion", 50)
    story_completed = getattr(game, "story_completed", 0)
    story_goal = getattr(game, "story_goal", 12)

    # Barra de Felicidad
    # 🎨 ASSET_UI: Imagenes/UI/barra_felicidad.png | 240x24 | Barra de felicidad estilo pixel-art
    _draw_stat_bar(game, "Felicidad (F)", felicidad, 100,
                   left_col, stats_y, bar_w, bar_h, (245, 170, 70))

    # Barra de Reputación
    # 🎨 ASSET_UI: Imagenes/UI/barra_reputacion.png | 240x24 | Barra de reputación estilo pixel-art
    _draw_stat_bar(game, "Reputacion (R)", reputacion, 100,
                   right_col, stats_y, bar_w, bar_h, (90, 190, 255))

    # Barra de completitud
    stats_y += 56
    _draw_stat_bar(game, f"Eventos completados ({story_completed}/{story_goal})",
                   story_completed, story_goal,
                   left_col, stats_y, bar_w * 2 + right_col - left_col - bar_w, bar_h,
                   PIXEL_CYAN)

    # ── Habilidades ───────────────────────────────────────────────────────────
    skills_y = stats_y + 60
    pygame.draw.line(
        game.screen, CARD_BORDER,
        (panel.x + 40, skills_y - 12), (panel.right - 40, skills_y - 12), 2
    )
    game.draw_pixel_text("HABILIDADES", w // 2, skills_y + 4, "subtitle", TEXT_MAIN, True)

    skills = getattr(game, "skills_inventory", {})
    skill_x = panel.x + 60
    skill_y = skills_y + 30
    skill_col_w = (panel.width - 120) // max(1, len(skills))

    for i, (skill_name, skill_data) in enumerate(skills.items()):
        sx = skill_x + i * skill_col_w
        nivel = skill_data.get("nivel", 0)
        max_nivel = 3

        # 🎨 ASSET_UI: Imagenes/UI/icono_habilidad.png | 48x48 | Icono genérico de habilidad
        icon_rect = pygame.Rect(sx, skill_y, 48, 48)
        color = PIXEL_CYAN if nivel > 0 else (160, 165, 175)
        pygame.draw.rect(game.screen, color, icon_rect, 0, 8)
        pygame.draw.rect(game.screen, CARD_BORDER, icon_rect, 2, 8)
        game.draw_pixel_text(
            str(nivel), icon_rect.centerx, icon_rect.centery, "subtitle", TEXT_MAIN, True
        )

        short_name = skill_name.split()[0][:12]
        game.draw_pixel_text(
            short_name, sx + 24, skill_y + 54, "small", TEXT_MAIN, True
        )
        # Mini barras de nivel
        for lvl in range(max_nivel):
            dot_rect = pygame.Rect(sx + lvl * 18, skill_y + 70, 14, 8)
            dot_color = PIXEL_CYAN if lvl < nivel else (190, 195, 200)
            pygame.draw.rect(game.screen, dot_color, dot_rect, 0, 3)

    # ── Panel de logros ───────────────────────────────────────────────────────
    logros_y = skill_y + 96
    pygame.draw.line(
        game.screen, CARD_BORDER,
        (panel.x + 40, logros_y - 12), (panel.right - 40, logros_y - 12), 2
    )
    game.draw_pixel_text("LOGROS", w // 2, logros_y + 4, "subtitle", TEXT_MAIN, True)

    lista_logros = getattr(game, "lista_logros", None)
    logros_list = lista_logros.todos() if lista_logros else []
    pct_logros = lista_logros.porcentaje() if lista_logros else 0

    game.draw_pixel_text(
        f"Desbloqueados: {len(lista_logros.completados()) if lista_logros else 0}"
        f"/{len(logros_list)} ({pct_logros}%)",
        panel.x + 60, logros_y + 28, "small", TEXT_SOFT, False
    )

    logros_panel_y = logros_y + 52
    logros_panel_h = panel.bottom - logros_panel_y - 50
    ROW_H = 48
    ROW_STEP = 54
    visible_rows = max(1, logros_panel_h // ROW_STEP)
    _SCROLL = max(0, min(_SCROLL, max(0, len(logros_list) - visible_rows)))

    for i in range(_SCROLL, min(len(logros_list), _SCROLL + visible_rows)):
        logro = logros_list[i]
        row_y = logros_panel_y + (i - _SCROLL) * ROW_STEP
        row_rect = pygame.Rect(panel.x + 40, row_y, panel.width - 80, ROW_H)

        if logro.completo:
            # 🎨 ASSET_UI: Imagenes/UI/icono_logro_desbloqueado.png | 36x36 | Estrella dorada
            bg = (230, 245, 215)
            border = (60, 160, 60)
            nombre_color = TEXT_MAIN
            desc_color = TEXT_SOFT
        else:
            # 🎨 ASSET_UI: Imagenes/UI/icono_logro_bloqueado.png | 36x36 | Candado gris
            bg = (205, 210, 215)
            border = (150, 155, 165)
            nombre_color = (140, 145, 155)
            desc_color = (160, 165, 175)

        pygame.draw.rect(game.screen, bg, row_rect, 0, 6)
        pygame.draw.rect(game.screen, border, row_rect, 2, 6)

        # Ícono de estado (procedural)
        icon_x = row_rect.x + 12
        icon_y = row_rect.centery
        if logro.completo:
            pygame.draw.polygon(
                game.screen, (230, 180, 30),
                [(icon_x, icon_y - 8), (icon_x + 7, icon_y + 8),
                 (icon_x - 8, icon_y - 2), (icon_x + 8, icon_y - 2),
                 (icon_x - 7, icon_y + 8)]
            )
        else:
            pygame.draw.rect(game.screen, (120, 120, 140),
                             pygame.Rect(icon_x - 5, icon_y - 5, 10, 8), 0, 2)
            pygame.draw.rect(game.screen, (120, 120, 140),
                             pygame.Rect(icon_x - 7, icon_y, 14, 10), 0, 2)

        game.draw_pixel_text(
            logro.nombre, row_rect.x + 32, row_rect.y + 8, "small", nombre_color, False
        )
        desc_short = logro.descripcion[:50] + ".." if len(logro.descripcion) > 52 else logro.descripcion
        game.draw_pixel_text(
            desc_short, row_rect.x + 32, row_rect.y + 26, "small", desc_color, False
        )

    # Scrollbar
    if len(logros_list) > visible_rows:
        track = pygame.Rect(panel.right - 28, logros_panel_y, 14, logros_panel_h)
        pygame.draw.rect(game.screen, (190, 198, 178), track)
        thumb_h = max(28, int((visible_rows / len(logros_list)) * logros_panel_h))
        scroll_max = max(1, len(logros_list) - visible_rows)
        thumb_y = track.y + int((_SCROLL / scroll_max) * (logros_panel_h - thumb_h))
        pygame.draw.rect(game.screen, PIXEL_CYAN,
                         pygame.Rect(track.x + 2, thumb_y + 2, 10, thumb_h - 4), 0, 4)

    game.draw_pixel_text(
        "Rueda del raton: desplazar logros | ESC: volver",
        w // 2, panel.bottom - 24, "small", (62, 74, 98), True
    )


def handle_event(game, event):
    """Maneja eventos en la pantalla de Progreso."""
    global _SCROLL
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            game.transitions.request(game, "menu")
        elif event.key == pygame.K_DOWN:
            _SCROLL += 1
        elif event.key == pygame.K_UP:
            _SCROLL = max(0, _SCROLL - 1)
    if event.type == pygame.MOUSEWHEEL:
        _SCROLL = max(0, _SCROLL - event.y)
