import os
import asyncio
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from bs4 import BeautifulSoup

# Bot token, group ID, and owner ID placeholders
#BOT_TOKEN = os.getenv("7972418774:AAFgeS8Nw15K3tbY7akJ7im6cQHXZbeO3Ko")  # Add your bot token here or set as env variable
BOT_TOKEN = "7786966143:AAHyWWfnc37KMeva8QEmVC4NIZUYjrX8AqY"
#GROUP_ID = int(os.getenv("GROUP_ID", "-4671966297"))  # Replace with your group ID
GROUP_ID = "-4671966297"
# OWNER_ID = int(os.getenv("OWNER_ID", "5218536687"))  # Replace with your Telegram user ID
OWNER_ID = "5218536687"

# Delay between polls (in seconds)
POLL_DELAY = 5

# Temporary storage
pending_polls = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me an HTML file with MCQs.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    if not update.message.document:
        return

    file = await update.message.document.get_file()
    file_path = f"/tmp/{update.message.document.file_name}"
    await file.download_to_drive(file_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    questions = []
    current_question = None

    for div in soup.find_all('div'):
        class_name = div.get('class', [''])[0]
        text = div.get_text(strip=True)

        if class_name == 'question':
            if current_question:
                questions.append(current_question)
            current_question = {'text': text, 'options': [], 'image': None}

        elif class_name == 'answer' and current_question:
            current_question['options'].append(text)

        elif div.find('img') and current_question:
            img_tag = div.find('img')
            if img_tag.get('src'):
                current_question['image'] = img_tag['src']

    if current_question:
        questions.append(current_question)

    if not questions:
        await update.message.reply_text("No questions found in the file.")
        return

    pending_polls[update.effective_chat.id] = questions

    # Show summary and confirmation
    preview = "Here are some questions parsed:\n\n"
    for q in questions[:3]:
        preview += q['text'] + "\n"
    preview += f"\nTotal questions parsed: {len(questions)}"

    buttons = [
        [InlineKeyboardButton("✅ Yes, send polls", callback_data="confirm_send"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_send")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(preview, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("You are not authorized to confirm sending polls.")
        return

    if query.data == "confirm_send":
        await send_polls(update, context)
    elif query.data == "cancel_send":
        pending_polls.pop(update.effective_chat.id, None)
        await query.edit_message_text("Cancelled sending polls.")

async def send_polls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    questions = pending_polls.pop(chat_id, [])

    if not questions:
        await update.callback_query.edit_message_text("No polls to send.")
        return

    await update.callback_query.edit_message_text("Sending polls to group...")

    for idx, q in enumerate(questions, start=1):
        try:
            if q['image']:
                await context.bot.send_photo(chat_id=GROUP_ID, photo=q['image'])

            await context.bot.send_poll(
                chat_id=GROUP_ID,
                question=q['text'][:300],
                options=q['options'][:4],
                is_anonymous=False,
                allows_multiple_answers=False,
            )

            await asyncio.sleep(POLL_DELAY)

        except Exception as e:
            print(f"Error sending question {idx}: {e}")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    
