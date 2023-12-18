"""CDEK Integration"""
import asyncio
import json
import os
import random
import sys
import time

import requests

PROJECT_ROOT = os.path.abspath(os.path.join(
                  os.path.dirname(__file__),
                  os.pardir)
)
sys.path.append(PROJECT_ROOT)



import config  # pylint: disable=import-error
import database as base  # pylint: disable=import-error, wrong-import-position
from trans_company.trans import Contact, Order  # pylint: disable=import-error

CDEK_CLIENT_ID = 'MI0HEYEwLe8kjteRL7DQHz2ucutQqVEy'
CDEK_CLIENT_SECRET = 'tQnrAiHhB3gfmj3mtr6whd1OEZWZSYq2'

class CDEK:
    """CDEK API"""

    headers = {'Authorization' : None}
    base_url = 'https://api.cdek.ru'

    def __init__(self, city, order: Order, mas_order: dict) -> None:
        self.city = city
        self.mas_order = mas_order
        self.order = order
        self.order_uuid = ''
        self.auth()

    def auth(self) -> None:
        """Authentication"""
        path = '/v2/oauth/token'
        params = {
            'grant_type' :	'client_credentials',
            'client_id' : CDEK_CLIENT_ID,
            'client_secret' : CDEK_CLIENT_SECRET
        }

        req = requests.post(url=self.base_url+path, params=params, timeout=10).json()
        self.headers = {'Authorization' : f"Bearer {req['access_token']}"}

    def check_city(self) -> str:
        """Check city"""
        path = '/v2/location/cities'
        req = requests.get(url=self.base_url+path, headers=self.headers, timeout=10).json()
        for city_struc in req:
            if city_struc['city'].lower() == self.city.lower():
                return True

        return False

    def get_city(self) -> dict:
        """Getting city"""
        path = '/v2/location/cities'
        req = requests.get(url=self.base_url+path, headers=self.headers, timeout=10).json()
        for city_struc in req:
            if city_struc['city'].lower() == self.city.lower():
                return city_struc
        return None

    def create_order(self) -> None:
        """Create order"""
        struct_to = self.get_city()
        packages = []
        all_weight = 0
        number = 1
        for order in self.mas_order:
            for i in range(int(self.mas_order[0]['count'])):
                weight = float(order['weight'])
                packages.append({
                    "number" : f"{number}{i}",
                    "weight" : int(round(weight)),
                    "length" : int(round(float(order['lenght_rul'])*100)),
                    "width" : int(round(float(order['diametr'])*100)),
                    "height" : int(round(float(order['diametr'])*100)),
                    "comment" : f"{i}",
                    "items" : [ {
                        "ware_key" : order['order_id'],
                        "payment" : {
                            "value" : 0,
                        },
                        "name" : order['color'],
                        "cost" : order['cost'] / order['count'],
                        "amount" : 1,
                        "weight" : int(round(weight)),
                        #"url" : "www.item.ru"
                    } ]
                })
                all_weight += weight
            number += 1

        number_cdek = random.randint(10000000, 100000000)
        order_cdek = {
            #"type": 2,
            "type": 1,
            #"number" : str(number_cdek),
            "shipment_point" : "TBL2",
            
            "sender": {
                "company": 'ООО "ТЕНЕТ"',
                "name": "Лучко Александр Евгеньевич",
                "email": "info@tenet-zavod.ru",
                "phones": [
                    {
                        "number": "+74952913788"
                    }
                ]
            },
            "recipient": {
                "company": self.order.contact.name,
                "name": self.order.contact.name,
                "phones": [
                    {
                        "number": f"+{self.order.contact.phone}"
                    }
                ]
            },
            "packages": packages,
        }

        if self.order.delivery_type == 'Самовывоз из пункта':
            #code_pvz = self.find_pvz(struct_to, all_weight)
            order_cdek["delivery_point"] = self.order.contact.address
            #order_cdek["tariff_code"] = 62
            order_cdek["tariff_code"] = 136
        else:
            to_location = {
                "code" : str(struct_to['code']),
                "fias_guid" : "",
                "postal_code" : "",
                "longitude" : "",
                "latitude" : "",
                "country_code" : "",
                "region" : "",
                "sub_region" : "",
                "city" : struct_to['city'],
                "kladr_code" : "",
                "address" : self.order.contact.address
            }
            order_cdek["tariff_code"] = 122
            order_cdek["to_location"] = to_location

        path = '/v2/orders'
        req = requests.post(url=self.base_url+path, headers=self.headers,
                            json=order_cdek, timeout=10).json()
        self.order_uuid = req['entity']['uuid']
        path = f"/v2/orders/{req['entity']['uuid']}"
        time.sleep(1)
        req = requests.get(url=self.base_url+path, headers=self.headers, timeout=10).json()
        time.sleep(1)
        order_cdek["uuid"] = req['entity']['uuid']
        order_cdek["delivery_recipient_cost"] = {"value" : req['entity']['delivery_detail']['total_sum']}
        path = '/v2/orders'
        req = requests.post(url=self.base_url+path, headers=self.headers,
                            json=order_cdek, timeout=10).json()
        self.order_uuid = req['entity']['uuid']
        path = f"/v2/orders/{req['entity']['uuid']}"
        time.sleep(1)
        req = requests.get(url=self.base_url+path, headers=self.headers, timeout=10).json()
        time.sleep(1)
        file_name = self.gen_receipt()
        return file_name

    def gen_receipt(self) -> None:
        """Generation receipt"""
        
        check = True
        count_check = 0
        while check:
            receipt_json = {
                "orders": [
                    {
                        "order_uuid": self.order_uuid
                    }
                ],
                "copy_count": 1
            }
            path = '/v2/print/orders'
            req = requests.post(url=self.base_url+path, headers=self.headers,
                                json=receipt_json, timeout=10).json()
            path = f"/v2/print/orders/{req['entity']['uuid']}"
            uuid = req['entity']['uuid']
            time.sleep(5)
            req = requests.get(url=self.base_url+path, headers=self.headers, timeout=10).json()
            for status in req['entity']['statuses']:
                if status['code'] == "READY":
                    check = False
                    url_pdf = req['entity']['url']
                    req = requests.get(url=url_pdf, headers=self.headers, timeout=10)
                    file_name = f'trans_company/cdek_pdf/{uuid}.pdf'
                    with open(file_name, 'wb') as file:
                        file.write(req.content)
                    return file_name
                elif status['code'] == 'INVALID':
                    if count_check > 3:
                        print('ERROR')
                        self.send_report(json.dumps(req))
                        check = False
                        return None
                    else:
                        time.sleep(4)
                        count_check += 1

    def check_price(self):
        """Check price"""
        path = '/v2/calculator/tarifflist'
        struct_to = self.get_city()
        packages = []
        all_weight = 0
        number = 1
        for order in self.mas_order:
            for i in range(int(self.mas_order[0]['count'])):
                weight = float(order['width']) * float(order['lenght']) * float(order['weight'])
                packages.append({
                    "number" : f"{number}_{i}",
                    "weight" : int(round(weight)),
                    "length" : int(round(float(order['lenght_rul'])*100)),
                    "width" : int(round(float(order['diametr'])*100)),
                    "height" : int(round(float(order['diametr'])*100)),
                    "comment" : f"{i}"
                })
                all_weight += weight
            number += 1

    def find_pvz(self, struct_to, all_weight):
        """Search PVZ"""
        path = f"/v2/deliverypoints?weight_min={int(all_weight)}\
            &city_code={struct_to['code']}&allowed_cod=1&type=PVZ"
        req = requests.get(url=self.base_url+path, headers=self.headers, timeout=10).json()
        return req[0]['code']

    def find_pvz_to_bot(self):
        """Search PVZ to TG_BOT"""
        all_weight = 0
        for order in self.mas_order:
            for _ in range(int(order['count'])):
                weight = float(order['weight']) / 1000
                all_weight += weight
        struct_to = self.get_city()
        params = {
            'weight_max' : int(round(all_weight)),
            'city_code' : struct_to['code'],
            'allowd_code' : 1,
            'type' : 'PVZ'
        }
        path = "/v2/deliverypoints"
        req = requests.get(url=self.base_url+path, params=params,
                            headers=self.headers, timeout=10).json()

        alias = {
            "пр." : [
                "проспект","пр.", "пр-т.", "пр-т", "пр", "Пр-т", "Пр."
            ],
            'ул.' : [
                "улица", "Ул.", "ул.", "ул" , "Улица", "Ул", "УЛ.", "УЛ"
            ],
            "тупик" : [
                "ТУПИК", "Тупик", "тупик"
            ]
        }

        mas_pvz = []
        for pvz in req:
            address = pvz['location']['address']
            for key, value in alias.items():
                code_alias = None
                for street in value:
                    if code_alias is None:
                        if street in address:
                            code_alias = f'{key} '
                            address = address.replace(street, 'None ')
                            address = address.lower().title()
                            address = address.replace('None ', code_alias)
                            address = address.replace("  ", " ")
            # code_alias = None
            # for street in alias['ул']:
            #     if code_alias is None:
            #         if street in address:
            #             code_alias = 'ул '
            #             address = address.replace(street, code_alias)
            #             address = address.replace("  ", " ")

            pvz_dict = {
                'code' : pvz['code'],
                'x' : pvz['location']['longitude'],
                'y' : pvz['location']['latitude'],
                'address' : address,
            }

            if 'nearest_metro_station' in pvz:
                pvz_dict['metro'] = pvz['nearest_metro_station']
            mas_pvz.append(pvz_dict)

        sort_pvz = sorted(mas_pvz, key=lambda x: x['address'])
        return sort_pvz

    def send_report(self, text):
        params = {
            'chat_id' : config.ADMIN,
            'text' : text,
        }
        url = f'https://api.telegram.org/bot{config.TOKEN}/sendMessage'
        requests.get(url, params=params, timeout=10)

def main():
    """Main Function"""
    select = asyncio.run(base.get_final('dFPceiBVGfsHqnM'))
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

    # CDEK(select['city'],
    #     Order(
    #         Contact(select['phone'], select['name'], select['address'], select['city']),
    #             select['delivery_type'], select['final_id'], select['order_type']),
    #                 mas_orders).find_pvz_to_bot()

    CDEK(select['city'],
        Order(
            Contact(select['phone'], select['name'], select['address'], select['city']),
                select['delivery_type'], select['final_id'], select['order_type']),
                    mas_orders).create_order()

if __name__ == '__main__':
    main()
    