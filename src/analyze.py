import sqlite3


def main():
    conn = sqlite3.connect("project.db")

    query = """
        SELECT
            d.brand_name,
            d.generic_name,
            e.recall_number,
            e.report_date,
            e.reason_for_recall
        FROM enforcement e
        JOIN drugs d
            ON e.product_ndc = d.product_ndc
        ORDER BY e.report_date DESC
    """

    rows = conn.execute(query).fetchall()

    print("DRUG RECALL RESULTS")
    print("-" * 80)

    for brand, generic, recall, report_date, reason in rows:
        print(f"Brand: {brand}")
        print(f"Generic: {generic}")
        print(f"Recall number: {recall}")
        print(f"Report date: {report_date}")
        print(f"Reason: {reason}")
        print("-" * 80)

    conn.close()


if __name__ == "__main__":
    main()