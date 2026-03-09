# ОБЩЕЕ

MENU_BUTTON_TEXT = "🔙 Меню"
BACK_BUTTON_TEXT = "🔙 Назад"
CANCEL_BUTTON_TEXT = "❌ Отмена"

SCHEDULE_TYPE_PROMPTS = {
    "once": "Укажи дату и время единоразового приёма\n\nФормат: <b><code>05.03.2026 8:00</code></b>",
    "daily": "Укажи время ежедневного приёма\n\nФормат: <b><code>8:00</code></b>",
    "wdays": (
        "Укажи дни недели и время\n"
        "Дни: 1=пн, 2=вт, 3=ср, 4=чт, 5=пт, 6=сб, 7=вс\n\n"
        "Пример (пн, ср, пт в 9 утра):\n"
        "<code>1 3 5 9:00</code>"
    ),
    "month": "Укажи число месяца и время\n\nПример (15-го числа в 21:30):\n<code>15 21:30</code>"
}

NO_MEDS_TEXT = "У тебя пока нет добавленных лекарств 😔"

ERR_TOO_SHORT_NAME_TEXT = "Слишком короткое название. Напиши хотя бы 2 символа."
ERR_TOO_LONG_NAME_TEXT = (
    "Ого, какое длинное название! 😅\n\n"
    "В нем {name_len} символов, а лимит — 40.\n"
    "Попробуй сократить, например: '{med_name}...'"
)

ERR_INPUT_INT_INTERVAL_TEXT = "Пожалуйста, введи число (минуты):"
ERR_MIN_INTERVAL_TEXT = "Минимальный интервал — 5 минут.\n\nПопробуй еще раз:"
ERR_MAX_INTERVAL_TEXT = "Максимальный интервал — 1440 минут (24 часа).\n\nПопробуй еще раз:"

# common.py

START_TEXT = (
    "Привет! 👋 Я <b>HealthSafe</b> — твой личный страж здоровья 💊\n\n"
    "Не пропусти ни одной таблетки — я напомню вовремя, даже если ты занят(а) 😌\n\n"
    "Добавляй лекарства, редактируй расписание и следи за приёмом — всё просто и удобно!\n\n"
    "<i>Что делаем сегодня?</i>"
)

MAIN_MENU_TEXT = (
    "Добавляй лекарства, редактируй расписание и следи за приёмом — всё просто и удобно!\n\n"
    "<i>Что сделаем сейчас?</i>"
)

TAKE_TEXT = "✅ Кайф, лекарство <b>«{med_name}»</b> принято! Будь здоров(а)! 💪"
TAKE_NOT_ACTUAL_TEXT = "Этот прием уже зафиксирован или не актуален."

ADD_MED_BUTTON_TEXT = "➕ Добавить лекарство"
MY_MEDS_BUTTON_TEXT = "📋 Мои лекарства"
LOG_STATS_BUTTON_TEXT = "📊 Журнал приема"

# add_med.py

ADD_MED_NAME_TEXT = "Окей, давай добавим новое лекарство! 💊\n\nКак называется препарат?"
ADD_MED_DESC_TEXT =(
    "Отлично!\n\n"
    "Теперь добавь описание (например, 'после еды') или напиши '-', если описание не нужно:"
)
ADD_MED_SCHEDULE_TYPE_TEXT = "Выбери тип расписания:"
ADD_MED_INTERVAL_TEXT = "Укажи интервал повтора при пропуске (в минутах, например 30):"

ONCE_TYPE_TEXT = "Единоразово"
DAILY_TYPE_TEXT = "Ежедневно"
WDAYS_TYPE_TEXT = "По дням недели"
MONTH_TYPE_TEXT = "Ежемесячно"

ADD_MED_SUCCESS_TEXT = "Лекарство <b>«{med_name}»</b> добавлено! 🎉"

# edit_med.py

SCHEDULE_TYPE_MAP = {
    "once": ONCE_TYPE_TEXT,
    "daily": DAILY_TYPE_TEXT,
    "wdays": WDAYS_TYPE_TEXT,
    "month": MONTH_TYPE_TEXT
}

EDIT_MED_PROMPTS = {
    "name": "Введи новое название лекарства:",
    "description": "Введи новое описание (например, 'после еды') или напиши '-', если описание не нужно:",
    "schedule_type": "Выбери новый тип расписания:",
    "interval_minutes": "Введи новый интервал повтора (в минутах, например 30):"
}

MED_CARD_TEXT = text = (
    "💊 <b>Карточка лекарства: {med_name}</b>\n\n"
    "📝 Описание: {med_desc}\n"
    "⏰ Расписание: {med_schedule_type} ({med_schedule_data})\n"
    "⏳ Интервал: {med_interval} мин.\n\n"
    "<i>Что изменим?</i>"
)

EDIT_MEDS_LIST_TEXT = "📋 <b>Твои лекарства:</b>"
EDIT_MED_DELETED_TEXT = "Удалено"
EDIT_MED_DEFAULT_VALUE_TEXT = "Введи значение:"
EDIT_MED_DEFAULT_DATA_TEXT = "Введи данные:"
EDIT_MED_SUCCESS_TEXT = "✅ Данные лекарства <b>«{med_name}»</b> успешно обновлены!"

EDIT_MED_NAME_BUTTON_TEXT = "✏️ Название"
EDIT_MED_DESC_BUTTON_TEXT = "📝 Описание"
EDIT_MED_SCHEDULE_TYPE_BUTTON_TEXT = "⏰ Расписание"
EDIT_MED_INTEVAL_BUTTON_TEXT = "⏳ Интервал"
EDIT_MED_DELETE_BUTTON_TEXT = "🗑 Удалить"

# reports.py

SELECT_MED_LOGS_TEXT = "Выбери лекарство для просмотра журнала приема:"
MED_LOGS_TEXT = "📊 Журнал приема: <b>«{med_name}»</b>\n\n"
NO_LOG_RECORDS_TEXT= "Записей пока нет."
DATA_REFRESHED_TEXT = "Данные обновлены!"

REFRESH_BUTTON_TEXT = "🔄 Обновить"

# scheduler.py

REMINDER_BASE_TEXT = "🔔 Пора принять лекарство: "
REMINDER_TEXT = REMINDER_BASE_TEXT + "<b>«{med_name}»</b>!"

REMINDER_BUTTON_TEXT = "✅ Принято"
