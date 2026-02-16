# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # подхватит .env, если файл существует

# Основные значения из переменных окружения
TOKEN = os.getenv("TOKEN")
ENCRYPTION_KEY_STR = os.getenv("ENCRYPTION_KEY")

# Проверки
if not TOKEN:
    raise ValueError("TOKEN не задан в переменных окружения или .env")
if not ENCRYPTION_KEY_STR:
    raise ValueError("ENCRYPTION_KEY не задан в переменных окружения или .env")

# Преобразование строки в bytes (то, что ожидает Fernet)
ENCRYPTION_KEY = ENCRYPTION_KEY_STR.encode('utf-8')

# Дополнительная проверка длины (защита от ошибок)
if len(ENCRYPTION_KEY) != 44 or not ENCRYPTION_KEY.endswith(b'='):
    raise ValueError(
        f"Неверный ENCRYPTION_KEY: длина должна быть 44 символа и заканчиваться '='\n"
        f"Текущая длина: {len(ENCRYPTION_KEY_STR)}"
    )