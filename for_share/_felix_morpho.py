"""Morpho contract for Felix."""

from __future__ import annotations

__all__ = [
    "get_market_params_by_id",
    "get_marketbalance",
]

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast

from eth_utils.conversions import to_bytes
from eth_utils.conversions import to_hex
from eth_utils.crypto import keccak
from web3 import Web3

from . import _erc20
from . import _onchain_tools
from ._types import WeiAmount
from ._types import info

if TYPE_CHECKING:
    from ._types import ChainName

MY_ADDRESS = NotImplemented


MARKET_PARAMS_STRUCT = [
    {"internalType": "address", "name": "loanToken", "type": "address"},
    {"internalType": "address", "name": "collateralToken", "type": "address"},
    {"internalType": "address", "name": "oracle", "type": "address"},
    {"internalType": "address", "name": "irm", "type": "address"},
    {"internalType": "uint256", "name": "lltv", "type": "uint256"},
]

FELIX_MORPHO_ABI = [
    {
        "inputs": [{"internalType": "Id", "name": "", "type": "bytes32"}],
        "name": "market",
        "outputs": [
            {"internalType": "uint128", "name": "totalSupplyAssets", "type": "uint128"},
            {"internalType": "uint128", "name": "totalSupplyShares", "type": "uint128"},
            {"internalType": "uint128", "name": "totalBorrowAssets", "type": "uint128"},
            {"internalType": "uint128", "name": "totalBorrowShares", "type": "uint128"},
            {"internalType": "uint128", "name": "lastUpdate", "type": "uint128"},
            {"internalType": "uint128", "name": "fee", "type": "uint128"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "name": "idToMarketParams",
        "outputs": MARKET_PARAMS_STRUCT,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": MARKET_PARAMS_STRUCT,
                "internalType": "struct MarketParams",
                "name": "market",
                "type": "tuple",
            },
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "uint256", "name": "maxWithdrawable", "type": "uint256"},
            {"internalType": "address", "name": "onBehalf", "type": "address"},
            {"internalType": "address", "name": "receiver", "type": "address"},
        ],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": MARKET_PARAMS_STRUCT,
                "internalType": "struct MarketParams",
                "name": "market",
                "type": "tuple",
            },
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "uint256", "name": "maxDeposit", "type": "uint256"},
            {"internalType": "address", "name": "onBehalf", "type": "address"},
            {"internalType": "bytes", "name": "permit", "type": "bytes"},
        ],
        "name": "supply",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "Id", "name": "", "type": "bytes32"},
            {"internalType": "address", "name": "", "type": "address"},
        ],
        "name": "position",
        "outputs": [
            {"internalType": "uint256", "name": "supplyShares", "type": "uint256"},
            {"internalType": "uint128", "name": "borrowShares", "type": "uint128"},
            {"internalType": "uint128", "name": "collateral", "type": "uint128"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

FELIX_MORPHO_ADDR = Web3.to_checksum_address(
    "0x68e37de8d93d3496ae143f2e900490f6280c57cd"
)  # Ethereum mainnet
CHAIN_NAME: ChainName = ChainName.HYPE
HYPEREVM_TOKENS = {
    "USDE": {
        "address": "0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34",
        "decimals": 18,
    },
    "WHYPE": {
        "address": "0x5555555555555555555555555555555555555555",
        "decimals": 18,
    },
    "USDT0": {
        "address": "0xB8CE59FC3717ada4C02eaDF9682A9e934F625ebb",
        "decimals": 6,
    },
    "FEUSD": {
        "address": "0x02c6a2fA58cC01A18B8D9E00eA48d65E4dF26c70",
        "decimals": 18,
    },
    "UETH": {
        "address": "0xBe6727B535545C67d5cAa73dEa54865B92CF7907",
        "decimals": 24,
    },
    "WSTHYPE": {
        "address": "0x94e8396e0869c9F2200760aF0621aFd240E1CF38",
        "decimals": 18,
    },
    "UBTC": {
        "address": "0x9FDBdA0A5e284c32744D2f17Ee5c74B284993463",
        "decimals": 24,
    },
}

address_to_coin = {v["address"].lower(): k for k, v in HYPEREVM_TOKENS.items()}

morpho_contract = _onchain_tools.get_contract(
    chain_name=CHAIN_NAME, address=FELIX_MORPHO_ADDR, abi=FELIX_MORPHO_ABI
)


def _contract_functions(chain_name, function):
    return getattr(morpho_contract.functions, function)


async def _do_helper(
    chain_name,
    addr,
    fn,
    arguments,
):
    return await _onchain_tools.build_and_send(
        chain_name=CHAIN_NAME,
        addr=addr,
        transaction=_contract_functions(chain_name, fn)(**arguments),
    )


async def get_market_params_by_id(chain_name, market_id):
    # tuple: (loanToken, collateralToken, oracle, irm, lltv)
    return await morpho_contract.functions.idToMarketParams(market_id).call()


async def get_marketbalance(chain_name, market_id, address):
    # tuple: (loanToken, collateralToken, oracle, irm, lltv)
    return await morpho_contract.functions.position(market_id, address).call()


async def add_supply(chain_name, addr, market_params, amount):
    return await _do_helper(
        chain_name,
        addr,
        "supply",
        dict(market=market_params, amount=int(amount), maxDeposit=0, onBehalf=addr, permit=b""),
    )


async def remove_supply(chain_name, addr, market_params, amount):
    return await _do_helper(
        chain_name,
        addr,
        "withdraw",
        dict(
            market=market_params,
            amount=int(amount),
            maxWithdrawable=0,
            onBehalf=addr,
            receiver=addr,
        ),
    )


# %%
# pip install web3 eth-utils


def pad32(value) -> bytes:
    """Left-pad an address / hex-string / int to 32-byte length."""
    if isinstance(value, int):
        return value.to_bytes(32, "big")
    if isinstance(value, (bytes, bytearray)):
        data = bytes(value)
    else:  # assume 0x-prefixed str
        data = to_bytes(hexstr=value)
    if len(data) > 32:
        raise ValueError("value longer than 32 bytes")
    return data.rjust(32, b"\x00")


@dataclass
class MarketParams:
    loan_token: str
    collateral_token: str
    oracle: str
    irm: str
    lltv: int  # solidity uint256


def compute_market_params_id(p: MarketParams) -> str:
    blob = (
        pad32(p.loan_token)
        + pad32(p.collateral_token)
        + pad32(p.oracle)
        + pad32(p.irm)
        + pad32(p.lltv)
    )
    return to_hex(keccak(blob))


# %%

MAIN_MARKETS_FELIX_MORPHO = {
    ("UBTC", "USDE"): {
        "id": "0x5fe3ac84f3a2c4e3102c3e6e9accb1ec90c30f6ee87ab1fcafc197b8addeb94c",
        "params": (
            Web3.to_checksum_address(
                "0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34"
            ),  # loanToken (USDe)
            Web3.to_checksum_address(
                "0x9FDBdA0A5e284c32744D2f17Ee5c74B284993463"
            ),  # collateralToken
            Web3.to_checksum_address("0x6254E080263CeD51A82d6471CD49996765F84bB8"),  # oracle
            Web3.to_checksum_address("0xD4a426F010986dCad727e8dd6eed44cA4A9b7483"),  # IRM
            770_000_000_000_000_000,
        ),
    },
    ("HYPE", "USDE"): {
        "id": "0x292f0a3ddfb642fbaadf258ebcccf9e4b0048a9dc5af93036288502bde1a71b1",
        "params": (
            Web3.to_checksum_address(
                "0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34"
            ),  # loanToken (USDe)
            Web3.to_checksum_address(
                "0x5555555555555555555555555555555555555555"
            ),  # collateralToken
            Web3.to_checksum_address("0x754d069bAccB22F80eD46e5B4AFeC08C3b891A69"),  # oracle
            Web3.to_checksum_address("0xD4A426F010986dCaD727E8DD6eed44cA4A9B7483"),  # IRM
            625_000_000_000_000_000,
        ),
    },
    ("HYPE", "USDT0"): {
        "id": "0xace279b5c6eff0a1ce7287249369fa6f4d3d32225e1629b04ef308e0eb568fb0",
        "params": (
            Web3.to_checksum_address(
                "0xb8ce59fc3717ada4c02eadf9682a9e934f625ebb"
            ),  # loanToken (USDe)
            Web3.to_checksum_address(
                "0x5555555555555555555555555555555555555555"
            ),  # collateralToken
            Web3.to_checksum_address("0x8f36df5a5a9fc1238d03401b96aa411d6ebca973"),  # oracle
            Web3.to_checksum_address("0xD4A426F010986dCaD727E8DD6eed44cA4A9B7483"),  # IRM
            625_000_000_000_000_000,
        ),
    },
}
OTHER_MARKETS = {
    "market_id": "0xa24d04c3aff60d49b3475f0084334546cbf66182e788b6bf173e6f9990b2c816",
    "lend_coin": "USDT0",
    "lend_coin_address": "b8ce59fc3717ada4c02eadf9682a9e934f625ebb",
    "collateral_coin": "UBTC",
    "collateral_coin_address": "9fdbda0a5e284c32744d2f17ee5c74b284993463",
    "oracle_address": "f4693c969b2c619a9b468cd1078bc51084ead96e",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "860000000000000000",
    "lltv": 0.86,
}
{
    "market_id": "0xa62327642e110efd38ba2d153867a8625c8dc40832e1d211ba4f4151c3de9050",
    "lend_coin": "USDT0",
    "lend_coin_address": "b8ce59fc3717ada4c02eadf9682a9e934f625ebb",
    "collateral_coin": "UETH",
    "collateral_coin_address": "be6727b535545c67d5caa73dea54865b92cf7907",
    "oracle_address": "06dafb8abe56f9fcebfac3b71cf004312261fd95",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "860000000000000000",
    "lltv": 0.86,
}
{
    "market_id": "0xb5b575e402c7c19def8661069c39464c8bf3297b638e64d841b09a4eb2807de5",
    "lend_coin": "USDT0",
    "lend_coin_address": "b8ce59fc3717ada4c02eadf9682a9e934f625ebb",
    "collateral_coin": "HYPE",
    "collateral_coin_address": "5555555555555555555555555555555555555555",
    "oracle_address": "ba7263ed5d7e825b5cd991705f39ecda281b2c58",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "770000000000000000",
    "lltv": 0.77,
}
{
    "market_id": "0x31aaa663d718e83ea15326ec110c4bcf5e123585d0b6c4d0ad61a50c4aa65b1e",
    "lend_coin": "USDT0",
    "lend_coin_address": "b8ce59fc3717ada4c02eadf9682a9e934f625ebb",
    "collateral_coin": "WSTHYPE",
    "collateral_coin_address": "94e8396e0869c9f2200760af0621afd240e1cf38",
    "oracle_address": "3a459d5ec6c576d56d40dd58ae6ba337ed8d6752",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "770000000000000000",
    "lltv": 0.77,
}
{
    "market_id": "0x292f0a3ddfb642fbaadf258ebcccf9e4b0048a9dc5af93036288502bde1a71b1",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "HYPE",
    "collateral_coin_address": "5555555555555555555555555555555555555555",
    "oracle_address": "754d069baccb22f80ed46e5b4afec08c3b891a69",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "625000000000000000",
    "lltv": 0.625,
}
{
    "market_id": "0xb142d65d7c624def0a9f4b49115b83f400a86bd2904d4f3339ec4441e28483ea",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "WSTHYPE",
    "collateral_coin_address": "94e8396e0869c9f2200760af0621afd240e1cf38",
    "oracle_address": "d0a9b8d550f205f47a595c847f2801d315f40da9",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "770000000000000000",
    "lltv": 0.77,
}
{
    "market_id": "0xa7fe39c692f0192fb2f281a6cc16c8b2e1c8f9b9f2bc418e0c0c1e9374bf4b04",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "HYPE",
    "collateral_coin_address": "5555555555555555555555555555555555555555",
    "oracle_address": "b846105d2d0cdbf28c271aa17f6709c4814d2c23",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "770000000000000000",
    "lltv": 0.77,
}
{
    "market_id": "0x964e7d1db11bdf32262c71274c297dcdb4710d73acb814f04fdca8b0c7cdf028",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "UETH",
    "collateral_coin_address": "be6727b535545c67d5caa73dea54865b92cf7907",
    "oracle_address": "e091929500fb992a81c7e850a6f33b999c1f7205",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "860000000000000000",
    "lltv": 0.86,
}
{
    "market_id": "0x5ef35fe4418a6bcfcc70fe32efce30074f22e9a782f81d432c1e537ddbda11e2",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "UBTC",
    "collateral_coin_address": "9fdbda0a5e284c32744d2f17ee5c74b284993463",
    "oracle_address": "f38d4a7e167f4e56703235e1ecab185d0fbdc967",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "860000000000000000",
    "lltv": 0.86,
}
{
    "market_id": "0x5ecb7a25d51c870ec57f810c880e3e20743e56d0524575b7b8934a778aaec1af",
    "lend_coin": "UETH",
    "lend_coin_address": "be6727b535545c67d5caa73dea54865b92cf7907",
    "collateral_coin": "UBTC",
    "collateral_coin_address": "9fdbda0a5e284c32744d2f17ee5c74b284993463",
    "oracle_address": "b4e3544ba4b2d92013051efce6fe1a3d10b21bc6",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "860000000000000000",
    "lltv": 0.86,
}
{
    "market_id": "0x81726bee59db4f284158e6d8dbf6722c7a4b24719021f9d992f57482393d2c6c",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "HYPE",
    "collateral_coin_address": "5555555555555555555555555555555555555555",
    "oracle_address": "754d069baccb22f80ed46e5b4afec08c3b891a69",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "770000000000000000",
    "lltv": 0.77,
}
{
    "market_id": "0xbc15a1782163f4be46c23ac61f5da50fed96ad40293f86a5ce0501ce4a246b32",
    "lend_coin": "HYPE",
    "lend_coin_address": "5555555555555555555555555555555555555555",
    "collateral_coin": "WSTHYPE",
    "collateral_coin_address": "94e8396e0869c9f2200760af0621afd240e1cf38",
    "oracle_address": "f92cce636920d3835b135ea1d58bead4e2d62b15",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "915000000000000000",
    "lltv": 0.915,
}
{
    "market_id": "0xaba6ad3c2adbae92e6fa0d9cc76e443705bb1ba0c85ba2d1ee4de9890a6c9cf4",
    "lend_coin": "UETH",
    "lend_coin_address": "be6727b535545c67d5caa73dea54865b92cf7907",
    "collateral_coin": "UBTC",
    "collateral_coin_address": "9fdbda0a5e284c32744d2f17ee5c74b284993463",
    "oracle_address": "b4e3544ba4b2d92013051efce6fe1a3d10b21bc6",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "915000000000000000",
    "lltv": 0.915,
}
{
    "market_id": "0xe41ace68f2de7be8e47185b51ddc23d4a58aac4ce9f8cc5f9384fe26f2104ec8",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "0x211cc4dd073734da055fbf44a2b4667d5e5fe5d2",
    "collateral_coin_address": "211cc4dd073734da055fbf44a2b4667d5e5fe5d2",
    "oracle_address": "8f90bbfe69a0f05682b16c64cae6bfaf55f6dc8d",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "915000000000000000",
    "lltv": 0.915,
}
{
    "market_id": "0xebeabb17bd69d4b8ed6929a821d69478b564f4cc604d0995944c9da8b5cb3f04",
    "lend_coin": "USDT0",
    "lend_coin_address": "b8ce59fc3717ada4c02eadf9682a9e934f625ebb",
    "collateral_coin": "0x211cc4dd073734da055fbf44a2b4667d5e5fe5d2",
    "collateral_coin_address": "211cc4dd073734da055fbf44a2b4667d5e5fe5d2",
    "oracle_address": "0233de0b346bd410334b37f21c0fee50ff1a1ce6",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "915000000000000000",
    "lltv": 0.915,
}
{
    "market_id": "0x707dddc200e95dc984feb185abf1321cabec8486dca5a9a96fb5202184106e54",
    "lend_coin": "USDT0",
    "lend_coin_address": "b8ce59fc3717ada4c02eadf9682a9e934f625ebb",
    "collateral_coin": "UBTC",
    "collateral_coin_address": "9fdbda0a5e284c32744d2f17ee5c74b284993463",
    "oracle_address": "ce5b111739b8b6a10fd7e9dd6a1c7df9b653317f",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "770000000000000000",
    "lltv": 0.77,
}
{
    "market_id": "0x5fe3ac84f3a2c4e3102c3e6e9accb1ec90c30f6ee87ab1fcafc197b8addeb94c",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "UBTC",
    "collateral_coin_address": "9fdbda0a5e284c32744d2f17ee5c74b284993463",
    "oracle_address": "6254e080263ced51a82d6471cd49996765f84bb8",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "770000000000000000",
    "lltv": 0.77,
}
{
    "market_id": "0x81726bee59db4f284158e6d8dbf6722c7a4b24719021f9d992f57482393d2c6c",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "HYPE",
    "collateral_coin_address": "5555555555555555555555555555555555555555",
    "oracle_address": "754d069baccb22f80ed46e5b4afec08c3b891a69",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "770000000000000000",
    "lltv": 0.77,
}
{
    "market_id": "0x292f0a3ddfb642fbaadf258ebcccf9e4b0048a9dc5af93036288502bde1a71b1",
    "lend_coin": "USDE",
    "lend_coin_address": "5d3a1ff2b6bab83b63cd9ad0787074081a52ef34",
    "collateral_coin": "HYPE",
    "collateral_coin_address": "5555555555555555555555555555555555555555",
    "oracle_address": "754d069baccb22f80ed46e5b4afec08c3b891a69",
    "irm_address": "d4a426f010986dcad727e8dd6eed44ca4a9b7483",
    "irm": "default_irm",
    "lltv_wei": "625000000000000000",
    "lltv": 0.625,
}


async def remove_supply_id(collateral, lend, amount_in_usd):
    info("CC Removing felix-morpho supply", f"{collateral} {lend} ${amount_in_usd}")
    return await remove_supply(
        "HYPEREVM",
        MY_ADDRESS,
        market_params=MAIN_MARKETS_FELIX_MORPHO[collateral, lend]["params"],
        amount=int(amount_in_usd * 10 ** HYPEREVM_TOKENS[lend]["decimals"]),
    )


def allowance(collateral, lend):
    return (
        _erc20.erc20_allowance(
            ChainName.HYPE, HYPEREVM_TOKENS[lend]["address"], MY_ADDRESS, FELIX_MORPHO_ADDR
        )
        / 10 ** HYPEREVM_TOKENS[lend]["decimals"]
    )


async def add_supply_id(collateral, lend, amount_in_usd):
    if allowance(collateral, lend) < amount_in_usd:
        info("CD Need more allowance to supply", f"{collateral} {lend} ${amount_in_usd}")

        await authorize_morpho(collateral, lend, 10 * amount_in_usd)
        await asyncio.sleep(4)
    info("CE Adding felix-morpho supply", f"{collateral} {lend} ${amount_in_usd}")

    return await add_supply(
        "HYPEREVM",
        MY_ADDRESS,
        market_params=MAIN_MARKETS_FELIX_MORPHO[collateral, lend]["params"],
        amount=int(amount_in_usd * 10 ** HYPEREVM_TOKENS[lend]["decimals"]),
    )


async def authorize_morpho(collateral, lend, amount_in_usd):
    info("CF Authorizing felix-morpho", f"{collateral} {lend} ${amount_in_usd}")

    return await _erc20.erc20_authorize(
        CHAIN_NAME,
        HYPEREVM_TOKENS[lend]["address"],
        MY_ADDRESS,
        FELIX_MORPHO_ADDR,
        amount=cast("WeiAmount", int(amount_in_usd * 10 ** HYPEREVM_TOKENS[lend]["decimals"])),
    )


async def get_bal_on_market(collateral, lend):
    return (
        (
            await get_marketbalance(
                CHAIN_NAME, MAIN_MARKETS_FELIX_MORPHO[collateral, lend]["id"], MY_ADDRESS
            )
        )[0]
        / 10 ** HYPEREVM_TOKENS[lend]["decimals"]
        // 1e6
    )


morpho_blue_core_abi = []
ADAPTIVE_CURVE_IRM_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "loanToken", "type": "address"},
                    {"internalType": "address", "name": "collateralToken", "type": "address"},
                    {"internalType": "address", "name": "oracle", "type": "address"},
                    {"internalType": "address", "name": "irm", "type": "address"},
                    {"internalType": "uint256", "name": "lltv", "type": "uint256"},
                ],
                "internalType": "struct MarketParams",
                "name": "marketParams",
                "type": "tuple",
            },
            {
                "components": [
                    {"internalType": "uint128", "name": "totalSupplyAssets", "type": "uint128"},
                    {"internalType": "uint128", "name": "totalSupplyShares", "type": "uint128"},
                    {"internalType": "uint128", "name": "totalBorrowAssets", "type": "uint128"},
                    {"internalType": "uint128", "name": "totalBorrowShares", "type": "uint128"},
                    {"internalType": "uint128", "name": "lastUpdate", "type": "uint128"},
                    {"internalType": "uint128", "name": "fee", "type": "uint128"},
                ],
                "internalType": "struct Market",
                "name": "market",
                "type": "tuple",
            },
        ],
        "name": "borrowRateView",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]

lend = "USDT0"
collat = "HYPE"

adaptive_curve_irm = _onchain_tools.get_contract(
    chain_name=CHAIN_NAME,
    address=Web3.to_checksum_address("0xD4A426F010986dCaD727E8DD6eed44cA4A9B7483"),
    abi=ADAPTIVE_CURVE_IRM_ABI,
)


def get_market_data(collat, lend):
    return morpho_contract.functions.market(MAIN_MARKETS_FELIX_MORPHO[collat, lend]["id"]).call()


async def get_irm_apr(collat, lend):
    market_data = get_market_data(collat, lend)
    params = MAIN_MARKETS_FELIX_MORPHO[collat, lend]["params"]
    borrow_rate = await adaptive_curve_irm.functions.borrowRateView(params, market_data).call()
    return borrow_rate * 60 * 60 * 24 * 365 / 1e18
