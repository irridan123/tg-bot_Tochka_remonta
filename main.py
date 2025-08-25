import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TELEGRAM_TOKEN
from handlers import setup_handlers

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    setup_handlers(dp)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())