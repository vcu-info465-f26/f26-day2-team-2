import json
import sqlite3
from pathlib import Path


DATA_DIR = Path("data")
DB_PATH = Path("project.db")


def create_database():
    # Start fresh every time
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute("""
        CREATE TABLE drugs (
            product_ndc TEXT PRIMARY KEY,
            brand_name TEXT,
            generic_name TEXT,
            manufacturer_name TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE enforcement (
            recall_number TEXT NOT NULL,
            product_ndc TEXT NOT NULL,
            report_date TEXT,
            reason_for_recall TEXT,

            PRIMARY KEY (recall_number, product_ndc),

            FOREIGN KEY (product_ndc)
                REFERENCES drugs(product_ndc)
        )
    """)

    return conn


def load_drugs(conn):
    # Reads both drug_labels.json and dated drug_labels files
    files = sorted(DATA_DIR.glob("drug_labels*.json"))

    for file_path in files:
        with open(file_path, "r") as file:
            records = json.load(file)

        for record in records:
            conn.execute("""
                INSERT OR REPLACE INTO drugs (
                    product_ndc,
                    brand_name,
                    generic_name,
                    manufacturer_name
                )
                VALUES (?, ?, ?, ?)
            """, (
                record.get("product_ndc"),
                record.get("brand_name"),
                record.get("generic_name"),
                record.get("manufacturer_name")
            ))


def load_enforcement(conn):
    # Reads both drug_enforcement.json and dated files
    files = sorted(DATA_DIR.glob("drug_enforcement*.json"))

    for file_path in files:
        with open(file_path, "r") as file:
            records = json.load(file)

        for record in records:
            conn.execute("""
                INSERT OR IGNORE INTO enforcement (
                    recall_number,
                    product_ndc,
                    report_date,
                    reason_for_recall
                )
                VALUES (?, ?, ?, ?)
            """, (
                record.get("recall_number"),
                record.get("product_ndc"),
                record.get("report_date"),
                record.get("reason_for_recall")
            ))


def show_counts(conn):
    drug_count = conn.execute(
        "SELECT COUNT(*) FROM drugs"
    ).fetchone()[0]

    enforcement_count = conn.execute(
        "SELECT COUNT(*) FROM enforcement"
    ).fetchone()[0]

    print("Drug rows:", drug_count)
    print("Enforcement rows:", enforcement_count)


def main():
    conn = create_database()

    # Load drug table first because enforcement links to it
    load_drugs(conn)
    load_enforcement(conn)

    conn.commit()

    show_counts(conn)

    conn.close()

    print("Database built successfully.")


if __name__ == "__main__":
    main()