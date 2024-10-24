import pathlib
import ssl
import requests


async def image_compress_and_resize(
        path: pathlib.Path,
        output: pathlib.Path = None,
        quality: int = 80,
        thumbnail_size=(960, 960)
):
    return path


async def download(url: str, output):
    output = pathlib.Path(output)
    ssl._create_default_https_context = ssl._create_stdlib_context

    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with output.open('wb') as f:
                f.write(response.content)
        else:
            print(f'🟠 Thumbnail. Not a 200 valid code. Response code: {response.status_code}.')
            return
    except Exception as e:
        print(f'🟠 Thumbnail. Failed to download. Exception: {e}.')
        return

    return output


async def download_thumbnail_by_movie_meta(movie_meta: dict):

    data_dir = pathlib.Path(movie_meta['store'])

    data_dir.mkdir(parents=True, exist_ok=True)

    thumbnail = data_dir.joinpath(movie_meta['id'] + '-thumbnail.jpg')

    if thumbnail.exists():
        print(f'💕 Thumbnail file yet exists: {thumbnail}')
        return thumbnail

    # Special SSL setting to make valid HTTP request to Youtube server.
    ssl._create_default_https_context = ssl._create_stdlib_context

    thumbnail = await download(movie_meta['thumbnail_url'], thumbnail)
    if not thumbnail:
        thumbnail = await download(movie_meta['thumbnail_url'], thumbnail)
    if not thumbnail:
        return

    if not thumbnail.exists():
        return

    return thumbnail
