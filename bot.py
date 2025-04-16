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

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /setapi to send your API token.")

# /setapi command
async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 Please send your API token now:")

# Handle message: detect if it's API token or a link
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip()

    with shelve.open(DATA_FILE, writeback=True) as db:
        # If user hasn't set token and message starts with "da" → treat as API token
        if user_id not in db:
            if text.startswith("da"):
                db[user_id] = text
                await update.message.reply_text("✅ API token saved! Now send a link to shorten.")
            else:
                await update.message.reply_text("❌ Please send your API token first using /setapi.")
            return

        # If token exists → try shortening URL
        if text.startswith("http"):
            api_token = db[user_id]
            encoded_url = urllib.parse.quote_plus(text)
            api_url = f"https://shortner.in/api?api={api_token}&url={encoded_url}&format=text"

            try:
                response = requests.get(api_url, timeout=10)
                short_url = response.text.strip()
                if short_url.startswith("http"):
                    await update.message.reply_text(f"🔗 Shortened Link:\n`{short_url}`", parse_mode="Markdown")
                else:
                    await update.message.reply_text("❌ Invalid API token or link. Please check and try again.")
            except Exception as e:
                await update.message.reply_text("🚨 An error occurred while shortening.")
        else:
            await update.message.reply_text("❌ Send a valid URL starting with http/https.")

# /removeApi command
async def remove_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    with shelve.open(DATA_FILE, writeback=True) as db:
        if user_id in db:
            del db[user_id]
            await update.message.reply_text("🗑️ API token removed. Use /setapi to set a new one.")
        else:
            await update.message.reply_text("⚠️ No API token was found for your account.")

# Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), None)
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setapi", set_api))
    application.add_handler(CommandHandler("removeApi", remove_api))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.process_update(update)
    return "ok"

# Test home route
@app.route("/")
def home():
    return "🤖 Bot is running!"

# Start app for Railway deployment
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setapi", set_api))
    app.add_handler(CommandHandler("removeApi", remove_api))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()
