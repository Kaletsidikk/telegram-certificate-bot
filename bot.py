import os
import csv
import zipfile
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

# PUT YOUR TELEGRAM ID HERE
ADMIN_ID = 1349142732

NAME, STUDENT_ID, CERTIFICATE = range(3)

# create folders
os.makedirs("certificates", exist_ok=True)

CSV_FILE = "submissions.csv"

# create csv if not exists
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

    filename = None

    if update.message.document:

        doc = update.message.document
        file = await doc.get_file()

        filename = f"{student_id}_{doc.file_name}"

        await file.download_to_drive(f"certificates/{filename}")

    elif update.message.photo:

        photo = update.message.photo[-1]
        file = await photo.get_file()

        filename = f"{student_id}_certificate.jpg"

        await file.download_to_drive(f"certificates/{filename}")

    else:

        await update.message.reply_text(
            "Please upload a certificate file."
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


async def files(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    files = os.listdir("certificates")

    if not files:

        await update.message.reply_text(
            "No certificates submitted yet."
        )

        return

    for f in files:

        await update.message.reply_document(
            document=open(f"certificates/{f}", "rb")
        )


async def download_all(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    zip_name = "certificates.zip"

    with zipfile.ZipFile(zip_name, "w") as zipf:

        for root, dirs, files in os.walk("certificates"):

            for file in files:

                zipf.write(
                    os.path.join(root, file),
                    file
                )

    await update.message.reply_document(
        document=open(zip_name, "rb")
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

    app.add_handler(CommandHandler("files", files))

    app.add_handler(CommandHandler("download_all", download_all))

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()