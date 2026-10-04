import urllib.parse
import requests

def get_weather(city: str = "Jakarta") -> str:
    """
    Fetches real-time weather information for any city worldwide using Open-Meteo.
    """
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote_plus(city)}&count=1"
        geo_resp = requests.get(geo_url, timeout=6).json()
        if not geo_resp.get("results"):
            return f"Kota '{city}' tidak ditemukan. Coba sebutkan nama kota yang lebih spesifik."
        
        location = geo_resp["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        city_name = location["name"]
        country = location.get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
        w_data = requests.get(weather_url, timeout=6).json().get("current", {})

        temp = w_data.get("temperature_2m")
        feels_like = w_data.get("apparent_temperature")
        humidity = w_data.get("relative_humidity_2m")
        wind = w_data.get("wind_speed_10m")
        code = w_data.get("weather_code", 0)

        conditions = {
            0: "Cerah",
            1: "Cerah Berawan",
            2: "Berawan Sebagian",
            3: "Mendung (Overcast)",
            45: "Berkabut",
            48: "Kabut Tebal",
            51: "Gerimis Ringan",
            53: "Gerimis Sedang",
            55: "Gerimis Lebat",
            61: "Hujan Ringan",
            63: "Hujan Sedang",
            65: "Hujan Lebat",
            80: "Hujan Rintik",
            95: "Badai Petir (Thunderstorm)"
        }
        condition_str = conditions.get(code, "Cerah berawan")

        return (
            f"Cuaca di {city_name} ({country}):\n"
            f"- Kondisi: {condition_str}\n"
            f"- Suhu: {temp}°C (Terasa seperti {feels_like}°C)\n"
            f"- Kelembapan: {humidity}%\n"
            f"- Kecepatan Angin: {wind} km/jam"
        )
    except Exception as e:
        return f"Gagal mengambil informasi cuaca: {e}"
