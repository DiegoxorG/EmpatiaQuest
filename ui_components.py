"""
Componentes de interfaz de usuario reutilizables.
"""

import pygame
from config import CARD, CARD_HOVER, CARD_BORDER, TEXT_MAIN


class Button:
    """Botón interactivo con estilo pixel."""
    
    def __init__(self, rect, text, action):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action

    def draw(self, surface, ui, hover=False):
        color = CARD_HOVER if hover else CARD
        shadow = self.rect.move(4, 4)
        pygame.draw.rect(surface, (12, 11, 23), shadow)
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, CARD_BORDER, self.rect, width=4)

        ui.draw_pixel_text(self.text, self.rect.centerx, self.rect.centery, "button", TEXT_MAIN, True)

    def contains(self, pos):
        return self.rect.collidepoint(pos)
