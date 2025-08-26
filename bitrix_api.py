import aiohttp
from config import BITRIX_WEBHOOK_URL
import logging

# Маппинг: Telegram ID -> Bitrix User ID (обновите на ваши реальные)
USER_MAPPING = {
    1389473957: 1  # Ваш Telegram ID и Bitrix ID
}

async def get_user_id_by_tg(tg_id: int) -> int | None:
    return USER_MAPPING.get(tg_id, None)

async def get_deals_for_user(user_id: int) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_WEBHOOK_URL}crm.deal.list"
        params = {
            'filter': {'RESPONSIBLE_ID': user_id},
            'select': [
                'ID', 
                'TITLE', 
                'UF_CRM_1756190928',   # Замените на реальный код для адреса
                'CONTACT_ID',   # Для контактов
                'UF_CRM_1756191602',      # Для вида техники
                'UF_CRM_1756191922',     # Для марки/модели
                'UF_CRM_1756191987'  # Для даты доставки
            ]
        }
        try:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                logging.debug(f"Bitrix response: {data}")
                return data.get('result', [])
        except Exception as e:
            logging.error(f"Bitrix API error: {e}")
            return []

async def update_deal(deal_id: int, fields: dict):
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_WEBHOOK_URL}crm.deal.update"
        params = {'id': deal_id, 'fields': fields}  # Здесь fields вроде {'UF_CRM_XXXXXXXX_MODEL': 'New Model'}
        try:
            async with session.post(url, json=params) as resp:
                return await resp.json()
        except Exception as e:
            logging.error(f"Bitrix update error: {e}")
            return {}