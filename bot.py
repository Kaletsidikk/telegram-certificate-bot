import os
import csv
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Environment variables
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
PORT = int(os.getenv("PORT", "8080"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Conversation states
NAME, STUDENT_ID, CERTIFICATE = range(3)

# Create certificates folder
os.makedirs("certificates", exist_ok=True)

CSV_FILE = "submissions.csv"

# Create CSV file if it does not exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "StudentID", "Username", "Time", "File"])


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome!\n\nPlease enter your Full Name:"
    )
    return NAME


# Get name
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Please enter your Student ID:")
    return STUDENT_ID


# Get student ID
async def get_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student_id"] = update.message.text
    await update.message.reply_text(
        "Please upload your Certificate (PDF, Image, or Document):"
    )
    return CERTIFICATE


# Receive certificate
async def receive_certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.message.from_user
    name = context.user_data.get("name")
    student_id = context.user_data.get("student_id")
    username = user.username or "N/A"

    file = None

    if update.message.document:
        file = update.message.document
    elif update.message.photo:
        file = update.message.photo[-1]

    if file is None:
        await update.message.reply_text("Please upload a valid certificate file.")
        return CERTIFICATE

    file_obj = await file.get_file()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{student_id}_{timestamp}"

    if update.message.document:
        filename += f"_{file.file_name}"
    else:
        filename += ".jpg"

    filepath = os.path.join("certificates", filename)

    await file_obj.download_to_drive(filepath)

    # Save to CSV
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([name, student_id, username, timestamp, filename])

    await update.message.reply_text("✅ Certificate submitted successfully!")

    return ConversationHandler.END


# Admin command to download submissions
async def submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return

    await update.message.reply_document(open(CSV_FILE, "rb"))


# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Submission cancelled.")
    return ConversationHandler.END


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
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("submissions", submissions))

    webhook_base_url = WEBHOOK_URL or (
        f"https://{RAILWAY_PUBLIC_DOMAIN}" if RAILWAY_PUBLIC_DOMAIN else None
    )

    if webhook_base_url:
        webhook_path = TOKEN
        webhook_url = f"{webhook_base_url.rstrip('/')}/{webhook_path}"

        logger.info("Bot running in webhook mode on port %s", PORT)
        logger.info("Webhook URL: %s", webhook_url)

        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=webhook_url,
            drop_pending_updates=True,
        )
    else:
        logger.info("Bot running in polling mode")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()