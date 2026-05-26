"""
SceneManager — sistema de escenas cinemáticas para EmpatiaQuest.

Beats disponibles:
    DialogBeat(speaker, text, color)   — diálogo con efecto typewriter
    WaitBeat(condition, prompt_text)   — espera hasta que game.<condition> sea True
    ActionBeat(action, params)         — ejecuta una acción inmediata y avanza

Uso típico:
    game.scene_manager = get_scene_dia1_salon(player_name)
    game.escena_activa  = "dia1_salon"

    # En _update_adventure:
    if game.escena_activa:
        game.scene_manager.update(dt_ms, game)

    # En _handle_adventure_events (después del check de intro):
    if game.escena_activa:
        if game.scene_manager.handle_input(event):
            return

    # En _draw_adventure_screen (antes del status bar):
    if game.escena_activa:
        game.scene_manager.draw(screen, game.base_fonts, game.width, game.height)
        return
"""

from __future__ import annotations
import os
import pygame
from dataclasses import dataclass, field
from typing import Optional


# ── Beat types ─────────────────────────────────────────────────────────────────

@dataclass
class DialogBeat:
    speaker: str
    text: str
    color: tuple = (255, 255, 255)


@dataclass
class WaitBeat:
    condition: str = ""
    prompt_text: str = ""


@dataclass
class ActionBeat:
    action: str
    params: dict = field(default_factory=dict)


# ── SceneManager ───────────────────────────────────────────────────────────────

