import json
import random
import string
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen

from pydantic import BaseModel

from ghoshell.contracts import TTS, ASR


class BaiduSpeechTTSConfig(BaseModel):
    # 发音人选择, 基础音库：0为度小美，1为度小宇，3为度逍遥，4为度丫丫，
    # 精品音库：5为度小娇，103为度米朵，106为度博文，110为度小童，111为度小萌，默认为度小美
    per = 4
    # 语速，取值0-15，默认为5中语速
    spd = 5
    # 音调，取值0-15，默认为5中语调
    pit = 5
    # 音量，取值0-9，默认为5中音量
    vol = 5

    # 下载的文件格式, 3：mp3(default) 4： pcm-16k 5： pcm-8k 6. wav
    aue = 3

    cuid = "".join(random.choice(string.ascii_letters + string.digits) for i in range(12))

    tts_url = 'https://tsn.baidu.com/text2audio'
    token_url = 'https://aip.baidubce.com/oauth/2.0/token'
    scope = 'audio_tts_post'  # 有此scope表示有tts能力，没有请在网页里勾选

    FORMATS = {3: "mp3", 4: "pcm", 5: "pcm", 6: "wav"}

    @property
    def format(self) -> str:
        return self.FORMATS[self.aue]


class BaiduSpeechConfig(BaseModel):
    tts: BaiduSpeechTTSConfig = BaiduSpeechTTSConfig()


class BaiduSpeech(TTS, ASR):

    def __init__(self, app_key: str, app_secret: str, tts_config: BaiduSpeechConfig):
        self._config = tts_config
        self._app_key = app_key
        self._app_secret = app_secret
        self._token: str | None = None

    def _fetch_token(self) -> str:
        if self._token is not None:
            return self._token
        params = {'grant_type': 'client_credentials',
                  'client_id': self._app_key,
                  'client_secret': self._app_secret}

        post_data = urlencode(params)
        post_data = post_data.encode('utf-8')
        req = Request(self._config.tts.token_url, post_data)

        f = urlopen(req, timeout=5)
        result_str = f.read()
        result_str = result_str.decode()

        result = json.loads(result_str)
        if 'access_token' in result.keys() and 'scope' in result.keys():
            if self._config.tts.scope not in result['scope'].split(' '):
                raise URLError('scope is not correct')
            # print('SUCCESS WITH TOKEN: %s ; EXPIRES IN SECONDS: %s' % (result['access_token'], result['expires_in']))
            self._token = result['access_token']
            return self._token
        else:
            raise RuntimeError(
                'MAYBE API_KEY or SECRET_KEY not correct: access_token or scope not found in token response')

    def speech2text(self, speech_data: str) -> str:
        """
        语音内容转文字
        format: wav
        """
        pass

    def text2speech(self, text: str, filename: str) -> None:
        """
        文字内容转语音.
        随便写写.
        """
        token = self._fetch_token()
        params = {
            'tok': token,
            'tex': text,
            'per': self._config.tts.per,
            'spd': self._config.tts.spd,
            'pit': self._config.tts.pit,
            'vol': self._config.tts.vol,
            'aue': self._config.tts.aue,
            'cuid': self._config.tts.cuid,
            'lan': 'zh',
            'ctp': 1,
        }
        data = urlencode(params)
        req = Request(self._config.tts.tts_url, data.encode('utf-8'))
        start = time.time()
        f = urlopen(req)
        end = time.time()
        print("+++++++++++++=l", end - start)
        result_str = f.read()
        headers = dict((name.lower(), value) for name, value in f.headers.items())

        has_error = 'content-type' not in headers.keys() or headers['content-type'].find('audio/') < 0
        if not has_error:
            with open(filename, 'wb') as of:
                of.write(result_str)
        else:
            raise RuntimeError("tts err:" + result_str)
