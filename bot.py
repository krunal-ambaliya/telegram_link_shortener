import os
import logging
import shelve
import urllib.parse
import requests
from dotenv import load_dotenv
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "8080"))
DATA_FILE = "user_tokens.db"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    with shelve.open(DATA_FILE) as db:
        if user_id not in db:
            await update.message.reply_text("Welcome! Please send your Shortner.in API token to start.")
            db[user_id] = ""
        else:
            await update.message.reply_text("You’re all set! Just send a link to shorten.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip()

    with shelve.open(DATA_FILE, writeback=True) as db:
        api_token = db.get(user_id)

        if not api_token:
            db[user_id] = text
            await update.message.reply_text("✅ API token saved! Now send me a link to shorten.")
            return

        if text.startswith("http"):
            encoded_url = urllib.parse.quote_plus(text)
            api_url = f"https://shortner.in/api?api={api_token}&url={encoded_url}&format=text"

            try:
                response = requests.get(api_url, timeout=10)
                short_url = response.text.strip()

                if short_url.startswith("http"):
                    await update.message.reply_text(f"🔗 Shortened Link:\n`{short_url}`", parse_mode="Markdown")
                else:
                    await update.message.reply_text("❌ Error shortening the link. Please check your API token or link.")
            except Exception as e:
                await update.message.reply_text("🚨 An error occurred. Try again later.")
        else:
            await update.message.reply_text("❌ Please send a valid URL (starting with http or https).")

# Telegram bot runner
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    from telegram import Update
    from telegram.ext import Application

    update = Update.de_json(request.get_json(force=True), None)
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Bot is running."

if __name__ == "__main__":
    from telegram.ext import Application

    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # For local testing
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()
    app_telegram.run_polling()
