from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bitrix_api import get_deals_for_user, update_deal, get_user_id_by_tg, get_contact_data, get_enum_text, get_user_name_by_tg, set_user_name, get_deal_amount
from config import MANAGER_TG_ID
from models import Deal
from states import ShiftStates
import logging

def setup_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command('start'))  # Handler для /start
    dp.message.register(start_shift, Command('start_shift'))
    dp.message.register(set_name_handler, Command('set_name'))  # Handler для /set_name
    dp.callback_query.register(handle_branch_choice, ShiftStates.choose_branch)  # Handler для выбора ветки
    dp.callback_query.register(handle_deal_choice, ShiftStates.choose_deal)  # Handler для выбора сделки
    dp.callback_query.register(handle_pickup_confirm, ShiftStates.confirm_pickup)
    dp.message.register(update_model_handler, ShiftStates.update_model)
    dp.message.register(enter_complectation_handler, ShiftStates.enter_complectation)  # Новый handler для комплектации
    dp.callback_query.register(handle_complete_order, ShiftStates.complete_order)  # Handler для завершения заказа
    dp.callback_query.register(handle_delivery_confirm, ShiftStates.confirm_delivery)
    dp.message.register(enter_amount_handler, ShiftStates.enter_amount)
    dp.message.register(enter_reject_comment_handler, ShiftStates.enter_reject_comment)  # Handler для комментария при отказе
    dp.message.register(enter_name_handler, ShiftStates.enter_name)  # Handler для ввода имени
    dp.callback_query.register(handle_return_to_menu, lambda query: query.data == "return_to_menu")  # Handler для "Вернуться"

async def start_handler(message: types.Message):
    await message.answer("Добро пожаловать в бота для курьеров! Чтобы начать смену, используйте команду /start_shift.")

async def set_name_handler(message: types.Message, state: FSMContext):
    await message.answer("Введите ваше имя для уведомлений:")
    await state.set_state(ShiftStates.enter_name)

async def enter_name_handler(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if name:
        await set_user_name(message.from_user.id, name)
        await message.answer(f"Имя '{name}' сохранено.")
    else:
        await message.answer("Имя не может быть пустым. Попробуйте снова.")
    await state.clear()

async def start_shift(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id
    user_id = await get_user_id_by_tg(tg_id)
    if not user_id:
        await message.answer("Вы не авторизованы. Добавьте свой ID в маппинг.")
        return
    # Запрашиваем количество сделок для каждой ветки
    deals_branch1 = await get_deals_for_user(user_id, 1)
    deals_branch2 = await get_deals_for_user(user_id, 2)
    count1 = len(deals_branch1)
    count2 = len(deals_branch2)
    # Показываем кнопки выбора ветки с количеством
    text = "Выберите тип смены:"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f"1. Получение товара от заказчика ({count1} сделок)", callback_data="branch_1")],
        [types.InlineKeyboardButton(text=f"2. Доставка отремонтированного товара ({count2} сделок)", callback_data="branch_2")]
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
        text = "Нет активных сделок для получения товара." if branch == 1 else "Нет активных сделок для доставки товара."
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться", callback_data="return_to_menu")]
        ])
        await query.message.answer(text, reply_markup=keyboard)
        return  # Не очищаем состояние, чтобы обработать "Вернуться"
    if len(deals) == 1:
        # Если одна сделка, сразу показываем данные
        await show_deal_data(query, state, deals[0], branch)
    else:
        # Если несколько, показываем список для выбора
        text = "Выберите сделку:"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=deal.get('TITLE', 'Сделка без названия'), callback_data=f"deal_{deal['ID']}_{branch}")] for deal in deals
        ])
        await query.message.answer(text, reply_markup=keyboard)
        await state.set_state(ShiftStates.choose_deal)

async def handle_deal_choice(query: types.CallbackQuery, state: FSMContext):
    data_parts = query.data.split('_')
    deal_id = int(data_parts[1])
    branch = int(data_parts[2])
    await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопки
    await query.answer(f"Выбрана сделка ID {deal_id}.")
    user_id = await get_user_id_by_tg(query.from_user.id)
    deals = await get_deals_for_user(user_id, branch)
    selected_deal = next((deal for deal in deals if deal['ID'] == str(deal_id)), None)
    if not selected_deal:
        await query.message.answer("Сделка не найдена. Попробуйте заново.")
        await state.clear()
        return
    await show_deal_data(query, state, selected_deal, branch)

