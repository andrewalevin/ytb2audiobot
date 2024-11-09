from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import os
from pydub import AudioSegment
from speechkit import configure_credentials, creds
from speechkit import model_repository
from speechkit.stt import AudioProcessingType
import pathlib
from dotenv import load_dotenv

from src.ytb2audiobot.gpt import promt_gpt


async def get_subtitles(movie_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(movie_id, languages=['ru'])
    except TranscriptsDisabled:
        print('⛔️ YouTubeTranscriptApi: TranscriptsDisabled')
        return
    except (ValueError, Exception):
        print('⛔️ Undefined problem in YouTubeTranscriptApi')
        return

    subtitles = [[entry['start'], entry['text']] for entry in transcript]
    return subtitles


def time_to_seconds(time_str):
    hours, minutes, seconds = map(int, time_str.split_by_duration(':'))
    return hours * 3600 + minutes * 60 + seconds


def filter_subtitles(subtitles, time_mark, time_delta):
    time_borders = [time_mark - time_delta, time_mark + time_delta]
    filtered_data = [entry for entry in subtitles if time_borders[0] <= entry[0] <= time_borders[1]]
    return filtered_data


async def convert_m4a_to_ogg(path):
    path = pathlib.Path(path)
    audio = AudioSegment.from_file(path.as_posix(), format="m4a")
    ogg_path = path.with_suffix('.ogg')
    audio.export(ogg_path.as_posix(), format="ogg")
    return ogg_path


async def voice2text(path):
    load_dotenv()

    yandex_bot_token = os.getenv('YANDEX_CLOUD_SPEACH_API_TOKEN')

    if not yandex_bot_token or len(yandex_bot_token) < 10:
        return

    configure_credentials(
        yandex_credentials=creds.YandexCredentials(
            api_key=yandex_bot_token
        )
    )

    path = pathlib.Path(path)
    model = model_repository.recognition_model()
    model.model = 'general'
    model.language = 'ru-RU'
    model.audio_processing_type = AudioProcessingType.Full

    result = model.transcribe_file(path.as_posix())
    return result


async def voice2text_processor(path):
    results = await voice2text(path)
    if not results:
        return

    data = []
    for c, res in enumerate(results):
        utterances = []
        for utterance in res.utterances:
            utterances.append(str(utterance))
        print('utterances: ')
        print(utterances)

        item = {
            'channel': c,
            'raw_text': res.raw_text,
            'normalized_text': res.normalized_text,
            'words': res.words,
            'utterances': utterances
        }
        data.append(item)
    return data


async def recogniser_trsinscript(original_audio_small_path):
    ogg_path = await convert_m4a_to_ogg(original_audio_small_path)
    if not ogg_path:
        return

    trans = await voice2text_processor(ogg_path)
    if not trans:
        return

    trans_normal = trans[0].get('normalized_text')

    if not trans_normal:
        return

    return trans_normal


SMALL_ORIRGINAL_PATH = 'pustovit-quote.m4a'

async def quote_designer(movie_id, time_mark_raw, time_delta):
    subtitles = await get_subtitles(movie_id)
    if not subtitles:
        return

    time_mark = time_to_seconds(time_mark_raw)
    subtitles_segments = filter_subtitles(subtitles, time_mark, time_delta)

    if not subtitles_segments:
        return
    print(subtitles_segments)

    fine_subtitles_list = [item[1] for item in subtitles_segments]
    fine_subtitles = '\n'.join(fine_subtitles_list)
    print('💐: ', fine_subtitles)

    inst = 'Это субтитры из youtube видео. Отредактируй несильно эти субтитры. В местах, где пропущено слово по смыслу поставть троеточие. В ответе не добавляй никаких служебных комментариев.'
    gpt_ytb_subtitles_text = promt_gpt(inst, fine_subtitles, temperature=0.4)
    if not gpt_ytb_subtitles_text:
        return fine_subtitles

    recong_trans = await recogniser_trsinscript(SMALL_ORIRGINAL_PATH)
    if not recong_trans:
        return gpt_ytb_subtitles_text

    instruction = 'Несильно отредактируй текст. Раздели его на смысловые абзацы. В ответе не добавляй никаких служебных комментариев'
    edited_trans = promt_gpt(instruction, recong_trans, temperature=0.4)
    if not edited_trans:
        return recong_trans

    return edited_trans
