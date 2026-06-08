import os
import json
import ccxt
import sys

# Global state
# It's generally better to avoid global variables if possible, or at least
# initialize them with default values. For this script, they are used to
# store the active exchange and API credentials, which are set during initialization.
# Initializing with `None` can help in debugging and makes it clearer that
# they are not set until `initialize_exchange` is called.
exchange = None
api_key = None
secret = None
password = None

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
        # Improved checking for common HTTP error codes and messages
        if "451" in msg or "restricted location" in msg.lower():
            print("Error: API access is blocked from your region for this exchange.")
            print("  Consider another exchange like kraken, coinbasepro, kucoin, or bitstamp.")
        elif "401" in msg or "unauthorized" in msg.lower():
            print("Error: Unauthorized. Check API credentials and permissions.")
        elif "403" in msg or "forbidden" in msg.lower():
            print("Error: Access forbidden — check IP whitelist or API restrictions.")
        else:
            # Fallback for any other unexpected errors
            print(f"An unexpected error occurred: {e}")

def _get_preconfigured_config():
    """Returns preconfigured global state values.
    This function retrieves environment variables. It's good practice to
    handle potential `KeyError` if these variables are not set, although
    the `main` function already attempts to check for their existence.
    """
    try:
        exchange_name_env = os.environ["DEF_EXCH"].strip().lower()
        api_key_env = os.environ["DEF_API"].strip()
        secret_env = os.environ["DEF_SEC"].strip()
        password_env = os.environ.get("DEF_PASS", "").strip() # Use .get for optional password
        return exchange_name_env, api_key_env, secret_env, password_env
    except KeyError as e:
        print(f"Configuration error: Environment variable {e} is not set.")
        return None, None, None, None

def initialize_exchange(exchange_name, key, sec, pwd=None):
    """Initializes the CCXT exchange object with provided credentials.

    Args:
        exchange_name (str): The name of the exchange (e.g., 'binance').
        key (str): The API key.
        sec (str): The API secret.
        pwd (str, optional): The API password or passphrase. Defaults to None.

    Returns:
        bool: True if initialization was successful, False otherwise.
    """
    global exchange, api_key, secret, password # Declare intent to modify globals

    if exchange_name not in ccxt.exchanges:
        print(f"Error: Exchange '{exchange_name}' is not supported by CCXT.")
        return False

    exchange_class = getattr(ccxt, exchange_name)
    params = {
        "apiKey": key,
        "secret": sec,
        "enableRateLimit": True,  # Essential for staying within API limits
        "timeout": 15000,         # Increased timeout for potentially slower APIs
        "verbose": False,         # Set to True for debugging CCXT requests
    }
    if pwd:
        # CCXT uses 'password' for exchanges that require a passphrase
        params["password"] = pwd

    try:
        # Instantiate the exchange
        ex = exchange_class(params)
        # Load markets early. This also validates connectivity and the exchange name.
        # It's a good check before committing to using the exchange object.
        ex.load_markets()

        # Update global state only if initialization and market loading are successful
        exchange = ex
        api_key = key
        secret = sec
        password = pwd or "" # Ensure password is an empty string if not provided
        print(f"Exchange: {exchange_name} | API keys set and markets loaded.")
        return True
    except Exception as e:
        # Use the dedicated error handler for CCXT-specific issues
        handle_ccxt_error(e)
        print("Exchange initialization failed.")
        return False

def require_auth():
    """Checks if authentication details are available and the exchange object is initialized."""
    if exchange is None or not api_key or not secret:
        print("Error: Authentication details are not configured or the exchange is not initialized.")
        print("Please run option 1 to set up your exchange and API keys.")
        return False
    return True

def _mask(s):
    """Masks a string for display, showing only the first and last few characters."""
    if not s:
        return ""
    if len(s) <= 8:
        return "*" * len(s) # Mask the entire string if it's short
    return f"{s[:4]}...{s[-4:]}" # Show first 4 and last 4 characters

# --- Command handlers ---

