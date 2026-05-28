from dataclasses import dataclass


@dataclass(frozen=True)
class EmotionalChoice:
    key: str
    label: str
    df: int
    dr: int


@dataclass(frozen=True)
class EmotionalEvent:
    event_id: str
    done_attr: str
    decision_attr: str
    choice_context: str
    next_target: str
    mission: str
    choices: tuple[EmotionalChoice, ...]

    def choice(self, key: str, fallback: str | None = None) -> EmotionalChoice:
        selected = key or fallback or self.choices[0].key
        for choice in self.choices:
            if choice.key == selected:
                return choice
        return self.choices[0]


DAY4_AZOTEA = EmotionalEvent(
    event_id="dia4_broma",
    done_attr="escena_dia4_azotea_completada",
    decision_attr="decision_dia4_azotea",
    choice_context="azotea",
    next_target="biblioteca",
    mission="Ir a la biblioteca",
    choices=(
        EmotionalChoice("defender", "Defender calmadamente", +4, +2),
        EmotionalChoice("diego", "Pedirle ayuda a Diego", +3, +1),
        EmotionalChoice("ignorar", "Ignorar", -5, 0),
        EmotionalChoice("reirse", "Reirse para encajar", -8, +3),
    ),
)

DAY4_BIBLIOTECA = EmotionalEvent(
    event_id="dia4_biblioteca",
    done_attr="escena_dia4_biblioteca_completada",
    decision_attr="decision_dia4_biblioteca",
    choice_context="biblioteca",
    next_target="rumores",
    mission='Ir al evento: "Rumores"',
    choices=(
        EmotionalChoice("sara", "Hacer grupo con Sara", +3, -1),
        EmotionalChoice("diego", "Ir con Diego", -3, +2),
        EmotionalChoice("incluir", "Convencer al grupo de incluirla", +4, +1),
    ),
)

DAY4_RUMORES = EmotionalEvent(
    event_id="dia4_rumores",
    done_attr="escena_dia4_rumores_completada",
    decision_attr="decision_dia4_rumores",
    choice_context="rumores",
    next_target="cama",
    mission="Ir a dormir",
    choices=(
        EmotionalChoice("acompanar", "Escucharla y acompanarla", +4, +1),
        EmotionalChoice("defender", "Defenderla publicamente", +3, +2),
        EmotionalChoice("compartir", "Compartir rumores", -8, +2),
        EmotionalChoice("juzgar", "Juzgarla", -10, -2),
    ),
)


DAY4_EVENTS = {
    DAY4_AZOTEA.choice_context: DAY4_AZOTEA,
    DAY4_BIBLIOTECA.choice_context: DAY4_BIBLIOTECA,
    DAY4_RUMORES.choice_context: DAY4_RUMORES,
}
