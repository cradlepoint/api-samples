# Ericsson NCM API Postman Collection

This folder contains the **Ericsson Enterprise Wireless NetCloud Manager (NCM) API** Postman collection, a pre-configured set of API requests for interacting with Ericsson's NetCloud Manager API.

## 📥 How to Import the Collection

### Downloading the Collection File from GitHub

If you only need the Postman collection file without cloning the entire repository:

1. Navigate to the file on GitHub: `Ericsson NCM API Postman Collection.json`
2. Click the **Download** button (or **Download raw file** icon) in the top right
3. Save the file to your computer

### Step 1: Open Postman
1. Launch **Postman** on your computer
2. If you don't have Postman, download it from [postman.com](https://www.postman.com/downloads/)

### Step 2: Import the Collection
1. Click the **Import** button (top-left corner of Postman)
2. Select **Upload Files**
3. Choose the **`Ericsson NCM API Postman Collection.json`** file
4. Click **Import**

The collection will now appear in your Postman sidebar under **Collections**.

---

## 🔑 Quick Setup Guide

### 1. Create an Environment
Before making API calls, you need to set up your API credentials:

1. Click the **Environments** tab (left sidebar)
2. Click **Create Environment** 
3. Name it something like `NCM Production` or `NCM Dev`

### 2. Add API Variables
Add the following variables to your environment with your actual API credentials:

| Variable | Value |
|----------|-------|
| `X-ECM-API-ID` | Your ECM API ID |
| `X-ECM-API-KEY` | Your ECM API Key |
| `X-CP-API-ID` | Your CP API ID |
| `X-CP-API-KEY` | Your CP API Key |
| `TOKEN` | Your NCM API v3 Token |

**How to obtain these credentials:**
- Follow the official Ericsson documentation: [Obtaining API Keys](https://docs.cradlepoint.com/r/NCM-APIv2-Overview/Obtaining-API-Keys)

### 3. Select Your Environment
In the **environment dropdown** (top-right of Postman), select the environment you just created.

---

## 🚀 Making Your First Request

1. **Expand the collection** in your sidebar
2. Navigate to **Accounts** folder
3. Click **Get Accounts Information**
4. Click the **Send** button

**Expected Result:**
- Status: `200 OK`
- Response body with your account information in JSON format

If you receive a `401` or `403` error:
- ✓ Verify the correct environment is selected
- ✓ Double-check that your API keys are entered correctly
- ✓ Ensure the variables are saved in your environment

---

## 📚 Collection Features

### Pre-configured Requests
The collection includes requests for:
- Account management
- Router/device operations
- Configuration management
- User management
- And more...

### Bulk Operations with CSV
Run operations on multiple devices using CSV files:
1. Click **Run** on any folder
2. Select **Test data file** and upload your CSV
3. Postman will execute the request for each row in your CSV

**CSV Example:**
```csv
id,mac,serial_number,ip_address
12345,AA:BB:CC:DD:EE:FF,SN001,192.168.1.10
67890,11:22:33:44:55:66,SN002,192.168.1.11
```

### Automation Workflows
The collection includes pre-built multi-step workflows under "Automation Workflows" folder that:
- Call multiple API endpoints in sequence
- Handle common complex operations automatically
- Pass data between requests

---

## 📖 Full Documentation

For complete detailed instructions and all available operations, open the **Ericsson NCM API Postman Collection** in Postman and look at the **Description** tab at the collection level. It contains comprehensive documentation about:
- All available endpoints
- Bulk operation usage
- Automation workflows
- Variable references
- And more

---

## 🔗 Additional Resources

- [NCM API Documentation](https://docs.cradlepoint.com/r/NCM-APIv2-Overview)
- [API Key Setup](https://docs.cradlepoint.com/r/NCM-APIv2-Overview/Obtaining-API-Keys)
- [Postman Documentation](https://learning.postman.com/docs/getting-started/overview/)

---

## 💡 Tips

- Use **Postman Environments** to manage different API credentials (dev, staging, production)
- Check the **Tests** tab on requests to see any automated validation
- Use **Collection Runner** for bulk operations with CSV files
- Export responses for further analysis

---

## ❓ Troubleshooting

| Issue | Solution |
|-------|----------|
| **401/403 Errors** | Verify API keys in environment and ensure correct environment is selected |
| **Request not found** | Make sure the collection was imported correctly |
| **Variables showing as undefined** | Check that your environment variables use exact names (case-sensitive) |
| **CSV bulk operations fail** | Ensure CSV column headers match variable names used in requests |

---

Happy API testing! 🎉