def cmd_setup():
    """Handles the setup of exchange and API keys.
    This version prompts the user for input and uses environment variables as defaults.
    """
    print("\n--- Setup Exchange & API Keys ---")
    print("You can enter your exchange details or press Enter to use pre-configured environment variables.")

    name_default, key_default, sec_default, pwd_default = _get_preconfigured_config()

    # Prompt for exchange name
    exchange_name_input = input(f"Exchange name [{name_default if name_default else 'e.g., binance'}]: ").strip().lower()
    exchange_name = exchange_name_input if exchange_name_input else name_default
    if not exchange_name:
        print("Error: Exchange name is required.")
        return

    # Prompt for API key
    api_key_input = input(f"API Key [{_mask(key_default) if key_default else 'your_api_key'}]: ").strip()
    api_key_val = api_key_input if api_key_input else key_default
    if not api_key_val:
        print("Error: API key is required.")
        return

    # Prompt for secret key
    secret_key_input = input(f"Secret Key [{_mask(sec_default) if sec_default else 'your_secret_key'}]: ").strip()
    secret_key_val = secret_key_input if secret_key_input else sec_default
    if not secret_key_val:
        print("Error: Secret key is required.")
        return

    # Prompt for password/passphrase (optional)
    password_input = input(f"Password/Passphrase (optional) [{_mask(pwd_default) if pwd_default else 'optional'}]: ").strip()
    password_val = password_input if password_input else pwd_default

    # Attempt to initialize the exchange with the gathered credentials
    initialize_exchange(exchange_name, api_key_val, secret_key_val, password_val or None)

def _ensure_markets_loaded():
    """Ensures that exchange markets are loaded, handling potential errors.
    This is a critical step before performing most operations that require
    knowledge of trading pairs and their properties.
    """
    try:
        # Check if the exchange object exists and has markets loaded.
        # If `exchange` is None or `exchange.markets` is empty, attempt to load.
        if exchange and hasattr(exchange, 'markets') and exchange.markets:
            return True
        if exchange:
            # If already initialized but markets are not loaded (e.g., after an error), try loading them.
            print("Markets not loaded, attempting to load now...")
            exchange.load_markets()
            print("Markets loaded successfully.")
            return True
        # If exchange is None, it means initialization failed or wasn't attempted.
        return False
    except Exception as e:
        handle_ccxt_error(e)
        print("Failed to load exchange markets. Please check your connection and API credentials.")
        return False

def cmd_fetch_balance():
    """Fetches and displays the account balance."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return
    try:
        print("Fetching account balance...")
        balance = exchange.fetch_balance()
        print_result(balance)
    except Exception as e:
        handle_ccxt_error(e)

def _validate_symbol(symbol):
    """Performs basic symbol validation against loaded markets.
    This prevents users from attempting operations on invalid trading pairs.
    """
    if not symbol:
        print("Error: Symbol cannot be empty.")
        return False
    try:
        # The `market` method will raise an exception if the symbol is not found.
        exchange.market(symbol)
        return True
    except Exception:
        print(f"Error: Symbol '{symbol}' is unknown or unsupported on this exchange.")
        return False

def cmd_create_limit_buy():
    """Creates a limit buy order."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return

    symbol = input("Enter symbol (e.g. BTC/USDT): ").strip().upper()
    if not _validate_symbol(symbol):
        return

    try:
        amount_str = input("Enter amount to buy: ").strip()
        price_str = input("Enter price per unit: ").strip()

        # Input validation for numerical values
        amount = float(amount_str)
        price = float(price_str)

        if amount <= 0 or price <= 0:
            print("Error: Amount and price must be positive values.")
            return

        print(f"Creating limit buy order for {amount} {symbol.split('/')[0]} at {price} {symbol.split('/')[1]}...")
        order = exchange.create_limit_buy_order(symbol, amount, price)
        print_result(order)
        print("Limit buy order created successfully.")
    except ValueError:
        print("Error: Invalid input. Please enter numeric values for amount and price.")
    except Exception as e:
        handle_ccxt_error(e)

def cmd_create_limit_sell():
    """Creates a limit sell order."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return

    symbol = input("Enter symbol (e.g. BTC/USDT): ").strip().upper()
    if not _validate_symbol(symbol):
        return

    try:
        amount_str = input("Enter amount to sell: ").strip()
        price_str = input("Enter price per unit: ").strip()

        # Input validation for numerical values
        amount = float(amount_str)
        price = float(price_str)

        if amount <= 0 or price <= 0:
            print("Error: Amount and price must be positive values.")
            return

        print(f"Creating limit sell order for {amount} {symbol.split('/')[0]} at {price} {symbol.split('/')[1]}...")
        order = exchange.create_limit_sell_order(symbol, amount, price)
        print_result(order)
        print("Limit sell order created successfully.")
    except ValueError:
        print("Error: Invalid input. Please enter numeric values for amount and price.")
    except Exception as e:
        handle_ccxt_error(e)

def cmd_cancel_order():
    """Cancels an existing order."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return

    order_id = input("Enter order ID to cancel: ").strip()
    symbol = input("Enter symbol for the order (e.g. BTC/USDT): ").strip().upper()

    if not order_id or not symbol:
        print("Error: Order ID and symbol are required.")
        return
    if not _validate_symbol(symbol):
        return

    try:
        print(f"Cancelling order ID {order_id} for symbol {symbol}...")
        result = exchange.cancel_order(order_id, symbol)
        print_result(result)
        print("Order cancellation request submitted.")
    except Exception as e:
        handle_ccxt_error(e)

