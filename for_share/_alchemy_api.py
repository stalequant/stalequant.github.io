"""Alchemy api methods."""

from __future__ import annotations

__all__ = [
    "AlchemyGetTokenBalancesResult",
    "AlchemyTokenBalanceItem",
    "AlchemyTokenMetadataItem",
    "alchemy_get_token_balances",
    "alchemy_get_token_metadata",
]

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from ._onchain_tools import fetch_onchain
from ._onchain_tools import to_checksum_address
from ._types import ZERO_ADDRESS_ETH
from ._types import ChainName
from ._types import DecimalForWeiAmount
from ._types import EthAddressAsStr
from ._types import WeiAmount


# ────────────────────────────────────────────────────────────────
# public
class AlchemyTokenBalanceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contract_address: EthAddressAsStr = Field(..., alias="contractAddress")
    token_balance: WeiAmount = Field(..., alias="tokenBalance")
    error: str | None = None

    # --- field coercions -----------------------------------------------------
    @field_validator("token_balance", mode="before")
    @classmethod
    def parse_hex(cls, v: str | int) -> WeiAmount:
        if isinstance(v, str):
            try:
                v = int(v, 16)
            except ValueError as exc:
                msg = "Value must be a 0x-prefixed hex string"
                raise ValueError(msg) from exc
        return WeiAmount(v)

    @field_validator("contract_address", mode="before")
    @classmethod
    def _parse_contract_address(cls, v: str) -> EthAddressAsStr:
        """Convert 'native' sentinel to zero-address."""
        return ZERO_ADDRESS_ETH if v == "native" else to_checksum_address(v, force=True)


class AlchemyGetTokenBalancesResult(BaseModel):
    """Result from alchemy api for fetching token balances.

    https://www.alchemy.com/docs/data/token-api/token-api-endpoints/alchemy-get-token-balances
    """

    model_config = ConfigDict(extra="ignore")

    address: EthAddressAsStr
    token_balances: list[AlchemyTokenBalanceItem] = Field(..., alias="tokenBalances")

    # --- field coercions -----------------------------------------------------
    @field_validator("address", mode="before")
    @classmethod
    def _parse_native_address(cls, v: str) -> EthAddressAsStr:
        """Convert 'native' sentinel to zero-address."""
        return ZERO_ADDRESS_ETH if v == "native" else to_checksum_address(v, force=True)


async def alchemy_get_token_balances(
    chain: ChainName, address: EthAddressAsStr
) -> AlchemyGetTokenBalancesResult:
    raw = await fetch_onchain(chain=chain, method="alchemy_getTokenBalances", params=[address])

    return AlchemyGetTokenBalancesResult.model_validate(raw)


# Fetch metadata
class AlchemyTokenMetadataItem(BaseModel):
    """Metadata for a token from alchemy api."""

    model_config = ConfigDict(extra="ignore")
    name: str | None = Field(..., alias="name")
    symbol: str | None = Field(..., alias="symbol")
    decimals: DecimalForWeiAmount | None = Field(..., alias="decimals")
    logo: str | None = None


async def alchemy_get_token_metadata(
    chain: ChainName, address: EthAddressAsStr
) -> AlchemyTokenMetadataItem:
    raw = await fetch_onchain(chain=chain, method="alchemy_getTokenMetadata", params=[address])

    return AlchemyTokenMetadataItem.model_validate(raw)
