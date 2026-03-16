from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes

TOKEN = "YOUR_BOT_TOKEN"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send your certificate file.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    await file.download_to_drive(f"certificates/{update.message.document.file_name}")
    await update.message.reply_text("Certificate received!")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

app.run_polling()