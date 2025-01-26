# это главный файл в которой мы будем вызывать другие файлы
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher

from config import TOKEN # из файла config берём переменную TOKEN в ней записан токен нашего бота
from app.handlers import router # из handlers который находится в папке app мы импортируем router
from app.backup import on_startup
bot = Bot(token = TOKEN) # задаём значение токена в боте (этот токен получаем у fatherBot)
dp = Dispatcher() # это диспетчер работа происходит через него

async def main():
    await on_startup()
    dp.include_router(router) # теперь диспетчер выполняет работу router
    await dp.start_polling(bot) # если ответ есть от телеграмма, то бот будет работать

if __name__ == '__main__':
    try:
        print("Бот начал работу")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот завершил работу")
