# handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from db import (
    add_med, get_meds, get_med, update_med, delete_med, get_logs, log_action
)
from scheduler import schedule_reminders
from datetime import datetime

# ────────────────────────────────────────────────
#               Вспомогательные функции
# ────────────────────────────────────────────────

def clear_state(context):
    """Очищает временные данные пользователя в FSM"""
    context.user_data.clear()

# ────────────────────────────────────────────────
#               Тексты и клавиатуры
# ────────────────────────────────────────────────

MAIN_MENU_TEXT = (
    "Привет! 👋 Я <b>HealthSafe</b> — твой личный страж здоровья 💊\n\n"
    "Не пропусти ни одной таблетки — я напомню вовремя, даже если ты занят(а) 😌\n"
    "Добавляй лекарства, редактируй расписание и следи за приёмом — всё просто и удобно!\n\n"
    "<i>Что делаем сегодня?</i>"
)

MAIN_MENU_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("➕ Добавить лекарство", callback_data="add_med")],
    [InlineKeyboardButton("📋 Мои лекарства", callback_data="list_meds")],
    [InlineKeyboardButton("📊 Логи приёмов", callback_data="view_logs")],
])

CANCEL_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
])

BACK_KB = lambda text="🔙 Назад": InlineKeyboardMarkup([
    [InlineKeyboardButton(text, callback_data="main")]
])

BACK_TO_LIST_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 Назад к списку", callback_data="list_meds")]
])

# ────────────────────────────────────────────────
#               FSM состояния
# ────────────────────────────────────────────────

STATES = {
    'add_name': 'add_name',
    'add_desc': 'add_desc',
    'add_type': 'add_type',
    'add_details': 'add_details',
    'add_interval': 'add_interval',

    'edit_name': 'edit_name',
    'edit_desc': 'edit_desc',
    'edit_interval': 'edit_interval',
    # edit_schedule — можно добавить позже
}

