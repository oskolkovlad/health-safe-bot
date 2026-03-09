import db
import scheduler as sc
import handlers.message_texts as texts

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.common import to_main_answer

router = Router()

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
        [InlineKeyboardButton(text=texts.CANCEL_BUTTON_TEXT, callback_data="cancel")]
    ])

def nav_kb(back_data: str):
    """Универсальная клавиатура с кнопками Назад и Отмена"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts.BACK_BUTTON_TEXT, callback_data=back_data),
            InlineKeyboardButton(text=texts.CANCEL_BUTTON_TEXT, callback_data="cancel")
        ]
    ])

# --- Сценарий: Добавление лекарства (с навигацией Назад) ---

@router.callback_query(F.data == "add_med")
async def add_med_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddMed.name)
    await callback.message.edit_text(texts.ADD_MED_NAME_TEXT, reply_markup=cancel_kb())

@router.message(AddMed.name)
async def add_med_name(msg: Message, state: FSMContext):
    # Убираем лишние пробелы по краям
    med_name = msg.text.strip()
    
    # ПРОВЕРКА ДЛИНЫ
    if len(med_name) < 2:
        return await msg.answer(texts.ERR_TOO_SHORT_NAME_TEXT)
    
    if len(med_name) > 40:
        return await msg.answer(texts.ERR_TOO_LONG_NAME_TEXT.format(name_len=len(med_name), med_name=med_name[:30]))

    await state.update_data(name=med_name)
    await state.set_state(AddMed.description)
    await msg.answer(texts.ADD_MED_DESC_TEXT, reply_markup=nav_kb("back_to_name_input"), parse_mode="HTML")

@router.message(AddMed.description)
async def add_med_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddMed.schedule_type)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.ONCE_TYPE_TEXT, callback_data="sch_once")],
        [InlineKeyboardButton(text=texts.DAILY_TYPE_TEXT, callback_data="sch_daily")],
        [InlineKeyboardButton(text=texts.WDAYS_TYPE_TEXT, callback_data="sch_wdays")],
        [InlineKeyboardButton(text=texts.MONTH_TYPE_TEXT, callback_data="sch_month")],
        [
            InlineKeyboardButton(text=texts.BACK_BUTTON_TEXT, callback_data="back_to_desc_input"),
            InlineKeyboardButton(text=texts.CANCEL_BUTTON_TEXT, callback_data="cancel")
        ]
    ])
    await message.answer(texts.ADD_MED_SCHEDULE_TYPE_TEXT, reply_markup=kb)

@router.callback_query(F.data.startswith("sch_"))
async def add_med_sch_choice(callback: CallbackQuery, state: FSMContext):
    sch_type = callback.data.split("_")[1]
    await state.update_data(schedule_type=sch_type)
    await state.set_state(AddMed.schedule_data)
    await callback.message.edit_text(texts.SCHEDULE_TYPE_PROMPTS[sch_type], reply_markup=nav_kb("back_to_sch_type"), parse_mode="HTML")

@router.message(AddMed.schedule_data)
async def add_med_sch_data(message: Message, state: FSMContext):
    await state.update_data(schedule_data=message.text)
    await state.set_state(AddMed.interval)
    await message.answer(texts.ADD_MED_INTERVAL_TEXT, reply_markup=nav_kb("back_to_sch_data"))

@router.message(AddMed.interval)
async def add_med_finish(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit():
        return await message.answer(texts.ERR_INPUT_INT_INTERVAL_TEXT, reply_markup=nav_kb("back_to_sch_data"))
    
    interval = int(message.text)
    
    # Валидация диапазона
    if interval < 5:
        return await message.answer(texts.ERR_MIN_INTERVAL_TEXT, reply_markup=nav_kb("back_to_sch_data"))
    if interval > 1440:
        return await message.answer(texts.ERR_MAX_INTERVAL_TEXT, reply_markup=nav_kb("back_to_sch_data"))

    data = await state.get_data()
    db.add_medicine(message.from_user.id, data['name'], data['description'], data['schedule_type'], data['schedule_data'], interval)
    
    meds = db.get_user_medicines(message.from_user.id)
    new_med = meds[-1]
    
    sc.add_med_job(bot, message.from_user.id, new_med[0], new_med[1],  data['schedule_type'], data['schedule_data'], interval)
    
    await state.clear()
    await message.answer(texts.ADD_MED_SUCCESS_TEXT.format(med_name=data['name']), parse_mode="HTML")
    await to_main_answer(message, state)

# --- Обработчики кнопок "Назад" ---

@router.callback_query(F.data == "back_to_name_input")
async def back_to_name_input(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddMed.name)
    await cb.message.edit_text(texts.ADD_MED_NAME_TEXT, reply_markup=cancel_kb())

@router.callback_query(F.data == "back_to_desc_input")
async def back_to_desc_input(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddMed.description)
    await cb.message.edit_text(texts.ADD_MED_DESC_TEXT, reply_markup=nav_kb("back_to_name_input"))

@router.callback_query(F.data == "back_to_sch_type")
async def back_to_sch_type(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddMed.schedule_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.ONCE_TYPE_TEXT, callback_data="sch_once")],
        [InlineKeyboardButton(text=texts.DAILY_TYPE_TEXT, callback_data="sch_daily")],
        [InlineKeyboardButton(text=texts.WDAYS_TYPE_TEXT, callback_data="sch_wdays")],
        [InlineKeyboardButton(text=texts.MONTH_TYPE_TEXT, callback_data="sch_month")],
        [
            InlineKeyboardButton(text=texts.BACK_BUTTON_TEXT, callback_data="back_to_desc_input"),
            InlineKeyboardButton(text=texts.CANCEL_BUTTON_TEXT, callback_data="cancel")
        ]
    ])
    await cb.message.edit_text(texts.ADD_MED_SCHEDULE_TYPE_TEXT, reply_markup=kb)

@router.callback_query(F.data == "back_to_sch_data")
async def back_to_sch_data(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sch_type = data.get("schedule_type", "daily")
    await state.set_state(AddMed.schedule_data)
    await cb.message.edit_text(texts.SCHEDULE_TYPE_PROMPTS[sch_type], reply_markup=nav_kb("back_to_sch_type"), parse_mode="HTML")