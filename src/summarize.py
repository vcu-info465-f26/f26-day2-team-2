import os
import sqlite3
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from build_db import build


DB_PATH = Path("project.db")
SUMMARY_PATH = Path("data/summary.md")
MODEL = "openai/gpt-oss-120b"


def format_date(value):
    if not value:
        return "Unknown"

    try:
        return datetime.strptime(str(value), "%Y%m%d").strftime("%B %d, %Y")
    except ValueError:
        return str(value)


def get_facts():
    if not DB_PATH.exists():
        build()

    conn = sqlite3.connect(DB_PATH)

    total_recalls = conn.execute(
        "SELECT COUNT(*) FROM enforcement"
    ).fetchone()[0]

    manufacturer_count = conn.execute(
        """
        SELECT COUNT(DISTINCT d.manufacturer_name)
        FROM enforcement e
        LEFT JOIN drugs d
            ON e.product_ndc = d.product_ndc
        WHERE d.manufacturer_name IS NOT NULL
        """
    ).fetchone()[0]

    first_date, latest_date = conn.execute(
        """
        SELECT MIN(report_date), MAX(report_date)
        FROM enforcement
        """
    ).fetchone()

    top_manufacturer = conn.execute(
        """
        SELECT d.manufacturer_name, COUNT(*) AS recall_count
        FROM enforcement e
        LEFT JOIN drugs d
            ON e.product_ndc = d.product_ndc
        WHERE d.manufacturer_name IS NOT NULL
        GROUP BY d.manufacturer_name
        ORDER BY recall_count DESC
        LIMIT 1
        """
    ).fetchone()

    conn.close()

    if top_manufacturer:
        top_name = top_manufacturer[0]
        top_count = top_manufacturer[1]
    else:
        top_name = "Unknown"
        top_count = 0

    return {
        "total_recalls": total_recalls,
        "manufacturer_count": manufacturer_count,
        "first_date": format_date(first_date),
        "latest_date": format_date(latest_date),
        "top_manufacturer": top_name,
        "top_manufacturer_recalls": top_count,
    }


def generate_summary():
    facts = get_facts()

    prompt = f"""
You are writing a short summary for an FDA drug recall dashboard.

Use ONLY the facts below. Do not guess or add outside information.

Total recall records: {facts["total_recalls"]}
Number of manufacturers: {facts["manufacturer_count"]}
Data date range: {facts["first_date"]} to {facts["latest_date"]}
Manufacturer with the most recall records: {facts["top_manufacturer"]}
Recall records for that manufacturer: {facts["top_manufacturer_recalls"]}

Write a clear 2-3 sentence summary for someone who knows nothing about the project.
"""

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ["GROQ_API_KEY"],
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        reasoning_effort="low",
    )

    summary = response.choices[0].message.content.strip()

    new_content = (
        "# FDA Drug Recall Summary\n\n"
        f"**Data range:** {facts['first_date']} to {facts['latest_date']}\n\n"
        f"{summary}\n"
    )

    SUMMARY_PATH.parent.mkdir(exist_ok=True)
    SUMMARY_PATH.write_text(new_content, encoding="utf-8")

    print("Summary saved to data/summary.md")
    print(summary)


if __name__ == "__main__":
    try:
        generate_summary()
    except Exception as error:
        print(f"Summary generation failed: {error}")
        print("Existing summary.md was not changed.")
