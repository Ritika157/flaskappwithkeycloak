import requests
from flask import Flask, redirect, url_for, session, request, render_template
import logging

app = Flask(__name__)
app.secret_key = '123456'

logging.basicConfig(level=logging.DEBUG)  # Basic logging configuration

keycloak_server_url = 'http://localhost:8080/'
realm_name = 'keycloak'
client_id = 'flask_app'
client_secret = 'awiQI1amOKsNBwOrOZrt4Bkabg3zsDGY'

@app.route('/')
def index():
    if 'user' in session:
        return render_template('home.html', username=session['user']['username'])
    else:
        return redirect(url_for('login'))

@app.route('/login')
def login():
    authorize_url = f"{keycloak_server_url}/realms/{realm_name}/protocol/openid-connect/auth"
    redirect_uri = 'http://127.0.0.1:5000/callback'
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid profile email'
    }
    return redirect(f"{authorize_url}?{'&'.join([f'{key}={value}' for key, value in params.items()])}")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    
    logging.debug(f"Callback received with code: {code}")

    token_endpoint = f"{keycloak_server_url}/realms/{realm_name}/protocol/openid-connect/token"
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'http://127.0.0.1:5000/callback',
        'client_id': client_id,
        'client_secret': client_secret
    }

    try:
        response = requests.post(token_endpoint, data=payload)
        token_data = response.json()

        if 'access_token' in token_data:
            userinfo_endpoint = f"{keycloak_server_url}/realms/{realm_name}/protocol/openid-connect/userinfo"
            userinfo_response = requests.get(userinfo_endpoint, headers={'Authorization': f"Bearer {token_data['access_token']}"})
            userinfo = userinfo_response.json()

            session['user'] = {
                'id_token': token_data.get('id_token'),
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'username': userinfo.get('preferred_username'),
                'email': userinfo.get('email')
            }

            logging.debug("User logged in successfully.")
            return redirect(url_for('index'))
        else:
            logging.error("Failed to fetch tokens.")
            return "Failed to fetch tokens."

    except Exception as e:
        logging.error(f"Exception during token exchange: {e}")
        return "Failed to fetch tokens."

@app.route('/logout')
def logout():
    logging.debug('Attempting to logout...')

    try:
        end_session_endpoint = f"{keycloak_server_url}/realms/{realm_name}/protocol/openid-connect/logout"
        redirect_uri = 'http://127.0.0.1:5000/login'

        # Optionally add 'id_token_hint' to request to invalidate session at IdP
        response = requests.get(f"{end_session_endpoint}?redirect_uri={redirect_uri}", timeout=5)

        session.clear()  # Clear session data upon successful logout
        logging.debug('Session cleared. Redirecting to login...')

        return redirect(url_for('login'))

    except requests.exceptions.RequestException as e:
        logging.error(f"Exception during logout: {e}")
        return "Failed to logout. Please try again."

if __name__ == '__main__':
    app.run(debug=True)
