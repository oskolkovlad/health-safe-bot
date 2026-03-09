import db
import scheduler as sc

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.med_management import show_medicine_card, schedule_type_prompts

router = Router()

class EditMed(StatesGroup):
    waiting_for_value = State()

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
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_{mid}")]])

    if field == "schedule":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Единоразово", callback_data="esch_once")],
            [InlineKeyboardButton(text="Ежедневно", callback_data="esch_daily")],
            [InlineKeyboardButton(text="По дням", callback_data="esch_wdays")],
            [InlineKeyboardButton(text="Ежемесячно", callback_data="esch_month")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_{mid}")]
        ])
        await cb.message.edit_text("Выбери новый тип расписания:", reply_markup=kb)
    else:
        await state.set_state(EditMed.waiting_for_value)
        prompts = {
            "name": "Введи новое название лекарства:",
            "description": "Введи новое описание (или '-'):",
            "interval_minutes": "Введи новый интервал повтора (в минутах, например 30):"
        }
        await cb.message.edit_text(prompts.get(field, "Введи значение:"), reply_markup=back_kb)

# 2. Обработка выбора ТИПА расписания (только для поля schedule)
@router.callback_query(F.data.startswith("esch_"))
async def upd_sch_type(cb: CallbackQuery, state: FSMContext):
    sch_type = cb.data.split("_")[1]
    data = await state.get_data()
    mid = data.get("edit_med_id")
    
    await state.update_data(edit_sch_type=sch_type)
    await state.set_state(EditMed.waiting_for_value)

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_{mid}")]])
    await cb.message.edit_text(schedule_type_prompts.get(sch_type, "Введи данные:"), reply_markup=back_kb, parse_mode="HTML")

# 3. Финал: получение текста и сохранение в базу
@router.message(EditMed.waiting_for_value)
async def finish_upd(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    mid, field = int(data['edit_med_id']), data['edit_field']
    
    if field == "interval_minutes":
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_{mid}")]])

        if not msg.text.isdigit():
            return await msg.answer("Пожалуйста, введи число (минуты):", reply_markup=back_kb)
        
        interval = int(msg.text)
    
        # Валидация диапазона
        if interval < 5:
            return await msg.answer("Минимальный интервал — 5 минут.\n\nПопробуй еще раз:", reply_markup=back_kb)
        if interval > 1440:
            return await msg.answer("Максимальный интервал — 1440 минут (24 часа).\n\nПопробуй еще раз:", reply_markup=back_kb)

    if field == "schedule":
        db.update_medicine(mid, "schedule_type", data['edit_sch_type'])
        db.update_medicine(mid, "schedule_data", msg.text)
    else:
        db.update_medicine(mid, field, msg.text)
    
    m = db.get_full_medicine_by_id(mid)
    sc.update_med_job(bot, msg.from_user.id, mid, m['name'], m['schedule_type'], m['schedule_data'], m['interval_minutes'])
    
    await state.clear()
    await msg.answer(f"✅ Данные лекарства «{m['name']}» успешно обновлены!")
    await show_medicine_card(msg, mid)