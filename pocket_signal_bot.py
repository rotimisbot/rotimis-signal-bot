import os, logging, requests
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
BOT_TOKEN = "8654604992:AAEXAYJlgjKuSDAufljDHdrVn30oC5Njj-Y"
ASSETS = {"EURUSD":"EURUSD=X","GBPUSD":"GBPUSD=X","BTCUSD":"BTC-USD","GOLD":"GC=F"}

def fetch_prices(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        r = requests.get(url, params={"interval":"5m","range":"1d"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        closes = r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        return [c for c in closes if c is not None][-60:]
    except: return []

def rsi(prices):
    if len(prices) < 15: return 50.0
    gains = [abs(prices[-i]-prices[-i-1]) for i in range(1,15) if prices[-i]>prices[-i-1]]
    losses = [abs(prices[-i]-prices[-i-1]) for i in range(1,15) if prices[-i]<=prices[-i-1]]
    ag = sum(gains)/14 if gains else 0
    al = sum(losses)/14 if losses else 0.0001
    return round(100-(100/(1+ag/al)),2)

def ma(prices, n):
    return sum(prices[-n:])/n if len(prices)>=n else prices[-1]

def analyse(key):
    ticker = ASSETS.get(key.upper())
    if not ticker: return None
    prices = fetch_prices(ticker)
    if len(prices) < 30: return None
    price = prices[-1]
    r = rsi(prices)
    ma10 = ma(prices,10)
    ma30 = ma(prices,30)
    score = 0
    if r < 35: score += 2
    elif r < 45: score += 1
    elif r > 65: score -= 2
    elif r > 55: score -= 1
    if ma10 > ma30: score += 2
    elif ma10 < ma30: score -= 2
    if price > ma10: score += 1
    else: score -= 1
    direction = "BUY" if score > 0 else "SELL"
    confidence = min(95, 50 + abs(score)*8)
    strength = "STRONG" if abs(score)>=4 else "MODERATE" if abs(score)>=2 else "WEAK"
    return {"asset":key.upper(),"direction":direction,"confidence":confidence,"strength":strength,"price":round(price,5),"rsi":r,"timestamp":datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}

def fmt(s):
    arrow = "📈" if s["direction"]=="BUY" else "📉"
    action = "🟢 *BUY / CALL*" if s["direction"]=="BUY" else "🔴 *SELL / PUT*"
    expiry = "1-5 min" if s["strength"]=="STRONG" else "5-15 min"
    bar = "█"*int(s["confidence"]/10) + "░"*(10-int(s["confidence"]/10))
    return (f"{arrow} *POCKET OPTION SIGNAL*\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Asset:* `{s['asset']}`\n💰 *Price:* `{s['price']}`\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{action}\n💪 *Strength:* `{s['strength']}`\n📶 *Confidence:* `{s['confidence']}%`\n"
            f"   `{bar}`\n⏱ *Expiry:* `{expiry}`\n📉 *RSI:* `{s['rsi']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n🕐 `{s['timestamp']}`\n\n⚠️ _Not financial advice._")

def keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("EURUSD"),KeyboardButton("GBPUSD")],[KeyboardButton("BTCUSD"),KeyboardButton("GOLD")],[KeyboardButton("📊 ALL SIGNALS")]],resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 *Welcome to Rotimi Signal Bot!*\n\nTap an asset to get BUY or SELL signal! 🚀",parse_mode=ParseMode.MARKDOWN,reply_markup=keyboard())

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper().replace(" ","")
    if text in ["📊ALLSIGNALS","ALLSIGNALS"]:
        await update.message.reply_text("⏳ Analysing all assets...")
        results = []
        for key in ["EURUSD","GBPUSD","BTCUSD","GOLD"]:
            s = analyse(key)
            if s:
                arrow = "📈" if s["direction"]=="BUY" else "📉"
                results.append(f"{arrow} `{key}` — *{s['direction']}* `{s['confidence']}%`")
        await update.message.reply_text("📊 *Signal Summary*\n━━━━━━━━━━━━━━━\n"+"\n".join(results),parse_mode=ParseMode.MARKDOWN,reply_markup=keyboard())
        return
    if text in ASSETS:
        await update.message.reply_text(f"⏳ Analysing {text}...")
        s = analyse(text)
        if s:
            await update.message.reply_text(fmt(s),parse_mode=ParseMode.MARKDOWN,reply_markup=keyboard())
        else:
            await update.message.reply_text("⚠️ Could not fetch data. Try again.",reply_markup=keyboard())
        return
    await update.message.reply_text("❓ Tap a button below!",reply_markup=keyboard())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
