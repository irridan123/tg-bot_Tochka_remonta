# Файл: handlers.py
# Изменения: 
# - В enter_reject_comment_handler: Для ветки 1 (branch == 1) добавлено обновление стадии сделки на 'UC_O7XQVC' при отказе (после отправки уведомления менеджеру).
#   Это реализует функцию возврата сделки на указанную стадию при отказе в ветке 1.
#   deal_id извлекается из state.get_data(), и вызывается update_deal(deal_id, {'STAGE_ID': 'UC_O7XQVC'}).
# - В show_deal_data: Поле адреса UF_CRM_1747140776508 с парсингом JSON для ключа 'address'. Если парсинг не удался, оставляем оригинальное значение с логом ошибки.
#   Парсинг даты для delivery_date (UF_CRM_1756808681) без времени.
#   Для контакта используется SECOND_NAME: contact = ' '.join([part for part in [NAME, SECOND_NAME, LAST_NAME] if part]).strip()
#   Проверка завершенности сделки по STAGE_ID ('PREPARATION' для branch 1, 'UC_I1EGHC' для branch 2) с добавлением '✅ ' перед TITLE.
# - В handle_branch_choice: Для списка сделок добавляем '✅ ' перед TITLE, если завершена.
# - Импорт: import json для парсинга JSON.
# - В upload_file_handler: Добавление URL в поле UF_CRM_1756808993.
# - Остальной код без изменений.
from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.filters.command import Command
from aiogram.types import ContentType
from aiogram.fsm.context import FSMContext
from bitrix_api import get_deals_for_user, update_deal, get_user_id_by_tg, get_contact_data, get_enum_text, get_user_name_by_tg, set_user_name, get_deal_amount, upload_file_to_disk, add_link_to_deal_field
from config import MANAGER_TG_ID, BITRIX_FOLDER_ID
from models import Deal
from states import ShiftStates
from datetime import datetime
import logging
import time
import json

def setup_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command('start'))
    dp.message.register(start_shift, Command('start_shift'))
    dp.message.register(set_name_handler, Command('set_name'))
    dp.callback_query.register(handle_branch_choice, ShiftStates.choose_branch)
    dp.callback_query.register(handle_deal_choice, ShiftStates.choose_deal)
    dp.callback_query.register(handle_pickup_confirm, ShiftStates.confirm_pickup)
    dp.message.register(update_model_handler, ShiftStates.update_model)
    dp.message.register(enter_complectation_handler, ShiftStates.enter_complectation)
    dp.message.register(upload_file_handler, F.photo | F.document, ShiftStates.upload_files)
    dp.callback_query.register(handle_finish_upload, lambda query: query.data == "finish_upload")
    dp.callback_query.register(handle_complete_order, ShiftStates.complete_order)
    dp.callback_query.register(handle_delivery_confirm, ShiftStates.confirm_delivery)
    dp.message.register(enter_amount_handler, ShiftStates.enter_amount)
    dp.message.register(enter_reject_comment_handler, ShiftStates.enter_reject_comment)
    dp.message.register(enter_name_handler, ShiftStates.enter_name)
    dp.callback_query.register(handle_return_to_menu, lambda query: query.data == "return_to_menu")

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
    deals_branch1 = await get_deals_for_user(user_id, 1)
    deals_branch2 = await get_deals_for_user(user_id, 2)
    count1 = len(deals_branch1)
    count2 = len(deals_branch2)
    text = "Выберите тип смены:"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f"1. Получение товара от заказчика ({count1} сделок)", callback_data="branch_1")],
        [types.InlineKeyboardButton(text=f"2. Доставка отремонтированного товара ({count2} сделок)", callback_data="branch_2")]
    ])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(ShiftStates.choose_branch)

async def handle_branch_choice(query: types.CallbackQuery, state: FSMContext):
    branch = 1 if query.data == "branch_1" else 2
    await query.message.edit_reply_markup(reply_markup=None)
    await query.answer(f"Выбрана ветка {branch}.")
    user_id = await get_user_id_by_tg(query.from_user.id)
    deals = await get_deals_for_user(user_id, branch)
    if not deals:
        text = "Нет активных сделок для получения товара." if branch == 1 else "Нет активных сделок для доставки товара."
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться", callback_data="return_to_menu")]
        ])
        await query.message.answer(text, reply_markup=keyboard)
        return
    if len(deals) == 1:
        await show_deal_data(query, state, deals[0], branch)
    else:
        text = "Выберите сделку:"
        inline_keyboard = []
        for deal in deals:
            is_completed = (branch == 1 and deal.get('STAGE_ID') == 'PREPARATION') or (branch == 2 and deal.get('STAGE_ID') == 'UC_I1EGHC')
            button_text = ('✅ ' if is_completed else '') + deal['TITLE']
            inline_keyboard.append([types.InlineKeyboardButton(text=button_text, callback_data=f"deal_{deal['ID']}")])
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await query.message.answer(text, reply_markup=keyboard)
        await state.set_state(ShiftStates.choose_deal)
        await state.update_data(branch=branch, deals=deals)

