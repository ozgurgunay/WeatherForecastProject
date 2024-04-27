from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timedelta
import requests
import spacy
import dateparser


nlp = spacy.load("en_core_web_trf")
app = Flask(__name__)
CORS(app)

# OpenWeatherMap API key
API_KEY = "8e0f7c46028954888f028cda9d2566ae"

# Ensure this route is defined to serve your main page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_greeting')
def get_greeting():
    greeting = get_time_sensitive_greeting()
    return jsonify({'greeting': greeting})

def get_time_sensitive_greeting():
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        greeting = "Good morning!"
    elif 12 <= current_hour < 18:
        greeting = "Good afternoon!"
    else:
        greeting = "Good evening!"
    return greeting + " How can I assist you with the weather today?"

@app.route("/handle_data", methods=["POST"])
def handle_data_post():
    """Handles POST request for user input and calls handle_data()."""
    data = request.get_json(force=True)
    if not data or 'chat-input' not in data:
        return jsonify({'error': 'Bad Request, invalid JSON or missing key'}), 400
    user_input = data['chat-input']
    return handle_data(user_input)


def handle_data(user_input):
    """Handles user input, extracts city and date, and fetches weather if applicable."""
    city, date_text = extract_city_and_date(user_input)
    if city:
        if "today" in user_input.lower() or "now" in user_input.lower():
            date_time = date_time.now()
        elif any(day in user_input.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
            date_time = parse_relative_weekday(user_input)
        elif date_text:
            date_time = parse_relative_date(date_text)
        else:
            date_time = datetime.now()

        # date_time = parse_relative_date(date_text) if date_text else datetime.now()
        weather_info = fetch_weather_data(city, date_time)
        if 'error' not in weather_info:
            return jsonify(weather_info)
        else:
            return jsonify(weather_info), 400
    else:
        return jsonify({"message": "Please specify a location for weather information."})


def parse_relative_weekday(user_input):
    """Finds the next occurrence of the specified weekday from user input."""
    today = datetime.now()
    weekdays = {
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
        'saturday': 5,
        'sunday': 6
    }
    
    for day, day_index in weekdays.items():
        if day in user_input.lower():
            return next_weekday(today, day_index)
    
    return today  # Default to today if no weekday is found


def next_weekday(d, weekday):
    """Given a datetime `d`, finds the next occurrence of `weekday`."""
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + timedelta(days_ahead)



def fetch_weather_data(city, date_time=None):
    geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
    geocode_response = requests.get(geocode_url)
    if geocode_response.status_code == 200:
        location_data = geocode_response.json()[0]
        lat, lon = location_data["lat"], location_data["lon"]

        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        response = requests.get(forecast_url)
        if response.status_code == 200:
            return process_forecast_data(response.json(), city, date_time)
        else:
            return {'error': 'Failed to retrieve forecast data'}, response.status_code
    else:
        return {'error': 'Failed to retrieve location data'}, geocode_response.status_code


def process_forecast_data(forecast_data, city, target_date):
    forecast_list = forecast_data['list']
    closest_forecast = None
    for forecast in forecast_list:
        forecast_time = datetime.utcfromtimestamp(forecast['dt'])
        if not closest_forecast or abs((target_date - forecast_time).total_seconds()) < abs((target_date - datetime.utcfromtimestamp(closest_forecast['dt'])).total_seconds()):
            closest_forecast = forecast
    if closest_forecast:
        return {
            "city": city,
            "current_temperature": closest_forecast['main']['temp'],
            "wind_speed": closest_forecast['wind']['speed'],
            "weather_description": closest_forecast['weather'][0]['description'],
            "forecast_time": datetime.utcfromtimestamp(closest_forecast['dt']).strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        return {"message": "No forecast available for the requested date"}



def determine_weather_condition(description):
    if "Rain" in description:
        return "Rainy"
    elif "Snow" in description:
        return "Snowy"
    elif "Clouds" in description:
        return "Cloudy"
    else:
        return "Clear"


def extract_city_and_date(user_input):
    """Uses NLP to extract a city name from user input, identifying geographical entities."""
    # Return the city name with proper capitalization .title()
    doc = nlp(user_input.title())
    city = None
    date_text = None
    for ent in doc.ents:
        if ent.label_ == "GPE":
            city = ent.text.title()
        elif ent.label_ == "DATE":
            date_text = ent.text

    return city, date_text
    

def parse_relative_date(text):
    if text:
        return dateparser.parse(text, settings={'DATE_ORDER': 'MDY', 'PREFER_DAY_OF_MONTH': 'first'})
    return datetime.now()



if __name__ == '__main__':
    app.run(debug=True)

