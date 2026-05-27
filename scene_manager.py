"""
SceneManager — sistema de escenas cinemáticas para EmpatiaQuest.

Beats disponibles
─────────────────
  DialogBeat(personaje, texto, duracion_min, avanza_con, tiempo_ms, condition, camera_rx, camera_ry)
      personaje   : str  — nombre del personaje que habla
      texto       : str  — texto que aparece con efecto typewriter
      duracion_min: int  — ms mínimos antes de poder avanzar (bloquea el clic prematuro)
      avanza_con  : str  — "click" | "auto" | "tiempo"
      tiempo_ms   : int  — solo para avanza_con=="tiempo": ms totales hasta auto-avanzar
      condition   : callable(game) → bool  — si no None y devuelve False, el beat se salta
      camera_rx   : float  — si no None, pana la cámara aquí (normalizado) al iniciar el beat
      camera_ry   : float

  WaitBeat(condicion, timeout_ms)
      condicion  : callable(game) → bool  — avanza cuando devuelve True
      timeout_ms : int  — si > 0, fuerza avance tras este tiempo aunque no se cumpla la condición

  ActionBeat(funcion)
      funcion : callable(game)  — se ejecuta inmediatamente y avanza al siguiente beat

Uso
───
    game.scene_manager = get_scene_dia1_salon(player_name)
    game.escena_activa  = "dia1_salon"

    # En _update_adventure (cada frame):
    scene_manager.update(dt_ms, game)

    # En _handle_adventure_events (después del check de intro):
    if game.escena_activa:
        if scene_manager.handle_input(event):
            return

    # En _draw_adventure_screen (antes del status bar):
    if game.escena_activa:
        scene_manager.draw(screen, game.base_fonts, game.width, game.height)
        return

# 🎵 ASSET_SFX: Audio/SFX/dialogo_letra.ogg | sonido typewriter por carácter
# 🎨 ASSET_UI: Imagenes/UI/caja_dialogo.png  | 1280x140 | fondo decorativo de caja de diálogo
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional
import pygame


# ── Colores por personaje ─────────────────────────────────────────────────────

_SPEAKER_COLORS: dict[str, tuple] = {
    "diego":  (74,  158, 255),
    "sara":   (126, 203, 161),
    "profe":  (220, 180,  80),
    "npc":    (170, 170, 170),
    "lucas":  (255, 180, 100),
    "carlos": (200, 130, 255),
    "mateo":  (255, 200,  80),
    "andres": (100, 220, 180),
}
_DEFAULT_COLOR = (255, 255, 255)   # jugador / cualquier otro


def _speaker_color(name: str) -> tuple:
    return _SPEAKER_COLORS.get(name.lower(), _DEFAULT_COLOR)


# ── Beat types ────────────────────────────────────────────────────────────────

@dataclass
class DialogBeat:
    personaje:    str
    texto:        str
    duracion_min: int   = 0         # ms mínimos antes de poder avanzar
    avanza_con:   str   = "click"   # "click" | "auto" | "tiempo"
    tiempo_ms:    int   = 2000
    condition:    object = None     # callable(game) → bool; None = siempre mostrar
    camera_rx:    Optional[float] = None   # paneo cámara al iniciar (normalizado)
    camera_ry:    Optional[float] = None


@dataclass
class WaitBeat:
    condicion:  object = None  # callable(game) → bool
    timeout_ms: int    = 0


@dataclass
class ActionBeat:
    funcion: object    # callable(game)


# ── SceneManager ──────────────────────────────────────────────────────────────

class SceneManager:
    _TYPEWRITER_MS: int = 40    # ms por carácter
    _BOX_H:         int = 140   # altura de la caja de diálogo

    def __init__(self, beats: list) -> None:
        self.beats      = beats
        self.beat_index = 0
        self._tw_text:  str   = ""
        self._tw_timer: float = 0.0   # acumulador ms del beat actual
        self._wait_ms:  float = 0.0   # acumulador para WaitBeat timeout
        self.done       = False

    # ── Acceso ────────────────────────────────────────────────────────────────

    def _current(self):
        if self.beat_index >= len(self.beats):
            return None
        return self.beats[self.beat_index]

    def _advance(self) -> None:
        self.beat_index += 1
        self._tw_text   = ""
        self._tw_timer  = 0.0
        self._wait_ms   = 0.0
        if self.beat_index >= len(self.beats):
            self.done = True

    @property
    def is_blocking_interaction(self) -> bool:
        """True durante DialogBeat — la tecla E no debe disparar interacciones."""
        return isinstance(self._current(), DialogBeat)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt_ms: int, game) -> None:
        while True:
            beat = self._current()
            if beat is None:
                self.done = True
                return

            # ── ActionBeat: ejecutar y avanzar ──────────────────────────────
            if isinstance(beat, ActionBeat):
                try:
                    beat.funcion(game)
                except Exception:
                    pass
                self._advance()
                continue

            # ── WaitBeat ─────────────────────────────────────────────────────
            if isinstance(beat, WaitBeat):
                if beat.condicion is not None and beat.condicion(game):
                    self._advance()
                    continue
                if beat.timeout_ms > 0:
                    self._wait_ms += dt_ms
                    if self._wait_ms >= beat.timeout_ms:
                        self._advance()
                        continue
                return

            # ── DialogBeat ───────────────────────────────────────────────────
            if isinstance(beat, DialogBeat):
                # Primera entrada: verificar condición y aplicar cámara
                if self._tw_timer == 0.0 and self._tw_text == "":
                    if beat.condition is not None and not beat.condition(game):
                        self._advance()
                        continue
                    if beat.camera_rx is not None and beat.camera_ry is not None:
                        game.camera_mode   = "cinematic"
                        game.camera_lerp   = 0.05
                        game.camera_target = (
                            int(beat.camera_rx * game.story_world_width),
                            int(beat.camera_ry * game.story_world_height),
                        )
                        game.camera_return_after_ms = 0  # cancelar retorno automático

                self._tw_timer += dt_ms

                # Avanzar typewriter
                if len(self._tw_text) < len(beat.texto):
                    chars = min(len(beat.texto),
                                int(self._tw_timer / self._TYPEWRITER_MS))
                    self._tw_text = beat.texto[:chars]

                # Auto-avance para "auto" y "tiempo"
                text_done_at = len(beat.texto) * float(self._TYPEWRITER_MS)
                if beat.avanza_con == "auto":
                    if self._tw_timer >= text_done_at:
                        self._advance()
                        continue
                elif beat.avanza_con == "tiempo":
                    if self._tw_timer >= max(text_done_at, float(beat.tiempo_ms)):
                        self._advance()
                        continue
                return   # "click" — esperar input

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle_input(self, event: pygame.event.Event) -> bool:
        """
        Procesa un evento de pygame.
        Devuelve True si el evento fue consumido (no pasarlo al resto del juego).
        """
        if event.type != pygame.KEYDOWN:
            return False
        if event.key not in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            return False

        beat = self._current()
        if beat is None:
            return False

        if isinstance(beat, DialogBeat) and beat.avanza_con == "click":
            # Bloquear durante duracion_min
            if self._tw_timer < float(beat.duracion_min):
                return True
            if len(self._tw_text) < len(beat.texto):
                # Saltar typewriter: mostrar texto completo
                self._tw_text  = beat.texto
                self._tw_timer = float(len(beat.texto) * self._TYPEWRITER_MS)
            else:
                self._advance()
            return True

        return False

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface, fonts: dict,
             width: int, height: int) -> None:
        beat = self._current()
        if beat is None or isinstance(beat, ActionBeat):
            return
        self._draw_box(screen, fonts, width, height, beat)

    def _draw_box(self, screen: pygame.Surface, fonts: dict,
                  width: int, height: int, beat) -> None:
        BOX_H = self._BOX_H
        box_y = height - BOX_H

        # ── Fondo ────────────────────────────────────────────────────────────
        bg = pygame.Surface((width, BOX_H), pygame.SRCALPHA)
        bg.fill((10, 12, 22, 200))
        screen.blit(bg, (0, box_y))

        # ── Diálogo ───────────────────────────────────────────────────────────
        if isinstance(beat, DialogBeat):
            color     = _speaker_color(beat.personaje)
            is_player = color == _DEFAULT_COLOR  # pensamiento del jugador

            # Línea de color superior (identifica al personaje)
            pygame.draw.line(screen, color, (0, box_y), (width, box_y), 2)

            font_small = fonts.get("small") or fonts.get("body")
            font_body  = fonts.get("body")  or font_small

            # Nombre del personaje
            if font_small and beat.personaje:
                label = f"✦ {beat.personaje}" if is_player else beat.personaje
                name_surf = font_small.render(label, True, color)
                name_bg   = pygame.Rect(16, box_y - 30,
                                        name_surf.get_width() + 20, 28)
                pygame.draw.rect(screen, (10, 12, 22), name_bg)
                pygame.draw.rect(screen, color, name_bg, 2)
                screen.blit(name_surf, (name_bg.x + 10, name_bg.y + 4))

            # Texto con typewriter + word-wrap
            if font_body:
                display_text = self._tw_text
                # pensamiento en cursiva visual: añadir comillas
                if is_player:
                    display_text = f"\"{display_text}"
                    if len(self._tw_text) >= len(beat.texto):
                        display_text += "\""

                max_w = width - 48
                words: list[str] = display_text.split(" ")
                lines: list[str] = []
                cur = ""
                for word in words:
                    test = (cur + " " + word).strip() if cur else word
                    if font_body.size(test)[0] <= max_w:
                        cur = test
                    else:
                        if cur:
                            lines.append(cur)
                        cur = word
                if cur:
                    lines.append(cur)

                text_color = (220, 230, 255) if is_player else (245, 248, 255)
                line_h = font_body.get_height() + 4
                ty     = box_y + 32
                for line in lines[:3]:
                    surf = font_body.render(line, True, text_color)
                    screen.blit(surf, (24, ty))
                    ty += line_h

            # Indicador ▼ (parpadea cuando texto completo + beat "click")
            full = len(self._tw_text) >= len(beat.texto)
            waiting_click = beat.avanza_con == "click" and full
            past_min = self._tw_timer >= float(beat.duracion_min)
            if waiting_click and past_min:
                ind_font = font_small or font_body
                if ind_font and (pygame.time.get_ticks() // 500) % 2:
                    ind = ind_font.render("▼", True, (180, 180, 180))
                    screen.blit(ind, (width - ind.get_width() - 24,
                                      height - ind.get_height() - 6))

        # ── WaitBeat ─────────────────────────────────────────────────────────
        elif isinstance(beat, WaitBeat):
            pygame.draw.line(screen, (200, 200, 100), (0, box_y), (width, box_y), 2)
            font_body = fonts.get("body") or fonts.get("small")
            if font_body:
                surf = font_body.render(
                    "Elige dónde sentarte y presiona  E", True, (220, 220, 160))
                screen.blit(surf, (24, box_y + 38))
            if font_body and (pygame.time.get_ticks() // 700) % 2:
                hint = font_body.render(
                    "E — interactuar con un pupitre libre", True, (140, 200, 140))
                screen.blit(hint, (24, box_y + 80))


# ── Escenas predefinidas ──────────────────────────────────────────────────────

def get_scene_dia1_salon(player_name: str) -> SceneManager:
    """
    Retorna la escena cinemática del Día 1 — primer ingreso al salón.

    Beats:
        1. ActionBeat  — bloquea movimiento, paneo cámara al salón
        2. DialogBeat  — jugador piensa "¿Dónde debería sentarme...?"  (auto 2500ms)
        3. DialogBeat  — Diego "Ey, acá hay puesto."  (click; cámara a Diego)
        4. ActionBeat  — desbloquea movimiento, activa eligiendo_asiento
        5. WaitBeat    — espera jugador_sentado (timeout 60s)
        6. ActionBeat  — evalúa zona + aplica stats
        7. DialogBeat  — NPC "Ella siempre anda sola..." (sólo si zona sara)
        8. ActionBeat  — marca escena completada
    """
    pname = player_name or "Protagonista"

    # ── Beat 1 ────────────────────────────────────────────────────────────────
    def beat1_bloquear_y_panear(game):
        game.player_can_move    = False
        game.camera_mode        = "cinematic"
        game.camera_lerp        = 0.04
        # Paneo hacia el centro del salón para mostrar a los NPCs sentados
        game.camera_target      = (
            game.story_world_width  // 2,
            int(game.story_world_height * 0.38),
        )
        game.camera_return_after_ms = 1500   # vuelve al jugador automáticamente

    # ── Beat 4 ────────────────────────────────────────────────────────────────
    def beat4_desbloquear(game):
        game.player_can_move   = True
        game.camera_mode       = "follow_player"
        game.eligiendo_asiento = True

    # ── Beat 6 ────────────────────────────────────────────────────────────────
    def beat6_evaluar_asiento(game):
        """
        Usa la posición del pupitre elegido para determinar la zona.
          D7 (index 6 deco): x≈0.288, y≈0.725  → sara_zone  → F+2, R-1
          D8 (index 7 deco): x≈0.447, y≈0.722  → diego_zone → F-3, R+2
          D3 está ocupado por NPC2 → no accesible para el jugador.
          Sin elección (timeout)   → ninguno → F+0, R+0
        """
        seated_h = (getattr(game, "story_seated_pupitre", None)
                    or getattr(game, "story_seated_hitbox",  None))

        result = "ninguno"
        df, dr = 0, 0

        if seated_h:
            rx = float(seated_h.get("rx", 0.5))
            ry = float(seated_h.get("ry", 0.5))
            if rx < 0.35 and ry > 0.65:           # D7 — junto a Sara
                result, df, dr = "sara",  +2, -1
            elif 0.35 <= rx < 0.65 and ry > 0.65: # D8 — junto a Diego
                result, df, dr = "diego", -3, +2

        game.decision_dia1_asiento = result
        game._sm_dia1_result       = result   # usado por beat 7

        game.story_felicidad  = max(0, min(100, game.story_felicidad  + df))
        game.story_reputacion = max(0, min(100, game.story_reputacion + dr))

        pname_inner = getattr(game, "player_name", "") or "Protagonista"
        thoughts = {
            "sara":   "Me senté cerca de Sara.",
            "diego":  "Me senté cerca de Diego.",
            "ninguno": "",
        }
        game.story_thought = thoughts.get(result, "")

        game.decision_history.append({
            "event_id":     "primer_dia_asiento",
            "option_label": result,
            "dF": df, "dR": dr,
            "thought": game.story_thought,
        })
        game.story_completed += 1
        if game.story_completed >= game.story_goal:
            game._resolve_ending()

    # ── Beat 8 ────────────────────────────────────────────────────────────────
    def beat8_completar(game):
        game.escena_dia1_completada = True
        game.eligiendo_asiento      = False
        game.player_can_move        = True
        game.escena_activa          = None
        npc_mgr = getattr(game, "npc_ai_manager", None)
        if npc_mgr is not None:
            npc_mgr.notify_phase("en_clase")

    # Diego está en decoracion index 8: x≈0.610, y≈0.716
    _DIEGO_RX, _DIEGO_RY = 0.610, 0.716

    return SceneManager([
        # 1 — bloquear + paneo general
        ActionBeat(beat1_bloquear_y_panear),

        # 2 — pensamiento del jugador (auto, 2500ms)
        DialogBeat(
            pname, "¿Dónde debería sentarme...?",
            avanza_con="tiempo", tiempo_ms=2500,
        ),

        # 3 — Diego habla; cámara se mueve hacia su pupitre
        DialogBeat(
            "Diego", "Ey, acá hay puesto.",
            avanza_con="click",
            camera_rx=_DIEGO_RX, camera_ry=_DIEGO_RY,
        ),

        # 4 — desbloquear movimiento y activar elección de asiento
        ActionBeat(beat4_desbloquear),

        # 5 — esperar que el jugador se siente (1 minuto de timeout)
        WaitBeat(
            condicion=lambda g: bool(getattr(g, "jugador_sentado", False)),
            timeout_ms=60_000,
        ),

        # 6 — evaluar zona y aplicar stats
        ActionBeat(beat6_evaluar_asiento),

        # 7 — comentario de NPC si el jugador se sentó con Sara
        DialogBeat(
            "NPC", "Ella siempre anda sola...",
            avanza_con="tiempo", tiempo_ms=2000,
            condition=lambda g: getattr(g, "_sm_dia1_result", "") == "sara",
        ),

        # 8 — marcar escena completada
        ActionBeat(beat8_completar),
    ])
