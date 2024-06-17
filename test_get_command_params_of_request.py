import unittest

from src.ytb2audiobot.ytb2audiobot_asynced import get_command_params_of_request2 as parser


TESTS = [
    [
        'youtu.be/8jn9ah_aprE',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': '',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE bitr',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'bitrate',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE bitr 96',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'bitrate',
            'params': ['96']
        }
    ],[
        'youtu.be/8jn9ah_aprE bitr 96 one two three',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'bitrate',
            'params': ['96', 'one']
        }
    ],[
        'youtu.be/8jn9ah_aprE split',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'split',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE spl',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'split',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE sp',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'split',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE split 320',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'split',
            'params': ['320']
        }
    ],[
        'youtu.be/8jn9ah_aprE split 300 additional text and what to du',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'split',
            'params': ['300', 'additional']
        }
    ],[
        'youtu.be/8jn9ah_aprE bitr 96 one two three',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'bitrate',
            'params': ['96', 'one']
        }
    ],[
        'Начиная с Руссо и Канта существовали две шко- лы либерализма, которые можно определить как твердолобых и мягкосердечных. '
        'Твердолобое направление через Бентама, Рикардо и Маркса логично подвело к Сталину; '
        'мягкосердеч- ное через другие логические стадии перешло через Фихте, Байрона, Карлейля и Ницше к Гитлеру.'
        ' youtu.be/8jn9ah_aprE bitr 96 one two three Твердолобое направление через Бентама, Рикардо и Маркса логично подвело к Сталину;',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': False,
            'command': '',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE subtitles',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'subtitles',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE subt',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'subtitles',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE subs',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'subtitles',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE sub',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'subtitles',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE subs',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'subtitles',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE subs мост',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'subtitles',
            'params': ['мост']
        }
    ],[
        'youtu.be/8jn9ah_aprE subs подвесной мост',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'subtitles',
            'params': ['подвесной', 'мост']
        }
    ],[
        'youtu.be/8jn9ah_aprE download',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'download',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE down',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'download',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE dow',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'download',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE d',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'download',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE скачать',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'download',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE скач',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'download',
            'params': []
        }
    ],[
        'youtu.be/8jn9ah_aprE bot',
        {
            'url': 'youtu.be/8jn9ah_aprE',
            'url_started': True,
            'command': 'download',
            'params': []
        }
    ],



]


class TestRequestParser(unittest.TestCase):

    def test_parser(self):
        for test in TESTS:
            print('💧', test[0])
            self.assertEqual(parser(test[0]), test[1])
            print()


if __name__ == '__main__':
    unittest.main()
