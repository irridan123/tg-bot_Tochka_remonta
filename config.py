from dotenv import load_dotenv
import os

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BITRIX_DEAL_WEBHOOK_URL = os.getenv('BITRIX_DEAL_WEBHOOK_URL')  # Для crm.deal.list
BITRIX_CONTACT_WEBHOOK_URL = os.getenv('BITRIX_CONTACT_WEBHOOK_URL')  # Для crm.contact.get
BITRIX_DEAL_UPDATE_WEBHOOK_URL = os.getenv('BITRIX_DEAL_UPDATE_WEBHOOK_URL')  # Для crm.deal.update
BITRIX_USERFIELD_WEBHOOK_URL = os.getenv('BITRIX_USERFIELD_WEBHOOK_URL')  # Новый: Для crm.deal.userfield.get
MANAGER_TG_ID = int(os.getenv('MANAGER_TG_ID'))