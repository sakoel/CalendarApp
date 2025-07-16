from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
import pysseract
from PIL import Image
import re
from googleapiclient.discovery import build
from google.oauth2 import credentials
import datetime
from google_auth_oauthlib.flow import Flow
import os

# TO ACTIVATE VENV:  source venv/bin/activate (Linux/Mac) or venv\Scripts\activate (Windows)
# TO DEACTIVATE VENV:  deactivate

app = Flask(__name__)
CORS(app)
app.secret_key = "super secret key"  # Change this in a real application!

# Configure Tesseract (replace with your actual path)
pysseract.tesseract_cmd = r'/usr/bin/tesseract'

# OAuth 2.0 Configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(script_dir, 'client_secret.json')
print(f"CLIENT_SECRETS_FILE: {CLIENT_SECRETS_FILE}")  # Debugging
SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = '/oauth2callback' #This is important for the route!

print("Current working directory:", os.getcwd())
print("Directory contents:", os.listdir())

def get_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)  # Use url_for
    )

@app.route('/api/authenticate')
def authenticate():
    flow = get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)


@app.route(REDIRECT_URI)  # OAuth 2.0 callback endpoint
def oauth2callback():
    state = session['state']
    flow = get_flow()

    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    try:
        with open('token.json', 'w') as token:
            token.write(creds.to_json()) #save tokens for further use
    except Exception as e:
        print("could not save token.json")
        return jsonify({"error":"could not save token.json, but calendar may still work."})

    session['credentials'] = creds.to_json()

    return jsonify({'message': "Authentication successful! You can now create calendar events."}) #or redirect to another page


def load_credentials():
    try:
        with open('token.json', 'r') as f:
            token_data = f.read()
        creds = credentials.Credentials.from_authorized_user_info(info=eval(token_data), scopes=SCOPES) #had to change the parsing to make it work.
        return creds
    except FileNotFoundError:
        print("Error: token.json file not found.  Please authenticate with Google Calendar API.")
        return None
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None


def create_calendar_event(date, description, creds): #had to add creds
    try:
        service = build('calendar', 'v3', credentials=creds) #had to add creds

        # Convert date string to datetime object
        event_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        start_time = datetime.datetime.combine(event_date, datetime.time(9, 0))  # Example: 9:00 AM
        end_time = datetime.datetime.combine(event_date, datetime.time(10, 0))  # Example: 10:00 AM

        event = {
            'summary': description,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Los_Angeles',  # Replace with your time zone
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Los_Angeles',  # Replace with your time zone
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
        return True, event.get('htmlLink')  # returns the link and true

    except Exception as e:
        print(f"Error creating event: {e}")
        return False, str(e)  # returns the error string and false


@app.route('/api/create_event', methods=['POST'])
def create_event():
    # Load credentials at the beginning of the function.
    creds = load_credentials()
    if not creds:
        return jsonify({'message': 'Event creation request failed!',
                        'error': "Could not authenticate with Google Calendar. Please authenticate first by going to /api/authenticate"}), 401

    # **Important:  Use request.form to access form data, and request.files to access files**

    # Handle Image Upload (if any)
    date = None  # Initializes date variable
    if 'image' in request.files:
        image = request.files['image']
        if image.filename != '':
            try:
                # Save the image
                image.save("temp_image.jpg")
                img = Image.open("temp_image.jpg")

                # Perform OCR
                text = pysseract.image_to_string(img)
                print(f"OCR Output: {text}")

                # Extract Date (using regex - adjust as needed)
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', text)
                if date_match:
                    date = date_match.group(0)
                else:
                    date = request.form.get('date')  # fallback to manually entered date
                    print("Date not found in OCR output - using manual date")
            except Exception as e:
                print(f"Error processing image: {e}")
                date = request.form.get('date')  # fallback to manually entered date
                print("Image processing error - using manual date")
        else:
            date = request.form.get('date')  # Use manual date if no image is uploaded
    else:
        date = request.form.get('date')  # Use manual date if no image is uploaded

    description = request.form.get('description')

    print(f"Received date: {date}")
    print(f"Received description: {description}")

    # Add your Google Calendar API integration here
    if creds:  # Only tries to create the event if the credentials have successfully been loaded.
        success, result = create_calendar_event(date, description, creds)  # call the function and record its success
        if success:
            return jsonify({'message': 'Event creation request received!', 'date': date, 'description': description,
                            "calendar_link": result}), 200  # return calendar_link
        else:
            return jsonify({'message': 'Event creation request failed!', 'error': result}), 500  # return the error message.
    else:
        return jsonify({'message': 'Event creation request failed!',
                        'error': "Could not authenticate with Google Calendar. Please authenticate first by going to /api/authenticate"}), 401


if __name__ == '__main__':
    app.run(debug=True)