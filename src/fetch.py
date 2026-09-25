import json
import os
from datetime import date
import requests


def first_value(value):
    if isinstance(value, list) and value:
        return value[0]
    return None


def fetch_enforcement():
    url = "https://api.fda.gov/drug/enforcement.json"

    params = {
        "search": "_exists_:openfda.product_ndc",
        "limit": 10
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    recalls = []

    for record in data["results"]:
        openfda = record.get("openfda", {})
        ndcs = openfda.get("product_ndc", [])

        if ndcs:
            recalls.append({
                "product_ndc": ndcs[0],
                "recall_number": record.get("recall_number"),
                "report_date": record.get("report_date"),
                "reason_for_recall": record.get("reason_for_recall")
            })

    return recalls


def fetch_labels(product_ndcs):
    url = "https://api.fda.gov/drug/label.json"
    drugs = []

    for ndc in product_ndcs:
        params = {
            "search": f'openfda.product_ndc:"{ndc}"',
            "limit": 1
        }

        response = requests.get(url, params=params)

        if response.status_code == 404:
            continue

        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            continue

        openfda = data["results"][0].get("openfda", {})

        drugs.append({
            "product_ndc": ndc,
            "brand_name": first_value(openfda.get("brand_name")),
            "generic_name": first_value(openfda.get("generic_name")),
            "manufacturer_name": first_value(
                openfda.get("manufacturer_name")
            )
        })

    return drugs


def save_json(filename, data):
    os.makedirs("data", exist_ok=True)

    with open(filename, "w") as file:
        json.dump(data, file, indent=2)


def main():
    today = date.today().isoformat()

    recalls = fetch_enforcement()

    enforcement_file = f"data/drug_enforcement_{today}.json"
    save_json(enforcement_file, recalls)

    print(f"Saved {enforcement_file}")
    print("Recall records:", len(recalls))

    ndcs = list({
        recall["product_ndc"]
        for recall in recalls
        if recall["product_ndc"]
    })

    drugs = fetch_labels(ndcs)

    labels_file = f"data/drug_labels_{today}.json"
    save_json(labels_file, drugs)

    print(f"Saved {labels_file}")
    print("Drug records:", len(drugs))

    print("\nShared product_ndc values:")

    drug_ndcs = {
        drug["product_ndc"]
        for drug in drugs
    }

    for ndc in ndcs:
        if ndc in drug_ndcs:
            print(ndc)


if __name__ == "__main__":
    main()