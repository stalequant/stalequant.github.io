"""Tools to interact with ERC20 coins."""

from __future__ import annotations

__all__ = [
    "erc20_allowance",
    "erc20_authorize",
    "erc20_holdings",
    "erc20_send",
]

from typing import TYPE_CHECKING
from typing import cast

from . import _onchain_tools
from ._types import WEI_AMOUNT_MAX
from ._types import ChainName
from ._types import EthAddressAsStr
from ._types import WeiAmount

if TYPE_CHECKING:
    from eth_typing import ChecksumAddress
    from web3.contract import AsyncContract
    from web3.types import TxReceipt

from ._types import info


# ────────────────────────────────────────────────────────────────
# public
async def erc20_authorize(
    chain_name: ChainName,
    token_addr: EthAddressAsStr,
    owner_addr: EthAddressAsStr,
    spender_addr: EthAddressAsStr | EthAddressAsStr,
    amount: WeiAmount = WEI_AMOUNT_MAX,
) -> TxReceipt:
    """Authorize a contract for an amount of wei."""
    tx = await _onchain_tools.build_and_send(
        chain_name,
        owner_addr,
        _get_erc20_contract(chain_name, token_addr).functions.approve(spender_addr, int(amount)),
    )

    info(
        f"75 Authorized {chain_name} "
        f"{owner_addr[:6]}-> {spender_addr[:6]} "
        f"for {amount} {token_addr[:6]}"
    )

    return tx


async def erc20_send(
    chain_name: ChainName,
    sender_address: EthAddressAsStr,
    receiver_address: EthAddressAsStr,
    contract_address: EthAddressAsStr,
    amount: WeiAmount,
) -> TxReceipt:
    """Send an amount of ERC20 tokens."""
    tx = await _onchain_tools.build_and_send(
        chain_name,
        sender_address,
        _get_erc20_contract(chain_name, contract_address).functions.transfer(
            receiver_address, int(amount)
        ),
    )

    info(
        f"72 Transfer {chain_name} "
        f"{sender_address[:6]}-> {receiver_address[:6]} "
        f"for {amount} {contract_address[:6]}"
    )

    return tx


async def erc20_holdings(
    chain_name: ChainName,
    contract_address: EthAddressAsStr,
    addr: EthAddressAsStr,
) -> WeiAmount:
    """Get the balance of an address for an ERC20 contract."""
    return cast(
        "WeiAmount",
        int(
            (
                await _onchain_tools.get_rpc_async(chain_name, allow_native=True).eth.call(
                    await _get_erc20_contract(chain_name, contract_address)
                    .functions.balanceOf(addr)
                    .build_transaction(),
                    block_identifier="latest",
                )
            ).hex(),
            16,
        ),
    )


async def erc20_allowance(
    chain_name: ChainName,
    token_addr: EthAddressAsStr,
    owner_addr: EthAddressAsStr,
    spender_addr: EthAddressAsStr | EthAddressAsStr,
) -> WeiAmount:
    """Get the allowance of an address for an ERC20 contract."""
    return cast(
        "WeiAmount",
        await _get_erc20_contract(chain_name, token_addr)
        .functions.allowance(owner_addr, spender_addr)
        .call(),
    )


# ────────────────────────────────────────────────────────────────
# private


def _get_erc20_contract(chain_name: ChainName, contract_address: EthAddressAsStr) -> AsyncContract:
    loc = chain_name, contract_address
    if loc not in _all_erc20_contracts:
        _all_erc20_contracts[loc] = _onchain_tools.get_rpc_async(
            chain_name, allow_native=True
        ).eth.contract(address=cast("ChecksumAddress", contract_address), abi=_ERC20_ABI)
    return _all_erc20_contracts[loc]


_all_erc20_contracts: dict[tuple[ChainName, EthAddressAsStr], AsyncContract] = {}

_ERC20_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "remaining", "type": "uint256"}],
        "type": "function",
    },
]
