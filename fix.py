with open('renderer.py', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total líneas: {len(lines)}")
print(f"Línea 841: {repr(lines[841])}")
print(f"Línea 842: {repr(lines[842])}")
print(f"Línea 843: {repr(lines[843])}")