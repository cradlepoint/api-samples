#!/usr/bin/env python3
"""
Create and manage users in NCM API v3 from a CSV file with user details and roles.

This script reads a CSV file containing user information (first name, last name, email,
and role) and automatically creates new users in NCM or updates existing users. It first
creates the user account, then assigns the specified role. Supports all NCM user roles
including administrator, full access, read-only, and no access.

CSV Format:
    Required columns (case-insensitive):
        - first name: User's first name
        - last name: User's last name
        - email: User's email address
        - role: User role (must be one of: no_access, read_only_user, full_access_user, administrator)
    
    Example CSV:
        first name,last name,email,role
        John,Doe,john.doe@example.com,full_access_user
        Jane,Smith,jane.smith@example.com,administrator

Usage:
    python ncm_v3_create_users.py <csv_file_path>

Requirements:
    - NCM API v3 token set as TOKEN or NCM_API_TOKEN environment variable
      (Can be set in the API Keys tab of the CSV Script Manager)
    - CSV file with required columns in the first row
"""

import csv
import os
import sys
from ncm import ncm

# Get CSV filename from command-line argument
if len(sys.argv) < 2:
    print("Error: CSV filename required as command-line argument")
    print(f"Usage: {sys.argv[0]} <csv_file_path>")
    sys.exit(1)

csv_filename = sys.argv[1]

# Get token from environment variable
token = os.environ.get('TOKEN') or os.environ.get('NCM_API_TOKEN')

if not token:
    print("Error: Please set your NCM API v3 token as TOKEN environment variable")
    print("You can set it in the API Keys tab of the CSV Script Manager")
    sys.exit(1)

# Initialize the NCM client
ncm_client = ncm.NcmClientv3(api_key=token, log_events=True)

def create_and_update_user(first_name, last_name, email, role):
    try:
        # Create the user first
        response = ncm_client.create_user(first_name=first_name, last_name=last_name, email=email)
        if response.startswith('ERROR'):
            print(f"Error creating user {email} - does it already exist? {response}")
        else:
            print(f"User {email} created successfully")

        # Then update their role
        response = ncm_client.update_user_role(email, role)
        if response.startswith('ERROR'):
            print(f"Error updating user {email} - {response}")
        else:
            print(f"User {email} updated role to {role} successfully")
    except Exception as e:
        print(f"Error processing {email}: {str(e)}")

# Check if CSV file exists
if not os.path.exists(csv_filename):
    print(f"Error: CSV file not found: {csv_filename}")
    sys.exit(1)

# Read and process CSV file
print(f"Processing CSV file: {csv_filename}")
try:
    with open(csv_filename, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        # Check for required columns
        required_columns = ['first name', 'last name', 'email', 'role']
        csv_columns = [col.lower().strip() for col in csv_reader.fieldnames] if csv_reader.fieldnames else []
        
        missing_columns = []
        for req_col in required_columns:
            if req_col.lower() not in csv_columns:
                missing_columns.append(req_col)
        
        if missing_columns:
            print(f"Error: Missing required columns: {', '.join(missing_columns)}")
            print(f"Found columns: {', '.join(csv_reader.fieldnames)}")
            sys.exit(1)
        
        # Find the actual column names (case-insensitive)
        column_map = {}
        for req_col in required_columns:
            for csv_col in csv_reader.fieldnames:
                if csv_col.lower().strip() == req_col.lower():
                    column_map[req_col] = csv_col
                    break
        
        row_count = 0
        for row in csv_reader:
            row_count += 1
            create_and_update_user(
                first_name=row[column_map['first name']].strip(),
                last_name=row[column_map['last name']].strip(),
                email=row[column_map['email']].strip(),
                role=row[column_map['role']].strip()
            )
        
        print(f"\nProcessed {row_count} user(s) from CSV file")
        
except FileNotFoundError:
    print(f"Error: CSV file not found: {csv_filename}")
    sys.exit(1)
except KeyError as e:
    print(f"Error: Column '{e}' not found in CSV file")
    sys.exit(1)
except Exception as e:
    print(f"Error reading CSV file: {e}")
    sys.exit(1)
