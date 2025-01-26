from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder # импортируем билдер (Builder)
import sqlite3
# ReplyKeyboardMarkup, KeyboardButton для кнопок клавиатуры
# InlineKeyboardMarkup, InlineKeyboardButton для кнопок сообщения

from config import TOKEN,LOCATION_DB
from datetime import datetime as dt


async def convert_to_data(id_order: int, data: str,short_description: str):
    arr = []
    arr.append(id_order)
    date_object = dt.strptime(data, '%Y-%m-%d %H:%M')
    arr.append(date_object)
    arr.append(short_description)
    return arr

replay = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Ввести ещё раз', callback_data='replay')],
])

main_workers = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Заявки', callback_data='tasks')],
    [InlineKeyboardButton(text='Карта опор', url = 'https://mail.ru/')],
    [InlineKeyboardButton(text='Добавить новую опору', callback_data='new_support')],
])

main_manager = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='новое задание', callback_data='new_tasks')],
    [InlineKeyboardButton(text='Карта опор', url = 'https://mail.ru/')],
    [InlineKeyboardButton(text='просмотреть информацию об опоре', callback_data='viewing')],
    [InlineKeyboardButton(text='Добавить новую опору', callback_data='new_support')],
    [InlineKeyboardButton(text='Изменить данные об опоре', callback_data='change_support')],
])

main_admin = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='новое задание', callback_data='new_tasks')],
    [InlineKeyboardButton(text='Карта опор', url = 'https://mail.ru/')],
    [InlineKeyboardButton(text='просмотреть информацию об опоре', callback_data='viewing')],
    [InlineKeyboardButton(text='Добавить новую опору', callback_data='new_support')],
    [InlineKeyboardButton(text='Изменить данные об опоре', callback_data='change_support')],
    [InlineKeyboardButton(text='Панель администратора', callback_data='admin_panel')],
])

done_task = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Назад', callback_data='tasks')],
])


async def tasks_in_db(id_worker: int):
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT id_order,deadline,short_description FROM orders WHERE (id_worker = ? AND status IN (?,?))", (id_worker,'active','in_progress'))
    all_tasks = cursor.fetchall()
    connection.close()

    arr_norm_dates = []
    for tasks_one in all_tasks:
        arr_norm_dates.append(await convert_to_data(tasks_one[0],tasks_one[1],tasks_one[2]))

    sorted_data = sorted(arr_norm_dates, key=lambda item: item[1], reverse=True)

    keyboard = InlineKeyboardBuilder()
    count = len(sorted_data)
    for tasks_one in sorted_data:
        keyboard.add(InlineKeyboardButton(text = str(count)+ ' — ' + tasks_one[2], callback_data=f"tasks_{tasks_one[0]}"))
        count -= 1
    keyboard.add(InlineKeyboardButton(text='На главную', callback_data='to_main'))

    return keyboard.adjust(1).as_markup() # adjust(2) регулируем клавиатуру по ширине (в одном ряду может быть до 2 кнопок), as_markup() нужно использовать всегда когда мы используем Builder (это для превращения в клавиатуру)


async def task(id_order: int):
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT time_start FROM orders WHERE id_order = ?", (id_order,))
    result_from_db = cursor.fetchone()
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Информация о опоре', callback_data='infoSupport_' + str(id_order)))
    if result_from_db[0] == 'нет':
        keyboard.add(InlineKeyboardButton(text='Начать выполнение', callback_data='timeStart_' + str(id_order)))
    else:
        keyboard.add(InlineKeyboardButton(text='Закончить выполнение', callback_data='timeEnd_' + str(id_order)))
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data='tasks'))
    return keyboard.adjust(1).as_markup()

async def info_task(id_order: int):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Изменить информацию', callback_data='changeInfo_' + str(id_order))) # вылезут кнопки с выбором чего изменить
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data='backInTask_' + str(id_order)))
    return keyboard.adjust(1).as_markup()

async def changeInfo(id_support: int,id_order: int, role: str):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Фото', callback_data='changePhoto_' + str(id_support) + '_' + str(id_order)))
    keyboard.add(InlineKeyboardButton(text='Количество оптики', callback_data='changeCountOptics_' + str(id_support)+ '_' + str(id_order)))
    keyboard.add(InlineKeyboardButton(text='Незаконные подключения', callback_data='changeIllegalConnections_' + str(id_support)+ '_' + str(id_order)))
    if role == 'worker':
        keyboard.add(InlineKeyboardButton(text='Назад', callback_data='infoSupport_' + str(id_order)))
    elif role == 'manager':
        keyboard.add(InlineKeyboardButton(text='Назад', callback_data='to_main_manager' ))
    else:
        keyboard.add(InlineKeyboardButton(text='Назад', callback_data='to_main_admin'))
    return keyboard.adjust(1).as_markup()

async def back_change_info(id_order: int):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='Назад', callback_data='changeInfo_' + str(id_order)))
    return keyboard.adjust(1).as_markup()

