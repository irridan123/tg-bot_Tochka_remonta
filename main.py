import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import ClientTimeout
from config import TELEGRAM_TOKEN
from handlers import setup_handlers
from aiogram.exceptions import TelegramNetworkError
import time

# Включаем детальное логирование для отладки
logging.basicConfig(level=logging.DEBUG)

async def main():
    # Создаём Bot с увеличенным timeout для сетевых проблем
    bot = Bot(token=TELEGRAM_TOKEN, timeout=ClientTimeout(total=60))
    dp = Dispatcher(storage=MemoryStorage())
    setup_handlers(dp)
    
    # Запускаем polling с retry на network errors
    while True:
        try:
            logging.info("Starting polling...")
            await dp.start_polling(bot)
        except TelegramNetworkError as e:
            logging.error(f"Network error: {e}. Retrying in 5 seconds...")
            time.sleep(5)  # Retry после паузы
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            break

if __name__ == '__main__':
    asyncio.run(main())