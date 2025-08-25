from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bitrix_api import get_deals_for_user, update_deal, get_user_id_by_tg
from config import MANAGER_TG_ID
from models import Deal
from states import ShiftStates

def setup_handlers(dp: Dispatcher):
    dp.message.register(start_shift, Command('start_shift'))
    dp.callback_query.register(handle_pickup_confirm, ShiftStates.confirm_pickup)
    dp.message.register(update_model_handler, ShiftStates.update_model)
    dp.callback_query.register(handle_delivery_confirm, ShiftStates.confirm_delivery)
    dp.message.register(enter_amount_handler, ShiftStates.enter_amount)

async def start_shift(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id
    user_id = await get_user_id_by_tg(tg_id)
    if not user_id:
        await message.answer("Вы не авторизованы. Добавьте свой ID в маппинг.")
        return
    deals = await get_deals_for_user(user_id)
    if not deals:
        await message.answer("Нет активных сделок.")
        return
    # Берём первую сделку для простоты
    deal_data = deals[0]
    deal = Deal(
        id=deal_data.get('ID'),
        title=deal_data.get('TITLE', ''),
        address=deal_data.get('UF_ADDRESS', ''),
        contact=deal_data.get('UF_CONTACT', ''),
        type=deal_data.get('UF_TYPE', ''),
        model=deal_data.get('UF_MODEL', ''),
        delivery_date=deal_data.get('UF_DELIVERY_DATE')
    )
    await state.set_data({'deal_id': deal.id})  # Сохраняем ID сделки

    if deal.delivery_date:  # Ветка 2: Доставка
        text = f"Данные: Контакты: {deal.contact}, Адрес: {deal.address}, Дата: {deal.delivery_date}, Вид: {deal.type}, Модель: {deal.model}"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Принять", callback_data="accept_delivery"),
             types.InlineKeyboardButton(text="Отказать", callback_data="reject_delivery")]
        ])
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(ShiftStates.confirm_delivery)
    else:  # Ветка 1: Получение
        text = f"Данные: Адрес: {deal.address}, Контакты: {deal.contact}, Вид: {deal.type}, Модель: {deal.model}, Название: {deal.title}"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm_pickup"),
             types.InlineKeyboardButton(text="Отказать", callback_data="reject_pickup")]
        ])
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(ShiftStates.confirm_pickup)

async def handle_pickup_confirm(query: types.CallbackQuery, state: FSMContext):
    if query.data == "confirm_pickup":
        await query.answer("Заказ подтверждён.")
        await query.message.answer("После получения введите марку/модель:")
        await state.set_state(ShiftStates.update_model)
    else:
        await query.bot.send_message(MANAGER_TG_ID, f"Курьер {query.from_user.id} не подтвердил заказ (Ветка 1).")
        await query.answer("Отказано. Уведомление отправлено.")
        await state.clear()

async def update_model_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('deal_id')
    if deal_id:
        await update_deal(deal_id, {'UF_MODEL': message.text})
        await message.answer("Марка/модель обновлена в CRM.")
    await state.clear()

async def handle_delivery_confirm(query: types.CallbackQuery, state: FSMContext):
    if query.data == "accept_delivery":
        await query.answer("Заявка принята.")
        await query.message.answer("После доставки введите сумму в рублях:")
        await state.set_state(ShiftStates.enter_amount)
    else:
        await query.bot.send_message(MANAGER_TG_ID, f"Курьер {query.from_user.id} не принял заявку (Ветка 2).")
        await query.answer("Отказано. Уведомление отправлено.")
        await state.clear()

async def enter_amount_handler(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Введите число в рублях.")
        return
    data = await state.get_data()
    deal_id = data.get('deal_id')
    if deal_id:
        await update_deal(deal_id, {'STAGE_ID': 'BABKI_U_NAS'})  # Замените на реальный ID стадии
        await message.answer("Сделка обновлена в CRM (стадия 'бабки у нас').")
    await state.clear()