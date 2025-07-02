import os
import requests
from datetime import datetime, time
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Hard-coded credentials for local run
BOT_TOKEN   = '7855190653:AAHuTOvMc-0EyYj9K_KPxQfMd77b8Av4WOs'
CHANNEL_ID  = '@wheugroup'
GROUP_CHAT_ID = -4953278038

# European countries for holiday lookups
def get_countries():
    return {
        'PT': 'Portugal', 'ES': 'Spain', 'FR': 'France', 'BE': 'Belgium',
        'NL': 'Netherlands', 'LU': 'Luxembourg', 'DE': 'Germany', 'CH': 'Switzerland',
        'IT': 'Italy', 'AT': 'Austria', 'PL': 'Poland', 'GB': 'United Kingdom',
        'DK': 'Denmark', 'IE': 'Ireland', 'NO': 'Norway', 'SE': 'Sweden',
        'FI': 'Finland', 'GR': 'Greece', 'CZ': 'Czech Republic', 'SK': 'Slovakia',
        'HU': 'Hungary', 'SI': 'Slovenia', 'HR': 'Croatia', 'RO': 'Romania',
        'BG': 'Bulgaria', 'EE': 'Estonia', 'LV': 'Latvia', 'LT': 'Lithuania',
        'CY': 'Cyprus', 'MT': 'Malta', 'IS': 'Iceland', 'BA': 'Bosnia and Herzegovina',
        'RS': 'Serbia', 'ME': 'Montenegro', 'MK': 'North Macedonia', 'AL': 'Albania',
        'AD': 'Andorra', 'LI': 'Liechtenstein', 'UA': 'Ukraine', 'BY': 'Belarus',
        'RU': 'Russia'
    }
COUNTRIES = get_countries()

# Fetch public holidays

def get_holidays(country_code: str, year: int):
    url = f'https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}'
    r = requests.get(url)
    return r.json() if r.ok else []

# Scrape driving bans summary
def fetch_driving_bans():
    url = 'https://truckban.eu/'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    text = soup.get_text('\n')
    lines = [l.strip() for l in text.splitlines()]
    start = lines.index('General driving bans by countries for the whole year')
    end   = lines.index('Latest fuel prices')
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
    # collapse and return full text per country
    return {country: ' '.join(info) for country, info in bans.items()}

# /holiday command handler
async def holiday_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now(ZoneInfo('Europe/London')).date().isoformat()
    msgs = []
    for code, name in COUNTRIES.items():
        for h in get_holidays(code, datetime.now().year):
            if h['date'] == today:
                msgs.append(f"📅 Today in {name}: {h['localName']}")
    await update.message.reply_text('\n'.join(msgs) if msgs else 'No holidays today.')

# /drivingban command handler with simplified messages
async def drivingban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bans = fetch_driving_bans()
    for country, info in bans.items():
        # take only the first sentence to simplify
        summary = info.split('.')[0].strip() + '.'
        await update.message.reply_text(f"🚚 {country} (>7.5 t): {summary}")

# Scheduled daily job
async def scheduled_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    today = datetime.now(ZoneInfo('Europe/London')).date().isoformat()
    # Holiday alerts for today
    for code, name in COUNTRIES.items():
        for h in get_holidays(code, datetime.now().year):
            if h['date'] == today:
                text = f"📅 Today in {name}: {h['localName']}"
                for cid in (CHANNEL_ID, GROUP_CHAT_ID):
                    await bot.send_message(cid, text)
    # Driving-ban summaries simplified
    bans = fetch_driving_bans()
    for country, info in bans.items():
        summary = info.split('.')[0].strip() + '.'
        msg = f"🚚 {country} (>7.5 t): {summary}"
        for cid in (CHANNEL_ID, GROUP_CHAT_ID):
            await bot.send_message(cid, msg)

# Main entrypoint
async def main() -> None:
    app = (ApplicationBuilder()
           .token(BOT_TOKEN)
           .post_init(lambda bot_app: bot_app.bot.set_my_commands([
               BotCommand('holiday', "Show today's European holidays"),
               BotCommand('drivingban', "Show driving-ban rules for >7.5 t")
           ]))
           .build())
    app.add_handler(CommandHandler('holiday', holiday_handler))
    app.add_handler(CommandHandler('drivingban', drivingban_handler))
    # schedule daily at 09:00 Europe/London
    tz = ZoneInfo('Europe/London')
    app.job_queue.run_daily(scheduled_job, time(9, 0, tzinfo=tz))
    print("Bot started — polling for commands...")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
