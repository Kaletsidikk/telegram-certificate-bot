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

# Environment variables
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
RAILWAY_STATIC_URL = os.getenv("RAILWAY_STATIC_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "telegram")
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

ON_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
NAME, STUDENT_ID, CERTIFICATE = range(3)

# Create folder for certificates
os.makedirs("certificates", exist_ok=True)

CSV_FILE = "submissions.csv"

# Create CSV file if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "StudentID", "Username", "Time", "File"])


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Welcome!\n\nPlease enter your Full Name:")
    return NAME


# Get name
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Please enter your Student ID:")
    return STUDENT_ID


# Get student ID
async def get_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student_id"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Now send your certificate (PDF, image, or document)."
    )
    return CERTIFICATE


# Receive certificate
async def receive_certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    name = context.user_data.get("name")
    student_id = context.user_data.get("student_id")

    if not name or not student_id:
        await message.reply_text("Session expired. Please send /start again.")
        return ConversationHandler.END

    file = None
    filename = ""

    if message.document:
        file = await message.document.get_file()
        filename = message.document.file_name or f"{student_id}.bin"

    elif message.photo:
        file = await message.photo[-1].get_file()
        filename = f"{student_id}.jpg"

    else:
        await message.reply_text("Please send a valid certificate file.")
        return CERTIFICATE

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"certificates/{student_id}_{timestamp}_{filename}"

    await file.download_to_drive(filepath)

    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([name, student_id, user.username or "", time_now, filepath])

    await message.reply_text("✅ Certificate submitted successfully!")

    return ConversationHandler.END


# Admin command to download submissions
async def submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if user.id != ADMIN_ID:
        await message.reply_text("Unauthorized")
        return

    with open(CSV_FILE, "rb") as submissions_file:
        await message.reply_document(submissions_file)


# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Submission cancelled.")
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        logger.warning(
            "Telegram Conflict error (multiple polling instances). "
            "Use webhook mode on Railway by setting WEBHOOK_URL."
        )
        return

    logger.exception("Unhandled exception while processing update", exc_info=context.error)


# Main function
def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_student_id)],
            CERTIFICATE: [
                MessageHandler(filters.Document.ALL | filters.PHOTO, receive_certificate)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("submissions", submissions))
    app.add_error_handler(error_handler)

    webhook_base_url = (
        WEBHOOK_URL
        or RAILWAY_STATIC_URL
        or (f"https://{RAILWAY_PUBLIC_DOMAIN}" if RAILWAY_PUBLIC_DOMAIN else None)
    )

    if ON_RAILWAY and not webhook_base_url:
        logger.warning(
            "Railway detected but no webhook URL found. Falling back to polling mode. "
            "Set WEBHOOK_URL to avoid getUpdates conflicts when multiple instances run."
        )

    if webhook_base_url:
        webhook_path = WEBHOOK_PATH.strip("/") or "telegram"
        webhook_url = f"{webhook_base_url.rstrip('/')}/{webhook_path}"

        logger.info("Bot running in webhook mode on port %s", PORT)
        logger.info("Webhook base URL configured: %s", webhook_base_url)
        logger.info("Webhook path configured: /%s", webhook_path)

        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=webhook_url,
            secret_token=WEBHOOK_SECRET_TOKEN,
            drop_pending_updates=True,
        )
    else:
        logger.info("Bot running in polling mode")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()import csv
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

# Environment variables
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
RAILWAY_STATIC_URL = os.getenv("RAILWAY_STATIC_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "telegram")
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

ON_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
NAME, STUDENT_ID, CERTIFICATE = range(3)

# Create folder for certificates
os.makedirs("certificates", exist_ok=True)

CSV_FILE = "submissions.csv"

# Create CSV file if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "StudentID", "Username", "Time", "File"])


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Welcome!\n\nPlease enter your Full Name:")
    return NAME


# Get name
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("Please enter your Student ID:")
    return STUDENT_ID


# Get student ID
async def get_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student_id"] = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Now send your certificate (PDF, image, or document)."
    )
    return CERTIFICATE


# Receive certificate
async def receive_certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    name = context.user_data.get("name")
    student_id = context.user_data.get("student_id")

    if not name or not student_id:
        await message.reply_text("Session expired. Please send /start again.")
        return ConversationHandler.END

    file = None
    filename = ""

    if message.document:
        file = await message.document.get_file()
        filename = message.document.file_name or f"{student_id}.bin"

    elif message.photo:
        file = await message.photo[-1].get_file()
        filename = f"{student_id}.jpg"

    else:
        await message.reply_text("Please send a valid certificate file.")
        return CERTIFICATE

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"certificates/{student_id}_{timestamp}_{filename}"

    await file.download_to_drive(filepath)

    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([name, student_id, user.username or "", time_now, filepath])

    await message.reply_text("✅ Certificate submitted successfully!")

    return ConversationHandler.END


# Admin command to download submissions
async def submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if user.id != ADMIN_ID:
        await message.reply_text("Unauthorized")
        return

    with open(CSV_FILE, "rb") as submissions_file:
        await message.reply_document(submissions_file)


# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Submission cancelled.")
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        logger.warning(
            "Telegram Conflict error (multiple polling instances). "
            "Use webhook mode on Railway by setting WEBHOOK_URL."
        )
        return

    logger.exception("Unhandled exception while processing update", exc_info=context.error)


# Main function
def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_student_id)],
            CERTIFICATE: [
                MessageHandler(filters.Document.ALL | filters.PHOTO, receive_certificate)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("submissions", submissions))
    app.add_error_handler(error_handler)

    webhook_base_url = (
        WEBHOOK_URL
        or RAILWAY_STATIC_URL
        or (f"https://{RAILWAY_PUBLIC_DOMAIN}" if RAILWAY_PUBLIC_DOMAIN else None)
    )

    if ON_RAILWAY and not webhook_base_url:
        logger.warning(
            "Railway detected but no webhook URL found. Falling back to polling mode. "
            "Set WEBHOOK_URL to avoid getUpdates conflicts when multiple instances run."
        )

    if webhook_base_url:
        webhook_path = WEBHOOK_PATH.strip("/") or "telegram"
        webhook_url = f"{webhook_base_url.rstrip('/')}/{webhook_path}"

        logger.info("Bot running in webhook mode on port %s", PORT)
        logger.info("Webhook base URL configured: %s", webhook_base_url)
        logger.info("Webhook path configured: /%s", webhook_path)

        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=webhook_url,
            secret_token=WEBHOOK_SECRET_TOKEN,
            drop_pending_updates=True,
        )
    else:
        logger.info("Bot running in polling mode")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()