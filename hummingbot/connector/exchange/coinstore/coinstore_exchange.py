import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from bidict import bidict

from hummingbot.connector.exchange.coinstore import (
    coinstore_constants as CONSTANTS,
    coinstore_utils,
    coinstore_web_utils as web_utils,
)
from hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source import CoinstoreAPIOrderBookDataSource
from hummingbot.connector.exchange.coinstore.coinstore_api_user_stream_data_source import (
    CoinstoreAPIUserStreamDataSource,
)
from hummingbot.connector.exchange.coinstore.coinstore_auth import CoinstoreAuth
from hummingbot.connector.exchange_base import s_decimal_NaN
from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderState, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import TokenAmount, TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.utils.estimate_fee import build_trade_fee
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

if TYPE_CHECKING:
    from hummingbot.client.config.config_helpers import ClientConfigAdapter


class CoinstoreExchange(ExchangePyBase):

    web_utils = web_utils

    def __init__(self,
                 client_config_map: "ClientConfigAdapter",
                 coinstore_api_key: str,
                 coinstore_secret_key: str,
                 trading_pairs: Optional[List[str]] = None,
                 trading_required: bool = True):
        self.coinstore_api_key = coinstore_api_key
        self.coinstore_secret_key = coinstore_secret_key
        self._trading_required = trading_required
        self._trading_pairs = trading_pairs
        super().__init__(client_config_map)

    @property
    def authenticator(self):
        return CoinstoreAuth(
            api_key=self.coinstore_api_key,
            secret_key=self.coinstore_secret_key,
            time_provider=self._time_synchronizer)

    @property
    def name(self) -> str:
        return "coinstore"

    @property
    def rate_limits_rules(self):
        return CONSTANTS.RATE_LIMITS

    @property
    def domain(self):
        return ""

    @property
    def client_order_id_max_length(self):
        return CONSTANTS.MAX_ID_LEN

    @property
    def client_order_id_prefix(self):
        return CONSTANTS.CLIENT_ID_PREFIX

    @property
    def trading_rules_request_path(self) -> str:
        return CONSTANTS.COINSTORE_SYMBOL_PATH

    @property
    def trading_pairs_request_path(self):
        return CONSTANTS.COINSTORE_SYMBOL_PATH

    @property
    def check_network_request_path(self):
        return CONSTANTS.COINSTORE_NETWORKS_PATH

    @property
    def trading_pairs(self):
        return self._trading_pairs

    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return False

    @property
    def is_trading_required(self) -> bool:
        return self._trading_required

    def supported_order_types(self):
        return [OrderType.LIMIT, OrderType.LIMIT_MAKER, OrderType.MARKET]

    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception):
        # TODO: implement this method correctly for the connector
        return False

    def _is_order_not_found_during_status_update_error(self, status_update_exception: Exception) -> bool:
        # TODO: implement this method correctly for the connector
        # The default implementation was added when the functionality to detect not found orders was introduced in the
        # ExchangePyBase class. Also fix the unit test test_lost_order_removed_if_not_found_during_order_status_update
        # when replacing the dummy implementation
        return False

    def _is_order_not_found_during_cancelation_error(self, cancelation_exception: Exception) -> bool:
        # TODO: implement this method correctly for the connector
        # The default implementation was added when the functionality to detect not found orders was introduced in the
        # ExchangePyBase class. Also fix the unit test test_cancel_order_not_found_in_the_exchange when replacing the
        # dummy implementation
        return False

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(
            throttler=self._throttler,
            auth=self._auth)

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        return CoinstoreAPIOrderBookDataSource(
            trading_pairs=self.trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory)

    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        return CoinstoreAPIUserStreamDataSource(
            auth=self._auth,
            connector=self,
            api_factory=self._web_assistants_factory)

    async def _make_network_check_request(self):
        res = await self._api_request(
            path_url=CONSTANTS.COINSTORE_NETWORKS_PATH,
            method=RESTMethod.GET,
            data={},
            params={},
            is_auth_required=True,
            limit_id=CONSTANTS.COINSTORE_NETWORKS_PATH,
        )


    def _get_fee(self,
                 base_currency: str,
                 quote_currency: str,
                 order_type: OrderType,
                 order_side: TradeType,
                 amount: Decimal,
                 price: Decimal = s_decimal_NaN,
                 is_maker: Optional[bool] = None) -> TradeFeeBase:

        is_maker = is_maker or (order_type is OrderType.LIMIT_MAKER)
        fee = build_trade_fee(
            self.name,
            is_maker,
            base_currency=base_currency,
            quote_currency=quote_currency,
            order_type=order_type,
            order_side=order_side,
            amount=amount,
            price=price,
        )
        return fee

    async def _initialize_trading_pair_symbol_map(self):
        try:
            exchange_info = await self._api_request(
                method=RESTMethod.POST, 
                path_url=self.trading_pairs_request_path,
                limit_id=self.trading_pairs_request_path,
                is_auth_required=True,
                data={},
                params={},
            )
            self._initialize_trading_pair_symbols_from_exchange_info(exchange_info=exchange_info)
        except Exception:
            self.logger().exception("There was an error requesting exchange info.")

    def _initialize_trading_pair_symbols_from_exchange_info(self, exchange_info: Dict[str, Any]):
        mapping = bidict()
        for symbol_data in exchange_info["data"]:
            if not coinstore_utils.is_exchange_information_valid(traid_pair=symbol_data):
                continue

            mapping[str(symbol_data["symbolCode"]) + "/" + str(symbol_data["symbolId"])] = combine_to_hb_trading_pair(
                base=symbol_data["tradeCurrencyCode"],
                quote=symbol_data["quoteCurrencyCode"]
            )
        self._set_trading_pair_symbol_map(mapping)

    async def _place_order(self,
                           order_id: str,
                           trading_pair: str,
                           amount: Decimal,
                           trade_type: TradeType,
                           order_type: OrderType,
                           price: Decimal,
                           **kwargs) -> Tuple[str, float]:

        data = {
            "clOrdId": order_id,
            "symbol": (await self.exchange_symbol_associated_to_pair(trading_pair=trading_pair)).split('/')[0],
            "side": trade_type.name,
            "ordType": CONSTANTS.ORDER_TYPE_MAP[order_type],
            "timestamp": int(self.current_timestamp * 1e3),
        }
        if order_type.is_limit_type():
            data["ordPrice"] = str(price)
            data["ordQty"] = str(amount)
        else:
            data["ordAmt"] = str(amount)

        exchange_order_id = await self._api_request(
            path_url=CONSTANTS.COINSTORE_PLACE_ORDER_PATH,
            method=RESTMethod.POST,
            data=data,
            is_auth_required=True,
            limit_id=CONSTANTS.COINSTORE_PLACE_ORDER_PATH,
        )
        if exchange_order_id["code"] != 0:
            raise IOError(f"Error submitting order {order_id}: {data['sMsg']}")

        data = exchange_order_id["data"]
        
        return str(data["ordId"]), self.current_timestamp

    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder):
        """
        This implementation specific function is called by _cancel, and returns True if successful
        """
        params = {
            "ordId": tracked_order.exchange_order_id,
            "symbol": (await self.exchange_symbol_associated_to_pair(trading_pair=tracked_order.trading_pair)).split('/')[0]
        }
        cancel_result = await self._api_request(
            method=RESTMethod.POST,
            path_url=CONSTANTS.COINSTORE_ORDER_CANCEL_PATH,
            data=params,
            is_auth_required=True,
            limit_id=CONSTANTS.COINSTORE_ORDER_CANCEL_PATH
        )
        if cancel_result["code"] == 0:
            final_result = True
        else:
            raise IOError(f"Error cancelling order {order_id}: {cancel_result}")

        return final_result

    async def _get_last_traded_price(self, trading_pair: str) -> float:
        symbol = (await self.exchange_symbol_associated_to_pair(trading_pair=trading_pair)).split('/')[0]
        
        resp_json = await self._api_request(
            path_url=CONSTANTS.COINSTORE_TICKER_PATH,
            method=RESTMethod.GET,
            throttler_limit_id=CONSTANTS.COINSTORE_TICKER_PATH,
            is_auth_required=True,
            data={},
        )

        ticker_data = resp_json["data"]

        # TODO: FIX
        for item in ticker_data:
            if item["symbol"] == symbol:
                return float(item["price"])
    
        raise ValueError(f"Symbol {symbol} not found in ticker data")

    async def _update_balances(self):
        # data should be empty object here, balance is post request
        msg = await self._api_request(
            method=RESTMethod.POST,
            path_url=CONSTANTS.COINSTORE_BALANCE_PATH,
            is_auth_required=True,
            data={})

        
        balances = msg['data']

        self._account_available_balances.clear()
        self._account_balances.clear()

        for balance in balances:
            self._update_balance_from_details(balance_details=balance)


    def _update_balance_from_details(self, balance_details: Dict[str, Any]):
        currency = balance_details["currency"]
        balance = Decimal(balance_details["balance"])
        balance_type = balance_details["type"]

        if currency in self._account_balances:
            if balance_type == 1: 
                self._account_balances[currency] += balance
                self._account_available_balances[currency] += balance
            elif balance_type == 4:
                self._account_balances[currency] += balance
        else:
            if balance_type == 1: 
                self._account_balances[currency] = balance
                self._account_available_balances[currency] = balance
            elif balance_type == 4:
                self._account_balances[currency] = balance
                self._account_available_balances[currency] = 0
            

    async def _update_trading_rules(self):
        exchange_info = await self._api_request(
            method=RESTMethod.POST, 
            path_url=self.trading_pairs_request_path,
            limit_id=self.trading_pairs_request_path,
            is_auth_required=True,
            data={},
            params={},
        )
        trading_rules_list = await self._format_trading_rules(exchange_info["data"])
        self._trading_rules.clear()
        for trading_rule in trading_rules_list:
            self._trading_rules[trading_rule.trading_pair] = trading_rule
        self._initialize_trading_pair_symbols_from_exchange_info(exchange_info=exchange_info)


    async def _format_trading_rules(self, raw_trading_pair_info: List[Dict[str, Any]]) -> List[TradingRule]:
        trading_rules = []

        for symbol_data in raw_trading_pair_info:
            try:
                pair = str(symbol_data["symbolCode"]) + "/" + str(symbol_data["symbolId"])
                trading_rules.append(TradingRule(
                    trading_pair=await self.trading_pair_associated_to_exchange_symbol(symbol=pair),
                    min_order_size=Decimal(symbol_data["minLmtSz"]),
                    min_price_increment=Decimal(symbol_data["tickSz"]),
                    min_base_amount_increment=Decimal(symbol_data["minLmtSz"]),
                ))
            except Exception:
                self.logger().exception(f"Error parsing the trading pair rule {symbol_data}. Skipping.")
        return trading_rules

    async def _update_trading_fees(self):
        """
        Update fees information from the exchange
        """
        pass

    async def _request_order_update(self, order: InFlightOrder) -> Dict[str, Any]:
        """
        Get order status from the exchange
        """
        return await self._api_request(
            method=RESTMethod.GET,
            path_url=CONSTANTS.COINSTORE_ORDER_INFO_PATH,
            params={
                "ordId": await order.get_exchange_order_id()},
            is_auth_required=True)

    async def _request_order_fills(self, order: InFlightOrder) -> Dict[str, Any]:
        return await self._api_request(
            method=RESTMethod.GET,
            path_url=CONSTANTS.CONSTORE_TRADE_INFO_PATH,
            params={
                "symbol": (await self.exchange_symbol_associated_to_pair(trading_pair=order.trading_pair)).split('/')[0],
                },
            is_auth_required=True,
            limit_id=CONSTANTS.CONSTORE_TRADE_INFO_PATH);

    def _find_order_by_order_id(self, order_list, order_id):
        for order in order_list:
            if order['orderId'] == order_id:
                return order
        return None

    async def _all_trade_updates_for_order(self, order: InFlightOrder) -> List[TradeUpdate]:
        trade_updates = []

        if order.exchange_order_id is not None:
            all_fills_response = await self._request_order_update(order=order)
            fill_data = all_fills_response["data"]

            fee = TradeFeeBase.new_spot_fee(
                fee_schema=self.trade_fee_schema(),
                trade_type=order.trade_type,
                percent_token=fill_data["qtoteCurrency"],
                flat_fees=[TokenAmount(amount=0, token=fill_data["quoteCurrency"])]
            )
            trade_update = TradeUpdate(
                trade_id=str(fill_data["ordId"]),
                client_order_id=order.client_order_id,
                exchange_order_id=str(fill_data["clOrdId"]),
                trading_pair=order.trading_pair,
                fill_base_amount=Decimal(Decimal(fill_data['ordQty']) - Decimal(fill_data["leavesQty"])),
                fill_quote_amount=Decimal(fill_data["cumAmt"]),
                fill_price=Decimal(fill_data["avgPrice"]),
                fill_timestamp=int(fill_data["timestamp"]) * 1e-3,
                fee=fee,
                )
            trade_updates.append(trade_update)

        return trade_updates

    async def _request_order_status(self, tracked_order: InFlightOrder) -> OrderUpdate:
        updated_order_data = await self._request_order_update(order=tracked_order)

        order_data = updated_order_data["data"]
        new_state = CONSTANTS.ORDER_STATE[order_data["ordStatus"]]

        order_update = OrderUpdate(
            client_order_id=tracked_order.client_order_id,
            exchange_order_id=str(order_data["ordId"]),
            trading_pair=tracked_order.trading_pair,
            update_timestamp=int(order_data["timestamp"]) * 1e-3, #?
            new_state=new_state,
        )
        return order_update

    async def _user_stream_event_listener(self):
        async for stream_message in self._iter_user_event_queue():
            try:
                channel = stream_message.get("T", None)

                if channel == CONSTANTS.COINSTORE_WS_ORDERS_CHANNEL:
                    for data in stream_message.get("orderVoList", []):
                        order_status = CONSTANTS.ORDER_STATE[data["ordStatus"]]
                        client_order_id = data["clOrdId"]
                        trade_id = data["ordId"]
                        fillable_order = self._order_tracker.all_fillable_orders.get(client_order_id)
                        updatable_order = self._order_tracker.all_updatable_orders.get(client_order_id)

                        if (fillable_order is not None
                                and order_status in [OrderState.PARTIALLY_FILLED, OrderState.FILLED]
                                and trade_id):
                            fee = TradeFeeBase.new_spot_fee(
                                fee_schema=self.trade_fee_schema(),
                                trade_type=fillable_order.trade_type,
                                percent_token=data["fillFeeCcy"],
                               flat_fees=[TokenAmount(amount=Decimal(data["fillFee"]), token=data["fillFeeCcy"])]
                            )
                            trade_update = TradeUpdate(
                                trade_id=str(trade_id),
                                client_order_id=fillable_order.client_order_id,
                                exchange_order_id=str(data["ordId"]),
                                trading_pair=fillable_order.trading_pair,
                                fill_base_amount=Decimal(data["fillSz"]),
                                fill_quote_amount=Decimal(data["fillSz"]) * Decimal(data["fillPx"]),
                                fill_price=Decimal(data["fillPx"]),
                                fill_timestamp=int(data["uTime"]) * 1e-3,
                            )
                            self._order_tracker.process_trade_update(trade_update)

                        if updatable_order is not None:
                            order_update = OrderUpdate(
                                trading_pair=updatable_order.trading_pair,
                                update_timestamp=int(data["timestamp"]) * 1e-3,
                                new_state=order_status,
                                client_order_id=updatable_order.client_order_id,
                                exchange_order_id=str(data["ordId"]),
                            )
                            self._order_tracker.process_order_update(order_update=order_update)

                elif channel == CONSTANTS.COINSTORE_WS_ACCOUNT_CHANNEL:
                    for data in stream_message.get("assets", []):
                        if data["btcValuation"] != "0":
                            self._update_balance_from_ws(balance_details=data)

            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().exception("Unexpected error in user stream listener loop.")
                await self._sleep(5.0)

    def _update_balance_from_ws(self, balance_details: Dict[str, Any]):
        currency = balance_details["symbol"]
        balance = Decimal(balance_details["usdValuation"])
        balance_type = 1

        if currency in self._account_balances:
            if balance_type == 1: 
                self._account_balances[currency] += balance
                self._account_available_balances[currency] += balance
            elif balance_type == 4:
                self._account_balances[currency] += balance
        else:
            if balance_type == 1: 
                self._account_balances[currency] = balance
                self._account_available_balances[currency] = balance
            elif balance_type == 4:
                self._account_balances[currency] = balance
                self._account_available_balances[currency] = 0