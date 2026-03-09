import db
import handlers.message_texts as texts

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from db import cipher

scheduler = AsyncIOScheduler(job_defaults={
    'misfire_grace_time': 180, # Допускаем опоздание до 180 секунд
    'coalesce': True           # Если было несколько пропусков, запустить один раз
})

# Функция, которая непосредственно отправляет уведомление
async def send_reminder(bot: Bot, user_id: int, med_id: int, med_name: str, interval: int):
    # 1. Пытаемся получить данные о текущем (плановом) напоминании из БД
    # Это нужно, чтобы вычислить следующий шаг без "дрейфа" времени
    active_retry = db.get_active_retry(user_id, med_id)
    
    if active_retry:
        # active_retry[0] - это msg_id, active_retry[1] - это запланированное время (run_at)
        old_msg_id = active_retry[0]
        planned_run_at = datetime.fromisoformat(active_retry[1])
        
        # Убираем кнопку у предыдущего сообщения, если оно было
        try:
            # Убираем кнопку у старого сообщения (оставляем только текст)
            await bot.edit_message_reply_markup(chat_id=user_id, message_id=old_msg_id, reply_markup=None)
        except Exception:
            pass # Если сообщение удалено пользователем или слишком старое
    else:
        # Если в базе почему-то нет записи (первый запуск), берем текущее время как точку отсчета
        planned_run_at = datetime.now()

    # 2. Формируем и отправляем новое уведомление
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.REMINDER_BUTTON_TEXT, callback_data=f"take_{med_id}")]
    ])
    
    try:
        msg = await bot.send_message(
            user_id, 
            texts.REMINDER_TEXT.format(med_name=med_name),
            reply_markup=kb,
            parse_mode="HTML"
        )
        
        # 3. ВЫЧИСЛЯЕМ СЛЕДУЮЩИЙ ПОВТОР
        # Прибавляем интервал к ПЛАНОВОМУ времени, чтобы сетка (23:00, 23:30...) не сдвигалась
        next_run = planned_run_at + timedelta(minutes=interval)
        
        # Защита от "догона": если бот лежал очень долго, и next_run все еще в прошлом,
        # сдвигаем его в ближайшее будущее относительно "сейчас"
        if next_run <= datetime.now():
            next_run = datetime.now() + timedelta(minutes=interval)

        # 4. Обновляем информацию в БД и планируем новую задачу
        db.add_active_retry(user_id, med_id, next_run, msg.message_id)
        
        # Планируем задачу
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=next_run,
            args=[bot, user_id, med_id, med_name, interval],
            id=f"retry_{user_id}_{med_id}",
            misfire_grace_time=3600 # Даем час на "опоздание"
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")

# Функция для настройки всех задач при старте бота
async def setup_all_schedules(bot: Bot):
    # В реальном проекте здесь нужно пройтись по всей БД и добавить задачи
    # Для краткости реализуем добавление задачи при создании лекарства в handlers.py
    pass

def add_med_job(bot: Bot, user_id: int, med_id: int, med_name: str, s_type: str, s_data: str, interval: int):
    trigger = None
    trigger_args = {}

    if s_type == "once":
        trigger = "date"
        # Формат: 20.02.2026 14:30 или 20.02.2026 8:30
        try:
            trigger_args["run_date"] = datetime.strptime(s_data, "%d.%m.%Y %H:%M")
        except ValueError:
            # На случай, если ввели H:MM (одну цифру в часе)
            # datetime.strptime часто требует 08:00, поэтому подстрахуемся
            date_part, time_part = s_data.split()
            if len(time_part.split(':')[0]) == 1:
                time_part = "0" + time_part
            trigger_args["run_date"] = datetime.strptime(f"{date_part} {time_part}", "%d.%m.%Y %H:%M")
    
    elif s_type == "daily":
        # Формат: 08:00
        trigger = "cron"
        hour, minute = map(int, s_data.split(":"))
        trigger_args["hour"] = hour
        trigger_args["minute"] = minute
    
    elif s_type == "wdays":
        # Формат: 1 3 5 21:00 (дни недели 1-7)
        trigger = "cron"
        parts = s_data.split()
        days = ",".join([str(int(d)-1) for d in parts[:-1]]) # APScheduler использует 0-6 (mon-sun)
        hour, minute = map(int, parts[-1].split(":"))
        trigger_args["day_of_week"] = days
        trigger_args["hour"] = hour
        trigger_args["minute"] = minute
    
    elif s_type == "month":
        # Формат: 15 09:30
        trigger = "cron"
        parts = s_data.split()
        day = int(parts[0])
        hour, minute = map(int, parts[1].split(":"))
        trigger_args["day"] = day
        trigger_args["hour"] = hour
        trigger_args["minute"] = minute

    if trigger:
        scheduler.add_job(
            send_reminder,
            trigger,
            **trigger_args,
            args=[bot, user_id, med_id, med_name, interval],
            id=f"main_{user_id}_{med_id}",
            replace_existing=True,
            misfire_grace_time=3600 # Для основных задач (раз в день) можно и час запаса дать
        )

async def restore_all_jobs(bot: Bot):
    print("🚀 Начинаем восстанавливать основные задачи...")

    # 1. Восстанавливаем основные задачи
    all_meds = db.get_all_medicines_raw()
    for m in all_meds:
        try:
            name = cipher.decrypt(m[2].encode()).decode()
            add_med_job(bot, m[1], m[0], name, m[4], m[5], m[6])
        except Exception as e:
            print(f"Ошибка восстановления основной задачи {m[0]}: {e}")

    print("🚀 Закончили восстанавливать основные задачи!")
    print("🚀 Начали восстанавливать активные повторы...")

    # 2. Восстанавливаем активные повторы
    all_retries = db.get_all_retries()
    for r in all_retries:
        uid, mid, run_at_str, last_msg_id = r
        run_at = datetime.fromisoformat(run_at_str)
        
        # Если время повтора уже прошло, пока бот был выключен,
        # APScheduler может выполнить его сразу (если не прошло слишком много времени)
        if run_at > (datetime.now() - timedelta(hours=1)):
            m = db.get_full_medicine_by_id(mid) # Получаем инфо о лекарстве
            if not m: continue
            
            scheduler.add_job(
                send_reminder,
                "date",
                run_date=run_at,
                args=[bot, uid, mid, m['name'], m['interval_minutes']],
                id=f"retry_{uid}_{mid}",
                misfire_grace_time=3600 # Дополнительная страховка для конкретной задачи
            )
    
    print("🚀 Закончили восстанавливать активные повторы!")

def update_med_job(bot: Bot, user_id: int, med_id: int, med_name: str, s_type: str, s_data: str, interval: int):
    job_id = f"main_{user_id}_{med_id}"
    # Удаляем старую задачу, если она есть
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    # Создаем новую с актуальными данными
    add_med_job(bot, user_id, med_id, med_name, s_type, s_data, interval)
