"""Slepping Users"""
import asyncio
import json
import time
from datetime import datetime, timedelta

import requests

import config  # pylint: disable=import-error

SLEEPING = 21600

def check_sleeps():
    """Check user"""
    while True:
        with open('users.json', 'r', encoding='utf-8') as file:
            data_json = json.loads(file.read())       
        pops_user = []
        for user in data_json:
            text = ''
            time_user = datetime.strptime(data_json[user], "%Y-%m-%d %H:%M:%S")
            if datetime.now() - time_user > timedelta(seconds=SLEEPING):
                text += 'Пользователь не дошел до конца:\n'
                text += f'<a href="tg://user?id={user}">Открыть профиль</a>'
                url = f"https://api.telegram.org/bot{config.TOKEN}/sendMessage"
                params = {
                    'chat_id' : config.GROUP_ID,
                    'text' : text,
                    'parse_mode' : 'HTML'
                }
                requests.get(url, params=params, timeout=10)
                pops_user.append(user)

        for user in pops_user:
            data_json.pop(user, None)

        with open('users.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(data_json))

        time.sleep(40)


if __name__ == "__main__":
    check_sleeps()
