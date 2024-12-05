import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from .handlers import router


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")


dp = Dispatcher()

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

async def main():
    dp.include_router(router=router)
    await dp.start_polling(bot) 

