from gc import callbacks
import os
import sqlite3
import datetime as dt
import random

from aiogram import F,Bot, Router # F добавляет обработчик на сообщения от пользователя (он будет принимать всё (картинки, стикеры, контакты))
from aiogram.filters import CommandStart, Command # CommandStart добавляет команду '/start'   Command добавляет команду которую мы сами можем придумать (ниже есть пример)
from aiogram.types import Message, FSInputFile
from aiogram.types import Message, CallbackQuery
from aiogram import types
from aiogram.types import InputFile
from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext # для управления состояниями
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

import app.keyboards as kb # импортируем клавиатуру и сокращаем её на 'kb'
from aiohttp.abc import AbstractStreamWriter
from pyexpat.errors import messages
from io import BytesIO
from config import TOKEN,LOCATION_DB

last_messages= {}

bot = Bot(token = TOKEN)
router = Router() # это почти как диспетчер только для handlers

class Form(StatesGroup): # этот класс хранит в себе ответ пользователя на запрос ввести канал дял парсинга
    answer_code = State()
    waiting_for_photo = State()


async def get_info_order(id_order: int):
    info = ''
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT time_start, deadline,status, description,time_end,id_support,report  FROM orders WHERE id_order = ?", (id_order,))
    result_from_db = cursor.fetchone()
    connection.close()
    state_order = ''
    if result_from_db[2] == 'active':
        state_order = 'не начато'
    elif result_from_db[2] == 'in_progress':
        state_order = 'в процессе'
    else:
        state_order = 'выполнен'
    info = f'id опоры: {result_from_db[5]}\nid заявки: {id_order}\nДата начала: {result_from_db[0]}\nДата окончания: {result_from_db[4]}\nНеобходимая Дата сдачи: {result_from_db[1]}\nОтчёт: {result_from_db[6]}\nСтатус: {state_order}\n\nОписание: {result_from_db[3]}'
    return info

async def get_info_support(id_support: int):
    info = ''
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(
        f"SELECT id_support, adress,emergency,photo,count_of_optics,id_last_use_workers,illegal_connections,id_connection_supports_array,coordinates  FROM support WHERE id_support = ?",(id_support,))
    from_db = cursor.fetchone()
    connection.close()
    state_order = ''
    emergency = 'нет' # аварийное ли
    illegal_connections = 'нет'
    if from_db[4] > 5:
        emergency = 'да'
    if from_db[6] == 1:
        illegal_connections = 'имеются'

    info = f'id опоры: {from_db[0]}\nАдрес: {from_db[1]}\nКоординаты: {from_db[8]}\nАварийное: {emergency}\nКоличество оптики: {from_db[4]}\nid последнего сотрудника который с ним взаимодействовал: {from_db[5]}\nНелегальные подключения: {illegal_connections}\n\nid сетей которые подключены к ней: {from_db[7]}'
    return info

async def delete_last_message(user_id,chat_id):
    if user_id in last_messages:
        try:
            message_id = last_messages[user_id]
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            del last_messages[user_id] # Удаляем message_id из словаря, так как сообщение уже удалено
        except Exception:
            pass

@router.message(CommandStart()) # этот handler выполняется только при отправки команды старт (/start), ниже действия которые произойдут после вхождения в этот handler
async  def cmd_start(message: Message, state: FSMContext): # принимает сообщение от пользователя это асинхронная функция будет выполнена как только мы войдём в этот handler
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM workers WHERE id_tg = ?", (message.from_user.id,))
    worker_in_db = cursor.fetchone()[0]
    if worker_in_db > 0:
        cursor.execute(f"SELECT FIO,role,ID FROM workers WHERE id_tg = ?", (message.from_user.id,))
        result_from_db = cursor.fetchone()
        if result_from_db[1] == 'worker':
            cursor.execute(f"SELECT COUNT(*) FROM orders WHERE (id_worker = ? AND status IN (?,?))",(result_from_db[2], 'active','in_progress'))
            tasks = cursor.fetchone()[0]
            await message.answer(f'Здравствуйте <b>{result_from_db[0]}</b>!\nВаша роль: <b>Рабочий</b>\n\nКоличество задач: <b>{tasks}</b>',parse_mode='HTML', reply_markup=kb.main_workers)
        elif result_from_db[1] == 'manager':
            await message.answer(f'Здравствуйте <b>{result_from_db[0]}</b>!\nВаша роль: <b>Менеджер</b>',parse_mode='HTML', reply_markup=kb.main_manager)
        elif result_from_db[1] == 'admin':
            await message.answer(f'Здравствуйте <b>{result_from_db[0]}</b>!\nВаша роль: <b>Админ</b>',parse_mode='HTML', reply_markup=kb.main_admin)
    else:
        await state.set_state(Form.answer_code)  # устанавливаем состояние ожидания ответа
        await message.answer(f'Здравствуйте!\nВведи ваш код доступа:')
    connection.close()


