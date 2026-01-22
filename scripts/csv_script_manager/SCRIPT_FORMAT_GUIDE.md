# Script Format Guide for CSV Script Manager

This guide explains the standardized format for scripts used with the CSV Script Manager and how to format your code and CSV files accordingly.

## Standardized Docstring Format

All scripts in the `scripts/` directory should follow a consistent triple-quoted docstring format at the top of the file. The CSV Script Manager extracts and displays these docstrings in the web interface, making it easy for users to understand what each script does and what CSV format it expects.

### Required Sections

The standardized format includes the following sections:

1. **Brief Description** (1-2 lines)
   - What the script does
   - High-level purpose

2. **Detailed Description** (optional, 1-3 lines)
   - Additional context about how the script works
   - Important behaviors or features

3. **CSV Format** (required)
   - Required columns with descriptions
   - Optional columns with descriptions
   - Example CSV snippet showing the format
   - Column name variations (if case-insensitive or multiple names accepted)

4. **Usage** (required)
   - Command-line usage examples
   - Optional parameters

5. **Requirements** (required)
   - API keys needed (and how to set them)
   - Dependencies
   - Other prerequisites

### Format Template

```python
#!/usr/bin/env python3
"""
Brief description of what the script does.

Optional detailed description explaining how it works or important behaviors.

CSV Format:
    Required columns (case-insensitive if applicable):
        - column_name: Description of what this column contains
        - another_column: Description
    
    Optional columns (used if present):
        - optional_column: Description
    
    Alternative column names accepted:
        - For column_name: "column_name", "Column Name", "column-name"
    
    Example CSV:
        column_name,another_column,optional_column
        value1,value2,value3

Usage:
    python script_name.py <csv_file_path> [optional_args]

Requirements:
    - API keys or tokens (specify how to set them)
    - Dependencies or other prerequisites
"""
```

## How CSV Script Manager Uses Docstrings

The CSV Script Manager:

1. **Extracts docstrings** from scripts using the `extract_docstring()` method
2. **Displays them** in the web interface when listing available scripts
3. **Shows them** to users before running scripts so they understand:
   - What the script does
   - What CSV format is required
   - What API keys are needed

## CSV File Formatting Guidelines

### Column Names

- **Case-insensitive matching**: Most scripts accept column names in any case (e.g., "MAC", "mac", "Mac Address")
- **Multiple name variations**: Scripts often accept multiple column name formats:
  - MAC addresses: "mac", "mac address", "mac_address", "MAC Address"
  - Router IDs: "id", "router id", "router_id", "routerId"
  - Serial numbers: "serial_number", "serial number", "serial"

### Data Formatting

1. **MAC Addresses**: Can be in any format:
   - With colons: `00:30:44:A2:CA:75`
   - With dashes: `00-30-44-A2-CA-75`
   - No separators: `003044A2CA75`
   - Scripts typically normalize these automatically

2. **Router IDs**: Should be integers (as strings in CSV):
   - Valid: `1234567`
   - Scripts will convert to integers

3. **Text Fields**: Can contain any text, but:
   - Use quotes if the field contains commas: `"Value, with comma"`
   - Escape quotes by doubling them: `"Value with ""quotes""`

4. **Empty Values**: 
   - Empty cells are typically handled gracefully
   - Some scripts skip rows with empty required fields

### CSV Best Practices

1. **Header Row**: Always include a header row with column names
2. **Encoding**: Use UTF-8 encoding (most scripts handle this automatically)
3. **Quoting**: Quote fields that contain commas, quotes, or newlines
4. **Consistency**: Use consistent column names across your CSV files

## Code Formatting Guidelines

### Script Structure

1. **Shebang Line**: Include `#!/usr/bin/env python3` at the top (for Unix-like systems)
2. **Docstring**: Use triple-quoted strings (`"""`) for the main docstring
3. **Imports**: Place imports after the docstring
4. **Command-line Arguments**: Scripts receive the CSV file path as `sys.argv[1]`

### Accessing CSV Data

The CSV Script Manager passes the CSV file path as the first command-line argument:

```python
import sys
import csv

# Get CSV file path
if len(sys.argv) < 2:
    print("Error: CSV filename required")
    sys.exit(1)

csv_filename = sys.argv[1]

# Read CSV file
with open(csv_filename, 'r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Access columns by name (case-insensitive matching)
        value = row.get('column_name', '')
```

### Case-Insensitive Column Matching

Many scripts implement case-insensitive column matching:

```python
# Normalize column names for comparison
csv_columns = [col.lower().strip() for col in reader.fieldnames]

# Find column (case-insensitive)
column_map = {}
for req_col in required_columns:
    for csv_col in reader.fieldnames:
        if csv_col.lower().strip() == req_col.lower():
            column_map[req_col] = csv_col
            break

# Use mapped column name
value = row[column_map['required_column']]
```

### API Key Handling

Scripts should support API keys from multiple sources:

1. **Environment Variables** (preferred for CSV Script Manager):
   ```python
   token = os.environ.get('TOKEN') or os.environ.get('NCM_API_TOKEN')
   ```

2. **Script Configuration** (for standalone use):
   ```python
   api_keys = {
       "X-CP-API-ID": "",
       "X-CP-API-KEY": "",
   }
   # Fall back to environment variables
   if not api_keys.get("X-CP-API-ID"):
       api_keys["X-CP-API-ID"] = os.environ.get("X_CP_API_ID", "")
   ```

3. **Command-line Arguments** (optional):
   ```python
   if len(sys.argv) >= 3:
       token = sys.argv[2]
   ```

## Example: Complete Script Template

```python
#!/usr/bin/env python3
"""
Brief description of what the script does.

Optional detailed description explaining how it works.

CSV Format:
    Required columns (case-insensitive):
        - column1: Description
        - column2: Description
    
    Example CSV:
        column1,column2
        value1,value2

Usage:
    python script_name.py <csv_file_path>

Requirements:
    - API keys set as environment variables
    - CSV file with required columns
"""

import sys
import csv
import os

# Get CSV file path
if len(sys.argv) < 2:
    print("Error: CSV filename required")
    sys.exit(1)

csv_filename = sys.argv[1]

# Get API keys from environment
api_key = os.environ.get('API_KEY')
if not api_key:
    print("Error: API_KEY environment variable not set")
    sys.exit(1)

# Read and process CSV
with open(csv_filename, 'r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        # Process each row
        value1 = row.get('column1', '')
        value2 = row.get('column2', '')
        # ... your processing logic here
```

## Summary

- **Use triple-quoted docstrings** (`"""`) at the top of every script
- **Include CSV Format section** explaining required/optional columns
- **Provide usage examples** showing command-line syntax
- **List requirements** including API keys and dependencies
- **Handle CSV files** passed as `sys.argv[1]`
- **Support case-insensitive column matching** for better user experience
- **Use environment variables** for API keys (compatible with CSV Script Manager)
- **Include shebang line** (`#!/usr/bin/env python3`) for cross-platform compatibility

Following this format ensures your scripts are:
- Easy to understand for users
- Properly displayed in the CSV Script Manager interface
- Consistent with other scripts in the repository
- Well-documented for maintenance and updates
