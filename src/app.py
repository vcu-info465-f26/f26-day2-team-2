
import json
import os
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI
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


def build_summary_context(df):
    dated_records = df.dropna(subset=["report_date"])
    date_range = "Unavailable"
    if not dated_records.empty:
        date_range = (
            f"{dated_records['report_date'].min():%Y-%m-%d} to "
            f"{dated_records['report_date'].max():%Y-%m-%d}"
        )

    recent_records = df.sort_values(
        "report_date", ascending=False, na_position="last"
    ).head(10).copy()
    recent_records["report_date"] = recent_records["report_date"].dt.strftime(
        "%Y-%m-%d"
    )

    return json.dumps({
        "data_range": date_range,
        "recall_product_rows": len(df),
        "distinct_recall_notices": int(df["recall_number"].nunique()),
        "records_with_manufacturer": int(df["manufacturer_name"].notna().sum()),
        "top_manufacturers": df["manufacturer_name"]
        .dropna()
        .value_counts()
        .head(10)
        .to_dict(),
        "top_recall_reasons": df["reason_for_recall"]
        .fillna("Unknown")
        .value_counts()
        .head(8)
        .to_dict(),
        "most_recent_recalls": recent_records[[
            "report_date",
            "brand_name",
            "generic_name",
            "manufacturer_name",
            "reason_for_recall",
        ]].fillna("Not listed").to_dict(orient="records"),
    })


@st.cache_data(ttl=86400)
def generate_daily_summary(summary_context, generation_date):
    api_key = os.environ.get("GROQ_API")
    if not api_key:
        raise RuntimeError("GROQ_API is not configured")

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a concise, factual daily summary of these FDA "
                    "drug recall statistics. Use only facts and numbers in "
                    "the supplied JSON; do not recalculate counts or infer "
                    "unsupported trends. Clearly distinguish recall-product "
                    "rows from distinct recall notices. Do not give medical "
                    "advice. Format the top reasons under this Markdown "
                    "heading: ### Top recall reasons (frequency across all "
                    "records). Do not include a Key Takeaways section."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Generated on {generation_date}. Summarize this data:\n"
                    f"{summary_context}"
                ),
            },
        ],
        reasoning_effort="low",
    )
    summary = response.choices[0].message.content
    if not summary:
        raise RuntimeError("The AI returned an empty summary")
    return summary


st.title("FDA Drug Recall Dashboard")

st.write(
    "Explore FDA drug recalls by manufacturer, date, and reason for recall."
)

df = load_data()

if df.empty:
    st.warning("No recall data was found in project.db.")
    st.stop()

summary_context = build_summary_context(df)
summary_dates = df["report_date"].dropna()
coverage = "Data range unavailable"
if not summary_dates.empty:
    coverage = (
        f"Data range: {summary_dates.min():%B %d, %Y} to "
        f"{summary_dates.max():%B %d, %Y}"
    )

st.header("Daily AI Summary")
st.caption(f"{coverage} | Generated: {date.today():%B %d, %Y}")
try:
    st.markdown(
        generate_daily_summary(summary_context, date.today().isoformat())
    )
except Exception:
    st.info("AI summary unavailable. Check GROQ_API and your network connection.")


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


# Underlying dataframe
st.subheader("Underlying Recall Data")

display_columns = [
    "brand_name",
    "generic_name",
    "manufacturer_name",
    "recall_number",
    "report_date",
    "reason_for_recall",
]

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Most Recent Recalls")

recent_df = (
    filtered_df
    .sort_values("report_date", ascending=False, na_position="last")
    .reset_index(drop=True)
)

recent_columns = [
    "report_date",
    "brand_name",
    "generic_name",
    "manufacturer_name",
    "recall_number",
    "reason_for_recall",
]

st.dataframe(
    recent_df[recent_columns],
    use_container_width=True,
    hide_index=True,
    column_config={
        "report_date": st.column_config.DateColumn(
            "Report date", format="YYYY-MM-DD"
        ),
    },
)