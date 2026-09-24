import json
import os
import requests


def first_value(value):
    if isinstance(value, list) and value:
        return value[0]
    return None


def fetch_enforcement():
    """Endpoint 1: Get a small set of drug recall records."""

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
        product_ndcs = openfda.get("product_ndc", [])

        if product_ndcs:
            recalls.append({
                "recall_number": record.get("recall_number"),
                "report_date": record.get("report_date"),
                "reason_for_recall": record.get("reason_for_recall"),
                "product_ndc": product_ndcs[0]
            })

    return recalls


def fetch_labels(product_ndcs):
    """Endpoint 2: Get drug information for the recall NDCs."""

    url = "https://api.fda.gov/drug/label.json"

    drugs = []

    for ndc in product_ndcs:

        params = {
            "search": f'openfda.product_ndc:"{ndc}"',
            "limit": 1
        }

        response = requests.get(url, params=params)

        # Skip NDCs that do not have a matching label
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

    # Endpoint 1: Drug Enforcement / Recalls
    recalls = fetch_enforcement()

    save_json(
        "data/drug_enforcement.json",
        recalls
    )

    print("Saved data/drug_enforcement.json")
    print("Recall records:", len(recalls))

    # Get the product_ndc values from the recall data
    ndcs = list({
        recall["product_ndc"]
        for recall in recalls
        if recall["product_ndc"]
    })

    # Endpoint 2: Drug Labels
    drugs = fetch_labels(ndcs)

    save_json(
        "data/drug_labels.json",
        drugs
    )

    print("Saved data/drug_labels.json")
    print("Drug records:", len(drugs))

    # Prove the two files share product_ndc values
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