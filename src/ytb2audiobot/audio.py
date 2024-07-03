import pathlib
from ytb2audio.ytb2audio import download_audio


async def download_audio_by_movie_meta(movie_meta: dict):
    print('🍍🍍 Starting downloading audio ... ')
    data_dir = pathlib.Path(movie_meta['store'])
    path = data_dir.joinpath(movie_meta['id'] + '.m4a')
    if path.exists():
        print('💾 Audio file yet exists: ', path)
        return path

    audio = await download_audio(
        movie_id=movie_meta['id'],
        data_dir=movie_meta['store'],
        ytdlprewriteoptions=movie_meta['ytdlprewriteoptions']
    )
    if not audio.exists():
        print('🔄 Retry download')
        audio = await download_audio(
            movie_id=movie_meta['id'],
            data_dir=movie_meta['store'],
            ytdlprewriteoptions=movie_meta['ytdlprewriteoptions']
        )

    return pathlib.Path(audio)
