"""
NCM API Key Encryptor
For encrypting NCM API keys into group or device configurations for use in SDK applications.
"""

from flask import Flask, render_template, request, session, redirect, url_for, flash
import ncm

app = Flask(__name__)
app.secret_key = 'ncm-api-key-tool-secret-key-change-in-production'

@app.route('/clear', methods=['POST'])
def clear_admin_keys():
    session.pop('admin_keys_set', None)
    session.pop('account_name', None)
    session.pop('admin_x_ecm_api_id', None)
    session.pop('admin_x_ecm_api_key', None)
    session.pop('admin_x_cp_api_id', None)
    session.pop('admin_x_cp_api_key', None)
    flash('Admin keys cleared.', 'info')
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle admin keys form submission
        if 'admin_submit' in request.form:
            admin_x_ecm_api_id = request.form.get('admin_x_ecm_api_id', '').strip()
            admin_x_ecm_api_key = request.form.get('admin_x_ecm_api_key', '').strip()
            admin_x_cp_api_id = request.form.get('admin_x_cp_api_id', '').strip()
            admin_x_cp_api_key = request.form.get('admin_x_cp_api_key', '').strip()
            
            if not all([admin_x_ecm_api_id, admin_x_ecm_api_key, admin_x_cp_api_id, admin_x_cp_api_key]):
                flash('Please fill in all admin API key fields.', 'error')
            else:
                try:
                    # Set admin API keys
                    admin_api_keys = {
                        'X-ECM-API-ID': admin_x_ecm_api_id,
                        'X-ECM-API-KEY': admin_x_ecm_api_key,
                        'X-CP-API-ID': admin_x_cp_api_id,
                        'X-CP-API-KEY': admin_x_cp_api_key
                    }
                    ncm.set_api_keys(admin_api_keys)
                    
                    # Verify by getting accounts
                    accounts = ncm.get_accounts()
                    
                    if accounts and len(accounts) > 0:
                        account_name = accounts[0].get('name', 'Unknown')
                        session['account_name'] = account_name
                        session['admin_keys_set'] = True
                        # Store admin keys in session to restore after server restart
                        session['admin_x_ecm_api_id'] = admin_x_ecm_api_id
                        session['admin_x_ecm_api_key'] = admin_x_ecm_api_key
                        session['admin_x_cp_api_id'] = admin_x_cp_api_id
                        session['admin_x_cp_api_key'] = admin_x_cp_api_key
                    else:
                        flash('Failed to retrieve accounts. Please check your API keys.', 'error')
                except Exception as e:
                    flash(f'Error setting admin API keys: {str(e)}', 'error')
            
            return redirect(url_for('index'))
        
        # Handle config keys form submission
        elif 'config_submit' in request.form:
            # Re-set admin keys if session has them (in case server was restarted)
            if session.get('admin_keys_set'):
                try:
                    # Try to get accounts to verify NCM instance exists
                    ncm.get_accounts()
                except:
                    # NCM instance lost, restore from session
                    if all([session.get('admin_x_ecm_api_id'), session.get('admin_x_ecm_api_key'), 
                            session.get('admin_x_cp_api_id'), session.get('admin_x_cp_api_key')]):
                        admin_api_keys = {
                            'X-ECM-API-ID': session['admin_x_ecm_api_id'],
                            'X-ECM-API-KEY': session['admin_x_ecm_api_key'],
                            'X-CP-API-ID': session['admin_x_cp_api_id'],
                            'X-CP-API-KEY': session['admin_x_cp_api_key']
                        }
                        ncm.set_api_keys(admin_api_keys)
                    else:
                        session['config_error_message'] = 'Admin keys session expired. Please re-enter admin keys.'
                        return redirect(url_for('index'))
            
            config_x_ecm_api_id = request.form.get('config_x_ecm_api_id', '').strip()
            config_x_ecm_api_key = request.form.get('config_x_ecm_api_key', '').strip()
            config_x_cp_api_id = request.form.get('config_x_cp_api_id', '').strip()
            config_x_cp_api_key = request.form.get('config_x_cp_api_key', '').strip()
            config_bearer_token = request.form.get('config_bearer_token', '').strip()
            destination_type = request.form.get('destination_type', 'Group')
            identifier_type = request.form.get('identifier_type', 'ID')
            identifier_value = request.form.get('identifier_value', '').strip()
            
            # Validate inputs - require all APIv2 keys OR APIv3 token
            has_all_apiv2 = all([config_x_ecm_api_id, config_x_ecm_api_key, config_x_cp_api_id, config_x_cp_api_key])
            has_apiv3 = bool(config_bearer_token)
            
            if not has_all_apiv2 and not has_apiv3:
                session['config_error_message'] = 'Please fill in all 4 APIv2 key fields OR provide an APIv3 token.'
            elif not identifier_value:
                session['config_error_message'] = f'Please enter a {destination_type} {identifier_type.lower()}.'
            else:
                try:
                    # Prepare parameters
                    kwargs = {
                        'x_ecm_api_id': config_x_ecm_api_id if config_x_ecm_api_id else '',
                        'x_ecm_api_key': config_x_ecm_api_key if config_x_ecm_api_key else '',
                        'x_cp_api_id': config_x_cp_api_id if config_x_cp_api_id else '',
                        'x_cp_api_key': config_x_cp_api_key if config_x_cp_api_key else '',
                        'bearer_token': config_bearer_token if config_bearer_token else ''
                    }
                    
                    # Set identifier parameter
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
                    
                    # Call appropriate function
                    if destination_type == "Group":
                        result = ncm.set_ncm_api_keys_by_group(**kwargs)
                    else:
                        result = ncm.set_ncm_api_keys_by_router(**kwargs)
                    
                    session['config_success_message'] = f'Successfully set API keys for {destination_type.lower()}: {identifier_value}'
                except Exception as e:
                    session['config_error_message'] = f'Error setting API keys: {str(e)}'
            
            return redirect(url_for('index'))
    
    # On page load, verify NCM instance is still valid if session says keys are set
    if session.get('admin_keys_set'):
        try:
            # Try to get accounts to verify NCM instance exists
            ncm.get_accounts()
        except:
            # NCM instance lost, restore from session
            if all([session.get('admin_x_ecm_api_id'), session.get('admin_x_ecm_api_key'), 
                    session.get('admin_x_cp_api_id'), session.get('admin_x_cp_api_key')]):
                try:
                    admin_api_keys = {
                        'X-ECM-API-ID': session['admin_x_ecm_api_id'],
                        'X-ECM-API-KEY': session['admin_x_ecm_api_key'],
                        'X-CP-API-ID': session['admin_x_cp_api_id'],
                        'X-CP-API-KEY': session['admin_x_cp_api_key']
                    }
                    ncm.set_api_keys(admin_api_keys)
                    # Verify it works
                    ncm.get_accounts()
                except:
                    # Still failed, clear session
                    session.pop('admin_keys_set', None)
                    session.pop('account_name', None)
                    session.pop('admin_x_ecm_api_id', None)
                    session.pop('admin_x_ecm_api_key', None)
                    session.pop('admin_x_cp_api_id', None)
                    session.pop('admin_x_cp_api_key', None)
            else:
                # No keys in session, clear state
                session.pop('admin_keys_set', None)
                session.pop('account_name', None)
    
    config_success = session.pop('config_success_message', None)
    config_error = session.pop('config_error_message', None)
    return render_template('index.html', 
                         admin_keys_set=session.get('admin_keys_set', False),
                         account_name=session.get('account_name'),
                         config_success_message=config_success,
                         config_error_message=config_error)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
