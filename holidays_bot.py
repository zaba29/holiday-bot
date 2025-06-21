import os
import requests
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

BOT_TOKEN  = os.environ['BOT_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']

# Western Europe countries
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
    for code, country_name in COUNTRIES.items():
        for h in get_holidays(code, today.year):
            h_date = datetime.fromisoformat(h['date']).date()
            if (h_date - today).days == 2:
                # formatted date
                formatted_date = h_date.strftime("%a %d %b %Y")
                # determine holiday type
                h_type = "Public holiday"
                types = h.get("types") or []
                if types:
                    t = types[0].lower()
                    if t == "bank":
                        h_type = "Bank holiday"
                    else:
                        h_type = f"{types[0].capitalize()} holiday"
                # regional notes
                counties = h.get("counties") or []
                region_line = f"📍 Regions: {', '.join(counties)}" if counties else ""
                # build message
                lines = [
                    f"📅 {country_name} – {h['localName']}",
                    f"🗓️ {formatted_date} | {h_type}"
                ]
                if region_line:
                    lines.append(region_line)
                message = "\n".join(lines)
                send_message(message)
                print(f"{datetime.now()}: Sent holiday alert – {message}")

def fetch_driving_bans():
    url  = "https://truckban.eu/"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    text = soup.get_text("\n")
    lines = [l.strip() for l in text.splitlines()]
    start = lines.index("General driving bans by countries for the whole year")
    end   = lines.index("Latest fuel prices")
    bans  = {}
    current = None

    for line in lines[start+1:end]:
        if not line:
            continue
        if line in COUNTRIES.values():
            current = line
            bans[current] = []
        elif current:
            bans[current].append(line)

    return {k: " ".join(v) for k, v in bans.items()}

def check_driving_bans():
    bans = fetch_driving_bans()
    for country in COUNTRIES.values():
        info = bans.get(country, "No general ban info found.")
        msg = f"🚚 {country} (> 7.5 t): {info}"
        send_message(msg)
        print(f"{datetime.now()}: Sent driving-ban for {country}")

def daily_job():
    check_holidays()
    check_driving_bans()

if __name__ == "__main__":
    # run once immediately…
    daily_job()
    # …then schedule every day at 09:00 Europe/London
    scheduler = BlockingScheduler(timezone=ZoneInfo("Europe/London"))
    scheduler.add_job(daily_job, 'cron', hour=9, minute=0)
    scheduler.start()
