# ASSETS PENDIENTES — EmpatiaQuest

Lista completa de todos los recursos visuales y de audio marcados en el código
con los prefijos `🖼️ ASSET_IMG`, `🎨 ASSET_UI`, `🎵 ASSET_SFX` y `🎶 ASSET_BGM`.

Cada asset tiene un **fallback procedural** implementado: el juego corre sin ellos.
Cuando el asset se crea, basta con colocarlo en la ruta indicada para que se cargue
automáticamente en la próxima ejecución.

---

## 🖼️ Sprites e imágenes del mundo (`ASSET_IMG`)

> **Día 1 — nuevos assets (CAMBIOS 3, 4)**

| Archivo | Dimensiones | Descripción |
|---|---|---|
| `Imagenes/Interactuables/PupitreRayado_zoom.png` | 1280×720 | Pupitre con insultos escritos, vista de cerca |
| `Imagenes/Interactuables/PupitreRayones.png` | 1280×720 | Capa transparente PNG con los insultos encima del pupitre (para borrar progresivamente) |
| `Imagenes/UI/borrador_cursor.png` | 48×48 | Borrador de tablero pixel-art (cursor del minijuego de borrado) |
| `Imagenes/Personajes/Profesor/parado.png` | mismas dims que otros NPCs | Profesor adulto pixel-art, sprite parado |

> **Personajes existentes**

| Archivo | Dimensiones | Descripción |

| Archivo | Dimensiones | Descripción |
|---|---|---|
| `Imagenes/Personajes/NPC2/parado.png` | mismas que NPC1 | Sprite en reposo del NPC2 (fallback: usa NPC1) |
| `Imagenes/Personajes/NPC2/sentado.png` | mismas que NPC1 | Sprite sentado del NPC2 (fallback: usa NPC1) |
| `Imagenes/Personajes/NPC2/hablando.png` | mismas que NPC1 | Sprite hablando del NPC2 (fallback: usa NPC1) |

---

## 🎨 Assets de interfaz de usuario (`ASSET_UI`)

> **Escena cinemática Día 1 — nuevos assets de UI (SceneManager)**

| Archivo | Dimensiones | Descripción |
|---|---|---|
| `Imagenes/UI/caja_dialogo.png` | 1280×140 | Fondo decorativo de la caja de diálogo cinemática (fallback: rect semitransparente) |

> **Día 1 — nuevos assets de UI (CAMBIOS 1, 2)**

| Archivo | Dimensiones | Descripción |
|---|---|---|
| `Imagenes/UI/fondo_nombre.png` | 1280×720 | Pantalla de ingreso de nombre, estilo pixel-art escolar |
| `Imagenes/flecha_guia.png` | 64×64 | Flecha pixel-art amarilla apuntando hacia arriba, se rota por código según dirección |

> **Assets de UI existentes**

| Archivo | Dimensiones | Descripción |
|---|---|---|
| `Imagenes/UI/logo_menu.png` | 800×200 | Logo "EMPATIA QUEST" en el menú (fallback: texto pixel) |
| `Imagenes/UI/logo_empatia_quest.png` | 600×200 | Logo del juego en créditos (fallback: texto pixel) |
| `Imagenes/UI/popup_logro.png` | 400×100 | Banner de logro desbloqueado estilo Undertale (fallback: rect + texto) |
| `Imagenes/UI/habilidades_panel.png` | 500×600 | Panel lateral de habilidades (TAB) (fallback: rect + texto) |
| `Imagenes/UI/transition_overlay.png` | 1280×720 | Overlay negro para transiciones de pantalla (fallback: Surface negro) |
| `Imagenes/UI/barra_felicidad.png` | 240×24 | Barra de felicidad estilo pixel-art (fallback: rect naranja) |
| `Imagenes/UI/barra_reputacion.png` | 240×24 | Barra de reputación estilo pixel-art (fallback: rect azul) |
| `Imagenes/UI/icono_logro_desbloqueado.png` | 36×36 | Estrella dorada (fallback: polígono procedural) |
| `Imagenes/UI/icono_logro_bloqueado.png` | 36×36 | Candado gris (fallback: rectángulo procedural) |
| `Imagenes/UI/icono_habilidad.png` | 48×48 | Icono genérico de habilidad (fallback: rect coloreado) |
| `Imagenes/UI/capitulo_completado.png` | 300×80 | Banner de capítulo completado (fallback: rect verde) |
| `Imagenes/UI/capitulo_bloqueado.png` | 300×80 | Banner de capítulo bloqueado con candado (fallback: rect gris) |
| `Imagenes/UI/icono_dia.png` | 40×40 | Icono de día del calendario escolar (fallback: texto) |
| `Imagenes/UI/tutorial_controles.png` | 800×400 | Diagrama de controles WASD (fallback: teclas procedurales) |
| `Imagenes/UI/tutorial_stats.png` | 800×400 | Diagrama de barras F y R (fallback: barras procedurales) |
| `Imagenes/UI/tutorial_decisiones.png` | 800×400 | Diagrama del flujo de decisiones (fallback: texto) |

