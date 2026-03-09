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

MENU_BUTTON_TEXT = "🔙 Меню"

# med_management.py

# edit_med.py

# reports.py

# scheduler.py

REMINDER_BASE_TEXT = "🔔 Пора принять лекарство: "
REMINDER_TEXT = REMINDER_BASE_TEXT + "<b>{med_name}</b>!"
REMINDER_BUTTON_TEXT = "✅ Принято"

# TODO: вынести сюда текст