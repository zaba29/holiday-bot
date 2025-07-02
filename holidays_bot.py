import os
from telegram import Bot
import requests
from datetime import datetime, time
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Read credentials & targets from env (or fall back for local dev)
BOT_TOKEN     = os.environ['BOT_TOKEN']
CHANNEL_ID    = os.environ['CHANNEL_ID']
GROUP_CHAT_ID = int(os.environ['GROUP_CHAT_ID'])

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

def get_holidays(country_code: str, year: int):
    url = f'https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}'
    r = requests.get(url)
    return r.json() if r.ok else []

def fetch_driving_bans():
    r = requests.get('https://truckban.eu/')
    lines = [l.strip() for l in BeautifulSoup(r.text, 'html.parser').get_text('\n').splitlines()]
    start = lines.index('General driving bans by countries for the whole year')
    end   = lines.index('Latest fuel prices')
    bans, current = {}, None
    for line in lines[start+1:end]:
        if not line: continue
        if line in COUNTRIES.values():
            current = line
            bans[current] = []
        elif current:
            bans[current].append(line)
    return {c: ' '.join(info) for c, info in bans.items()}

async def holiday_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now(ZoneInfo('Europe/London')).date().isoformat()
    msgs = []
    for cc, name in COUNTRIES.items():
        for h in get_holidays(cc, datetime.now().year):
            if h['date'] == today:
                msgs.append(f"📅 Today in {name}: {h['localName']}")
    await update.message.reply_text('\n'.join(msgs) or 'No holidays today.')

async def drivingban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bans = fetch_driving_bans()
    for country, info in bans.items():
        summary = info.split('.')[0].strip() + '.'
        await update.message.reply_text(f"🚚 {country} (>7.5 t): {summary}")

async def scheduled_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    today = datetime.now(ZoneInfo('Europe/London')).date().isoformat()
    # Holiday alerts
    for cc, name in COUNTRIES.items():
        for h in get_holidays(cc, datetime.now().year):
            if h['date'] == today:
                text = f"📅 Today in {name}: {h['localName']}"
                for chat in (CHANNEL_ID, GROUP_CHAT_ID):
                    await bot.send_message(chat, text)
    # Driving-ban summaries
    bans = fetch_driving_bans()
    for country, info in bans.items():
        summary = info.split('.')[0].strip() + '.'
        msg = f"🚚 {country} (>7.5 t): {summary}"
        for chat in (CHANNEL_ID, GROUP_CHAT_ID):
            await bot.send_message(chat, msg)

async def main() -> None:
    # In GitHub Actions, do one scheduled run then exit
    if os.getenv("GITHUB_ACTIONS"):
        ctx = type('Ctx', (), {})()
        ctx.bot = Bot(BOT_TOKEN)
        await scheduled_job(ctx)
        return

    # Otherwise (local), start interactive polling + schedule
    app = (ApplicationBuilder()
           .token(BOT_TOKEN)
           .post_init(lambda a: a.bot.set_my_commands([
               BotCommand('holiday', "Show today's European holidays"),
               BotCommand('drivingban', "Show driving-ban rules for >7.5 t")
           ]))
           .build())

    app.add_handler(CommandHandler('holiday', holiday_handler))
    app.add_handler(CommandHandler('drivingban', drivingban_handler))

    tz = ZoneInfo('Europe/London')
    app.job_queue.run_daily(scheduled_job, time(9, 0, tzinfo=tz))

    print("Bot started — polling for commands…")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
