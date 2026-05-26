"""
Sistema de eventos de historia y narrativa del juego.
"""


def build_story_events():
    """Construye lista de eventos de historia disponibles."""
    return [
        {
            "id": "primer_dia",
            "title": "Dia/Mision: con quien te sientas",
            "sensitive": False,
            "condition": None,
            "scene": {
                "moment": "Primer dia de clases",
                "place": "Salon de clases antes de iniciar la jornada",
                "atmosphere": [
                    "Estudiantes conversando",
                    "Grupos ya formados",
                    "Ruido moderado",
                ],
                "setup": "El protagonista entra tarde al salon. Solo quedan dos lugares: uno junto a Sara y otro junto a Diego y el grupo popular.",
                "characters": {
                    "Sara": {
                        "state": [
                            "Sola",
                            "Dibujando en su cuaderno",
                            "Evitando mirar alrededor",
                        ],
                        "npc_line": "Ella siempre anda sola.",
                    },
                    "Diego": {
                        "state": [
                            "Hablando con varios companeros",
                            "Riendo",
                            "Intentando verse relajado",
                        ],
                        "line": "Ey, aca hay puesto.",
                    },
                },
            },
            "options": [
                {
                    "label": "1) Sentarte con Sara",
                    "dF": 8,
                    "dR": -2,
                    "thought": "A veces las personas solo necesitan saber que alguien quiso quedarse.",
                    "consequences": [
                        "Sara se sorprende",
                        "Algunos estudiantes observan al protagonista",
                        "Diego parece confundido",
                    ],
                    "dialogue": [
                        {"speaker": "Sara", "line": "Gracias... pense que nadie iba a sentarse aqui."},
                    ],
                },
                {
                    "label": "2) Sentarte con Diego",
                    "dF": -5,
                    "dR": 5,
                    "thought": "Fue mas facil encajar que preguntarme como se sentia ella.",
                    "consequences": [
                        "El grupo acepta al protagonista rapidamente",
                        "Sara baja la mirada",
                    ],
                    "dialogue": [
                        {"speaker": "Diego", "line": "Sabia que no te ibas a quedar alla solo."},
                    ],
                },
            ],
        },
        {
            "id": "voces_pasillo",
            "title": "Voces en el pasillo",
            "sensitive": False,
            "condition": None,
            "options": [
                {"label": "1) Defender calmadamente", "dF": 10, "dR": 5, "thought": "Hablar con calma tambien puede detener dano."},
                {"label": "2) Defender agresivamente", "dF": 5, "dR": -5, "thought": "Quise ayudar, pero subi la violencia."},
                {"label": "3) Buscar docente", "dF": 8, "dR": 3, "thought": "No tenia que resolverlo solo."},
                {"label": "4) Ignorar", "dF": -10, "dR": 0, "thought": "Escuche todo y segui caminando."},
                {"label": "5) Reirte", "dF": -15, "dR": 5, "thought": "Me rei para encajar y lo empeore."},
            ],
        },
        {
            "id": "reenviado",
            "title": "Reenviado",
            "sensitive": True,
            "condition": None,
            "options": [
                {"label": "1) Defender correctamente", "dF": 10, "dR": 5, "thought": "Defender empieza por no participar del dano."},
                {"label": "2) Defender agresivamente", "dF": 5, "dR": -5, "thought": "Termine sumando caos."},
                {"label": "3) Reportar grupo", "dF": 8, "dR": 3, "thought": "Alguien tenia que intervenir."},
                {"label": "4) Ignorar", "dF": -8, "dR": 0, "thought": "Cerrar el chat no borra el dolor."},
                {"label": "5) Reenviar contenido", "dF": -15, "dR": 5, "thought": "Solo un reenvio tambien hace dano."},
            ],
        },
        {
            "id": "detras_agresor",
            "title": "Detras del agresor",
            "sensitive": False,
            "condition": None,
            "options": [
                {"label": "1) Hablar en privado", "dF": 12, "dR": 3, "thought": "Entender no es justificar."},
                {"label": "2) Confrontar publicamente", "dF": 5, "dR": -3, "thought": "Humillar no corrige."},
                {"label": "3) Ignorar", "dF": -8, "dR": 0, "thought": "Decidi no mirar lo que habia detras."},
                {"label": "4) Exponer su situacion", "dF": -12, "dR": 5, "thought": "Converti su dolor en espectaculo."},
            ],
        },
        {
            "id": "encajar",
            "title": "Encajar",
            "sensitive": False,
            "condition": None,
            "options": [
                {"label": "1) Participar", "dF": -12, "dR": 10, "thought": "Encajar no valia ese costo."},
                {"label": "2) Negarte", "dF": 5, "dR": -5, "thought": "Decir no tambien exige valentia."},
                {"label": "3) Intentar detenerlos", "dF": 12, "dR": 5, "thought": "No queria callar."},
                {"label": "4) Irte", "dF": 0, "dR": -3, "thought": "No participe, pero tampoco ayude."},
            ],
        },
        {
            "id": "broma",
            "title": "La broma",
            "sensitive": False,
            "condition": None,
            "options": [
                {"label": "1) Defender calmadamente", "dF": 12, "dR": 5, "thought": "Humillar nunca es broma."},
                {"label": "2) Defender agresivamente", "dF": 5, "dR": -5, "thought": "Frene una cosa, empeore otra."},
                {"label": "3) Pedirle a Diego que actue", "dF": 10, "dR": 3, "thought": "Una voz puede activar otras."},
                {"label": "4) Ignorar", "dF": -12, "dR": 0, "thought": "Escuche risas y segui de largo."},
                {"label": "5) Reirte para encajar", "dF": -18, "dR": 8, "thought": "Encaje y alguien salio herida."},
            ],
        },
        {
            "id": "rumores",
            "title": "Rumores",
            "sensitive": True,
            "condition": None,
            "options": [
                {"label": "1) Escuchar y acompanar", "dF": 12, "dR": 4, "thought": "No necesitaba detalles para respetarla."},
                {"label": "2) Defender respetuosamente", "dF": 10, "dR": 5, "thought": "La vida de alguien no es espectaculo."},
                {"label": "3) Difundir rumores", "dF": -18, "dR": 6, "thought": "Comentar tambien destruye."},
                {"label": "4) Juzgarla", "dF": -20, "dR": -5, "thought": "Fue facil juzgar desde afuera."},
            ],
        },
        {
            "id": "no_era_flojera",
            "title": "No era flojera",
            "sensitive": True,
            "condition": None,
            "options": [
                {"label": "1) Escuchar y acompanar", "dF": 15, "dR": 5, "thought": "Escuchar puede cambiarlo todo."},
                {"label": "2) Buscar ayuda responsable", "dF": 12, "dR": 5, "thought": "Habia senales muy fuertes."},
                {"label": "3) Minimizar", "dF": -20, "dR": -5, "thought": "Reduci su dolor a algo pasajero."},
                {"label": "4) Ignorar", "dF": -18, "dR": 0, "thought": "Lo vi apagarse y no actue."},
            ],
        },
        {
            "id": "racismo",
            "title": "No es un chiste",
            "sensitive": True,
            "condition": None,
            "options": [
                {"label": "1) Defender", "dF": 12, "dR": 4, "thought": "No era humor: era dano repetido."},
                {"label": "2) Educar calmadamente", "dF": 15, "dR": 5, "thought": "Normalizar racismo lo expande."},
                {"label": "3) Reirte", "dF": -18, "dR": 6, "thought": "Me rei sabiendo que dolia."},
                {"label": "4) Decir 'solo era humor'", "dF": -15, "dR": -3, "thought": "Minimice algo grave."},
            ],
        },
        {
            "id": "xenofobia",
            "title": "No eres de aqui",
            "sensitive": True,
            "condition": None,
            "options": [
                {"label": "1) Integrarlo al grupo", "dF": 15, "dR": 4, "thought": "Nadie deberia sentirse menos por venir de otro lugar."},
                {"label": "2) Defenderlo publicamente", "dF": 12, "dR": 5, "thought": "El respeto no tiene fronteras."},
                {"label": "3) Ignorar", "dF": -12, "dR": 0, "thought": "Lo escuche y mire a otro lado."},
                {"label": "4) Participar en comentarios", "dF": -20, "dR": 7, "thought": "Encajar asi deshumaniza a otros."},
            ],
        },
        {
            "id": "persona_llorando",
            "title": "Persona llorando",
            "sensitive": False,
            "condition": "f_40_49",
            "options": [
                {"label": "1) Consolar", "dF": 10, "dR": 3, "thought": "Acompanamiento antes que respuestas."},
                {"label": "2) Preguntar que ocurre", "dF": 8, "dR": 2, "thought": "Preguntar tambien sostiene."},
                {"label": "3) Ignorar", "dF": -10, "dR": 0, "thought": "Escuche llorar y segui."},
                {"label": "4) Decir 'no es para tanto'", "dF": -15, "dR": -2, "thought": "Minimizar tambien hiere."},
            ],
        },
        {
            "id": "pelea_pasillos",
            "title": "Pelea en pasillos",
            "sensitive": False,
            "condition": "f_25_39",
            "options": [
                {"label": "1) Separar pelea", "dF": 10, "dR": 5, "thought": "Si nadie intervenia, empeoraba."},
                {"label": "2) Buscar ayuda", "dF": 8, "dR": 3, "thought": "Pedi apoyo en lugar de grabar."},
                {"label": "3) Grabar", "dF": -10, "dR": 5, "thought": "Lo volvi espectaculo."},
                {"label": "4) Ignorar", "dF": -12, "dR": 0, "thought": "Espere que otro actuara."},
            ],
        },
    ]


def condition_ok(condition, felicidad):
    """Verifica si una condición de evento es válida."""
    if condition is None:
        return True
    if condition == "f_40_49":
        return 40 <= felicidad < 50
    if condition == "f_25_39":
        return 25 <= felicidad < 40
    return False


def pick_next_event(event_pool, felicidad):
    """Selecciona el siguiente evento de la piscina de eventos."""
    if not event_pool:
        return None
    for i, event in enumerate(event_pool):
        if condition_ok(event["condition"], felicidad):
            return event_pool.pop(i)
    return event_pool.pop(0) if event_pool else None


PROLOGO_RAZON_CHOICES = [
    "apariencia fisica",
    "forma de hablar",
    "timidez",
    "gusto personal",
    "dificultad social",
]
