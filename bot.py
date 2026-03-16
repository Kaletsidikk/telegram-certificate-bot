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
ADMIN_ID = int(os.getenv("ADMIN_ID"))

NAME, STUDENT_ID, CERTIFICATE = range(3)

os.makedirs("certificates", exist_ok=True)

CSV_FILE = "submissions.csv"

# Create CSV if not exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "StudentID", "Username", "Time", "File"])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome!\n\nPlease enter your *Full Name*.",
        parse_mode="Markdown",
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Now enter your *Student ID*.", parse_mode="Markdown")
    return STUDENT_ID


async def get_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student_id"] = update.message.text

    await update.message.reply_text(
        "Now send your *certificate file*.\n\nAccepted formats:\nPDF / Image / Document",
        parse_mode="Markdown",
    )
    return CERTIFICATE


async def receive_certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    name = context.user_data["name"]
    student_id = context.user_data["student_id"]

    file = None
    file_ext = "file"

    if update.message.document:
        file = update.message.document.file_id
        file_ext = update.message.document.file_name

    elif update.message.photo:
        file = update.message.photo[-1].file_id
        file_ext = f"{student_id}.jpg"

    else:
        await update.message.reply_text("Please send a valid certificate file.")
        return CERTIFICATE

    file_obj = await context.bot.get_file(file)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"certificates/{student_id}_{timestamp}_{file_ext}"

    await file_obj.download_to_drive(filename)

    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            name,
            student_id,
            user.username,
            time_now,
            filename,
        ])

    await update.message.reply_text("✅ Certificate submitted successfully!")

    return ConversationHandler.END


async def submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return

    await update.message.reply_document(open(CSV_FILE, "rb"))


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Submission cancelled.")
    return ConversationHandler.END


def main():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_student_id)],
            CERTIFICATE: [
                MessageHandler(
                    filters.Document.ALL | filters.PHOTO,
                    receive_certificate,
                )
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