import requests


def get_adverse_events():
    url = "https://api.fda.gov/drug/event.json"

    params = {
        "limit": 100
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    for event in data["results"]:
        drugs = event.get("patient", {}).get("drug", [])

        for drug in drugs:
            openfda = drug.get("openfda", {})

            product_ndc = openfda.get("product_ndc")

            if product_ndc:
                print("FOUND MATCHABLE DRUG")
                print("product_ndc:", product_ndc[0])
                print("brand_name:", openfda.get("brand_name", [None])[0])
                print("generic_name:", openfda.get("generic_name", [None])[0])
                print("application_number:",
                      openfda.get("application_number", [None])[0])
                print("rxcui:", openfda.get("rxcui", [None])[0])

                return product_ndc[0]

    print("No product_ndc found.")
    return None


if __name__ == "__main__":
    get_adverse_events()