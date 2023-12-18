"""Main Module"""
import asyncio
import datetime
import json
import threading
from random import choice
from string import ascii_letters

#import pandas
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardRemove)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.utils.markdown import hbold, hitalic, hlink

import config
import google_api
import sleep
from database import database as base
from trans_company.cdek import CDEK, Contact, Order
from trans_company.kit import KIT
from payments import command_buy_handler

dp = Dispatcher()
bot = Bot(config.TOKEN, parse_mode=ParseMode.HTML)

choise_user = {515551867: {}, 5776722082: {'company' : 'Кит'}}
user_log = {5776722082: 'city'}

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(config.START_MES, reply_markup=await create_btn('start', None, message.from_user.id))
    await sleeps(message.from_user.id)

@dp.message(F.contact)
async def contact(message: Message):
    choise_user[message.from_user.id]['phone'] = message.contact.phone_number
    text = "Напишите свое ФИО полностью"
    user_log[message.from_user.id] = 'Name'
    await message.answer(text, reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == 'Загрузить')
async def download_price(message: Message):
    await google_api.get_price()
    await message.reply("Успешно!")

@dp.message()
async def download_file(message: Message):
    if message.from_user.id == message.chat.id:
        if user_log[message.from_user.id] == 'Name':
            mes = await message.answer(text="Ожидайте, создаем необходимые документы")
            id_base = ''.join(choice(ascii_letters) for i in range(15))
            choise_user[message.from_user.id]['base_id'] = id_base
            choise_user[message.from_user.id]['name'] = message.text
            text = 'Спасибо! Ваш заказ принят. Ожидайте, в ближайшее время с вами свяжется менеджер по поводу оплаты.'
            await base.insert_finals(choise_user[message.from_user.id], message.from_user.id)

            price_delivery = None
            select = await base.get_final(id_base)
            orders_id = select['orders_id'].split(', ')
            mas_orders = []
            for order_id in orders_id:
                if not order_id == '':
                    order = await base.get_order_id(order_id)
                    mas_char = await base.find_weight_dia(order['color'],
                                                    order['width'], order['lenght'], order['category'])
                    mas_orders.append({
                        'order_id' : order_id,
                        'category' : order['category'],
                        'color' : order['color'],
                        'width' : order['width'],
                        'lenght' : order['lenght'],
                        'count' : order['count'],
                        'cost' : order['cost'],
                        'weight' : mas_char[0],
                        'diametr' : mas_char[1],
                        'lenght_rul' : mas_char[2]
                    })
            #CDEK
            if choise_user[message.from_user.id]['company'] == 'Сдек':
                try:
                    file_name = CDEK(choise_user[message.from_user.id]['city'],
                                    Order(
                                        Contact(select['phone'], select['name'], select['address'], choise_user[message.from_user.id]['city']),
                                            select['delivery_type'], select['final_id'], select['order_type']),
                                                mas_orders).create_order()
                except:
                    file_name = None
                if file_name == None:
                    text = "К сожалению накладная СДЕК не создалась автоматически. Ожидайте, в ближайшее время с вами свяжется менеджер"
                else:
                    await message.answer_document(document=FSInputFile(file_name))
                    await bot.send_document(chat_id=config.GROUP_ID, document=FSInputFile(file_name))
            elif choise_user[message.from_user.id]['company'] == 'Кит':
                try:
                    order_info = KIT(choise_user[message.from_user.id]['city'],
                                    Order(
                                        Contact(select['phone'], select['name'], select['address'], choise_user[message.from_user.id]['city']),
                                            select['delivery_type'], select['final_id'], select['order_type']),
                                                mas_orders).create_order()
                except:
                    order_info = None
                if order_info == None:
                    text = "К сожалению накладная КИТ не создалась автоматически. Ожидайте, в ближайшее время с вами свяжется менеджер"
                else:
                    #await message.answer_document(document=FSInputFile(file_name))
                    await bot.send_document(chat_id=config.GROUP_ID, document=FSInputFile(order_info['file_name']))
                    text += f"\nТрек-номер: {order_info['cargo_number']}\nСтоимость доставки: {order_info['price']} руб."
                    price_delivery = order_info['price']

            user_log[message.from_user.id] = ''
            # Добавка в БД
            if select['order_type'] == 'Самовывоз':
                contacts = await google_api.get_contacts(select['city'])
                text += f'\n{hbold("Адрес для получения")}: {contacts["address"]}'
                text += f'\n{hbold("Контакт")}: {contacts["contact"]}'
            await bot.edit_message_text(text=text, chat_id=message.from_user.id, message_id=mes.message_id, reply_markup=await create_btn('start', None, message.from_user.id))
            #await message.answer(text, reply_markup=await create_btn('start', None, message.from_user.id))
            await send_to_group(id_base, price_delivery)
            await remove_user(str(message.from_user.id))
            await command_buy_handler(message, bot, select['cost'])

        elif user_log[message.from_user.id] == 'phone':
            choise_user[message.from_user.id]['phone'] = message.text
            text = "Напишите свое ФИО полностью"
            user_log[message.from_user.id] = 'Name'
            await message.answer(text, reply_markup=ReplyKeyboardRemove())

        elif user_log[message.from_user.id] == 'count':
            try:
                count = float(message.text)
                if count > 1000:
                    await message.reply('Слишком большое значение!')
                else:
                    choise_user[message.from_user.id]['count'] = count
                    choise_user[message.from_user.id]['user_id'] = message.from_user.id
                    id_base = ''.join(choice(ascii_letters) for i in range(15))
                    choise_user[message.from_user.id]['base_id'] = id_base
                    choise_user[message.from_user.id]['user_name'] = message.from_user.username

                    # расчитать стоимость
                    price = await base.find_price(choise_user[message.from_user.id])
                    cost = round(count * price[0], 3)
                    if cost >= 50000:
                        cost = round(count * price[1], 3)
                    if cost >= 500000:
                        cost = round(count * price[2], 3)
                    choise_user[message.from_user.id]['cost'] = cost
                    await base.insert_order(choise_user[message.from_user.id])
                    category = await base.get_category(choise_user[message.from_user.id]['category'])
                    text = f'{hbold("Выбрано:")}\n\nКатегория: {hitalic(category)}\n'
                    text += f'Цвет: {hitalic(choise_user[message.from_user.id]["color"])}\n'
                    text += f'Ширина: {hitalic(choise_user[message.from_user.id]["width"])}\n'
                    text += f'Длина: {hitalic(choise_user[message.from_user.id]["length"])}\n'
                    text += f'Кол-во: {hitalic(choise_user[message.from_user.id]["count"])}\n'
                    text += f'Стоимость: {hitalic(choise_user[message.from_user.id]["cost"])} руб.'
                    builder = InlineKeyboardBuilder()
                    builder.button(text='Удалить', callback_data=f'delete /-p {id_base}')
                    await message.delete()
                    await message.answer(text, reply_markup=builder.as_markup())
                    data = 'add_product'
                    select = await base.get_algo_pred(data)
                    await message.answer(text=select[0][1], reply_markup=await create_btn(data, None, message.from_user.id))
                    user_log[message.from_user.id] = 'stat'
            except:
                await message.reply('Ошибка ввода!\nВведите число')
            pass

        elif user_log[message.from_user.id] == 'city':
            city = message.text
            if choise_user[message.from_user.id]['company'] == 'Сдек':
                check = CDEK(city, None, None).check_city()
                if check:
                    choise_user[message.from_user.id]['city'] = city
                    data = 'city'
                    select = await base.get_algo_pred(data)
                    await message.answer(text=select[0][1], reply_markup=await create_btn(data, None, message.from_user.id))
                    user_log[message.from_user.id] = ''
                else:
                    text = 'Город не найден в базе СДЕК\nНапишите полностью свой город без ошибок'
                    data = 'TK'
                    await message.answer(text, reply_markup=await create_btn(data, 'Сдек', message.from_user.id))
            elif choise_user[message.from_user.id]['company'] == 'Кит':
                check = KIT(city, None, None).check_city()
                if check:
                    choise_user[message.from_user.id]['city'] = city
                    data = 'city'
                    select = await base.get_algo_pred(data)
                    await message.answer(text=select[0][1], reply_markup=await create_btn(data, None, message.from_user.id))
                    user_log[message.from_user.id] = ''
                else:
                    text = 'Город не найден в базе КИТ\nНапишите полностью свой город без ошибок'
                    data = 'TK'
                    await message.answer(text, reply_markup=await create_btn(data, 'Кит', message.from_user.id))
            else:
                choise_user[message.from_user.id]['city'] = city
                data = 'city'
                select = await base.get_algo_pred(data)
                await message.answer(text=select[0][1], reply_markup=await create_btn(data, None, message.from_user.id))
                user_log[message.from_user.id] = ''

        elif user_log[message.from_user.id] == 'checkout a a':
            choise_user[message.from_user.id]['type_del'] = "Доставка"
            choise_user[message.from_user.id]['address'] = message.text
            choise_user[message.from_user.id]['delivery_type'] = "Самовывоз из пункта"
            user_log[message.from_user.id] = ''
            await message.answer("Отправьте свой номер телефона (Нажмите на кнопку 'Отправить телефон' или напишите номер в формате 79994443322)", reply_markup=await btn_contact())
            user_log[message.from_user.id] = 'phone'
            # Продолжить

        elif user_log[message.from_user.id] == 'checkout a b':
            choise_user[message.from_user.id]['type_del'] = "Доставка"
            choise_user[message.from_user.id]['address'] = message.text
            choise_user[message.from_user.id]['delivery_type'] = "Доставка до двери"
            user_log[message.from_user.id] = ''
            await message.answer("Отправьте свой номер телефона (Нажмите на кнопку 'Отправить телефон' или напишите номер в формате 79994443322)", reply_markup=await btn_contact())
            user_log[message.from_user.id] = 'phone'
            # Продолжить

