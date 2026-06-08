import os
import json
import ccxt
import sys

# Global state
exchange = os.environ["DEF_EXCH"]
api_key = os.environ["DEF_API"]
secret = os.environ["DEF_SEC"]
password = os.environ["DEF_PASS"]

def print_result(data):
    """Prints the result in a formatted JSON string."""
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))

def handle_ccxt_error(e):
    """Detailed, user-friendly error handling based on ccxt exception classes."""
    if isinstance(e, ccxt.AuthenticationError):
        print("Error: Authentication failed. Check API key/secret/password and permissions.")
    elif isinstance(e, ccxt.PermissionDenied):
        print("Error: Permission denied. Check API key restrictions and IP whitelist.")
    elif isinstance(e, ccxt.InvalidAddress):
        print("Error: Invalid address.")
    elif isinstance(e, ccxt.InsufficientFunds):
        print("Error: Insufficient funds.")
    elif isinstance(e, ccxt.BadSymbol):
        print("Error: Invalid or unsupported symbol.")
    elif isinstance(e, ccxt.ExchangeNotAvailable):
        print("Error: Exchange not available. Network or maintenance issue.")
    elif isinstance(e, ccxt.DDoSProtection):
        print("Error: DDoS protection triggered. Please slow down or try again later.")
    elif isinstance(e, ccxt.RateLimitExceeded):
        print("Error: Rate limit exceeded. Reduce request frequency.")
    else:
        msg = str(e)
        if "451" in msg or "restricted location" in msg.lower():
            print("Error: API access is blocked from your region for this exchange.")
            print("  Consider another exchange like kraken, coinbasepro, kucoin, or bitstamp.")
        elif "401" in msg or "unauthorized" in msg.lower():
            print("Error: Unauthorized. Check API credentials and permissions.")
        elif "403" in msg or "forbidden" in msg.lower():
            print("Error: Access forbidden — check IP whitelist or API restrictions.")
        else:
            print(f"Error: {e}")

def _get_preconfigured_config():
    """Returns preconfigured global state values."""
    return (
        DEF_EXCH.strip().lower(),
        DEF_API.strip(),
        DEF_SEC.strip(),
        DEF_PASS.strip(),
    )

def initialize_exchange(exchange_name, key, sec, pwd=None):
    """Initializes the CCXT exchange object with provided credentials."""
    global exchange, api_key, secret, password
    if exchange_name not in ccxt.exchanges:
        print(f"Error: Exchange '{exchange_name}' is not valid.")
        return False

    exchange_class = getattr(ccxt, exchange_name)
    params = {
        "apiKey": key,
        "secret": sec,
        "enableRateLimit": True,
        "timeout": 15000,
        "verbose": False,
    }
    if pwd:
        params["password"] = pwd  # also called 'passphrase' by some exchanges

    try:
        ex = exchange_class(params)
        # Load markets early to validate connectivity and name
        ex.load_markets()
    except Exception as e:
        handle_ccxt_error(e)
        return False

    exchange = ex
    api_key = key
    secret = sec
    password = pwd or ""
    print(f"Exchange: {exchange_name} | API keys set.")
    return True

def require_auth():
    """Checks if authentication details are available."""
    if exchange is None or not api_key or not secret:
        print("Error: Authentication details are not configured.")
        return False
    return True

def _mask(s):
    """Masks a string for display, showing only the first and last few characters."""
    if not s:
        return ""
    if len(s) <= 8:
        return "*" * len(s)
    return f"{s[:4]}...{s[-4:]}"

# --- Command handlers ---

def cmd_setup():
    """Handles the setup of exchange and API keys (demonstrative, uses preconfigured)."""
    print("\n--- Setup Exchange & API Keys ---")
    print("Using pre-configured API keys. To change, modify the script directly.")

    name_default, key_default, sec_default, pwd_default = _get_preconfigured_config()

    print(f"Exchange name: {name_default}")
    print(f"API Key: {_mask(key_default)}")
    print(f"Secret: {_mask(sec_default)}")
    if pwd_default:
        print(f"Password/Passphrase: {_mask(pwd_default)}")

    if not name_default or not key_default or not sec_default:
        print("\nError: Pre-configured exchange, API key, or secret is missing. Please update the script.")
        return

    initialize_exchange(name_default, key_default, sec_default, pwd_default or None)

