"""
NCM API Key Encryptor
For encrypting NCM API keys into group or device configurations for use in SDK applications.
"""

import os
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import ncm

app = FastAPI(title="NCM API Key Encryptor")
app.add_middleware(SessionMiddleware, secret_key="ncm-api-key-tool-secret-key-change-in-production")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Try to load admin keys from environment variables on startup
def load_admin_keys_from_env():
    """Load the admin API keys (first form) from environment variables if available.
    Uses: X_ECM_API_ID, X_ECM_API_KEY, X_CP_API_ID, X_CP_API_KEY.
    NCM_API_TOKEN is optional - use as CP key if X_CP_API_KEY is empty.
    """
    admin_x_ecm_api_id = (os.environ.get('X_ECM_API_ID') or '').strip()
    admin_x_ecm_api_key = (os.environ.get('X_ECM_API_KEY') or '').strip()
    admin_x_cp_api_id = (os.environ.get('X_CP_API_ID') or '').strip()
    admin_x_cp_api_key = (os.environ.get('X_CP_API_KEY') or os.environ.get('NCM_API_TOKEN') or '').strip()

    if all([admin_x_ecm_api_id, admin_x_ecm_api_key, admin_x_cp_api_id, admin_x_cp_api_key]):
        try:
            admin_api_keys = {
                'X-ECM-API-ID': admin_x_ecm_api_id,
                'X-ECM-API-KEY': admin_x_ecm_api_key,
                'X-CP-API-ID': admin_x_cp_api_id,
                'X-CP-API-KEY': admin_x_cp_api_key
            }
            ncm.set_api_keys(admin_api_keys)
            accounts = ncm.get_accounts()
            if accounts and len(accounts) > 0:
                return admin_api_keys
        except Exception:
            pass
    return None


# Load admin keys on startup
_admin_keys_from_env = load_admin_keys_from_env()


def _add_flash(request: Request, message: str, category: str = "info"):
    """Add a flash message to the session."""
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append({"category": category, "message": message})


def _get_flashed_messages(request: Request):
    """Retrieve and clear flash messages from the session."""
    messages = request.session.pop("flash_messages", [])
    return messages


@app.post("/clear")
async def clear_admin_keys(request: Request):
    request.session.pop('admin_keys_set', None)
    request.session.pop('account_name', None)
    request.session.pop('admin_x_ecm_api_id', None)
    request.session.pop('admin_x_ecm_api_key', None)
    request.session.pop('admin_x_cp_api_id', None)
    request.session.pop('admin_x_cp_api_key', None)
    _add_flash(request, 'Admin keys cleared.', 'info')
    return RedirectResponse(url="/", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def index_get(request: Request):
    """Render the main page."""
    # On page load: if keys were loaded from env at startup but session isn't set yet, sync session
    if isinstance(_admin_keys_from_env, dict) and not request.session.get('admin_keys_set'):
        try:
            accounts = ncm.get_accounts()
            if accounts and len(accounts) > 0:
                request.session['admin_keys_set'] = True
                request.session['account_name'] = accounts[0].get('name', 'Unknown')
                request.session['admin_x_ecm_api_id'] = _admin_keys_from_env.get('X-ECM-API-ID', '')
                request.session['admin_x_ecm_api_key'] = _admin_keys_from_env.get('X-ECM-API-KEY', '')
                request.session['admin_x_cp_api_id'] = _admin_keys_from_env.get('X-CP-API-ID', '')
                request.session['admin_x_cp_api_key'] = _admin_keys_from_env.get('X-CP-API-KEY', '')
        except Exception:
            pass
    elif request.session.get('admin_keys_set'):
        try:
            ncm.get_accounts()
        except Exception:
            if all([request.session.get('admin_x_ecm_api_id'), request.session.get('admin_x_ecm_api_key'),
                    request.session.get('admin_x_cp_api_id'), request.session.get('admin_x_cp_api_key')]):
                try:
                    admin_api_keys = {
                        'X-ECM-API-ID': request.session['admin_x_ecm_api_id'],
                        'X-ECM-API-KEY': request.session['admin_x_ecm_api_key'],
                        'X-CP-API-ID': request.session['admin_x_cp_api_id'],
                        'X-CP-API-KEY': request.session['admin_x_cp_api_key']
                    }
                    ncm.set_api_keys(admin_api_keys)
                    ncm.get_accounts()
                except Exception:
                    request.session.pop('admin_keys_set', None)
                    request.session.pop('account_name', None)
                    request.session.pop('admin_x_ecm_api_id', None)
                    request.session.pop('admin_x_ecm_api_key', None)
                    request.session.pop('admin_x_cp_api_id', None)
                    request.session.pop('admin_x_cp_api_key', None)
            else:
                request.session.pop('admin_keys_set', None)
                request.session.pop('account_name', None)

    config_success = request.session.pop('config_success_message', None)
    config_error = request.session.pop('config_error_message', None)
    messages = _get_flashed_messages(request)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "admin_keys_set": request.session.get('admin_keys_set', False),
        "account_name": request.session.get('account_name'),
        "config_success_message": config_success,
        "config_error_message": config_error,
        "messages": messages,
    })


