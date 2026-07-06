import os
import logging
import requests
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

ASSETS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "BTCUSD": "BTC-USD",
    "GOLD": "GC=F",
}
def analyse(asset_key):
    ticker = ASSETS.get(asset_key.upper())
    if not ticker:
        return None
    prices = fetch_prices(ticker, 60)
    if len(prices) < 30:
        return None
    price = prices[-1]
    rsi = compute_rsi(prices)
    ma10 = compute_ma(prices, 10)
    ma30 = compute_ma(prices, 30)
    score = 0
    if rsi < 35: score += 2
    elif rsi < 45: score += 1
    elif rsi > 65: score -= 2
    elif rsi > 55: score -= 1
    if ma10 > ma30: score += 2
    elif ma10 < ma30: score -= 2
    if price > ma10: score += 1
    else: score -= 1
    direction = "BUY" if score > 0 else "SELL"
    confidence = min(95, 50 + abs(score) * 8)
    strength = "STRONG" if abs(score) >= 4 else "MODERATE" if abs(score) >= 2 else "WEAK"
    return {
        "asset": asset_key.upper(),
        "direction": direction,
        "confidence": confidence,
        "strength": strength,
        "price": round(price, 5),
        "rsi": rsi,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
def format_signal(s):
    is_buy = s["direction"] == "BUY"
    arrow = "📈" if is_buy else "📉"
    action = "🟢 *BUY / CALL*" if is_buy else "🔴 *SELL / PUT*"
    expiry = "1-5 min" if s["strength"] == "STRONG" else "5-15 min"
    conf_filled = int(s["confidence"] / 10)
    conf_bar = "█" * conf_filled + "░" * (10 - conf_filled)
    return (
        f"{arrow} *POCKET OPTION SIGNAL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Asset:* `{s['asset']}`\n"
        f"💰 *Price:* `{s['price']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{action}\n"
        f"💪 *Strength:* `{s['strength']}`\n"
        f"📶 *Confidence:* `{s['confidence']}%`\n"
        f"   `{conf_bar}`\n"
        f"⏱ *Expiry:* `{expiry}`\n"
        f"📉 *RSI:* `{s['rsi']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 `{s['timestamp']}`\n\n"
        f"⚠️ _Not financial advice. Manage your risk._"
    )

def main_keyboard():
    buttons = [
        [KeyboardButton("EURUSD"), KeyboardButton("GBPUSD")],
        [KeyboardButton("BTCUSD"), KeyboardButton("GOLD")],
        [KeyboardButton("📊 ALL SIGNALS")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to Rotimi Signal Bot!*\n\n"
        "Tap an asset to get BUY or SELL signal! 🚀\n\n"
        "Supported: EURUSD GBPUSD BTCUSD GOLD",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard(),
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper().replace(" ", "")
    if text in ["📊 ALL SIGNALS", "ALL SIGNALS"]:
        await update.message.reply_text("⏳ Analysing all assets...")
        results = []
        for key in ["EURUSD", "GBPUSD", "BTCUSD", "GOLD"]:
            s = analyse(key)
            if s:
                arrow = "📈" if s["direction"] == "BUY" else "📉"
                results.append(f"{arrow} `{key}` — *{s['direction']}* `{s['confidence']}%`")
        await update.message.reply_text(
            "📊 *Signal Summary*\n━━━━━━━━━━━━━━━\n" + "\n".join(results),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard(),
        )
        return
    if text in ASSETS:
        await update.message.reply_text(f"⏳ Analysing {text}...")
        s = analyse(text)
        if s:
            await update.message.reply_text(
                format_signal(s),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_keyboard(),
            )
        else:
            await update.message.reply_text("⚠️ Could not fetch data. Try again.")
        return
    await update.message.reply_text("❓ Tap a button below!", reply_markup=main_keyboard())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
