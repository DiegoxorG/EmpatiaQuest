"""
Pantalla de Historia — muestra los capítulos/días del juego y las decisiones tomadas.

# 🎨 ASSET_UI: Imagenes/UI/capitulo_completado.png | 300x80 | Banner de capítulo completado estilo pixel
# 🎨 ASSET_UI: Imagenes/UI/capitulo_bloqueado.png  | 300x80 | Banner de capítulo bloqueado con candado
# 🎨 ASSET_UI: Imagenes/UI/icono_dia.png           | 40x40  | Icono de día del calendario escolar
"""

import pygame
from config import (
    CARD, CARD_HOVER, CARD_BORDER, BG_DARK, BG_MID, GRID,
    TEXT_MAIN, TEXT_SOFT, PIXEL_CYAN, PIXEL_PINK,
)

# Definición de los 5 días / capítulos de la historia
CAPITULOS = [
    {
        "dia": 1,
        "titulo": "Dia 1: Las primeras decisiones",
        "eventos": ["primer_dia", "voces_pasillo"],
        "descripcion": "El primer dia de clases y los pasillos del colegio.",
    },
    {
        "dia": 2,
        "titulo": "Dia 2: El mundo digital",
        "eventos": ["reenviado", "detras_agresor"],
        "descripcion": "El bullying no para en el colegio — sigue en el celular.",
    },
    {
        "dia": 3,
        "titulo": "Dia 3: El precio de encajar",
        "eventos": ["encajar", "broma"],
        "descripcion": "Ser aceptado puede costar mas de lo que parece.",
    },
    {
        "dia": 4,
        "titulo": "Dia 4: Cuando el dano es invisible",
        "eventos": ["rumores", "no_era_flojera"],
        "descripcion": "Algunos dolores no se ven, pero estan ahi.",
    },
    {
        "dia": 5,
        "titulo": "Dia 5: Quien eres tu",
        "eventos": ["racismo", "xenofobia"],
        "descripcion": "El final depende de cada decision que tomaste.",
    },
]


def _get_event_decision(decision_history, event_id):
    """Busca en el historial la decision tomada para un evento dado."""
    if not decision_history:
        return None
    for d in decision_history:
        if d.get("event_id") == event_id:
            return d
    return None


def _event_completed(decision_history, event_id):
    return _get_event_decision(decision_history, event_id) is not None


def draw(game):
    """Renderiza la pantalla de Historia."""
    game._draw_pixel_background()

    w, h = game.screen.get_size()
    title_y = 52

    game.draw_pixel_text("HISTORIA", w // 2, title_y, "title", TEXT_MAIN, True)
    game.draw_pixel_text(
        "Tus decisiones dia a dia", w // 2, title_y + 46, "small", TEXT_SOFT, True
    )

    decision_history = getattr(game, "decision_history", [])

    cap_w = min(340, (w - 80) // max(1, len(CAPITULOS)))
    cap_h = 380
    total_caps_w = cap_w * len(CAPITULOS) + 16 * (len(CAPITULOS) - 1)
    start_x = w // 2 - total_caps_w // 2
    cap_y = title_y + 90

    mouse_pos = pygame.mouse.get_pos()

    for i, cap in enumerate(CAPITULOS):
        cx = start_x + i * (cap_w + 16)
        cap_rect = pygame.Rect(cx, cap_y, cap_w, cap_h)

        # Determinar estado del capítulo
        completados_en_cap = sum(
            1 for eid in cap["eventos"] if _event_completed(decision_history, eid)
        )
        cap_completado = completados_en_cap == len(cap["eventos"])
        cap_en_progreso = 0 < completados_en_cap < len(cap["eventos"])
        cap_bloqueado = completados_en_cap == 0

        # Fondo del capítulo
        if cap_completado:
            bg_color = (220, 240, 210)
            border_color = (60, 160, 60)
            estado_text = "COMPLETADO"
            estado_color = (60, 160, 60)
        elif cap_en_progreso:
            bg_color = CARD_HOVER
            border_color = PIXEL_CYAN
            estado_text = "EN PROGRESO"
            estado_color = (30, 140, 200)
        else:
            # 🎨 ASSET_UI: Imagenes/UI/capitulo_bloqueado.png | 300x80 | Capítulo bloqueado con candado
            bg_color = (190, 195, 200)
            border_color = (130, 130, 150)
            estado_text = "BLOQUEADO"
            estado_color = (130, 130, 150)

        shadow = cap_rect.move(4, 4)
        pygame.draw.rect(game.screen, (13, 12, 24), shadow)
        pygame.draw.rect(game.screen, bg_color, cap_rect)
        pygame.draw.rect(game.screen, border_color, cap_rect, 4)

        # Título del capítulo
        game.draw_pixel_text(
            cap["titulo"], cap_rect.centerx, cap_rect.y + 28,
            "small", TEXT_MAIN, True
        )

        # Estado
        game.draw_pixel_text(
            estado_text, cap_rect.centerx, cap_rect.y + 56,
            "small", estado_color, True
        )

        # Línea separadora
        pygame.draw.line(
            game.screen, border_color,
            (cap_rect.x + 16, cap_rect.y + 72),
            (cap_rect.right - 16, cap_rect.y + 72), 2
        )

        # Eventos del capítulo
        ey = cap_rect.y + 86
        for eid in cap["eventos"]:
            dec = _get_event_decision(decision_history, eid)
            if dec:
                label = dec.get("option_label", "Decision tomada")
                # Truncar label para que quepa
                if len(label) > 28:
                    label = label[:26] + ".."
                df = dec.get("dF", 0)
                color = (60, 160, 60) if df > 0 else (200, 60, 60) if df < 0 else TEXT_SOFT
                game.draw_pixel_text(
                    f"> {label}", cap_rect.x + 12, ey, "small", color, False
                )
                thought = dec.get("thought", "")
                if thought:
                    if len(thought) > 32:
                        thought = thought[:30] + ".."
                    game.draw_pixel_text(
                        f"  {thought}", cap_rect.x + 12, ey + 22,
                        "small", TEXT_SOFT, False
                    )
                ey += 54
            elif not cap_bloqueado:
                game.draw_pixel_text(
                    "- Pendiente...", cap_rect.x + 12, ey, "small", TEXT_SOFT, False
                )
                ey += 30
            else:
                game.draw_pixel_text(
                    "- ???", cap_rect.x + 12, ey, "small", (160, 160, 170), False
                )
                ey += 30

        # Descripción del día
        desc = cap["descripcion"]
        if len(desc) > 36:
            desc = desc[:34] + ".."
        game.draw_pixel_text(
            desc, cap_rect.centerx, cap_rect.bottom - 26, "small", TEXT_SOFT, True
        )

    # Estadísticas rápidas al fondo
    story_completed = getattr(game, "story_completed", 0)
    story_goal = getattr(game, "story_goal", 12)
    pct = int((story_completed / max(1, story_goal)) * 100)
    game.draw_pixel_text(
        f"Eventos completados: {story_completed}/{story_goal} ({pct}%)",
        w // 2, h - 46, "small", TEXT_SOFT, True
    )
    game.draw_pixel_text(
        "ESC para volver al menu", w // 2, h - 24, "small", (62, 74, 98), True
    )


def handle_event(game, event):
    """Maneja eventos de teclado/ratón en la pantalla Historia."""
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            game.transitions.request(game, "menu")
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pass  # Reservado para futuras interacciones con capítulos
