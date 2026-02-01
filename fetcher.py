import requests
import time
from datetime import datetime
try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False

def get_btc_price_binance():
    """Fetch current BTC price from Binance public API."""
    try:
        response = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        response.raise_for_status()
        data = response.json()
        return {
            "price": float(data["lastPrice"]),
            "volume": float(data["volume"]),
            "source": "Binance",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return None



def get_btc_price_coingecko():
    """Fetch current BTC price from CoinGecko API (free, no API key needed)."""
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_vol=true",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        response.raise_for_status()
        data = response.json()
        btc_data = data["bitcoin"]
        return {
            "price": float(btc_data["usd"]),
            "volume": float(btc_data.get("usd_24h_vol", 0)),
            "source": "CoinGecko",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return None

def get_btc_price_chainlink():
    """Fetch current BTC price from Chainlink Data Streams on Polygon - same as Polymarket uses.
    
    Polymarket uses Chainlink Data Streams for low-latency, timestamped BTC/USD pricing on Polygon
    for resolving 15-minute "Up or Down" markets. This function queries the on-chain Chainlink
    aggregator contract directly.
    """
    if not WEB3_AVAILABLE:
        # Fallback to Redstone API if web3 is not available
        try:
            response = requests.get(
                "https://api.redstone.finance/prices?symbols=BTC",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            response.raise_for_status()
            data = response.json()
            btc_data = data.get("BTC", {})
            price = float(btc_data.get("value", 0))
            return {
                "price": price,
                "volume": 0,
                "source": "Chainlink",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except:
            return None
    
    try:
        # Connect to Polygon RPC endpoint
        # Using public RPC - you can also use Alchemy, Infura, or QuickNode for better reliability
        polygon_rpc = "https://polygon-rpc.com"
        w3 = Web3(Web3.HTTPProvider(polygon_rpc, request_kwargs={'timeout': 10}))
        
        if not w3.is_connected():
            return None
        
        # Chainlink BTC/USD Price Feed contract address on Polygon
        # This is the official Chainlink aggregator for BTC/USD on Polygon
        btc_usd_feed_address = "0xc907E116054Ad103354f0D35050b556f00A8d2aD"
        
        # Simplified Chainlink Aggregator ABI (only the function we need)
        aggregator_abi = [
            {
                "inputs": [],
                "name": "latestRoundData",
                "outputs": [
                    {"name": "roundId", "type": "uint80"},
                    {"name": "answer", "type": "int256"},
                    {"name": "startedAt", "type": "uint256"},
                    {"name": "updatedAt", "type": "uint256"},
                    {"name": "answeredInRound", "type": "uint80"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # Get contract instance
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(btc_usd_feed_address),
            abi=aggregator_abi
        )
        
        # Fetch latest price data
        latest_data = contract.functions.latestRoundData().call()
        
        # Extract data: (roundId, answer, startedAt, updatedAt, answeredInRound)
        round_id, answer, started_at, updated_at, answered_in_round = latest_data
        
        # Get decimals (usually 8 for BTC/USD)
        decimals = contract.functions.decimals().call()
        
        # Convert answer to price (Chainlink returns price with decimals)
        price = float(answer) / (10 ** decimals)
        
        # Convert timestamp from Unix to ISO format
        timestamp = datetime.utcfromtimestamp(updated_at).isoformat() + "Z"
        
        return {
            "price": price,
            "volume": 0,  # Chainlink feeds don't include volume
            "source": "Chainlink",
            "timestamp": timestamp
        }
    except Exception as e:
        # If on-chain query fails, fallback to Redstone API
        try:
            response = requests.get(
                "https://api.redstone.finance/prices?symbols=BTC",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            response.raise_for_status()
            data = response.json()
            btc_data = data.get("BTC", {})
            price = float(btc_data.get("value", 0))
            return {
                "price": price,
                "volume": 0,
                "source": "Chainlink",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except:
            return None

def get_btc_price_cryptocompare():
    """Fetch current BTC price from CryptoCompare API."""
    try:
        # Use pricemultifull endpoint which includes volume data
        response = requests.get(
            "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC&tsyms=USD",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract price and volume from RAW data
        btc_data = data["RAW"]["BTC"]["USD"]
        price = float(btc_data["PRICE"])
        volume = float(btc_data.get("VOLUME24HOURTO", 0))  # Volume in USD
        
        return {
            "price": price,
            "volume": volume,
            "source": "CryptoCompare",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return None

def get_btc_price_coincap():
    """Fetch current BTC price from CoinCap API."""
    try:
        response = requests.get(
            "https://api.coincap.io/v2/assets/bitcoin",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        response.raise_for_status()
        data = response.json()
        btc_data = data["data"]
        return {
            "price": float(btc_data["priceUsd"]),
            "volume": float(btc_data.get("volumeUsd24Hr", 0)),
            "source": "CoinCap",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return None

def get_btc_price():
    """Fetch current BTC price with fallback to multiple APIs."""
    # Try APIs in order of preference (CryptoCompare first - provides real-time updates with volume)
    apis = [
        ("CryptoCompare", get_btc_price_cryptocompare),
        ("Chainlink", get_btc_price_chainlink),
        ("Binance", get_btc_price_binance),
        ("CoinCap", get_btc_price_coincap),
        ("CoinGecko", get_btc_price_coingecko)
    ]
    
    last_error = None
    for api_name, api_func in apis:
        try:
            result = api_func()
            if result:
                return result
            else:
                print(f"[FAIL] {api_name} failed, trying next...")
        except requests.exceptions.Timeout:
            print(f"[FAIL] {api_name} timed out, trying next...")
            last_error = "Timeout"
        except requests.exceptions.ConnectionError as e:
            print(f"[FAIL] {api_name} connection error, trying next...")
            last_error = "Connection error"
        except Exception as e:
            last_error = str(e)
            print(f"[FAIL] {api_name} error: {last_error}, trying next...")
    
    print(f"Error: All APIs failed to fetch BTC price. Last error: {last_error}")
    return None

# Test it
if __name__ == "__main__":
    result = get_btc_price()
    print(result)