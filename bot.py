import csv
import os
from datetime import datetime

from telegram import Update
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

# Conversation states
NAME, STUDENT_ID, CERTIFICATE = range(3)

# Storage setup
CERTIFICATES_DIR = "certificates"
CSV_FILE = "submissions.csv"
os.makedirs(CERTIFICATES_DIR, exist_ok=True)

# Create CSV header if needed
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "StudentID", "Username", "Time", "File"])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start submission flow."""
    await update.message.reply_text("Welcome!\n\nPlease enter your Full Name:")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store student's full name and ask for student ID."""
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Please enter your Student ID:")
    return STUDENT_ID


async def get_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store student ID and ask for certificate file."""
    context.user_data["student_id"] = update.message.text.strip()
    await update.message.reply_text("Now send your certificate (PDF, image, or document).")
    return CERTIFICATE


async def receive_certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Accept certificate file, store it, and log submission to CSV."""
    message = update.message
    user = message.from_user

    name = context.user_data.get("name")
    student_id = context.user_data.get("student_id")

    if not name or not student_id:
        await message.reply_text("Session expired. Please send /start again.")
        return ConversationHandler.END

    tg_file = None
    filename = ""

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
    filepath = f"{CERTIFICATES_DIR}/{student_id}_{timestamp}_{filename}"
    await tg_file.download_to_drive(filepath)

    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            name,
            student_id,
            user.username or "",
            submitted_at,
            filepath,
        ])

    await message.reply_text("✅ Certificate submitted successfully!")
    return ConversationHandler.END


async def submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to download submissions CSV."""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return

    with open(CSV_FILE, "rb") as f:
        await update.message.reply_document(f)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current submission flow."""
    await update.message.reply_text("Submission cancelled.")
    return ConversationHandler.END


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = ApplicationBuilder().token(TOKEN).build()

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

    print("Bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()