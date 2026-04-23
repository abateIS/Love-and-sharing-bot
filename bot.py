import logging
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# --- CONFIGURATION ---
BOT_TOKEN = "8799539357:AAGwznJ1CLDdvJaH5YXBf-WvOGtRHE48Lv0"
TEAM_CHAT_ID = -1003925691311 
CBE_ACCOUNT = "1000726186964"

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
ASKING_NAME, ASKING_GENDER, ASKING_MATERIAL, ASKING_PHONE = range(4)

# --- HANDLERS ---

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🙋‍♂️ Ask Support", callback_data="ask_support")],
        [InlineKeyboardButton("💰 Donate", callback_data="donate")],
    ]
    await update.message.reply_text(
        "👋 Welcome to the **Love Sharing Team Bot**!\n\nHow can we help you today?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def button_click(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "donate":
        await query.message.reply_text(
            f"💰 **Donation Information**\n\n🏦 **CBE Account:** `{CBE_ACCOUNT}`\n\nMay God bless you!",
            parse_mode="Markdown"
        )
    elif query.data == "ask_support":
        await query.message.reply_text("📝 **New Support Request**\n\nWhat is your **Full Name**?")
        return ASKING_NAME

async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["name"] = update.message.text
    await update.message.reply_text(
        f"Thank you, {ctx.user_data['name']}.\n\nWhat is your **Gender**?",
        reply_markup=ReplyKeyboardMarkup([["Male", "Female"]], one_time_keyboard=True, resize_keyboard=True),
    )
    return ASKING_GENDER

async def get_gender(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["gender"] = update.message.text
    materials = [["Clothing", "Medicine"], ["Learning Materials", "Other"]]
    await update.message.reply_text(
        "What do you need?",
        reply_markup=ReplyKeyboardMarkup(materials, one_time_keyboard=True, resize_keyboard=True),
    )
    return ASKING_MATERIAL

async def get_material(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["material"] = update.message.text
    await update.message.reply_text("Please enter your **Phone Number**:", reply_markup=ReplyKeyboardRemove())
    return ASKING_PHONE

async def get_phone_and_submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["phone"] = update.message.text
    user = update.effective_user
    username = f"@{user.username}" if user.username else "No Username"

    await update.message.reply_text("✅ **Thank you!** Your request has been sent.")

    admin_message = (
        f"🚨 **New Support Request**\n\n👤 **Name:** {ctx.user_data['name']}\n"
        f"🚻 **Gender:** {ctx.user_data['gender']}\n📦 **Needs:** {ctx.user_data['material']}\n"
        f"📞 **Phone:** `{ctx.user_data['phone']}`\n💬 **Telegram:** {username}"
    )
    await ctx.bot.send_message(chat_id=TEAM_CHAT_ID, text=admin_message, parse_mode="Markdown")
    return ConversationHandler.END

# --- HUGGING FACE STABILITY ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        # Silence the flood of health check logs
        return

def run_health_check_server():
    # Render uses port 10000 by default for health checks
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    """Survival mode for Hugging Face."""
    print("DEBUG: Setting up bot handlers...")
    
    # Use longer timeouts to fight the server lag
    request = HTTPXRequest(connect_timeout=30, read_timeout=30)
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(request)
        .build()
    )
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_click, pattern="^ask_support$")],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASKING_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            ASKING_MATERIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_material)],
            ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone_and_submit)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click, pattern="^donate$"))
    application.add_handler(conv_handler)

    # Start health server in background (HF needs this on port 7860)
    threading.Thread(target=run_health_check_server, daemon=True).start()

    print("--- STARTING CONNECTION LOOP ---")
    
    while True:
        try:
            logger.info("Attempting to connect to Telegram...")
            application.run_polling(drop_pending_updates=True)
            break 
        except Exception as e:
            logger.error(f"Network error: {e}. Retrying in 15 seconds...")
            time.sleep(15)

if __name__ == "__main__":
    main()
