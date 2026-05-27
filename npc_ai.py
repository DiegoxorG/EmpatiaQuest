"""
NPC AI system for EmpatiaQuest — Evento 1 (Día 1 — primer_dia).

Clases:
    NPCEntity       — un NPC vivo en el mundo con estado, posición y lógica de movimiento.
    NPCAIManager    — gestiona todos los NPCEntity activos, los actualiza y los dibuja.

Integración:
    En game_state._start_adventure():
        self.npc_ai_manager = NPCAIManager(os.path.dirname(__file__))

    En game_state._change_adventure_background():
        self.npc_ai_manager.on_map_change(new_map_basename, self)

    En game_state._update_adventure() (dentro del bloque de dt_ms):
        self.npc_ai_manager.update(dt_ms, self)

    En renderer._draw_adventure_screen() (después de dibujar objetos, antes del jugador):
        current_map = os.path.basename(self.aventura_fondo.ruta_imagen)
        self.npc_ai_manager.draw(self.screen, self.story_camera_x,
                                 self.story_camera_y,
                                 self.story_world_width, self.story_world_height,
                                 current_map)
"""

import json
import math
import os
import random

import pygame

# ── Velocidades por NPC (fracción de world_width por frame a 60fps) ─────────
_SPEEDS: dict[str, float] = {
    "Sara":   0.0021,
    "Diego":  0.0024,
    "Carlos": 0.0020,
    "Lucas":  0.0026,
    "Mateo":  0.0019,
    "Samuel": 0.0028,
}

# ── Zonas de spawn en PatioDia (rx_min, rx_max, ry_min, ry_max) ─────────────
_SPAWN_ZONES = [
    (0.15, 0.30, 0.40, 0.60),   # A
    (0.35, 0.50, 0.30, 0.50),   # B
    (0.55, 0.70, 0.40, 0.65),   # C
    (0.20, 0.40, 0.65, 0.80),   # D
]

# ── Posiciones de puertas clave del Evento 1 (rx, ry normalizado) ────────────
_E1_DOOR = {
    "patio_exit":    (0.4896, 0.1670),
    "pasillo_exit":  (0.1837, 0.3468),
    "salon_entry":   (0.9046, 0.3959),
}

# ── Posiciones de spawn al llegar al nuevo mapa ──────────────────────────────
_ARRIVAL_SPAWN = {
    "Pasillo1_dia.png": (0.39, 0.345),
    "salonDia.png":     (0.905, 0.395),
    "Pasillo1_tarde.png": (0.40, 0.355),
    "PatioTarde.png":   (0.50, 0.70),
}

_NPC_W = 24
_NPC_H = 32
_PROXIMITY_SQ = 120 * 120
_WALK_FRAME_DUR = 150.0   # ms por frame de caminata
_STUCK_THRESHOLD = 500.0  # ms bloqueado antes de rodeo
_RODEO_TIMEOUT = 3000.0   # ms máximo en modo rodeo
_WP_TIMEOUT = 8000.0      # ms máximo hacia un waypoint antes de teleport
_CHAIR_IDLE_TIMEOUT = 10000.0  # ms: NPC deja de intentar llegar a su silla y espera en idle
_FADE_DUR = 300.0          # ms del fade-in tras teleport


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(bx - ax, by - ay)


def _normalize(dx: float, dy: float) -> tuple[float, float]:
    d = math.hypot(dx, dy)
    if d < 0.0001:
        return 0.0, 0.0
    return dx / d, dy / d


def _map_key(fondo_name: str) -> str:
    return os.path.splitext(os.path.basename(fondo_name))[0].lower()


# ── NPCEntity ─────────────────────────────────────────────────────────────────

class NPCEntity:
    """Un NPC vivo en el mundo del juego."""

    def __init__(self, nombre: str, fondo: str, rx: float, ry: float,
                 velocidad: float, spawn_delay_ms: float = 0.0):
        self.nombre = nombre
        self.fondo_actual = fondo
        self.estado = "spawning"        # spawning|walking|sitting|leaving|despawned
        self.fase_evento = "llegando"   # llegando|en_clase|saliendo
        self.velocidad = velocidad

        self.rx = rx
        self.ry = ry
        self.destino_rx = rx
        self.destino_ry = ry

        self.chair_rx: float | None = None
        self.chair_ry: float | None = None

        self.waypoints: list[tuple[float, float]] = []
        self.waypoint_idx = 0

        self.spawn_delay_ms = spawn_delay_ms
        self.spawn_elapsed_ms = 0.0

        self.reaction_ms = 0.0
        self.reacted_segment = False

        self.idle_ms = random.uniform(4000, 8000)
        self.idle_alt_ms = 0.0
        self.idle_active = False

        self.leave_delay_ms = 0.0
        self.leave_elapsed_ms = 0.0

        # Animación — reemplaza el viejo "sprite: str"
        self.facing: str = "down"       # "down"|"up"|"left"|"right"
        self.anim_state: str = "idle"   # "idle"|"walk"|"sitting"|"hablando"|"dibujando"|"riendose"|"mirando"
        self.walk_frame_idx: int = 0
        self.walk_frame_ms: float = 0.0
        self.anim_ms: float = random.uniform(0, 1000)   # stagger para idle loop

        # Steering / Bug-3
        self.steer_stuck_ms: float = 0.0
        self.steer_rodeo_target: tuple[float, float] | None = None
        self.steer_rodeo_ms: float = 0.0
        self.waypoint_timeout_ms: float = 0.0

        # Fade tras teleport
        self.fade_alpha: int = 255
        self.fade_in_ms: float = 0.0

        # Bug 4: flag que impide sentarse antes de pasar el primer waypoint interior
        self.dentro_del_salon: bool = False

    def alive(self) -> bool:
        return self.estado != "despawned"

    def current_map_key(self) -> str:
        return _map_key(self.fondo_actual)


