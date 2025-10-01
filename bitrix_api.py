import aiohttp
import json
import os
from config import BITRIX_DEAL_WEBHOOK_URL, BITRIX_CONTACT_WEBHOOK_URL, BITRIX_DEAL_UPDATE_WEBHOOK_URL, BITRIX_USERFIELD_WEBHOOK_URL, BITRIX_DISK_WEBHOOK_URL, BITRIX_FOLDER_ID
import logging
import base64

USER_DATA_FILE = 'user_data.json'

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error in {USER_DATA_FILE}: {e}")
            return {}
        except Exception as e:
            logging.error(f"Error loading {USER_DATA_FILE}: {e}")
            return {}
    return {}

def save_user_data(user_data):
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(user_data, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving {USER_DATA_FILE}: {e}")

USER_DATA = load_user_data()

async def get_user_id_by_tg(tg_id: int) -> int | None:
    tg_str = str(tg_id)
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
        USER_DATA[tg_str] = {'bitrix_id': None, 'name': name}
    save_user_data(USER_DATA)

async def get_deals_for_user(user_id: int, branch: int) -> list[dict]:
    filter_params = {'UF_CRM_1756808838': user_id}
    if branch == 1:
        filter_params['UF_CRM_1756808681'] = None
        filter_params['STAGE_ID'] = 'UC_GDXHB8'
    elif branch == 2:
        filter_params['!UF_CRM_1756808681'] = None
        filter_params['STAGE_ID'] = 'UC_W02MYL'

    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_DEAL_WEBHOOK_URL}crm.deal.list"
        params = {
            'filter': filter_params,
            'select': [
                'ID',
                'TITLE',
                'UF_CRM_1747140776508',
                'CONTACT_ID',
                'UF_CRM_1747068372',
                'UF_CRM_1727124284490',
                'UF_CRM_1756808681',
                'OPPORTUNITY',
                'STAGE_ID',
                'UF_CRM_1758315289607'
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

async def get_deal_amount(deal_id: int) -> float:
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_DEAL_WEBHOOK_URL}crm.deal.get"
        params = {
            'id': deal_id,
            'select': ['OPPORTUNITY']
        }
        try:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                logging.debug(f"Bitrix deal get response: {data}")
                amount = data.get('result', {}).get('OPPORTUNITY', 0.0)
                return float(amount) if amount else 0.0
        except Exception as e:
            logging.error(f"Bitrix deal get error: {e}")
            return 0.0

async def get_deal_field(deal_id: int, field_name: str) -> list:
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_DEAL_WEBHOOK_URL}crm.deal.get"
        params = {
            'id': deal_id,
            'select': [field_name]
        }
        try:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                logging.debug(f"Bitrix deal field get response: {data}")
                value = data.get('result', {}).get('field_name', [])
                return value if isinstance(value, list) else [value] if value else []
        except Exception as e:
            logging.error(f"Bitrix deal field get error: {e}")
            return []

async def add_link_to_deal_field(deal_id: int, field_name: str, new_link: str):
    current_links = await get_deal_field(deal_id, field_name)
    current_links.append(new_link)
    fields = {field_name: current_links}
    await update_deal(deal_id, fields)

async def add_comment_to_deal(deal_id: int, comment: str):
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_DEAL_WEBHOOK_URL}crm.timeline.comment.add"
        params = {
            'fields': {
                'ENTITY_TYPE': 'deal',
                'ENTITY_ID': deal_id,
                'COMMENT': comment
            }
        }
        try:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                logging.debug(f"Bitrix comment add response: {data}")
                return data
        except Exception as e:
            logging.error(f"Bitrix comment add error: {e}")
            return {}

async def get_contact_data(contact_id: int) -> dict:
    if not contact_id:
        return {}
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_CONTACT_WEBHOOK_URL}crm.contact.get"
        params = {
            'id': contact_id,
            'select': ['NAME', 'SECOND_NAME', 'LAST_NAME', 'PHONE', 'EMAIL']
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
    if not value_id:
        return "Неизвестно"
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_USERFIELD_WEBHOOK_URL}crm.deal.userfield.list"
        params = {
            'filter': {'FIELD_NAME': field_code}
        }
        try:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                logging.debug(f"Bitrix userfield list response: {data}")
                fields = data.get('result', [])
                if not fields:
                    logging.debug(f"No fields found for code: {field_code}")
                    return value_id
                enum_list = fields[0].get('LIST', [])
                logging.debug(f"Enum list for field {field_code}: {enum_list}")
                for item in enum_list:
                    if item.get('ID') == value_id:
                        value_text = item.get('VALUE', value_id)
                        logging.debug(f"Found value: {value_text} for ID {value_id}")
                        return value_text
                logging.debug(f"No matching ID {value_id} in enum list")
                return value_id
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

async def upload_file_to_disk(folder_id: int, file_name: str, file_content: bytes) -> dict:
    base64_content = base64.b64encode(file_content).decode('utf-8')
    async with aiohttp.ClientSession() as session:
        url = f"{BITRIX_DISK_WEBHOOK_URL}disk.folder.uploadfile"
        params = {
            'id': folder_id,
            'data': {'NAME': file_name},
            'fileContent': [file_name, base64_content]
        }
        try:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                logging.debug(f"Bitrix disk upload response: {data}")
                return data
        except Exception as e:
            logging.error(f"Bitrix disk upload error: {e}")
            return {}