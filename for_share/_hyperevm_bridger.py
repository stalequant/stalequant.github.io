import asyncio

from web3 import Web3

from ._erc20 import erc20_allowance
from ._erc20 import erc20_authorize
from ._erc20 import erc20_holdings
from ._onchain_tools import extend_dict_and_send
from ._onchain_tools import get_rpc_async
from ._types import ChainName
from ._types import EthAddressAsStr
from ._types import info

base_coin = "USDC"

FROM_ADDR: EthAddressAsStr = NotImplemented
FROM_CHAIN = ChainName.ARB

DEST_ADDR: EthAddressAsStr = NotImplemented

CHAIN_IDS = {"ETH": 1, ChainName.ARB: 30110, "HYPEREVM": 30367, "HYPERCORE": 999}

CONTRACT_ARB_DETAILS = {
    "USDC": {
        "address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "decimals": 6,
    },
    "USDT": {
        "address": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "decimals": 6,
        "bridge_contract_address": "0x14E4A1B13bf7F943c8ff7C51fb60FA964A298D92",
        "transfer_router_addr": "0xcb768e263fb1c62214e7cab4aa8d036d76dc59cc",
    },
    "USDE": {
        "address": "0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34",
        "decimals": 18,
        "bridge_contract_address": "0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34",
    },
}

OFT_ABI = [
    {
        "stateMutability": "view",
        "type": "function",
        "name": "quoteOFT",
        "inputs": [
            {
                "name": "params",
                "type": "tuple",
                "components": [
                    {"name": "dstEid", "type": "uint32"},
                    {"name": "to", "type": "bytes32"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "minAmount", "type": "uint256"},
                    {"name": "zroPayParam", "type": "bytes"},
                    {"name": "adapterParam", "type": "bytes"},
                    {"name": "composeMsg", "type": "bytes"},
                ],
            }
        ],
        "outputs": [
            {
                "name": "result",
                "type": "tuple",
                "components": [
                    {"name": "nativeFee", "type": "uint256"},
                    {"name": "lzFee", "type": "uint256"},
                ],
            },
            {
                "name": "path",
                "type": "tuple[]",
                "components": [
                    {"name": "amount", "type": "int256"},
                    {"name": "message", "type": "string"},
                ],
            },
            {
                "name": "receipt",
                "type": "tuple",
                "components": [
                    {"name": "minAmount", "type": "uint256"},
                    {"name": "dust", "type": "uint256"},
                ],
            },
        ],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "quoteSend",
        "inputs": [
            {
                "name": "params",
                "type": "tuple",
                "components": [
                    {"name": "dstEid", "type": "uint32"},
                    {"name": "to", "type": "bytes32"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "minAmount", "type": "uint256"},
                    {"name": "zroPayParam", "type": "bytes"},
                    {"name": "adapterParam", "type": "bytes"},
                    {"name": "composeMsg", "type": "bytes"},
                ],
            },
            {"name": "useZro", "type": "bool"},
        ],
        "outputs": [
            {
                "name": "fees",
                "type": "tuple",
                "components": [
                    {"name": "nativeFee", "type": "uint256"},
                    {"name": "zroFee", "type": "uint256"},
                ],
            }
        ],
    },
    {
        "stateMutability": "payable",
        "type": "function",
        "name": "send",
        "inputs": [
            {
                "name": "params",
                "type": "tuple",
                "components": [
                    {"name": "dstEid", "type": "uint32"},
                    {"name": "to", "type": "bytes32"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "minAmount", "type": "uint256"},
                    {"name": "zroPayParam", "type": "bytes"},
                    {"name": "adapterParam", "type": "bytes"},
                    {"name": "composeMsg", "type": "bytes"},
                ],
            },
            {
                "name": "fees",
                "type": "tuple",
                "components": [
                    {"name": "nativeFee", "type": "uint256"},
                    {"name": "zroFee", "type": "uint256"},
                ],
            },
            {"name": "refundAddress", "type": "address"},
        ],
        "outputs": [
            {
                "name": "lzTxInfo",
                "type": "tuple",
                "components": [
                    {"name": "guid", "type": "bytes32"},
                    {"name": "nonce", "type": "uint64"},
                    {
                        "name": "receipt",
                        "type": "tuple",
                        "components": [
                            {"name": "minAmount", "type": "uint256"},
                            {"name": "dust", "type": "uint256"},
                        ],
                    },
                ],
            },
            {
                "name": "fees",
                "type": "tuple",
                "components": [
                    {"name": "nativeFee", "type": "uint256"},
                    {"name": "zroFee", "type": "uint256"},
                ],
            },
        ],
    },
]