def cmd_fetch_open_orders():
    """Fetches and displays all open orders."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return

    symbol = input("Enter symbol (leave blank for all symbols): ").strip().upper()

    try:
        print("Fetching open orders...")
        if symbol:
            if not _validate_symbol(symbol):
                return
            open_orders = exchange.fetch_open_orders(symbol)
        else:
            open_orders = exchange.fetch_open_orders()
        print_result(open_orders)
        if not open_orders:
            print("No open orders found.")
    except Exception as e:
        handle_ccxt_error(e)

def cmd_fetch_order():
    """Fetches and displays details of a single order."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return

    order_id = input("Enter order ID to fetch: ").strip()
    symbol = input("Enter symbol for the order (e.g. BTC/USDT): ").strip().upper()

    if not order_id or not symbol:
        print("Error: Order ID and symbol are required.")
        return
    if not _validate_symbol(symbol):
        return

    try:
        print(f"Fetching details for order ID {order_id} on {symbol}...")
        order_details = exchange.fetch_order(order_id, symbol)
        print_result(order_details)
    except Exception as e:
        handle_ccxt_error(e)

def cmd_fetch_closed_orders():
    """Fetches and displays all closed orders."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return

    symbol = input("Enter symbol (leave blank for all symbols): ").strip().upper()
    # Fetching a limited number of closed orders to avoid overwhelming the user/API
    limit = 20

    try:
        print(f"Fetching last {limit} closed orders...")
        if symbol:
            if not _validate_symbol(symbol):
                return
            closed_orders = exchange.fetch_closed_orders(symbol, limit=limit)
        else:
            closed_orders = exchange.fetch_closed_orders(limit=limit)
        print_result(closed_orders)
        if not closed_orders:
            print("No closed orders found.")
    except Exception as e:
        handle_ccxt_error(e)

def cmd_get_deposit_address():
    """Fetches and displays the deposit address for a given asset and network."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return

    asset = input("Enter asset to get deposit address for (e.g. BTC): ").strip().upper()
    if not asset:
        print("Error: Asset is required.")
        return

    # Network is often optional but crucial for some assets/exchanges
    network = input("Enter network (optional, e.g. ERC20, TRC20, BEP20): ").strip().upper()

    params = {}
    if network:
        # CCXT uses a flexible 'params' dictionary for exchange-specific arguments.
        # Common keys for network include 'network', 'chain', 'assetNetwork'.
        # We'll try a couple of common ones, but specific exchanges might differ.
        params["network"] = network
        params["chain"] = network # Some exchanges use 'chain'
        # It's good practice to document that specific exchanges might require different keys.

    try:
        print(f"Fetching deposit address for {asset} on network {network if network else 'default'}...")
        deposit_address = exchange.fetch_deposit_address(asset, params)
        print_result(deposit_address)
    except Exception as e:
        handle_ccxt_error(e)

def cmd_deposit_history():
    """Fetches and displays deposit history."""
    if not require_auth():
        return

    asset = input("Enter asset to filter deposits by (leave blank for all): ").strip().upper()
    limit = 20 # Limit results to avoid overwhelming output

    try:
        print(f"Fetching last {limit} deposit history entries...")
        if asset:
            deposits = exchange.fetch_deposits(asset, limit=limit)
        else:
            deposits = exchange.fetch_deposits(None, limit=limit) # None fetches all assets
        print_result(deposits)
        if not deposits:
            print("No deposit history found.")
    except Exception as e:
        handle_ccxt_error(e)

def cmd_withdrawal_history():
    """Fetches and displays withdrawal history."""
    if not require_auth():
        return

    asset = input("Enter asset to filter withdrawals by (leave blank for all): ").strip().upper()
    limit = 20 # Limit results

    try:
        print(f"Fetching last {limit} withdrawal history entries...")
        if asset:
            withdrawals = exchange.fetch_withdrawals(asset, limit=limit)
        else:
            withdrawals = exchange.fetch_withdrawals(None, limit=limit)
        print_result(withdrawals)
        if not withdrawals:
            print("No withdrawal history found.")
    except Exception as e:
        handle_ccxt_error(e)

