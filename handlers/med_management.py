import db
import scheduler as sc

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.common import main_menu_kb, to_main_answer

router = Router()

schedule_type_prompts = {
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

# Состояния для добавления нового лекарства
class AddMed(StatesGroup):
    name = State()
    description = State()
    schedule_type = State()
    schedule_data = State()
    interval = State()

# --- Вспомогательные клавиатуры ---

def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def nav_kb(back_data: str):
    """Универсальная клавиатура с кнопками Назад и Отмена"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data=back_data),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ])

# --- Вспомогательные функции ---

async def show_medicine_card(message_or_callback, mid: int):
    m = db.get_full_medicine_by_id(mid)
    if not m: 
        return
    
    t_map = {"once": "Единоразово", "daily": "Ежедневно", "wdays": "По дням", "month": "Ежемесячно"}
    
    text = (f"💊 <b>Карточка лекарства: {m['name']}</b>\n\n"
            f"📝 Описание: {m['description']}\n"
            f"⏰ Расписание: {t_map.get(m['schedule_type'])} ({m['schedule_data']})\n"
            f"⏳ Интервал: {m['interval_minutes']} мин.\n\n"
            f"<i>Что изменим?</i>")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Название", callback_data=f"upd_name_{mid}")],
        [InlineKeyboardButton(text="📝 Описание", callback_data=f"upd_description_{mid}")],
        [InlineKeyboardButton(text="⏰ Расписание", callback_data=f"upd_schedule_{mid}")],
        [InlineKeyboardButton(text="⏳ Интервал", callback_data=f"upd_interval_minutes_{mid}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_{mid}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="my_meds")]
    ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# --- Обработчики списка и удаления ---

@router.callback_query(F.data == "my_meds")
async def my_meds(cb: CallbackQuery):
    meds = db.get_user_medicines(cb.from_user.id)
    if not meds: 
        return await cb.message.edit_text("У тебя пока нет добавленных лекарств 😔", reply_markup=main_menu_kb())
    
    btns = [[InlineKeyboardButton(text=m[1], callback_data=f"edit_{m[0]}")] for m in meds]
    btns.append([InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu")])
    
    await cb.message.edit_text("📋 <b>Твои лекарства:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@router.callback_query(F.data.startswith("del_"))
async def del_med(cb: CallbackQuery):
    db.delete_medicine(int(cb.data.split("_")[1]))
    await cb.answer("Удалено")
    await my_meds(cb)

# --- Сценарий: Добавление лекарства (с навигацией Назад) ---

@router.callback_query(F.data == "add_med")
async def add_med_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddMed.name)
    await callback.message.edit_text("Окей, давай добавим новое лекарство! 💊\n\nКак называется препарат?", reply_markup=cancel_kb())

@router.message(AddMed.name)
async def add_med_name(msg: Message, state: FSMContext):
    # Убираем лишние пробелы по краям
    med_name = msg.text.strip()
    
    # ПРОВЕРКА ДЛИНЫ
    if len(med_name) < 2:
        return await msg.answer("Слишком короткое название. Напиши хотя бы 2 символа.")
    
    if len(med_name) > 40:
        return await msg.answer(
            f"Ого, какое длинное название! 😅\n\n"
            f"В нем {len(med_name)} символов, а лимит — 40.\n"
            f"Попробуй сократить, например: '{med_name[:30]}...'"
        )

    await state.update_data(name=med_name)
    await state.set_state(AddMed.description)
    await msg.answer(
        f"Отлично!\n\n"
        "Теперь добавь описание (например, 'после еды') или напиши '-', если описание не нужно:",
        reply_markup=nav_kb("back_to_name_input"),
        parse_mode="HTML"
    )

@router.message(AddMed.description)
async def add_med_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddMed.schedule_type)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Единоразово", callback_data="sch_once")],
        [InlineKeyboardButton(text="Ежедневно", callback_data="sch_daily")],
        [InlineKeyboardButton(text="По дням недели", callback_data="sch_wdays")],
        [InlineKeyboardButton(text="Ежемесячно", callback_data="sch_month")],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_desc_input"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ])
    await message.answer("Выбери тип расписания:", reply_markup=kb)

@router.callback_query(F.data.startswith("sch_"))
async def add_med_sch_choice(callback: CallbackQuery, state: FSMContext):
    sch_type = callback.data.split("_")[1]
    await state.update_data(schedule_type=sch_type)
    await state.set_state(AddMed.schedule_data)
    await callback.message.edit_text(schedule_type_prompts[sch_type], reply_markup=nav_kb("back_to_sch_type"), parse_mode="HTML")

@router.message(AddMed.schedule_data)
async def add_med_sch_data(message: Message, state: FSMContext):
    await state.update_data(schedule_data=message.text)
    await state.set_state(AddMed.interval)
    await message.answer("Укажи интервал повтора при пропуске (в минутах):", reply_markup=nav_kb("back_to_sch_data"))

@router.message(AddMed.interval)
async def add_med_finish(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введи число (минуты):", reply_markup=nav_kb("back_to_sch_data"))
    
    interval = int(message.text)
    
    # Валидация диапазона
    if interval < 5:
        return await message.answer("Минимальный интервал — 5 минут.\n\nПопробуй еще раз:", reply_markup=nav_kb("back_to_sch_data"))
    if interval > 1440:
        return await message.answer("Максимальный интервал — 1440 минут (24 часа).\n\nПопробуй еще раз:", reply_markup=nav_kb("back_to_sch_data"))

    data = await state.get_data()
    db.add_medicine(message.from_user.id, data['name'], data['description'], data['schedule_type'], data['schedule_data'], interval)
    
    meds = db.get_user_medicines(message.from_user.id)
    new_med = meds[-1]
    
    sc.add_med_job(bot, message.from_user.id, new_med[0], new_med[1],  data['schedule_type'], data['schedule_data'], interval)
    
    await state.clear()
    await message.answer(f"Лекарство <b>«{data['name']}»</b> добавлено! 🎉", parse_mode="HTML")
    await to_main_answer(message, state)

# --- Обработчики кнопок "Назад" ---

@router.callback_query(F.data == "back_to_name_input")
async def back_to_name_input(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddMed.name)
    await cb.message.edit_text("Как называется препарат?", reply_markup=cancel_kb())

@router.callback_query(F.data == "back_to_desc_input")
async def back_to_desc_input(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddMed.description)
    await cb.message.edit_text("Укажи описание или напиши '-', если не нужно:", reply_markup=nav_kb("back_to_name_input"))

@router.callback_query(F.data == "back_to_sch_type")
async def back_to_sch_type(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddMed.schedule_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Единоразово", callback_data="sch_once")],
        [InlineKeyboardButton(text="Ежедневно", callback_data="sch_daily")],
        [InlineKeyboardButton(text="По дням недели", callback_data="sch_wdays")],
        [InlineKeyboardButton(text="Ежемесячно", callback_data="sch_month")],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_desc_input"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
        ]
    ])
    await cb.message.edit_text("Выбери тип расписания:", reply_markup=kb)

@router.callback_query(F.data == "back_to_sch_data")
async def back_to_sch_data(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sch_type = data.get("schedule_type", "daily")
    await state.set_state(AddMed.schedule_data)
    await cb.message.edit_text(schedule_type_prompts[sch_type], reply_markup=nav_kb("back_to_sch_type"), parse_mode="HTML")