@router.message(Form.answer_code)
async def answer_code(message: types.Message, state: FSMContext):  # принимаем сообщение от пользователя
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT ID,id_tg,FIO,role FROM workers WHERE code = ?",(message.text,))
    result_from_db = cursor.fetchone()
    if result_from_db: # если ввели правильный ключ
        if result_from_db[1] != 0: # если есть такой id в БД (запись активирована)
            await message.answer(f'Внимание!\n\nДанный ключ уже активирован\nЕсли это были не вы, то обратитесь к администратору!\nМожете ещё раз ввести код доступа', parse_mode='HTML')
        else: # если всё норм
            await state.clear() #
            if result_from_db[3] == 'worker':
                cursor.execute(f"SELECT COUNT(*) FROM orders WHERE (id_worker = ? AND status IN (?,?))",(result_from_db[0], 'active','in_progress'))
                tasks = cursor.fetchone()[0]
                await message.answer(f'Здравствуйте <b>{result_from_db[2]}</b>!\nВаша роль: <b>Рабочий</b>\n\nКоличество заявок: <b>{tasks}</b>',parse_mode='HTML', reply_markup=kb.main_workers)
            elif result_from_db[3] == 'manager':
                await message.answer(f'Здравствуйте <b>{result_from_db[2]}</b>!\nВаша роль: <b>Менеджер</b>', parse_mode='HTML', reply_markup=kb.main_manager)
            elif result_from_db[3] == 'admin':
                await message.answer(f'Здравствуйте <b>{result_from_db[2]}</b>!\nВаша роль: <b>Админ</b>', parse_mode='HTML', reply_markup=kb.main_admin)
            cursor.execute(f"UPDATE workers SET id_tg = ?  WHERE code = ?",(message.from_user.id, message.text))
            connection.commit()  # сохранение
    else:
        await message.answer(f'Введён неверный код доступа\n попробуйте ещё раз')
        await state.set_state(Form.answer_code)
    connection.close()

@router.callback_query(F.data == 'to_main')
async def to_main(callback: CallbackQuery, state: FSMContext):
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT FIO,role,ID FROM workers WHERE id_tg = ?", (callback.from_user.id,))
    result_from_db = cursor.fetchone()
    if result_from_db[1] == 'worker':
        cursor.execute(f"SELECT COUNT(*) FROM orders WHERE (id_worker = ? AND status IN (?,?))",(result_from_db[2], 'active', 'in_progress'))
        tasks = cursor.fetchone()[0]
        await callback.message.edit_text(f'Здравствуйте <b>{result_from_db[0]}</b>!\nВаша роль: <b>Рабочий</b>\n\nКоличество заявок: <b>{tasks}</b>',parse_mode='HTML', reply_markup=kb.main_workers)
    elif result_from_db[1] == 'manager':
        await callback.message.edit_text(f'Здравствуйте <b>{result_from_db[0]}</b>!\nВаша роль: <b>Менеджер</b>', parse_mode='HTML',reply_markup=kb.main_manager)
    elif result_from_db[1] == 'admin':
        await callback.message.edit_text(f'Здравствуйте <b>{result_from_db[0]}</b>!\nВаша роль: <b>Админ</b>', parse_mode='HTML',reply_markup=kb.main_admin)
    connection.close()

@router.callback_query(F.data == 'tasks')
async def tasks(callback: CallbackQuery, state: FSMContext):
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT ID FROM workers WHERE id_tg = ?", (callback.from_user.id,))
    result_from_db = cursor.fetchone()
    cursor.execute(f"SELECT COUNT(*) FROM orders WHERE (id_worker = ? AND status IN (?,?))",(result_from_db[0], 'active', 'in_progress'))
    tasks = cursor.fetchone()[0]
    if tasks == 0:
        await callback.message.edit_text(f'Все задачи выполнены!', reply_markup= await kb.tasks_in_db(result_from_db[0]))
    else:
        await callback.message.edit_text(f'Выберите одну из задач для её подробного описания', reply_markup= await kb.tasks_in_db(result_from_db[0]))
    connection.close()

@router.callback_query(F.data.startswith('tasks_')) # ловим callback_query который начинается с tasks_   (startswith это использовании метода который вернёт True если значение начинается с переданной строки)
async def category(callback: CallbackQuery):
    id_order = callback.data.split('_')[1]
    sent_message = await callback.message.edit_text(await get_info_order(int(id_order)), reply_markup=await kb.task(int(id_order)))
    last_messages[callback.from_user.id] = sent_message.message_id  # Сохраняем message_id в словаре

@router.callback_query(F.data.startswith('timeStart_')) # ловим callback_query который начинается с tasks_   (startswith это использовании метода который вернёт True если значение начинается с переданной строки)
async def time_start(callback: CallbackQuery):
    id_order = callback.data.split('_')[1]
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"UPDATE orders SET time_start = ?, status = ?  WHERE id_order = ?",(dt.datetime.now().strftime("%Y-%m-%d %H:%M"),'in_progress',id_order))
    connection.commit()  # сохранение
    cursor.execute(f"SELECT id_worker,id_support FROM orders WHERE id_order = ?", (id_order,))
    id_from_db = cursor.fetchone()
    cursor.execute(f"UPDATE support SET id_last_use_workers = ?  WHERE id_support = ?",(id_from_db[0], id_from_db[1]))
    connection.commit()  # сохранение
    connection.close()
    await callback.message.edit_text(await get_info_order(int(id_order)), reply_markup=await kb.task(int(id_order)))

