import asyncio
import sqlite3

con = sqlite3.connect("database/tenet.db")
cur = con.cursor()

cur.execute('CREATE TABLE IF NOT EXISTS {}(pred_data, text, btn, data)'.format('algoritms'))
con.commit()

cur.execute('CREATE TABLE IF NOT EXISTS {}(color, width, length, weight, diametr, category, price, price_30, price_500, length_rul)'.format('prices'))
con.commit()

cur.execute('CREATE TABLE IF NOT EXISTS {}(id, user_name, user_id, color, width, length, category, count, cost, status)'.format('orders'))
con.commit()

cur.execute('CREATE TABLE IF NOT EXISTS {}(id, user_id, type, company, city, delivery_type, address, orders_id, phone, name, cost, status)'.format('finals'))
con.commit()

cur.execute('CREATE TABLE IF NOT EXISTS {}(id, section, category)'.format('categories'))
con.commit()


## Таблица ALGORITMS

async def insert_algo(mas_algo) -> None:
    delete_query = "DELETE FROM algoritms"
    cur.execute(delete_query)
    con.commit()
    for algo in mas_algo:
        insert_query = f'INSERT INTO algoritms VALUES("{algo[0]}","{algo[1]}","{algo[2]}","{algo[3]}")'
        cur.execute(insert_query)
        con.commit()

async def get_algo_pred(pred_data) -> list:
    select_query = f"SELECT * FROM algoritms WHERE pred_data='{pred_data}'"
    all_select = cur.execute(select_query).fetchall()
    return all_select

async def get_pred_data(pred_data) -> str:
    select_query = f"SELECT pred_data FROM algoritms WHERE data='{pred_data}'"
    select = cur.execute(select_query).fetchone()[0]
    return select    
#
## Таблица PRICES
async def insert_prices(mas_price) -> None:
    delete_query = "DELETE FROM prices"
    cur.execute(delete_query)
    con.commit()
    for price in mas_price:
        insert_query = f'INSERT INTO prices VALUES("{price[0]}","{price[1]}","{price[2]}","{price[3]}", "{price[4]}", "{price[5]}", {price[6]}, {price[7]}, {price[8]}, "{price[9]}")'
        cur.execute(insert_query)
        con.commit()

async def find_color(category) -> list:
    select_query = "SELECT color, category FROM prices"
    all_select = cur.execute(select_query).fetchall()
    mas_color = []
    for select in all_select:
        cat = select[1]
        cat = cat.split(' ')
        if not select[0] in mas_color and category in cat:
            mas_color.append(select[0])     
    return mas_color

async def find_width(color, category) -> list:
    select_query = f"SELECT width, category FROM prices WHERE color = '{color}'"
    all_select = cur.execute(select_query).fetchall()
    mas_width = []
    for select in all_select:
        cat = select[1]
        cat = cat.split(' ')
        if not select[0] in mas_width and category in cat:
            mas_width.append(select[0]) 
    mas_width.sort()    
    return mas_width

async def find_length(color, width, category) -> list:
    select_query = f"SELECT length, category FROM prices WHERE color = '{color}' and width = '{width}'"
    all_select = cur.execute(select_query).fetchall()
    mas_length = []
    for select in all_select:
        cat = select[1]
        cat = cat.split(' ')
        if not select[0] in mas_length and category in cat:
            mas_length.append(select[0])  
    mas_length.sort()   
    return mas_length

async def find_weight_dia(color, width, length, category) -> list:
    select_query = f"SELECT weight, diametr, category, length_rul FROM prices WHERE color = '{color}' and width = '{width}' and length = '{length}'"
    all_select = cur.execute(select_query).fetchall()
    mas_length = []
    for select in all_select:
        cat = select[2]
        cat = cat.split(' ')
        if not select[0] in mas_length and category in cat:
            mas_length.append([select[0], select[1], select[3]])
    return mas_length[0] 

async def find_price(user_choise):
    select_query = f"SELECT price, price_30, price_500, category FROM prices WHERE color = '{user_choise['color']}' and width = '{user_choise['width']}' and length = '{user_choise['length']}'"
    all_select = cur.execute(select_query).fetchall()
    mas_price = []
    for select in all_select:
        cat = select[3]
        cat = cat.split(' ')
        if user_choise['category'] in cat:
            mas_price.append(select)
    return mas_price[0]
#
## Таблица ORDERS

async def insert_order(user_choise):        # id, user_id, color, width, length, category, count, cost, status
    insert_query = f'INSERT INTO orders VALUES("{user_choise["base_id"]}", "{user_choise["user_name"]}" ,{user_choise["user_id"]},"{user_choise["color"]}","{user_choise["width"]}","{user_choise["length"]}","{user_choise["category"]}",{user_choise["count"]},{user_choise["cost"]}, "prepare")'
    cur.execute(insert_query)
    con.commit()

