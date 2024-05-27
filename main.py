from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from datetime import datetime, timedelta
from cachetools import TTLCache
import requests
import spacy
import dateparser
import secrets


nlp = spacy.load("en_core_web_trf")
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)
# Cache setup: Cache up to 100 items, each item lives for 3600 seconds (1 hour)
cache = TTLCache(maxsize=100, ttl=3600)
# OpenWeatherMap API key
API_KEY = "8e0f7c46028954888f028cda9d2566ae"

# Serve the main page
@app.route('/')
def index():
    return render_template('index.html')

# Route to get a time-sensitive greeting
@app.route('/get_greeting')
def get_greeting():
    greeting = get_time_sensitive_greeting()
    return jsonify({'greeting': greeting})

# Generate a greeting based on the current time
def get_time_sensitive_greeting():
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        greeting = "Good morning!"
    elif 12 <= current_hour < 18:
        greeting = "Good afternoon!"
    else:
        greeting = "Good evening!"
    return greeting + " How can I assist you with the weather today?"

# Handle POST requeests with user input
@app.route("/handle_data", methods=["POST"])
def handle_data_post():
    """Handles POST request for user input and calls handle_data()."""
    data = request.get_json(force=True)
    if not data or 'chat-input' not in data:
        return jsonify({'error': 'Bad Request, invalid JSON or missing key'}), 400
    user_input = data['chat-input']
    response = handle_data(user_input)
    session['last_input'] = user_input
    return response

