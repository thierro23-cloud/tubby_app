import os
from config_templates import *

BASE = "templates"

for name, path in globals().items():
    if name.startswith("TPL_"):
        full = os.path.join(BASE, path)
        if not os.path.exists(full):
            print("❌ FALTA:", full)
        else:
            print("✅ OK:", full)