@dp.callback_query(F.data == '0')
async def call_section(callback: types.CallbackQuery):
    sections = await base.get_unique_section()
    builder = InlineKeyboardBuilder()
    for section in sections:
        builder.button(text=section[0], callback_data=f"sec_{section[0]}")
    builder.button(text='Назад', callback_data="start")
    builder.adjust(1)
    await callback.message.edit_text('Выберите направление', reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("sec_"))
async def call_section(callback: types.CallbackQuery):
    section = callback.data.replace("sec_", "")
    choise_user[callback.from_user.id] = {'section' : section}
    categories = await base.get_section_category(section)
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=category[1], callback_data=f"cat_{category[0]}")
    builder.button(text='Назад', callback_data="0")
    builder.adjust(1)
    await callback.message.edit_text('Выберите направление', reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("cat_"))
async def call_section(callback: types.CallbackQuery):
    category = callback.data.replace("cat_", "")
    choise_user[callback.from_user.id]['category'] = category
    colors = await base.find_color(category)
    builder = InlineKeyboardBuilder()
    for color in colors:
        builder.button(text=color, callback_data=f"color /-p {color}")
    builder.button(text='Назад', callback_data=f"sec_{choise_user[callback.from_user.id]['section']}")
    builder.adjust(1)
    photo_path = f'jpg/{category}.jpg'
    await callback.message.delete()
    try:
        await callback.message.answer_photo(photo=FSInputFile(photo_path))
    except:
        pass

    await callback.message.answer("Выберите цвет", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("color_"))
