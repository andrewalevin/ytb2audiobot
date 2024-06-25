import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os

load_dotenv()
token = os.environ.get("TG_TOKEN")


# Initialize bot and dispatcher
bot = Bot(token=token)
dp = Dispatcher()


# Define inline keyboard
inline_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📣 Just Download️", callback_data='button_pressed'), ], ],
        )


# Command handler to start the bot
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.reply("Hi!\nI'm your bot.\nPress the button below:", reply_markup=inline_kb)


# Callback query handler
@dp.callback_query(lambda c: c.data == 'button_pressed')
async def process_callback(callback_query: types.CallbackQuery):
    # Acknowledge the callback query
    await bot.answer_callback_query(callback_query.id, text='🥶 Button pressed!')

    # Optionally, you can send a message or edit the current message
    await bot.send_message(callback_query.from_user.id, 'You pressed the button!')


async def run():
    await dp.start_polling(bot)

# Start polling
if __name__ == '__main__':
    asyncio.run(run())
