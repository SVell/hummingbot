import sys

from hummingbot.core.api_throttler.data_types import RateLimit
from hummingbot.core.data_type.common import OrderType
from hummingbot.core.data_type.in_flight_order import OrderState

CLIENT_ID_PREFIX = "93027a12dac34fBC"
MAX_ID_LEN = 32
SECONDS_TO_WAIT_TO_RECEIVE_MESSAGE = 30 * 0.8

DEFAULT_DOMAIN = ""

# URLs

TOOBIT_BASE_URL = "https://api.toobit.com"
TOOBIT_PLACE_ORDER_PATH = '/api/v1/spot/order'
TOOBIT_ORDER_CANCEL_PATH = '/api/v1/spot/order'
TOOBIT_BALANCE_PATH = '/api/v1/account'
TOOBIT_TICKER_PATH = '/quote/v1/ticker/price'

ORDER_TYPE_MAP = {
    OrderType.LIMIT: "LIMIT",
    OrderType.MARKET: "MARKET",
    OrderType.LIMIT_MAKER: "LIMIT_MAKER",
}

# Doesn't include base URL as the tail is required to generate the signature

TOOBIT_SERVER_TIMEPATH = '/api/v1/time'
TOOBIT_TICKER_PATH = '/api/v1/exchangeInfo'

TOOBIT_ORDER_BOOK_PATH = '/quote/v1/depth'


# WS
TOOBIT_WS_URI_PUBLIC = "wss://stream.toobit.com/quote/ws/v1"
TOOBIT_WS_URI_PRIVATE = "wss://stream.toobit.com/api/v1/ws/"

TOOBIT_USER_STREAM_PATH_URL="/api/v1/userDataStream"

WS_HEARTBEAT_TIME_INTERVAL = 30




COINSTORE_INSTRUMENTS_PATH = '/api/v5/public/instruments'
COINSTORE_TICKER_PATH = '/api/v5/market/ticker'


COINSTORE_NETWORKS_PATH = '/api/v1/market/depth/BTCUSDT'
# Auth required

COINSTORE_BALANCE_PATH = '/api/spot/accountList'
COINSTORE_SYMBOL_PATH = '/api/v2/public/config/spot/symbols'

COINSTORE_ORDER_INFO_PATH = '/api/v2/trade/order/orderInfo'
CONSTORE_TRADE_INFO_PATH = '/api/trade/match/accountMatches'
COINSTORE_TICKER_PATH = '/api/v1/ticker/price'
COINSTORE_ORDER_DETAILS_PATH = '/api/v2/trade/order/active'
COINSTORE_ORDER_BOOK_PATH = '/api/v1/market/depth'



COINSTORE_WS_ACCOUNT_CHANNEL = "spot_asset"
COINSTORE_WS_ORDERS_CHANNEL = "spot_order"
COINSTORE_WS_PUBLIC_TRADES_CHANNEL = "trade"
COINSTORE_WS_PUBLIC_BOOKS_CHANNEL = "depth"

COINSTORE_WS_CHANNELS = {
    COINSTORE_WS_ACCOUNT_CHANNEL,
    COINSTORE_WS_ORDERS_CHANNEL
}

WS_CONNECTION_LIMIT_ID = "WSConnection"
WS_REQUEST_LIMIT_ID = "WSRequest"
WS_SUBSCRIPTION_LIMIT_ID = "WSSubscription"
WS_LOGIN_LIMIT_ID = "WSLogin"

ORDER_STATE = {
    "NOT_FOUND": OrderState.FAILED, # Not sure if this is correct
    "SUBMITTING": OrderState.PENDING_CREATE,
    "SUBMITTED": OrderState.CREATED,
    "PARTIAL_FILLED": OrderState.PARTIALLY_FILLED,
	"CANCELED": OrderState.CANCELED,
	"FILLED": OrderState.FILLED,
}



NO_LIMIT = sys.maxsize

RATE_LIMITS = [
    RateLimit(WS_CONNECTION_LIMIT_ID, limit=3, time_interval=1),
    RateLimit(WS_REQUEST_LIMIT_ID, limit=100, time_interval=10),
    RateLimit(WS_SUBSCRIPTION_LIMIT_ID, limit=240, time_interval=60 * 60),
    RateLimit(WS_LOGIN_LIMIT_ID, limit=1, time_interval=15),
    RateLimit(limit_id=TOOBIT_TICKER_PATH, limit=120, time_interval=3),
    RateLimit(limit_id=TOOBIT_BALANCE_PATH, limit=120, time_interval=3),
    RateLimit(limit_id=TOOBIT_SERVER_TIMEPATH, limit=120, time_interval=3),
    RateLimit(limit_id=TOOBIT_PLACE_ORDER_PATH, limit=120, time_interval=3),
    RateLimit(limit_id=TOOBIT_ORDER_CANCEL_PATH, limit=120, time_interval=3),
    RateLimit(limit_id=TOOBIT_USER_STREAM_PATH_URL, limit=120, time_interval=3),
    RateLimit(limit_id=TOOBIT_ORDER_BOOK_PATH, limit=120, time_interval=3),
]


