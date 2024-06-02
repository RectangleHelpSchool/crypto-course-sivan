import argparse
import json
from web3 import Web3
from pathlib import Path

NODE_URL = "https://eth-mainnet.g.alchemy.com/v2/XKCDK5nIGQZC4ADASNvLy_gqTOfcsDH2"

# Calculate the Approval event signature hash
event_signature = "Approval(address,address,uint256)"
APPROVAL_EVENT_SIGNATURE = Web3.keccak(text=event_signature).hex()
print(f"Approval event signature hash: {APPROVAL_EVENT_SIGNATURE}")

# Load the ABI from a JSON file
ABI_PATH = Path(__file__).parent / 'erc20_abi.json'
with open(ABI_PATH) as f:
    TOKEN_ABI = json.load(f)


def get_approval_logs(w3, address, from_block='earliest', to_block='latest'):
    """
    Get all approval logs for the specified address.

    :param w3: Web3 instance
    :param address: Ethereum address to query
    :param from_block: The starting block to query from
    :param to_block: The ending block to query to
    """
    padded_address = '0x' + address[2:].zfill(64)
    print(f"Querying logs for padded address: {padded_address}")
    print(f"From block: {from_block}, To block: {to_block}")

    try:
        logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': to_block,
            'topics': [APPROVAL_EVENT_SIGNATURE, padded_address]
        })
        print(f"Found {len(logs)} logs")
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return

    if len(logs) == 0:
        print("No logs found. Try a different address or block range.")
        return

    addresses = set([log['address'] for log in logs])
    names = {addr: get_token_name(w3, addr) for addr in addresses}

    for log in logs:
        display_log(log, names)


def get_token_name(w3, address):
    """
    Get the token name from the contract at the specified address.

    :param w3: Web3 instance
    :param address: Contract address
    :return: The token name
    """
    print(f"Fetching token name for address: {address}")
    contract = w3.eth.contract(address=w3.to_checksum_address(address), abi=TOKEN_ABI)
    try:
        name = contract.functions.name().call()
        decimals = contract.functions.decimals().call()
    except Exception as e:
        print(f"Error fetching token name: {e}")
        name = "Unknown Token"
        decimals = 18  # Use a default value if fetching fails
    return name, decimals


def display_log(log, names):
    """
    Display a single approval log.

    :param log: Log entry
    :param names: Dictionary mapping addresses to token names and decimals
    """
    name, decimals = names[log['address']]
    amount = int.from_bytes(log['data'], byteorder='big') / (10 ** decimals)
    print(f"Approval on {name} for amount of {amount}")


def main():
    parser = argparse.ArgumentParser(description="Retrieve all ERC-20 approval events for a given address.")
    parser.add_argument('--address', required=True, help="The address to retrieve approval logs for.")
    parser.add_argument('--from_block', default='earliest', help="The starting block to query from.")
    parser.add_argument('--to_block', default='latest', help="The ending block to query to.")
    args = parser.parse_args()

    w3 = Web3(Web3.HTTPProvider(NODE_URL))
    if not w3.is_connected():
        raise Exception(f"Cannot connect to the node at {NODE_URL}")

    print(f"Connected to Ethereum node: {w3.is_connected()}")
    print(f"Retrieving approval logs for address: {args.address}")

    get_approval_logs(w3, args.address, from_block=args.from_block, to_block=args.to_block)

if __name__ == '__main__':
    main()
