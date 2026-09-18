import requests


def fetch_adverse_events(limit=5):
    url = "https://api.fda.gov/drug/event.json"

    params = {
        "limit": limit
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    return data["results"]


def fetch_drug_labels(product_ndc="55910-518", limit=5):
    url = "https://api.fda.gov/drug/label.json"

    params = {
        "search": f'openfda.product_ndc:"{product_ndc}"',
        "limit": limit
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    return data["results"]


if __name__ == "__main__":
    events = fetch_adverse_events()

    print("ADVERSE EVENT SAMPLE:")
    print(events[0])

    labels = fetch_drug_labels()

    print("\nDRUG LABEL SAMPLE:")
    print(labels[0])