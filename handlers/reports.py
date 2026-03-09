import db
import handlers.message_texts as texts

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from handlers.common import back_to_main_kb

router = Router()

@router.callback_query(F.data == "log_stats")
async def log_list(callback: CallbackQuery):
    meds = db.get_user_medicines(callback.from_user.id)
    if not meds:
        return await callback.message.edit_text(
            texts.NO_MEDS_TEXT, 
            reply_markup=back_to_main_kb()
        )
    
    btns = [[InlineKeyboardButton(text=m[1], callback_data=f"viewlog_{m[0]}")] for m in meds]
    btns.append([InlineKeyboardButton(text=texts.MENU_BUTTON_TEXT, callback_data="main_menu")])
    
    await callback.message.edit_text(
        texts.SELECT_MED_LOGS_TEXT, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )

@router.callback_query(F.data.startswith("viewlog_"))
async def view_log(callback: CallbackQuery):
    mid = int(callback.data.split("_")[1])
    med = db.get_medicine_by_id(mid) 
    logs = db.get_logs_for_medicine(mid)
    
    text = texts.MED_LOGS_TEXT.format(med_name = med[1])
    
    if not logs:
        text += texts.NO_LOG_RECORDS_TEXT
    else:
        for log_raw in logs[:10]:
            try:
                # Преобразуем из YYYY-MM-DD HH:MM:SS в DD.MM.YYYY HH:MM:SS
                dt_obj = datetime.strptime(log_raw, "%Y-%m-%d %H:%M:%S")
                formatted_date = dt_obj.strftime("%d.%m.%Y %H:%M:%S")
                text += f"✅ {formatted_date}\n"
            except ValueError:
                text += f"✅ {log_raw}\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.REFRESH_BUTTON_TEXT, callback_data=f"viewlog_{mid}")],
        [InlineKeyboardButton(text=texts.BACK_BUTTON_TEXT, callback_data="log_stats")]
    ])
    
    # Чтобы кнопка не "висела", уведомляем Telegram, что запрос обработан
    await callback.answer(texts.DATA_REFRESHED_TEXT) 
    
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        # Если текст лога не изменился, Telegram выдаст ошибку "message is not modified"
        # В этом случае просто ничего не делаем
        pass