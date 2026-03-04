import os

from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Валидация при старте
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в файле .env")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY не найден в файле .env. Сгенерируй его через cryptography.")