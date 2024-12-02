import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from hummingbot.connector.exchange.coinstore import coinstore_constants as CONSTANTS, coinstore_web_utils as web_utils
from hummingbot.core.data_type.common import TradeType
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, WSJSONRequest, WSPlainTextRequest
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger

if TYPE_CHECKING:
    from hummingbot.connector.exchange.coinstore.coinstore_exchange import CoinstoreExchange


class CoinstoreAPIOrderBookDataSource(OrderBookTrackerDataSource):

    _logger: Optional[HummingbotLogger] = None

    def __init__(self,
                 trading_pairs: List[str],
                 connector: 'CoinstoreExchange',
                 api_factory: WebAssistantsFactory):
        super().__init__(trading_pairs)
        self._connector = connector
        self._api_factory = api_factory

    async def get_last_traded_prices(self,
                                     trading_pairs: List[str],
                                     domain: Optional[str] = None) -> Dict[str, float]:
        return await self._connector.get_last_traded_prices(trading_pairs=trading_pairs)

    # Done
    async def _order_book_snapshot(self, trading_pair: str) -> OrderBookMessage:
        snapshot_response: Dict[str, Any] = await self._request_order_book_snapshot(trading_pair)
        snapshot_data: Dict[str, Any] = snapshot_response['data']
        snapshot_timestamp: float = int(time.time()) * 1e-3
        update_id: int = int(snapshot_timestamp)

        order_book_message_content = {
            "trading_pair": trading_pair,
            "update_id": update_id,
            "bids": [(bid[0], bid[1]) for bid in snapshot_data["b"]],
            "asks": [(ask[0], ask[1]) for ask in snapshot_data["a"]],
        }
        snapshot_msg: OrderBookMessage = OrderBookMessage(
            OrderBookMessageType.SNAPSHOT,
            order_book_message_content,
            snapshot_timestamp)

        return snapshot_msg

    # Done
    async def _request_order_book_snapshot(self, trading_pair: str) -> Dict[str, Any]:
        """
        Retrieves a copy of the full order book from the exchange, for a particular trading pair.

        :param trading_pair: the trading pair for which the order book will be retrieved

        :return: the response from the exchange (JSON dictionary)
        """

        rest_assistant = await self._api_factory.get_rest_assistant()
        symbol = (await self._connector.exchange_symbol_associated_to_pair(trading_pair=trading_pair)).split("/")[0]
        data = await rest_assistant.execute_request(
            url=web_utils.public_rest_url(path_url=f"{CONSTANTS.COINSTORE_ORDER_BOOK_PATH}/{symbol}"),
            method=RESTMethod.GET,
            throttler_limit_id=CONSTANTS.COINSTORE_ORDER_BOOK_PATH,
            is_auth_required=True,
            data={},
        )

        return data

    async def _parse_order_book_snapshot_message(self, raw_message: Dict[str, Any], message_queue: asyncio.Queue):
        pair = str(raw_message["symbol"]) + '/' + str(raw_message["instrumentId"])
        trading_pair = await self._connector.trading_pair_associated_to_exchange_symbol(symbol=pair)
        snapshot_data = raw_message
        snapshot_timestamp: float = int(time.time()) * 1e-3
        update_id: int = int(snapshot_timestamp)

        order_book_message_content = {
            "trading_pair": trading_pair,
            "update_id": update_id,
            "bids": [(bid[0], bid[1]) for bid in snapshot_data["b"]],
            "asks": [(ask[0], ask[1]) for ask in snapshot_data["a"]],
        }
        snapshot_msg: OrderBookMessage = OrderBookMessage(
            OrderBookMessageType.SNAPSHOT,
            order_book_message_content,
            snapshot_timestamp)

        message_queue.put_nowait(snapshot_msg)

    async def _parse_trade_message(self, raw_message: Dict[str, Any], message_queue: asyncio.Queue):

        if "data" in raw_message:
            await self._parse_trade_message_multipe(raw_message=raw_message, message_queue=message_queue)
        else:
            await self._parse_trade_message_single(raw_message=raw_message, message_queue=message_queue)

    async def _parse_trade_message_single(self, raw_message: Dict[str, Any], message_queue: asyncio.Queue):
        trade_data = raw_message
        pair = str(trade_data["symbol"]) + '/' + str(trade_data["instrumentId"])
        trading_pair = await self._connector.trading_pair_associated_to_exchange_symbol(symbol=pair)
        message_content = {
            "trade_id": trade_data["tradeId"],
            "trading_pair": trading_pair,
            "trade_type": float(TradeType.BUY.value) if trade_data["takerSide"] == "BUY" else float(
                TradeType.SELL.value),
            "amount": trade_data["volume"],
            "price": trade_data["price"]
        }
        trade_message: Optional[OrderBookMessage] = OrderBookMessage(
            message_type=OrderBookMessageType.TRADE,
            content=message_content,
            timestamp=(int(trade_data["time"]) * 1e-3))

        message_queue.put_nowait(trade_message)

    async def _parse_trade_message_multipe(self, raw_message: Dict[str, Any], message_queue: asyncio.Queue):
        trade_updates = raw_message["data"]

        for trade_data in trade_updates:
            pair = str(trade_data["symbol"]) + '/' + str(trade_data["instrumentId"])
            trading_pair = await self._connector.trading_pair_associated_to_exchange_symbol(symbol=pair)
            message_content = {
                "trade_id": trade_data["tradeId"],
                "trading_pair": trading_pair,
                "trade_type": float(TradeType.BUY.value) if trade_data["takerSide"] == "BUY" else float(
                    TradeType.SELL.value),
                "amount": trade_data["volume"],
                "price": trade_data["price"]
            }
            trade_message: Optional[OrderBookMessage] = OrderBookMessage(
                message_type=OrderBookMessageType.TRADE,
                content=message_content,
                timestamp=(int(trade_data["time"]) * 1e-3))

            message_queue.put_nowait(trade_message)


    async def _parse_order_book_diff_message(self, raw_message: Dict[str, Any], message_queue: asyncio.Queue):
        diff_updates: Dict[str, Any] = raw_message["data"]

        for diff_data in diff_updates:
            timestamp: float = int(diff_data["ts"]) * 1e-3
            update_id: int = int(timestamp)
            trading_pair = await self._connector.trading_pair_associated_to_exchange_symbol(
                symbol=raw_message["arg"]["instId"])

            order_book_message_content = {
                "trading_pair": trading_pair,
                "update_id": update_id,
                "bids": [(bid[0], bid[1]) for bid in diff_data["bids"]],
                "asks": [(ask[0], ask[1]) for ask in diff_data["asks"]],
            }
            diff_message: OrderBookMessage = OrderBookMessage(
                OrderBookMessageType.DIFF,
                order_book_message_content,
                timestamp)

            message_queue.put_nowait(diff_message)

    async def _subscribe_channels(self, ws: WSAssistant):
        try:
            for trading_pair in self._trading_pairs:
                symbol = (await self._connector.exchange_symbol_associated_to_pair(trading_pair=trading_pair)).split("/")[1]

                payload = {
                    "op": "SUB",
                    "channel": [
                            f"{symbol}@trade",
                    ],
                    'id': 1
                }
                subscribe_trade_request: WSJSONRequest = WSJSONRequest(payload=payload)

                payload = {
                    "op": "SUB",
                    "channel": [
                            f"{symbol}@depth@100",
                        ],
                    'id': 2
                }
                subscribe_orderbook_request: WSJSONRequest = WSJSONRequest(payload=payload)

                async with self._api_factory.throttler.execute_task(limit_id=CONSTANTS.WS_SUBSCRIPTION_LIMIT_ID):
                    await ws.send(subscribe_trade_request)
                async with self._api_factory.throttler.execute_task(limit_id=CONSTANTS.WS_SUBSCRIPTION_LIMIT_ID):
                    await ws.send(subscribe_orderbook_request)

            self.logger().info("Subscribed to public order book and trade channels...")
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger().exception("Unexpected error occurred subscribing to order book trading and delta streams...")
            raise

    def _channel_originating_message(self, event_message: Dict[str, Any]) -> str:
        channel = ""
        if "T" in event_message:
            event_channel = event_message['T']
            if event_channel == CONSTANTS.COINSTORE_WS_PUBLIC_TRADES_CHANNEL:
                channel = self._trade_messages_queue_key
            elif event_channel == CONSTANTS.COINSTORE_WS_ORDERS_CHANNEL:
                channel = self._diff_messages_queue_key
            elif event_channel == CONSTANTS.COINSTORE_WS_PUBLIC_BOOKS_CHANNEL:
                channel = self._snapshot_messages_queue_key
            else:
                channel = self._message_queue

        return channel

    async def _process_websocket_messages(self, websocket_assistant: WSAssistant):
        while True:
            try:
                await super()._process_websocket_messages(websocket_assistant=websocket_assistant)
            except asyncio.TimeoutError:
                pong_request = WSPlainTextRequest(payload="pong")
                await websocket_assistant.send(request=pong_request)

    async def _connected_websocket_assistant(self) -> WSAssistant:
        ws: WSAssistant = await self._api_factory.get_ws_assistant()
        async with self._api_factory.throttler.execute_task(limit_id=CONSTANTS.WS_CONNECTION_LIMIT_ID):
            await ws.connect(
                ws_url=CONSTANTS.COINSTORE_WS_URI_PUBLIC,
                message_timeout=CONSTANTS.SECONDS_TO_WAIT_TO_RECEIVE_MESSAGE)
        return ws