async def handle_deal_choice(query: types.CallbackQuery, state: FSMContext):
    deal_id = int(query.data.split('_')[1])
    data = await state.get_data()
    branch = data.get('branch')
    deals = data.get('deals')
    deal = next((d for d in deals if d['ID'] == str(deal_id)), None)
    if deal:
        await show_deal_data(query, state, deal, branch)
    else:
        await query.answer("Сделка не найдена.")

async def show_deal_data(query: types.CallbackQuery, state: FSMContext, deal: dict, branch: int):
    contact_data = await get_contact_data(int(deal.get('CONTACT_ID', 0)))
    contact = ' '.join([part for part in [contact_data.get('NAME', ''), contact_data.get('SECOND_NAME', ''), contact_data.get('LAST_NAME', '')] if part]).strip()
    phone = contact_data.get('PHONE', [{}])[0].get('VALUE', 'Нет') if contact_data.get('PHONE') else 'Нет'
    type_id = deal.get('UF_CRM_1747068372')
    type_text = await get_enum_text('UF_CRM_1747068372', type_id)
    model = deal.get('UF_CRM_1727124284490', 'Не указана')
    address = deal.get('UF_CRM_1747140776508', 'Не указан')
    delivery_date = deal.get('UF_CRM_1756808681', 'Не указана')
    
    if address != 'Не указан':
        try:
            addr_data = json.loads(address)
            address = addr_data.get('address', address)
        except (json.JSONDecodeError, TypeError) as e:
            logging.error(f"Error parsing address JSON: {e}. Keeping original: {address}")
    
    if branch == 2 and delivery_date != 'Не указана':
        try:
            dt = datetime.fromisoformat(delivery_date)
            delivery_date = dt.date().isoformat()
        except ValueError as e:
            logging.error(f"Error parsing delivery date: {e}. Keeping original: {delivery_date}")
    
    is_completed = (branch == 1 and deal.get('STAGE_ID') == 'PREPARATION') or (branch == 2 and deal.get('STAGE_ID') == 'UC_I1EGHC')
    title = ('✅ ' if is_completed else '') + deal['TITLE']
    
    text = f"Сделка: {title}\nАдрес: {address}\nКонтакт: {contact}\nТелефон: {phone}\nВид техники: {type_text}\nМарка/модель: {model}"
    if branch == 2:
        text += f"\nДата доставки: {delivery_date}"
    
    if branch == 1:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Подтвердить забор", callback_data="accept_pickup"),
             types.InlineKeyboardButton(text="Отказаться", callback_data="reject_pickup")]
        ])
        await query.message.answer(text, reply_markup=keyboard)
        await state.set_state(ShiftStates.confirm_pickup)
    else:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Принять заявку", callback_data="accept_delivery"),
             types.InlineKeyboardButton(text="Отказаться", callback_data="reject_delivery")]
        ])
        await query.message.answer(text, reply_markup=keyboard)
        await state.set_state(ShiftStates.confirm_delivery)
    
    await state.update_data(deal_id=int(deal['ID']), branch=branch)

async def handle_pickup_confirm(query: types.CallbackQuery, state: FSMContext):
    if query.data == "accept_pickup":
        await query.answer("Забор подтверждён.")
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.answer("Введите марку/модель (если нужно обновить):")
        await state.set_state(ShiftStates.update_model)
    else:
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.answer("Введите комментарий к отказу:")
        await state.set_state(ShiftStates.enter_reject_comment)

async def update_model_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('deal_id')
    if deal_id:
        await update_deal(deal_id, {'UF_CRM_1727124284490': message.text})
        await message.answer("Марка/модель обновлена в CRM.")
    
    await message.answer("Введите комплектацию:")
    await state.set_state(ShiftStates.enter_complectation)

async def enter_complectation_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('deal_id')
    complectation = message.text.strip()
    if deal_id and complectation:
        await update_deal(deal_id, {'UF_CRM_1727124322720': complectation})
        await message.answer("Комплектация обновлена в CRM.")
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Завершить загрузку", callback_data="finish_upload")]
    ])
    await message.answer("Теперь загрузите фото/документы по одному (или сразу завершите, если файлов нет):", reply_markup=keyboard)
    await state.set_state(ShiftStates.upload_files)

