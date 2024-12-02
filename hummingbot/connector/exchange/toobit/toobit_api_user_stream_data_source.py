import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from hummingbot.connector.exchange.toobit import toobit_constants as CONSTANTS
from hummingbot.connector.exchange.toobit.toobit_auth import ToobitAuth
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, WSJSONRequest, WSPlainTextRequest
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger

if TYPE_CHECKING:
    from hummingbot.connector.exchange.toobit.toobit_exchange import ToobitExchange


class ToobitAPIUserStreamDataSource(UserStreamTrackerDataSource):

    _logger: Optional[HummingbotLogger] = None

    def __init__(
            self,
            auth: ToobitAuth,
            connector: 'ToobitExchange',
            api_factory: WebAssistantsFactory):
        super().__init__()
        self._auth: ToobitAuth = auth
        self._connector = connector
        self._api_factory = api_factory
        self.LISTEN_KEY_KEEP_ALIVE_INTERVAL = 5000
        self._listen_key_initialized_event: asyncio.Event = asyncio.Event()
        self._last_listen_key_ping_ts = 0
        self._current_listen_key = None

    async def _connected_websocket_assistant(self) -> WSAssistant:
        """
        Creates an instance of WSAssistant connected to the exchange
        """
        self._manage_listen_key_task = safe_ensure_future(self._manage_listen_key_task_loop())
        await self._listen_key_initialized_event.wait()

        ws: WSAssistant = await self._get_ws_assistant()
        url = f"{CONSTANTS.TOOBIT_WS_URI_PRIVATE}/{self._current_listen_key}"
        await ws.connect(ws_url=url, ping_timeout=CONSTANTS.WS_HEARTBEAT_TIME_INTERVAL)
        return ws

    async def _manage_listen_key_task_loop(self):
        try:
            while True:
                now = int(time.time())
                if self._current_listen_key is None:
                    self._current_listen_key = await self._get_listen_key()
                    self.logger().info(f"Successfully obtained listen key {self._current_listen_key}")
                    self._listen_key_initialized_event.set()
                    self._last_listen_key_ping_ts = int(time.time())

                if now - self._last_listen_key_ping_ts >= self.LISTEN_KEY_KEEP_ALIVE_INTERVAL:
                    success: bool = await self._ping_listen_key()
                    if not success:
                        self.logger().error("Error occurred renewing listen key ...")
                        break
                    else:
                        self.logger().info(f"Refreshed listen key {self._current_listen_key}.")
                        self._last_listen_key_ping_ts = int(time.time())
                else:
                    await self._sleep(self.LISTEN_KEY_KEEP_ALIVE_INTERVAL)
        finally:
            self._current_listen_key = None
            self._listen_key_initialized_event.clear()

    async def _get_listen_key(self):
        try:
            data = await self._connector._api_request(
                method=RESTMethod.POST,
                path_url=CONSTANTS.TOOBIT_USER_STREAM_PATH_URL,
                params={"timestamp": int(self._connector._time_synchronizer.time())},
                limit_id=CONSTANTS.TOOBIT_USER_STREAM_PATH_URL,
                is_auth_required=True
            )
        except asyncio.CancelledError:
            raise
        except Exception as exception:
            raise IOError(f"Error fetching user stream listen key. Error: {exception}")

        return data["listenKey"]

    async def _ping_listen_key(self) -> bool:
        try:
            data = await self._connector._api_request(
                path_url=CONSTANTS.TOOBIT_USER_STREAM_PATH_URL,
                params={"listenKey": self._current_listen_key,
                        "timestamp": self._connector._time_synchronizer.time()},
                method=RESTMethod.PUT,
                return_err=True,
                limit_id=CONSTANTS.TOOBIT_USER_STREAM_PATH_URL,
                is_auth_required=True
            )

            if "code" in data:
                self.logger().warning(f"Failed to refresh the listen key {self._current_listen_key}: {data}")
                return False

        except asyncio.CancelledError:
            raise
        except Exception as exception:
            self.logger().warning(f"Failed to refresh the listen key {self._current_listen_key}: {exception}")
            return False

        return True

    async def _subscribe_channels(self, websocket_assistant: WSAssistant):
        try:
            payload = {
                "topic": "outboundAccountInfo",
                "event": "sub"
            }
            subscribe_account_request: WSJSONRequest = WSJSONRequest(payload=payload)

            payload = {
                "topic": "executionReport",
                "event": "sub"
            }
            subscribe_orders_request: WSJSONRequest = WSJSONRequest(payload=payload)

            async with self._api_factory.throttler.execute_task(limit_id=CONSTANTS.WS_SUBSCRIPTION_LIMIT_ID):
                await websocket_assistant.send(subscribe_account_request)
            async with self._api_factory.throttler.execute_task(limit_id=CONSTANTS.WS_SUBSCRIPTION_LIMIT_ID):
                await websocket_assistant.send(subscribe_orders_request)
            self.logger().info("Subscribed to private account and orders channels...")
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger().exception("Unexpected error occurred subscribing to order book trading and delta streams...")
            raise

    async def _process_websocket_messages(self, websocket_assistant: WSAssistant, queue: asyncio.Queue):
        while True:
            try:
                await super()._process_websocket_messages(
                    websocket_assistant=websocket_assistant,
                    queue=queue)
            except asyncio.TimeoutError:
                ping_request = WSPlainTextRequest(payload="ping")
                await websocket_assistant.send(request=ping_request)

    async def _process_event_message(self, event_message: Dict[str, Any], queue: asyncio.Queue):
        if len(event_message) > 0 and "data" in event_message:
            queue.put_nowait(event_message)

    async def _get_ws_assistant(self) -> WSAssistant:
        if self._ws_assistant is None:
            self._ws_assistant = await self._api_factory.get_ws_assistant()
        return self._ws_assistant
