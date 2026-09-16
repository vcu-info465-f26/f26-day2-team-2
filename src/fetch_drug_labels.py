import requests


def get_drug_label():
    url = "https://api.fda.gov/drug/label.json"

    params = {
        "search": 'openfda.product_ndc:"55910-518"',
        "limit": 1
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    result = data["results"][0]
    openfda = result.get("openfda", {})

    print("MATCH FOUND")
    print("product_ndc:", openfda.get("product_ndc"))
    print("brand_name:", openfda.get("brand_name"))
    print("generic_name:", openfda.get("generic_name"))
    print("application_number:", openfda.get("application_number"))
    print("rxcui:", openfda.get("rxcui"))

    return result


if __name__ == "__main__":
    get_drug_label()