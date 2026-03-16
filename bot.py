import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Read token from Railway environment variable
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing!")

# Create folder for certificates
os.makedirs("certificates", exist_ok=True)


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\n\nPlease upload your certificate file."
    )


# Handle file uploads
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document:
        return

    file = await document.get_file()
    filename = document.file_name

    filepath = f"certificates/{filename}"

    await file.download_to_drive(filepath)

    await update.message.reply_text("✅ Certificate received successfully!")


# Handle wrong messages
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please upload your certificate as a file 📄"
    )


def main():
    print("Starting bot...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()