# ── NPCAIManager ──────────────────────────────────────────────────────────────

class NPCAIManager:
    """Gestiona todos los NPCEntity del Evento 1."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.npcs: list[NPCEntity] = []
        self.npc_ai_active = False

        self._phase = "llegando"
        self._event1_done = False
        self._pending_salon_npcs: list[str] = []

        self._waypoints_cache: dict[str, list[tuple[float, float]]] = {}
        # clave: (nombre, anim_state, facing) → list[Surface]
        self._sprite_cache: dict[tuple[str, str, str], list[pygame.Surface]] = {}
        # ancho del frame idle por personaje (para slicing correcto de walk sheets)
        self._idle_width_cache: dict[str, int] = {}

    # ── API pública ───────────────────────────────────────────────────────────

    def _read_salon_chair_owners(self) -> list[str]:
        """Lee salonDia_hitboxes.json y devuelve los npc_owner únicos de los pupitres."""
        path = os.path.join(self.base_dir, "Hitboxes", "salonDia_hitboxes.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return []
        owners = []
        seen = set()
        # Buscar en hitboxes[] (action:"pupitre" o action:"objeto" con npc_owner)
        for entry in data.get("hitboxes", []):
            owner = entry.get("npc_owner", "")
            action = entry.get("action", "")
            if owner and owner not in seen and action in ("pupitre", "objeto"):
                seen.add(owner)
                owners.append(owner)
        # Buscar también en decoracion[] por si el usuario asignó via editor
        for entry in data.get("decoracion", []):
            owner = entry.get("npc_owner", "")
            name = entry.get("name", "")
            if owner and owner not in seen and "pupitre" in name.lower():
                seen.add(owner)
                owners.append(owner)
        return owners

    def init_event1_routine(self, world_w: int, world_h: int, walls=None):
        if self._event1_done:
            return
        self._event1_done = True
        self.npc_ai_active = True
        self._phase = "llegando"

        names = self._read_salon_chair_owners()
        self._pending_salon_npcs = names if names else ["Sara", "Diego", "Carlos", "Lucas"]
        # NPC2 siempre se sienta en D3 (deco index 2, sin npc_owner en JSON)
        if "NPC2" not in self._pending_salon_npcs:
            self._pending_salon_npcs.append("NPC2")

    def notify_phase(self, phase: str):
        if phase == self._phase:
            return
        self._phase = phase

        if phase == "en_clase":
            for npc in self.npcs:
                if npc.alive() and npc.estado == "sitting":
                    npc.fase_evento = "en_clase"
                    npc.anim_state = "sitting"

        elif phase == "saliendo":
            stagger = 0.0
            for npc in self.npcs:
                if not npc.alive():
                    continue
                # Sara permanece en su pupitre durante el evento de SalonTarde
                if npc.nombre == "Sara":
                    continue
                npc.fase_evento = "saliendo"
                npc.leave_delay_ms = stagger
                npc.leave_elapsed_ms = 0.0
                if npc.estado == "walking":
                    npc.estado = "sitting"
                    if npc.chair_rx is not None:
                        npc.rx = npc.chair_rx
                        npc.ry = npc.chair_ry
                npc.anim_state = "sitting"
                npc.reacted_segment = False
                stagger += 300.0

    def on_map_change(self, new_map_basename: str, game):
        if not self.npc_ai_active:
            return
        key = _map_key(new_map_basename)
        if "salondia" in key or "salondía" in key:
            self._place_npcs_at_chairs(game)

    def update(self, dt_ms: float, game):
        if not self.npc_ai_active or not self.npcs:
            return

        world_w = getattr(game, "story_world_width", 1280)
        world_h = getattr(game, "story_world_height", 720)
        walls = getattr(game, "story_walls", [])
        player_rect: pygame.Rect | None = getattr(game, "player_rect", None)
        current_map = self._current_map_name(game)

        for npc in self.npcs:
            if not npc.alive():
                continue
            npc.anim_ms = (npc.anim_ms + dt_ms) % 100000

            # Walk frame animation
            if npc.anim_state == "walk":
                npc.walk_frame_ms += dt_ms
                if npc.walk_frame_ms >= _WALK_FRAME_DUR:
                    npc.walk_frame_ms -= _WALK_FRAME_DUR
                    npc.walk_frame_idx += 1

            # Fade in tras teleport
            if npc.fade_in_ms > 0:
                npc.fade_in_ms = max(0.0, npc.fade_in_ms - dt_ms)
                npc.fade_alpha = min(255, int(255 * (1.0 - npc.fade_in_ms / _FADE_DUR)))

            if npc.estado == "spawning":
                npc.spawn_elapsed_ms += dt_ms
                if npc.spawn_elapsed_ms >= npc.spawn_delay_ms:
                    npc.estado = "walking"
                    self._assign_destination(npc, game, walls)
                continue

            same_map = (npc.current_map_key() == _map_key(current_map))

            if npc.fase_evento == "llegando":
                self._update_llegando(npc, dt_ms, walls, world_w, world_h,
                                      player_rect, same_map, game)
            elif npc.fase_evento == "en_clase":
                self._update_en_clase(npc, dt_ms, player_rect, same_map)
            elif npc.fase_evento == "saliendo":
                self._update_saliendo(npc, dt_ms, walls, world_w, world_h,
                                      same_map, game)

    def draw(self, screen: pygame.Surface, cam_x: int, cam_y: int,
             world_w: int, world_h: int, current_map: str):
        if not self.npc_ai_active:
            return
        cur_key = _map_key(current_map)
        for npc in self.npcs:
            if not npc.alive() or npc.estado == "spawning":
                continue
            if npc.current_map_key() != cur_key:
                continue
            if npc.estado == "sitting":
                continue  # renderer dibuja el sprite grande desde _draw_seated_npc_at_pupitre
            self._draw_npc(screen, npc, cam_x, cam_y, world_w, world_h)

    # ── Update por fase ───────────────────────────────────────────────────────

    def _update_llegando(self, npc: NPCEntity, dt_ms: float, walls,
                         world_w, world_h, player_rect, same_map: bool, game):
        if npc.estado not in ("walking", "talking"):
            return

        # Reacción de proximidad
        if same_map and player_rect is not None and not npc.reacted_segment:
            px = player_rect.centerx / max(1, world_w)
            py = player_rect.centery / max(1, world_h)
            d2 = (npc.rx - px) ** 2 + (npc.ry - py) ** 2
            if d2 * world_w * world_w < _PROXIMITY_SQ:
                npc.reacted_segment = True
                npc.reaction_ms = 1000.0
                npc.estado = "talking"
                npc.anim_state = "hablando"

        if npc.estado == "talking":
            npc.reaction_ms -= dt_ms
            if npc.reaction_ms <= 0:
                npc.estado = "walking"
                npc.anim_state = "idle"
            return

        dest_wx = npc.destino_rx * world_w
        dest_wy = npc.destino_ry * world_h
        npc_wx = npc.rx * world_w
        npc_wy = npc.ry * world_h
        dist = _dist(npc_wx, npc_wy, dest_wx, dest_wy)

        if dist < 10:
            npc.waypoint_timeout_ms = 0.0
            npc.steer_stuck_ms = 0.0
            npc.steer_rodeo_target = None
            npc.anim_state = "idle"
            self._on_reached_destination(npc, game, walls)
            return

        npc.anim_state = "walk"

        # Timeout global
        npc.waypoint_timeout_ms += dt_ms
        mk_t = npc.current_map_key()
        is_chair_dest = (
            ("salondia" in mk_t or "salondía" in mk_t)
            and npc.waypoint_idx >= len(npc.waypoints) - 1
        )
        timeout_limit = _CHAIR_IDLE_TIMEOUT if is_chair_dest else _WP_TIMEOUT
        if npc.waypoint_timeout_ms > timeout_limit:
            if is_chair_dest:
                # Bug 5: no teleportar al asiento — dejar al NPC en idle donde está
                print(f"[NPC_AI] {npc.nombre} salon timeout → idle (sin teleport)")
                npc.waypoint_timeout_ms = 0.0
                npc.steer_stuck_ms = 0.0
                npc.steer_rodeo_target = None
                npc.steer_rodeo_ms = 0.0
                npc.velocidad = 0.0
                npc.anim_state = "idle"
            else:
                print(f"[NPC_AI] {npc.nombre} llegando timeout → teleport a waypoint")
                npc.rx = npc.destino_rx
                npc.ry = npc.destino_ry
                npc.waypoint_timeout_ms = 0.0
                npc.steer_stuck_ms = 0.0
                npc.steer_rodeo_target = None
                npc.steer_rodeo_ms = 0.0
                npc.fade_alpha = 0
                npc.fade_in_ms = _FADE_DUR
                npc.anim_state = "idle"
                self._on_reached_destination(npc, game, walls)
            return

        step = npc.velocidad * world_w * (dt_ms / 16.667)
        step = min(step, dist)
        dx_raw, dy_raw = _normalize(dest_wx - npc_wx, dest_wy - npc_wy)

        if same_map:
            self._move_npc(npc, dx_raw * step, dy_raw * step,
                           walls, world_w, world_h, dt_ms)
        else:
            npc.rx += dx_raw * step / world_w
            npc.ry += dy_raw * step / world_h
            self._update_facing(npc, dx_raw, dy_raw)

    def _update_en_clase(self, npc: NPCEntity, dt_ms: float,
                         player_rect, same_map: bool):
        if npc.estado != "sitting":
            return

        if npc.idle_active:
            npc.idle_alt_ms -= dt_ms
            if npc.idle_alt_ms <= 0:
                npc.idle_active = False
                npc.anim_state = "sitting"
                npc.idle_ms = random.uniform(4000, 8000)
            # else: mantener anim_state actual (dibujando/riendose/hablando)
        else:
            npc.idle_ms -= dt_ms
            if npc.idle_ms <= 0:
                npc.idle_active = True
                npc.idle_alt_ms = 1500.0
                if npc.nombre == "Sara":
                    npc.anim_state = "dibujando"
                elif npc.nombre == "Diego":
                    npc.anim_state = "riendose"
                else:
                    npc.anim_state = "hablando"

    def _update_en_clase_with_dims(self, npc: NPCEntity, dt_ms: float,
                                   player_rect, same_map: bool,
                                   world_w: int, world_h: int):
        self._update_en_clase(npc, dt_ms, player_rect, same_map)
        if same_map and player_rect is not None and not npc.idle_active:
            px = player_rect.centerx / max(1, world_w)
            py = player_rect.centery / max(1, world_h)
            d2 = (npc.rx - px) ** 2 + (npc.ry - py) ** 2
            if d2 * world_w * world_w < _PROXIMITY_SQ:
                npc.idle_active = True
                if npc.nombre == "Sara":
                    npc.idle_alt_ms = 2000.0
                    npc.anim_state = "hablando"
                elif npc.nombre == "Diego":
                    npc.idle_alt_ms = 1500.0
                    npc.anim_state = "riendose"
                else:
                    npc.idle_alt_ms = 800.0
                    npc.anim_state = "hablando"

    def _update_saliendo(self, npc: NPCEntity, dt_ms: float, walls,
                         world_w, world_h, same_map: bool, game):
        if npc.estado == "sitting":
            npc.anim_state = "sitting"
            npc.leave_elapsed_ms += dt_ms
            if npc.leave_elapsed_ms >= npc.leave_delay_ms:
                npc.estado = "leaving"
                npc.anim_state = "idle"
                self._assign_destination(npc, game, walls)
            return

        if npc.estado != "leaving":
            return

        dest_wx = npc.destino_rx * world_w
        dest_wy = npc.destino_ry * world_h
        npc_wx = npc.rx * world_w
        npc_wy = npc.ry * world_h
        dist = _dist(npc_wx, npc_wy, dest_wx, dest_wy)

        if dist < 10:
            npc.waypoint_timeout_ms = 0.0
            npc.steer_stuck_ms = 0.0
            npc.steer_rodeo_target = None
            npc.anim_state = "idle"
            self._on_reached_destination_saliendo(npc, game, walls)
            return

        npc.anim_state = "walk"

        # Timeout global → teleport con fade
        npc.waypoint_timeout_ms += dt_ms
        if npc.waypoint_timeout_ms > _WP_TIMEOUT:
            print(f"[NPC_AI] {npc.nombre} saliendo timeout → teleport")
            npc.rx = npc.destino_rx
            npc.ry = npc.destino_ry
            npc.waypoint_timeout_ms = 0.0
            npc.steer_stuck_ms = 0.0
            npc.steer_rodeo_target = None
            npc.steer_rodeo_ms = 0.0
            npc.fade_alpha = 0
            npc.fade_in_ms = _FADE_DUR
            npc.anim_state = "idle"
            self._on_reached_destination_saliendo(npc, game, walls)
            return

        step = npc.velocidad * world_w * (dt_ms / 16.667)
        step = min(step, dist)
        dx_raw, dy_raw = _normalize(dest_wx - npc_wx, dest_wy - npc_wy)

        if same_map:
            self._move_npc(npc, dx_raw * step, dy_raw * step,
                           walls, world_w, world_h, dt_ms)
        else:
            npc.rx += dx_raw * step / world_w
            npc.ry += dy_raw * step / world_h
            self._update_facing(npc, dx_raw, dy_raw)

    # ── Lógica de destinos y transiciones ────────────────────────────────────

    def _assign_destination(self, npc: NPCEntity, game, walls):
        mk = npc.current_map_key()
        npc.waypoint_timeout_ms = 0.0
        npc.steer_stuck_ms = 0.0
        npc.steer_rodeo_target = None
        npc.steer_rodeo_ms = 0.0

        if npc.fase_evento == "llegando":
            if "patiod" in mk:
                door = self._find_door(walls, "pasillo1_dia", game) or _E1_DOOR["patio_exit"]
                npc.destino_rx, npc.destino_ry = door
                wpts = self._load_waypoints(npc.fondo_actual)
                npc.waypoints = wpts + [door]
                npc.waypoint_idx = 0
                self._advance_waypoint(npc)
            elif "pasillo1_dia" in mk:
                door = self._find_door(walls, "salondia", game) or _E1_DOOR["pasillo_exit"]
                npc.destino_rx, npc.destino_ry = door
                wpts = self._load_waypoints(npc.fondo_actual)
                npc.waypoints = wpts + [door]
                npc.waypoint_idx = 0
                self._advance_waypoint(npc)
            elif "salondia" in mk or "salondía" in mk:
                chair = self._get_npc_chair(npc.nombre, game)
                npc.dentro_del_salon = False
                if chair:
                    npc.chair_rx, npc.chair_ry = chair
                    # Bug 4: navegar por waypoints interiores antes de sentarse
                    wpts = self._load_waypoints("salonDia.png")
                    npc.waypoints = wpts + [chair]
                    npc.waypoint_idx = 0
                    self._advance_waypoint(npc)
                else:
                    npc.chair_rx, npc.chair_ry = npc.rx, npc.ry
                    npc.destino_rx, npc.destino_ry = npc.rx, npc.ry

        elif npc.fase_evento == "saliendo":
            if any(k in mk for k in ("salontarde", "salondia", "salondía")):
                door = (self._find_door(walls, "pasillo1_tarde", game)
                        or self._find_door(walls, "pasillo1", game))
                if door:
                    npc.destino_rx, npc.destino_ry = door
            elif "pasillo1" in mk:
                door = (self._find_door(walls, "patiotarde", game)
                        or self._find_door(walls, "patiod", game))
                if door:
                    npc.destino_rx, npc.destino_ry = door
            elif "patiotarde" in mk or "patiod" in mk:
                door = self._find_door(walls, "calle", game)
                if door:
                    npc.destino_rx, npc.destino_ry = door

    def _advance_waypoint(self, npc: NPCEntity):
        if npc.waypoint_idx < len(npc.waypoints):
            wp = npc.waypoints[npc.waypoint_idx]
            npc.destino_rx, npc.destino_ry = wp
            npc.waypoint_timeout_ms = 0.0
            npc.steer_stuck_ms = 0.0
            npc.steer_rodeo_target = None
            npc.steer_rodeo_ms = 0.0

    def _on_reached_destination(self, npc: NPCEntity, game, walls):
        mk = npc.current_map_key()

        if npc.waypoint_idx < len(npc.waypoints) - 1:
            npc.waypoint_idx += 1
            # Bug 4: primer waypoint interior del salón alcanzado → habilitar sentarse
            if ("salondia" in mk or "salondía" in mk) and npc.waypoint_idx >= 1:
                npc.dentro_del_salon = True
            self._advance_waypoint(npc)
            return

        if "patiod" in mk:
            self._teleport_npc(npc, "Pasillo1_dia.png", *_ARRIVAL_SPAWN["Pasillo1_dia.png"])
            self._assign_destination(npc, game, walls)
        elif "pasillo1_dia" in mk:
            self._teleport_npc(npc, "salonDia.png", *_ARRIVAL_SPAWN["salonDia.png"])
            self._assign_destination(npc, game, walls)
        elif "salondia" in mk or "salondía" in mk:
            if not npc.dentro_del_salon:
                # Bug 4: aún no pasó checkpoint interior — seguir esperando en idle
                npc.anim_state = "idle"
                return
            npc.estado = "sitting"
            npc.anim_state = "sitting"
            if npc.chair_rx is not None:
                npc.rx = npc.chair_rx
                npc.ry = npc.chair_ry
            # Mejora 2: marcar pupitre como ocupado para ocultar la decoración
            pup_set = getattr(game, "pupitres_ocupados", None)
            if pup_set is not None and npc.chair_rx is not None:
                pup_set.add((round(npc.chair_rx, 4), round(npc.chair_ry, 4)))

    def _on_reached_destination_saliendo(self, npc: NPCEntity, game, walls):
        mk = npc.current_map_key()

        if any(k in mk for k in ("salontarde", "salondia", "salondía")):
            self._teleport_npc(npc, "Pasillo1_tarde.png", *_ARRIVAL_SPAWN["Pasillo1_tarde.png"])
            self._assign_destination(npc, game, walls)
        elif "pasillo1" in mk:
            self._teleport_npc(npc, "PatioTarde.png", *_ARRIVAL_SPAWN["PatioTarde.png"])
            self._assign_destination(npc, game, walls)
        elif "patiotarde" in mk:
            npc.estado = "despawned"

    def _teleport_npc(self, npc: NPCEntity, new_fondo: str, rx: float, ry: float):
        npc.fondo_actual = new_fondo
        npc.rx = rx
        npc.ry = ry
        npc.reacted_segment = False
        npc.waypoints = []
        npc.waypoint_idx = 0
        npc.steer_stuck_ms = 0.0
        npc.steer_rodeo_target = None
        npc.steer_rodeo_ms = 0.0
        npc.waypoint_timeout_ms = 0.0
        npc.fade_alpha = 0
        npc.fade_in_ms = _FADE_DUR

    # Posiciones normalizadas de sillas sin npc_owner en el JSON (no modificar JSON)
    _SALON_NPC_FALLBACK: dict = {
        "NPC2": (0.44587, 0.52964),   # D3 — decoracion index 2
    }

    def _place_npcs_at_chairs(self, game):
        """Spawna (o recoloca) todos los NPCs pendientes directamente en sus sillas."""
        pup_set = getattr(game, "pupitres_ocupados", None)
        # Reubicar NPCs ya existentes que aún no estén sentados.
        # Para los ya sentados, solo re-registrar su silla en pupitres_ocupados
        # (que fue limpiado por _change_adventure_background al re-entrar al mapa).
        for npc in self.npcs:
            if not npc.alive():
                continue
            if npc.estado == "sitting":
                # Volver a registrar la silla para que _draw_object_interactables
                # sepa que debe dibujar al NPC sentado en lugar del pupitre vacío.
                if pup_set is not None and npc.chair_rx is not None:
                    pup_set.add((round(npc.chair_rx, 4), round(npc.chair_ry, 4)))
                continue
            chair = self._get_npc_chair(npc.nombre, game)
            if chair:
                npc.fondo_actual = "salonDia.png"
                npc.chair_rx, npc.chair_ry = chair
                npc.rx, npc.ry = chair
                npc.estado = "sitting"
                npc.anim_state = "sitting"
                npc.dentro_del_salon = True
                npc.fade_alpha = 255
                npc.fade_in_ms = 0.0
                if pup_set is not None:
                    pup_set.add((round(chair[0], 4), round(chair[1], 4)))
        # Crear NPCs pendientes por primera vez
        for nombre in self._pending_salon_npcs:
            chair = self._get_npc_chair(nombre, game)
            if chair is None:
                chair = self._SALON_NPC_FALLBACK.get(nombre)
            if chair is None:
                continue
            rx, ry = chair
            npc = NPCEntity(nombre, "salonDia.png", rx, ry,
                            _SPEEDS.get(nombre, 0.0022), 0)
            npc.estado = "sitting"
            npc.anim_state = "sitting"
            npc.fase_evento = "llegando"
            npc.chair_rx, npc.chair_ry = rx, ry
            npc.dentro_del_salon = True
            npc.fade_alpha = 255
            npc.fade_in_ms = 0.0
            if pup_set is not None:
                pup_set.add((round(rx, 4), round(ry, 4)))
            self.npcs.append(npc)
        self._pending_salon_npcs = []

    # ── Pathfinding — Bug 3 ───────────────────────────────────────────────────

    def _update_facing(self, npc: NPCEntity, dx: float, dy: float):
        """Actualiza la dirección del NPC a partir del vector de movimiento."""
        if abs(dx) > abs(dy):
            npc.facing = "right" if dx > 0 else "left"
        elif abs(dy) > 0.001:
            npc.facing = "down" if dy > 0 else "up"

    def _move_npc(self, npc: NPCEntity, dx_px: float, dy_px: float,
                  walls, world_w: int, world_h: int, dt_ms: float):
        """
        Mueve el NPC usando separación de ejes + wall-following.
        Algoritmo:
          1. Vector completo
          2. Solo X / solo Y
          3. Modo rodeo (perpendicular) si bloqueado > 500ms
          4. Timeout rodeo 3s → abortar rodeo
        """
        hw, hh = _NPC_W // 2, _NPC_H // 2

        def _rect(x_px, y_px):
            return pygame.Rect(int(x_px - hw), int(y_px - hh), _NPC_W, _NPC_H)

        cx = npc.rx * world_w
        cy = npc.ry * world_h

        # ── Modo rodeo activo ─────────────────────────────────────────────────
        if npc.steer_rodeo_target is not None:
            npc.steer_rodeo_ms += dt_ms
            if npc.steer_rodeo_ms > _RODEO_TIMEOUT:
                # Timeout: abandonar rodeo, el caller hará teleport si sigue bloqueado
                npc.steer_rodeo_target = None
                npc.steer_rodeo_ms = 0.0
                npc.steer_stuck_ms = 0.0
                return

            rtx = npc.steer_rodeo_target[0] * world_w
            rty = npc.steer_rodeo_target[1] * world_h
            rdx = rtx - cx
            rdy = rty - cy
            rdist = math.hypot(rdx, rdy)

            if rdist < 15:
                npc.steer_rodeo_target = None
                npc.steer_rodeo_ms = 0.0
                npc.steer_stuck_ms = 0.0
                # continuar con movimiento normal abajo
            else:
                speed = math.hypot(dx_px, dy_px)
                step = min(rdist, speed)
                rndx, rndy = _normalize(rdx, rdy)
                rdx_s, rdy_s = rndx * step, rndy * step

                # Intentar el rodeo con separación de ejes
                if not self._collides_walls(_rect(cx + rdx_s, cy + rdy_s), walls, world_w, world_h):
                    npc.rx += rdx_s / world_w
                    npc.ry += rdy_s / world_h
                    self._update_facing(npc, rdx_s, rdy_s)
                    return
                if not self._collides_walls(_rect(cx + rdx_s, cy), walls, world_w, world_h):
                    npc.rx += rdx_s / world_w
                    self._update_facing(npc, rdx_s, 0)
                    return
                if not self._collides_walls(_rect(cx, cy + rdy_s), walls, world_w, world_h):
                    npc.ry += rdy_s / world_h
                    self._update_facing(npc, 0, rdy_s)
                    return
                # Rodeo también bloqueado — incrementar timer y salir
                npc.steer_rodeo_ms += dt_ms  # extra penalty
                return

        # ── Movimiento normal ─────────────────────────────────────────────────

        # PASO 1: vector completo
        if not self._collides_walls(_rect(cx + dx_px, cy + dy_px), walls, world_w, world_h):
            npc.rx += dx_px / world_w
            npc.ry += dy_px / world_h
            self._update_facing(npc, dx_px, dy_px)
            npc.steer_stuck_ms = 0.0
            return

        # PASO 2a: solo eje X
        if not self._collides_walls(_rect(cx + dx_px, cy), walls, world_w, world_h):
            npc.rx += dx_px / world_w
            self._update_facing(npc, dx_px, 0)
            npc.steer_stuck_ms = max(0.0, npc.steer_stuck_ms - dt_ms * 0.5)
            return

        # PASO 2b: solo eje Y
        if not self._collides_walls(_rect(cx, cy + dy_px), walls, world_w, world_h):
            npc.ry += dy_px / world_h
            self._update_facing(npc, 0, dy_px)
            npc.steer_stuck_ms = max(0.0, npc.steer_stuck_ms - dt_ms * 0.5)
            return

        # PASO 3: completamente bloqueado
        npc.steer_stuck_ms += dt_ms

        # PASO 4: entrar en rodeo si bloqueado suficiente tiempo
        if npc.steer_stuck_ms > _STUCK_THRESHOLD and npc.steer_rodeo_target is None:
            dx_dest = npc.destino_rx - npc.rx
            dy_dest = npc.destino_ry - npc.ry
            d = math.hypot(dx_dest, dy_dest)
            if d > 0.001:
                nx, ny = dx_dest / d, dy_dest / d
                # Perpendicular derecha: (-ny, nx)
                perp_x, perp_y = -ny, nx
                rodeo_rx = max(0.01, min(0.99, npc.rx + perp_x * 0.06))
                rodeo_ry = max(0.01, min(0.99, npc.ry + perp_y * 0.06))
                # Si la perpendicular derecha parece bloqueada, probar izquierda
                test_rod = _rect(rodeo_rx * world_w, rodeo_ry * world_h)
                if self._collides_walls(test_rod, walls, world_w, world_h):
                    rodeo_rx = max(0.01, min(0.99, npc.rx - perp_x * 0.06))
                    rodeo_ry = max(0.01, min(0.99, npc.ry - perp_y * 0.06))
                npc.steer_rodeo_target = (rodeo_rx, rodeo_ry)
                npc.steer_rodeo_ms = 0.0

    def _collides_walls(self, test_rect: pygame.Rect, walls,
                        world_w: int, world_h: int) -> bool:
        for h in walls:
            if h.get("type") != "rect":
                continue
            if h.get("role", "wall") == "interactable" and not h.get("blocking", False):
                continue
            r = pygame.Rect(
                int(world_w * h["rx"]), int(world_h * h["ry"]),
                max(8, int(world_w * h["rw"])), max(8, int(world_h * h["rh"])),
            )
            if test_rect.colliderect(r):
                return True
        return False

    # ── Utilidades de mapa / JSON ─────────────────────────────────────────────

    def _load_waypoints(self, fondo_name: str) -> list[tuple[float, float]]:
        base = os.path.splitext(os.path.basename(fondo_name))[0]
        key = base.lower()
        if key in self._waypoints_cache:
            return list(self._waypoints_cache[key])
        path = os.path.join(self.base_dir, "Hitboxes", f"{base}_hitboxes.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            wpts = [(float(p["rx"]), float(p["ry"])) for p in data.get("npc_waypoints", [])]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            wpts = []
        self._waypoints_cache[key] = wpts
        return list(wpts)

    def _find_door(self, walls, target_kw: str, game) -> tuple[float, float] | None:
        kw = target_kw.lower()
        for h in walls:
            if h.get("role") != "interactable" or h.get("action") != "puerta":
                continue
            if h.get("type") != "rect":
                continue
            tgt = h.get("target_image", "").lower().replace("\\", "/")
            if kw in tgt:
                cx = h["rx"] + h["rw"] / 2
                cy = h["ry"] + h["rh"] / 2
                return (cx, cy)
        return None

    def _get_npc_chair(self, nombre: str, game) -> tuple[float, float] | None:
        walls = getattr(game, "story_walls", [])
        nombre_lower = nombre.lower()
        for h in walls:
            action = h.get("action", "")
            if action == "objeto":
                if "pupitre" not in h.get("object_name", "").lower():
                    continue
            elif action == "pupitre":
                pass  # compatibilidad con hitboxes antiguos
            else:
                continue
            if h.get("npc_owner", "").lower() == nombre_lower and h.get("type") == "rect":
                cx = h["rx"] + h["rw"] / 2
                cy = h["ry"] + h["rh"] / 2
                return (cx, cy)
        return None

    def _current_map_name(self, game) -> str:
        fondo = getattr(game, "aventura_fondo", None)
        if fondo is None:
            return ""
        return os.path.basename(str(getattr(fondo, "ruta_imagen", "")))

    # ── Resolución de assets de sprite ───────────────────────────────────────

    def _get_npc_dir(self, nombre: str) -> str:
        """Devuelve la carpeta del personaje, con fallback a NPC1."""
        npc_dir = os.path.join(self.base_dir, "Imagenes", "Personajes", nombre)
        if os.path.isdir(npc_dir):
            return npc_dir
        fallback = os.path.join(self.base_dir, "Imagenes", "Personajes", "NPC1")
        return fallback if os.path.isdir(fallback) else ""

    def _resolve_anim_file(self, nombre: str, anim_state: str, facing: str) -> str:
        """
        Devuelve la ruta absoluta del sprite para (nombre, anim_state, facing).
        Usa el patrón real de archivos: {Nombre}_{animacion}_{direccion}.png
        """
        npc_dir = self._get_npc_dir(nombre)
        if not npc_dir:
            return ""

        def try_f(fname: str) -> str:
            p = os.path.join(npc_dir, fname)
            return p if os.path.isfile(p) else ""

        if anim_state == "sitting":
            return (try_f(f"{nombre}_Sentado.png")
                    or try_f(f"{nombre}_sentado.png")
                    or try_f(f"{nombre}_idle_{facing}.png")
                    or try_f(f"{nombre}_idle_down.png"))

        if anim_state == "walk":
            return (try_f(f"{nombre}_walk_{facing}.png")
                    or try_f(f"{nombre}_idle_{facing}.png")
                    or try_f(f"{nombre}_idle_down.png"))

        # Estados con sprites específicos (dibujando, riendose, hablando, mirando…)
        specific = try_f(f"{nombre}_{anim_state}.png")
        if specific:
            return specific

        # Fallback: idle con dirección
        return (try_f(f"{nombre}_idle_{facing}.png")
                or try_f(f"{nombre}_idle_down.png"))

    def _get_idle_width(self, nombre: str) -> int:
        """Ancho del frame idle (para calcular frame_count en walk sheets)."""
        if nombre in self._idle_width_cache:
            return self._idle_width_cache[nombre]
        npc_dir = self._get_npc_dir(nombre)
        w = 0
        if npc_dir:
            idle_path = os.path.join(npc_dir, f"{nombre}_idle_down.png")
            if os.path.isfile(idle_path):
                try:
                    img = pygame.image.load(idle_path)
                    w = img.get_width()
                except (OSError, pygame.error):
                    w = 0
        self._idle_width_cache[nombre] = w
        return w

    # ── Carga de frames ───────────────────────────────────────────────────────

    def _load_frames(self, nombre: str, anim_state: str,
                     facing: str) -> list[pygame.Surface]:
        cache_key = (nombre, anim_state, facing)
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]

        path = self._resolve_anim_file(nombre, anim_state, facing)
        if not path:
            print(f"[NPC_AI] FALTANTE: {nombre} anim={anim_state} facing={facing}")
            self._sprite_cache[cache_key] = []
            return []

        print(f"[NPC_AI] Cargando: {os.path.relpath(path, self.base_dir)}")
        if anim_state == "walk":
            frames = self._load_sheet_by_idle_width(path, nombre)
        else:
            frames = self._load_sheet(path)

        self._sprite_cache[cache_key] = frames
        return frames

    def _load_sheet(self, path: str) -> list[pygame.Surface]:
        """Carga un sprite (estático o spritesheet) aplicando convert_alpha()."""
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except (OSError, pygame.error, FileNotFoundError):
            return []
        sw, sh = sheet.get_size()
        basename = os.path.basename(path).lower()
        is_static = any(t in basename for t in ("sentado", "idle", "stand", "parado"))
        count = 1 if is_static else max(1, round(sw / max(1, sh)))
        fw = max(1, sw // count)
        return self._slice_sheet(sheet, sw, sh, count, fw)

    def _load_sheet_by_idle_width(self, path: str, nombre: str) -> list[pygame.Surface]:
        """
        Carga un walk spritesheet dividiendo por el ancho del idle frame del mismo
        personaje para obtener el frame_count correcto.
        Ejemplo: Sara walk_down 472×96, idle_down 118px → 4 frames.
                 Carlos walk_down 944×192, idle_down 118px → 8 frames.
        """
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except (OSError, pygame.error, FileNotFoundError):
            return []
        sw, sh = sheet.get_size()
        idle_w = self._get_idle_width(nombre)
        if idle_w > 0 and sw % idle_w == 0:
            count = sw // idle_w
            fw = idle_w
        else:
            # fallback
            count = max(1, round(sw / max(1, sh)))
            fw = sw // count
        return self._slice_sheet(sheet, sw, sh, count, fw)

    def _slice_sheet(self, sheet: pygame.Surface, sw: int, sh: int,
                     count: int, fw: int) -> list[pygame.Surface]:
        frames = []
        for i in range(count):
            f = sheet.subsurface(pygame.Rect(i * fw, 0, fw, sh)).copy()
            h_px = max(76, int(f.get_height() * 0.82))
            w_px = max(42, int(f.get_width() * (h_px / max(1, f.get_height()))))
            frames.append(pygame.transform.smoothscale(f, (w_px, h_px)))
        return frames

    # ── Renderizado ───────────────────────────────────────────────────────────

    def _draw_npc(self, screen: pygame.Surface, npc: NPCEntity,
                  cam_x: int, cam_y: int, world_w: int, world_h: int):
        # idle y sitting-prematuro: frame 0 de la hoja de caminata
        # (sitting real nunca llega aquí: draw() lo salta cuando estado=="sitting")
        if npc.anim_state in ("idle", "sitting"):
            frames = self._load_frames(npc.nombre, "walk", npc.facing)
            if not frames:
                frames = self._load_frames(npc.nombre, "walk", "down")
            frame_idx = 0
        elif npc.anim_state == "walk":
            frames = self._load_frames(npc.nombre, "walk", npc.facing)
            frame_idx = npc.walk_frame_idx % max(1, len(frames))
        else:
            frames = self._load_frames(npc.nombre, npc.anim_state, npc.facing)
            frame_idx = int(npc.anim_ms // 220) % max(1, len(frames))

        sx = int(npc.rx * world_w) - cam_x
        sy = int(npc.ry * world_h) - cam_y

        if not frames:
            # "Imagen Faltante" — borde rosa, no bloque gris sólido
            rect = pygame.Rect(sx - _NPC_W // 2, sy - _NPC_H // 2, _NPC_W, _NPC_H)
            pygame.draw.rect(screen, (255, 20, 147), rect, 2)
            return

        frame = frames[frame_idx]

        if npc.fade_alpha < 255:
            frame = frame.copy()
            frame.set_alpha(npc.fade_alpha)

        fw, fh = frame.get_size()
        screen.blit(frame, (sx - fw // 2, sy - fh // 2))
