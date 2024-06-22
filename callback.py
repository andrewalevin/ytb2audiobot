import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

API_TOKEN = 'YOUR_BOT_API_TOKEN'

# Configure logging
logging.basicConfig(level=logging.INFO)

load_dotenv()
token = os.environ.get("TG_TOKEN")

# Initialize bot and dispatcher
bot = Bot(token=token)
dp = Dispatcher()

# Create inline keyboard
inline_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton('Button 1', callback_data='button1'),
    InlineKeyboardButton('Button 2', callback_data='button2')
)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Hi! I'm your bot. Use the buttons below.", reply_markup=inline_kb)


@dp.callback_query_handler(lambda c: c.data)
async def process_callback(callback_query: types.CallbackQuery):
    if callback_query.data == 'button1':
        await bot.send_message(callback_query.from_user.id, 'You pressed Button 1')
    elif callback_query.data == 'button2':
        await bot.send_message(callback_query.from_user.id, 'You pressed Button 2')
    await bot.answer_callback_query(callback_query.id)


async def run():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(run())
