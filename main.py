from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timedelta
from cachetools import TTLCache
import requests
import spacy
import dateparser


nlp = spacy.load("en_core_web_trf")
app = Flask(__name__)
CORS(app)

# Cache setup: Cache up to 100 items, each item lives for 3600 seconds (1 hour)
cache = TTLCache(maxsize=100, ttl=3600)

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
    date_time, date_label = parse_date_from_input(user_input)
    weather_info = fetch_weather_data(city, date_time)

    if city:
        if "today" in user_input.lower() or "now" in user_input.lower():
            date_time = date_time.now()
        elif any(day in user_input.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
            date_time = parse_relative_weekday(user_input)
        elif date_text:
            date_time = parse_relative_date(date_text)
        else:
            date_time = datetime.now()


        if 'error' not in weather_info:
            if 'wind' in user_input.lower():
                response = get_wind_speed_response(weather_info, city, date_label)
            elif 'sun' in user_input.lower():
                response = get_sunny_response(weather_info, city, date_label)
            elif 'rain' in user_input.lower():
                response = get_rain_response(weather_info, city, date_label)
            elif 'snow' in user_input.lower():
                response = get_snow_response(weather_info, city, date_label)
            else:
                response = provide_general_weather_info(weather_info, city, date_label)
            return jsonify({'response': response})
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
    # Cache key'ini yalnızca tarihle oluştur
    cache_key = (city, date_time.strftime('%Y-%m-%d'))

    # Cache'den veri çekmeye çalış
    if cache_key in cache:
        print(f"Fetching weather data from cache for {city} on {date_time.strftime('%Y-%m-%d')}")
        return cache[cache_key]
    else:
        # Eğer cache'de yoksa, API'den veri çek
        return get_weather_data_from_api(city, date_time, cache_key)

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


def parse_date_from_input(user_input):
    if "today" in user_input:
        return datetime.now(), "today"
    elif "tomorrow" in user_input:
        return datetime.now() + timedelta(days=1), "tomorrow"
    else:
        # Dateparser kullanarak tarih çıkarımı yap
        parsed_date = dateparser.parse(user_input, settings={'DATE_ORDER': 'DMY'})
        if parsed_date:
            return parsed_date, parsed_date.strftime('%Y-%m-%d')
        else:
            return datetime.now(), "today"  # Eğer tarih belirtilmemişse today olarak kabul et
        

def check_weather_condition(weather_data, condition):
    """Belirtilen hava durumu koşulunu kontrol eder ve uygun cevap döndürür."""
    description = weather_data.get('weather_description', '').lower()
    return condition in description


def get_wind_speed_response(weather_data, city, date_label):
    return f"The wind in {city} is expected to be at {weather_data['wind_speed']} km/h on {date_label}."

def get_sunny_response(weather_data, city, date_label):
    if check_weather_condition(weather_data, 'clear'):
        return f"{date_label} in {city} is expected to be sunny."
    else:
        return f"{date_label} there is no sunny expected in {city}."

def get_rain_response(weather_data, city, date_label):
    if check_weather_condition(weather_data, 'rain'):
        return f"{date_label} in {city} is expected to be rainy."
    else:
        return f"{date_label} there is no rain expected in {city}."

def get_snow_response(weather_data, city, date_label):
    if check_weather_condition(weather_data, 'snow'):
        return f"{date_label} in {city} is expected to be snowy."
    else:
        return f"{date_label} there is no snow expected in {city}."

def provide_general_weather_info(weather_data, city, date_label):
    temperature = weather_data['current_temperature']
    wind_speed = weather_data['wind_speed']
    description = weather_data['weather_description'].capitalize()
    # Tarih etiketi, kullanıcı girdisine bağlı olarak "bugün", "yarın" veya spesifik bir tarih olabilir
    return f"Temperature {temperature}°C, wind speed {wind_speed} km/h and weather forecast in {city} from {date_label}: {description}."


if __name__ == '__main__':
    app.run(debug=True)

