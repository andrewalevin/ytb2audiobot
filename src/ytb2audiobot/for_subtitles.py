from string import Template

from aiogram import Bot
from aiogram.types import BufferedInputFile

from src.ytb2audiobot import config
from src.ytb2audiobot.subtitles import get_subtitles

bot = Bot()

async def send():
    result = None
    sender_id = None
    message_id = None

    if result.get('subtitles'):
        full_caption = config.SUBTITLES_WITH_CAPTION_TEXT_TEMPLATE.substitute(
            caption=result.get('subtitles').get('caption'),
            subtitles=result.get('subtitles').get('text'))

        if len(full_caption) >= config.TELEGRAM_MAX_MESSAGE_TEXT_SIZE:
            full_caption = full_caption.replace('<b><s><b><s>', '🔹')
            full_caption = full_caption.replace('</s></b></s></b>', '🔹')
            await bot.send_document(
                chat_id=sender_id,
                reply_to_message_id=message_id,
                caption=result.get('subtitles').get('caption'),
                parse_mode='HTML',
                document=BufferedInputFile(
                    filename=result.get('subtitles').get('filename'),
                    file=full_caption.encode('utf-8'),))
        else:
            await bot.send_message(
                chat_id=sender_id,
                reply_to_message_id=message_id,
                text=full_caption,
                parse_mode='HTML',
                disable_web_page_preview=False)


def save_timer():
    stopwatch_time = time.perf_counter()


    # Save Timer in Dev mode
    if False:
        stopwatch_time = int(time.perf_counter() - stopwatch_time)
        timerlogger.info(f'duration_' + str(movie_meta.get('duration')) + f' :  predict_{predict_time} : actual_{stopwatch_time} : delta_{int(stopwatch_time - predict_time)}')


async def from_processing():
    command = dict()
    movie_meta = dict()
    context = dict()
    caption_head = ''
    filename = ''

    if command.get('name') == 'subtitles':
        param = ''
        if command.get('params'):
            params = command.get('params')
            param = ' '.join(params)

        text, _err = await get_subtitles(movie_meta.get('id'), param)
        if _err:
            context['error'] = f'🟥️ Subtitles. Internal error: {_err}'
            return context

        caption = Template(caption_head).safe_substitute(partition='', timecodes='', duration='', additional='')
        caption = caption.replace('\n\n\n', '\n')
        caption = caption.replace('[]', '')

        caption_subtitles = '📝 Subtitles'
        if param:
            caption_subtitles += f' 🔎 Search [{param}]'
        caption = caption.strip() + '\n\n' + caption_subtitles

        context['subtitles'] = {
            'caption': caption,
            'text': text,
            'filename': 'subtitles-' + filename.replace('.m4a', '') + '-' + movie_meta.get('id') + '.txt'
        }

        return context

    if command.get('name') == 'quote':
        print('🐠 QUOTE: ')
        context['quote'] = 'quote'
        return context