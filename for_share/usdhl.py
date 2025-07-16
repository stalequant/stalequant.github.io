"""Transfer $M from Ethereum to HyperEVM via USDHL."""

from typing import cast

from . import _erc20
from . import _onchain_tools
from ._onchain_tools import to_checksum_address
from ._types import ChainName
from ._types import EthAddressAsStr
from ._types import WeiAmount
from ._types import info

MY_ADDRESS = NotImplemented
PRIVATE_KEY = NotImplemented

DEST_CHAIN_ID = 999  # HyperEVM chain ID

PORTAL_LITE: EthAddressAsStr = to_checksum_address("0x36f586A30502AE3afb555b8aA4dCc05d233c2ecE")
WM_TOKEN: EthAddressAsStr = to_checksum_address("0x437cc33344a0B27A429f795ff6B469C72698B291")
USDHL_DEST: EthAddressAsStr = to_checksum_address("0xb50A96253aBDF803D85efcDce07Ad8becBc52BD5")

DECIMALS = 10**6  # 6-decimals $M

PORTAL_ABI = [
    {
        "name": "quoteTransfer",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "amount", "type": "uint256"},
            {"name": "destinationChainId", "type": "uint256"},
            {"name": "recipient", "type": "address"},
        ],
        "outputs": [{"name": "fee", "type": "uint256"}],
    },
    {
        "name": "transferMLikeToken",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {"name": "amount", "type": "uint256"},
            {"name": "sourceToken", "type": "address"},
            {"name": "destinationChainId", "type": "uint256"},
            {"name": "destinationToken", "type": "address"},
            {"name": "recipient", "type": "address"},
            {"name": "refundAddress", "type": "address"},
        ],
        "outputs": [],
    },
]


async def transfer_eth_m_by_m0_to_hyperevm_usdhl(
    sender_address: EthAddressAsStr, receiver_address: EthAddressAsStr, amount: int
):
    portal_contract = _onchain_tools.get_contract(
        chain_name=ChainName.ETH, address=PORTAL_LITE, abi=PORTAL_ABI
    )

    allowance = await _erc20.erc20_allowance(
        chain_name=ChainName.ETH,
        token_addr=WM_TOKEN,
        owner_addr=sender_address,
        spender_addr=PORTAL_LITE,
    )
    if allowance < amount:
        await _erc20.erc20_authorize(
            ChainName.ETH,
            token_addr=WM_TOKEN,
            owner_addr=MY_ADDRESS,
            spender_addr=PORTAL_LITE,
            amount=cast("WeiAmount", amount * 2.1),
        )

    fee = await portal_contract.functions.quoteTransfer(
        amount, DEST_CHAIN_ID, sender_address
    ).call()
    info(f"Delivery fee (wei): {fee:,}")

    await _onchain_tools.build_and_send(
        ChainName.ETH,
        sender_address,
        portal_contract.functions.transferMLikeToken(
            amount, WM_TOKEN, DEST_CHAIN_ID, USDHL_DEST, receiver_address, sender_address
        ),
        value=fee,
    )
