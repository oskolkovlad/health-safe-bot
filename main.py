# main.py
import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from handlers import start, callback_handler, message_handler
from config import TOKEN

# Создаём приложение (без запуска polling/webhook)
application = Application.builder().token(TOKEN).build()

# Все твои хэндлеры
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Для удобства — функция установки webhook (выполни один раз)
async def set_webhook():
    webhook_url = f"https://{os.getenv('PA_USERNAME')}.pythonanywhere.com/{TOKEN.split(':')[0]}"  # секретный путь
    await application.bot.set_webhook(
        url=webhook_url,
        allowed_updates=["message", "callback_query"]
    )
    print(f"Webhook установлен на: {webhook_url}")

# Если запускаешь локально — polling (для теста)
if __name__ == "__main__":
    import asyncio
    print("Запуск в режиме polling (локально)")
    application.run_polling()