from aiogram.filters import CommandStart
from dotenv import load_dotenv
import os

load_dotenv()
token = os.environ.get("TG_TOKEN")

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv


# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=token)
dp = Dispatcher()


kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Button-1", callback_data="button1"),
            InlineKeyboardButton(text="Button-2", callback_data="button2"),
        ]
    ],
    row_width=2
)


@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.reply(f'Choose option', reply_markup=kb)

    if False:
        timer = 10
        text = f"Choose one of these options. Hide over seconds: "
        post = await message.reply(f'{text} {timer}', reply_markup=kb)
        while timer:
            timer -= 1
            await post.edit_text(f'{text} {timer}', reply_markup=kb)
            await asyncio.sleep(1)

        await post.delete()



@dp.callback_query(lambda c: c.data == 'button1')
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, 'You pressed Button 1!')


@dp.callback_query(lambda c: c.data == 'button2')
async def process_callback_button2(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, 'You pressed Button 2!')


async def run():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(run())
