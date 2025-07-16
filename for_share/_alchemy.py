"""Alchemy API helpers."""

from __future__ import annotations

__all__ = [
    "evm_fetch_wallet_holdings",
]

from asyncio import gather
from typing import cast

from ._alchemy_api import AlchemyTokenBalanceItem
from ._alchemy_api import alchemy_get_token_balances
from ._alchemy_api import alchemy_get_token_metadata
from ._eth_rpc import rpc_eth_get_balance
from ._onchain_tools import to_checksum_address
from ._types import WEI_DECIMALS_18
from ._types import ZERO_ADDRESS_ETH
from ._types import ChainName
from ._types import EthAddressAsStr
from ._types import Quantity
from ._types import WalletHolding
from ._types import WeiAmount
from ._types import make_coin


async def evm_fetch_wallet_holdings(
    chain: ChainName, address: EthAddressAsStr
) -> tuple[WalletHolding, ...]:
    """Fetch wallet holdings for evm."""
    raw_balances = await alchemy_get_token_balances(chain, address)
    return (
        await _evm_make_base_holding(chain, address),
        *await gather(
            *[
                _evm_make_token_holding(chain, token_info)
                for token_info in raw_balances.token_balances
                if token_info.token_balance
            ]
        ),
    )


# ────────────────────────────────────────────────────────────────
# private


async def _evm_make_token_holding(
    chain: ChainName, token: AlchemyTokenBalanceItem
) -> WalletHolding:
    metadata = await alchemy_get_token_metadata(chain, token.contract_address)

    ui_amount = token.token_balance * (10**-metadata.decimals if metadata.decimals else 1)

    return {
        "contract": to_checksum_address(token.contract_address),
        "symbol": make_coin(metadata.symbol) if metadata.symbol else "MISSING_COIN",
        "amount": WeiAmount(token.token_balance),
        "decimals": metadata.decimals if metadata.decimals else WEI_DECIMALS_18,
        "uiAmount": cast("Quantity", ui_amount),
        "info": metadata.model_dump(),
    }


BASE_ASSET_BY_CHAIN = {
    ChainName.ETH: make_coin("ETH"),
    ChainName.SOL: make_coin("SOL"),
    ChainName.BSC: make_coin("BNB"),
    ChainName.BASE: make_coin("ETH"),
    ChainName.HYPE: make_coin("HYPE"),
    ChainName.ARB: make_coin("ETH"),
}


async def _evm_make_base_holding(chain: ChainName, address: EthAddressAsStr) -> WalletHolding:
    bal = await rpc_eth_get_balance(chain, address)
    return {
        "contract": ZERO_ADDRESS_ETH,
        "symbol": BASE_ASSET_BY_CHAIN[chain],
        "amount": bal,
        "decimals": WEI_DECIMALS_18,
        "uiAmount": cast("Quantity", bal / 10**18),
        "info": {},
    }
