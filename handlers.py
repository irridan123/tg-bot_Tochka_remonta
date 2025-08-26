from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bitrix_api import get_deals_for_user, update_deal, get_user_id_by_tg, get_contact_data, get_enum_text
from config import MANAGER_TG_ID
from models import Deal
from states import ShiftStates
import logging

def setup_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command('start'))  # Новый handler для /start
    dp.message.register(start_shift, Command('start_shift'))
    dp.callback_query.register(handle_branch_choice, ShiftStates.choose_branch)  # Новый handler для выбора ветки
    dp.callback_query.register(handle_pickup_confirm, ShiftStates.confirm_pickup)
    dp.message.register(update_model_handler, ShiftStates.update_model)
    dp.callback_query.register(handle_delivery_confirm, ShiftStates.confirm_delivery)
    dp.message.register(enter_amount_handler, ShiftStates.enter_amount)

async def start_handler(message: types.Message):
    await message.answer("Добро пожаловать в бота для курьеров! Чтобы начать смену, используйте команду /start_shift.")

async def start_shift(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id
    user_id = await get_user_id_by_tg(tg_id)
    if not user_id:
        await message.answer("Вы не авторизованы. Добавьте свой ID в маппинг.")
        return
    # Показываем кнопки выбора ветки
    text = "Выберите тип смены:"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="1. Получение товара от заказчика", callback_data="branch_1")],
        [types.InlineKeyboardButton(text="2. Доставка отремонтированного товара", callback_data="branch_2")]
    ])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(ShiftStates.choose_branch)

async def handle_branch_choice(query: types.CallbackQuery, state: FSMContext):
    branch = 1 if query.data == "branch_1" else 2
    await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопки
    await query.answer(f"Выбрана ветка {branch}.")
    user_id = await get_user_id_by_tg(query.from_user.id)
    deals = await get_deals_for_user(user_id, branch)
    if not deals:
        if branch == 1:
            await query.message.answer("Нет активных сделок для получения товара.")
        else:
            await query.message.answer("Нет активных сделок для доставки товара.")
        await state.clear()
        return
    # Берём первую сделку для простоты
    deal_data = deals[0]
    
    # Получаем ID контакта и запрашиваем полные данные
    contact_id = deal_data.get('CONTACT_ID')
    contact_data = await get_contact_data(int(contact_id) if contact_id else 0)
    
    # Формируем строку с контактными данными (имя, фамилия, телефон; добавьте email если нужно)
    contact_str = "Нет контактов"
    if contact_data:
        name = contact_data.get('NAME', '')
        last_name = contact_data.get('LAST_NAME', '')
        phone = contact_data.get('PHONE', [{}])[0].get('VALUE', '') if 'PHONE' in contact_data else ''
        contact_str = f"{name} {last_name} {phone}".strip()
    
    # Обработка даты доставки: берём только дату из ISO-формата
    raw_delivery_date = deal_data.get('UF_CRM_1756191987')
    delivery_date_formatted = "Нет даты"
    if raw_delivery_date:
        delivery_date_formatted = raw_delivery_date.split('T')[0]
    
    # Обработка "Вид": Получаем текст по ID enum
    raw_type_id = deal_data.get('UF_CRM_1756191602')
    type_text = await get_enum_text('UF_CRM_1756191602', raw_type_id) if raw_type_id else "Неизвестно"
    
    deal = Deal(
        id=int(deal_data.get('ID', 0)),
        title=deal_data.get('TITLE', ''),
        address=deal_data.get('UF_CRM_1756190928', ''),
        contact=contact_str,
        type=type_text,
        model=deal_data.get('UF_CRM_1756191922', ''),
        delivery_date=raw_delivery_date
    )
    await state.set_data({'deal_id': deal.id, 'branch': branch})  # Сохраняем ID сделки и ветку
    logging.info(f"Processing deal ID: {deal.id} for user {query.from_user.id} in branch {branch}")

    # Формат отображения данных
    text = f"Ветка: {branch}\n" \
           f"Название сделки: {deal.title}\n" \
           f"Контакты: {deal.contact}\n" \
           f"Адрес: {deal.address}\n" \
           f"Дата доставки: {delivery_date_formatted}\n" \
           f"Вид: {deal.type}\n" \
           f"Модель: {deal.model}"

    if branch == 2:  # Ветка 2: Доставка
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Принять", callback_data="accept_delivery"),
             types.InlineKeyboardButton(text="Отказать", callback_data="reject_delivery")]
        ])
        await query.message.answer(text, reply_markup=keyboard)
        await state.set_state(ShiftStates.confirm_delivery)
    else:  # Ветка 1: Получение
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm_pickup"),
             types.InlineKeyboardButton(text="Отказать", callback_data="reject_pickup")]
        ])
        await query.message.answer(text, reply_markup=keyboard)
        await state.set_state(ShiftStates.confirm_pickup)

async def handle_pickup_confirm(query: types.CallbackQuery, state: FSMContext):
    if query.data == "confirm_pickup":
        await query.answer("Заказ подтверждён.")
        await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопки
        await query.message.answer("После получения введите марку/модель:")
        await state.set_state(ShiftStates.update_model)
    else:
        await query.bot.send_message(MANAGER_TG_ID, f"Курьер {query.from_user.id} не подтвердил заказ (Ветка 1).")
        await query.answer("Отказано. Уведомление отправлено.")
        await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопки
        await state.clear()

async def update_model_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('deal_id')
    if deal_id:
        await update_deal(deal_id, {'UF_CRM_1756191922': message.text})  # Используйте реальный код поля модели
        await message.answer("Марка/модель обновлена в CRM.")
    await state.clear()

async def handle_delivery_confirm(query: types.CallbackQuery, state: FSMContext):
    if query.data == "accept_delivery":
        await query.answer("Заявка принята.")
        await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопки
        await query.message.answer("После доставки введите сумму в рублях:")
        await state.set_state(ShiftStates.enter_amount)
    else:
        await query.bot.send_message(MANAGER_TG_ID, f"Курьер {query.from_user.id} не принял заявку (Ветка 2).")
        await query.answer("Отказано. Уведомление отправлено.")
        await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопки
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
        # Обновляем стадию и сумму (реальный код поля суммы)
        await update_deal(deal_id, {
            'STAGE_ID': 'FINAL_INVOICE',  # Реальный ID стадии
            'UF_CRM_1756212985': amount  # Присваиваем сумму в кастомное поле
        })
        await message.answer("Сделка обновлена в CRM (стадия 'бабки у нас', сумма сохранена).")
    await state.clear()