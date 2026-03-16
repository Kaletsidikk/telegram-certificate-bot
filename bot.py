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

ADMIN_ID = 1349142732   

NAME, STUDENT_ID, CERTIFICATE = range(3)

os.makedirs("certificates", exist_ok=True)

CSV_FILE = "submissions.csv"

# create csv file
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "StudentID", "File", "Time"])


def already_submitted(student_id):
    with open(CSV_FILE, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 1 and row[1] == student_id:
                return True
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Welcome!\n\nPlease enter your FULL NAME."
    )

    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["name"] = update.message.text

    await update.message.reply_text(
        "Enter your STUDENT ID."
    )

    return STUDENT_ID


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    student_id = update.message.text

    if already_submitted(student_id):
        await update.message.reply_text(
            "⚠️ This Student ID has already submitted."
        )
        return ConversationHandler.END

    context.user_data["id"] = student_id

    await update.message.reply_text(
        "Upload your certificate (PDF or Image)."
    )

    return CERTIFICATE


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    name = context.user_data["name"]
    student_id = context.user_data["id"]

    file_path = None
    filename = None

    # DOCUMENT (PDF etc)
    if update.message.document:

        doc = update.message.document
        file = await doc.get_file()

        filename = f"{student_id}_{doc.file_name}"
        file_path = f"certificates/{filename}"

        await file.download_to_drive(file_path)

    # PHOTO
    elif update.message.photo:

        photo = update.message.photo[-1]
        file = await photo.get_file()

        filename = f"{student_id}_certificate.jpg"
        file_path = f"certificates/{filename}"

        await file.download_to_drive(file_path)

    else:
        await update.message.reply_text(
            "Please upload a certificate file (PDF or Image)."
        )
        return CERTIFICATE

    submit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([name, student_id, filename, submit_time])

    await update.message.reply_text(
        "✅ Certificate submitted successfully!"
    )

    return ConversationHandler.END


async def submissions(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_document(
        document=open(CSV_FILE, "rb")
    )


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
            CERTIFICATE: [
                MessageHandler(
                    filters.Document.ALL | filters.PHOTO,
                    handle_file
                )
            ],
        },
        fallbacks=[],
    )

    app.add_handler(conv)

    app.add_handler(CommandHandler("submissions", submissions))

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()