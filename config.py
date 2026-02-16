# config.py
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Загружаем .env из текущей директории проекта
load_dotenv()  # автоматически ищет .env в папке, откуда запущен скрипт

TOKEN = os.getenv("TOKEN")
ENCRYPTION_KEY_STR = os.getenv("ENCRYPTION_KEY")
PA_USERNAME = os.getenv("PA_USERNAME")

if not TOKEN:
    raise ValueError("TOKEN не задан в .env или окружении")
if not ENCRYPTION_KEY_STR:
    raise ValueError("ENCRYPTION_KEY не задан в .env или окружении")
if not PA_USERNAME:
    raise ValueError("PA_USERNAME не задан в .env или окружении")

ENCRYPTION_KEY = ENCRYPTION_KEY_STR.encode('utf-8')

# Проверка валидности ключа (Fernet сам выбросит ошибку, если неверный)
try:
    _ = Fernet(ENCRYPTION_KEY)
except Exception as e:
    raise ValueError(f"Неверный ENCRYPTION_KEY: {e}")