async def get_orsers_prepare_user(user_id) -> list:
    select_query = f"SELECT id, cost FROM orders WHERE user_id = {user_id} and status = 'prepare'"
    all_select = cur.execute(select_query).fetchall()
    return all_select

async def get_order_id(base_id) -> tuple:
    select_query = f"SELECT * FROM orders WHERE id = '{base_id}'"
    select = cur.execute(select_query).fetchone()
    dict_select = {
        "id_base" : select[0],
        "user_name": select[1],
        "user_id" : select[2],
        "color" : select[3],
        "width" : select[4],
        "lenght" : select[5],
        "category" : select[6],
        "count" : select[7],
        "cost" : select[8],
        "status" : select[9]
    }
    return dict_select

async def update_status(id_base) -> None:
    update_query = f'UPDAte orders SET status = "in-final" WHERE id = "{id_base}"'
    cur.execute(update_query)
    con.commit()

async def delete_order(id_base) -> None:
    delete_query = f"DELETE FROM orders WHERE id='{id_base}'"
    cur.execute(delete_query)
    con.commit()
#
## Таблица FINALS

async def insert_finals(user_choise, user_id) -> None:
    all_select = await get_orsers_prepare_user(user_id)
    id_base = ''
    full_cost = 0
    for select in all_select:
        await update_status(select[0])
        id_base += select[0] + ', '
        full_cost += select[1]
    
    if user_choise["type_del"] == 'Самовывоз':
        insert_query = f'INSERT INTO finals VALUES("{user_choise["base_id"]}",{user_id},"{user_choise["type_del"]}","None","{user_choise["address"]}","None","None","{id_base}","{user_choise["phone"]}", "{user_choise["name"]}", {full_cost}, "prepare")'
    elif user_choise["type_del"] == 'Доставка':
        insert_query = f'INSERT INTO finals VALUES("{user_choise["base_id"]}",{user_id},"{user_choise["type_del"]}","{user_choise["company"]}","{user_choise["city"]}","{user_choise["delivery_type"]}","{user_choise["address"]}","{id_base}", "{user_choise["phone"]}", "{user_choise["name"]}", {full_cost}, "prepare")'
    elif user_choise["type_del"] == 'Повтор':
        insert_query = f'INSERT INTO finals VALUES("{user_choise["base_id"]}",{user_choise["select"][1]},"{user_choise["select"][2]}","{user_choise["select"][3]}","{user_choise["select"][4]}","{user_choise["select"][5]}","{user_choise["select"][6]}","{user_choise["select"][7]}", "{user_choise["select"][8]}", "{user_choise["select"][9]}", {user_choise["select"][10]}, "prepare")'
    cur.execute(insert_query)
    con.commit()

async def get_final(base_id) -> tuple:
    select_query = f"SELECT * FROM finals WHERE id = '{base_id}'"
    select = cur.execute(select_query).fetchone()
    select_dict = {
        'final_id' : select[0],
        'user_id' : select[1],
        'order_type' : select[2],
        'company' : select[3],
        'city' : select[4],
        'delivery_type' : select[5],
        'address' : select[6],
        'orders_id' : select[7],
        'phone' : select[8],
        'name' : select[9],
        'cost' : select[10],
        'status' : select[11],
    }
    return select_dict

async def get_final_user(user_id) -> list:
    select_query = f"SELECT * FROM finals WHERE user_id = {user_id}"
    selects = cur.execute(select_query).fetchall()
    select_dict = []
    for select in selects:
        select_dict.append({
        'final_id' : select[0],
        'user_id' : select[1],
        'order_type' : select[2],
        'company' : select[3],
        'city' : select[4],
        'delivery_type' : select[5],
        'address' : select[6],
        'orders_id' : select[7],
        'phone' : select[8],
        'name' : select[9],
        'cost' : select[10],
        'status' : select[11],
    })
    return select_dict
#
## Таблица CATEGORIES

async def insert_cat(mas_cat) -> None:
    for cat in mas_cat:
        insert_query = f'INSERT INTO categories VALUES({cat[0]}, "{cat[1]}", "{cat[2]}")'
        cur.execute(insert_query)
        con.commit()

async def get_unique_section() -> list:
    select_query = "SELECT DISTINCT section FROM categories"
    return cur.execute(select_query).fetchall()

async def get_section_category(section) -> list:
    select_query = f"SELECT id, category FROM categories WHERE section = '{section}'"
    return cur.execute(select_query).fetchall()

async def get_category(cat) -> str:
    select_query = f"SELECT category FROM categories WHERE id = {cat}"
    select = cur.execute(select_query).fetchone()[0]
    return select

async def main() -> None:
    # cur.execute("DELETE FROM orders")
    # con.commit()
    # cur.execute("DROP TABLE prices")
    # con.commit()
    #await insert_finals({}, 515551867)
    #await delete_order('MQuwYgjecCjlPRI')
    pass

if __name__ == "__main__":
    asyncio.run(main())