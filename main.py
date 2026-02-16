# main.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton  # Из telegram
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters  # Из telegram.ext
from handlers import start, message_handler, callback_handler
from db import cursor, conn
from config import TOKEN
from scheduler import schedule_reminders

application = Application.builder().token(TOKEN).build()

# JobQueue создаётся автоматически
job_queue = application.job_queue

# Хэндлеры
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Загрузка существующих расписаний
cursor.execute("SELECT id FROM medications")
for row in cursor.fetchall():
    schedule_reminders(job_queue, row[0])

application.run_polling()

# Закрыть при остановке (Ctrl+C)
conn.close()