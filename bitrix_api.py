import aiohttp
import json
import os
from config import BITRIX_DEAL_WEBHOOK_URL, BITRIX_CONTACT_WEBHOOK_URL, BITRIX_DEAL_UPDATE_WEBHOOK_URL, BITRIX_USERFIELD_WEBHOOK_URL
import logging

# Путь к JSON-файлу для хранения данных курьеров
USER_DATA_FILE = 'user_data.json'

# Загрузка USER_DATA из JSON при запуске
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                content = f.read().strip()  # Удаляем пробелы
                if not content:  # Если файл пуст
                    return {}  # Возвращаем пустой dict
                return json.loads(content)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error in {USER_DATA_FILE}: {e}")
            return {}  # Возвращаем пустой dict при ошибке
        except Exception as e:
            logging.error(f"Error loading {USER_DATA_FILE}: {e}")
            return {}
    return {}  # Если файла нет, пустой dict

# Сохранение USER_DATA в JSON
def save_user_data(user_data):
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(user_data, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving {USER_DATA_FILE}: {e}")

USER_DATA = load_user_data()  # Загружаем при старте

async def get_user_id_by_tg(tg_id: int) -> int | None:
    tg_str = str(tg_id)  # Ключи в JSON как строки
    user = USER_DATA.get(tg_str)
    return user.get('bitrix_id') if user else None

async def get_user_name_by_tg(tg_id: int) -> str:
    tg_str = str(tg_id)
    user = USER_DATA.get(tg_str)
    return user.get('name', 'Неизвестный') if user else 'Неизвестный'

async def set_user_name(tg_id: int, name: str):
    tg_str = str(tg_id)
    if tg_str in USER_DATA:
        USER_DATA[tg_str]['name'] = name
    else:
        # Если новый пользователь, добавляем с placeholder bitrix_id (замените на реальный)
        USER_DATA[tg_str] = {'bitrix_id': None, 'name': name}  # Если bitrix_id неизвестен, обновите вручную
    save_user_data(USER_DATA)  # Сохраняем в файл

async def get_deals_for_user(user_id: int, branch: int) -> list[dict]:
    filter_params = {'UF_CRM_1756305557': user_id}  # Изменено: Фильтр по кастомному полю "Курьер"
    if branch == 1:  # Ветка 1: Без даты доставки
        filter_params['UF_CRM_1756191987'] = None  # null
    elif branch == 2:  # Ветка 2: С датой доставки
        filter_params['!UF_CRM_1756191987'] = None  # not null

    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_DEAL_WEBHOOK_URL}crm.deal.list"
        params = {
            'filter': filter_params,
            'select': [
                'ID', 
                'TITLE', 
                'UF_CRM_1756190928',   # Адрес
                'CONTACT_ID',          # ID контакта
                'UF_CRM_1756191602',   # Вид техники (ID enum)
                'UF_CRM_1756191922',   # Марка/модель
                'UF_CRM_1756191987'    # Дата доставки
            ]
        }
        try:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                logging.debug(f"Bitrix deal response: {data}")
                return data.get('result', [])
        except Exception as e:
            logging.error(f"Bitrix deal API error: {e}")
            return []

async def get_contact_data(contact_id: int) -> dict:
    if not contact_id:
        return {}
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_CONTACT_WEBHOOK_URL}crm.contact.get"
        params = {
            'id': contact_id,
            'select': ['NAME', 'LAST_NAME', 'PHONE', 'EMAIL']
        }
        try:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                logging.debug(f"Bitrix contact response: {data}")
                return data.get('result', {})
        except Exception as e:
            logging.error(f"Bitrix contact API error: {e}")
            return {}

async def get_enum_text(field_code: str, value_id: str) -> str:
    """Получает текст значения для списочного (enum) поля по ID."""
    if not value_id:
        return "Неизвестно"
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_USERFIELD_WEBHOOK_URL}crm.deal.userfield.list"
        params = {
            'filter': {'FIELD_NAME': field_code}  # Фильтр по коду поля
        }
        try:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                logging.debug(f"Bitrix userfield list response: {data}")
                fields = data.get('result', [])
                if not fields:
                    logging.debug(f"No fields found for code: {field_code}")
                    return value_id  # Если поле не найдено
                enum_list = fields[0].get('LIST', [])  # Исправлено: 'LIST' вместо 'ENUM'
                logging.debug(f"Enum list for field {field_code}: {enum_list}")
                for item in enum_list:
                    if item.get('ID') == value_id:
                        value_text = item.get('VALUE', value_id)
                        logging.debug(f"Found value: {value_text} for ID {value_id}")
                        return value_text  # Возвращаем текст или ID если не найдено
                logging.debug(f"No matching ID {value_id} in enum list")
                return value_id  # Если не найдено, возвращаем ID
        except Exception as e:
            logging.error(f"Bitrix userfield API error: {e}")
            return value_id

async def update_deal(deal_id: int, fields: dict):
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_DEAL_UPDATE_WEBHOOK_URL}crm.deal.update"
        params = {'id': deal_id, 'fields': fields}
        try:
            async with session.post(url, json=params) as resp:
                return await resp.json()
        except Exception as e:
            logging.error(f"Bitrix update error: {e}")
            return {}