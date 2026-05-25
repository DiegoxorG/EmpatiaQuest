"""
Sistema de eventos de historia y narrativa del juego EmpatiaQuest.
Cada evento tiene una escena completa, opciones con consecuencias, y condiciones
de aparición basadas en estadísticas o en decisiones previas.
"""

# ─── Eventos de historia ──────────────────────────────────────────────────────

def build_story_events():
    """Construye y retorna la lista completa de eventos de historia disponibles."""
    return [
        # ── DÍA 1 ─────────────────────────────────────────────────────────────
        {
            "id": "primer_dia",
            "title": "Con quien te sientas",
            "sensitive": False,
            "condition": None,
            "uses_razon": False,
            "scene": {
                "moment": "Primer dia de clases, manana",
                "place": "Salon de clases antes de iniciar la jornada",
                "atmosphere": [
                    "Estudiantes conversando en grupos",
                    "Ruido moderado de sillas y mochilas",
                    "Grupos ya formados desde el primer dia",
                ],
                "setup": (
                    "El protagonista entra tarde al salon. Solo quedan dos lugares: "
                    "uno junto a Sara, quien dibuja sola en su cuaderno; "
                    "otro junto a Diego y el grupo popular."
                ),
                "characters": {
                    "Sara": {
                        "state": ["Sola", "Dibujando en su cuaderno", "Evitando mirar alrededor"],
                        "npc_line": "Ella siempre anda sola...",
                    },
                    "Diego": {
                        "state": ["Hablando con varios companeros", "Riendo", "Haciendo senales para que te acerques"],
                        "npc_line": "Ey, aca hay puesto.",
                    },
                },
            },
            "options": [
                {
                    "label": "1) Sentarte con Sara",
                    "dF": 8, "dR": -2,
                    "thought": "A veces las personas solo necesitan saber que alguien quiso quedarse.",
                    "consequences": ["Sara se sorprende", "Algunos observan al protagonista"],
                    "dialogue": [{"speaker": "Sara", "line": "Gracias... pense que nadie iba a sentarse aqui."}],
                },
                {
                    "label": "2) Sentarte con Diego",
                    "dF": -5, "dR": 5,
                    "thought": "Fue mas facil encajar que preguntarme como se sentia ella.",
                    "consequences": ["El grupo acepta al protagonista", "Sara baja la mirada"],
                    "dialogue": [{"speaker": "Diego", "line": "Sabia que no te ibas a quedar alla solo."}],
                },
                {
                    "label": "3) Intentar unirlos",
                    "dF": 10, "dR": 3,
                    "thought": "Nadie deberia quedarse aparte el primer dia.",
                    "consequences": ["Hay un momento incomodo", "Pero los dos terminan conversando"],
                    "dialogue": [{"speaker": "Sara", "line": "No... no es necesario."}],
                },
                {
                    "label": "4) Sentarte aparte",
                    "dF": -5, "dR": 0,
                    "thought": "Quedarme al margen tambien fue una eleccion.",
                    "consequences": ["Todos se quedan en sus grupos", "El protagonista queda solo"],
                    "dialogue": [],
                },
            ],
        },

        # ── DÍA 1 (continuación) ───────────────────────────────────────────────
        {
            "id": "voces_pasillo",
            "title": "Voces en el pasillo",
            "sensitive": False,
            "condition": None,
            "uses_razon": False,
            "scene": {
                "moment": "Entre clases, hora del descanso",
                "place": "Pasillo principal frente a los casilleros",
                "atmosphere": [
                    "Pasillo lleno de estudiantes",
                    "Voces altas que se escuchan desde lejos",
                    "Algunos se detienen a mirar",
                ],
                "setup": (
                    "Un grupo de chicos rodea a un estudiante mas pequeno y lo insulta. "
                    "Los demas fingen no ver. Nadie interviene."
                ),
                "characters": {
                    "Agresor": {
                        "state": ["Riendo con sus amigos", "Bloqueando el paso del otro"],
                        "npc_line": "Que, te vas a quejar ahora?",
                    },
                    "Victima": {
                        "state": ["Cabizbajo", "Intentando ignorarlos", "Con los hombros caidos"],
                        "npc_line": "",
                    },
                },
            },
            "options": [
                {"label": "1) Defender calmadamente", "dF": 10, "dR": 5,
                 "thought": "Hablar con calma tambien puede detener el dano."},
                {"label": "2) Defender agresivamente", "dF": 5, "dR": -5,
                 "thought": "Quise ayudar, pero termine subiendo la violencia."},
                {"label": "3) Buscar un docente", "dF": 8, "dR": 3,
                 "thought": "No tenia que resolverlo solo."},
                {"label": "4) Ignorar y seguir", "dF": -10, "dR": 0,
                 "thought": "Escuche todo y segui caminando."},
                {"label": "5) Reirte con ellos", "dF": -15, "dR": 5,
                 "thought": "Me rei para encajar y lo empeore."},
            ],
        },

        # ── DÍA 2 ─────────────────────────────────────────────────────────────
        {
            "id": "reenviado",
            "title": "El mensaje reenviado",
            "sensitive": True,
            "condition": None,
            "uses_razon": False,
            "scene": {
                "moment": "Noche, en casa",
                "place": "Cuarto del protagonista, pantalla del celular",
                "atmosphere": [
                    "Silencio del cuarto",
                    "Luz azul de la pantalla",
                    "Notificaciones que no paran de llegar",
                ],
                "setup": (
                    "Llega un mensaje al grupo de clase. Alguien reenviO una foto "
                    "intima de una companera. El hilo ya tiene 30 mensajes de burlas. "
                    "El protagonista es el siguiente en verlo."
                ),
                "characters": {
                    "Grupo de clase": {
                        "state": ["Mensajes de burla", "Emojis de risa", "Nadie defendiendo"],
                        "npc_line": "jajaja ya la vieron??",
                    },
                },
            },
            "options": [
                {"label": "1) Defender publicamente en el grupo", "dF": 10, "dR": 5,
                 "thought": "Defender empieza por no participar del dano."},
                {"label": "2) Defender con insultos", "dF": 5, "dR": -5,
                 "thought": "Termine sumando caos al caos."},
                {"label": "3) Reportar el grupo al colegio", "dF": 8, "dR": 3,
                 "thought": "Alguien tenia que intervenir de verdad."},
                {"label": "4) Cerrar el chat e ignorar", "dF": -8, "dR": 0,
                 "thought": "Cerrar el chat no borra el dolor."},
                {"label": "5) Reenviar el contenido", "dF": -15, "dR": 5,
                 "thought": "Solo un reenvio tambien hace dano."},
            ],
        },

        # ── DÍA 2 (continuación) ───────────────────────────────────────────────
        {
            "id": "detras_agresor",
            "title": "Detras del agresor",
            "sensitive": False,
            # Condición: reputación >= 50 (la gente te habla porque confía en ti)
            "condition": "r_50_plus",
            "uses_razon": True,  # Integra prologo_razon: el agresor también fue víctima
            "scene": {
                "moment": "Tarde, recreo",
                "place": "Cancha trasera del colegio",
                "atmosphere": [
                    "Pocos estudiantes alrededor",
                    "El agresor sentado solo en una banca",
                    "Actitud defensiva pero cansada",
                ],
                "setup": (
                    "El mismo que agredía a otros está solo. Alguien te cuenta que "
                    "él también fue víctima de bullying por su {razon} cuando era pequeño. "
                    "Entender no es justificar, pero hay una oportunidad aquí."
                ),
                "characters": {
                    "Agresor": {
                        "state": ["Solo en la banca", "Cabizbajo", "Sin su grupo usual"],
                        "npc_line": "Que quieres.",
                    },
                },
            },
            "options": [
                {"label": "1) Hablar con el en privado", "dF": 12, "dR": 3,
                 "thought": "Entender no es justificar."},
                {"label": "2) Confrontarlo publicamente", "dF": 5, "dR": -3,
                 "thought": "Humillar no corrige."},
                {"label": "3) Ignorarlo", "dF": -8, "dR": 0,
                 "thought": "Decidi no mirar lo que habia detras."},
                {"label": "4) Exponer su situacion al grupo", "dF": -12, "dR": 5,
                 "thought": "Converti su dolor en espectaculo."},
            ],
        },

        # ── DÍA 3 ─────────────────────────────────────────────────────────────
        {
            "id": "encajar",
            "title": "El precio de encajar",
            "sensitive": False,
            "condition": None,
            "uses_razon": False,
            "scene": {
                "moment": "Recreo del mediodia",
                "place": "Cafeteria, mesa del grupo popular",
                "atmosphere": [
                    "Risas fuertes",
                    "Una silla vacia que te ofrecen",
                    "Alguien ausente — es el blanco de la broma",
                ],
                "setup": (
                    "Diego y su grupo te invitan a sentarte con ellos. "
                    "Pero la condición es participar en una broma humillante "
                    "contra un companero que no está presente."
                ),
                "characters": {
                    "Diego": {
                        "state": ["Sonriendo", "Esperando tu respuesta", "Con el grupo mirando"],
                        "npc_line": "Vamos, es solo una broma. Sientate con nosotros.",
                    },
                },
            },
            "options": [
                {"label": "1) Participar en la broma", "dF": -12, "dR": 10,
                 "thought": "Encajar no valia ese costo."},
                {"label": "2) Negarte a la broma", "dF": 5, "dR": -5,
                 "thought": "Decir no tambien exige valentia."},
                {"label": "3) Intentar detenerlos", "dF": 12, "dR": 5,
                 "thought": "No queria quedarme callado."},
                {"label": "4) Irte sin decir nada", "dF": 0, "dR": -3,
                 "thought": "No participe, pero tampoco ayude."},
            ],
        },

        # ── DÍA 3 (continuación) ──────────────────────────────────────────────
        {
            "id": "broma",
            "title": "La broma que duele",
            "sensitive": False,
            "condition": None,
            "uses_razon": True,  # Integra prologo_razon: la broma es sobre algo similar
            "scene": {
                "moment": "Clase de educacion fisica",
                "place": "Cancha principal, formados en equipos",
                "atmosphere": [
                    "Calor de mediodia",
                    "Risas de un grupo al otro lado",
                    "Un estudiante con la cabeza gacha",
                ],
                "setup": (
                    "Carlos hace una imitacion burlona de un companero "
                    "por su {razon}. Todos rien. El companero se queda quieto, "
                    "mirando el suelo. Sara te mira esperando que hagas algo."
                ),
                "characters": {
                    "Carlos": {
                        "state": ["Haciendo la imitacion", "Buscando aprobacion del grupo"],
                        "npc_line": "Es solo una broma, relax.",
                    },
                    "Sara": {
                        "state": ["Incómoda", "Mirando al protagonista"],
                        "npc_line": "",
                    },
                },
            },
            "options": [
                {"label": "1) Defender con calma", "dF": 12, "dR": 5,
                 "thought": "Humillar nunca es broma."},
                {"label": "2) Defender agresivamente", "dF": 5, "dR": -5,
                 "thought": "Frene una cosa, empeore otra."},
                {"label": "3) Pedirle a Diego que actue", "dF": 10, "dR": 3,
                 "thought": "Una voz puede activar otras."},
                {"label": "4) Ignorar", "dF": -12, "dR": 0,
                 "thought": "Escuche risas y segui de largo."},
                {"label": "5) Reirte para encajar", "dF": -18, "dR": 8,
                 "thought": "Encaje y alguien salio herida."},
            ],
        },

        # ── DÍA 4 ─────────────────────────────────────────────────────────────
        {
            "id": "rumores",
            "title": "Los rumores",
            "sensitive": True,
            # Condición: ya tomaste una decisión previa de ignorar (dF <= -8)
            "condition": "prev_ignored",
            "uses_razon": False,
            "scene": {
                "moment": "Pasillo entre clases",
                "place": "Frente a los banos, zona con poca supervision",
                "atmosphere": [
                    "Cuchicheos",
                    "Miradas de costado",
                    "Una companera caminando sola, acelerado el paso",
                ],
                "setup": (
                    "Un grupo comparte rumores sobre la vida personal de una companera. "
                    "La informacion era privada. Alguien la filtro. "
                    "Ella lo sabe y esta tratando de evitar a todos."
                ),
                "characters": {
                    "Grupo": {
                        "state": ["Hablando en voz baja", "Compartiendo el rumor en el celular"],
                        "npc_line": "Oiste lo de Laura?",
                    },
                    "Laura": {
                        "state": ["Caminando rapido", "Evitando mirar", "Ojos rojos"],
                        "npc_line": "",
                    },
                },
            },
            "options": [
                {"label": "1) Escucharla y acompanarla", "dF": 12, "dR": 4,
                 "thought": "No necesitaba detalles para respetarla."},
                {"label": "2) Defender su privacidad", "dF": 10, "dR": 5,
                 "thought": "La vida de alguien no es espectaculo."},
                {"label": "3) Difundir el rumor", "dF": -18, "dR": 6,
                 "thought": "Comentar tambien destruye."},
                {"label": "4) Juzgarla", "dF": -20, "dR": -5,
                 "thought": "Fue facil juzgar desde afuera."},
            ],
        },

        # ── DÍA 4 (continuación) ──────────────────────────────────────────────
        {
            "id": "no_era_flojera",
            "title": "No era flojera",
            "sensitive": True,
            "condition": None,
            "uses_razon": False,
            "scene": {
                "moment": "Despues de clase, pasillo desierto",
                "place": "Pasillo lateral, cercano a las escaleras",
                "atmosphere": [
                    "El pasillo casi vacio",
                    "Luz de tarde que entra por las ventanas",
                    "Un companero sentado en el suelo contra la pared",
                ],
                "setup": (
                    "Lucas, que lleva semanas faltando y sacando malas notas, "
                    "esta sentado en el suelo del pasillo. Te mira un momento "
                    "y luego vuelve a mirar el piso. No parece cansancio — "
                    "parece algo mucho mas pesado."
                ),
                "characters": {
                    "Lucas": {
                        "state": ["Sentado en el suelo", "Sin mochila en el hombro", "Ojos apagados"],
                        "npc_line": "No es nada. Vete.",
                    },
                },
            },
            "options": [
                {"label": "1) Sentarte y escucharle", "dF": 15, "dR": 5,
                 "thought": "Escuchar puede cambiarlo todo."},
                {"label": "2) Buscar ayuda de un adulto de confianza", "dF": 12, "dR": 5,
                 "thought": "Habia senales muy fuertes."},
                {"label": "3) Decirle que se esfuerce mas", "dF": -20, "dR": -5,
                 "thought": "Reduci su dolor a algo pasajero."},
                {"label": "4) Seguir tu camino", "dF": -18, "dR": 0,
                 "thought": "Lo vi apagarse y no actue."},
            ],
        },

        # ── DÍA 5 ─────────────────────────────────────────────────────────────
        {
            "id": "racismo",
            "title": "No es un chiste",
            "sensitive": True,
            "condition": None,
            "uses_razon": False,
            "scene": {
                "moment": "Hora del almuerzo en la cafeteria",
                "place": "Cafeteria, mesa larga con varios grupos mezclados",
                "atmosphere": [
                    "Ruido de platos y conversaciones",
                    "Un grupo riendose fuerte",
                    "Un estudiante con expresion tensa que intenta ignorar",
                ],
                "setup": (
                    "Un grupo hace comentarios racistas disfrazados de chistes "
                    "sobre Mateo, un companero afrodescendiente. "
                    "El dice que no le molesta, pero su expresion dice otra cosa."
                ),
                "characters": {
                    "Mateo": {
                        "state": ["Sonrisa forzada", "Mirando el plato", "Hombros tensos"],
                        "npc_line": "Es broma. No me afecta.",
                    },
                    "Grupo": {
                        "state": ["Riendo", "Haciendo mas comentarios"],
                        "npc_line": "Oye no te pongas asi, es solo humor.",
                    },
                },
            },
            "options": [
                {"label": "1) Defender directamente", "dF": 12, "dR": 4,
                 "thought": "No era humor: era dano repetido."},
                {"label": "2) Educar calmadamente al grupo", "dF": 15, "dR": 5,
                 "thought": "Normalizar el racismo lo expande."},
                {"label": "3) Reirte con el grupo", "dF": -18, "dR": 6,
                 "thought": "Me rei sabiendo que dolia."},
                {"label": "4) Decir que es solo humor", "dF": -15, "dR": -3,
                 "thought": "Minimice algo grave."},
            ],
        },

        # ── DÍA 5 (continuación) ──────────────────────────────────────────────
        {
            "id": "xenofobia",
            "title": "No eres de aqui",
            "sensitive": True,
            "condition": None,
            "uses_razon": False,
            "scene": {
                "moment": "Educacion fisica, formacion de equipos",
                "place": "Cancha principal",
                "atmosphere": [
                    "Equipos eligiendo jugadores",
                    "Un estudiante parado al final sin que nadie lo llame",
                    "Comentarios en voz baja",
                ],
                "setup": (
                    "Samuel llegó hace dos meses de Venezuela. "
                    "Siempre queda de ultimo al elegir equipos. "
                    "Hoy escuchas comentarios: 'Por que vienen a quitarnos los puestos'. "
                    "El lo escucha todo."
                ),
                "characters": {
                    "Samuel": {
                        "state": ["Parado solo", "Mirando hacia otro lado", "Sin quejarse"],
                        "npc_line": "",
                    },
                    "Estudiante": {
                        "state": ["Hablando con otro", "Sin bajar la voz"],
                        "npc_line": "Por que no se quedo en su pais.",
                    },
                },
            },
            "options": [
                {"label": "1) Integrarlo al equipo activamente", "dF": 15, "dR": 4,
                 "thought": "Nadie deberia sentirse menos por venir de otro lugar."},
                {"label": "2) Defenderlo publicamente", "dF": 12, "dR": 5,
                 "thought": "El respeto no tiene fronteras."},
                {"label": "3) Ignorar la situacion", "dF": -12, "dR": 0,
                 "thought": "Lo escuche y mire a otro lado."},
                {"label": "4) Participar en los comentarios", "dF": -20, "dR": 7,
                 "thought": "Encajar asi deshumaniza a otros."},
            ],
        },

        # ── Eventos condicionales ──────────────────────────────────────────────
        {
            "id": "persona_llorando",
            "title": "Alguien llorando",
            "sensitive": False,
            "condition": "f_40_49",      # Solo si felicidad está entre 40 y 49
            "uses_razon": False,
            "scene": {
                "moment": "Pasillo, entrada al bano",
                "place": "Pasillo lateral, zona sin camaras",
                "atmosphere": [
                    "Pasillo vacio",
                    "Sonido de llanto que sale por la puerta entreabierta",
                    "Nadie mas alrededor",
                ],
                "setup": (
                    "Al pasar por el bano escuchas llanto. "
                    "Asomas la cabeza: es una companera sentada en el suelo. "
                    "Al verte, intenta disimular."
                ),
                "characters": {
                    "Companera": {
                        "state": ["Sentada en el suelo", "Ojos rojos", "Intentando sonreir"],
                        "npc_line": "Estoy bien. De verdad.",
                    },
                },
            },
            "options": [
                {"label": "1) Sentarte a su lado sin preguntar", "dF": 10, "dR": 3,
                 "thought": "Acompanamiento antes que respuestas."},
                {"label": "2) Preguntar que ocurre", "dF": 8, "dR": 2,
                 "thought": "Preguntar tambien sostiene."},
                {"label": "3) Respetar su espacio e irte", "dF": -10, "dR": 0,
                 "thought": "Escuche llorar y segui."},
                {"label": "4) Decirle que no es para tanto", "dF": -15, "dR": -2,
                 "thought": "Minimizar tambien hiere."},
            ],
        },

        {
            "id": "pelea_pasillos",
            "title": "Pelea en los pasillos",
            "sensitive": False,
            "condition": "f_25_39",       # Solo si felicidad está entre 25 y 39
            "uses_razon": False,
            "scene": {
                "moment": "Cambio de clase, pasillo lleno",
                "place": "Pasillo segundo piso, frente a los casilleros",
                "atmosphere": [
                    "Circulo de estudiantes mirando",
                    "Gritos y empujones",
                    "Nadie interviniendo, varios grabando con el celular",
                ],
                "setup": (
                    "Una pelea entre dos estudiantes escala rapidamente. "
                    "El circulo crece. Algunos graban. "
                    "No hay docentes a la vista."
                ),
                "characters": {
                    "Estudiante A": {
                        "state": ["Empujando", "Gritando"],
                        "npc_line": "",
                    },
                    "Estudiante B": {
                        "state": ["Respondiendo a los empujones"],
                        "npc_line": "",
                    },
                },
            },
            "options": [
                {"label": "1) Interponerte fisicamente para separar", "dF": 10, "dR": 5,
                 "thought": "Si nadie intervenia, empeoraba."},
                {"label": "2) Buscar un docente rapidamente", "dF": 8, "dR": 3,
                 "thought": "Pedi apoyo en lugar de grabar."},
                {"label": "3) Grabar con el celular", "dF": -10, "dR": 5,
                 "thought": "Lo volvi espectaculo."},
                {"label": "4) Esperar a que pase", "dF": -12, "dR": 0,
                 "thought": "Espere que otro actuara."},
            ],
        },

        # ── Evento de reputación alta ─────────────────────────────────────────
        {
            "id": "lider_empatia",
            "title": "Te piden consejo",
            "sensitive": False,
            "condition": "r_60_plus",    # Solo si reputacion >= 60
            "uses_razon": False,
            "scene": {
                "moment": "Biblioteca, hora libre",
                "place": "Mesa del fondo de la biblioteca",
                "atmosphere": [
                    "Silencio de biblioteca",
                    "Una companera que se acerca con cara de preocupacion",
                    "Nadie mas cerca",
                ],
                "setup": (
                    "Andres, un companero que antes miraba sin actuar, "
                    "te busca. Vio como manejaste situaciones difíciles. "
                    "Quiere saber como hablar con alguien que esta siendo "
                    "acosado sin que la situacion empeore."
                ),
                "characters": {
                    "Andres": {
                        "state": ["Nervioso", "Buscando palabras", "Queriendo hacer lo correcto"],
                        "npc_line": "Tu como harias para ayudarlo sin que se ponga peor?",
                    },
                },
            },
            "options": [
                {"label": "1) Darle consejos concretos y practicos", "dF": 12, "dR": 6,
                 "thought": "Ensenar a otros a ayudar multiplica el impacto."},
                {"label": "2) Ofrecerte a ir con el juntos", "dF": 15, "dR": 5,
                 "thought": "Dos personas siempre generan mas seguridad."},
                {"label": "3) Decirle que es problema de otro", "dF": -10, "dR": -5,
                 "thought": "Podia haberlo guiado y no lo hice."},
                {"label": "4) Decirle que avise a un adulto", "dF": 8, "dR": 3,
                 "thought": "Los adultos tienen recursos que nosotros no."},
            ],
        },

        # ── Evento de reputación baja ─────────────────────────────────────────
        {
            "id": "reputacion_baja",
            "title": "Lo que dicen de ti",
            "sensitive": False,
            "condition": "r_below_30",   # Solo si reputacion < 30
            "uses_razon": True,           # Integra prologo_razon: ahora tú eres señalado
            "scene": {
                "moment": "Manana, entrada al colegio",
                "place": "Entrada principal, escaleras",
                "atmosphere": [
                    "Grupos que cuchichean",
                    "Miradas que se desvian cuando pasas",
                    "Sensacion de que algo cambio",
                ],
                "setup": (
                    "Alguien empezo a difundir rumores sobre ti. "
                    "Dicen que te burlas de los demas, que no eres de fiar. "
                    "Ahora sabes como se siente estar en el otro lado. "
                    "Antes te senalaban por tu {razon}. Hoy te senalan por tus acciones."
                ),
                "characters": {
                    "Diego": {
                        "state": ["Alejado", "Evitando el contacto visual"],
                        "npc_line": "Ey... tengo que irme.",
                    },
                },
            },
            "options": [
                {"label": "1) Hablar con los involucrados directamente", "dF": 10, "dR": 8,
                 "thought": "La unica salida es la conversacion honesta."},
                {"label": "2) Ignorar los rumores y actuar bien", "dF": 8, "dR": 5,
                 "thought": "Las acciones hablan mas que las palabras."},
                {"label": "3) Contraatacar con tus propios rumores", "dF": -15, "dR": -10,
                 "thought": "Ensuciar a otros no te limpia a ti."},
                {"label": "4) Aislarte completamente", "dF": -8, "dR": -5,
                 "thought": "El aislamiento no resuelve nada."},
            ],
        },
    ]


