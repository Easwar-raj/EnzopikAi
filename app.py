import os
import logging
from flask_cors import CORS
from flask import Flask, request, jsonify
from Chatbot_rag import generate_response
from googlemapsapicall import get_lat_long_google, vincenty_distance
from dotenv import load_dotenv

load_dotenv()

# ====================
# Logging Configuration
# ====================
logging.basicConfig(
    filename="carewell_chatbot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
)

app = Flask(__name__)
CORS(app)

api_key = os.getenv("GOOGLE_MAPS_API_KEY")


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data or "question" not in data or "role" not in data or "user_id" not in data or "user_name" not in data:
            app.logger.warning("Missing 'question', 'role', 'user_id', or 'user_name' in request")
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        question = data["question"].strip()
        if not question:
            app.logger.warning("Received empty question")
            return jsonify({"status": "error", "message": "Question cannot be empty"}), 400

        response = generate_response(question, data["role"], data["user_id"], data["user_name"])
        app.logger.info(f"Processed question: {question}")
        return jsonify({
            "status": "success",
            "response": response
        }), 200

    except Exception as e:
        app.logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "An error occurred while processing your request"
        }), 500


@app.route("/api/distance_calculation", methods=['POST'])
def _address_based_distance_calculation():
    try:
        data = request.get_json()
        if not data:
            app.logger.warning("Missing JSON data in distance calculation")
            return jsonify({'error': 'Invalid or missing JSON data'}), 400

        required_fields = ['latitude', 'longitude', 'registered_address']
        for field in required_fields:
            if field not in data:
                app.logger.warning(f"Missing field: {field}")
                return jsonify({'error': f'Missing Field: {field}'}), 400

        address = data['registered_address']
        lat2, lon2 = float(data['latitude']), float(data['longitude'])

        location = get_lat_long_google(address, api_key)
        app.logger.info(f"Geocoded address: {address} => {location}")

        if location:
            lat1 = location['latitude']
            lon1 = location['longitude']
            distance = vincenty_distance(lat1, lon1, lat2, lon2)
            threshold = 500

            app.logger.info(f"Distance between coordinates: {distance:.2f} meters")

            if distance < threshold:
                return jsonify({'status': 'success', 'message': f'Distance {distance:.2f} (Within threshold)'}), 200
            else:
                return jsonify({'status': 'success', 'message': f'Distance {distance:.2f} (Exceeds threshold)'}), 200
        else:
            app.logger.error(f"Failed to get location for address: {address}")
            return jsonify(location)

    except Exception as e:
        app.logger.error(f"Distance calculation error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == "__main__":
    app.run(threaded=True, host="0.0.0.0", port=5002)
