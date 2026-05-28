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
    condicion:  object = None  # callable(game) ?? bool
    timeout_ms: int    = 0
    prompt: str = "Elige dónde sentarte y presiona  E"
    hint: str = "E para interactuar con un pupitre libre"


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
                surf = font_body.render(beat.prompt, True, (220, 220, 160))
                screen.blit(surf, (24, box_y + 38))
            if font_body and (pygame.time.get_ticks() // 700) % 2:
                hint = font_body.render(beat.hint, True, (140, 200, 140))
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
        # Bug-5 fix: solo transicionar a SalonTarde si el jugador aún está en el salón de día.
        # Si salió por la puerta antes de que el timeout disparara, no lo forzamos de vuelta.
        _fondo = getattr(game, "aventura_fondo", None)
        _ruta  = str(getattr(_fondo, "ruta_imagen", "")).lower().replace("\\", "/")
        _mapa  = _ruta.rsplit("/", 1)[-1]  # basename
        if "salond" not in _mapa:           # "salondia" / "salondía" — salió del salón
            return
        transitions = getattr(game, "transitions", None)
        if transitions is not None and transitions.is_idle():
            transitions.request(
                game, "aventura",
                callback=lambda: game._change_adventure_background("SalonTarde.png"),
                duration_ms=1000,   # fundido lento: ~1 seg oscureciendo, ~1 seg aclarando
            )
        else:
            game._change_adventure_background("SalonTarde.png")

    # Diego está en decoracion index 8: x≈0.610, y≈0.716
    _DIEGO_RX, _DIEGO_RY = 0.610, 0.716
    # Profesora se ubica al frente del salón (centro-top del mapa)
    _PROFE_RX, _PROFE_RY = 0.50, 0.25

    return SceneManager([
        # 1 — bloquear + paneo general al salón
        ActionBeat(beat1_bloquear_y_panear),

        # 2 — pensamiento del jugador (auto, 2500ms)
        DialogBeat(
            pname, "¿Dónde debería sentarme...?",
            avanza_con="tiempo", tiempo_ms=2500,
        ),

        # 3 — Bug-4: la Profesora da la bienvenida (cámara a pizarrón/frente)
        DialogBeat(
            "Profesora", "Buenos días a todos. Siéntense rápido, ya vamos a empezar.",
            avanza_con="tiempo", tiempo_ms=2800,
            camera_rx=_PROFE_RX, camera_ry=_PROFE_RY,
        ),

        # 4 — Diego habla; cámara se mueve hacia su pupitre
        DialogBeat(
            "Diego", "Ey, acá hay puesto.",
            avanza_con="click",
            camera_rx=_DIEGO_RX, camera_ry=_DIEGO_RY,
        ),

        # 5 — desbloquear movimiento y activar elección de asiento
        ActionBeat(beat4_desbloquear),

        # 6 — esperar que el jugador se siente (1 minuto de timeout)
        WaitBeat(
            condicion=lambda g: bool(getattr(g, "jugador_sentado", False)),
            timeout_ms=60_000,
        ),

        # 7 — evaluar zona y aplicar stats
        ActionBeat(beat6_evaluar_asiento),

        # 8a — notificación "Te has sentado junto a Diego"
        DialogBeat(
            pname, "Me he sentado junto a Diego.",
            avanza_con="tiempo", tiempo_ms=1800,
            condition=lambda g: getattr(g, "decision_dia1_asiento", "") == "diego",
        ),

        # 8b — notificación "Te has sentado junto a Sara"
        DialogBeat(
            pname, "Me he sentado junto a Sara.",
            avanza_con="tiempo", tiempo_ms=1800,
            condition=lambda g: getattr(g, "decision_dia1_asiento", "") == "sara",
        ),

        # 9 — comentario de NPC si el jugador se sentó con Sara
        DialogBeat(
            "NPC", "Ella siempre anda sola...",
            avanza_con="tiempo", tiempo_ms=2000,
            condition=lambda g: getattr(g, "_sm_dia1_result", "") == "sara",
        ),

        # 10 — marcar escena completada + transición a SalonTarde
        ActionBeat(beat8_completar),
    ])


# ── Pupitre Rayado — escenas post-asiento ────────────────────────────────────

def get_scene_pupitre_rayado_intro(player_name: str) -> SceneManager:
    """
    Intro del evento del pupitre rayado.
    El jugador se levanta en SalonTarde → fondo cambia a sara_pupitre_rayado_256x256.png
    → conversación → fondo cambia a Pupitre.png + letras.png para decidir.
    """
    import os as _os
    import pygame as _pg

    pname = player_name or "Protagonista"

    def beat_activar_zoom(game):
        """Cierra el fondo cinemático y activa la vista de decisión (Pupitre.png + letras.png)."""
        game.pupitre_rayado_fondo     = ""         # ya no mostramos la imagen de Sara
        game.escena_activa            = None        # cerrar overlay de la escena
        game.day1_pupitre_step        = 2           # mostrar panel A/B/C/D
        game.day1_pupitre_zoom_active = True

        # Crear superficie borradora con letras.png (los insultos que se pueden borrar)
        erase_surf = _pg.Surface((game.width, game.height), _pg.SRCALPHA)
        if hasattr(game, "_resolve_image_path"):
            letras_path = game._resolve_image_path("letras.png")
        else:
            letras_path = _os.path.join(
                _os.path.dirname(__file__),
                "Imagenes", "Cosas_especificas_eventos", "letras.png",
            )
        try:
            raw = _pg.image.load(letras_path).convert_alpha()
            erase_surf.blit(_pg.transform.scale(raw, (game.width, game.height)), (0, 0))
        except (OSError, _pg.error):
            erase_surf.fill((80, 40, 40, 200))
        game.day1_pupitre_erase_surface  = erase_surf
        game.day1_pupitre_erase_progress = 0.0

    return SceneManager([
        # 1 — protagonista nota el pupitre (fondo ya es sara_pupitre_rayado, activado al levantarse)
        DialogBeat(
            pname, "¿Qué es eso...? El pupitre de Sara tiene algo escrito.",
            avanza_con="tiempo", tiempo_ms=2800,
        ),
        # 2 — Sara parece triste (pausa dramática)
        DialogBeat(
            "Sara", "...",
            avanza_con="tiempo", tiempo_ms=1800,
        ),
        # 3 — protagonista lee los insultos en voz alta
        DialogBeat(
            pname,
            '"Nadie te quiere.", "Rara.", "Mejor no vengas." — ¿Quién hizo esto?',
            avanza_con="tiempo", tiempo_ms=3200,
        ),
        # 4 — cambiar al zoom del pupitre con letras.png para la decisión
        ActionBeat(beat_activar_zoom),
    ])


def get_scene_pupitre_borrar_gracias(player_name: str) -> SceneManager:
    """
    Post-decisión A: el jugador borra los insultos.
    Sara agradece; se actualiza la misión y la habilidad.
    """
    pname = player_name or "Protagonista"

    def beat_completar(game):
        game.escena_activa             = None
        game.player_can_move           = True
        game.pupitre_rayado_completado = True
        game.current_mission           = "Volver a casa"
        game.decision_history.append({
            "event_id":     "dia1_pupitre_rayado",
            "option_label": "borrar",
            "dF": +1, "dR": 0,
            "thought": "Borré los mensajes del pupitre de Sara.",
        })
        skills = getattr(game, "skills_inventory", {})
        if "Intervencion Pacifica" in skills:
            s = skills["Intervencion Pacifica"]
            s["nivel"] = min(s.get("max_nivel", 3), s.get("nivel", 0) + 1)

    return SceneManager([
        DialogBeat(
            "Sara", "Gracias... no esperaba que nadie lo notara.",
            avanza_con="click",
        ),
        DialogBeat(
            pname, "Nadie merece ver eso.",
            avanza_con="click",
        ),
        ActionBeat(beat_completar),
    ])


def get_scene_pupitre_foto(player_name: str) -> SceneManager:
    """
    Post-decisión C: el jugador toma foto del pupitre.
    Sara reacciona con tristeza.
    """
    pname = player_name or "Protagonista"

    def beat_completar(game):
        game.escena_activa             = None
        game.player_can_move           = True
        game.pupitre_rayado_completado = True
        game.current_mission           = "Volver a casa"
        game.decision_history.append({
            "event_id":     "dia1_pupitre_rayado",
            "option_label": "foto",
            "dF": -5, "dR": +1,
            "thought": "Tomé foto del pupitre de Sara para documentarlo.",
        })

    return SceneManager([
        DialogBeat(
            pname, "*¡Clic!* Documentado. Que quede constancia.",
            avanza_con="tiempo", tiempo_ms=2000,
        ),
        DialogBeat(
            "Sara", "¿Por qué...? Ahora todo el mundo lo verá.",
            avanza_con="click",
        ),
        DialogBeat(
            pname, "...",
            avanza_con="tiempo", tiempo_ms=1500,
        ),
        ActionBeat(beat_completar),
    ])


def get_scene_pupitre_profesor(player_name: str) -> SceneManager:
    """
    Post-decisión D: el jugador llama al profesor.
    El profesor consolida y anima a Sara.
    """
    pname = player_name or "Protagonista"

    def beat_completar(game):
        game.escena_activa               = None
        game.player_can_move             = True
        game.pupitre_rayado_completado   = True
        game.current_mission             = "Volver a casa"
        # Item-2 fix: restaurar cámara tras la escena (la cámara quedaba en modo cinemático)
        game.camera_mode                 = "follow_player"
        # Bug-9 fix: apagar el overlay de llamar profe al terminar la escena
        game.mision3_llamar_profe_active = False
        game.mision3_llamar_profe_ms     = 0
        # La profesora aparece junto al pupitre de Sara (desaparece de su posición original)
        game.profe_en_sara               = True
        game.decision_history.append({
            "event_id":     "dia1_pupitre_rayado",
            "option_label": "profesor",
            "dF": +2, "dR": +1,
            "thought": "Llamé al profesor para que vea lo del pupitre de Sara.",
        })
        skills = getattr(game, "skills_inventory", {})
        if "Valentia Social" in skills:
            s = skills["Valentia Social"]
            s["nivel"] = min(s.get("max_nivel", 3), s.get("nivel", 0) + 1)

    # Sara está en rx≈0.165, ry≈0.72 en SalonTarde
    _SARA_RX, _SARA_RY = 0.165, 0.72

    return SceneManager([
        # Jugador llama a la profesora
        DialogBeat(
            pname, "¡Profe! Venga, necesito que vea algo.",
            avanza_con="tiempo", tiempo_ms=1800,
        ),
        # Bug-7: cámara se desplaza hacia el pupitre de Sara mientras la profesora camina
        DialogBeat(
            pname, "Se dirige hacia el pupitre de Sara...",
            avanza_con="tiempo", tiempo_ms=1400,
            camera_rx=_SARA_RX, camera_ry=_SARA_RY,
        ),
        # Profesora llega y ve el rayado (cámara ya está en el pupitre de Sara)
        DialogBeat(
            "Profesora", "Dios mío... ¿quién hizo esto?",
            avanza_con="click",
        ),
        DialogBeat(
            "Profesora", "Sara, esto no puede quedar así. Vamos a hablar con el director.",
            avanza_con="click",
        ),
        DialogBeat(
            "Sara", "Gracias...",
            avanza_con="tiempo", tiempo_ms=2000,
        ),
        ActionBeat(beat_completar),
    ])


# ── Minijuego Callejón — diálogo previo ──────────────────────────────────────

def get_scene_callejon_emociones(player_name: str, tipo: str = "atrapa_emociones") -> SceneManager:
    """
    Diálogo breve con el NPC del callejón antes de lanzar Atrapa Emociones.

    Beats:
        1. DialogBeat  — NPC invita al jugador (click)
        2. DialogBeat  — respuesta del jugador (auto 1200 ms)
        3. ActionBeat  — lanza el minijuego y limpia la escena
    """
    pname = player_name or "Protagonista"
    _tipo = tipo

    def beat_lanzar(game):
        game.escena_activa   = None
        game.player_can_move = True
        _trigger = getattr(game, "_trigger_minijuego", None)
        if _trigger is not None:
            _trigger(_tipo)

    return SceneManager([
        DialogBeat(
            "Extraño",
            "Aquí las emociones andan sueltas... ¿Ves las que flotan? Atrapa solo las buenas.",
            avanza_con="click",
        ),
        DialogBeat(
            pname, "Entendido. ¡Voy a intentarlo!",
            avanza_con="tiempo", tiempo_ms=1200,
        ),
        ActionBeat(beat_lanzar),
    ])


# ── Minijuego Penaltis — diálogo previo ──────────────────────────────────────

def get_scene_patio_penaltis(player_name: str, tipo: str = "penaltis") -> SceneManager:
    """
    Bug-3 fix: diálogo de Lucas antes del minijuego de penaltis.
    El ActionBeat final llama a game._trigger_minijuego(tipo) para lanzar el juego.

    Beats:
        1. DialogBeat  — Lucas invita al jugador a jugar (click)
        2. DialogBeat  — respuesta del jugador (auto 1200ms)
        3. ActionBeat  — lanza el minijuego y limpia la escena
    """
    pname = player_name or "Protagonista"
    _tipo = tipo   # captura en closure para el ActionBeat

    def beat_lanzar(game):
        game.escena_activa   = None
        game.player_can_move = True
        _trigger = getattr(game, "_trigger_minijuego", None)
        if _trigger is not None:
            _trigger(_tipo)

    return SceneManager([
        DialogBeat(
            "Lucas",
            "¡Oye! ¿Una pachangita? Si le metes un gol al Diego ganas algo chévere.",
            avanza_con="click",
        ),
        DialogBeat(
            pname, "¡Claro que sí, vamos!",
            avanza_con="tiempo", tiempo_ms=1200,
        ),
        ActionBeat(beat_lanzar),
    ])


# ── Intro del dormitorio — cinemática de inicio del Día 1 ────────────────────

def get_scene_bedroom_intro(player_name: str) -> SceneManager:
    """
    Item-4: Cinemática de introducción del Día 1.
    El jugador aparece durmiendo (overlay A_Sleeping.png), dice "Zzzzz...",
    se despierta y exclama que llega tarde al colegio.

    Solo se lanza en partidas nuevas (no al cargar guardado).

    Beats:
        1. ActionBeat  — activa overlay A_Sleeping.png, bloquea movimiento
        2. DialogBeat  — "Zzzzz..." (sin speaker, 2.5 s automático)
        3. ActionBeat  — desactiva overlay (jugador "despierta")
        4. DialogBeat  — jugador: "¡Oh no! ¡Voy tarde al colegio!" (click)
        5. ActionBeat  — limpia escena, restaura control
    """
    pname = player_name or "Protagonista"

    def beat_dormir(game):
        game.bedroom_sleeping_active = True
        game.player_can_move         = False

    def beat_despertar(game):
        game.bedroom_sleeping_active = False

    def beat_completar(game):
        game.escena_activa           = None
        game.player_can_move         = True

    return SceneManager([
        ActionBeat(beat_dormir),
        DialogBeat(
            "", "Zzzzz...",
            avanza_con="tiempo", tiempo_ms=2500,
        ),
        ActionBeat(beat_despertar),
        DialogBeat(
            pname, "¡Oh no! ¡Voy tarde al colegio, tengo que salir ya!",
            avanza_con="click",
        ),
        ActionBeat(beat_completar),
    ])


def get_scene_cama_dormir(player_name: str) -> SceneManager:
    """
    Cinemática al interactuar con la cama en HabTarde.
    Termina el Día 1 y hace transición a HabNoche para iniciar el Día 2.
    """
    pname = player_name or "Protagonista"

    def beat_dormir(game):
        game.bedroom_sleeping_active = True
        game.player_can_move = False

    def beat_ir_hab_noche(game):
        game.bedroom_sleeping_active = False   # apagar overlay justo antes del fade
        game.current_day = 2
        transitions = getattr(game, "transitions", None)
        if transitions is not None and transitions.is_idle():
            transitions.request(
                game, "aventura",
                callback=lambda: game._change_adventure_background("HabNoche (2).png"),
                duration_ms=400,
            )
        else:
            game._change_adventure_background("HabNoche (2).png")

    def beat_completar(game):
        game.escena_activa = None
        game.player_can_move = True

    return SceneManager([
        ActionBeat(beat_dormir),
        DialogBeat("", "Zzzzz...", avanza_con="tiempo", tiempo_ms=2000),
        DialogBeat(pname, "Mañana será otro día...", avanza_con="tiempo", tiempo_ms=1600),
        ActionBeat(beat_ir_hab_noche),
        ActionBeat(beat_completar),
    ])


def get_scene_dia2_chat(player_name: str) -> SceneManager:
    pname = player_name or "Protagonista"

    def beat1_setup(game):
        game.player_can_move = False
        game.day2_chat_active = True
        game.day2_chat_choice_menu_active = False
        game.day2_chat_show_ana_photo = False
        game.day2_chat_overlay_image = None
        game.day2_chat_overlay_until_ms = 0
        game.day2_chat_choice = ""
        game.day2_chat_pending_choice = ""
        game.current_mission = "Tomar una decisión acerca del grupo"
        audio = getattr(game, "audio", None)
        if audio is not None:
            audio.play_sfx("notificaciones", cooldown_ms=150)

    def beat6_show_choices(game):
        game.day2_chat_show_ana_photo = True
        game.day2_chat_choice_menu_active = True
        game.day2_chat_choice = ""
        game.day2_chat_pending_choice = ""

    def beat8_finalize(game):
        deltas = {
            "defender": (+3, +1),
            "reportar": (+2, +1),
            "ignorar": (-4, 0),
            "reenviar": (-7, +2),
            "psicologo": (-3, 0),
        }
        choice = getattr(game, "day2_chat_choice", "") or "ignorar"
        df, dr = deltas.get(choice, (-4, 0))
        skills = getattr(game, "skills_inventory", {})
        digital = skills.get("Empatia Digital", {}).get("nivel", 0)
        if df < 0 and digital > 0:
            df = min(0, df + digital)
        if choice in ("defender", "reportar") and "Empatia Digital" in skills:
            s = skills["Empatia Digital"]
            s["nivel"] = min(s.get("max_nivel", 3), s.get("nivel", 0) + 1)
        game.story_felicidad = max(0, min(100, game.story_felicidad + df))
        game.story_reputacion = max(0, min(100, game.story_reputacion + dr))
        game.decision_dia2_chat = choice
        game.escena_dia2_chat_completada = True
        game.day2_chat_choice_menu_active = False
        game.day2_chat_active = False
        game.day2_chat_show_ana_photo = False
        game.player_can_move = True
        game.escena_activa = None
        game._change_adventure_background("HabDía.png")
        game.story_thought = "Bueno, hora de ir a la escuela."
        game.current_mission = "Ir a la escuela"
        game.day2_guide_target = "escuela"

    return SceneManager([
        ActionBeat(beat1_setup),
        DialogBeat("Chat escolar", "JAJAJA.", avanza_con="tiempo", tiempo_ms=800),
        DialogBeat("Chat escolar", "Miren esto.", avanza_con="tiempo", tiempo_ms=800),
        ActionBeat(lambda g: setattr(g, "day2_chat_show_ana_photo", True)),
        DialogBeat("Chat escolar", "Pásenlo.", avanza_con="tiempo", tiempo_ms=1000),
        DialogBeat(pname, "Esto no está bien... están compartiendo imágenes editadas de Ana por todo el grupo.", avanza_con="click"),
        ActionBeat(beat6_show_choices),
        WaitBeat(
            condicion=lambda g: bool(getattr(g, "day2_chat_choice", "")),
            prompt="Toma una decisión del chat (1-5)",
            hint="1 Defender  2 Reportar  3 Ignorar  4 Reenviar  5 Psicólogo",
        ),
        DialogBeat("Chat escolar", "No la traten así. Bórrenlo. Eso no da risa.", avanza_con="click", condition=lambda g: getattr(g, "day2_chat_choice", "") == "defender"),
        DialogBeat("Chat escolar", "Uy, qué intenso.", avanza_con="tiempo", tiempo_ms=1200, condition=lambda g: getattr(g, "day2_chat_choice", "") == "defender"),
        DialogBeat(pname, "Al menos por un momento dejaron de reenviar.", avanza_con="tiempo", tiempo_ms=1400, condition=lambda g: getattr(g, "day2_chat_choice", "") == "defender"),
        DialogBeat(pname, "Salí del grupo y reporté el contenido.", avanza_con="tiempo", tiempo_ms=1400, condition=lambda g: getattr(g, "day2_chat_choice", "") == "reportar"),
        DialogBeat(pname, "Nadie lo sabrá, pero era lo correcto.", avanza_con="tiempo", tiempo_ms=1400, condition=lambda g: getattr(g, "day2_chat_choice", "") == "reportar"),
        DialogBeat(pname, "Cerré el chat... como si no fuera conmigo.", avanza_con="tiempo", tiempo_ms=1400, condition=lambda g: getattr(g, "day2_chat_choice", "") == "ignorar"),
        DialogBeat(pname, "Pero esa sensación incómoda no se fue.", avanza_con="tiempo", tiempo_ms=1500, condition=lambda g: getattr(g, "day2_chat_choice", "") == "ignorar"),
        DialogBeat("Chat escolar", "¡Durísimo! Pásalo más.", avanza_con="tiempo", tiempo_ms=1300, condition=lambda g: getattr(g, "day2_chat_choice", "") == "reenviar"),
        DialogBeat("Chat escolar", "Así se habla.", avanza_con="tiempo", tiempo_ms=1100, condition=lambda g: getattr(g, "day2_chat_choice", "") == "reenviar"),
        DialogBeat(pname, "Quise encajar... y me arrepentí al instante.", avanza_con="tiempo", tiempo_ms=1500, condition=lambda g: getattr(g, "day2_chat_choice", "") == "reenviar"),
        DialogBeat("Chat escolar", "Ana, ve al psicólogo.", avanza_con="tiempo", tiempo_ms=1300, condition=lambda g: getattr(g, "day2_chat_choice", "") == "psicologo"),
        DialogBeat("Chat escolar", "JAJAJA, qué comentario.", avanza_con="tiempo", tiempo_ms=1200, condition=lambda g: getattr(g, "day2_chat_choice", "") == "psicologo"),
        DialogBeat(pname, "No entendí por qué sonó tan mal.", avanza_con="tiempo", tiempo_ms=1300, condition=lambda g: getattr(g, "day2_chat_choice", "") == "psicologo"),
        ActionBeat(beat8_finalize),
    ])


def get_scene_dia2_lucas_bano(player_name: str) -> SceneManager:
    pname = player_name or "Protagonista"

    def beat1_setup(game):
        game.player_can_move = False
        game.day2_lucas_event_active = True
        game.day2_lucas_choice_menu_active = False
        game.day2_lucas_choice = ""
        game.day2_lucas_sprite = "llorando"
        # Entrada al baño: jugador mira hacia abajo (idle_down)
        p = getattr(game, "aventura_personaje", None)
        if p is not None:
            p.direccion = "down"
            p.moviendose = False
        # Paneo cinematográfico hacia Lucas (igual que evento 1 Día 1)
        game.camera_mode   = "cinematic"
        game.camera_lerp   = 0.05
        game.camera_target = (
            int(game.story_world_width  * 0.25),
            int(game.story_world_height * 0.52),
        )
        game.camera_return_after_ms = 2200   # vuelve al jugador tras ver a Lucas
        audio = getattr(game, "audio", None)
        if audio is not None:
            audio.play_sfx("llanto_suave", cooldown_ms=150)

    def beat4_change_sprite(game):
        game.day2_lucas_sprite = "llorando"

    def beat5_choices(game):
        game.player_can_move = True
        game.day2_lucas_choice_menu_active = True
        game.day2_lucas_choice = ""
        # Devolver cámara al jugador para que pueda navegar
        game.camera_mode = "follow_player"

    def beat6_approach(game):
        """Acercar o alejar al jugador a Lucas según su decisión."""
        choice = getattr(game, "day2_lucas_choice", "") or "ignorar"
        game.player_can_move = False
        p = getattr(game, "aventura_personaje", None)
        if p is not None:
            mw = getattr(game, "story_world_width", 1280)
            mh = getattr(game, "story_world_height", 960)
            if choice in ("consolar", "preguntar"):
                # Se acerca a Lucas: coloca al jugador junto a él
                p.x = int(mw * 0.31)
                p.y = int(mh * 0.50)
                p.direccion = "up"
                p.moviendose = False
                # Cámara pana suavemente hacia Lucas con el jugador
                game.camera_mode   = "cinematic"
                game.camera_lerp   = 0.10
                game.camera_target = (
                    int(mw * 0.25),
                    int(mh * 0.52),
                )
                game.camera_return_after_ms = 0   # sin retorno automático; beat7 lo libera
            else:
                # Ignorar/Minimizar: da la espalda (hacia la salida)
                p.direccion = "down"
                p.moviendose = False
                # Cámara ya sigue al jugador (set en beat5_choices)

    def beat7_finalize(game):
        deltas = {
            "consolar": (+3, +1),
            "preguntar": (+2, 0),
            "ignorar": (-5, 0),
            "minimizar": (-7, -1),
        }
        choice = getattr(game, "day2_lucas_choice", "") or "ignorar"
        df, dr = deltas.get(choice, (-5, 0))
        skills = getattr(game, "skills_inventory", {})
        escucha = skills.get("Escucha Activa", {}).get("nivel", 0)
        if df < 0 and escucha > 0:
            df = min(0, df + escucha)
        if choice in ("consolar", "preguntar") and "Escucha Activa" in skills:
            s = skills["Escucha Activa"]
            s["nivel"] = min(s.get("max_nivel", 3), s.get("nivel", 0) + 1)
        game.story_felicidad = max(0, min(100, game.story_felicidad + df))
        game.story_reputacion = max(0, min(100, game.story_reputacion + dr))
        game.decision_dia2_lucas = choice
        game.escena_dia2_lucas_completada = True
        game.day2_lucas_choice_menu_active = False
        game.day2_lucas_event_active = False
        game.day2_lucas_sprite = ""
        game.current_mission = "Volver a casa"
        game.day2_guide_target = "habtarde"
        # Liberar cámara; el jugador queda bloqueado hasta beat_complete
        game.camera_mode = "follow_player"
        game.player_can_move = False   # se libera en beat_complete

    def beat9_tarde(game):
        """Salto temporal: ya pasaron las clases → transición al pasillo tarde."""
        game.story_clock_hour   = 14
        game.story_clock_minute = 30
        transitions = getattr(game, "transitions", None)
        target = "Pasillo1_tarde.png"
        if transitions is not None and transitions.is_idle():
            transitions.request(
                game, "aventura",
                callback=lambda: game._change_adventure_background(target),
                duration_ms=600,
            )
        else:
            game._change_adventure_background(target)

    def beat_complete(game):
        game.escena_activa   = None
        game.player_can_move = True

    return SceneManager([
        ActionBeat(beat1_setup),
        ActionBeat(lambda g: None),
        DialogBeat(pname, "¿Ese es... Lucas? Está llorando.", avanza_con="tiempo", tiempo_ms=2000),
        DialogBeat("Lucas", "...", avanza_con="tiempo", tiempo_ms=1500),
        ActionBeat(beat4_change_sprite),
        ActionBeat(beat5_choices),
        WaitBeat(
            condicion=lambda g: bool(getattr(g, "day2_lucas_choice", "")),
            prompt="Elige cómo responder a Lucas (A-D)",
            hint="A Consolar  B Preguntar  C Ignorar  D Minimizar",
        ),
        ActionBeat(beat6_approach),
        DialogBeat(pname, "Me senté a su lado sin decir nada al principio.", avanza_con="tiempo", tiempo_ms=1400, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "consolar"),
        DialogBeat("Lucas", "Gracias... de verdad.", avanza_con="tiempo", tiempo_ms=1300, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "consolar"),
        DialogBeat(pname, "No tienes que pasarlo solo.", avanza_con="tiempo", tiempo_ms=1400, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "consolar"),
        DialogBeat(pname, "¿Quieres contarme qué pasó?", avanza_con="tiempo", tiempo_ms=1300, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "preguntar"),
        DialogBeat("Lucas", "No es nada... en serio.", avanza_con="tiempo", tiempo_ms=1300, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "preguntar"),
        DialogBeat(pname, "Me quedé un momento, por si cambiaba de idea.", avanza_con="tiempo", tiempo_ms=1400, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "preguntar"),
        DialogBeat(pname, "Seguí de largo... pero el sonido del llanto se quedó conmigo.", avanza_con="tiempo", tiempo_ms=1700, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "ignorar"),
        DialogBeat(pname, "No es para tanto.", avanza_con="tiempo", tiempo_ms=1100, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "minimizar"),
        DialogBeat("Lucas", "...", avanza_con="tiempo", tiempo_ms=1200, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "minimizar"),
        DialogBeat(pname, "Creo que lo empeoré.", avanza_con="tiempo", tiempo_ms=1300, condition=lambda g: getattr(g, "day2_lucas_choice", "") == "minimizar"),
        ActionBeat(beat7_finalize),
        DialogBeat("", "Pasaron las horas...", avanza_con="tiempo", tiempo_ms=1400),
        DialogBeat(pname, "Las clases terminaron. Es hora de volver a casa.", avanza_con="tiempo", tiempo_ms=2000),
        ActionBeat(beat9_tarde),
        ActionBeat(beat_complete),
    ])