class SceneManager:
    _TYPEWRITER_MS: int = 40
    _BOX_H: int = 140

    def __init__(self, beats: list) -> None:
        self.beats = beats
        self.beat_index: int = 0
        self._tw_text: str = ""
        self._tw_timer: float = 0.0
        self.done: bool = False

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _current(self):
        if self.beat_index >= len(self.beats):
            return None
        return self.beats[self.beat_index]

    def _advance(self) -> None:
        self.beat_index += 1
        self._tw_text = ""
        self._tw_timer = 0.0
        if self.beat_index >= len(self.beats):
            self.done = True

    @property
    def is_blocking_interaction(self) -> bool:
        return isinstance(self._current(), DialogBeat)

    # ── Update ─────────────────────────────────────────────────────────────────

    def update(self, dt_ms: int, game) -> None:
        while True:
            beat = self._current()
            if beat is None:
                self.done = True
                return

            if isinstance(beat, DialogBeat):
                if len(self._tw_text) < len(beat.text):
                    self._tw_timer += dt_ms
                    chars = min(len(beat.text), int(self._tw_timer / self._TYPEWRITER_MS))
                    self._tw_text = beat.text[:chars]
                return

            elif isinstance(beat, WaitBeat):
                if not beat.condition or getattr(game, beat.condition, False):
                    self._advance()
                    continue
                return

            elif isinstance(beat, ActionBeat):
                self._execute(beat, game)
                self._advance()
                continue

    def _execute(self, beat: ActionBeat, game) -> None:
        action = beat.action
        params = beat.params

        if action == "camera_pan":
            game.camera_mode = "cinematic"
            game.camera_lerp = float(params.get("lerp", 0.04))
            game.camera_target = self._resolve_cam_target(
                params.get("target", "center"), params, game
            )

        elif action == "camera_follow":
            game.camera_mode = "follow_player"

        elif action == "enable_seating":
            game.eligiendo_asiento = True

        elif action == "apply_seating_stats":
            decision = getattr(game, "decision_dia1_asiento", "solo")
            if decision == "sara_zone":
                df, dr = 2, -1
                thought = "Me senté cerca de Sara."
            elif decision == "diego_zone":
                df, dr = -3, 2
                thought = "Me senté cerca de Diego."
            else:
                df, dr = -2, 0
                thought = "Elegí sentarme solo."

            game.story_felicidad  = max(0, min(100, game.story_felicidad + df))
            game.story_reputacion = max(0, min(100, game.story_reputacion + dr))
            game.story_thought    = thought
            game.decision_history.append({
                "event_id":    "primer_dia_asiento",
                "option_label": decision,
                "dF": df, "dR": dr,
                "thought": thought,
            })
            game.story_completed += 1
            if game.story_completed >= game.story_goal:
                game._resolve_ending()

            npc_mgr = getattr(game, "npc_ai_manager", None)
            if npc_mgr is not None:
                npc_mgr.notify_phase("en_clase")

            # Marcar escena completada ANTES de la transición de mapa
            game.escena_dia1_completada = True
            game.escena_activa          = None
            game.eligiendo_asiento      = False
            game.day1_seq_step          = 4

            audio = getattr(game, "audio", None)
            if audio is not None:
                audio.sfx_sentarse()

            transitions = getattr(game, "transitions", None)
            if transitions is not None and transitions.is_idle():
                transitions.request(
                    game, "aventura",
                    callback=lambda: game._change_adventure_background("SalonTarde.png"),
                )
            else:
                game._change_adventure_background("SalonTarde.png")

        elif action == "play_sfx":
            sfx_name = params.get("sfx", "")
            audio = getattr(game, "audio", None)
            if audio and sfx_name:
                method = getattr(audio, f"sfx_{sfx_name}", None)
                if callable(method):
                    try:
                        method()
                    except Exception:
                        pass

    @staticmethod
    def _resolve_cam_target(name: str, params: dict, game) -> tuple:
        if name == "teacher_desk":
            return (game.story_world_width // 2, int(game.story_world_height * 0.18))
        if name == "center":
            return (game.story_world_width // 2, game.story_world_height // 2)
        rx = float(params.get("rx", 0.5))
        ry = float(params.get("ry", 0.5))
        return (int(rx * game.story_world_width), int(ry * game.story_world_height))

    # ── Input ──────────────────────────────────────────────────────────────────

    def handle_input(self, event: pygame.event.Event) -> bool:
        if event.type != pygame.KEYDOWN:
            return False
        if event.key not in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            return False
        beat = self._current()
        if beat is None:
            return False
        if isinstance(beat, DialogBeat):
            if len(self._tw_text) < len(beat.text):
                self._tw_text  = beat.text
                self._tw_timer = float(len(beat.text) * self._TYPEWRITER_MS)
            else:
                self._advance()
            return True
        return False

    # ── Draw ───────────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface, fonts: dict, width: int, height: int) -> None:
        beat = self._current()
        if beat is None or isinstance(beat, ActionBeat):
            return
        self._draw_box(screen, fonts, width, height, beat)

    def _draw_box(self, screen: pygame.Surface, fonts: dict,
                  width: int, height: int, beat) -> None:
        BOX_H = self._BOX_H
        box_y = height - BOX_H

        # Fondo semitransparente
        bg = pygame.Surface((width, BOX_H), pygame.SRCALPHA)
        bg.fill((10, 12, 22, 235))
        screen.blit(bg, (0, box_y))
        pygame.draw.line(screen, (255, 255, 255), (0, box_y), (width, box_y), 2)

        if isinstance(beat, DialogBeat):
            font_small = fonts.get("small") or fonts.get("body")
            font_body  = fonts.get("body")  or font_small

            # Nombre del speaker
            if font_small and beat.speaker:
                name_surf = font_small.render(beat.speaker, True, beat.color)
                name_bg = pygame.Rect(16, box_y - 30, name_surf.get_width() + 20, 28)
                pygame.draw.rect(screen, (10, 12, 22), name_bg)
                pygame.draw.rect(screen, beat.color, name_bg, 2)
                screen.blit(name_surf, (name_bg.x + 10, name_bg.y + 4))

            # Texto con typewriter y word-wrap
            if font_body:
                max_w = width - 48
                words  = self._tw_text.split(" ")
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
                line_h = font_body.get_height() + 4
                ty = box_y + 30
                for line in lines[:3]:
                    surf = font_body.render(line, True, (245, 248, 255))
                    screen.blit(surf, (24, ty))
                    ty += line_h

            # Indicador ▼ (parpadea cuando texto completo)
            if len(self._tw_text) >= len(beat.text):
                ind_font = font_small or font_body
                if ind_font and (pygame.time.get_ticks() // 500) % 2:
                    ind = ind_font.render("▼", True, (180, 180, 180))
                    screen.blit(ind, (width - ind.get_width() - 24, height - 22))

        elif isinstance(beat, WaitBeat):
            font_body = fonts.get("body") or fonts.get("small")
            if font_body and beat.prompt_text:
                surf = font_body.render(beat.prompt_text, True, (220, 220, 160))
                screen.blit(surf, (24, box_y + 40))
            if font_body and (pygame.time.get_ticks() // 700) % 2:
                hint = font_body.render("E — interactuar con un pupitre", True, (140, 200, 140))
                screen.blit(hint, (24, box_y + 82))


# ── Escenas predefinidas ───────────────────────────────────────────────────────

def get_scene_dia1_salon(player_name: str) -> SceneManager:
    pname = player_name or "Protagonista"
    return SceneManager([
        ActionBeat("camera_pan", {"target": "teacher_desk", "lerp": 0.04}),
        DialogBeat("Profe",  "Buenos días a todos. Siéntense donde quieran.", (220, 180, 80)),
        ActionBeat("camera_follow"),
        DialogBeat("Diego",  f"Ey, {pname}! Acá al lado hay un puesto libre.", (100, 200, 255)),
        DialogBeat("Sara",   "...", (210, 130, 220)),
        DialogBeat(pname,    "Tengo que elegir dónde sentarme.", (255, 255, 255)),
        ActionBeat("enable_seating"),
        WaitBeat("jugador_sentado", "Elige un pupitre libre y presiona E"),
        ActionBeat("apply_seating_stats"),
    ])
