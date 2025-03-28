# This script creates and updates users in NCM API v3
# It reads a CSV file with user details and updates the users in NCM
# The CSV file should have the following columns named on row 1:
# first name, last name, email, role
# Install the ncm library using "pip install ncm"

import csv
from ncm import ncm

token = "Put your NCM API v3 token here"

# Initialize the NCM client
ncm = ncm.NcmClientv3(api_key=token)

def create_and_update_user(first_name, last_name, email, role):
    try:
        # Create the user first
        response = ncm.create_user(first_name=first_name, last_name=last_name, email=email)
        if response.startswith('ERROR'):
            print(f"Error creating user {email} - does it already exist? {response}")
        else:
            print(f"User {email} created successfully")

        # Then update their role
        response = ncm.update_user_role(email, role)
        if response.startswith('ERROR'):
            print(f"Error updating user {email} - {response}")
        else:
            print(f"User {email} updated role to {role} successfully")
    except Exception as e:
        print(f"Error processing {email}: {str(e)}")

# Read and process CSV file
with open('users.csv', 'r') as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        create_and_update_user(
            first_name=row['first name'],
            last_name=row['last name'],
            email=row['email'],
            role=row['role']
        )
