from core.db import get_connection

def get_user_by_email(email):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM tbl_login
        WHERE email = %s
        LIMIT 1
    """, (email,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user