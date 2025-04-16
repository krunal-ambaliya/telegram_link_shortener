import os
import logging
import shelve
import urllib.parse
import requests
from dotenv import load_dotenv
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Dictionary to store user-specific API tokens
user_tokens = {}

load_dotenv()



BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "8080"))
DATA_FILE = "user_tokens.db"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_tokens:
        await update.message.reply_text("Please send your API token to get started.")
    else:
        await update.message.reply_text("You're all set! Send a link to shorten.")
        
# Handle API token message
async def save_api_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text.strip()
    if message.startswith("da"):  # rough check for API format
        user_tokens[user_id] = message
        await update.message.reply_text("API token saved. Now send a link to shorten!")
    else:
        await update.message.reply_text("That doesn't look like a valid API token. Try again.")

# /removeApi command
async def remove_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_tokens:
        del user_tokens[user_id]
        await update.message.reply_text("Your API token has been removed. Send a new one anytime.")
    else:
        await update.message.reply_text("No API token was set for you yet.")

# Shorten link
async def shorten_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    original_url = update.message.text.strip()
    if user_id not in user_tokens:
        await update.message.reply_text("Please send your API token first using /start.")
        return
    api_token = user_tokens[user_id]
    shortener_url = f"https://shortner.in/api?api={api_token}&url={original_url}&format=text"
    try:
        short_url = requests.get(shortener_url).text
        if short_url:
            await update.message.reply_text(f"Shortened URL: {short_url}")
        else:
            await update.message.reply_text("Failed to shorten the link. Make sure your API token is valid.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


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

# Main bot setup
if __name__ == '__main__':
    from dotenv import load_dotenv
    import os
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("removeApi", remove_api))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_api_token))  # handles both token and links
    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), shorten_link))

    app.run_polling()
