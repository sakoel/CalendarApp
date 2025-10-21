from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from PIL import Image
import pytesseract
import re
from googleapiclient.discovery import build
from google.oauth2 import credentials
from google_auth_oauthlib.flow import Flow
import os
import requests
import json

import jwt, datetime
from db import save_user_creds, get_user_creds
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from google.oauth2 import credentials as google_creds

from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config.update(PREFERRED_URL_SCHEME="https")

# --- Configuration ---
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://calendar-app-henna-five.vercel.app",
            "chrome-extension://<YOUR_EXTENSION_ID>"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 86400
    }
})
app.secret_key = os.environ.get("SECRET_KEY", "default-secret-key")

# Tesseract OCR path (update for Windows if needed)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
# Example for Windows:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# OAuth2 Configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = json.loads(os.environ.get("CLIENT_SECRET_JSON"))
SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = '/oauth2callback'
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://calendar-app-henna-five.vercel.app/")

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALG = "HS256"
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_flow(redirect_uri):
    return Flow.from_client_config(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

OCR_ENABLED = os.environ.get("OCR_ENABLED", "0") == "1"
try:
    if OCR_ENABLED:
        from PIL import Image
        import pytesseract
except Exception as _e:
    OCR_ENABLED = False

@app.route('/api/authenticate', methods=['GET'])
def authenticate():
    try:
        redirect_uri = url_for('oauth2callback', _external=True, _scheme='https')
        flow = get_flow(redirect_uri)
        authorization_url, state = flow.authorization_url(
            access_type='offline', prompt='consent', include_granted_scopes='true'
        )
        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
        print("Auth setup error:", e)
        return jsonify({'error': f'Auth not configured: {e}'}), 500

@app.route(REDIRECT_URI)
def oauth2callback():
    redirect_uri = url_for('oauth2callback', _external=True, _scheme='https')
    flow = get_flow(redirect_uri)
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    # Identify Google user
    try:
        req = google_requests.Request()
        idinfo = google_id_token.verify_oauth2_token(
            creds.id_token, req, CLIENT_SECRETS_FILE["web"]["client_id"]
        )
        sub = idinfo["sub"]
        email = idinfo.get("email", "")
    except Exception:
        # Fallback if id_token missing
        sub, email = "unknown", ""

    # Persist this user's Google creds
    save_user_creds(sub, email, creds.to_json())

    # Issue your short-lived app token
    app_token = issue_app_token(sub, email)

    # Simple success page that shows the token and lets users copy it
    return f"""<!doctype html><meta charset="utf-8">
    <h3>Signed in as {email}</h3>
    <p>Copy this token into the extension (Settings → Token):</p>
    <textarea id=t rows=4 cols=80>{app_token}</textarea>
    <p><button onclick="navigator.clipboard.writeText(document.getElementById('t').value)">Copy</button></p>
    <p>You can close this tab.</p>
    """

def load_credentials():
    if os.path.exists('token.json'):
        with open('token.json', 'r') as token:
            creds = credentials.Credentials.from_authorized_user_info(json.load(token), SCOPES)
        return creds
    return None  # Return None if token.json is missing
    
@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        # Remove the stored token
        if os.path.exists('token.json'):
            os.remove('token.json')
        session.pop('credentials', None)
        # Revoke the token from Google if possible
        creds_json = session.get('credentials')
        if creds_json:
            creds = json.loads(creds_json)
            token = creds.get('token')
            if token:
                revoke = requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
                if revoke.status_code != 200:
                    print(f"Failed to revoke token: {revoke.text}")
        return redirect(FRONTEND_URL)
    except Exception as e:
        print(f"Error during logout: {e}")
        return jsonify({'error': 'Logout failed!'}), 500

@app.route('/api/create_event', methods=['POST'])
def create_event():
    creds = load_user_credentials_for(request.user_sub)
    if not creds:
        return jsonify({'error': 'User not authenticated with Google'}), 401

    try:
        service = build('calendar', 'v3', credentials=creds)

        data = request.get_json(silent=True) or request.form
        date = (data.get('date') or '').strip()
        time_ = (data.get('time') or '').strip()
        description = (data.get('description') or '').strip()

        if not (date and time_ and description):
            return jsonify({'error': 'Missing fields: date, time, description'}), 400

        event = {
            'summary': description,
            'start': {'dateTime': f"{date}T{time_}:00", 'timeZone': 'America/Toronto'},
            'end':   {'dateTime': f"{date}T{time_}:00", 'timeZone': 'America/Toronto'},
        }

        created = service.events().insert(calendarId='primary', body=event).execute()

        # Optional: save refreshed creds if they changed
        try:
            save_user_creds(request.user_sub, request.user_email, creds.to_json())
        except Exception:
            pass

        return jsonify({'success': True, 'eventLink': created.get('htmlLink')}), 200
    except Exception as e:
        print("Error creating event:", e)
        return jsonify({'error': 'Enter all data!'}), 500
    
def issue_app_token(sub: str, email: str):
    now = datetime.datetime.utcnow()
    payload = {
        "sub": sub,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(hours=24)).timestamp())  # 24h
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def require_bearer(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing bearer token"}), 401
        token = auth.split(" ", 1)[1]
        try:
            claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            request.user_sub = claims["sub"]
            request.user_email = claims.get("email")
        except Exception:
            return jsonify({"error": "invalid/expired token"}), 401
        return func(*args, **kwargs)
    return wrapper

def load_user_credentials_for(sub: str):
    stored = get_user_creds(sub)
    if not stored:
        return None
    return google_creds.Credentials.from_authorized_user_info(stored, SCOPES)


if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)