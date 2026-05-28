"""
Pantalla de Tutorial - explica las mec?nicas del juego en 3 p?ginas.

# [UI] ASSET_UI: Imagenes/UI/tutorial_controles.png  | 800x400 | Diagrama de controles del teclado
# [UI] ASSET_UI: Imagenes/UI/tutorial_stats.png      | 800x400 | Diagrama de barras F y R
# [UI] ASSET_UI: Imagenes/UI/tutorial_decisiones.png | 800x400 | Diagrama del sistema de decisiones
"""

import pygame
from config import (
    CARD, CARD_HOVER, CARD_BORDER, TEXT_MAIN, TEXT_SOFT,
    PIXEL_CYAN, PIXEL_PINK,
)

_PAGE = 0   # P?gina actual del tutorial (persistente en sesi?n)
_TOTAL_PAGES = 3


def _draw_key(game, label, x, y, w=64, h=40):
    """Dibuja una tecla estilo pixel-art con su etiqueta."""
    rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
    pygame.draw.rect(game.screen, (230, 235, 225), rect, 0, 6)
    pygame.draw.rect(game.screen, CARD_BORDER, rect, 3, 6)
    game.draw_pixel_text(label, x, y, "small", TEXT_MAIN, True)
    return rect


def _draw_page_0(game, panel):
    """P?gina 1: Controles."""
    # [UI] ASSET_UI: Imagenes/UI/tutorial_controles.png | 800x400 | Diagrama WASD y acciones
    game.draw_pixel_text(
        "CONTROLES", panel.centerx, panel.y + 100, "subtitle", TEXT_MAIN, True
    )

    center_x = panel.centerx - 80
    wasd_y = panel.y + 175

    # Tecla W (arriba)
    _draw_key(game, "W", center_x, wasd_y - 46)
    # Teclas A S D
    _draw_key(game, "A", center_x - 50, wasd_y)
    _draw_key(game, "S", center_x, wasd_y)
    _draw_key(game, "D", center_x + 50, wasd_y)

    game.draw_pixel_text("Mover al personaje", center_x + 120, wasd_y, "small", TEXT_SOFT, False)

    # Tecla E
    _draw_key(game, "E", center_x, wasd_y + 60)
    game.draw_pixel_text("Interactuar / Elegir silla", center_x + 120, wasd_y + 60, "small", TEXT_SOFT, False)

    # Teclas 1-5
    nums_x = center_x - 80
    _draw_key(game, "1-5", nums_x + 80, wasd_y + 120, w=80)
    game.draw_pixel_text("Elegir opción en eventos", center_x + 120, wasd_y + 120, "small", TEXT_SOFT, False)

    # F5
    _draw_key(game, "F5", center_x, wasd_y + 180, w=64)
    game.draw_pixel_text("Guardar partida rápida", center_x + 120, wasd_y + 180, "small", TEXT_SOFT, False)

    # ESC
    _draw_key(game, "ESC", center_x, wasd_y + 230, w=64)
    game.draw_pixel_text("Abrir menú de pausa", center_x + 120, wasd_y + 230, "small", TEXT_SOFT, False)

    # TAB
    _draw_key(game, "TAB", center_x, wasd_y + 280, w=64)
    game.draw_pixel_text("Ver inventario de habilidades", center_x + 120, wasd_y + 280, "small", TEXT_SOFT, False)


