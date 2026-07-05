# =====================================================
# 🔎 Buscar usos de 'auth.' en lugar de 'auth_bp.' en todo el proyecto
# =====================================================

import os
import re

# 📂 Carpeta donde está tu proyecto
project_dir = r"C:\Users\thier\Desktop\tubby_app\blueprints"  # <-- cambia esto

# 🔹 Lista para almacenar resultados
errores = []

# 🔹 Recorremos todos los archivos .py
for root, dirs, files in os.walk(project_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                # 🔍 Buscamos "auth." que no sea "auth_bp."
                matches = re.finditer(r"\bauth\.(?!bp)", content)
                for m in matches:
                    # Guardamos archivo y posición
                    errores.append((filepath, m.start()))

# 🖨️ Mostramos resultados
if errores:
    print("❌ Se encontraron usos de 'auth.' en lugar de 'auth_bp.' en:")
    for filepath, pos in errores:
        print(f"Archivo: {filepath}, posición: {pos}")
else:
    print("✅ No se encontraron errores de 'auth.'")