async def upload_file_handler(message: types.Message, state: FSMContext):
    if message.photo:
        file = message.photo[-1]
        file_name = f"photo_{int(time.time())}.jpg"
    elif message.document:
        file = message.document
        file_name = file.file_name or f"document_{int(time.time())}"
    else:
        await message.answer("Отправьте фото или документ.")
        return
    
    file_info = await message.bot.get_file(file.file_id)
    downloaded_file = await message.bot.download_file(file_info.file_path)
    file_content = downloaded_file.read()
    
    upload_result = await upload_file_to_disk(BITRIX_FOLDER_ID, file_name, file_content)
    if upload_result.get('result'):
        file_url = upload_result['result'].get('DETAIL_URL')
        if file_url:
            data = await state.get_data()
            deal_id = data.get('deal_id')
            if deal_id:
                await add_link_to_deal_field(deal_id, 'UF_CRM_1756808993', file_url)
                await message.answer(f"Файл '{file_name}' успешно загружен в Bitrix Disk и ссылка добавлена в сделку.")
            else:
                await message.answer("Ошибка: ID сделки не найден.")
        else:
            await message.answer("Файл загружен, но URL не получен.")
    else:
        await message.answer("Ошибка загрузки файла в Bitrix. Попробуйте снова.")

async def handle_finish_upload(query: types.CallbackQuery, state: FSMContext):
    await query.answer("Загрузка файлов завершена.")
    await query.message.edit_reply_markup(reply_markup=None)
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Завершить заказ", callback_data="complete_order")]
    ])
    await query.message.answer("Нажмите, чтобы завершить заказ:", reply_markup=keyboard)
    await state.set_state(ShiftStates.complete_order)

async def handle_complete_order(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('deal_id')
    if deal_id:
        await update_deal(deal_id, {'STAGE_ID': 'PREPARATION'})
        await query.answer("Заказ завершён. Сделка перемещена в стадию 'Устройство в офисе'.")
    await query.message.edit_reply_markup(reply_markup=None)
    await state.clear()

async def handle_delivery_confirm(query: types.CallbackQuery, state: FSMContext):
    if query.data == "accept_delivery":
        await query.answer("Заявка принята.")
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.answer("После доставки введите сумму в рублях:")
        await state.set_state(ShiftStates.enter_amount)
    else:
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.answer("Введите комментарий к отказу:")
        await state.set_state(ShiftStates.enter_reject_comment)

async def enter_reject_comment_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    branch = data.get('branch')
    deal_id = data.get('deal_id')  # Извлекаем deal_id для обновления стадии
    comment = message.text.strip()
    user_id = message.from_user.id
    user_name = await get_user_name_by_tg(user_id)
    if branch == 1:
        notification = f"Курьер {user_name} ({user_id}) не подтвердил заказ (Ветка 1)."
    else:
        notification = f"Курьер {user_name} ({user_id}) не принял заявку (Ветка 2)."
    if comment:
        notification += f" Комментарий: {comment}"
    await message.bot.send_message(MANAGER_TG_ID, notification)
    await message.answer("Отказ подтверждён. Уведомление отправлено руководителю.")
    
    # Для ветки 1: Возврат сделки на стадию 'UC_O7XQVC'
    if branch == 1 and deal_id:
        await update_deal(deal_id, {'STAGE_ID': 'UC_O7XQVC'})
    
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
        current_amount = await get_deal_amount(deal_id)
        new_amount = current_amount + amount
        await update_deal(deal_id, {
            'STAGE_ID': 'UC_I1EGHC',
            'OPPORTUNITY': new_amount,
            'UF_CRM_1756810984': amount
        })
        await message.answer("Сделка обновлена в CRM (стадия 'бабки у нас', сумма сохранена и добавлена к общей).")
    await state.clear()

async def handle_return_to_menu(query: types.CallbackQuery, state: FSMContext):
    await query.message.edit_reply_markup(reply_markup=None)
    await query.answer("Возвращаемся к выбору смены.")
    text = "Выберите тип смены:"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="1. Получение товара от заказчика", callback_data="branch_1")],
        [types.InlineKeyboardButton(text="2. Доставка отремонтированного товара", callback_data="branch_2")]
    ])
    await query.message.answer(text, reply_markup=keyboard)
    await state.set_state(ShiftStates.choose_branch)