# =====================================================
# 🔧 corregir_imports_auth.py
# =====================================================
# 🧙‍♂️ Script mágico para:
# 1️⃣ Corregir imports de auth_bp
# 2️⃣ Cambiar url_for("auth.*") → url_for("auth_bp.*")
# =====================================================

import os
import re

# 📂 Carpeta raíz de los blueprints
ROOT_DIR = "blueprints"

# 🔍 Patrón de imports mal escritos
pattern_import = re.compile(r"\bfrom\s+blueprints\.(auth_bp|auth_hp)\b")
pattern_login_required = re.compile(
    r"\bfrom\s+blueprints\.auth\.(login|super_admin)_required\b"
)
pattern_url_for = re.compile(r'url_for\(["\']auth\.(.*?)["\']\)')

# 👶 Recorremos todos los archivos .py
for subdir, dirs, files in os.walk(ROOT_DIR):
    for file in files:
        if not file.endswith(".py"):
            continue

        path = os.path.join(subdir, file)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 1️⃣ Reemplazar imports mal escritos: auth_bp / auth_hp → auth.auth_bp
        content = pattern_import.sub("from blueprints.auth.auth_bp", content)

        # 2️⃣ Reemplazar url_for("auth.xxx") → url_for("auth_bp.xxx")
        content = pattern_url_for.sub(r'url_for("auth_bp.\1")', content)

        # 3️⃣ Si cambió algo, sobrescribimos el archivo
        if content != original:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Corregido: {path}")

print("\n🎉 Todos los imports de auth_bp y url_for corregidos!\n")