async def call_section(callback: types.CallbackQuery):
    category = callback.data.replace("color_", "")
    colors = await base.find_color(category)
    builder = InlineKeyboardBuilder()
    for color in colors:
        builder.button(text=color, callback_data=f"color /-p {color}")
    builder.button(text='Назад', callback_data=f"sec_{choise_user[callback.from_user.id]['section']}")
    builder.adjust(1)
    await callback.message.edit_text("Выберите цвет", reply_markup=builder.as_markup())

@dp.callback_query()
async def callbacks_num(callback: types.CallbackQuery):
    data = callback.data
    text = None
    photo = False
    if data == 'show':
        await send_orders_user(callback.from_user.id)
        data = 'start'
        photo = True
        await callback.message.delete()

    if ' /-p 'in data:
        data = data.split(' /-p ')
        text = data[1]
        data = data[0]

    if data == 're-pay':
        select = await base.get_final(text)
        base_id = ''.join(choice(ascii_letters) for i in range(15))
        choise_user[callback.from_user.id] = {
            "base_id" : base_id,
            "type_del" : "Повтор",
            "select" : select
        }
        await base.insert_finals(choise_user[callback.from_user.id], callback.from_user.id)
        await callback.message.answer("Заказ успешно повторен!", reply_markup=await create_btn('start', None, callback.from_user.id))
        await send_to_group(base_id)

    elif data == 'count':
        user_log[callback.from_user.id] = 'count'
        await callback.message.delete()
        await callback.message.answer('Напишите необходимое количество', reply_markup=await create_btn(data, text, callback.from_user.id))

    elif data == 'delete':
        if user_log[callback.from_user.id] == 'stat':
            await base.delete_order(text)
            await callback.message.delete()
        else:
            pass

    elif data == 'add_product':
        user_log[callback.from_user.id] = 'stat'

    elif data == 'checkout a a':
        if choise_user[callback.from_user.id]['company'] == 'Сдек':
            mas_orders = []
            orders_id = await base.get_orsers_prepare_user(callback.from_user.id)
            for order_id in orders_id:
                order = await base.get_order_id(order_id[0])
                mas_char = await base.find_weight_dia(order['color'],
                                             order['width'], order['lenght'], order['category'])
                mas_orders.append({
                    'order_id' : order_id,
                    'category' : order['category'],
                    'color' : order['color'],
                    'width' : order['width'],
                    'lenght' : order['lenght'],
                    'count' : order['count'],
                    'cost' : order['cost'],
                    'weight' : mas_char[0],
                    'diametr' : mas_char[1],
                    'lenght_rul' : mas_char[2]
                })

            mas_pvz = CDEK(choise_user[callback.from_user.id]['city'], None, mas_orders).find_pvz_to_bot()
            if len(mas_pvz) > 0 and len(mas_pvz) <= 32:
                index = 1
                builder = InlineKeyboardBuilder()
                text_mes = 'Нажав на адрес - вы можете увидеть расположение пункта самовывоза на карте.\nДля выбора - нажмите номер пункта в меню.\n'
                for pvz in mas_pvz:
                    link_yandex = f"https://yandex.ru/maps/?ll={pvz['x']},{pvz['y']}&z=18&text=CDEK"
                    text_link = f"{hlink(title=pvz['address'], url=link_yandex)}"
                    if 'nearest_metro_station' in pvz:
                        text_mes += f"{hbold(index)}) {text_link} ({pvz['nearest_metro_station']})\n"
                    else:
                        text_mes += f"{hbold(index)}) {text_link}\n"

                    builder.button(text=f"{index}", callback_data=f"pvzCDEK /-p {pvz['code']}")
                    index += 1
                builder.button(text='Назад', callback_data='city')
                builder.adjust(4)
                await callback.message.edit_text(text=text_mes, reply_markup=builder.as_markup(), disable_web_page_preview=True)
                return
            elif len(mas_pvz) > 32:
                len_pvz = len(mas_pvz)
                if text == '0':
                    text = None
                if text is None:
                    mas_pvz = mas_pvz[:32]
                    index = 1
                else:
                    count = int(text)
                    index = count + 1
                    mas_pvz = mas_pvz[count:count+32]

                builder = InlineKeyboardBuilder()
                text_mes = 'Нажав на адрес - вы можете увидеть расположение пункта самовывоза на карте.\nДля выбора - нажмите номер пункта в меню.\n'
                for pvz in mas_pvz:
                    link_yandex = f"https://yandex.ru/maps/?ll={pvz['x']},{pvz['y']}&z=18&text=CDEK"
                    text_link = f"{hlink(title=pvz['address'], url=link_yandex)}"
                    if 'nearest_metro_station' in pvz:
                        text_mes += f"{hbold(index)}) {text_link} ({pvz['nearest_metro_station']})\n"
                    else:
                        text_mes += f"{hbold(index)}) {text_link}\n"

                    builder.button(text=f"{index}", callback_data=f"pvzCDEK /-p {pvz['code']}")
                    index += 1

                if text is None:
                    builder.button(text='Назад', callback_data='city')
                    builder.button(text='->', callback_data='checkout a a /-p 32')
                else:

                    builder.button(text='<-', callback_data=f'checkout a a /-p {count-32}')
                    builder.button(text='Назад', callback_data='city')
                    if count + 32 < len_pvz:
                        builder.button(text='->', callback_data=f'checkout a a /-p {count+32}')


                builder.adjust(4)
                await callback.message.edit_text(text=text_mes, reply_markup=builder.as_markup(), disable_web_page_preview=True)
                return

            else:
                text = 'В вашем городе не найдено подходящих пунктов самовывоза, измените город или способ доставки'
                data = 'TK'
                await callback.message.edit_text(text, reply_markup=await create_btn(data, 'Сдек', callback.from_user.id))
                return

        elif choise_user[callback.from_user.id]['company'] == 'Кит':
            pass

    elif data == 'pvzCDEK':
        choise_user[callback.from_user.id]['address'] = text
        choise_user[callback.from_user.id]['type_del'] = "Доставка"
        choise_user[callback.from_user.id]['delivery_type'] = "Самовывоз из пункта"
        user_log[callback.from_user.id] = ''
        await callback.message.answer("Отправьте свой номер телефона (Нажмите на кнопку 'Отправить телефон' или напишите номер в формате 79994443322)", reply_markup=await btn_contact())
        user_log[callback.from_user.id] = 'phone'

    elif data == 'choice':
        count = float(text)
        choise_user[callback.from_user.id]['count'] = count
        choise_user[callback.from_user.id]['user_id'] = callback.from_user.id
        id_base = ''.join(choice(ascii_letters) for i in range(15))
        choise_user[callback.from_user.id]['base_id'] = id_base
        choise_user[callback.from_user.id]['user_name'] = callback.from_user.username

        price = await base.find_price(choise_user[callback.from_user.id])
        cost = round(count * price[0], 3)
        if cost >= 50000:
            cost = round(count * price[1], 3)
        if cost >= 500000:
            cost = round(count * price[2], 3)
        choise_user[callback.from_user.id]['cost'] = cost
        await base.insert_order(choise_user[callback.from_user.id])
        category = await base.get_category(choise_user[callback.from_user.id]['category'])
        text = f'{hbold("Выбрано:")}\n\nКатегория: {hitalic(category)}\n'
        text += f'Цвет: {hitalic(choise_user[callback.from_user.id]["color"])}\n'
        text += f'Ширина: {hitalic(choise_user[callback.from_user.id]["width"])}\n'
        text += f'Длина: {hitalic(choise_user[callback.from_user.id]["length"])}\n'
        text += f'Кол-во: {hitalic(choise_user[callback.from_user.id]["count"])}\n'
        text += f'Стоимость: {hitalic(choise_user[callback.from_user.id]["cost"])} руб.'
        builder = InlineKeyboardBuilder()
        builder.button(text='Удалить', callback_data=f'delete /-p {id_base}')
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
        data = 'add_product'
        select = await base.get_algo_pred(data)
        await callback.message.answer(text=select[0][1], reply_markup=await create_btn(data, None, callback.from_user.id))
        user_log[callback.from_user.id] = 'stat'

    elif data == 'checkout':
        orders = await base.get_orsers_prepare_user(callback.from_user.id)
        if orders == []:
            text = 'В вашей корзине нет товаров!'
            await callback.message.edit_text(text, reply_markup=await create_btn('start', None, callback.from_user.id))
            return
        else:
            user_log[callback.from_user.id] = ''

    elif data == 'checkout b':
        await callback.message.delete_reply_markup()
        await callback.message.edit_text(text="Ожидайте, получаем остатки по городам")
        orders = await base.get_orsers_prepare_user(callback.from_user.id)
        orders_id = []
        for order in orders:
            orders_id.append(order[0])
        list_city = await google_api.get_city(orders_id)

        builder = InlineKeyboardBuilder()
        for city in list_city:
            builder.button(text=city, callback_data=f'samcity /-p {city}')
        builder.button(text='Назад', callback_data='checkout')
        builder.adjust(2)
        await callback.message.edit_text(text="Выберите город для самовывоза", reply_markup=builder.as_markup())
        return

    elif data == 'samcity':
        choise_user[callback.from_user.id]['address'] = 'None'
        choise_user[callback.from_user.id]['type_del'] = "Самовывоз"
        choise_user[callback.from_user.id]['delivery_type'] = 'None'
        choise_user[callback.from_user.id]['company'] = 'None'
        choise_user[callback.from_user.id]['city'] = text
        data = 'DataUser'

    try:
        if int(data) in range(1, 18):
            if data == '15':
                choise_user[callback.from_user.id] = {'category' : data}
                photo_path_1 = f'jpg/{data}_1.jpg'
                photo_path_2 = f'jpg/{data}_2.jpg'
                data = '1-17'
                photo = True
                await callback.message.delete()
                await callback.message.answer_photo(photo=FSInputFile(photo_path_1))
                await callback.message.answer_photo(photo=FSInputFile(photo_path_2))
            else:
                choise_user[callback.from_user.id] = {'category' : data}
                photo_path = f'jpg/{data}.jpg'
                data = '1-17'
                photo = True
                await callback.message.delete()
                await callback.message.answer_photo(photo=FSInputFile(photo_path))

    except:
        pass

    if text == 'Сдек' or text == 'Кит':
        await callback.message.delete()
        photo = True
        text_mes = 'Вы начинаете заполнения накладной на ваш товар!\nВсе внесенные данные будут использованы, указывайте реальную информацию, иначе ваша посылка не дойдёт до вас!'
        await callback.message.answer(text=text_mes)

    select = await base.get_algo_pred(data)
    markup = await create_btn(data, text, callback.from_user.id)
    if data == 'DataUser':
        await callback.message.answer("Отправьте свой номер телефона (Нажмите на кнопку 'Отправить телефон' или напишите номер в формате 79994443322)", reply_markup=await btn_contact())
        user_log[callback.from_user.id] = 'phone'
    else:
        if photo:
            await callback.message.answer(text=select[0][1], reply_markup=markup)
        else:
            await callback.message.edit_text(text=select[0][1], reply_markup=markup)