---

## 🎵 Efectos de sonido (`ASSET_SFX`)

> **Minijuego Penaltis — nuevos SFX**

| Archivo | Descripción |
|---|---|
| `Audio/SFX/balon_disparo.ogg` | Sonido de patear el balón al disparar |
| `Audio/SFX/gol_marcado.ogg` | Fanfare breve al marcar un gol |
| `Audio/SFX/balon_bloqueado.ogg` | Sonido de disparo bloqueado o fuera |

> **Minijuego Atrapa Emociones — nuevos SFX**

| Archivo | Descripción |
|---|---|
| `Audio/SFX/emocion_buena.ogg` | Tono positivo al atrapar emoción buena |
| `Audio/SFX/emocion_mala.ogg` | Sonido negativo al atrapar emoción mala |

> **Minijuego Undertale — nuevos SFX**

| Archivo | Descripción |
|---|---|
| `Audio/SFX/hit_corazon.ogg` | Golpe recibido por el corazón del jugador |
| `Audio/SFX/minijuego_ganar.ogg` | Fanfare breve de victoria al sobrevivir 60s |
| `Audio/SFX/minijuego_perder.ogg` | Sonido de derrota al perder las 3 vidas |

> **Escena cinemática Día 1 — nuevos SFX (SceneManager)**

| Archivo | Descripción |
|---|---|
| `Audio/SFX/dialogo_letra.ogg` | Sonido de typewriter reproducido por cada carácter de la caja de diálogo cinemática |

> **Día 1 — nuevos SFX (CAMBIO 4)**

| Archivo | Descripción |
|---|---|
| `Audio/SFX/camara_foto.ogg` | Sonido de shutter de cámara (opción C del pupitre) |

> **SFX existentes**

Ruta base: `Audio/SFX/`

| Archivo | Descripción |
|---|---|
| `click_boton.ogg` | Clic en un botón de menú |
| `hover_boton.ogg` | Hover sobre botón de menú |
| `guardar_partida.ogg` | Confirmación al guardar la partida |
| `decision_tomada.ogg` | Al elegir una opción de evento narrativo |
| `logro_desbloqueado.ogg` | Fanfare breve al desbloquear un logro |
| `pasos.ogg` | Pasos del personaje al moverse |
| `puerta.ogg` | Al cruzar una puerta / cambio de mapa |
| `interactuar.ogg` | Al interactuar con un objeto del mundo |
| `sentarse.ogg` | Al sentarse o levantarse de una silla |
| `dialogo_avanzar.ogg` | Al avanzar texto de diálogo en el prólogo |

---

## 🎶 Música de fondo (`ASSET_BGM`)

Ruta base: `Audio/BGM/`

| Archivo | Descripción |
|---|---|
| `menu_principal.ogg` | Música tranquila pixel-art — menú, jugar, creador de personaje |
| `prologo.ogg` | Nostálgico y melancólico — prólogo/flashback |
| `exploracion.ogg` | Ambiente escolar suave — exploración del mundo |
| `decision.ogg` | Tensión leve — cuando aparece un evento de decisión |
| `final_positivo.ogg` | Esperanzador y cálido — final positivo |
| `final_negativo.ogg` | Sombrío y melancólico — final negativo |
| `final_neutral.ogg` | Ambiguo — los dos finales neutrales |
| `minijuego_batalla.ogg` | Música tensa estilo Undertale durante los 60s del minijuego |
| `minijuego_penaltis.ogg` | Música arcade rápida y animada para el minijuego de penaltis |
| `minijuego_emociones.ogg` | Música suave y emotiva para el minijuego de Atrapa Emociones |

---

## Notas de implementación

- Todos los assets de audio deben estar en formato **OGG Vorbis** (compatibilidad con `pygame.mixer`).
- Los sprites de NPC deben ser **sprite sheets horizontales** con 4 frames para animaciones
  de movimiento, o 1 frame para animaciones estáticas (el código detecta `sentado/parado/idle/stand`
  en el nombre de archivo y carga 1 frame).
- Los assets de UI pueden estar en **PNG con canal alfa** (`.convert_alpha()` aplicado automáticamente).
- Si un asset de BGM o SFX no existe, `AudioManager` falla silenciosamente y el juego
  continúa sin sonido en ese evento.