async def show_deal_data(query: types.CallbackQuery, state: FSMContext, deal_data: dict, branch: int):
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

    # Формат отображения данных с полным текстом ветки
    branch_text = "1. Получение товара от заказчика" if branch == 1 else "2. Доставка отремонтированного товара"
    text = f"{branch_text}\n" \
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
        await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопки
        await query.message.answer("Введите комментарий к отказу:")
        await state.set_state(ShiftStates.enter_reject_comment)

async def update_model_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('deal_id')
    if deal_id:
        await update_deal(deal_id, {'UF_CRM_1756191922': message.text})  # Обновляем поле модели
        await message.answer("Марка/модель обновлена в CRM.")
    
    await message.answer("Введите комплектацию:")
    await state.set_state(ShiftStates.enter_complectation)

async def enter_complectation_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('deal_id')
    complectation = message.text.strip()
    if deal_id and complectation:
        await update_deal(deal_id, {'UF_CRM_1756474226': complectation})  # Обновляем поле комплектации
        await message.answer("Комплектация обновлена в CRM.")
    
    # Показываем кнопку "Завершить заказ"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Завершить заказ", callback_data="complete_order")]
    ])
    await message.answer("Нажмите, чтобы завершить заказ:", reply_markup=keyboard)
    await state.set_state(ShiftStates.complete_order)

async def handle_complete_order(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('deal_id')
    if deal_id:
        await update_deal(deal_id, {'STAGE_ID': 'EXECUTING'})  # Реальный ID стадии "Устройство в офисе"
        await query.answer("Заказ завершён. Сделка перемещена в стадию 'Устройство в офисе'.")
    await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопку
    await state.clear()

async def handle_delivery_confirm(query: types.CallbackQuery, state: FSMContext):
    if query.data == "accept_delivery":
        await query.answer("Заявка принята.")
        await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопки
        await query.message.answer("После доставки введите сумму в рублях:")
        await state.set_state(ShiftStates.enter_amount)
    else:
        await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопки
        await query.message.answer("Введите комментарий к отказу:")
        await state.set_state(ShiftStates.enter_reject_comment)

async def enter_reject_comment_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    branch = data.get('branch')
    comment = message.text.strip()
    user_id = message.from_user.id
    user_name = await get_user_name_by_tg(user_id)  # Получаем имя курьера
    if branch == 1:
        notification = f"Курьер {user_name} ({user_id}) не подтвердил заказ (Ветка 1)."
    else:
        notification = f"Курьер {user_name} ({user_id}) не принял заявку (Ветка 2)."
    if comment:
        notification += f" Комментарий: {comment}"
    await message.bot.send_message(MANAGER_TG_ID, notification)
    await message.answer("Отказ подтверждён. Уведомление отправлено руководителю.")
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
        current_amount = await get_deal_amount(deal_id)  # Получаем текущую сумму
        new_amount = current_amount + amount  # Прибавляем введённую сумму
        # Обновляем стадию и сумму
        await update_deal(deal_id, {
            'STAGE_ID': 'FINAL_INVOICE',  # Реальный ID стадии
            'OPPORTUNITY': new_amount,  # Обновляем сумму сделки
            'UF_CRM_1756360872': amount  # Присваиваем сумму в кастомное поле
        })
        await message.answer("Сделка обновлена в CRM (стадия 'бабки у нас', сумма сохранена и добавлена к общей).")
    await state.clear()

async def handle_return_to_menu(query: types.CallbackQuery, state: FSMContext):
    await query.message.edit_reply_markup(reply_markup=None)  # Удаляем кнопку "Вернуться"
    await query.answer("Возвращаемся к выбору смены.")
    text = "Выберите тип смены:"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="1. Получение товара от заказчика", callback_data="branch_1")],
        [types.InlineKeyboardButton(text="2. Доставка отремонтированного товара", callback_data="branch_2")]
    ])
    await query.message.answer(text, reply_markup=keyboard)
    await state.set_state(ShiftStates.choose_branch)