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

TOKEN = os.environ.get("BOT_TOKEN")

# CHANGE THIS TO YOUR TELEGRAM USER ID
ADMIN_ID = 123456789

# DEADLINE (YYYY-MM-DD HH:MM)
DEADLINE = datetime(2026, 3, 20, 23, 59)

NAME, STUDENT_ID, CERTIFICATE = range(3)

os.makedirs("certificates", exist_ok=True)

CSV_FILE = "submissions.csv"

# create csv if not exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Student ID", "File", "Time"])


def student_exists(student_id):
    with open(CSV_FILE, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 1 and row[1] == student_id:
                return True
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if datetime.now() > DEADLINE:
        await update.message.reply_text("❌ Submission deadline has passed.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome!\n\nEnter your FULL NAME:"
    )

    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["name"] = update.message.text

    await update.message.reply_text(
        "Enter your STUDENT ID:"
    )

    return STUDENT_ID


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    student_id = update.message.text

    if student_exists(student_id):
        await update.message.reply_text(
            "⚠️ This Student ID has already submitted."
        )
        return ConversationHandler.END

    context.user_data["id"] = student_id

    await update.message.reply_text(
        "Upload your certificate file."
    )

    return CERTIFICATE


async def handle_certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    document = update.message.document
    file = await document.get_file()

    name = context.user_data["name"]
    student_id = context.user_data["id"]

    filename = f"{student_id}_{document.file_name}"
    filepath = f"certificates/{filename}"

    await file.download_to_drive(filepath)

    submit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([name, student_id, filename, submit_time])

    await update.message.reply_text(
        "✅ Submission successful!"
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Submission cancelled.")
    return ConversationHandler.END


# ADMIN COMMANDS

async def submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_document(document=open(CSV_FILE, "rb"))


async def files(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    files = os.listdir("certificates")

    if not files:
        await update.message.reply_text("No submissions yet.")
        return

    for f in files:
        await update.message.reply_document(
            document=open(f"certificates/{f}", "rb")
        )


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
            CERTIFICATE: [MessageHandler(filters.Document.ALL, handle_certificate)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)

    app.add_handler(CommandHandler("submissions", submissions))
    app.add_handler(CommandHandler("files", files))

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()