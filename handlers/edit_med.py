import db
import scheduler as sc
import handlers.message_texts as texts

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.common import main_menu_kb

router = Router()

class EditMed(StatesGroup):
    waiting_for_value = State()

async def show_medicine_card(message_or_callback, mid: int):
    m = db.get_full_medicine_by_id(mid)
    if not m: 
        return
    
    text = texts.MED_CARD_TEXT.format(
        med_name = m['name'],
        med_desc = m['description'],
        med_schedule_type = texts.SCHEDULE_TYPE_MAP.get(m['schedule_type']),
        med_schedule_data = m['schedule_data'],
        med_interval = m['interval_minutes']
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.EDIT_MED_NAME_BUTTON_TEXT, callback_data=f"upd_name_{mid}")],
        [InlineKeyboardButton(text=texts.EDIT_MED_DESC_BUTTON_TEXT, callback_data=f"upd_description_{mid}")],
        [InlineKeyboardButton(text=texts.EDIT_MED_SCHEDULE_TYPE_BUTTON_TEXT, callback_data=f"upd_schedule_{mid}")],
        [InlineKeyboardButton(text=texts.EDIT_MED_INTEVAL_BUTTON_TEXT, callback_data=f"upd_interval_minutes_{mid}")],
        [InlineKeyboardButton(text=texts.EDIT_MED_DELETE_BUTTON_TEXT, callback_data=f"del_{mid}")],
        [InlineKeyboardButton(text=texts.BACK_BUTTON_TEXT, callback_data="my_meds")]
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
        return await cb.message.edit_text(texts.EDIT_NO_MEDS_TEXT, reply_markup=main_menu_kb())
    
    btns = [[InlineKeyboardButton(text=m[1], callback_data=f"edit_{m[0]}")] for m in meds]
    btns.append([InlineKeyboardButton(text=texts.MENU_BUTTON_TEXT, callback_data="main_menu")])
    
    await cb.message.edit_text(texts.EDIT_MEDS_LIST_TEXT, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@router.callback_query(F.data.startswith("del_"))
async def del_med(cb: CallbackQuery):
    db.delete_medicine(int(cb.data.split("_")[1]))
    await cb.answer(texts.EDIT_MED_DELETED_TEXT)
    await my_meds(cb)


@router.callback_query(F.data.startswith("edit_"))
async def edit_call(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    mid = int(cb.data.split("_")[1])
    await show_medicine_card(cb, mid)

# 1. Начало редактирования (нажатие кнопки в карточке)
@router.callback_query(F.data.startswith("upd_"))
async def start_upd(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    mid = parts[-1]
    field = "_".join(parts[1:-1])
    
    await state.update_data(edit_med_id=mid, edit_field=field)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=texts.CANCEL_BUTTON_TEXT, callback_data=f"edit_{mid}")]])

    if field == "schedule":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts.ONCE_TYPE_TEXT, callback_data="esch_once")],
            [InlineKeyboardButton(text=texts.DAILY_TYPE_TEXT, callback_data="esch_daily")],
            [InlineKeyboardButton(text=texts.WDAYS_TYPE_TEXT, callback_data="esch_wdays")],
            [InlineKeyboardButton(text=texts.MONTH_TYPE_TEXT, callback_data="esch_month")],
            [InlineKeyboardButton(text=texts.CANCEL_BUTTON_TEXT, callback_data=f"edit_{mid}")]
        ])
        await cb.message.edit_text(texts.EDIT_MED_PROMPTS.get("schedule_type"), reply_markup=kb)
    else:
        await state.set_state(EditMed.waiting_for_value)
        await cb.message.edit_text(texts.EDIT_MED_PROMPTS.get(field, texts.EDIT_MED_DEFAULT_VALUE_TEXT), reply_markup=back_kb)

# 2. Обработка выбора ТИПА расписания (только для поля schedule)
@router.callback_query(F.data.startswith("esch_"))
async def upd_sch_type(cb: CallbackQuery, state: FSMContext):
    sch_type = cb.data.split("_")[1]
    data = await state.get_data()
    mid = data.get("edit_med_id")
    
    await state.update_data(edit_sch_type=sch_type)
    await state.set_state(EditMed.waiting_for_value)

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=texts.CANCEL_BUTTON_TEXT, callback_data=f"edit_{mid}")]])
    await cb.message.edit_text(texts.SCHEDULE_TYPE_PROMPTS.get(sch_type, texts.EDIT_MED_DEFAULT_DATA_TEXT), reply_markup=back_kb, parse_mode="HTML")

# 3. Финал: получение текста и сохранение в базу
@router.message(EditMed.waiting_for_value)
async def finish_upd(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    mid, field = int(data['edit_med_id']), data['edit_field']

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=texts.CANCEL_BUTTON_TEXT, callback_data=f"edit_{mid}")]])

    if field == "name":
        if len(msg.text) < 2:
            return await msg.answer(texts.ERR_TOO_SHORT_NAME_TEXT, reply_markup=back_kb)
    
        if len(msg.text) > 40:
            return await msg.answer(texts.ERR_TOO_LONG_NAME_TEXT.format(name_len=len(msg.text), med_name=msg.text[:30]), reply_markup=back_kb)
    
    if field == "interval_minutes":
        if not msg.text.isdigit():
            return await msg.answer(texts.ERR_INPUT_INT_INTERVAL_TEXT, reply_markup=back_kb)
        
        interval = int(msg.text)
    
        # Валидация диапазона
        if interval < 5:
            return await msg.answer(texts.ERR_MIN_INTERVAL_TEXT, reply_markup=back_kb)
        if interval > 1440:
            return await msg.answer(texts.ERR_MAX_INTERVAL_TEXT, reply_markup=back_kb)

    if field == "schedule":
        db.update_medicine(mid, "schedule_type", data['edit_sch_type'])
        db.update_medicine(mid, "schedule_data", msg.text)
    else:
        db.update_medicine(mid, field, msg.text)
    
    m = db.get_full_medicine_by_id(mid)
    sc.update_med_job(bot, msg.from_user.id, mid, m['name'], m['schedule_type'], m['schedule_data'], m['interval_minutes'])
    
    await state.clear()
    await msg.answer(texts.EDIT_MED_SUCCESS_TEXT.format(med_name=m['name']), parse_mode="HTML")
    await show_medicine_card(msg, mid)