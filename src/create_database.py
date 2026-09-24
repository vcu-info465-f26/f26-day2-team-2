import json
import sqlite3


# Create/connect to the SQLite database
connection = sqlite3.connect("data/drugs.db")
cursor = connection.cursor()


# Create the DRUGS table
cursor.execute("""
CREATE TABLE IF NOT EXISTS drugs (
    product_ndc TEXT PRIMARY KEY,
    brand_name TEXT,
    generic_name TEXT
)
""")


# Create the ENFORCEMENT table
cursor.execute("""
CREATE TABLE IF NOT EXISTS enforcement (
    product_ndc TEXT,
    recall_number TEXT,
    report_date TEXT,
    reason_for_recall TEXT
)
""")


# Load drug label data
with open("data/drug_labels.json", "r") as file:
    drugs = json.load(file)


# Insert drug label data
for drug in drugs:
    cursor.execute("""
    INSERT OR REPLACE INTO drugs
    (product_ndc, brand_name, generic_name)
    VALUES (?, ?, ?)
    """, (
        drug.get("product_ndc"),
        drug.get("brand_name"),
        drug.get("generic_name")
    ))


# Load enforcement data
with open("data/drug_enforcement.json", "r") as file:
    recalls = json.load(file)


# Insert enforcement data
for recall in recalls:
    cursor.execute("""
    INSERT INTO enforcement
    (product_ndc, recall_number, report_date, reason_for_recall)
    VALUES (?, ?, ?, ?)
    """, (
        recall.get("product_ndc"),
        recall.get("recall_number"),
        recall.get("report_date"),
        recall.get("reason_for_recall")
    ))


# Save the database
connection.commit()


# Close the database
connection.close()

print("SQLite database created successfully!")