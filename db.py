import sqlite3

from cryptography.fernet import Fernet
from config import ENCRYPTION_KEY
from datetime import datetime, timedelta, timezone

# Инициализируем объект для шифрования один раз
cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def get_connection():
    return sqlite3.connect("healthsafe.db")

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Таблица лекарств
    cursor.execute('''CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        description TEXT,
        schedule_type TEXT,
        schedule_data TEXT,
        interval_minutes INTEGER
    )''')
    # Таблица логов приема
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_id INTEGER,
        user_id INTEGER,
        taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # Таблица для хранения активных повторов
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_retries (
        user_id INTEGER,
        med_id INTEGER,
        run_at TIMESTAMP,
        PRIMARY KEY (user_id, med_id)
    )''')
    conn.commit()
    conn.close()

def add_medicine(user_id, name, desc, s_type, s_data, interval):
    conn = get_connection()
    cursor = conn.cursor()
    # Шифруем имя (на входе строка -> кодируем в байты -> шифруем -> в текст для БД)
    enc_name = cipher.encrypt(name.encode()).decode()
    enc_desc = cipher.encrypt(desc.encode()).decode()
    cursor.execute(
        "INSERT INTO medicines (user_id, name, description, schedule_type, schedule_data, interval_minutes) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, enc_name, enc_desc, s_type, s_data, interval)
    )
    conn.commit()
    conn.close()

def get_user_medicines(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM medicines WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        try:
            # Расшифровываем: текст из БД -> в байты -> дешифруем -> в строку
            dec_name = cipher.decrypt(row[1].encode()).decode()
            dec_desc = cipher.decrypt(row[2].encode()).decode()
            result.append((row[0], dec_name, dec_desc))
        except Exception:
            result.append((row[0], "[Ошибка расшифровки]", "[Ошибка расшифровки]"))
    return result

def get_medicine_by_id(med_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM medicines WHERE id = ?", (med_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        dec_name = cipher.decrypt(row[1].encode()).decode()
        dec_desc = cipher.decrypt(row[2].encode()).decode()
        return (row[0], dec_name, dec_desc)
    return None

def delete_medicine(med_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medicines WHERE id = ?", (med_id,))
    cursor.execute("DELETE FROM logs WHERE med_id = ?", (med_id,))
    conn.commit()
    conn.close()

def log_intake(med_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Вычисляем московское время (UTC+3)
    moscow_time = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("INSERT INTO logs (med_id, user_id, taken_at) VALUES (?, ?, ?)", (med_id, user_id, moscow_time))
    conn.commit()
    conn.close()

def get_logs_for_medicine(med_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT taken_at FROM logs WHERE med_id = ? ORDER BY taken_at DESC", (med_id,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_all_medicines_raw():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, name, description, schedule_type, schedule_data, interval_minutes FROM medicines")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_medicine(med_id, field, new_value):
    conn = get_connection()
    cursor = conn.cursor()
    
    if field == "name":
        new_value = cipher.encrypt(new_value.encode()).decode()
    
    if field == "description":
        new_value = cipher.encrypt(new_value.encode()).decode()
    
    # field должен быть "interval_minutes", если мы меняем интервал
    query = f"UPDATE medicines SET {field} = ? WHERE id = ?"
    cursor.execute(query, (new_value, med_id))
    conn.commit()
    conn.close()

def get_full_medicine_by_id(med_id):
    conn = get_connection()
    cursor = conn.cursor()
    # Важно: выбираем все 4 поля в строгом порядке
    cursor.execute("SELECT name, description, schedule_type, schedule_data, interval_minutes FROM medicines WHERE id = ?", (med_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "name": cipher.decrypt(row[0].encode()).decode(),
            "description": cipher.decrypt(row[1].encode()).decode(),
            "schedule_type": row[2],
            "schedule_data": row[3],
            "interval_minutes": row[4]
        }
    return None

def add_active_retry(user_id, med_id, run_at):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO active_retries (user_id, med_id, run_at) VALUES (?, ?, ?)",
                   (user_id, med_id, run_at.isoformat()))
    conn.commit()
    conn.close()

def remove_active_retry(user_id, med_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_retries WHERE user_id = ? AND med_id = ?", (user_id, med_id))
    conn.commit()
    conn.close()

def get_all_retries():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, med_id, run_at FROM active_retries")
    rows = cursor.fetchall()
    conn.close()
    return rows