def _ensure_markets_loaded():
    """Ensures that exchange markets are loaded, handling potential errors."""
    try:
        # No need to load markets if they are already loaded and the exchange object is valid
        if exchange and hasattr(exchange, 'markets') and exchange.markets:
            return True
        if exchange:
            exchange.load_markets()
            return True
        return False
    except Exception as e:
        handle_ccxt_error(e)
        return False

def cmd_fetch_balance():
    """Fetches and displays the account balance."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return
    try:
        print_result(exchange.fetch_balance())
    except Exception as e:
        handle_ccxt_error(e)

def _validate_symbol(symbol):
    """Performs basic symbol validation against loaded markets."""
    try:
        exchange.market(symbol)
        return True
    except Exception:
        print("Error: Unknown or unsupported symbol.")
        return False

def cmd_create_limit_buy():
    """Creates a limit buy order."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return
    symbol = input("Symbol (e.g. BTC/USDT): ").strip().upper()
    if not symbol or not _validate_symbol(symbol):
        return
    try:
        amount = float(input("Amount: "))
        price = float(input("Price: "))
    except ValueError:
        print("Invalid amount or price.")
        return
    if amount <= 0 or price <= 0:
        print("Amount and price must be positive.")
        return
    try:
        print_result(exchange.create_limit_buy_order(symbol, amount, price))
    except Exception as e:
        handle_ccxt_error(e)

def cmd_create_limit_sell():
    """Creates a limit sell order."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return
    symbol = input("Symbol (e.g. BTC/USDT): ").strip().upper()
    if not symbol or not _validate_symbol(symbol):
        return
    try:
        amount = float(input("Amount: "))
        price = float(input("Price: "))
    except ValueError:
        print("Invalid amount or price.")
        return
    if amount <= 0 or price <= 0:
        print("Amount and price must be positive.")
        return
    try:
        print_result(exchange.create_limit_sell_order(symbol, amount, price))
    except Exception as e:
        handle_ccxt_error(e)

def cmd_cancel_order():
    """Cancels an existing order."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return
    order_id = input("Order ID: ").strip()
    symbol = input("Symbol (e.g. BTC/USDT): ").strip().upper()
    if not order_id or not symbol:
        print("Order ID and symbol are required.")
        return
    if not _validate_symbol(symbol):
        return
    try:
        print_result(exchange.cancel_order(order_id, symbol))
    except Exception as e:
        handle_ccxt_error(e)

def cmd_fetch_open_orders():
    """Fetches and displays all open orders."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return
    symbol = input("Symbol (leave blank for all): ").strip().upper()
    try:
        if symbol:
            if not _validate_symbol(symbol):
                return
            print_result(exchange.fetch_open_orders(symbol))
        else:
            print_result(exchange.fetch_open_orders())
    except Exception as e:
        handle_ccxt_error(e)

def cmd_fetch_order():
    """Fetches and displays details of a single order."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return
    order_id = input("Order ID: ").strip()
    symbol = input("Symbol (e.g. BTC/USDT): ").strip().upper()
    if not order_id or not symbol:
        print("Order ID and symbol are required.")
        return
    if not _validate_symbol(symbol):
        return
    try:
        print_result(exchange.fetch_order(order_id, symbol))
    except Exception as e:
        handle_ccxt_error(e)

def cmd_fetch_closed_orders():
    """Fetches and displays all closed orders."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return
    symbol = input("Symbol (leave blank for all): ").strip().upper()
    try:
        if symbol:
            if not _validate_symbol(symbol):
                return
            print_result(exchange.fetch_closed_orders(symbol, limit=20))
        else:
            print_result(exchange.fetch_closed_orders(limit=20))
    except Exception as e:
        handle_ccxt_error(e)

def cmd_get_deposit_address():
    """Fetches and displays the deposit address for a given asset."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return
    asset = input("Asset (e.g. BTC): ").strip().upper()
    network = input("Network (optional, e.g. ERC20, TRC20, BEP20): ").strip().upper()
    if not asset:
        print("Enter an asset.")
        return
    params = {}
    if network:
        # Some exchanges require network parameter under various keys:
        # try common forms
        params["network"] = network
        params["chain"] = network
    try:
        print_result(exchange.fetch_deposit_address(asset, params))
    except Exception as e:
        handle_ccxt_error(e)

def cmd_deposit_history():
    """Fetches and displays deposit history."""
    if not require_auth():
        return
    asset = input("Asset (e.g. BTC, leave blank for all): ").strip().upper()
    try:
        if asset:
            print_result(exchange.fetch_deposits(asset, limit=20))
        else:
            print_result(exchange.fetch_deposits(None, limit=20))
    except Exception as e:
        handle_ccxt_error(e)

