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

**Updating from an older copy:** delete the old "Ericsson NCM API" collection first, then import. If a folder shows **"Couldn't load items"** and **Retry** doesn't clear it, delete the collection and import it again.

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
| `NCM_API_TOKEN` | Your NCM API v3 Token |

The four `X-` keys are for APIv2. `NCM_API_TOKEN` is for APIv3 (every request that uses `{{v3BaseUrl}}`, including the BETA folders). The older name `TOKEN` still works as an alias.

Keep credentials in the environment, not in the collection's **Variables** tab, so they aren't included if you export or share the collection.

**How to obtain these credentials:**
- Follow the official Ericsson documentation: [Obtaining API Keys](https://docs.cradlepoint.com/r/NCM-APIv2-Overview/Obtaining-API-Keys)

### 3. Select Your Environment
In the **environment dropdown** (top-right of Postman), select the environment you just created.

---

## 🚀 Making Your First Request

1. **Expand the collection** in your sidebar
2. Navigate to **Accounts** folder
3. Click **List Accounts**
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
- Remote Connect (LAN Manager), modem upgrades, PCN, NetCloud Exchange
- And more...

### Variables and Safety Checks
Requests that need an ID use variables like `{{router_id}}`, `{{group_id}}` or `{{id}}`. Set them in the collection **Variables** tab, your environment, or a CSV column.

A collection-level pre-request script checks every request before it's sent. If credentials or a variable are missing, the request isn't sent and the **Test Results** tab (and Postman Console) names what to set. This stops literal `{{router_id}}` values from reaching the API.

`start_time` and `end_time` default to the last 24 hours for endpoints that require a time window.

### Bulk Operations with CSV
Run operations on multiple devices using CSV files:
1. Click **Run** on any folder
2. Select **Test data file** and upload your CSV
3. Postman will execute the request for each row in your CSV

**Note:** Bulk operations with CSV files require a paid Postman account.

**CSV Example:**
```csv
router_id
1234567
2345678
```

Column headers must match variable names used by the request. A column named `id` is also mapped to `router_id`.

### Automation Workflows
The collection includes pre-built multi-step workflows under "Automation Workflows" folder that:
- Call multiple API endpoints in sequence
- Handle common complex operations automatically
- Pass data between requests

**Note:** Automation workflows require a paid Postman account.

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
| **"Request not sent"** | The message names the missing credential or variable. Set it and send again |
| **"Couldn't load items" in the sidebar** | If Retry doesn't clear it, delete the collection and import it again |
| **409 on a samples or logs endpoint** | Those endpoints need a `router` or `net_device` filter (max 100 IDs). Set `router_id` / `net_device_id` |
| **Request not found** | Make sure the collection was imported correctly |
| **Variables showing as undefined** | Check that your environment variables use exact names (case-sensitive) |
| **CSV bulk operations fail** | Ensure CSV column headers match variable names used in requests |

---

Happy API testing! 🎉
