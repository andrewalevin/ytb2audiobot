from pytube import YouTube


async def get_movie_meta(movie_meta: dict, movie_id):
    yt = None
    try:
        yt = YouTube.from_id(movie_id)
    except Exception as e:
        print(f'🟠 {e}\n\n 🟠 Exception. Cant get pytube object. Continue ... ')
        movie_meta['error'] = e
        return movie_meta

    if yt.title:
        movie_meta['title'] = yt.title

    print('💈 Description: ', yt.description)
    if yt.description:
        movie_meta['description'] = yt.description

    if yt.author:
        movie_meta['author'] = yt.author

    if yt.thumbnail_url:
        movie_meta['thumbnail_url'] = yt.thumbnail_url

    if yt.length:
        movie_meta['duration'] = yt.length

    return movie_meta

