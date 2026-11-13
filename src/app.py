import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from groq import Groq
from build_db import build


DB_PATH = "project.db"
if not Path(DB_PATH).exists():
    build()

st.set_page_config(
    page_title="FDA Drug Recall Dashboard",
    page_icon="💊",
    layout="wide",
)

SUMMARY_MODEL = "openai/gpt-oss-120b"  # or "openai/gpt-oss-20b" for faster/cheaper
SUMMARY_MAX_SAMPLE_ROWS = 40  # keeps prompt ~2,000 tokens (under Groq's 8,000 TPM limit)


def load_data():
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            d.brand_name,
            d.generic_name,
            COALESCE(d.manufacturer_name, e.recalling_firm) AS manufacturer_name,
            e.recall_number,
            e.report_date,
            e.reason_for_recall
        FROM enforcement AS e
        LEFT JOIN drugs AS d
            ON e.product_ndc = d.product_ndc
        ORDER BY e.report_date DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df["report_date"] = pd.to_datetime(
            df["report_date"],
            errors="coerce",
        )

    return df


def generate_summary_text(all_df: pd.DataFrame, start_day: date, end_day: date) -> str:
    reasons = (
        all_df["reason_for_recall"].fillna("Unknown").str[:100]
        .value_counts().head(10).to_string()
    )
    manufacturers = (
        all_df["manufacturer_name"].fillna("Unknown")
        .value_counts().head(10).to_string()
    )
    brands = (
        all_df["brand_name"].fillna("Unknown")
        .value_counts().head(10).to_string()
    )
    per_year = (
        all_df.groupby(all_df["report_date"].dt.year).size().to_string()
    )

    # Sample of most recent rows so prompt stays well below 8,000 TPM
    sample_df = all_df.head(SUMMARY_MAX_SAMPLE_ROWS)
    rows = []
    for _, r in sample_df.iterrows():
        reason = (r["reason_for_recall"] or "Unknown")[:100]
        rows.append(
            f"{r['report_date'].date()} | {r['brand_name']} | "
            f"{r['manufacturer_name']} | {reason}"
        )
    prompt = (
        f"FDA drug recall dataset covering {start_day.isoformat()} "
        f"to {end_day.isoformat()} ({len(all_df)} total records).\n\n"
        f"Recalls per year (all {len(all_df)} records):\n{per_year}\n\n"
        f"Top recall reasons across all records:\n{reasons}\n\n"
        f"Top manufacturers across all records:\n{manufacturers}\n\n"
        f"Top brands across all records:\n{brands}\n\n"
        f"Most recent {len(sample_df)} records (date | brand | manufacturer | reason):\n"
        + "\n".join(rows)
        + "\n\nWrite a concise Daily Summary in a maximum of 3 sentences covering all "
        f"{len(all_df)} sUse only the data above and do not speculate."
    )

    client = Groq()  # reads GROQ_API_KEY
    response = client.chat.completions.create(
        model=SUMMARY_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def get_daily_summary(df: pd.DataFrame):
    """Return (generated_on, range_start, range_end, record_count, summary),
    covering all records and refreshing automatically once per calendar day."""
    today_str = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_summary (
            generated_on TEXT PRIMARY KEY,
            range_start  TEXT,
            range_end    TEXT,
            record_count INTEGER,
            summary      TEXT
        )
        """
    )

    # Migrate table if an older schema exists
    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(daily_summary)").fetchall()
    }
    if not {"range_start", "range_end", "record_count"}.issubset(cols):
        conn.execute("DROP TABLE daily_summary")
        conn.execute(
            """
            CREATE TABLE daily_summary (
                generated_on TEXT PRIMARY KEY,
                range_start  TEXT,
                range_end    TEXT,
                record_count INTEGER,
                summary      TEXT
            )
            """
        )

    row = conn.execute(
        "SELECT generated_on, range_start, range_end, record_count, summary "
        "FROM daily_summary WHERE generated_on = ?",
        (today_str,),
    ).fetchone()
    if row:
        conn.close()
        return row

    dated = df.dropna(subset=["report_date"]).sort_values(
        "report_date", ascending=False
    )
    if dated.empty:
        conn.close()
        return None

    start_day = dated["report_date"].min().date()
    end_day = dated["report_date"].max().date()

    text = generate_summary_text(dated, start_day, end_day)

    conn.execute(
        "INSERT OR REPLACE INTO daily_summary VALUES (?, ?, ?, ?, ?)",
        (today_str, start_day.isoformat(), end_day.isoformat(), len(dated), text),
    )
    conn.commit()
    conn.close()
    return (today_str, start_day.isoformat(), end_day.isoformat(), len(dated), text)


# --- Header & Top-of-Page Automatic Daily Summary ---
st.title("💊 FDA Drug Recall Dashboard")
st.write(
    "Explore FDA drug recalls by manufacturer, date, and reason for recall."
)

df = load_data()

if df.empty:
    st.warning("No recall data was found in project.db.")
    st.stop()

# Sidebar button: clears today's cached summary and regenerates it
if st.sidebar.button("Regenerate today's summary"):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "DELETE FROM daily_summary WHERE generated_on = ?",
            (date.today().isoformat(),),
        )
        conn.commit()
        conn.close()
    except sqlite3.OperationalError:
        pass
    st.rerun()

try:
    summary = get_daily_summary(df)
except Exception as exc:
    summary = None
    st.warning(f"Could not generate today's summary: {exc}")

if summary:
    generated_on, range_start, range_end, record_count, summary_text = summary
    st.subheader(f"Daily Summary ({range_start} to {range_end})")
    st.caption(
        f"Date Range: **{range_start}** to **{range_end}** · "
        f"Records summarized: **{record_count}** · "
        f"Auto-updated on **{generated_on}**"
    )
    st.info(summary_text)

st.divider()


# --- Interactive Manufacturer Filter ---
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


# --- Summary Metrics ---
st.subheader("Recall Summary")

col1, col2 = st.columns(2)

with col1:
    st.metric("Recall records", len(filtered_df))

with col2:
    st.metric(
        "Manufacturers",
        filtered_df["manufacturer_name"].nunique(),
    )


# --- Plot 1: Recalls Over Time ---
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
        recalls_over_time.set_index("report_date")["recall_count"]
    )
else:
    st.info("There are no valid report dates to display.")


# --- Plot 2: Recall Reasons ---
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


# --- Most Recent Recalls ---
st.subheader("Most Recent Recalls")

recent_df = (
    filtered_df
    .copy()
)

recent_columns = [
    "report_date",
    "brand_name",
    "generic_name",
    "manufacturer_name",
    "recall_number",
    "reason_for_recall",
]

complete_fields = recent_df[recent_columns].apply(
    lambda column: (
        column.astype("string").str.strip().ne("").fillna(False)
    )
)
recent_df["_completeness"] = complete_fields.sum(axis=1)
recent_df = (
    recent_df
    .sort_values(
        ["_completeness", "report_date"],
        ascending=[False, False],
        na_position="last",
    )
    .drop(columns="_completeness")
    .reset_index(drop=True)
)

st.dataframe(
    recent_df[recent_columns],
    width="stretch",
    hide_index=True,
    column_config={
        "report_date": st.column_config.DateColumn(
            "Report date", format="YYYY-MM-DD"
        ),
    },
) 
from chat import render_chat
render_chat(recent_df) 