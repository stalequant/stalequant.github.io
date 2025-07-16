"""Unified wallet methods."""

from __future__ import annotations

__all__ = [
    "fetch_wallet_balance",
]

from ._alchemy import evm_fetch_wallet_holdings
from ._onchain_tools import to_checksum_address
from ._types import Balance
from ._types import ChainName
from ._types import EthAddressAsStr
from ._types import WalletHolding


async def fetch_wallet_balance(chain: ChainName, address: EthAddressAsStr) -> Balance:
    """Return a dict of coin symbols to their uiAmount."""
    return {v["symbol"]: v["uiAmount"] for v in await fetch_wallet_holdings(chain, address)}


async def fetch_wallet_holdings(
    chain: ChainName, address: EthAddressAsStr
) -> tuple[WalletHolding, ...]:
    """Return a tuple of base holding and token holdings with detail."""
    eth_address = to_checksum_address(address)
    return await evm_fetch_wallet_holdings(chain, eth_address)
