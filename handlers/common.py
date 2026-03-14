import db
import scheduler as sc
import handlers.message_texts as texts

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

router = Router()

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.ADD_MED_BUTTON_TEXT, callback_data="add_med")],
        [InlineKeyboardButton(text=texts.MY_MEDS_BUTTON_TEXT, callback_data="my_meds")],
        [InlineKeyboardButton(text=texts.LOG_STATS_BUTTON_TEXT, callback_data="log_stats")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.START_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "main_menu")
@router.callback_query(F.data == "cancel")
async def to_main_edit(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(texts.MAIN_MENU_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")

async def to_main_answer(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.MAIN_MENU_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("take_"))
async def take_handler(cb: CallbackQuery, state: FSMContext):
    mid = int(cb.data.split("_")[1])
    uid = cb.from_user.id

    # Сначала проверяем, есть ли активный повтор в базе
    active_retry = db.get_active_retry(uid, mid)
    
    if not active_retry:
        # Если записи нет, значит либо уже нажали, либо это старое уведомление
        await cb.answer(texts.TAKE_NOT_ACTUAL_TEXT, show_alert=True)
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

    # Удаляем задачу повторного напоминания, если она есть
    retry_id = f"retry_{uid}_{mid}"
    if sc.scheduler.get_job(retry_id):
        sc.scheduler.remove_job(retry_id)
    
    try:
        await cb.message.edit_text(
            texts.TAKE_TEXT.format(med_name = cb.message.text.replace(texts.REMINDER_BASE_TEXT, '').replace('!', '')),
            reply_markup=None,
            parse_mode="HTML")
    except TelegramBadRequest as e:
        if "query is too old" in e.message:
            # Если запрос устарел, просто отправляем новое сообщение
            await cb.message.edit_text(
                texts.TAKE_TEXT.format(med_name = cb.message.text.replace(texts.REMINDER_BASE_TEXT, '').replace('!', '')),
                reply_markup=None,
                parse_mode="HTML")
            
            # Пытаемся хотя бы убрать кнопку, если это возможно
            try: await cb.message.edit_reply_markup(reply_markup=None)
            except: pass
        else:
            print(f"Ошибка при нажатии кнопки \"Принято\": {e}")
    except Exception:
        pass

    # 5. Отправляем основное меню через твой метод
    await to_main_answer(cb.message, state)
    await cb.answer()

def back_to_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.MENU_BUTTON_TEXT, callback_data="main_menu")]
    ])
