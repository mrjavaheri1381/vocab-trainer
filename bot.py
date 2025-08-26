import os
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
from core import Session, WordEntry, get_def_ex
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=TOKEN)

# A global variable to store the current word for the user
current_word = None

async def start(update, context):
    global current_word
    session = Session()
    word_entry = session.query(WordEntry).order_by(WordEntry.last_seen).first()
    session.close()

    if not word_entry:
        await update.message.reply_text("No words in the database. Add one with /add <word>")
        return

    current_word = word_entry

    message = f"""
    <b>Definition:</b> {word_entry.definition}
    <i>Example 1:</i> {word_entry.example1}
    <i>Example 2:</i> {word_entry.example2}
    """

    await update.message.reply_text(message, parse_mode=telegram.ParseMode.HTML)

async def handle_message(update, context):
    global current_word
    if not current_word:
        await update.message.reply_text("Use /start to get a word.")
        return

    user_input = update.message.text.strip().lower()
    correct_word = current_word.word.strip().lower()

    if user_input == correct_word:
        await update.message.reply_text("Correct!")

        keyboard = [
            [
                telegram.InlineKeyboardButton("0", callback_data='0'),
                telegram.InlineKeyboardButton("1", callback_data='1'),
                telegram.InlineKeyboardButton("2", callback_data='2'),
                telegram.InlineKeyboardButton("3", callback_data='3'),
                telegram.InlineKeyboardButton("4", callback_data='4'),
            ],
            [telegram.InlineKeyboardButton("Skip", callback_data='-1')],
        ]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('How well did you know this word?', reply_markup=reply_markup)
    else:
        await update.message.reply_text("Incorrect! Try again.")

async def handle_callback_query(update, context):
    global current_word
    query = update.callback_query
    await query.answer()

    rating = int(query.data)

    session = Session()
    word_to_update = session.query(WordEntry).get(current_word.id)

    if word_to_update:
        word_to_update.last_seen = datetime.now()
        word_to_update.last_read = datetime.now()
        if rating == -1:
            word_to_update.cycle = 9999
        else:
            word_to_update.cycle = rating
        session.commit()

    session.close()
    current_word = None

    await query.edit_message_text(text=f"Rated as {rating}. Use /start for the next word.")

async def add_word_command(update, context):
    try:
        word = context.args[0]
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /add <word>")
        return

    session = Session()
    existing = session.query(WordEntry).filter_by(word=word).first()
    if existing:
        await update.message.reply_text(f"'{word}' already exists.")
        session.close()
        return

    try:
        definition, example1, example2 = get_def_ex(word)
        if not definition:
            await update.message.reply_text(f"Could not find a definition for '{word}'.")
            return

        new_entry = WordEntry(
            word=word,
            definition=definition,
            example1=example1,
            example2=example2,
            cycle=0,
            last_seen=datetime.now(),
            last_read=datetime.now()
        )
        session.add(new_entry)
        session.commit()
        await update.message.reply_text(f"'{word}' added successfully.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        session.close()

def setup_bot():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(CommandHandler("add", add_word_command))

    return application
