from flask import Flask, request, jsonify, send_from_directory
import requests
import os

app = Flask("router_lookup")

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

@app.route('/')
def serve_index():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'index.html')

@app.route('/router', methods=['GET'])
def get_router_info():
    user_input = request.args.get('input')
    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    if len(user_input) == 14:
        filter_type = 'serial_number'
    else:
        filter_type = 'mac'
        user_input = user_input.replace(':', '')
        if len(user_input) != 12:
            return jsonify({"result": "Invalid serial number or MAC address"}), 200

    results = {}
    for account_name, api_keys in named_keys.items():
        url = f'https://www.cradlepointecm.com/api/v2/routers/?{filter_type}={user_input}'
        response = requests.get(url, headers=api_keys)
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get("data"):
                return jsonify({"result": f"Account Name: {account_name}"}), 200

    return jsonify({"result": "No router found"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