def _draw_page_1(game, panel):
    """P?gina 2: Sistema de estad?sticas."""
    # [UI] ASSET_UI: Imagenes/UI/tutorial_stats.png | 800x400 | Diagrama de F y R
    game.draw_pixel_text(
        "ESTADÍSTICAS", panel.centerx, panel.y + 100, "subtitle", TEXT_MAIN, True
    )

    content_y = panel.y + 145
    bar_w = 340
    bar_h = 28
    bx = panel.centerx - bar_w // 2

    # Felicidad
    pygame.draw.rect(game.screen, (200, 208, 192), (bx, content_y, bar_w, bar_h))
    pygame.draw.rect(game.screen, CARD_BORDER, (bx, content_y, bar_w, bar_h), 2)
    pygame.draw.rect(game.screen, (245, 170, 70), (bx, content_y, bar_w // 2, bar_h))
    game.draw_pixel_text("F - Felicidad (0-100)", bx, content_y - 16, "small", TEXT_MAIN, False)
    game.draw_pixel_text(
        "Sube cuando tomas decisiones empaticas.",
        bx, content_y + bar_h + 10, "small", TEXT_SOFT, False
    )
    game.draw_pixel_text(
        "Baja cuando ignoras o participas en el daño.",
        bx, content_y + bar_h + 30, "small", TEXT_SOFT, False
    )

    content_y += 90
    # Reputaci?n
    pygame.draw.rect(game.screen, (200, 208, 192), (bx, content_y, bar_w, bar_h))
    pygame.draw.rect(game.screen, CARD_BORDER, (bx, content_y, bar_w, bar_h), 2)
    pygame.draw.rect(game.screen, (90, 190, 255), (bx, content_y, int(bar_w * 0.7), bar_h))
    game.draw_pixel_text("R - Reputación (0-100)", bx, content_y - 16, "small", TEXT_MAIN, False)
    game.draw_pixel_text(
        "Sube cuando encajas socialmente (aunque no siempre es bueno).",
        bx, content_y + bar_h + 10, "small", TEXT_SOFT, False
    )
    game.draw_pixel_text(
        "Baja cuando vas contra el grupo popular.",
        bx, content_y + bar_h + 30, "small", TEXT_SOFT, False
    )

    content_y += 100
    # Cuatro finales
    game.draw_pixel_text(
        "LOS 4 FINALES", panel.centerx, content_y, "small", TEXT_MAIN, True
    )
    finales = [
        ("F>=50 y R>=50", "Final Positivo", (60, 160, 60)),
        ("F<50 y R<50", "Final Negativo", (200, 60, 60)),
        ("F<50, R>=50", "Neutral - Rep alta", (200, 160, 30)),
        ("F>=50, R<50", "Neutral - F alta", (30, 160, 200)),
    ]
    for j, (cond, nombre, color) in enumerate(finales):
        fx = panel.x + 60 + j * (panel.width - 120) // 4
        fy = content_y + 26
        game.draw_pixel_text(nombre, fx, fy, "small", color, False)
        game.draw_pixel_text(cond, fx, fy + 20, "small", TEXT_SOFT, False)


def _draw_page_2(game, panel):
    """P?gina 3: Sistema de decisiones y habilidades."""
    # [UI] ASSET_UI: Imagenes/UI/tutorial_decisiones.png | 800x400 | Diagrama del flujo de decisiones
    game.draw_pixel_text(
        "DECISIONES Y HABILIDADES", panel.centerx, panel.y + 100, "subtitle", TEXT_MAIN, True
    )

    content_y = panel.y + 145
    px = panel.x + 60
    pw = panel.width - 120

    lineas = [
        ("Cómo funcionan los eventos:", TEXT_MAIN),
        ("  1. Exploras el mapa del colegio.", TEXT_SOFT),
        ("  2. Aparece un evento narrativo con opciones (1-5).", TEXT_SOFT),
        ("  3. Tu elección modifica F (Felicidad) y R (Reputación).", TEXT_SOFT),
        ("  4. Algunas opciones desbloquean Logros y suben Habilidades.", TEXT_SOFT),
        ("", TEXT_SOFT),
        ("Las 5 Habilidades:", TEXT_MAIN),
        ("  Escucha Activa     - sube al consolar o escuchar.", TEXT_SOFT),
        ("  Intervención Pac.  - sube al defender con calma.", TEXT_SOFT),
        ("  Empatía Digital    - sube al actuar bien en ciberbullying.", TEXT_SOFT),
        ("  Valentía Social    - sube al negarte a participar en el daño.", TEXT_SOFT),
        ("  Mediación          - sube al buscar soluciones dialogadas.", TEXT_SOFT),
        ("", TEXT_SOFT),
        ("Abre tu inventario de habilidades con TAB en cualquier momento.", (30, 140, 200)),
    ]

    for texto, color in lineas:
        game.draw_pixel_text(texto, px, content_y, "small", color, False)
        content_y += 28


def draw(game):
    """Renderiza la pantalla de Tutorial."""
    global _PAGE
    game._draw_pixel_background()

    w, h = game.screen.get_size()
    panel = pygame.Rect(w // 2 - 520, 30, 1040, h - 60)
    shadow = panel.move(5, 5)
    pygame.draw.rect(game.screen, (13, 12, 24), shadow)
    pygame.draw.rect(game.screen, CARD, panel)
    pygame.draw.rect(game.screen, CARD_BORDER, panel, 5)

    game.draw_pixel_text("TUTORIAL", w // 2, panel.y + 44, "title", TEXT_MAIN, True)

    page_names = ["Controles", "Estadísticas y Finales", "Decisiones y Habilidades"]
    game.draw_pixel_text(
        f"({_PAGE + 1}/{_TOTAL_PAGES}) {page_names[_PAGE]}",
        w // 2, panel.y + 76, "small", TEXT_SOFT, True
    )

    # L?nea separadora
    pygame.draw.line(
        game.screen, CARD_BORDER,
        (panel.x + 40, panel.y + 90), (panel.right - 40, panel.y + 90), 2
    )

    if _PAGE == 0:
        _draw_page_0(game, panel)
    elif _PAGE == 1:
        _draw_page_1(game, panel)
    else:
        _draw_page_2(game, panel)

    # Navegaci?n
    nav_y = panel.bottom - 48
    mouse_pos = pygame.mouse.get_pos()

    if _PAGE > 0:
        prev_rect = pygame.Rect(panel.x + 40, nav_y, 160, 36)
        prev_hover = prev_rect.collidepoint(mouse_pos)
        pygame.draw.rect(game.screen, CARD_HOVER if prev_hover else (208, 216, 196), prev_rect, 0, 6)
        pygame.draw.rect(game.screen, CARD_BORDER, prev_rect, 2, 6)
        game.draw_pixel_text("< Anterior", prev_rect.centerx, prev_rect.centery, "small", TEXT_MAIN, True)

    if _PAGE < _TOTAL_PAGES - 1:
        next_rect = pygame.Rect(panel.right - 200, nav_y, 160, 36)
        next_hover = next_rect.collidepoint(mouse_pos)
        pygame.draw.rect(game.screen, CARD_HOVER if next_hover else (208, 216, 196), next_rect, 0, 6)
        pygame.draw.rect(game.screen, CARD_BORDER, next_rect, 2, 6)
        game.draw_pixel_text("Siguiente >", next_rect.centerx, next_rect.centery, "small", TEXT_MAIN, True)

    game.draw_pixel_text(
        "ESC volver | Flechas izq/der cambiar página",
        w // 2, panel.bottom - 22, "small", (62, 74, 98), True
    )


def handle_event(game, event):
    """Maneja eventos en la pantalla de Tutorial."""
    global _PAGE
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            game.transitions.request(game, "menu")
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            _PAGE = min(_TOTAL_PAGES - 1, _PAGE + 1)
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            _PAGE = max(0, _PAGE - 1)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        w, h = game.screen.get_size()
        panel = pygame.Rect(w // 2 - 520, 30, 1040, h - 60)
        nav_y = panel.bottom - 48
        prev_rect = pygame.Rect(panel.x + 40, nav_y, 160, 36)
        next_rect = pygame.Rect(panel.right - 200, nav_y, 160, 36)
        if prev_rect.collidepoint(event.pos) and _PAGE > 0:
            _PAGE -= 1
        elif next_rect.collidepoint(event.pos) and _PAGE < _TOTAL_PAGES - 1:
            _PAGE += 1

