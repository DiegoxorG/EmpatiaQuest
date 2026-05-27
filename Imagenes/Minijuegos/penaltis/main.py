import pygame
import math
import os
import random

# =========================
# INICIALIZAR
# =========================

pygame.init()

ANCHO = 1200
ALTO = 700

pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Penaltis")

clock = pygame.time.Clock()

# =========================
# RUTAS
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ruta_imagenes = os.path.join(BASE_DIR, "imagenes_penaltis")

# =========================
# CARGAR IMÁGENES
# =========================

fondo = pygame.image.load(
    os.path.join(ruta_imagenes, "cancha.jpeg")
).convert()

balon_original = pygame.image.load(
    os.path.join(ruta_imagenes, "balon.png")
).convert_alpha()

# =========================
# ESCALAR
# =========================

fondo = pygame.transform.scale(fondo, (ANCHO, ALTO))

TAMANO_INICIAL_BALON = 50

balon = pygame.transform.scale(
    balon_original,
    (TAMANO_INICIAL_BALON, TAMANO_INICIAL_BALON)
)

# =========================
# ARCO
# =========================

ARCO_X1 = 457
ARCO_X2 = 766

ARCO_Y = 233
ARCO_ALTO = 116

ARCO_ANCHO = ARCO_X2 - ARCO_X1

# =========================
# BARRA ENTRENAMIENTO
# =========================

barra_ancho = 90
barra_alto = 16

barra_x = 560
barra_y = 233

barra = pygame.Rect(
    barra_x,
    barra_y,
    barra_ancho,
    barra_alto
)

velocidad_barra = 4
direccion_barra = 1

# =========================
# BALÓN
# =========================

balon_x = ANCHO // 2 - 25
balon_y = 560

vel_x = 0
vel_y = 0

disparado = False

tamano_balon = TAMANO_INICIAL_BALON

# =========================
# TRAYECTORIA
# =========================

trayectoria = []

# =========================
# MODO
# =========================

entrenamiento = True

intentos = 0
MAX_INTENTOS = 5

# =========================
# ESPACIOS ABIERTOS
# =========================

espacios_abiertos = []

# =========================
# TEXTO
# =========================

fuente = pygame.font.SysFont("Arial", 38, bold=True)

mensaje = ""

goles = 0

# =========================
# GENERAR ESPACIOS DIFÍCILES
# =========================

def generar_espacios():

    global espacios_abiertos

    espacios_abiertos = []

    # MÁS DIFÍCIL CADA RONDA
    tamaños = [50, 40, 35, 30, 25]

    tamaño = tamaños[min(intentos, 4)]

    # ESQUINAS
    esquina_izq = pygame.Rect(
        ARCO_X1 + 5,
        ARCO_Y,
        tamaño,
        ARCO_ALTO
    )

    esquina_der = pygame.Rect(
        ARCO_X2 - tamaño - 5,
        ARCO_Y,
        tamaño,
        ARCO_ALTO
    )

    espacios_abiertos.append(esquina_izq)
    espacios_abiertos.append(esquina_der)

    # HUECO EXTRA ALEATORIO
    if intentos >= 2:

        x_random = random.randint(
            ARCO_X1 + 80,
            ARCO_X2 - 80
        )

        espacio_random = pygame.Rect(
            x_random,
            ARCO_Y,
            tamaño,
            ARCO_ALTO
        )

        espacios_abiertos.append(espacio_random)

# =========================
# RESET
# =========================

def reset_balon():

    global balon_x
    global balon_y
    global vel_x
    global vel_y
    global disparado
    global trayectoria
    global balon
    global tamano_balon

    balon_x = ANCHO // 2 - 25
    balon_y = 560

    vel_x = 0
    vel_y = 0

    disparado = False

    trayectoria = []

    tamano_balon = TAMANO_INICIAL_BALON

    balon = pygame.transform.scale(
        balon_original,
        (tamano_balon, tamano_balon)
    )

# =========================
# GENERAR PRIMEROS ESPACIOS
# =========================

generar_espacios()

# =========================
# BUCLE PRINCIPAL
# =========================

running = True

