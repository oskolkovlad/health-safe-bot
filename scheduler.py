import db

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from db import cipher

scheduler = AsyncIOScheduler()

# Функция, которая непосредственно отправляет уведомление
async def send_reminder(bot: Bot, user_id: int, med_id: int, med_name: str, interval: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принято", callback_data=f"take_{med_id}")]
    ])
    
    try:
        await bot.send_message(
            user_id, 
            f"🔔 Пора принять лекарство: <b>{med_name}</b>!",
            reply_markup=kb,
            parse_mode="HTML"
        )
        
        # Вычисляем время повтора
        run_date = datetime.now() + timedelta(minutes=interval)
        retry_id = f"retry_{user_id}_{med_id}"
        
        # Сохраняем информацию о повторе в БД
        db.add_active_retry(user_id, med_id, run_date)
        
        # Планируем задачу
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=run_date,
            args=[bot, user_id, med_id, med_name, interval],
            id=retry_id,
            replace_existing=True
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")

# Функция для настройки всех задач при старте бота
async def setup_all_schedules(bot: Bot):
    # В реальном проекте здесь нужно пройтись по всей БД и добавить задачи
    # Для краткости реализуем добавление задачи при создании лекарства в handlers.py
    pass

def add_med_job(bot: Bot, user_id: int, med_id: int, med_name: str, s_type: str, s_data: str, interval: int):
    job_id = f"main_{user_id}_{med_id}"
    
    # Парсинг расписания
    if s_type == "once":
        # Формат: 20.02.2026 14:30 или 20.02.2026 8:30
        try:
            run_time = datetime.strptime(s_data, "%d.%m.%Y %H:%M")
        except ValueError:
            # На случай, если ввели H:MM (одну цифру в часе)
            # datetime.strptime часто требует 08:00, поэтому подстрахуемся
            date_part, time_part = s_data.split()
            if len(time_part.split(':')[0]) == 1:
                time_part = "0" + time_part
            run_time = datetime.strptime(f"{date_part} {time_part}", "%d.%m.%Y %H:%M")
            
        scheduler.add_job(send_reminder, "date", run_date=run_time, 
                          args=[bot, user_id, med_id, med_name, interval], id=job_id)
    
    elif s_type == "daily":
        # Формат: 08:00
        hour, minute = map(int, s_data.split(":"))
        scheduler.add_job(send_reminder, "cron", hour=hour, minute=minute, 
                          args=[bot, user_id, med_id, med_name, interval], id=job_id)
    
    elif s_type == "wdays":
        # Формат: 1 3 5 21:00 (дни недели 1-7)
        parts = s_data.split()
        days = ",".join([str(int(d)-1) for d in parts[:-1]]) # APScheduler использует 0-6 (mon-sun)
        hour, minute = map(int, parts[-1].split(":"))
        scheduler.add_job(send_reminder, "cron", day_of_week=days, hour=hour, minute=minute, 
                          args=[bot, user_id, med_id, med_name, interval], id=job_id)
    
    elif s_type == "month":
        # Формат: 15 09:30
        parts = s_data.split()
        day = int(parts[0])
        hour, minute = map(int, parts[1].split(":"))
        scheduler.add_job(send_reminder, "cron", day=day, hour=hour, minute=minute, 
                          args=[bot, user_id, med_id, med_name, interval], id=job_id)

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
        uid, mid, run_at_str = r
        run_at = datetime.fromisoformat(run_at_str)
        
        # Если время повтора уже прошло, пока бот был выключен,
        # APScheduler может выполнить его сразу (если не прошло слишком много времени)
        if run_at > datetime.now():
            m = db.get_full_medicine_by_id(mid) # Получаем инфо о лекарстве
            
            scheduler.add_job(
                send_reminder,
                "date",
                run_date=run_at,
                args=[bot, uid, mid, m['name'], m['interval_minutes']],
                id=f"retry_{uid}_{mid}"
            )
    
    print("🚀 Закончили восстанавливать активные повторы!")

def update_med_job(bot: Bot, user_id: int, med_id: int, med_name: str, s_type: str, s_data: str, interval: int):
    job_id = f"main_{user_id}_{med_id}"
    # Удаляем старую задачу, если она есть
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    # Создаем новую с актуальными данными
    add_med_job(bot, user_id, med_id, med_name, s_type, s_data, interval)
