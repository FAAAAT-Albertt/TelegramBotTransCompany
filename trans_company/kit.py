"""KIT Integration"""
import asyncio
import base64
import json
import os
import sys
from datetime import datetime, timedelta

import requests

PROJECT_ROOT = os.path.abspath(os.path.join(
                  os.path.dirname(__file__),
                  os.pardir)
)
sys.path.append(PROJECT_ROOT)


import config  # pylint: disable=import-error
import database as base  # pylint: disable=import-error, wrong-import-position
from trans_company.trans import Contact, Order  # pylint: disable=import-error

KIT_TOKEN = "J7Lakt2Aq9aKXFrEhjW8h-MnLbYZwhWk"

class KIT:
    """Kit Class"""

    headers = {'Authorization' : f"Bearer {KIT_TOKEN}"}
    base_url = 'https://capi.tk-kit.com'

    def __init__(self, city, order: Order, mas_order: dict) -> None:
        self.city = city
        self.mas_order = mas_order
        self.order = order

    def send_request(self, type_request = 'GET', path='', params=None, json_data=None):
        """Sending request to url"""
        try:
            if type_request == 'GET':
                req = requests.get(url=self.base_url+path, params=params,
                                    headers=self.headers, timeout=10).json()
            else:
                req = requests.post(url=self.base_url+path, headers=self.headers,
                                    json=json_data, timeout=10).json()
            if 'status' in req:
                if req['status'] == 429:
                    self.send_report(json.dumps(req))
                    return False
            return req
        except requests.exceptions.RequestException:
            return False


    def check_city(self):
        """Function returns"""
        req = self.send_request(type_request='GET', path='/1.0/tdd/city/get-list')
        for city_struct in req:
            if city_struct['name'].lower() == self.city.lower():
                return True
        return False

    def get_city_code(self):
        """Function returns"""
        req = self.send_request(type_request='GET', path='/1.0/tdd/city/get-list')
        for city_struct in req:
            if city_struct['name'].lower() == self.order.contact.city.lower():
                return city_struct['code']
        return False

    def create_order(self):
        """Create Order in tk KIT"""
        sender_data = { # Отправитель
            "debitor_type" : 3,
            "country_code" : "RU",
            "name_ur" : "Лучко Александр Евгеньевич",
            "organization_name_ur" : 'ООО "ТЕНЕТ"',
            "organization_phone_ur" : "74952913788",
            "phone_ur" :  "74952913788",
            "inn_ur" : "7206062613",
            "kpp" : "720601001"
        }

        receiver_data = { # Получатель
            "debitor_type" : 1,
            "country_code" : "RU",
            "real_country" : "RU",
            "real_city" : self.order.contact.city,
            "real_street" : self.order.contact.address,
            "real_contact_name" : self.order.contact.name,
            "real_contact_phone" : self.order.contact.phone,
        }
        places = []
        for order in self.mas_order:
            weight = float(order['width']) * float(order['lenght']) * float(order['weight']) / 1000
            places.append({
                "count_place" : int(order['count']),
                "weight" : int(round(weight)),
                "length" : int(round(float(order['lenght_rul'])*100)),
                "width" : int(round(float(order['diametr'])*100)),
                "height" : int(round(float(order['diametr'])*100)),
            })

        json_data = {
            "city_pickup_code": "720000200000", # Тобольск
            "city_delivery_code": self.get_city_code(), # Новокузнецк
            "type" : "01",
            "declared_price": 1000,
            "currency_code": "RUB",
            "sender" : sender_data,
            "receiver" : receiver_data,
            "places": places,
            "additional_payment_shipping" : "WE",
            "additional_payment_delivery" : "WE",
            "insurance": 0,
        }
        if self.order.delivery_type == 'Самовывоз из пункта':
            json_data['deliver'] = 0
        else:
            json_data['deliver'] = 1
            json_data['delivery_date'] = (datetime.now() + timedelta(days=6)).strftime('%Y-%m-%d')
            json_data['delivery_time_start'] = '09:00'
            json_data['delivery_time_end'] = '18:00'
        req = self.send_request(type_request='POST', path='/1.0/order/create', json_data=json_data)
        file_name = self.get_doc(str(req['result']['sale_number']), 3)
        if file_name is None:
            pass
        else:
            order_info = self.get_order(str(req['result']['sale_number']))
            order_info['file_name'] = file_name
            return order_info

    def get_doc(self, sale_number: str, type_doc = 1):
        """
        Download Document
        type_doc = 1 - Экспедиторская расписка
        type_doc = 5 - Счет на оплату
        """
        
        json_data = {
            "sale_number": sale_number,
            "type_code": str(type_doc)
        }
        req = self.send_request(type_request='POST', path="/1.0/order/document/get", json_data=json_data)
        if not req['data'] == '':
            file_name = f'trans_company/kit_pdf/{sale_number}.pdf'
            file_content=base64.b64decode(req['data'])
            with open(file_name,"wb") as file:
                    file.write(file_content)

            # with open(file_name, 'wb') as file:
            #     file.write(bytes(req['data']))
            return file_name
        else:
            return None

    def get_order(self, sale_number: str):
        """Get info about order"""
        json_data = {
            "sale_number": sale_number,
        }
        req = self.send_request(type_request='POST', path="/1.0/order/get", json_data=json_data)
        order_info = {
            'price' : req['total']['price'],
            'cargo_number' : req['total']['cargo_number']
        }
        return order_info
    
    def send_report(self, text):
        params = {
            'chat_id' : config.ADMIN,
            'text' : text,
        }
        url = f'https://api.telegram.org/bot{config.TOKEN}/sendMessage'
        requests.get(url, params=params, timeout=10)

def main():
    """Start"""
    select = asyncio.run(base.get_final('XmJMBwQgHWtmpnq'))
    orders_id = select['orders_id'].split(', ')
    mas_orders = []
    for order_id in orders_id:
        if not order_id == '':
            order = asyncio.run(base.get_order_id(order_id))
            mas_char = asyncio.run(base.find_weight_dia(order['color'],
                                             order['width'], order['lenght'], order['category']))
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

    KIT(select['city'],
        Order(
            Contact(select['phone'], select['name'], select['address'], select['city']),
                select['delivery_type'], select['final_id'], select['order_type']),
                    mas_orders).create_order()

if __name__ == '__main__':
    main()