# Process user input to extract city and date, and fetch weather information
def handle_data(user_input):
    """Handles user input, extracts city and date, and fetches weather if applicable."""
    # city, date_text = extract_city_and_date(user_input)
    intent, entities = parse_input(user_input)
    city = entities.get('city', session.get('last_city'))
    date_text = entities.get('date_text')

    if not city:
        # If there is no city information and no city is stored in the session, ask the user for city information
        return jsonify({"message": "Please specify a location for weather information."})

    date_time, date_label = parse_date_from_input(user_input, date_text)
    weather_info = fetch_weather_data(city, date_time)
   
    if "today" in user_input.lower() or "now" in user_input.lower():
        date_time = date_time.now()
    elif any(day in user_input.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
        date_time = parse_relative_weekday(user_input)
    elif date_text:
        date_time = parse_relative_date(date_text)
    else:
        date_time = datetime.now()

    session['last_city'] = city # Store the updated city in the session
    if 'error' not in weather_info:
        return handle_weather_response(weather_info, city, date_label, user_input)
    else:
        return jsonify(weather_info), 400        
   
# Generate appropriate weather response based on user input
def handle_weather_response(weather_info, city, date_label, user_input):
    """Generates appropriate weather response based on user input."""
    if 'temperature' in user_input.lower() or 'temp' in user_input.lower() or 'hot' in user_input.lower() or 'cold' in user_input.lower():
        response = get_temperature_response(weather_info, city, date_label)
    elif 'wind' in user_input.lower():
        response = get_wind_speed_response(weather_info, city, date_label)
    elif 'sun' in user_input.lower():
        response = get_sunny_response(weather_info, city, date_label)
    elif 'rain' in user_input.lower():
        response = get_rain_response(weather_info, city, date_label)
    elif 'snow' in user_input.lower():
        response = get_snow_response(weather_info, city, date_label)
    elif 'cloud' in user_input.lower():
        response = get_cloud_response(weather_info, city, date_label)
    else:
        response = provide_general_weather_info(weather_info, city, date_label)
    return jsonify({'response': response})

# Parse user input to find the next occurrence of a specified weekday
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

# Find the next occurrence of a given weekday from a datetime object
def next_weekday(d, weekday):
    """Given a datetime `d`, finds the next occurrence of `weekday`."""
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + timedelta(days_ahead)

# Fetch weather data, using cache if available
def fetch_weather_data(city, date_time=None):
    # Create the cache key using only the date
    cache_key = (city, date_time.strftime('%Y-%m-%d'))

    # Try to fetch data from the cache
    if cache_key in cache:
        print(f"Fetching weather data from cache for {city} on {date_time.strftime('%Y-%m-%d')}")
        return cache[cache_key]
    else:
        # If not in cache, fetch data from the API
        return get_weather_data_from_api(city, date_time, cache_key)

# Fetch weather data from the API and store it in the cache
def get_weather_data_from_api(city, date_time, cache_key):
    geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
    geocode_response = requests.get(geocode_url)
    if geocode_response.status_code == 200:
        location_data = geocode_response.json()[0]
        lat, lon = location_data["lat"], location_data["lon"]

        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        response = requests.get(forecast_url)
        if response.status_code == 200:
            weather_data = process_forecast_data(response.json(), city, date_time)
            cache[cache_key] = weather_data
            return weather_data
        else:
            return {'error': 'Failed to retrieve forecast data'}, response.status_code
    else:
        return {'error': 'Failed to retrieve location data'}, geocode_response.status_code

# Process forecast data to find the closest match to the target date
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

# Parse user input to extract intent and entities
def parse_input(user_input):
    doc = nlp(user_input)
    intent = None
    entities = {}
    for ent in doc.ents:
        if ent.label_ == "GPE":
            entities['city'] = ent.text.title()
            intent = "weather_inquiry"
        elif ent.label_ == "DATE":
            entities['date_text'] = ent.text
    return intent, entities

# Parse a relative date from text using dateparser
def parse_relative_date(text):
    if text:
        return dateparser.parse(text, settings={'DATE_ORDER': 'MDY', 'PREFER_DAY_OF_MONTH': 'first'})
    return datetime.now()

# Parse a date from user input, considering various keywords and formats
def parse_date_from_input(user_input, date_text=None):
    if "today" in user_input.lower() or "now" in user_input.lower():
        return datetime.now(), "today"
    elif "tomorrow" in user_input.lower():
        return datetime.now() + timedelta(days=1), "tomorrow"
    elif any(day in user_input.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
        target_date = parse_relative_weekday(user_input)
        return target_date, target_date.strftime('%A')
    elif date_text:
        parsed_date = dateparser.parse(date_text, settings={'DATE_ORDER': 'DMY'})
        if parsed_date:
            return parsed_date, parsed_date.strftime('%Y-%m-%d')
        else:
            return datetime.now(), "today"
    else:
        return datetime.now(), "today"   

# Check if the weather data contains a specific condition
def check_weather_condition(weather_data, condition):
    """Check for a specified weather condition and return an appropriate response."""
    description = weather_data.get('weather_description', '').lower()
    return condition in description

# Generate a response for wind speed
def get_wind_speed_response(weather_data, city, date_label):
    return f"The wind in {city} is expected to be at {weather_data['wind_speed']} km/h on {date_label}."

# Generate a response for temperature
def get_temperature_response(weather_data, city, date_label):
    temperature = weather_data['current_temperature']
    return f"The temperature in {city} on {date_label} is expected to be {temperature}°C."

# Generate a response for sunny weather
def get_sunny_response(weather_data, city, date_label):
    if check_weather_condition(weather_data, 'clear'):
        return f"{date_label} in {city} is expected to be sunny."
    else:
        return f"{date_label} there is no sunny expected in {city}."

# Generate a response for rainy weather
def get_rain_response(weather_data, city, date_label):
    if check_weather_condition(weather_data, 'rain'):
        return f"{date_label} in {city} is expected to be rainy."
    else:
        return f"{date_label} there is no rain expected in {city}."

# Generate a response for snowy weather
def get_snow_response(weather_data, city, date_label):
    if check_weather_condition(weather_data, 'snow'):
        return f"{date_label} in {city} is expected to be snowy."
    else:
        return f"{date_label} there is no snow expected in {city}."

# Generate a response for cloudy weather    
def get_cloud_response(weather_data, city, date_label):
    if check_weather_condition(weather_data, 'cloud'):
        return f"{date_label} in {city} is expected to be cloudy."
    else:
        return f"{date_label} there is no cloud expected in {city}."

# Provide general weather information
def provide_general_weather_info(weather_data, city, date_label):
    temperature = weather_data['current_temperature']
    wind_speed = weather_data['wind_speed']
    description = weather_data['weather_description'].capitalize()
    return f"Temperature {temperature}°C, wind speed {wind_speed} km/h and weather forecast in {city} from {date_label}: {description}."


if __name__ == '__main__':
    app.run(debug=True)

