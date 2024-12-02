import hashlib
import hmac
import math
import urllib
from typing import Any, Dict

from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest, WSRequest


class CoinstoreAuth(AuthBase):

    def __init__(self, api_key: str, secret_key: str, time_provider: TimeSynchronizer):
        self.api_key: str = api_key
        self.secret_key: str = secret_key
        self.time_provider: TimeSynchronizer = time_provider

    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        headers = {}
        if request.headers is not None:
            headers.update(request.headers)
        headers.update(self.authentication_headers(request=request))
        request.headers = headers

        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        """
        This method is intended to configure a websocket request to be authenticated. OKX does not use this
        functionality
        """

        timestamp = int(self.time_provider.time() * 1000)
        key = self._calculate_key(timestamp)
        sign = self._calculate_sign(key, str(timestamp))

        channel = request.payload["channel"]

        payload = {
            "op": "login",
            "channel": channel,
            "auth": {
            "token": self.api_key,
            "type": "apikey",
            "expires": str(timestamp),
            "signature": sign,
            },
        }

        request.payload = payload
        return request  # pass-through

    def _calculate_key(self, timestamp: int) -> str:
        expires_key = str(math.floor(timestamp / 30000))
        expires_key = expires_key.encode("utf-8")
        key = hmac.new(self.secret_key.encode("utf-8"), expires_key, hashlib.sha256).hexdigest()
        return key

    def _calculate_sign(self, key: str, payload: str) -> str:
        sign = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return sign

    def authentication_headers(self, request: RESTRequest) -> Dict[str, Any]:
        timestamp = int(self.time_provider.time() * 1000)

        payload: str = ""

        

        if request.params:
            payload = urllib.parse.urlencode(request.params)
        

        if request.data:
            if request.data == '{}':
                payload = payload + str(request.data)
            else:
                payload = request.data

        if payload == "":
            payload = "{}"

        key = self._calculate_key(timestamp)
        sign = self._calculate_sign(key, payload)

        
        headers = {
            'X-CS-APIKEY': self.api_key,
            'X-CS-SIGN': sign,
            'X-CS-EXPIRES': str(timestamp),
        }

        return headers
