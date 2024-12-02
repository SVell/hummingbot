from decimal import Decimal
from typing import Any, Dict

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0008"),
    taker_percent_fee_decimal=Decimal("0.0001"),
)

CENTRALIZED = True

EXAMPLE_PAIR = "BTC-USDT"


class CoinstoreConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="coinstore", const=True, client_data=None)
    coinstore_api_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Coinstore API key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        ),
    )
    coinstore_secret_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Coinstore secret key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        ),
    )


KEYS = CoinstoreConfigMap.construct()


def is_exchange_information_valid(traid_pair) -> bool:
    """
    Verifies if a trading pair is enabled to operate with based on its exchange information

    :param exchange_info: the exchange information for a trading pair

    :return: True if the trading pair is enabled, False otherwise
    """
    return traid_pair["openTrade"]
