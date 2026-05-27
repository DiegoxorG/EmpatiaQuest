import pygame
import random
import os

# =========================
# INICIALIZAR
# =========================

pygame.init()

ANCHO = 1000
ALTO = 600

pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Atrapa Emociones")

clock = pygame.time.Clock()

# =========================
# COLORES
# =========================

BLANCO = (255, 255, 255)

# =========================
# RUTA DE IMÁGENES
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ruta = os.path.join(BASE_DIR, "imagenes_atrapa")

# =========================
# CARGAR IMÁGENES
# =========================

# PERSONAJE
img_frente = pygame.image.load(
    os.path.join(ruta, "frente.png")
).convert_alpha()

img_izquierda = pygame.image.load(
    os.path.join(ruta, "izquierda.png")
).convert_alpha()

img_derecha = pygame.image.load(
    os.path.join(ruta, "derecha.png")
).convert_alpha()

# FONDO
fondo = pygame.image.load(
    os.path.join(ruta, "atras.jpeg")
).convert()

# IMÁGENES BUENAS
imagenes_buenas = [
    pygame.image.load(os.path.join(ruta, "abrazo.png")).convert_alpha(),
    pygame.image.load(os.path.join(ruta, "empatia.png")).convert_alpha(),
    pygame.image.load(os.path.join(ruta, "feliz.png")).convert_alpha(),
    pygame.image.load(os.path.join(ruta, "sol.png")).convert_alpha(),
    pygame.image.load(os.path.join(ruta, "solidaridad.png")).convert_alpha(),
    pygame.image.load(os.path.join(ruta, "corazon.png")).convert_alpha()
]

# IMÁGENES MALAS
imagenes_malas = [
    pygame.image.load(os.path.join(ruta, "burbujainsultos.png")).convert_alpha(),
    pygame.image.load(os.path.join(ruta, "llorar.png")).convert_alpha(),
    pygame.image.load(os.path.join(ruta, "notainsultos.png")).convert_alpha(),
    pygame.image.load(os.path.join(ruta, "ira.png")).convert_alpha(),
    pygame.image.load(os.path.join(ruta, "pelea.png")).convert_alpha()
]

# =========================
# ESCALAR PERSONAJE
# =========================

TAMANO_PERSONAJE = (170, 170)

img_frente = pygame.transform.scale(img_frente, TAMANO_PERSONAJE)
img_izquierda = pygame.transform.scale(img_izquierda, TAMANO_PERSONAJE)
img_derecha = pygame.transform.scale(img_derecha, TAMANO_PERSONAJE)

# =========================
# ESCALAR FONDO
# =========================

fondo = pygame.transform.scale(fondo, (ANCHO, ALTO))

# =========================
# ESCALAR OBJETOS
# =========================

ALTURA_OBJETO = 110

for i in range(len(imagenes_buenas)):

    imagen = imagenes_buenas[i]

    ancho_original = imagen.get_width()
    alto_original = imagen.get_height()

    proporcion = ALTURA_OBJETO / alto_original

    nuevo_ancho = int(ancho_original * proporcion)

    imagenes_buenas[i] = pygame.transform.scale(
        imagen,
        (nuevo_ancho, ALTURA_OBJETO)
    )

for i in range(len(imagenes_malas)):

    imagen = imagenes_malas[i]

    ancho_original = imagen.get_width()
    alto_original = imagen.get_height()

    proporcion = ALTURA_OBJETO / alto_original

    nuevo_ancho = int(ancho_original * proporcion)

    imagenes_malas[i] = pygame.transform.scale(
        imagen,
        (nuevo_ancho, ALTURA_OBJETO)
    )

# =========================
# JUGADOR
# =========================

jugador_x = ANCHO // 2
jugador_y = ALTO - 200

velocidad_jugador = 8

imagen_actual = img_frente

jugador_rect = pygame.Rect(
    jugador_x,
    jugador_y,
    TAMANO_PERSONAJE[0],
    TAMANO_PERSONAJE[1]
)

# =========================
# OBJETOS
# =========================

objetos = []

# MÁS LENTOS
velocidad_objetos = 3

def crear_objeto():

    tipo = random.choice(["bueno", "malo"])

    if tipo == "bueno":
        imagen = random.choice(imagenes_buenas)
    else:
        imagen = random.choice(imagenes_malas)

    ancho_objeto = imagen.get_width()

    x = random.randint(0, ANCHO - ancho_objeto)

    y = -120

    rect = imagen.get_rect(topleft=(x, y))

    objetos.append({
        "imagen": imagen,
        "rect": rect,
        "tipo": tipo
    })

# =========================
# PUNTAJE
# =========================

puntos = 0

fuente = pygame.font.SysFont("Arial", 42, bold=True)

# =========================
# CONTROL DE SPAWN
# =========================

contador_spawn = 0

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

    # =====================
    # MOVIMIENTO
    # =====================

    teclas = pygame.key.get_pressed()

    moviendo = False

    # IZQUIERDA
    if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:

        jugador_x -= velocidad_jugador

        imagen_actual = img_izquierda

        moviendo = True

    # DERECHA
    if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:

        jugador_x += velocidad_jugador

        imagen_actual = img_derecha

        moviendo = True

    # QUIETO
    if not moviendo:

        imagen_actual = img_frente

    # =====================
    # LÍMITES
    # =====================

    if jugador_x < 0:
        jugador_x = 0

    if jugador_x > ANCHO - TAMANO_PERSONAJE[0]:
        jugador_x = ANCHO - TAMANO_PERSONAJE[0]

    # ACTUALIZAR RECT
    jugador_rect.x = jugador_x
    jugador_rect.y = jugador_y

    # =====================
    # CREAR OBJETOS
    # =====================

    contador_spawn += 1

    if contador_spawn >= 40:

        crear_objeto()

        contador_spawn = 0

    # =====================
    # MOVER OBJETOS
    # =====================

    for objeto in objetos[:]:

        objeto["rect"].y += velocidad_objetos

        # COLISIÓN
        # HITBOX MÁS PEQUEÑA DEL JUGADOR
        hitbox_jugador = jugador_rect.inflate(-60, -40)

# HITBOX MÁS PEQUEÑA DEL OBJETO
        hitbox_objeto = objeto["rect"].inflate(-30, -30)

# COLISIÓN
        if hitbox_jugador.colliderect(hitbox_objeto):

            if objeto["tipo"] == "bueno":
                puntos += 1
            else:
                puntos -= 1

            objetos.remove(objeto)

        # ELIMINAR SI SALE
        elif objeto["rect"].y > ALTO:

            objetos.remove(objeto)

    # =====================
    # DIBUJAR
    # =====================

    # FONDO
    pantalla.blit(fondo, (0, 0))

    # OBJETOS
    for objeto in objetos:

        pantalla.blit(
            objeto["imagen"],
            objeto["rect"]
        )

    # PERSONAJE
    pantalla.blit(
        imagen_actual,
        (jugador_x, jugador_y)
    )

    # TEXTO PUNTOS
    texto_puntos = fuente.render(
        f"Puntos: {puntos}",
        True,
        BLANCO
    )

    pantalla.blit(texto_puntos, (20, 20))

    # ACTUALIZAR PANTALLA
    pygame.display.update()

# =========================
# CERRAR
# =========================

pygame.quit()