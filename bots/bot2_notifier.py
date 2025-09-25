import asyncio
import datetime as dt
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from shared.config import get_settings
from shared.password import derive_password, hour_floor_utc

settings = get_settings()
bot = Bot(settings.BOT2_TOKEN)

async def send_password_update():
    now = hour_floor_utc(dt.datetime.utcnow())
    pwd = derive_password(settings.PASSWORD_SECRET, now)
    text = f"Пароль обновлен ! - Новый пароль: {pwd}"
    await bot.send_message(chat_id=settings.ADMIN_CHAT_ID, text=text)

def setup_scheduler():
    sched = AsyncIOScheduler(timezone="UTC")
    # Ежечасно, в начале часа
    sched.add_job(send_password_update, "cron", minute=0)
    # Одноразово при старте — на случай рестартов
    sched.add_job(send_password_update, "date", run_date=dt.datetime.utcnow())
    sched.start()
    return sched

async def main():
    setup_scheduler()
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())