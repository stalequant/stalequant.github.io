"""Wallet data."""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Any
from typing import NewType

import aiosonic
import orjson
from eth_typing import HexStr

__all__ = [
    "WEI_AMOUNT_MAX",
    "WEI_DECIMALS_0",
    "WEI_DECIMALS_6",
    "WEI_DECIMALS_18",
    "ZERO_ADDRESS_ETH",
    "ChainName",
    "DecimalForWeiAmount",
    "EthAddressAsStr",
    "PrivateKey",
    "WalletHolding",
    "WeiAmount",
]


# ────────────────────────────────────────────────────────────────
# classes and types
import logging
from typing import TypedDict
from typing import cast

type Price = float


def info(*args) -> None:
    logging.info(str(*args))


type Coin = str

type Quantity = float


class ChainName(StrEnum):
    """The three letter name of the chain, e.g., ETH, HYP."""

    # ────────────────────────────────────────────────────────────────
    # MAIN
    ETH = "ETH"
    SOL = "SOL"
    BSC = "BSC"
    BASE = "BASE"
    OP = "OP"
    HYPE = "HYPE"
    ARB = "ARB"


WalletName = NewType("WalletName", str)
PrivateKey = NewType("PrivateKey", str)
WeiAmount = NewType("WeiAmount", int)
WEI_AMOUNT_MAX = cast("WeiAmount", 2**256 - 1)
DecimalForWeiAmount = NewType("DecimalForWeiAmount", int)


WEI_DECIMALS_6 = cast("DecimalForWeiAmount", 6)
WEI_DECIMALS_18 = cast("DecimalForWeiAmount", 18)
WEI_DECIMALS_0 = cast("DecimalForWeiAmount", 0)


class WalletHolding(TypedDict):
    """Detail of a wallet holding."""

    contract: EthAddressAsStr
    symbol: Coin
    amount: WeiAmount
    decimals: DecimalForWeiAmount
    uiAmount: Quantity
    info: dict


EthAddressAsStr = HexStr

ZERO_ADDRESS_ETH = HexStr("0x0000000000000000000000000000000000000000")

Balance = dict[Coin, Quantity]


type DollarAmount = float


def make_coin(coin: str) -> Coin:
    """Create a Coin object from a string.

    Args:
        coin: String representation of the coin

    Returns:
        Coin object

    """
    return cast("Coin", coin)


async def get_json(url: str, **kw) -> Any:
    """Return an json from a url using aiosonic get."""
    resp = await aiosonic.HTTPClient().get(url, **kw)
    return orjson.loads(await resp.content())


async def post_json(url: str, **kw) -> Any:
    """Return an json from a url using aiosonic post."""
    resp = await aiosonic.HTTPClient().post(url, **kw)
    return orjson.loads(await resp.content())


safe_create_task = asyncio.create_task


def addr_to_private_key(addr: EthAddressAsStr) -> str:
    raise NotImplementedError
