from pathlib import Path
from PIL import Image
base = Path('Imagenes/Personajes/personaje_main')
names = ['walk_down.png','walk_left.png','walk_right.png','walk_up.png','idle_down.png','idle_left.png','idle_right.png','idle_up.png']
for name in names:
    with Image.open(base/name) as im:
        print(name, im.size, im.mode)
