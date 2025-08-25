import aiohttp
from config import BITRIX_WEBHOOK_URL

# Тестовый маппинг: Telegram ID -> Bitrix User ID (замените на реальные)
USER_MAPPING = {
    1389473957: 1  # Пример: ваш Telegram ID и Bitrix ID
}

async def get_user_id_by_tg(tg_id: int) -> int | None:
    return USER_MAPPING.get(tg_id, None)

async def get_deals_for_user(user_id: int) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_WEBHOOK_URL}crm.deal.list"
        params = {
            'filter': {'RESPONSIBLE_ID': user_id},
            'select': ['ID', 'TITLE', 'UF_ADDRESS', 'UF_CONTACT', 'UF_TYPE', 'UF_MODEL', 'UF_DELIVERY_DATE']
        }
        async with session.post(url, json=params) as resp:
            data = await resp.json()
            return data.get('result', [])

async def update_deal(deal_id: int, fields: dict):
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_WEBHOOK_URL}crm.deal.update"
        params = {'id': deal_id, 'fields': fields}
        async with session.post(url, json=params) as resp:
            return await resp.json()