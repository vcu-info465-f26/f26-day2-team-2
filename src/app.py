import sqlite3

import pandas as pd
import streamlit as st

st.title("FDA Drug Recalls")


# ---------- Story 4 (#32): label and enforcement data combined ----------

def load_combined_data():
    """Join drug labels to recalls so each recall shows its drug name and maker."""
    conn = sqlite3.connect("project.db")
    query = """
        SELECT
            d.brand_name,
            d.generic_name,
            d.manufacturer_name,
            e.recall_number,
            e.report_date,
            e.reason_for_recall
        FROM enforcement e
        JOIN drugs d
            ON e.product_ndc = d.product_ndc
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Dates are stored as text like "20240103". Convert them to real dates
    # so they sort by time instead of alphabetically.
    df["report_date"] = pd.to_datetime(df["report_date"], format="%Y%m%d")

    return df.sort_values("report_date", ascending=False)


def show_combined_table(df):
    """Show the combined table. Takes df as input so a filter can pass in filtered rows."""
    st.subheader("Recalls with drug label details")
    st.dataframe(
        df.rename(columns={
            "brand_name": "Brand",
            "generic_name": "Generic name",
            "manufacturer_name": "Manufacturer",
            "recall_number": "Recall #",
            "report_date": "Report date",
            "reason_for_recall": "Reason for recall",
        }),
        hide_index=True,
    )


# ---------- Page ----------

df = load_combined_data()
show_combined_table(df)