import asyncio
import hashlib
import hmac
import math
from unittest import TestCase
from unittest.mock import MagicMock
from urllib.parse import urlencode

from typing_extensions import Awaitable

from hummingbot.connector.exchange.coinstore.coinstore_auth import CoinstoreAuth
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest


class CoinsotreAuthTests(TestCase):

    def setUp(self) -> None:
        self._api_key = "testApiKey"
        self._secret = "testSecret"

    def async_run_with_timeout(self, coroutine: Awaitable, timeout: float = 1):
        ret = asyncio.get_event_loop().run_until_complete(asyncio.wait_for(coroutine, timeout))
        return ret

    def test_rest_authenticate(self):
        now = 1234567890
        mock_time_provider = MagicMock()
        mock_time_provider.time.return_value = now

        params = ""
        data = {}

        payload = params + str(data)

        auth = CoinstoreAuth(api_key=self._api_key, secret_key=self._secret,time_provider=mock_time_provider)
        request = RESTRequest(method=RESTMethod.POST, params=params, is_auth_required=True, data=data)
        configured_request = self.async_run_with_timeout(auth.rest_authenticate(request))

        expires = int(now * 1000)
        expires_key = str(math.floor(expires / 30000))
        expires_key = expires_key.encode("utf-8")
        key = hmac.new(self._secret.encode("utf-8"), expires_key, hashlib.sha256).hexdigest()
        key = key.encode("utf-8")
        payload = payload.encode("utf-8")
        signature = hmac.new(key, payload, hashlib.sha256).hexdigest()


        self.assertEqual(str(expires), configured_request.headers["X-CS-EXPIRES"])
        self.assertEqual(signature, configured_request.headers["X-CS-SIGN"])
        self.assertEqual(self._api_key, configured_request.headers["X-CS-APIKEY"])

    def test_rest_authenticate_params_data(self):
        now = 1234567890
        mock_time_provider = MagicMock()
        mock_time_provider.time.return_value = now

        params = "symbol=aaaa88&size=10"
        data = {"symbol":"aaaa88","side":"SELL","ordType":"LIMIT","ordPrice":2,"ordQty":1,"timestamp":1627384801051}

        payload = params + str(data)

        auth = CoinstoreAuth(api_key=self._api_key, secret_key=self._secret,time_provider=mock_time_provider)
        request = RESTRequest(method=RESTMethod.POST, params=params, is_auth_required=True, data=data)
        configured_request = self.async_run_with_timeout(auth.rest_authenticate(request))

        expires = int(now * 1000)
        expires_key = str(math.floor(expires / 30000))
        expires_key = expires_key.encode("utf-8")
        key = hmac.new(self._secret.encode("utf-8"), expires_key, hashlib.sha256).hexdigest()
        key = key.encode("utf-8")
        payload = payload.encode("utf-8")
        signature = hmac.new(key, payload, hashlib.sha256).hexdigest()


        self.assertEqual(str(expires), configured_request.headers["X-CS-EXPIRES"])
        self.assertEqual(signature, configured_request.headers["X-CS-SIGN"])
        self.assertEqual(self._api_key, configured_request.headers["X-CS-APIKEY"])
