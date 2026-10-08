import sqlite3

import pandas as pd
import streamlit as st
from pathlib import Path
from build_db import build

DB_PATH = "project.db"
if not Path(DB_PATH).exists():
    build()

st.set_page_config(
    page_title="FDA Drug Recall Dashboard",
    page_icon="💊",
    layout="wide",
)


def load_data():
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            d.brand_name,
            d.generic_name,
            d.manufacturer_name,
            e.recall_number,
            e.report_date,
            e.reason_for_recall
        FROM enforcement AS e
        JOIN drugs AS d
            ON e.product_ndc = d.product_ndc
        ORDER BY e.report_date
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    if not df.empty:
        df["report_date"] = pd.to_datetime(
            df["report_date"],
            errors="coerce",
        )

    return df


def show_combined_table(df):
    """Show recalls joined with their drug label details, newest first.

    Takes a dataframe as input, so the manufacturer filter's rows pass straight in.
    """
    st.subheader("Recalls with Drug Label Details")
    st.dataframe(
        df.sort_values("report_date", ascending=False).rename(columns={
            "brand_name": "Brand",
            "generic_name": "Generic name",
            "manufacturer_name": "Manufacturer",
            "recall_number": "Recall #",
            "report_date": "Report date",
            "reason_for_recall": "Reason for recall",
        }),
        width="stretch",
        hide_index=True,
    )


st.title("FDA Drug Recall Dashboard")

st.write(
    "Explore FDA drug recalls by manufacturer, date, and reason for recall."
)

df = load_data()

if df.empty:
    st.warning("No recall data was found in project.db.")
    st.stop()


# Interactive manufacturer filter
manufacturers = sorted(
    df["manufacturer_name"]
    .dropna()
    .unique()
)

selected_manufacturer = st.selectbox(
    "Filter by manufacturer",
    ["All manufacturers"] + manufacturers,
)

if selected_manufacturer == "All manufacturers":
    filtered_df = df.copy()
else:
    filtered_df = df[
        df["manufacturer_name"] == selected_manufacturer
    ].copy()


# Summary
st.subheader("Recall Summary")

col1, col2 = st.columns(2)

with col1:
    st.metric("Recall records", len(filtered_df))

with col2:
    st.metric(
        "Manufacturers",
        filtered_df["manufacturer_name"].nunique(),
    )


# Plot 1: Recalls over time
st.subheader("Drug Recalls Over Time")

recalls_over_time = (
    filtered_df
    .dropna(subset=["report_date"])
    .groupby("report_date")
    .size()
    .reset_index(name="recall_count")
    .sort_values("report_date")
)

if not recalls_over_time.empty:
    st.line_chart(
        recalls_over_time.set_index("report_date")[
            "recall_count"
        ]
    )
else:
    st.info("There are no valid report dates to display.")


# Plot 2: Recall reasons
st.subheader("Most Common Recall Reasons")

reason_counts = (
    filtered_df["reason_for_recall"]
    .fillna("Unknown")
    .value_counts()
    .head(10)
)

if not reason_counts.empty:
    st.bar_chart(reason_counts)
else:
    st.info("There are no recall reasons to display.")


# Underlying dataframe (Story 4, #32: label and enforcement data combined)
show_combined_table(filtered_df)