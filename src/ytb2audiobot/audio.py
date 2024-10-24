import asyncio
import pathlib
from ytb2audio.ytb2audio import download_audio
from ytb2audiobot.predictor import predict_downloading_time


async def download_audio_by_movie_meta(movie_meta: dict):
    #print('🍍🍍 Starting downloading audio ... ')
    data_dir = pathlib.Path(movie_meta['store'])
    path = data_dir.joinpath(movie_meta['id'] + '.m4a')
    if path.exists():
        #print('💾 Audio file yet exists: ', path)
        return path

    tmp_webp_file = data_dir.joinpath(movie_meta['id'] + '.webp')
    tmp_webm_file = data_dir.joinpath(movie_meta['id'] + '.webm.part')
    MAX_CYCLE_EXIST = 4
    for cycle in range(MAX_CYCLE_EXIST):
        if not tmp_webp_file.exists():
            continue
        if not tmp_webp_file.exists():
            continue
        #print('🛼 Cycle: ', cycle)
        #print('😈 One of tmp file yet exists: ', tmp_webm_file, tmp_webp_file)
        sleep_time = predict_downloading_time(movie_meta.get('duration'))

        if sleep_time < 30:
            sleep_time = 30
        else:
            sleep_time = sleep_time // 2
        #print('💤 Sleep time: ', sleep_time)
        await asyncio.sleep(sleep_time)

        if cycle == MAX_CYCLE_EXIST - 1:
            #print('🥊 Finally 🚮🗑 Remove tmp files: ')
            if tmp_webm_file.exists():
                #print('\t', '🔹', tmp_webm_file)
                tmp_webm_file.unlink()
            if tmp_webp_file.exists():
                #print('\t', '🔹', tmp_webp_file)
                tmp_webp_file.unlink()

    audio = await download_audio(
        movie_id=movie_meta['id'],
        data_dir=movie_meta['store'],
        ytdlprewriteoptions=movie_meta['ytdlprewriteoptions']
    )
    if not audio.exists():
        #print('🔄 Retry download')
        audio = await download_audio(
            movie_id=movie_meta['id'],
            data_dir=movie_meta['store'],
            ytdlprewriteoptions=movie_meta['ytdlprewriteoptions']
        )

    return pathlib.Path(audio)