@router.callback_query(F.data.startswith('timeEnd_')) # ловим callback_query который начинается с tasks_   (startswith это использовании метода который вернёт True если значение начинается с переданной строки)
async def time_start(callback: CallbackQuery):
    id_order = callback.data.split('_')[1]
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"UPDATE orders SET time_end = ?, status = ?  WHERE id_order = ?",(dt.datetime.now().strftime("%Y-%m-%d %H:%M"),'done',id_order))
    connection.commit()  # сохранение
    connection.close()
    await callback.message.edit_text(f'Заявка успешно завершена!\n\n' + await get_info_order(int(id_order)), reply_markup= kb.done_task)

@router.callback_query(F.data.startswith('infoSupport_'))
async def infoSupport(callback: CallbackQuery):
    await delete_last_message(callback.from_user.id,callback.message.chat.id)
    id_order = callback.data.split('_')[1]
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT id_support FROM orders WHERE id_order = ?", (id_order,))
    id_from_db = cursor.fetchone()

    cursor.execute(f"SELECT photo FROM support WHERE id_support = ?", (id_from_db[0],))
    photo_from_db = cursor.fetchone()
    connection.close()
    file_tols = 'resours\\'+str(callback.from_user.id)+'.png'
    with open(file_tols, "wb") as file:  # Путь, по которому хотите сохранить файл
        file.write(photo_from_db[0])  # Записываем извлеченные байты в файл
        file.close()

    sent_message = await callback.message.answer_photo(FSInputFile(file_tols),caption = await get_info_support(int(id_from_db[0])),reply_markup=await kb.info_task(int(id_order)))
    os.remove(file_tols)

    last_messages[callback.from_user.id] = sent_message.message_id # Сохраняем message_id в словаре

@router.callback_query(F.data.startswith('backInTask_'))
async def backInTask(callback: CallbackQuery):
    await delete_last_message(callback.from_user.id, callback.message.chat.id)
    id_order = callback.data.split('_')[1]
    sent_message = await callback.message.answer(await get_info_order(int(id_order)), reply_markup=await kb.task(int(id_order)))
    last_messages[callback.from_user.id] = sent_message.message_id

@router.callback_query(F.data.startswith('changeInfo_'))
async def changeInfo(callback: CallbackQuery,state: FSMContext):
    await state.clear()
    await delete_last_message(callback.from_user.id, callback.message.chat.id)
    id_order = callback.data.split('_')[1]
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT id_support,id_worker FROM orders WHERE id_order = ?", (id_order,))
    id_support_from_db = cursor.fetchone()
    cursor.execute(f"SELECT role FROM workers WHERE ID = ?", (id_support_from_db[1],))
    role_from_db = cursor.fetchone()
    sent_message = await callback.message.answer('Выберите категорию для изменения',reply_markup=await kb.changeInfo(id_support_from_db[0],int(id_order),role_from_db[0]))
    last_messages[callback.from_user.id] = sent_message.message_id


@router.callback_query(F.data.startswith('changePhoto_'))
async def changeInfo(callback: CallbackQuery, state: FSMContext):
    id_support = callback.data.split('_')[1]
    id_order = callback.data.split('_')[2]
    await state.set_state(Form.waiting_for_photo)
    await state.update_data(id_order=id_order)
    sent_message = await callback.message.edit_text(f'Можете присылать фото:', reply_markup = await kb.back_change_info(int(id_order)))
    last_messages[callback.from_user.id] = sent_message.message_id

@router.message(Form.waiting_for_photo)
async def answer_code(message: types.Message, state: Form.waiting_for_photo):
    await delete_last_message(message.from_user.id, message.chat.id)
    user_data = await state.get_data() # словарь который хранит id_order

    try:
        photo_id = message.photo[-1].file_id  # Берем наибольшее качество
    except TypeError:
        sent_message = await message.answer("отошлите фото, а не документ!",reply_markup=await kb.back_change_info(int(user_data['id_order'])))
        last_messages[message.from_user.id] = sent_message.message_id
        return
    file = await bot.get_file(photo_id)

    photo_data = await bot.download_file(file.file_path)
    connection = sqlite3.connect(LOCATION_DB)
    cursor = connection.cursor()
    cursor.execute(f"SELECT id_support FROM orders WHERE id_order = ?",(int(user_data['id_order']),))
    id_support_from_db = cursor.fetchone()
    cursor.execute('UPDATE support SET photo = ? WHERE id_support = ?', (photo_data.getvalue(),id_support_from_db[0]))
    connection.commit()
    connection.close()

    sent_message = await message.answer("Фото успешно сохранено!",reply_markup = await kb.back_change_info(int(user_data['id_order'])))
    await state.clear()
    last_messages[message.from_user.id] = sent_message.message_id








