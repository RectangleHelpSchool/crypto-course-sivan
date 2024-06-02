import typing

import matplotlib.pyplot as plt
import pandas as pd
import pydantic
from eth_abi.codec import ABICodec
from web3 import Web3
from web3._utils.events import get_event_data
from web3.middleware import geth_poa_middleware

# Define constants and connection parameters
BASE_URL = "https://eth-mainnet.g.alchemy.com/v2/XKCDK5nIGQZC4ADASNvLy_gqTOfcsDH2"
CONTRACT_ADDRESS = '0x4b92d19c11435614CD49Af1b589001b7c08cD4D5'
START_BLOCK = 13129988  # 2021-08-31
END_BLOCK = 14084738  # 2022-01-27

# Set up Web3 provider
provider = Web3.HTTPProvider(BASE_URL)
w3 = Web3(provider)

# Add support for POA (Proof of Authority)
w3.middleware_onion.inject(geth_poa_middleware, layer=0)


class ABIParam(pydantic.BaseModel):
    indexed: bool
    name: str
    type: str


class EventABI(pydantic.BaseModel):
    inputs: typing.List[ABIParam]
    name: str
    type: str = 'event'
    anonymous: bool = False

    @property
    def signature(self) -> str:
        params = ",".join(param.type for param in self.inputs)
        return f"{self.name}({params})"

    @property
    def signature_hex(self) -> str:
        return Web3.keccak(text=self.signature).hex()


def get_event_filter(event_abi: EventABI):
    """
    Create a filter for the specified event type.

    :param event_abi: EventABI object representing the event.
    :return: Filter object for the specified event.
    """
    return w3.eth.filter({
        'address': CONTRACT_ADDRESS,
        'topics': [event_abi.signature_hex],
        'fromBlock': START_BLOCK,
        'toBlock': END_BLOCK
    })


def parse_event(event, abi: EventABI) -> typing.Dict:
    """
    Parse an event log entry.

    :param event: Event log entry from the blockchain.
    :param abi: EventABI object representing the event.
    :return: Dictionary containing the parsed event data.
    """
    codec: ABICodec = w3.codec
    event_data = get_event_data(codec, abi.dict(), event)
    return {
        'transaction': event['transactionHash'].hex(),
        'block_number': event['blockNumber'],
        **event_data['args']
    }


def collect_events(event_abi: EventABI) -> typing.List[typing.Dict]:
    """
    Collect all events of the specified type within the block range.

    :param event_abi: EventABI object representing the event.
    :return: List of dictionaries containing the parsed event data.
    """
    event_filter = get_event_filter(event_abi)
    raw_events = event_filter.get_all_entries()
    return [parse_event(event, event_abi) for event in raw_events]


def main():
    """
    Main function to collect event data, create a summary table, and plot the results.
    """
    ERC20_APPROVAL_ABI = EventABI.parse_obj({
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "spender", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Approval",
        "type": "event"
    })

    # Collect data
    events = collect_events(ERC20_APPROVAL_ABI)

    # Create DataFrame
    df = pd.DataFrame(events)

    # Create summary table by spender and block
    summary_table = df.pivot_table(index='block_number', columns='spender', values='transaction', aggfunc='count')

    # Create line plot
    block_range_summary = summary_table.groupby(pd.cut(summary_table.index, range(START_BLOCK, END_BLOCK, 10000))).sum()
    block_range_summary.plot(kind='line')

    # Show plot
    plt.show()


if __name__ == '__main__':
    main()
