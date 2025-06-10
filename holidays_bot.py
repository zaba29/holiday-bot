import os
import requests
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from zoneinfo import ZoneInfo

BOT_TOKEN   = os.environ['BOT_TOKEN']
CHANNEL_ID  = os.environ['CHANNEL_ID']

COUNTRIES = {
    'FR': 'France',
    'IT': 'Italy',
    'DE': 'Germany',
    'CH': 'Switzerland'
}

def send_message(text: str):
    url  = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    resp = requests.post(url, data={'chat_id': CHANNEL_ID, 'text': text})
    if not resp.ok:
        print(f"Failed to send message: {resp.status_code} {resp.text}")

def get_holidays(country_code: str, year: int):
    url  = f'https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}'
    resp = requests.get(url)
    return resp.json() if resp.status_code == 200 else []

def check_and_alert():
    today = datetime.now(ZoneInfo("Europe/London")).date()
    for code, name in COUNTRIES.items():
        for h in get_holidays(code, today.year):
            h_date   = datetime.fromisoformat(h['date']).date()
            delta    = (h_date - today).days
            if delta in (1, 2):
                msg = (f"Upcoming holiday in {name}: "
                       f"{h['localName']} ({h['name']}) on {h['date']}.")
                send_message(msg)
                print(f"{datetime.now()}: Sent – {msg}")

if __name__ == "__main__":
    # immediate run
    check_and_alert()

    # schedule daily at 09:00 Europe/London
    scheduler = BlockingScheduler(timezone=ZoneInfo("Europe/London"))
    scheduler.add_job(check_and_alert, 'cron', hour=9, minute=0)
    scheduler.start()
