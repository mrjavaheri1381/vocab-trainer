import requests
import os
from dotenv import load_dotenv
import json


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
def send_message(chat_id: int, text: str, parse_mode: str = None, reply_markup: dict = None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)  # convert dict to JSON string

    requests.post(url, json=payload)