# ─── Condiciones de eventos ───────────────────────────────────────────────────

def condition_ok(condition, felicidad, reputacion=50, decision_history=None):
    """Verifica si una condición de evento es válida dado el estado del juego."""
    if condition is None:
        return True
    if condition == "f_40_49":
        return 40 <= felicidad < 50
    if condition == "f_25_39":
        return 25 <= felicidad < 40
    if condition == "r_50_plus":
        return reputacion >= 50
    if condition == "r_60_plus":
        return reputacion >= 60
    if condition == "r_below_30":
        return reputacion < 30
    if condition == "prev_ignored":
        if not decision_history:
            return False  # Sin historial de decisiones negativas, no mostrar aún
        return any(d.get("dF", 0) <= -8 for d in decision_history)
    return False


def pick_next_event(event_pool, felicidad, reputacion=50, decision_history=None):
    """Selecciona el siguiente evento de la piscina respetando condiciones."""
    if not event_pool:
        return None
    for i, event in enumerate(event_pool):
        if condition_ok(event["condition"], felicidad, reputacion, decision_history):
            return event_pool.pop(i)
    # Si ninguno cumple condición, tomar el primero disponible
    return event_pool.pop(0) if event_pool else None


# ─── Integración de prologo_razon ─────────────────────────────────────────────

def format_event_text(text, prologo_razon="tu forma de ser"):
    """Reemplaza {razon} en textos del evento con la razón elegida en el prólogo."""
    if not isinstance(text, str):
        return text
    return text.replace("{razon}", str(prologo_razon))


# ─── Opciones del prólogo ────────────────────────────────────────────────────

PROLOGO_RAZON_CHOICES = [
    "apariencia fisica",
    "forma de hablar",
    "timidez",
    "gusto personal",
    "dificultad para socializar",
]
