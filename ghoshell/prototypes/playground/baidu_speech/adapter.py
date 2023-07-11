import base64
import json
import os
from typing import Dict, Type, ClassVar
from urllib.parse import urlencode, quote_plus

import requests
import yaml

from ghoshell.container import Provider, Container, Contract
from ghoshell.prototypes.playground.baidu_speech.config import BaiduSpeechConfig
from ghoshell.shell import Shell, BoostrapException


#
# import requests.packages.urllib3.util.connection as urllib3_cn
#
#
# def allowed_gai_family():
#     """
#      https://github.com/shazow/urllib3/blob/master/urllib3/util/connection.py
#     """
#     family = socket.AF_INET
#     if urllib3_cn.HAS_IPV6:
#         family = socket.AF_INET6  # force ipv6 only if it is available
#     return family
#
#
# urllib3_cn.allowed_gai_family = allowed_gai_family


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
        resp = requests.get(self._config.token_url, post_data)

        result = resp.json()
        if 'access_token' in result.keys() and 'scope' in result.keys():
            self.__token = result['access_token']
            return self.__token
        else:
            raise RuntimeError(
                'MAYBE API_KEY or SECRET_KEY not correct: access_token or scope not found in token response')

    def wave2text(self, wave_data: bytes) -> str:
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
        resp = requests.post(
            self._config.asr.asr_url,
            post_data.encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        result_str = resp.text

        result_data = json.loads(result_str)
        if result_data.get("err_no", -1) == 0:
            return "\n".join(result_data.get("result", ""))
        return result_str

    def text2speech(self, text: str) -> bytes:
        """
        文字内容转语音.
        随便写写.
        """
        token = self._fetch_token()
        text = quote_plus(text)
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
        payload = urlencode(params)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*'
        }

        resp = requests.request(
            "POST",
            self._config.tts.tts_url,
            headers=headers,
            data=payload,
        )

        result_str = resp.content

        headers = dict((name.lower(), value) for name, value in resp.headers.items())
        has_error = 'content-type' not in headers.keys() or headers['content-type'].find('audio/') < 0
        if not has_error:
            return result_str
        else:
            raise RuntimeError("tts err:" + str(result_str) + "; text: " + text)


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
