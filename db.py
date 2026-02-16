import sqlite3
import json
from cryptography.fernet import Fernet
from config import ENCRYPTION_KEY
from datetime import datetime

cipher = Fernet(ENCRYPTION_KEY)

def encrypt(text):
    return cipher.encrypt(text.encode()).decode() if text else None

def decrypt(encrypted_text):
    return cipher.decrypt(encrypted_text.encode()).decode() if encrypted_text else ''

# Инициализация БД
conn = sqlite3.connect('data.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    name TEXT,
    description TEXT,
    schedule_type TEXT,  -- 'once', 'daily', 'weekly', 'monthly'
    schedule_details TEXT,  -- JSON: e.g., {'time': '09:00', 'days': [1,3]} for weekly
    reminder_interval INTEGER  -- минуты для повторного напоминания
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY,
    med_id INTEGER,
    timestamp TEXT,
    status TEXT  -- 'accepted', 'missed'
)
''')
conn.commit()

def add_med(user_id, name, description, schedule_type, schedule_details, reminder_interval=30):
    enc_name = encrypt(name)
    enc_desc = encrypt(description)
    details_json = json.dumps(schedule_details)
    cursor.execute("INSERT INTO medications (user_id, name, description, schedule_type, schedule_details, reminder_interval) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, enc_name, enc_desc, schedule_type, details_json, reminder_interval))
    conn.commit()
    return cursor.lastrowid

def get_meds(user_id):
    cursor.execute("SELECT * FROM medications WHERE user_id=?", (user_id,))
    return [
        {
            'id': row[0],
            'name': decrypt(row[2]),
            'description': decrypt(row[3]),
            'type': row[4],
            'details': json.loads(row[5]),
            'interval': row[6]
        } for row in cursor.fetchall()
    ]

def get_med(med_id):
    cursor.execute("SELECT * FROM medications WHERE id=?", (med_id,))
    row = cursor.fetchone()
    if row:
        return {
            'id': row[0],
            'user_id': row[1],
            'name': decrypt(row[2]),
            'description': decrypt(row[3]),
            'type': row[4],
            'details': json.loads(row[5]),
            'interval': row[6]
        }
    return None

def update_med(med_id, field, value):
    if field in ['name', 'description']:
        value = encrypt(value)
    elif field == 'schedule_details':
        value = json.dumps(value)
    cursor.execute(f"UPDATE medications SET {field}=? WHERE id=?", (value, med_id))
    conn.commit()

def delete_med(med_id):
    cursor.execute("DELETE FROM medications WHERE id=?", (med_id,))
    conn.commit()

def log_action(med_id, status):
    cursor.execute("INSERT INTO logs (med_id, timestamp, status) VALUES (?, ?, ?)", (med_id, datetime.now().isoformat(), status))
    conn.commit()

def get_logs(med_id):
    cursor.execute("SELECT timestamp, status FROM logs WHERE med_id=? ORDER BY timestamp DESC", (med_id,))
    return cursor.fetchall()
