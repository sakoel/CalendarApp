from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (for development)

@app.route('/api/create_event', methods=['POST'])
def create_event():
    data = request.get_json()  # Get the JSON data from the request
    date = data.get('date')  # Extract the date from the data
    description = data.get('description')  # Extract the description from the data

    print(f"Received date: {date}")  # Print the date to the console
    print(f"Received description: {description}")  # Print the description to the console

    #  Eventually, you'll add the Google Calendar API interaction here

    return jsonify({'message': 'Event creation request received!'}), 200  # Return a JSON response

if __name__ == '__main__':
    app.run(debug=True)  # Run the Flask app in debug mode