def cmd_withdraw():
    """Initiates a withdrawal of funds."""
    if not require_auth():
        return
    if not _ensure_markets_loaded():
        return

    asset = input("Enter asset to withdraw (e.g. BTC): ").strip().upper()
    if not asset:
        print("Error: Asset is required.")
        return

    try:
        amount_str = input("Enter amount to withdraw: ").strip()
        amount = float(amount_str)
        if amount <= 0:
            print("Error: Amount must be a positive value.")
            return
    except ValueError:
        print("Error: Invalid input. Please enter a numeric value for amount.")
        return

    address = input("Enter destination address: ").strip()
    if not address:
        print("Error: Destination address is required.")
        return

    tag = input("Enter Tag/Memo (optional, press Enter to skip): ").strip()
    network = input("Enter Network (optional, e.g. ERC20, TRC20, BEP20): ").strip().upper()

    # Confirmation step is crucial for withdrawals
    confirmation_message = f"Confirm withdrawal of {amount} {asset} to address {address}"
    if tag:
        confirmation_message += f" (tag: {tag})"
    if network:
        confirmation_message += f" on network {network}"
    confirmation_message += "? (yes/no): "

    confirm = input(confirmation_message).strip().lower()
    if confirm != "yes":
        print("Withdrawal cancelled.")
        return

    params = {}
    if network:
        params["network"] = network
        params["chain"] = network # Common keys for network

    try:
        print(f"Initiating withdrawal of {amount} {asset}...")
        withdrawal_result = exchange.withdraw(asset, amount, address, tag or None, params)
        print_result(withdrawal_result)
        print("Withdrawal request submitted successfully.")
    except Exception as e:
        handle_ccxt_error(e)

# --- Menu ---

MENU_ITEMS = [
    ("1.  Setup exchange + API keys", cmd_setup),
    ("", None), # Spacer
    ("--- Account ---", None),
    ("2.  Fetch balance", cmd_fetch_balance),
    ("", None), # Spacer
    ("--- Orders ---", None),
    ("3.  Create limit buy order", cmd_create_limit_buy),
    ("4.  Create limit sell order", cmd_create_limit_sell),
    ("5.  Cancel order", cmd_cancel_order),
    ("6.  Fetch open orders", cmd_fetch_open_orders),
    ("7.  Fetch closed orders", cmd_fetch_closed_orders),
    ("8.  Fetch single order", cmd_fetch_order),
    ("", None), # Spacer
    ("--- Deposits & Withdrawals ---", None),
    ("9.  Get deposit address", cmd_get_deposit_address),
    ("10. Deposit history", cmd_deposit_history),
    ("11. Withdrawal history", cmd_withdrawal_history),
    ("12. Withdraw funds", cmd_withdraw),
    ("", None), # Spacer
    ("0.  Exit", None),
]

# Mapping of user input choices to corresponding command functions
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
    # Dynamically display exchange status
    if exchange and api_key:
        try:
            exchange_id = exchange.id if exchange else "N/A"
            print(f"  Exchange: {exchange_id}  |  Keys: set")
        except Exception: # Handle cases where exchange object might be partially initialized or invalid
            print("  Exchange: (Error loading status)")
    else:
        print("  Exchange: (not configured)")
    print("=" * 48)
    for label, _ in MENU_ITEMS:
        print(f"  {label}" if label else "") # Print empty lines as spacers

def main():
    """Main function to run the CCXT terminal application."""
    print("Welcome to the CCXT Private API Terminal!")

    # Attempt to initialize with pre-configured values from environment variables
    name_default, key_default, sec_default, pwd_default = _get_preconfigured_config()

    if name_default and key_default and sec_default:
        print("Attempting to load pre-configured exchange and API keys from environment variables...")
        if initialize_exchange(name_default, key_default, sec_default, pwd_default or None):
            print("Pre-configured exchange and API keys loaded successfully.\n")
        else:
            print("Failed to load pre-configured exchange and API keys. Please run option 1 to manually configure.\n")
    else:
        print("No pre-configured API keys found in environment variables (DEF_EXCH, DEF_API, DEF_SEC).")
        print("Please run option 1 to set up your exchange and API keys.\n")

    # Main application loop
    while True:
        print_menu()
        try:
            choice = input("Enter option: ").strip()
        except (EOFError, KeyboardInterrupt): # Graceful exit on Ctrl+D or Ctrl+C
            print("\nExiting terminal. Goodbye!")
            sys.exit(0)

        if choice == "0":
            print("Exiting terminal. Goodbye!")
            sys.exit(0)
        elif choice in COMMANDS:
            print() # Add a blank line before executing command output
            COMMANDS[choice]() # Execute the corresponding command function
        else:
            print("Invalid option. Please enter a number from the menu.")

if __name__ == "__main__":
    main()