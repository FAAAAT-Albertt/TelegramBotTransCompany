import asyncio
from datetime import datetime

import gspread

from database import database as base


async def insert_order(select, mas_order) -> None:
    """Function Inserts to Google Table"""
    gc = gspread.service_account(filename='credentials.json')

    wks = gc.open("Tenet TG Bot").sheet1
    val = wks.get_all_values()
    num_row = len(val) + 1

    for order in mas_order:
        row = [datetime.now().strftime("%d-%m-%Y"), select['name'], select['phone'], f"t.me/+{select['phone']}", 
            order['category'], order['color'], order['width'], order['lenght'], order['weight'], order['diametr'],
            order['count'], order['cost'], select['order_type'], select['company'], select['city'], select['delivery_type'],
            select['address'], select['cost']]
        wks.insert_row(row, index=num_row)
        num_row += 1

async def get_city(orders_id: list) -> list:
    """Function returns cities to pickup"""
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

    city_list = ["Тобольск", "Тюмень"]
    gc = gspread.service_account(filename='credentials.json')

    wks = gc.open("Завод Тенет. Наличие")

    worksheet_list = wks.worksheets()
    for worksheet_name in worksheet_list[3:]:
        list_google = wks.worksheet(worksheet_name.title).get_all_values()
        cur_count = 0
        cont = False
        for order in mas_orders:
            ord_color = order['color']
            ord_width = float(order['width'].replace(',', '.'))
            ord_lenght = float(order['lenght'].replace(',', '.'))
            ord_count = int(order['count'])
            for row in list_google[2:]:
                try:
                    row_color = row[1].strip()
                    row_width = float(row[3].strip().replace(',', '.'))
                    row_lenght = float(row[4].strip().replace(',', '.'))
                    row_count = int(row[5])
                    if cont:
                        continue
                    else:
                        if "НЕЛИКВИД" in row[1]:
                            cont = True
                        else:
                            if ord_color == row_color and ord_width == row_width and ord_lenght == row_lenght and row_count >= ord_count:
                                cur_count += 1
                except:
                    continue

        if cur_count >= len(mas_orders):
            city_list.append(worksheet_name.title)

    return city_list

async def get_contacts(city) -> dict:
    """Function returns contacts from city"""
    contacts = {
        "address" : None,
        "contact" : None,
    }

    if city == 'Тобольск':
        city = 'Тобольск. Производство'
    
    gc = gspread.service_account(filename='credentials.json')
    wks = gc.open("Завод Тенет. Наличие")
    list_google = wks.worksheet(city).get_all_values()
    for row in list_google[:2]:
        adr = False
        cont = False
        for cel in row:
            if adr:
                contacts['address'] = cel
                adr = False
            if cont:
                contacts['contact'] = cel
                cont = False
            if cel == 'Адрес:':
                adr = True
            elif cel == 'Контакт:':
                cont = True

    return contacts

async def get_price() -> dict:
    """Function returns price"""
    gc = gspread.service_account(filename='credentials.json')
    wks = gc.open("Прайс_Тенет")
    list_google = wks.worksheet("Прайс").get_all_values()
    mas_price = []
    for row in list_google[2:]:
        if not row[0] == "":
            try:
                category = str(int(row[10])) + " " + str(int(row[11])) + " " + str(int(row[12]))
                category = category.strip()
            except:
                try:
                    category = str(int(row[10])) + " " + str(int(row[11]))
                    category = category.strip()
                except:
                    try:
                        category = str(int(row[10]))
                        category = category.strip()
                    except:
                        category = str(int(row[11]))
                        category = category.strip()
            
            mas_price.append([row[1], row[3].strip().replace(',', '.'), row[4].strip().replace(',', '.'), row[9].strip().replace('\xa0', '').replace(',', '.'), row[7].strip().replace(',', '.'), category, round(float(row[13].replace('\xa0', '').replace(',', '.'))), round(float(row[14].replace('\xa0', '').replace(',', '.')),1), round(float(row[15].replace('\xa0', '').replace(',', '.')),2), float(row[8].replace('\xa0', '').replace(',', '.'))])
    await base.insert_prices(mas_price)

async def get_cat() -> dict:
    """Function returns categories"""
    gc = gspread.service_account(filename='credentials.json')
    wks = gc.open("Прайс_Тенет")
    list_google = wks.worksheet("Категории").get_all_values()
    # Получаем направления
    sections_in = list_google[1]
    index = 1
    section = {

    }
    for sec in sections_in[1:]:
        section[index] = sec
        index += 1
    mas_cat = []
    for row in list_google[2:]:
        id_cat = row[0]
        index = 1
        for cat in row[1:]:
            if not cat == '':
                mas_cat.append([id_cat, section[index], cat])
            index += 1
    
    await base.insert_cat(mas_cat)

if __name__ == "__main__":
    asyncio.run(get_price())
