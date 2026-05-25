"""
Pantalla de Créditos — scroll automático con el equipo, herramientas y licencias.

# 🎨 ASSET_UI: Imagenes/UI/logo_empatia_quest.png | 600x200 | Logo del juego en estilo pixel-art
"""

import pygame
from config import (
    CARD, CARD_BORDER, TEXT_MAIN, TEXT_SOFT,
    PIXEL_CYAN, PIXEL_PINK, BG_DARK,
)

# Velocidad de scroll automático en píxeles por segundo
_SCROLL_SPEED = 42
_scroll_y = 0      # posición actual del scroll (módulo-level)
_paused = False    # el usuario puede pausar el scroll con ESPACIO

_CREDITOS = [
    ("titulo",    "EMPATIA QUEST"),
    ("subtitulo", "Un juego sobre empatia en el entorno escolar"),
    ("separador", ""),
    ("seccion",   "EQUIPO DE DESARROLLO"),
    ("separador", ""),
    ("rol",       "Diseno y Programacion"),
    ("nombre",    "DiegoxorG"),
    ("separador", ""),
    ("rol",       "Historia y Narrativa"),
    ("nombre",    "EmpatiaQuest Team"),
    ("separador", ""),
    ("rol",       "Arte y Diseno Visual"),
    ("nombre",    "EmpatiaQuest Team"),
    ("separador", ""),
    ("rol",       "Fondos y Escenarios"),
    ("nombre",    "Creados especialmente para este proyecto"),
    ("separador", ""),
    ("seccion",   "HERRAMIENTAS"),
    ("separador", ""),
    ("item",      "Python 3.11"),
    ("item",      "Pygame 2.6.1"),
    ("item",      "VS Code"),
    ("item",      "Hitbox Editor (herramienta interna)"),
    ("item",      "Personaje Editor (herramienta interna)"),
    ("separador", ""),
    ("seccion",   "FUENTES"),
    ("separador", ""),
    ("item",      "Determination Mono Web"),
    ("item",      "Determination Sans Web"),
    ("texto",     "Licencia: Creative Commons (by-nc-nd)"),
    ("texto",     "Attribution Non-commercial No Derivatives"),
    ("texto",     "fontspace.com/determination-mono-web-font-f23209"),
    ("separador", ""),
    ("seccion",   "AGRADECIMIENTOS"),
    ("separador", ""),
    ("texto",     "A quienes alguna vez hablaron cuando era facil"),
    ("texto",     "quedarse callados."),
    ("separador", ""),
    ("texto",     "A quienes aprendieron que la empatia"),
    ("texto",     "no es debilidad, sino el acto mas valiente."),
    ("separador", ""),
    ("separador", ""),
    ("titulo",    "EMPATIA QUEST"),
    ("subtitulo", "2024 — Universidad del Norte"),
    ("separador", ""),
    ("separador", ""),
    ("separador", ""),
]

_LINE_HEIGHTS = {
    "titulo":    64,
    "subtitulo": 38,
    "seccion":   46,
    "rol":       30,
    "nombre":    34,
    "item":      28,
    "texto":     28,
    "separador": 22,
}

_LINE_COLORS = {
    "titulo":    (245, 248, 255),
    "subtitulo": (198, 220, 255),
    "seccion":   PIXEL_CYAN,
    "rol":       TEXT_SOFT,
    "nombre":    TEXT_MAIN,
    "item":      TEXT_SOFT,
    "texto":     TEXT_SOFT,
    "separador": (0, 0, 0, 0),
}

_FONT_STYLE = {
    "titulo":    "title",
    "subtitulo": "subtitle",
    "seccion":   "subtitle",
    "rol":       "small",
    "nombre":    "body",
    "item":      "small",
    "texto":     "small",
    "separador": "small",
}

_total_height = sum(_LINE_HEIGHTS.get(t, 28) for t, _ in _CREDITOS)


def _reset():
    global _scroll_y, _paused
    _scroll_y = 0
    _paused = False


def draw(game):
    """Renderiza la pantalla de Créditos con scroll automático."""
    global _scroll_y, _paused

    screen = game.screen
    w, h = screen.get_size()
    screen.fill(BG_DARK)

    dt_ms = game.clock.get_time()
    if not _paused:
        _scroll_y += (_SCROLL_SPEED * dt_ms) / 1000.0

    # Reiniciar si terminó el scroll
    if _scroll_y > _total_height + h:
        _scroll_y = -h * 0.5

    # 🎨 ASSET_UI: Imagenes/UI/logo_empatia_quest.png | 600x200 | Logo estilo pixel-art
    # (procedural fallback: renderizado con texto)

    current_y = h // 2 - int(_scroll_y)

    for tipo, texto in _CREDITOS:
        lh = _LINE_HEIGHTS.get(tipo, 28)
        if current_y + lh < -10 or current_y > h + 10:
            current_y += lh
            continue

        if tipo != "separador":
            color = _LINE_COLORS.get(tipo, TEXT_SOFT)
            style = _FONT_STYLE.get(tipo, "small")
            game.draw_pixel_text(texto, w // 2, current_y + lh // 2, style, color, True)

        current_y += lh

    # Degradados superior e inferior para suavizar la entrada/salida
    for grad_y, direction in [(0, 1), (h - 80, -1)]:
        for line in range(80):
            alpha = int(255 * (line / 80))
            if direction == 1:
                a = 255 - alpha
            else:
                a = alpha
            surf = pygame.Surface((w, 1))
            surf.fill(BG_DARK)
            surf.set_alpha(a)
            screen.blit(surf, (0, grad_y + line))

    # Hint de controles
    game.draw_pixel_text(
        "ESC volver | ESPACIO pausar scroll",
        w // 2, h - 24, "small", (62, 74, 98), True
    )


def handle_event(game, event):
    """Maneja eventos en la pantalla de Créditos."""
    global _scroll_y, _paused
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            _reset()
            game.transitions.request(game, "menu")
        elif event.key == pygame.K_SPACE:
            _paused = not _paused
        elif event.key == pygame.K_DOWN:
            _scroll_y += 40
        elif event.key == pygame.K_UP:
            _scroll_y = max(-game.screen.get_height() * 0.5, _scroll_y - 40)
    if event.type == pygame.MOUSEWHEEL:
        _scroll_y -= event.y * 30
