import argparse
import asyncio
import datetime
import os
import pathlib
import re
import time
from io import BytesIO
from string import Template

import yaml
from PIL import Image
from audio2splitted.audio2splitted import get_split_audio_scheme, make_split_audio, DURATION_MINUTES_MIN, \
    DURATION_MINUTES_MAX
from dotenv import load_dotenv
from pytube.extract import video_id
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from mutagen.mp4 import MP4

from utils4audio.duration import get_duration
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from ytb2audio.ytb2audio import download_audio, download_thumbnail, YT_DLP_OPTIONS_DEFAULT
from datetime import timedelta

import random


async def parser_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if False:
        print('🍎 Update Processing: ')
        print(yaml.dump(update, default_flow_style=False))
        print()

    if not update._effective_message:
        return print('🟥 not update._effective_message')
    text = None
    if update._effective_message.text:
        text = update._effective_message.text
    if not text:
        return print('🟥 Text')

    sender_id = None
    if update._effective_message.sender_chat:
        sender_id = update._effective_message.sender_chat.id
    if update._effective_message.from_user:
        sender_id = update._effective_message.from_user.id
    if not sender_id:
        return print('🟥 No sender ID')

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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Help text',
        parse_mode=ParseMode.HTML
    )


async def run_bot(token: str, opt_keepfiles: str):
    print('🚀 Run bot...')

    application = ApplicationBuilder().token(token).build()

    application.bot_data['keepfiles'] = opt_keepfiles

    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, parser_request))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("Bot is running...")

    # Run the bot until Ctrl+C is pressed
    await application.updater.idle()

def main():
    parser = argparse.ArgumentParser(description='Bot ytb 2 audio')
    parser.add_argument('--keepfiles', type=int,
                        help='Keep raw files 1=True, 0=False (default)', default=0)

    args = parser.parse_args()

    load_dotenv()
    token = os.environ.get("TG_TOKEN")
    if not token:
        print('⛔️ No telegram bot token. Exit')
        return

    asyncio.run(run_bot(token, args.keepfiles))


if __name__ == "__main__":
    main()
