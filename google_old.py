import asyncio

import requests
from bs4 import BeautifulSoup

from database import database as base


async def download_algo() -> None:
    url = 'https://docs.google.com/spreadsheets/d/1gPsPAB1PPfNUwYYoLjcbb1eGGf_FqXNkdP7VrtFSTJ4/edit#gid=0'
    req = requests.get(url)
    soup = BeautifulSoup(req.text, 'lxml')
    table = soup.find('tbody')
    trs = table.find_all('tr')
    mas_algo = []
    for i in range(0, len(trs), 4):
        obj_trs = trs[i:i+5]
        pred_data = obj_trs[0].find('td').find_next('td').text
        text_btn = obj_trs[1].find('td').find_next('td').text
        btns = obj_trs[2].find_all('td')
        call_datas = obj_trs[3].find_all('td')
        i = 1
        for btn in btns[1:]:
            if not btn.text == '':
                btn_text = btn.text
                btn_call = call_datas[i].text
                mas_algo.append([pred_data, text_btn, btn_text, btn_call])
            i += 1
            
    await base.insert_algo(mas_algo)

async def find_option(option) -> list:
    if option == 'color':
        index = 1
    elif option == 'width':
        index = 3
    elif option == 'length':
        index = 4
    url = 'https://docs.google.com/spreadsheets/d/1mTdSEm04uOd_3EufbYtktJZCUkFilQwsfX-Pci484Uc/edit#gid=1179187572'
    req = requests.get(url)
    soup = BeautifulSoup(req.text, 'lxml')
    table = soup.find('tbody')
    trs = table.find_all('tr')
    mas_option = []
    for tr in trs[2:]:
        try:
            tds = tr.find_all('td')
            need = tds[index].text
            if not need == '' and not need in mas_option:
                mas_option.append(need)  
        except: 
            continue    
        
    return mas_option

async def download_price() -> None:
    url = 'https://docs.google.com/spreadsheets/d/1mTdSEm04uOd_3EufbYtktJZCUkFilQwsfX-Pci484Uc/edit#gid=1179187572'
    req = requests.get(url)
    soup = BeautifulSoup(req.text, 'lxml')
    table = soup.find('tbody')
    trs = table.find_all('tr')
    mas_price = []
    for tr in trs[2:]:
        tds = tr.find_all('td')
        if not tds[0].text == "":
            category = tds[8].text.strip() + " " + tds[9].text.strip() + " " + tds[10].text.strip()
            category = category.strip()
            color = tds[1].text.strip()
            width = tds[3].text.strip()
            length = tds[4].text.strip()
            try:
                price = float(tds[11].text.replace(',', '.'))
            except:
                price = tds[11].text.strip().replace('\xa0', '')
                price = float(price.replace(',', '.'))
            try:
                price_30 = float(tds[12].text.replace(',', '.'))
            except:
                price_30 = tds[12].text.strip().replace('\xa0', '')
                price_30 = float(price_30.replace(',', '.'))
            try:
                price_500 = float(tds[13].text.replace(',', '.'))
            except:
                price_500 = tds[13].text.strip().replace('\xa0', '')
                price_500 = float(price_500.replace(',', '.'))
            mas_price.append([color, width, length, category, price, price_30, price_500])
    pass


if __name__ == "__main__":
    asyncio.run(download_algo())