"""Tools for interacting with ETH."""

from functools import lru_cache
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address as eth_to_checksum_address
from hexbytes import HexBytes
from web3 import AsyncWeb3
from web3 import Web3
from web3.contract import AsyncContract
from web3.contract.async_contract import AsyncContractFunction
from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware
from web3.types import TxParams
from web3.types import TxReceipt
from web3.types import Wei

from ._types import ChainName
from ._types import EthAddressAsStr
from ._types import WeiAmount
from ._types import addr_to_private_key
from ._types import make_coin
from ._types import post_json

PRIVATE_KEY = NotImplemented
ALCHEMY_API_KEY = NotImplemented


def to_checksum_address(in_address: EthAddressAsStr | str, force: bool = False) -> ChecksumAddress:
    """Convert a text address to a checksum address.

    If force is False [default], raises an error if the address is not already a checksum address.
    If force is True, converts the address to a checksum address if needed.
    Use force=True CAREFULLY for contract addresses from apis (e.g., from Dune or Alchemy )
    Use force=False for hardcoded addresses
    """
    trial_checksum = eth_to_checksum_address(in_address)
    if in_address == trial_checksum or force:
        return trial_checksum
    msg = f"Invalid address: {in_address}"
    raise ValueError(msg)


if TYPE_CHECKING:
    from web3.providers import AsyncHTTPProvider

native_rpc_possible = [ChainName.ARB]


CHAIN_DATA = {
    ChainName.ETH: {
        "chain_id": 1,
        "base_asset": make_coin("ETH"),
        "alchemy_rpc": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    },
    ChainName.ARB: {
        "chain_id": 42161,
        "base_asset": make_coin("ETH"),
        "native_rpc": "https://arb1.arbitrum.io/rpc",
        "alchemy_rpc": f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    },
    ChainName.HYPE: {
        "chain_id": 999,
        "alchemy_rpc": "https://rpc.hyperliquid.xyz/evm",
        "native_rpc": "https://rpc.hyperliquid.xyz/evm",
    },
}


def get_chain_id(chain_name: ChainName) -> int:
    return CHAIN_DATA[chain_name]["chain_id"]


def get_contract(
    chain_name: ChainName, address: EthAddressAsStr, abi: list[dict[str, Any]]
) -> AsyncContract:
    return get_rpc_async(chain_name).eth.contract(
        address=Web3.to_checksum_address(address), abi=abi
    )


async def add_gas(tx: TxParams, web3: AsyncWeb3) -> TxParams:
    if "gas" not in tx:
        tx = {"gas": int(1.1 * (await web3.eth.estimate_gas(tx))), **tx}
    if "maxPriorityFeePerGas" not in tx or "maxFeePerGas" not in tx:
        pr = await web3.eth.gas_price
        tx = {"maxPriorityFeePerGas": Wei(int(pr * 1.1)), "maxFeePerGas": Wei(int(pr * 1.2)), **tx}
    return tx


async def build_and_send(
    chain_name: ChainName,
    addr: EthAddressAsStr,
    transaction: AsyncContractFunction,
    value: WeiAmount | None = None,
) -> TxReceipt:
    web3 = get_rpc_async(chain_name)
    tx_params: TxParams
    if value is None:
        tx_params = {
            "from": addr,
            "nonce": await web3.eth.get_transaction_count(to_checksum_address(addr)),
            "chainId": await web3.eth.chain_id,
        }
    else:
        tx_params = {
            "from": addr,
            "nonce": await web3.eth.get_transaction_count(to_checksum_address(addr)),
            "chainId": await web3.eth.chain_id,
            "value": Wei(value),
        }

    return await sign_and_send(web3, addr, await transaction.build_transaction(tx_params))


async def extend_dict_and_send(
    chain_name: ChainName, addr: EthAddressAsStr, transaction_dict: TxParams
) -> TxReceipt:
    web3 = get_rpc_async(chain_name)
    tx_with_gas = await add_gas(
        {
            "from": addr,
            "nonce": await web3.eth.get_transaction_count(to_checksum_address(addr)),
            "chainId": await web3.eth.chain_id,
            **transaction_dict,
        },
        web3,
    )
    return await sign_and_send(web3=web3, addr=addr, tx=tx_with_gas)


async def sign_and_send(web3: AsyncWeb3, addr: EthAddressAsStr, tx: TxParams) -> TxReceipt:
    tx_hash = await web3.eth.send_raw_transaction(
        web3.eth.account.sign_transaction(tx, private_key=addr_to_private_key(addr)).raw_transaction
    )
    return await eth_wait_for_finality_by_rpc(web3, tx_hash)


async def _fetch_alchemy(chain: ChainName, method: str, params: list[Any]) -> dict[str, Any]:
    if chain not in ["ETH", "BSC"] and method.startswith("alchemy_"):
        msg = f"Invalid chain: {chain}"
        raise ValueError(msg)
    endpoint_uri = cast("AsyncHTTPProvider", get_rpc_async(chain).provider).endpoint_uri
    if endpoint_uri is None:
        msg = f"No endpoint URI for {chain}"
        raise ValueError(msg)

    return (
        await post_json(
            url=endpoint_uri,
            headers={"accept": "application/json", "content-type": "application/json"},
            json={
                "jsonrpc": "2.0",  # Specify JSON-RPC version
                "id": 1,  # A unique ID for the request
                "method": method,
                "params": params,
            },
        )
    ).get("result", {})  # type: ignore


async def fetch_onchain(chain: ChainName, method: str, params: list[Any]) -> dict[str, Any]:
    return await _fetch_alchemy(chain, method, params)


@lru_cache
def get_rpc_async(chain_name: ChainName, allow_native: bool = False) -> AsyncWeb3:
    do_native = allow_native and "native_rpc" in CHAIN_DATA[chain_name]
    rpc_url = CHAIN_DATA[chain_name]["native_rpc" if do_native else "alchemy_rpc"]
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
    if chain_name == "BSC":
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


async def eth_wait_for_finality(chain_name: ChainName, tx_hash: HexBytes) -> TxReceipt:
    return await get_rpc_async(chain_name).eth.wait_for_transaction_receipt(tx_hash)


async def eth_wait_for_finality_by_rpc(web3: AsyncWeb3, tx_hash: HexBytes) -> TxReceipt:
    return await web3.eth.wait_for_transaction_receipt(tx_hash)
