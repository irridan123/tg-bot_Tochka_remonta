# Файл: config.py
# Изменения: Добавлен BITRIX_DISK_WEBHOOK_URL и новый BITRIX_FOLDER_ID для ID папки на диске Bitrix24,
# куда будут загружаться файлы. Добавьте BITRIX_FOLDER_ID в .env (получите ID папки через Bitrix API,
# например, методом disk.folder.get с фильтром по имени папки, если она общая/shared).
# Инструкция: Создайте общую папку в Bitrix24 Disk (например, "Курьерские файлы"), получите её ID
# через REST API (метод disk.folder.getchildren или вручную из URL), и добавьте в .env как BITRIX_FOLDER_ID=12345
from dotenv import load_dotenv
import os

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BITRIX_DEAL_WEBHOOK_URL = os.getenv('BITRIX_DEAL_WEBHOOK_URL')  # Для crm.deal.list
BITRIX_CONTACT_WEBHOOK_URL = os.getenv('BITRIX_CONTACT_WEBHOOK_URL')  # Для crm.contact.get
BITRIX_DEAL_UPDATE_WEBHOOK_URL = os.getenv('BITRIX_DEAL_UPDATE_WEBHOOK_URL')  # Для crm.deal.update
BITRIX_USERFIELD_WEBHOOK_URL = os.getenv('BITRIX_USERFIELD_WEBHOOK_URL')  # Для crm.deal.userfield.get
BITRIX_DISK_WEBHOOK_URL = os.getenv('BITRIX_DISK_WEBHOOK_URL')  # Для disk.folder.uploadfile
BITRIX_FOLDER_ID = int(os.getenv('BITRIX_FOLDER_ID'))  # Новый: ID папки для загрузки файлов (добавьте в .env)
MANAGER_TG_ID = int(os.getenv('MANAGER_TG_ID'))