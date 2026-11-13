import json
import sqlite3
from pathlib import Path


def find_data_dir():
    here = Path(__file__).resolve().parent
    for candidate in (Path("data"), here / "data", here.parent / "data"):
        if candidate.is_dir():
            return candidate
    return Path("data")


DATA_DIR = find_data_dir()
DB_PATH = Path("project.db")


# ---------- helpers ----------

def as_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "")]
    return [value]


def first(value):
    items = as_list(value)
    return items[0] if items else None


def get_field(record, name):
    """Top-level field first, then the nested openfda object."""
    value = first(record.get(name))
    if value is None:
        value = first((record.get("openfda") or {}).get(name))
    return value


def get_ndcs(record):
    ndcs = as_list(record.get("product_ndc"))
    if not ndcs:
        ndcs = as_list((record.get("openfda") or {}).get("product_ndc"))
    return ndcs


def normalize_date(value):
    if value is None:
        return None
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():  # 20250416 -> 2025-04-16
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def read_records(path):
    """Handles a list, {"results": [...]}, a single record, or JSON lines."""
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in text.splitlines() if line.strip()]

    if isinstance(data, dict):
        if isinstance(data.get("results"), list):
            data = data["results"]
        else:
            data = [data]
    return [r for r in data if isinstance(r, dict)]


# ---------- database ----------

def create_database():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE drugs (
            product_ndc TEXT PRIMARY KEY,
            brand_name TEXT,
            generic_name TEXT,
            manufacturer_name TEXT
        )
    """)

    # No foreign key and no NOT NULL on the NDC, so no recall is ever dropped
    conn.execute("""
        CREATE TABLE enforcement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recall_number TEXT NOT NULL,
            product_ndc TEXT NOT NULL DEFAULT 'UNKNOWN',
            report_date TEXT,
            reason_for_recall TEXT,
            recalling_firm TEXT,
            product_description TEXT NOT NULL DEFAULT '',
            classification TEXT,
            status TEXT,
            UNIQUE (recall_number, product_ndc, product_description)
        )
    """)
    return conn


def load_drugs(conn):
    files = sorted(DATA_DIR.glob("*label*.json"))
    if not files:
        print("WARNING: no *label*.json files found in", DATA_DIR.resolve())

    skipped = 0
    for file_path in files:
        records = read_records(file_path)
        print(f"{file_path.name}: {len(records)} drug records read")

        for record in records:
            ndcs = get_ndcs(record)
            if not ndcs:
                skipped += 1
                continue

            for ndc in ndcs:  # one row per NDC
                conn.execute("""
                    INSERT OR REPLACE INTO drugs
                        (product_ndc, brand_name, generic_name, manufacturer_name)
                    VALUES (?, ?, ?, ?)
                """, (
                    ndc,
                    get_field(record, "brand_name"),
                    get_field(record, "generic_name"),
                    get_field(record, "manufacturer_name"),
                ))

    print(f"Drug records skipped (no NDC anywhere): {skipped}")


def load_enforcement(conn):
    files = sorted(DATA_DIR.glob("*enforcement*.json"))
    if not files:
        print("WARNING: no *enforcement*.json files found in", DATA_DIR.resolve())

    read = inserted = duplicates = no_ndc = skipped = 0

    for file_path in files:
        records = read_records(file_path)
        print(f"{file_path.name}: {len(records)} enforcement records read")

        for record in records:
            read += 1
            recall_number = record.get("recall_number")
            if not recall_number:
                skipped += 1
                continue

            ndcs = get_ndcs(record)
            ndc = ndcs[0] if ndcs else "UNKNOWN"
            if not ndcs:
                no_ndc += 1

            brand_name = get_field(record, "brand_name")
            generic_name = get_field(record, "generic_name")
            manufacturer_name = get_field(record, "manufacturer_name")
            if any((brand_name, generic_name, manufacturer_name)):
                conn.execute("""
                    INSERT INTO drugs
                        (product_ndc, brand_name, generic_name, manufacturer_name)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(product_ndc) DO UPDATE SET
                        brand_name = COALESCE(excluded.brand_name, drugs.brand_name),
                        generic_name = COALESCE(excluded.generic_name, drugs.generic_name),
                        manufacturer_name = COALESCE(
                            excluded.manufacturer_name,
                            drugs.manufacturer_name
                        )
                """, (ndc, brand_name, generic_name, manufacturer_name))

            cursor = conn.execute("""
                INSERT OR IGNORE INTO enforcement
                    (recall_number, product_ndc, report_date, reason_for_recall,
                     recalling_firm, product_description, classification, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recall_number,
                ndc,
                normalize_date(record.get("report_date")),
                first(record.get("reason_for_recall")),
                first(record.get("recalling_firm")),
                first(record.get("product_description")) or "",
                first(record.get("classification")),
                first(record.get("status")),
            ))
            if cursor.rowcount:
                inserted += 1
            else:
                duplicates += 1

    print(f"Enforcement records read: {read}")
    print(f"Enforcement rows inserted: {inserted}")
    print(f"Duplicates ignored (overlapping files): {duplicates}")
    print(f"Records with no NDC (kept as UNKNOWN): {no_ndc}")
    print(f"Records skipped (no recall_number): {skipped}")


def show_counts(conn):
    q = lambda sql: conn.execute(sql).fetchone()
    print("Drug rows:", q("SELECT COUNT(*) FROM drugs")[0])
    print("Enforcement rows:", q("SELECT COUNT(*) FROM enforcement")[0])
    print("Enforcement rows with no matching drug:", q("""
        SELECT COUNT(*) FROM enforcement e
        LEFT JOIN drugs d ON e.product_ndc = d.product_ndc
        WHERE d.product_ndc IS NULL
    """)[0])
    lo, hi = q("SELECT MIN(report_date), MAX(report_date) FROM enforcement")
    print("Report dates:", lo, "to", hi)


def build():
    print("Data folder:", DATA_DIR.resolve())
    print("JSON files found:", [p.name for p in sorted(DATA_DIR.glob("*.json"))])

    conn = create_database()
    load_drugs(conn)
    load_enforcement(conn)
    conn.commit()
    show_counts(conn)
    conn.close()

    print("Database built successfully:", DB_PATH.resolve())


if __name__ == "__main__":
    build()