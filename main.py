import asyncio
import logging

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import common, med_management, edit_med, reports
from db import init_db
from scheduler import scheduler, restore_all_jobs

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s: %(message)s',
    datefmt='%d.%m.%Y %H:%M:%S'
)

async def main():
    # Инициализируем БД (создание таблиц)
    init_db()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Подключаем обработчики
    dp.include_router(common.router)
    dp.include_router(med_management.router)
    dp.include_router(edit_med.router)
    dp.include_router(reports.router)
    
    # Запускаем планировщик
    scheduler.start()
    await restore_all_jobs(bot)
    
    print("🚀 Бот HealthSafe запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен... ⛔️")