while running:

    clock.tick(60)

    # =====================
    # EVENTOS
    # =====================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        # DISPARAR
        if event.type == pygame.MOUSEBUTTONDOWN:

            if not disparado and intentos < MAX_INTENTOS:

                mouse_x, mouse_y = pygame.mouse.get_pos()

                dx = mouse_x - balon_x
                dy = mouse_y - balon_y

                distancia = math.sqrt(dx**2 + dy**2)

                velocidad = 13

                vel_x = (dx / distancia) * velocidad
                vel_y = (dy / distancia) * velocidad

                disparado = True

                mensaje = ""

    # =====================
    # BARRA SOLO ENTRENAMIENTO
    # =====================

    if entrenamiento:

        barra.x += velocidad_barra * direccion_barra

        if barra.left <= ARCO_X1:
            direccion_barra = 1

        if barra.right >= ARCO_X2:
            direccion_barra = -1

    # =====================
    # MOVER BALÓN
    # =====================

    if disparado:

        balon_x += vel_x
        balon_y += vel_y

        trayectoria.append((
            balon_x + tamano_balon // 2,
            balon_y + tamano_balon // 2
        ))

        # HACER PEQUEÑO
        if tamano_balon > 18:

            tamano_balon -= 1

            balon = pygame.transform.scale(
                balon_original,
                (tamano_balon, tamano_balon)
            )

        balon_rect = pygame.Rect(
            balon_x,
            balon_y,
            tamano_balon,
            tamano_balon
        )

        # =====================
        # ENTRENAMIENTO
        # =====================

        if entrenamiento:

            if balon_rect.colliderect(barra):

                mensaje = "ATAJADO"

                entrenamiento = False

                pygame.display.update()
                pygame.time.delay(700)

                reset_balon()

            elif balon_y <= ARCO_Y:

                centro_x = balon_x + tamano_balon // 2

                if ARCO_X1 <= centro_x <= ARCO_X2:

                    mensaje = "GOOOOL ⚽"
                    goles += 1

                else:

                    mensaje = "FALLASTE"

                entrenamiento = False

                pygame.display.update()
                pygame.time.delay(700)

                reset_balon()

        # =====================
        # MODO DIFÍCIL
        # =====================

        else:

            if balon_y <= ARCO_Y:

                centro_x = balon_x + tamano_balon // 2

                gol = False

                for espacio in espacios_abiertos:

                    if espacio.left <= centro_x <= espacio.right:

                        gol = True
                        break

                if gol:

                    mensaje = "GOOOOL ⚽"
                    goles += 1

                else:

                    mensaje = "FALLASTE"

                intentos += 1

                generar_espacios()

                pygame.display.update()
                pygame.time.delay(700)

                reset_balon()

    # =====================
    # DIBUJAR
    # =====================

    pantalla.blit(fondo, (0, 0))

    # =====================
    # BLOQUEOS DIFÍCILES
    # =====================

    if not entrenamiento:

        bloqueos = []

        x_actual = ARCO_X1

        espacios_ordenados = sorted(
            espacios_abiertos,
            key=lambda r: r.x
        )

        for espacio in espacios_ordenados:

            if espacio.x > x_actual:

                bloqueos.append(
                    pygame.Rect(
                        x_actual,
                        ARCO_Y,
                        espacio.x - x_actual,
                        ARCO_ALTO
                    )
                )

            x_actual = espacio.right

        if x_actual < ARCO_X2:

            bloqueos.append(
                pygame.Rect(
                    x_actual,
                    ARCO_Y,
                    ARCO_X2 - x_actual,
                    ARCO_ALTO
                )
            )

        # DIBUJAR BLOQUEOS
        for bloqueo in bloqueos:

            pygame.draw.rect(
                pantalla,
                (25, 25, 25),
                bloqueo
            )

    # =====================
    # TRAYECTORIA
    # =====================

    if len(trayectoria) > 1:

        pygame.draw.lines(
            pantalla,
            (255,255,255),
            False,
            trayectoria,
            3
        )

    # =====================
    # LÍNEA SOLO ENTRENAMIENTO
    # =====================

    if entrenamiento and not disparado:

        mouse_x, mouse_y = pygame.mouse.get_pos()

        pygame.draw.line(
            pantalla,
            (255,255,255),
            (
                balon_x + tamano_balon // 2,
                balon_y + tamano_balon // 2
            ),
            (mouse_x, mouse_y),
            3
        )

    # =====================
    # BARRA SOLO ENTRENAMIENTO
    # =====================

    if entrenamiento:

        pygame.draw.rect(
            pantalla,
            (255,0,0),
            barra
        )

    # =====================
    # BALÓN
    # =====================

    pantalla.blit(
        balon,
        (balon_x, balon_y)
    )

    # =====================
    # TEXTOS
    # =====================

    if entrenamiento:

        texto_modo = fuente.render(
            "ENTRENAMIENTO",
            True,
            (255,255,0)
        )

    else:

        texto_modo = fuente.render(
            f"Intento: {intentos + 1}/5",
            True,
            (255,255,255)
        )

    pantalla.blit(texto_modo, (20, 20))

    texto_goles = fuente.render(
        f"Goles: {goles}",
        True,
        (255,255,255)
    )

    pantalla.blit(texto_goles, (20, 70))

    texto_mensaje = fuente.render(
        mensaje,
        True,
        (255,255,0)
    )

    pantalla.blit(texto_mensaje, (20, 120))

    # =====================
    # FIN
    # =====================

    if intentos >= MAX_INTENTOS:

        texto_final = fuente.render(
            "FIN DEL JUEGO",
            True,
            (255,0,0)
        )

        pantalla.blit(texto_final, (430, 40))

    pygame.display.update()

pygame.quit()