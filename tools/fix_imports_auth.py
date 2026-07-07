# ============================================================
# 🧙‍♂️ FIX IMPORTS AUTH - MODO DIOS
# ============================================================
# Este script busca importaciones MALAS de auth
# y las corrige automáticamente sin romper nada.
#
# 👶 Explicado como para niño de 6 años:
# Si un archivo dice:
#   "ve a auth/auth_bp/decoradores"
# pero esa casa NO existe,
# lo cambiamos a:
#   "auth/decoradores"
# ============================================================

import os
import re
import shutil

# 📁 Carpeta donde está tu proyecto
ROOT_DIR = "."

# 🛡️ Carpeta backup
BACKUP_DIR = "backup_imports_auth"

# 🔍 Reglas de corrección
REGLAS = {
    "blueprints.auth.decoradores": "blueprints.auth.decoradores",
    "blueprints.auth.super_admin_required": "blueprints.auth.super_admin_required",
}


# ============================================================
# 🧸 Función copiar backup
# ============================================================
def crear_backup():
    print("\n🛡️ Creando copia de seguridad...")
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    for root, dirs, files in os.walk("blueprints"):
        for file in files:
            if file.endswith(".py"):
                src = os.path.join(root, file)
                dst = os.path.join(BACKUP_DIR, src)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
    print("✅ Backup creado en /backup_imports_auth")


# ============================================================
# 🧙‍♂️ Función reparar imports
# ============================================================
def reparar_imports():
    print("\n🔎 Buscando imports rotos...")

    cambios = 0

    for root, dirs, files in os.walk(ROOT_DIR):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)

                with open(path, "r", encoding="utf-8") as f:
                    contenido = f.read()

                original = contenido

                # 🧠 Aplicar reglas mágicas
                for malo, bueno in REGLAS.items():
                    if malo in contenido:
                        print(f"🧨 FIX en {path}")
                        contenido = contenido.replace(malo, bueno)

                # ✨ Guardar si hubo cambios
                if contenido != original:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(contenido)
                    cambios += 1

    print(f"\n🎉 Archivos corregidos: {cambios}")


# ============================================================
# 🚀 EJECUCIÓN PRINCIPAL
# ============================================================
if __name__ == "__main__":
    print("======================================")
    print("🤖 SCRIPT ARREGLAR AUTH IMPORTS v1.0")
    print("======================================")

    crear_backup()
    reparar_imports()

    print("\n✅ TODO TERMINADO. Reinicia Flask 😎")
