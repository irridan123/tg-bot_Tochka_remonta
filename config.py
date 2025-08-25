from dotenv import load_dotenv
import os

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BITRIX_WEBHOOK_URL = os.getenv('BITRIX_WEBHOOK_URL')
MANAGER_TG_ID = int(os.getenv('MANAGER_TG_ID'))