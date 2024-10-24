from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

prime_numbers_row1 = [2, 3, 5, 7, 11, 13, 17, 19]
prime_numbers_row2 = [23, 29, 31, 37, 41, 43]
prime_numbers_row3 = [47, 53, 59, 61, 67,]
prime_numbers_row4 = [73, 79, 83, 89]

menu_extra_keyboard_duration = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=str(number), callback_data=str(number)) for number in prime_numbers_row1],
    [InlineKeyboardButton(text=str(number), callback_data=str(number)) for number in prime_numbers_row2],
    [InlineKeyboardButton(text=str(number), callback_data=str(number)) for number in prime_numbers_row3],
    [InlineKeyboardButton(text=str(number), callback_data=str(number)) for number in prime_numbers_row4],
])
