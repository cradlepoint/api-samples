from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
import os
from pathlib import Path
import uvicorn

app = FastAPI(title="Router Lookup")

# Serve static files (index.html)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Dictionary of named keys
named_keys = {
    'account1': {
        'X-ECM-API-ID': '1234567890',
        'X-ECM-API-KEY': '0987654321',
        'X-CP-API-ID': '1234567890',
        'X-CP-API-KEY': '0987654321'
    },
    'account2': {
        'X-ECM-API-ID': '1234567890',
        'X-ECM-API-KEY': '0987654321',
        'X-CP-API-ID': '1234567890',
        'X-CP-API-KEY': '0987654321'
    },
    'account3': {
        'X-ECM-API-ID': '1234567890',
        'X-ECM-API-KEY': '0987654321',
        'X-CP-API-ID': '1234567890',
        'X-CP-API-KEY': '0987654321'
    }
}


@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/router")
async def get_router_info(input: str = ""):
    if not input:
        return JSONResponse({"error": "No input provided"}, status_code=400)

    user_input = input
    if len(user_input) == 14:
        filter_type = 'serial_number'
    else:
        filter_type = 'mac'
        user_input = user_input.replace(':', '')
        if len(user_input) != 12:
            return JSONResponse({"result": "Invalid serial number or MAC address"})

    async with httpx.AsyncClient() as client:
        for account_name, api_keys in named_keys.items():
            url = f'https://www.cradlepointecm.com/api/v2/routers/?{filter_type}={user_input}'
            response = await client.get(url, headers=api_keys)
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get("data"):
                    return JSONResponse({"result": f"Account Name: {account_name}"})

    return JSONResponse({"result": "No router found"})


if __name__ == '__main__':
    print("Router Lookup starting...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
