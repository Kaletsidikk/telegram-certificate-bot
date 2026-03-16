import csv
import logging
import os
from datetime import datetime

from telegram import Update
from telegram.error import Conflict
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Basic config
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CSV_FILE = "submissions.csv"
os.makedirs("certificates", exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
NAME, STUDENT_ID, CERTIFICATE = range(3)

# Create CSV header if missing
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "StudentID", "Username", "Time", "File"])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome!\n\nPlease enter your Full Name:")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Please enter your Student ID:")
    return STUDENT_ID


async def get_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student_id"] = update.message.text.strip()
    await update.message.reply_text("Now send your certificate (PDF, image, or document).")
    return CERTIFICATE


async def receive_certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user

    name = context.user_data.get("name")
    student_id = context.user_data.get("student_id")

    if not name or not student_id:
        await message.reply_text("Session expired. Please send /start again.")
        return ConversationHandler.END

    if message.document:
        tg_file = await message.document.get_file()
        filename = message.document.file_name or f"{student_id}.bin"
    elif message.photo:
        tg_file = await message.photo[-1].get_file()
        filename = f"{student_id}.jpg"
    else:
        await message.reply_text("Please send a valid certificate file.")
        return CERTIFICATE

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"certificates/{student_id}_{timestamp}_{filename}"
    await tg_file.download_to_drive(filepath)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            name,
            student_id,
            user.username or "",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            filepath,
        ])

    await message.reply_text("✅ Certificate submitted successfully!")
    return ConversationHandler.END


async def submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return

    with open(CSV_FILE, "rb") as f:
        await update.message.reply_document(f)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Submission cancelled.")
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        logger.warning(
            "Telegram polling conflict: another process is using this bot token. "
            "Stop duplicate instances or switch to webhook mode in production."
        )
        return

    logger.exception("Unhandled bot error", exc_info=context.error)


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_student_id)],
            CERTIFICATE: [MessageHandler(filters.Document.ALL | filters.PHOTO, receive_certificate)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("submissions", submissions))
    app.add_error_handler(error_handler)

    logger.info("Bot running (polling mode)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()