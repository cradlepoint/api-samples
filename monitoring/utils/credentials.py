"""
This file stores API credentials used by the samples. The samples call
get_credentials() to retrieve them.

IN REAL LIFE:
You may not want to store your keys in plaintext in a source code file.
You can just replace get_credentials() with code to securely retrieve your
keys from wherever you keep them.
"""

my_creds = {
    "cp_api_id": "MY_CP_API_ID",  # replace me
    "cp_api_key": "MY_CP_API_KEY",  # replace me
    "ecm_api_id": "MY_ECM_API_ID",  # replace me
    "ecm_api_key": "MY_ECM_API_KEY",  # replace me
}


def get_credentials():
    return my_creds
