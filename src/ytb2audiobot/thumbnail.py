import pathlib
import ssl

import requests
from PIL import Image


async def image_compress_and_resize(
        path: pathlib.Path,
        output: pathlib.Path = None,
        quality: int = 80,
        thumbnail_size=(960, 960)
):
    print('🖼 image_compress_and_resize(): ')
    path = pathlib.Path(path)
    if not path.exists():
        return pathlib.Path('none.file')

    image = Image.open(path)
    image.thumbnail(thumbnail_size)
    if not output:
        output = path
    image.save(output, optimize=True, quality=quality)
    return output


async def download_thumbnail_by_movie_meta(movie_meta: dict):
    print('🥑 Starting downloading thumbnail ... ')

    data_dir = pathlib.Path(movie_meta['store'])

    data_dir.mkdir(parents=True, exist_ok=True)
    if not movie_meta['id']:
        _err = f'🟠 Thumbnail. No ID in movie meta.'
        print(_err)
        return 'Error'

    thumbnail = data_dir.joinpath(movie_meta['id'] + '-thumbnail.jpg')

    if thumbnail.exists():
        print(f'💚 Thumbnail file yet exists: {thumbnail}')
        return thumbnail

    # Special SSL setting to make valid HTTP request to Youtube server.
    ssl._create_default_https_context = ssl._create_stdlib_context

    print('🦠 URL to download: ', movie_meta['thumbnail_url'])

    try:
        response = requests.get(movie_meta['thumbnail_url'], stream=True)
        if response.status_code == 200:
            with thumbnail.open('wb') as f:
                f.write(response.content)
        else:
            _err = f'🟠 Thumbnail. Not a 200 valid code. Response code: {response.status_code}.'
            print(_err)
            return 'Error'
    except Exception as e:
        _err = f'🟠 Thumbnail. Failed to download. Exception: {e}.'
        print(_err)
        return 'Error'

    if not thumbnail.exists():
        return pathlib.Path('none.file')

    return thumbnail
