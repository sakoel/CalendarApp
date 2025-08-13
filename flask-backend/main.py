from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
import pytesseract
from PIL import Image
import re
from googleapiclient.discovery import build
from google.oauth2 import credentials
from google_auth_oauthlib.flow import Flow
import datetime
import os
import requests
import json

# --- Configuration ---
app = Flask(__name__)
CORS(app)
app.secret_key = "super secret key"  # Change this in production!

# Tesseract OCR path (update for Windows if needed)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
# Example for Windows:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# OAuth2 Configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(script_dir, 'client_secret.json')
SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = 'https://calendarapp-9jvu.onrender.com/oauth2callback'
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://calendar-app-henna-five.vercel.app/")

def get_flow(redirect_uri):
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

@app.route('/api/authenticate')
def authenticate():
    redirect_uri = url_for('oauth2callback', _external=True)
    flow = get_flow(redirect_uri)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    print(f"Authorization URL: {authorization_url}")
    return redirect(authorization_url)

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
    try:
        with open('token.json', 'r') as f:
            token_data = f.read()
        creds = credentials.Credentials.from_authorized_user_info(
            info=eval(token_data), scopes=SCOPES
        )
        return creds
    except FileNotFoundError:
        print("Error: token.json file not found. Please authenticate with Google Calendar API.")
        return None
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def create_calendar_event(date, description, creds):
    try:
        service = build('calendar', 'v3', credentials=creds)
        event_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        start_time = datetime.datetime.combine(event_date, datetime.time(9, 0))
        end_time = datetime.datetime.combine(event_date, datetime.time(10, 0))
        event = {
            'summary': description,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
        return True, event.get('htmlLink')
    except Exception as e:
        print(f"Error creating event: {e}")
        return False, str(e)
    
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
        # Just redirect to your frontend (not Google's logout)
        return redirect(FRONTEND_URL)
    except Exception as e:
        print(f"Error during logout: {e}")
        return jsonify({'error': 'Logout failed!'}), 500

@app.route('/api/create_event', methods=['POST'])
def create_event():
    creds = load_credentials()
    if not creds:
        return jsonify({
            'message': 'Event creation request failed!',
            'error': "Could not authenticate with Google Calendar. Please authenticate first by going to /api/authenticate"
        }), 401

    # Handle image upload and OCR
    date = None
    if 'image' in request.files:
        image = request.files['image']
        if image.filename != '':
            try:
                image.save("temp_image.jpg")
                img = Image.open("temp_image.jpg")
                text = pytesseract.image_to_string(img)
                print(f"OCR Output: {text}")
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', text)
                if date_match:
                    date = date_match.group(0)
                else:
                    date = request.form.get('date')
                    print("Date not found in OCR output - using manual date")
            except Exception as e:
                print(f"Error processing image: {e}")
                date = request.form.get('date')
                print("Image processing error - using manual date")
        else:
            date = request.form.get('date')
    else:
        date = request.form.get('date')

    description = request.form.get('description')
    print(f"Received date: {date}")
    print(f"Received description: {description}")

    success, result = create_calendar_event(date, description, creds)
    if success:
        return jsonify({
            'message': 'Event creation request received!',
            'date': date,
            'description': description,
            "calendar_link": result
        }), 200
    else:
        return jsonify({
            'message': 'Event creation request failed!',
            'error': result
        }), 500

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)