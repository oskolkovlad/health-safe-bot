# scheduler.py
from datetime import datetime, timedelta, time  # Добавлен time
from apscheduler.triggers.cron import CronTrigger  # Импортируем для custom расписаний
from db import get_med, log_action, cursor, conn  # Для доступа к БД
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def send_reminder(context):
    job_data = context.job.data  # Данные, переданные в job
    user_id = job_data['user_id']
    med_id = job_data['med_id']
    name = job_data['name']
    description = job_data['description']
    
    desc = description if description else ""
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Я принял", callback_data=f"accept_{med_id}")]])
    await context.bot.send_message(chat_id=user_id, text=f"Время принять {name}! {desc}", reply_markup=keyboard)
    
    # Запланировать проверку на пропуск
    med = get_med(med_id)
    if med:
        context.job_queue.run_once(check_missed, when=med['interval'] * 60,  # в секундах
                                   data={'user_id': user_id, 'med_id': med_id, 'name': med['name']})

async def check_missed(context):
    job_data = context.job.data
    user_id = job_data['user_id']
    med_id = job_data['med_id']
    name = job_data['name']
    
    med = get_med(med_id)
    if not med:
        return
    # Проверка: если нет 'accepted' лога за последние interval + 1 мин
    cursor.execute("SELECT * FROM logs WHERE med_id=? AND timestamp > ? AND status='accepted'",
                   (med_id, (datetime.now() - timedelta(minutes=med['interval'] + 1)).isoformat()))
    if not cursor.fetchone():
        await context.bot.send_message(chat_id=user_id, text=f"Вы пропустили {name}! Напоминаю снова.")
        log_action(med_id, 'missed')
        # Опционально: Повторить send_reminder, если нужно цепочку повторов (с лимитом)

def schedule_reminders(job_queue, med_id):
    med = get_med(med_id)
    if not med:
        return
    details = med['details']
    data = {
        'user_id': med['user_id'],
        'med_id': med_id,
        'name': med['name'],
        'description': med['description']
    }
    chat_id = med['user_id']  # Для job (опционально, но полезно)

    if med['type'] == 'once':
        run_date = datetime.fromisoformat(details['datetime'])
        job_queue.run_once(send_reminder, when=run_date, data=data, chat_id=chat_id)

    elif med['type'] == 'daily':
        time_parts = details['time'].split(':')
        hour, minute = int(time_parts[0]), int(time_parts[1])
        job_queue.run_daily(send_reminder, time=time(hour, minute), data=data, chat_id=chat_id)

    elif med['type'] == 'weekly':
        time_parts = details['time'].split(':')
        hour, minute = int(time_parts[0]), int(time_parts[1])
        # day_of_week: 'mon,tue,...' (0=mon в PTB/APS, но map: 1=mon,7=sun)
        day_map = {1: 'mon', 2: 'tue', 3: 'wed', 4: 'thu', 5: 'fri', 6: 'sat', 7: 'sun'}  # Подкорректировал для 1=пн,7=вс
        cron_days = ','.join(day_map.get(d, '') for d in details['days'])
        trigger = CronTrigger(day_of_week=cron_days, hour=hour, minute=minute)
        job_queue.run_custom(send_reminder, job_kwargs={'trigger': trigger}, data=data, chat_id=chat_id)

    elif med['type'] == 'monthly':
        time_parts = details['time'].split(':')
        hour, minute = int(time_parts[0]), int(time_parts[1])
        day = details['day']
        job_queue.run_monthly(send_reminder, time=time(hour, minute), day=day, data=data, chat_id=chat_id)