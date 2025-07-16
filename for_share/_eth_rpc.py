"""Pydantic helpers for evm rpcs."""

from __future__ import annotations

__all__ = ["rpc_eth_get_balance"]

from typing import TYPE_CHECKING
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_validator

from . import _onchain_tools
from ._types import WeiAmount

if TYPE_CHECKING:
    from ._types import ChainName
    from ._types import EthAddressAsStr


class RpcGetBalanceReturn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wei: WeiAmount  # caller sees a WeiAmount, not HexWei or str

    # accept either a 0x-prefixed hex string or an int
    @field_validator("wei", mode="before")
    @classmethod
    def parse_hex(cls, v: str | int) -> WeiAmount:
        if isinstance(v, str):
            try:
                v = int(v, 16)
            except ValueError as exc:
                msg = "Value must be a 0x-prefixed hex string"
                raise ValueError(msg) from exc
        return WeiAmount(v)


async def rpc_eth_get_balance(chain: ChainName, address: EthAddressAsStr) -> WeiAmount:
    """Return the base balance of the wallet."""
    raw_bal = await _onchain_tools.fetch_onchain(
        chain=chain, method="eth_getBalance", params=[address, "latest"]
    )
    return cast("WeiAmount", RpcGetBalanceReturn.model_validate({"wei": raw_bal}).wei)
