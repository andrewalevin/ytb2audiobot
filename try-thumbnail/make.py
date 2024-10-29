from yt_dlp import YoutubeDL


def download_thumbnail(video_url, output_path="thumbnail.jpg"):
    ydl_opts = {
        'skip_download': True,  # Пропустить загрузку видео
        'writethumbnail': True,  # Скачивать только миниатюру
        'convert_thumbnails': 'jpg',  # Конвертировать миниатюру в JPG
        'outtmpl': output_path,  # Указать имя файла
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


# Пример использования
download_thumbnail("dQw4w9WgXcQ")