def cmd_withdrawal_history():
    """Fetches and displays withdrawal history."""
    if not require_auth():
        return
    asset = input("Asset (e.g. BTC, leave blank for all): ").strip().upper()
    try:
        if asset:
            print_result(exchange.fetch_withdrawals(asset, limit=20))
        else:
            print_result(exchange.fetch_withdrawals(None, limit=20))
    except Exception as e:
        handle_ccxt_error(e)

def cmd_withdraw():
    """Initiates a withdrawal of funds."""
    if not require_auth():
        return
    asset = input("Asset (e.g. BTC): ").strip().upper()
    if not asset:
        print("Asset is required.")
        return
    try:
        amount = float(input("Amount: "))
    except ValueError:
        print("Invalid amount.")
        return
    address = input("Destination address: ").strip()
    tag = input("Tag/Memo (optional): ").strip()
    network = input("Network (optional, e.g. ERC20, TRC20, BEP20): ").strip().upper()
    if amount <= 0 or not address:
        print("Enter valid amount and address.")
        return

    confirm = input(f"Confirm withdraw {amount} {asset} to {address}{(' (tag ' + tag + ')' ) if tag else ''}? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return
    params = {}
    if network:
        params["network"] = network
        params["chain"] = network
    try:
        print_result(exchange.withdraw(asset, amount, address, tag or None, params))
    except Exception as e:
        handle_ccxt_error(e)

# --- Menu ---

MENU_ITEMS = [
    ("1.  Setup exchange + API keys", cmd_setup),
    ("", None),
    ("--- Account ---", None),
    ("2.  Fetch balance", cmd_fetch_balance),
    ("", None),
    ("--- Orders ---", None),
    ("3.  Create limit buy order", cmd_create_limit_buy),
    ("4.  Create limit sell order", cmd_create_limit_sell),
    ("5.  Cancel order", cmd_cancel_order),
    ("6.  Fetch open orders", cmd_fetch_open_orders),
    ("7.  Fetch closed orders", cmd_fetch_closed_orders),
    ("8.  Fetch single order", cmd_fetch_order),
    ("", None),
    ("--- Deposits & Withdrawals ---", None),
    ("9.  Get deposit address", cmd_get_deposit_address),
    ("10. Deposit history", cmd_deposit_history),
    ("11. Withdrawal history", cmd_withdrawal_history),
    ("12. Withdraw funds", cmd_withdraw),
    ("", None),
    ("0.  Exit", None),
]

COMMANDS = {
    "1": cmd_setup,
    "2": cmd_fetch_balance,
    "3": cmd_create_limit_buy,
    "4": cmd_create_limit_sell,
    "5": cmd_cancel_order,
    "6": cmd_fetch_open_orders,
    "7": cmd_fetch_closed_orders,
    "8": cmd_fetch_order,
    "9": cmd_get_deposit_address,
    "10": cmd_deposit_history,
    "11": cmd_withdrawal_history,
    "12": cmd_withdraw,
}

def print_menu():
    """Prints the main menu of the application."""
    print("\n" + "=" * 48)
    print("  CCXT - Private API Terminal")
    if exchange and api_key:
        print(f"  Exchange: {exchange.id}  |  Keys: set")
    else:
        print("  Exchange: (not configured)")
    print("=" * 48)
    for label, _ in MENU_ITEMS:
        print(f"  {label}" if label else "")

def main():
    """Main function to run the CCXT terminal application."""
    print("CCXT Private API Terminal")
    # Attempt to initialize with pre-configured values directly
    name_default, key_default, sec_default, pwd_default = _get_preconfigured_config()
    if name_default and key_default and sec_default:
        if initialize_exchange(name_default, key_default, sec_default, pwd_default or None):
            print("Pre-configured exchange and API keys loaded.\n")
        else:
            print("Failed to load pre-configured exchange and API keys. Run option 1 to manually configure.\n")
    else:
        print("Pre-configured API keys not found. Run option 1 to set your exchange and API keys.\n")

    while True:
        print_menu()
        try:
            choice = input("\nEnter option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            sys.exit(0)
        if choice == "0":
            print("Goodbye.")
            sys.exit(0)
        elif choice in COMMANDS:
            print()
            COMMANDS[choice]()
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()