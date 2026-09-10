import requests


def get_forecast():
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": 37.5407,
        "longitude": -77.4360,
        "hourly": "temperature_2m,relative_humidity_2m",
        "timezone": "auto"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    print(data.keys())
    print(data["hourly"])

    return data["hourly"]


if __name__ == "__main__":
    get_forecast()