import yt_dlp
from src.ytb2audiobot import config
from src.ytb2audiobot.datadir import get_data_dir
from src.ytb2audiobot.logger import logger


async def get_yt_dlp_info(movie_id):
    ydl_opts = {
        'logtostderr': False,  # Avoids logging to stderr, logs to the logger instead
        'quiet': True,  # Suppresses default output,
        'nocheckcertificate': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            _info = ydl.extract_info(f"https://www.youtube.com/watch?v={movie_id}", download=False)
    except Exception as e:
        logger.error(f'🍅 Cant Extract YT_DLP info. \n{e}')
        return {}

    return _info


async def get_movie_meta(movie_id):
    logger.debug(f'🐞 get_movie_meta(movie_id): {movie_id}')

    movie_meta = config.DEFAULT_MOVIE_META.copy()

    movie_meta['id'] = movie_id
    movie_meta['store'] = get_data_dir()

    try:
        ydl_opts = {
            'logger': logger,  # Redirect yt-dlp output to the logger
            'logtostderr': False,  # Avoids logging to stderr, logs to the logger instead
            'quiet': True,  # Suppresses default output,
            'nocheckcertificate': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            yt = ydl.extract_info(f"https://www.youtube.com/watch?v={movie_id}", download=False)
    except Exception as e:
        logger.error(f'🍅 Cant Extract movie meta using YT_DLP. \n{e}')
        return movie_meta

    mapping = {
        'title': 'title',
        'description': 'description',
        'uploader': 'author',
        'thumbnail': 'thumbnail_url',
        'duration': 'duration'
    }

    for yt_key, meta_key in mapping.items():
        if yt.get(yt_key):
            movie_meta[meta_key] = yt.get(yt_key)

    return movie_meta