# ────────────────────────────────────────────────
#               Хэндлеры
# ────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=MAIN_MENU_KB,
        parse_mode="HTML"
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    # ─── Главное меню ───────────────────────────────────────
    if data == "main":
        await query.message.edit_text(MAIN_MENU_TEXT, reply_markup=MAIN_MENU_KB, parse_mode="HTML")
        clear_state(context)
        return

    # ─── Отмена ──────────────────────────────────────────────
    if data == "cancel":
        clear_state(context)
        await query.message.edit_text(
            "Действие отменено 👌",
            reply_markup=MAIN_MENU_KB
        )
        return

    # ─── Добавить лекарство ─────────────────────────────────
    if data == "add_med":
        await query.message.edit_text(
            "Окей, давай добавим новое лекарство! 💊\n\nКак называется препарат?",
            reply_markup=CANCEL_KB
        )
        context.user_data['state'] = STATES['add_name']
        context.user_data['temp_med'] = {}
        context.user_data['edit_msg_id'] = query.message.message_id
        return

    # ─── Выбор типа расписания ──────────────────────────────
    if data.startswith("type_"):
        typ = data.split("_")[1]  # once / daily / weekly / monthly
        context.user_data['temp_med']['type'] = typ

        prompts = {
            "once": "Укажи дату и время единоразового приёма\nФормат: 2026-02-20 14:30",
            "daily": "Укажи время ежедневного приёма\nФормат: 08:00",
            "weekly": "Укажи дни недели (1=пн, 2=вт, …, 7=вс) и время\nПример: 1 3 5 21:00",
            "monthly": "Укажи число месяца и время\nПример: 15 09:30"
        }

        prompt = prompts.get(typ, "Укажи детали расписания:")

        await query.message.edit_text(
            f"Выбран тип: <b>{typ.capitalize()}</b>\n\n{prompt}",
            reply_markup=CANCEL_KB,
            parse_mode="HTML"
        )

        context.user_data['state'] = STATES['add_details']
        return

    # ─── Список лекарств ────────────────────────────────────
    if data == "list_meds":
        meds = get_meds(user_id)
        if not meds:
            text = "У тебя пока нет добавленных лекарств 😔\nХочешь добавить первое?"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить", callback_data="add_med")],
                [InlineKeyboardButton("🔙 В главное", callback_data="main")]
            ])
            await query.message.edit_text(text, reply_markup=kb)
            return

        text = "<b>Твои лекарства:</b>\n\n"
        buttons = []
        for med in meds:
            text += f"• <b>{med['name']}</b>  ({med['type']})\n"
            if med['description']:
                text += f"  ↳ {med['description'][:60]}{'...' if len(med['description']) > 60 else ''}\n"
            text += "\n"
            buttons.append([
                InlineKeyboardButton(
                    f"✏️ {med['name'][:18]}{'...' if len(med['name']) > 18 else ''}",
                    callback_data=f"edit_med_{med['id']}"
                )
            ])
        buttons.append([InlineKeyboardButton("🔙 В главное меню", callback_data="main")])

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
        return

    # ─── Редактирование лекарства ───────────────────────────
    if data.startswith("edit_med_"):
        med_id = int(data.split("_")[-1])
        med = get_med(med_id)
        if not med or med['user_id'] != user_id:
            await query.message.edit_text("Лекарство не найдено или не принадлежит тебе.", reply_markup=BACK_KB())
            return

        context.user_data['edit_med_id'] = med_id

        text = f"<b>Редактируем:</b> {med['name']}\n\nЧто меняем?"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Название", callback_data=f"edit_name_{med_id}")],
            [InlineKeyboardButton("Описание", callback_data=f"edit_desc_{med_id}")],
            [InlineKeyboardButton("Расписание", callback_data=f"edit_schedule_{med_id}")],
            [InlineKeyboardButton("Интервал повтора", callback_data=f"edit_interval_{med_id}")],
            [InlineKeyboardButton("🗑️ Удалить лекарство", callback_data=f"delete_med_{med_id}")],
            [InlineKeyboardButton("🔙 Назад к списку", callback_data="list_meds")],
        ])
        await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return

    if data.startswith("delete_med_"):
        med_id = int(data.split("_")[-1])
        delete_med(med_id)
        await query.message.edit_text(
            "Лекарство удалено 🗑️",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 К списку лекарств", callback_data="list_meds")],
                [InlineKeyboardButton("🔙 В главное", callback_data="main")]
            ])
        )
        clear_state(context)
        return

    # ─── Редактирование полей ───────────────────────────────
    edit_fields = {
        "edit_name_": ("edit_name", "Новое название лекарства:"),
        "edit_desc_": ("edit_desc", "Новое описание (или напиши '-', чтобы очистить):"),
        "edit_interval_": ("edit_interval", "Новый интервал напоминания при пропуске (в минутах):"),
    }

    for prefix, (state, prompt) in edit_fields.items():
        if data.startswith(prefix):
            med_id = int(data.split("_")[-1])
            context.user_data['edit_med_id'] = med_id
            context.user_data['state'] = state
            context.user_data['edit_msg_id'] = query.message.message_id

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
            ])
            await query.message.edit_text(prompt, reply_markup=kb)
            return

    # ─── Логи ───────────────────────────────────────────────
    if data == "view_logs":
        meds = get_meds(user_id)
        if not meds:
            await query.message.edit_text(
                "Нет лекарств → нет логов 😅",
                reply_markup=BACK_KB("🔙 В главное")
            )
            return

        text = "<b>Выбери лекарство для просмотра логов:</b>"
        buttons = []
        for med in meds:
            buttons.append([InlineKeyboardButton(med['name'], callback_data=f"logs_{med['id']}")])
        buttons.append([InlineKeyboardButton("🔙 В главное", callback_data="main")])

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
        return

    if data.startswith("logs_"):
        med_id = int(data.split("_")[1])
        logs = get_logs(med_id)
        med = get_med(med_id)

        if not logs:
            text = f"<b>{med['name']}</b>\n\nПока нет записей о приёмах."
        else:
            text = f"<b>Логи для {med['name']}:</b>\n\n"
            for ts, status in logs[:15]:
                emoji = "✅" if status == "accepted" else "❌"
                text += f"{emoji} {ts.split('.')[0].replace('T', ' ')} — {status}\n"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Обновить", callback_data=f"logs_{med_id}")],
            [InlineKeyboardButton("🔙 Назад к списку", callback_data="view_logs")],
            [InlineKeyboardButton("🔙 В главное", callback_data="main")]
        ])
        await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return


