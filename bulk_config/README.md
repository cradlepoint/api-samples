# bulk_config.py

bulk configure devices in NCM from .csv file

 1. Create routers.csv with router IDs listed in column A and other
     device-specific values in subsequent columns (B, C, D, etc)
 2. Use NCM Config Editor to build a config template, then click
     "View Pending Changes" and copy the config
 3. Paste your config below in the build_config() function and replace
     config values with corresponding csv column letters
 4. Enter API Keys and run script

     Example config for a csv file with hostname in column B:

        [{
             "system": {
                 "system_id": column["B"]
            }
        },
            []
        ]