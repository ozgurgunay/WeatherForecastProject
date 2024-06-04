# Weather Chatbot Project - Weatherman App

## Overview

The **Weatherman App** is a weather chatbot that provides users with real-time weather forecasts based on their input. Users can ask questions about the weather for any city and specify a date, receiving detailed responses about current conditions, forecasts, and more.

This project is part of the course for my master's degree in Artificial Intelligence at IU of Aplied Sciences University. It demonstrates the practical application of various AI and web development technologies.

## Features

- **User Interaction:** Handles a variety of weather-related queries, such as current temperature, wind speed, and whether it will rain or snow.
- **City and Date Recognition:** Utilizes Natural Language Processing (NLP) with spaCy to extract city names and dates from user inputs.
- **Weather Data:** Fetches weather data using the OpenWeatherMap API, providing forecasts up to 5 days in advance.
- **Caching:** Implements TTLCache to store weather data temporarily, reducing API calls and improving response times.

## Technologies Used

- **Flask:** Lightweight WSGI web application framework used for server-side logic.
- **spaCy:** NLP library used for extracting entities from user input.
- **OpenWeatherMap API:** Weather data provider API used to fetch current and forecasted weather conditions.
- **TTLCache:** Caching mechanism to store weather data and reduce API calls.
- **Replit:** Platform used to deploy the chatbot.
- **Uptimerobot:** Service used to keep the application active and minimize downtime.
