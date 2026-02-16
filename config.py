# config.py
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

TOKEN = os.getenv("TOKEN")
ENCRYPTION_KEY_STR = os.getenv("ENCRYPTION_KEY")
PA_USERNAME = os.getenv("PA_USERNAME")          # ← новый параметр

if not TOKEN:
    raise ValueError("TOKEN не задан")
if not ENCRYPTION_KEY_STR:
    raise ValueError("ENCRYPTION_KEY не задан")
if not PA_USERNAME:
    raise ValueError("PA_USERNAME не задан (твой логин на PythonAnywhere)")

ENCRYPTION_KEY = ENCRYPTION_KEY_STR.encode('utf-8')

# Проверка ключа Fernet
try:
    _ = Fernet(ENCRYPTION_KEY)
except Exception as e:
    raise ValueError(f"Неверный ENCRYPTION_KEY: {e}")