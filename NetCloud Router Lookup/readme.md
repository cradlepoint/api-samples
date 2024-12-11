# NetCloud Router Lookup

## Web App for Looking Up Routers Across Multiple Accounts

This Flask web application allows users to input a MAC address or serial number of a router and looks it up across multiple NetCloud accounts. The application then returns the account name that the router belongs to.

### Features

- Input MAC address or serial number of a router
- Lookup across multiple NetCloud accounts
- Return the account name associated with the router

### Requirements

- Python 3.x
- Flask
- Requests

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/cradlepoint/api-samples/tree/master/NetCloud%20Router%20Lookup
    cd NetCloud\ Router\ Lookup
    ```

2. Create a virtual environment and activate it:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1. Update the `named_keys` section of router_lookup.py with your NetCloud Accounts' APIv2 Keys.
    ```python
    # Dictionary of named keys
    named_keys = {
        'account1': {
            'X-ECM-API-ID': '1234567890',
            'X-ECM-API-KEY': '0987654321',
            'X-CP-API-ID': '1234567890',
            'X-CP-API-KEY': '0987654321'
        },
        'account2': {
            'X-ECM-API-ID': '1234567890',
            'X-ECM-API-KEY': '0987654321',
            'X-CP-API-ID': '1234567890',
            'X-CP-API-KEY': '0987654321'
        },
        'account3': {
            'X-ECM-API-ID': '1234567890',
            'X-ECM-API-KEY': '0987654321',
            'X-CP-API-ID': '1234567890',
            'X-CP-API-KEY': '0987654321'
        }
    }
    ```

### Usage

1. Run the Flask application:
    ```bash
    flask run
    ```

2. Open your web browser and go to `http://127.0.0.1:8000`.

3. Enter the MAC address or serial number of the router in the input field and click "Lookup".

4. The application will display the account name associated with the router, or an error message if the router is not found.

