import db
import scheduler as sc

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

router = Router()

main_text = (
    "Добавляй лекарства, редактируй расписание и следи за приёмом — всё просто и удобно!\n\n"
    "<i>Что сделаем сейчас?</i>"
)

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить лекарство", callback_data="add_med")],
        [InlineKeyboardButton(text="📋 Мои лекарства", callback_data="my_meds")],
        [InlineKeyboardButton(text="📊 Журнал приема", callback_data="log_stats")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "Привет! 👋 Я <b>HealthSafe</b> — твой личный страж здоровья 💊\n\n"
        "Не пропусти ни одной таблетки — я напомню вовремя, даже если ты занят(а) 😌\n\n"
        "Добавляй лекарства, редактируй расписание и следи за приёмом — всё просто и удобно!\n\n"
        "<i>Что делаем сегодня?</i>"
    )
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "main_menu")
@router.callback_query(F.data == "cancel")
async def to_main_edit(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(main_text, reply_markup=main_menu_kb(), parse_mode="HTML")

async def to_main_answer(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(main_text, reply_markup=main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("take_"))
async def take_handler(cb: CallbackQuery, state: FSMContext):
    mid = int(cb.data.split("_")[1])
    uid = cb.from_user.id

    # Сначала проверяем, есть ли активный повтор в базе
    active_retry = db.get_active_retry(uid, mid)
    
    if not active_retry:
        # Если записи нет, значит либо уже нажали, либо это старое уведомление
        await cb.answer("Этот прием уже зафиксирован или не актуален.", show_alert=True)
        try:
            await cb.message.edit_reply_markup(reply_markup=None) # Убираем кнопку от греха подальше
        except:
            pass
        return
    
    # Если мы здесь — значит нажатие легитимное
    # 1. СРАЗУ удаляем из базы, чтобы другие нажатия не прошли
    db.remove_active_retry(uid, mid) # Удаляем из БД, чтобы не восстановилось
    
    # 2. Логируем прием
    db.log_intake(mid, uid)

    # 3. Убираем кнопку у текущего сообщения (превращаем в текст "Принято")
    try:
        await cb.message.edit_text(f"✅ Принято: {cb.message.text.replace('🔔 Пора принять лекарство: ', '')}", reply_markup=None)
    except Exception:
        pass
    
    # Удаляем задачу повторного напоминания, если она есть
    retry_id = f"retry_{uid}_{mid}"
    if sc.scheduler.get_job(retry_id):
        sc.scheduler.remove_job(retry_id)
        
    await cb.message.edit_text("✅ Кайф, лекарство принято! Будь здоров(а)! 💪", reply_markup=back_to_main_kb())
    
    # 5. Отправляем основное меню через твой метод
    await to_main_answer(cb.message, state)
    await cb.answer()

def back_to_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu")]
    ])
