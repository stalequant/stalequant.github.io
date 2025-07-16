"""get prices from kitten swap."""

from __future__ import annotations

__all__ = [
    "get_kittenswap_prices",
]

from typing import Any
from typing import cast

from ._types import Coin
from ._types import Price
from ._types import get_json


# ────────────────────────────────────────────────────────────────
# public
async def get_kittenswap_prices() -> dict[tuple[Coin, Coin], Price]:
    all_details = await get_json(
        url="https://api.kittenswap.finance/pairs-data", headers={"accept": "*/*"}
    )

    all_prices = {}
    for d in sorted(cast("list[dict[str, Any]]", all_details), key=_liquidity_sort):
        if not d:
            continue

        base_symbol = d["baseToken"]["symbol"].upper().replace("₮", "T")
        quote_symbol = d["quoteToken"]["symbol"].upper().replace("₮", "T")
        price = float(d["priceNative"])
        if base_symbol < quote_symbol:
            all_prices[base_symbol, quote_symbol] = price
        else:
            all_prices[quote_symbol, base_symbol] = 1 / price
    return all_prices


# ────────────────────────────────────────────────────────────────
# private


def _liquidity_sort(x: dict[str, Any]) -> float:
    return not x or float(x.get("liquidity", {}).get("usd", -1))