async def create_btn(pred_data, text, user_id) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    all_select = await base.get_algo_pred(pred_data)
    if all_select == []:
        all_select = [[0,0,0,0]]
    if pred_data == 'DataUser':
        choise_user[user_id]['type_del'] = "Самовывоз"
        choise_user[user_id]['address'] = text

    elif len(all_select) == 1 and all_select[0][2] == 'from_base':
        if all_select[0][3] == 'color':
            mas_option = await base.find_color(choise_user[user_id]['category'])
        elif all_select[0][3] == 'width':
            choise_user[user_id]['color'] = text
            mas_option = await base.find_width(text, choise_user[user_id]['category'])
        elif all_select[0][3] == 'length':
            choise_user[user_id]['width'] = text
            mas_option = await base.find_length(choise_user[user_id]['color'], text, choise_user[user_id]['category'])

        for option in mas_option:
            btn = InlineKeyboardButton(text=option, callback_data=f'{all_select[0][3]} /-p {option}')
            builder.button(text=option, callback_data=f'{all_select[0][3]} /-p {option}')
    elif all_select[0][0] == 'checkout a' or all_select[0][0] == 'checkout b':
        for select in all_select:
            btn = InlineKeyboardButton(text=select[2], callback_data=f'{select[3]} /-p {select[2]}')
            builder.button(text=select[2], callback_data=f'{select[3]} /-p {select[2]}')
    elif all_select[0][2] == 'user_input':
        if all_select[0][0] == 'length':
            choise_user[user_id]['length'] = text
            user_log[user_id] = 'count'
        elif all_select[0][0] == 'TK':
            choise_user[user_id]['company'] = text
            user_log[user_id] = 'city'
        elif all_select[0][0] == 'checkout a a':
            user_log[user_id] = 'checkout a a'
        elif all_select[0][0] == 'checkout a b':
            user_log[user_id] = 'checkout a b'
    else:
        if not pred_data == 'count':
            for select in all_select:
                btn = InlineKeyboardButton(text=select[2], callback_data=select[3])
                builder.button(text=select[2], callback_data=select[3])
    if pred_data == 'color':
        builder.button(text="Назад", callback_data=f"color_{choise_user[user_id]['category']}")
    elif not pred_data == 'start':
        if pred_data == '1-17':
            pred_data = choise_user[user_id]['category']
        data = await base.get_pred_data(pred_data)
        #btn = InlineKeyboardButton(text='Назад', callback_data=data)
        builder.button(text='Назад', callback_data=data)
    if all_select[0][0] == 'length':
        choise_user[user_id]['length'] = text
        builder.adjust(5, 2)
    else:
        builder.adjust(1)
    markup = InlineKeyboardMarkup(inline_keyboard=builder.export())
    return markup

