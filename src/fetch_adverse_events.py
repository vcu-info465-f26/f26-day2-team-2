import requests


def get_adverse_events():
    url = "https://api.fda.gov/drug/event.json"

    params = {
        "limit": 5
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    print(data.keys())
    print(data["results"][0])

    return data["results"]


if __name__ == "__main__":
    get_adverse_events()