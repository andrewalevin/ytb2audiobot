import asyncio
import os
import random
import time

from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


# Define the start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sender_id = update.message.from_user.id
    post_status = await context.bot.send_message(
        chat_id=sender_id,
        reply_to_message_id=update._effective_message.message_id,
        text=f'Start ...'
    )

    coll = '🫑 🍒 🍓 🍐 🍎 🌽 🚲'
    one = random.choice(coll.split(' '))

    for idx in range(20):
        print(f'{one} {sender_id} time: ', idx)
        time.sleep(1)

    await post_status.edit_text('End')

# Define the main function to set up the bot and add handlers
async def main() -> None:
    load_dotenv()
    token = os.environ.get("TG_TOKEN")
    if not token:
        print('⛔️ No telegram bot token. Exit')
        return

    # Create the application and pass it your bot's token
    application = Application.builder().token(token).build()

    # Add a command handler for the /start command
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    # Start the bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("Bot is running...")

# Run the main function in the event loop
if __name__ == '__main__':
    asyncio.run(main())
