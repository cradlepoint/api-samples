# Cradlepoint NCM SDK
This is a Python client library for Cradlepoint NCM API (both v2 and v3)

INSTALL AND RUN INSTRUCTIONS

1. Install the ncm pip package, or copy the ncm.py file into your working directory:
    ```
    pip3 install ncm
    ```

2. Set NCM API v2 Keys. API Keys must be passed as a dictionary:
    ```
    api_keys = {
        'X-CP-API-ID': 'aaaa',
        'X-CP-API-KEY': 'bbbb',
        'X-ECM-API-ID': 'cccc',
        'X-ECM-API-KEY': 'dddd'
    }
    ```
    For API v3 Key it can be included in the same dictionary as token (optional):
    ```
    api_keys = {
        'X-CP-API-ID': 'aaaa',
        'X-CP-API-KEY': 'bbbb',
        'X-ECM-API-ID': 'cccc',
        'X-ECM-API-KEY': 'dddd',
        "token": 'eeee'
    }
    ```
    Note: if only using v3, just include the token in the dictionary.

3. Import the module and create an instance of the NcmClient object:
   
   If using pip:
    ```
    from ncm import ncm
    n = ncm.NcmClient(api_keys=api_keys)
    ```
   
   If not using pip:
    ```
    import ncm
    n = ncm.NcmClient(api_keys=api_keys)
    ```

4. Call functions from the module as needed. For example:
    ```
    print(n.get_accounts())
    ```
   
USAGE AND TIPS:

This python class includes a few optimizations to make it easier to work with the API.
The default record limit is set at 500 instead of the Cradlepoint default of 20, 
which reduces the number of API calls required to return large sets of data. 

This can be modified by specifying a "limit parameter":
   ```
   n.get_accounts(limit=10)
   ```
You can also return the full list of records in a single array without the need for paging
by passing limit='all':
   ```
   n.get_accounts(limit='all')
   ```
It also has native support for handling any number of "__in" filters beyond Cradlepoint's limit of 100.
The script automatically chunks the list into groups of 100 and combines the results into a single array.
