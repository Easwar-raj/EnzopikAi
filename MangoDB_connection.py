from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient
import traceback
import pytz
import os

load_dotenv()


mongodb_connection = MongoClient(os.getenv("MONGODB_URL"), tls=True,
    tlsAllowInvalidCertificates=True)
db = mongodb_connection['carewell_chatbot_live']
Chatbot_history = db['chatbot_history']
ErrorHandling = db['error_handling']

def _CareWell_chatbot_history(data):
    try:
        ist_timezone = pytz.timezone('Asia/Kolkata')
        date_data = datetime.now(ist_timezone)
        date = date_data.strftime('%d-%m-%Y')
        time = date_data.strftime('%I:%M:%S %p')
        intent = data['intent']
        user_input = data['user_input']
        ai_response = data['ai_response']
        role = data['role']
        user_id = data['user_id']
        user_name = data['user_name']
        response_time = data['response_time']

        data = {
            "date": date,
            "time": time,
            "intent": intent,
            "user_input": user_input,
            "ai_response": ai_response,
            "role": role,
            "user_id": user_id,
            "user_name": user_name,
            "response_time": response_time
        }

        result = Chatbot_history.insert_many([data])

        return f"Successfully Inserted a Data {result.inserted_ids}"

    except Exception as e:
        Error_data = {
                "error_type" : type(e).__name__ ,
                "error_name" : e.__class__.__name__  ,
                "error_description" : str(e)  ,
                "error_traceback" : traceback.format_exc()
               }
        errorResult = ErrorHandling.insert_one(Error_data)

        return f"Successfully Inserted a error data {errorResult.inserted_id}"
    
def log_chatbot_error(exception: Exception) -> str:
    try:
        ist_timezone = pytz.timezone('Asia/Kolkata')
        date_data = datetime.now(ist_timezone)
        date = date_data.strftime('%d-%m-%Y')
        time = date_data.strftime('%I:%M:%S %p')

        error_data = {
            "date": date,
            "time": time,
            "error_type": type(exception).__name__,
            "error_name": exception.__class__.__name__,
            "error_description": str(exception),
            "error_traceback": traceback.format_exc()
        }

        error_result = ErrorHandling.insert_one(error_data)

        return f"Error Logged with ID: {error_result.inserted_id}"

    except Exception as log_error:
        return f"Failed to log error: {str(log_error)}"