async def btn_contact():
    builder = ReplyKeyboardBuilder()
    btn = KeyboardButton(text="Отправить телефон", request_contact=True)
    builder.row(btn)
    return builder.as_markup(resize_keyboard=True)

async def send_orders_user(user_id):
    selects = await base.get_final_user(user_id)
    a = 1
    for select in selects:
        text = ''
        orders_id = select['orders_id'].split(', ')
        mas_orders = []
        for order_id in orders_id:
            if not order_id == '':
                order = await base.get_order_id(order_id)
                mas_char = await base.find_weight_dia(order['color'],
                                                order['width'], order['lenght'], order['category'])
                mas_orders.append({
                    'order_id' : order_id,
                    'category' : await base.get_category(order['category']),
                    'color' : order['color'],
                    'width' : order['width'],
                    'lenght' : order['lenght'],
                    'count' : order['count'],
                    'cost' : order['cost'],
                    'weight' : mas_char[0],
                    'diametr' : mas_char[1],
                    'lenght_rul' : mas_char[2]
                })

        text = f'{hbold("Заказ №")}{hbold(a)}\n\n'
        i = 1
        for order in mas_orders:
            weight = float(order['width']) * float(order['lenght']) * float(order['weight']) / 1000
            text += f'{i}).\n'
            text += f'Категория: {hitalic(order["category"])}\n'
            text += f'Цвет: {hitalic(order["color"])}\n'
            text += f'Ширина: {hitalic(order["width"])}\n'
            text += f'Длина: {hitalic(order["lenght"])}\n'
            text += f'Вес: {hitalic(weight)}\n'
            text += f'Диаметр: {hitalic(order["diametr"])}\n'
            text += f'Кол-во: {hitalic(order["count"])}\n'
            text += f'Стоимость: {hitalic(order["cost"])} руб.\n\n'
            i += 1
        if select["order_type"] == 'Самовывоз':
            text += f'{hbold("Способ: ")}{hitalic(select["order_type"])}\n'
            text += f'{hbold("Город: ")}{hitalic(select["city"])}\n\n'
        if select["order_type"] == 'Доставка':
            text += f'{hbold("Способ: ")}{hitalic(select["order_type"])}\n'
            text += f'{hbold("Компания доставки: ")}{hitalic(select["company"])}\n'
            text += f'{hbold("Город: ")}{hitalic(select["city"])}\n'
            text += f'{hbold("Тип доставки: ")}{hitalic(select["delivery_type"])}\n'
            text += f'{hbold("Адрес: ")}{hitalic(select["address"])}\n\n'
        text += f'{hbold("Полная стоимость: ")}{hbold(select["cost"])}{hbold(" руб.")}'
        a += 1

        builder = InlineKeyboardBuilder()
        btn = InlineKeyboardButton(text="Повторить заказ", callback_data=f"re-pay /-p {select['final_id']}")
        builder.row(btn)

        await bot.send_message(chat_id=user_id, text=text, reply_markup=builder.as_markup())

