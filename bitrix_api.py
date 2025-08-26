import aiohttp
from config import BITRIX_DEAL_WEBHOOK_URL, BITRIX_CONTACT_WEBHOOK_URL, BITRIX_DEAL_UPDATE_WEBHOOK_URL, BITRIX_USERFIELD_WEBHOOK_URL
import logging

# Маппинг: Telegram ID -> Bitrix User ID (обновите на ваши реальные)
USER_MAPPING = {
    1389473957: 1  # Ваш Telegram ID и Bitrix ID
}

async def get_user_id_by_tg(tg_id: int) -> int | None:
    return USER_MAPPING.get(tg_id, None)

async def get_deals_for_user(user_id: int, branch: int) -> list[dict]:
    filter_params = {'RESPONSIBLE_ID': user_id}
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