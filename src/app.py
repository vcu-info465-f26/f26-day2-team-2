from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st

from build_db import build


# Build the database if it does not exist
if not Path("project.db").exists():
    build()


st.title("FDA Drug Recall Dashboard")
st.write("Most recently reported FDA drug recalls")


conn = sqlite3.connect("project.db")

query = """
SELECT
    e.report_date,
    d.brand_name,
    d.generic_name,
    d.manufacturer_name,
    e.recall_number,
    e.reason_for_recall
FROM enforcement e
LEFT JOIN drugs d
    ON e.product_ndc = d.product_ndc
ORDER BY e.report_date DESC
"""

df = pd.read_sql_query(query, conn)
conn.close()


# Make dates easier to read
df["report_date"] = pd.to_datetime(
    df["report_date"],
    format="%Y%m%d"
).dt.strftime("%m/%d/%Y")


# Make column names easier to read
df = df.rename(columns={
    "report_date": "Report Date",
    "brand_name": "Drug Name",
    "generic_name": "Generic Name",
    "manufacturer_name": "Manufacturer",
    "recall_number": "Recall Number",
    "reason_for_recall": "Reason for Recall"
})


st.subheader("Most Recent Drug Recalls")

display_df = df[
    [
        "Report Date",
        "Drug Name",
        "Manufacturer",
        "Reason for Recall"
    ]
]

st.dataframe(
    display_df,
    width="stretch",
    hide_index=True
)
