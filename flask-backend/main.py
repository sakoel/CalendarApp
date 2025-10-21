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

# --- Configuration ---
app = Flask(__name__)
CORS(app, origins=["https://calendar-app-henna-five.vercel.app"])
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
        redirect_uri = url_for('oauth2callback', _external=True)
        flow = get_flow(redirect_uri)
        authorization_url, state = flow.authorization_url(
            access_type='offline',  # Request offline access
            prompt='consent',       # Force re-authentication
            include_granted_scopes='true'
        )
        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
        print(f"Error during authentication: {e}")
        return jsonify({'error': 'Authentication failed!'}), 500

@app.route(REDIRECT_URI)
def oauth2callback():
    state = session.get('state')
    redirect_uri = url_for('oauth2callback', _external=True)
    flow = get_flow(redirect_uri)
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    try:
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    except Exception as e:
        print("Could not save token.json:", e)
        return jsonify({"error": "Could not save token.json, but calendar may still work."})
    session['credentials'] = creds.to_json()
    # Redirect to your frontend after authentication
    return redirect(FRONTEND_URL + "?authenticated=true")

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
    creds = load_credentials()
    if not creds:
        return jsonify({'error': 'User not authenticated'}), 401

    try:
        service = build('calendar', 'v3', credentials=creds)
        event = None  # define up front

        # --- If OCR is enabled and an image is provided ---
        if OCR_ENABLED and 'image' in request.files:
            try:
                image = Image.open(request.files['image'])
                text = pytesseract.image_to_string(image)
                print(f"OCR Extracted Text: {text}")

                # Simple regex to find date, time, and description
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
                time_match = re.search(r'(\d{2}:\d{2})', text)
                description_match = re.search(r'Description:\s*(.*)', text)

                if date_match and time_match and description_match:
                    date = date_match.group(1)
                    time_ = time_match.group(1)
                    description = description_match.group(1).strip()
                    event = {
                        'summary': description,
                        'start': {
                            'dateTime': f"{date}T{time_}:00",
                            'timeZone': 'UTC'
                        },
                        'end': {
                            'dateTime': f"{date}T{time_}:00",
                            'timeZone': 'UTC'
                        },
                    }
                else:
                    return jsonify({'error': 'Could not parse date/time/description from image'}), 400

            except Exception as ocr_err:
                print("OCR error:", ocr_err)
                return jsonify({'error': 'OCR failed'}), 400

        # --- Otherwise, expect form data or JSON ---
        else:
            data = request.get_json(silent=True) or request.form
            date = data.get('date')
            time_ = data.get('time')
            description = data.get('description')

            if not (date and time_ and description):
                return jsonify({'error': 'Missing fields: date, time, description'}), 400

            event = {
                'summary': description,
                'start': {
                    'dateTime': f"{date}T{time_}:00",
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': f"{date}T{time_}:00",
                    'timeZone': 'UTC'
                },
            }

        # --- Create the event in Google Calendar ---
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return jsonify({'success': True, 'eventLink': created_event.get('htmlLink')}), 200

    except Exception as e:
        print(f"Error creating event: {e}")
        return jsonify({'error': 'Enter all data!'}), 500


if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)