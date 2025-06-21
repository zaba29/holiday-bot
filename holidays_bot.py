import os
import requests
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

BOT_TOKEN  = os.environ['BOT_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']

# 1) All Western Europe countries
COUNTRIES = {
    'PT': 'Portugal',
    'ES': 'Spain',
    'FR': 'France',
    'BE': 'Belgium',
    'NL': 'Netherlands',
    'LU': 'Luxembourg',
    'DE': 'Germany',
    'CH': 'Switzerland',
    'IT': 'Italy',
    'AT': 'Austria',
    'PL': 'Poland'
}

def send_message(text: str):
    url  = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    resp = requests.post(url, data={'chat_id': CHANNEL_ID, 'text': text})
    if not resp.ok:
        print(f"⚠️ Failed to send message: {resp.status_code} {resp.text}")

def get_holidays(country_code: str, year: int):
    url  = f'https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}'
    resp = requests.get(url)
    return resp.json() if resp.status_code == 200 else []

def check_holidays():
    today = datetime.now(ZoneInfo("Europe/London")).date()
    for code, name in COUNTRIES.items():
        for h in get_holidays(code, today.year):
            h_date = datetime.fromisoformat(h['date']).date()
            # 2) Exactly 2 days before
            if (h_date - today).days == 2:
                msg = (
                    f"📅 Holiday in {name}: "
                    f"{h['localName']} ({h['name']}) on {h['date']} — in 2 days!"
                )
                send_message(msg)
                print(f"{datetime.now()}: Sent holiday alert – {msg}")

def fetch_driving_bans():
    url  = "https://truckban.eu/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    text = soup.get_text("\n")
    lines = [l.strip() for l in text.splitlines()]
    start = lines.index("General driving bans by countries for the whole year")
    end   = lines.index("Latest fuel prices")
    bans = {}
    current = None

    for line in lines[start+1:end]:
        if not line:
            continue
        if line in COUNTRIES.values():
            current = line
            bans[current] = []
        elif current:
            bans[current].append(line)

    for k in bans:
        bans[k] = " ".join(bans[k])

    return bans

def check_driving_bans():
    bans = fetch_driving_bans()
    parts = []
    for name in COUNTRIES.values():
        info = bans.get(name, "No general ban info found.")
        parts.append(f"*{name}*: {info}")
    summary = "🚚 General driving-ban rules (> 7.5 t):\n" + "\n".join(parts)
    send_message(summary)
    print(f"{datetime.now()}: Sent driving-ban summary")

def daily_job():
    check_holidays()
    check_driving_bans()

if __name__ == "__main__":
    # Run once immediately...
    daily_job()
    # …then schedule every day at 09:00 Europe/London
    scheduler = BlockingScheduler(timezone=ZoneInfo("Europe/London"))
    scheduler.add_job(daily_job, 'cron', hour=9, minute=0)
    scheduler.start()
