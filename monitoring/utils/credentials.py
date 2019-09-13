"""
This file stores API credentials used by the samples. The samples call
get_credentials() to retrieve them.

IN REAL LIFE:
You may not want to store your keys in plaintext in a source code file.
You can just replace get_credentials() with code to securely retrieve your
keys from wherever you keep them.
"""

my_creds = {
    'cp_api_id': 'MY_CP_API_ID',  # replace me
    'cp_api_key': 'MY_CP_API_KEY',  # replace me
    'ecm_api_id': 'MY_ECM_API_ID',  # replace me
    'ecm_api_key': 'MY_ECM_API_KEY',  # replace me
}

# TODO
""" prod
my_creds = {
    'cp_api_id': 'd2173a77',
    'cp_api_key': '02a70bf263fbab0dd232b93591e4ec93',
    'ecm_api_id': '8e40601d-2489-4004-9875-b4b875a39516',
    'ecm_api_key': '7ea39fc56a3608b3a75a033572559a00944b4e0f'
}
"""

""" local """
my_creds = {
    'cp_api_id': 'd2173a77',
    'cp_api_key': '02a70bf263fbab0dd232b93591e4ec93',
    'ecm_api_id': 'd9f0445c-14ec-4719-b639-8404f471be88',
    'ecm_api_key': '9921410b53f813df6e71271a3274d06967078b3e'
}
""" """


def get_credentials():
    return my_creds
