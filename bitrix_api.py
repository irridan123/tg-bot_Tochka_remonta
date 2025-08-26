import aiohttp
from config import BITRIX_DEAL_WEBHOOK_URL, BITRIX_CONTACT_WEBHOOK_URL, BITRIX_DEAL_UPDATE_WEBHOOK_URL
import logging

# Маппинг: Telegram ID -> Bitrix User ID (обновите на ваши реальные)
USER_MAPPING = {
    1389473957: 1  # Ваш Telegram ID и Bitrix ID
}

async def get_user_id_by_tg(tg_id: int) -> int | None:
    return USER_MAPPING.get(tg_id, None)

async def get_deals_for_user(user_id: int) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_DEAL_WEBHOOK_URL}crm.deal.list"
        params = {
            'filter': {'RESPONSIBLE_ID': user_id},
            'select': [
                'ID', 
                'TITLE', 
                'UF_CRM_1756190928',   # Адрес
                'CONTACT_ID',          # ID контакта
                'UF_CRM_1756191602',   # Вид техники
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