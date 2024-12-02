import time
from typing import Callable, Optional
from urllib.parse import urljoin

import hummingbot.connector.exchange.coinstore.coinstore_constants as CONSTANTS
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.connector.utils import TimeSynchronizerRESTPreProcessor
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


def public_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """
    Creates a full URL for provided REST endpoint

    :param path_url: a public REST endpoint
    :param domain: not required for Coinstore. Added only for compatibility.

    :return: the full URL to the endpoint
    """
    return urljoin(CONSTANTS.COINSTORE_BASE_URL, path_url)


def private_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    return public_rest_url(path_url, domain)


def build_api_factory(
    throttler: Optional[AsyncThrottler] = None,
    domain: str = CONSTANTS.DEFAULT_DOMAIN,
    auth: Optional[AuthBase] = None,
) -> WebAssistantsFactory:
    throttler = throttler or create_throttler()
    api_factory = WebAssistantsFactory(throttler=throttler, auth=auth)
    return api_factory


def create_throttler() -> AsyncThrottler:
    return AsyncThrottler(CONSTANTS.RATE_LIMITS)


async def get_current_server_time(
    throttler: Optional[AsyncThrottler] = None,
    domain: str = CONSTANTS.DEFAULT_DOMAIN,
) -> int:
    return int(time.time() * 1e3)
