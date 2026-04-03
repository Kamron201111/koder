import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from database.models import init_db
from database.db import expire_premiums
from services.userbot import load_all
from handlers import start, account, settings, payment, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp  = Dispatcher(storage=MemoryStorage())

dp.include_router(start.router)
dp.include_router(account.router)
dp.include_router(settings.router)
dp.include_router(payment.router)
dp.include_router(admin.router)

async def premium_checker():
    while True:
        await asyncio.sleep(3600)
        n = await expire_premiums()
        if n:
            log.info(f"Premium: {n} ta muddati tugadi")

async def main():
    log.info("=" * 50)
    log.info("  ChatSpyer v2.0 — AI Avtonom Yordamchi")
    log.info("=" * 50)

    await init_db()
    log.info("✅ Database tayyor")

    n = await load_all()
    log.info(f"✅ {n} ta userbot yuklandi")

    asyncio.create_task(premium_checker())

    await bot.delete_webhook(drop_pending_updates=True)
    log.info("🚀 Bot ishga tushdi!")
    log.info("=" * 50)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
