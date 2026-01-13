# This script unlicenses devices by MAC address using the NCM library (pip install -U ncm)
# It reads a CSV file with device details and unlicenses the devices in NCM
# The CSV file should have "mac_address" in the first row of the first column, with MAC addresses below it

import csv
from ncm import ncm

token = "Put Your NCM APIv3 Token Here"

csv_filename = "routers.csv"

# Initialize the NCM client
ncm_client = ncm.NcmClientv3(api_key=token, log_events=True)

# Read all MAC addresses from CSV file
with open(csv_filename, 'r') as file:
    csv_reader = csv.DictReader(file)
    mac_addresses = [row['mac_address'].lower().strip().replace(':', '') for row in csv_reader]

print(f"Found {len(mac_addresses)} devices to unlicense")

# Unlicense all devices in bulk
if mac_addresses:
    result = ncm_client.unlicense_devices(mac_addresses)
    print(f"Bulk unlicense result: {result}")
else:
    print("No MAC addresses found in CSV file")