async def send_to_group(base_id, delivery_price = None):
    select = await base.get_final(base_id)
    orders_id = select['orders_id'].split(', ')
    mas_orders = []
    user_name = 'None'
    for order_id in orders_id:
        if not order_id == '':
            order = await base.get_order_id(order_id)
            mas_char = await base.find_weight_dia(order['color'],
                                             order['width'], order['lenght'], order['category'])
            mas_orders.append({
                'order_id' : order_id,
                'category' : await base.get_category(order['category']),
                'color' : order['color'],
                'width' : order['width'],
                'lenght' : order['lenght'],
                'count' : order['count'],
                'cost' : order['cost'],
                'weight' : mas_char[0],
                'diametr' : mas_char[1],
                'lenght_rul' : mas_char[2]
            })
            user_name = order['user_name']
    text = f'{hbold("Новый Заказ!")}\n\n{hbold("Контактные данные")}\n'
    if user_name == 'None':
        user_name = f't.me/+{select["phone"]}'
        text += f"{hitalic(select['name'])}\n{select['phone']}\n{user_name}\n\n{hbold('Товары')}\n"
    else:
        text += f"{hitalic(select['name'])}\n{select['phone']}\n@{user_name}\n\n{hbold('Товары')}\n"
    i = 1
    for order in mas_orders:
        weight = float(order['width']) * float(order['lenght']) * float(order['weight']) / 1000
        text += f'{i}).\n'
        text += f'Категория: {hitalic(order["category"])}\n'
        text += f'Цвет: {hitalic(order["color"])}\n'
        text += f'Ширина: {hitalic(order["width"])}\n'
        text += f'Длина: {hitalic(order["lenght"])}\n'
        text += f'Вес: {hitalic(weight)}\n'
        text += f'Диаметр: {hitalic(order["diametr"])}\n'
        text += f'Кол-во: {hitalic(order["count"])}\n'
        text += f'Стоимость: {hitalic(order["cost"])} руб.\n\n'
        i += 1
    if select["order_type"] == 'Самовывоз':
        text += f'{hbold("Способ: ")}{hitalic(select["order_type"])}\n'
        text += f'{hbold("Город: ")}{hitalic(select["city"])}\n\n'
    if select["order_type"] == 'Доставка':
        text += f'{hbold("Способ: ")}{hitalic(select["order_type"])}\n'
        text += f'{hbold("Компания доставки: ")}{hitalic(select["company"])}\n'
        text += f'{hbold("Город: ")}{hitalic(select["city"])}\n'
        text += f'{hbold("Тип доставки: ")}{hitalic(select["delivery_type"])}\n'
        text += f'{hbold("Адрес: ")}{hitalic(select["address"])}\n\n'
    text += f'{hbold("Полная стоимость: ")}{hbold(select["cost"])}{hbold(" руб.")}'
    if not delivery_price is None:
        text += f'{hbold("Стоимость доставки: ")}{hbold(delivery_price)}{hbold(" руб.")}'
    await bot.send_message(chat_id=config.GROUP_ID, text=text)
    await google_api.insert_order(select, mas_orders)

async def sleeps(user_id):
    with open('users.json', 'r') as file:
        data_json = json.loads(file.read())
    data_json[user_id] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('users.json', 'w') as file:
        file.write(json.dumps(data_json, ensure_ascii=True, indent=4))

async def remove_user(user_id):
    with open('users.json', 'r') as file:
        data_json = json.loads(file.read())
    data_json.pop(user_id, None)
    with open('users.json', 'w') as file:
        file.write(json.dumps(data_json, ensure_ascii=True, indent=4))

def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(dp.start_polling(bot))
    loop.close()

async def main_async() -> None:
    #await send_to_group('eGDAsgEixwvovNP')
    await dp.start_polling(bot)


if __name__ == "__main__":
    x = threading.Thread(target=sleep.check_sleeps).start()
    asyncio.run(main_async())

    pass

    # asyncio.run(main())
    #asyncio.run(send_to_group('mglAHYwYVQiUvyw'))