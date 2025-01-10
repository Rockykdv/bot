#!/bin/bash

sudo apt update

sudo apt install -y ufw

sudo ufw enable

sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 10000:30000/udp
sudo ufw allow 10000:30000/tcp

sudo apt install -y python3-pip python3-venv

python3 -m venv myenv

source myenv/bin/activate

pip install flask pyngrok

pip install telebot pymongo aiohttp

pip install telebot flask aiogram pyTelegramBotAPI python-telegram-bot

chmod +x *

nohup python3 app.py > output.log 2>&1 &
