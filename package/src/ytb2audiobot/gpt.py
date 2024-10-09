import pathlib

from dotenv import load_dotenv

import utils
import requests
import json
import os

TEMP_JSON = 'temp-promt-body.json'


def promt_gpt(instruction_text, request_text, temperature=0.6, max_tokens='500'):
    load_dotenv()

    api_key = os.getenv('YANDEX_CLOUD_GPT_API_KEY')
    if not api_key:
        return

    folder_id = os.getenv('YANDEX_CLOUD_FOLDER_ID')
    if not folder_id:
        return

    json_temp_file = pathlib.Path(TEMP_JSON)

    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_tokens
        },
        "messages": [
            {
                "role": "system",
                "text": instruction_text
            },
            {
                "role": "user",
                "text": request_text
            }
        ]
    }

    utils.write_json(json_temp_file, data)

    headers = {
        'Authorization': f'Api-Key {api_key}',
    }

    url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'

    with open(json_temp_file.as_posix(), 'r', encoding='utf-8') as f:
        data = json.dumps(json.load(f))
    resp = requests.post(url, headers=headers, data=data)

    if resp.status_code != 200:
        raise RuntimeError(
            'Invalid response received: code: {}, message: {}'.format(
                {resp.status_code}, {resp.text}
            )
        )

    json_temp_file.unlink()

    data_result = json.loads(resp.text)

    usage = data_result.get('result').get('usage')
    #print('🐬 GPT: ', 'inputTextTokens:', usage.get('inputTextTokens'),
    #      'completionTokens:', usage.get('completionTokens'),
    #      'totalTokens:', usage.get('totalTokens'),
    #      'temperature:', temperature,
    #      'maxTokens:', max_tokens
    #      )
    #print()

    text = data_result.get('result').get('alternatives')[0].get('message').get('text')
    #print(text)
    #print()

    return text
