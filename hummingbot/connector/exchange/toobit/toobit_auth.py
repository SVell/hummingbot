import base64
import hashlib
import hmac
import json
import urllib
from collections import OrderedDict
from typing import Any, Dict
from urllib.parse import urlencode

from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest, WSRequest


class ToobitAuth(AuthBase):

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

        if request.params is None:
            request.params = {}
            newData = json.loads(request.data)
            newData["signature"] = headers["X-BB-SIGN"]
            request.data = newData
            
        request.params["signature"] = headers["X-BB-SIGN"]

        if request.data is not None:
            newData = json.loads(request.data)
            newData["signature"] = headers["X-BB-SIGN"]
            request.data = newData

        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        return request  # pass-through

    @staticmethod
    def keysort(dictionary: Dict[str, str]) -> Dict[str, str]:
        return OrderedDict(sorted(dictionary.items(), key=lambda t: t[0]))

    def _calculate_sign(self, key: str, payload: str) -> str:
        sign = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return sign

    def authentication_headers(self, request: RESTRequest) -> Dict[str, Any]:
        payload: str = ""

        if request.params:
            payload = urllib.parse.urlencode(request.params)
        
        if request.data:
            if request.data != '{}':
                payload = payload + urllib.parse.urlencode(json.loads(request.data))
                

        if payload == "":
            payload = "{}"

        sign = self._calculate_sign(self.secret_key, payload)


        header = {
            "X-BB-APIKEY": self.api_key,
            "X-BB-SIGN": sign,
        }

        return header

    def websocket_login_parameters(self) -> Dict[str, Any]:
        timestamp = str(int(self.time_provider.time()))

        return {
            "apiKey": self.api_key,
            "passphrase": self.passphrase,
            "timestamp": timestamp,
            "sign": self._generate_signature(timestamp, "GET", "/users/self/verify")
        }
