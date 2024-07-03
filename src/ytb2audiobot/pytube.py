from pytube import YouTube
from ytb2audiobot import config
from ytb2audiobot.datadir import get_data_dir


async def get_movie_meta(movie_id):
    movie_meta = config.DEFAULT_MOVIE_META.copy()

    movie_meta['id'] = movie_id
    movie_meta['store'] = get_data_dir()

    try:
        yt = YouTube.from_id(movie_id)
    except Exception as e:
        movie_meta['error'] = f'🟠 Exception. Cant get pytube object. \n🟠 {e}\n\n Continue ... '
        return movie_meta

    if yt.title:
        movie_meta['title'] = yt.title

    if yt.description:
        movie_meta['description'] = yt.description

    if yt.author:
        movie_meta['author'] = yt.author

    if yt.thumbnail_url:
        movie_meta['thumbnail_url'] = yt.thumbnail_url

    if yt.length:
        movie_meta['duration'] = yt.length

    return movie_meta
