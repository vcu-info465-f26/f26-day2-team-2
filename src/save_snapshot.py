import json
import os
from datetime import date

import requests


def save_snapshot():
    url = "https://api.fda.gov/drug/event.json"

    params = {
        "limit": 5
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    # Create the data folder if it does not already exist
    os.makedirs("data", exist_ok=True)

    # Give today's snapshot its own filename
    filename = f"data/adverse_events_{date.today().isoformat()}.json"

    with open(filename, "w") as file:
        json.dump(data, file, indent=2)

    print(f"Snapshot saved to {filename}")


if __name__ == "__main__":
    save_snapshot()