async def bridge_to_hyperevm(target: ChainName, bridge_coin: str, quantity_dollars: float) -> None:
    info("C1 Fetching bridge coin on hand", f"{bridge_coin}")
    coin_arb_addr = CONTRACT_ARB_DETAILS[bridge_coin]["address"]
    bridge_coin_on_hand = await erc20_holdings(ChainName.ARB, coin_arb_addr, FROM_ADDR)

    bridge_coin_wei = int(quantity_dollars * 10 ** CONTRACT_ARB_DETAILS[bridge_coin]["decimals"])
    bridge_coin_wei = int(quantity_dollars * 10 ** CONTRACT_ARB_DETAILS[bridge_coin]["decimals"])

    if bridge_coin_wei > bridge_coin_on_hand:
        info("C2 Too little bridge coin", f"{bridge_coin}")
        return

    if bridge_coin == "USDE":
        info("C9 Send bridge request manually", f"{bridge_coin}")

    current_bridge_coin_allowance = await erc20_allowance(
        chain_name=FROM_CHAIN,
        token_addr=CONTRACT_ARB_DETAILS[bridge_coin]["address"],
        owner_addr=FROM_ADDR,
        spender_addr=CONTRACT_ARB_DETAILS[bridge_coin]["bridge_contract_address"],
    )

    if current_bridge_coin_allowance < bridge_coin_wei:  # USDE = 18 dec
        info(
            "CA Current allowance for bridge too low",
            f"{current_bridge_coin_allowance} < {bridge_coin_wei} for {bridge_coin}",
        )
        await erc20_authorize(
            chain_name=FROM_CHAIN,
            token_addr=CONTRACT_ARB_DETAILS[bridge_coin]["address"],
            owner_addr=FROM_ADDR,
            spender_addr=CONTRACT_ARB_DETAILS[bridge_coin]["bridge_contract_address"],
        )
        await asyncio.sleep(6)
    else:
        info(f"D2B> Enough {bridge_coin} allowance")

    padded_to_addr = Web3.to_bytes(hexstr=DEST_ADDR).rjust(32, b"\x00")
    send_param = [CHAIN_IDS[target], padded_to_addr, bridge_coin_wei, 0, b"", b"", b""]

    if bridge_coin == "USDT":
        send_param[4] = bytes.fromhex("0003")

        if target == "HYPERCORE":
            send_param[1] = Web3.to_bytes(
                hexstr=CONTRACT_ARB_DETAILS[bridge_coin]["transfer_router_addr"]
            ).rjust(32, b"\x00")
            send_param[5] = padded_to_addr

    if "bridge_contract" not in CONTRACT_ARB_DETAILS[bridge_coin]:
        CONTRACT_ARB_DETAILS[bridge_coin]["bridge_contract"] = get_rpc_async(
            FROM_CHAIN, True
        ).eth.contract(
            address=CONTRACT_ARB_DETAILS[bridge_coin]["bridge_contract_address"],
            abi=OFT_ABI,
        )
    oft = CONTRACT_ARB_DETAILS[bridge_coin]["bridge_contract"]

    _, _, oft_receipt = oft.functions.quoteOFT(tuple(send_param)).call()
    send_param[3] = oft_receipt[1]

    native_fee, zro_fee = oft.functions.quoteSend(
        tuple(send_param),
        False,  # pay in native, not ZRO
    ).call()  # returns (nativeFee, zroFee)

    info("DA Got bridge quote", f"{bridge_coin} {quantity_dollars}")

    tx_hash = await extend_dict_and_send(
        FROM_CHAIN,
        FROM_ADDR,
        oft.functions.send(
            tuple(send_param),  # first param
            (native_fee, zro_fee),  # second param (fee tuple)
            DEST_ADDR,  # third param (string address)
        ).build_transaction(
            {"from": FROM_ADDR, "value": native_fee}  # pay the LayerZero fee
        ),
    )

    info("D8 Sent bridge request", tx_hash)