# ────────────────────────────────────────────────
#               Обработка текстового ввода (FSM)
# ────────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    if not state:
        return

    text = update.message.text.strip()
    user_id = update.message.from_user.id

    # ─── Добавление ─────────────────────────────────────────
    if state == STATES['add_name']:
        context.user_data['temp_med']['name'] = text
        await update.message.reply_text(
            "Описание (или напиши '-', если не нужно):",
            reply_markup=CANCEL_KB
        )
        context.user_data['state'] = STATES['add_desc']

    elif state == STATES['add_desc']:
        desc = '' if text in ('-', 'skip') else text
        context.user_data['temp_med']['desc'] = desc

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Единоразово", callback_data="type_once")],
            [InlineKeyboardButton("Ежедневно", callback_data="type_daily")],
            [InlineKeyboardButton("По дням недели", callback_data="type_weekly")],
            [InlineKeyboardButton("Ежемесячно", callback_data="type_monthly")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ])
        await update.message.reply_text("Выбери тип расписания:", reply_markup=kb)

    elif state == STATES['add_details']:
        typ = context.user_data['temp_med'].get('type')
        details = {}

        try:
            if typ == "once":
                dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
                details['datetime'] = dt.isoformat()

            elif typ == "daily":
                h, m = map(int, text.split(":"))
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise ValueError("Неверное время")
                details['time'] = f"{h:02d}:{m:02d}"

            elif typ == "weekly":
                parts = text.split()
                days = [int(d) for d in parts[:-1]]
                if any(d < 1 or d > 7 for d in days):
                    raise ValueError("Дни должны быть от 1 до 7")
                time_str = parts[-1]
                h, m = map(int, time_str.split(":"))
                details['days'] = days
                details['time'] = f"{h:02d}:{m:02d}"

            elif typ == "monthly":
                day_str, time_str = text.split()
                day = int(day_str)
                if not 1 <= day <= 31:
                    raise ValueError("День месяца от 1 до 31")
                h, m = map(int, time_str.split(":"))
                details['day'] = day
                details['time'] = f"{h:02d}:{m:02d}"

            context.user_data['temp_med']['details'] = details

            await update.message.reply_text(
                "Отлично! Теперь укажи интервал повторного напоминания при пропуске (в минутах, например 30):",
                reply_markup=CANCEL_KB
            )
            context.user_data['state'] = STATES['add_interval']

        except Exception as e:
            await update.message.reply_text(
                f"Не понял формат. Попробуй ещё раз.\n\nПодсказка: {e}\n\nПовтори ввод:",
                reply_markup=CANCEL_KB
            )
            return

    elif state == STATES['add_interval']:
        try:
            interval = int(text)
            if interval < 5:
                raise ValueError("Слишком маленький интервал")
        except:
            await update.message.reply_text(
                "Нужно ввести число (минуты). Попробуй ещё раз:",
                reply_markup=CANCEL_KB
            )
            return

        temp = context.user_data['temp_med']
        med_id = add_med(
            user_id,
            temp['name'],
            temp.get('desc', ''),
            temp['type'],
            temp['details'],
            interval
        )
        schedule_reminders(context.job_queue, med_id)

        await update.message.reply_text(
            f"Лекарство «{temp['name']}» успешно добавлено! 🎉",
            reply_markup=MAIN_MENU_KB
        )
        clear_state(context)

    # ─── Редактирование полей ───────────────────────────────
    elif state in (STATES['edit_name'], STATES['edit_desc'], STATES['edit_interval']):
        med_id = context.user_data.get('edit_med_id')
        if not med_id:
            await update.message.reply_text("Ошибка сессии. Начни заново.", reply_markup=MAIN_MENU_KB)
            clear_state(context)
            return

        field_map = {
            STATES['edit_name']: 'name',
            STATES['edit_desc']: 'description',
            STATES['edit_interval']: 'reminder_interval'
        }
        field = field_map[state]

        value = text
        if field == 'reminder_interval':
            try:
                value = int(text)
            except:
                await update.message.reply_text("Нужно число (минуты). Попробуй ещё раз:", reply_markup=CANCEL_KB)
                return

        update_med(med_id, field, value)
        schedule_reminders(context.job_queue, med_id)

        await update.message.reply_text(
            f"Поле обновлено! ✅",
            reply_markup=BACK_TO_LIST_KB
        )
        clear_state(context)
