cd ~/holiday-bot
cat > holidays_bot.py << 'EOF'
import os
import requests
from datetime import datetime, time
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from telegram import Bot, BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN  = os.environ['BOT_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']

COUNTRIES = {
    'PT': 'Portugal','ES': 'Spain','FR': 'France','BE': 'Belgium',
    'NL': 'Netherlands','LU': 'Luxembourg','DE': 'Germany','CH': 'Switzerland',
    'IT': 'Italy','AT': 'Austria','PL': 'Poland','GB': 'United Kingdom',
    'DK': 'Denmark','IE': 'Ireland','NO': 'Norway','SE': 'Sweden',
    'FI': 'Finland','GR': 'Greece','CZ': 'Czech Republic','SK': 'Slovakia',
    'HU': 'Hungary','SI': 'Slovenia','HR': 'Croatia','RO': 'Romania',
    'BG': 'Bulgaria','EE': 'Estonia','LV': 'Latvia','LT': 'Lithuania',
    'CY': 'Cyprus','MT': 'Malta','IS': 'Iceland','BA': 'Bosnia and Herzegovina',
    'RS': 'Serbia','ME': 'Montenegro','MK': 'North Macedonia','AL': 'Albania',
    'AD': 'Andorra','LI': 'Liechtenstein','UA': 'Ukraine','BY': 'Belarus',
    'RU': 'Russia'
}

def get_holidays(cc, year):
    url = f'https://date.nager.at/api/v3/PublicHolidays/{year}/{cc}'
    r = requests.get(url)
    return r.json() if r.ok else []

def fetch_driving_bans():
    r = requests.get('https://truckban.eu/')
    lines = [l.strip() for l in BeautifulSoup(r.text, 'html.parser').get_text('\n').splitlines()]
    start = lines.index('General driving bans by countries for the whole year')
    end   = lines.index('Latest fuel prices')
    bans, cur = {}, None
    for line in lines[start+1:end]:
        if not line: continue
        if line in COUNTRIES.values():
            cur = line; bans[cur]=[]
        elif cur:
            bans[cur].append(line)
    return {c: ' '.join(v) for c,v in bans.items()}

async def holiday_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(ZoneInfo('Europe/London')).date().isoformat()
    msgs = [f"📅 Today in {COUNTRIES[cc]}: {h['localName']}"
            for cc in COUNTRIES
            for h in get_holidays(cc, datetime.now().year)
            if h['date']==today]
    await update.message.reply_text('\n'.join(msgs) or 'No holidays today.')

async def drivingban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bans = fetch_driving_bans()
    for country, info in bans.items():
        summary = info.split('.')[0].strip() + '.'
        await update.message.reply_text(f"🚚 {country} (>7.5 t): {summary}")

async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    today = datetime.now(ZoneInfo('Europe/London')).date().isoformat()
    for cc in COUNTRIES:
        for h in get_holidays(cc, datetime.now().year):
            if h['date']==today:
                text = f"📅 Today in {COUNTRIES[cc]}: {h['localName']}"
                await bot.send_message(CHANNEL_ID, text)
    bans = fetch_driving_bans()
    for country, info in bans.items():
        summary = info.split('.')[0].strip() + '.'
        msg = f"🚚 {country} (>7.5 t): {summary}"
        await bot.send_message(CHANNEL_ID, msg)

async def main():
    # One‐off for GH Actions:
    if os.getenv('GITHUB_ACTIONS'):
        from telegram import Bot
        ctx = type('Ctx', (), {})(); ctx.bot = Bot(BOT_TOKEN)
        await scheduled_job(ctx); return

    app = (ApplicationBuilder()
           .token(BOT_TOKEN)
           .post_init(lambda a: a.bot.set_my_commands([
               BotCommand('holiday',   "Show today's holidays"),
               BotCommand('drivingban',"Show >7.5 t driving bans")
           ])).build())

    app.add_handler(CommandHandler('holiday', holiday_handler))
    app.add_handler(CommandHandler('drivingban', drivingban_handler))
    tz = ZoneInfo('Europe/London')
    app.job_queue.run_daily(scheduled_job, time(9,0,tzinfo=tz))

    print("Bot started — polling…")
    await app.run_polling()

if __name__=='__main__':
    import asyncio; asyncio.run(main())
EOF
