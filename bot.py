import os
import csv
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

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

NAME, STUDENT_ID, CERTIFICATE = range(3)

os.makedirs("certificates", exist_ok=True)

CSV_FILE = "submissions.csv"

# Create CSV file if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "StudentID", "Username", "Time", "File"])


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("User started bot")
    await update.message.reply_text("Welcome! Please enter your Full Name:")
    return NAME


# GET NAME
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Enter your Student ID:")
    return STUDENT_ID


# GET STUDENT ID
async def get_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student_id"] = update.message.text
    await update.message.reply_text(
        "Now send your certificate (PDF, image, or document)."
    )
    return CERTIFICATE


# RECEIVE FILE
async def receive_certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.message.from_user
    name = context.user_data["name"]
    student_id = context.user_data["student_id"]

    file = None
    filename = ""

    if update.message.document:
        file = await update.message.document.get_file()
        filename = update.message.document.file_name

    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        filename = f"{student_id}.jpg"

    else:
        await update.message.reply_text("Please send a valid file.")
        return CERTIFICATE

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"certificates/{student_id}_{timestamp}_{filename}"

    await file.download_to_drive(filepath)

    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            name,
            student_id,
            user.username,
            time_now,
            filepath,
        ])

    await update.message.reply_text("✅ Certificate submitted successfully!")

    return ConversationHandler.END


# ADMIN COMMAND
async def submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return

    await update.message.reply_document(open(CSV_FILE, "rb"))


# CANCEL
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# MAIN
def main():

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

    print("Bot running...")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()