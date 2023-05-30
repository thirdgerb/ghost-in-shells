import base64
import json
import os
from typing import Dict, Type, ClassVar
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen

import yaml

from ghoshell.container import Provider, Container, Contract
from ghoshell.shell import Shell, BoostrapException
from ghoshell.shell_protos.baidu_speech.config import BaiduSpeechConfig


class BaiduSpeechAdapter:

    def __init__(
            self,
            app_key: str,
            app_secret: str,
            tts_config: BaiduSpeechConfig,
    ):
        self._config = tts_config
        self._app_key = app_key
        self._app_secret = app_secret
        self.__token: str | None = None

    def _fetch_token(self) -> str:
        if self.__token is not None:
            return self.__token
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
            self.__token = result['access_token']
            return self.__token
        else:
            raise RuntimeError(
                'MAYBE API_KEY or SECRET_KEY not correct: access_token or scope not found in token response')

    def wave2text(self, wave_data: str) -> str:
        """
        语音内容转文字
        format: wav
        """
        length = len(wave_data)
        if length == 0:
            raise RuntimeError('speech data length read 0 bytes')
        speech = base64.b64encode(wave_data)
        speech = str(speech, 'utf-8')
        token = self._fetch_token()
        params = {
            'dev_pid': self._config.asr.dev_pid,
            # "lm_id" : LM_ID,    #测试自训练平台开启此项
            'format': self._config.asr.format,
            'rate': self._config.asr.rate,
            'token': token,
            'cuid': self._config.asr.cuid,
            'channel': 1,
            'speech': speech,
            'len': length,
        }
        post_data = json.dumps(params, sort_keys=False)
        # print post_data
        req = Request(self._config.asr.asr_url, post_data.encode('utf-8'))
        req.add_header('Content-Type', 'application/json')
        f = urlopen(req)
        result_str = f.read()
        result_data = json.loads(result_str)
        if result_data.get("err_no", -1) == 0:
            return "\n".join(result_data.get("result", ""))
        return result_str

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
        f = urlopen(req)
        result_str = f.read()
        headers = dict((name.lower(), value) for name, value in f.headers.items())

        has_error = 'content-type' not in headers.keys() or headers['content-type'].find('audio/') < 0
        if not has_error:
            with open(filename, 'wb') as of:
                of.write(result_str)
        else:
            raise RuntimeError("tts err:" + result_str)


class BaiduSpeechProvider(Provider):
    APP_KEY_ENV_NAME: ClassVar[str] = "BAIDU_APP_KEY"
    APP_SECRET_ENV_NAME: ClassVar[str] = "BAIDU_APP_SECRET"

    def __init__(self, relative_config_file_name: str = "baidu_speech.yml"):
        self.relative_config_file_name = relative_config_file_name

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return BaiduSpeechAdapter

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        shell = con.force_fetch(Shell)
        config_filename = "/".join([shell.config_path.rstrip("/"), self.relative_config_file_name])
        with open(config_filename, 'r') as f:
            config_data = yaml.safe_load(f)
        adapter_config = BaiduSpeechConfig(**config_data)
        app_key = os.environ.get(self.APP_KEY_ENV_NAME, "")
        app_secret = os.environ.get(self.APP_SECRET_ENV_NAME, "")
        if not app_key or not app_secret:
            raise BoostrapException("baidu app key or secret is empty")
        adapter = BaiduSpeechAdapter(app_key, app_secret, adapter_config)
        return adapter
