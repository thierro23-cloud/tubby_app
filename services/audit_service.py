# 📜 Diario secreto del Ayuntamiento

from db import ejecutar_query
from datetime import datetime

def log_event(user_id, accion, ip):
    conn = get_comunes_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tbl_auditorias_accesos (idtbl_gestores, fecha, hora_entrada, ip, resultado)
        VALUES (%s, CURDATE(), CURTIME(), %s, %s)
    """, (user_id, ip, accion))
    conn.commit()
    conn.close()