@app.post("/", response_class=HTMLResponse)
async def index_post(request: Request):
    """Handle form submissions."""
    form = await request.form()

    # Handle admin keys form submission
    if 'admin_submit' in form:
        admin_x_ecm_api_id = (form.get('admin_x_ecm_api_id') or '').strip()
        admin_x_ecm_api_key = (form.get('admin_x_ecm_api_key') or '').strip()
        admin_x_cp_api_id = (form.get('admin_x_cp_api_id') or '').strip()
        admin_x_cp_api_key = (form.get('admin_x_cp_api_key') or '').strip()

        if not all([admin_x_ecm_api_id, admin_x_ecm_api_key, admin_x_cp_api_id, admin_x_cp_api_key]):
            _add_flash(request, 'Please fill in all admin API key fields.', 'error')
        else:
            try:
                admin_api_keys = {
                    'X-ECM-API-ID': admin_x_ecm_api_id,
                    'X-ECM-API-KEY': admin_x_ecm_api_key,
                    'X-CP-API-ID': admin_x_cp_api_id,
                    'X-CP-API-KEY': admin_x_cp_api_key
                }
                ncm.set_api_keys(admin_api_keys)

                accounts = ncm.get_accounts()

                if accounts and len(accounts) > 0:
                    account_name = accounts[0].get('name', 'Unknown')
                    request.session['account_name'] = account_name
                    request.session['admin_keys_set'] = True
                    request.session['admin_x_ecm_api_id'] = admin_x_ecm_api_id
                    request.session['admin_x_ecm_api_key'] = admin_x_ecm_api_key
                    request.session['admin_x_cp_api_id'] = admin_x_cp_api_id
                    request.session['admin_x_cp_api_key'] = admin_x_cp_api_key
                else:
                    _add_flash(request, 'Failed to retrieve accounts. Please check your API keys.', 'error')
            except Exception as e:
                _add_flash(request, f'Error setting admin API keys: {str(e)}', 'error')

        return RedirectResponse(url="/", status_code=303)

    # Handle config keys form submission
    elif 'config_submit' in form:
        # Re-set admin keys if session has them (in case server was restarted)
        if request.session.get('admin_keys_set'):
            try:
                ncm.get_accounts()
            except Exception:
                if all([request.session.get('admin_x_ecm_api_id'), request.session.get('admin_x_ecm_api_key'),
                        request.session.get('admin_x_cp_api_id'), request.session.get('admin_x_cp_api_key')]):
                    admin_api_keys = {
                        'X-ECM-API-ID': request.session['admin_x_ecm_api_id'],
                        'X-ECM-API-KEY': request.session['admin_x_ecm_api_key'],
                        'X-CP-API-ID': request.session['admin_x_cp_api_id'],
                        'X-CP-API-KEY': request.session['admin_x_cp_api_key']
                    }
                    ncm.set_api_keys(admin_api_keys)
                else:
                    request.session['config_error_message'] = 'Admin keys session expired. Please re-enter admin keys.'
                    return RedirectResponse(url="/", status_code=303)

        use_admin_keys = form.get('use_admin_keys') == '1'
        destination_type = form.get('destination_type', 'Group')
        identifier_type = form.get('identifier_type', 'ID')
        identifier_value = (form.get('identifier_value') or '').strip()

        if use_admin_keys:
            if isinstance(_admin_keys_from_env, dict):
                config_x_ecm_api_id = request.session.get('admin_x_ecm_api_id') or _admin_keys_from_env.get('X-ECM-API-ID', '')
                config_x_ecm_api_key = request.session.get('admin_x_ecm_api_key') or _admin_keys_from_env.get('X-ECM-API-KEY', '')
                config_x_cp_api_id = request.session.get('admin_x_cp_api_id') or _admin_keys_from_env.get('X-CP-API-ID', '')
                config_x_cp_api_key = request.session.get('admin_x_cp_api_key') or _admin_keys_from_env.get('X-CP-API-KEY', '')
            else:
                config_x_ecm_api_id = request.session.get('admin_x_ecm_api_id', '')
                config_x_ecm_api_key = request.session.get('admin_x_ecm_api_key', '')
                config_x_cp_api_id = request.session.get('admin_x_cp_api_id', '')
                config_x_cp_api_key = request.session.get('admin_x_cp_api_key', '')
            config_bearer_token = ''
            has_all_apiv2 = all([config_x_ecm_api_id, config_x_ecm_api_key, config_x_cp_api_id, config_x_cp_api_key])
            has_apiv3 = False
        else:
            config_x_ecm_api_id = (form.get('config_x_ecm_api_id') or '').strip()
            config_x_ecm_api_key = (form.get('config_x_ecm_api_key') or '').strip()
            config_x_cp_api_id = (form.get('config_x_cp_api_id') or '').strip()
            config_x_cp_api_key = (form.get('config_x_cp_api_key') or '').strip()
            config_bearer_token = (form.get('config_bearer_token') or '').strip()
            has_all_apiv2 = all([config_x_ecm_api_id, config_x_ecm_api_key, config_x_cp_api_id, config_x_cp_api_key])
            has_apiv3 = bool(config_bearer_token)

        # Validate inputs
        if use_admin_keys and not has_all_apiv2:
            request.session['config_error_message'] = 'Admin keys are not available. Please re-enter admin keys in Step 1.'
        elif not use_admin_keys and not has_all_apiv2 and not has_apiv3:
            request.session['config_error_message'] = 'Please fill in all 4 APIv2 key fields OR provide an APIv3 token.'
        elif not identifier_value:
            request.session['config_error_message'] = f'Please enter a {destination_type} {identifier_type.lower()}.'
        else:
            try:
                kwargs = {
                    'x_ecm_api_id': config_x_ecm_api_id or '',
                    'x_ecm_api_key': config_x_ecm_api_key or '',
                    'x_cp_api_id': config_x_cp_api_id or '',
                    'x_cp_api_key': config_x_cp_api_key or '',
                    'bearer_token': config_bearer_token or ''
                }

                if identifier_type == "ID":
                    if destination_type == "Group":
                        kwargs['group_id'] = identifier_value
                    else:
                        kwargs['router_id'] = identifier_value
                else:
                    if destination_type == "Group":
                        kwargs['group_name'] = identifier_value
                    else:
                        kwargs['router_name'] = identifier_value

                if destination_type == "Group":
                    ncm.set_ncm_api_keys_by_group(**kwargs)
                else:
                    ncm.set_ncm_api_keys_by_router(**kwargs)

                request.session['config_success_message'] = f'Successfully set API keys for {destination_type.lower()}: {identifier_value}'
            except Exception as e:
                request.session['config_error_message'] = f'Error setting API keys: {str(e)}'

        return RedirectResponse(url="/", status_code=303)

    # Unknown form submission
    return RedirectResponse(url="/", status_code=303)


if __name__ == '__main__':
    print("NCM API Key Encryptor starting...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
